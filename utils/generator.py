import logging
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from typing import Any

import yaml  # Import PyYAML

from utils.checker import check_img_arch_support, get_compatible_tag
from utils.dumper import write_json
from utils.helper import show_spinner
from utils.loader import load_json_config

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


def substitute_port_placeholders(
    port_placeholders: list[str], actual_ports: list[int]
) -> list[str]:
    """
    Substitute port placeholders with actual port values.

    Args:
        port_placeholders (list[str]): List of port placeholders in format
            "${ENV_VAR}:container_port".
        actual_ports (list[int]): List of actual port numbers to use.

    Returns:
        list[str]: List of port mappings in format "host_port:container_port".

    Raises:
        ValueError: If actual_ports is empty.
    """
    if not actual_ports:
        raise ValueError("actual_ports cannot be empty")

    new_ports = []
    for idx, port_placeholder in enumerate(port_placeholders):
        # Extract env var name from placeholder
        match = re.match(r"\$\{([^}]+)\}:(\d+)", port_placeholder)
        if match:
            container_port = match.group(2)
            # Use indexed port if available, otherwise fallback to first port
            host_port = (
                actual_ports[idx] if idx < len(actual_ports) else actual_ports[0]
            )
            new_ports.append(f"{host_port}:{container_port}")
        else:
            # If not a placeholder, keep as is
            new_ports.append(port_placeholder)
    return new_ports


def validate_uuid(uuid: str, length: int) -> bool:
    """
    Validate a UUID against the specified length.

    Args:
        uuid (str): The UUID to validate.
        length (int): The expected length of the UUID.

    Returns:
        bool: True if the UUID is valid, False otherwise.
    """
    if (
        not isinstance(uuid, str)
        or len(uuid) != length
        or not re.match(f"[0-9a-f]{{{length}}}", uuid)
    ):
        return False
    return True


