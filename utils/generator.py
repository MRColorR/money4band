from __future__ import annotations

"""Generator facade -- device naming, UUID utilities, dashboard URL generation,
and CLI entry point for file regeneration.

Heavy-lifting functions (compose assembly, env generation) have been extracted to
`compose_builder` and `env_builder`.  This module re-exports them so that
existing `from utils.generator import ...` statements keep working.
"""

import logging
import os
import re
import secrets
import subprocess
import sys
import threading
from utils.helper import show_spinner
from utils.loader import load_json_config

# -- Re-exports for backward compatibility ------------------------------------
from utils.compose_builder import (  # noqa: F401
    assemble_docker_compose,
    substitute_port_placeholders,
)
from utils.env_builder import generate_env_file  # noqa: F401

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


def validate_uuid(uuid: str, length: int) -> bool:
    """
    Validate a UUID against the specified length.

    Args:
        uuid (str): The UUID to validate.
        length (int): The expected length of the UUID.

    Returns:
        bool: True if the UUID is valid, False otherwise.
    """
    if (
        not isinstance(uuid, str)
        or len(uuid) != length
        or not re.match(f"[0-9a-f]{{{length}}}", uuid)
    ):
        return False
    return True


def generate_uuid(length: int) -> str:
    """
    Generate a UUID of the specified length.

    Args:
        length (int): The length of the UUID to generate.

    Returns:
        str: The generated UUID.
    """
    return str(os.urandom(length // 2 + 1).hex())[:length]


def generate_dashboard_urls(
    compose_project_name: str,
    device_name: str,
    env_file: str = str(os.path.join(os.getcwd(), ".env")),
) -> None:
    """
    Generate dashboard URLs based on the provided compose project name and device name.
    If the parameters are not provided, it tries to read them from the .env file.
    The generated dashboard URLs are written to a file named "dashboards_URLs_<compose_project_name>-<device_name>.txt".

    Args:
        compose_project_name (str): The name of the compose project.
        device_name (str): The name of the device.
        env_file (str, optional): The path to the environment file. Defaults to ".env".

    Raises:
        Exception: If an error occurs during the URL generation process.
    """
    event = threading.Event()
    spinner_thread = threading.Thread(
        target=show_spinner, args=("Generating dashboard URLs...", event)
    )
    spinner_thread.start()

    try:
        if not compose_project_name or not device_name:
            if os.path.isfile(env_file):
                logger.info(
                    "Reading COMPOSE_PROJECT_NAME and DEVICE_NAME from .env file..."
                )
                with open(env_file) as f:
                    for line in f:
                        if "COMPOSE_PROJECT_NAME" in line:
                            compose_project_name = line.split("=")[1].strip()
                        if "DEVICE_NAME" in line:
                            device_name = line.split("=")[1].strip()
            else:
                logger.error("Error: Parameters not provided and .env file not found.")
                return

        if not compose_project_name or not device_name:
            logger.error(
                "Error: COMPOSE_PROJECT_NAME and DEVICE_NAME must be provided."
            )
            return

        dashboard_file = f"dashboards_URLs_{compose_project_name}-{device_name}.txt"
        with open(dashboard_file, "w") as f:
            f.write(f"------ Dashboards {compose_project_name}-{device_name} ------\n")

        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Ports}} {{.Names}}"],
            check=False,
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            container_info = line.split()[-1]
            port_mapping = re.search(r"0.0.0.0:(\d+)->", line)
            if port_mapping:
                with open(dashboard_file, "a") as f:
                    f.write(
                        f"If enabled you can visit the {container_info} web dashboard on http://localhost:{port_mapping.group(1)}\n"
                    )

        logger.info(f"Dashboard URLs have been written to {dashboard_file}")
    finally:
        event.set()
        spinner_thread.join()


