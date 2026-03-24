"""Container monitoring API — health, stats, restart-loop detection."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from money4band.api._deps import ConfigPaths, get_paths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitor", tags=["monitor"])


@router.get("/health")
async def stack_health(
    project: str | None = Query(None, description="Docker Compose project filter"),
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return rich health status for all stack containers."""
    from money4band.monitor import get_stack_health

    statuses = get_stack_health(project_filter=project)
    return [
        {
            "name": s.name,
            "running": s.running,
            "health": s.health,
            "restart_count": s.restart_count,
            "last_started": s.last_started,
            "last_error": s.last_error,
            "image": s.image,
        }
        for s in statuses
    ]


@router.get("/restart-loops")
async def restart_loops(
    threshold: int = Query(5, ge=1, description="Restart count threshold"),
    paths: ConfigPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Detect containers stuck in restart loops."""
    from money4band.monitor import get_stack_health

    statuses = get_stack_health()
    loops: list[dict[str, Any]] = []
    for s in statuses:
        if s.restart_count >= threshold:
            loops.append(
                {
                    "name": s.name,
                    "restart_count": s.restart_count,
                    "last_error": s.last_error,
                    "image": s.image,
                }
            )
    return loops
