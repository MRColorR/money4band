"""Configuration API - view, update, and reset configs + resource limits."""

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
    from money4band.core.viewer import _mask_dict

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
    accepted - this prevents injection of arbitrary new keys while
    allowing the API full parity with the CLI menu.
    """
    from money4band.core.dumper import write_json

    cfg = load_user_config()
    unknown = set(payload.data) - set(cfg)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown config keys: {', '.join(sorted(unknown))}",
        )

    # Reject type changes on dict-valued keys - prevents nuking nested
    # objects (e.g. m4b_dashboard) with a scalar and bypassing _IMMUTABLE_KEYS.
    for key, value in payload.data.items():
        if isinstance(cfg.get(key), dict) and not isinstance(value, dict):
            raise HTTPException(
                status_code=400,
                detail=f"Key '{key}' must be an object, not {type(value).__name__}",
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

    from money4band.core.reset import reset_config

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
    """Return the aggregated catalog dict."""
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
    from money4band.system.detector import get_active_profile

    m4b = load_m4b_config()
    usr = load_user_config()
    profiles = m4b.get("resource_profiles", {}).get("profiles", {})
    return {
        "active_profile": get_active_profile(usr),
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
    from money4band.core.dumper import write_json
    from money4band.system.detector import calculate_resource_limits, get_valid_profiles

    m4b = load_m4b_config()
    valid = get_valid_profiles(m4b)
    if payload.profile not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid profile '{payload.profile}'. Valid: {', '.join(valid)}",
        )

    usr = load_user_config()
    usr.setdefault("settings", {})["resource_profile"] = payload.profile
    write_json(usr, paths.user_config)

    calculate_resource_limits(paths.user_config, m4b_config=m4b)
    return {"status": "ok", "profile": payload.profile}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Keys that must never be overwritten via the config update API.
_IMMUTABLE_KEYS = frozenset({"api_key", "master_key"})


def _deep_merge(base: dict, updates: dict) -> None:
    """Recursively merge *updates* into *base* in-place.

    Keys listed in ``_IMMUTABLE_KEYS`` are silently skipped to prevent
    API callers from overwriting security-sensitive fields like the
    dashboard API key.
    """
    for key, value in updates.items():
        if key in _IMMUTABLE_KEYS:
            continue
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# ---------------------------------------------------------------------------
# Dashboard auto-start config
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_model=dict[str, Any])
async def get_dashboard_config(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return the ``m4b_dashboard`` section of user-config."""
    cfg = load_user_config()
    dash = cfg.get("m4b_dashboard", {})
    from money4band.dashboard.setup import read_dashboard_pid

    pid = read_dashboard_pid(paths.config_dir)
    return {
        "enabled": dash.get("enabled", True),
        "port": dash.get("port", 8088),
        "running": pid is not None,
        "pid": pid,
    }


class DashboardConfigUpdate(BaseModel):
    """Payload for updating dashboard auto-start settings."""

    enabled: bool | None = None
    port: int | None = None


@router.put("/dashboard", response_model=StatusOk)
async def update_dashboard_config(
    payload: DashboardConfigUpdate,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Update the ``m4b_dashboard.enabled`` and/or ``port`` in user-config."""
    from money4band.dashboard.setup import set_dashboard_state

    if payload.enabled is None and payload.port is None:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: enabled, port",
        )

    kwargs: dict[str, Any] = {}
    if payload.enabled is not None:
        kwargs["enabled"] = payload.enabled
    else:
        cfg = load_user_config()
        kwargs["enabled"] = cfg.get("m4b_dashboard", {}).get("enabled", True)
    if payload.port is not None:
        kwargs["port"] = payload.port

    set_dashboard_state(paths.config_dir, **kwargs)
    return {"status": "ok"}
