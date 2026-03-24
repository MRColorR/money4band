"""Docker image security API — stale images, digests, CVE scanning."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from money4band.api._deps import ConfigPaths, get_paths, load_app_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/security", tags=["security"])


@router.get("/stale")
async def stale_images(
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return images that haven't been updated in >90 days."""
    from money4band.image_security import check_stale_images

    app_config = load_app_config()
    return check_stale_images(app_config)


@router.get("/digests")
async def image_digests(
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return digests for all pulled images."""
    from money4band.image_security import log_image_digests

    app_config = load_app_config()
    return log_image_digests(app_config)


@router.post("/scan/{image_name:path}")
async def scan_image(
    image_name: str,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Run a CVE scan on a specific Docker image using docker scout."""
    import re

    from money4band.image_security import run_scout_cves

    if not re.match(r"^[a-zA-Z0-9._:/@-]+$", image_name):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Invalid image name")

    result = run_scout_cves(image_name)
    return {"image": image_name, "report": result}
