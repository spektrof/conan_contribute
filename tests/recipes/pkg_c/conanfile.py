from conans import ConanFile

class pkg_c(ConanFile):
  name = "pkg_c"
  settings = "os", "arch", "compiler", "build_type"
  requires = "pkg_b/1.0"

  def package_info(self):
    self.cpp_info.libs = ["c"]
