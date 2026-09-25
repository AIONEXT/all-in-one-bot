#!/usr/bin/env python3
"""
Linux Build Script for AIO Bot.
Creates AppImage, .deb, and .rpm packages.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd, **kwargs):
    """Run a command and return result."""
    print(f"[build] {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kwargs)


def create_appdir(project_root, dist_dir):
    """Create AppDir structure for AppImage."""
    appdir = dist_dir / "AIOBot.AppDir"
    usr_bin = appdir / "usr" / "bin"
    usr_lib = appdir / "usr" / "lib"
    usr_share = appdir / "usr" / "share"
    applications = usr_share / "applications"
    icons = usr_share / "icons" / "hicolor" / "256x256" / "apps"

    for d in [usr_bin, usr_lib, applications, icons]:
        d.mkdir(parents=True, exist_ok=True)

    # Copy the built executable
    exe_src = dist_dir / "AllInOneBot" / "AllInOneBot"
    if exe_src.exists():
        shutil.copy2(exe_src, usr_bin / "aiobot")
    else:
        # Build with PyInstaller first
        pass

    # Desktop file
    desktop_content = """[Desktop Entry]
Type=Application
Name=AIO Bot
GenericName=All-In-One System Intelligence
Comment=Comprehensive system monitoring and automation
Exec=aiobot
Icon=aiobot
Terminal=false
Categories=System;Utility;Monitor;
StartupNotify=true
"""
    (applications / "aiobot.desktop").write_text(desktop_content)

    # AppRun script
    apprun_content = """#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
export PYTHONPATH="${HERE}/usr/lib/python3.12/site-packages:${PYTHONPATH}"
exec "${HERE}/usr/bin/aiobot" "$@"
"""
    apprun = appdir / "AppRun"
    apprun.write_text(apprun_content)
    apprun.chmod(0o755)

    # Icon (placeholder)
    # shutil.copy(project_root / "assets/icon.png", icons / "aiobot.png")

    return appdir


def build_appimage(project_root):
    """Build AppImage using appimagetool."""
    dist_dir = project_root / "dist"
    appdir = create_appdir(project_root, dist_dir)

    # Download appimagetool if not present
    appimagetool = dist_dir / "appimagetool-x86_64.AppImage"
    if not appimagetool.exists():
        run([
            "wget", "-q", "-O", str(appimagetool),
            "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        ])
        appimagetool.chmod(0o755)

    # Build AppImage
    output = dist_dir / "AIOBot-2.0.0-x86_64.AppImage"
    run([str(appimagetool), str(appdir), str(output)])

    print(f"[build] AppImage created: {output}")
    return output


def build_deb(project_root):
    """Build .deb package."""
    dist_dir = project_root / "dist"
    pkg_dir = dist_dir / "pkg_deb"

    # Clean
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)

    # Create structure
    debian = pkg_dir / "DEBIAN"
    usr_bin = pkg_dir / "usr" / "bin"
    usr_lib = pkg_dir / "usr" / "lib"
    usr_share = pkg_dir / "usr" / "share"
    applications = usr_share / "applications"
    icons = usr_share / "icons" / "hicolor" / "256x256" / "apps"

    for d in [debian, usr_bin, usr_lib, applications, icons]:
        d.mkdir(parents=True, exist_ok=True)

    # Control file
    control_content = """Package: aiobot
Version: 2.0.0
Section: utils
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.11), libglib2.0-0, libqt6core6, libqt6widgets6, libqt6gui6
Maintainer: AIO Bot Team <team@aiobot.example>
Description: All-In-One System Intelligence Bot
 Comprehensive system monitoring, AI-driven habit learning,
 automated file organization, health monitoring, and self-healing.
"""
    (debian / "control").write_text(control_content)

    # Copy executable (would need to be built for Linux)
    # shutil.copy(dist_dir / "AllInOneBot" / "AllInOneBot", usr_bin / "aiobot")

    # Desktop file
    desktop_content = """[Desktop Entry]
