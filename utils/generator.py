import os
import subprocess
import sys
import argparse
import logging
import json
import re
from typing import Dict, Any
import yaml  # Import PyYAML
import secrets
import getpass

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from utils.checker import check_img_arch_support, get_compatible_tag
from utils.detector import detect_architecture
from utils.loader import load_json_config
from utils.dumper import write_json

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
    m4b_config = load_json_config(m4b_config_path_or_dict)
    app_config = load_json_config(app_config_path_or_dict)
    user_config = load_json_config(user_config_path_or_dict)

    arch_info = detect_architecture(m4b_config)
    dkarch = arch_info['dkarch']

    services = {}
    for category in ['apps', 'extra-apps']:
        for app in app_config.get(category, []):
            app_name = app['name'].lower()
            if user_config['apps'].get(app_name, {}).get('enabled'):
                app_compose_config = app['compose_config']
                image = app_compose_config['image']
                image_name, image_tag = image.split(':')

                if not check_img_arch_support(image_name, image_tag, dkarch):
                    compatible_tag = get_compatible_tag(image_name, dkarch)
                    if compatible_tag:
                        app_compose_config['image'] = f"{image_name}:{compatible_tag}"
                    else:
                        logging.warning(f"No compatible tag found for {image_name} with architecture {dkarch}. Using default tag {image_tag}.")

                services[app_name] = app_compose_config

    # Add common services only if this is the main instance
    compose_config_common = m4b_config.get('compose_config_common', {})
    if is_main_instance:
        services['watchtower'] = compose_config_common['watchtower_service']
        services['m4bwebdashboard'] = compose_config_common['dashboard_service']
    if user_config['proxies']['enabled']:
        services['proxy'] = compose_config_common['proxy_service']

    # Define network configuration using config json and environment variables
    # This is an hybrid solution to remember that it could be possible to ditch the env file and generate all compose file parts from config json
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
        yaml.dump(compose_dict, f, sort_keys=False, default_flow_style=False)
    logging.info(f"Docker Compose file assembled and saved to {compose_output_path}")

def generate_env_file(m4b_config_path_or_dict: Any, app_config_path_or_dict: Any, user_config_path_or_dict: Any, env_output_path: str = str(os.path.join(os.getcwd(), '.env'))) -> None:
    """
    Generate a .env file based on the m4b and user configuration.

    Args:
        m4b_config_path_or_dict (Any): The path to the m4b configuration file or the config dictionary.
        app_config_path_or_dict (Any): The path to the app configuration file or the config dictionary.
        user_config_path_or_dict (Any): The path to the user configuration file or the config dictionary.
        env_output_path (str, optional): The path to save the generated .env file. Defaults to './.env'.

    Raises:
        Exception: If an error occurs during the file generation process.
    """
    m4b_config = load_json_config(m4b_config_path_or_dict)
    app_config = load_json_config(app_config_path_or_dict)
    user_config = load_json_config(user_config_path_or_dict)

    env_lines = []

    # Add project and system configurations
    project_config = m4b_config.get('project', {})
    for key, value in project_config.items():
        env_lines.append(f"{key.upper()}={value}")

    # system_config = m4b_config.get('system', {})
    # for key, value in system_config.items():
    #     if isinstance(value, dict):
    #         for sub_key, sub_value in value.items():
    #             env_lines.append(f"{key.upper()}_{sub_key.upper()}={sub_value}")
    #     else:
    #         env_lines.append(f"{key.upper()}={value}")

    # Add dashboards configurations
    dashboards_config = m4b_config.get('dashboards', {})
    for key, value in dashboards_config.items():
        env_lines.append(f"{key.upper()}={value}")

    # Add resource limits configurations
    resource_limits_config = m4b_config.get('resource_limits', {})
    for key, value in resource_limits_config.items():
        env_lines.append(f"{key.upper()}={value}")
    
    # Add network configurations
    network_config = m4b_config.get('network', {})
    for key, value in network_config.items():
        env_lines.append(f"NETWORK_{key.upper()}={value}")

    # Add user and device configurations
    # user_info = user_config.get('user', {})
    # for key, value in user_info.items():
    #     env_lines.append(f"{key.upper()}={value}")

    device_info = user_config.get('device_info', {})
    for key, value in device_info.items():
        env_lines.append(f"{key.upper()}={value}")

    # Add proxy configurations
    proxy_config = user_config.get('proxies', {})
    for key, value in proxy_config.items():
        env_lines.append(f"{key.upper()}={value}")

    # Add notification configurations
    notifications_config = user_config.get('notifications', {})
    for key, value in notifications_config.items():
        env_lines.append(f"{key.upper()}={value}")

    # Add app-specific configurations
    for category in ['apps', 'extra-apps']:
        for app in app_config.get(category, []):
            app_name = app['name'].upper()
            app_flags = app.get('flags', {})
            app_user_config = user_config['apps'].get(app['name'].lower(), {})
            for flag_name in app_flags.keys():
                if flag_name in app_user_config:
                    env_var_name = f"{app_name}_{flag_name.upper()}"
                    env_var_value = app_user_config[flag_name]
                    env_lines.append(f"{env_var_name}={env_var_value}")

    # Write to .env file
    with open(env_output_path, 'w') as f:
        f.write('\n'.join(env_lines))
    logging.info(f".env file generated and saved to {env_output_path}")


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
    if not compose_project_name or not device_name:
        if os.path.isfile(env_file):
            logging.info("Reading COMPOSE_PROJECT_NAME and DEVICE_NAME from .env file...")
            with open(env_file, 'r') as f:
                for line in f:
                    if 'COMPOSE_PROJECT_NAME' in line:
                        compose_project_name = line.split('=')[1].strip()
                    if 'DEVICE_NAME' in line:
                        device_name = line.split('=')[1].strip()
        else:
            logging.error("Error: Parameters not provided and .env file not found.")
            return

    if not compose_project_name or not device_name:
        logging.error("Error: COMPOSE_PROJECT_NAME and DEVICE_NAME must be provided.")
        return

    dashboard_file = f"dashboards_URLs_{compose_project_name}-{device_name}.txt"
    with open(dashboard_file, 'w') as f:
        f.write(f"------ Dashboards {compose_project_name}-{device_name} ------\n")

    result = subprocess.run(["docker", "ps", "--format", "{{.Ports}} {{.Names}}"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        container_info = line.split()[-1]
        port_mapping = re.search(r'0.0.0.0:(\d+)->', line)
        if port_mapping:
            with open(dashboard_file, 'a') as f:
                f.write(f"If enabled you can visit the {container_info} web dashboard on http://localhost:{port_mapping.group(1)}\n")

    logging.info(f"Dashboard URLs have been written to {dashboard_file}")

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
