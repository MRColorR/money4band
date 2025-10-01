from utils.helper import (
    is_user_root,
    is_user_in_docker_group,
    create_docker_group_if_needed,
    run_docker_command,
    show_spinner,
)
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
import re

# Ensure the parent directory is in the sys.path
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Global config loading and global variables
m4b_config_path = os.path.join(parent_dir, "config", "m4b-config.json")
try:
    m4b_config = loader.load_json_config(m4b_config_path)
except FileNotFoundError:
    m4b_config = {}  # Fallback to empty config if not found
    logging.warning("Configuration file not found. Using default values.")

# Set global sleep time
sleep_time = m4b_config.get("system", {}).get(
    "sleep_time", 3
)  # Default to 3 seconds if not specified


def get_compose_project_name(env_file: str) -> str:
    """
    Extract the COMPOSE_PROJECT_NAME from an environment file.

    Args:
        env_file (str): Path to the .env file

    Returns:
        str: The COMPOSE_PROJECT_NAME value, or None if not found
    """
    project_name = None
    try:
        if os.path.isfile(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    if line.startswith("COMPOSE_PROJECT_NAME="):
                        project_name = line.strip().split("=", 1)[1]
                        logging.info(
                            f"Found COMPOSE_PROJECT_NAME in {env_file}: {project_name}"
                        )
                        break
    except Exception as e:
        logging.error(f"Error reading COMPOSE_PROJECT_NAME from {env_file}: {str(e)}")

    return project_name


def get_device_name_from_env(env_file: str) -> str:
    """
    Extract the DEVICE_NAME from an environment file.

    Args:
        env_file (str): Path to the .env file

    Returns:
        str: The DEVICE_NAME value, or None if not found
    """
    device_name = None
    try:
        if os.path.isfile(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    if line.startswith("DEVICE_NAME="):
                        device_name = line.strip().split("=", 1)[1]
                        logging.info(f"Found DEVICE_NAME in {env_file}: {device_name}")
                        break
    except Exception as e:
        logging.error(f"Error reading DEVICE_NAME from {env_file}: {str(e)}")

    return device_name


def start_stack(
    compose_file: str = "./docker-compose.yaml",
    env_file: str = "./.env",
    instance_name: str = "money4band",
    skip_questions: bool = False,
) -> bool:
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
        f"Starting stack for '{instance_name}' instance with compose file: {compose_file} and env file: {env_file}"
    )
    just_fix_windows_console()

    if not skip_questions and not ask_question_yn(
        f"This will launch all the apps for '{instance_name}' instance using the configured .env file and the docker-compose.yaml file (Docker must be already installed and running). Do you wish to proceed?"
    ):
        print(
            f"{Fore.BLUE}Docker stack startup for '{instance_name}' instance canceled.{Style.RESET_ALL}"
        )
        time.sleep(sleep_time)
        return False

    event = threading.Event()
    spinner_thread = threading.Thread(
        target=show_spinner, args=(f"Starting stack for '{instance_name}'...", event)
    )
    spinner_thread.start()

    use_sudo = not is_user_root() and platform.system().lower() == "linux"
    try:
        # Read COMPOSE_PROJECT_NAME from the .env file
        project_name = get_compose_project_name(env_file)
        device_name = get_device_name_from_env(env_file)

        if device_name:
            logging.info(
                f"Using device name '{device_name}' for instance '{instance_name}'"
            )

        # Build the docker compose command, adding -p flag if project_name was found
        command = ["docker", "compose"]

        if project_name:
            command.extend(["-p", project_name])
            logging.info(
                f"Using project name '{project_name}' for instance '{instance_name}'"
            )
        else:
            logging.warning(
                f"COMPOSE_PROJECT_NAME not found in {env_file}, relying on Docker Compose defaults"
            )

        command.extend(
            ["-f", compose_file, "--env-file", env_file, "up", "-d", "--remove-orphans"]
        )

        result = run_docker_command(command, use_sudo=use_sudo)
        if result == 0:
            print(
                f"{Fore.GREEN}All Apps for '{instance_name}' instance started.{Style.RESET_ALL}"
            )
            logging.info(f"Stack for '{instance_name}' started successfully.")
        else:
            print(
                f"{Fore.RED}Error starting Docker stack for '{instance_name}' instance. Please check that Docker is running and that the configuration is complete, then try again.{Style.RESET_ALL}"
            )
            logging.error(
                f"Stack for '{instance_name}' failed to start with exit code {result}."
            )
            time.sleep(sleep_time)
        return result == 0
    except Exception as e:
        print(
            f"{Fore.RED}An unexpected error occurred while starting the stack for '{instance_name}' instance.{Style.RESET_ALL}"
        )
        logging.error(f"Unexpected error: {str(e)}")
        time.sleep(sleep_time)
    finally:
        event.set()
        spinner_thread.join()
    return False


def start_all_stacks(
    main_compose_file: str = "./docker-compose.yaml",
    main_env_file: str = "./.env",
    main_instance_name: str = "money4band",
    instances_dir: str = "m4b_proxy_instances",
    skip_questions: bool = False,
    force_clean: bool = False,
) -> None:
    """
    Start the main stack and all multi-proxy instances.

    Args:
        main_compose_file (str): The path to the main Docker Compose file.
        main_env_file (str): The path to the main environment file.
        main_instance_name (str): The name of the main instance.
        instances_dir (str): The directory containing the proxy instances.
        skip_questions (bool): Whether to skip the confirmation question.
        force_clean (bool): Whether to stop all containers before starting.
    """
    if not skip_questions and not ask_question_yn(
        f"This will launch all the apps for '{main_instance_name}' and any multi-proxy instances using the configured .env files and docker-compose.yaml files. Docker must be already installed and running. Do you wish to proceed?"
    ):
        print(f"{Fore.BLUE}Docker stack startup canceled.{Style.RESET_ALL}")
        time.sleep(sleep_time)
        return

    if platform.system().lower() == "linux" and not is_user_in_docker_group():
        create_docker_group_if_needed()

    # If force_clean is True, stop all containers first
    if force_clean:
        if not skip_questions and not ask_question_yn(
            "This will stop ALL running Docker containers. Continue?"
        ):
            print(f"{Fore.BLUE}Docker stack startup canceled.{Style.RESET_ALL}")
            return

        print(f"{Fore.YELLOW}Stopping all Docker containers...{Style.RESET_ALL}")
        subprocess.run(["docker", "stop", "$(docker ps -q)"], shell=True)
        print(f"{Fore.GREEN}All containers stopped.{Style.RESET_ALL}")

    # Check for any running containers that might conflict
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True
    )
    running_containers = result.stdout.splitlines()

    # Print warning if any containers already exist
    if running_containers:
        print(
            f"{Fore.YELLOW}Warning: Found {len(running_containers)} running containers. Check for conflicts:{Style.RESET_ALL}"
        )
        for container in running_containers:
            print(f" - {container}")

        if not skip_questions and not ask_question_yn(
            "Continue despite existing containers?"
        ):
            print(f"{Fore.BLUE}Docker stack startup canceled.{Style.RESET_ALL}")
            return

    try:
        # First verify each instance has unique container names
        container_names = {}
        device_names = set()

        # Check main instance container names
        main_device_name = None
        with open(main_env_file, "r") as f:
            for line in f:
                if line.startswith("DEVICE_NAME="):
                    main_device_name = line.strip().split("=", 1)[1]
                    device_names.add(main_device_name)
                    break

        if main_device_name:
            print(
                f"{Fore.CYAN}Main instance device name: {main_device_name}{Style.RESET_ALL}"
            )
            main_containers = get_container_names_from_env(main_env_file)
            for container in main_containers:
                container_names[container] = "main instance"

        # Check proxy instances container names and device names
        has_conflicts = False
        if os.path.isdir(instances_dir):
            for instance in os.listdir(instances_dir):
                instance_dir = os.path.join(instances_dir, instance)
                env_file = os.path.join(instance_dir, ".env")
                if os.path.isfile(env_file):
                    # Get device name from this instance
                    instance_device_name = None
                    with open(env_file, "r") as f:
                        for line in f:
                            if line.startswith("DEVICE_NAME="):
                                instance_device_name = line.strip().split("=", 1)[1]
                                break

                    if instance_device_name:
                        if instance_device_name in device_names:
                            print(
                                f"{Fore.RED}Duplicate device name detected: '{instance_device_name}' is already used by another instance!{Style.RESET_ALL}"
                            )
                            print(
                                f"{Fore.RED}This will cause container name conflicts. Please run the validator to fix this issue.{Style.RESET_ALL}"
                            )
                            has_conflicts = True
                        else:
                            device_names.add(instance_device_name)
                            print(
                                f"{Fore.GREEN}Instance {instance} device name: {instance_device_name}{Style.RESET_ALL}"
                            )

                    instance_containers = get_container_names_from_env(env_file)
                    for container in instance_containers:
                        if container in container_names:
                            print(
                                f"{Fore.RED}Container name conflict detected: '{container}' is used in both {container_names[container]} and {instance}{Style.RESET_ALL}"
                            )
                            print(
                                f"{Fore.RED}This conflict occurs because your docker-compose.yaml files explicitly name containers using DEVICE_NAME{Style.RESET_ALL}"
                            )
                            print(
                                f"{Fore.RED}For example: container_name: ${{DEVICE_NAME}}_earnapp{Style.RESET_ALL}"
                            )
                            logging.error(
                                f"Container name conflict: '{container}' in {container_names[container]} and {instance}"
                            )
                            has_conflicts = True
                        container_names[container] = instance

        if has_conflicts:
            print(
                f"{Fore.RED}Container name conflicts detected! These must be fixed before starting.{Style.RESET_ALL}"
            )
            print(
                f"{Fore.YELLOW}Please run the validator tool: python utils/validate_instances.py --fix{Style.RESET_ALL}"
            )
            if not skip_questions and not ask_question_yn(
                "Continue anyway? (Conflicts will cause failures)"
            ):
                return
            print(
                f"{Fore.YELLOW}Continuing despite container name conflicts. This may lead to unpredictable behavior.{Style.RESET_ALL}"
            )

        # Start main stack
        all_started = start_stack(
            main_compose_file, main_env_file, main_instance_name, skip_questions=True
        )

        # Wait a moment for main stack to initialize
        time.sleep(3)

        # Start proxy instances
        if all_started and os.path.isdir(instances_dir):
            for instance in os.listdir(instances_dir):
                instance_dir = os.path.join(instances_dir, instance)
                compose_file = os.path.join(instance_dir, "docker-compose.yaml")
                env_file = os.path.join(instance_dir, ".env")
                if os.path.isfile(compose_file) and os.path.isfile(env_file):
                    try:
                        print(
                            f"{Fore.YELLOW}Starting instance: {instance}{Style.RESET_ALL}"
                        )
                        instance_started = start_stack(
                            compose_file, env_file, instance, skip_questions=True
                        )
                        all_started &= instance_started
                        if not instance_started:
                            logging.error(f"Failed to start instance '{instance}'")

                        # Add small delay between instance starts to prevent race conditions
                        time.sleep(2)
                    except Exception as e:
                        all_started = False
                        logging.error(f"Error starting instance '{instance}': {str(e)}")

        if all_started:
            generate_dashboard_urls(None, None, main_env_file)
            print(
                f"{Fore.YELLOW}Use the previously generated apps nodes URLs to add your device in any apps dashboard that require node claiming/registration (e.g., Earnapp, ProxyRack, etc.){Style.RESET_ALL}"
            )
            logging.info("All stacks started.")
    finally:
        time.sleep(sleep_time)


