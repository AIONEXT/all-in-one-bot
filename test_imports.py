#!/usr/bin/env python3
"""
Test script to verify AIO Bot modules can be imported correctly.
"""

import sys
import traceback


def test_import(module_name, import_path):
    """Test importing a module."""
    try:
        __import__(import_path)
        print(f"✓ {module_name}")
        return True
    except Exception as e:
        print(f"✗ {module_name}: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all import tests."""
    print("Testing AIO Bot module imports...\n")

    # Add project root to path
    sys.path.insert(0, r"C:\Users\aio_s\Projects\all-in-one-bot-main")

    tests = [
        ("Config Manager", "aio_bot.config.manager"),
        ("Core Bot", "aio_bot.core.bot"),
        ("System Monitor", "aio_bot.monitoring.system_monitor"),
        ("Habit Engine", "aio_bot.learning.habit_engine"),
        ("File Organizer", "aio_bot.data_mgmt.file_organizer"),
        ("Health Monitor", "aio_bot.health.health_monitor"),
        ("Task Runner", "aio_bot.automation.task_runner"),
        ("Scheduler", "aio_bot.automation.scheduler"),
        ("Security Manager", "aio_bot.security.manager"),
        ("GUI Main Window", "aio_bot.gui.main_window"),
        ("Dashboard Widget", "aio_bot.gui.dashboard"),
        ("System Monitor Widget", "aio_bot.gui.system_monitor_widget"),
        ("Health Widget", "aio_bot.gui.health_widget"),
        ("Learning Widget", "aio_bot.gui.learning_widget"),
        ("Files Widget", "aio_bot.gui.files_widget"),
        ("Automation Widget", "aio_bot.gui.automation_widget"),
        ("Settings Dialog", "aio_bot.gui.settings_dialog"),
        ("GUI App", "aio_bot.gui.app"),
    ]

    passed = 0
    failed = 0

    for name, path in tests:
        if test_import(name, path):
            passed += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("All modules imported successfully!")
        return 0
    else:
        print("Some modules failed to import.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