def generate_uuid(length: int) -> str:
    """
    Generate a UUID of the specified length.

    Args:
        length (int): The length of the UUID to generate.

    Returns:
        str: The generated UUID.
    """
    return str(os.urandom(length // 2 + 1).hex())[:length]


def assemble_docker_compose(
    m4b_config_path_or_dict: Any,
    app_config_path_or_dict: Any,
    user_config_path_or_dict: Any,
    compose_output_path: str = str(os.path.join(os.getcwd(), "docker-compose.yaml")),
    is_main_instance: bool = False,
) -> None:
    """
    Assemble a Docker Compose file based on the app and user configuration.

    Args:
        m4b_config_path_or_dict (Any): The path to the m4b configuration file or the config dictionary.
        app_config_path_or_dict (Any): The path to the app configuration file or the config dictionary.
        user_config_path_or_dict (Any): The path to the user configuration file or the config dictionary.
        compose_output_path (str, optional): The path to save the assembled docker-compose.yaml file. Defaults to './docker-compose.yaml'.
        is_main_instance (bool, optional): Whether this is the main instance. Defaults to False.

    Raises:
        Exception: If an error occurs during the assembly process.
    """
    event = threading.Event()
    spinner_thread = threading.Thread(
        target=show_spinner, args=("Assembling Docker Compose file...", event)
    )
    spinner_thread.start()

    try:
        m4b_config = load_json_config(m4b_config_path_or_dict)
        app_config = load_json_config(app_config_path_or_dict)
        user_config = load_json_config(user_config_path_or_dict)

        default_docker_platform = m4b_config["system"].get(
            "default_docker_platform", "linux/amd64"
        )
        proxy_enabled = user_config["proxies"].get("enabled", False)

        services = {}
        disabled_apps_due_to_incompatibility = []
        apps_categories = ["apps"]
        # Overrides extra apps exclusion from m4b proxies instances
        apps_categories.append("extra-apps")
        if is_main_instance:
            apps_categories.append("extra-apps")

        # Collect ports for proxy service if proxy is enabled
        proxy_ports = []
        # Dictionary to keep track of which app ports have been added to proxy
        app_ports_transferred = {}

        for category in apps_categories:
            for app in app_config.get(category, []):
                app_name = app["name"].lower()
                user_app_config = user_config["apps"].get(app_name, {})
                if user_app_config.get("enabled"):
                    # Copy the app's compose configuration to avoid modifying the original
                    app_compose_config = app["compose_config"].copy()
                    # Substitute port placeholders with actual values
                    if "ports" in app_compose_config and "ports" in user_app_config:
                        app_compose_config["ports"] = substitute_port_placeholders(
                            app_compose_config["ports"], user_app_config["ports"]
                        )
                    image = app_compose_config["image"]
                    image_name, image_tag = image.split(":")
                    docker_platform = user_app_config.get(
                        "docker_platform", default_docker_platform
                    )

                    if not check_img_arch_support(
                        image_name, image_tag, docker_platform
                    ):
                        compatible_tag = get_compatible_tag(image_name, docker_platform)
                        if compatible_tag:
                            app_compose_config["image"] = (
                                f"{image_name}:{compatible_tag}"
                            )
                            # Add platform also on all already compatible images tags
                            app_compose_config["platform"] = docker_platform
                            logging.info(
                                f"Updated {app_name} to compatible tag: {compatible_tag}"
                            )
                        else:
                            logging.warning(
                                f"No compatible tag found for {image_name} with architecture {docker_platform}. Searching for a suitable tag for default emulation architecture {default_docker_platform}."
                            )
                            # find a compatibile tag with default docker platform
                            compatible_tag = get_compatible_tag(
                                image_name, default_docker_platform
                            )
                            if compatible_tag:
                                app_compose_config["image"] = (
                                    f"{image_name}:{compatible_tag}"
                                )
                                # Add platform to the compose configuration to force image pull for emulation
                                app_compose_config["platform"] = default_docker_platform
                                logging.warning(
                                    f"Compatible tag found to run {image_name} with emulation on {default_docker_platform} architecture. Using binfmt emulation for {app_name} with image {image_name}:{image_tag}"
                                )
                            else:
                                error_msg = (
                                    f"No compatible tag found for {image_name} either with "
                                    f"specified architecture {docker_platform} or with default "
                                    f"architecture {default_docker_platform}."
                                )
                                logging.error(error_msg)
                                logging.error(
                                    f"Please check the image tag and architecture compatibility "
                                    f"on the registry. Disabling {app_name}..."
                                )
                                user_app_config["enabled"] = False
                                user_config["apps"][app_name] = user_app_config
                                write_json(user_config, user_config_path_or_dict)
                                logging.info(
                                    f"{app_name} has been disabled in user-config.json due to lack of compatible image tag."
                                )
                                disabled_apps_due_to_incompatibility.append(app_name)
                                continue  # Do not add the app to the compose file
                    else:
                        # Add platform also on all already compatible images tags
                        app_compose_config["platform"] = docker_platform

                    if proxy_enabled:
                        app_proxy_compose = app.get("compose_config_proxy", {})

                        # If using proxy's network, we can't publish ports directly
                        if app_proxy_compose.get("network_mode", "").startswith(
                            "service:"
                        ):
                            # If the app has ports and will use proxy, collect them for the proxy service
                            if "ports" in app_compose_config:
                                logging.info(
                                    f"Moving ports from {app_name} to proxy service as it's using proxy network"
                                )

                                # Track which app's ports are being transferred to proxy
                                app_ports_transferred[app_name] = True

                                # Check if 'ports' is a list or a single value
                                if isinstance(app_compose_config["ports"], list):
                                    for port_mapping in app_compose_config["ports"]:
                                        # Only add if the port mapping contains a variable that's defined
                                        if "${" in str(port_mapping) and "}" in str(
                                            port_mapping
                                        ):
                                            env_var = (
                                                str(port_mapping)
                                                .split(":")[0]
                                                .strip("${}")
                                            )
                                            # Check if this app is enabled (we already know it is at this point)
                                            # and if it has the port defined in user_config
                                            if user_app_config.get("ports"):
                                                proxy_ports.append(port_mapping)
                                                logging.info(
                                                    f"Added port mapping {port_mapping} to proxy from {app_name}"
                                                )
                                        else:
                                            # For static port mappings
                                            proxy_ports.append(port_mapping)
                                            logging.info(
                                                f"Added static port mapping {port_mapping} to proxy from {app_name}"
                                            )
                                else:
                                    # For single port value
                                    port_mapping = app_compose_config["ports"]
                                    if "${" in str(port_mapping) and "}" in str(
                                        port_mapping
                                    ):
                                        env_var = (
                                            str(port_mapping).split(":")[0].strip("${}")
                                        )
                                        # Check if this app is enabled and has the port defined
                                        if user_app_config.get("ports"):
                                            proxy_ports.append(port_mapping)
                                            logging.info(
                                                f"Added port mapping {port_mapping} to proxy from {app_name}"
                                            )
                                    else:
                                        # For static port mapping
                                        proxy_ports.append(port_mapping)
                                        logging.info(
                                            f"Added static port mapping {port_mapping} to proxy from {app_name}"
                                        )

                                # Remove ports from the app config since they're now handled by the proxy
                                del app_compose_config["ports"]

                        # Apply all other proxy-specific configurations
                        for key, value in app_proxy_compose.items():
                            app_compose_config[key] = value
                            if app_compose_config[key] is None:
                                del app_compose_config[key]

                    services[app_name] = app_compose_config

        # Add common services only if this is the main instance
        compose_config_common = user_config.get("compose_config_common", {})
        if is_main_instance:
            watchtower_service_key = (
                "proxy_enabled" if proxy_enabled else "proxy_disabled"
            )
            watchtower_service = compose_config_common["watchtower_service"][
                watchtower_service_key
            ]
            services["watchtower"] = watchtower_service
            # Only add m4bwebdashboard if dashboard is enabled
            m4b_dashboard_config = user_config.get("m4b_dashboard", {})
            if m4b_dashboard_config.get("enabled", False):
                services["m4bwebdashboard"] = compose_config_common[
                    "m4b_dashboard_service"
                ]

        if proxy_enabled:
            # Get the base proxy service configuration
            proxy_service = compose_config_common["proxy_service"].copy()

            # Add collected ports from apps to the proxy service
            if proxy_ports:
                # If 'ports' key not in the proxy service, create it
                if "ports" not in proxy_service:
                    proxy_service["ports"] = []
                elif not isinstance(proxy_service["ports"], list):
                    # If it's not a list, convert it to one
                    proxy_service["ports"] = [proxy_service["ports"]]

                # IMPORTANT: Remove any existing dashboard port from the proxy service ports
                dashboard_port = "${M4B_DASHBOARD_PORT}:80"
                if dashboard_port in proxy_service["ports"]:
                    proxy_service["ports"].remove(dashboard_port)
                    logging.info(
                        "Removed existing dashboard port mapping from proxy service"
                    )

                # Add required ports from enabled apps
                for port_mapping in proxy_ports:
                    if port_mapping not in proxy_service["ports"]:
                        proxy_service["ports"].append(port_mapping)

                # Dashboard port handling based on instance type
                if is_main_instance and user_config["m4b_dashboard"].get("enabled"):
                    # Only add dashboard port to proxy service if using proxy AND dashboard is enabled
                    if proxy_enabled and not app_ports_transferred.get(
                        "m4bwebdashboard"
                    ):
                        # Add the dashboard port to proxy service
                        proxy_service["ports"].append(dashboard_port)
                        logging.info(
                            "Added M4B dashboard port mapping to proxy service for main instance"
                        )

                        # If we're adding dashboard port to proxy, we should remove 'ports' entirely from the dashboard service
                        if (
                            "m4bwebdashboard" in services
                            and "ports" in services["m4bwebdashboard"]
                        ):
                            del services["m4bwebdashboard"]["ports"]
                            logging.info(
                                "Removed ports key from m4bwebdashboard service as it's handled by proxy"
                            )
                else:
                    logging.info(
                        "Skipping dashboard port mapping for multiproxy instance to avoid conflicts"
                    )

                logging.info(
                    f"Added {len(proxy_ports)} port mappings to the proxy service from apps using its network"
                )

            services["proxy"] = proxy_service

        # Define network configuration using config json and environment variables
        # This is a hybrid solution to remember that it could be possible to ditch the env file and generate all compose file parts from config json
        network_config = {
            "networks": {
                "default": {
                    "driver": compose_config_common["network"]["driver"],
                    "ipam": {
                        "config": [
                            {
                                "subnet": f"{compose_config_common['network']['subnet']}/{compose_config_common['network']['netmask']}"
                            }
                        ]
                    },
                }
            }
        }

        # Create the compose dictionary
        compose_dict = {"services": services}

        # Append network configuration at the bottom
        compose_dict.update(network_config)

        with open(compose_output_path, "w") as f:
            yaml.dump(compose_dict, f, sort_keys=False, default_flow_style=False)
        logging.info(
            f"Docker Compose file assembled and saved to {compose_output_path}"
        )
        if disabled_apps_due_to_incompatibility:
            # disable the apps and save updated config

            # inform the user
            print(
                "\nThe following apps were disabled due to image tag/architecture incompatibility with this device:"
            )
            for app in disabled_apps_due_to_incompatibility:
                print(f"- {app}")
            time.sleep(2 * m4b_config.get("system", {}).get("sleep_time", 2))
    except Exception as e:
        logging.error(f"Error during Docker Compose assembly: {e}")
        raise
    finally:
        event.set()
        spinner_thread.join()


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
        m4b_dashboard_name = "m4b_dashboard"
        m4b_dashboard_config = user_config.get(m4b_dashboard_name, {})
        if m4b_dashboard_config.get("enabled", False):
            for key, value in m4b_dashboard_config.items():
                if key == "ports":
                    # Ports are stored as a list, extract the first port for M4B_DASHBOARD_PORT
                    port_value = value[0] if isinstance(value, list) and value else value
                    env_lines.append(f"{m4b_dashboard_name.upper()}_PORT={port_value}")
                else:
                    env_lines.append(
                        f"{m4b_dashboard_name.upper()}_{key.upper()}={value}"
                    )

        # Add proxy configurations
        proxy_config = user_config.get("proxies", {})
        for key, value in proxy_config.items():
            env_lines.append(f"STACK_PROXY_{key.upper()}={value}")

        # Add notification configurations if enabled
        notifications_config = user_config.get("notifications", {})
        if notifications_config.get("enabled"):
            for key, value in notifications_config.items():
                env_lines.append(f"WATCHTOWER_NOTIFICATION_{key.upper()}={value}")

        # Add app-specific configurations only if the app is enabled
        apps_categories = ["apps"]
        if is_main_instance:
            apps_categories.append("extra-apps")
        for category in apps_categories:
            for app in app_config.get(category, []):
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
        logging.info(f".env file generated and saved to {env_output_path}")
    finally:
        event.set()
        spinner_thread.join()


def generate_dashboard_urls(
    compose_project_name: str,
    device_name: str,
    env_file: str = str(os.path.join(os.getcwd(), ".env")),
) -> None:
    """
    Generate dashboard URLs based on the provided compose project name and device name.
    If the parameters are not provided, it tries to read them from the .env file.
    The generated dashboard URLs are written to a file named "dashboards_URLs_<compose_project_name>-<device_name>.txt".

    Args:
        compose_project_name (str): The name of the compose project.
        device_name (str): The name of the device.
        env_file (str, optional): The path to the environment file. Defaults to ".env".

    Raises:
        Exception: If an error occurs during the URL generation process.
    """
    event = threading.Event()
    spinner_thread = threading.Thread(
        target=show_spinner, args=("Generating dashboard URLs...", event)
    )
    spinner_thread.start()

    try:
        if not compose_project_name or not device_name:
            if os.path.isfile(env_file):
                logging.info(
                    "Reading COMPOSE_PROJECT_NAME and DEVICE_NAME from .env file..."
                )
                with open(env_file) as f:
                    for line in f:
                        if "COMPOSE_PROJECT_NAME" in line:
                            compose_project_name = line.split("=")[1].strip()
                        if "DEVICE_NAME" in line:
                            device_name = line.split("=")[1].strip()
            else:
                logging.error("Error: Parameters not provided and .env file not found.")
                return

        if not compose_project_name or not device_name:
            logging.error(
                "Error: COMPOSE_PROJECT_NAME and DEVICE_NAME must be provided."
            )
            return

        dashboard_file = f"dashboards_URLs_{compose_project_name}-{device_name}.txt"
        with open(dashboard_file, "w") as f:
            f.write(f"------ Dashboards {compose_project_name}-{device_name} ------\n")

        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Ports}} {{.Names}}"],
            check=False,
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            container_info = line.split()[-1]
            port_mapping = re.search(r"0.0.0.0:(\d+)->", line)
            if port_mapping:
                with open(dashboard_file, "a") as f:
                    f.write(
                        f"If enabled you can visit the {container_info} web dashboard on http://localhost:{port_mapping.group(1)}\n"
                    )

        logging.info(f"Dashboard URLs have been written to {dashboard_file}")
    finally:
        event.set()
        spinner_thread.join()


