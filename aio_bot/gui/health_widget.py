"""
Health Widget for AIO Bot GUI.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from aio_bot.core.bot import AIOBot
from aio_bot.health.health_monitor import EventType, HealthStatus, SystemHealthReport


class HealthWidget(QWidget):
    """System health monitoring widget."""

    def __init__(self, bot: AIOBot):
        super().__init__()
        self.bot = bot
        self.logger = logging.getLogger("AIOBot.GUI.HealthWidget")
        self._setup_ui()

    def _setup_ui(self):
        """Setup the health widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Overview tab
        self.overview_tab = QWidget()
        self._setup_overview_tab()
        self.tabs.addTab(self.overview_tab, "Overview")

        # Services tab
        self.services_tab = QWidget()
        self._setup_services_tab()
        self.tabs.addTab(self.services_tab, "Services")

        # Disk Health tab
        self.disk_health_tab = QWidget()
        self._setup_disk_health_tab()
        self.tabs.addTab(self.disk_health_tab, "Disk Health")

        # Events tab
        self.events_tab = QWidget()
        self._setup_events_tab()
        self.tabs.addTab(self.events_tab, "Events")

        # Updates tab
        self.updates_tab = QWidget()
        self._setup_updates_tab()
        self.tabs.addTab(self.updates_tab, "Updates")

    def _setup_overview_tab(self):
        """Setup overview tab."""
        layout = QVBoxLayout(self.overview_tab)
        layout.setSpacing(16)

        # Overall health status
        status_group = QGroupBox("Overall System Health")
        status_layout = QHBoxLayout(status_group)

        self.health_status_label = QLabel("UNKNOWN")
        self.health_status_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        self.health_status_label.setAlignment(Qt.AlignCenter)
        self.health_status_label.setMinimumHeight(80)
        status_layout.addWidget(self.health_status_label)

        # Performance score
        self.perf_score_bar = QProgressBar()
        self.perf_score_bar.setRange(0, 100)
        self.perf_score_bar.setValue(100)
        self.perf_score_bar.setFormat("Performance Score: %p%")
        self.perf_score_bar.setFixedWidth(300)
        status_layout.addWidget(self.perf_score_bar)

        layout.addWidget(status_group)

        # Key metrics grid
        metrics_group = QGroupBox("Key Metrics")
        metrics_layout = QGridLayout(metrics_group)

        self.metric_labels = {}
        metrics = [
            ("Services Running", "services_running", "--"),
            ("Services Total", "services_total", "--"),
            ("Critical Services Down", "critical_down", "--"),
            ("Disks Healthy", "disks_healthy", "--"),
            ("Disks Warning", "disks_warning", "--"),
            ("Disks Critical", "disks_critical", "--"),
            ("Pending Updates", "updates_pending", "--"),
            ("Security Issues", "security_issues", "--"),
        ]

        for i, (label, key, default) in enumerate(metrics):
            lbl = QLabel(label + ":")
            lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
            val = QLabel(default)
            val.setFont(QFont("Segoe UI", 9))
            metrics_layout.addWidget(lbl, i // 4, (i % 4) * 2)
            metrics_layout.addWidget(val, i // 4, (i % 4) * 2 + 1)
            self.metric_labels[key] = val

        layout.addWidget(metrics_group)

        # Recent critical events
        events_group = QGroupBox("Recent Critical Events")
        events_layout = QVBoxLayout(events_group)

        self.events_table = QTableWidget()
        self.events_table.setColumnCount(4)
        self.events_table.setHorizontalHeaderLabels(["Time", "Type", "Component", "Message"])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.events_table.setAlternatingRowColors(True)
        self.events_table.setMaximumHeight(200)
        events_layout.addWidget(self.events_table)

        layout.addWidget(events_group)

        layout.addStretch()

    def _setup_services_tab(self):
        """Setup services tab."""
        layout = QVBoxLayout(self.services_tab)

        self.services_table = QTableWidget()
        self.services_table.setColumnCount(6)
        self.services_table.setHorizontalHeaderLabels([
            "Service", "Display Name", "Status", "Startup", "Critical", "PID"
        ])
        self.services_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.services_table.setAlternatingRowColors(True)
        self.services_table.setSortingEnabled(True)
        layout.addWidget(self.services_table)

    def _setup_disk_health_tab(self):
        """Setup disk health tab."""
        layout = QVBoxLayout(self.disk_health_tab)

        self.disk_health_table = QTableWidget()
        self.disk_health_table.setColumnCount(9)
        self.disk_health_table.setHorizontalHeaderLabels([
            "Device", "Model", "Health", "Temp (°C)", "Power On (hrs)",
            "Reallocated", "Pending", "Uncorrectable", "Last Check"
        ])
        self.disk_health_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.disk_health_table.setAlternatingRowColors(True)
        layout.addWidget(self.disk_health_table)

    def _setup_events_tab(self):
        """Setup events tab."""
        layout = QVBoxLayout(self.events_tab)

        # Filter controls
        filter_layout = QHBoxLayout()

        from PySide6.QtWidgets import QComboBox, QPushButton

        filter_layout.addWidget(QLabel("Severity:"))
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All", "Critical", "Warning", "Info"])
        self.severity_filter.currentTextChanged.connect(self._filter_events)
        filter_layout.addWidget(self.severity_filter)

        filter_layout.addWidget(QLabel("Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All"] + [e.value for e in EventType])
        self.type_filter.currentTextChanged.connect(self._filter_events)
        filter_layout.addWidget(self.type_filter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(refresh_btn)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Events table
        self.all_events_table = QTableWidget()
        self.all_events_table.setColumnCount(6)
        self.all_events_table.setHorizontalHeaderLabels([
            "Time", "Type", "Severity", "Component", "Message", "Resolved"
        ])
        self.all_events_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.all_events_table.setAlternatingRowColors(True)
        self.all_events_table.setSortingEnabled(True)
        layout.addWidget(self.all_events_table)

    def _setup_updates_tab(self):
        """Setup updates tab."""
        layout = QVBoxLayout(self.updates_tab)

        # Update status
        status_group = QGroupBox("Update Status")
        status_layout = QGridLayout(status_group)

        self.update_labels = {}
        update_fields = [
            ("Pending Updates", "pending"),
            ("Last Check", "last_check"),
            ("Security Updates", "security"),
            ("Feature Updates", "feature"),
        ]

        for i, (label, key) in enumerate(update_fields):
            lbl = QLabel(label + ":")
            lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
            val = QLabel("--")
            status_layout.addWidget(lbl, i // 2, (i % 2) * 2)
            status_layout.addWidget(val, i // 2, (i % 2) * 2 + 1)
            self.update_labels[key] = val

        layout.addWidget(status_group)

        # Available updates
        updates_group = QGroupBox("Available Updates")
        updates_layout = QVBoxLayout(updates_group)

        self.updates_table = QTableWidget()
        self.updates_table.setColumnCount(4)
        self.updates_table.setHorizontalHeaderLabels(["Name", "Version", "Type", "Size"])
        self.updates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.updates_table.setAlternatingRowColors(True)
        updates_layout.addWidget(self.updates_table)

        layout.addWidget(updates_group)

        # Actions
        from PySide6.QtWidgets import QPushButton

        actions_layout = QHBoxLayout()
        check_btn = QPushButton("Check for Updates")
        check_btn.clicked.connect(self._check_updates)
        install_btn = QPushButton("Install Updates")
        install_btn.clicked.connect(self._install_updates)
        actions_layout.addWidget(check_btn)
        actions_layout.addWidget(install_btn)
        actions_layout.addStretch()

        layout.addLayout(actions_layout)

        layout.addStretch()

    def refresh(self):
        """Refresh the widget."""
        self.update_data()

    def update_data(self):
        """Update with latest health data."""
        try:
            if not self.bot.health_monitor:
                return

            report = self.bot.health_monitor.get_health_report()

            # Update overview
            self._update_overview(report)

            # Update services
            self._update_services(report)

            # Update disk health
            self._update_disk_health(report)

            # Update events
            self._update_events(report)

            # Update updates
            self._update_updates()

        except Exception as e:
            self.logger.error("Health widget update error: %s", e)

    def _update_overview(self, report: SystemHealthReport):
        """Update overview tab."""
        # Overall status
        status_colors = {
            HealthStatus.HEALTHY: "#107c10",
            HealthStatus.WARNING: "#ff8c00",
            HealthStatus.CRITICAL: "#d13438",
            HealthStatus.UNKNOWN: "#888888",
        }

        color = status_colors.get(report.overall_status, "#888888")
        self.health_status_label.setText(report.overall_status.value.upper())
        self.health_status_label.setStyleSheet(f"color: {color};")

        # Performance score
        self.perf_score_bar.setValue(int(report.performance_score))

        # Metrics
        critical_down = sum(1 for s in report.services if s.critical and s.status != "running")
        disks_healthy = sum(1 for d in report.disks if d.health_status == HealthStatus.HEALTHY)
        disks_warning = sum(1 for d in report.disks if d.health_status == HealthStatus.WARNING)
        disks_critical = sum(1 for d in report.disks if d.health_status == HealthStatus.CRITICAL)

        self.metric_labels["services_running"].setText(str(sum(1 for s in report.services if s.status == "running")))
        self.metric_labels["services_total"].setText(str(len(report.services)))
        self.metric_labels["critical_down"].setText(str(critical_down))
        self.metric_labels["disks_healthy"].setText(str(disks_healthy))
        self.metric_labels["disks_warning"].setText(str(disks_warning))
        self.metric_labels["disks_critical"].setText(str(disks_critical))
        self.metric_labels["updates_pending"].setText(str(report.updates_pending))
        self.metric_labels["security_issues"].setText(str(report.security_issues))

        # Critical events table
        critical_events = [e for e in report.events if e.severity == HealthStatus.CRITICAL]
        self.events_table.setRowCount(min(len(critical_events), 10))
        for row, event in enumerate(critical_events[:10]):
            self.events_table.setItem(row, 0, QTableWidgetItem(event.timestamp.strftime("%H:%M:%S")))
            self.events_table.setItem(row, 1, QTableWidgetItem(event.event_type.value))
            self.events_table.setItem(row, 2, QTableWidgetItem(event.component))
            self.events_table.setItem(row, 3, QTableWidgetItem(event.message[:100]))

            # Color critical rows
            for col in range(4):
                item = self.events_table.item(row, col)
                if item:
                    item.setForeground(QColor("#d13438"))

    def _update_services(self, report: SystemHealthReport):
        """Update services tab."""
        self.services_table.setRowCount(len(report.services))
        for row, svc in enumerate(report.services):
            self.services_table.setItem(row, 0, QTableWidgetItem(svc.name))
            self.services_table.setItem(row, 1, QTableWidgetItem(svc.display_name))

            status_item = QTableWidgetItem(svc.status)
            if svc.status == "running":
                status_item.setForeground(QColor("#107c10"))
            elif svc.status in ["stopped", "failed"]:
                status_item.setForeground(QColor("#d13438"))
            self.services_table.setItem(row, 2, status_item)

            self.services_table.setItem(row, 3, QTableWidgetItem(svc.startup_type))

            critical_item = QTableWidgetItem("Yes" if svc.critical else "No")
            if svc.critical:
                critical_item.setForeground(QColor("#d13438"))
            self.services_table.setItem(row, 4, critical_item)

            self.services_table.setItem(row, 5, QTableWidgetItem(str(svc.pid) if svc.pid else "N/A"))

    def _update_disk_health(self, report: SystemHealthReport):
        """Update disk health tab."""
        self.disk_health_table.setRowCount(len(report.disks))
        for row, disk in enumerate(report.disks):
            self.disk_health_table.setItem(row, 0, QTableWidgetItem(disk.device))
            self.disk_health_table.setItem(row, 1, QTableWidgetItem(disk.model))

            health_item = QTableWidgetItem(disk.health_status.value)
            health_colors = {
                HealthStatus.HEALTHY: "#107c10",
                HealthStatus.WARNING: "#ff8c00",
                HealthStatus.CRITICAL: "#d13438",
                HealthStatus.UNKNOWN: "#888888",
            }
            health_item.setForeground(QColor(health_colors.get(disk.health_status, "#888888")))
            self.disk_health_table.setItem(row, 2, health_item)

            self.disk_health_table.setItem(row, 3, QTableWidgetItem(str(disk.temperature) if disk.temperature else "N/A"))
            self.disk_health_table.setItem(row, 4, QTableWidgetItem(str(disk.power_on_hours) if disk.power_on_hours else "N/A"))
            self.disk_health_table.setItem(row, 5, QTableWidgetItem(str(disk.reallocated_sectors)))
            self.disk_health_table.setItem(row, 6, QTableWidgetItem(str(disk.pending_sectors)))
            self.disk_health_table.setItem(row, 7, QTableWidgetItem(str(disk.uncorrectable_sectors)))
            self.disk_health_table.setItem(row, 8, QTableWidgetItem(disk.last_check.strftime("%H:%M:%S")))

    def _update_events(self, report: SystemHealthReport):
        """Update events tab."""
        # Apply filters
        severity_filter = self.severity_filter.currentText()
        type_filter = self.type_filter.currentText()

        events = report.events
        if severity_filter != "All":
            events = [e for e in events if e.severity.value == severity_filter.lower()]
        if type_filter != "All":
            events = [e for e in events if e.event_type.value == type_filter]

        self.all_events_table.setRowCount(len(events))
        for row, event in enumerate(events):
            self.all_events_table.setItem(row, 0, QTableWidgetItem(event.timestamp.strftime("%Y-%m-%d %H:%M:%S")))
            self.all_events_table.setItem(row, 1, QTableWidgetItem(event.event_type.value))

            sev_item = QTableWidgetItem(event.severity.value)
            sev_colors = {
                HealthStatus.CRITICAL: "#d13438",
                HealthStatus.WARNING: "#ff8c00",
                HealthStatus.INFO: "#0078d4",
            }
            sev_item.setForeground(QColor(sev_colors.get(event.severity, "#888888")))
            self.all_events_table.setItem(row, 2, sev_item)

            self.all_events_table.setItem(row, 3, QTableWidgetItem(event.component))
            self.all_events_table.setItem(row, 4, QTableWidgetItem(event.message[:200]))
            self.all_events_table.setItem(row, 5, QTableWidgetItem("Yes" if event.resolved else "No"))

    def _update_updates(self):
        """Update updates tab."""
        if not self.bot.health_monitor:
            return

        update_status = self.bot.health_monitor.get_update_status()
        self.update_labels["pending"].setText(str(update_status.get("pending", 0)))
        self.update_labels["last_check"].setText(update_status.get("last_check", "Never"))

    def _filter_events(self):
        """Filter events table."""
        self.update_data()

    def _check_updates(self):
        """Check for updates."""
        if self.bot.health_monitor:
            asyncio.create_task(self.bot.health_monitor._check_updates())
        self.logger.info("Update check requested")

    def _install_updates(self):
        """Install updates."""
        self.logger.info("Install updates requested")
        # Would trigger update installation
