from conans import ConanFile
import os

class pkg_b(ConanFile):
  name = "pkg_b"
  topics = ("conan")

  settings = "os", "arch", "compiler", "build_type"

  requires = (
    "pkg_a/1.0"
  )

  def package_id(self):
    self.info.header_only()

  def package_info(self):
    self.cpp_info.name = "pkg_b"
    self.cpp_info.components["pkg_b_lib"].name = "pkg_b_lib"
    self.cpp_info.components["pkg_b_lib"].includes = ["include"]
    self.cpp_info.components["pkg_b_lib"].requires = ["pkg_a::pkg_a_lib"]
