from __future__ import annotations

"""Config backup and restore utilities.

Backups are stored as copies of the (possibly encrypted) user-config file
under ``~/.m4b/backups/`` with ISO-8601 timestamps in the filename.  The
module intentionally copies the *raw file bytes* so encrypted configs stay
encrypted and plaintext configs stay plaintext — no re-encryption needed.
"""

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

BACKUP_DIR = Path.home() / ".m4b" / "backups"
DEFAULT_KEEP = 5


class BackupInfo(NamedTuple):
    path: Path
    timestamp: datetime


def _backup_dir() -> Path:
    """Return (and lazily create) the backup directory."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def create_backup(config_path: str) -> Path:
    """Copy *config_path* into the backup directory with a timestamp suffix.

    Returns the ``Path`` of the newly created backup file.
    """
    src = Path(config_path)
    if not src.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = _backup_dir() / f"user-config.{ts}.bak"
    shutil.copy2(str(src), str(dest))
    logger.info("Backup created: %s", dest)
    return dest


def list_backups() -> list[BackupInfo]:
    """Return all backups sorted newest-first."""
    result: list[BackupInfo] = []
    bdir = _backup_dir()
    for p in bdir.glob("user-config.*.bak"):
        # Extract timestamp from filename: user-config.20260320T120000Z.bak
        stem = p.stem  # user-config.20260320T120000Z
        ts_str = stem.split(".", 1)[1] if "." in stem else ""
        try:
            ts = datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            logger.warning("Skipping unrecognised backup file: %s", p.name)
            continue
        result.append(BackupInfo(path=p, timestamp=ts))
    result.sort(key=lambda b: b.timestamp, reverse=True)
    return result


def restore_backup(backup_path: str | Path, config_path: str) -> None:
    """Restore a backup file over the live config."""
    src = Path(backup_path)
    if not src.is_file():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    shutil.copy2(str(src), config_path)
    logger.info("Restored backup %s → %s", src.name, config_path)


def cleanup_backups(keep: int = DEFAULT_KEEP) -> int:
    """Delete old backups, keeping the *keep* most recent ones.

    Returns the number of files deleted.
    """
    backups = list_backups()
    to_delete = backups[keep:]
    for b in to_delete:
        b.path.unlink()
        logger.info("Deleted old backup: %s", b.path.name)
    return len(to_delete)
