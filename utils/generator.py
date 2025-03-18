from utils.helper import show_spinner
from utils.dumper import write_json
from utils.loader import load_json_config
from utils.detector import detect_architecture
from utils.checker import check_img_arch_support, get_compatible_tag
import os
import subprocess
import sys
import argparse
import logging
import json
import re
from typing import Dict, Any, List
import yaml  # Import PyYAML
import secrets
import getpass
import threading

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


def validate_uuid(uuid: str, length: int) -> bool:
    """
    Validate a UUID against the specified length.

    Args:
        uuid (str): The UUID to validate.
        length (int): The expected length of the UUID.

    Returns:
        bool: True if the UUID is valid, False otherwise.
    """
    if not isinstance(uuid, str) or len(uuid) != length or not re.match('[0-9a-f]{{{}}}'.format(length), uuid):
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


def assemble_docker_compose(m4b_config_path_or_dict: Any, app_config_path_or_dict: Any, user_config_path_or_dict: Any, compose_output_path: str = str(os.path.join(os.getcwd(), 'docker-compose.yaml')), is_main_instance: bool = False) -> None:
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
    spinner_thread = threading.Thread(target=show_spinner, args=(
        "Assembling Docker Compose file...", event))
    spinner_thread.start()

    try:
        m4b_config = load_json_config(m4b_config_path_or_dict)
        app_config = load_json_config(app_config_path_or_dict)
        user_config = load_json_config(user_config_path_or_dict)

        default_docker_platform = m4b_config['system'].get(
            'default_docker_platform', 'linux/amd64')
        proxy_enabled = user_config['proxies'].get('enabled', False)

        services = {}
        apps_categories = ['apps']
        # Overrides extra apps exclusion from m4b proxies instances
        apps_categories.append('extra-apps')
        if is_main_instance:
            apps_categories.append('extra-apps')

        # Collect ports for proxy service if proxy is enabled
        proxy_ports = []
        # Dictionary to keep track of which app ports have been added to proxy
        app_ports_transferred = {}

        for category in apps_categories:
            for app in app_config.get(category, []):
                app_name = app['name'].lower()
                user_app_config = user_config['apps'].get(app_name, {})
                if user_app_config.get('enabled'):
                    # Copy the app's compose configuration to avoid modifying the original
                    app_compose_config = app['compose_config'].copy()
                    image = app_compose_config['image']
                    image_name, image_tag = image.split(':')
                    docker_platform = user_app_config.get(
                        'docker_platform', default_docker_platform)

                    if not check_img_arch_support(image_name, image_tag, docker_platform):
                        compatible_tag = get_compatible_tag(
                            image_name, docker_platform)
                        if compatible_tag:
                            app_compose_config['image'] = f"{image_name}:{compatible_tag}"
                            # Add platform also on all already compatible images tags
                            app_compose_config['platform'] = docker_platform
                            logging.info(
                                f"Updated {app_name} to compatible tag: {compatible_tag}")
                        else:
                            logging.warning(
                                f"No compatible tag found for {image_name} with architecture {docker_platform}. Searching for a suitable tag for default emulation architecture {default_docker_platform}.")
                            # find a compatibile tag with default docker platform
                            compatible_tag = get_compatible_tag(
                                image_name, default_docker_platform)
                            if compatible_tag:
                                app_compose_config['image'] = f"{image_name}:{compatible_tag}"
                                # Add platform to the compose configuration to force image pull for emulation
                                app_compose_config['platform'] = default_docker_platform
                                logging.warning(
                                    f"Compatible tag found to run {image_name} with emulation on {default_docker_platform} architecture. Using binfmt emulation for {app_name} with image {image_name}:{image_tag}")
                            else:
                                logging.error(
                                    f"No compatible tag found for {image_name} with default architecture {default_docker_platform}.")
                                logging.error(
                                    f"Please check the image tag and architecture compatibility on the registry. Skipping {app_name}...")
                                continue  # Do not add the app to the compose file
                    else:
                        # Add platform also on all already compatible images tags
                        app_compose_config['platform'] = docker_platform

                    if proxy_enabled:
                        app_proxy_compose = app.get('compose_config_proxy', {})

                        # If using proxy's network, we can't publish ports directly
                        if app_proxy_compose.get('network_mode', '').startswith('service:'):
                            # If the app has ports and will use proxy, collect them for the proxy service
                            if 'ports' in app_compose_config:
                                logging.info(
                                    f"Moving ports from {app_name} to proxy service as it's using proxy network")

                                # Track which app's ports are being transferred to proxy
                                app_ports_transferred[app_name] = True

                                # Check if 'ports' is a list or a single value
                                if isinstance(app_compose_config['ports'], list):
                                    for port_mapping in app_compose_config['ports']:
                                        # Only add if the port mapping contains a variable that's defined
                                        if "${" in str(port_mapping) and "}" in str(port_mapping):
                                            env_var = str(port_mapping).split(
                                                ':')[0].strip('${}')
                                            # Check if this app is enabled (we already know it is at this point)
                                            # and if it has the port defined in user_config
                                            if user_app_config.get('ports'):
                                                proxy_ports.append(
                                                    port_mapping)
                                                logging.info(
                                                    f"Added port mapping {port_mapping} to proxy from {app_name}")
                                        else:
                                            # For static port mappings
                                            proxy_ports.append(port_mapping)
                                            logging.info(
                                                f"Added static port mapping {port_mapping} to proxy from {app_name}")
                                else:
                                    # For single port value
                                    port_mapping = app_compose_config['ports']
                                    if "${" in str(port_mapping) and "}" in str(port_mapping):
                                        env_var = str(port_mapping).split(
                                            ':')[0].strip('${}')
                                        # Check if this app is enabled and has the port defined
                                        if user_app_config.get('ports'):
                                            proxy_ports.append(port_mapping)
                                            logging.info(
                                                f"Added port mapping {port_mapping} to proxy from {app_name}")
                                    else:
                                        # For static port mapping
                                        proxy_ports.append(port_mapping)
                                        logging.info(
                                            f"Added static port mapping {port_mapping} to proxy from {app_name}")

                                # Remove ports from the app config since they're now handled by the proxy
                                del app_compose_config['ports']

                        # Apply all other proxy-specific configurations
                        for key, value in app_proxy_compose.items():
                            app_compose_config[key] = value
                            if app_compose_config[key] is None:
                                del app_compose_config[key]

                    services[app_name] = app_compose_config

        # Add common services only if this is the main instance
        compose_config_common = user_config.get('compose_config_common', {})
        if is_main_instance:
            watchtower_service_key = 'proxy_enabled' if proxy_enabled else 'proxy_disabled'
            watchtower_service = compose_config_common['watchtower_service'][watchtower_service_key]
            services['watchtower'] = watchtower_service
            services['m4bwebdashboard'] = compose_config_common['m4b_dashboard_service']

        if proxy_enabled:
            # Get the base proxy service configuration
            proxy_service = compose_config_common['proxy_service'].copy()

            # Add collected ports from apps to the proxy service
            if proxy_ports:
                # If 'ports' key not in the proxy service, create it
                if 'ports' not in proxy_service:
                    proxy_service['ports'] = []
                elif not isinstance(proxy_service['ports'], list):
                    # If it's not a list, convert it to one
                    proxy_service['ports'] = [proxy_service['ports']]

                # Add required ports from enabled apps
                for port_mapping in proxy_ports:
                    if port_mapping not in proxy_service['ports']:
                        proxy_service['ports'].append(port_mapping)

                # Always ensure m4b_dashboard port is included if enabled
                if user_config['m4b_dashboard'].get('enabled') and not app_ports_transferred.get('m4bwebdashboard'):
                    dashboard_port = "${M4B_DASHBOARD_PORT}:80"
                    if dashboard_port not in proxy_service['ports']:
                        proxy_service['ports'].append(dashboard_port)
                        logging.info(
                            "Added M4B dashboard port mapping to proxy service")

                logging.info(
                    f"Added {len(proxy_ports)} port mappings to the proxy service from apps using its network")

            services['proxy'] = proxy_service

        # Define network configuration using config json and environment variables
        # This is a hybrid solution to remember that it could be possible to ditch the env file and generate all compose file parts from config json
        network_config = {
            'networks': {
                'default': {
                    'driver': compose_config_common['network']['driver'],
                    'ipam': {
                        'config': [
                            {
                                'subnet': f"{compose_config_common['network']['subnet']}/{compose_config_common['network']['netmask']}"
                            }
                        ]
                    }
                }
            }
        }

        # Create the compose dictionary
        compose_dict = {
            'services': services
        }

        # Append network configuration at the bottom
        compose_dict.update(network_config)

        with open(compose_output_path, 'w') as f:
            yaml.dump(compose_dict, f, sort_keys=False,
                      default_flow_style=False)
        logging.info(
            f"Docker Compose file assembled and saved to {compose_output_path}")
    finally:
        event.set()
        spinner_thread.join()


