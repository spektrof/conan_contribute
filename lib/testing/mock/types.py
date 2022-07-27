import dataclasses

from base.types import FlattenedConanPackageInfo


@dataclasses.dataclass(frozen=False)
class PackageToBuild():
    """The class is used to store information to build a conan package"""

    package : FlattenedConanPackageInfo = dataclasses.field(default_factory=FlattenedConanPackageInfo)
    patch_file : str = dataclasses.field(default_factory=str)

    @property
    def name(self):
        return self.package.name

    @property
    def version(self):
        return self.package.version

    @property
    def revision(self):
        return self.package.revision

    @revision.setter
    def revision(self, value):
        self.package.revision = value

    @property
    def pid(self):
        return self.package.pid

    @pid.setter
    def pid(self, value):
        self.package.pid = value

    @property
    def options(self):
        return self.package.options

    @options.setter
    def options(self, value):
        self.package.options = value

    @property
    def prev(self):
        return self.package.prev

    @prev.setter
    def prev(self, value):
        self.package.prev = value

    @property
    def requires(self):
        return self.package.requires
    
    @requires.setter
    def requires(self, value):
        self.package.requires = value

    @property
    def reference(self):
        return self.package.reference

    @property
    def full_reference(self):
        return self.package.full_reference

    @property
    def full_package_reference(self):
        return self.package.full_package_reference

    def as_str(self, **kwargs):
        return self.package.as_str(**kwargs)
