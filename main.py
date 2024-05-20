import os
import argparse
import logging
import locale
import time
from typing import Dict, Any
from colorama import Fore, Back, Style, just_fix_windows_console
from utils import load, detect
from utils.cls import cls

def mainmenu(m4b_config_path: str, apps_config_path: str, user_config_path: str, utils_dir_path: str) -> None:
    """
    Main menu of the script.

    Arguments:
    m4b_config_path -- the path to the m4b config file
    apps_config_path -- the path to the apps config file
    user_config_path -- the path to the user config file
    utils_dir_path -- the path to the utils directory
    """
    try:
        cls()
        logging.debug("Initializing colorama")
        just_fix_windows_console()
        logging.info("Colorama initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing colorama: {str(e)}")
        raise

    while True:
        try:
            logging.debug("Loading m4b config from config file")
            m4b_config = load.load_json_config(m4b_config_path)
            logging.info(f"Successfully loaded m4b config from {m4b_config_path}")
            logging.debug("Loading apps config from config file")
            apps_config = load.load_json_config(apps_config_path)
            logging.info(f"Successfully loaded apps config from {apps_config_path}")
            logging.debug("Loading user config from config file")
            user_config = load.load_json_config(user_config_path)
            logging.info(f"Successfully loaded user config from {user_config_path}")
        except FileNotFoundError as e:
            logging.error(f"File not found: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            raise

        try:
            logging.debug("Loading main menu")
            logging.debug("Loading OS and architecture maps from config file")
            sleep_time = m4b_config.get("system").get("sleep_time")
            system_info = {
                **detect.detect_os(m4b_config_path),
                **detect.detect_architecture(m4b_config_path)
            }

            # Load the functions from the passed tools dir
            logging.debug(f"Loading modules from {utils_dir_path}")
            m4b_tools_modules = load.load_modules_from_directory(utils_dir_path)
            logging.info(f"Successfully loaded modules from {utils_dir_path}")

            print(f"{Fore.GREEN}----------------------------------------------")
            print(f"{Back.GREEN}MONEY4BAND AUTOMATIC GUIDED SETUP v{m4b_config.get('project')['project_version']}{Back.RESET}")
            print(f"----------------------------------------------{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Support the M4B development <3 check the donation options in the README, on GitHub or in our Discord. Every bit helps!")
            print(f"{Fore.MAGENTA}Join our Discord community for updates, help and discussions: {m4b_config.get('project')['ds_project_server_url']}{Style.RESET_ALL}")
            print("----------------------------------------------")
            print(f"Detected OS type: {system_info.get('os_type')}")
            print(f"Detected architecture: {system_info.get('arch')}")
            print(f"Docker {system_info.get('dkarch')} image architecture will be used if the app's image permits it")
            print("----------------------------------------------")
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            raise

        try:
            # Load menu options from the JSON file
            logging.debug("Loading menu options from config file")
            menu_options = m4b_config["menu"]

            for i, option in enumerate(menu_options, start=1):
                print("{}. {}".format(i, option["label"]))

            choice = input("Select an option and press Enter: ")

            try:
                # Convert the user's choice to an integer
                choice = int(choice)
            except ValueError:
                print("Invalid input. Please select a menu option between 1 and {}.".format(len(menu_options)))
                time.sleep(sleep_time)
                continue

            if 1 <= choice <= len(menu_options):
                # Fetch the function name associated with the chosen menu item
                function_label = menu_options[choice - 1]["label"]
                function_name = menu_options[choice - 1]["function"]
                logging.info(f"User selected menu option number {choice} that corresponds to menu item {function_label}")
                m4b_tools_modules[function_name].main(apps_config, m4b_config, user_config)

            else:
                print("Invalid input. Please select a menu option between 1 and {}.".format(len(menu_options)))
                time.sleep(sleep_time)
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            raise

def main():   
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the script.')
    parser.add_argument('--config-dir', default=os.path.join(script_dir, 'config'), help='Set the config directory')
    parser.add_argument('--config-m4b-file', default='m4b-config.json', help='Set the m4b  config file name')
    parser.add_argument('--config-usr-file', default='user-config.json', help='Set  the user config file name')
    parser.add_argument('--config-app-file', default='app-config.json', help='Set the apps config file name')
    parser.add_argument('--utils-dir', default=os.path.join(script_dir, 'utils'), help='Set the m4b tools directory')
    parser.add_argument('--requirements-path', default=os.path.join(script_dir, 'requirements.toml'), help='Set the requirements path')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help='Set the logging level')
    parser.add_argument('--log-dir', default=os.path.join(script_dir, 'logs'), help='Set the logging directory')
    parser.add_argument('--log-file', default='m4b.log', help='Set the logging file name')
    args = parser.parse_args()
    # Address possible locale issues that use different notations for decimal numbers and so on
    locale.setlocale(locale.LC_ALL, 'C')

    # Set logging level based on command-line arguments
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    # Setup logging reporting date time, error level, and message
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(filename=os.path.join(args.log_dir, args.log_file), format='%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=log_level)

    logging.info(f"Starting {script_name} script...")

    try:
        mainmenu(
            m4b_config_path=os.path.join(args.config_dir, args.config_m4b_file),
            apps_config_path=os.path.join(args.config_dir, args.config_app_file),
            user_config_path=os.path.join(args.config_dir, args.config_usr_file),
            utils_dir_path=args.utils_dir
        )
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise


if __name__ == '__main__':
    main()