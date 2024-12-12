import os
import argparse
import logging
from logging.handlers import RotatingFileHandler
import locale
import time
from typing import Dict, Any
from colorama import Fore, Back, Style, just_fix_windows_console

# Ensure the parent directory is in the sys.path
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import the module from the parent directory
from utils import detector, loader, dumper
from utils.cls import cls
from utils.fn_reset_config import main as reset_main
from utils.updater import check_update_available


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
        logging.debug("Initializing colorama")
        just_fix_windows_console()
        logging.info("Colorama initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing colorama: {str(e)}")
        raise

    while True:
        try:
            logging.info("Loading configurations")
            m4b_config = loader.load_json_config(m4b_config_path)
            user_config = loader.load_json_config(user_config_path)
            logging.info("Configurations loaded successfully")
        except FileNotFoundError as e:
            logging.error(f"File not found: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"An error occurred while loading configurations: {str(e)}")
            raise

        try:
            logging.debug("Loading main menu")
            sleep_time = m4b_config.get("system", {}).get("sleep_time", 2)

            logging.debug("Detecting OS and architecture")
            system_info = {
                **detector.detect_os(m4b_config_path),
                **detector.detect_architecture(m4b_config_path)
            }

            # Update user_config with detected OS, architecture, and docker architecture
            device_info = user_config.setdefault("device_info", {})
            device_info["os_type"] = system_info.get("os_type")
            device_info["detected_architecture"] = system_info.get("arch")
            device_info["detected_docker_arch"] = system_info.get("dkarch")

            # Add default platform for apps if not already present
            for app_name in user_config.get("apps", {}):
                app_config = user_config["apps"].setdefault(app_name, {})
                app_config["docker_platform"] = f"linux/{device_info['detected_docker_arch']}"

            dumper.write_json(user_config, user_config_path)
            logging.info(f"System info and default platform stored: {device_info}")

            logging.debug("Calculating resources limits based on system")
            detector.calculate_resource_limits(user_config_path_or_dict=user_config_path)

            # Load the functions from the passed tools dir
            logging.debug(f"Loading modules from {utils_dir_path}")
            m4b_tools_modules = loader.load_modules_from_directory(utils_dir_path)
            logging.info(f"Successfully loaded modules from {utils_dir_path}")
            cls()
            print(f"{Fore.GREEN}----------------------------------------------")
            print(f"{Fore.GREEN}MONEY4BAND AUTOMATIC GUIDED SETUP v{m4b_config.get('project')['project_version']}{Style.RESET_ALL}")
            check_update_available(m4b_config)
            print(f"{Fore.GREEN}----------------------------------------------{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Support the M4B development <3 check the donation options in the README, on GitHub or in our Discord. Every bit helps!")
            print(f"{Fore.MAGENTA}Join our Discord community for updates, help and discussions: {m4b_config.get('project')['ds_project_server_url']}{Style.RESET_ALL}")
            print("----------------------------------------------")
            print(f"Detected OS type: {system_info.get('os_type')}")
            print(f"Detected architecture: {system_info.get('arch')}")
            print(f"Docker {system_info.get('dkarch')} image architecture will be used if the app's image permits it")
            print("----------------------------------------------")
        except Exception as e:
            logging.error(f"An error occurred while setting up the menu: {str(e)}")
            raise
        try:
            logging.debug("Loading menu options from config file")
            menu_options = m4b_config["menu"]

            for i, option in enumerate(menu_options, start=1):
                print(f"{i}. {option['label']}")

            choice = input("Select an option and press Enter: ")

            try:
                choice = int(choice)
            except ValueError:
                print(f"Invalid input. Please select a menu option between 1 and {len(menu_options)}.")
                time.sleep(sleep_time)
                continue

            if 1 <= choice <= len(menu_options):
                function_label = menu_options[choice - 1]["label"]
                function_name = menu_options[choice - 1]["function"]
                logging.info(f"User selected menu option number {choice} that corresponds to menu item {function_label}")
                m4b_tools_modules[function_name].main(apps_config_path, m4b_config_path, user_config_path)
            else:
                print(f"Invalid input. Please select a menu option between 1 and {len(menu_options)}.")
                time.sleep(sleep_time)
        except Exception as e:
            logging.error(f"An error occurred while processing the menu: {str(e)}")
            raise


def main():
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the script.')
    parser.add_argument('--config-dir', default=os.path.join(script_dir, 'config'), help='Set the config directory')
    parser.add_argument('--config-m4b-file', default='m4b-config.json', help='Set the m4b config file name')
    parser.add_argument('--config-usr-file', default='user-config.json', help='Set the user config file name')
    parser.add_argument('--config-app-file', default='app-config.json', help='Set the apps config file name')
    parser.add_argument('--utils-dir', default=os.path.join(script_dir, 'utils'), help='Set the m4b tools directory')
    parser.add_argument('--requirements-path', default=os.path.join(script_dir, 'requirements.toml'), help='Set the requirements path')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help='Set the logging level')
    parser.add_argument('--log-dir', default=os.path.join(script_dir, 'logs'), help='Set the logging directory')
    parser.add_argument('--log-file', default='m4b.log', help='Set the logging file name')
    parser.add_argument('--template-user-config-path', default=os.path.join(script_dir, 'template', 'user-config.json'), help='Set the template user config file path')
    args = parser.parse_args()

    # Address possible locale issues that use different notations for decimal numbers and so on
    locale.setlocale(locale.LC_ALL, 'C')

    # Set logging level based on command-line arguments
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    # Setup logging with rotation and reporting date time, error level, and message
    os.makedirs(args.log_dir, exist_ok=True)
    log_file_path = os.path.join(args.log_dir, args.log_file)
    rotating_handler = RotatingFileHandler(log_file_path, maxBytes=1*1024*1024, backupCount=3)  # 1 MB per file, keep 3 backups
    rotating_handler.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    rotating_handler.setLevel(log_level)

    logging.basicConfig(level=log_level, handlers=[rotating_handler])

    logging.info(f"Starting {script_name} script...")

    # Check if user config exists; if not, reset it from the template
    user_config_path = os.path.join(args.config_dir, args.config_usr_file)
    if not os.path.exists(user_config_path):
        logging.info("User config not found. Resetting from template...")
        # Call the reset_config main function
        reset_main(
            app_config_path=None,
            m4b_config_path=None,
            user_config_path=user_config_path,
            src_path=args.template_user_config_path,
            dest_path=user_config_path
        )

    try:
        mainmenu(
            m4b_config_path=os.path.join(args.config_dir, args.config_m4b_file),
            apps_config_path=os.path.join(args.config_dir, args.config_app_file),
            user_config_path=user_config_path,
            utils_dir_path=args.utils_dir
        )
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise


if __name__ == '__main__':
    main()
