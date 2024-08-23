import os
import platform
import sys
import argparse
import logging
import json
import time
import getpass
import shutil
import re
from copy import deepcopy
from typing import Dict, Any
import socket
from colorama import Fore, Back, Style, just_fix_windows_console

# Ensure the parent directory is in the sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from utils import loader, detector
from utils.cls import cls
from utils.dumper import write_json
from utils.prompt_helper import ask_question_yn, ask_email, ask_string, ask_uuid
from utils.generator import generate_uuid, assemble_docker_compose, generate_env_file, generate_device_name
from utils.checker import fetch_docker_tags, check_img_arch_support
from utils.fn_stopStack import stop_stack, stop_all_stacks
from utils.networker import find_next_available_port

def configure_email(app: Dict, flag_config: Dict, config: Dict):
    email = ask_email(f'Enter your {app["name"].lower().title()} email:', default=config.get("email"))
    config['email'] = email

def configure_password(app: Dict, flag_config: Dict, config: Dict):
    print(f'Note: If you are using login with Google, remember to set also a password for your {app["name"].lower().title()} account!')
    password = ask_string(f'Enter your {app["name"].lower().title()} password:', default=config.get("password"))
    config['password'] = password

def configure_apikey(app: Dict, flag_config: Dict, config: Dict):
    print(f'Find/Generate your APIKey inside your {app["name"].lower().title()} dashboard/profile.')
    apikey = ask_string(f'Enter your {app["name"].lower().title()} APIKey:', default=config.get("apikey"))
    config['apikey'] = apikey

def configure_userid(app: Dict, flag_config: Dict, config: Dict):
    print(f'Find your UserID inside your {app["name"].lower().title()} dashboard/profile.')
    userid = ask_string(f'Enter your {app["name"].lower().title()} UserID:', default=config.get("userid"))
    config['userid'] = userid

def configure_uuid(app: Dict, flag_config: Dict, config: Dict):
    print(f'Starting UUID generation/import for {app["name"].lower().title()}')
    if 'length' not in flag_config:
        print(f'{Fore.RED}Error: Length not specified for UUID generation/import{Style.RESET_ALL}')
        logging.error('Length not specified for UUID generation/import')
        return

    length = flag_config['length']
    if not isinstance(length, int) or length <= 0:
        print(f'{Fore.RED}Error: Invalid length for UUID generation/import{Style.RESET_ALL}')
        logging.error(f'Invalid length for UUID generation/import: {length}')
        return

    if ask_question_yn(f'Do you want to use a previously registered uuid for {app["name"].lower().title()} (current: {Fore.YELLOW}{config.get("uuid", "not set")}{Fore.GREEN})?'):
        print(f'{Fore.GREEN}Please enter the alphanumeric part of the existing uuid for {app["name"].lower().title()}, it should be {length} characters long.')
        print('E.g. if existing registered node is sdk-node-b86301656baefekba8917349bdf0f3g4 then enter just b86301656baefekba8917349bdf0f3g4')
        uuid = ask_uuid('Insert uuid:', length, default=config.get("uuid"))
    else:
        uuid = generate_uuid(length)
        print(f'{Fore.GREEN}Generated UUID: {uuid}{Style.RESET_ALL}')
    if 'claimURLBase' in flag_config:
        print(f'{Fore.BLUE}Save the following instructions/link somewhere to claim/register your {app["name"].lower().title()} '
              f'node/device after completing the setup and starting the apps stack:{Style.RESET_ALL}')
        print(f'{Fore.BLUE}{Style.BRIGHT}{flag_config["claimURLBase"]}{uuid}{Style.RESET_ALL}')
        try:
            with open(f'claim_instructions_{app["name"].lower()}.txt', 'w') as f:
                f.write(f'{flag_config["claimURLBase"]}{uuid}')
            print(f'{Fore.GREEN}Claim instructions written to claim_instructions_{app["name"].lower()}.txt{Style.RESET_ALL}')
        except Exception as e:
            logging.error(f'Error writing claim instructions to file: {e}')
        input('Press enter to continue...')
    
    prefix = flag_config.get('prefix', '')
    uuid = f'{prefix}{uuid}'
    config['uuid'] = uuid

def configure_cid(app: Dict, flag_config: Dict, config: Dict):
    print(f'Find your CID inside your {app["name"].lower().title()} dashboard/profile.')
    print("Example: For packetstream you can fetch it from your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page, you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)")
    cid = ask_string(f'Enter your {app["name"].lower().title()} CID:', default=config.get("cid"))
    config['cid'] = cid

