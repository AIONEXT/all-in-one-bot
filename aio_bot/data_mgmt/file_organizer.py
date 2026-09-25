"""
File Organization and Data Management Module.
Smart file categorization, duplicate detection, cleanup, and backup automation.
"""

import asyncio
import hashlib
import json
import logging
import mimetypes
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class FileCategory(Enum):
    """File categories for organization."""
    DOCUMENTS = "documents"
    IMAGES = "images"
    VIDEOS = "videos"
    AUDIO = "audio"
    ARCHIVES = "archives"
    CODE = "code"
    EXECUTABLES = "executables"
    SPREADSHEETS = "spreadsheets"
    PRESENTATIONS = "presentations"
    DATABASES = "databases"
    FONTS = "fonts"
    TEMP = "temp"
    OTHER = "other"


class CleanupAction(Enum):
    """Actions for file cleanup."""
    DELETE = "delete"
    MOVE_TO_TRASH = "move_to_trash"
    ARCHIVE = "archive"
    COMPRESS = "compress"
    DEDUPLICATE = "deduplicate"


@dataclass
class FileInfo:
    """File information."""
    path: Path
    name: str
    extension: str
    size: int
    category: FileCategory
    mime_type: str
    created: datetime
    modified: datetime
    accessed: datetime
    hash: str = ""
    is_duplicate: bool = False
    duplicate_of: Path | None = None


@dataclass
class DuplicateGroup:
    """Group of duplicate files."""
    hash: str
    files: list[FileInfo]
    size: int
    count: int
    keep_path: Path | None = None


@dataclass
class CleanupPlan:
    """Plan for cleaning up files."""
    action: CleanupAction
    files: list[FileInfo]
    target_dir: Path | None = None
    reason: str = ""
    estimated_space_saved: int = 0


@dataclass
class OrganizeRule:
    """Rule for file organization."""
    category: FileCategory
    extensions: list[str]
    target_subdir: str
    min_size: int = 0
    max_size: int = 0
    min_age_days: int = 0


