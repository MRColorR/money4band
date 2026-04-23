"""FastAPI backend for the M4B web dashboard.

Provides REST endpoints for container status, resource stats, health
indicators, quick actions (start/stop/restart), and full M4B control
via modular API routers.

Run standalone:  ``m4b dashboard [--port 8088]``
"""

from __future__ import annotations

import asyncio
import collections
import hashlib
import hmac
import json
import logging
import os
import subprocess
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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

# OpenAPI security scheme — shows the "Authorize" padlock in Swagger UI.
_bearer_scheme = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "description": (
            "Paste the API key shown at dashboard startup "
            "(or via `m4b dashboard show-key`)."
        ),
    }
}

app = FastAPI(
    title="M4B Dashboard API",
    version="2.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    swagger_ui_init_oauth={},
    openapi_tags=None,
)

# Inject the security scheme into the generated OpenAPI spec so Swagger
# renders an "Authorize" button where users can enter their Bearer token.
_original_openapi = app.openapi


def _custom_openapi():  # type: ignore[no-untyped-def]
    if app.openapi_schema:
        return app.openapi_schema
    schema = _original_openapi()
    schema.setdefault("components", {}).setdefault("securitySchemes", {}).update(
        _bearer_scheme
    )
    # Apply globally — every endpoint requires it (middleware handles actual auth).
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi  # type: ignore[method-assign]

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Add standard security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------------------
# Rate limiting — per-IP sliding window, 60 requests / minute.
# ---------------------------------------------------------------------------

_RATE_LIMIT = 60  # max requests per window
_RATE_WINDOW = 60.0  # window size in seconds
_rate_log: dict[str, collections.deque[float]] = {}


@app.middleware("http")
async def _rate_limit_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Enforce a per-IP rate limit on API endpoints.

    Loopback clients are exempt — the threat model targets remote access.
    """
    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    # Rate limit only applies when the server is exposed to the network.
    # On localhost-only binding, brute-force from remote IPs is impossible.
    if not _exposed or client_ip in _LOOPBACK:
        return await call_next(request)
    now = time.monotonic()
    timestamps = _rate_log.setdefault(client_ip, collections.deque())

    # Evict entries outside the sliding window.
    while timestamps and timestamps[0] < now - _RATE_WINDOW:
        timestamps.popleft()

    # GC: remove empty deques so the dict doesn't grow unboundedly.
    if not timestamps:
        del _rate_log[client_ip]
        timestamps = _rate_log.setdefault(client_ip, collections.deque())

    if len(timestamps) >= _RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
        )

    timestamps.append(now)
    return await call_next(request)


# ---------------------------------------------------------------------------
# API-key auth — auto-generated, stored in user-config, localhost exempt.
# ---------------------------------------------------------------------------

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})
_PUBLIC_PREFIXES = (
    "/api/docs",
    "/api/openapi.json",
    "/api/auth/login",
    "/docs",
    "/openapi.json",
)

# Populated by configure() from user-config or freshly generated.
_api_key: str = ""

# True when the server is bound to a non-loopback address (0.0.0.0, LAN IP, …).
# When exposed, the auth middleware NEVER skips auth even if no key is set
# it will reject all non-localhost requests with 401.
_exposed: bool = False


def _get_session_salt() -> bytes:
    """Return a per-installation random salt, creating it if needed.

    Stored at ``~/.m4b/session.salt`` (32 bytes, hex-encoded on disk).
    This ensures session tokens are unique per M4B installation.
    """
    salt_path = os.path.join(os.path.expanduser("~"), ".m4b", "session.salt")
    try:
        with open(salt_path, "rb") as f:
            return bytes.fromhex(f.read().decode().strip())
    except (OSError, ValueError):
        pass
    salt = os.urandom(32)
    os.makedirs(os.path.dirname(salt_path), exist_ok=True)
    fd = os.open(salt_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, salt.hex().encode())
    finally:
        os.close(fd)
    return salt


def _derive_session_token(api_key: str) -> str:
    """Derive a one-way session token from the API key.

    Uses a per-installation random salt so tokens are not predictable
    across installations.  Includes an epoch-hour component so tokens
    roll every 24 hours even if the cookie ``max_age`` is bypassed.
    """
    salt = _get_session_salt()
    epoch_day = str(int(time.time()) // 86400)
    payload = f"{api_key}:{epoch_day}".encode()
    return hmac.new(salt, payload, hashlib.sha256).hexdigest()


def _derive_session_token_previous(api_key: str) -> str:
    """Derive session token for the *previous* epoch-day (grace window)."""
    salt = _get_session_salt()
    epoch_day = str(int(time.time()) // 86400 - 1)
    payload = f"{api_key}:{epoch_day}".encode()
    return hmac.new(salt, payload, hashlib.sha256).hexdigest()


def is_exposed() -> bool:
    """Return True when the server is bound to a non-loopback address."""
    return _exposed


@app.middleware("http")
async def _auth_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Require ``Authorization: Bearer <key>`` for non-localhost API calls."""
    path = request.url.path

    # Always allow non-API routes (static frontend), docs, and health.
    if not path.startswith("/api/") or path.startswith(_PUBLIC_PREFIXES):
        return await call_next(request)

    # Localhost is trusted when binding to loopback only.
    client_host = request.client.host if request.client else ""
    if not _exposed and client_host in _LOOPBACK:
        return await call_next(request)

    # If no key configured and we're NOT exposed, auth is disabled
    # (fresh install / tests).  When exposed, always require a key.
    if not _api_key:
        if _exposed:
            return JSONResponse(
                status_code=401,
                content={"detail": "API key required (server is exposed)"},
            )
        return await call_next(request)

    # All callers must supply a valid token (header or cookie).
    auth = request.headers.get("authorization", "")
    if hmac.compare_digest(auth, f"Bearer {_api_key}"):
        return await call_next(request)

    cookie_token = request.cookies.get("m4b_token", "")
    expected_session = _derive_session_token(_api_key)
    if hmac.compare_digest(cookie_token, expected_session):
        return await call_next(request)
    # Grace window: accept tokens from the previous epoch-day so users
    # aren't force-logged-out at the exact day boundary.
    expected_prev = _derive_session_token_previous(_api_key)
    if hmac.compare_digest(cookie_token, expected_prev):
        return await call_next(request)

    return JSONResponse(status_code=401, content={"detail": "Unauthorized"})


