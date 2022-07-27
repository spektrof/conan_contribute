import copy
import os
import shutil


class ConanEnvironment():

    def __init__(self, root = os.getcwd(), test_case = "test_case", keep=False):
        self.test_case_dir = os.path.join(root, test_case)
        self.keep = keep
        self.user_home = os.path.join(self.test_case_dir, "home")
        self.storage_path = os.path.join(self.test_case_dir, "data")
        # need to save environ to be able encapsulate different processes
        self.env = copy.deepcopy(os.environ)
        self.env.update({
            "CONAN_USER_HOME" : self.user_home,
            "CONAN_STORAGE_PATH" : self.storage_path,
        })
    
    def __enter__(self):
        shutil.rmtree(self.storage_path, ignore_errors=True)
        shutil.rmtree(self.user_home, ignore_errors=True)
        os.makedirs(self.storage_path)
        os.makedirs(self.user_home)
        return self
    
    def __exit__(self, exception_type, exception_value, traceback):
        if not self.keep:
            shutil.rmtree(self.test_case_dir, ignore_errors=False)
    
    def copy_directory(self, src, dst):
        if not os.path.exists(src): return

        if not os.path.exists(dst):
            os.makedirs(dst)

        for f in os.listdir(src):
            s = os.path.join(src, f)
            d = os.path.join(dst, f)
            if os.path.isdir(s):
                if not os.path.exists(d):
                    os.makedirs(d)
                self.copy_directory(s, d)
            else:
                shutil.copy2(s, d)
                os.chmod(d, 0o755)

    def run_with_env_forward(self, fp, **args):
        return fp(**args, cwd=self.test_case_dir, env=self.env)

    def init(self):
        conan_user_home_to_inherit = os.environ.get("CONAN_USER_HOME")
        if not conan_user_home_to_inherit:
            raise Exception("Please set up your CONAN_USER_HOME!")
        self.copy_directory(conan_user_home_to_inherit, self.env.get("CONAN_USER_HOME"))
        print(f"conan_user_home_to_inherit = {conan_user_home_to_inherit}")
        print(f"CONAN_USER_HOME = {self.env.get('CONAN_USER_HOME')}")

