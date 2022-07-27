import configparser
import json
import os

from typing import Iterable


class LockFileNode:
    def __init__(self, node):
        self.__node = node
        self.ref = None
        _ref = node.get("ref", None)
        if _ref:
            self.ref, self.revision = _ref.split("#")
            self.name, self.version = self.ref.split("/")
        self.package_id = node.get("package_id")
        self.prev = node.get("prev")
        options = node.get("options", None).split("\n")
        self.raw_options = options
        self.requires = node.get("requires", [])
        self.build_requires = node.get("build_requires", [])
        self.path = node.get("path", None)

        self.options = {}
        for option in options:
            if not option:
                continue
            k, v = option.split("=")
            self.options[k] = v

    def __getattr__(self, attr):
        return self.__node.get(attr, None)


class LockFileProfileHost:
    def __init__(self, raw_string: str):
        self.config = configparser.ConfigParser(delimiters=["="], allow_no_value=True)
        self.config.optionxform = str  # keep the original letter case
        self.config.read_string(raw_string)

    def get(self, section: str, keys: Iterable):
        return {k: v for k, v in self.config.items(section) if k in keys}


class LockFile:
    def __init__(self, lockfile_path):
        lockfile = None
        with open(lockfile_path, "r") as f:
            lockfile = json.load(f)
        self.raw_nodes = lockfile["graph_lock"]["nodes"]
        self.profile_host: LockFileProfileHost = LockFileProfileHost(
            lockfile["profile_host"]
        )
        self.nodes = {k: LockFileNode(v) for k, v in self.raw_nodes.items()}
        _conanfile_node = self.nodes.get("0")
        if _conanfile_node and _conanfile_node.path:
            self.conanfile_path = os.path.normpath(os.path.join(os.path.dirname(lockfile_path), _conanfile_node.path))

    @property
    def first_node(self):
        return self.nodes.get("1")

    @property
    def node_set(self):
        return set(self.nodes.values())