# ---------------------------------------------------------------------------
# Cookie-based auth for the web frontend
# ---------------------------------------------------------------------------


class _LoginPayload(BaseModel):
    token: str


@app.post("/api/auth/login", tags=["auth"])
async def login(payload: _LoginPayload) -> JSONResponse:
    """Validate the API key and set an ``m4b_token`` session cookie."""
    if not _api_key or not hmac.compare_digest(payload.token, _api_key):
        return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    response = JSONResponse(content={"status": "ok"})
    response.set_cookie(
        key="m4b_token",
        value=_derive_session_token(_api_key),
        httponly=True,
        samesite="strict",
        secure=_exposed,
        max_age=86400,
        path="/",
    )
    return response


@app.post("/api/auth/logout", tags=["auth"])
async def logout() -> JSONResponse:
    """Clear the ``m4b_token`` session cookie."""
    response = JSONResponse(content={"status": "ok"})
    response.delete_cookie(key="m4b_token", path="/")
    return response


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
    global _config_dir, _api_key
    _config_dir = config_dir
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    configure_paths(config_dir=config_dir, base_dir=base_dir)

    # Load API key from user-config if present (do NOT generate here).
    user_cfg_path = os.path.join(config_dir, "user-config.json")
    try:
        from money4band.core.loader import load_json_config

        cfg = load_json_config(user_cfg_path)
        _api_key = cfg.get("m4b_dashboard", {}).get("api_key", "")
    except Exception:  # noqa: BLE001
        _api_key = ""


def ensure_api_key(config_dir: str) -> str:
    """Generate and persist an API key if one doesn't exist yet.

    Delegates to ``dashboard_setup.ensure_api_key_on_disk`` and syncs
    the module-level ``_api_key`` used by the auth middleware.
    """
    global _api_key
    if _api_key:
        return _api_key

    from money4band.dashboard.setup import ensure_api_key_on_disk

    key = ensure_api_key_on_disk(config_dir)
    _api_key = key
    return key


