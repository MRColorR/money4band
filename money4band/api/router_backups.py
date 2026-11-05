"""Backup & Restore API."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from money4band.api._deps import ConfigPaths, get_paths
from money4band.api.schemas import BackupCleanup, BackupEntry, BackupRestore, StatusPath
from money4band.core.backup import get_backup_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/backups", tags=["backups"])


@router.get("", response_model=list[BackupEntry])
async def list_all_backups(
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """List available config backups, newest first."""
    from money4band.core.backup import list_backups

    backups = list_backups()
    return [
        {
            "path": str(b.path),
            "timestamp": b.timestamp,
            "size": Path(b.path).stat().st_size if Path(b.path).exists() else 0,
        }
        for b in backups
    ]


@router.post("", response_model=StatusPath)
async def create_new_backup(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Create a new backup of the current config."""
    from money4band.core.backup import create_backup

    backup_path = create_backup(paths.user_config)
    return {"status": "ok", "path": str(backup_path)}


class RestoreRequest(BaseModel):
    """Identify which backup to restore."""

    path: str


@router.post("/restore", response_model=BackupRestore)
async def restore_from_backup(
    payload: RestoreRequest,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Restore a previously created backup."""
    from money4band.core.backup import restore_backup

    # Resolve at request time: freezing the backup dir at import broke
    # restores after a data-dir migration (validated against a stale dir).
    resolved = Path(payload.path).resolve()
    if not resolved.is_relative_to(get_backup_dir().resolve()):
        raise HTTPException(
            status_code=400, detail="Path must be inside the backup directory"
        )
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Backup file not found")
    restore_backup(str(resolved), paths.user_config)
    return {"status": "ok", "restored_from": str(resolved)}


@router.delete("/cleanup", response_model=BackupCleanup)
async def cleanup_old_backups(
    keep: int = Query(5, ge=1, description="Number of recent backups to keep"),
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Delete old backups, keeping the *keep* most recent."""
    from money4band.core.backup import cleanup_backups

    deleted = cleanup_backups(keep=keep)
    return {"status": "ok", "deleted_count": deleted}
