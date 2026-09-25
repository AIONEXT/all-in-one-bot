"""
AIO Bot GUI Package - Cross-platform desktop interface using PySide6.
"""

# PySide6 imports with fallback
try:
    from aio_bot.gui.dashboard import DashboardWidget
    from aio_bot.gui.main_window import MainWindow
    from aio_bot.gui.settings_dialog import SettingsDialog
    from aio_bot.gui.system_monitor_widget import SystemMonitorWidget
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    MainWindow = None
    DashboardWidget = None
    SystemMonitorWidget = None
    SettingsDialog = None

__all__ = ['MainWindow', 'DashboardWidget', 'SystemMonitorWidget', 'SettingsDialog', 'GUI_AVAILABLE']
