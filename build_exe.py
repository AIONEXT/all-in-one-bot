"""Build a standalone Windows .exe for the all-in-one bot.

Usage:
    pip install -r requirements-build.txt
    python build_exe.py

This bundles the FastAPI backend, example client, and the new AIO Bot modules
into a single executable that can be run on any Windows machine without Python installed.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC_NAME = "all_in_one_bot.spec"


def run(cmd, **kwargs):
    print(f"[build] {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kwargs)


def clean():
    for d in (DIST, BUILD, ROOT / SPEC_NAME):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    for p in ROOT.glob("*.spec"):
        p.unlink()


def main():
    clean()

    spec = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run_bot.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('backend', 'backend'),
        ('client', 'client'),
        ('aio_bot', 'aio_bot'),
        ('.env.example', '.'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.config',
        'uvicorn.server',
        'fastapi',
        'fastapi.middleware.cors',
        'fastapi.security',
        'pydantic',
        'pydantic_settings',
        'jose',
        'jose.jwt',
        'aiohttp',
        'websockets',
        'websockets.legacy',
        'websockets.server',
        'websockets.client',
        'dotenv',
        'psutil',
        'GPUtil',
        'croniter',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'aio_bot.core.bot',
        'aio_bot.config.manager',
        'aio_bot.monitoring.system_monitor',
        'aio_bot.learning.habit_engine',
        'aio_bot.data_mgmt.file_organizer',
        'aio_bot.health.health_monitor',
        'aio_bot.automation.task_runner',
        'aio_bot.automation.scheduler',
        'aio_bot.security.manager',
        'aio_bot.gui.main_window',
        'aio_bot.gui.dashboard',
        'aio_bot.gui.system_monitor_widget',
        'aio_bot.gui.health_widget',
        'aio_bot.gui.learning_widget',
        'aio_bot.gui.files_widget',
        'aio_bot.gui.automation_widget',
        'aio_bot.gui.settings_dialog',
        'aio_bot.gui.app',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AllInOneBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='AllInOneBot',
    upx_exclude=[],
)
"""

    spec_path = ROOT / SPEC_NAME
    spec_path.write_text(spec, encoding="utf-8")

    # Run PyInstaller with the generated spec.
    run([sys.executable, "-m", "PyInstaller", str(spec_path), "--noconfirm", "--clean"])

    exe_path = DIST / "AllInOneBot" / "AllInOneBot.exe"
    print(f"\n[build] Done. Executable is at: {exe_path}")


if __name__ == "__main__":
    main()
