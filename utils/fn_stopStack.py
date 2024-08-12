import json
import os
import argparse
import logging
import platform
import subprocess
import time
from colorama import Fore, Style, just_fix_windows_console

# Ensure the parent directory is in the sys.path
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from utils.cls import cls
from utils.prompt_helper import ask_question_yn
from utils.loader import load_json_config
from utils.helper import is_user_root, is_user_in_docker_group, create_docker_group_if_needed, run_docker_command

def stop_stack(compose_file: str = './docker-compose.yaml', instance_name: str = 'money4band', skip_questions: bool = False) -> bool:
    """
    Stop the Docker Compose stack using the provided compose file.

    Args:
        compose_file (str): The path to the Docker Compose file.
        instance_name (str): The name of the instance.
        skip_questions (bool): Whether to skip the confirmation question.

    Returns:
        bool: True if the stack stopped successfully, False otherwise.
    """
    logging.info(f"Stopping stack for '{instance_name}' instance with compose file: {compose_file}")
    just_fix_windows_console()

    if not skip_questions and not ask_question_yn(f"This will stop all the apps for '{instance_name}' instance and delete the docker stack previously created using the configured docker-compose.yaml file. Do you wish to proceed?"):
        print(f"{Fore.BLUE}Docker stack removal for '{instance_name}' instance canceled.{Style.RESET_ALL}")
        time.sleep(2)
        return False

    use_sudo = not is_user_root() and platform.system().lower() == 'linux'
    try:
        command = ["docker", "compose", "-f", compose_file, "down"]
        result = run_docker_command(command, use_sudo=use_sudo)
        print(f"{Fore.GREEN}All Apps for '{instance_name}' instance stopped and stack deleted.{Style.RESET_ALL}")
        time.sleep(2)
        logging.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Error stopping and deleting Docker stack for '{instance_name}' instance. Please check the configuration and try again.{Style.RESET_ALL}")
        logging.error(e.stderr)
        time.sleep(2)
    except Exception as e:
        print(f"{Fore.RED}An unexpected error occurred while stopping the stack for '{instance_name}' instance.{Style.RESET_ALL}")
        logging.error(f"Unexpected error: {str(e)}")
        time.sleep(2)
    return False

def stop_all_stacks(main_compose_file: str = './docker-compose.yaml', main_instance_name: str = 'money4band', instances_dir: str = 'm4b_proxy_instances', skip_questions: bool = False) -> None:
    """
    Stop the main stack and all multi-proxy instances.

    Args:
        main_compose_file (str): The path to the main Docker Compose file.
        main_instance_name (str): The name of the main instance.
        instances_dir (str): The directory containing the proxy instances.
        skip_questions (bool): Whether to skip the confirmation question.
    """
    if not skip_questions and not ask_question_yn(f"This will stop all the apps for '{main_instance_name}' and any multi-proxy instances and delete the docker stacks previously created. Do you wish to proceed?"):
        print(f"{Fore.BLUE}Docker stack removal canceled.{Style.RESET_ALL}")
        time.sleep(2)
        return

    if platform.system().lower() == 'linux' and not is_user_in_docker_group():
        create_docker_group_if_needed()

    stop_stack(main_compose_file, main_instance_name, skip_questions=True)
    if os.path.isdir(instances_dir):
        print(f"{Fore.YELLOW}Stopping multi-proxy instances...{Style.RESET_ALL}")
        for instance in os.listdir(instances_dir):
            instance_dir = os.path.join(instances_dir, instance)
            compose_file = os.path.join(instance_dir, 'docker-compose.yaml')
            if os.path.isfile(compose_file):
                try:
                    stop_stack(compose_file, instance, skip_questions=True)
                except Exception as e:
                    logging.error(f"Failed to stop instance '{instance}': {str(e)}")
        print(f"{Fore.GREEN}All multi-proxy instances stopped successfully.{Style.RESET_ALL}")
    else:
        logging.warning(f"Multi-proxy instances directory '{instances_dir}' does not exist.")

def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    try:
        m4b_config = load_json_config(m4b_config_path)
        user_config = load_json_config(user_config_path)
        base_instance_name = m4b_config.get('project', {}).get('compose_project_name', 'money4band')

        stop_all_stacks(main_instance_name=base_instance_name)
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        print(f"{Fore.RED}File not found: {str(e)}{Style.RESET_ALL}")
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        print(f"{Fore.RED}Error decoding JSON: {str(e)}{Style.RESET_ALL}")
    except Exception as e:
        logging.error(f"An unexpected error occurred in main function: {str(e)}")
        print(f"{Fore.RED}An unexpected error occurred: {str(e)}{Style.RESET_ALL}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Stop the Docker Compose stack.')
    parser.add_argument('--app-config', type=str, required=True, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=True, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config', type=str, required=True, help='Path to user_config JSON file')
    parser.add_argument('--log-dir', default='./logs', help='Set the logging directory')
    parser.add_argument('--log-file', default='fn_stopStack.log', help='Set the logging file name')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help='Set the logging level')
    parser.add_argument('--skip-questions', action='store_true', help='Skip confirmation questions')
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
