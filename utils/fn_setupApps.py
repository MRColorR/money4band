import os
import argparse
import logging
import json
from typing import Dict, Any
from colorama import Fore, Back, Style, just_fix_windows_console
from utils import loader, detector
from utils.cls import cls
from utils.dumper import write_json
import time

def collect_user_info(user_config: Dict[str, Any]) -> None:
    """
    Collect user information and update the user configuration.

    Arguments:
    user_config -- the user configuration dictionary
    """
    nickname = input('Enter your nickname: ')
    device_name = input('Enter your device name: ')

    user_config['user']['Nickname'] = nickname
    user_config['device_info']['device_name'] = device_name

def configure_apps(user_config: Dict[str, Any], app_config: Dict) -> None:
    """
    Configure apps by collecting user inputs.

    Arguments:
    user_config -- the user configuration dictionary
    app_config -- the app configuration dictionary
    """
    asking = {
        'email': 'Enter your {} email: ',
        'password': 'Enter your {} password: ',
        'apikey': 'Enter your {} API key: ',
        'cid': 'Enter your {} CID: ',
        'token': 'Enter your {} token: ',
        'code': 'Enter your {} code: ',
        "device": "Enter your {} device name (if you skip it a random one will be generated)"
    }

    for i in app_config['apps']:
        app_name = i['name']
        user_input = input(f'Do you want to run {app_name.title()}? (y/n) : ')
        if user_input == '404':
            break
        if user_input.lower().strip() != 'y':
            continue
        user_config['apps'][app_name.lower()]['enabled'] = True
        for property in user_config['apps'][app_name.lower()]:
            if property in asking:
                player_input = input(asking[property].format(app_name.title()))
                if player_input == '404':
                    break
                user_config['apps'][app_name.lower()][property] = player_input

    return user_config

def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Main function for setting up user configurations.

    Arguments:
    app_config_path -- the path to the app configuration file
    m4b_config_path -- the path to the m4b configuration file
    user_config_path -- the path to the user configuration file
    """
    app_config = loader.load_json_config(app_config_path)
    user_config = loader.load_json_config(user_config_path)

    advance_setup = input('Do you want to go with Multiproxy setup? (y/n): ').lower().strip()
    if advance_setup == 'y':
        logging.info("Multiproxy setup selected")
        print('Create a proxies.txt file in the same folder and add proxies in the following format: protocol://user:pass@ip:port (one proxy per line)')
        user_config['proxies']['multiproxy'] = True
        time.sleep(3)
    else:
        logging.info("Basic setup selected")
        single_proxy = input('Do you want to setup proxy for the apps? (y/n) ')
        if single_proxy.strip().lower() == 'y':
            user_config['proxies']['proxy'] = input('Enter proxy details \n').strip()

    user_config = configure_apps(user_config, app_config)
    write_json(user_config, user_config_path)

if __name__ == '__main__':
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the module standalone.')
    parser.add_argument('--app-config', type=str, required=True, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=True, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config-path', type=str, default='./config/user-config.json', help='Path to user_config JSON file')
    parser.add_argument('--log-dir', default=os.path.join(script_dir, 'logs'), help='Set the logging directory')
    parser.add_argument('--log-file', default=f"{script_name}.log", help='Set the logging file name')
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
