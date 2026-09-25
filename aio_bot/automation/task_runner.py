"""
Automation Task Runner - Executes background tasks, auto-fixes, and maintenance.
"""

import asyncio
import logging
import os
import platform
import shutil
import subprocess
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Automation task."""
    id: str
    type: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300


class TaskRunner:
    """
    Background task runner for automation, auto-fixes, and maintenance tasks.
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("AIOBot.TaskRunner")
        self._running = False
        self._runner_task: asyncio.Task | None = None

        # Task queue
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running_tasks: dict[str, Task] = {}
        self._completed_tasks: deque = deque(maxlen=100)
        self._failed_tasks: deque = deque(maxlen=50)

        # Task handlers
        self._handlers: dict[str, Callable] = {}
        self._register_default_handlers()

        # Stats
        self._stats = {
            "total_queued": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_retries": 0,
        }

    def _register_default_handlers(self):
        """Register default task handlers."""
        self._handlers.update({
            "auto_fix": self._handle_auto_fix,
            "restart_service": self._handle_restart_service,
            "cleanup_temp": self._handle_cleanup_temp,
            "cleanup_duplicates": self._handle_cleanup_duplicates,
            "archive_files": self._handle_archive_files,
            "run_backup": self._handle_run_backup,
            "update_system": self._handle_update_system,
            "disk_cleanup": self._handle_disk_cleanup,
            "memory_optimize": self._handle_memory_optimize,
            "network_reset": self._handle_network_reset,
        })

    async def initialize(self):
        """Initialize the task runner."""
        self.logger.info("Initializing Task Runner")
        self.logger.info("Task Runner initialized")

    async def run(self):
        """Main task runner loop."""
        self._running = True
        self.logger.info("Task Runner started")

        while self._running:
            try:
                # Get next task with timeout
                try:
                    priority, task = await asyncio.wait_for(
                        self._task_queue.get(), timeout=1.0
                    )
                except TimeoutError:
                    continue

                # Execute task
                await self._execute_task(task)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Task runner error: %s", e, exc_info=True)
                await asyncio.sleep(1)

        self.logger.info("Task Runner stopped")

    async def queue_task(self, task_data: dict[str, Any]) -> str:
        """Queue a new task."""
        task = Task(
            id=task_data.get("id", f"task_{datetime.now().timestamp()}"),
            type=task_data.get("type", "unknown"),
            priority=TaskPriority(task_data.get("priority", 1)),
            payload=task_data.get("payload", {}),
            max_retries=task_data.get("max_retries", self.config.max_auto_fix_attempts),
            timeout_seconds=task_data.get("timeout", 300),
        )

        # Priority queue uses negative priority for max-heap behavior
        await self._task_queue.put((-task.priority.value, task))
        self._stats["total_queued"] += 1

        self.logger.info("Queued task: %s (type: %s, priority: %s)", task.id, task.type, task.priority.name)
        return task.id

    async def _execute_task(self, task: Task):
        """Execute a single task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self._running_tasks[task.id] = task

        self.logger.info("Executing task: %s (%s)", task.id, task.type)

        try:
            # Get handler
            handler = self._handlers.get(task.type)
            if not handler:
                raise ValueError(f"No handler for task type: {task.type}")

            # Run with timeout
            result = await asyncio.wait_for(
                handler(task),
                timeout=task.timeout_seconds
            )

            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()
            self._completed_tasks.append(task)
            self._stats["total_completed"] += 1

            self.logger.info("Task completed: %s", task.id)

            # Notify if configured
            if self.config.notification_on_auto_fix and task.type in ["auto_fix", "restart_service"]:
                await self._notify_completion(task)

        except TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = f"Task timed out after {task.timeout_seconds}s"
            self.logger.error("Task timed out: %s", task.id)
            await self._handle_failure(task)

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.logger.error("Task failed: %s - %s", task.id, e)
            await self._handle_failure(task)

        finally:
            self._running_tasks.pop(task.id, None)

    async def _handle_failure(self, task: Task):
        """Handle task failure with retry logic."""
        self._stats["total_failed"] += 1

        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            self._stats["total_retries"] += 1
            self.logger.info("Retrying task: %s (attempt %d/%d)", task.id, task.retry_count, task.max_retries)

            # Re-queue with delay
            await asyncio.sleep(min(2 ** task.retry_count, 60))
            await self._task_queue.put((-task.priority.value, task))
        else:
            task.completed_at = datetime.now()
            self._failed_tasks.append(task)
            self.logger.error("Task failed permanently: %s - %s", task.id, task.error)

    # ============================================================
    # Task Handlers
    # ============================================================

    async def _handle_auto_fix(self, task: Task) -> dict[str, Any]:
        """Handle generic auto-fix task."""
        trigger = task.payload.get("trigger", {})
        fix_type = trigger.get("type", "unknown")

        results = {"fixes_applied": []}

        if fix_type == "high_cpu":
            # Find and potentially limit CPU-hungry processes
            result = await self._fix_high_cpu()
            results["fixes_applied"].append(result)

        elif fix_type == "high_memory":
            # Trigger garbage collection, clear caches
            result = await self._fix_high_memory()
            results["fixes_applied"].append(result)

        elif fix_type == "high_disk":
            # Clean temp files, empty trash
            result = await self._fix_high_disk()
            results["fixes_applied"].append(result)

        elif fix_type == "service_failed":
            # Restart the service
            service = trigger.get("service")
            if service:
                result = await self._restart_service_internal(service)
                results["fixes_applied"].append(result)

        return results

    async def _fix_high_cpu(self) -> dict[str, Any]:
        """Attempt to fix high CPU usage."""
        import psutil

        # Find top CPU processes
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                if proc.info['cpu_percent'] > 50:
                    processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)

        # Don't auto-kill, just report
        return {
            "action": "high_cpu_analysis",
            "top_processes": processes[:5],
            "recommendation": "Review high CPU processes manually"
        }

    async def _fix_high_memory(self) -> dict[str, Any]:
        """Attempt to fix high memory usage."""
        import gc

        import psutil

        # Force garbage collection
        gc.collect()

        # Get memory info
        mem = psutil.virtual_memory()

        return {
            "action": "memory_optimization",
            "gc_collected": True,
            "memory_percent_after": mem.percent,
            "recommendation": "Consider closing unused applications"
        }

    async def _fix_high_disk(self) -> dict[str, Any]:
        """Attempt to fix high disk usage."""

        # Clean system temp
        cleaned = 0
        temp_dirs = []
        if platform.system() == "Windows":
            temp_dirs = [
                Path(os.environ.get('TEMP', 'C:\\Temp')),
                Path('C:\\Windows\\Temp'),
            ]
        else:
            temp_dirs = [Path('/tmp'), Path('/var/tmp')]

        for temp_dir in temp_dirs:
            if temp_dir.exists():
                for item in temp_dir.iterdir():
                    try:
                        if item.is_file():
                            if (datetime.now() - datetime.fromtimestamp(item.stat().st_mtime)).days > 1:
                                size = item.stat().st_size
                                item.unlink()
                                cleaned += size
                        elif item.is_dir():
                            if (datetime.now() - datetime.fromtimestamp(item.stat().st_mtime)).days > 1:
                                shutil.rmtree(item, ignore_errors=True)
                    except Exception:
                        pass

        return {
            "action": "disk_cleanup",
            "bytes_cleaned": cleaned,
            "recommendation": "Review large files and duplicates"
        }

    async def _handle_restart_service(self, task: Task) -> dict[str, Any]:
        """Handle service restart task."""
        service = task.payload.get("service")
        if not service:
            raise ValueError("No service specified")

        return await self._restart_service_internal(service)

    async def _restart_service_internal(self, service: str) -> dict[str, Any]:
        """Internal service restart logic."""
        system = platform.system()

        try:
            if system == "Windows":
                # Use sc or net commands
                subprocess.run(["sc", "stop", service], capture_output=True, timeout=30)
                await asyncio.sleep(2)
                result = subprocess.run(["sc", "start", service], capture_output=True, timeout=30)
                success = result.returncode == 0
            elif system == "Darwin":
                # Use launchctl
                subprocess.run(["launchctl", "stop", service], capture_output=True, timeout=30)
                await asyncio.sleep(2)
                result = subprocess.run(["launchctl", "start", service], capture_output=True, timeout=30)
                success = result.returncode == 0
            else:
                # Use systemctl
                subprocess.run(["systemctl", "restart", service], capture_output=True, timeout=60)
                success = True

            return {
                "action": "service_restart",
                "service": service,
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "action": "service_restart",
                "service": service,
                "success": False,
                "error": str(e)
            }

    async def _handle_cleanup_temp(self, task: Task) -> dict[str, Any]:
        """Handle temp file cleanup."""
        return await self._fix_high_disk()

    async def _handle_cleanup_duplicates(self, task: Task) -> dict[str, Any]:
        """Handle duplicate file cleanup."""
        duplicates = task.payload.get("duplicates", [])
        deleted = 0
        space_freed = 0

        for dup in duplicates:
            path = Path(dup.get("path", ""))
            if path.exists():
                try:
                    size = path.stat().st_size
                    path.unlink()
                    deleted += 1
                    space_freed += size
                except Exception as e:
                    self.logger.warning("Failed to delete duplicate %s: %s", path, e)

        return {
            "action": "cleanup_duplicates",
            "deleted": deleted,
            "space_freed_bytes": space_freed
        }

    async def _handle_archive_files(self, task: Task) -> dict[str, Any]:
        """Handle file archival."""
        files = task.payload.get("files", [])
        target_dir = Path(task.payload.get("target_dir", ""))

        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)

        archived = 0
        space_freed = 0

        for f in files:
            path = Path(f.get("path", ""))
            if path.exists():
                try:
                    target = target_dir / path.name
                    # Handle conflicts
                    counter = 1
                    while target.exists():
                        target = target_dir / f"{path.stem}_{counter}{path.suffix}"
                        counter += 1

                    shutil.move(str(path), str(target))
                    archived += 1
                    space_freed += f.get("size", 0)
                except Exception as e:
                    self.logger.warning("Failed to archive %s: %s", path, e)

        return {
            "action": "archive_files",
            "archived": archived,
            "space_freed_bytes": space_freed,
            "target_dir": str(target_dir)
        }

    async def _handle_run_backup(self, task: Task) -> dict[str, Any]:
        """Handle backup task."""
        # This would integrate with the file organizer's backup
        return {
            "action": "run_backup",
            "status": "delegated_to_file_organizer",
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_update_system(self, task: Task) -> dict[str, Any]:
        """Handle system update task."""
        system = platform.system()

        try:
            if system == "Windows":
                # Windows updates are complex, just check
                return {"action": "update_system", "platform": "windows", "status": "check_only"}
            elif system == "Darwin":
                # macOS updates
                result = subprocess.run(["softwareupdate", "-i", "-a"], capture_output=True, text=True, timeout=300)
                return {"action": "update_system", "platform": "macos", "success": result.returncode == 0}
            else:
                # Linux - try apt
                result = subprocess.run(["apt", "update", "&&", "apt", "upgrade", "-y"],
                                      shell=True, capture_output=True, text=True, timeout=300)
                return {"action": "update_system", "platform": "linux", "success": result.returncode == 0}
        except Exception as e:
            return {"action": "update_system", "error": str(e)}

    async def _handle_disk_cleanup(self, task: Task) -> dict[str, Any]:
        """Handle disk cleanup task."""
        return await self._fix_high_disk()

    async def _handle_memory_optimize(self, task: Task) -> dict[str, Any]:
        """Handle memory optimization."""
        return await self._fix_high_memory()

    async def _handle_network_reset(self, task: Task) -> dict[str, Any]:
        """Handle network reset."""
        system = platform.system()

        try:
            if system == "Windows":
                subprocess.run(["netsh", "winsock", "reset"], capture_output=True, timeout=30)
                subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=10)
                return {"action": "network_reset", "platform": "windows", "success": True}
            elif system == "Darwin":
                subprocess.run(["dscacheutil", "-flushcache"], capture_output=True, timeout=10)
                subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], capture_output=True, timeout=10)
                return {"action": "network_reset", "platform": "macos", "success": True}
            else:
                subprocess.run(["systemctl", "restart", "systemd-resolved"], capture_output=True, timeout=30)
                return {"action": "network_reset", "platform": "linux", "success": True}
        except Exception as e:
            return {"action": "network_reset", "error": str(e)}

    async def _notify_completion(self, task: Task):
        """Notify about task completion."""
        # This would integrate with notification system
        self.logger.info("Auto-fix completed: %s - %s", task.id, task.type)

    def register_handler(self, task_type: str, handler: Callable):
        """Register a custom task handler."""
        self._handlers[task_type] = handler

    def get_task_status(self, task_id: str) -> Task | None:
        """Get task status."""
        if task_id in self._running_tasks:
            return self._running_tasks[task_id]
        for task in self._completed_tasks:
            if task.id == task_id:
                return task
        for task in self._failed_tasks:
            if task.id == task_id:
                return task
        return None

    def get_stats(self) -> dict[str, Any]:
        """Get runner statistics."""
        return {
            **self._stats,
            "queue_size": self._task_queue.qsize(),
            "running_tasks": len(self._running_tasks),
        }

    async def shutdown(self):
        """Shutdown the task runner."""
        self._running = False
        if self._runner_task:
            self._runner_task.cancel()
            try:
                await self._runner_task
            except asyncio.CancelledError:
                pass

        # Wait for running tasks
        if self._running_tasks:
            await asyncio.sleep(2)
