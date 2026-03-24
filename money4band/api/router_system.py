"""System info & DNS API."""

from __future__ import annotations

import logging
import platform
from typing import Any

import psutil
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from money4band.api._deps import (
    ConfigPaths,
    get_paths,
    load_m4b_config,
    load_user_config,
)
from money4band.api.schemas import DnsConfig, DnsSet, SystemInfo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/info", response_model=SystemInfo)
async def system_info(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return system information: OS, arch, memory, CPU, Docker version."""
    from money4band.detector import detect_architecture, detect_os

    m4b = load_m4b_config()
    usr = load_user_config()

    mem = psutil.virtual_memory()
    cores = psutil.cpu_count(logical=False)

    os_info = detect_os(m4b)
    arch_info = detect_architecture(m4b)
    device = usr.get("device_info", {})

    enabled_apps = [
        name
        for name, cfg in usr.get("apps", {}).items()
        if isinstance(cfg, dict) and cfg.get("enabled")
    ]

    return {
        "platform": platform.platform(),
        "os_type": os_info.get("os_type", ""),
        "architecture": arch_info.get("arch", ""),
        "docker_arch": arch_info.get("dkarch", ""),
        "total_ram_mb": round(mem.total / (1024**2)),
        "available_ram_mb": round(mem.available / (1024**2)),
        "cpu_cores": cores,
        "device_name": device.get("device_name", ""),
        "project_version": m4b.get("project", {}).get("project_version", ""),
        "enabled_apps": len(enabled_apps),
    }


@router.get("/dns", response_model=DnsConfig)
async def get_dns(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return the current DNS configuration."""
    from money4band.system_info import get_dns_config

    m4b = load_m4b_config()
    return get_dns_config(m4b)


class DnsUpdate(BaseModel):
    """DNS configuration update."""

    mode: str
    servers: list[str] | None = None


@router.put("/dns", response_model=DnsSet)
async def set_dns(
    payload: DnsUpdate,
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, str]:
    """Update the DNS configuration."""
    from money4band.system_info import get_dns_modes, set_dns_mode

    m4b = load_m4b_config()
    valid_modes = get_dns_modes(m4b)
    if payload.mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{payload.mode}'. Valid: {', '.join(valid_modes)}",
        )
    set_dns_mode(paths.m4b_config, payload.mode, servers=payload.servers)
    return {"status": "ok", "mode": payload.mode}
