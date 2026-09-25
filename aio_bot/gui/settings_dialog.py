"""
Settings Dialog for AIO Bot GUI.
"""

import logging

from PySide6.QtCore import QTime
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from aio_bot.core.bot import AIOBot


class SettingsDialog(QWidget):
    """Settings dialog for AIO Bot."""

    def __init__(self, bot: AIOBot, parent=None):
        super().__init__(parent)
        self.bot = bot
        self.logger = logging.getLogger("AIOBot.GUI.SettingsDialog")
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Setup the settings UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(16, 16, 16, 16)

        # Tabs for each config section
        self.tabs = QTabWidget()
        content_layout.addWidget(self.tabs)

        # General tab
        self.general_tab = QWidget()
        self._setup_general_tab()
        self.tabs.addTab(self.general_tab, "General")

        # Monitoring tab
        self.monitoring_tab = QWidget()
        self._setup_monitoring_tab()
        self.tabs.addTab(self.monitoring_tab, "Monitoring")

        # Learning tab
        self.learning_tab = QWidget()
        self._setup_learning_tab()
        self.tabs.addTab(self.learning_tab, "Learning")

        # Data Management tab
        self.data_tab = QWidget()
        self._setup_data_tab()
        self.tabs.addTab(self.data_tab, "Data Management")

        # Health tab
        self.health_tab = QWidget()
        self._setup_health_tab()
        self.tabs.addTab(self.health_tab, "Health")

        # Automation tab
        self.automation_tab = QWidget()
        self._setup_automation_tab()
        self.tabs.addTab(self.automation_tab, "Automation")

        # Security tab
        self.security_tab = QWidget()
        self._setup_security_tab()
        self.tabs.addTab(self.security_tab, "Security")

        # GUI tab
        self.gui_tab = QWidget()
        self._setup_gui_tab()
        self.tabs.addTab(self.gui_tab, "Interface")

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(save_btn)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        buttons_layout.addWidget(reset_btn)

        content_layout.addLayout(buttons_layout)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_section(self, parent_layout, title: str) -> QGroupBox:
        """Create a section group box."""
        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(8)
        parent_layout.addWidget(group)
        return group

    def _add_field(self, layout: QGridLayout, row: int, label: str, widget, tooltip: str = ""):
        """Add a field to a grid layout."""
        lbl = QLabel(label + ":")
        lbl.setFont(QFont("Segoe UI", 9))
        if tooltip:
            lbl.setToolTip(tooltip)
            widget.setToolTip(tooltip)
        layout.addWidget(lbl, row, 0)
        layout.addWidget(widget, row, 1)

    def _setup_general_tab(self):
        """Setup general settings tab."""
        layout = QVBoxLayout(self.general_tab)
        layout.setSpacing(16)

        # App info
        info_group = self._create_section(layout, "Application")
        info_layout = QGridLayout(info_group)

        self.app_name = QLineEdit()
        self._add_field(info_layout, 0, "Application Name", self.app_name)

        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self._add_field(info_layout, 1, "Log Level", self.log_level)

        self.data_dir = QLineEdit()
        self.data_dir.setReadOnly(True)
        self._add_field(info_layout, 2, "Data Directory", self.data_dir)

        # Startup
        startup_group = self._create_section(layout, "Startup")
        startup_layout = QGridLayout(startup_group)

        self.auto_start = QCheckBox("Start automatically on login")
        startup_layout.addWidget(self.auto_start, 0, 0, 1, 2)

        self.start_minimized = QCheckBox("Start minimized to tray")
        startup_layout.addWidget(self.start_minimized, 1, 0, 1, 2)

        self.show_tray = QCheckBox("Show system tray icon")
        startup_layout.addWidget(self.show_tray, 2, 0, 1, 2)

        layout.addStretch()

    def _setup_monitoring_tab(self):
        """Setup monitoring settings tab."""
        layout = QVBoxLayout(self.monitoring_tab)
        layout.setSpacing(16)

        # General monitoring
        gen_group = self._create_section(layout, "General")
        gen_layout = QGridLayout(gen_group)

        self.mon_enabled = QCheckBox("Enable system monitoring")
        gen_layout.addWidget(self.mon_enabled, 0, 0, 1, 2)

        self.mon_interval = QSpinBox()
        self.mon_interval.setRange(5, 3600)
        self.mon_interval.setSuffix(" seconds")
        self._add_field(gen_layout, 1, "Check Interval", self.mon_interval)

        # Thresholds
        thresh_group = self._create_section(layout, "Alert Thresholds")
        thresh_layout = QGridLayout(thresh_group)

        self.cpu_threshold = QDoubleSpinBox()
        self.cpu_threshold.setRange(10, 100)
        self.cpu_threshold.setSuffix(" %")
        self._add_field(thresh_layout, 0, "CPU Usage", self.cpu_threshold)

        self.mem_threshold = QDoubleSpinBox()
        self.mem_threshold.setRange(10, 100)
        self.mem_threshold.setSuffix(" %")
        self._add_field(thresh_layout, 1, "Memory Usage", self.mem_threshold)

        self.disk_threshold = QDoubleSpinBox()
        self.disk_threshold.setRange(10, 100)
        self.disk_threshold.setSuffix(" %")
        self._add_field(thresh_layout, 2, "Disk Usage", self.disk_threshold)

        # Component enables
        comp_group = self._create_section(layout, "Components")
        comp_layout = QGridLayout(comp_group)

        self.net_mon = QCheckBox("Network Monitoring")
        comp_layout.addWidget(self.net_mon, 0, 0)

        self.gpu_mon = QCheckBox("GPU Monitoring")
        comp_layout.addWidget(self.gpu_mon, 0, 1)

        self.proc_mon = QCheckBox("Process Monitoring")
        comp_layout.addWidget(self.proc_mon, 1, 0)

        self.log_mon = QCheckBox("Log Monitoring")
        comp_layout.addWidget(self.log_mon, 1, 1)

        self.smart_mon = QCheckBox("SMART Disk Monitoring")
        comp_layout.addWidget(self.smart_mon, 2, 0)

        layout.addStretch()

    def _setup_learning_tab(self):
        """Setup learning settings tab."""
        layout = QVBoxLayout(self.learning_tab)
        layout.setSpacing(16)

        # General
        gen_group = self._create_section(layout, "General")
        gen_layout = QGridLayout(gen_group)

        self.learn_enabled = QCheckBox("Enable habit learning")
        gen_layout.addWidget(self.learn_enabled, 0, 0, 1, 2)

        self.model_update_interval = QSpinBox()
        self.model_update_interval.setRange(1, 168)
        self.model_update_interval.setSuffix(" hours")
        self._add_field(gen_layout, 1, "Model Update Interval", self.model_update_interval)

        self.detection_window = QSpinBox()
        self.detection_window.setRange(1, 90)
        self.detection_window.setSuffix(" days")
        self._add_field(gen_layout, 2, "Detection Window", self.detection_window)

        self.min_confidence = QDoubleSpinBox()
        self.min_confidence.setRange(0.1, 1.0)
        self.min_confidence.setSingleStep(0.05)
        self.min_confidence.setSuffix("")
        self._add_field(gen_layout, 3, "Min Pattern Confidence", self.min_confidence)

        self.auto_schedule = QCheckBox("Auto-schedule predicted tasks")
        gen_layout.addWidget(self.auto_schedule, 4, 0, 1, 2)

        self.prediction_horizon = QSpinBox()
        self.prediction_horizon.setRange(1, 30)
        self.prediction_horizon.setSuffix(" days")
        self._add_field(gen_layout, 5, "Prediction Horizon", self.prediction_horizon)

        # Privacy
        privacy_group = self._create_section(layout, "Privacy")
        privacy_layout = QGridLayout(privacy_group)

        self.privacy_mode = QComboBox()
        self.privacy_mode.addItems(["Local Only", "Anonymized", "Cloud Sync"])
        self._add_field(privacy_layout, 0, "Privacy Mode", self.privacy_mode)

        layout.addStretch()

    def _setup_data_tab(self):
        """Setup data management settings tab."""
        layout = QVBoxLayout(self.data_tab)
        layout.setSpacing(16)

        # General
        gen_group = self._create_section(layout, "General")
        gen_layout = QGridLayout(gen_group)

        self.data_enabled = QCheckBox("Enable file management")
        gen_layout.addWidget(self.data_enabled, 0, 0, 1, 2)

        self.auto_organize = QCheckBox("Auto-organize files")
        gen_layout.addWidget(self.auto_organize, 1, 0, 1, 2)

        self.organize_interval = QSpinBox()
        self.organize_interval.setRange(1, 168)
        self.organize_interval.setSuffix(" hours")
        self._add_field(gen_layout, 2, "Organize Interval", self.organize_interval)

        # Cleanup
        cleanup_group = self._create_section(layout, "Cleanup")
        cleanup_layout = QGridLayout(cleanup_group)

        self.dup_detection = QCheckBox("Duplicate Detection")
        cleanup_layout.addWidget(self.dup_detection, 0, 0, 1, 2)

        self.temp_cleanup = QCheckBox("Cleanup Temp Files")
        cleanup_layout.addWidget(self.temp_cleanup, 1, 0, 1, 2)

        self.cleanup_interval = QSpinBox()
        self.cleanup_interval.setRange(1, 168)
        self.cleanup_interval.setSuffix(" hours")
        self._add_field(cleanup_layout, 2, "Cleanup Interval", self.cleanup_interval)

        self.max_temp_age = QSpinBox()
        self.max_temp_age.setRange(1, 90)
        self.max_temp_age.setSuffix(" days")
        self._add_field(cleanup_layout, 3, "Max Temp File Age", self.max_temp_age)

        # Backup
        backup_group = self._create_section(layout, "Backup")
        backup_layout = QGridLayout(backup_group)

        self.backup_enabled = QCheckBox("Enable Backups")
        backup_layout.addWidget(self.backup_enabled, 0, 0, 1, 2)

        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(1, 168)
        self.backup_interval.setSuffix(" hours")
        self._add_field(backup_layout, 1, "Backup Interval", self.backup_interval)

        self.backup_retention = QSpinBox()
        self.backup_retention.setRange(1, 365)
        self.backup_retention.setSuffix(" days")
        self._add_field(backup_layout, 2, "Backup Retention", self.backup_retention)

        # Watched directories
        dirs_group = self._create_section(layout, "Watched Directories")
        dirs_layout = QVBoxLayout(dirs_group)

        self.dirs_list = QListWidget()
        dirs_layout.addWidget(self.dirs_list)

        dirs_btns = QHBoxLayout()
        add_dir_btn = QPushButton("Add")
        add_dir_btn.clicked.connect(self._add_watch_dir)
        remove_dir_btn = QPushButton("Remove")
        remove_dir_btn.clicked.connect(self._remove_watch_dir)
        dirs_btns.addWidget(add_dir_btn)
        dirs_btns.addWidget(remove_dir_btn)
        dirs_btns.addStretch()
        dirs_layout.addLayout(dirs_btns)

        layout.addStretch()

    def _setup_health_tab(self):
        """Setup health monitoring settings tab."""
        layout = QVBoxLayout(self.health_tab)
        layout.setSpacing(16)

        # General
        gen_group = self._create_section(layout, "General")
        gen_layout = QGridLayout(gen_group)

        self.health_enabled = QCheckBox("Enable health monitoring")
        gen_layout.addWidget(self.health_enabled, 0, 0, 1, 2)

        self.check_interval = QSpinBox()
        self.check_interval.setRange(1, 1440)
        self.check_interval.setSuffix(" minutes")
        self._add_field(gen_layout, 1, "Check Interval", self.check_interval)

        self.critical_threshold = QSpinBox()
        self.critical_threshold.setRange(1, 10)
        self._add_field(gen_layout, 2, "Critical Alert Threshold", self.critical_threshold)

        # Log sources
        logs_group = self._create_section(layout, "Log Sources")
        logs_layout = QGridLayout(logs_group)

        self.win_event_log = QCheckBox("Windows Event Logs")
        logs_layout.addWidget(self.win_event_log, 0, 0)

        self.macos_unified_log = QCheckBox("macOS Unified Logs")
        logs_layout.addWidget(self.macos_unified_log, 0, 1)

        self.linux_journal = QCheckBox("Linux Journalctl")
        logs_layout.addWidget(self.linux_journal, 1, 0)

        self.smart_mon = QCheckBox("SMART Monitoring")
        logs_layout.addWidget(self.smart_mon, 1, 1)

        self.service_mon = QCheckBox("Service Monitoring")
        logs_layout.addWidget(self.service_mon, 2, 0)

        self.update_check = QCheckBox("Update Checking")
        logs_layout.addWidget(self.update_check, 2, 1)

        layout.addStretch()

    def _setup_automation_tab(self):
        """Setup automation settings tab."""
        layout = QVBoxLayout(self.automation_tab)
        layout.setSpacing(16)

        # General
        gen_group = self._create_section(layout, "General")
        gen_layout = QGridLayout(gen_group)

        self.auto_enabled = QCheckBox("Enable automation")
        gen_layout.addWidget(self.auto_enabled, 0, 0, 1, 2)

        self.auto_restart = QCheckBox("Auto-restart failed services")
        gen_layout.addWidget(self.auto_restart, 1, 0, 1, 2)

        self.auto_cleanup = QCheckBox("Auto-cleanup temp files")
        gen_layout.addWidget(self.auto_cleanup, 2, 0, 1, 2)

        self.auto_update = QCheckBox("Auto-update system")
        gen_layout.addWidget(self.auto_update, 3, 0, 1, 2)

        self.update_check_interval = QSpinBox()
        self.update_check_interval.setRange(1, 168)
        self.update_check_interval.setSuffix(" hours")
        self._add_field(gen_layout, 4, "Update Check Interval", self.update_check_interval)

        # Maintenance window
        maint_group = self._create_section(layout, "Maintenance Window")
        maint_layout = QGridLayout(maint_group)

        self.maint_start = QTimeEdit()
        self.maint_start.setTime(QTime(2, 0))
        self._add_field(maint_layout, 0, "Start Time", self.maint_start)

        self.maint_end = QTimeEdit()
        self.maint_end.setTime(QTime(4, 0))
        self._add_field(maint_layout, 1, "End Time", self.maint_end)

        self.max_fix_attempts = QSpinBox()
        self.max_fix_attempts.setRange(1, 10)
        self._add_field(maint_layout, 2, "Max Auto-fix Attempts", self.max_fix_attempts)

        self.notify_on_fix = QCheckBox("Notify on auto-fix")
        maint_layout.addWidget(self.notify_on_fix, 3, 0, 1, 2)

        layout.addStretch()

    def _setup_security_tab(self):
        """Setup security settings tab."""
        layout = QVBoxLayout(self.security_tab)
        layout.setSpacing(16)

        # General
        gen_group = self._create_section(layout, "General")
        gen_layout = QGridLayout(gen_group)

        self.local_first = QCheckBox("Local-first data processing")
        gen_layout.addWidget(self.local_first, 0, 0, 1, 2)

        self.encrypt_local = QCheckBox("Encrypt local data")
        gen_layout.addWidget(self.encrypt_local, 1, 0, 1, 2)

        self.require_auth = QCheckBox("Require authentication for GUI")
        gen_layout.addWidget(self.require_auth, 2, 0, 1, 2)

        self.api_key_rotation = QSpinBox()
        self.api_key_rotation.setRange(1, 365)
        self.api_key_rotation.setSuffix(" days")
        self._add_field(gen_layout, 3, "API Key Rotation", self.api_key_rotation)

        # Privacy
        privacy_group = self._create_section(layout, "Privacy & Telemetry")
        privacy_layout = QGridLayout(privacy_group)

        self.audit_log = QCheckBox("Enable audit logging")
        privacy_layout.addWidget(self.audit_log, 0, 0, 1, 2)

        self.telemetry = QCheckBox("Enable anonymous telemetry")
        privacy_layout.addWidget(self.telemetry, 1, 0, 1, 2)

        layout.addStretch()

    def _setup_gui_tab(self):
        """Setup GUI settings tab."""
        layout = QVBoxLayout(self.gui_tab)
        layout.setSpacing(16)

        # Appearance
        app_group = self._create_section(layout, "Appearance")
        app_layout = QGridLayout(app_group)

        self.theme = QComboBox()
        self.theme.addItems(["System", "Light", "Dark"])
        self._add_field(app_layout, 0, "Theme", self.theme)

        self.language = QComboBox()
        self.language.addItems(["English", "Spanish", "French", "German", "Chinese", "Japanese"])
        self._add_field(app_layout, 1, "Language", self.language)

        # Behavior
        beh_group = self._create_section(layout, "Behavior")
        beh_layout = QGridLayout(beh_group)

        self.dashboard_refresh = QSpinBox()
        self.dashboard_refresh.setRange(1, 300)
        self.dashboard_refresh.setSuffix(" seconds")
        self._add_field(beh_layout, 0, "Dashboard Refresh", self.dashboard_refresh)

        self.notifications = QCheckBox("Enable notifications")
        beh_layout.addWidget(self.notifications, 1, 0, 1, 2)

        layout.addStretch()

    def _load_settings(self):
        """Load settings from config."""
        cfg = self.bot.config

        # General
        self.app_name.setText(cfg.app_name)
        self.log_level.setCurrentText(cfg.log_level)
        self.data_dir.setText(cfg.data_dir)
        self.auto_start.setChecked(cfg.gui.auto_start)
        self.start_minimized.setChecked(cfg.gui.start_minimized)
        self.show_tray.setChecked(cfg.gui.show_tray_icon)

        # Monitoring
        mon = cfg.monitoring
        self.mon_enabled.setChecked(mon.enabled)
        self.mon_interval.setValue(mon.interval_seconds)
        self.cpu_threshold.setValue(mon.cpu_threshold_percent)
        self.mem_threshold.setValue(mon.memory_threshold_percent)
        self.disk_threshold.setValue(mon.disk_threshold_percent)
        self.net_mon.setChecked(mon.network_monitor_enabled)
        self.gpu_mon.setChecked(mon.gpu_monitor_enabled)
        self.proc_mon.setChecked(mon.process_monitor_enabled)
        self.log_mon.setChecked(mon.log_monitor_enabled)
        self.smart_mon.setChecked(mon.smart_disk_check_enabled)

        # Learning
        learn = cfg.learning
        self.learn_enabled.setChecked(learn.enabled)
        self.model_update_interval.setValue(learn.model_update_interval_hours)
        self.detection_window.setValue(learn.habit_detection_window_days)
        self.min_confidence.setValue(learn.min_pattern_confidence)
        self.auto_schedule.setChecked(learn.auto_schedule_enabled)
        self.prediction_horizon.setValue(learn.prediction_horizon_days)
        self.privacy_mode.setCurrentText(learn.privacy_mode.replace("_", " ").title())

        # Data
        data = cfg.data_mgmt
        self.data_enabled.setChecked(data.enabled)
        self.auto_organize.setChecked(data.auto_organize_enabled)
        self.organize_interval.setValue(data.organize_interval_hours)
        self.dup_detection.setChecked(data.duplicate_detection_enabled)
        self.temp_cleanup.setChecked(data.cleanup_temp_files_enabled)
        self.cleanup_interval.setValue(data.cleanup_interval_hours)
        self.max_temp_age.setValue(data.max_temp_file_age_days)
        self.backup_enabled.setChecked(data.backup_enabled)
        self.backup_interval.setValue(data.backup_interval_hours)
        self.backup_retention.setValue(data.backup_retention_days)

        # Populate watched directories
        for d in data.watch_directories:
            self.dirs_list.addItem(d)

        # Health
        health = cfg.health
        self.health_enabled.setChecked(health.enabled)
        self.check_interval.setValue(health.check_interval_minutes)
        self.win_event_log.setChecked(health.windows_event_log_enabled)
        self.macos_unified_log.setChecked(health.macos_unified_log_enabled)
        self.linux_journal.setChecked(health.linux_journal_enabled)
        self.smart_mon.setChecked(health.smart_monitoring_enabled)
        self.service_mon.setChecked(health.service_monitor_enabled)
        self.update_check.setChecked(health.update_check_enabled)
        self.critical_threshold.setValue(health.critical_alert_threshold)

        # Automation
        auto = cfg.automation
        self.auto_enabled.setChecked(auto.enabled)
        self.auto_restart.setChecked(auto.auto_restart_failed_services)
        self.auto_cleanup.setChecked(auto.auto_cleanup_enabled)
        self.auto_update.setChecked(auto.auto_update_enabled)
        self.update_check_interval.setValue(auto.update_check_interval_hours)
        self.maint_start.setTime(QTime.fromString(auto.maintenance_window_start, "HH:mm"))
        self.maint_end.setTime(QTime.fromString(auto.maintenance_window_end, "HH:mm"))
        self.max_fix_attempts.setValue(auto.max_auto_fix_attempts)
        self.notify_on_fix.setChecked(auto.notification_on_auto_fix)

        # Security
        sec = cfg.security
        self.local_first.setChecked(sec.local_first)
        self.encrypt_local.setChecked(sec.encrypt_local_data)
        self.require_auth.setChecked(sec.require_auth_for_gui)
        self.api_key_rotation.setValue(sec.api_key_rotation_days)
        self.audit_log.setChecked(sec.audit_log_enabled)
        self.telemetry.setChecked(sec.telemetry_enabled)

        # GUI
        gui = cfg.gui
        self.theme.setCurrentText(gui.theme.title())
        self.language.setCurrentText(gui.language.title())
        self.dashboard_refresh.setValue(gui.dashboard_refresh_seconds)
        self.notifications.setChecked(gui.notifications_enabled)

    def _save_settings(self):
        """Save settings to config."""
        cfg = self.bot.config

        # General
        cfg.app_name = self.app_name.text()
        cfg.log_level = self.log_level.currentText()
        cfg.gui.auto_start = self.auto_start.isChecked()
        cfg.gui.start_minimized = self.start_minimized.isChecked()
        cfg.gui.show_tray_icon = self.show_tray.isChecked()

        # Monitoring
        mon = cfg.monitoring
        mon.enabled = self.mon_enabled.isChecked()
        mon.interval_seconds = self.mon_interval.value()
        mon.cpu_threshold_percent = self.cpu_threshold.value()
        mon.memory_threshold_percent = self.mem_threshold.value()
        mon.disk_threshold_percent = self.disk_threshold.value()
        mon.network_monitor_enabled = self.net_mon.isChecked()
        mon.gpu_monitor_enabled = self.gpu_mon.isChecked()
        mon.process_monitor_enabled = self.proc_mon.isChecked()
        mon.log_monitor_enabled = self.log_mon.isChecked()
        mon.smart_disk_check_enabled = self.smart_mon.isChecked()

        # Learning
        learn = cfg.learning
        learn.enabled = self.learn_enabled.isChecked()
        learn.model_update_interval_hours = self.model_update_interval.value()
        learn.habit_detection_window_days = self.detection_window.value()
        learn.min_pattern_confidence = self.min_confidence.value()
        learn.auto_schedule_enabled = self.auto_schedule.isChecked()
        learn.prediction_horizon_days = self.prediction_horizon.value()
        learn.privacy_mode = self.privacy_mode.currentText().lower().replace(" ", "_")

        # Data
        data = cfg.data_mgmt
        data.enabled = self.data_enabled.isChecked()
        data.auto_organize_enabled = self.auto_organize.isChecked()
        data.organize_interval_hours = self.organize_interval.value()
        data.duplicate_detection_enabled = self.dup_detection.isChecked()
        data.cleanup_temp_files_enabled = self.temp_cleanup.isChecked()
        data.cleanup_interval_hours = self.cleanup_interval.value()
        data.max_temp_file_age_days = self.max_temp_age.value()
        data.backup_enabled = self.backup_enabled.isChecked()
        data.backup_interval_hours = self.backup_interval.value()
        data.backup_retention_days = self.backup_retention.value()

        # Watched directories
        data.watch_directories = []
        for i in range(self.dirs_list.count()):
            data.watch_directories.append(self.dirs_list.item(i).text())

        # Health
        health = cfg.health
        health.enabled = self.health_enabled.isChecked()
        health.check_interval_minutes = self.check_interval.value()
        health.windows_event_log_enabled = self.win_event_log.isChecked()
        health.macos_unified_log_enabled = self.macos_unified_log.isChecked()
        health.linux_journal_enabled = self.linux_journal.isChecked()
        health.smart_monitoring_enabled = self.smart_mon.isChecked()
        health.service_monitor_enabled = self.service_mon.isChecked()
        health.update_check_enabled = self.update_check.isChecked()
        health.critical_alert_threshold = self.critical_threshold.value()

        # Automation
        auto = cfg.automation
        auto.enabled = self.auto_enabled.isChecked()
        auto.auto_restart_failed_services = self.auto_restart.isChecked()
        auto.auto_cleanup_enabled = self.auto_cleanup.isChecked()
        auto.auto_update_enabled = self.auto_update.isChecked()
        auto.update_check_interval_hours = self.update_check_interval.value()
        auto.maintenance_window_start = self.maint_start.time().toString("HH:mm")
        auto.maintenance_window_end = self.maint_end.time().toString("HH:mm")
        auto.max_auto_fix_attempts = self.max_fix_attempts.value()
        auto.notification_on_auto_fix = self.notify_on_fix.isChecked()

        # Security
        sec = cfg.security
        sec.local_first = self.local_first.isChecked()
        sec.encrypt_local_data = self.encrypt_local.isChecked()
        sec.require_auth_for_gui = self.require_auth.isChecked()
        sec.api_key_rotation_days = self.api_key_rotation.value()
        sec.audit_log_enabled = self.audit_log.isChecked()
        sec.telemetry_enabled = self.telemetry.isChecked()

        # GUI
        gui = cfg.gui
        gui.theme = self.theme.currentText().lower()
        gui.language = self.language.currentText().lower()
        gui.dashboard_refresh_seconds = self.dashboard_refresh.value()
        gui.notifications_enabled = self.notifications.isChecked()

        # Save
        if self.bot.config_manager.save():
            QMessageBox.information(self, "Success", "Settings saved successfully")
            self.logger.info("Settings saved")
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings")

    def _reset_defaults(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self, "Confirm Reset",
            "Reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Create new default config
            from aio_bot.config.manager import AppConfig
            self.bot.config = AppConfig()
            self.bot.config.data_dir = self.bot.config_manager.config.data_dir
            self._load_settings()

    def _add_watch_dir(self):
        """Add a watched directory."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            self.dirs_list.addItem(dir_path)

    def _remove_watch_dir(self):
        """Remove selected watched directory."""
        current = self.dirs_list.currentRow()
        if current >= 0:
            self.dirs_list.takeItem(current)


# Need to import QTime, QListWidget
from PySide6.QtWidgets import QListWidget
