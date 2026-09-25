"""
Core configuration management for AIO Bot.
Supports YAML/JSON config files with environment variable overrides.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MonitoringConfig:
    """System monitoring configuration."""
    enabled: bool = True
    interval_seconds: int = 30
    cpu_threshold_percent: float = 80.0
    memory_threshold_percent: float = 85.0
    disk_threshold_percent: float = 90.0
    network_monitor_enabled: bool = True
    gpu_monitor_enabled: bool = True
    process_monitor_enabled: bool = True
    log_monitor_enabled: bool = True
    smart_disk_check_enabled: bool = True


@dataclass
class LearningConfig:
    """AI learning and habit detection configuration."""
    enabled: bool = True
    model_update_interval_hours: int = 24
    habit_detection_window_days: int = 14
    min_pattern_confidence: float = 0.75
    auto_schedule_enabled: bool = True
    prediction_horizon_days: int = 7
    privacy_mode: str = "local_only"  # local_only, anonymized, cloud_sync


@dataclass
class DataManagementConfig:
    """Data management and file organization configuration."""
    enabled: bool = True
    auto_organize_enabled: bool = True
    organize_interval_hours: int = 6
    duplicate_detection_enabled: bool = True
    cleanup_temp_files_enabled: bool = True
    cleanup_interval_hours: int = 12
    max_temp_file_age_days: int = 7
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    backup_retention_days: int = 30
    watch_directories: list = field(default_factory=list)


@dataclass
class HealthConfig:
    """System health monitoring configuration."""
    enabled: bool = True
    check_interval_minutes: int = 15
    windows_event_log_enabled: bool = True
    macos_unified_log_enabled: bool = True
    linux_journal_enabled: bool = True
    smart_monitoring_enabled: bool = True
    service_monitor_enabled: bool = True
    update_check_enabled: bool = True
    critical_alert_threshold: int = 3


@dataclass
class AutomationConfig:
    """Auto-healing and automation configuration."""
    enabled: bool = True
    auto_restart_failed_services: bool = True
    auto_cleanup_enabled: bool = True
    auto_update_enabled: bool = True
    update_check_interval_hours: int = 6
    maintenance_window_start: str = "02:00"
    maintenance_window_end: str = "04:00"
    max_auto_fix_attempts: int = 3
    notification_on_auto_fix: bool = True


@dataclass
class SecurityConfig:
    """Security and privacy configuration."""
    local_first: bool = True
    encrypt_local_data: bool = True
    require_auth_for_gui: bool = True
    api_key_rotation_days: int = 90
    audit_log_enabled: bool = True
    telemetry_enabled: bool = False
    allowed_network_access: list = field(default_factory=lambda: ["localhost"])


@dataclass
class GUIConfig:
    """GUI configuration."""
    enabled: bool = True
    theme: str = "system"  # light, dark, system
    language: str = "en"
    start_minimized: bool = True
    show_tray_icon: bool = True
    auto_start: bool = True
    dashboard_refresh_seconds: int = 10
    notifications_enabled: bool = True


@dataclass
class AppConfig:
    """Main application configuration."""
    app_name: str = "AIO Bot"
    version: str = "2.0.0"
    data_dir: str = ""
    log_level: str = "INFO"
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)
    data_mgmt: DataManagementConfig = field(default_factory=DataManagementConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    automation: AutomationConfig = field(default_factory=AutomationConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    gui: GUIConfig = field(default_factory=GUIConfig)

    def __post_init__(self):
        if not self.data_dir:
            if os.name == 'nt':
                self.data_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'AIOBot')
            else:
                self.data_dir = os.path.join(os.path.expanduser('~'), '.aiobot')
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)


class ConfigManager:
    """Manages application configuration with file persistence."""

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = AppConfig()
        self.load()

    def _get_default_config_path(self) -> str:
        if os.name == 'nt':
            base = os.environ.get('LOCALAPPDATA', '')
        else:
            base = os.path.join(os.path.expanduser('~'), '.config')
        return os.path.join(base, 'AIOBot', 'config.json')

    def load(self) -> AppConfig:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path) as f:
                    data = json.load(f)
                self.config = self._dict_to_config(data)
        except Exception as e:
            print(f"Warning: Failed to load config: {e}")
        return self.config

    def save(self) -> bool:
        """Save configuration to file."""
        try:
            Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self._config_to_dict(self.config), f, indent=2)
            return True
        except Exception as e:
            print(f"Error: Failed to save config: {e}")
            return False

    def _config_to_dict(self, config: AppConfig) -> dict[str, Any]:
        return asdict(config)

    def _dict_to_config(self, data: dict[str, Any]) -> AppConfig:
        config = AppConfig()
        for key, value in data.items():
            if hasattr(config, key):
                if key in ['monitoring', 'learning', 'data_mgmt', 'health', 'automation', 'security', 'gui']:
                    sub_config = getattr(config, key)
                    for sub_key, sub_value in value.items():
                        if hasattr(sub_config, sub_key):
                            setattr(sub_config, sub_key, sub_value)
                else:
                    setattr(config, key, value)
        return config

    def get(self, path: str, default: Any = None) -> Any:
        """Get config value by dot notation path (e.g., 'monitoring.interval_seconds')."""
        keys = path.split('.')
        obj = self.config
        for key in keys:
            if hasattr(obj, key):
                obj = getattr(obj, key)
            else:
                return default
        return obj

    def set(self, path: str, value: Any) -> bool:
        """Set config value by dot notation path."""
        keys = path.split('.')
        obj = self.config
        for key in keys[:-1]:
            if hasattr(obj, key):
                obj = getattr(obj, key)
            else:
                return False
        if hasattr(obj, keys[-1]):
            setattr(obj, keys[-1], value)
            return self.save()
        return False
