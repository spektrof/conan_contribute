from conans import ConanFile

class pkg_c(ConanFile):
  name = "pkg_c"
  settings = "os", "arch", "compiler", "build_type"
  requires = "pkg_b/1.0"

  def package_info(self):
    self.cpp_info.name = "pkg_c"
    self.cpp_info.components["pkg_c_lib"].name = "pkg_c_lib"
    self.cpp_info.components["pkg_c_lib"].requires = ["pkg_b::pkg_b_lib"]
