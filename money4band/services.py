"""Service layer — UI-agnostic wrappers around M4B business logic.

Each function here encapsulates one logical operation that both the legacy
CLI menu and the new Textual TUI can call.  All heavy I/O (subprocess,
file writes) lives in the existing modules; this layer only coordinates.
"""

from __future__ import annotations

import io
import logging
import os
from contextlib import redirect_stdout
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_config_paths(
    config_dir: str | None = None,
) -> tuple[str, str, str]:
    """Return (m4b_config_path, app_config_path, user_config_path)."""
    config_dir = config_dir or os.path.join(_BASE_DIR, "config")
    return (
        os.path.join(config_dir, "m4b-config.json"),
        os.path.join(config_dir, "app-config.json"),
        os.path.join(config_dir, "user-config.json"),
    )


# ---------------------------------------------------------------------------
# Config loading (cached per call — keeps reactive data fresh)
# ---------------------------------------------------------------------------


def load_configs(
    m4b_path: str, app_path: str, user_path: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    from money4band.core.loader import load_json_config

    return (
        load_json_config(m4b_path),
        load_json_config(app_path),
        load_json_config(user_path),
    )


def load_m4b_config(m4b_path: str) -> dict[str, Any]:
    from money4band.core.loader import load_json_config

    return load_json_config(m4b_path)


# ---------------------------------------------------------------------------
# Menu items — service wrappers
# ---------------------------------------------------------------------------


def get_menu_items(m4b_config: dict[str, Any]) -> list[dict[str, str]]:
    """Return the menu list from m4b-config.json."""
    return m4b_config.get("menu", [])


def get_project_version(m4b_config: dict[str, Any]) -> str:
    return m4b_config.get("project", {}).get("project_version", "?")


def get_discord_url(m4b_config: dict[str, Any]) -> str:
    return m4b_config.get("project", {}).get("ds_project_server_url", "")


# ---------------------------------------------------------------------------
# System info
# ---------------------------------------------------------------------------


def get_system_info_text(
    m4b_config: dict[str, Any],
    app_config: dict[str, Any],
    user_config: dict[str, Any],
) -> str:
    """Capture system_info dashboard output as a string."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        from money4band.system.info import show_system_info

        show_system_info(m4b_config, app_config, user_config)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Docker operations (blocking — run in a worker thread)
# ---------------------------------------------------------------------------


def is_docker_installed() -> bool:
    from money4band.docker.install import is_docker_installed as _check

    return _check()


def start_stack(
    compose_file: str | list[str] = "./docker-compose.yaml",
    env_file: str = "./.env",
    instance_name: str = "money4band",
    profiles: tuple[str, ...] = (),
) -> bool:
    from money4band.docker.start import start_stack as _start

    return _start(
        compose_file=compose_file,
        env_file=env_file,
        instance_name=instance_name,
        skip_questions=True,
        profiles=profiles,
    )


def stop_stack(
    compose_file: str | list[str] = "./docker-compose.yaml",
    instance_name: str = "money4band",
) -> bool:
    from money4band.docker.stop import stop_stack as _stop

    return _stop(
        compose_file=compose_file,
        instance_name=instance_name,
        skip_questions=True,
    )


def start_all_stacks(
    main_compose_file: str | list[str] = "./docker-compose.yaml",
    main_env_file: str = "./.env",
    main_instance_name: str = "money4band",
    instances_dir: str = "m4b_proxy_instances",
    profiles: tuple[str, ...] = (),
) -> str:
    """Start all stacks, capture stdout."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        from money4band.docker.start import start_all_stacks as _start_all

        _start_all(
            main_compose_file=main_compose_file,
            main_env_file=main_env_file,
            main_instance_name=main_instance_name,
            instances_dir=instances_dir,
            skip_questions=True,
            profiles=profiles,
        )
    return buf.getvalue()


def stop_all_stacks(
    main_compose_file: str | list[str] = "./docker-compose.yaml",
    main_instance_name: str = "money4band",
    instances_dir: str = "m4b_proxy_instances",
) -> str:
    """Stop all stacks, capture stdout."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        from money4band.docker.stop import stop_all_stacks as _stop_all

        _stop_all(
            main_compose_file=main_compose_file,
            main_instance_name=main_instance_name,
            instances_dir=instances_dir,
            skip_questions=True,
        )
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


def regenerate_files(
    app_config_path: str, m4b_config_path: str, user_config_path: str
) -> str:
    """Regenerate compose + env, capture stdout."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        from money4band.docker.generator import main as gen_main

        gen_main(app_config_path, m4b_config_path, user_config_path)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Stack status
# ---------------------------------------------------------------------------


def get_stack_status() -> str:
    """Get docker compose ps output."""
    import subprocess

    from money4band.docker.compose_builder import get_compose_files
    from money4band.docker.helper import get_compose_project_name

    compose_files = get_compose_files(_BASE_DIR)
    env_file = os.path.join(_BASE_DIR, ".env")

    if not compose_files:
        return "No compose files found. Run setup or generate first."

    cmd = ["docker", "compose"]
    if os.path.isfile(env_file):
        project_name = get_compose_project_name(env_file)
        if project_name:
            cmd.extend(["-p", project_name])
    for cf in compose_files:
        cmd.extend(["-f", cf])
    for profile in ("monitoring", "proxy"):
        cmd.extend(["--profile", profile])
    cmd.extend(["ps", "--format", "table"])

    result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
    if result.returncode == 0:
        return result.stdout
    return f"Error: {result.stderr.strip()}"


def get_health_summary() -> list[dict[str, Any]]:
    """Return container health summaries."""
    from money4band.docker.helper import get_compose_project_name
    from money4band.docker.monitor import get_stack_health

    env_file = os.path.join(_BASE_DIR, ".env")
    project_name = None
    if os.path.isfile(env_file):
        project_name = get_compose_project_name(env_file)

    statuses = get_stack_health(project_filter=project_name)
    return [
        {
            "name": s.name,
            "ok": s.ok,
            "health": s.health if s.health != "none" else "no-healthcheck",
            "restarts": s.restart_count,
            "error": s.last_error[:80] if s.last_error else "",
            "restart_loop": s.restart_count >= 5,
        }
        for s in statuses
    ]


# ---------------------------------------------------------------------------
# App catalog
# ---------------------------------------------------------------------------


def get_app_catalog_rich(app_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return category groups with active flag and per-app detail rows.

    Each element: {category, active, apps: [{name, link, layer, payout, reason}]}
    Sorted: active categories first.
    """
    from money4band.core.loader import (
        get_all_app_categories,
        get_category_entries,
        is_category_active,
    )

    all_cats = get_all_app_categories(app_config)
    active_cats = [c for c in all_cats if is_category_active(app_config, c)]
    inactive_cats = [c for c in all_cats if not is_category_active(app_config, c)]

    result: list[dict[str, Any]] = []
    for cat_key in active_cats + inactive_cats:
        entries = get_category_entries(app_config, cat_key)
        apps = []
        for e in entries:
            earnings = e.get("app_details", {}).get("earnings", {})
            apps.append(
                {
                    "name": e.get("name", "?"),
                    "link": e.get("link", ""),
                    "layer": e.get("compose_layer", "-"),
                    "payout": earnings.get("min_payout", "-"),
                    "reason": e.get("removal_reason", ""),
                }
            )
        result.append(
            {
                "category": cat_key,
                "active": is_category_active(app_config, cat_key),
                "apps": apps,
            }
        )
    return result


def get_app_catalog(app_config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Return apps grouped by category (legacy compat)."""
    result: dict[str, list[dict[str, Any]]] = {}
    for category_key in ("supported-apps", "deprecated-apps", "candidate-apps"):
        cat = app_config.get(category_key, {})
        entries = cat.get("entries", [])
        result[category_key] = entries
    return result


def get_system_info_structured(
    m4b_config: dict[str, Any],
    app_config: dict[str, Any],
    user_config: dict[str, Any],
) -> dict[str, Any]:
    """Return structured system info dict for the TUI."""
    import shutil

    from money4band.system import detector
    from money4band.system.info import get_dns_config
    from money4band.updater import check_for_update

    version = m4b_config.get("project", {}).get("project_version", "?")
    new_version = check_for_update(m4b_config)

    device = user_config.get("device_info", {})
    os_type = device.get("os_type", "unknown")
    arch = device.get("detected_architecture", "unknown")
    dk_arch = device.get("detected_docker_arch", "unknown")
    dk_platform = m4b_config.get("system", {}).get(
        "default_docker_platform", "linux/amd64"
    )

    active_profile = detector.get_active_profile(m4b_config)
    profile_def = detector.get_profile_definition(m4b_config, active_profile)
    try:
        total_mem, cores = detector.get_system_memory_and_cores()
    except Exception:
        total_mem, cores = 0, 0

    dns = get_dns_config(m4b_config)

    apps_cfg = user_config.get("apps", {})
    enabled_apps = [
        name
        for name, cfg in apps_cfg.items()
        if isinstance(cfg, dict) and cfg.get("enabled", False)
    ]
    total_supported = 0
    for cat in app_config.values():
        if isinstance(cat, dict) and cat.get("active", False):
            total_supported += len(cat.get("entries", []))

    proxy_enabled = user_config.get("proxies", {}).get("enabled", False)
    wt_enabled = user_config.get("watchtower", {}).get("enabled", True)
    dash_enabled = user_config.get("m4b_dashboard", {}).get("enabled", True)

    docker_ok = shutil.which("docker") is not None
    docker_running = False
    multiarch = False
    if docker_ok:
        from money4band.docker.helper import (
            is_docker_daemon_running,
            is_multiarch_emulation_available,
        )

        docker_running = is_docker_daemon_running()
        if docker_running:
            multiarch = is_multiarch_emulation_available()

    from money4band.docker.compose_builder import get_compose_files

    compose_files = get_compose_files(".")
    compose_mode = (
        "layered"
        if len(compose_files) > 1
        else ("monolithic" if compose_files else "none")
    )

    return {
        "version": version,
        "new_version": new_version,
        "os_type": os_type,
        "arch": arch,
        "dk_arch": dk_arch,
        "dk_platform": dk_platform,
        "docker_installed": docker_ok,
        "docker_running": docker_running,
        "multiarch": multiarch,
        "ram_mb": total_mem,
        "cpu_cores": cores,
        "active_profile": active_profile,
        "profile_desc": profile_def.get("description", ""),
        "dns_mode": dns.get("mode", "default"),
        "dns_servers": dns.get("servers", []),
        "enabled_apps": enabled_apps,
        "total_supported": total_supported,
        "proxy_enabled": proxy_enabled,
        "watchtower_enabled": wt_enabled,
        "dashboard_enabled": dash_enabled,
        "compose_mode": compose_mode,
        "compose_files": [os.path.basename(f) for f in compose_files],
    }


def get_generator_summary(
    m4b_config_path: str, app_config_path: str, user_config_path: str
) -> dict[str, Any]:
    """Return pre-generation config summary for the TUI."""
    from money4band.core.loader import load_json_config

    user = load_json_config(user_config_path)
    m4b = load_json_config(m4b_config_path)

    device_name = user.get("device_info", {}).get("device_name", "?")
    proxy_enabled = user.get("proxies", {}).get("enabled", False)
    apps_cfg = user.get("apps", {})
    enabled_apps = [
        name
        for name, cfg in apps_cfg.items()
        if isinstance(cfg, dict) and cfg.get("enabled", False)
    ]
    dash = user.get("m4b_dashboard", {})
    dash_port = dash.get("port", 8088) if dash.get("enabled") else None
    compose_mode = m4b.get("system", {}).get("compose_mode", "monolithic")

    # Count proxy instances
    instances_dir = os.path.join(_BASE_DIR, "m4b_proxy_instances")
    proxy_count = 0
    if os.path.isdir(instances_dir):
        proxy_count = len(
            [
                d
                for d in os.listdir(instances_dir)
                if os.path.isdir(os.path.join(instances_dir, d))
            ]
        )

    return {
        "device_name": device_name,
        "proxy_enabled": proxy_enabled,
        "dashboard_port": dash_port,
        "enabled_apps": enabled_apps,
        "compose_mode": compose_mode,
        "proxy_instances": proxy_count,
    }


# ---------------------------------------------------------------------------
# Update check
# ---------------------------------------------------------------------------


def check_update(m4b_config: dict[str, Any]) -> str | None:
    """Return new version string if available, else None."""
    from money4band.updater import check_for_update

    return check_for_update(m4b_config)


# ---------------------------------------------------------------------------
# Reset config
# ---------------------------------------------------------------------------


def reset_user_config(
    user_config_path: str,
    template_path: str | None = None,
) -> None:
    from money4band.core.reset import reset_config

    src = template_path or os.path.join(_BASE_DIR, "template", "user-config.json")
    reset_config(src, user_config_path)


# ---------------------------------------------------------------------------
# Farewell (non-destructive version for TUI)
# ---------------------------------------------------------------------------


def get_farewell_message(m4b_config: dict[str, Any]) -> str:
    """Return a random farewell message without calling sys.exit()."""
    import random

    words = m4b_config.get("project", {}).get("farewell_words", ["Goodbye!"])
    return random.choice(words)  # noqa: S311
