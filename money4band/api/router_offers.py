"""Referral & passive income offers API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from money4band.api._deps import ConfigPaths, get_paths
from money4band.api.schemas import OfferEntry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/offers", tags=["offers"])


@router.get("", response_model=list[OfferEntry])
async def get_offers(
    category: str | None = Query(None, description="Filter by offer category"),
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return all referral & passive income offers."""
    import os

    from money4band.apps.offers import load_all_offers
    from money4band.core.offers_migration import migrate_offers_file

    # One-shot split of the legacy monolithic referral-offers.json.
    migrate_offers_file(paths.m4b_config)

    offers_dir = os.path.join(paths.config_dir, "offers.d")
    all_offers = load_all_offers(
        app_config_path=paths.m4b_config,
        offers_path=offers_dir,
    )
    if category:
        all_offers = [o for o in all_offers if o.get("category") == category]
    return all_offers
