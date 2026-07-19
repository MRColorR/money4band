"""Stack management API - start / stop the Docker Compose stack."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from money4band.api._deps import ConfigPaths, get_paths
from money4band.api.schemas import StatusMessage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stack", tags=["stack"])


def _active_profiles() -> tuple[str, ...]:
    """Resolve the compose profiles for the current config.

    Every generated service is profile-gated, so starting without the
    resolved profile set would start nothing at all.
    """
    from money4band.api._deps import load_app_config, load_user_config
    from money4band.docker.helper import get_active_profiles

    return tuple(get_active_profiles(load_user_config(), load_app_config()))


def _regenerate_stack_files(paths: ConfigPaths) -> None:
    """Rebuild docker-compose.yaml and .env from the current config.

    The API mutates config without touching the generated artifacts (a
    PUT /api/config/user that enables an app does not edit compose), and
    a successful start securely wipes .env. Regenerating both before
    every start keeps the stack consistent with the config and is
    idempotent - identical config yields byte-identical files.
    """
    from money4band.core.loader import load_app_config_with_overlays
    from money4band.docker.generator import (
        assemble_docker_compose,
        generate_env_file,
    )

    app_config = load_app_config_with_overlays(
        paths.m4b_config, user_config_path=paths.user_config
    )
    assemble_docker_compose(
        m4b_config_path_or_dict=paths.m4b_config,
        app_config_path_or_dict=app_config,
        user_config_path_or_dict=paths.user_config,
        compose_output_path="./docker-compose.yaml",
        is_main_instance=True,
    )
    generate_env_file(
        m4b_config_path_or_dict=paths.m4b_config,
        app_config_path_or_dict=app_config,
        user_config_path_or_dict=paths.user_config,
        env_output_path="./.env",
        is_main_instance=True,
    )


@router.post("/start", response_model=StatusMessage)
async def start_stack(paths: ConfigPaths = Depends(get_paths)) -> dict[str, Any]:
    """Start all Docker Compose stacks (main + proxy instances)."""
    from money4band.docker.start import start_all_stacks

    try:
        await asyncio.to_thread(_regenerate_stack_files, paths)
        profiles = _active_profiles()
        started = await asyncio.to_thread(
            start_all_stacks, skip_questions=True, profiles=profiles
        )
        if not started:
            raise HTTPException(
                status_code=500, detail="Stack failed to start - check the logs"
            )
        return {"status": "ok", "message": "Stack started"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to start stack")
        raise HTTPException(
            status_code=500, detail=str(exc) or type(exc).__name__
        ) from exc


@router.post("/stop", response_model=StatusMessage)
async def stop_stack(paths: ConfigPaths = Depends(get_paths)) -> dict[str, Any]:
    """Stop all Docker Compose stacks (main + proxy instances)."""
    from money4band.docker.stop import stop_all_stacks

    try:
        stopped = await asyncio.to_thread(stop_all_stacks, skip_questions=True)
        if not stopped:
            raise HTTPException(
                status_code=500, detail="Stack failed to stop - check the logs"
            )
        return {"status": "ok", "message": "Stack stopped"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to stop stack")
        raise HTTPException(
            status_code=500, detail=str(exc) or type(exc).__name__
        ) from exc


@router.post("/restart", response_model=StatusMessage)
async def restart_stack(paths: ConfigPaths = Depends(get_paths)) -> dict[str, Any]:
    """Stop then start all stacks."""
    from money4band.docker.start import start_all_stacks
    from money4band.docker.stop import stop_all_stacks

    try:
        await asyncio.to_thread(stop_all_stacks, skip_questions=True)
        await asyncio.to_thread(_regenerate_stack_files, paths)
        profiles = _active_profiles()
        started = await asyncio.to_thread(
            start_all_stacks, skip_questions=True, profiles=profiles
        )
        if not started:
            raise HTTPException(
                status_code=500, detail="Stack failed to restart - check the logs"
            )
        return {"status": "ok", "message": "Stack restarted"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to restart stack")
        raise HTTPException(
            status_code=500, detail=str(exc) or type(exc).__name__
        ) from exc
