from __future__ import annotations

"""Multi-proxy instance setup, subnet calculation, and directory management for M4B."""

import logging
import os
import platform
import shutil
import stat
import time
from copy import deepcopy
from typing import Any

from collections.abc import Callable

from colorama import Fore, Style

from utils.dumper import write_json
from utils.fn_stopStack import stop_all_stacks
from utils.generator import (
    assemble_docker_compose,
    generate_env_file,
    generate_uuid,
)
from utils.loader import (
    get_active_app_categories,
    get_category_entries,
    get_install_limit,
    load_json_config,
)

logger = logging.getLogger(__name__)
from utils.port_manager import assign_app_ports, collect_assigned_ports
from utils.prompt_helper import ask_question_yn


def remove_readonly(func: Callable[..., Any], path: str, excinfo: object) -> None:
    """
    Error handler for Windows readonly file removal.

    Args:
        func: The function that raised the exception
        path: The path to the file/directory
        excinfo: Exception information
    """
    # Clear the readonly bit and reattempt the removal
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        logger.warning(f"Could not remove {path}: {str(e)}")


def safe_rmtree(directory: str) -> bool:
    """
    Safely remove a directory tree, handling Windows permission issues.

    Args:
        directory (str): Path to the directory to remove

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if platform.system().lower() == "windows":
            # On Windows, use onerror callback to handle readonly files
            shutil.rmtree(directory, onerror=remove_readonly)
        else:
            shutil.rmtree(directory)
        logger.info(f"Successfully removed directory: {directory}")
        return True
    except PermissionError as e:
        logger.error(f"Permission denied when removing {directory}: {str(e)}")
        print(
            f"{Fore.RED}Permission denied when removing {directory}. Please ensure no files are in use and you have proper permissions.{Style.RESET_ALL}"
        )
        return False


def cleanup_multiproxy_instances_dir(
    instances_dir: str = "m4b_proxy_instances",
    backup_root: str = ".backup",
) -> None:
    """
    Clean up multiproxy instances directory when multiproxy is disabled.

    Behavior:
    - If directory does not exist: no-op
    - If directory is empty: remove it
    - If directory has content: move it to a timestamped backup folder

    Args:
        instances_dir (str): Path to multiproxy instances directory.
        backup_root (str): Path to backup root directory.
    """
    if not os.path.isdir(instances_dir):
        logger.info("No multiproxy instances directory found. Nothing to clean up.")
        return

    try:
        entries = os.listdir(instances_dir)
    except Exception as e:
        logger.error(
            f"Unable to inspect multiproxy instances directory '{instances_dir}': {str(e)}"
        )
        return

    if not entries:
        if safe_rmtree(instances_dir):
            print(
                f"{Fore.GREEN}Removed empty multiproxy instances directory '{instances_dir}'.{Style.RESET_ALL}"
            )
            logger.info(
                f"Removed empty multiproxy instances directory '{instances_dir}'."
            )
        return

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_base_dir = os.path.join(backup_root, "m4b_proxy_instances")
    os.makedirs(backup_base_dir, exist_ok=True)
    backup_dir = os.path.join(backup_base_dir, f"instances_{timestamp}")

    suffix = 1
    while os.path.exists(backup_dir):
        backup_dir = os.path.join(backup_base_dir, f"instances_{timestamp}_{suffix}")
        suffix += 1

    try:
        shutil.move(instances_dir, backup_dir)
        print(
            f"{Fore.YELLOW}Multiproxy disabled: moved existing instances to '{backup_dir}'.{Style.RESET_ALL}"
        )
        logger.info(
            f"Multiproxy disabled. Moved '{instances_dir}' to backup '{backup_dir}'."
        )
    except Exception as e:
        logger.error(
            f"Failed to move multiproxy instances directory '{instances_dir}' to backup: {str(e)}"
        )
        print(
            f"{Fore.RED}Failed to back up multiproxy instances directory '{instances_dir}'.{Style.RESET_ALL}"
        )


def ipv4_to_int(ip_address: str) -> int:
    """
    Convert an IPv4 address string to an integer representation.

    Args:
        ip_address (str): IPv4 address in dotted decimal notation (e.g., "192.168.1.0").

    Returns:
        int: Integer representation of the IP address.
    """
    octets = ip_address.split(".")
    return sum(int(octet) << (8 * (3 - i)) for i, octet in enumerate(octets))


def int_to_ipv4(ip_int: int) -> str:
    """
    Convert an integer to an IPv4 address string.

    Args:
        ip_int (int): Integer representation of an IP address.

    Returns:
        str: IPv4 address in dotted decimal notation (e.g., "192.168.1.0").
    """
    return ".".join(str((ip_int >> (8 * (3 - i))) & 0xFF) for i in range(4))


def calculate_subnet(base_subnet: str, base_netmask: int, offset: int) -> str:
    """
    Calculate a new subnet by applying an offset to a base subnet.

    The offset is applied based on the subnet size derived from the netmask.

    Args:
        base_subnet (str): The base subnet address (e.g., "172.19.7.0").
        base_netmask (int): The CIDR netmask value (e.g., 27).
        offset (int): The offset to apply (e.g., 1 for the first proxied instance).

    Returns:
        str: The new subnet address string.
    """
    base_int = ipv4_to_int(base_subnet)
    subnet_size = 2 ** (32 - base_netmask)
    new_int = base_int + subnet_size * offset
    return int_to_ipv4(new_int)


def regenerate_uuids_for_apps(
    user_config: dict[str, Any], app_config: dict[str, Any]
) -> None:
    """
    Regenerate UUIDs for apps that require them, preserving prefixes or postfixes if defined.

    Args:
        user_config (dict): The user configuration dictionary.
        app_config (dict): The app configuration dictionary.
    """
    for app_category in get_active_app_categories(app_config):
        for app in get_category_entries(app_config, app_category):
            app_name = app["name"].lower()
            app_user_config = user_config["apps"].get(app_name, {})

            # Check if the app has a UUID flag and is enabled
            if app_user_config.get("enabled") and "uuid" in app.get("flags", {}):
                uuid_length = app["flags"]["uuid"].get(
                    "length", 32
                )  # Default to 32 if not specified
                prefix = app["flags"]["uuid"].get("prefix", "")
                postfix = app["flags"]["uuid"].get("postfix", "")

                # Generate the new UUID part
                new_uuid_part = generate_uuid(uuid_length)
                new_uuid = f"{prefix}{new_uuid_part}{postfix}"

                app_user_config["uuid"] = new_uuid
                logger.info(f"Generated new UUID for {app_name}: {new_uuid}")


def setup_multiproxy_instances(
    user_config: dict[str, Any],
    app_config: dict[str, Any],
    m4b_config: dict[str, Any],
    proxies: list[str],
) -> None:
    """
    Setup multiple proxy instances based on the given proxies list.

    Args:
        user_config (dict): The user configuration dictionary.
        app_config (dict): The app configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
        proxies (list): List of proxy configurations.
    """
    # Load sleep_time from config
    sleep_time = m4b_config.get("system", {}).get("sleep_time", 3)

    instances_dir = "m4b_proxy_instances"
    os.makedirs(instances_dir, exist_ok=True)

    base_device_name = user_config["device_info"]["device_name"]
    base_project_name = m4b_config.get("project", {}).get(
        "compose_project_name", "money4band"
    )

    # Track used device names to ensure uniqueness
    used_device_names = {base_device_name}  # Start with the main device name
    # Start with the main project name
    used_project_names = {base_project_name}

    print(
        f"{Fore.BLUE}Base device name for instances: {base_device_name}{Style.RESET_ALL}"
    )
    logger.info(f"Base device name for proxy instances: {base_device_name}")

    base_subnet = m4b_config["network"]["subnet"]
    base_netmask = int(m4b_config["network"]["netmask"])

    if os.listdir(instances_dir):
        if ask_question_yn(
            f"Existing proxy instances found in '{instances_dir}'. Do you want to delete them?",
            default=True,
        ):
            stop_all_stacks(instances_dir, skip_questions=True)
            if not safe_rmtree(instances_dir):
                print(
                    f"{Fore.RED}Failed to remove existing instances. Aborting setup.{Style.RESET_ALL}"
                )
                time.sleep(sleep_time)
                return
            os.makedirs(instances_dir, exist_ok=True)
        else:
            print(
                f"{Fore.YELLOW}Keeping existing instances alongside new ones.{Style.RESET_ALL}"
            )

    # Keep a global reservation set to avoid collisions with existing/main/new instances.
    reserved_ports = collect_assigned_ports(user_config)

    # --- Install-limit enforcement ---
    enforce_limits = m4b_config.get("system", {}).get(
        "enforce_install_limits", True
    )
    # Total instances = proxies list + 1 main instance.
    total_instances = len(proxies) + 1
    app_limits: dict[str, int] = {}  # app_name -> limit (-1 = unlimited)
    limited_apps: dict[str, int] = {}  # app_name -> limit (only those exceeded)

    if enforce_limits:
        for cat_key in get_active_app_categories(app_config):
            for entry in get_category_entries(app_config, cat_key):
                name = entry["name"].lower()
                limit = get_install_limit(entry)
                app_limits[name] = limit
                if limit >= 0 and total_instances > limit:
                    limited_apps[name] = limit
    else:
        print(
            f"{Fore.YELLOW}Install-limit enforcement is DISABLED. "
            f"All apps will run on every instance.{Style.RESET_ALL}"
        )
        logger.info("Install-limit enforcement disabled by user.")

    if limited_apps:
        print(
            f"{Fore.YELLOW}Install limits: {total_instances} instances requested "
            f"(1 main + {len(proxies)} proxies).{Style.RESET_ALL}"
        )
        for app_name, limit in sorted(limited_apps.items()):
            print(
                f"  {Fore.YELLOW}{app_name.upper()}: max {limit} instances "
                f"— will be disabled in instances beyond #{limit}{Style.RESET_ALL}"
            )
        logger.info(
            "Install-limit enforcement: %s",
            {k: v for k, v in limited_apps.items()},
        )

    for existing_instance in os.listdir(instances_dir):
        existing_user_cfg = os.path.join(
            instances_dir, existing_instance, "user-config.json"
        )
        if os.path.isfile(existing_user_cfg):
            try:
                existing_config = load_json_config(existing_user_cfg)
                reserved_ports.update(collect_assigned_ports(existing_config))
            except Exception as e:
                logger.warning(
                    f"Failed to preload ports from existing instance '{existing_instance}': {e}"
                )

    for i, proxy in enumerate(proxies):
        logger.info(f"Creating instance {i + 1}/{len(proxies)} with proxy: {proxy}")
        instance_user_config = deepcopy(user_config)
        instance_m4b_config = deepcopy(m4b_config)
        instance_app_config = deepcopy(app_config)

        # Generate a unique suffix for device and project names
        while True:
            suffix = generate_uuid(4)
            instance_device_name = f"{base_device_name}_{suffix}"
            instance_project_name = f"{base_project_name}_{suffix}"

            # Ensure the device name and project name are unique
            if (
                instance_device_name not in used_device_names
                and instance_project_name not in used_project_names
            ):
                used_device_names.add(instance_device_name)
                used_project_names.add(instance_project_name)
                break

        print(
            f"{Fore.GREEN}Created proxy instance {i + 1} with device name: {instance_device_name}{Style.RESET_ALL}"
        )
        logger.info(
            f"Created proxy instance with unique device name: {instance_device_name}"
        )

        instance_dir = os.path.join(instances_dir, instance_project_name)
        os.makedirs(instance_dir, exist_ok=True)

        instance_user_config["device_info"]["device_name"] = instance_device_name
        instance_m4b_config["project"]["compose_project_name"] = instance_project_name

        instance_user_config["proxies"]["url"] = proxy
        instance_user_config["proxies"]["enabled"] = True

        # Calculate unique subnet for this instance
        new_subnet = calculate_subnet(base_subnet, base_netmask, i + 1)

        instance_m4b_config["network"]["subnet"] = new_subnet

        # Update all enabled apps with unique ports using the unified assignment logic
        # Track port_app_index separately - only incremented for apps WITH ports
        # Instance number for limit check: main = 0, proxy instances = 1..N
        instance_number = i + 1
        port_app_index = 0
        for app_category in get_active_app_categories(app_config):
            for app_details in get_category_entries(instance_app_config, app_category):
                app_name = app_details["name"].lower()
                app_config_entry = instance_user_config["apps"].get(app_name, {})

                # Enforce install_limit: disable app if this instance exceeds it
                limit = app_limits.get(app_name, -1)
                if limit >= 0 and instance_number >= limit:
                    if app_config_entry.get("enabled", False):
                        app_config_entry["enabled"] = False
                        logger.info(
                            "Disabled %s in instance %d (limit: %d)",
                            app_name, instance_number, limit,
                        )
                    continue

                # Only process enabled apps
                if app_details.get("enabled", False) or (
                    app_config_entry and app_config_entry.get("enabled", False)
                ):
                    logger.info(
                        f"Processing port assignments for {app_name} "
                        f"in instance {instance_project_name}"
                    )

                    # If app isn't in user_config yet, initialize it
                    if not app_config_entry:
                        instance_user_config["apps"][app_name] = {"enabled": True}
                        app_config_entry = instance_user_config["apps"][app_name]

                    # Check if this app has ports defined in compose_config
                    if (
                        "compose_config" in app_details
                        and "ports" in app_details["compose_config"]
                    ):
                        # Use unified port assignment logic (instance number = i+1)
                        assigned_ports = assign_app_ports(
                            app_name,
                            app_details,
                            app_config_entry,
                            app_index=port_app_index,
                            instance_number=i + 1,
                            reserved_ports=reserved_ports,
                        )
                        app_config_entry["ports"] = assigned_ports
                        logger.info(
                            f"Assigned ports for {app_name} in instance "
                            f"{instance_project_name}: {assigned_ports}"
                        )
                        # Only increment port_app_index for apps that have ports
                        port_app_index += 1

        # Properly disable dashboard for multiproxy instances to avoid port conflicts
        if "m4b_dashboard" in instance_user_config:
            instance_user_config["m4b_dashboard"]["enabled"] = False
            # Remove dashboard port to ensure it's not included anywhere in multiproxy instances
            if "ports" in instance_user_config["m4b_dashboard"]:
                del instance_user_config["m4b_dashboard"]["ports"]

            # Also completely remove dashboard port from proxy_service configuration ports
            if (
                "compose_config_common" in instance_user_config
                and "proxy_service" in instance_user_config["compose_config_common"]
                and "ports"
                in instance_user_config["compose_config_common"]["proxy_service"]
            ):
                # Get ports configuration
                ports = instance_user_config["compose_config_common"]["proxy_service"][
                    "ports"
                ]

                # Filter out any dashboard port references
                if isinstance(ports, list):
                    dashboard_port = "${M4B_DASHBOARD_PORT}:80"
                    ports = [port for port in ports if port != dashboard_port]
                    instance_user_config["compose_config_common"]["proxy_service"][
                        "ports"
                    ] = ports
                    logger.info(
                        f"Filtered out dashboard port from proxy_service configuration for multiproxy instance {instance_project_name}"
                    )

            logger.info(
                f"Completely disabled dashboard for multiproxy instance {instance_project_name} to avoid port conflicts"
            )

        # Regenerate UUIDs for apps that require them
        regenerate_uuids_for_apps(instance_user_config, instance_app_config)

        instance_user_config_path = os.path.join(instance_dir, "user-config.json")
        instance_m4b_config_path = os.path.join(instance_dir, "m4b-config.json")
        instance_app_config_path = os.path.join(instance_dir, "app-config.json")

        write_json(instance_user_config, instance_user_config_path)
        write_json(instance_m4b_config, instance_m4b_config_path)
        write_json(instance_app_config, instance_app_config_path)

        assemble_docker_compose(
            instance_m4b_config_path,
            instance_app_config_path,
            instance_user_config_path,
            compose_output_path=os.path.join(instance_dir, "docker-compose.yaml"),
        )
        generate_env_file(
            instance_m4b_config_path,
            instance_app_config_path,
            instance_user_config_path,
            env_output_path=os.path.join(instance_dir, ".env"),
        )

    print(
        f"{Fore.GREEN}Created {len(proxies)} proxy instances with unique device names.{Style.RESET_ALL}"
    )
    print(f"{Fore.GREEN}Multiproxy instances setup completed.{Style.RESET_ALL}")
    time.sleep(sleep_time)
