from conans import ConanFile
import os

class pkg_a(ConanFile):
  name = "pkg_a"
  topics = ("conan")

  settings = "os", "arch", "compiler", "build_type"
  options = {"shared": [True, False], "fPIC": [True, False]}
  default_options = {"shared": False, "fPIC": True}

  def configure(self):
    if self.options.shared:
        self.options.fPIC = False

  def package_info(self):
    self.cpp_info.libs = ["a"]
