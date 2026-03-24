"""FastAPI backend for the M4B web dashboard.

Provides REST endpoints for container status, resource stats, health
indicators, quick actions (start/stop/restart), and full M4B control
via modular API routers.

Run standalone:  ``m4b dashboard [--port 8088]``
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from money4band.api._deps import configure_paths
from money4band.api.router_apps import router as apps_router
from money4band.api.router_backups import router as backups_router
from money4band.api.router_config import router as config_router
from money4band.api.router_earnings import router as earnings_router
from money4band.api.router_ip import router as ip_router
from money4band.api.router_monitor import router as monitor_router
from money4band.api.router_notifications import router as notifications_router
from money4band.api.router_offers import router as offers_router
from money4band.api.router_profiles import router as profiles_router
from money4band.api.router_security import router as security_router
from money4band.api.router_stack import router as stack_router
from money4band.api.router_system import router as system_router
from money4band.api.router_update import router as update_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="M4B Dashboard API",
    version="2.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Register modular API routers
app.include_router(stack_router)
app.include_router(config_router)
app.include_router(apps_router)
app.include_router(system_router)
app.include_router(monitor_router)
app.include_router(backups_router)
app.include_router(profiles_router)
app.include_router(earnings_router)
app.include_router(ip_router)
app.include_router(offers_router)
app.include_router(notifications_router)
app.include_router(update_router)
app.include_router(security_router)

# Config directory — set at startup via configure()
_config_dir: str = ""
_ALLOWED_ACTIONS = {"start", "stop", "restart"}


def configure(config_dir: str, base_dir: str | None = None) -> None:
    """Set config directory for the dashboard API and all routers."""
    global _config_dir
    _config_dir = config_dir
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    configure_paths(config_dir=config_dir, base_dir=base_dir)


def _run_docker(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a docker command and return the result."""
    cmd = ["docker"] + list(args)
    return subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, timeout=30
    )


@app.get("/api/status")
async def get_status() -> list[dict[str, Any]]:
    """Return status of all M4B containers."""
    result = _run_docker(
        "ps",
        "-a",
        "--filter",
        "label=com.centurylinklabs.watchtower.enable=true",
        "--format",
        "{{.Names}}\t{{.Status}}\t{{.State}}\t{{.Ports}}",
    )
    containers: list[dict[str, Any]] = []
    if result.returncode != 0:
        return containers

    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            containers.append(
                {
                    "name": parts[0],
                    "status": parts[1],
                    "state": parts[2],
                    "ports": parts[3] if len(parts) > 3 else "",
                }
            )
    return containers


@app.get("/api/health")
async def get_health() -> list[dict[str, Any]]:
    """Return health status for all M4B containers via docker inspect."""
    result = _run_docker(
        "ps",
        "-a",
        "-q",
        "--filter",
        "label=com.centurylinklabs.watchtower.enable=true",
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []

    ids = result.stdout.strip().splitlines()
    inspect_result = _run_docker(
        "inspect",
        "--format",
        '{"name":"{{.Name}}","running":{{.State.Running}},'
        '"health":"{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",'
        '"restarts":{{.RestartCount}}}',
        *ids,
    )
    if inspect_result.returncode != 0:
        return []

    statuses: list[dict[str, Any]] = []
    for line in inspect_result.stdout.strip().splitlines():
        try:
            data = json.loads(line)
            data["name"] = data["name"].lstrip("/")
            statuses.append(data)
        except json.JSONDecodeError:
            continue
    return statuses


@app.get("/api/stats")
async def get_stats() -> list[dict[str, Any]]:
    """Return CPU and memory stats for running M4B containers."""
    result = _run_docker(
        "stats",
        "--no-stream",
        "--format",
        "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}",
    )
    stats: list[dict[str, Any]] = []
    if result.returncode != 0:
        return stats

    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 4:
            stats.append(
                {
                    "name": parts[0],
                    "cpu_percent": parts[1],
                    "mem_usage": parts[2],
                    "mem_percent": parts[3],
                }
            )
    return stats


@app.post("/api/action/{container}/{action}")
async def container_action(container: str, action: str) -> dict[str, str]:
    """Start, stop, or restart a specific container."""
    if action not in _ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid action '{action}'")

    # Sanitize container name — only allow alphanumeric, dash, underscore, dot
    import re

    if not re.match(r"^[a-zA-Z0-9._-]+$", container):
        raise HTTPException(status_code=400, detail="Invalid container name")

    result = _run_docker(action, container)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr.strip())

    return {"status": "ok", "action": action, "container": container}


@app.get("/api/events")
async def event_stream() -> StreamingResponse:
    """SSE endpoint for live container status updates."""

    async def generate():
        while True:
            result = _run_docker(
                "ps",
                "-a",
                "--filter",
                "label=com.centurylinklabs.watchtower.enable=true",
                "--format",
                "{{.Names}}\t{{.State}}",
            )
            data: list[dict[str, str]] = []
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        data.append({"name": parts[0], "state": parts[1]})

            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/config")
async def get_app_config() -> dict[str, Any]:
    """Return the current app-config.json for the frontend."""
    config_path = os.path.join(_config_dir, "app-config.json")
    if not os.path.isfile(config_path):
        raise HTTPException(status_code=404, detail="app-config.json not found")
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def _mount_frontend() -> None:
    """Mount the static web dashboard at ``/`` replicating the nginx layout."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    www_dir = os.path.join(base, ".resources", ".www")
    assets_dir = os.path.join(base, ".resources", ".assets")

    if os.path.isdir(assets_dir):
        app.mount("/.images", StaticFiles(directory=assets_dir), name="assets")
    if os.path.isdir(www_dir):
        app.mount("/", StaticFiles(directory=www_dir, html=True), name="frontend")


def start_server(host: str = "0.0.0.0", port: int = 8088) -> None:
    """Start the dashboard API server."""
    import uvicorn

    configure(_config_dir)
    _mount_frontend()
    logger.info("Starting M4B Dashboard API on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")
