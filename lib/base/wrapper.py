import configparser
import subprocess

from logger import logger
from .lockfile import LockFile


class ConanWrapper:
    @staticmethod
    def run(cmd, shell=True, text=True, capture_output=True, **kwargs):
        logger.debug(f"Run: {cmd}")
        result = subprocess.run(cmd, shell=shell, text=text, capture_output=capture_output, **kwargs)
        logger.debug(f"Result: {result.stdout}")
        if result.returncode:
            raise Exception(result.stderr)
        return result

    @staticmethod
    def export(path, version, **kwargs):
        return ConanWrapper.run(f"conan export {path} {version}@", **kwargs)

    @staticmethod
    def create_lock(lockfile, 
        conanfile_path=None, reference=None, revision=None,
        profile=None, remote=None, update=False, options=[], build=[],
        testonly=False, **kwargs
      ):
        cmd = f"conan lock create --lockfile-out={lockfile}" 
        if conanfile_path:  cmd += f" {conanfile_path}"
        elif reference:
            cmd += f" --reference={reference}@"
            if revision:
                cmd += f"#{revision}"
        if profile:         cmd += f" --profile={profile}"
        if remote:          cmd += f" --remote={remote}"
        if update:          cmd += f" --update"
        for option in options:
            cmd += f" --options={option}"
        for b in build:
            cmd += f" --build={b}"
        ConanWrapper.run(cmd, **kwargs)
        return LockFile(lockfile)

    @staticmethod
    def get(package, revision=None, package_id=None, remote=None, **kwargs):
        cmd = f"conan get --raw {package}@"
        if revision:    cmd += f"#{revision}"
        if package_id:  cmd += f":{package_id}"
        if remote:      cmd += f" --remote {remote}"
        response = ConanWrapper.run(cmd, **kwargs)
        return ConanGetResponse(package, response)

    @staticmethod
    def create(
        conanfile_path=None, version=None, options=[],
        profile=None, lockfile=None, **kwargs
    ):
        cmd = f"conan create"
        if conanfile_path: cmd += f" {conanfile_path}"
        if version: cmd += f" {version}@"
        if lockfile:  cmd += f" --lockfile={lockfile}"
        else:
            if profile:    cmd += f" --profile={profile}"
            for option in options:
                cmd += f" --options={option}"
        return ConanWrapper.run(cmd, **kwargs)


class ConanGetResponse:
    def __init__(self, pkg, result):
        self.pkg = pkg
        self.__pkg_name = pkg.split("/")[0]
        self.config = configparser.ConfigParser(delimiters=["="], allow_no_value=True)
        self.__parse_response(result.stdout)

    def __parse_response(self, response):
        self.config.optionxform = str  # keep the original letter case
        self.config.read_string(response)
        # full_requires have options without values: pkg_name/version:pkg_id
        # to handle easier later, set the pkg_id as a value to them
        for option, value in self.config.items("full_requires"):
            pkg_name, pkg_id = option.split(":")
            self.config.remove_option("full_requires", option)
            self.config.set("full_requires", pkg_name, pkg_id)

    @property
    def build_options(self):
        return [(f"{self.__pkg_name}:{k}", v) for k, v in self.config.items("options")]

    @property
    def requires(self):
        return [r for r,_ in self.config.items("requires")]

    @property
    def full_requires(self):
        return self.config.items("full_requires")

    @property
    def full_options(self):
        all_options = []
        for option in self.config.items("full_options"):
            k, v = option
            if k.find(":") == -1:
                all_options.append((f"{self.__pkg_name}:{k}", v))
            else:
                all_options.append(option)
        return all_options

    @property
    def full_settings(self):
        return self.config.items("full_settings")
