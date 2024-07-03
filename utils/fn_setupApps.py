import os
import sys
import argparse
import logging
import json
from typing import Dict, Any
from colorama import Fore, Back, Style, just_fix_windows_console
import time

# Ensure the parent directory is in the sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from utils import loader, detector
from utils.cls import cls
from utils.dumper import write_json
from utils.prompt_helper import ask_question_yn, ask_email, ask_string, ask_uuid
from utils.generator import generate_uuid


def configure_email(app: Dict, flag_config: Dict, config: Dict):
    email = ask_email(f'{Fore.GREEN}Enter your email:{Style.RESET_ALL}')
    config['email'] = email

def configure_password(app: Dict, flag_config: Dict, config: Dict):
    print(f'Note: If you are using login with Google, remember to set also a password for your {app["name"].lower().title()} account!')
    password = ask_string(f'{Fore.GREEN}Enter your {app["name"].lower().title()} password:{Style.RESET_ALL}')
    config['password'] = password

def configure_apikey(app: Dict, flag_config: Dict, config: Dict):
    print(f'Find/Generate your APIKey inside your {app["name"].lower().title()} dashboard/profile.')
    apikey = ask_string(f'{Fore.GREEN}Enter your {app["name"].lower().title()} APIKey:{Style.RESET_ALL}')
    config['apikey'] = apikey

def configure_userid(app: Dict, flag_config: Dict, config: Dict):
    print(f'Find your UserID inside your {app["name"].lower().title()} dashboard/profile.')
    userid = ask_string(f'{Fore.GREEN}Enter your {app["name"].lower().title()} UserID:{Style.RESET_ALL}')
    config['userid'] = userid

def configure_uuid(app: Dict, flag_config: Dict, config: Dict):
    print(f'Starting UUID generation/import for {app["name"].lower().title()}')
    if 'length' not in flag_config:
        print(f'{Fore.RED}Error: Length not specified for UUID generation/import{Style.RESET_ALL}')
    length = flag_config['length']
    if ask_question_yn(f'Do you want to use a previously registered uuid for {app["name"].lower().title()}? (y/n):'):
        print(f'{Fore.GREEN}Please enter the alphanumeric part of the existing uuid for {app["name"].lower().title()}, it should be {length} characters long.')
        print('E.g. if existing registered node is sdk-node-b86301656baefekba8917349bdf0f3g4 then enter just b86301656baefekba8917349bdf0f3g4')
        uuid = ask_uuid('Insert uuid:', length)
    else:
        uuid = generate_uuid(length)
        print(f'{Fore.GREEN}Generated UUID: {uuid}{Style.RESET_ALL}')
    if 'claimURLBase' in flag_config:
        print(f'{Fore.BLUE}Save the following instructions/link somewhere to claim/register your {app["name"].lower().title()} '
              f'node/device after completing the setup and starting the apps stack:{Style.RESET_ALL}')
        print(f'{Fore.BLUE}{Style.BRIGHT}{flag_config["claimURLBase"]}{uuid}{Style.RESET_ALL}')
        try:
            with open(f'{app["name"].lower()}_claim_instructions.txt', 'w') as f:
                f.write(f'{flag_config["claimURLBase"]}{uuid}')
            print(f'{Fore.GREEN}Claim instructions written to {app["name"].lower()}_claim_instructions.txt{Style.RESET_ALL}')
        except Exception as e:
            logging.error(f'Error writing claim instructions to file: {e}')
        input('Press enter to continue...')
    config['uuid'] = uuid

def configure_cid(app: Dict, flag_config: Dict, config: Dict):
    print(f'Find your CID inside your {app["name"].lower().title()} dashboard/profile.')
    print("Example: For packetstream you can fetch it from your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page, you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)")
    cid = ask_string(f'{Fore.GREEN}Enter your {app["name"].lower().title()} CID:{Style.RESET_ALL}')
    config['cid'] = cid

def configure_code(app: Dict, flag_config: Dict, config: Dict):
    print(f'Find your code inside your {app["name"].lower().title()} dashboard/profile.')
    code = ask_string(f'{Fore.GREEN}Enter your {app["name"].lower().title()} code:{Style.RESET_ALL}')
    config['code'] = code

def configure_token(app: Dict, flag_config: Dict, config: Dict):
    print(f'Find your token inside your {app["name"].lower().title()} dashboard/profile.')
    token = ask_string(f'{Fore.GREEN}Enter your {app["name"].lower().title()} token:{Style.RESET_ALL}')
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

def _configure_apps(user_config: Dict[str, Any], apps: Dict, m4b_config: Dict):
    """
    Configure apps by collecting user inputs.

    Arguments:
    user_config -- the user configuration dictionary
    app_config -- the app configuration dictionary
    """
    for app in apps:
        app_name = app['name']
        config = user_config['apps'][app_name.lower()]
        cls()
        config['enabled'] = ask_question_yn(f'Do you want to run {app_name.title()}? (y/n):')
        if not config['enabled']:
            continue
        print(f'{Fore.CYAN}Go to {app_name.title()} {app["link"]} and register{Style.RESET_ALL}')
        print(f'{Fore.GREEN}Use CTRL+Click to open links or copy them:{Style.RESET_ALL}')
        input('When you are done press Enter to continue')
        for flag_name, flag_config in app.get('flags', {}).items():
            if flag_name in flag_function_mapper:
                flag_function_mapper[flag_name](app, flag_config, config)
            else:
                logging.error(f'Flag {flag_name} not recognized')
        time.sleep(m4b_config['system']['sleep_time'])

def configure_apps(user_config: Dict[str, Any], app_config: Dict, m4b_config: Dict) -> None:
    """
    Configure apps by collecting user inputs.

    Arguments:
    user_config -- the user configuration dictionary
    app_config -- the app configuration dictionary
    """
    _configure_apps(user_config, app_config['apps'], m4b_config)

def configure_extra_apps(user_config: Dict[str, Any], app_config: Dict, m4b_config: Dict) -> None:
    """
    Configure apps by collecting user inputs.

    Arguments:
    user_config -- the user configuration dictionary
    app_config -- the app configuration dictionary
    """
    _configure_apps(user_config, app_config['extra-apps'], m4b_config)

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
    m4b_config = loader.load_json_config(m4b_config_path)

    advance_setup = ask_question_yn('Do you want to go with Multiproxy setup? (y/n):')
    if advance_setup == 'y':
        logging.info("Multiproxy setup selected")
        print('Create a proxies.txt file in the same folder and add proxies in the following format: protocol://user:pass@ip:port (one proxy per line)')
        user_config['proxies']['multiproxy'] = True
        time.sleep(m4b_config['system']['sleep_time'])
    else:
        logging.info("Basic setup selected")
        if ask_question_yn('Do you want to setup proxy for the apps? (y/n)'):
            user_config['proxies']['proxy'] = input('Enter proxy details \n').strip()

    configure_apps(user_config, app_config, m4b_config)
    if ask_question_yn('Do you want to configure extra apps? (y/n)'):
        configure_extra_apps(user_config, app_config, m4b_config)
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