def configure_code(app: Dict, flag_config: Dict, config: Dict):
    print(f'Find your code inside your {app["name"].lower().title()} dashboard/profile.')
    code = ask_string(f'Enter your {app["name"].lower().title()} code:', default=config.get("code"))
    config['code'] = code

def configure_token(app: Dict, flag_config: Dict, config: Dict):
    print(f'Find your token inside your {app["name"].lower().title()} dashboard/profile.')
    token = ask_string(f'Enter your {app["name"].lower().title()} token:', default=config.get("token"))
    config['token'] = token

def configure_manual(app: Dict, flag_config: Dict, config: Dict):
    if 'instructions' not in flag_config:
        print(f'{Fore.RED}Error: Instructions not provided for manual configuration{Style.RESET_ALL}')
        return
    print(f'{Fore.BLUE}"{app["name"].lower().title()} requires further manual configuration.{Style.RESET_ALL}')
    print(f'{Fore.YELLOW}{flag_config["instructions"]}{Style.RESET_ALL}')
    print(f'{Fore.YELLOW}Please after completing this automated setup check also the app\'s website for further instructions if there are any.{Style.RESET_ALL}')
    input('Press enter to continue...')

flag_function_mapper = {
    'email': configure_email,
    'password': configure_password,
    'apikey': configure_apikey,
    'userid': configure_userid,
    'uuid': configure_uuid,
    'cid': configure_cid,
    'code': configure_code,
    'token': configure_token,
    'manual': configure_manual
}

def collect_user_info(user_config: Dict[str, Any], m4b_config: Dict[str, Any]) -> None:
    """
    Collect user information and update the user configuration.

    Args:
        user_config (dict): The user configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
    """
    try:
        nickname = getpass.getuser()
    except Exception:
        nickname = "user"
    user_config['user']['Nickname'] = nickname
    
    # If the device_name is equal to the placeholder then take the hostname as default device_name and ask user if wants to change it 
    device_name = user_config['device_info'].get('device_name')
    if device_name and device_name.lower() == ('yourDeviceName').lower():
        try:
            device_name = platform.node()
        except Exception:
            logging.warning('Unable to get hostname for devicename')
            pass

    if device_name:
        if not ask_question_yn(f'The current device name is {device_name}. Do you want to change it?'):
            return

    device_name = input('Enter your device name: Or leave it blank to generate a random one:').strip()
    device_name = generate_device_name(
        m4b_config['word_lists']['adjectives'], 
        m4b_config['word_lists']['animals'], 
        device_name=device_name, 
        use_uuid_suffix=False 
    )

    user_config['device_info']['device_name'] = device_name

def _configure_apps(user_config: Dict[str, Any], apps: Dict, m4b_config: Dict):
    """
    Configure apps by collecting user inputs.

    Args:
        user_config (dict): The user configuration dictionary.
        apps (dict): The app configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
    """
    for app in apps:
        app_name = app['name'].lower()
        config = user_config['apps'].get(app_name, {})
        cls()
        if config.get('enabled'):
            print(f'The app {app_name} is currently enabled.')
            if ask_question_yn('Do you want to disable it?'):
                config['enabled'] = False
                continue
            print(f'Do you want to change the current {app_name} configuration?')
            for key, value in config.items():
                if key != 'enabled':
                    print(f'{key}: {value}')
            if not ask_question_yn(''):
                continue
        
        config['enabled'] = ask_question_yn(f'Do you want to run {app["name"].title()}?')
        if not config['enabled']:
            continue
        print(f'{Fore.CYAN}Go to {app["name"].title()} {app["link"]} and register{Style.RESET_ALL}')
        print(f'{Fore.GREEN}Use CTRL+Click to open links or copy them:{Style.RESET_ALL}')
        input('When you are done press Enter to continue')
        for flag_name, flag_config in app.get('flags', {}).items():
            if flag_name in flag_function_mapper:
                flag_function_mapper[flag_name](app, flag_config, config)
            else:
                logging.error(f'Flag {flag_name} not recognized')
        user_config['apps'][app_name] = config
        time.sleep(m4b_config['system']['sleep_time'])

def configure_apps(user_config: Dict[str, Any], app_config: Dict, m4b_config: Dict) -> None:
    """
    Configure apps by collecting user inputs.

    Args:
        user_config (dict): The user configuration dictionary.
        app_config (dict): The app configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
    """
    _configure_apps(user_config, app_config['apps'], m4b_config)

