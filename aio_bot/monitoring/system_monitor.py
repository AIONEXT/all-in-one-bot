"""
System Monitoring Module - Comprehensive cross-platform system metrics collection.
Monitors CPU, RAM, Disk, Network, GPU, Processes, and System Logs.
"""

import asyncio
import logging
import os
import platform
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import psutil

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SystemMetrics:
    """Container for system metrics snapshot."""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_percent: float = 0.0
    cpu_per_core: list[float] = field(default_factory=list)
    cpu_freq_mhz: float = 0.0
    memory_total: int = 0
    memory_available: int = 0
    memory_used: int = 0
    memory_percent: float = 0.0
    swap_total: int = 0
    swap_used: int = 0
    swap_percent: float = 0.0
    disk_usage: dict[str, dict[str, Any]] = field(default_factory=dict)
    disk_io: dict[str, dict[str, Any]] = field(default_factory=dict)
    network_io: dict[str, dict[str, Any]] = field(default_factory=dict)
    network_connections: int = 0
    gpu_metrics: list[dict[str, Any]] = field(default_factory=list)
    process_count: int = 0
    top_processes: list[dict[str, Any]] = field(default_factory=list)
    boot_time: datetime = field(default_factory=datetime.now)
    uptime_seconds: float = 0.0
    load_average: list[float] = field(default_factory=list)


@dataclass
class SystemEvent:
    """System monitoring event."""
    timestamp: datetime = field(default_factory=datetime.now)
    type: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = ""
    source: str = ""
    component: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False


