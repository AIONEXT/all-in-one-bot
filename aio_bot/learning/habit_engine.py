"""
AI-Driven Habit Learning Engine - Pattern recognition, habit detection, and predictive scheduling.
"""

import asyncio
import hashlib
import json
import logging
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class PatternType(Enum):
    """Types of patterns the engine can detect."""
    TEMPORAL = "temporal"           # Time-based patterns (daily, weekly)
    APPLICATION_USAGE = "app_usage" # Application usage patterns
    SYSTEM_RESOURCE = "system_resource"  # Resource usage patterns
    FILE_ACCESS = "file_access"     # File access patterns
    NETWORK_ACTIVITY = "network"    # Network activity patterns
    USER_ACTIVITY = "user_activity" # General user activity patterns


@dataclass
class HabitPattern:
    """Detected habit pattern."""
    id: str
    pattern_type: PatternType
    name: str
    description: str
    confidence: float
    frequency: str  # daily, weekly, monthly, irregular
    time_windows: list[dict[str, Any]] = field(default_factory=list)  # {"start": "09:00", "end": "17:00", "days": [0,1,2,3,4]}
    triggers: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    occurrence_count: int = 0


@dataclass
class Prediction:
    """Predicted future event/action."""
    id: str
    pattern_id: str
    predicted_time: datetime
    prediction_type: str
    description: str
    confidence: float
    suggested_action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningEvent:
    """Event fed into the learning engine."""
    timestamp: datetime
    event_type: str
    source: str
    data: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)