def generate_env_file(m4b_config_path_or_dict: Any, app_config_path_or_dict: Any, user_config_path_or_dict: Any, env_output_path: str = str(os.path.join(os.getcwd(), '.env')), is_main_instance: bool = False) -> None:
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
        target=show_spinner, args=("Generating .env file...", event))
    spinner_thread.start()

    try:
        m4b_config = load_json_config(m4b_config_path_or_dict)
        app_config = load_json_config(app_config_path_or_dict)
        user_config = load_json_config(user_config_path_or_dict)

        env_lines = []

        # Add project and system configurations
        project_config = m4b_config.get('project', {})
        for key, value in project_config.items():
            env_lines.append(f"{key.upper()}={value}")

        # Add resource limits configurations
        resource_limits_config = user_config.get('resource_limits', {})
        for key, value in resource_limits_config.items():
            env_lines.append(f"{key.upper()}={value}")

        # Add network configurations
        network_config = m4b_config.get('network', {})
        for key, value in network_config.items():
            env_lines.append(f"NETWORK_{key.upper()}={value}")

        # Add user and device configurations
        device_info = user_config.get('device_info', {})
        for key, value in device_info.items():
            env_lines.append(f"{key.upper()}={value}")

        # Add m4b_dashboard configurations
        m4b_dashboard_name = 'm4b_dashboard'
        m4b_dashboard_config = user_config.get(m4b_dashboard_name, {})
        for key, value in m4b_dashboard_config.items():
            if key == 'ports':
                env_lines.append(f"{m4b_dashboard_name.upper()}_PORT={value}")
            else:
                env_lines.append(
                    f"{m4b_dashboard_name.upper()}_{key.upper()}={value}")

        # Add proxy configurations
        proxy_config = user_config.get('proxies', {})
        for key, value in proxy_config.items():
            env_lines.append(f"STACK_PROXY_{key.upper()}={value}")

        # Add notification configurations if enabled
        notifications_config = user_config.get('notifications', {})
        if notifications_config.get('enabled'):
            for key, value in notifications_config.items():
                env_lines.append(
                    f"WATCHTOWER_NOTIFICATION_{key.upper()}={value}")

        # Add app-specific configurations only if the app is enabled
        apps_categories = ['apps']
        if is_main_instance:
            apps_categories.append('extra-apps')
        for category in apps_categories:
            for app in app_config.get(category, []):
                app_name = app['name'].upper()
                app_flags = app.get('flags', {})
                app_user_config = user_config['apps'].get(
                    app['name'].lower(), {})
                if app_user_config.get('enabled', False):
                    for flag_name in app_flags.keys():
                        if flag_name in app_user_config:
                            env_var_name = f"{app_name}_{flag_name.upper()}"
                            env_var_value = app_user_config[flag_name]
                            env_lines.append(f"{env_var_name}={env_var_value}")

                    # Add ports configurations for apps that have them
                    # TODO: remove dashboard_port from here and user config and use ports instead
                    if 'dashboard_port' in app_user_config:
                        env_lines.append(
                            f"{app_name.upper()}_DASHBOARD_PORT={app_user_config['dashboard_port']}")
                    if 'ports' in app_user_config:
                        env_lines.append(
                            f"{app_name.upper()}_PORT={app_user_config['ports']}")

        # Write to .env file
        with open(env_output_path, 'w') as f:
            f.write('\n'.join(env_lines))
        logging.info(f".env file generated and saved to {env_output_path}")
    finally:
        event.set()
        spinner_thread.join()


