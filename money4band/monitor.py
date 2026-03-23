from __future__ import annotations

"""Container health monitoring — query Docker for health status and restart-loop detection."""

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class HealthStatus:
    """Snapshot of a single container's health."""

    name: str
    running: bool = False
    health: str = "unknown"  # healthy | unhealthy | starting | none | unknown
    restart_count: int = 0
    last_started: str = ""
    last_error: str = ""
    image: str = ""

    @property
    def ok(self) -> bool:
        return self.running and self.health in ("healthy", "none")


# ---------------------------------------------------------------------------
# Docker inspection helpers
# ---------------------------------------------------------------------------


def _docker_inspect(name: str) -> dict[str, Any] | None:
    """Run ``docker inspect`` on a container, return parsed JSON or None."""
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["docker", "inspect", "--format", "{{json .}}", name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except Exception:
        logger.debug("docker inspect failed for %s", name, exc_info=True)
        return None


def _docker_ps_names(project_filter: str | None = None) -> list[str]:
    """Return names of running containers, optionally filtered by compose project label."""
    cmd = ["docker", "ps", "--format", "{{.Names}}"]
    if project_filter:
        cmd.extend(["--filter", f"label=com.docker.compose.project={project_filter}"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)  # noqa: S603
        if result.returncode != 0:
            return []
        return [n.strip() for n in result.stdout.splitlines() if n.strip()]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_container_health(name: str) -> HealthStatus:
    """Query Docker for the current health of container *name*."""
    info = _docker_inspect(name)
    if info is None:
        return HealthStatus(name=name)

    state = info.get("State", {})
    running = state.get("Running", False)
    restart_count = int(info.get("RestartCount", 0))

    # Health check status: Docker nests it under .State.Health.Status
    health_obj = state.get("Health") or {}
    health_status = health_obj.get("Status", "none")

    # Last started time
    started_at = state.get("StartedAt", "")

    # Last error from health check log
    last_error = ""
    health_log = health_obj.get("Log") or []
    if health_log:
        last_entry = health_log[-1]
        if last_entry.get("ExitCode", 0) != 0:
            last_error = last_entry.get("Output", "").strip()[:200]

    # If no healthcheck error, check OOMKilled or Error in state
    if not last_error:
        if state.get("OOMKilled"):
            last_error = "OOMKilled"
        elif state.get("Error"):
            last_error = state["Error"][:200]

    image = info.get("Config", {}).get("Image", "")

    return HealthStatus(
        name=name,
        running=running,
        health=health_status,
        restart_count=restart_count,
        last_started=started_at,
        last_error=last_error,
        image=image,
    )


def detect_restart_loops(name: str, threshold: int = 5) -> bool:
    """Return True if container *name* has restarted ≥ *threshold* times."""
    status = check_container_health(name)
    return status.restart_count >= threshold


def get_stack_health(project_filter: str | None = None) -> list[HealthStatus]:
    """Return health status for all containers in the stack."""
    names = _docker_ps_names(project_filter)
    return [check_container_health(n) for n in names]
