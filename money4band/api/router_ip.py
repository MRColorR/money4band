"""IP quality scoring API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from money4band.api._deps import ConfigPaths, get_paths
from money4band.api.schemas import IpScoreEntry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ip", tags=["ip"])


@router.get("/score", response_model=list[IpScoreEntry])
async def ip_score(
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Run IP quality analysis on the host (and proxy IPs if proxies.txt exists)."""
    from money4band.ip_scorer import analyse_ips

    return analyse_ips()
