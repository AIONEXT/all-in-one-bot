"""
AIO Bot Security Package - Local-first privacy, encryption, and permission management.
"""

import asyncio
import hashlib
import json
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class Permission(Enum):
    """Permission levels."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class DataClassification(Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    local_first: bool = True
    encrypt_at_rest: bool = True
    encrypt_in_transit: bool = True
    require_auth: bool = True
    session_timeout_minutes: int = 60
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 15
    audit_log_enabled: bool = True
    telemetry_enabled: bool = False
    allowed_networks: list[str] = field(default_factory=lambda: ["127.0.0.1", "::1"])
    api_key_rotation_days: int = 90


@dataclass
class AuditEvent:
    """Audit log event."""
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = ""
    user: str = "system"
    action: str = ""
    resource: str = ""
    result: str = "success"  # success, failure, denied
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str = "local"
    severity: str = "info"  # info, warning, critical


class SecurityManager:
    """
    Security and privacy manager for AIO Bot.
    Handles encryption, authentication, authorization, and audit logging.
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("AIOBot.SecurityManager")
        self._policy = SecurityPolicy()
        self._encryption_key: bytes | None = None
        self._fernet: Any | None = None
        self._audit_log: list[AuditEvent] = []
        self._failed_attempts: dict[str, list[datetime]] = {}
        self._locked_out: dict[str, datetime] = {}
        self._api_keys: dict[str, dict[str, Any]] = {}
        self._permissions: dict[str, set[Permission]] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize security manager."""
        self.logger.info("Initializing Security Manager")

        if not CRYPTO_AVAILABLE:
            self.logger.warning("Cryptography library not available - encryption disabled")

        # Load or generate encryption key
        await self._setup_encryption()

        # Load policy from config
        self._load_policy()

        # Load API keys
        await self._load_api_keys()

        # Setup audit log
        self._audit_log_path = Path(self.config.data_dir) / 'audit.log' if hasattr(self.config, 'data_dir') else Path.home() / '.aiobot' / 'audit.log'
        self._audit_log_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialized = True
        self.logger.info("Security Manager initialized")

    def _load_policy(self):
        """Load security policy from config."""
        if hasattr(self.config, 'security'):
            sec = self.config.security
            self._policy.local_first = getattr(sec, 'local_first', True)
            self._policy.encrypt_at_rest = getattr(sec, 'encrypt_local_data', True)
            self._policy.require_auth = getattr(sec, 'require_auth_for_gui', True)
            self._policy.audit_log_enabled = getattr(sec, 'audit_log_enabled', True)
            self._policy.telemetry_enabled = getattr(sec, 'telemetry_enabled', False)
            self._policy.api_key_rotation_days = getattr(sec, 'api_key_rotation_days', 90)

    async def _setup_encryption(self):
        """Setup encryption key."""
        if not CRYPTO_AVAILABLE:
            return

        key_file = Path(self.config.data_dir) / '.encryption_key' if hasattr(self.config, 'data_dir') else Path.home() / '.aiobot' / '.encryption_key'
        key_file.parent.mkdir(parents=True, exist_ok=True)

        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    self._encryption_key = f.read()
            except Exception as e:
                self.logger.error("Failed to load encryption key: %s", e)
                self._encryption_key = self._generate_key()
                await self._save_encryption_key(key_file)
        else:
            self._encryption_key = self._generate_key()
            await self._save_encryption_key(key_file)

        if self._encryption_key:
            self._fernet = Fernet(self._encryption_key)

    def _generate_key(self) -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()

    async def _save_encryption_key(self, key_file: Path):
        """Save encryption key to file."""
        try:
            with open(key_file, 'wb') as f:
                f.write(self._encryption_key)
            # Restrict permissions (Unix only)
            if hasattr(os, 'chmod'):
                os.chmod(key_file, 0o600)
        except Exception as e:
            self.logger.error("Failed to save encryption key: %s", e)

    async def _load_api_keys(self):
        """Load API keys from storage."""
        key_file = Path(self.config.data_dir) / 'api_keys.json' if hasattr(self.config, 'data_dir') else Path.home() / '.aiobot' / 'api_keys.json'

        if key_file.exists():
            try:
                with open(key_file) as f:
                    self._api_keys = json.load(f)
            except Exception as e:
                self.logger.warning("Failed to load API keys: %s", e)

    async def _save_api_keys(self):
        """Save API keys to storage."""
        key_file = Path(self.config.data_dir) / 'api_keys.json' if hasattr(self.config, 'data_dir') else Path.home() / '.aiobot' / 'api_keys.json'

        try:
            with open(key_file, 'w') as f:
                json.dump(self._api_keys, f, indent=2, default=str)
        except Exception as e:
            self.logger.error("Failed to save API keys: %s", e)

    # ============================================================
    # Encryption
    # ============================================================

    def encrypt(self, data: str) -> str:
        """Encrypt a string."""
        if not self._fernet:
            return data
        try:
            return self._fernet.encrypt(data.encode()).decode()
        except Exception as e:
            self.logger.error("Encryption failed: %s", e)
            return data

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt a string."""
        if not self._fernet:
            return encrypted_data
        try:
            return self._fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            self.logger.error("Decryption failed: %s", e)
            return encrypted_data

    def encrypt_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Encrypt sensitive fields in a dictionary."""
        sensitive_keys = {'password', 'token', 'secret', 'key', 'api_key', 'auth'}
        result = {}
        for k, v in data.items():
            if any(sk in k.lower() for sk in sensitive_keys) and isinstance(v, str):
                result[k] = self.encrypt(v)
            elif isinstance(v, dict):
                result[k] = self.encrypt_dict(v)
            elif isinstance(v, list):
                result[k] = [self.encrypt_dict(item) if isinstance(item, dict) else item for item in v]
            else:
                result[k] = v
        return result

    def decrypt_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Decrypt sensitive fields in a dictionary."""
        sensitive_keys = {'password', 'token', 'secret', 'key', 'api_key', 'auth'}
        result = {}
        for k, v in data.items():
            if any(sk in k.lower() for sk in sensitive_keys) and isinstance(v, str):
                result[k] = self.decrypt(v)
            elif isinstance(v, dict):
                result[k] = self.decrypt_dict(v)
            elif isinstance(v, list):
                result[k] = [self.decrypt_dict(item) if isinstance(item, dict) else item for item in v]
            else:
                result[k] = v
        return result

    # ============================================================
    # API Key Management
    # ============================================================

    def generate_api_key(self, name: str, permissions: list[Permission] = None) -> str:
        """Generate a new API key."""
        key = f"aio_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        self._api_keys[key_hash] = {
            "name": name,
            "key_prefix": key[:12] + "...",
            "permissions": [p.value for p in (permissions or [Permission.READ])],
            "created": datetime.now().isoformat(),
            "last_used": None,
            "expires": (datetime.now() + timedelta(days=self._policy.api_key_rotation_days)).isoformat(),
            "active": True,
        }

        asyncio.create_task(self._save_api_keys())
        self._audit("api_key_created", "system", "create", f"api_key:{name}", "success", {"name": name})

        return key

    def validate_api_key(self, key: str) -> dict[str, Any] | None:
        """Validate an API key and return its info."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_info = self._api_keys.get(key_hash)

        if not key_info:
            self._audit("api_key_invalid", "unknown", "validate", "api_key", "failure", {})
            return None

        if not key_info.get("active", False):
            self._audit("api_key_inactive", key_info.get("name", "unknown"), "validate", "api_key", "denied", {})
            return None

        expires = datetime.fromisoformat(key_info["expires"])
        if datetime.now() > expires:
            self._audit("api_key_expired", key_info.get("name", "unknown"), "validate", "api_key", "denied", {})
            return None

        # Update last used
        key_info["last_used"] = datetime.now().isoformat()
        asyncio.create_task(self._save_api_keys())

        return key_info

    def revoke_api_key(self, key: str) -> bool:
        """Revoke an API key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        if key_hash in self._api_keys:
            name = self._api_keys[key_hash].get("name", "unknown")
            del self._api_keys[key_hash]
            asyncio.create_task(self._save_api_keys())
            self._audit("api_key_revoked", "system", "revoke", f"api_key:{name}", "success", {})
            return True
        return False

    def list_api_keys(self) -> list[dict[str, Any]]:
        """List all API keys (without full key)."""
        return [
            {
                "name": info["name"],
                "prefix": info["key_prefix"],
                "permissions": info["permissions"],
                "created": info["created"],
                "last_used": info["last_used"],
                "expires": info["expires"],
                "active": info["active"],
            }
            for info in self._api_keys.values()
        ]

    # ============================================================
    # Authentication & Authorization
    # ============================================================

    def check_permission(self, user: str, permission: Permission) -> bool:
        """Check if user has a permission."""
        user_perms = self._permissions.get(user, set())
        return permission in user_perms or Permission.ADMIN in user_perms

    def grant_permission(self, user: str, permission: Permission):
        """Grant a permission to a user."""
        if user not in self._permissions:
            self._permissions[user] = set()
        self._permissions[user].add(permission)

    def revoke_permission(self, user: str, permission: Permission):
        """Revoke a permission from a user."""
        if user in self._permissions:
            self._permissions[user].discard(permission)

    def check_rate_limit(self, identifier: str, max_attempts: int = None, window_minutes: int = 15) -> bool:
        """Check rate limiting for an identifier."""
        max_attempts = max_attempts or self._policy.max_failed_attempts
        now = datetime.now()
        cutoff = now - timedelta(minutes=window_minutes)

        if identifier not in self._failed_attempts:
            self._failed_attempts[identifier] = []

        # Clean old attempts
        self._failed_attempts[identifier] = [
            t for t in self._failed_attempts[identifier] if t > cutoff
        ]

        # Check lockout
        if identifier in self._locked_out:
            lockout_until = self._locked_out[identifier]
            if now < lockout_until:
                return False
            else:
                del self._locked_out[identifier]

        return len(self._failed_attempts[identifier]) < max_attempts

    def record_failed_attempt(self, identifier: str):
        """Record a failed authentication attempt."""
        now = datetime.now()
        if identifier not in self._failed_attempts:
            self._failed_attempts[identifier] = []
        self._failed_attempts[identifier].append(now)

        # Check if should lockout
        if len(self._failed_attempts[identifier]) >= self._policy.max_failed_attempts:
            self._locked_out[identifier] = now + timedelta(minutes=self._policy.lockout_duration_minutes)
            self._audit("account_locked", identifier, "auth", "login", "denied", {"reason": "max_attempts_exceeded"})

    def record_successful_attempt(self, identifier: str):
        """Record a successful authentication attempt."""
        if identifier in self._failed_attempts:
            del self._failed_attempts[identifier]
        if identifier in self._locked_out:
            del self._locked_out[identifier]

    # ============================================================
    # Audit Logging
    # ============================================================

    def _audit(self, event_type: str, user: str, action: str, resource: str,
               result: str, details: dict[str, Any] = None, severity: str = "info"):
        """Record an audit event."""
        if not self._policy.audit_log_enabled:
            return

        event = AuditEvent(
            event_type=event_type,
            user=user,
            action=action,
            resource=resource,
            result=result,
            details=details or {},
            severity=severity,
        )

        self._audit_log.append(event)

        # Keep only recent events in memory
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]

        # Write to file
        self._write_audit_event(event)

    def _write_audit_event(self, event: AuditEvent):
        """Write audit event to file."""
        try:
            with open(self._audit_log_path, 'a') as f:
                f.write(json.dumps({
                    "timestamp": event.timestamp.isoformat(),
                    "event_type": event.event_type,
                    "user": event.user,
                    "action": event.action,
                    "resource": event.resource,
                    "result": event.result,
                    "details": event.details,
                    "ip_address": event.ip_address,
                    "severity": event.severity,
                }) + '\n')
        except Exception as e:
            self.logger.error("Failed to write audit log: %s", e)

    def get_audit_log(self, limit: int = 100, event_type: str = None,
                      user: str = None, since: datetime = None) -> list[AuditEvent]:
        """Get audit log entries."""
        events = self._audit_log

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if user:
            events = [e for e in events if e.user == user]
        if since:
            events = [e for e in events if e.timestamp >= since]

        return events[-limit:]

    # ============================================================
    # Data Classification & Handling
    # ============================================================

    def classify_data(self, data: dict[str, Any]) -> DataClassification:
        """Classify data sensitivity."""
        # Check for sensitive patterns
        sensitive_patterns = {
            DataClassification.RESTRICTED: ['password', 'secret', 'private_key', 'ssn', 'credit_card'],
            DataClassification.CONFIDENTIAL: ['token', 'api_key', 'auth', 'credential', 'personal'],
            DataClassification.INTERNAL: ['email', 'name', 'address', 'phone', 'ip'],
        }

        data_str = json.dumps(data, default=str).lower()

        for classification, patterns in sensitive_patterns.items():
            if any(p in data_str for p in patterns):
                return classification

        return DataClassification.PUBLIC

    def sanitize_for_logging(self, data: dict[str, Any]) -> dict[str, Any]:
        """Sanitize data for safe logging."""
        classification = self.classify_data(data)

        if classification in [DataClassification.RESTRICTED, DataClassification.CONFIDENTIAL]:
            # Return only non-sensitive keys
            safe_keys = {'id', 'type', 'status', 'timestamp', 'count', 'size'}
            return {k: v for k, v in data.items() if k in safe_keys}

        return data

    # ============================================================
    # Secure Storage
    # ============================================================

    async def secure_store(self, key: str, value: str, classification: DataClassification = DataClassification.INTERNAL) -> bool:
        """Securely store a value."""
        try:
            storage_dir = Path(self.config.data_dir) / 'secure_storage' if hasattr(self.config, 'data_dir') else Path.home() / '.aiobot' / 'secure_storage'
            storage_dir.mkdir(parents=True, exist_ok=True)

            # Encrypt if needed
            if self._policy.encrypt_at_rest and classification in [DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED]:
                value = self.encrypt(value)

            # Store with metadata
            metadata = {
                "key": key,
                "classification": classification.value,
                "encrypted": self._policy.encrypt_at_rest and classification in [DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED],
                "created": datetime.now().isoformat(),
            }

            # Use hashed filename
            filename = hashlib.sha256(key.encode()).hexdigest()[:32]
            filepath = storage_dir / filename

            with open(filepath, 'w') as f:
                json.dump({"metadata": metadata, "value": value}, f)

            # Restrict permissions
            if hasattr(os, 'chmod'):
                os.chmod(filepath, 0o600)

            return True
        except Exception as e:
            self.logger.error("Secure store failed: %s", e)
            return False

    async def secure_retrieve(self, key: str) -> str | None:
        """Retrieve a securely stored value."""
        try:
            storage_dir = Path(self.config.data_dir) / 'secure_storage' if hasattr(self.config, 'data_dir') else Path.home() / '.aiobot' / 'secure_storage'
            filename = hashlib.sha256(key.encode()).hexdigest()[:32]
            filepath = storage_dir / filename

            if not filepath.exists():
                return None

            with open(filepath) as f:
                data = json.load(f)

            value = data.get("value", "")
            metadata = data.get("metadata", {})

            # Decrypt if needed
            if metadata.get("encrypted", False):
                value = self.decrypt(value)

            return value
        except Exception as e:
            self.logger.error("Secure retrieve failed: %s", e)
            return None

    async def secure_delete(self, key: str) -> bool:
        """Securely delete a stored value."""
        try:
            storage_dir = Path(self.config.data_dir) / 'secure_storage' if hasattr(self.config, 'data_dir') else Path.home() / '.aiobot' / 'secure_storage'
            filename = hashlib.sha256(key.encode()).hexdigest()[:32]
            filepath = storage_dir / filename

            if filepath.exists():
                # Overwrite before delete (basic)
                with open(filepath, 'wb') as f:
                    f.write(secrets.token_bytes(filepath.stat().st_size))
                filepath.unlink()
                return True
            return False
        except Exception as e:
            self.logger.error("Secure delete failed: %s", e)
            return False

    # ============================================================
    # Network Security
    # ============================================================

    def is_allowed_network(self, ip: str) -> bool:
        """Check if an IP is in allowed networks."""
        import ipaddress

        try:
            client_ip = ipaddress.ip_address(ip)
            for network_str in self._policy.allowed_networks:
                network = ipaddress.ip_network(network_str, strict=False)
                if client_ip in network:
                    return True
            return False
        except Exception:
            return False

    def add_allowed_network(self, network: str):
        """Add an allowed network."""
        if network not in self._policy.allowed_networks:
            self._policy.allowed_networks.append(network)

    # ============================================================
    # Status & Health
    # ============================================================

    def get_security_status(self) -> dict[str, Any]:
        """Get security status summary."""
        return {
            "policy": {
                "local_first": self._policy.local_first,
                "encrypt_at_rest": self._policy.encrypt_at_rest,
                "require_auth": self._policy.require_auth,
                "audit_log_enabled": self._policy.audit_log_enabled,
                "telemetry_enabled": self._policy.telemetry_enabled,
            },
            "encryption": {
                "available": CRYPTO_AVAILABLE,
                "enabled": self._fernet is not None,
            },
            "api_keys": {
                "total": len(self._api_keys),
                "active": sum(1 for k in self._api_keys.values() if k.get("active", False)),
            },
            "audit_log": {
                "entries": len(self._audit_log),
                "recent_critical": sum(1 for e in self._audit_log[-100:] if e.severity == "critical"),
            },
            "rate_limiting": {
                "locked_out": len(self._locked_out),
                "tracked_identifiers": len(self._failed_attempts),
            },
        }

    async def rotate_api_keys(self):
        """Rotate expired API keys."""
        now = datetime.now()
        rotated = 0

        for key_hash, info in list(self._api_keys.items()):
            expires = datetime.fromisoformat(info["expires"])
            if now > expires and info.get("active", False):
                info["active"] = False
                rotated += 1
                self._audit("api_key_auto_rotated", info.get("name", "unknown"), "rotate", "api_key", "success", {})

        if rotated > 0:
            await self._save_api_keys()
            self.logger.info("Rotated %d expired API keys", rotated)

        return rotated

    async def shutdown(self):
        """Shutdown security manager."""
        await self._save_api_keys()
        self.logger.info("Security Manager shutdown")
