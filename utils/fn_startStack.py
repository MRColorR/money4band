from utils.helper import is_user_root, is_user_in_docker_group, create_docker_group_if_needed, run_docker_command, show_spinner
from utils.prompt_helper import ask_question_yn
from utils.generator import generate_dashboard_urls
from utils.cls import cls
from utils import loader
import json
import os
import argparse
import logging
import platform
import subprocess
import time
import threading
from colorama import Fore, Style, just_fix_windows_console

# Ensure the parent directory is in the sys.path
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import the module from the parent directory

# Global config loading and global variables
m4b_config_path = os.path.join(parent_dir, "config", "m4b-config.json")
try:
    m4b_config = loader.load_json_config(m4b_config_path)
except FileNotFoundError:
    m4b_config = {}  # Fallback to empty config if not found
    logging.warning("Configuration file not found. Using default values.")

# Set global sleep time
sleep_time = m4b_config.get("system", {}).get(
    "sleep_time", 3)  # Default to 3 seconds if not specified


def start_stack(compose_file: str = './docker-compose.yaml', env_file: str = './.env', instance_name: str = 'money4band', skip_questions: bool = False) -> bool:
    """
    Start the Docker Compose stack using the provided compose and env files.

    Args:
        compose_file (str): The path to the Docker Compose file.
        env_file (str): The path to the environment file.
        instance_name (str): The name of the instance.
        skip_questions (bool): Whether to skip the confirmation question.

    Returns:
        bool: True if the stack started successfully, False otherwise.
    """
    logging.info(
        f"Starting stack for '{instance_name}' instance with compose file: {compose_file} and env file: {env_file}")
    just_fix_windows_console()

    if not skip_questions and not ask_question_yn(f"This will launch all the apps for '{instance_name}' instance using the configured .env file and the docker-compose.yaml file (Docker must be already installed and running). Do you wish to proceed?"):
        print(
            f"{Fore.BLUE}Docker stack startup for '{instance_name}' instance canceled.{Style.RESET_ALL}")
        time.sleep(sleep_time)
        return False

    event = threading.Event()
    spinner_thread = threading.Thread(target=show_spinner, args=(
        f"Starting stack for '{instance_name}'...", event))
    spinner_thread.start()

    use_sudo = not is_user_root() and platform.system().lower() == 'linux'
    try:
        command = ["docker", "compose", "-f", compose_file,
                   "--env-file", env_file, "up", "-d", "--remove-orphans"]
        result = run_docker_command(command, use_sudo=use_sudo)
        if result == 0:
            print(
                f"{Fore.GREEN}All Apps for '{instance_name}' instance started successfully.{Style.RESET_ALL}")
            logging.info(f"Stack for '{instance_name}' started successfully.")
        else:
            print(f"{Fore.RED}Error starting Docker stack for '{instance_name}' instance. Please check that Docker is running and that the configuration is complete, then try again.{Style.RESET_ALL}")
            logging.error(
                f"Stack for '{instance_name}' failed to start with exit code {result}.")
            time.sleep(sleep_time)
        return result == 0
    except Exception as e:
        print(f"{Fore.RED}An unexpected error occurred while starting the stack for '{instance_name}' instance.{Style.RESET_ALL}")
        logging.error(f"Unexpected error: {str(e)}")
        time.sleep(sleep_time)
    finally:
        event.set()
        spinner_thread.join()
    return False


def start_all_stacks(main_compose_file: str = './docker-compose.yaml', main_env_file: str = './.env', main_instance_name: str = 'money4band', instances_dir: str = 'm4b_proxy_instances', skip_questions: bool = False) -> None:
    """
    Start the main stack and all multi-proxy instances.

    Args:
        main_compose_file (str): The path to the main Docker Compose file.
        main_env_file (str): The path to the main environment file.
        main_instance_name (str): The name of the main instance.
        instances_dir (str): The directory containing the proxy instances.
        skip_questions (bool): Whether to skip the confirmation question.
    """
    if not skip_questions and not ask_question_yn(f"This will launch all the apps for '{main_instance_name}' and any multi-proxy instances using the configured .env files and docker-compose.yaml files. Docker must be already installed and running. Do you wish to proceed?"):
        print(f"{Fore.BLUE}Docker stack startup canceled.{Style.RESET_ALL}")
        time.sleep(sleep_time)
        return

    if platform.system().lower() == 'linux' and not is_user_in_docker_group():
        create_docker_group_if_needed()

    try:
        all_started = start_stack(
            main_compose_file, main_env_file, main_instance_name, skip_questions=True)
        if all_started and os.path.isdir(instances_dir):
            for instance in os.listdir(instances_dir):
                instance_dir = os.path.join(instances_dir, instance)
                compose_file = os.path.join(
                    instance_dir, 'docker-compose.yaml')
                env_file = os.path.join(instance_dir, '.env')
                if os.path.isfile(compose_file) and os.path.isfile(env_file):
                    try:
                        instance_started = start_stack(
                            compose_file, env_file, instance, skip_questions=True)
                        all_started &= instance_started
                        if not instance_started:
                            logging.error(
                                f"Failed to start instance '{instance}'")
                    except Exception as e:
                        all_started = False
                        logging.error(
                            f"Error starting instance '{instance}': {str(e)}")

        if all_started:
            generate_dashboard_urls(None, None, main_env_file)
            print(f"{Fore.YELLOW}Use the previously generated apps nodes URLs to add your device in any apps dashboard that require node claiming/registration (e.g., Earnapp, ProxyRack, etc.){Style.RESET_ALL}")
            logging.info("All stacks started successfully.")
    finally:
        time.sleep(sleep_time)


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    try:
        m4b_config = loader.load_json_config(m4b_config_path)
        user_config = loader.load_json_config(user_config_path)
        base_instance_name = m4b_config.get('project', {}).get(
            'compose_project_name', 'money4band')

        start_all_stacks(main_instance_name=base_instance_name)
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        print(f"{Fore.RED}File not found: {str(e)}{Style.RESET_ALL}")
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        print(f"{Fore.RED}Error decoding JSON: {str(e)}{Style.RESET_ALL}")
    except Exception as e:
        logging.error(
            f"An unexpected error occurred in main function: {str(e)}")
        print(f"{Fore.RED}An unexpected error occurred: {str(e)}{Style.RESET_ALL}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Start the Docker Compose stack.')
    parser.add_argument('--app-config', type=str, required=True,
                        help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=True,
                        help='Path to m4b_config JSON file')
    parser.add_argument('--user-config', type=str,
                        required=True, help='Path to user_config JSON file')
    parser.add_argument('--log-dir', default='./logs',
                        help='Set the logging directory')
    parser.add_argument('--log-file', default='fn_startStack.log',
                        help='Set the logging file name')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING',
                        'ERROR', 'CRITICAL'], default='INFO', help='Set the logging level')
    parser.add_argument('--skip-questions', action='store_true',
                        help='Skip confirmation questions')
    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.log_dir, args.log_file),
        format='%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=log_level
    )

    logging.info("Starting fn_startStack script...")

    try:
        main(app_config_path=args.app_config,
             m4b_config_path=args.m4b_config, user_config_path=args.user_config)
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
