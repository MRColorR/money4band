"""Docker image security API - stale images, digests, CVE scanning."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends

from money4band.api._deps import ConfigPaths, get_paths, load_app_config
from money4band.api.schemas import (
    ApiKeyInfo,
    ApiKeyRegenerated,
    ImageDigest,
    ImageScanResult,
    StaleImage,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/security", tags=["security"])


@router.get("/stale", response_model=list[StaleImage])
async def stale_images(
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return images that haven't been updated in >90 days."""
    from money4band.docker.image_security import check_stale_images

    app_config = load_app_config()
    return await asyncio.to_thread(check_stale_images, app_config)


@router.get("/digests", response_model=list[ImageDigest])
async def image_digests(
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return digests for all pulled images."""
    from money4band.docker.image_security import log_image_digests

    app_config = load_app_config()
    return await asyncio.to_thread(log_image_digests, app_config)


@router.post("/scan/{image_name:path}", response_model=ImageScanResult)
async def scan_image(
    image_name: str,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Run a CVE scan on a specific Docker image using docker scout."""
    import re

    from money4band.docker.image_security import run_scout_cves

    if not re.match(r"^[a-zA-Z0-9._:/@-]+$", image_name):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Invalid image name")

    result = await asyncio.to_thread(run_scout_cves, image_name)
    return {"image": image_name, "report": result}


# ---------------------------------------------------------------------------
# API-key management
# ---------------------------------------------------------------------------


@router.get("/key", response_model=ApiKeyInfo)
async def get_api_key_info(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, object]:
    """Return a masked preview of the current API key."""
    from money4band.api.server import ensure_api_key

    key = ensure_api_key(paths.config_dir)
    if key:
        preview = "*" * max(0, len(key) - 8) + key[-8:]
        return {"key_preview": preview, "has_key": True}
    return {"key_preview": "", "has_key": False}


@router.post("/key/regenerate", response_model=ApiKeyRegenerated)
async def regenerate_key(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Regenerate the dashboard API key.  The new key is shown once."""
    from money4band.api.server import regenerate_api_key

    new_key = regenerate_api_key(paths.config_dir)
    if not new_key:
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail="Failed to regenerate API key")
    return {"key": new_key}
