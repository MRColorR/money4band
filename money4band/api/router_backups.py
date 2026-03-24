"""Backup & Restore API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from money4band.api._deps import ConfigPaths, get_paths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/backups", tags=["backups"])


@router.get("")
async def list_all_backups(
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """List available config backups, newest first."""
    from money4band.backup import list_backups

    backups = list_backups()
    return [
        {
            "path": str(b.path),
            "timestamp": b.timestamp,
            "size": b.size,
        }
        for b in backups
    ]


@router.post("")
async def create_new_backup(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Create a new backup of the current config."""
    from money4band.backup import create_backup

    backup_path = create_backup(paths.config_dir)
    return {"status": "ok", "path": str(backup_path)}


class RestoreRequest(BaseModel):
    """Identify which backup to restore."""

    path: str


@router.post("/restore")
async def restore_from_backup(
    payload: RestoreRequest,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Restore a previously created backup."""
    import os

    from money4band.backup import restore_backup

    if not os.path.isfile(payload.path):
        raise HTTPException(status_code=404, detail="Backup file not found")
    restore_backup(payload.path, paths.config_dir)
    return {"status": "ok", "restored_from": payload.path}


@router.delete("/cleanup")
async def cleanup_old_backups(
    keep: int = Query(5, ge=1, description="Number of recent backups to keep"),
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Delete old backups, keeping the *keep* most recent."""
    from money4band.backup import cleanup_backups

    deleted = cleanup_backups(keep=keep)
    return {"status": "ok", "deleted_count": deleted}
