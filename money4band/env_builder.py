from __future__ import annotations

"""Environment file generation — builds .env from configuration."""

import logging
import os
import threading
from typing import Any

from money4band.helper import show_spinner
from money4band.loader import get_active_app_categories, get_category_entries, load_json_config



logger = logging.getLogger(__name__)
def generate_env_file(
    m4b_config_path_or_dict: Any,
    app_config_path_or_dict: Any,
    user_config_path_or_dict: Any,
    env_output_path: str = str(os.path.join(os.getcwd(), ".env")),
    is_main_instance: bool = False,
) -> None:
    """
    Generate a .env file based on the m4b and user configuration.

    Args:
        m4b_config_path_or_dict (Any): The path to the m4b configuration file or the config dictionary.
        app_config_path_or_dict (Any): The path to the app configuration file or the config dictionary.
        user_config_path_or_dict (Any): The path to the user configuration file or the config dictionary.
        env_output_path (str, optional): The path to save the generated .env file. Defaults to './.env'.
        is_main_instance (bool, optional): Whether this is the main instance. Defaults to False.

    Raises:
        Exception: If an error occurs during the file generation process.
    """
    event = threading.Event()
    spinner_thread = threading.Thread(
        target=show_spinner, args=("Generating .env file...", event)
    )
    spinner_thread.start()

    try:
        m4b_config = load_json_config(m4b_config_path_or_dict)
        app_config = load_json_config(app_config_path_or_dict)
        user_config = load_json_config(user_config_path_or_dict)

        env_lines = []

        # Add project and system configurations
        project_config = m4b_config.get("project", {})
        for key, value in project_config.items():
            env_lines.append(f"{key.upper()}={value}")

        # Add resource limits configurations
        resource_limits_config = user_config.get("resource_limits", {})
        for key, value in resource_limits_config.items():
            env_lines.append(f"{key.upper()}={value}")

        # Add network configurations
        network_config = m4b_config.get("network", {})
        for key, value in network_config.items():
            env_lines.append(f"NETWORK_{key.upper()}={value}")

        # Add user and device configurations
        device_info = user_config.get("device_info", {})
        for key, value in device_info.items():
            env_lines.append(f"{key.upper()}={value}")

        # Add m4b_dashboard configurations ONLY if enabled
        m4b_dashboard_config = user_config.get("m4b_dashboard", {})
        if m4b_dashboard_config.get("enabled", False):
            for key, value in m4b_dashboard_config.items():
                if key == "ports":
                    # Ports are stored as a list, extract the first port for M4B_DASHBOARD_PORT
                    port_value = (
                        value[0] if isinstance(value, list) and value else value
                    )
                    env_lines.append(f"M4B_DASHBOARD_PORT={port_value}")
                elif key != "enabled":  # Skip the enabled flag
                    env_lines.append(f"M4B_DASHBOARD_{key.upper()}={value}")

        # Add proxy configurations
        proxy_config = user_config.get("proxies", {})
        for key, value in proxy_config.items():
            env_lines.append(f"STACK_PROXY_{key.upper()}={value}")

        # Add notification configurations if enabled
        notifications_config = user_config.get("notifications", {})
        if notifications_config.get("enabled"):
            for key, value in notifications_config.items():
                env_lines.append(f"WATCHTOWER_NOTIFICATION_{key.upper()}={value}")

        # Add Watchtower label scoping configuration
        watchtower_config = m4b_config.get("watchtower", {})
        watchtower_labels_enabled = watchtower_config.get("enable_labels", True)
        watchtower_scope = watchtower_config.get("scope", "money4band")
        env_lines.append(
            f"M4B_WATCHTOWER_LABELS={'true' if watchtower_labels_enabled else 'false'}"
        )
        env_lines.append(f"M4B_WATCHTOWER_SCOPE={watchtower_scope}")

        # Add app-specific configurations only if the app is enabled
        apps_categories = get_active_app_categories(app_config)
        for category in apps_categories:
            for app in get_category_entries(app_config, category):
                app_name = app["name"].upper()
                app_lower = app["name"].lower()
                app_flags = app.get("flags", {})
                app_user_config = user_config["apps"].get(app_lower, {})
                if app_user_config.get("enabled", False):
                    for flag_name in app_flags.keys():
                        if flag_name in app_user_config:
                            env_var_name = f"{app_name}_{flag_name.upper()}"
                            env_var_value = app_user_config[flag_name]
                            env_lines.append(f"{env_var_name}={env_var_value}")

                    # Add ports configurations for apps that have them
                    if "dashboard_port" in app_user_config:
                        env_lines.append(
                            f"{app_name.upper()}_DASHBOARD_PORT={app_user_config['dashboard_port']}"
                        )
                    if "ports" in app_user_config:
                        # Ports are always stored as a list
                        ports = app_user_config["ports"]
                        if not isinstance(ports, list):
                            ports = [ports]  # Convert to list for consistency
                        for i, port in enumerate(ports):
                            env_lines.append(f"{app_name.upper()}_PORT_{i + 1}={port}")
                            # For backward compatibility, also add non-indexed variable for single port
                            if len(ports) == 1:
                                env_lines.append(f"{app_name.upper()}_PORT={port}")
                                env_lines.append(f"{app_lower.upper()}_PORT={port}")

        # Write to .env file
        with open(env_output_path, "w") as f:
            f.write("\n".join(env_lines))
        logger.info(f".env file generated and saved to {env_output_path}")
    finally:
        event.set()
        spinner_thread.join()
