import info
import os
from CraftStandardDirs import CraftStandardDirs
from CraftCore import CraftCore

class subinfo(info.infoclass):
    def setTargets(self):
        for ver in ["6.0.0-tineDrive"]:
            self.svnTargets[ver] = f"[git]https://github.com/tine20/craft-blueprints-tineDrive.git|{ver}|"
        self.defaultTarget = "6.0.0-tineDrive"

    def setDependencies(self):
        self.buildDependencies["craft/craft-core"] = "default"


from Package.SourceOnlyPackageBase import *


class Package(SourceOnlyPackageBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.subinfo.options.package.disableBinaryCache = True
        self.subinfo.options.dailyUpdate = True

    def unpack(self):
        return True

    def install(self):
        return True

    def qmerge(self):
        if not SourceOnlyPackageBase.qmerge(self):
            return False
        CraftCore.cache.clear()
        return True

    def createPackage(self):
        return True

    def checkoutDir(self, index=0):
        return os.path.join(CraftStandardDirs.blueprintRoot(), self.package.name)
