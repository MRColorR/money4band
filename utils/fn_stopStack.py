import json
import os
import argparse
import logging
import subprocess
from colorama import Fore, Style, just_fix_windows_console
from utils.cls import cls
import time
from utils.prompt_helper import ask_question_yn
from utils.loader import load_json_config

def stop_stack(compose_file: str = './docker-compose.yaml', instance_name: str = 'money4band', skip_questions: bool = False) -> None:
    """
    Stop the Docker Compose stack using the provided compose file.

    Args:
        compose_file (str): The path to the Docker Compose file.
        instance_name (str): The name of the instance.
        skip_questions (bool): Whether to skip the confirmation question.
    """
    logging.info(f"Stopping stack for '{instance_name}' instance with compose file: {compose_file}")
    just_fix_windows_console()

    if not skip_questions and not ask_question_yn(f"This will stop all the apps for '{instance_name}' instance and delete the docker stack previously created using the configured docker-compose.yaml file. Do you wish to proceed?"):
        print(f"{Fore.BLUE}Docker stack removal for '{instance_name}' instance canceled.{Style.RESET_ALL}")
        time.sleep(2)
        return

    try:
        result = subprocess.run(
            ["docker", "compose", "-f", compose_file, "down"],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"{Fore.GREEN}All Apps for '{instance_name}' instance stopped and stack deleted.{Style.RESET_ALL}")
        time.sleep(2)
        logging.info(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Error stopping and deleting Docker stack for '{instance_name}' instance. Please check the configuration and try again.{Style.RESET_ALL}")
        logging.error(e.stderr)
        time.sleep(2)
    except Exception as e:
        print(f"{Fore.RED}An unexpected error occurred while stopping the stack for '{instance_name}' instance.{Style.RESET_ALL}")
        logging.error(f"Unexpected error: {str(e)}")
        time.sleep(2)


def stop_multi_proxy_instances(instances_dir: str = 'm4b_proxy_instances', skip_questions: bool = False) -> None:
    """
    Stop all multi-proxy instances by iterating through the instances directory.

    Args:
        instances_dir (str): The directory containing the proxy instances.
        skip_questions (bool): Whether to skip the confirmation question.
    """
    if os.path.isdir(instances_dir):
        print(f"{Fore.YELLOW}Stopping multi-proxy instances...{Style.RESET_ALL}")
        for instance in os.listdir(instances_dir):
            instance_dir = os.path.join(instances_dir, instance)
            compose_file = os.path.join(instance_dir, 'docker-compose.yaml')
            if os.path.isfile(compose_file):
                try:
                    stop_stack(compose_file, instance, skip_questions=skip_questions)
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
        stop_stack(instance_name=base_instance_name, skip_questions=False)
        if user_config['proxies'].get('enabled', False):
            stop_multi_proxy_instances(skip_questions=True)
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
    parser.add_argument('--app-config', type=str, required=False, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=True, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config', type=str, required=False, help='Path to user_config JSON file')
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
        main(app_config_path=args.app_config, m4b_config_path=args.m4b_config, user_config_path=args.user_config, skip_questions=args.skip_questions)
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