class HabitEngine:
    """
    AI-driven habit detection and prediction engine.
    Learns user patterns from system events and makes predictions.
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("AIOBot.HabitEngine")
        self._running = False
        self._engine_task: asyncio.Task | None = None

        # Data storage
        self._events: deque = deque(maxlen=10000)
        self._patterns: dict[str, HabitPattern] = {}
        self._predictions: list[Prediction] = []
        self._pending_suggestions: list[dict[str, Any]] = []

        # Model state
        self._temporal_models: dict[str, Any] = {}
        self._sequence_models: dict[str, Any] = {}

        # Persistence
        self._model_path = Path(config.data_dir) / 'models' if hasattr(config, 'data_dir') else Path.home() / '.aiobot' / 'models'
        self._model_path.mkdir(parents=True, exist_ok=True)

        # Feature extractors
        self._feature_extractors = {
            PatternType.TEMPORAL: self._extract_temporal_features,
            PatternType.APPLICATION_USAGE: self._extract_app_features,
            PatternType.SYSTEM_RESOURCE: self._extract_resource_features,
            PatternType.FILE_ACCESS: self._extract_file_features,
            PatternType.NETWORK_ACTIVITY: self._extract_network_features,
            PatternType.USER_ACTIVITY: self._extract_activity_features,
        }

    async def initialize(self):
        """Initialize the habit engine."""
        self.logger.info("Initializing Habit Engine")
        await self._load_models()
        self.logger.info("Habit Engine initialized with %d patterns", len(self._patterns))

    async def run(self):
        """Main learning loop."""
        self._running = True
        self.logger.info("Habit Engine started")

        last_model_update = datetime.now()
        update_interval = timedelta(hours=self.config.model_update_interval_hours)

        while self._running:
            try:
                # Process new events
                await self._process_events()

                # Update models periodically
                if datetime.now() - last_model_update >= update_interval:
                    await self.update_models()
                    last_model_update = datetime.now()

                # Generate predictions
                await self._generate_predictions()

                await asyncio.sleep(300)  # Run every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Habit engine error: %s", e, exc_info=True)
                await asyncio.sleep(60)

        self.logger.info("Habit Engine stopped")

    async def _process_events(self):
        """Process collected events for pattern detection."""
        if len(self._events) < 10:
            return

        # Group events by type
        events_by_type = defaultdict(list)
        for event in self._events:
            events_by_type[event.event_type].append(event)

        # Detect patterns for each type
        for event_type, events in events_by_type.items():
            if len(events) >= 5:  # Minimum events for pattern detection
                await self._detect_patterns(event_type, events)

    async def _detect_patterns(self, event_type: str, events: list[LearningEvent]):
        """Detect patterns in events."""
        # Temporal pattern detection
        temporal_patterns = self._detect_temporal_patterns(events)
        for pattern in temporal_patterns:
            await self._add_or_update_pattern(pattern)

        # Sequence pattern detection
        sequence_patterns = self._detect_sequence_patterns(events)
        for pattern in sequence_patterns:
            await self._add_or_update_pattern(pattern)

    def _detect_temporal_patterns(self, events: list[LearningEvent]) -> list[HabitPattern]:
        """Detect time-based patterns (hourly, daily, weekly)."""
        patterns = []

        # Extract timestamps
        timestamps = [e.timestamp for e in events]
        timestamps.sort()

        # Hourly patterns
        hour_counts = defaultdict(int)
        for ts in timestamps:
            hour_counts[ts.hour] += 1

        # Find significant hours (occurring > 30% of days in window)
        window_days = self.config.habit_detection_window_days
        min_occurrences = max(3, window_days * 0.3)

        for hour, count in hour_counts.items():
            if count >= min_occurrences:
                confidence = min(count / window_days, 1.0)
                if confidence >= self.config.min_pattern_confidence:
                    pattern = HabitPattern(
                        id=hashlib.md5(f"{event_type}_hourly_{hour}".encode()).hexdigest()[:12],
                        pattern_type=PatternType.TEMPORAL,
                        name=f"{event_type} at hour {hour}",
                        description=f"Recurring {event_type} around {hour:02d}:00",
                        confidence=confidence,
                        frequency="daily",
                        time_windows=[{"start": f"{hour:02d}:00", "end": f"{hour:02d}:59", "days": list(range(7))}],
                        triggers=[f"time_{hour:02d}"],
                        actions=[event_type],
                        metadata={"hour": hour, "avg_count_per_day": count / window_days},
                        occurrence_count=count,
                    )
                    patterns.append(pattern)

        # Daily patterns (day of week)
        dow_counts = defaultdict(int)
        for ts in timestamps:
            dow_counts[ts.weekday()] += 1

        for dow, count in dow_counts.items():
            if count >= min_occurrences:
                confidence = min(count / (window_days / 7), 1.0)
                if confidence >= self.config.min_pattern_confidence:
                    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                    pattern = HabitPattern(
                        id=hashlib.md5(f"{event_type}_daily_{dow}".encode()).hexdigest()[:12],
                        pattern_type=PatternType.TEMPORAL,
                        name=f"{event_type} on {days[dow]}",
                        description=f"Recurring {event_type} on {days[dow]}s",
                        confidence=confidence,
                        frequency="weekly",
                        time_windows=[{"start": "00:00", "end": "23:59", "days": [dow]}],
                        triggers=[f"day_{days[dow].lower()}"],
                        actions=[event_type],
                        metadata={"day_of_week": dow, "avg_count_per_week": count / (window_days / 7)},
                        occurrence_count=count,
                    )
                    patterns.append(pattern)

        return patterns

    def _detect_sequence_patterns(self, events: list[LearningEvent]) -> list[HabitPattern]:
        """Detect sequential patterns (A followed by B)."""
        patterns = []

        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)

        # Look for sequences within 1 hour
        for i in range(len(events) - 1):
            e1 = events[i]
            e2 = events[i + 1]

            time_diff = (e2.timestamp - e1.timestamp).total_seconds()
            if time_diff <= 3600:  # Within 1 hour
                seq_key = f"{e1.event_type}->{e2.event_type}"
                # Count this sequence
                self._sequence_models[seq_key] = self._sequence_models.get(seq_key, 0) + 1

        # Create patterns for frequent sequences
        total_events = len(events)
        for seq_key, count in self._sequence_models.items():
            if count >= 3:
                confidence = min(count / (total_events * 0.1), 1.0)
                if confidence >= self.config.min_pattern_confidence:
                    parts = seq_key.split("->")
                    pattern = HabitPattern(
                        id=hashlib.md5(seq_key.encode()).hexdigest()[:12],
                        pattern_type=PatternType.USER_ACTIVITY,
                        name=f"Sequence: {parts[0]} then {parts[1]}",
                        description=f"{parts[0]} typically followed by {parts[1]} within 1 hour",
                        confidence=confidence,
                        frequency="irregular",
                        triggers=[parts[0]],
                        actions=[parts[1]],
                        metadata={"sequence": seq_key, "count": count},
                        occurrence_count=count,
                    )
                    patterns.append(pattern)

        return patterns

    async def _add_or_update_pattern(self, pattern: HabitPattern):
        """Add new pattern or update existing one."""
        if pattern.id in self._patterns:
            existing = self._patterns[pattern.id]
            # Update with weighted average
            total_occurrences = existing.occurrence_count + pattern.occurrence_count
            existing.confidence = (
                (existing.confidence * existing.occurrence_count) +
                (pattern.confidence * pattern.occurrence_count)
            ) / total_occurrences
            existing.occurrence_count = total_occurrences
            existing.last_seen = datetime.now()
            existing.metadata.update(pattern.metadata)
        else:
            self._patterns[pattern.id] = pattern
            self.logger.info("New pattern detected: %s (confidence: %.2f)", pattern.name, pattern.confidence)

            # Generate suggestion for new pattern
            if self.config.auto_schedule_enabled:
                self._pending_suggestions.append({
                    "type": "new_pattern",
                    "pattern": pattern,
                    "timestamp": datetime.now(),
                })

    async def _generate_predictions(self):
        """Generate predictions based on detected patterns."""
        now = datetime.now()
        self._predictions = []

        for pattern in self._patterns.values():
            if pattern.confidence < self.config.min_pattern_confidence:
                continue

            # Predict next occurrences based on pattern frequency
            if pattern.frequency == "daily":
                for window in pattern.time_windows:
                    next_time = self._get_next_daily_occurrence(window, now)
                    if next_time and (next_time - now).total_seconds() < self.config.prediction_horizon_days * 86400:
                        self._predictions.append(Prediction(
                            id=hashlib.md5(f"{pattern.id}_{next_time}".encode()).hexdigest()[:12],
                            pattern_id=pattern.id,
                            predicted_time=next_time,
                            prediction_type="habit_occurrence",
                            description=f"Predicted: {pattern.name}",
                            confidence=pattern.confidence * 0.9,  # Slightly lower for predictions
                            suggested_action=pattern.actions[0] if pattern.actions else None,
                            metadata={"pattern_name": pattern.name, "window": window}
                        ))

            elif pattern.frequency == "weekly":
                for window in pattern.time_windows:
                    next_time = self._get_next_weekly_occurrence(window, now)
                    if next_time and (next_time - now).total_seconds() < self.config.prediction_horizon_days * 86400:
                        self._predictions.append(Prediction(
                            id=hashlib.md5(f"{pattern.id}_{next_time}".encode()).hexdigest()[:12],
                            pattern_id=pattern.id,
                            predicted_time=next_time,
                            prediction_type="habit_occurrence",
                            description=f"Predicted: {pattern.name}",
                            confidence=pattern.confidence * 0.85,
                            suggested_action=pattern.actions[0] if pattern.actions else None,
                            metadata={"pattern_name": pattern.name, "window": window}
                        ))

        # Sort by predicted time
        self._predictions.sort(key=lambda p: p.predicted_time)

        # Limit predictions
        self._predictions = self._predictions[:50]

    def _get_next_daily_occurrence(self, window: dict[str, Any], now: datetime) -> datetime | None:
        """Get next daily occurrence for a time window."""
        try:
            start_time = datetime.strptime(window["start"], "%H:%M").time()
            next_date = now.date()
            if now.time() > start_time:
                next_date += timedelta(days=1)
            return datetime.combine(next_date, start_time)
        except Exception:
            return None

    def _get_next_weekly_occurrence(self, window: dict[str, Any], now: datetime) -> datetime | None:
        """Get next weekly occurrence for a time window."""
        try:
            start_time = datetime.strptime(window["start"], "%H:%M").time()
            days = window.get("days", [])
            if not days:
                return None

            current_dow = now.weekday()
            # Find next matching day
            for offset in range(8):
                check_dow = (current_dow + offset) % 7
                if check_dow in days:
                    next_date = now.date() + timedelta(days=offset)
                    if offset == 0 and now.time() > start_time:
                        continue
                    return datetime.combine(next_date, start_time)
        except Exception:
            return None
        return None

    def feed_event(self, event_type: str, source: str, data: dict[str, Any], context: dict[str, Any] = None):
        """Feed an event into the learning engine."""
        event = LearningEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            source=source,
            data=data,
            context=context or {}
        )
        self._events.append(event)

    async def update_models(self):
        """Update learning models with latest data."""
        self.logger.info("Updating learning models...")

        # Retrain temporal models
        await self._retrain_temporal_models()

        # Save models
        await self._save_models()

        self.logger.info("Models updated. Patterns: %d, Predictions: %d", len(self._patterns), len(self._predictions))

    async def _retrain_temporal_models(self):
        """Retrain temporal models from event history."""
        # Group events by type and time
        for pattern_type in PatternType:
            events_of_type = [e for e in self._events if self._classify_event(e) == pattern_type]
            if len(events_of_type) > 20:
                self._temporal_models[pattern_type.value] = self._build_temporal_model(events_of_type)

    def _classify_event(self, event: LearningEvent) -> PatternType:
        """Classify event into pattern type."""
        if event.event_type.startswith("app."):
            return PatternType.APPLICATION_USAGE
        elif event.event_type.startswith("system."):
            return PatternType.SYSTEM_RESOURCE
        elif event.event_type.startswith("file."):
            return PatternType.FILE_ACCESS
        elif event.event_type.startswith("network."):
            return PatternType.NETWORK_ACTIVITY
        elif "time" in event.event_type or "schedule" in event.event_type:
            return PatternType.TEMPORAL
        return PatternType.USER_ACTIVITY

    def _build_temporal_model(self, events: list[LearningEvent]) -> dict[str, Any]:
        """Build temporal probability model."""
        model = {
            "hourly": defaultdict(float),
            "daily": defaultdict(float),
            "total": len(events)
        }

        for event in events:
            model["hourly"][event.timestamp.hour] += 1
            model["daily"][event.timestamp.weekday()] += 1

        # Normalize
        for hour in model["hourly"]:
            model["hourly"][hour] /= model["total"]
        for day in model["daily"]:
            model["daily"][day] /= model["total"]

        return model

    def _extract_temporal_features(self, event: LearningEvent) -> dict[str, float]:
        """Extract temporal features from event."""
        ts = event.timestamp
        return {
            "hour": ts.hour / 24.0,
            "day_of_week": ts.weekday() / 7.0,
            "day_of_month": ts.day / 31.0,
            "month": ts.month / 12.0,
            "is_weekend": 1.0 if ts.weekday() >= 5 else 0.0,
        }

    def _extract_app_features(self, event: LearningEvent) -> dict[str, float]:
        """Extract application usage features."""
        return {
            "app_name_hash": hash(event.data.get("app_name", "")) % 1000 / 1000.0,
            "duration": min(event.data.get("duration", 0) / 3600.0, 1.0),
            "focus_time": min(event.data.get("focus_time", 0) / 3600.0, 1.0),
        }

    def _extract_resource_features(self, event: LearningEvent) -> dict[str, float]:
        """Extract system resource features."""
        return {
            "cpu_percent": event.data.get("cpu_percent", 0) / 100.0,
            "memory_percent": event.data.get("memory_percent", 0) / 100.0,
            "disk_percent": event.data.get("disk_percent", 0) / 100.0,
        }

    def _extract_file_features(self, event: LearningEvent) -> dict[str, float]:
        """Extract file access features."""
        return {
            "file_type_hash": hash(event.data.get("extension", "")) % 1000 / 1000.0,
            "file_size_mb": min(event.data.get("size", 0) / (1024*1024) / 100.0, 1.0),
            "operation_hash": hash(event.data.get("operation", "")) % 1000 / 1000.0,
        }

    def _extract_network_features(self, event: LearningEvent) -> dict[str, float]:
        """Extract network activity features."""
        return {
            "bytes_sent_mb": min(event.data.get("bytes_sent", 0) / (1024*1024) / 100.0, 1.0),
            "bytes_recv_mb": min(event.data.get("bytes_recv", 0) / (1024*1024) / 100.0, 1.0),
            "connections": min(event.data.get("connections", 0) / 100.0, 1.0),
        }

    def _extract_activity_features(self, event: LearningEvent) -> dict[str, float]:
        """Extract general user activity features."""
        return {
            "idle_time": min(event.data.get("idle_time", 0) / 3600.0, 1.0),
            "active_window_hash": hash(event.data.get("active_window", "")) % 1000 / 1000.0,
        }

    def get_patterns(self, pattern_type: PatternType = None) -> list[HabitPattern]:
        """Get detected patterns, optionally filtered by type."""
        patterns = list(self._patterns.values())
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        return sorted(patterns, key=lambda p: p.confidence, reverse=True)

    def get_predictions(self, hours_ahead: int = 24) -> list[Prediction]:
        """Get predictions for the next N hours."""
        now = datetime.now()
        cutoff = now + timedelta(hours=hours_ahead)
        return [p for p in self._predictions if p.predicted_time <= cutoff]

    def get_pending_suggestions(self) -> list[dict[str, Any]]:
        """Get and clear pending suggestions."""
        suggestions = self._pending_suggestions.copy()
        self._pending_suggestions.clear()
        return suggestions

    async def _save_models(self):
        """Save models to disk."""
        try:
            model_data = {
                "patterns": {k: asdict(v) for k, v in self._patterns.items()},
                "temporal_models": self._temporal_models,
                "sequence_models": self._sequence_models,
                "saved_at": datetime.now().isoformat(),
            }

            model_file = self._model_path / "habit_models.json"
            with open(model_file, 'w') as f:
                json.dump(model_data, f, default=str, indent=2)

        except Exception as e:
            self.logger.error("Failed to save models: %s", e)

    async def _load_models(self):
        """Load models from disk."""
        try:
            model_file = self._model_path / "habit_models.json"
            if model_file.exists():
                with open(model_file) as f:
                    model_data = json.load(f)

                # Restore patterns
                for pid, pdata in model_data.get("patterns", {}).items():
                    # Convert datetime strings back
                    pdata["first_seen"] = datetime.fromisoformat(pdata["first_seen"])
                    pdata["last_seen"] = datetime.fromisoformat(pdata["last_seen"])
                    pdata["pattern_type"] = PatternType(pdata["pattern_type"])
                    self._patterns[pid] = HabitPattern(**pdata)

                self._temporal_models = model_data.get("temporal_models", {})
                self._sequence_models = model_data.get("sequence_models", {})

                self.logger.info("Loaded %d patterns from disk", len(self._patterns))
        except Exception as e:
            self.logger.warning("Failed to load models: %s", e)

    async def shutdown(self):
        """Shutdown the habit engine."""
        self._running = False
        await self.update_models()  # Save before shutdown
        if self._engine_task:
            self._engine_task.cancel()
            try:
                await self._engine_task
            except asyncio.CancelledError:
                pass