def generate_dashboard_urls(compose_project_name: str, device_name: str, env_file: str = str(os.path.join(os.getcwd(), ".env"))) -> None:
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
        target=show_spinner, args=("Generating dashboard URLs...", event))
    spinner_thread.start()

    try:
        if not compose_project_name or not device_name:
            if os.path.isfile(env_file):
                logging.info(
                    "Reading COMPOSE_PROJECT_NAME and DEVICE_NAME from .env file...")
                with open(env_file, 'r') as f:
                    for line in f:
                        if 'COMPOSE_PROJECT_NAME' in line:
                            compose_project_name = line.split('=')[1].strip()
                        if 'DEVICE_NAME' in line:
                            device_name = line.split('=')[1].strip()
            else:
                logging.error(
                    "Error: Parameters not provided and .env file not found.")
                return

        if not compose_project_name or not device_name:
            logging.error(
                "Error: COMPOSE_PROJECT_NAME and DEVICE_NAME must be provided.")
            return

        dashboard_file = f"dashboards_URLs_{compose_project_name}-{device_name}.txt"
        with open(dashboard_file, 'w') as f:
            f.write(
                f"------ Dashboards {compose_project_name}-{device_name} ------\n")

        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Ports}} {{.Names}}"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            container_info = line.split()[-1]
            port_mapping = re.search(r'0.0.0.0:(\d+)->', line)
            if port_mapping:
                with open(dashboard_file, 'a') as f:
                    f.write(
                        f"If enabled you can visit the {container_info} web dashboard on http://localhost:{port_mapping.group(1)}\n")

        logging.info(f"Dashboard URLs have been written to {dashboard_file}")
    finally:
        event.set()
        spinner_thread.join()


def generate_device_name(adjectives: list, animals: list, device_name: str = "", use_uuid_suffix: bool = False) -> str:
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