def regenerate_api_key(config_dir: str) -> str:
    """Force-regenerate the API key and update the auth middleware."""
    global _api_key
    from money4band.dashboard.setup import regenerate_api_key_on_disk

    key = regenerate_api_key_on_disk(config_dir)
    if key:
        _api_key = key
    return key


def _run_docker_sync(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a docker command and return the result (blocking)."""
    cmd = ["docker"] + list(args)
    return subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, timeout=30
    )


async def _run_docker(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a docker command off the event loop."""
    import asyncio

    return await asyncio.to_thread(_run_docker_sync, *args)


@app.get("/api/status")
async def get_status() -> dict[str, Any]:
    """Return status of M4B containers plus Docker availability info.

    When Docker is unreachable or no M4B containers exist the response
    still provides useful context (``docker_available``, ``containers``).
    """
    try:
        result = await _run_docker(
            "ps",
            "-a",
            "--filter",
            "label=com.centurylinklabs.watchtower.enable=true",
            "--format",
            "{{.Names}}\t{{.Status}}\t{{.State}}\t{{.Ports}}",
        )
    except Exception:
        return {
            "docker_available": False,
            "error": "Docker is not reachable",
            "containers": [],
        }

    if result.returncode != 0:
        logger.error("docker ps failed: %s", result.stderr.strip())
        return {
            "docker_available": True,
            "error": "Failed to list containers",
            "containers": [],
        }

    containers: list[dict[str, Any]] = []
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

    return {"docker_available": True, "containers": containers}


@app.get("/api/health")
async def get_health() -> list[dict[str, Any]]:
    """Return health status for all M4B containers via docker inspect."""
    result = await _run_docker(
        "ps",
        "-a",
        "-q",
        "--filter",
        "label=com.centurylinklabs.watchtower.enable=true",
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []

    ids = result.stdout.strip().splitlines()
    inspect_result = await _run_docker(
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
    result = await _run_docker(
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

    result = await _run_docker(action, container)
    if result.returncode != 0:
        logger.error(
            "Docker %s %s failed: %s", action, container, result.stderr.strip()
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to {action} container '{container}'"
        )

    return {"status": "ok", "action": action, "container": container}


@app.get("/api/events")
async def event_stream() -> StreamingResponse:
    """SSE endpoint for live container status updates."""

    async def generate():
        while True:
            result = await _run_docker(
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


def _mount_frontend() -> None:
    """Mount the static web dashboard at ``/``."""
    from money4band.resources import get_path

    www_dir = get_path("www")
    assets_dir = get_path("assets")

    if assets_dir.is_dir():
        app.mount("/.images", StaticFiles(directory=str(assets_dir)), name="assets")
    if www_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(www_dir), html=True), name="frontend")


def find_dashboard_port(preferred: int = 8088) -> int:
    """Return *preferred* if free, otherwise the next available port.

    Uses the shared :func:`networker.find_next_available_port` helper so
    the behaviour is consistent with the rest of the project.
    """
    from money4band.network.networker import is_port_in_use

    if not is_port_in_use(preferred):
        return preferred

    from money4band.network.networker import find_next_available_port

    return find_next_available_port(preferred + 1)


def start_server(
    host: str = "127.0.0.1",
    port: int = 8088,
) -> None:
    """Start the dashboard API server.

    Parameters
    ----------
    host:
        Bind address.  Defaults to ``127.0.0.1`` (localhost only).
        Pass ``0.0.0.0`` to expose on all interfaces (LAN / VPS).
    port:
        Preferred port.  If the port is occupied an alternative is
        chosen automatically and a warning is logged.
    """
    import uvicorn

    global _exposed
    _exposed = host not in ("127.0.0.1", "::1", "localhost")

    configure(_config_dir)
    _mount_frontend()

    # Always verify port availability.
    resolved = find_dashboard_port(port)
    if resolved != port:
        logger.warning("Port %d in use — falling back to %d", port, resolved)
    port = resolved

    # Generate / load API key for remote access.
    key = ensure_api_key(_config_dir)
    if key:
        logger.info("Dashboard API key: %s…", key[:8])

    if _exposed and not key:
        logger.warning(
            "Server is exposed on %s but no API key is configured — "
            "generating one automatically.",
            host,
        )
        key = regenerate_api_key(_config_dir)

    logger.info("Starting M4B Dashboard API on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")
