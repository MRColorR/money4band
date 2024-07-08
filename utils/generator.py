import os
import sys
import argparse
import logging
import json
import re
from typing import Dict, Any

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from utils.checker import check_img_arch_support, get_compatible_tag
from utils.detector import detect_architecture
from utils.loader import load_json_config

def validate_uuid(uuid: str, length: int) -> bool:
    """
    Validate a UUID against the specified length.

    Arguments:
    uuid -- the UUID to validate
    length -- the expected length of the UUID
    """
    if not isinstance(uuid, str) or len(uuid) != length or not re.match('[0-9a-f]{{{}}}'.format(length), uuid):
        return False
    return True
    

def generate_uuid(length: int) -> str:
    """
    Generate a UUID of the specified length.

    Arguments:
    length -- the length of the UUID to generate

    Returns:
    str -- The generated UUID.
    """
    return str(os.urandom(length // 2 + 1).hex())[:length]

def assemble_docker_compose(app_config_path_or_dict: Any, user_config_path_or_dict: Any, m4b_config_path_or_dict: Any, compose_output_path: str = str(os.path.join(os.getcwd(), 'compose.yaml'))) -> None:
    """
    Assemble a Docker Compose file based on the app and user configuration.

    Arguments:
    app_config_path_or_dict -- the path to the app configuration file or the config dictionary
    user_config_path_or_dict -- the path to the user configuration file or the config dictionary
    m4b_config_path_or_dict -- the path to the m4b configuration file or the config dictionary
    compose_output_path -- the path to save the assembled docker-compose.yaml file
    """
    app_config = load_json_config(app_config_path_or_dict)
    user_config = load_json_config(user_config_path_or_dict)
    m4b_config = load_json_config(m4b_config_path_or_dict)

    arch_info = detect_architecture(m4b_config)
    dkarch = arch_info['dkarch']

    services = {}
    for app in app_config['apps']:
        app_name = app['name'].lower()
        if user_config['apps'][app_name]['enabled']:
            image = app['compose_config']['image']
            image_name, image_tag = image.split(':')
            
            if not check_img_arch_support(image_name, image_tag, dkarch):
                compatible_tag = get_compatible_tag(image_name, dkarch)
                if compatible_tag:
                    app['compose_config']['image'] = f"{image_name}:{compatible_tag}"
                else:
                    logging.warning(f"No compatible tag found for {image_name} with architecture {dkarch}. Using default tag {image_tag}.")

            services[app_name] = app['compose_config']

    compose_dict = {
        'version': '3',
        'services': services
    }

    with open(compose_output_path, 'w') as f:
        json.dump(compose_dict, f, indent=2)
    logging.info(f"Docker Compose file assembled and saved to {compose_output_path}")

def generate_env_file(m4b_config_path_or_dict: Any, user_config_path_or_dict: Any, env_output_path: str = str(os.path.join(os.getcwd(), '.env'))) -> None:
    """
    Generate a .env file based on the m4b and user configuration.

    Arguments:
    m4b_config_path_or_dict -- the path to the m4b configuration file or the config dictionary
    user_config_path_or_dict -- the path to the user configuration file or the config dictionary
    env_output_path -- the path to save the generated .env file
    """
    m4b_config = load_json_config(m4b_config_path_or_dict)
    user_config = load_json_config(user_config_path_or_dict)

    lines = [
        f"PROJECT_VERSION={m4b_config['project']['project_version']}",
        f"DS_PROJECT_SERVER_URL={m4b_config['project']['ds_project_server_url']}",
        f"M4B_DASHBOARD_PORT={m4b_config['dashboards']['m4b_dashboard_port']}",
        f"APP_CPU_LIMIT_LITTLE={m4b_config['resource_limits']['app_cpu_limit_little']}",
        f"APP_CPU_LIMIT_MEDIUM={m4b_config['resource_limits']['app_cpu_limit_medium']}",
        f"APP_CPU_LIMIT_BIG={m4b_config['resource_limits']['app_cpu_limit_big']}",
        f"APP_CPU_LIMIT_HUGE={m4b_config['resource_limits']['app_cpu_limit_huge']}",
        f"RAM_CAP_MB_DEFAULT={m4b_config['resource_limits']['ram_cap_mb_default']}",
        f"APP_MEM_RESERV_LITTLE={m4b_config['resource_limits']['app_mem_reserv_little']}",
        f"APP_MEM_LIMIT_LITTLE={m4b_config['resource_limits']['app_mem_limit_little']}",
        f"APP_MEM_RESERV_MEDIUM={m4b_config['resource_limits']['app_mem_reserv_medium']}",
        f"APP_MEM_LIMIT_MEDIUM={m4b_config['resource_limits']['app_mem_limit_medium']}",
        f"APP_MEM_RESERV_BIG={m4b_config['resource_limits']['app_mem_reserv_big']}",
        f"APP_MEM_LIMIT_BIG={m4b_config['resource_limits']['app_mem_limit_big']}",
        f"APP_MEM_RESERV_HUGE={m4b_config['resource_limits']['app_mem_reserv_huge']}",
        f"APP_MEM_LIMIT_HUGE={m4b_config['resource_limits']['app_mem_limit_huge']}",
        f"COMPOSE_PROJECT_NAME={m4b_config['project']['compose_project_name']}",
        f"DEVICE_NAME={user_config['device_info']['device_name']}",
        f"STACK_PROXY={user_config['proxies']['stack_proxy']}",
        f"EARNAPP_DEVICE_UUID={user_config['apps']['earnapp']['uuid']}",
        f"HONEYGAIN_EMAIL={user_config['apps']['honeygain']['email']}",
        f"HONEYGAIN_PASSWD={user_config['apps']['honeygain']['password']}",
        f"IPROYALPAWNS_EMAIL={user_config['apps']['iproyalpawns']['email']}",
        f"IPROYALPAWNS_PASSWD={user_config['apps']['iproyalpawns']['password']}",
        f"PEER2PROFIT_EMAIL={user_config['apps']['peer2profit']['email']}",
        f"PACKETSTREAM_CID={user_config['apps']['packetstream']['cid']}",
        f"TRAFFMONETIZER_TOKEN={user_config['apps']['traffmonetizer']['token']}",
        f"REPOCKET_EMAIL={user_config['apps']['repocket']['email']}",
        f"REPOCKET_APIKEY={user_config['apps']['repocket']['apikey']}",
        f"EARNFM_APIKEY={user_config['apps']['earnfm']['apikey']}",
        f"PROXYRACK_APIKEY={user_config['apps']['proxyrack']['apikey']}",
        f"PROXYRACK_DEVICE_UUID={user_config['apps']['proxyrack']['uuid']}",
        f"PROXYLITE_USER_ID={user_config['apps']['proxylite']['userid']}",
        f"BITPING_EMAIL={user_config['apps']['bitping']['email']}",
        f"BITPING_PASSWD={user_config['apps']['bitping']['password']}",
        f"SPEEDSHARE_CODE={user_config['apps']['speedshare']['code']}",
        f"SPEEDSHARE_DEVICE_UUID={user_config['apps']['speedshare']['uuid']}",
        f"GRASS_EMAIL={user_config['apps']['grass']['email']}",
        f"GRASS_PASSWD={user_config['apps']['grass']['password']}",
        f"MYSTNODE_DASHBOARD_PORT={m4b_config['dashboards']['mystnode_dashboard_port']}"
    ]

    with open(env_output_path, 'w') as f:
        f.write('\n'.join(lines))
    logging.info(f".env file generated and saved to {env_output_path}")

