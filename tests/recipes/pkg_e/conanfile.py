from conans import ConanFile

class pkg_e(ConanFile):
  name = "pkg_e"
  topics = ("conan")
  settings = "os", "arch", "compiler", "build_type"
  build_requires = (
      "pkg_d/1.0"
  )

  def package_info(self):
    self.cpp_info.libs = ["e"]
