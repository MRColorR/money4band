import json
import os
import argparse
import logging
import subprocess
from colorama import Fore, Style, just_fix_windows_console
from utils.cls import cls
import time

def stop_stack(compose_file: str = './docker-compose.yaml') -> None:
    """
    Stop the Docker Compose stack using the provided compose file.

    Args:
        compose_file (str): The path to the Docker Compose file.
    """
    logging.info(f"Stopping stack with compose file: {compose_file}")
    just_fix_windows_console()

    while True:
        response = input(f"{Fore.YELLOW}This will stop all the apps and delete the docker stack previously created using the configured docker-compose.yaml file. Do you wish to proceed (Y/N)?{Style.RESET_ALL} ").strip().lower()
        if response in ['y', 'yes']:
            try:
                result = subprocess.run(
                    ["docker", "compose", "-f", compose_file, "down"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"{Fore.GREEN}All Apps stopped and stack deleted.{Style.RESET_ALL}")
                time.sleep(2)
                logging.info(result.stdout)
            except subprocess.CalledProcessError as e:
                print(f"{Fore.RED}Error stopping and deleting Docker stack. Please check the configuration and try again.{Style.RESET_ALL}")
                logging.error(e.stderr)
            break
        elif response in ['n', 'no']:
            print(f"{Fore.BLUE}Docker stack removal canceled.{Style.RESET_ALL}")
            time.sleep(2)
            break
        else:
            print(f"{Fore.RED}Please answer yes or no.{Style.RESET_ALL}")

def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    stop_stack()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Stop the Docker Compose stack.')
    parser.add_argument('--app-config', type=str, required=False, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=True, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config', type=str, required=False, help='Path to user_config JSON file')
    parser.add_argument('--log-dir', default='./logs', help='Set the logging directory')
    parser.add_argument('--log-file', default='fn_stopStack.log', help='Set the logging file name')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help='Set the logging level')
    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.log_dir, args.log_file),
        format='%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=log_level
    )

    logging.info("Starting fn_stopStack script...")

    try:
        main(app_config_path=args.app_config, m4b_config_path=args.m4b_config, user_config_path=args.user_config)
        logging.info("fn_stopStack script completed successfully")
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise
