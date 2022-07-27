from conans import ConanFile

class pkg_d(ConanFile):
  name = "pkg_d"
  topics = ("conan")
  settings = "os", "arch", "compiler", "build_type"
  options = {"with_optimization" : [True, False]}
  default_options = {"with_optimization" : False}
