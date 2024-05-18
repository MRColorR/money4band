import os
import argparse
import logging
import json
from typing import Dict, Any
from colorama import Fore, Back, Style, just_fix_windows_console
from utils.cls import cls


def main(app_config: Dict=None, m4b_config=None):
    """
    Show the links of the apps.

    Arguments:
    app_config -- the app config dictionary
    m4b_config -- the m4b config dictionary (not used)
    """
    try:
        cls()
        just_fix_windows_console()
        print("Use CTRL+Click to open links or copy them:")

        # Iterate over all app types and apps
        for app_type, apps in app_config.items():
            print(f"{Back.YELLOW}---{app_type.upper()}---{Back.RESET}")
            for app in apps:
                print(f"{Fore.GREEN}{app['name'].upper()}: {Fore.CYAN}{app['link']}{Style.RESET_ALL}")

        input("Press Enter to go back to mainmenu")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == '__main__':
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the module standalone.')
    parser.add_argument('--app_config', type=str, required=False, help='Path to app_config JSON file')
    parser.add_argument('--m4b_config', type=str, required=False, help='Path to m4b_config JSON file')
    parser.add_argument('--log-dir', default=os.path.join(script_dir, 'logs'), help='Set the logging directory')
    parser.add_argument('--log-file', default=f"{script_name}.log", help='Set the logging file name')
    args = parser.parse_args()

    # Start logging
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(filename=os.path.join(args.log_dir, args.log_file),  format='%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level="DEBUG")

    msg = f"Testing {script_name} function"
    print(msg)
    logging.info(msg)

    # Test the function
    logging.info("Loading app_config JSON file")
    with open(args.app_config, 'r') as f:
        app_config = json.load(f)
        logging.info("app_config JSON file loaded successfully")

    logging.info("Loading m4b_config JSON file")
    with open(args.m4b_config, 'r') as f:
        m4b_config = json.load(f)
        logging.info("m4b_config JSON file loaded successfully")

    main(app_config, m4b_config)
    logging.info(f"{script_name} test complete")

    msg = f"{script_name} test complete"
    print(msg)
    logging.info(msg)
