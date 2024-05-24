import os
import argparse
import logging
import time
import random
import sys
import json
from typing import Dict, Any
from colorama import Fore, Style, just_fix_windows_console
from utils.cls import cls

# Initialize colorama for Windows compatibility
just_fix_windows_console()

def main(app_config: Dict[str, Any], m4b_config: Dict[str, Any], user_config: Dict[str, Any]):
    """
    Quit the application gracefully with a farewell message.

    Parameters:
    app_config (dict): The application configuration dictionary.
    m4b_config (dict): The m4b configuration dictionary.
    user_config (dict): The user configuration dictionary.
    """
    cls()
    print(f"{Fore.GREEN}Share this app with your friends thank you!{Style.RESET_ALL}")
    print(Fore.CYAN + "Support the M4B development <3 check the donation options in the README, on GitHub or in our Discord. Every bit helps!" + Style.RESET_ALL)
    print(Fore.GREEN + "Exiting the application...Bye!Bye!" + Style.RESET_ALL)

    sleep_time = m4b_config.get('system', {}).get('sleep_time', 1)
    time.sleep(sleep_time)

    farewell_messages = [
        'Have a great day........',
        'If you see this then Sam probably succeeded in making this, yay!!!',
        'Look into the eyes deeper, they never lie!!',
        'Enjoy the rest of your day',
        'The world will never be with you when you need it the most :('
    ]
    print(random.choice(farewell_messages))
    time.sleep(sleep_time)
    sys.exit()

if __name__ == '__main__':
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the module standalone.')
    parser.add_argument('--app-config', type=str, required=False, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=False, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config', type=str, required=False, help='Path to user_config JSON file')
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

        # Load the user_config JSON file if provided
        user_config = {}
        if args.user_config:
            logging.debug("Loading user_config JSON file")
            with open(args.user_config, 'r') as f:
                user_config = json.load(f)
            logging.info("user_config JSON file loaded successfully")
        else:
            logging.info("No user_config JSON file provided, proceeding without it")

        # Call the main function
        main(app_config=app_config, m4b_config=m4b_config, user_config=user_config)

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
