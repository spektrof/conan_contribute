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
    pass
