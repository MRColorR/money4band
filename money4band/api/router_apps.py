"""Apps API — list apps, get details, manage categories."""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from money4band.api._deps import (
    ConfigPaths,
    get_app_categories,
    get_paths,
    iter_all_apps,
    load_app_config,
)
from money4band.api.schemas import AppSummary, CategorySummary, CategoryToggle

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/apps", tags=["apps"])

# Regex to extract the tier name from compose template variables like
# ${APP_CPU_LIMIT_MEDIUM} → "medium"
_TIER_RE = re.compile(r"\$\{APP_CPU_LIMIT_(\w+)\}", re.IGNORECASE)


def _extract_resource_tier(app: dict[str, Any]) -> str:
    """Derive the resource tier from compose_config cpu template var."""
    cpus = app.get("compose_config", {}).get("cpus", "")
    m = _TIER_RE.match(cpus)
    return m.group(1).lower() if m else ""


def _extract_image(app: dict[str, Any]) -> str:
    """Return the Docker image from the real config structure."""
    # Real config: compose_config.image is a plain string
    cc = app.get("compose_config", {})
    if isinstance(cc, dict):
        img = cc.get("image", "")
        if isinstance(img, str):
            return img
    # Legacy/test format: image.name
    img_obj = app.get("image", {})
    if isinstance(img_obj, dict):
        return img_obj.get("name", "")
    return ""


def _extract_earnings_range(app: dict[str, Any]) -> str:
    """Return the earnings range from the real config structure."""
    details = app.get("app_details", {})
    # Real config: app_details.earnings.avg_monthly_residential_usd
    earnings = details.get("earnings", {})
    if isinstance(earnings, dict):
        val = earnings.get("avg_monthly_residential_usd", "")
        if val is not None:
            return str(val)
    # Legacy/test format: app_details.earnings_range
    return str(details.get("earnings_range", ""))


@router.get("", response_model=list[AppSummary])
async def list_apps(
    category: str | None = Query(None, description="Filter by category name"),
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return a compact listing of all apps, optionally filtered by category."""
    results: list[dict[str, Any]] = []

    for cat_name, cat_data, app in iter_all_apps():
        if category and cat_name != category:
            continue
        details = app.get("app_details", {})
        results.append(
            {
                "name": app.get("name", ""),
                "category": cat_name,
                "active": cat_data.get("active", False),
                "image": _extract_image(app),
                "resource_tier": _extract_resource_tier(app),
                "earnings_range": _extract_earnings_range(app),
                "compose_layer": app.get("compose_layer", ""),
                "status": details.get("status", ""),
                "dashboard_url": app.get("dashboard", ""),
            }
        )
    return results


@router.get("/categories", response_model=list[CategorySummary])
async def list_categories(
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return all categories with their active status and app count."""
    categories = get_app_categories()
    cats: list[dict[str, Any]] = []
    for name, data in categories.items():
        cats.append(
            {
                "name": name,
                "active": data.get("active", False),
                "app_count": len(data.get("entries", [])),
            }
        )
    return cats


@router.post("/categories/{name}/toggle", response_model=CategoryToggle)
async def toggle_category(
    name: str,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Toggle the active flag on a category."""
    from money4band.core.dumper import write_json

    app_config = load_app_config()
    categories = get_app_categories(app_config)
    if name not in categories:
        raise HTTPException(status_code=404, detail=f"Category '{name}' not found")

    new_state = not categories[name].get("active", False)
    categories[name]["active"] = new_state
    write_json(app_config, paths.app_config)
    return {"category": name, "active": new_state}


@router.get("/{app_name}")
async def get_app_detail(
    app_name: str,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return full detail for a single app (case-insensitive match)."""
    lower = app_name.lower()

    for cat_name, _cat_data, app in iter_all_apps():
        if app.get("name", "").lower() == lower:
            return {**app, "category": cat_name}

    raise HTTPException(status_code=404, detail=f"App '{app_name}' not found")
