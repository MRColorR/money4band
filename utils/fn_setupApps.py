import os
import argparse
import logging
import json
from typing import Dict, Any
from colorama import Fore, Back, Style, just_fix_windows_console
from utils import loader, detector
from utils.cls import cls
from utils.dumper import write_json

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

def configure_apps(user_config: Dict[str, Any]) -> None:
    """
    Configure apps by collecting user inputs.

    Arguments:
    user_config -- the user configuration dictionary
    """
    asking = {
        'enabled': 'Do you want to run {}: ',
        'email': 'Enter your {} email: ',
        'password': 'Enter your {} password: ',
        'apikey': 'Enter your {} API key: ',
        'cid': 'Enter your {} CID: ',
        'token': 'Enter your {} token: ',
        'code': 'Enter your {} code: '
    }

    for app, properties in user_config['apps'].items():
        cls()
        for property, prompt in asking.items():
            if property in properties:
                user_input = input(prompt.format(app.title()))
                user_input = user_input.lower().strip()

                if property == 'enabled':
                    if user_input != 'y':
                        logging.info(f'Skipping {app}')
                        break
                    else:
                        user_config['apps'][app][property] = True
                else:
                    user_config['apps'][app][property] = user_input

def main(app_config: Dict[str, Any] = None, m4b_config: Dict[str, Any] = None, user_config_path: str = './config/user-config.json') -> None:
    """
    Main function for setting up user configurations.

    Arguments:
    app_config -- the app configuration dictionary
    m4b_config -- the m4b configuration dictionary
    user_config_path -- the path to the user configuration JSON file
    """
    user_config = loader.load_json_config(user_config_path)

    advance_setup = input('Do you want to go with advanced setup? (y/n): ').lower().strip()
    if advance_setup == 'y':
        logging.info("Advanced setup selected")
        # Advanced setup code can be added here if needed
    else:
        logging.info("Basic setup selected")
        collect_user_info(user_config)
        configure_apps(user_config)

    write_json(user_config, user_config_path)

if __name__ == '__main__':
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the module standalone.')
    parser.add_argument('--app-config', type=str, required=False, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=False, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config', type=str, default='./config/user-config.json', help='Path to user_config JSON file')
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
        # Load the app_config JSON file
        app_config = {}
        if args.app_config:
            logging.debug("Loading app_config JSON file")
            with open(args.app_config, 'r') as f:
                app_config = json.load(f)
            logging.info("app_config JSON file loaded successfully")

        # Load the m4b_config JSON file if provided
        m4b_config = {}
        if args.m4b_config:
            logging.debug("Loading m4b_config JSON file")
            with open(args.m4b_config, 'r') as f:
                m4b_config = json.load(f)
            logging.info("m4b_config JSON file loaded successfully")
        else:
            logging.info("No m4b_config JSON file provided, proceeding without it")

        # Load the user_config JSON file
        user_config = {}
        if args.user_config:
            logging.debug("Loading user_config JSON file")
            with open(args.user_config, 'r') as f:
                user_config = json.load(f)
            logging.info("user_config JSON file loaded successfully")

        # Call the main function
        main(app_config=app_config, m4b_config=m4b_config, user_config_path=args.user_config)

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

def main(app_config:dict,m4b_config:dict,user_config:dict=load.load_json_config('./config/user-config.json')):
    user_config = load.load_json_config('./config/user-config.json')
    multiproxy = input('Do you want to run multiproxy(y/n)')
    if multiproxy.lower().strip(' ') == 'y':
        user_config['proxies']['multiproxy'] = True
        # maybe automatically create a proxies.txt file
    else:
        single_proxy = input('Do you want to set up a single proxy?')


    nickename = input('Enter your nickname')
    #Dont think email is needed
    device_name = input('Enter your device name')

    user_config['user']['Nickname'] = nickename
    user_config['device_info']['device_name'] = device_name


    #ask proxy info lazy to code rn

    #Set up apps now
    asking = {
        'enabled': 'Do you want to run {}: ',
        'email': 'Enter your {} email : ',
        'password': 'Enter your {} password : ',
        'apikey': 'Enter your {} api key : ',
        'cid': 'Enter your {} cid : ',
        'token': 'Enter your {} token :',
        'code': 'Enter your {} code : '
    }
    for app in user_config['apps']:
        cls()
        for property in user_config['apps'][app]:
            if property in asking:
                user_input = input(asking[property].format(app.title()))
                print(user_input.lower().strip(' '))
                if property == 'enabled':
                    if user_input.lower().strip(' ') !='y':
                        print(f'skipping {app}')
                        break
                    else:
                        user_config['apps'][app][property] = True
                else:
                    user_config['apps'][app][property] = user_input

    #ask additional config settings 


    write_json(user_config,'./config/user-config.json')