class FileOrganizer:
    """
    Smart file organizer with categorization, duplicate detection, and cleanup.
    """

    # Default organization rules
    DEFAULT_RULES = [
        OrganizeRule(FileCategory.DOCUMENTS, ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.md'], 'Documents'),
        OrganizeRule(FileCategory.IMAGES, ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.heic'], 'Images'),
        OrganizeRule(FileCategory.VIDEOS, ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'], 'Videos'),
        OrganizeRule(FileCategory.AUDIO, ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'], 'Audio'),
        OrganizeRule(FileCategory.ARCHIVES, ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'], 'Archives'),
        OrganizeRule(FileCategory.CODE, ['.py', '.js', '.ts', '.html', '.css', '.cpp', '.c', '.java', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.json', '.xml', '.yaml', '.yml'], 'Code'),
        OrganizeRule(FileCategory.EXECUTABLES, ['.exe', '.msi', '.dmg', '.app', '.apk', '.deb', '.rpm', '.appimage'], 'Executables'),
        OrganizeRule(FileCategory.SPREADSHEETS, ['.xls', '.xlsx', '.csv', '.ods', '.numbers'], 'Spreadsheets'),
        OrganizeRule(FileCategory.PRESENTATIONS, ['.ppt', '.pptx', '.odp', '.key'], 'Presentations'),
        OrganizeRule(FileCategory.DATABASES, ['.db', '.sqlite', '.sql', '.mdb', '.accdb'], 'Databases'),
        OrganizeRule(FileCategory.FONTS, ['.ttf', '.otf', '.woff', '.woff2', '.eot'], 'Fonts'),
        OrganizeRule(FileCategory.TEMP, ['.tmp', '.temp', '.log', '.bak', '.swp', '~'], 'Temp', min_age_days=1),
    ]

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("AIOBot.FileOrganizer")
        self._running = False
        self._organize_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None
        self._backup_task: asyncio.Task | None = None

        # Rules
        self._rules: list[OrganizeRule] = self.DEFAULT_RULES.copy()

        # Watched directories
        self._watch_dirs: list[Path] = []
        for d in config.watch_directories:
            p = Path(d).expanduser()
            if p.exists():
                self._watch_dirs.append(p)

        # Default to common directories if none specified
        if not self._watch_dirs:
            home = Path.home()
            defaults = [
                home / 'Downloads',
                home / 'Desktop',
                home / 'Documents',
            ]
            for d in defaults:
                if d.exists():
                    self._watch_dirs.append(d)

        # State
        self._file_cache: dict[str, FileInfo] = {}
        self._duplicate_groups: list[DuplicateGroup] = []
        self._cleanup_plans: list[CleanupPlan] = []
        self._last_organize: datetime | None = None
        self._last_cleanup: datetime | None = None
        self._last_backup: datetime | None = None

        # Trash directory
        self._trash_dir = Path(config.data_dir) / 'trash' if hasattr(config, 'data_dir') else Path.home() / '.aiobot' / 'trash'
        self._trash_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize the file organizer."""
        self.logger.info("Initializing File Organizer")
        self.logger.info("Watching %d directories", len(self._watch_dirs))
        for d in self._watch_dirs:
            self.logger.info("  - %s", d)
        self.logger.info("File Organizer initialized")

    async def run(self):
        """Main file organizer loop."""
        self._running = True
        self.logger.info("File Organizer started")

        # Initial scan
        await self.scan_and_organize()

        while self._running:
            try:
                now = datetime.now()

                # Periodic organization
                if self.config.auto_organize_enabled and self._last_organize:
                    if (now - self._last_organize).total_seconds() >= self.config.organize_interval_hours * 3600:
                        await self.scan_and_organize()

                # Periodic cleanup
                if self.config.cleanup_temp_files_enabled and self._last_cleanup:
                    if (now - self._last_cleanup).total_seconds() >= self.config.cleanup_interval_hours * 3600:
                        await self.cleanup_temp_files()

                # Periodic backup
                if self.config.backup_enabled and self._last_backup:
                    if (now - self._last_backup).total_seconds() >= self.config.backup_interval_hours * 3600:
                        await self.run_backup()

                await asyncio.sleep(300)  # Check every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("File organizer error: %s", e, exc_info=True)
                await asyncio.sleep(60)

        self.logger.info("File Organizer stopped")

    async def scan_and_organize(self):
        """Scan watched directories and organize files."""
        self.logger.info("Starting file scan and organization")
        self._last_organize = datetime.now()

        all_files = []
        for watch_dir in self._watch_dirs:
            files = await self._scan_directory(watch_dir)
            all_files.extend(files)

        self.logger.info("Scanned %d files", len(all_files))

        # Categorize files
        categorized = self._categorize_files(all_files)

        # Detect duplicates
        if self.config.duplicate_detection_enabled:
            await self._detect_duplicates(all_files)

        # Generate cleanup plans
        await self._generate_cleanup_plans(all_files)

        # Auto-organize if enabled
        if self.config.auto_organize_enabled:
            await self._apply_organization(categorized)

        self.logger.info("File organization complete. Duplicates: %d, Cleanup plans: %d",
                        len(self._duplicate_groups), len(self._cleanup_plans))

    async def _scan_directory(self, directory: Path) -> list[FileInfo]:
        """Scan a directory for files."""
        files = []
        try:
            for entry in directory.rglob('*'):
                if entry.is_file() and not entry.is_symlink():
                    # Skip hidden files and system directories
                    if any(part.startswith('.') for part in entry.parts):
                        continue
                    if any(skip in str(entry) for skip in ['__pycache__', '.git', 'node_modules', 'venv', '.venv']):
                        continue

                    try:
                        stat = entry.stat()
                        file_info = FileInfo(
                            path=entry,
                            name=entry.name,
                            extension=entry.suffix.lower(),
                            size=stat.st_size,
                            category=self._categorize_file(entry),
                            mime_type=mimetypes.guess_type(str(entry))[0] or 'application/octet-stream',
                            created=datetime.fromtimestamp(stat.st_ctime),
                            modified=datetime.fromtimestamp(stat.st_mtime),
                            accessed=datetime.fromtimestamp(stat.st_atime),
                        )
                        files.append(file_info)
                    except (OSError, PermissionError):
                        continue
        except Exception as e:
            self.logger.warning("Error scanning %s: %s", directory, e)

        return files

    def _categorize_file(self, path: Path) -> FileCategory:
        """Categorize a file by extension."""
        ext = path.suffix.lower()
        for rule in self._rules:
            if ext in rule.extensions:
                return rule.category
        return FileCategory.OTHER

    def _categorize_files(self, files: list[FileInfo]) -> dict[FileCategory, list[FileInfo]]:
        """Group files by category."""
        categorized = defaultdict(list)
        for f in files:
            categorized[f.category].append(f)
        return categorized

    async def _detect_duplicates(self, files: list[FileInfo]):
        """Detect duplicate files by content hash."""
        self.logger.info("Detecting duplicates...")

        # Group by size first (fast filter)
        size_groups = defaultdict(list)
        for f in files:
            size_groups[f.size].append(f)

        # Hash files with same size
        hash_groups = defaultdict(list)
        for size, group in size_groups.items():
            if len(group) > 1:
                for f in group:
                    try:
                        f.hash = await self._compute_hash(f.path)
                        hash_groups[f.hash].append(f)
                    except Exception as e:
                        self.logger.debug("Hash failed for %s: %s", f.path, e)

        # Create duplicate groups
        self._duplicate_groups = []
        for hash_val, group in hash_groups.items():
            if len(group) > 1:
                # Keep the oldest/original (first by creation time)
                group.sort(key=lambda f: f.created)
                keep = group[0]
                for dup in group[1:]:
                    dup.is_duplicate = True
                    dup.duplicate_of = keep.path

                self._duplicate_groups.append(DuplicateGroup(
                    hash=hash_val,
                    files=group,
                    size=size,
                    count=len(group),
                    keep_path=keep.path
                ))

        self.logger.info("Found %d duplicate groups", len(self._duplicate_groups))

    async def _compute_hash(self, path: Path, algorithm: str = 'sha256') -> str:
        """Compute file hash."""
        hasher = hashlib.new(algorithm)
        try:
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
        except Exception:
            return ""
        return hasher.hexdigest()

    async def _generate_cleanup_plans(self, files: list[FileInfo]):
        """Generate cleanup plans for temp files, old files, etc."""
        self._cleanup_plans = []
        now = datetime.now()

        # Temp files cleanup
        if self.config.cleanup_temp_files_enabled:
            temp_files = [f for f in files if f.category == FileCategory.TEMP]
            old_temp = [f for f in temp_files if (now - f.modified).days >= self.config.max_temp_file_age_days]
            if old_temp:
                self._cleanup_plans.append(CleanupPlan(
                    action=CleanupAction.MOVE_TO_TRASH,
                    files=old_temp,
                    reason=f"Temp files older than {self.config.max_temp_file_age_days} days",
                    estimated_space_saved=sum(f.size for f in old_temp)
                ))

        # Duplicate files cleanup
        for group in self._duplicate_groups:
            duplicates = [f for f in group.files if f.is_duplicate]
            if duplicates:
                self._cleanup_plans.append(CleanupPlan(
                    action=CleanupAction.DELETE,
                    files=duplicates,
                    reason=f"Duplicate files (keeping {group.keep_path.name})",
                    estimated_space_saved=sum(f.size for f in duplicates)
                ))

        # Large old files
        large_files = [f for f in files if f.size > 100 * 1024 * 1024 and (now - f.accessed).days > 90]
        if large_files:
            archive_dir = Path(self.config.data_dir) / 'archive' if hasattr(self.config, 'data_dir') else Path.home() / '.aiobot' / 'archive'
            self._cleanup_plans.append(CleanupPlan(
                action=CleanupAction.ARCHIVE,
                files=large_files,
                target_dir=archive_dir,
                reason="Large files not accessed in 90+ days",
                estimated_space_saved=sum(f.size for f in large_files)
            ))

    async def _apply_organization(self, categorized: dict[FileCategory, list[FileInfo]]):
        """Apply organization rules to files."""
        for category, files in categorized.items():
            if not files:
                continue

            # Find rule for this category
            rule = next((r for r in self._rules if r.category == category), None)
            if not rule:
                continue

            for watch_dir in self._watch_dirs:
                target_dir = watch_dir / rule.target_subdir
                target_dir.mkdir(exist_ok=True)

                # Find files in this watch_dir that belong to this category
                category_files = [f for f in files if f.path.parent == watch_dir or watch_dir in f.path.parents]

                for file_info in category_files:
                    if file_info.path.parent == target_dir:
                        continue  # Already organized

                    target_path = target_dir / file_info.name
                    if target_path.exists():
                        # Handle name conflict
                        target_path = self._resolve_name_conflict(target_dir, file_info.name)

                    try:
                        shutil.move(str(file_info.path), str(target_path))
                        self.logger.info("Moved %s -> %s", file_info.path, target_path)
                        file_info.path = target_path
                    except Exception as e:
                        self.logger.warning("Failed to move %s: %s", file_info.path, e)

    def _resolve_name_conflict(self, target_dir: Path, name: str) -> Path:
        """Resolve filename conflicts by adding suffix."""
        stem = Path(name).stem
        suffix = Path(name).suffix
        counter = 1
        new_name = f"{stem}_{counter}{suffix}"
        while (target_dir / new_name).exists():
            counter += 1
            new_name = f"{stem}_{counter}{suffix}"
        return target_dir / new_name

    async def cleanup_temp_files(self):
        """Execute temp file cleanup."""
        self.logger.info("Running temp file cleanup")
        self._last_cleanup = datetime.now()

        # Execute cleanup plans for temp files
        temp_plans = [p for p in self._cleanup_plans if p.reason.startswith("Temp files")]
        for plan in temp_plans:
            await self._execute_cleanup_plan(plan)

    async def _execute_cleanup_plan(self, plan: CleanupPlan):
        """Execute a cleanup plan."""
        self.logger.info("Executing cleanup: %s (%d files, %.2f MB)",
                        plan.reason, len(plan.files), plan.estimated_space_saved / (1024*1024))

        for file_info in plan.files:
            try:
                if plan.action == CleanupAction.DELETE:
                    file_info.path.unlink()
                elif plan.action == CleanupAction.MOVE_TO_TRASH:
                    trash_path = self._trash_dir / file_info.name
                    trash_path = self._resolve_name_conflict(self._trash_dir, file_info.name)
                    shutil.move(str(file_info.path), str(trash_path))
                elif plan.action == CleanupAction.ARCHIVE and plan.target_dir:
                    plan.target_dir.mkdir(parents=True, exist_ok=True)
                    archive_path = plan.target_dir / file_info.name
                    archive_path = self._resolve_name_conflict(plan.target_dir, file_info.name)
                    shutil.move(str(file_info.path), str(archive_path))
            except Exception as e:
                self.logger.warning("Failed to clean %s: %s", file_info.path, e)

    async def run_backup(self):
        """Run backup of important files."""
        self.logger.info("Running backup")
        self._last_backup = datetime.now()

        # Backup important directories
        backup_dir = Path(self.config.data_dir) / 'backups' if hasattr(self.config, 'data_dir') else Path.home() / '.aiobot' / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = backup_dir / backup_name

        # Determine what to backup
        important_dirs = []
        for watch_dir in self._watch_dirs:
            # Only backup Documents, Code, etc. - not Downloads or Temp
            if watch_dir.name in ['Documents', 'Code', 'Projects', 'Desktop']:
                important_dirs.append(watch_dir)

        try:
            for src_dir in important_dirs:
                dst_dir = backup_path / src_dir.name
                shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns('*.tmp', '*.log', '__pycache__', '.git', 'node_modules'))

            # Create manifest
            manifest = {
                "timestamp": timestamp,
                "directories": [str(d) for d in important_dirs],
                "created": datetime.now().isoformat(),
            }
            with open(backup_path / 'manifest.json', 'w') as f:
                json.dump(manifest, f, indent=2)

            self.logger.info("Backup completed: %s", backup_path)

            # Cleanup old backups
            await self._cleanup_old_backups(backup_dir)

        except Exception as e:
            self.logger.error("Backup failed: %s", e)

    async def _cleanup_old_backups(self, backup_dir: Path):
        """Remove backups older than retention period."""
        retention_days = self.config.backup_retention_days
        cutoff = datetime.now() - timedelta(days=retention_days)

        for backup in backup_dir.iterdir():
            if backup.is_dir():
                try:
                    manifest_file = backup / 'manifest.json'
                    if manifest_file.exists():
                        with open(manifest_file) as f:
                            manifest = json.load(f)
                        created = datetime.fromisoformat(manifest['created'])
                        if created < cutoff:
                            shutil.rmtree(backup)
                            self.logger.info("Removed old backup: %s", backup)
                except Exception:
                    pass

    def get_duplicate_groups(self) -> list[DuplicateGroup]:
        """Get detected duplicate groups."""
        return self._duplicate_groups

    def get_cleanup_plans(self) -> list[CleanupPlan]:
        """Get pending cleanup plans."""
        return self._cleanup_plans

    def get_organization_stats(self) -> dict[str, Any]:
        """Get organization statistics."""
        total_files = sum(len(g.files) for g in self._duplicate_groups)
        duplicate_files = sum(g.count - 1 for g in self._duplicate_groups)
        space_wasted = sum((g.count - 1) * g.size for g in self._duplicate_groups)

        return {
            "watched_directories": [str(d) for d in self._watch_dirs],
            "total_files_scanned": len(self._file_cache),
            "duplicate_groups": len(self._duplicate_groups),
            "duplicate_files": duplicate_files,
            "space_wasted_mb": round(space_wasted / (1024*1024), 2),
            "cleanup_plans": len(self._cleanup_plans),
            "estimated_cleanup_space_mb": round(sum(p.estimated_space_saved for p in self._cleanup_plans) / (1024*1024), 2),
            "last_organize": self._last_organize.isoformat() if self._last_organize else None,
            "last_cleanup": self._last_cleanup.isoformat() if self._last_cleanup else None,
            "last_backup": self._last_backup.isoformat() if self._last_backup else None,
        }

    def add_watch_directory(self, path: str) -> bool:
        """Add a directory to watch."""
        p = Path(path).expanduser()
        if p.exists() and p.is_dir() and p not in self._watch_dirs:
            self._watch_dirs.append(p)
            return True
        return False

    def add_organization_rule(self, rule: OrganizeRule):
        """Add a custom organization rule."""
        self._rules.append(rule)

    async def shutdown(self):
        """Shutdown the file organizer."""
        self._running = False
        for task in [self._organize_task, self._cleanup_task, self._backup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
