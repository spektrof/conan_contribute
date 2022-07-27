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
    self.cpp_info.name = "pkg_a"
    self.cpp_info.components["pkg_a_lib"].name = "pkg_a_lib"
    self.cpp_info.components["pkg_a_lib"].libdirs = ["lib"]
    self.cpp_info.components["pkg_a_lib"].libs = ["lib"]