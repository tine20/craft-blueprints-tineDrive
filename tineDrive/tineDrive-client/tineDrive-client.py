import os
import re
import subprocess
import utils
from pathlib import Path

import info
from Packager.NullsoftInstallerPackager import NullsoftInstallerPackager
from Blueprints.CraftPackageObject import CraftPackageObject
from CraftCore import CraftCore

class subinfo(info.infoclass):
    def registerOptions(self):
        self.options.dynamic.registerOption("buildVfsWin", False)
        self.options.dynamic.registerOption("buildNumber", "")
        self.options.dynamic.registerOption("enableCrashReporter", False)
        self.options.dynamic.registerOption("enableAppImageUpdater", False)
        self.options.dynamic.registerOption("enableAutoUpdater", False)
        self.options.dynamic.registerOption("forceAsserts", False)

    def setTargets(self):
        self.versionInfo.setDefaultValues(
            tarballUrl="https://download.tineDrive.com/desktop/stable/tineDriveclient-${VERSION}.tar.xz",
            tarballInstallSrc="tineDriveclient-${VERSION}",
            gitUrl="[git]https://github.com/tine20/tineDrive",
        )

        self.description = "tineDrive Desktop Client"
        self.displayName = "tineDrive"
        self.webpage = "https://www.tine-groupware.de"

    def setDependencies(self):
        self.buildDependencies["craft/craft-blueprints-tineDrive"] = None
        self.buildDependencies["dev-utils/cmake"] = None
        self.buildDependencies["kde/frameworks/extra-cmake-modules"] = None

        self.runtimeDependencies["libs/libre-graph-api-cpp-qt-client"] = None
        self.runtimeDependencies["libs/sparkle"] = None
        self.runtimeDependencies["libs/zlib"] = None
        self.runtimeDependencies["libs/sqlite"] = None
        if CraftCore.compiler.isWindows:
            self.buildDependencies["libs/nlohmann-json"] = None

        self.runtimeDependencies["libs/qt/qtbase"] = None
        self.runtimeDependencies["libs/qt/qttranslations"] = None
        self.runtimeDependencies["libs/qt/qtsvg"] = None
        self.runtimeDependencies["libs/qt/qtimageformats"] = None
        self.runtimeDependencies["libs/qt/qtdeclarative"] = None
        if CraftCore.compiler.isLinux:
            self.runtimeDependencies["libs/qt/qtwayland"] = None

        self.runtimeDependencies["qt-libs/qtkeychain"] = None
        self.runtimeDependencies["libs/kdsingleapplication"] = None

        if self.options.dynamic.buildVfsWin:
            self.runtimeDependencies["tineDrive/client-desktop-vfs-win"] = None

        if self.options.dynamic.enableAppImageUpdater:
            self.runtimeDependencies["libs/libappimageupdate"] = None

        if self.options.dynamic.enableCrashReporter:
            self.runtimeDependencies["tineDrive/libcrashreporter-qt"] = None
            self.buildDependencies["dev-utils/breakpad"] = None
            self.buildDependencies["dev-utils/symsorter"] = None


from Package.CMakePackageBase import *