def configure_extra_apps(user_config: Dict[str, Any], app_config: Dict, m4b_config: Dict) -> None:
    """
    Configure extra apps by collecting user inputs.

    Args:
        user_config (dict): The user configuration dictionary.
        app_config (dict): The app configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
    """
    _configure_apps(user_config, app_config['extra-apps'], m4b_config)

# Supported services and their URL patterns
SUPPORTED_NOTIFICATION_SERVICES = {
    'bark': r'^bark://[a-zA-Z0-9]+@.+$',
    'discord': r'^discord://[a-zA-Z0-9]+@[a-zA-Z0-9]+$',
    'email': r'^smtp://[a-zA-Z0-9]+:[a-zA-Z0-9]+@.+:\d+/\?from=.*&to=.*$',
    'gotify': r'^gotify://.+/token$',
    'googlechat': r'^googlechat://chat\.googleapis\.com/v1/spaces/.+/messages\?key=.*&token=.*$',
    'ifttt': r'^ifttt://.+/\?events=.*$',
    'join': r'^join://shoutrrr:[a-zA-Z0-9]+@join/\?devices=.*$',
    'mattermost': r'^mattermost://(?:[a-zA-Z0-9]+@)?.+/token(?:/channel)?$',
    'matrix': r'^matrix://.+:.+@.+:\d+/\?rooms=.*$',
    'ntfy': r'^ntfy://(?:[a-zA-Z0-9]+:[a-zA-Z0-9]+@)?.+/topic$',
    'opsgenie': r'^opsgenie://.+/token\?responders=.*$',
    'pushbullet': r'^pushbullet://[a-zA-Z0-9]+(?:/device/#channel/[a-zA-Z0-9]+)?$',
    'pushover': r'^pushover://shoutrrr:[a-zA-Z0-9]+@[a-zA-Z0-9]+/\?devices=.*$',
    'rocketchat': r'^rocketchat://(?:[a-zA-Z0-9]+@)?.+/token(?:/channel)?$',
    'slack': r'^slack://(?:[a-zA-Z0-9]+@)?.+/token-a/token-b/token-c$',
    'teams': r'^teams://[a-zA-Z0-9]+@[a-zA-Z0-9]+/.+/groupOwner\?host=.*$',
    'telegram': r'^telegram://.+@telegram\?chats=.*$',
    'zulip': r'^zulip://.+:.+@zulip-domain/\?stream=.*&topic=.*$',
}

def validate_notification_url(url: str) -> bool:
    """
    Validate the notification URL against supported services.

    Args:
        url (str): The URL to validate.

    Returns:
        bool: True if the URL is valid, False otherwise.
    """
    for service, pattern in SUPPORTED_NOTIFICATION_SERVICES.items():
        if re.match(pattern, url):
            logging.info(f"Given URL {url} matches notification service {service}")
            return True
    logging.error(f"Given URL {url} does not match any supported notification service")
    return False

def setup_notifications(user_config: Dict[str, Any]) -> None:
    """
    Set up notifications for app updates using a supported service.

    Args:
        user_config (dict): The user configuration dictionary.
    """
    notifications_config = user_config.get('notifications', {})

    # Check if notifications are already set up
    if notifications_config.get('enabled'):
        print(f"Notifications are currently enabled with the following URL: {notifications_config.get('url')}")
        if not ask_question_yn('Do you want to change the current notification settings?'):
            print("Keeping existing notification settings.")
            logging.info("User chose to keep existing notification settings.")
            return

    # Proceed to set up or change the notification settings
    if ask_question_yn('Do you want to enable notifications about apps images updates?'):
        logging.info("User decided to set up notifications about apps images updates.")
        print("Setting-up notifications for images updates using Shoutrrr.")
        print("Format WATCHTOWER_NOTIFICATION_URL as: <app>://<token>@<webhook>.")
        print("<app> is a supported messaging app (e.g., Discord), <token> and <webhook> are app-specific.")
        print("Create a webhook for your app and format its URL accordingly.")
        print("For details, visit https://containrrr.dev/shoutrrr/ and select your app.")
        print("You can also specify multiple URLs separated by spaces (e.g., 'discord://token@channel slack://watchtower@token-a/token-b/token-c').")
        input("Press Enter to continue...")

        while True:
            notification_url = ask_string('Enter the notification URL (e.g., discord://token@id):', default=notifications_config.get('url', ''))
            if validate_notification_url(notification_url):
                user_config['notifications']['enabled'] = True
                user_config['notifications']['url'] = notification_url
                logging.info(f"Notification URL set to: {notification_url}")
                break
            else:
                print("Invalid URL format. Please ensure it matches one of the supported formats.")
                if not ask_question_yn('Do you want to try again?'):
                    logging.info("User chose to skip notification setup.")
                    break
    else:
        user_config['notifications']['enabled'] = False
        print("Noted: All updates will be applied automatically and silently.")
        logging.info("User chose not to enable notifications.")


