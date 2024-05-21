import os
import argparse
import logging
import json
from typing import Dict
from colorama import Fore, Back, Style, just_fix_windows_console
# Ensure the parent directory is in the sys.path
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
# Import the module from the parent directory
from utils.cls import cls

def fn_show_links(app_config: Dict) -> None:
    """
    Show the links of the apps.

    Arguments:
    app_config -- the app config dictionary
    """
    try:
        logging.info("Showing links of the apps")
        cls()
        just_fix_windows_console()
        # Iterate over all categories and apps
        for category, apps in app_config.items():
            print(f"{Back.YELLOW}---{category.upper()}---{Back.RESET}")
            for app in apps:
                print(f"{Fore.GREEN}{app['name'].upper()}: {Fore.CYAN}{app['link']}{Style.RESET_ALL}")
        print("\nInfo: Use CTRL+Click to open links or copy them:")
        input("Press Enter to go back to main menu")
    except Exception as e:
        logging.error(f"An error occurred in fn_show_links: {str(e)}")
        raise

def main(app_config: Dict = None, m4b_config: Dict = None, user_config: Dict = None) -> None:
    """
    Main function to call the fn_show_links function.

    Arguments:
    app_config -- the app config dictionary
    m4b_config -- the m4b config dictionary
    user_config -- the user config dictionary
    """
    fn_show_links(app_config)

if __name__ == '__main__':
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the module standalone.')
    parser.add_argument('--app-config', type=str, required=True, help='Path to app_config JSON file')
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
