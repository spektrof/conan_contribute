import os
import re
import subprocess


class RecipeUpdateModes():
    NONE = 0
    EXPAND_REVISION = 1
    IGNORE_PACKAGE_ID = 2
    ALL = 3


class RecipeUpdater():
    def __init__(self, mode = RecipeUpdateModes.IGNORE_PACKAGE_ID):
        self.mode = mode
        self.recipe_path = None
        self.previous_content = None
    
    def apply(self, patch_file=None, **kwargs):
        self.recipe_dir = kwargs.pop("recipe_dir")
        self.recipe_path = os.path.join(self.recipe_dir, "conanfile.py")
        if not os.path.exists(self.recipe_path): return

        self.patch_file = patch_file
        if self.patch_file:
            self.__patch(force=True)

        with open(self.recipe_path, "r") as content:
            self.previous_content = content.read()

        actual_content = self.previous_content
        if self.mode & RecipeUpdateModes.IGNORE_PACKAGE_ID:
            actual_content = self.__ignore_package_id(actual_content)
        if self.mode & RecipeUpdateModes.EXPAND_REVISION:
            actual_content = self.__expand_revision(actual_content, **kwargs)     
    
        with open(self.recipe_path, "w") as recipe:
            recipe.write(actual_content)

    def revert(self):
        if self.recipe_path and self.previous_content:
            with open(self.recipe_path, "w") as recipe:
                recipe.write(self.previous_content)

        if self.patch_file:
            self.__patch(reverse=True)
            self.patch_file = None

    def __patch(self, force=False, reverse=False):
        cmd = f"patch -i {self.patch_file} -d {self.recipe_dir}"
        if force:       cmd += " --force"
        if reverse:     cmd += " --reverse"
        subprocess.check_output(cmd, shell=True)    

    def __ignore_package_id(self, actual_content):
        actual_content = re.sub(r"(\s\sdef package_id.*)\s\sdef", "  def", actual_content, flags=re.DOTALL)
        return actual_content
        
    def __expand_revision(self, actual_content, packages):
        visited = []
        for package in reversed(list(packages.values())):
            if not package.revision: continue
            if package.reference in visited: continue
            visited.append(package.reference)
            actual_content = re.sub(package.reference, package.as_str(revision=True), actual_content)
        return actual_content
