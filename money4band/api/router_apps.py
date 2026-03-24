"""Apps API — list apps, get details, manage categories."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from money4band.api._deps import ConfigPaths, get_paths, load_app_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/apps", tags=["apps"])


@router.get("")
async def list_apps(
    category: str | None = Query(None, description="Filter by category name"),
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return a compact listing of all apps, optionally filtered by category."""
    app_config = load_app_config()
    results: list[dict[str, Any]] = []

    for cat_name, cat_data in app_config.get("categories", {}).items():
        if category and cat_name != category:
            continue
        for app in cat_data.get("entries", []):
            results.append(
                {
                    "name": app.get("name", ""),
                    "category": cat_name,
                    "active": cat_data.get("active", False),
                    "image": app.get("image", {}).get("name", ""),
                    "resource_tier": app.get("resource_tier", ""),
                    "earnings_range": app.get("app_details", {}).get(
                        "earnings_range", ""
                    ),
                }
            )
    return results


@router.get("/categories")
async def list_categories(
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return all categories with their active status and app count."""
    app_config = load_app_config()
    cats: list[dict[str, Any]] = []
    for name, data in app_config.get("categories", {}).items():
        cats.append(
            {
                "name": name,
                "active": data.get("active", False),
                "app_count": len(data.get("entries", [])),
            }
        )
    return cats


@router.post("/categories/{name}/toggle")
async def toggle_category(
    name: str,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Toggle the active flag on a category."""
    from money4band.dumper import write_json

    app_config = load_app_config()
    cats = app_config.get("categories", {})
    if name not in cats:
        raise HTTPException(status_code=404, detail=f"Category '{name}' not found")

    new_state = not cats[name].get("active", False)
    cats[name]["active"] = new_state
    write_json(app_config, paths.app_config)
    return {"category": name, "active": new_state}


@router.get("/{app_name}")
async def get_app_detail(
    app_name: str,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return full detail for a single app (case-insensitive match)."""
    app_config = load_app_config()
    lower = app_name.lower()

    for cat_name, cat_data in app_config.get("categories", {}).items():
        for app in cat_data.get("entries", []):
            if app.get("name", "").lower() == lower:
                return {**app, "category": cat_name}

    raise HTTPException(status_code=404, detail=f"App '{app_name}' not found")
