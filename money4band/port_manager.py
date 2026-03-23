from __future__ import annotations

"""Port assignment and collection utilities for M4B apps."""

import logging
import os
import sys
from typing import Any

from money4band.networker import find_next_available_port

# Ensure the parent directory is in the sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from money4band import loader


logger = logging.getLogger(__name__)
# Global config loading for port constants
m4b_config_path = os.path.join(parent_dir, "config", "m4b-config.json")
try:
    _m4b_config = loader.load_json_config(m4b_config_path)
except FileNotFoundError:
    _m4b_config = {}
    logger.warning("Configuration file not found. Using default port values.")

DEFAULT_PORT_BASE = _m4b_config.get("ports", {}).get("default_port_base", 50000)
PORT_OFFSET_PER_APP = _m4b_config.get("ports", {}).get("port_offset_per_app", 100)
PORT_OFFSET_PER_INSTANCE = _m4b_config.get("ports", {}).get(
    "port_offset_per_instance", 10
)


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
    assigned_ports = []
    reserved_ports = reserved_ports or set()

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
