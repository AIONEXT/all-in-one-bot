"""
Files Widget for AIO Bot GUI.
"""

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
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
    QVBoxLayout,
    QWidget,
)

from aio_bot.core.bot import AIOBot
from aio_bot.data_mgmt.file_organizer import FileCategory


class FilesWidget(QWidget):
    """File organization and management widget."""

    def __init__(self, bot: AIOBot):
        super().__init__()
        self.bot = bot
        self.logger = logging.getLogger("AIOBot.GUI.FilesWidget")
        self._setup_ui()

    def _setup_ui(self):
        """Setup the files widget UI."""
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

        # Duplicates tab
        self.duplicates_tab = QWidget()
        self._setup_duplicates_tab()
        self.tabs.addTab(self.duplicates_tab, "Duplicates")

        # Cleanup tab
        self.cleanup_tab = QWidget()
        self._setup_cleanup_tab()
        self.tabs.addTab(self.cleanup_tab, "Cleanup Plans")

        # Organization tab
        self.org_tab = QWidget()
        self._setup_org_tab()
        self.tabs.addTab(self.org_tab, "Organization")

        # Backup tab
        self.backup_tab = QWidget()
        self._setup_backup_tab()
        self.tabs.addTab(self.backup_tab, "Backups")

    def _setup_overview_tab(self):
        """Setup overview tab."""
        layout = QVBoxLayout(self.overview_tab)
        layout.setSpacing(16)

        # Watched directories
        dirs_group = QGroupBox("Watched Directories")
        dirs_layout = QVBoxLayout(dirs_group)

        self.dirs_table = QTableWidget()
        self.dirs_table.setColumnCount(3)
        self.dirs_table.setHorizontalHeaderLabels(["Directory", "Status", "Files"])
        self.dirs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dirs_table.setAlternatingRowColors(True)
        dirs_layout.addWidget(self.dirs_table)

        # Add directory button
        add_dir_layout = QHBoxLayout()
        add_dir_btn = QPushButton("Add Directory")
        add_dir_btn.clicked.connect(self._add_watch_directory)
        add_dir_layout.addWidget(add_dir_btn)
        add_dir_layout.addStretch()
        dirs_layout.addLayout(add_dir_layout)

        layout.addWidget(dirs_group)

        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QGridLayout(stats_group)

        self.stats_labels = {}
        stats_fields = [
            ("Total Files Scanned", "total_files"),
            ("Duplicate Groups", "duplicate_groups"),
            ("Duplicate Files", "duplicate_files"),
            ("Space Wasted", "space_wasted"),
            ("Cleanup Plans", "cleanup_plans"),
            ("Est. Cleanup Space", "est_cleanup"),
            ("Last Organize", "last_organize"),
            ("Last Cleanup", "last_cleanup"),
            ("Last Backup", "last_backup"),
        ]

        for i, (label, key) in enumerate(stats_fields):
            lbl = QLabel(label + ":")
            lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
            val = QLabel("--")
            stats_layout.addWidget(lbl, i // 3, (i % 3) * 2)
            stats_layout.addWidget(val, i // 3, (i % 3) * 2 + 1)
            self.stats_labels[key] = val

        layout.addWidget(stats_group)

        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout(actions_group)

        scan_btn = QPushButton("Scan Now")
        scan_btn.clicked.connect(self._scan_now)
        actions_layout.addWidget(scan_btn)

        organize_btn = QPushButton("Organize Files")
        organize_btn.clicked.connect(self._organize_now)
        actions_layout.addWidget(organize_btn)

        cleanup_btn = QPushButton("Run Cleanup")
        cleanup_btn.clicked.connect(self._cleanup_now)
        actions_layout.addWidget(cleanup_btn)

        backup_btn = QPushButton("Backup Now")
        backup_btn.clicked.connect(self._backup_now)
        actions_layout.addWidget(backup_btn)

        actions_layout.addStretch()
        layout.addWidget(actions_group)

        layout.addStretch()

    def _setup_duplicates_tab(self):
        """Setup duplicates tab."""
        layout = QVBoxLayout(self.duplicates_tab)

        # Controls
        controls_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        controls_layout.addWidget(refresh_btn)

        auto_select_btn = QPushButton("Auto-Select Duplicates")
        auto_select_btn.clicked.connect(self._auto_select_duplicates)
        controls_layout.addWidget(auto_select_btn)

        delete_selected_btn = QPushButton("Delete Selected")
        delete_selected_btn.clicked.connect(self._delete_selected_duplicates)
        delete_selected_btn.setStyleSheet("background-color: #d13438; color: white;")
        controls_layout.addWidget(delete_selected_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Duplicates table
        self.duplicates_table = QTableWidget()
        self.duplicates_table.setColumnCount(6)
        self.duplicates_table.setHorizontalHeaderLabels([
            "Keep", "File", "Size", "Path", "Duplicate Of", "Hash"
        ])
        self.duplicates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.duplicates_table.setAlternatingRowColors(True)
        self.duplicates_table.setSortingEnabled(True)
        layout.addWidget(self.duplicates_table)

    def _setup_cleanup_tab(self):
        """Setup cleanup plans tab."""
        layout = QVBoxLayout(self.cleanup_tab)

        # Cleanup plans table
        self.cleanup_table = QTableWidget()
        self.cleanup_table.setColumnCount(5)
        self.cleanup_table.setHorizontalHeaderLabels([
            "Action", "Reason", "Files", "Est. Space", "Status"
        ])
        self.cleanup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cleanup_table.setAlternatingRowColors(True)
        layout.addWidget(self.cleanup_table)

        # Actions
        actions_layout = QHBoxLayout()

        execute_btn = QPushButton("Execute Selected")
        execute_btn.clicked.connect(self._execute_cleanup)
        actions_layout.addWidget(execute_btn)

        execute_all_btn = QPushButton("Execute All")
        execute_all_btn.clicked.connect(self._execute_all_cleanup)
        actions_layout.addWidget(execute_all_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

    def _setup_org_tab(self):
        """Setup organization rules tab."""
        layout = QVBoxLayout(self.org_tab)

        # Rules table
        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(5)
        self.rules_table.setHorizontalHeaderLabels([
            "Category", "Extensions", "Target Folder", "Min Size", "Min Age (days)"
        ])
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rules_table.setAlternatingRowColors(True)
        layout.addWidget(self.rules_table)

        # Add rule
        add_group = QGroupBox("Add Custom Rule")
        add_layout = QGridLayout(add_group)

        add_layout.addWidget(QLabel("Category:"), 0, 0)
        self.rule_category = QComboBox()
        self.rule_category.addItems([c.value for c in FileCategory])
        add_layout.addWidget(self.rule_category, 0, 1)

        add_layout.addWidget(QLabel("Extensions (comma-separated):"), 0, 2)
        self.rule_extensions = QComboBox()
        self.rule_extensions.setEditable(True)
        add_layout.addWidget(self.rule_extensions, 0, 3)

        add_layout.addWidget(QLabel("Target Folder:"), 1, 0)
        self.rule_target = QComboBox()
        self.rule_target.setEditable(True)
        add_layout.addWidget(self.rule_target, 1, 1)

        add_layout.addWidget(QLabel("Min Size (MB):"), 1, 2)
        self.rule_min_size = QComboBox()
        self.rule_min_size.setEditable(True)
        add_layout.addWidget(self.rule_min_size, 1, 3)

        add_layout.addWidget(QLabel("Min Age (days):"), 2, 0)
        self.rule_min_age = QComboBox()
        self.rule_min_age.setEditable(True)
        add_layout.addWidget(self.rule_min_age, 2, 1)

        add_rule_btn = QPushButton("Add Rule")
        add_rule_btn.clicked.connect(self._add_org_rule)
        add_layout.addWidget(add_rule_btn, 2, 2)

        layout.addWidget(add_group)

        layout.addStretch()

    def _setup_backup_tab(self):
        """Setup backup tab."""
        layout = QVBoxLayout(self.backup_tab)

        # Backup history
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(5)
        self.backup_table.setHorizontalHeaderLabels([
            "Name", "Date", "Directories", "Size", "Status"
        ])
        self.backup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.backup_table.setAlternatingRowColors(True)
        layout.addWidget(self.backup_table)

        # Actions
        actions_layout = QHBoxLayout()

        backup_now_btn = QPushButton("Backup Now")
        backup_now_btn.clicked.connect(self._backup_now)
        actions_layout.addWidget(backup_now_btn)

        restore_btn = QPushButton("Restore Selected")
        restore_btn.clicked.connect(self._restore_backup)
        actions_layout.addWidget(restore_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self._delete_backup)
        delete_btn.setStyleSheet("background-color: #d13438; color: white;")
        actions_layout.addWidget(delete_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        layout.addStretch()

    def refresh(self):
        """Refresh the widget."""
        self.update_data()

    def update_data(self):
        """Update with latest file management data."""
        try:
            if not self.bot.file_organizer:
                return

            # Update overview
            self._update_overview()

            # Update duplicates
            self._update_duplicates()

            # Update cleanup plans
            self._update_cleanup()

            # Update organization rules
            self._update_rules()

            # Update backups
            self._update_backups()

        except Exception as e:
            self.logger.error("Files widget update error: %s", e)

    def _update_overview(self):
        """Update overview tab."""
        stats = self.bot.file_organizer.get_organization_stats()

        self.stats_labels["total_files"].setText(str(stats.get("total_files_scanned", 0)))
        self.stats_labels["duplicate_groups"].setText(str(stats.get("duplicate_groups", 0)))
        self.stats_labels["duplicate_files"].setText(str(stats.get("duplicate_files", 0)))
        self.stats_labels["space_wasted"].setText(f"{stats.get('space_wasted_mb', 0):.1f} MB")
        self.stats_labels["cleanup_plans"].setText(str(stats.get("cleanup_plans", 0)))
        self.stats_labels["est_cleanup"].setText(f"{stats.get('estimated_cleanup_space_mb', 0):.1f} MB")
        self.stats_labels["last_organize"].setText(stats.get("last_organize", "Never") or "Never")
        self.stats_labels["last_cleanup"].setText(stats.get("last_cleanup", "Never") or "Never")
        self.stats_labels["last_backup"].setText(stats.get("last_backup", "Never") or "Never")

        # Watched directories
        dirs = stats.get("watched_directories", [])
        self.dirs_table.setRowCount(len(dirs))
        for row, d in enumerate(dirs):
            self.dirs_table.setItem(row, 0, QTableWidgetItem(d))
            self.dirs_table.setItem(row, 1, QTableWidgetItem("Active"))
            self.dirs_table.setItem(row, 2, QTableWidgetItem("--"))  # Would need file count

    def _update_duplicates(self):
        """Update duplicates tab."""
        groups = self.bot.file_organizer.get_duplicate_groups()

        # Flatten duplicates
        all_dupes = []
        for group in groups:
            for f in group.files:
                if f.is_duplicate:
                    all_dupes.append({
                        "file": f,
                        "group": group
                    })

        self.duplicates_table.setRowCount(len(all_dupes))
        for row, dupe in enumerate(all_dupes):
            f = dupe["file"]
            g = dupe["group"]

            # Checkbox for keep
            from PySide6.QtWidgets import QTableWidgetItem
            keep_item = QTableWidgetItem()
            keep_item.setCheckState(Qt.Unchecked)
            self.duplicates_table.setItem(row, 0, keep_item)

            self.duplicates_table.setItem(row, 1, QTableWidgetItem(f.name))
            self.duplicates_table.setItem(row, 2, QTableWidgetItem(self._format_size(f.size)))
            self.duplicates_table.setItem(row, 3, QTableWidgetItem(str(f.path)))
            self.duplicates_table.setItem(row, 4, QTableWidgetItem(str(f.duplicate_of) if f.duplicate_of else "Original"))
            self.duplicates_table.setItem(row, 5, QTableWidgetItem(g.hash[:16] + "..."))

    def _update_cleanup(self):
        """Update cleanup plans tab."""
        plans = self.bot.file_organizer.get_cleanup_plans()

        self.cleanup_table.setRowCount(len(plans))
        for row, plan in enumerate(plans):
            self.cleanup_table.setItem(row, 0, QTableWidgetItem(plan.action.value))
            self.cleanup_table.setItem(row, 1, QTableWidgetItem(plan.reason))
            self.cleanup_table.setItem(row, 2, QTableWidgetItem(str(len(plan.files))))
            self.cleanup_table.setItem(row, 3, QTableWidgetItem(self._format_size(plan.estimated_space_saved)))
            self.cleanup_table.setItem(row, 4, QTableWidgetItem("Pending"))

    def _update_rules(self):
        """Update organization rules tab."""
        rules = self.bot.file_organizer._rules

        self.rules_table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            self.rules_table.setItem(row, 0, QTableWidgetItem(rule.category.value))
            self.rules_table.setItem(row, 1, QTableWidgetItem(", ".join(rule.extensions)))
            self.rules_table.setItem(row, 2, QTableWidgetItem(rule.target_subdir))
            self.rules_table.setItem(row, 3, QTableWidgetItem(self._format_size(rule.min_size)))
            self.rules_table.setItem(row, 4, QTableWidgetItem(str(rule.min_age_days)))

    def _update_backups(self):
        """Update backup tab."""
        # Would scan backup directory
        backup_dir = Path(self.bot.config.data_dir) / 'backups' if hasattr(self.bot.config, 'data_dir') else Path.home() / '.aiobot' / 'backups'

        backups = []
        if backup_dir.exists():
            for backup in sorted(backup_dir.iterdir(), reverse=True):
                if backup.is_dir():
                    manifest = backup / 'manifest.json'
                    if manifest.exists():
                        try:
                            import json
                            with open(manifest) as f:
                                m = json.load(f)
                            backups.append({
                                "name": backup.name,
                                "date": m.get("created", "Unknown"),
                                "dirs": len(m.get("directories", [])),
                                "size": self._get_dir_size(backup),
                            })
                        except Exception:
                            pass

        self.backup_table.setRowCount(len(backups))
        for row, b in enumerate(backups):
            self.backup_table.setItem(row, 0, QTableWidgetItem(b["name"]))
            self.backup_table.setItem(row, 1, QTableWidgetItem(b["date"]))
            self.backup_table.setItem(row, 2, QTableWidgetItem(str(b["dirs"])))
            self.backup_table.setItem(row, 3, QTableWidgetItem(self._format_size(b["size"])))
            self.backup_table.setItem(row, 4, QTableWidgetItem("Complete"))

    def _format_size(self, size: int) -> str:
        """Format bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def _get_dir_size(self, path: Path) -> int:
        """Get directory size."""
        total = 0
        try:
            for f in path.rglob('*'):
                if f.is_file():
                    total += f.stat().st_size
        except Exception:
            pass
        return total

    def _add_watch_directory(self):
        """Add a watch directory."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory to Watch")
        if dir_path:
            if self.bot.file_organizer.add_watch_directory(dir_path):
                QMessageBox.information(self, "Success", f"Added {dir_path} to watched directories")
                self.update_data()
            else:
                QMessageBox.warning(self, "Error", "Failed to add directory")

    def _scan_now(self):
        """Trigger scan."""
        if self.bot.file_organizer:
            asyncio.create_task(self.bot.file_organizer.scan_and_organize())
        self.logger.info("Manual scan requested")

    def _organize_now(self):
        """Trigger organization."""
        self.logger.info("Manual organize requested")

    def _cleanup_now(self):
        """Trigger cleanup."""
        if self.bot.file_organizer:
            asyncio.create_task(self.bot.file_organizer.cleanup_temp_files())
        self.logger.info("Manual cleanup requested")

    def _backup_now(self):
        """Trigger backup."""
        if self.bot.file_organizer:
            asyncio.create_task(self.bot.file_organizer.run_backup())
        self.logger.info("Manual backup requested")

    def _auto_select_duplicates(self):
        """Auto-select duplicate files for deletion (keep originals)."""
        for row in range(self.duplicates_table.rowCount()):
            item = self.duplicates_table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def _delete_selected_duplicates(self):
        """Delete selected duplicates."""
        selected = []
        for row in range(self.duplicates_table.rowCount()):
            item = self.duplicates_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                path_str = self.duplicates_table.item(row, 3).text()
                selected.append(path_str)

        if selected:
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete {len(selected)} duplicate files?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                for path_str in selected:
                    try:
                        Path(path_str).unlink()
                    except Exception as e:
                        self.logger.error("Failed to delete %s: %s", path_str, e)
                self.update_data()

    def _execute_cleanup(self):
        """Execute selected cleanup plan."""
        self.logger.info("Execute cleanup requested")

    def _execute_all_cleanup(self):
        """Execute all cleanup plans."""
        self.logger.info("Execute all cleanup requested")

    def _add_org_rule(self):
        """Add organization rule."""
        self.logger.info("Add organization rule requested")

    def _restore_backup(self):
        """Restore from backup."""
        self.logger.info("Restore backup requested")

    def _delete_backup(self):
        """Delete backup."""
        self.logger.info("Delete backup requested")
