"""
Core AIO Bot - Main orchestration class.
The central brain that coordinates all subsystems.
"""

import asyncio
import logging
import platform
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from aio_bot.automation.scheduler import Scheduler
from aio_bot.automation.task_runner import TaskRunner
from aio_bot.config.manager import AppConfig, ConfigManager
from aio_bot.data_mgmt.file_organizer import FileOrganizer
from aio_bot.health.health_monitor import HealthMonitor
from aio_bot.learning.habit_engine import HabitEngine
from aio_bot.monitoring.system_monitor import SystemMonitor


class BotState(Enum):
    """Bot operational states."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class BotStatus:
    """Current bot status information."""
    state: BotState = BotState.INITIALIZING
    started_at: datetime | None = None
    last_health_check: datetime | None = None
    active_tasks: int = 0
    completed_tasks: int = 0
    errors_count: int = 0
    warnings_count: int = 0
    system_info: dict[str, Any] = field(default_factory=dict)


class AIOBot:
    """
    Main AIO Bot class - The master mind that orchestrates all subsystems.
    """

    def __init__(self, config_path: str | None = None):
        self.config_manager = ConfigManager(config_path)
        self.config: AppConfig = self.config_manager.config
        self.state = BotState.INITIALIZING
        self.status = BotStatus()
        self.logger = self._setup_logging()

        # Core components
        self.system_monitor: SystemMonitor | None = None
        self.habit_engine: HabitEngine | None = None
        self.file_organizer: FileOrganizer | None = None
        self.health_monitor: HealthMonitor | None = None
        self.task_runner: TaskRunner | None = None
        self.scheduler: Scheduler | None = None

        # Runtime
        self._running = False
        self._main_task: asyncio.Task | None = None
        self._background_tasks: list[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()

    def _setup_logging(self) -> logging.Logger:
        """Setup application logging."""
        logger = logging.getLogger("AIOBot")
        logger.setLevel(getattr(logging, self.config.log_level.upper()))

        # Console handler
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            # File handler
            log_dir = Path(self.config.data_dir) / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_dir / 'aiobot.log')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    async def initialize(self) -> bool:
        """Initialize all subsystems."""
        self.logger.info("Initializing AIO Bot v%s", self.config.version)
        self.state = BotState.INITIALIZING

        try:
            # Collect system info
            self.status.system_info = self._collect_system_info()
            self.logger.info("System: %s %s", platform.system(), platform.release())

            # Initialize monitoring
            if self.config.monitoring.enabled:
                self.system_monitor = SystemMonitor(self.config.monitoring)
                await self.system_monitor.initialize()
                self.logger.info("System monitor initialized")

            # Initialize learning engine
            if self.config.learning.enabled:
                self.habit_engine = HabitEngine(self.config.learning)
                await self.habit_engine.initialize()
                self.logger.info("Habit engine initialized")

            # Initialize file organizer
            if self.config.data_mgmt.enabled:
                self.file_organizer = FileOrganizer(self.config.data_mgmt)
                await self.file_organizer.initialize()
                self.logger.info("File organizer initialized")

            # Initialize health monitor
            if self.config.health.enabled:
                self.health_monitor = HealthMonitor(self.config.health)
                await self.health_monitor.initialize()
                self.logger.info("Health monitor initialized")

            # Initialize automation
            if self.config.automation.enabled:
                self.task_runner = TaskRunner(self.config.automation)
                await self.task_runner.initialize()
                self.scheduler = Scheduler(self.config.automation)
                await self.scheduler.initialize()
                self.logger.info("Automation system initialized")

            self.state = BotState.RUNNING
            self.status.started_at = datetime.now()
            self.logger.info("AIO Bot initialization complete")
            return True

        except Exception as e:
            self.logger.error("Initialization failed: %s", e, exc_info=True)
            self.state = BotState.ERROR
            return False

    def _collect_system_info(self) -> dict[str, Any]:
        """Collect basic system information."""
        import psutil
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "disk_partitions": len(psutil.disk_partitions()),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
        }

    async def start(self) -> bool:
        """Start the bot and all background tasks."""
        if self.state != BotState.RUNNING:
            self.logger.error("Bot not initialized. Call initialize() first.")
            return False

        self._running = True
        self.logger.info("Starting AIO Bot...")

        # Start background tasks
        if self.system_monitor:
            self._background_tasks.append(
                asyncio.create_task(self.system_monitor.run())
            )

        if self.habit_engine:
            self._background_tasks.append(
                asyncio.create_task(self.habit_engine.run())
            )

        if self.file_organizer:
            self._background_tasks.append(
                asyncio.create_task(self.file_organizer.run())
            )

        if self.health_monitor:
            self._background_tasks.append(
                asyncio.create_task(self.health_monitor.run())
            )

        if self.task_runner:
            self._background_tasks.append(
                asyncio.create_task(self.task_runner.run())
            )

        if self.scheduler:
            self._background_tasks.append(
                asyncio.create_task(self.scheduler.run())
            )

        # Start main loop
        self._main_task = asyncio.create_task(self._main_loop())

        self.logger.info("AIO Bot started successfully")
        return True

    async def _main_loop(self):
        """Main bot loop - coordinates subsystems and handles events."""
        self.logger.info("Main loop started")

        while self._running and not self._shutdown_event.is_set():
            try:
                # Update status
                self._update_status()

                # Check for maintenance window
                if self._is_maintenance_window():
                    await self._run_maintenance()

                # Process cross-system events
                await self._process_events()

                # Sleep before next iteration
                await asyncio.sleep(10)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in main loop: %s", e, exc_info=True)
                self.status.errors_count += 1
                await asyncio.sleep(30)  # Back off on error

        self.logger.info("Main loop stopped")

    def _update_status(self):
        """Update bot status from subsystems."""
        self.status.active_tasks = sum(
            1 for t in self._background_tasks if not t.done()
        )
        self.status.last_health_check = datetime.now()

        # Collect errors/warnings from subsystems
        if self.health_monitor:
            self.status.errors_count = self.health_monitor.error_count
            self.status.warnings_count = self.health_monitor.warning_count

    def _is_maintenance_window(self) -> bool:
        """Check if current time is within maintenance window."""
        now = datetime.now().time()
        start = datetime.strptime(self.config.automation.maintenance_window_start, "%H:%M").time()
        end = datetime.strptime(self.config.automation.maintenance_window_end, "%H:%M").time()
        return start <= now <= end

    async def _run_maintenance(self):
        """Run scheduled maintenance tasks."""
        self.logger.info("Running maintenance window tasks")
        self.state = BotState.MAINTENANCE

        try:
            # Cleanup temp files
            if self.file_organizer and self.config.automation.auto_cleanup_enabled:
                await self.file_organizer.cleanup_temp_files()

            # Run health checks
            if self.health_monitor:
                await self.health_monitor.run_full_check()

            # Update learning models
            if self.habit_engine:
                await self.habit_engine.update_models()

            # Check for updates
            if self.config.automation.auto_update_enabled:
                await self._check_updates()

        except Exception as e:
            self.logger.error("Maintenance error: %s", e)
        finally:
            self.state = BotState.RUNNING

    async def _process_events(self):
        """Process events from all subsystems."""
        events = []

        # Collect events from monitors
        if self.system_monitor:
            for event in self.system_monitor.get_pending_events():
                events.append({
                    'type': event.type,
                    'severity': event.severity.value,
                    'message': event.message,
                    'source': event.source,
                    'component': event.component,
                    'data': event.data,
                })

        if self.health_monitor:
            for event in self.health_monitor.get_pending_events():
                events.append({
                    'type': event.event_type.value,
                    'severity': event.severity.value,
                    'message': event.message,
                    'source': event.source,
                    'component': event.component,
                    'data': event.data,
                })

        if self.habit_engine:
            for sugg in self.habit_engine.get_pending_suggestions():
                events.append({
                    'type': 'habit.suggestion',
                    'severity': 'info',
                    'message': sugg.get('type', 'suggestion'),
                    'source': 'habit_engine',
                    'data': sugg,
                })

        # Process events
        for event in events:
            await self._handle_event(event)

    async def _handle_event(self, event: dict[str, Any]):
        """Handle a single event."""
        event_type = event.get('type', 'unknown')
        self.logger.debug("Handling event: %s", event_type)

        # Route to appropriate handler
        if event_type.startswith('system.'):
            await self._handle_system_event(event)
        elif event_type.startswith('health.'):
            await self._handle_health_event(event)
        elif event_type.startswith('habit.'):
            await self._handle_habit_event(event)
        elif event_type.startswith('file.'):
            await self._handle_file_event(event)

    async def _handle_system_event(self, event: dict[str, Any]):
        """Handle system monitoring events."""
        if event.get('severity') == 'critical':
            # Trigger immediate automation
            if self.task_runner:
                await self.task_runner.queue_task({
                    'type': 'auto_fix',
                    'trigger': event,
                    'priority': 'high'
                })

    async def _handle_health_event(self, event: dict[str, Any]):
        """Handle health monitoring events."""
        if event.get('type') == 'service_failed':
            if self.config.automation.auto_restart_failed_services:
                await self.task_runner.queue_task({
                    'type': 'restart_service',
                    'service': event.get('service'),
                    'priority': 'high'
                })

    async def _handle_habit_event(self, event: dict[str, Any]):
        """Handle habit learning events."""
        if event.get('type') == 'pattern_detected':
            # Schedule predicted task
            if self.scheduler:
                await self.scheduler.schedule_predicted_task(event)

    async def _handle_file_event(self, event: dict[str, Any]):
        """Handle file organization events."""
        if event.get('type') == 'duplicates_found':
            await self.task_runner.queue_task({
                'type': 'cleanup_duplicates',
                'duplicates': event.get('duplicates'),
                'priority': 'normal'
            })

    async def _check_updates(self):
        """Check for application and system updates."""
        self.logger.info("Checking for updates...")
        # Implementation would check GitHub releases, package managers, etc.

    async def stop(self):
        """Gracefully stop the bot."""
        self.logger.info("Shutting down AIO Bot...")
        self._running = False
        self.state = BotState.SHUTTING_DOWN
        self._shutdown_event.set()

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Cancel main task
        if self._main_task:
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass

        # Shutdown subsystems
        for component in [self.system_monitor, self.habit_engine, self.file_organizer,
                          self.health_monitor, self.task_runner, self.scheduler]:
            if component and hasattr(component, 'shutdown'):
                await component.shutdown()

        self.state = BotState.STOPPED
        self.logger.info("AIO Bot stopped")

    def get_status(self) -> BotStatus:
        """Get current bot status."""
        return self.status

    def get_config(self) -> AppConfig:
        """Get current configuration."""
        return self.config

    def update_config(self, path: str, value: Any) -> bool:
        """Update configuration at runtime."""
        return self.config_manager.set(path, value)
