from __future__ import annotations

import json
import logging
import os
import platform
import threading

from colorama import Fore, Style, just_fix_windows_console

from money4band.core import loader
from money4band.docker.helper import (
    check_required_files,
    create_docker_group_if_needed,
    get_compose_project_name,
    is_user_in_docker_group,
    is_user_root,
    run_docker_command,
    show_spinner,
)
from money4band.ui.cls import cls
from money4band.ui.prompt import ask_question_yn

logger = logging.getLogger(__name__)

from money4band.notifier import fire_event as _notify_event


def stop_stack(
    compose_file: str | list[str] = "./docker-compose.yaml",
    instance_name: str = "money4band",
    skip_questions: bool = False,
) -> bool:
    """
    Stop the Docker Compose stack using the provided compose file(s).

    Args:
        compose_file (str | list[str]): Path(s) to the Docker Compose file(s).
        instance_name (str): The name of the instance.
        skip_questions (bool): Whether to skip the confirmation question.

    Returns:
        bool: True if the stack stopped successfully, False otherwise.
    """
    compose_files = (
        [compose_file] if isinstance(compose_file, str) else list(compose_file)
    )
    logger.info(
        f"Stopping stack for '{instance_name}' instance with compose file(s): {compose_files}"
    )
    just_fix_windows_console()

    if not skip_questions and not ask_question_yn(
        f"This will stop all the apps for '{instance_name}' instance and delete the docker stack previously created using the configured docker-compose.yaml file. Do you wish to proceed?"
    ):
        print(
            f"{Fore.BLUE}Docker stack removal for '{instance_name}' instance canceled.{Style.RESET_ALL}"
        )
        input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
        return False

    event = threading.Event()
    spinner_thread = threading.Thread(
        target=show_spinner, args=(f"Stopping stack for '{instance_name}'...", event)
    )
    spinner_thread.start()

    use_sudo = not is_user_root() and platform.system().lower() == "linux"
    try:
        # Get the env file path based on the compose file directory
        compose_dir = os.path.dirname(compose_files[0])
        if compose_dir == "":
            compose_dir = "."
        env_file = os.path.join(compose_dir, ".env")

        # Read COMPOSE_PROJECT_NAME from the .env file
        project_name = get_compose_project_name(env_file)

        # Build the docker compose command, adding -p flag if project_name was found
        command = ["docker", "compose"]

        if project_name:
            command.extend(["-p", project_name])
            logger.info(
                f"Using project name '{project_name}' for stopping instance '{instance_name}'"
            )
        else:
            logger.warning(
                f"COMPOSE_PROJECT_NAME not found in {env_file}, relying on Docker Compose defaults"
            )

        for cf in compose_files:
            command.extend(["-f", cf])

        # Activate every known profile (infra + app tiers) so ALL profiled
        # services are part of the model for `down` - otherwise tier-gated
        # app containers survive the shutdown as orphans.  Docker Compose
        # ignores profile flags that match no service.
        from money4band.apps.schema import _VALID_PROFILES

        for profile in ("monitoring", "proxy", *sorted(_VALID_PROFILES)):
            command.extend(["--profile", profile])

        command.extend(["down"])

        result = run_docker_command(command, use_sudo=use_sudo)
        if result == 0:
            print(
                f"{Fore.GREEN}All Apps for '{instance_name}' instance stopped and stack deleted.{Style.RESET_ALL}"
            )
            logger.info(f"Stack for '{instance_name}' stopped successfully.")
            _notify_event(
                "stack_stop", f"Stack '{instance_name}' stopped successfully."
            )
        else:
            print(
                f"{Fore.RED}Error stopping and deleting Docker stack for '{instance_name}' instance. Please check the configuration and try again.{Style.RESET_ALL}"
            )
            logger.error(
                f"Stack for '{instance_name}' failed to stop with exit code {result}."
            )
            _notify_event(
                "stack_error",
                f"Stack '{instance_name}' failed to stop (exit {result}).",
            )
        return result == 0
    except Exception as e:
        print(
            f"{Fore.RED}An unexpected error occurred while stopping the stack for '{instance_name}' instance.{Style.RESET_ALL}"
        )
        logger.error(f"Unexpected error: {str(e)}")
        _notify_event("stack_error", f"Stack '{instance_name}' error: {e}")
    finally:
        event.set()
        spinner_thread.join()
    return False


def stop_all_stacks(
    main_compose_file: str | list[str] = "./docker-compose.yaml",
    main_instance_name: str = "money4band",
    instances_dir: str = "m4b_proxy_instances",
    skip_questions: bool = False,
) -> bool:
    """
    Stop the main stack and all multi-proxy instances.

    Args:
        main_compose_file (str | list[str]): Path(s) to the main Docker Compose file(s).
        main_instance_name (str): The name of the main instance.
        instances_dir (str): The directory containing the proxy instances.
        skip_questions (bool): Whether to skip the confirmation question.

    Returns:
        True when the stacks were stopped (or the user declined), False
        when the main stack failed to stop.
    """
    from money4band.ui.prompt import pause

    if not skip_questions and not ask_question_yn(
        f"This will stop all the apps for '{main_instance_name}' and any multi-proxy instances and delete the docker stacks previously created. Do you wish to proceed?"
    ):
        print(f"{Fore.BLUE}Docker stack removal canceled.{Style.RESET_ALL}")
        pause(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
        return True

    if platform.system().lower() == "linux" and not is_user_in_docker_group():
        create_docker_group_if_needed()

    try:
        stopped = stop_stack(main_compose_file, main_instance_name, skip_questions=True)
        if os.path.isdir(instances_dir):
            print(f"{Fore.YELLOW}Stopping multi-proxy instances...{Style.RESET_ALL}")
            for instance in os.listdir(instances_dir):
                instance_dir = os.path.join(instances_dir, instance)
                from money4band.docker.compose_builder import get_compose_files

                instance_files = get_compose_files(instance_dir)
                if not instance_files:
                    compose_file = os.path.join(instance_dir, "docker-compose.yaml")
                    if os.path.isfile(compose_file):
                        instance_files = [compose_file]
                if instance_files:
                    try:
                        stop_stack(instance_files, instance, skip_questions=True)
                    except Exception as e:
                        logger.error(f"Failed to stop instance '{instance}': {str(e)}")
            print(f"{Fore.GREEN}All multi-proxy instances stopped.{Style.RESET_ALL}")
        else:
            logger.warning(
                f"Multi-proxy instances directory '{instances_dir}' does not exist."
            )
        return stopped
    finally:
        pause(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> bool:
    """Menu/CLI entry - returns False on failure so the CLI can exit 1."""
    from money4band.ui.prompt import pause

    cls()
    try:
        m4b_config = loader.load_json_config(m4b_config_path)
        loader.load_json_config(user_config_path)  # validate user config exists
        base_instance_name = m4b_config.get("project", {}).get(
            "compose_project_name", "money4band"
        )

        from money4band.docker.compose_builder import get_compose_files

        compose_files = get_compose_files(".")
        if not compose_files:
            missing = check_required_files(
                ["./docker-compose.yaml"],
                error_message="Cannot stop the stack. No compose files found.",
                hint_message="It looks like there is nothing to stop.",
            )
            if missing:
                pause(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
                return True

        return stop_all_stacks(
            main_compose_file=compose_files or "./docker-compose.yaml",
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
    return False
