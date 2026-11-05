"""Self-update API - check for and apply updates."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from money4band.api._deps import ConfigPaths, get_paths, load_m4b_config
from money4band.api.schemas import UpdateApplied, UpdateCheck

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/update", tags=["update"])

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


@router.get("/check", response_model=UpdateCheck)
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


@router.post("/apply", response_model=UpdateApplied)
async def apply_update(
    payload: ApplyUpdate,
    request: Request,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Apply an update to the specified (or latest) version.

    Restricted to localhost for safety - remote callers receive 403.
    """
    client = request.client.host if request.client else ""
    if client not in _LOOPBACK:
        raise HTTPException(
            status_code=403, detail="Updates can only be applied from localhost"
        )

    from money4band.updater import apply_update, check_for_update

    m4b = load_m4b_config()
    target = payload.version or check_for_update(m4b)
    if not target:
        raise HTTPException(status_code=400, detail="No update available")

    success = await asyncio.to_thread(apply_update, target)
    if not success:
        raise HTTPException(status_code=500, detail="Update failed")
    return {"status": "ok", "updated_to": target}
