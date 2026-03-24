"""Referral & passive income offers API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from money4band.api._deps import ConfigPaths, get_paths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/offers", tags=["offers"])


@router.get("")
async def get_offers(
    category: str | None = Query(None, description="Filter by offer category"),
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return all referral & passive income offers."""
    import os

    from money4band.offers import load_all_offers

    offers_path = os.path.join(paths.config_dir, "referral-offers.json")
    all_offers = load_all_offers(
        app_config_path=paths.app_config,
        offers_path=offers_path,
    )
    if category:
        all_offers = [o for o in all_offers if o.get("category") == category]
    return all_offers