def generate_device_name(
    adjectives: list[str],
    animals: list[str],
    device_name: str = "",
    use_uuid_suffix: bool = False,
) -> str:
    """
    Generate a device name from given word lists. If a device name is provided, it will be used.
    Optionally, a random UUID suffix can be added.

    Args:
        adjectives (list): List of adjectives.
        animals (list): List of animals.
        device_name (str, optional): Optional device name to use. Defaults to "".
        use_uuid_suffix (bool, optional): Flag to determine whether to add a UUID suffix. Defaults to False.

    Returns:
        str: The generated or provided device name.
    """
    if not device_name:
        adjective = secrets.choice(adjectives)
        animal = secrets.choice(animals)
        device_name = f"{adjective}_{animal}"

    if use_uuid_suffix:
        uuid_suffix = generate_uuid(4)
        device_name = f"{device_name}_{uuid_suffix}"

    return device_name


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Regenerate docker-compose.yaml and .env files from existing configuration.

    This is the menu entry point for regenerating files without going through
    the full setup wizard.

    Args:
        app_config_path: Path to the app configuration file.
        m4b_config_path: Path to the m4b configuration file.
        user_config_path: Path to the user configuration file.
    """
    import shutil

    from colorama import Fore, Style

    from utils.prompt_helper import ask_question_yn

    print(f"\n{Fore.CYAN}=== Regenerate Files from Configuration ==={Style.RESET_ALL}")
    print("This will regenerate docker-compose.yaml and .env files")
    print("based on your current configuration.")

    if not os.path.exists(user_config_path):
        logger.error("User config not found at %s", user_config_path)
        print(f"{Fore.RED}Error: User config not found.{Style.RESET_ALL}")
        print("Please run 'Setup Apps' first to create the initial configuration.")
        input("\nPress Enter to go back to main menu...")
        return

    try:
        m4b_config = load_json_config(m4b_config_path)
        app_config = load_json_config(app_config_path)
        user_config = load_json_config(user_config_path)
    except Exception as e:
        logger.error("Error loading config files: %s", e)
        print(f"{Fore.RED}Error loading config files: {e}{Style.RESET_ALL}")
        input("\nPress Enter to go back to main menu...")
        return

    # Show summary
    print(f"\n{Fore.BLUE}Current Configuration:{Style.RESET_ALL}")
    device = user_config.get("device_info", {}).get("device_name", "Unknown")
    proxy = user_config.get("proxies", {}).get("enabled", False)
    dash = user_config.get("m4b_dashboard", {})
    dash_on = dash.get("enabled", False)
    dash_port = dash.get("ports", [8081])[0] if dash.get("ports") else 8081

    print(f"  Device: {device}")
    print(f"  Proxy: {'Enabled' if proxy else 'Disabled'}")
    print(f"  Dashboard: {'Port ' + str(dash_port) if dash_on else 'Disabled'}")

    # Count enabled apps
    enabled = []
    apps = user_config.get("apps", {})
    if isinstance(apps, dict):
        for name, cfg in apps.items():
            if isinstance(cfg, dict) and cfg.get("enabled"):
                enabled.append(name)
    print(
        f"  Enabled Apps ({len(enabled)}): {', '.join(enabled) if enabled else 'None'}"
    )

    # Determine compose mode from config
    compose_mode = m4b_config.get("system", {}).get("compose_mode", "monolithic")
    layered = compose_mode == "layered"
    if layered:
        print(f"  Compose Mode: Layered (split by IP-policy tier)")
    else:
        print(f"  Compose Mode: Monolithic (single docker-compose.yaml)")

    # Check for multiproxy instances
    instances_dir = "m4b_proxy_instances"
    has_instances = os.path.exists(instances_dir) and os.listdir(instances_dir)
    instance_dirs = []
    if has_instances:
        instance_dirs = [
            d
            for d in os.listdir(instances_dir)
            if os.path.isdir(os.path.join(instances_dir, d))
        ]
        print(f"  Multiproxy Instances: {len(instance_dirs)}")

    # Check if containers are running
    containers_running = False
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={device}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            containers_running = True
            running_count = len(result.stdout.strip().split("\n"))
            print(
                f"\n{Fore.YELLOW}Warning: {running_count} container(s) currently running{Style.RESET_ALL}"
            )
    except Exception:
        pass  # Docker check failed, continue anyway

    print()
    if not ask_question_yn("Regenerate files with this configuration?"):
        print("Cancelled.")
        input("\nPress Enter to go back to main menu...")
        return

    # Create backup of existing files
    backup_dir = ".backup"
    os.makedirs(backup_dir, exist_ok=True)
    from utils.compose_builder import COMPOSE_LAYER_FILES

    files_to_backup = [".env"]
    # Back up either layered or monolithic compose files, whichever exist
    for layer_file in COMPOSE_LAYER_FILES.values():
        if os.path.exists(layer_file):
            files_to_backup.append(layer_file)
    if os.path.exists("docker-compose.yaml"):
        files_to_backup.append("docker-compose.yaml")
    backed_up = []

    for filename in files_to_backup:
        if os.path.exists(filename):
            backup_path = os.path.join(backup_dir, filename)
            try:
                shutil.copy2(filename, backup_path)
                backed_up.append(filename)
            except Exception as e:
                logger.warning(f"Could not backup {filename}: {e}")

    if backed_up:
        print(
            f"{Fore.BLUE}Backed up: {', '.join(backed_up)} -> {backup_dir}/{Style.RESET_ALL}"
        )

    try:
        # Regenerate main instance files
        mode_label = "layered compose files" if layered else "docker-compose.yaml"
        print(f"\n{Fore.CYAN}Regenerating {mode_label}...{Style.RESET_ALL}")
        assemble_docker_compose(
            m4b_config_path_or_dict=m4b_config,
            app_config_path_or_dict=app_config,
            user_config_path_or_dict=user_config,
            compose_output_path="./docker-compose.yaml",
            is_main_instance=True,
            layered=layered,
        )
        print(f"{Fore.GREEN}{mode_label} regenerated{Style.RESET_ALL}")

        print(f"{Fore.CYAN}Regenerating .env file...{Style.RESET_ALL}")
        generate_env_file(
            m4b_config_path_or_dict=m4b_config,
            app_config_path_or_dict=app_config,
            user_config_path_or_dict=user_config,
            env_output_path="./.env",
            is_main_instance=True,
        )
        print(f"{Fore.GREEN}.env file regenerated{Style.RESET_ALL}")

        # Handle multiproxy instances
        if has_instances and instance_dirs:
            print(
                f"\n{Fore.YELLOW}Multiproxy instances detected: {len(instance_dirs)}{Style.RESET_ALL}"
            )
            if ask_question_yn(
                "Regenerate multiproxy instance files too?", default=True
            ):
                for instance_name in instance_dirs:
                    instance_path = os.path.join(instances_dir, instance_name)
                    instance_user_config = os.path.join(
                        instance_path, "user-config.json"
                    )
                    instance_app_config = os.path.join(instance_path, "app-config.json")
                    instance_m4b_config = os.path.join(instance_path, "m4b-config.json")
                    instance_compose = os.path.join(
                        instance_path, "docker-compose.yaml"
                    )
                    instance_env = os.path.join(instance_path, ".env")

                    if not os.path.exists(instance_user_config):
                        print(
                            f"{Fore.YELLOW}  Skipping {instance_name}: no user-config.json{Style.RESET_ALL}"
                        )
                        continue

                    # Backup instance files
                    instance_backup = os.path.join(instance_path, ".backup")
                    os.makedirs(instance_backup, exist_ok=True)
                    backup_names = ["docker-compose.yaml", ".env"]
                    for lf in COMPOSE_LAYER_FILES.values():
                        backup_names.append(lf)
                    for f in backup_names:
                        src = os.path.join(instance_path, f)
                        if os.path.exists(src):
                            try:
                                shutil.copy2(src, os.path.join(instance_backup, f))
                            except Exception:
                                pass

                    try:
                        # Use main configs if instance-specific ones don't exist
                        i_app_cfg = (
                            instance_app_config
                            if os.path.exists(instance_app_config)
                            else app_config_path
                        )
                        i_m4b_cfg = (
                            instance_m4b_config
                            if os.path.exists(instance_m4b_config)
                            else m4b_config_path
                        )

                        print(
                            f"{Fore.CYAN}  Regenerating {instance_name}...{Style.RESET_ALL}"
                        )
                        assemble_docker_compose(
                            m4b_config_path_or_dict=i_m4b_cfg,
                            app_config_path_or_dict=i_app_cfg,
                            user_config_path_or_dict=instance_user_config,
                            compose_output_path=instance_compose,
                            is_main_instance=False,
                            layered=layered,
                        )
                        generate_env_file(
                            m4b_config_path_or_dict=i_m4b_cfg,
                            app_config_path_or_dict=i_app_cfg,
                            user_config_path_or_dict=instance_user_config,
                            env_output_path=instance_env,
                            is_main_instance=False,
                        )
                        print(
                            f"{Fore.GREEN}  {instance_name} regenerated{Style.RESET_ALL}"
                        )
                    except Exception as e:
                        print(
                            f"{Fore.RED}  {instance_name} failed: {e}{Style.RESET_ALL}"
                        )
                        logger.error(
                            f"Error regenerating instance {instance_name}: {e}"
                        )

        print(f"\n{Fore.GREEN}Done!{Style.RESET_ALL}")

        # Offer to restart if containers are running
        if containers_running:
            print(
                f"\n{Fore.YELLOW}Containers are running with old configuration.{Style.RESET_ALL}"
            )
            if ask_question_yn("Restart stack now to apply changes?"):
                print(f"{Fore.CYAN}Restarting stack...{Style.RESET_ALL}")
                try:
                    from utils.compose_builder import get_compose_files as _gcf

                    current_files = _gcf(".")
                    down_cmd = ["docker", "compose"]
                    up_cmd = ["docker", "compose"]
                    for cf in current_files:
                        down_cmd.extend(["-f", cf])
                        up_cmd.extend(["-f", cf])
                    down_cmd.append("down")
                    up_cmd.extend(["up", "-d"])
                    subprocess.run(down_cmd, check=True)
                    subprocess.run(up_cmd, check=True)
                    print(
                        f"{Fore.GREEN}Stack restarted successfully{Style.RESET_ALL}"
                    )
                except subprocess.CalledProcessError as e:
                    logger.error("Error restarting stack: %s", e)
                    print(f"{Fore.RED}Error restarting stack: {e}{Style.RESET_ALL}")
            else:
                print("Remember to restart your stack to apply changes.")
        else:
            print("Start your stack to use the new configuration.")

    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        logger.error(f"Error regenerating files: {e}")
        if backed_up:
            print(
                f"{Fore.YELLOW}Your previous files are backed up in {backup_dir}/{Style.RESET_ALL}"
            )

    input("\nPress Enter to go back to main menu...")
