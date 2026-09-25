"""
Automation Widget for AIO Bot GUI.
"""

import logging
from datetime import datetime

from PySide6.QtCore import QTime
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from aio_bot.automation.scheduler import ScheduleType
from aio_bot.automation.task_runner import TaskStatus
from aio_bot.core.bot import AIOBot


class AutomationWidget(QWidget):
    """Automation and scheduling widget."""

    def __init__(self, bot: AIOBot):
        super().__init__()
        self.bot = bot
        self.logger = logging.getLogger("AIOBot.GUI.AutomationWidget")
        self._setup_ui()

    def _setup_ui(self):
        """Setup the automation widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Scheduled Tasks tab
        self.tasks_tab = QWidget()
        self._setup_tasks_tab()
        self.tabs.addTab(self.tasks_tab, "Scheduled Tasks")

        # Maintenance Windows tab
        self.maint_tab = QWidget()
        self._setup_maint_tab()
        self.tabs.addTab(self.maint_tab, "Maintenance Windows")

        # Task History tab
        self.history_tab = QWidget()
        self._setup_history_tab()
        self.tabs.addTab(self.history_tab, "Task History")

        # Running Tasks tab
        self.running_tab = QWidget()
        self._setup_running_tab()
        self.tabs.addTab(self.running_tab, "Running Tasks")

    def _setup_tasks_tab(self):
        """Setup scheduled tasks tab."""
        layout = QVBoxLayout(self.tasks_tab)

        # Toolbar
        toolbar_layout = QHBoxLayout()

        add_task_btn = QPushButton("Add Task")
        add_task_btn.clicked.connect(self._add_task)
        toolbar_layout.addWidget(add_task_btn)

        edit_task_btn = QPushButton("Edit Task")
        edit_task_btn.clicked.connect(self._edit_task)
        toolbar_layout.addWidget(edit_task_btn)

        delete_task_btn = QPushButton("Delete Task")
        delete_task_btn.clicked.connect(self._delete_task)
        toolbar_layout.addWidget(delete_task_btn)

        toolbar_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        toolbar_layout.addWidget(refresh_btn)

        layout.addLayout(toolbar_layout)

        # Tasks table
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(8)
        self.tasks_table.setHorizontalHeaderLabels([
            "Name", "Type", "Schedule", "Next Run", "Priority", "Enabled", "Runs", "Last Result"
        ])
        self.tasks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tasks_table.setAlternatingRowColors(True)
        self.tasks_table.setSortingEnabled(True)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tasks_table)

        # Task details
        details_group = QGroupBox("Task Details")
        details_layout = QVBoxLayout(details_group)

        self.task_details = QLabel("Select a task to view details")
        self.task_details.setWordWrap(True)
        details_layout.addWidget(self.task_details)

        layout.addWidget(details_group)

        self.tasks_table.itemSelectionChanged.connect(self._on_task_selected)

    def _setup_maint_tab(self):
        """Setup maintenance windows tab."""
        layout = QVBoxLayout(self.maint_tab)

        # Toolbar
        toolbar_layout = QHBoxLayout()

        add_window_btn = QPushButton("Add Window")
        add_window_btn.clicked.connect(self._add_maintenance_window)
        toolbar_layout.addWidget(add_window_btn)

        edit_window_btn = QPushButton("Edit Window")
        edit_window_btn.clicked.connect(self._edit_maintenance_window)
        toolbar_layout.addWidget(edit_window_btn)

        delete_window_btn = QPushButton("Delete Window")
        delete_window_btn.clicked.connect(self._delete_maintenance_window)
        toolbar_layout.addWidget(delete_window_btn)

        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        # Windows table
        self.windows_table = QTableWidget()
        self.windows_table.setColumnCount(6)
        self.windows_table.setHorizontalHeaderLabels([
            "Name", "Start", "End", "Days", "Enabled", "Tasks"
        ])
        self.windows_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.windows_table.setAlternatingRowColors(True)
        layout.addWidget(self.windows_table)

        # Default maintenance window config
        config_group = QGroupBox("Default Maintenance Window (from settings)")
        config_layout = QGridLayout(config_group)

        config_layout.addWidget(QLabel("Start Time:"), 0, 0)
        self.default_start = QTimeEdit()
        self.default_start.setTime(QTime(2, 0))
        config_layout.addWidget(self.default_start, 0, 1)

        config_layout.addWidget(QLabel("End Time:"), 0, 2)
        self.default_end = QTimeEdit()
        self.default_end.setTime(QTime(4, 0))
        config_layout.addWidget(self.default_end, 0, 3)

        config_layout.addWidget(QLabel("Days:"), 1, 0)
        self.default_days = []
        days_layout = QHBoxLayout()
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(day_names):
            cb = QCheckBox(day)
            cb.setChecked(True)
            self.default_days.append(cb)
            days_layout.addWidget(cb)
        config_layout.addLayout(days_layout, 1, 1, 1, 3)

        apply_btn = QPushButton("Apply to Settings")
        apply_btn.clicked.connect(self._apply_maintenance_config)
        config_layout.addWidget(apply_btn, 2, 0, 1, 4)

        layout.addWidget(config_group)

        layout.addStretch()

    def _setup_history_tab(self):
        """Setup task history tab."""
        layout = QVBoxLayout(self.history_tab)

        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Status:"))

        self.history_status_filter = QComboBox()
        self.history_status_filter.addItems(["All", "Completed", "Failed", "Cancelled"])
        self.history_status_filter.currentTextChanged.connect(self._filter_history)
        filter_layout.addWidget(self.history_status_filter)

        filter_layout.addWidget(QLabel("Type:"))
        self.history_type_filter = QComboBox()
        self.history_type_filter.addItems(["All"])
        filter_layout.addWidget(self.history_type_filter)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Task", "Type", "Status", "Started", "Completed", "Duration", "Error"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSortingEnabled(True)
        layout.addWidget(self.history_table)

    def _setup_running_tab(self):
        """Setup running tasks tab."""
        layout = QVBoxLayout(self.running_tab)

        # Running tasks table
        self.running_table = QTableWidget()
        self.running_table.setColumnCount(6)
        self.running_table.setHorizontalHeaderLabels([
            "Task ID", "Type", "Priority", "Started", "Progress", "Actions"
        ])
        self.running_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.running_table.setAlternatingRowColors(True)
        layout.addWidget(self.running_table)

        # Actions
        actions_layout = QHBoxLayout()

        cancel_btn = QPushButton("Cancel Selected")
        cancel_btn.clicked.connect(self._cancel_task)
        cancel_btn.setStyleSheet("background-color: #d13438; color: white;")
        actions_layout.addWidget(cancel_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Stats
        stats_group = QGroupBox("Task Runner Statistics")
        stats_layout = QGridLayout(stats_group)

        self.stats_labels = {}
        stats_fields = [
            ("Total Queued", "total_queued"),
            ("Total Completed", "total_completed"),
            ("Total Failed", "total_failed"),
            ("Total Retries", "total_retries"),
            ("Queue Size", "queue_size"),
            ("Running Tasks", "running_tasks"),
        ]

        for i, (label, key) in enumerate(stats_fields):
            lbl = QLabel(label + ":")
            lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
            val = QLabel("0")
            stats_layout.addWidget(lbl, i // 3, (i % 3) * 2)
            stats_layout.addWidget(val, i // 3, (i % 3) * 2 + 1)
            self.stats_labels[key] = val

        layout.addWidget(stats_group)

        layout.addStretch()

    def refresh(self):
        """Refresh the widget."""
        self.update_data()

    def update_data(self):
        """Update with latest automation data."""
        try:
            if not self.bot.scheduler or not self.bot.task_runner:
                return

            # Update tasks
            self._update_tasks()

            # Maintenance windows
            self._update_maintenance_windows()

            # History
            self._update_history()

            # Running tasks
            self._update_running()

            # Stats
            self._update_stats()

        except Exception as e:
            self.logger.error("Automation widget update error: %s", e)

    def _update_tasks(self):
        """Update scheduled tasks table."""
        tasks = self.bot.scheduler.get_tasks(enabled_only=False)

        # Update type filter
        current_type = self.history_type_filter.currentText()
        types = set(t.task_type for t in tasks)
        self.history_type_filter.blockSignals(True)
        self.history_type_filter.clear()
        self.history_type_filter.addItems(["All"] + sorted(types))
        if current_type in types:
            self.history_type_filter.setCurrentText(current_type)
        self.history_type_filter.blockSignals(False)

        self.tasks_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            self.tasks_table.setItem(row, 0, QTableWidgetItem(task.name))
            self.tasks_table.setItem(row, 1, QTableWidgetItem(task.task_type))

            # Schedule description
            if task.schedule_type == ScheduleType.CRON:
                schedule = f"Cron: {task.cron_expression}"
            elif task.schedule_type == ScheduleType.INTERVAL:
                schedule = f"Every {task.interval_seconds // 60} min"
            elif task.schedule_type == ScheduleType.ONCE:
                schedule = f"Once: {task.run_at.strftime('%Y-%m-%d %H:%M') if task.run_at else 'N/A'}"
            elif task.schedule_type == ScheduleType.PREDICTED:
                schedule = "Predicted"
            elif task.schedule_type == ScheduleType.MAINTENANCE_WINDOW:
                schedule = "Maintenance Window"
            else:
                schedule = task.schedule_type.value
            self.tasks_table.setItem(row, 2, QTableWidgetItem(schedule))

            next_run = task.next_run.strftime("%Y-%m-%d %H:%M") if task.next_run else "Never"
            self.tasks_table.setItem(row, 3, QTableWidgetItem(next_run))

            priority_names = {0: "Low", 1: "Normal", 2: "High", 3: "Critical"}
            self.tasks_table.setItem(row, 4, QTableWidgetItem(priority_names.get(task.priority, "Normal")))

            enabled_item = QTableWidgetItem("Yes" if task.enabled else "No")
            if not task.enabled:
                enabled_item.setForeground(QColor("#888888"))
            self.tasks_table.setItem(row, 5, enabled_item)

            self.tasks_table.setItem(row, 6, QTableWidgetItem(f"{task.run_count}/{task.max_runs if task.max_runs else '∞'}"))

            last_result = task.last_result.get("status", "N/A")
            result_item = QTableWidgetItem(last_result)
            if last_result == "error":
                result_item.setForeground(QColor("#d13438"))
            elif last_result == "queued":
                result_item.setForeground(QColor("#0078d4"))
            self.tasks_table.setItem(row, 7, result_item)

    def _update_maintenance_windows(self):
        """Update maintenance windows table."""
        windows = self.bot.scheduler.get_maintenance_windows()

        self.windows_table.setRowCount(len(windows))
        for row, window in enumerate(windows):
            self.windows_table.setItem(row, 0, QTableWidgetItem(window.name))
            self.windows_table.setItem(row, 1, QTableWidgetItem(window.start_time.strftime("%H:%M")))
            self.windows_table.setItem(row, 2, QTableWidgetItem(window.end_time.strftime("%H:%M")))

            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            days_str = ", ".join(day_names[d] for d in window.days)
            self.windows_table.setItem(row, 3, QTableWidgetItem(days_str))

            enabled_item = QTableWidgetItem("Yes" if window.enabled else "No")
            if not window.enabled:
                enabled_item.setForeground(QColor("#888888"))
            self.windows_table.setItem(row, 4, enabled_item)

            self.windows_table.setItem(row, 5, QTableWidgetItem(", ".join(window.tasks)))

    def _update_history(self):
        """Update task history table."""
        if not self.bot.task_runner:
            return

        # Combine completed and failed
        all_tasks = list(self.bot.task_runner._completed_tasks) + list(self.bot.task_runner._failed_tasks)

        # Apply filter
        status_filter = self.history_status_filter.currentText()
        if status_filter != "All":
            if status_filter == "Completed":
                all_tasks = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
            elif status_filter == "Failed":
                all_tasks = [t for t in all_tasks if t.status == TaskStatus.FAILED]
            elif status_filter == "Cancelled":
                all_tasks = [t for t in all_tasks if t.status == TaskStatus.CANCELLED]

        # Sort by start time (newest first)
        all_tasks.sort(key=lambda t: t.started_at or datetime.min, reverse=True)

        self.history_table.setRowCount(len(all_tasks))
        for row, task in enumerate(all_tasks):
            self.history_table.setItem(row, 0, QTableWidgetItem(task.id))
            self.history_table.setItem(row, 1, QTableWidgetItem(task.type))

            status_item = QTableWidgetItem(task.status.value)
            if task.status == TaskStatus.COMPLETED:
                status_item.setForeground(QColor("#107c10"))
            elif task.status == TaskStatus.FAILED:
                status_item.setForeground(QColor("#d13438"))
            elif task.status == TaskStatus.CANCELLED:
                status_item.setForeground(QColor("#ff8c00"))
            self.history_table.setItem(row, 2, status_item)

            started = task.started_at.strftime("%Y-%m-%d %H:%M:%S") if task.started_at else "N/A"
            self.history_table.setItem(row, 3, QTableWidgetItem(started))

            completed = task.completed_at.strftime("%Y-%m-%d %H:%M:%S") if task.completed_at else "N/A"
            self.history_table.setItem(row, 4, QTableWidgetItem(completed))

            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds()
                self.history_table.setItem(row, 5, QTableWidgetItem(f"{duration:.1f}s"))
            else:
                self.history_table.setItem(row, 5, QTableWidgetItem("N/A"))

            error = task.error[:100] if task.error else ""
            self.history_table.setItem(row, 6, QTableWidgetItem(error))

    def _update_running(self):
        """Update running tasks table."""
        if not self.bot.task_runner:
            return

        running = list(self.bot.task_runner._running_tasks.values())

        self.running_table.setRowCount(len(running))
        for row, task in enumerate(running):
            self.running_table.setItem(row, 0, QTableWidgetItem(task.id))
            self.running_table.setItem(row, 1, QTableWidgetItem(task.type))

            priority_names = {0: "Low", 1: "Normal", 2: "High", 3: "Critical"}
            self.running_table.setItem(row, 2, QTableWidgetItem(priority_names.get(task.priority.value, "Normal")))

            started = task.started_at.strftime("%Y-%m-%d %H:%M:%S") if task.started_at else "N/A"
            self.running_table.setItem(row, 3, QTableWidgetItem(started))

            # Progress (unknown for now)
            self.running_table.setItem(row, 4, QTableWidgetItem("Running..."))

            # Cancel button
            from PySide6.QtWidgets import QPushButton
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setProperty("task_id", task.id)
            cancel_btn.clicked.connect(lambda checked, tid=task.id: self._cancel_task_by_id(tid))
            self.running_table.setCellWidget(row, 5, cancel_btn)

    def _update_stats(self):
        """Update statistics."""
        if not self.bot.task_runner:
            return

        stats = self.bot.task_runner.get_stats()
        self.stats_labels["total_queued"].setText(str(stats.get("total_queued", 0)))
        self.stats_labels["total_completed"].setText(str(stats.get("total_completed", 0)))
        self.stats_labels["total_failed"].setText(str(stats.get("total_failed", 0)))
        self.stats_labels["total_retries"].setText(str(stats.get("total_retries", 0)))
        self.stats_labels["queue_size"].setText(str(stats.get("queue_size", 0)))
        self.stats_labels["running_tasks"].setText(str(stats.get("running_tasks", 0)))

    def _filter_history(self):
        """Filter history."""
        self._update_history()

    def _on_task_selected(self):
        """Show task details."""
        selected = self.tasks_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        task_id = self.tasks_table.item(row, 0).text()

        task = self.bot.scheduler._tasks.get(task_id)
        if task:
            details = (
                f"<b>Name:</b> {task.name}<br>"
                f"<b>ID:</b> {task.id}<br>"
                f"<b>Type:</b> {task.task_type}<br>"
                f"<b>Schedule:</b> {task.schedule_type.value}<br>"
                f"<b>Priority:</b> {task.priority}<br>"
                f"<b>Enabled:</b> {'Yes' if task.enabled else 'No'}<br>"
                f"<b>Max Runs:</b> {task.max_runs if task.max_runs else 'Unlimited'}<br>"
                f"<b>Run Count:</b> {task.run_count}<br>"
                f"<b>Next Run:</b> {task.next_run.strftime('%Y-%m-%d %H:%M') if task.next_run else 'Never'}<br>"
                f"<b>Last Run:</b> {task.last_run.strftime('%Y-%m-%d %H:%M') if task.last_run else 'Never'}<br>"
                f"<b>Last Result:</b> {task.last_result.get('status', 'N/A')}<br>"
                f"<b>Payload:</b> {task.payload}"
            )
            self.task_details.setText(details)

    def _add_task(self):
        """Add new scheduled task."""
        # Would open a dialog
        self.logger.info("Add task requested")

    def _edit_task(self):
        """Edit selected task."""
        selected = self.tasks_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        task_id = self.tasks_table.item(row, 0).text()
        self.logger.info("Edit task requested: %s", task_id)

    def _delete_task(self):
        """Delete selected task."""
        selected = self.tasks_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        task_id = self.tasks_table.item(row, 0).text()

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete task '{task_id}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.bot.scheduler.remove_task(task_id)
            self.update_data()

    def _add_maintenance_window(self):
        """Add maintenance window."""
        self.logger.info("Add maintenance window requested")

    def _edit_maintenance_window(self):
        """Edit maintenance window."""
        self.logger.info("Edit maintenance window requested")

    def _delete_maintenance_window(self):
        """Delete maintenance window."""
        self.logger.info("Delete maintenance window requested")

    def _apply_maintenance_config(self):
        """Apply maintenance window config to settings."""
        days = [i for i, cb in enumerate(self.default_days) if cb.isChecked()]
        self.bot.config.automation.maintenance_window_start = self.default_start.time().toString("HH:mm")
        self.bot.config.automation.maintenance_window_end = self.default_end.time().toString("HH:mm")
        self.bot.config_manager.save()

        # Update scheduler
        if self.bot.scheduler._maintenance_windows:
            self.bot.scheduler._maintenance_windows[0].start_time = self.default_start.time().toPython()
            self.bot.scheduler._maintenance_windows[0].end_time = self.default_end.time().toPython()
            self.bot.scheduler._maintenance_windows[0].days = days

        QMessageBox.information(self, "Success", "Maintenance window configuration updated")

    def _cancel_task(self):
        """Cancel selected running task."""
        # Get selected from running table
        pass

    def _cancel_task_by_id(self, task_id: str):
        """Cancel task by ID."""
        if self.bot.task_runner:
            task = self.bot.task_runner.get_task_status(task_id)
            if task and task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.CANCELLED
                self.logger.info("Cancelled task: %s", task_id)
                self.update_data()
