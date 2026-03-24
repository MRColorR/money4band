"""Stack management API — start / stop the Docker Compose stack."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from money4band.api._deps import ConfigPaths, get_paths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stack", tags=["stack"])


@router.post("/start")
async def start_stack(paths: ConfigPaths = Depends(get_paths)) -> dict[str, Any]:
    """Start all Docker Compose stacks (main + proxy instances)."""
    from money4band.fn_startStack import start_all_stacks

    try:
        start_all_stacks(skip_questions=True)
        return {"status": "ok", "message": "Stack started"}
    except Exception as exc:
        logger.exception("Failed to start stack")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stop")
async def stop_stack(paths: ConfigPaths = Depends(get_paths)) -> dict[str, Any]:
    """Stop all Docker Compose stacks (main + proxy instances)."""
    from money4band.fn_stopStack import stop_all_stacks

    try:
        stop_all_stacks(skip_questions=True)
        return {"status": "ok", "message": "Stack stopped"}
    except Exception as exc:
        logger.exception("Failed to stop stack")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/restart")
async def restart_stack(paths: ConfigPaths = Depends(get_paths)) -> dict[str, Any]:
    """Stop then start all stacks."""
    from money4band.fn_startStack import start_all_stacks
    from money4band.fn_stopStack import stop_all_stacks

    try:
        stop_all_stacks(skip_questions=True)
        start_all_stacks(skip_questions=True)
        return {"status": "ok", "message": "Stack restarted"}
    except Exception as exc:
        logger.exception("Failed to restart stack")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
