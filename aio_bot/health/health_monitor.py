"""
System Health Monitoring Module.
Monitors system failures, errors, updates, critical issues, SMART disk health, services, etc.
"""

import asyncio
import json
import logging
import platform
import subprocess
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class EventType(Enum):
    """Health event types."""
    SERVICE_FAILED = "service_failed"
    SERVICE_RESTARTED = "service_restarted"
    DISK_ERROR = "disk_error"
    DISK_SMART_WARNING = "disk_smart_warning"
    MEMORY_ERROR = "memory_error"
    CPU_THROTTLING = "cpu_throttling"
    OVERHEATING = "overheating"
    UPDATE_AVAILABLE = "update_available"
    UPDATE_INSTALLED = "update_installed"
    UPDATE_FAILED = "update_failed"
    BOOT_ERROR = "boot_error"
    APPLICATION_CRASH = "application_crash"
    DRIVER_ISSUE = "driver_issue"
    NETWORK_ISSUE = "network_issue"
    PERMISSION_ERROR = "permission_error"
    FILESYSTEM_ERROR = "filesystem_error"


@dataclass
class HealthEvent:
    """Health monitoring event."""
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: EventType = EventType.SERVICE_FAILED
    severity: HealthStatus = HealthStatus.WARNING
    message: str = ""
    source: str = ""
    component: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    resolution_time: datetime | None = None


@dataclass
class ServiceStatus:
    """Service/daemon status."""
    name: str
    display_name: str
    status: str  # running, stopped, paused, unknown
    startup_type: str  # auto, manual, disabled
    pid: int | None = None
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    last_check: datetime = field(default_factory=datetime.now)
    restart_count: int = 0
    critical: bool = False


@dataclass
class DiskHealth:
    """Disk SMART health information."""
    device: str
    model: str
    serial: str
    health_status: HealthStatus = HealthStatus.UNKNOWN
    temperature: int | None = None
    power_on_hours: int | None = None
    reallocated_sectors: int = 0
    pending_sectors: int = 0
    uncorrectable_sectors: int = 0
    smart_attributes: dict[str, Any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.now)


@dataclass
class SystemHealthReport:
    """Complete system health report."""
    timestamp: datetime = field(default_factory=datetime.now)
    overall_status: HealthStatus = HealthStatus.HEALTHY
    services: list[ServiceStatus] = field(default_factory=list)
    disks: list[DiskHealth] = field(default_factory=list)
    events: list[HealthEvent] = field(default_factory=list)
    updates_pending: int = 0
    security_issues: int = 0
    performance_score: float = 100.0


