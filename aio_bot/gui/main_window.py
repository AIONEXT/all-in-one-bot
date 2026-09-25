"""
Main Window for AIO Bot GUI.
"""

import logging
from datetime import datetime

from PySide6.QtCore import QSize, QThread, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QToolBar,
)

from aio_bot.core.bot import AIOBot, BotState
from aio_bot.gui.automation_widget import AutomationWidget
from aio_bot.gui.dashboard import DashboardWidget
from aio_bot.gui.files_widget import FilesWidget
from aio_bot.gui.health_widget import HealthWidget
from aio_bot.gui.learning_widget import LearningWidget
from aio_bot.gui.settings_dialog import SettingsDialog
from aio_bot.gui.system_monitor_widget import SystemMonitorWidget


class BotWorkerThread(QThread):
    """Background thread for bot operations."""

    status_updated = Signal(object)
    log_message = Signal(str, int)  # message, level

    def __init__(self, bot: AIOBot):
        super().__init__()
        self.bot = bot
        self._running = False

    def run(self):
        self._running = True
        # This would run the bot's async loop
        # For now, we'll use a timer in the main thread
        self.exec()

    def stop(self):
        self._running = False
        self.quit()
        self.wait()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, bot: AIOBot):
        super().__init__()
        self.bot = bot
        self.logger = logging.getLogger("AIOBot.GUI.MainWindow")
        self._tray_icon: QSystemTrayIcon | None = None
        self._update_timer: QTimer | None = None

        self._setup_ui()
        self._setup_tray()
        self._setup_timers()
        self._connect_signals()

        # Apply theme
        self._apply_theme()

        self.logger.info("Main window initialized")

    def _setup_ui(self):
        """Setup the main UI."""
        self.setWindowTitle(f"{self.bot.config.app_name} v{self.bot.config.version}")
        self.setMinimumSize(1000, 700)

        # Central widget with tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(True)
        self.setCentralWidget(self.tab_widget)

        # Create tabs
        self.dashboard = DashboardWidget(self.bot)
        self.tab_widget.addTab(self.dashboard, "Dashboard")

        self.system_monitor = SystemMonitorWidget(self.bot)
        self.tab_widget.addTab(self.system_monitor, "System Monitor")

        # Health tab placeholder
        self.health_widget = HealthWidget(self.bot)
        self.tab_widget.addTab(self.health_widget, "Health")

        # Learning tab placeholder
        self.learning_widget = LearningWidget(self.bot)
        self.tab_widget.addTab(self.learning_widget, "Learning")

        # Files tab placeholder
        self.files_widget = FilesWidget(self.bot)
        self.tab_widget.addTab(self.files_widget, "Files")

        # Automation tab placeholder
        self.automation_widget = AutomationWidget(self.bot)
        self.tab_widget.addTab(self.automation_widget, "Automation")

        # Settings tab
        self.settings_dialog = SettingsDialog(self.bot, self)
        self.tab_widget.addTab(self.settings_dialog, "Settings")

        # Menu bar
        self._setup_menu_bar()

        # Toolbar
        self._setup_toolbar()

        # Status bar
        self._setup_status_bar()

    def _setup_menu_bar(self):
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_all)
        view_menu.addAction(refresh_action)

        view_menu.addSeparator()

        # Theme submenu
        theme_menu = view_menu.addMenu("&Theme")

        light_action = QAction("&Light", self)
        light_action.setCheckable(True)
        light_action.triggered.connect(lambda: self._set_theme("light"))
        theme_menu.addAction(light_action)

        dark_action = QAction("&Dark", self)
        dark_action.setCheckable(True)
        dark_action.triggered.connect(lambda: self._set_theme("dark"))
        theme_menu.addAction(dark_action)

        system_action = QAction("&System", self)
        system_action.setCheckable(True)
        system_action.triggered.connect(lambda: self._set_theme("system"))
        theme_menu.addAction(system_action)

        # Set current theme checked
        current_theme = self.bot.config.gui.theme
        if current_theme == "light":
            light_action.setChecked(True)
        elif current_theme == "dark":
            dark_action.setChecked(True)
        else:
            system_action.setChecked(True)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        run_maintenance_action = QAction("Run &Maintenance Now", self)
        run_maintenance_action.triggered.connect(self._run_maintenance)
        tools_menu.addAction(run_maintenance_action)

        tools_menu.addSeparator()

        check_updates_action = QAction("Check for &Updates", self)
        check_updates_action.triggered.connect(self._check_updates)
        tools_menu.addAction(check_updates_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        docs_action = QAction("&Documentation", self)
        docs_action.triggered.connect(self._open_docs)
        help_menu.addAction(docs_action)

    def _setup_toolbar(self):
        """Setup the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Refresh action
        refresh_action = QAction(self.style().standardIcon(QStyle.SP_BrowserReload), "Refresh", self)
        refresh_action.triggered.connect(self._refresh_all)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # Start/Stop bot
        self.start_action = QAction(self.style().standardIcon(QStyle.SP_MediaPlay), "Start Bot", self)
        self.start_action.triggered.connect(self._toggle_bot)
        toolbar.addAction(self.start_action)

        # Maintenance action
        maint_action = QAction(self.style().standardIcon(QStyle.SP_ComputerIcon), "Maintenance", self)
        maint_action.triggered.connect(self._run_maintenance)
        toolbar.addAction(maint_action)

        toolbar.addSeparator()

        # Settings
        settings_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Settings", self)
        settings_action.triggered.connect(lambda: self.tab_widget.setCurrentWidget(self.settings_dialog))
        toolbar.addAction(settings_action)

    def _setup_status_bar(self):
        """Setup the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_bar.addWidget(self.status_label)

        # Permanent widgets
        self.cpu_label = QLabel("CPU: --%")
        self.status_bar.addPermanentWidget(self.cpu_label)

        self.mem_label = QLabel("RAM: --%")
        self.status_bar.addPermanentWidget(self.mem_label)

        self.disk_label = QLabel("Disk: --%")
        self.status_bar.addPermanentWidget(self.disk_label)

        self.uptime_label = QLabel("Uptime: --")
        self.status_bar.addPermanentWidget(self.uptime_label)

    def _setup_tray(self):
        """Setup system tray icon."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.warning("System tray not available")
            return

        self._tray_icon = QSystemTrayIcon(self)

        # Create tray icon
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self._tray_icon.setIcon(icon)
        self._tray_icon.setToolTip(f"{self.bot.config.app_name} - Running")

        # Tray menu
        tray_menu = QMenu()

        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_normal)
        tray_menu.addAction(show_action)

        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        maintenance_action = QAction("Run Maintenance", self)
        maintenance_action.triggered.connect(self._run_maintenance)
        tray_menu.addAction(maintenance_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_application)
        tray_menu.addAction(quit_action)

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._tray_activated)

        if self.bot.config.gui.show_tray_icon:
            self._tray_icon.show()

    def _setup_timers(self):
        """Setup update timers."""
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_ui)
        self._update_timer.start(self.bot.config.gui.dashboard_refresh_seconds * 1000)

    def _connect_signals(self):
        """Connect bot signals."""
        # Bot status updates would come through signals
        pass

    def _apply_theme(self):
        """Apply the current theme."""
        theme = self.bot.config.gui.theme

        if theme == "dark":
            self._apply_dark_theme()
        elif theme == "light":
            self._apply_light_theme()
        else:
            # System theme - use default
            pass

    def _apply_dark_theme(self):
        """Apply dark theme."""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #3c3c3c;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
            QTabBar::tab:hover {
                background-color: #4c4c4c;
            }
            QMenuBar {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #0078d4;
            }
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3c3c3c;
            }
            QMenu::item:selected {
                background-color: #0078d4;
            }
            QToolBar {
                background-color: #2b2b2b;
                border: none;
                spacing: 4px;
            }
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: #3c3c3c;
            }
            QStatusBar {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                text-align: center;
                background-color: #3c3c3c;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
            QGroupBox {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QTableWidget {
                background-color: #2b2b2b;
                alternate-background-color: #333333;
                gridline-color: #3c3c3c;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #3c3c3c;
            }
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #4c4c4c;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5c5c5c;
            }
        """)

    def _apply_light_theme(self):
        """Apply light theme."""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #ffffff;
                color: #000000;
            }
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #000000;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #e0e0e0;
            }
        """)

    def _set_theme(self, theme: str):
        """Set the application theme."""
        self.bot.config.gui.theme = theme
        self.bot.config_manager.save()
        self._apply_theme()

    def _refresh_all(self):
        """Refresh all widgets."""
        self.dashboard.refresh()
        self.system_monitor.refresh()
        self.health_widget.refresh()
        self.learning_widget.refresh()
        self.files_widget.refresh()
        self.automation_widget.refresh()

    def _toggle_bot(self):
        """Toggle bot running state."""
        if self.bot.state == BotState.RUNNING:
            # Would stop the bot
            self.start_action.setText("Start Bot")
            self.start_action.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.status_label.setText("Bot stopped")
        else:
            # Would start the bot
            self.start_action.setText("Stop Bot")
            self.start_action.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
            self.status_label.setText("Bot running")

    def _run_maintenance(self):
        """Run maintenance tasks."""
        # This would trigger maintenance in the bot
        QMessageBox.information(self, "Maintenance", "Maintenance tasks scheduled.")
        self.logger.info("Manual maintenance triggered")

    def _check_updates(self):
        """Check for updates."""
        QMessageBox.information(self, "Updates", "Checking for updates...")
        self.logger.info("Manual update check triggered")

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(self, "About AIO Bot",
            f"<h3>{self.bot.config.app_name} v{self.bot.config.version}</h3>"
            "<p>All-In-One Desktop Intelligence System</p>"
            "<p>A fully automated, AI-driven master mind for system management.</p>"
            "<p>&copy; 2024 AIO Bot Team</p>"
        )

    def _open_docs(self):
        """Open documentation."""
        import webbrowser
        webbrowser.open("https://github.com/aio-bot/docs")

    def _tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()

    def show_normal(self):
        """Show the window normally."""
        self.show()
        self.raise_()
        self.activateWindow()

    def _update_ui(self):
        """Update UI with latest data."""
        try:
            status = self.bot.get_status()

            # Update status label
            state_text = status.state.value.capitalize()
            if status.started_at:
                uptime = datetime.now() - status.started_at
                hours = int(uptime.total_seconds() // 3600)
                minutes = int((uptime.total_seconds() % 3600) // 60)
                self.uptime_label.setText(f"Uptime: {hours}h {minutes}m")

            self.status_label.setText(f"Status: {state_text} | Tasks: {status.active_tasks} | Errors: {status.errors_count}")

            # Update system metrics
            metrics = self.bot.system_monitor.get_latest_metrics() if self.bot.system_monitor else None
            if metrics:
                self.cpu_label.setText(f"CPU: {metrics.cpu_percent:.1f}%")
                self.mem_label.setText(f"RAM: {metrics.memory_percent:.1f}%")

                # Get primary disk usage
                if metrics.disk_usage:
                    primary_disk = list(metrics.disk_usage.values())[0]
                    self.disk_label.setText(f"Disk: {primary_disk['percent']:.1f}%")

            # Update widgets
            self.dashboard.update_data()
            self.system_monitor.update_data()

        except Exception as e:
            self.logger.error("UI update error: %s", e)

    def closeEvent(self, event):
        """Handle close event."""
        if self.bot.config.gui.start_minimized and self._tray_icon and self._tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            self._quit_application()
            event.accept()

    def _quit_application(self):
        """Quit the application."""
        self.logger.info("Application quit requested")

        # Stop bot
        if hasattr(self.bot, 'stop'):
            asyncio.create_task(self.bot.stop())

        # Hide tray
        if self._tray_icon:
            self._tray_icon.hide()

        # Quit
        QApplication.quit()