class SystemMonitor:
    """
    Cross-platform system monitoring with alerting and historical tracking.
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("AIOBot.SystemMonitor")
        self._running = False
        self._monitor_task: asyncio.Task | None = None
        self._metrics_history: deque = deque(maxlen=1000)
        self._events: deque = deque(maxlen=500)
        self._alert_callbacks: list[Callable] = []
        self._last_alerts: dict[str, datetime] = {}
        self._alert_cooldown = timedelta(minutes=5)
        self._process_cache: dict[int, dict] = {}
        self._network_baseline: dict[str, Any] = {}

    async def initialize(self):
        """Initialize the system monitor."""
        self.logger.info("Initializing System Monitor")

        # Collect baseline metrics
        await self._collect_metrics()

        # Initialize platform-specific monitoring
        if platform.system() == "Windows":
            await self._init_windows_monitoring()
        elif platform.system() == "Darwin":
            await self._init_macos_monitoring()
        elif platform.system() == "Linux":
            await self._init_linux_monitoring()

        self.logger.info("System Monitor initialized")

    async def _init_windows_monitoring(self):
        """Initialize Windows-specific monitoring (WMI, Event Logs)."""
        if WMI_AVAILABLE:
            try:
                self._wmi = wmi.WMI()
                self.logger.info("WMI monitoring enabled")
            except Exception as e:
                self.logger.warning("WMI initialization failed: %s", e)

        # Initialize performance counters
        self._perf_counters = {}

    async def _init_macos_monitoring(self):
        """Initialize macOS-specific monitoring (powermetrics, sysctl)."""
        self.logger.info("macOS monitoring initialized")

    async def _init_linux_monitoring(self):
        """Initialize Linux-specific monitoring (/proc, sysfs, journalctl)."""
        self.logger.info("Linux monitoring initialized")

    async def run(self):
        """Main monitoring loop."""
        self._running = True
        self.logger.info("System Monitor started")

        while self._running:
            try:
                metrics = await self._collect_metrics()
                self._metrics_history.append(metrics)

                # Check thresholds and generate alerts
                await self._check_thresholds(metrics)

                # Update process cache
                await self._update_process_cache()

                await asyncio.sleep(self.config.interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Monitoring error: %s", e, exc_info=True)
                await asyncio.sleep(5)

        self.logger.info("System Monitor stopped")

    async def _collect_metrics(self) -> SystemMetrics:
        """Collect comprehensive system metrics."""
        metrics = SystemMetrics()

        # CPU metrics
        metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
        metrics.cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            metrics.cpu_freq_mhz = cpu_freq.current

        # Memory metrics
        mem = psutil.virtual_memory()
        metrics.memory_total = mem.total
        metrics.memory_available = mem.available
        metrics.memory_used = mem.used
        metrics.memory_percent = mem.percent

        swap = psutil.swap_memory()
        metrics.swap_total = swap.total
        metrics.swap_used = swap.used
        metrics.swap_percent = swap.percent

        # Disk metrics
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                metrics.disk_usage[partition.mountpoint] = {
                    "device": partition.device,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                }
            except PermissionError:
                continue

        # Disk I/O
        disk_io = psutil.disk_io_counters(perdisk=True)
        if disk_io:
            for disk, counters in disk_io.items():
                metrics.disk_io[disk] = {
                    "read_count": counters.read_count,
                    "write_count": counters.write_count,
                    "read_bytes": counters.read_bytes,
                    "write_bytes": counters.write_bytes,
                    "read_time": counters.read_time,
                    "write_time": counters.write_time,
                }

        # Network I/O
        net_io = psutil.net_io_counters(pernic=True)
        for nic, counters in net_io.items():
            metrics.network_io[nic] = {
                "bytes_sent": counters.bytes_sent,
                "bytes_recv": counters.bytes_recv,
                "packets_sent": counters.packets_sent,
                "packets_recv": counters.packets_recv,
                "errin": counters.errin,
                "errout": counters.errout,
                "dropin": counters.dropin,
                "dropout": counters.dropout,
            }

        # Network connections
        try:
            metrics.network_connections = len(psutil.net_connections())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            metrics.network_connections = 0

        # GPU metrics
        if self.config.gpu_monitor_enabled and GPU_AVAILABLE:
            metrics.gpu_metrics = await self._collect_gpu_metrics()

        # Process metrics
        metrics.process_count = len(psutil.pids())
        metrics.top_processes = await self._get_top_processes(10)

        # System info
        metrics.boot_time = datetime.fromtimestamp(psutil.boot_time())
        metrics.uptime_seconds = (datetime.now() - metrics.boot_time).total_seconds()

        # Load average (Unix-like)
        if hasattr(os, 'getloadavg'):
            metrics.load_average = list(os.getloadavg())

        return metrics

    async def _collect_gpu_metrics(self) -> list[dict[str, Any]]:
        """Collect GPU metrics using GPUtil."""
        gpu_metrics = []
        try:
            gpus = GPUtil.getGPUs()
            for gpu in gpus:
                gpu_metrics.append({
                    "id": gpu.id,
                    "name": gpu.name,
                    "load": gpu.load * 100,
                    "memory_total": gpu.memoryTotal,
                    "memory_used": gpu.memoryUsed,
                    "memory_free": gpu.memoryFree,
                    "memory_percent": (gpu.memoryUsed / gpu.memoryTotal) * 100 if gpu.memoryTotal > 0 else 0,
                    "temperature": gpu.temperature,
                    "driver": gpu.driver,
                })
        except Exception as e:
            self.logger.debug("GPU metrics collection failed: %s", e)
        return gpu_metrics

    async def _get_top_processes(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top processes by CPU and memory usage."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                info = proc.info
                if info['cpu_percent'] is not None and info['cpu_percent'] > 0.1:
                    processes.append({
                        "pid": info['pid'],
                        "name": info['name'],
                        "username": info['username'],
                        "cpu_percent": info['cpu_percent'],
                        "memory_percent": info['memory_percent'],
                        "create_time": datetime.fromtimestamp(info['create_time']).isoformat() if info['create_time'] else None,
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        return processes[:limit]

    async def _update_process_cache(self):
        """Update process cache for tracking."""
        current_pids = set(psutil.pids())
        cached_pids = set(self._process_cache.keys())

        # New processes
        new_pids = current_pids - cached_pids
        for pid in new_pids:
            try:
                proc = psutil.Process(pid)
                self._process_cache[pid] = {
                    "name": proc.name(),
                    "cmdline": proc.cmdline(),
                    "create_time": proc.create_time(),
                    "username": proc.username(),
                }
                self._add_event(SystemEvent(
                    type="system.process_started",
                    severity=AlertSeverity.INFO,
                    message=f"Process started: {self._process_cache[pid]['name']} (PID: {pid})",
                    source="system_monitor",
                    component=f"process:{pid}",
                    data={"pid": pid, **self._process_cache[pid]}
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Terminated processes
        terminated_pids = cached_pids - current_pids
        for pid in terminated_pids:
            proc_info = self._process_cache.pop(pid, {})
            self._add_event(SystemEvent(
                type="system.process_ended",
                severity=AlertSeverity.INFO,
                message=f"Process ended: {proc_info.get('name', 'Unknown')} (PID: {pid})",
                source="system_monitor",
                component=f"process:{pid}",
                data={"pid": pid, **proc_info}
            ))

    async def _check_thresholds(self, metrics: SystemMetrics):
        """Check metrics against thresholds and generate alerts."""
        now = datetime.now()

        # CPU threshold
        if metrics.cpu_percent >= self.config.cpu_threshold_percent:
            await self._maybe_alert("high_cpu",
                f"High CPU usage: {metrics.cpu_percent:.1f}%",
                AlertSeverity.WARNING if metrics.cpu_percent < 95 else AlertSeverity.CRITICAL,
                {"cpu_percent": metrics.cpu_percent, "per_core": metrics.cpu_per_core})

        # Memory threshold
        if metrics.memory_percent >= self.config.memory_threshold_percent:
            await self._maybe_alert("high_memory",
                f"High memory usage: {metrics.memory_percent:.1f}%",
                AlertSeverity.WARNING if metrics.memory_percent < 95 else AlertSeverity.CRITICAL,
                {"memory_percent": metrics.memory_percent, "used_gb": metrics.memory_used / (1024**3)})

        # Swap threshold
        if metrics.swap_percent > 50:
            await self._maybe_alert("high_swap",
                f"High swap usage: {metrics.swap_percent:.1f}%",
                AlertSeverity.WARNING,
                {"swap_percent": metrics.swap_percent})

        # Disk thresholds
        for mount, usage in metrics.disk_usage.items():
            if usage["percent"] >= self.config.disk_threshold_percent:
                await self._maybe_alert(f"high_disk_{mount.replace('/', '_')}",
                    f"Disk {mount} usage: {usage['percent']:.1f}%",
                    AlertSeverity.WARNING if usage["percent"] < 98 else AlertSeverity.CRITICAL,
                    {"mount": mount, **usage})

        # GPU thresholds
        for gpu in metrics.gpu_metrics:
            if gpu["temperature"] > 85:
                await self._maybe_alert(f"gpu_overheat_{gpu['id']}",
                    f"GPU {gpu['name']} overheating: {gpu['temperature']}°C",
                    AlertSeverity.CRITICAL,
                    gpu)
            if gpu["memory_percent"] > 90:
                await self._maybe_alert(f"gpu_memory_{gpu['id']}",
                    f"GPU {gpu['name']} memory high: {gpu['memory_percent']:.1f}%",
                    AlertSeverity.WARNING,
                    gpu)

    async def _maybe_alert(self, alert_key: str, message: str, severity: AlertSeverity, data: dict[str, Any]):
        """Generate alert with cooldown."""
        now = datetime.now()
        last = self._last_alerts.get(alert_key)

        if last and (now - last) < self._alert_cooldown:
            return

        self._last_alerts[alert_key] = now

        event = SystemEvent(
            type=f"alert.{alert_key}",
            severity=severity,
            message=message,
            source="system_monitor",
            component=alert_key,
            data=data
        )
        self._add_event(event)

        # Trigger callbacks
        for callback in self._alert_callbacks:
            try:
                await callback(event)
            except Exception as e:
                self.logger.error("Alert callback error: %s", e)

    def _add_event(self, event: SystemEvent):
        """Add event to queue."""
        self._events.append(event)
        self.logger.log(
            logging.WARNING if event.severity == AlertSeverity.WARNING else
            logging.CRITICAL if event.severity == AlertSeverity.CRITICAL else
            logging.INFO,
            "%s: %s", event.type, event.message
        )

    def register_alert_callback(self, callback: Callable):
        """Register callback for alerts."""
        self._alert_callbacks.append(callback)

    def get_pending_events(self) -> list[SystemEvent]:
        """Get and clear pending events."""
        events = list(self._events)
        self._events.clear()
        return events

    def get_latest_metrics(self) -> SystemMetrics | None:
        """Get most recent metrics."""
        return self._metrics_history[-1] if self._metrics_history else None

    def get_metrics_history(self, minutes: int = 60) -> list[SystemMetrics]:
        """Get metrics history for specified minutes."""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self._metrics_history if m.timestamp >= cutoff]

    def get_system_summary(self) -> dict[str, Any]:
        """Get human-readable system summary."""
        metrics = self.get_latest_metrics()
        if not metrics:
            return {"status": "no_data"}

        return {
            "timestamp": metrics.timestamp.isoformat(),
            "cpu": {
                "percent": round(metrics.cpu_percent, 1),
                "cores": len(metrics.cpu_per_core),
                "freq_mhz": round(metrics.cpu_freq_mhz, 1),
            },
            "memory": {
                "total_gb": round(metrics.memory_total / (1024**3), 2),
                "used_gb": round(metrics.memory_used / (1024**3), 2),
                "available_gb": round(metrics.memory_available / (1024**3), 2),
                "percent": round(metrics.memory_percent, 1),
            },
            "swap": {
                "total_gb": round(metrics.swap_total / (1024**3), 2),
                "used_gb": round(metrics.swap_used / (1024**3), 2),
                "percent": round(metrics.swap_percent, 1),
            },
            "disks": {
                mount: {
                    "total_gb": round(u["total"] / (1024**3), 2),
                    "used_gb": round(u["used"] / (1024**3), 2),
                    "free_gb": round(u["free"] / (1024**3), 2),
                    "percent": round(u["percent"], 1),
                }
                for mount, u in metrics.disk_usage.items()
            },
            "gpu": [
                {
                    "name": g["name"],
                    "load_percent": round(g["load"], 1),
                    "memory_percent": round(g["memory_percent"], 1),
                    "temperature": g["temperature"],
                }
                for g in metrics.gpu_metrics
            ],
            "processes": metrics.process_count,
            "uptime_hours": round(metrics.uptime_seconds / 3600, 1),
            "top_processes": metrics.top_processes[:5],
        }

    async def shutdown(self):
        """Shutdown the monitor."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