class HealthMonitor:
    """
    Comprehensive system health monitoring.
    Tracks services, disk health (SMART), system logs, updates, and critical issues.
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("AIOBot.HealthMonitor")
        self._running = False
        self._monitor_task: asyncio.Task | None = None
        self._full_check_task: asyncio.Task | None = None

        # State
        self._events: deque = deque(maxlen=1000)
        self._services: dict[str, ServiceStatus] = {}
        self._disks: dict[str, DiskHealth] = {}
        self._update_status: dict[str, Any] = {}
        self._error_count = 0
        self._warning_count = 0
        self._alert_callbacks: list[Callable] = []
        self._last_full_check: datetime | None = None

        # Critical services to monitor
        self._critical_services = self._get_critical_services()

    def _get_critical_services(self) -> list[str]:
        """Get list of critical services for the current platform."""
        system = platform.system()
        if system == "Windows":
            return [
                "wuauserv",  # Windows Update
                "WinDefend",  # Windows Defender
                "EventLog",   # Event Log
                "PlugPlay",   # Plug and Play
                "RpcSs",      # Remote Procedure Call
                "Dnscache",   # DNS Client
                "dhcp",       # DHCP Client
                "lanmanworkstation",  # Workstation
                "lanmanserver",       # Server
            ]
        elif system == "Darwin":
            return [
                "com.apple.systemkextd",
                "com.apple.kextd",
                "com.apple.mDNSResponder",
                "com.apple.configd",
            ]
        else:  # Linux
            return [
                "systemd-journald",
                "systemd-udevd",
                "dbus",
                "network-manager",
                "systemd-resolved",
                "cron",
                "sshd",
            ]

    async def initialize(self):
        """Initialize the health monitor."""
        self.logger.info("Initializing Health Monitor")

        # Initial service scan
        await self._scan_services()

        # Initial disk health check
        if self.config.smart_monitoring_enabled:
            await self._check_disk_health()

        # Check for updates
        if self.config.update_check_enabled:
            await self._check_updates()

        self.logger.info("Health Monitor initialized")

    async def run(self):
        """Main health monitoring loop."""
        self._running = True
        self.logger.info("Health Monitor started")

        while self._running:
            try:
                # Periodic service check
                await self._scan_services()

                # Periodic disk health check
                if self.config.smart_monitoring_enabled:
                    await self._check_disk_health()

                # Check system logs
                if self.config.windows_event_log_enabled or self.config.macos_unified_log_enabled or self.config.linux_journal_enabled:
                    await self._check_system_logs()

                # Check for updates
                if self.config.update_check_enabled:
                    await self._check_updates()

                await asyncio.sleep(self.config.check_interval_minutes * 60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Health monitor error: %s", e, exc_info=True)
                await asyncio.sleep(30)

        self.logger.info("Health Monitor stopped")

    async def _scan_services(self):
        """Scan system services."""
        system = platform.system()

        if system == "Windows":
            await self._scan_windows_services()
        elif system == "Darwin":
            await self._scan_macos_services()
        else:
            await self._scan_linux_services()

    async def _scan_windows_services(self):
        """Scan Windows services using WMI or sc query."""
        try:
            # Use PowerShell to get service info
            cmd = [
                "powershell", "-Command",
                "Get-Service | Select-Object Name, DisplayName, Status, StartType | ConvertTo-Json"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                services = json.loads(result.stdout)
                if not isinstance(services, list):
                    services = [services]

                for svc in services:
                    name = svc.get("Name", "")
                    if name in self._critical_services or svc.get("Status") == "Running":
                        status_str = svc.get("Status", "Unknown")
                        start_type = svc.get("StartType", "Unknown")
                        # Handle cases where StartType might be an integer
                        if isinstance(start_type, int):
                            start_type_map = {2: "auto", 3: "manual", 4: "disabled"}
                            start_type = start_type_map.get(start_type, "unknown")
                        elif not isinstance(start_type, str):
                            start_type = str(start_type).lower()

                        self._services[name] = ServiceStatus(
                            name=name,
                            display_name=svc.get("DisplayName", name),
                            status=str(status_str).lower(),
                            startup_type=str(start_type).lower(),
                            critical=name in self._critical_services,
                            last_check=datetime.now()
                        )

                        # Check if critical service stopped
                        if name in self._critical_services and svc.get("Status") != "Running":
                            await self._add_event(HealthEvent(
                                event_type=EventType.SERVICE_FAILED,
                                severity=HealthStatus.CRITICAL,
                                message=f"Critical service stopped: {svc.get('DisplayName', name)}",
                                source="health_monitor",
                                component=name,
                                data={"service": name, "display_name": svc.get("DisplayName", name)}
                            ))
        except Exception as e:
            self.logger.warning("Windows service scan failed: %s", e)

    async def _scan_macos_services(self):
        """Scan macOS services (launchd)."""
        try:
            cmd = ["launchctl", "list"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        pid = parts[0]
                        status = parts[1]
                        name = parts[2]

                        if name in self._critical_services or pid != "-":
                            self._services[name] = ServiceStatus(
                                name=name,
                                display_name=name,
                                status="running" if pid != "-" else "stopped",
                                startup_type="auto",
                                pid=int(pid) if pid != "-" else None,
                                critical=name in self._critical_services,
                                last_check=datetime.now()
                            )
        except Exception as e:
            self.logger.warning("macOS service scan failed: %s", e)

    async def _scan_linux_services(self):
        """Scan Linux services (systemd)."""
        try:
            cmd = ["systemctl", "list-units", "--type=service", "--state=running,failed", "--no-legend", "--plain"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 4:
                        name = parts[0]
                        load = parts[1]
                        active = parts[2]
                        sub = parts[3]

                        if name in self._critical_services or active == "active":
                            self._services[name] = ServiceStatus(
                                name=name,
                                display_name=name,
                                status=sub,
                                startup_type="auto" if load == "loaded" else "manual",
                                critical=name in self._critical_services,
                                last_check=datetime.now()
                            )

                            if name in self._critical_services and active != "active":
                                await self._add_event(HealthEvent(
                                    event_type=EventType.SERVICE_FAILED,
                                    severity=HealthStatus.CRITICAL,
                                    message=f"Critical service failed: {name}",
                                    source="health_monitor",
                                    component=name,
                                    data={"service": name, "state": active, "sub": sub}
                                ))
        except Exception as e:
            self.logger.warning("Linux service scan failed: %s", e)

    async def _check_disk_health(self):
        """Check disk health using SMART."""
        system = platform.system()

        try:
            if system == "Windows":
                await self._check_disk_health_windows()
            elif system == "Darwin":
                await self._check_disk_health_macos()
            else:
                await self._check_disk_health_linux()
        except Exception as e:
            self.logger.warning("Disk health check failed: %s", e)

    async def _check_disk_health_windows(self):
        """Check disk health on Windows using WMI or smartctl."""
        try:
            # Try smartctl first (if installed)
            cmd = ["smartctl", "--scan"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if '/dev/' in line or '\\\\.\\' in line:
                        device = line.split()[0]
                        await self._run_smartctl(device)
            else:
                # Fallback to WMI
                await self._check_disk_health_wmi()
        except FileNotFoundError:
            await self._check_disk_health_wmi()
        except Exception as e:
            self.logger.warning("Windows disk health check failed: %s", e)

    async def _check_disk_health_wmi(self):
        """Check disk health using WMI."""
        try:
            import wmi
            c = wmi.WMI()
            for disk in c.Win32_DiskDrive():
                dh = DiskHealth(
                    device=disk.DeviceID,
                    model=disk.Model,
                    serial=disk.SerialNumber,
                    health_status=HealthStatus.HEALTHY if disk.Status == "OK" else HealthStatus.WARNING,
                )
                self._disks[disk.DeviceID] = dh

                if disk.Status != "OK":
                    await self._add_event(HealthEvent(
                        event_type=EventType.DISK_SMART_WARNING,
                        severity=HealthStatus.WARNING,
                        message=f"Disk health warning: {disk.Model} ({disk.DeviceID})",
                        source="health_monitor",
                        component=disk.DeviceID,
                        data={"model": disk.Model, "status": disk.Status}
                    ))
        except Exception as e:
            self.logger.debug("WMI disk check failed: %s", e)

    async def _check_disk_health_macos(self):
        """Check disk health on macOS using smartctl."""
        try:
            cmd = ["diskutil", "list"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if '/dev/disk' in line and 'disk0s' not in line:
                        device = line.split()[-1]
                        await self._run_smartctl(device)
        except Exception as e:
            self.logger.warning("macOS disk health check failed: %s", e)

    async def _check_disk_health_linux(self):
        """Check disk health on Linux using smartctl."""
        try:
            cmd = ["lsblk", "-d", "-n", "-o", "NAME,TYPE"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "disk":
                        device = f"/dev/{parts[0]}"
                        await self._run_smartctl(device)
        except Exception as e:
            self.logger.warning("Linux disk health check failed: %s", e)

    async def _run_smartctl(self, device: str):
        """Run smartctl on a device."""
        try:
            # Get health status
            cmd = ["smartctl", "-H", device]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            health_ok = "PASSED" in result.stdout

            # Get detailed attributes
            cmd = ["smartctl", "-A", device]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            attributes = {}
            reallocated = 0
            pending = 0
            uncorrectable = 0
            temperature = None
            power_on_hours = None

            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('===') and not line.startswith('ID#'):
                    parts = line.split()
                    if len(parts) >= 10:
                        attr_id = parts[0]
                        attr_name = parts[1]
                        value = int(parts[3]) if parts[3].isdigit() else 0
                        worst = int(parts[4]) if parts[4].isdigit() else 0
                        threshold = int(parts[5]) if parts[5].isdigit() else 0
                        raw = parts[9]

                        attributes[attr_name] = {
                            "id": attr_id,
                            "value": value,
                            "worst": worst,
                            "threshold": threshold,
                            "raw": raw
                        }

                        # Key attributes
                        if "Reallocated_Sector" in attr_name:
                            reallocated = int(raw) if raw.isdigit() else 0
                        elif "Current_Pending_Sector" in attr_name:
                            pending = int(raw) if raw.isdigit() else 0
                        elif "Uncorrectable" in attr_name:
                            uncorrectable = int(raw) if raw.isdigit() else 0
                        elif "Temperature" in attr_name:
                            temperature = int(raw) if raw.isdigit() else None
                        elif "Power_On_Hours" in attr_name:
                            power_on_hours = int(raw) if raw.isdigit() else None

            # Get model info
            cmd = ["smartctl", "-i", device]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            model = "Unknown"
            serial = "Unknown"
            for line in result.stdout.split('\n'):
                if "Model" in line and ":" in line:
                    model = line.split(":", 1)[1].strip()
                elif "Serial" in line and ":" in line:
                    serial = line.split(":", 1)[1].strip()

            dh = DiskHealth(
                device=device,
                model=model,
                serial=serial,
                health_status=HealthStatus.HEALTHY if health_ok else HealthStatus.CRITICAL,
                temperature=temperature,
                power_on_hours=power_on_hours,
                reallocated_sectors=reallocated,
                pending_sectors=pending,
                uncorrectable_sectors=uncorrectable,
                smart_attributes=attributes,
            )

            self._disks[device] = dh

            # Check for warnings
            if reallocated > 0 or pending > 0 or uncorrectable > 0:
                await self._add_event(HealthEvent(
                    event_type=EventType.DISK_SMART_WARNING,
                    severity=HealthStatus.WARNING if health_ok else HealthStatus.CRITICAL,
                    message=f"Disk SMART warning: {model} ({device}) - Reallocated: {reallocated}, Pending: {pending}",
                    source="health_monitor",
                    component=device,
                    data={"reallocated": reallocated, "pending": pending, "uncorrectable": uncorrectable}
                ))

            if temperature and temperature > 55:
                await self._add_event(HealthEvent(
                    event_type=EventType.OVERHEATING,
                    severity=HealthStatus.WARNING,
                    message=f"Disk overheating: {model} ({device}) at {temperature}°C",
                    source="health_monitor",
                    component=device,
                    data={"temperature": temperature}
                ))

        except Exception as e:
            self.logger.debug("smartctl failed for %s: %s", device, e)

    async def _check_system_logs(self):
        """Check system logs for errors and warnings."""
        system = platform.system()

        if system == "Windows" and self.config.windows_event_log_enabled:
            await self._check_windows_event_logs()
        elif system == "Darwin" and self.config.macos_unified_log_enabled:
            await self._check_macos_logs()
        elif system == "Linux" and self.config.linux_journal_enabled:
            await self._check_linux_journal()

    async def _check_windows_event_logs(self):
        """Check Windows Event Logs for errors."""
        try:
            # Check System log for errors in last hour
            since_time = (datetime.now() - timedelta(hours=1)).isoformat()
            filter_xpath = f"*[System[(Level=1 or Level=2 or Level=3) and TimeCreated[@SystemTime>='{since_time}']]]"
            cmd = [
                "powershell", "-Command",
                f"Get-WinEvent -LogName System -FilterXPath \"{filter_xpath}\" | Select-Object Id, LevelDisplayName, Message, Source, TimeCreated | ConvertTo-Json"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout.strip():
                events = json.loads(result.stdout)
                if not isinstance(events, list):
                    events = [events]

                for evt in events[:20]:  # Limit to 20 most recent
                    level = evt.get("LevelDisplayName", "")
                    severity = HealthStatus.CRITICAL if level == "Error" else HealthStatus.WARNING

                    await self._add_event(HealthEvent(
                        event_type=EventType.APPLICATION_CRASH if "crash" in evt.get("Message", "").lower() else EventType.SYSTEM_ERROR,
                        severity=severity,
                        message=evt.get("Message", "")[:500],
                        source="windows_event_log",
                        component=evt.get("Source", "System"),
                        data={"event_id": evt.get("Id"), "level": level, "time": evt.get("TimeCreated")}
                    ))
        except Exception as e:
            self.logger.debug("Windows event log check failed: %s", e)

    async def _check_macos_logs(self):
        """Check macOS unified logs."""
        try:
            # Use log command to get recent errors
            cmd = ["log", "show", "--predicate", "eventMessage contains[c] 'error' OR eventMessage contains[c] 'fail'",
                   "--last", "1h", "--style", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    try:
                        evt = json.loads(line)
                        await self._add_event(HealthEvent(
                            event_type=EventType.APPLICATION_CRASH,
                            severity=HealthStatus.WARNING,
                            message=evt.get("eventMessage", "")[:500],
                            source="macos_unified_log",
                            component=evt.get("subsystem", "unknown"),
                            data=evt
                        ))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            self.logger.debug("macOS log check failed: %s", e)

    async def _check_linux_journal(self):
        """Check Linux systemd journal."""
        try:
            cmd = ["journalctl", "-p", "err..emerg", "--since", "1 hour ago", "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    try:
                        evt = json.loads(line)
                        await self._add_event(HealthEvent(
                            event_type=EventType.APPLICATION_CRASH,
                            severity=HealthStatus.WARNING,
                            message=evt.get("MESSAGE", "")[:500],
                            source="linux_journal",
                            component=evt.get("SYSLOG_IDENTIFIER", "systemd"),
                            data={"PRIORITY": evt.get("PRIORITY"), "_SYSTEMD_UNIT": evt.get("_SYSTEMD_UNIT")}
                        ))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            self.logger.debug("Linux journal check failed: %s", e)

    async def _check_updates(self):
        """Check for system updates."""
        system = platform.system()

        try:
            if system == "Windows":
                await self._check_windows_updates()
            elif system == "Darwin":
                await self._check_macos_updates()
            else:
                await self._check_linux_updates()
        except Exception as e:
            self.logger.warning("Update check failed: %s", e)

    async def _check_windows_updates(self):
        """Check for Windows updates."""
        try:
            cmd = [
                "powershell", "-Command",
                "$session = New-Object -ComObject Microsoft.Update.Session; $searcher = $session.CreateUpdateSearcher(); $result = $searcher.Search(\"IsInstalled=0 and Type='Software'\"); $result.Updates.Count"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
                self._update_status = {
                    "pending": count,
                    "last_check": datetime.now().isoformat()
                }

                if count > 0:
                    await self._add_event(HealthEvent(
                        event_type=EventType.UPDATE_AVAILABLE,
                        severity=HealthStatus.INFO,
                        message=f"{count} Windows updates available",
                        source="health_monitor",
                        component="windows_update",
                        data={"count": count}
                    ))
        except Exception as e:
            self.logger.debug("Windows update check failed: %s", e)

    async def _check_macos_updates(self):
        """Check for macOS updates."""
        try:
            cmd = ["softwareupdate", "-l"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                updates = [l for l in lines if "*" in l and "Title:" in l]
                count = len(updates)

                self._update_status = {
                    "pending": count,
                    "last_check": datetime.now().isoformat()
                }

                if count > 0:
                    await self._add_event(HealthEvent(
                        event_type=EventType.UPDATE_AVAILABLE,
                        severity=HealthStatus.INFO,
                        message=f"{count} macOS updates available",
                        source="health_monitor",
                        component="macos_update",
                        data={"count": count, "updates": updates[:5]}
                    ))
        except Exception as e:
            self.logger.debug("macOS update check failed: %s", e)

    async def _check_linux_updates(self):
        """Check for Linux updates (apt/dnf/pacman)."""
        try:
            # Try apt
            cmd = ["apt", "list", "--upgradable"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                count = len([l for l in result.stdout.split('\n') if '/' in l and 'upgradable' in l])
                self._update_status = {"pending": count, "last_check": datetime.now().isoformat()}

                if count > 0:
                    await self._add_event(HealthEvent(
                        event_type=EventType.UPDATE_AVAILABLE,
                        severity=HealthStatus.INFO,
                        message=f"{count} package updates available",
                        source="health_monitor",
                        component="apt",
                        data={"count": count}
                    ))
                return
        except Exception:
            pass

        try:
            # Try dnf
            cmd = ["dnf", "check-update", "-q"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 100:  # dnf returns 100 when updates available
                count = len(result.stdout.strip().split('\n'))
                self._update_status = {"pending": count, "last_check": datetime.now().isoformat()}
        except Exception:
            pass

    async def _add_event(self, event: HealthEvent):
        """Add a health event."""
        self._events.append(event)

        if event.severity == HealthStatus.CRITICAL:
            self._error_count += 1
        elif event.severity == HealthStatus.WARNING:
            self._warning_count += 1

        self.logger.log(
            logging.CRITICAL if event.severity == HealthStatus.CRITICAL else
            logging.WARNING if event.severity == HealthStatus.WARNING else
            logging.INFO,
            "%s: %s", event.event_type.value, event.message
        )

        # Trigger callbacks
        for callback in self._alert_callbacks:
            try:
                await callback(event)
            except Exception as e:
                self.logger.error("Health alert callback error: %s", e)

    def register_alert_callback(self, callback: Callable):
        """Register callback for health alerts."""
        self._alert_callbacks.append(callback)

    def get_pending_events(self) -> list[HealthEvent]:
        """Get and clear pending events."""
        events = list(self._events)
        self._events.clear()
        return events

    def get_service_status(self) -> dict[str, ServiceStatus]:
        """Get current service statuses."""
        return self._services

    def get_disk_health(self) -> dict[str, DiskHealth]:
        """Get current disk health."""
        return self._disks

    def get_update_status(self) -> dict[str, Any]:
        """Get update status."""
        return self._update_status

    async def run_full_check(self):
        """Run a comprehensive health check."""
        self.logger.info("Running full health check")
        self._last_full_check = datetime.now()

        await self._scan_services()
        if self.config.smart_monitoring_enabled:
            await self._check_disk_health()
        await self._check_system_logs()
        if self.config.update_check_enabled:
            await self._check_updates()

    def get_health_report(self) -> SystemHealthReport:
        """Get comprehensive health report."""
        # Determine overall status
        overall = HealthStatus.HEALTHY
        for event in self._events:
            if event.severity == HealthStatus.CRITICAL and not event.resolved:
                overall = HealthStatus.CRITICAL
                break
            elif event.severity == HealthStatus.WARNING and not event.resolved:
                overall = HealthStatus.WARNING

        for disk in self._disks.values():
            if disk.health_status == HealthStatus.CRITICAL:
                overall = HealthStatus.CRITICAL
                break
            elif disk.health_status == HealthStatus.WARNING:
                overall = HealthStatus.WARNING

        # Calculate performance score
        perf_score = 100.0
        perf_score -= self._error_count * 5
        perf_score -= self._warning_count * 2
        for disk in self._disks.values():
            if disk.reallocated_sectors > 0:
                perf_score -= min(disk.reallocated_sectors * 0.1, 10)
        perf_score = max(0, perf_score)

        return SystemHealthReport(
            timestamp=datetime.now(),
            overall_status=overall,
            services=list(self._services.values()),
            disks=list(self._disks.values()),
            events=list(self._events)[-50:],  # Last 50 events
            updates_pending=self._update_status.get("pending", 0),
            security_issues=0,  # Would integrate with security scanner
            performance_score=perf_score
        )

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def warning_count(self) -> int:
        return self._warning_count

    async def shutdown(self):
        """Shutdown the health monitor."""
        self._running = False
        for task in [self._monitor_task, self._full_check_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
