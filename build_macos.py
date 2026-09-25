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

    # Use PyInstaller command-line with all options
    # This avoids complex spec file issues
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",  # No console window (GUI app)
        "--name", "AIOBot",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--add-data", f"{project_root}/aio_bot:aio_bot",
        "--hidden-import", "psutil",
        "--hidden-import", "GPUtil",
        "--hidden-import", "croniter",
        "--hidden-import", "PySide6",
        "--hidden-import", "yaml",
        "--hidden-import", "watchdog",
        "--hidden-import", "plyer",
        "--hidden-import", "keyring",
        "--hidden-import", "cryptography",
        "--hidden-import", "aio_bot.config.manager",
        "--hidden-import", "aio_bot.core.bot",
        "--hidden-import", "aio_bot.monitoring.system_monitor",
        "--hidden-import", "aio_bot.learning.habit_engine",
        "--hidden-import", "aio_bot.data_mgmt.file_organizer",
        "--hidden-import", "aio_bot.health.health_monitor",
        "--hidden-import", "aio_bot.automation.task_runner",
        "--hidden-import", "aio_bot.automation.scheduler",
        "--hidden-import", "aio_bot.security.manager",
        "--hidden-import", "aio_bot.gui.app",
        "--hidden-import", "aio_bot.gui.main_window",
        "--hidden-import", "aio_bot.gui.dashboard",
        "--hidden-import", "aio_bot.gui.system_monitor_widget",
        "--hidden-import", "aio_bot.gui.health_widget",
        "--hidden-import", "aio_bot.gui.learning_widget",
        "--hidden-import", "aio_bot.gui.files_widget",
        "--hidden-import", "aio_bot.gui.automation_widget",
        "--hidden-import", "aio_bot.gui.settings_dialog",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "scipy",
        "--osx-bundle-identifier", "com.aiobot.app",
        f"{project_root}/aio_bot/gui/app.py"
    ]

    # Add icon if it exists
    icon_path = project_root / "assets" / "icon.icns"
    if icon_path.exists():
        pyinstaller_cmd.insert(-1, "--icon")
        pyinstaller_cmd.insert(-1, str(icon_path))

    # Run PyInstaller
    run(pyinstaller_cmd)

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
