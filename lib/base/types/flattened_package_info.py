import dataclasses


@dataclasses.dataclass(frozen=False)
class FlattenedPackageInfo:
    """Class to store a package configuration"""
    name : str = dataclasses.field(default_factory=str)
    version : str = dataclasses.field(default_factory=str)
    revision : str = dataclasses.field(default_factory=str)
    pid : str = dataclasses.field(default_factory=str)
    prev : str = dataclasses.field(default_factory=str)
    remote : str = dataclasses.field(default_factory=str)
    profiles : str = dataclasses.field(default_factory=str)
    options : dict = dataclasses.field(default_factory=dict)
    requires : list = dataclasses.field(default_factory=list)
    required_by : list = dataclasses.field(default_factory=list)
    lockfile_path : str = dataclasses.field(default_factory=str)

    @property
    def full_package_reference(self):
        return self.as_str(revision=True, pid=True, prev=True)

    @property
    def full_reference(self):
        return self.as_str(revision=True, pid=True)

    @property
    def reference(self):
        return self.as_str(revision=False, pid=False)

    def as_str(self, revision=None, pid=None, prev=None):
        result = f"{self.name}/{self.version}"
        if revision and self.revision:  result+= f"#{self.revision}"
        if pid and self.pid:       result+= f":{self.pid}"
        if prev and self.prev:       result+= f"#{self.prev}"
        return result
