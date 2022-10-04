from conans import ConanFile
from conan.tools.files import save, copy
import os, json

class pkg_b(ConanFile):
  name = "pkg_b"
  topics = ("conan")

  settings = "os", "arch", "compiler", "build_type"

  requires = (
    "pkg_a/1.0"
  )

  def generate(self):
    requires = []
    tool_requires = []
    for d in self.dependencies.values():
      if d.context == "build":
        tool_requires.append(repr(d.ref))
      else:
        requires.append(repr(d.ref))
    result = {"requires": requires,
              "tool_requires": tool_requires}
    save(self, "msdeps.json", json.dumps(result))

  def package(self):
    copy(self, "msdeps.json", dst=self.package_folder, src=self.generators_folder)
    
  def package_id(self):
    self.info.header_only()

  def package_info(self):
    pass
