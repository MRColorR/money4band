"""Configuration API — view, update, and reset configs + resource limits."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from money4band.api._deps import (
    ConfigPaths,
    get_paths,
    load_app_config,
    load_m4b_config,
    load_user_config,
)
from money4band.api.schemas import LimitSet, LimitsResponse, StatusMessage, StatusOk

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["config"])


# ---------------------------------------------------------------------------
# User config
# ---------------------------------------------------------------------------


@router.get("/user")
async def get_user_config(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return user-config.json with sensitive values masked."""
    from money4band.config_viewer import _mask_dict

    cfg = load_user_config()
    return _mask_dict(cfg)


class ConfigUpdate(BaseModel):
    """Partial user-config update payload."""

    data: dict[str, Any]


@router.put("/user", response_model=StatusOk)
async def update_user_config(
    payload: ConfigUpdate,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Merge *payload.data* into user-config.json and persist.

    Only top-level keys that already exist in the current config are
    accepted — this prevents injection of arbitrary new keys while
    allowing the API full parity with the CLI menu.
    """
    from money4band.dumper import write_json

    cfg = load_user_config()
    unknown = set(payload.data) - set(cfg)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown config keys: {', '.join(sorted(unknown))}",
        )

    _deep_merge(cfg, payload.data)
    write_json(cfg, paths.user_config)
    return {"status": "ok"}


@router.post("/reset", response_model=StatusMessage)
async def reset_config(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Reset user-config.json from the template."""
    import os

    from money4band.fn_reset_config import reset_config

    template = os.path.join(paths.base_dir, "template", "user-config.json")
    if not os.path.isfile(template):
        raise HTTPException(status_code=404, detail="Template not found")
    reset_config(template, paths.user_config)
    return {"status": "ok", "message": "Config reset to template defaults"}


# ---------------------------------------------------------------------------
# App config (read-only)
# ---------------------------------------------------------------------------


@router.get("/app")
async def get_app_config_endpoint(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return the full app-config.json."""
    return load_app_config()


@router.get("/m4b")
async def get_m4b_config(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return the full m4b-config.json (non-sensitive project metadata)."""
    return load_m4b_config()


# ---------------------------------------------------------------------------
# Resource limits
# ---------------------------------------------------------------------------


@router.get("/limits", response_model=LimitsResponse)
async def get_limits(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return current resource limits, active profile, and available profiles."""
    from money4band.detector import get_active_profile

    m4b = load_m4b_config()
    usr = load_user_config()
    profiles = m4b.get("resource_profiles", {}).get("profiles", {})
    return {
        "active_profile": get_active_profile(m4b),
        "available_profiles": profiles,
        "resource_limits": usr.get("resource_limits", {}),
    }


class LimitUpdate(BaseModel):
    """Payload for changing the resource profile."""

    profile: str


@router.put("/limits", response_model=LimitSet)
async def set_limits(
    payload: LimitUpdate,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Switch the active resource-limit profile and recalculate limits."""
    from money4band.detector import calculate_resource_limits, get_valid_profiles
    from money4band.dumper import write_json

    m4b = load_m4b_config()
    valid = get_valid_profiles(m4b)
    if payload.profile not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid profile '{payload.profile}'. Valid: {', '.join(valid)}",
        )

    m4b = load_m4b_config()
    m4b.setdefault("resource_profiles", {})["active"] = payload.profile
    write_json(m4b, paths.m4b_config)

    calculate_resource_limits(paths.user_config, m4b_config=m4b)
    return {"status": "ok", "profile": payload.profile}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deep_merge(base: dict, updates: dict) -> None:
    """Recursively merge *updates* into *base* in-place."""
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
