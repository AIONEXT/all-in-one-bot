#!/usr/bin/env python3
"""
macOS Build Script for AIO Bot.
Creates a .app bundle and DMG installer.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd, **kwargs):
    """Run a command and return result."""
    print(f"[build] {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kwargs)


def main():
    """Build macOS app bundle and DMG."""
    project_root = Path(__file__).parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    # Clean previous builds
    for d in [dist_dir, build_dir]:
        if d.exists():
            shutil.rmtree(d)

    # PyInstaller spec for macOS
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

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

# macOS app bundle
app = BUNDLE(
    a.pure + a.zipped_data,
    a.binaries + a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AIOBot',
    icon='{project_root}/assets/icon.icns' if Path('{project_root}/assets/icon.icns').exists() else None,
    bundle_identifier='com.aiobot.app',
    info_plist={{
        'CFBundleName': 'AIO Bot',
        'CFBundleDisplayName': 'AIO Bot',
        'CFBundleVersion': '2.0.0',
        'CFBundleShortVersionString': '2.0.0',
        'NSHighResolutionCapable': True,
        'LSUIElement': True,  # Run as background app
    }},
)
'''

    spec_path = project_root / "aio_bot_macos.spec"
    spec_path.write_text(spec_content)

    # Run PyInstaller
    run([sys.executable, "-m", "PyInstaller", str(spec_path), "--noconfirm", "--clean"])

    # Create DMG
    app_path = dist_dir / "AIOBot.app"
    if app_path.exists():
        dmg_path = dist_dir / "AIOBot-2.0.0-macos.dmg"
        run([
            "hdiutil", "create",
            "-volname", "AIO Bot",
            "-srcfolder", str(app_path),
            "-ov", "-format", "UDZO",
            str(dmg_path)
        ])
        print(f"[build] Done. DMG is at: {dmg_path}")
    else:
        print("[build] Error: App bundle not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
