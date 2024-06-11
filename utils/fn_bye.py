import os
import argparse
import logging
import json
import time
import random
import sys
from typing import Dict, Any
from colorama import Fore, Style, just_fix_windows_console

# Ensure the parent directory is in the sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
# Import the module from the parent directory
from utils.cls import cls

# Initialize colorama for Windows compatibility
just_fix_windows_console()

def fn_bye(m4b_config: Dict[str, Any]) -> None:
    """
    Quit the application gracefully with a farewell message.

    Arguments:
    m4b_config -- the m4b configuration dictionary
    """
    try:
        logging.info("Exiting the application gracefully")
        cls()
        print(Fore.GREEN + "Thank you for using M4B! Please share this app with your friends!" + Style.RESET_ALL)
        print(Fore.GREEN + "Exiting the application..." + Style.RESET_ALL)

        sleep_time = m4b_config.get('system', {}).get('sleep_time', 1)
        farewell_messages = m4b_config.get('farewell_messages', [
            'Have a fantastic day!',
            'Happy earning!',
            'Goodbye!',
            'Bye! Bye!',
            'Did you know if you simply click enter while setting up apps the app will be skipper ^^',
            'Did you know typing 404 while seting up apps will g'
        ])

        time.sleep(sleep_time)
        print(random.choice(farewell_messages))
        time.sleep(sleep_time)
        sys.exit(0)
    except Exception as e:
        logging.error(f"An error occurred in fn_bye: {str(e)}")
        raise

def main(app_config: Dict[str, Any] = None, m4b_config: Dict[str, Any] = None, user_config: Dict[str, Any] = None) -> None:
    """
    Main function to call the fn_bye function.

    Arguments:
    app_config -- the app config dictionary
    m4b_config -- the m4b config dictionary
    user_config -- the user config dictionary
    """
    fn_bye(m4b_config)

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
