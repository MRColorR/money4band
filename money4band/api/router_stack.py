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


@router.post("/start", response_model=StatusMessage)
async def start_stack(paths: ConfigPaths = Depends(get_paths)) -> dict[str, Any]:
    """Start all Docker Compose stacks (main + proxy instances)."""
    from money4band.docker.start import start_all_stacks

    try:
        await asyncio.to_thread(start_all_stacks, skip_questions=True)
        return {"status": "ok", "message": "Stack started"}
    except Exception as exc:
        logger.exception("Failed to start stack")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stop", response_model=StatusMessage)
async def stop_stack(paths: ConfigPaths = Depends(get_paths)) -> dict[str, Any]:
    """Stop all Docker Compose stacks (main + proxy instances)."""
    from money4band.docker.stop import stop_all_stacks

    try:
        await asyncio.to_thread(stop_all_stacks, skip_questions=True)
        return {"status": "ok", "message": "Stack stopped"}
    except Exception as exc:
        logger.exception("Failed to stop stack")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/restart", response_model=StatusMessage)
async def restart_stack(paths: ConfigPaths = Depends(get_paths)) -> dict[str, Any]:
    """Stop then start all stacks."""
    from money4band.docker.start import start_all_stacks
    from money4band.docker.stop import stop_all_stacks

    try:
        await asyncio.to_thread(stop_all_stacks, skip_questions=True)
        await asyncio.to_thread(start_all_stacks, skip_questions=True)
        return {"status": "ok", "message": "Stack restarted"}
    except Exception as exc:
        logger.exception("Failed to restart stack")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
