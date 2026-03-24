"""Self-update API — check for and apply updates."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from money4band.api._deps import ConfigPaths, get_paths, load_m4b_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/update", tags=["update"])


@router.get("/check")
async def check_update(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Check if a newer version of M4B is available."""
    from money4band.updater import check_for_update

    m4b = load_m4b_config()
    current = m4b.get("project", {}).get("project_version", "0.0.0")
    latest = check_for_update(m4b)

    return {
        "current_version": current,
        "latest_version": latest,
        "update_available": latest is not None,
    }


class ApplyUpdate(BaseModel):
    """Payload for applying an update."""

    version: str | None = None


@router.post("/apply")
async def apply_update(
    payload: ApplyUpdate,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Apply an update to the specified (or latest) version."""
    from money4band.updater import apply_update, check_for_update

    m4b = load_m4b_config()
    target = payload.version or check_for_update(m4b)
    if not target:
        raise HTTPException(status_code=400, detail="No update available")

    success = apply_update(target)
    if not success:
        raise HTTPException(status_code=500, detail="Update failed")
    return {"status": "ok", "updated_to": target}
