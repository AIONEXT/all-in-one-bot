"""
Automation Scheduler - Schedules predictive tasks, maintenance windows, and recurring jobs.
"""

import asyncio
import logging
import platform
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Any

import croniter


class ScheduleType(Enum):
    """Types of scheduled tasks."""
    ONCE = "once"
    RECURRING = "recurring"
    CRON = "cron"
    INTERVAL = "interval"
    PREDICTED = "predicted"
    MAINTENANCE_WINDOW = "maintenance_window"


@dataclass
class ScheduledTask:
    """A scheduled task."""
    id: str
    name: str
    schedule_type: ScheduleType
    task_type: str  # Type of task to execute (e.g., "cleanup", "backup", "update")
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 0=low, 1=normal, 2=high, 3=critical

    # Scheduling
    cron_expression: str = ""
    interval_seconds: int = 0
    run_at: datetime | None = None
    next_run: datetime | None = None

    # Constraints
    enabled: bool = True
    max_runs: int = 0  # 0 = unlimited
    run_count: int = 0
    last_run: datetime | None = None
    last_result: dict[str, Any] = field(default_factory=dict)

    # Conditions
    run_only_if_idle: bool = False
    run_only_on_ac_power: bool = False
    min_battery_percent: int = 0
    maintenance_window_only: bool = False

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)


@dataclass
class MaintenanceWindow:
    """Maintenance window configuration."""
    name: str
    start_time: time
    end_time: time
    days: list[int] = field(default_factory=lambda: list(range(7)))  # 0=Monday
    enabled: bool = True
    tasks: list[str] = field(default_factory=list)  # Task IDs to run


