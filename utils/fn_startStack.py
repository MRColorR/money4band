import json
import os
import argparse
import logging
import subprocess
import time
from colorama import Fore, Style, just_fix_windows_console
from utils.cls import cls

def start_stack(compose_file: str, env_file: str) -> None:
    """
    Start the Docker Compose stack using the provided compose and env files.

    Arguments:
    compose_file -- the path to the Docker Compose file
    env_file -- the path to the environment file
    """
    just_fix_windows_console()

    while True:
        response = input(f"{Fore.YELLOW}This will launch all the apps using the configured .env file and the docker-compose.yaml file (Docker must be already installed and running). Do you wish to proceed (Y/N)?{Style.RESET_ALL} ").strip().lower()
        if response in ['y', 'yes']:
            try:
                result = subprocess.run(
                    ["docker","compose" ,"-f", compose_file, "--env-file", env_file, "up", "-d"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"{Fore.GREEN}All Apps started successfully.{Style.RESET_ALL}")
                logging.info(result.stdout)

                dashboard_urls_script = "./generate_dashboard_urls.sh"
                if os.path.isfile(dashboard_urls_script):
                    os.chmod(dashboard_urls_script, 0o755)
                    result = subprocess.run([dashboard_urls_script], check=True, capture_output=True, text=True)
                    print(f"{Fore.GREEN}All Apps dashboards URLs generated. Check the generated dashboards file for the URLs.{Style.RESET_ALL}")
                    logging.info(result.stdout)
                else:
                    logging.error(f"{dashboard_urls_script} not found")

                print(f"{Fore.YELLOW}Use the previously generated apps nodes URLs to add your device in any apps dashboard that require node claiming/registration (e.g., Earnapp, ProxyRack, etc.){Style.RESET_ALL}")
            except subprocess.CalledProcessError as e:
                print(f"{Fore.RED}Error starting Docker stack. Please check the configuration and try again.{Style.RESET_ALL}")
                logging.error(e.stderr)
            break
        elif response in ['n', 'no']:
            print(f"{Fore.BLUE}Docker stack startup canceled.{Style.RESET_ALL}")
            time.sleep(1)
            break
        else:
            print(f"{Fore.RED}Please answer yes or no.{Style.RESET_ALL}")

def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    compose_file = './docker-compose.yaml'
    env_file = './.env'
    start_stack(compose_file, env_file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start the Docker Compose stack.')
    parser.add_argument('--app-config', type=str, required=True, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=True, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config', type=str, required=True, help='Path to user_config JSON file')
    parser.add_argument('--log-dir', default='./logs', help='Set the logging directory')
    parser.add_argument('--log-file', default='fn_startStack.log', help='Set the logging file name')
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

    logging.info("Starting fn_startStack script...")

    try:
        main(app_config_path=args.app_config, m4b_config_path=args.m4b_config, user_config_path=args.user_config)
        logging.info("fn_startStack script completed successfully")
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise
