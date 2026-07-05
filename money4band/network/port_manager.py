from __future__ import annotations

"""Port assignment and collection utilities for M4B apps."""

import logging
import os
from typing import Any

from money4band.core import loader
from money4band.network.networker import find_next_available_port

logger = logging.getLogger(__name__)

# __file__ is money4band/network/port_manager.py; the config dir lives at the
# project root, two levels up (package root, then repo root), not inside the
# package. A single ".." pointed at a nonexistent money4band/config and made
# port constants silently fall back to defaults.
_m4b_config_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "config",
    "m4b-config.json",
)

# Lazy-loaded port constants - populated on first access via _load_port_constants()
DEFAULT_PORT_BASE: int = 0
PORT_OFFSET_PER_APP: int = 0
PORT_OFFSET_PER_INSTANCE: int = 0
_port_constants_loaded = False


def _load_port_constants() -> None:
    """Load port constants from config on first use."""
    global \
        DEFAULT_PORT_BASE, \
        PORT_OFFSET_PER_APP, \
        PORT_OFFSET_PER_INSTANCE, \
        _port_constants_loaded
    if _port_constants_loaded:
        return
    try:
        cfg = loader.load_json_config(_m4b_config_path)
    except FileNotFoundError:
        cfg = {}
        logger.warning("Configuration file not found. Using default port values.")
    ports = cfg.get("ports", {})
    DEFAULT_PORT_BASE = ports.get("default_port_base", 50000)
    PORT_OFFSET_PER_APP = ports.get("port_offset_per_app", 100)
    PORT_OFFSET_PER_INSTANCE = ports.get("port_offset_per_instance", 10)
    _port_constants_loaded = True


def collect_assigned_ports(user_config: dict[str, Any]) -> set[int]:
    """
    Collect already assigned app ports from a user configuration.

    Only ports from enabled apps are considered.

    Args:
        user_config (dict[str, Any]): The user configuration dictionary.

    Returns:
        set[int]: Set of already assigned host ports.
    """
    used_ports: set[int] = set()
    apps_config = user_config.get("apps", {})
    if not isinstance(apps_config, dict):
        return used_ports

    for app_cfg in apps_config.values():
        if not isinstance(app_cfg, dict) or not app_cfg.get("enabled", False):
            continue

        ports_value = app_cfg.get("ports", [])
        if not isinstance(ports_value, list):
            ports_value = [ports_value]

        for port in ports_value:
            try:
                used_ports.add(int(port))
            except (TypeError, ValueError):
                logger.debug(f"Skipping non-numeric port value in config: {port}")

    return used_ports


def assign_app_ports(
    app_name: str,
    app: dict[str, Any],
    config: dict[str, Any],
    app_index: int = 0,
    instance_number: int = 0,
    reserved_ports: set[int] | None = None,
) -> list[int]:
    """
    Assign available ports for an app based on its configuration using consistent offset logic.

    This function uses a unified formula for both main and multiproxy instances:
    port = DEFAULT_PORT_BASE + (app_index * PORT_OFFSET_PER_APP) + (instance_number * PORT_OFFSET_PER_INSTANCE) + port_within_app_offset

    Args:
        app_name (str): Name of the app
        app (dict[str, Any]): App configuration containing compose_config
        config (dict[str, Any]): User configuration for the app
        app_index (int, optional): Zero-based index of the app in the apps list. Defaults to 0.
        instance_number (int, optional): Instance number (0 for main, 1+ for multiproxy). Defaults to 0.
        reserved_ports (set[int] | None, optional): Set of ports to exclude. Defaults to None.

    Returns:
        list[int]: List of assigned available ports
    """
    port_count = len(app["compose_config"]["ports"])
    assigned_ports: list[int] = []
    reserved_ports = reserved_ports or set()
    _load_port_constants()

    # Calculate the base port for this specific app and instance using the unified formula
    base_port_for_app_instance = (
        DEFAULT_PORT_BASE
        + (app_index * PORT_OFFSET_PER_APP)
        + (instance_number * PORT_OFFSET_PER_INSTANCE)
    )

    for i in range(port_count):
        # For apps with multiple ports, add a small offset for each additional port
        port_candidate = base_port_for_app_instance + i
        excluded_ports = assigned_ports + list(reserved_ports)

        # Find next available port starting from the calculated candidate
        available_port = find_next_available_port(
            port_candidate, exclude_ports=excluded_ports
        )
        assigned_ports.append(available_port)
        reserved_ports.add(available_port)

        # Log the port assignment
        port_placeholder = (
            app["compose_config"]["ports"][i]
            if "ports" in app["compose_config"]
            and i < len(app["compose_config"]["ports"])
            else f"port_{i + 1}"
        )
        logger.info(
            f"Port {port_placeholder} for {app_name} (app_index={app_index}, instance={instance_number}) set to: {available_port}"
        )

    return assigned_ports
