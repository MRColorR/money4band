"""Configuration profiles API — create, list, switch, delete."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from money4band.api._deps import ConfigPaths, get_paths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("")
async def list_all_profiles(
    paths: ConfigPaths = Depends(get_paths),
) -> list[str]:
    """Return names of all saved configuration profiles."""
    from money4band.profiles import list_profiles

    return list_profiles(paths.config_dir)


class ProfileCreate(BaseModel):
    """Payload for creating a named profile."""

    name: str


@router.post("")
async def create_profile(
    payload: ProfileCreate,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Save the current configuration as a named profile."""
    from money4band.profiles import create_profile

    path = create_profile(
        payload.name,
        config_dir=paths.config_dir,
        base_dir=paths.base_dir,
        user_config_path=paths.user_config,
    )
    return {"status": "ok", "profile": payload.name, "path": path}


@router.put("/{name}/switch")
async def switch_profile(
    name: str,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Activate a previously saved profile."""
    from money4band.profiles import list_profiles, switch_profile

    if name not in list_profiles(paths.config_dir):
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")
    switch_profile(
        name,
        config_dir=paths.config_dir,
        base_dir=paths.base_dir,
        user_config_path=paths.user_config,
    )
    return {"status": "ok", "active_profile": name}


@router.delete("/{name}")
async def delete_profile(
    name: str,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Delete a saved profile."""
    from money4band.profiles import delete_profile, list_profiles

    if name not in list_profiles(paths.config_dir):
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")
    delete_profile(name, config_dir=paths.config_dir)
    return {"status": "ok", "deleted": name}