def get_container_names_from_env(env_file):
    """
    Extract the potential container names from an env file by reading the DEVICE_NAME
    and generating the standard container name patterns used in the compose files.

    Args:
        env_file (str): Path to the .env file

    Returns:
        list: List of predicted container names
    """
    container_names = []
    try:
        with open(env_file, "r") as f:
            env_content = f.read()

        # Find the DEVICE_NAME value
        match = re.search(r"DEVICE_NAME=([^\s#]+)", env_content)
        if match:
            device_name = match.group(1)
            # Common app names used in container names
            app_names = [
                "earnapp",
                "iproyalpawns",
                "packetstream",
                "traffmonetizer",
                "repocket",
                "earnfm",
                "proxyrack",
                "bitping",
                "packetshare",
                "grass",
                "gradient",
                "dawn",
                "teneo",
                "mystnode",
                "peer2profit",
                "watchtower",
                "m4bwebdashboard",
                "tun2socks",
            ]

            # Generate container names based on pattern
            for app in app_names:
                container_names.append(f"{device_name}_{app}")

            logging.info(
                f"Extracted potential container names for {env_file}: {len(container_names)} names"
            )
        else:
            logging.warning(f"Could not find DEVICE_NAME in {env_file}")
    except Exception as e:
        logging.error(f"Error extracting container names from {env_file}: {str(e)}")

    return container_names


