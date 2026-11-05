"""Orphan-resource cleanup for an M4B Docker project.

When users add/remove apps or restructure proxies, Docker Compose leaves
behind stopped containers, unused networks, and orphan volumes scoped to
the project name. This module surfaces ``clean_orphans()`` which the
``m4b clean`` subcommand wraps.

Filtering uses the standard Docker Compose label
``com.docker.compose.project=<project>`` so only resources owned by *this*
M4B install are touched. Resources from other docker-compose projects on
the same host are never affected.

Volumes are opt-in (``include_volumes=True``) because they can hold the
only copy of an app's persistent state (e.g. mystnode keystore). The CLI
exposes them behind a ``--volumes`` flag with an extra confirmation.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CleanResult:
    """Summary of a ``clean_orphans`` invocation."""

    project: str
    containers_removed: list[str] = field(default_factory=list)
    networks_removed: list[str] = field(default_factory=list)
    volumes_removed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            len(self.containers_removed)
            + len(self.networks_removed)
            + len(self.volumes_removed)
        )


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False)  # noqa: S603


def _list_containers(project: str) -> list[tuple[str, str, str]]:
    """Return ``(id, name, state)`` for every container labelled with *project*."""
    result = _run(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            "{{json .}}",
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(f"docker ps failed: {result.stderr.strip()}")
    containers: list[tuple[str, str, str]] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        containers.append(
            (obj.get("ID", ""), obj.get("Names", ""), obj.get("State", ""))
        )
    return containers


def _list_networks(project: str) -> list[tuple[str, str]]:
    result = _run(
        [
            "docker",
            "network",
            "ls",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            "{{.ID}}\t{{.Name}}",
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(f"docker network ls failed: {result.stderr.strip()}")
    nets: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1]:
            nets.append((parts[0], parts[1]))
    return nets


def _list_volumes(project: str) -> list[str]:
    result = _run(
        [
            "docker",
            "volume",
            "ls",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            "{{.Name}}",
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(f"docker volume ls failed: {result.stderr.strip()}")
    return [v.strip() for v in result.stdout.splitlines() if v.strip()]


def _network_in_use(network_id: str) -> bool:
    """Return True if *network_id* is attached to any container."""
    result = _run(
        ["docker", "network", "inspect", "--format", "{{len .Containers}}", network_id]
    )
    if result.returncode != 0:
        return True  # be conservative: don't prune on inspect failure
    try:
        return int(result.stdout.strip()) > 0
    except ValueError:
        return True


def clean_orphans(
    project: str,
    *,
    include_volumes: bool = False,
    dry_run: bool = False,
) -> CleanResult:
    """Remove stopped containers, unused networks, and (opt-in) volumes
    scoped to the Docker Compose project named *project*.

    Only resources carrying the
    ``com.docker.compose.project=<project>`` label are touched.
    """
    result = CleanResult(project=project)

    # --- Containers: stopped only ---
    try:
        for cid, name, state in _list_containers(project):
            if state.lower() in {"running", "restarting", "paused"}:
                continue
            if dry_run:
                result.containers_removed.append(name or cid)
                continue
            rm = _run(["docker", "rm", "-f", cid])
            if rm.returncode == 0:
                result.containers_removed.append(name or cid)
            else:
                result.errors.append(f"rm container {name or cid}: {rm.stderr.strip()}")
    except RuntimeError as exc:
        result.errors.append(str(exc))

    # --- Networks: unused only ---
    try:
        for nid, name in _list_networks(project):
            if _network_in_use(nid):
                continue
            if dry_run:
                result.networks_removed.append(name)
                continue
            rm = _run(["docker", "network", "rm", nid])
            if rm.returncode == 0:
                result.networks_removed.append(name)
            else:
                result.errors.append(f"rm network {name}: {rm.stderr.strip()}")
    except RuntimeError as exc:
        result.errors.append(str(exc))

    # --- Volumes: opt-in, dangerous ---
    if include_volumes:
        try:
            for vol in _list_volumes(project):
                if dry_run:
                    result.volumes_removed.append(vol)
                    continue
                rm = _run(["docker", "volume", "rm", vol])
                if rm.returncode == 0:
                    result.volumes_removed.append(vol)
                else:
                    result.errors.append(f"rm volume {vol}: {rm.stderr.strip()}")
        except RuntimeError as exc:
            result.errors.append(str(exc))

    logger.info(
        "Clean project=%s containers=%d networks=%d volumes=%d errors=%d dry_run=%s",
        project,
        len(result.containers_removed),
        len(result.networks_removed),
        len(result.volumes_removed),
        len(result.errors),
        dry_run,
    )
    return result
