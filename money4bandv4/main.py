import platform
import os
import json
import time
import logging
import argparse
from typing import Dict, Any
import locale

# Load config variables from the config file
def load_json_config(config_file_path: str) -> Dict[str, Any]:
    try:
        with open(config_file_path, 'r') as f:
            logging.debug(f"Loading config from {config_file_path}")
            config = json.load(f)
        logging.info(f"Successfully loaded config from {config_file_path}")
        return config
    except FileNotFoundError:
        logging.error(f"Config file {config_file_path} not found.")
        raise
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {config_file_path}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred when loading {config_file_path}: {str(e)}")
        raise

def detect_os(os_map: Dict[str, str]) -> Dict[str, str]:
    try:
        logging.debug("Detecting OS type")
        os_type = platform.system().lower()
        os_type = os_map.get(os_type, "unknown")
        logging.info(f"OS type detected: {os_type}")
        return {"os_type": os_type}
    except Exception as e:
        logging.error(f"An error occurred while detecting OS: {str(e)}")
        raise

def detect_architecture(arch_map: Dict[str, str]) -> Dict[str, str]:
    try:
        logging.debug("Detecting system architecture")
        arch = platform.machine().lower()
        dkarch = arch_map.get(arch, "unknown")
        logging.info(f"System architecture detected: {arch}, Docker architecture has been set to {dkarch}")
        return {"arch": arch, "dkarch": dkarch}
    except Exception as e:
        logging.error(f"An error occurred while detecting architecture: {str(e)}")
        raise

def mainmenu(m4b_config: Dict[str, Any]) -> None:
    while True:
        try:
            logging.debug("Loading main menu")
            logging.debug("Loading OS and architecture maps from config file")
            os_map = m4b_config["system"]["os_map"]
            arch_map = m4b_config["system"]["arch_map"]
            system_info = {
                **detect_os(os_map),
                **detect_architecture(arch_map)
            }
            print("----------------------------------------------")
            print("MONEY4BAND AUTOMATIC GUIDED SETUP v{}".format(m4b_config.get("project")["project_version"]))
            print("----------------------------------------------")
            print("Support the M4B development <3 check the donation options in the README, on GitHub or in our Discord. Every bit helps!")
            print("Join our Discord community for updates, help and discussions: {}".format(m4b_config.get("project")["ds_project_server_url"]))
            print("----------------------------------------------")
            print("Detected OS type: {}".format(system_info.get("os_type")))
            print("Detected architecture: {}".format(system_info.get("arch")))
            print("Docker {} image architecture will be used if the app's image permits it".format(system_info.get("dkarch")))
            print("----------------------------------------------")
        except:
            err_msg = "An error occurred while loading the main menu"
            logging.error(err_msg)
            print(err_msg)
            raise
        try:
            # Load menu options from the JSON file
            logging.debug("Loading menu options from config file")
            with open(os.path.join(args.config_dir, args.config_app_file), 'r') as f:
                menu_options = json.load(f)

            for i, option in enumerate(menu_options, start=1):
                print("{}. {}".format(i, option["name"]))

            choice = input("Select an option and press Enter: ")

            try:
                # Convert the user's choice to an integer
                choice = int(choice)
            except ValueError:
                print("Invalid input. Please select a menu option between 1 and {}.".format(len(menu_options)))
                time.sleep(SLEEP_TIME)
                continue

            if 1 <= choice <= len(menu_options):
                # Fetch the function name associated with the chosen menu item
                function_name = menu_options[choice - 1]["name"]
                print("You selected option number {} that corresponds to menu item {}".format(choice, function_name))
                # Invoke the function
                # You'll need to define these functions elsewhere in your code

            else:
                print("Invalid input. Please select a menu option between 1 and {}.".format(len(menu_options)))
                time.sleep(SLEEP_TIME)
        except Exception as e:
            err_msg = f"An error occurred: {e}"
            print(err_msg)
            logging.error(err_msg)
            raise


def main():
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Get the default directories
    default_log_dir = os.path.join(script_dir, 'logs')
    default_config_dir = os.path.join(script_dir, 'config')
    default_apps_dir = os.path.join(script_dir, 'apps')
    default_utils_dir = os.path.join(script_dir, 'utils')
    default_requirements_path = os.path.join(script_dir, 'requirements.toml')

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the script.')
    parser.add_argument('--config-dir', default=default_config_dir, help='Set the config directory')
    parser.add_argument('--config-m4b-file', default='m4b-config.json', help='Set the m4b  config file name')
    parser.add_argument('--config-usr-file', default='usr-config.json', help='Set  the user config file name')
    parser.add_argument('--config-app-file', default='app-config.json', help='Set the apps config file name')
    parser.add_argument('--apps-dir', default=default_apps_dir, help='Set the apps directory')
    parser.add_argument('--utils-dir', default=default_utils_dir, help='Set the utils directory')
    parser.add_argument('--requirements-path', default=default_requirements_path, help='Set the requirements path')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help='Set the logging level')
    parser.add_argument('--log-dir', default=default_log_dir, help='Set the logging directory')
    parser.add_argument('--log-file', default='m4b.log', help='Set the logging file name')
    args = parser.parse_args()

    # Address possible locale issues that uses different notations for decimal numbers and so on
    locale.setlocale(locale.LC_ALL, 'C')

    # Set logging level based on command-line arguments
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    # Setup logging reporting date time, error level and message
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(filename=os.path.join(args.log_dir, args.log_file), format='%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=log_level)

    logging.info(f"Starting {script_name} script...")
    m4b_config = load_json_config(os.path.join(args.config_dir, args.config_m4b_file))
    # run mainmenu function until exit
    mainmenu(m4b_config=m4b_config)

if __name__ == '__main__':
    main()