def validate_env_files(main_env_file: str, instances_dir: str) -> bool:
    """
    Validate .env files to ensure DEVICE_NAME values are unique.

    Args:
        main_env_file (str): Path to the main .env file
        instances_dir (str): Directory containing proxy instances

    Returns:
        bool: True if all DEVICE_NAME values are unique, False otherwise
    """
    device_names = {}

    # Check main .env file
    main_device_name = get_device_name_from_env(main_env_file)
    if main_device_name:
        device_names[main_device_name] = "main"

    # Check instance .env files
    if os.path.isdir(instances_dir):
        for instance in os.listdir(instances_dir):
            instance_dir = os.path.join(instances_dir, instance)
            env_file = os.path.join(instance_dir, ".env")
            if os.path.isfile(env_file):
                device_name = get_device_name_from_env(env_file)
                if device_name:
                    if device_name in device_names:
                        print(
                            f"{Fore.RED}Duplicate DEVICE_NAME '{device_name}' found in {instance} and {device_names[device_name]}{Style.RESET_ALL}"
                        )
                        return False
                    device_names[device_name] = instance

    return True


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    try:
        m4b_config = loader.load_json_config(m4b_config_path)
        user_config = loader.load_json_config(user_config_path)
        base_instance_name = m4b_config.get("project", {}).get(
            "compose_project_name", "money4band"
        )

        start_all_stacks(main_instance_name=base_instance_name)
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        print(f"{Fore.RED}File not found: {str(e)}{Style.RESET_ALL}")
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        print(f"{Fore.RED}Error decoding JSON: {str(e)}{Style.RESET_ALL}")
    except Exception as e:
        logging.error(f"An unexpected error occurred in main function: {str(e)}")
        print(f"{Fore.RED}An unexpected error occurred: {str(e)}{Style.RESET_ALL}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the Docker Compose stack.")
    parser.add_argument(
        "--app-config", type=str, required=True, help="Path to app_config JSON file"
    )
    parser.add_argument(
        "--m4b-config", type=str, required=True, help="Path to m4b_config JSON file"
    )
    parser.add_argument(
        "--user-config", type=str, required=True, help="Path to user_config JSON file"
    )
    parser.add_argument("--log-dir", default="./logs", help="Set the logging directory")
    parser.add_argument(
        "--log-file", default="fn_startStack.log", help="Set the logging file name"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    parser.add_argument(
        "--skip-questions", action="store_true", help="Skip confirmation questions"
    )
    parser.add_argument(
        "--force-clean", action="store_true", help="Stop all containers before starting"
    )
    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.log_dir, args.log_file),
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_level,
    )

    logging.info("Starting fn_startStack script...")

    try:
        main(
            app_config_path=args.app_config,
            m4b_config_path=args.m4b_config,
            user_config_path=args.user_config,
        )
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
