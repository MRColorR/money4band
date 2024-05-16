import platform
import os
import json
import time
import logging
import argparse
from typing import Dict, Any
import locale
import importlib.util
from colorama import Fore, Style , just_fix_windows_console


# Load config variables from the config file
def load_json_config(config_file_path: str) -> Dict[str, Any]:
    """
    Load JSON config variables from a file.

    Arguments:
    config_file_path -- the path to the config file
    """
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


def load_module_from_file(module_name: str, file_path: str):
    """
    Dynamically load a module from a Python file.

    Arguments:
    module_name -- the name to give to the loaded module
    file_path -- the path to the Python file
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_modules_from_directory(directory_path: str):
    """
    Dynamically load all modules in a directory.

    Arguments:
    directory_path -- the path to the directory
    """
    modules = {}
    for filename in os.listdir(directory_path):
        if filename.endswith('.py') and filename != '__init__.py':
            path = os.path.join(directory_path, filename)
            module_name = filename[:-3]  # remove .py extension
            try:
                modules[module_name] = load_module_from_file(module_name, path)
                logging.info(f'Successfully loaded module: {module_name}')
            except Exception as e:
                logging.error(f'Failed to load module: {module_name}. Error: {str(e)}')
    return modules


def detect_os(os_map: Dict[str, str]) -> Dict[str, str]:
    """
    Detect the operating system and return its type.

    Arguments:
    os_map -- a dictionary mapping operating system names to their types
    """
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
    """
    Detect the system architecture and return its type.

    Arguments:
    arch_map -- a dictionary mapping system architectures to their types
    """
    try:
        logging.debug("Detecting system architecture")
        arch = platform.machine().lower()
        dkarch = arch_map.get(arch, "unknown")
        logging.info(f"System architecture detected: {arch}, Docker architecture has been set to {dkarch}")
        return {"arch": arch, "dkarch": dkarch}
    except Exception as e:
        logging.error(f"An error occurred while detecting architecture: {str(e)}")
        raise


def mainmenu(m4b_config: Dict[str, Any], apps_config: Dict[str, Any], utils_dir: str) -> None:
    while True:
        try:
            logging.debug("Loading main menu")
            logging.debug("Loading OS and architecture maps from config file")
            sleep_time = m4b_config.get("system").get("sleep_time")
            os_map = m4b_config.get("system").get("os_map")
            arch_map = m4b_config.get("system").get("arch_map")
            system_info = {
                **detect_os(os_map),
                **detect_architecture(arch_map)
            }
            
            # Load the functions from the passed utils_dir
            logging.debug(f"Loading modules from {utils_dir}")
            utils_modules = load_modules_from_directory(utils_dir)
            logging.info(f"Successfully loaded modules from {utils_dir}")

            print(f"{Fore.GREEN}----------------------------------------------")
            print(f"MONEY4BAND AUTOMATIC GUIDED SETUP v{m4b_config.get('project')['project_version']}")
            print(f"----------------------------------------------{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Support the M4B development <3 check the donation options in the README, on GitHub or in our Discord. Every bit helps!")
            print(f"{Fore.MAGENTA}Join our Discord community for updates, help and discussions: {m4b_config.get('project')['ds_project_server_url']}{Style.RESET_ALL}")
            print("----------------------------------------------")
            print(f"Detected OS type: {system_info.get('os_type')}")
            print(f"Detected architecture: {system_info.get('arch')}")
            print(f"Docker {system_info.get("dkarch")} image architecture will be used if the app's image permits it")
            print("----------------------------------------------")
        except:
            err_msg = "An error occurred while loading the main menu"
            logging.error(err_msg)
            print(err_msg)
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
                utils_modules[function_name].run(apps_config)


            else:
                print("Invalid input. Please select a menu option between 1 and {}.".format(len(menu_options)))
                time.sleep(sleep_time)
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
    default_utils_dir = os.path.join(script_dir, 'utils')
    default_requirements_path = os.path.join(script_dir, 'requirements.toml')

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the script.')
    parser.add_argument('--config-dir', default=default_config_dir, help='Set the config directory')
    parser.add_argument('--config-m4b-file', default='m4b-config.json', help='Set the m4b  config file name')
    parser.add_argument('--config-usr-file', default='usr-config.json', help='Set  the user config file name')
    parser.add_argument('--config-app-file', default='app-config.json', help='Set the apps config file name')
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
    # log colorama init in a try
    try:
        logging.debug("Initializing colorama")
        just_fix_windows_console()
        logging.info("Colorama initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing colorama: {str(e)}")
        raise
    m4b_config = load_json_config(os.path.join(args.config_dir, args.config_m4b_file))
    apps_config = load_json_config(os.path.join(args.config_dir, args.config_app_file))
    # run mainmenu function until exit
    mainmenu(m4b_config=m4b_config, 
             apps_config=apps_config, 
             utils_dir=args.utils_dir
             )

if __name__ == '__main__':
    main()
