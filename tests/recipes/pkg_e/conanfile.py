from conans import ConanFile

class pkg_e(ConanFile):
  name = "pkg_e"
  topics = ("conan")
  settings = "os", "arch", "compiler", "build_type"
  build_requires = (
      "pkg_d/1.0"
  )

  def package_info(self):
    self.cpp_info.name = "pkg_e"
    self.cpp_info.components["pkg_e_lib"].name = "pkg_e_lib"
