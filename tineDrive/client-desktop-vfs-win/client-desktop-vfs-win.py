import io
import os
import re

import info


class subinfo(info.infoclass):
    def setTargets(self):
        self.versionInfo.setDefaultValues(gitUrl="git@github.com:owncloud/client-desktop-vfs-win.git")

        for ver in self.targets:
            # we don't have tarballs only branches
            del self.targets[ver]
            self.svnTargets[ver] = self.versionInfo.format("git@github.com:owncloud/client-desktop-vfs-win.git|${VERSION_MAJOR}.${VERSION_MINOR}|", ver)

        self.description = "tineDrive Desktop Client - virtual file systme plugin"
        self.webpage = "https://www.tine-groupware.de"

    def setDependencies(self):
        self.buildDependencies["craft/craft-blueprints-tineDrive"] = None


from Package.VirtualPackageBase import *


class Package(SourceComponentPackageBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
