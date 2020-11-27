import info
import os

import io
import re

class subinfo(info.infoclass):
    def setTargets(self):
        self.versionInfo.setDefaultValues(gitUrl="ssh://git@gitea.tineDrive.services:2222/client/client-plugin-vfs-win.git")

        for ver in self.targets:
            # we don't have tarballs only branches
            del self.targets[ver]
            self.svnTargets[ver] = self.versionInfo.format("ssh://git@gitea.tineDrive.services:2222/client/client-plugin-vfs-win.git|${VERSION_MAJOR}.${VERSION_MINOR}|", ver)

        self.description = "tineDrive Desktop Client - virtual file systme plugin"
        self.webpage = "https://tineDrive.org"

    def setDependencies(self):
        self.buildDependencies["craft/craft-blueprints-tineDrive"] = None

from Package.VirtualPackageBase import *

class Package(SourceComponentPackageBase):
    def __init__(self):
        SourceComponentPackageBase.__init__(self)