class Package(CMakePackageBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.subinfo.options.fetch.checkoutSubmodules = True
        # TODO: fix msi generation which expects the existance of a /translation dir
        self.subinfo.options.package.moveTranslationsToBin = False

        extraParam = os.environ.get("OWNCLOUD_CMAKE_PARAMETERS", "")
        if extraParam:
            # appending a string will convert the args to a string
            self.subinfo.options.configure.args += self.subinfo.options.configure.args
        if self.subinfo.options.dynamic.buildVfsWin:
            self.win_vfs_plugin = CraftPackageObject.get("tineDrive/client-desktop-vfs-win")
            self.subinfo.options.configure.args += [f"-DVIRTUAL_FILE_SYSTEM_PLUGINS=off;suffix;{self.win_vfs_plugin.instance.sourceDir()}"]
        if self.subinfo.options.dynamic.enableCrashReporter:
            self.subinfo.options.configure.args += ["-DWITH_CRASHREPORTER=ON"]
        if self.subinfo.options.dynamic.enableAutoUpdater:
            self.subinfo.options.configure.args += ["-DWITH_AUTO_UPDATER=ON"]
        if self.subinfo.options.dynamic.enableAppImageUpdater:
            self.subinfo.options.configure.args += ["-DWITH_APPIMAGEUPDATER=ON"]
        if self.subinfo.options.dynamic.forceAsserts:
            self.subinfo.options.configure.args += ["-DFORCE_ASSERTS=ON"]
        if self.subinfo.options.dynamic.buildNumber:
            self.subinfo.options.configure.args += [f"-DMIRALL_VERSION_BUILD={self.subinfo.options.dynamic.buildNumber}"]

    @staticmethod
    def _get_env_vars(*names, fallback=None):
        for name in names:
            try:
                value = os.environ[name]

            except KeyError:
                continue

            return value

        else:
            return fallback

    @property
    def applicationExecutable(self):
        return self._get_env_vars("ApplicationExecutable", "APPLICATION_EXECUTABLE", fallback="tineDrive")

    @property
    def applicationShortname(self):
        return self._get_env_vars("ApplicationShortname", "APPLICATION_SHORTNAME", fallback="tineDrive")

    def fetch(self):
        if self.subinfo.options.dynamic.buildVfsWin:
            if not self.win_vfs_plugin.instance.fetch(noop=False):
                return False
        return super().fetch()

    def unpack(self):
        if self.subinfo.options.dynamic.buildVfsWin:
            if not self.win_vfs_plugin.instance.unpack(noop=False):
                return False
        return super().unpack()

    def install(self):
        if not super().install():
            return False

        if CraftCore.compiler.isWindows:
            # ensure we can find the sync-exclude.lst
            configDirName = self.applicationShortname

            if not configDirName:
                configDirName = self.applicationExecutable

            assert configDirName

            configDir = Path(self.installDir()) / "config" / configDirName

            if not configDir.exists():
                configDir = Path(self.installDir()) / "etc" / configDirName

            if configDir.exists():
                if not utils.mergeTree(configDir, Path(self.installDir()) / "bin"):
                    return False

        return True

    def dumpSymbols(self) -> bool:
        dest = self.archiveDebugDir() / "symbols"
        utils.cleanDirectory(dest)
        allowError = None
        if CraftCore.compiler.isWindows:
            skipDumpPattern = r"icu\d\d\.dll|asprintf-0\.dll|b2-1\.dll"
            if CraftCore.compiler.isWindows:
                for package in ["libs/runtime", "libs/d3dcompiler", "libs/gettext"]:
                    dbPackage = CraftCore.installdb.getInstalledPackages(CraftPackageObject.get(package))
                    if dbPackage:
                        files = dbPackage[0].getFiles()
                        skipDumpPattern += "|" + "|".join([re.escape(Path(x[0]).name) for x in files])
            allowError = re.compile(skipDumpPattern)
        else:
            # libs/qt6/qtbase installs .o files...
            # executing command: /drone/src/linux-64-gcc/dev-utils/bin/symsorter --compress --compress --output /drone/src/linux-64-gcc/build/owncloud/owncloud-client/archive-dbg/symbols /drone/src/linux-64-gcc/qml/Qt/test/controls/objects-RelWithDebInfo/QuickControlsTestUtilsPrivate_resources_1/.rcc/qrc_qmake_Qt_test_controls.cpp.o /drone/src/linux-64-gcc/qml/Qt/test/controls/objects-RelWithDebInfo/QuickControlsTestUtilsPrivate_resources_1/.rcc/qrc_qmake_Qt_test_controls.cpp.o.debug
            #
            # Sorting debug information files
            #
            # qrc_qmake_Qt_test_controls.cpp.o (rel, x86_64) -> /drone/src/linux-64-gcc/build/owncloud/owncloud-client/archive-dbg/symbols/00/0000e90000000000000000009f79900/executable
            #
            # error: failed to process file qrc_qmake_Qt_test_controls.cpp.o.debug
            #
            #   caused by failed to generate debug identifier
            allowError = re.compile(r".*\.o")

        for binaryFile in utils.filterDirectoryContent(
            self.archiveDir(), whitelist=lambda x, root: utils.isBinary(os.path.join(root, x)), blacklist=lambda x, root: True
        ):
            binaryFile = Path(binaryFile)
            # Assume all files are installed and the symbols are located next to the binary
            # TODO:
            installedBinary = CraftCore.standardDirs.craftRoot() / binaryFile.relative_to(self.archiveDir())
            if not installedBinary.exists():
                CraftCore.log.warning(f"{installedBinary} does not exist")
                return False

            if CraftCore.compiler.isWindows:
                symbolFile = Path(f"{installedBinary}.pdb")
                if not symbolFile.exists():
                    pdb = utils.getPDBForBinary(installedBinary)
                    if pdb:
                        symbolFile = installedBinary.parent / utils.getPDBForBinary(installedBinary).name
            elif CraftCore.compiler.isMacOS:
                debugInfoPath = installedBinary
                bundleDir = list(filter(lambda x: x.name.endswith(".framework") or x.name.endswith(".app"), debugInfoPath.parents))
                if bundleDir:
                    debugInfoPath = bundleDir[-1]
                debugInfoPath = Path(f"{debugInfoPath}.dSYM/Contents/Resources/DWARF/") / installedBinary.name
                if debugInfoPath.exists():
                    symbolFile = debugInfoPath
            elif CraftCore.compiler.isUnix:
                symbolFile = Path(f"{installedBinary}.debug")

            if not symbolFile.exists():
                if allowError and allowError.match(binaryFile.name):
                    # ignore errors in files matching allowError
                    continue
                CraftCore.log.warning(f"{symbolFile} does not exist")
                return False
            if not utils.system(["symsorter", "--compress", "--compress", "--output", dest, installedBinary, symbolFile]):
                if allowError and allowError.match(binaryFile.name):
                    # ignore errors in files matching allowError
                    CraftCore.log.warning(f"Ignoring error for {binaryFile.name}")
                    continue
                return False
        return True

    def owncloudVersion(self):
        versionFile = self.sourceDir() / "VERSION.cmake"
        if not versionFile.exists():
            CraftCore.log.warning(f"Failed to find {versionFile}")
            return None

        print_var_script = os.path.join(self.blueprintDir(), "print-var.cmake")

        def get_var(name) -> str:
            command = ["cmake", f"-DTARGET_SCRIPT={os.path.basename(versionFile)}", f"-DTARGET_VAR={name}"]

            if self.subinfo.options.dynamic.buildNumber:
                command.append(f"-DMIRALL_VERSION_BUILD={self.subinfo.options.dynamic.buildNumber}")

            command += ["-P", print_var_script]

            value = subprocess.check_output(
                command,
                cwd=os.path.dirname(versionFile),
                # make sure this call returns str instead of bytes
                universal_newlines=True,
            )
            value = value.strip()
            assert value, f"{name} empty"
            return value

        version_str = get_var("MIRALL_VERSION_STRING")

        print(f"*** version string fetched with CMake: {version_str} ***")

        return version_str

    def createPackage(self):
        self.blacklist_file.append(os.path.join(self.blueprintDir(), "blacklist.txt"))
        self.defines["appname"] = self.applicationExecutable
        self.defines["appimage_native_package_name"] = f'{self.applicationShortname.lower().replace("_", "-")}-client'
        self.defines["apppath"] = "Applications/KDE/" + self.applicationExecutable + ".app"
        self.defines["company"] = "Metaways Infosystems GmbH"

        exePath = f"{self.defines['appname']}{CraftCore.compiler.executableSuffix}"
        if isinstance(self, NullsoftInstallerPackager):
            exePath = f"bin/{exePath}"
        self.defines["shortcuts"] = [
            {
                "name": self.subinfo.displayName,
                "target": exePath,
                "description": self.subinfo.description,
            }
        ]
        self.defines["icon"] = self.buildDir() / "src/gui/tineDrive.ico"
        self.defines["pkgproj"] = self.buildDir() / "admin/osx/macosx.pkgproj"
        if CraftPackageObject.get("dev-utils/linuxdeploy-plugin-native-packages").isInstalled:
            self.defines["appimage_extra_output"] = ["native_packages"]
        ver = self.owncloudVersion()
        if ver:
            self.defines["version"] = ver

        self.addExecutableFilter(r"(bin|libexec)/(?!(" + self.applicationExecutable + r")).*")
        self.ignoredPackages += ["binary/mysql"]
        if not CraftCore.compiler.isLinux:
            self.ignoredPackages += ["libs/dbus"]
        return super().createPackage()

    def preArchiveMove(self):
        if self.subinfo.options.dynamic.enableCrashReporter:
            if not self.dumpSymbols():
                return False
        return super().preArchive()
