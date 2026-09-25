"""
Dashboard Widget for AIO Bot GUI.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from aio_bot.core.bot import AIOBot


class MetricCard(QFrame):
    """A card displaying a single metric."""

    def __init__(self, title: str, value: str = "--", unit: str = "",
                 color: str = "#0078d4", warning_threshold: float = None,
                 critical_threshold: float = None):
        super().__init__()
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self._color = color

        self.setFrameStyle(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(100)
        self.setMaximumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 10))
        self.title_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.title_label)

        # Value
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_label)

        # Unit
        if unit:
            self.unit_label = QLabel(unit)
            self.unit_label.setFont(QFont("Segoe UI", 9))
            self.unit_label.setStyleSheet("color: #888888;")
            layout.addWidget(self.unit_label)

        # Progress bar (optional)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 3px;
                background-color: #3c3c3c;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

    def update_value(self, value: str, progress: float = None):
        """Update the displayed value."""
        self.value_label.setText(str(value))

        if progress is not None:
            self.progress_bar.setValue(int(progress))
            self.progress_bar.show()

            # Update color based on thresholds
            if self.critical_threshold and progress >= self.critical_threshold:
                color = "#d13438"
            elif self.warning_threshold and progress >= self.warning_threshold:
                color = "#ff8c00"
            else:
                color = self._color

            self.value_label.setStyleSheet(f"color: {color};")
            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: none;
                    border-radius: 3px;
                    background-color: #3c3c3c;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 3px;
                }}
            """)


class DashboardWidget(QWidget):
    """Main dashboard widget."""

    def __init__(self, bot: AIOBot):
        super().__init__()
        self.bot = bot
        self.logger = logging.getLogger("AIOBot.GUI.DashboardWidget")

        self._metric_cards = {}
        self._setup_ui()

    def _setup_ui(self):
        """Setup the dashboard UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Scroll area for metrics
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        self.grid_layout = QGridLayout(content)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignTop)

        # Create metric cards
        self._create_metric_cards()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Quick actions section
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout(actions_group)

        from PySide6.QtWidgets import QPushButton, QStyle

        actions = [
            ("Run Maintenance", self._run_maintenance, QStyle.StandardPixmap.SP_ComputerIcon),
            ("Check Updates", self._check_updates, QStyle.StandardPixmap.SP_BrowserReload),
            ("Clean Temp Files", self._clean_temp, QStyle.StandardPixmap.SP_TrashIcon),
            ("Backup Now", self._backup_now, QStyle.StandardPixmap.SP_DriveHDIcon),
        ]

        for text, handler, icon_enum in actions:
            btn = QPushButton(text)
            btn.setIcon(self.style().standardIcon(icon_enum))
            btn.clicked.connect(handler)
            actions_layout.addWidget(btn)

        layout.addWidget(actions_group)

        # Status summary
        self.status_group = QGroupBox("System Status")
        status_layout = QVBoxLayout(self.status_group)

        self.status_label = QLabel("Initializing...")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)

        layout.addWidget(self.status_group)

    def _create_metric_cards(self):
        """Create metric display cards."""
        metrics = [
            ("CPU Usage", "--", "%", "#0078d4", 80, 95),
            ("Memory Usage", "--", "%", "#107c10", 85, 95),
            ("Disk Usage", "--", "%", "#5c2d91", 90, 98),
            ("GPU Usage", "--", "%", "#d83b01", 85, 95),
            ("Temperature", "--", "°C", "#ff8c00", 70, 85),
            ("Network I/O", "--", "MB/s", "#0078d4", None, None),
            ("Processes", "--", "", "#5c2d91", None, None),
            ("Uptime", "--", "", "#107c10", None, None),
        ]

        row = 0
        col = 0
        for i, (title, value, unit, color, warn, crit) in enumerate(metrics):
            card = MetricCard(title, value, unit, color, warn, crit)
            self._metric_cards[title.lower().replace(" ", "_")] = card
            self.grid_layout.addWidget(card, row, col)

            col += 1
            if col >= 4:
                col = 0
                row += 1

    def refresh(self):
        """Refresh dashboard data."""
        self.update_data()

    def update_data(self):
        """Update dashboard with latest data."""
        try:
            # Get bot status
            status = self.bot.get_status()

            # Get system metrics
            metrics = None
            if self.bot.system_monitor:
                metrics = self.bot.system_monitor.get_latest_metrics()

            # Update metric cards
            if metrics:
                self._metric_cards["cpu_usage"].update_value(f"{metrics.cpu_percent:.1f}", metrics.cpu_percent)
                self._metric_cards["memory_usage"].update_value(f"{metrics.memory_percent:.1f}", metrics.memory_percent)

                # Disk - use primary disk
                if metrics.disk_usage:
                    primary_disk = list(metrics.disk_usage.values())[0]
                    self._metric_cards["disk_usage"].update_value(f"{primary_disk['percent']:.1f}", primary_disk['percent'])

                # GPU
                if metrics.gpu_metrics:
                    gpu = metrics.gpu_metrics[0]
                    self._metric_cards["gpu_usage"].update_value(f"{gpu['load']:.1f}", gpu['load'])
                    self._metric_cards["temperature"].update_value(f"{gpu['temperature']:.0f}", gpu['temperature'])
                else:
                    self._metric_cards["gpu_usage"].update_value("N/A")
                    self._metric_cards["temperature"].update_value("N/A")

                # Network I/O (simplified)
                total_sent = sum(n.get("bytes_sent", 0) for n in metrics.network_io.values())
                total_recv = sum(n.get("bytes_recv", 0) for n in metrics.network_io.values())
                total_mb = (total_sent + total_recv) / (1024 * 1024)
                self._metric_cards["network_io"].update_value(f"{total_mb:.1f}")

                self._metric_cards["processes"].update_value(str(metrics.process_count))

                # Uptime
                hours = int(metrics.uptime_seconds // 3600)
                minutes = int((metrics.uptime_seconds % 3600) // 60)
                self._metric_cards["uptime"].update_value(f"{hours}h {minutes}m")

            # Update status summary
            state_text = status.state.value.capitalize()
            started = "Never"
            if status.started_at:
                started = status.started_at.strftime("%Y-%m-%d %H:%M")

            self.status_label.setText(
                f"<b>State:</b> {state_text}<br>"
                f"<b>Started:</b> {started}<br>"
                f"<b>Active Tasks:</b> {status.active_tasks}<br>"
                f"<b>Completed Tasks:</b> {status.completed_tasks}<br>"
                f"<b>Errors:</b> {status.errors_count} | <b>Warnings:</b> {status.warnings_count}"
            )

        except Exception as e:
            self.logger.error("Dashboard update error: %s", e)

    def _run_maintenance(self):
        """Trigger maintenance."""
        self.logger.info("Maintenance requested from dashboard")

    def _check_updates(self):
        """Check for updates."""
        self.logger.info("Update check requested from dashboard")

    def _clean_temp(self):
        """Clean temp files."""
        self.logger.info("Temp cleanup requested from dashboard")

    def _backup_now(self):
        """Run backup now."""
        self.logger.info("Backup requested from dashboard")
