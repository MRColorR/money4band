"""Catalog source management API — phase-8.7.

Mirrors the ``m4b catalog`` CLI one-to-one so CLI, TUI, and REST all
behave identically. All business logic is delegated to
:mod:`money4band.apps.catalog_manager`; this router is a thin HTTP
layer over it.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from money4band.api._deps import ConfigPaths, _cache, get_paths
from money4band.apps import catalog_manager as cm
from money4band.apps.catalog_manager import SOURCE_TYPES, CatalogSourceError

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SourceCreate(BaseModel):
    name: str = Field(min_length=1)
    type: Literal["local", "remote"]
    url: str | None = None
    path: str | None = None
    default_source: str | None = None
    cache_path: str | None = None
    timeout: float | None = None
    enabled: bool = True


class SourceToggle(BaseModel):
    enabled: bool


class CategoryToggle(BaseModel):
    active: bool


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _invalidate_config_cache() -> None:
    """Drop cached ``m4b-config`` after a mutation so subsequent reads are fresh."""
    _cache.invalidate()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/sources")
async def list_sources(
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return ``catalog_sources[]`` as declared in m4b-config.json."""
    return cm.list_sources(paths.m4b_config)


@router.get("/status")
async def catalog_status(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return per-source cache status and category flags."""
    return {
        "sources": cm.source_status(paths.m4b_config),
        "categories": cm.list_categories(paths.m4b_config),
    }


@router.post("/sources", status_code=201)
async def add_source(
    payload: SourceCreate,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    if payload.type not in SOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type {payload.type!r}")
    try:
        decl = cm.add_source(
            paths.m4b_config,
            name=payload.name,
            type=payload.type,
            url=payload.url,
            path=payload.path,
            default_source=payload.default_source,
            enabled=payload.enabled,
            cache_path=payload.cache_path,
            timeout=payload.timeout,
        )
    except CatalogSourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _invalidate_config_cache()
    return decl


@router.delete("/sources/{name}")
async def remove_source(
    name: str,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    if not cm.remove_source(paths.m4b_config, name):
        raise HTTPException(status_code=404, detail=f"Source {name!r} not found")
    _invalidate_config_cache()
    return {"status": "ok"}


@router.put("/sources/{name}/enabled")
async def set_source_enabled(
    name: str,
    payload: SourceToggle,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    if not cm.set_source_enabled(paths.m4b_config, name, payload.enabled):
        raise HTTPException(status_code=404, detail=f"Source {name!r} not found")
    _invalidate_config_cache()
    return {"status": "ok", "enabled": payload.enabled}


@router.post("/refresh")
async def refresh_all(
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Force-refresh every enabled remote source."""
    return cm.refresh_source(paths.m4b_config, None)


@router.post("/refresh/{name}")
async def refresh_one(
    name: str,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    try:
        results = cm.refresh_source(paths.m4b_config, name)
    except CatalogSourceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # refresh_source returns a list; callers asking for a single
    # source expect one entry.
    return results[0] if results else {"name": name, "status": "skipped"}


@router.get("/categories")
async def list_categories(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, dict[str, Any]]:
    return cm.list_categories(paths.m4b_config)


@router.put("/categories/{name}")
async def set_category(
    name: str,
    payload: CategoryToggle,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    try:
        cm.set_category(paths.m4b_config, name, payload.active)
    except CatalogSourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _invalidate_config_cache()
    return {"status": "ok", "category": name, "active": payload.active}