def setup_multiproxy_instances(user_config: Dict[str, Any], app_config: Dict[str, Any], m4b_config: Dict[str, Any], proxies: list) -> None:
    """
    Setup multiple proxy instances based on the given proxies list.

    Args:
        user_config (dict): The user configuration dictionary.
        app_config (dict): The app configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
        proxies (list): List of proxy configurations.
    """
    instances_dir = 'm4b_proxy_instances'
    os.makedirs(instances_dir, exist_ok=True)

    base_device_name = user_config['device_info']['device_name']
    base_project_name = m4b_config.get('project', {}).get('compose_project_name', 'money4band')

    base_subnet = m4b_config['network']['subnet']
    base_subnet_match = re.match(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', base_subnet)
    base_subnet = int(base_subnet_match[1]).to_bytes(1, 'big') + int(base_subnet_match[2]).to_bytes(1, 'big') \
                + int(base_subnet_match[3]).to_bytes(1, 'big') + int(base_subnet_match[4]).to_bytes(1, 'big')
    base_subnet = int.from_bytes(base_subnet, byteorder='big')
    base_netmask = int(m4b_config['network']['netmask'])
    base_subnet = ((pow(2, base_netmask) - 1) << (32 - base_netmask)) & base_subnet

    if os.listdir(instances_dir):
        if ask_question_yn(f"Existing proxy instances found in '{instances_dir}'. Do you want to delete them?", default=True):
            stop_all_stacks(instances_dir, skip_questions=True)
            shutil.rmtree(instances_dir)
            os.makedirs(instances_dir, exist_ok=True)
        else:
            print(f"{Fore.YELLOW}Keeping existing instances alongside new ones.{Style.RESET_ALL}")

    for i, proxy in enumerate(proxies):
        instance_user_config = deepcopy(user_config)
        instance_m4b_config = deepcopy(m4b_config)
        instance_app_config = deepcopy(app_config)

        suffix = generate_uuid(4)
        instance_device_name = f"{base_device_name}_{suffix}"
        instance_project_name = f"{base_project_name}_{suffix}"

        instance_dir = os.path.join(instances_dir, instance_project_name)
        os.makedirs(instance_dir, exist_ok=True)

        instance_user_config['device_info']['device_name'] = instance_device_name
        instance_m4b_config['project']['compose_project_name'] = instance_project_name

        instance_user_config['proxies']['url'] = proxy
        instance_user_config['proxies']['enabled'] = True
        
        new_subnet = base_subnet + ((i + 1) << (32 - base_netmask))
        new_subnet = new_subnet.to_bytes(4, 'big', signed=False)
        new_subnet = str(new_subnet[0]) + '.' + str(new_subnet[1]) \
            + '.' + str(new_subnet[2]) + '.' + str(new_subnet[3])
        
        instance_m4b_config['network']['subnet'] = new_subnet

        # Update apps dashboard ports to avoid conflicts
        for app in instance_user_config['apps'].keys():
            app_details = instance_user_config['apps'].get(app, {})
            if app_details.get('enabled') and app_details.get('dashboard_port'):
                logging.info(f"{app} is enabled and it has a dashboard port attribute, staring port update to avoid conflicts")
                app_details['dashboard_port'] = find_next_available_port(app_details['dashboard_port'] + (i + 1))

        instance_user_config_path = os.path.join(instance_dir, 'user-config.json')
        instance_m4b_config_path = os.path.join(instance_dir, 'm4b-config.json')
        instance_app_config_path = os.path.join(instance_dir, 'app-config.json')

        write_json(instance_user_config, instance_user_config_path)
        write_json(instance_m4b_config, instance_m4b_config_path)
        write_json(instance_app_config, instance_app_config_path)

        assemble_docker_compose(instance_m4b_config_path, instance_app_config_path, instance_user_config_path, compose_output_path=os.path.join(instance_dir, 'docker-compose.yaml'))
        generate_env_file(instance_m4b_config_path, instance_app_config_path, instance_user_config_path, env_output_path=os.path.join(instance_dir, '.env'))

    print(f"{Fore.GREEN}Multiproxy instances setup completed.{Style.RESET_ALL}")
    time.sleep(m4b_config['system']['sleep_time'])


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Main function for setting up user configurations.

    Args:
        app_config_path (str): Path to the app configuration file.
        m4b_config_path (str): Path to the m4b configuration file.
        user_config_path (str): Path to the user configuration file.
    """
    try:
        app_config = loader.load_json_config(app_config_path)
        user_config = loader.load_json_config(user_config_path)
        m4b_config = loader.load_json_config(m4b_config_path)
        logging.info("Setup apps started")

        # Step 1: Collect user information
        collect_user_info(user_config, m4b_config)
        # Step 2: Configure apps
        configure_apps(user_config, app_config, m4b_config)
        # Step 3: Configure extra apps if the user chooses to
        if ask_question_yn('Do you want to configure extra apps?'):
            logging.info("Extra apps setup selected")
            configure_extra_apps(user_config, app_config, m4b_config)
        else: # if there are extra-apps enabled disable them
            for app in app_config['extra-apps']:
                app_name = app['name'].lower()
                user_config['apps'][app_name]['enabled'] = False
        # Step 4: Set up notifications
        setup_notifications(user_config)
        # Step 5: Save the user configuration
        write_json(user_config, user_config_path)
        # Step 6: Set up proxy if the user chooses to
        proxy_setup = ask_question_yn('Do you want to enable (multi)proxy?')
        if proxy_setup:
            logging.info("Multiproxy setup selected")
            print('Create a proxies.txt file in the same folder and add proxies in the following format: protocol://user:pass@ip:port (one proxy per line)')
            input('Press enter to continue...')
            time.sleep(m4b_config['system']['sleep_time'])
            with open('proxies.txt', 'r') as file:
                proxies = [line.strip() for line in file if line.strip()]

            # Use the user config first proxy to update the base money4band docker compose and env file adding proxy
            user_config['proxies']['url'] = proxies.pop(-1)
            user_config['proxies']['enabled'] = True
            write_json(user_config, user_config_path)
            assemble_docker_compose(m4b_config_path_or_dict=m4b_config, app_config_path_or_dict=app_config, user_config_path_or_dict=user_config, compose_output_path='./docker-compose.yaml', is_main_instance=True)
            generate_env_file(m4b_config_path_or_dict=m4b_config, app_config_path_or_dict=app_config, user_config_path_or_dict=user_config, env_output_path='./.env', is_main_instance=True)
    
            setup_multiproxy_instances(user_config, app_config, m4b_config, proxies)
            logging.info("Multiproxy instances setup completed")
        else:
            # Disable proxy if proxy setup is not selected
            logging.info("Multiproxy setup not selected")
            if user_config['proxies'].get('enabled'):
                user_config['proxies']['url'] = ''
                user_config['proxies']['enabled'] = False
                write_json(user_config, user_config_path)
            assemble_docker_compose(m4b_config_path, app_config_path, user_config_path, compose_output_path='./docker-compose.yaml', is_main_instance=True)
            generate_env_file(m4b_config_path, app_config_path, user_config_path, env_output_path='./.env', is_main_instance=True)
        logging.info("Setup completed")

    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An error occurred in main setup apps process: {str(e)}")
        raise


if __name__ == '__main__':
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the setup apps module standalone.')
    parser.add_argument('--app-config', type=str, required=True, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=True, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config-path', type=str, default='./config/user-config.json', help='Path to user_config JSON file')
    parser.add_argument('--log-dir', default=os.path.join(script_dir, 'logs'), help='Set the logging directory')
    parser.add_argument('--log-file', default=f'{script_name}.log', help='Set the logging file name')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help='Set the logging level')
    args = parser.parse_args()

    # Set logging level based on command-line arguments
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    # Start logging
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.log_dir, args.log_file),
        format='%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=log_level
    )

    logging.info(f"Starting {script_name} script...")

    try:
        # Call the main function
        main(app_config_path=args.app_config, m4b_config_path=args.m4b_config, user_config_path=args.user_config_path)
        logging.info(f"{script_name} script completed successfully")
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise

