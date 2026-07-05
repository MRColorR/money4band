from __future__ import annotations

import json
import logging
import os
import platform
import re
import subprocess
import threading
import time

from colorama import Fore, Style, just_fix_windows_console

from money4band.core import loader
from money4band.docker.env_builder import secure_delete_env
from money4band.docker.generator import generate_container_url_list
from money4band.docker.helper import (
    create_docker_group_if_needed,
    get_compose_project_name,
    is_user_in_docker_group,
    is_user_root,
    run_docker_command,
    show_spinner,
)
from money4band.notifier import fire_event as _notify_event
from money4band.ui.cls import cls
from money4band.ui.prompt import ask_question_yn

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(os.path.abspath(__file__))

parent_dir = os.path.dirname(script_dir)

m4b_config_path = os.path.join(parent_dir, "config", "m4b-config.json")


def get_device_name_from_env(env_file: str) -> str | None:
    """
    Extract the DEVICE_NAME from an environment file.

    Falls back to ``.env.meta`` when the full ``.env`` has been
    securely deleted after compose-up.

    Args:
        env_file (str): Path to the .env file

    Returns:
        str: The DEVICE_NAME value, or None if not found
    """
    candidates = [env_file]
    meta_file = os.path.join(os.path.dirname(os.path.abspath(env_file)), ".env.meta")
    candidates.append(meta_file)

    for candidate in candidates:
        try:
            if os.path.isfile(candidate):
                with open(candidate) as f:
                    for line in f:
                        if line.startswith("DEVICE_NAME="):
                            device_name = line.strip().split("=", 1)[1]
                            logger.info(
                                "Found DEVICE_NAME in %s: %s", candidate, device_name
                            )
                            return device_name
        except Exception as e:
            logger.error("Error reading DEVICE_NAME from %s: %s", candidate, e)

    return None


def start_stack(
    compose_file: str | list[str] = "./docker-compose.yaml",
    env_file: str = "./.env",
    instance_name: str = "money4band",
    skip_questions: bool = False,
    profiles: tuple[str, ...] = (),
) -> bool:
    """
    Start the Docker Compose stack using the provided compose and env files.

    Args:
        compose_file (str | list[str]): Path(s) to Docker Compose file(s).
        env_file (str): The path to the environment file.
        instance_name (str): The name of the instance.
        skip_questions (bool): Whether to skip the confirmation question.
        profiles: Docker Compose profile names to activate.

    Returns:
        bool: True if the stack started successfully, False otherwise.
    """
    compose_files = (
        [compose_file] if isinstance(compose_file, str) else list(compose_file)
    )
    logger.info(
        f"Starting stack for '{instance_name}' instance with compose file(s): {compose_files} and env file: {env_file}"
    )
    just_fix_windows_console()

    if not skip_questions and not ask_question_yn(
        f"This will launch all the apps for '{instance_name}' instance using the configured .env file and the docker-compose.yaml file (Docker must be already installed and running). Do you wish to proceed?"
    ):
        print(
            f"{Fore.BLUE}Docker stack startup for '{instance_name}' instance canceled.{Style.RESET_ALL}"
        )
        input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
        return False

    event = threading.Event()
    spinner_thread = threading.Thread(
        target=show_spinner, args=(f"Starting stack for '{instance_name}'...", event)
    )
    spinner_thread.start()

    use_sudo = not is_user_root() and platform.system().lower() == "linux"

    # Pre-check: .env must exist for docker compose --env-file.
    if not os.path.isfile(env_file):
        event.set()
        spinner_thread.join()
        logger.error(
            "Environment file %s not found. Run 'm4b generate' first.", env_file
        )
        print(
            f"{Fore.RED}Environment file not found: {env_file}\n"
            f"Run 'm4b generate' to regenerate it.{Style.RESET_ALL}"
        )
        input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
        return False

    try:
        # Read COMPOSE_PROJECT_NAME from the .env file
        project_name = get_compose_project_name(env_file)
        device_name = get_device_name_from_env(env_file)

        if device_name:
            logger.info(
                f"Using device name '{device_name}' for instance '{instance_name}'"
            )

        # Build the docker compose command, adding -p flag if project_name was found
        command = ["docker", "compose"]

        if project_name:
            command.extend(["-p", project_name])
            logger.info(
                f"Using project name '{project_name}' for instance '{instance_name}'"
            )
        else:
            logger.warning(
                f"COMPOSE_PROJECT_NAME not found in {env_file}, relying on Docker Compose defaults"
            )

        for cf in compose_files:
            command.extend(["-f", cf])
        command.extend(["--env-file", env_file])

        for profile in profiles:
            command.extend(["--profile", profile])

        command.extend(["up", "-d", "--remove-orphans"])

        result = run_docker_command(command, use_sudo=use_sudo)
        if result == 0:
            # Securely wipe the .env - credentials should not persist on disk
            # after compose-up bakes them into running containers.
            secure_delete_env(env_file)
            print(
                f"{Fore.GREEN}All Apps for '{instance_name}' instance started.{Style.RESET_ALL}"
            )
            logger.info(f"Stack for '{instance_name}' started successfully.")
            _notify_event(
                "stack_start", f"Stack '{instance_name}' started successfully."
            )
        else:
            print(
                f"{Fore.RED}Error starting Docker stack for '{instance_name}' instance. Please check that Docker is running and that the configuration is complete, then try again.{Style.RESET_ALL}"
            )
            logger.error(
                f"Stack for '{instance_name}' failed to start with exit code {result}."
            )
            _notify_event(
                "stack_error",
                f"Stack '{instance_name}' failed to start (exit {result}).",
            )
            input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
        return result == 0
    except Exception as e:
        print(
            f"{Fore.RED}An unexpected error occurred while starting the stack for '{instance_name}' instance.{Style.RESET_ALL}"
        )
        logger.error(f"Unexpected error: {str(e)}")
        _notify_event("stack_error", f"Stack '{instance_name}' error: {e}")
        input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
    finally:
        event.set()
        spinner_thread.join()
    return False