def generate_device_name(
    adjectives: list,
    animals: list,
    device_name: str = "",
    use_uuid_suffix: bool = False,
) -> str:
    """
    Generate a device name from given word lists. If a device name is provided, it will be used.
    Optionally, a random UUID suffix can be added.

    Args:
        adjectives (list): List of adjectives.
        animals (list): List of animals.
        device_name (str, optional): Optional device name to use. Defaults to "".
        use_uuid_suffix (bool, optional): Flag to determine whether to add a UUID suffix. Defaults to False.

    Returns:
        str: The generated or provided device name.
    """
    if not device_name:
        adjective = secrets.choice(adjectives)
        animal = secrets.choice(animals)
        device_name = f"{adjective}_{animal}"

    if use_uuid_suffix:
        uuid_suffix = generate_uuid(4)
        device_name = f"{device_name}_{uuid_suffix}"

    return device_name


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Regenerate docker-compose.yaml and .env files from existing configuration.

    This is the menu entry point for regenerating files without going through
    the full setup wizard.

    Args:
        app_config_path: Path to the app configuration file.
        m4b_config_path: Path to the m4b configuration file.
        user_config_path: Path to the user configuration file.
    """
    import shutil

    from colorama import Fore, Style

    from utils.prompt_helper import ask_question_yn

    print(f"\n{Fore.CYAN}=== Regenerate Files from Configuration ==={Style.RESET_ALL}")
    print("This will regenerate docker-compose.yaml and .env files")
    print("based on your current configuration.")

    if not os.path.exists(user_config_path):
        print(f"{Fore.RED}Error: User config not found.{Style.RESET_ALL}")
        print("Please run 'Setup Apps' first to create the initial configuration.")
        input("\nPress Enter to go back to main menu...")
        return

    try:
        m4b_config = load_json_config(m4b_config_path)
        app_config = load_json_config(app_config_path)
        user_config = load_json_config(user_config_path)
    except Exception as e:
        print(f"{Fore.RED}Error loading config files: {e}{Style.RESET_ALL}")
        input("\nPress Enter to go back to main menu...")
        return

    # Show summary
    print(f"\n{Fore.BLUE}Current Configuration:{Style.RESET_ALL}")
    device = user_config.get("device_info", {}).get("device_name", "Unknown")
    proxy = user_config.get("proxies", {}).get("enabled", False)
    dash = user_config.get("m4b_dashboard", {})
    dash_on = dash.get("enabled", False)
    dash_port = dash.get("ports", [8081])[0] if dash.get("ports") else 8081

    print(f"  Device: {device}")
    print(f"  Proxy: {'Enabled' if proxy else 'Disabled'}")
    print(f"  Dashboard: {'Port ' + str(dash_port) if dash_on else 'Disabled'}")

    # Count enabled apps
    enabled = []
    for cat in ["apps", "extra-apps"]:
        apps = user_config.get(cat, {})
        if isinstance(apps, dict):
            for name, cfg in apps.items():
                if isinstance(cfg, dict) and cfg.get("enabled"):
                    enabled.append(name)
    print(f"  Enabled Apps ({len(enabled)}): {', '.join(enabled) if enabled else 'None'}")

    # Check for multiproxy instances
    instances_dir = "m4b_proxy_instances"
    has_instances = os.path.exists(instances_dir) and os.listdir(instances_dir)
    instance_dirs = []
    if has_instances:
        instance_dirs = [
            d for d in os.listdir(instances_dir)
            if os.path.isdir(os.path.join(instances_dir, d))
        ]
        print(f"  Multiproxy Instances: {len(instance_dirs)}")

    # Check if containers are running
    containers_running = False
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={device}", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            containers_running = True
            running_count = len(result.stdout.strip().split('\n'))
            print(f"\n{Fore.YELLOW}⚠ {running_count} container(s) currently running{Style.RESET_ALL}")
    except Exception:
        pass  # Docker check failed, continue anyway

    print()
    if not ask_question_yn("Regenerate files with this configuration?"):
        print("Cancelled.")
        input("\nPress Enter to go back to main menu...")
        return

    # Create backup of existing files
    backup_dir = ".backup"
    os.makedirs(backup_dir, exist_ok=True)
    files_to_backup = ["docker-compose.yaml", ".env"]
    backed_up = []

    for filename in files_to_backup:
        if os.path.exists(filename):
            backup_path = os.path.join(backup_dir, filename)
            try:
                shutil.copy2(filename, backup_path)
                backed_up.append(filename)
            except Exception as e:
                logging.warning(f"Could not backup {filename}: {e}")

    if backed_up:
        print(f"{Fore.BLUE}Backed up: {', '.join(backed_up)} → {backup_dir}/{Style.RESET_ALL}")

    try:
        # Regenerate main instance files
        print(f"\n{Fore.CYAN}Regenerating docker-compose.yaml...{Style.RESET_ALL}")
        assemble_docker_compose(
            m4b_config_path_or_dict=m4b_config,
            app_config_path_or_dict=app_config,
            user_config_path_or_dict=user_config,
            compose_output_path="./docker-compose.yaml",
            is_main_instance=True,
        )
        print(f"{Fore.GREEN}✓ docker-compose.yaml regenerated{Style.RESET_ALL}")

        print(f"{Fore.CYAN}Regenerating .env file...{Style.RESET_ALL}")
        generate_env_file(
            m4b_config_path_or_dict=m4b_config,
            app_config_path_or_dict=app_config,
            user_config_path_or_dict=user_config,
            env_output_path="./.env",
            is_main_instance=True,
        )
        print(f"{Fore.GREEN}✓ .env file regenerated{Style.RESET_ALL}")

        # Handle multiproxy instances
        if has_instances and instance_dirs:
            print(f"\n{Fore.YELLOW}Multiproxy instances detected: {len(instance_dirs)}{Style.RESET_ALL}")
            if ask_question_yn("Regenerate multiproxy instance files too?", default=True):
                for instance_name in instance_dirs:
                    instance_path = os.path.join(instances_dir, instance_name)
                    instance_user_config = os.path.join(instance_path, "user-config.json")
                    instance_app_config = os.path.join(instance_path, "app-config.json")
                    instance_m4b_config = os.path.join(instance_path, "m4b-config.json")
                    instance_compose = os.path.join(instance_path, "docker-compose.yaml")
                    instance_env = os.path.join(instance_path, ".env")

                    if not os.path.exists(instance_user_config):
                        print(f"{Fore.YELLOW}  Skipping {instance_name}: no user-config.json{Style.RESET_ALL}")
                        continue

                    # Backup instance files
                    instance_backup = os.path.join(instance_path, ".backup")
                    os.makedirs(instance_backup, exist_ok=True)
                    for f in ["docker-compose.yaml", ".env"]:
                        src = os.path.join(instance_path, f)
                        if os.path.exists(src):
                            try:
                                shutil.copy2(src, os.path.join(instance_backup, f))
                            except Exception:
                                pass

                    try:
                        # Use main configs if instance-specific ones don't exist
                        i_app_cfg = instance_app_config if os.path.exists(instance_app_config) else app_config_path
                        i_m4b_cfg = instance_m4b_config if os.path.exists(instance_m4b_config) else m4b_config_path

                        print(f"{Fore.CYAN}  Regenerating {instance_name}...{Style.RESET_ALL}")
                        assemble_docker_compose(
                            m4b_config_path_or_dict=i_m4b_cfg,
                            app_config_path_or_dict=i_app_cfg,
                            user_config_path_or_dict=instance_user_config,
                            compose_output_path=instance_compose,
                            is_main_instance=False,
                        )
                        generate_env_file(
                            m4b_config_path_or_dict=i_m4b_cfg,
                            app_config_path_or_dict=i_app_cfg,
                            user_config_path_or_dict=instance_user_config,
                            env_output_path=instance_env,
                            is_main_instance=False,
                        )
                        print(f"{Fore.GREEN}  ✓ {instance_name} regenerated{Style.RESET_ALL}")
                    except Exception as e:
                        print(f"{Fore.RED}  ✗ {instance_name} failed: {e}{Style.RESET_ALL}")
                        logging.error(f"Error regenerating instance {instance_name}: {e}")

        print(f"\n{Fore.GREEN}Done!{Style.RESET_ALL}")

        # Offer to restart if containers are running
        if containers_running:
            print(f"\n{Fore.YELLOW}Containers are running with old configuration.{Style.RESET_ALL}")
            if ask_question_yn("Restart stack now to apply changes?"):
                print(f"{Fore.CYAN}Restarting stack...{Style.RESET_ALL}")
                try:
                    subprocess.run(["docker", "compose", "down"], check=True)
                    subprocess.run(["docker", "compose", "up", "-d"], check=True)
                    print(f"{Fore.GREEN}✓ Stack restarted successfully{Style.RESET_ALL}")
                except subprocess.CalledProcessError as e:
                    print(f"{Fore.RED}Error restarting stack: {e}{Style.RESET_ALL}")
            else:
                print("Remember to restart your stack to apply changes.")
        else:
            print("Start your stack to use the new configuration.")

    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        logging.error(f"Error regenerating files: {e}")
        if backed_up:
            print(f"{Fore.YELLOW}Your previous files are backed up in {backup_dir}/{Style.RESET_ALL}")

    input("\nPress Enter to go back to main menu...")