Type=Application
Name=AIO Bot
Exec=aiobot
Icon=aiobot
Terminal=false
Categories=System;Utility;Monitor;
"""
    (applications / "aiobot.desktop").write_text(desktop_content)

    # Build .deb
    output = dist_dir / "aiobot_2.0.0_amd64.deb"
    run(["dpkg-deb", "--build", str(pkg_dir), str(output)])

    print(f"[build] DEB created: {output}")
    return output


def build_rpm(project_root):
    """Build .rpm package."""
    dist_dir = project_root / "dist"
    rpmbuild = Path.home() / "rpmbuild"

    # Create rpmbuild structure
    for d in ["BUILD", "RPMS", "SOURCES", "SPECS", "SRPMS"]:
        (rpmbuild / d).mkdir(parents=True, exist_ok=True)

    # Spec file
    spec_content = """Name: aiobot
Version: 2.0.0
Release: 1%{?dist}
Summary: All-In-One System Intelligence Bot

License: MIT
URL: https://github.com/aiobot/aiobot
Source0: %{name}-%{version}.tar.gz

Requires: python3 >= 3.11, qt6-qtbase, qt6-qtdeclarative

%description
Comprehensive system monitoring, AI-driven habit learning,
automated file organization, health monitoring, and self-healing.

%prep
%autosetup

%build
# Build would happen here

%install
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/lib/aiobot
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps

# install -m 755 aiobot %{buildroot}/usr/bin/
# install -m 644 aiobot.desktop %{buildroot}/usr/share/applications/

%files
/usr/bin/aiobot
/usr/lib/aiobot/
/usr/share/applications/aiobot.desktop
/usr/share/icons/hicolor/256x256/apps/aiobot.png

%changelog
* Wed Sep 25 2024 AIO Bot Team <team@aiobot.example> - 2.0.0-1
- Initial release
"""
    spec_file = rpmbuild / "SPECS" / "aiobot.spec"
    spec_file.write_text(spec_content)

    # Build RPM
    run(["rpmbuild", "-ba", str(spec_file)])

    # Find output
    rpm_files = list((rpmbuild / "RPMS" / "x86_64").glob("aiobot-*.rpm"))
    if rpm_files:
        output = dist_dir / rpm_files[0].name
        shutil.copy2(rpm_files[0], output)
        print(f"[build] RPM created: {output}")
        return output

    return None


def main():
    """Build Linux packages."""
    project_root = Path(__file__).parent
    dist_dir = project_root / "dist"
    dist_dir.mkdir(exist_ok=True)

    # First build the executable with PyInstaller
    print("[build] Building Linux executable with PyInstaller...")
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{project_root}/run_bot.py'],
    pathex=['{project_root}'],
    binaries=[],
    datas=[
        ('{project_root}/aio_bot', 'aio_bot'),
    ],
    hiddenimports=[
        'psutil',
        'GPUtil',
        'croniter',
        'PySide6',
        'yaml',
        'watchdog',
        'plyer',
        'keyring',
        'cryptography',
        'aio_bot.config.manager',
        'aio_bot.core.bot',
        'aio_bot.monitoring.system_monitor',
        'aio_bot.learning.habit_engine',
        'aio_bot.data_mgmt.file_organizer',
        'aio_bot.health.health_monitor',
        'aio_bot.automation.task_runner',
        'aio_bot.automation.scheduler',
        'aio_bot.security.manager',
        'aio_bot.gui.app',
        'aio_bot.gui.main_window',
        'aio_bot.gui.dashboard',
        'aio_bot.gui.system_monitor_widget',
        'aio_bot.gui.health_widget',
        'aio_bot.gui.learning_widget',
        'aio_bot.gui.files_widget',
        'aio_bot.gui.automation_widget',
        'aio_bot.gui.settings_dialog',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AllInOneBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''

    spec_path = project_root / "aio_bot_linux.spec"
    spec_path.write_text(spec_content)

    run([sys.executable, "-m", "PyInstaller", str(spec_path), "--noconfirm", "--clean"])

    # Build packages
    print("[build] Building AppImage...")
    try:
        build_appimage(project_root)
    except Exception as e:
        print(f"[build] AppImage build failed: {e}")

    print("[build] Building DEB...")
    try:
        build_deb(project_root)
    except Exception as e:
        print(f"[build] DEB build failed: {e}")

    print("[build] Building RPM...")
    try:
        build_rpm(project_root)
    except Exception as e:
        print(f"[build] RPM build failed: {e}")

    print("[build] Done!")


if __name__ == "__main__":
    main()