def start_all_stacks(
    main_compose_file: str | list[str] = "./docker-compose.yaml",
    main_env_file: str = "./.env",
    main_instance_name: str = "money4band",
    instances_dir: str = "m4b_proxy_instances",
    skip_questions: bool = False,
    force_clean: bool = False,
    profiles: tuple[str, ...] = (),
) -> None:
    """
    Start the main stack and all multi-proxy instances.

    Args:
        main_compose_file (str | list[str]): Path(s) to the main Docker Compose file(s).
        main_env_file (str): The path to the main environment file.
        main_instance_name (str): The name of the main instance.
        instances_dir (str): The directory containing the proxy instances.
        skip_questions (bool): Whether to skip the confirmation question.
        force_clean (bool): Whether to stop all containers before starting.
        profiles: Docker Compose profiles to activate for the main stack.
    """
    if not skip_questions and not ask_question_yn(
        f"This will launch all the apps for '{main_instance_name}' and any multi-proxy instances using the configured .env files and docker-compose.yaml files. Docker must be already installed and running. Do you wish to proceed?"
    ):
        print(f"{Fore.BLUE}Docker stack startup canceled.{Style.RESET_ALL}")
        input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
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
        # Two-step: get container IDs first, then stop them (avoids shell=True)
        ps_result = subprocess.run(
            ["docker", "ps", "-q"],
            check=False,
            capture_output=True,
            text=True,
        )
        container_ids = ps_result.stdout.split()
        if container_ids:
            subprocess.run(["docker", "stop", *container_ids], check=False)
        print(f"{Fore.GREEN}All containers stopped.{Style.RESET_ALL}")

    # Check for any running containers that might conflict
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        check=False,
        capture_output=True,
        text=True,
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
        main_device_name = get_device_name_from_env(main_env_file)
        if main_device_name:
            device_names.add(main_device_name)

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
                if os.path.isfile(env_file) or os.path.isfile(
                    os.path.join(instance_dir, ".env.meta")
                ):
                    # Get device name from this instance (falls back to .env.meta)
                    instance_device_name = get_device_name_from_env(env_file)

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
                            logger.error(
                                f"Container name conflict: '{container}' in {container_names[container]} and {instance}"
                            )
                            has_conflicts = True
                        container_names[container] = instance

        if has_conflicts:
            print(
                f"{Fore.RED}Container name conflicts detected! These must be fixed before starting.{Style.RESET_ALL}"
            )
            print(
                f"{Fore.YELLOW}Please run the validator tool: python -m money4band.validate_instances --fix{Style.RESET_ALL}"
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
            main_compose_file,
            main_env_file,
            main_instance_name,
            skip_questions=True,
            profiles=profiles,
        )

        # Wait a moment for main stack to initialize
        time.sleep(3)

        # Start proxy instances
        if all_started and os.path.isdir(instances_dir):
            for instance in os.listdir(instances_dir):
                instance_dir = os.path.join(instances_dir, instance)
                from money4band.docker.compose_builder import get_compose_files

                instance_files = get_compose_files(instance_dir)
                if not instance_files:
                    legacy = os.path.join(instance_dir, "docker-compose.yaml")
                    if os.path.isfile(legacy):
                        instance_files = [legacy]
                env_file = os.path.join(instance_dir, ".env")
                if instance_files and os.path.isfile(env_file):
                    try:
                        print(
                            f"{Fore.YELLOW}Starting instance: {instance}{Style.RESET_ALL}"
                        )
                        # Proxy instances always need the proxy profile
                        proxy_profiles = tuple(dict.fromkeys((*profiles, "proxy")))
                        instance_started = start_stack(
                            instance_files,
                            env_file,
                            instance,
                            skip_questions=True,
                            profiles=proxy_profiles,
                        )
                        all_started &= instance_started
                        if not instance_started:
                            logger.error(f"Failed to start instance '{instance}'")

                        # Add small delay between instance starts to prevent race conditions
                        time.sleep(2)
                    except Exception as e:
                        all_started = False
                        logger.error(f"Error starting instance '{instance}': {str(e)}")

        if all_started:
            generate_container_url_list(None, None, main_env_file)
            print(
                f"{Fore.YELLOW}Use the previously generated apps nodes URLs to add your device in any apps dashboard that require node claiming/registration (e.g., Earnapp, ProxyRack, etc.){Style.RESET_ALL}"
            )
            logger.info("All stacks started.")
    finally:
        input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")


