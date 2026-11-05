from __future__ import annotations

"""Container health monitoring - query Docker for health status and restart-loop detection."""

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
        parsed: dict[str, Any] = json.loads(result.stdout)
        return parsed
    except Exception:
        logger.debug("docker inspect failed for %s", name, exc_info=True)
        return None


def _docker_inspect_many(names: list[str]) -> dict[str, dict[str, Any]]:
    """Inspect all *names* in ONE ``docker inspect`` invocation.

    One process spawn regardless of container count - the per-container
    loop cost 50-150ms of spawn overhead each on every dashboard poll.
    Containers that disappeared between ps and inspect are simply absent
    from the result.
    """
    if not names:
        return {}
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["docker", "inspect", *names],
            capture_output=True,
            text=True,
            timeout=15,
        )
        # docker inspect exits non-zero if ANY name is missing but still
        # prints the JSON array for the ones it found - parse regardless.
        parsed = json.loads(result.stdout) if result.stdout.strip() else []
    except Exception:
        logger.debug("bulk docker inspect failed", exc_info=True)
        return {}
    out: dict[str, dict[str, Any]] = {}
    for info in parsed:
        if isinstance(info, dict):
            raw_name = str(info.get("Name", "")).lstrip("/")
            if raw_name:
                out[raw_name] = info
    return out


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


def check_container_health(
    name: str, info: dict[str, Any] | None = None
) -> HealthStatus:
    """Query Docker for the current health of container *name*.

    Pass *info* (a pre-fetched ``docker inspect`` payload) to skip the
    per-container subprocess - get_stack_health uses one bulk inspect.
    """
    if info is None:
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
    """Return True if container *name* has restarted >= *threshold* times."""
    status = check_container_health(name)
    return status.restart_count >= threshold


def get_stack_health(project_filter: str | None = None) -> list[HealthStatus]:
    """Return health status for all containers in the stack."""
    names = _docker_ps_names(project_filter)
    infos = _docker_inspect_many(names)
    return [check_container_health(n, info=infos.get(n)) for n in names]
