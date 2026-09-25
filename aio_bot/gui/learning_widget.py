"""
Learning Widget for AIO Bot GUI.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from aio_bot.core.bot import AIOBot
from aio_bot.learning.habit_engine import PatternType


class LearningWidget(QWidget):
    """Habit learning and prediction widget."""

    def __init__(self, bot: AIOBot):
        super().__init__()
        self.bot = bot
        self.logger = logging.getLogger("AIOBot.GUI.LearningWidget")
        self._setup_ui()

    def _setup_ui(self):
        """Setup the learning widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Patterns tab
        self.patterns_tab = QWidget()
        self._setup_patterns_tab()
        self.tabs.addTab(self.patterns_tab, "Detected Patterns")

        # Predictions tab
        self.predictions_tab = QWidget()
        self._setup_predictions_tab()
        self.tabs.addTab(self.predictions_tab, "Predictions")

        # Insights tab
        self.insights_tab = QWidget()
        self._setup_insights_tab()
        self.tabs.addTab(self.insights_tab, "Insights")

        # Model status tab
        self.model_tab = QWidget()
        self._setup_model_tab()
        self.tabs.addTab(self.model_tab, "Model Status")

    def _setup_patterns_tab(self):
        """Setup patterns tab."""
        layout = QVBoxLayout(self.patterns_tab)

        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Type:"))

        from PySide6.QtWidgets import QComboBox

        self.pattern_type_filter = QComboBox()
        self.pattern_type_filter.addItems(["All"] + [p.value for p in PatternType])
        self.pattern_type_filter.currentTextChanged.connect(self._filter_patterns)
        filter_layout.addWidget(self.pattern_type_filter)

        filter_layout.addWidget(QLabel("Min Confidence:"))
        self.confidence_filter = QComboBox()
        self.confidence_filter.addItems(["0%", "25%", "50%", "75%", "90%"])
        self.confidence_filter.setCurrentText("50%")
        self.confidence_filter.currentTextChanged.connect(self._filter_patterns)
        filter_layout.addWidget(self.confidence_filter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(refresh_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Patterns table
        self.patterns_table = QTableWidget()
        self.patterns_table.setColumnCount(7)
        self.patterns_table.setHorizontalHeaderLabels([
            "Name", "Type", "Confidence", "Frequency", "Occurrences", "Last Seen", "Description"
        ])
        self.patterns_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.patterns_table.setAlternatingRowColors(True)
        self.patterns_table.setSortingEnabled(True)
        layout.addWidget(self.patterns_table)

        # Pattern details
        details_group = QGroupBox("Pattern Details")
        details_layout = QVBoxLayout(details_group)

        self.pattern_details = QLabel("Select a pattern to view details")
        self.pattern_details.setWordWrap(True)
        details_layout.addWidget(self.pattern_details)

        layout.addWidget(details_group)

        # Connect selection
        self.patterns_table.itemSelectionChanged.connect(self._on_pattern_selected)

    def _setup_predictions_tab(self):
        """Setup predictions tab."""
        layout = QVBoxLayout(self.predictions_tab)

        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Hours Ahead:"))

        from PySide6.QtWidgets import QSpinBox

        self.hours_ahead = QSpinBox()
        self.hours_ahead.setRange(1, 168)
        self.hours_ahead.setValue(24)
        self.hours_ahead.valueChanged.connect(self._filter_predictions)
        filter_layout.addWidget(self.hours_ahead)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(refresh_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Predictions table
        self.predictions_table = QTableWidget()
        self.predictions_table.setColumnCount(6)
        self.predictions_table.setHorizontalHeaderLabels([
            "Time", "Type", "Confidence", "Pattern", "Suggested Action", "Description"
        ])
        self.predictions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.predictions_table.setAlternatingRowColors(True)
        self.predictions_table.setSortingEnabled(True)
        layout.addWidget(self.predictions_table)

    def _setup_insights_tab(self):
        """Setup insights tab."""
        layout = QVBoxLayout(self.insights_tab)

        # Summary cards
        summary_group = QGroupBox("Learning Summary")
        summary_layout = QGridLayout(summary_group)

        self.insight_cards = {}
        insights = [
            ("Total Patterns", "total_patterns", "0"),
            ("High Confidence", "high_confidence", "0"),
            ("Daily Patterns", "daily_patterns", "0"),
            ("Weekly Patterns", "weekly_patterns", "0"),
            ("Predictions (24h)", "predictions_24h", "0"),
            ("Model Accuracy", "model_accuracy", "--"),
        ]

        for i, (label, key, default) in enumerate(insights):
            card = self._create_insight_card(label, default)
            self.insight_cards[key] = card
            summary_layout.addWidget(card, i // 3, i % 3)

        layout.addWidget(summary_group)

        # Top patterns by type
        type_group = QGroupBox("Patterns by Type")
        type_layout = QVBoxLayout(type_group)

        self.type_table = QTableWidget()
        self.type_table.setColumnCount(4)
        self.type_table.setHorizontalHeaderLabels(["Type", "Count", "Avg Confidence", "Top Pattern"])
        self.type_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.type_table.setAlternatingRowColors(True)
        type_layout.addWidget(self.type_table)

        layout.addWidget(type_group)

        # Recent suggestions
        suggestions_group = QGroupBox("Recent Suggestions")
        suggestions_layout = QVBoxLayout(suggestions_group)

        self.suggestions_table = QTableWidget()
        self.suggestions_table.setColumnCount(4)
        self.suggestions_table.setHorizontalHeaderLabels(["Time", "Type", "Pattern", "Action"])
        self.suggestions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.suggestions_table.setAlternatingRowColors(True)
        self.suggestions_table.setMaximumHeight(200)
        suggestions_layout.addWidget(self.suggestions_table)

        layout.addWidget(suggestions_group)

        layout.addStretch()

    def _setup_model_tab(self):
        """Setup model status tab."""
        layout = QVBoxLayout(self.model_tab)

        # Model info
        info_group = QGroupBox("Model Information")
        info_layout = QGridLayout(info_group)

        self.model_labels = {}
        model_fields = [
            ("Model Version", "version"),
            ("Last Updated", "last_updated"),
            ("Training Events", "training_events"),
            ("Pattern Count", "pattern_count"),
            ("Prediction Accuracy", "accuracy"),
            ("Data Window (days)", "window_days"),
        ]

        for i, (label, key) in enumerate(model_fields):
            lbl = QLabel(label + ":")
            lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
            val = QLabel("--")
            info_layout.addWidget(lbl, i // 2, (i % 2) * 2)
            info_layout.addWidget(val, i // 2, (i % 2) * 2 + 1)
            self.model_labels[key] = val

        layout.addWidget(info_group)

        # Actions
        actions_group = QGroupBox("Model Actions")
        actions_layout = QHBoxLayout(actions_group)

        update_btn = QPushButton("Update Models Now")
        update_btn.clicked.connect(self._update_models)
        actions_layout.addWidget(update_btn)

        retrain_btn = QPushButton("Retrain Models")
        retrain_btn.clicked.connect(self._retrain_models)
        actions_layout.addWidget(retrain_btn)

        export_btn = QPushButton("Export Models")
        export_btn.clicked.connect(self._export_models)
        actions_layout.addWidget(export_btn)

        actions_layout.addStretch()
        layout.addWidget(actions_group)

        # Privacy settings
        privacy_group = QGroupBox("Privacy Settings")
        privacy_layout = QVBoxLayout(privacy_group)

        from PySide6.QtWidgets import QCheckBox

        self.local_only_cb = QCheckBox("Local-only processing (no cloud sync)")
        self.local_only_cb.setChecked(True)
        privacy_layout.addWidget(self.local_only_cb)

        self.anonymize_cb = QCheckBox("Anonymize data before any processing")
        privacy_layout.addWidget(self.anonymize_cb)

        layout.addWidget(privacy_group)

        layout.addStretch()

    def _create_insight_card(self, title: str, value: str) -> QFrame:
        """Create an insight card."""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card.setMinimumHeight(80)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)

        val_label = QLabel(value)
        val_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        val_label.setAlignment(Qt.AlignCenter)
        val_label.setStyleSheet("color: #0078d4;")
        layout.addWidget(val_label)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 9))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #888888;")
        layout.addWidget(title_label)

        return card

    def refresh(self):
        """Refresh the widget."""
        self.update_data()

    def update_data(self):
        """Update with latest learning data."""
        try:
            if not self.bot.habit_engine:
                return

            # Update patterns
            self._update_patterns()

            # Update predictions
            self._update_predictions()

            # Update insights
            self._update_insights()

            # Update model status
            self._update_model_status()

        except Exception as e:
            self.logger.error("Learning widget update error: %s", e)

    def _update_patterns(self):
        """Update patterns table."""
        patterns = self.bot.habit_engine.get_patterns()

        # Apply filters
        type_filter = self.pattern_type_filter.currentText()
        conf_filter = int(self.confidence_filter.currentText().rstrip('%')) / 100

        if type_filter != "All":
            patterns = [p for p in patterns if p.pattern_type.value == type_filter.lower()]

        patterns = [p for p in patterns if p.confidence >= conf_filter]

        self.patterns_table.setRowCount(len(patterns))
        for row, pattern in enumerate(patterns):
            self.patterns_table.setItem(row, 0, QTableWidgetItem(pattern.name))
            self.patterns_table.setItem(row, 1, QTableWidgetItem(pattern.pattern_type.value))

            conf_item = QTableWidgetItem(f"{pattern.confidence:.1%}")
            if pattern.confidence >= 0.9:
                conf_item.setForeground(QColor("#107c10"))
            elif pattern.confidence >= 0.7:
                conf_item.setForeground(QColor("#ff8c00"))
            else:
                conf_item.setForeground(QColor("#d13438"))
            self.patterns_table.setItem(row, 2, conf_item)

            self.patterns_table.setItem(row, 3, QTableWidgetItem(pattern.frequency))
            self.patterns_table.setItem(row, 4, QTableWidgetItem(str(pattern.occurrence_count)))
            self.patterns_table.setItem(row, 5, QTableWidgetItem(pattern.last_seen.strftime("%Y-%m-%d %H:%M")))
            self.patterns_table.setItem(row, 6, QTableWidgetItem(pattern.description))

    def _update_predictions(self):
        """Update predictions table."""
        hours = self.hours_ahead.value()
        predictions = self.bot.habit_engine.get_predictions(hours)

        self.predictions_table.setRowCount(len(predictions))
        for row, pred in enumerate(predictions):
            self.predictions_table.setItem(row, 0, QTableWidgetItem(pred.predicted_time.strftime("%Y-%m-%d %H:%M")))
            self.predictions_table.setItem(row, 1, QTableWidgetItem(pred.prediction_type))

            conf_item = QTableWidgetItem(f"{pred.confidence:.1%}")
            if pred.confidence >= 0.8:
                conf_item.setForeground(QColor("#107c10"))
            elif pred.confidence >= 0.6:
                conf_item.setForeground(QColor("#ff8c00"))
            else:
                conf_item.setForeground(QColor("#d13438"))
            self.predictions_table.setItem(row, 2, conf_item)

            self.predictions_table.setItem(row, 3, QTableWidgetItem(pred.metadata.get("pattern_name", "Unknown")))
            self.predictions_table.setItem(row, 4, QTableWidgetItem(pred.suggested_action or "None"))
            self.predictions_table.setItem(row, 5, QTableWidgetItem(pred.description))

    def _update_insights(self):
        """Update insights."""
        patterns = self.bot.habit_engine.get_patterns()
        predictions = self.bot.habit_engine.get_predictions(24)
        suggestions = self.bot.habit_engine.get_pending_suggestions()

        # Count by type
        type_counts = {}
        type_conf = {}
        for p in patterns:
            t = p.pattern_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
            type_conf[t] = type_conf.get(t, []) + [p.confidence]

        self.insight_cards["total_patterns"].findChild(QLabel).setText(str(len(patterns)))
        self.insight_cards["high_confidence"].findChild(QLabel).setText(str(sum(1 for p in patterns if p.confidence >= 0.8)))
        self.insight_cards["daily_patterns"].findChild(QLabel).setText(str(sum(1 for p in patterns if p.frequency == "daily")))
        self.insight_cards["weekly_patterns"].findChild(QLabel).setText(str(sum(1 for p in patterns if p.frequency == "weekly")))
        self.insight_cards["predictions_24h"].findChild(QLabel).setText(str(len(predictions)))

        # Type table
        self.type_table.setRowCount(len(type_counts))
        for row, (ptype, count) in enumerate(sorted(type_counts.items(), key=lambda x: -x[1])):
            avg_conf = sum(type_conf[ptype]) / len(type_conf[ptype]) if type_conf[ptype] else 0
            self.type_table.setItem(row, 0, QTableWidgetItem(ptype))
            self.type_table.setItem(row, 1, QTableWidgetItem(str(count)))
            self.type_table.setItem(row, 2, QTableWidgetItem(f"{avg_conf:.1%}"))

            # Top pattern for this type
            top = max([p for p in patterns if p.pattern_type.value == ptype], key=lambda x: x.confidence, default=None)
            self.type_table.setItem(row, 3, QTableWidgetItem(top.name if top else "None"))

        # Suggestions
        self.suggestions_table.setRowCount(len(suggestions))
        for row, sugg in enumerate(suggestions):
            self.suggestions_table.setItem(row, 0, QTableWidgetItem(sugg["timestamp"].strftime("%Y-%m-%d %H:%M")))
            self.suggestions_table.setItem(row, 1, QTableWidgetItem(sugg["type"]))
            if "pattern" in sugg:
                self.suggestions_table.setItem(row, 2, QTableWidgetItem(sugg["pattern"].name))
            self.suggestions_table.setItem(row, 3, QTableWidgetItem("Review suggested"))

    def _update_model_status(self):
        """Update model status."""
        config = self.bot.habit_engine.config
        self.model_labels["version"].setText("1.0.0")
        self.model_labels["window_days"].setText(str(config.habit_detection_window_days))

        patterns = self.bot.habit_engine.get_patterns()
        self.model_labels["pattern_count"].setText(str(len(patterns)))
        self.model_labels["training_events"].setText(str(len(self.bot.habit_engine._events)))

    def _filter_patterns(self):
        """Filter patterns."""
        self._update_patterns()

    def _filter_predictions(self):
        """Filter predictions."""
        self._update_predictions()

    def _on_pattern_selected(self):
        """Show pattern details."""
        selected = self.patterns_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        name = self.patterns_table.item(row, 0).text()

        # Find pattern
        patterns = self.bot.habit_engine.get_patterns()
        pattern = next((p for p in patterns if p.name == name), None)

        if pattern:
            details = (
                f"<b>Name:</b> {pattern.name}<br>"
                f"<b>Type:</b> {pattern.pattern_type.value}<br>"
                f"<b>Confidence:</b> {pattern.confidence:.1%}<br>"
                f"<b>Frequency:</b> {pattern.frequency}<br>"
                f"<b>Occurrences:</b> {pattern.occurrence_count}<br>"
                f"<b>First Seen:</b> {pattern.first_seen.strftime('%Y-%m-%d %H:%M')}<br>"
                f"<b>Last Seen:</b> {pattern.last_seen.strftime('%Y-%m-%d %H:%M')}<br>"
                f"<b>Triggers:</b> {', '.join(pattern.triggers) if pattern.triggers else 'None'}<br>"
                f"<b>Actions:</b> {', '.join(pattern.actions) if pattern.actions else 'None'}<br>"
                f"<b>Description:</b> {pattern.description}"
            )
            self.pattern_details.setText(details)

    def _update_models(self):
        """Update models."""
        if self.bot.habit_engine:
            asyncio.create_task(self.bot.habit_engine.update_models())
        self.logger.info("Model update requested")

    def _retrain_models(self):
        """Retrain models."""
        self.logger.info("Model retrain requested")

    def _export_models(self):
        """Export models."""
        self.logger.info("Model export requested")