def get_container_names_from_env(env_file: str) -> list[str]:
    """
    Extract the potential container names from an env file by reading the DEVICE_NAME
    and generating the standard container name patterns.

    Derives app names dynamically from the generated docker-compose.yaml alongside
    the env file, falling back to infrastructure service names only.

    Args:
        env_file (str): Path to the .env file

    Returns:
        list: List of predicted container names
    """
    container_names = []
    try:
        with open(env_file) as f:
            env_content = f.read()

        # Find the DEVICE_NAME value
        match = re.search(r"DEVICE_NAME=([^\s#]+)", env_content)
        if match:
            device_name = match.group(1)

            # Derive app names from the generated compose file(s) (always up-to-date)
            compose_dir = os.path.dirname(env_file) or "."
            from money4band.docker.compose_builder import get_compose_files

            compose_files = get_compose_files(compose_dir)
            if not compose_files:
                compose_files = [os.path.join(compose_dir, "docker-compose.yaml")]
            app_names = _extract_app_names_from_compose(compose_files)

            # Generate container names based on pattern
            for app in app_names:
                container_names.append(f"{device_name}_{app}")

            logger.info(
                f"Extracted potential container names for {env_file}: {len(container_names)} names"
            )
        else:
            logger.warning(f"Could not find DEVICE_NAME in {env_file}")
    except Exception as e:
        logger.error(f"Error extracting container names from {env_file}: {str(e)}")

    return container_names


def _extract_app_names_from_compose(compose_file: str | list[str]) -> list[str]:
    """
    Read the generated docker-compose file(s) and extract service names.

    Falls back to infrastructure-only names if no compose file exists.
    """
    infra_fallback = ["watchtower", "tun2socks"]
    compose_files = (
        [compose_file] if isinstance(compose_file, str) else list(compose_file)
    )
    all_services: list[str] = []
    try:
        import yaml

        for cf in compose_files:
            if not os.path.isfile(cf):
                continue
            with open(cf) as f:
                doc = yaml.safe_load(f)
            if doc and "services" in doc:
                all_services.extend(doc["services"].keys())
        return all_services if all_services else infra_fallback
    except Exception:
        logger.warning(
            "Could not parse compose files for container names; "
            "using infrastructure fallback",
            exc_info=True,
        )
        return infra_fallback


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
    cls()
    try:
        m4b_config = loader.load_json_config(m4b_config_path)
        user_config = loader.load_json_config(user_config_path)
        base_instance_name = m4b_config.get("project", {}).get(
            "compose_project_name", "money4band"
        )

        # Check if required files exist before proceeding
        from money4band.docker.compose_builder import get_compose_files

        compose_files = get_compose_files(".")
        if not compose_files or not os.path.isfile("./.env"):
            print("Cannot start the stack. Required compose/env files are missing.")
            print(
                "Please run the setup wizard first to generate the configuration files."
            )
            input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
            return

        from money4band.docker.helper import get_active_profiles

        profiles = tuple(get_active_profiles(user_config, app_config_path))
        start_all_stacks(
            main_compose_file=compose_files,
            profiles=profiles,
            main_instance_name=base_instance_name,
        )
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        print(f"{Fore.RED}File not found: {str(e)}{Style.RESET_ALL}")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {str(e)}")
        print(f"{Fore.RED}Error decoding JSON: {str(e)}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in main function: {str(e)}")
        print(f"{Fore.RED}An unexpected error occurred: {str(e)}{Style.RESET_ALL}")