class Scheduler:
    """
    Advanced task scheduler with cron support, maintenance windows, and predictive scheduling.
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("AIOBot.Scheduler")
        self._running = False
        self._scheduler_task: asyncio.Task | None = None

        # Task storage
        self._tasks: dict[str, ScheduledTask] = {}
        self._maintenance_windows: list[MaintenanceWindow] = []

        # Task runner reference (set externally)
        self._task_runner = None

        # Default maintenance window
        self._setup_default_maintenance_window()

        # Register default scheduled tasks
        self._register_default_tasks()

    def _setup_default_maintenance_window(self):
        """Setup default maintenance window from config."""
        try:
            start = datetime.strptime(self.config.maintenance_window_start, "%H:%M").time()
            end = datetime.strptime(self.config.maintenance_window_end, "%H:%M").time()

            self._maintenance_windows.append(MaintenanceWindow(
                name="Default Maintenance",
                start_time=start,
                end_time=end,
                days=list(range(7)),
                enabled=True,
                tasks=["cleanup_temp", "disk_cleanup", "run_backup", "update_system"]
            ))
        except Exception as e:
            self.logger.warning("Failed to parse maintenance window: %s", e)

    def _register_default_tasks(self):
        """Register default scheduled tasks."""
        # Daily cleanup at 3 AM
        self.add_task(ScheduledTask(
            id="daily_cleanup",
            name="Daily Temp Cleanup",
            schedule_type=ScheduleType.CRON,
            task_type="cleanup_temp",
            cron_expression="0 3 * * *",  # 3 AM daily
            priority=1,
            tags=["maintenance", "cleanup"]
        ))

        # Weekly backup on Sunday at 2 AM
        self.add_task(ScheduledTask(
            id="weekly_backup",
            name="Weekly Backup",
            schedule_type=ScheduleType.CRON,
            task_type="run_backup",
            cron_expression="0 2 * * 0",  # 2 AM Sunday
            priority=1,
            tags=["maintenance", "backup"]
        ))

        # Hourly disk check
        self.add_task(ScheduledTask(
            id="hourly_disk_check",
            name="Hourly Disk Space Check",
            schedule_type=ScheduleType.INTERVAL,
            task_type="disk_cleanup",
            interval_seconds=3600,  # 1 hour
            priority=0,
            tags=["monitoring", "disk"]
        ))

        # Daily update check at 4 AM
        self.add_task(ScheduledTask(
            id="daily_update_check",
            name="Daily Update Check",
            schedule_type=ScheduleType.CRON,
            task_type="update_system",
            cron_expression="0 4 * * *",
            priority=0,
            tags=["maintenance", "update"]
        ))

    def set_task_runner(self, task_runner):
        """Set the task runner for executing tasks."""
        self._task_runner = task_runner

    async def initialize(self):
        """Initialize the scheduler."""
        self.logger.info("Initializing Scheduler")

        # Calculate next run times
        for task in self._tasks.values():
            self._calculate_next_run(task)

        self.logger.info("Scheduler initialized with %d tasks", len(self._tasks))

    async def run(self):
        """Main scheduler loop."""
        self._running = True
        self.logger.info("Scheduler started")

        while self._running:
            try:
                now = datetime.now()

                # Check for tasks to run
                await self._check_due_tasks(now)

                # Check maintenance windows
                await self._check_maintenance_windows(now)

                # Recalculate next runs for recurring tasks
                for task in self._tasks.values():
                    if task.schedule_type in [ScheduleType.CRON, ScheduleType.INTERVAL]:
                        if task.next_run and task.next_run <= now:
                            self._calculate_next_run(task)

                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Scheduler error: %s", e, exc_info=True)
                await asyncio.sleep(10)

        self.logger.info("Scheduler stopped")

    async def _check_due_tasks(self, now: datetime):
        """Check for tasks that are due to run."""
        due_tasks = []

        for task in self._tasks.values():
            if not task.enabled:
                continue
            if task.max_runs > 0 and task.run_count >= task.max_runs:
                continue
            if task.next_run and task.next_run <= now:
                # Check conditions
                if await self._check_task_conditions(task, now):
                    due_tasks.append(task)

        # Sort by priority (highest first)
        due_tasks.sort(key=lambda t: t.priority, reverse=True)

        for task in due_tasks:
            await self._execute_scheduled_task(task, now)

    async def _check_task_conditions(self, task: ScheduledTask, now: datetime) -> bool:
        """Check if task conditions are met."""
        # Check idle condition
        if task.run_only_if_idle:
            # Would check user idle time
            pass

        # Check AC power (laptop)
        if task.run_only_on_ac_power:
            if platform.system() != "Windows":
                import psutil
                battery = psutil.sensors_battery()
                if battery and not battery.power_plugged:
                    return False

        # Check battery
        if task.min_battery_percent > 0:
            import psutil
            battery = psutil.sensors_battery()
            if battery and battery.percent < task.min_battery_percent:
                return False

        # Check maintenance window
        if task.maintenance_window_only:
            if not self._is_in_maintenance_window(now):
                return False

        return True

    def _is_in_maintenance_window(self, now: datetime) -> bool:
        """Check if current time is in any maintenance window."""
        current_time = now.time()
        current_day = now.weekday()  # 0=Monday

        for window in self._maintenance_windows:
            if not window.enabled:
                continue
            if current_day not in window.days:
                continue

            if window.start_time <= window.end_time:
                # Same day window
                if window.start_time <= current_time <= window.end_time:
                    return True
            else:
                # Overnight window
                if current_time >= window.start_time or current_time <= window.end_time:
                    return True

        return False

    async def _check_maintenance_windows(self, now: datetime):
        """Check and execute maintenance window tasks."""
        if not self._is_in_maintenance_window(now):
            return

        # Run maintenance window tasks
        for window in self._maintenance_windows:
            if not window.enabled or now.weekday() not in window.days:
                continue

            current_time = now.time()
            if window.start_time <= window.end_time:
                in_window = window.start_time <= current_time <= window.end_time
            else:
                in_window = current_time >= window.start_time or current_time <= window.end_time

            if in_window:
                for task_id in window.tasks:
                    task = self._tasks.get(task_id)
                    if task and task.enabled:
                        # Check if already run in this window
                        if task.last_run and task.last_run.date() == now.date():
                            continue
                        if await self._check_task_conditions(task, now):
                            await self._execute_scheduled_task(task, now)

    async def _execute_scheduled_task(self, task: ScheduledTask, now: datetime):
        """Execute a scheduled task."""
        self.logger.info("Executing scheduled task: %s (%s)", task.name, task.id)

        task.last_run = now
        task.run_count += 1

        try:
            if self._task_runner:
                task_id = await self._task_runner.queue_task({
                    "type": task.task_type,
                    "priority": task.priority,
                    "payload": task.payload,
                    "scheduled": True,
                    "schedule_id": task.id,
                })
                task.last_result = {"queued_task_id": task_id, "status": "queued"}
            else:
                task.last_result = {"status": "no_task_runner"}

        except Exception as e:
            self.logger.error("Failed to queue scheduled task %s: %s", task.id, e)
            task.last_result = {"status": "error", "error": str(e)}

        # Calculate next run
        self._calculate_next_run(task)

    def _calculate_next_run(self, task: ScheduledTask):
        """Calculate next run time for a task."""
        now = datetime.now()

        if task.schedule_type == ScheduleType.ONCE:
            if task.run_at and task.run_at > now:
                task.next_run = task.run_at
            else:
                task.next_run = None
                task.enabled = False

        elif task.schedule_type == ScheduleType.CRON:
            if task.cron_expression:
                try:
                    cron = croniter.croniter(task.cron_expression, now)
                    task.next_run = cron.get_next(datetime)
                except Exception as e:
                    self.logger.error("Invalid cron expression for %s: %s", task.id, e)
                    task.next_run = None

        elif task.schedule_type == ScheduleType.INTERVAL:
            if task.interval_seconds > 0:
                if task.last_run:
                    task.next_run = task.last_run + timedelta(seconds=task.interval_seconds)
                else:
                    task.next_run = now + timedelta(seconds=task.interval_seconds)

        elif task.schedule_type == ScheduleType.PREDICTED:
            # Handled by habit engine
            pass

    def add_task(self, task: ScheduledTask) -> bool:
        """Add a scheduled task."""
        if task.id in self._tasks:
            self.logger.warning("Task %s already exists, updating", task.id)

        self._tasks[task.id] = task
        self._calculate_next_run(task)
        self.logger.info("Added scheduled task: %s (next run: %s)", task.id, task.next_run)
        return True

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self.logger.info("Removed scheduled task: %s", task_id)
            return True
        return False

    def enable_task(self, task_id: str, enabled: bool = True) -> bool:
        """Enable or disable a task."""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = enabled
            if enabled:
                self._calculate_next_run(self._tasks[task_id])
            return True
        return False

    def add_maintenance_window(self, window: MaintenanceWindow):
        """Add a maintenance window."""
        self._maintenance_windows.append(window)
        self.logger.info("Added maintenance window: %s (%s-%s)", window.name, window.start_time, window.end_time)

    async def schedule_predicted_task(self, prediction_data: dict[str, Any]):
        """Schedule a task based on a prediction from the habit engine."""
        pattern_name = prediction_data.get("pattern_name", "predicted")
        predicted_time = prediction_data.get("predicted_time")
        suggested_action = prediction_data.get("suggested_action", "unknown")
        confidence = prediction_data.get("confidence", 0.5)

        if not predicted_time:
            return

        # Only schedule high confidence predictions
        if confidence < 0.7:
            return

        task_id = f"predicted_{pattern_name}_{int(predicted_time.timestamp())}"

        # Check if similar task already scheduled
        for existing in self._tasks.values():
            if existing.schedule_type == ScheduleType.PREDICTED and existing.run_at:
                if abs((existing.run_at - predicted_time).total_seconds()) < 3600:  # Within 1 hour
                    return  # Already scheduled

        task = ScheduledTask(
            id=task_id,
            name=f"Predicted: {pattern_name}",
            schedule_type=ScheduleType.PREDICTED,
            task_type=suggested_action,
            run_at=predicted_time,
            priority=1 if confidence > 0.8 else 0,
            payload={"predicted": True, "confidence": confidence, "pattern": pattern_name},
            tags=["predicted", "habit"],
        )

        self.add_task(task)
        self.logger.info("Scheduled predicted task: %s at %s", task_id, predicted_time)

    def get_tasks(self, enabled_only: bool = False) -> list[ScheduledTask]:
        """Get all scheduled tasks."""
        tasks = list(self._tasks.values())
        if enabled_only:
            tasks = [t for t in tasks if t.enabled]
        return sorted(tasks, key=lambda t: t.next_run or datetime.max)

    def get_upcoming_tasks(self, hours: int = 24) -> list[ScheduledTask]:
        """Get tasks scheduled to run in the next N hours."""
        now = datetime.now()
        cutoff = now + timedelta(hours=hours)

        upcoming = []
        for task in self._tasks.values():
            if task.enabled and task.next_run and now <= task.next_run <= cutoff:
                upcoming.append(task)

        return sorted(upcoming, key=lambda t: t.next_run)

    def get_maintenance_windows(self) -> list[MaintenanceWindow]:
        """Get all maintenance windows."""
        return self._maintenance_windows

    def get_stats(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        now = datetime.now()
        return {
            "total_tasks": len(self._tasks),
            "enabled_tasks": sum(1 for t in self._tasks.values() if t.enabled),
            "overdue_tasks": sum(1 for t in self._tasks.values()
                                 if t.enabled and t.next_run and t.next_run < now),
            "upcoming_24h": len(self.get_upcoming_tasks(24)),
            "maintenance_windows": len(self._maintenance_windows),
            "task_types": list(set(t.task_type for t in self._tasks.values())),
        }

    async def shutdown(self):
        """Shutdown the scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
