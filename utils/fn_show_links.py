from utils.loader import load_json_config
from utils.cls import cls
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
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
# Import the module from the parent directory


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
            if not isinstance(apps, list):
                logging.warning(f"Skipping {category} as it is not a list")
                continue

            if len(apps) == 0:
                continue

            print(f"{Back.YELLOW}---{category.upper()}---{Back.RESET}")
            for app in apps:
                print(
                    f"{Fore.GREEN}{app['name'].upper()}: {Fore.CYAN}{app['link']}{Style.RESET_ALL}"
                )
            print("\n")

        print("Info: Use CTRL+Click to open links or copy them")
        input("Press Enter to go back to main menu")
    except Exception as e:
        logging.error(f"An error occurred in fn_show_links: {str(e)}")
        raise


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Main function to call the fn_show_links function.

    Arguments:
    app_config_path -- the path to the app configuration file
    m4b_config_path -- the path to the m4b configuration file
    user_config_path -- the path to the user configuration file
    """
    app_config = load_json_config(app_config_path)
    fn_show_links(app_config)


if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the module standalone.")
    parser.add_argument(
        "--app-config", type=str, required=True, help="Path to app_config JSON file"
    )
    parser.add_argument(
        "--m4b-config", type=str, required=False, help="Path to m4b_config JSON file"
    )
    parser.add_argument(
        "--user-config", type=str, required=False, help="Path to user_config JSON file"
    )
    parser.add_argument(
        "--log-dir",
        default=os.path.join(script_dir, "logs"),
        help="Set the logging directory",
    )
    parser.add_argument(
        "--log-file", default=f"{script_name}.log", help="Set the logging file name"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    args = parser.parse_args()

    # Set logging level based on command-line arguments
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    # Start logging
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.log_dir, args.log_file),
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_level,
    )

    logging.info(f"Starting {script_name} script...")

    try:
        main(
            app_config_path=args.app_config,
            m4b_config_path=args.m4b_config,
            user_config_path=args.user_config,
        )
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
