"""Earnings estimation API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from money4band.api._deps import ConfigPaths, get_paths, load_app_config
from money4band.api.schemas import EarningsResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/earnings", tags=["earnings"])


@router.get("", response_model=EarningsResponse)
async def get_earnings(
    ip_type: str = Query(
        "residential", description="IP type: residential or datacenter"
    ),
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return per-app earnings estimates and totals."""
    from money4band.earnings_estimator import get_app_earnings

    app_config = load_app_config()
    apps = get_app_earnings(app_config, ip_type=ip_type)

    total_min = sum(a.get("range_low", 0) for a in apps)
    total_max = sum(a.get("range_high", 0) for a in apps)

    return {
        "ip_type": ip_type,
        "apps": apps,
        "total_min": round(total_min, 2),
        "total_max": round(total_max, 2),
    }
