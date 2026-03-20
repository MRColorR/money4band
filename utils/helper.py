import getpass
import logging
import os
import platform
import subprocess
import sys
import threading
import time
from itertools import cycle

from colorama import Fore, Style


def get_compose_project_name(env_file: str) -> str | None:
    """
    Extract the COMPOSE_PROJECT_NAME from an environment file.

    Args:
        env_file (str): Path to the .env file (or a compose file path,
                        which is automatically converted to the .env path).

    Returns:
        str | None: The COMPOSE_PROJECT_NAME value, or None if not found.
    """
    # Handle if compose file was passed instead of .env
    env_file = env_file.replace("docker-compose.yaml", ".env")

    project_name = None
    try:
        if os.path.isfile(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith("COMPOSE_PROJECT_NAME="):
                        project_name = line.strip().split("=", 1)[1]
                        logging.info(
                            "Found COMPOSE_PROJECT_NAME in %s: %s",
                            env_file,
                            project_name,
                        )
                        break
    except Exception as e:
        logging.error(
            "Error reading COMPOSE_PROJECT_NAME from %s: %s", env_file, e
        )

    return project_name


def is_user_root():
    """
    Check if the current user is the root user on Linux.
    On macOS and Windows, it always returns False since we don't manage Docker groups.
    """
    return os.geteuid() == 0 if platform.system().lower() == "linux" else False


def is_user_in_docker_group():
    """
    Check if the current user is in the Docker group on Linux.
    This function is skipped on Windows and macOS.
    """
    if platform.system().lower() != "linux":
        return True
    # use getpass.getuser() instead of os.getlogin() as it is more robust
    user = getpass.getuser()
    logging.info(f"Detected user: {user}")
    logging.info(f"Checking if user '{user}' is in the Docker group...")
    groups = subprocess.run(
        ["groups", user], check=False, capture_output=True, text=True
    )
    return "docker" in groups.stdout


def create_docker_group_if_needed():
    """
    Create the Docker group if it doesn't exist and add the current user to it on Linux.
    This function is skipped on Windows and macOS.
    """
    if platform.system().lower() != "linux":
        return

    try:
        if (
            subprocess.run(
                ["getent", "group", "docker"], check=False, capture_output=True
            ).returncode
            != 0
        ):
            logging.info(
                f"{Fore.YELLOW}Docker group does not exist. Creating it...{Style.RESET_ALL}"
            )
            subprocess.run(["sudo", "groupadd", "docker"], check=True)
            logging.info(
                f"{Fore.GREEN}Docker group created successfully.{Style.RESET_ALL}"
            )

        # use getpass.getuser() instead of os.getlogin() as it is more robust
        user = getpass.getuser()
        logging.info(f"Adding user '{user}' to Docker group...")
        subprocess.run(["sudo", "usermod", "-aG", "docker", user], check=True)
        logging.info(
            f"{Fore.GREEN}User '{user}' added to Docker group. Please log out and log back in.{Style.RESET_ALL}"
        )
    except subprocess.CalledProcessError as e:
        logging.error(
            f"{Fore.RED}Failed to add user to Docker group: {e}{Style.RESET_ALL}"
        )
        raise RuntimeError("Failed to add user to Docker group.") from e


def run_docker_command(command, use_sudo=False):
    """
    Run a Docker command, optionally using sudo, and handle errors gracefully.

    Args:
        command (list): The Docker command to run.
        use_sudo (bool): Whether to prepend 'sudo' to the command.

    Returns:
        int: The exit code of the command.
    """
    if use_sudo and platform.system().lower() == "linux":
        command.insert(0, "sudo")

    logging.info(f"Running command: {' '.join(command)}")

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logging.info(result.stdout)
        else:
            logging.error(f"Command failed with exit code {result.returncode}")
            logging.error(result.stderr)
            print(f"{Fore.RED}Error: {result.stderr.strip()}{Style.RESET_ALL}")
        return result.returncode
    except Exception as e:
        logging.error(f"{Fore.RED}Failed to run command: {e}{Style.RESET_ALL}")
        print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
        raise RuntimeError(f"Command failed: {e}")


def setup_service(
    service_name="docker.binfmt",
    service_file_path="./.resources/.files/docker.binfmt.service",
):
    """
    Set up a service on Linux systems, defaulting to setting up the Docker binfmt service.

    Args:
        service_name (str): The name of the service to set up. Default is "docker.binfmt".
        service_file_path (str): The path to the service file. Default is "./.resources/.files/docker.binfmt.service".
    """
    systemd_service_file = f"/etc/systemd/system/{service_name}.service"
    sysv_init_file = f"/etc/init.d/{service_name}"

    try:
        # Check if the service is already enabled and running
        if platform.system().lower() == "linux":
            if os.path.exists("/etc/systemd/system"):
                result = subprocess.run(
                    ["systemctl", "is-active", service_name],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.stdout.strip() == "active":
                    logging.info(
                        f"{Fore.GREEN}{service_name} is already active and running.{Style.RESET_ALL}"
                    )
                    return
            elif os.path.exists("/etc/init.d"):
                result = subprocess.run(
                    ["service", service_name, "status"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if "running" in result.stdout:
                    logging.info(
                        f"{Fore.GREEN}{service_name} is already active and running.{Style.RESET_ALL}"
                    )
                    return

        # Copy service file and enable service
        if os.path.exists("/etc/systemd/system"):
            if not os.path.exists(systemd_service_file):
                logging.info(f"Copying service file to {systemd_service_file}")
                subprocess.run(
                    ["sudo", "cp", service_file_path, systemd_service_file], check=True
                )
                subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                subprocess.run(
                    ["sudo", "systemctl", "enable", service_name], check=True
                )
            subprocess.run(["sudo", "systemctl", "start", service_name], check=False)
        elif os.path.exists("/etc/init.d"):
            if not os.path.exists(sysv_init_file):
                logging.info(f"Copying service file to {sysv_init_file}")
                subprocess.run(
                    ["sudo", "cp", service_file_path, sysv_init_file], check=True
                )
                subprocess.run(["sudo", "chmod", "+x", sysv_init_file], check=True)
                subprocess.run(
                    ["sudo", "update-rc.d", service_name, "defaults"], check=True
                )
            subprocess.run(["sudo", "service", service_name, "start"], check=False)

        logging.info(f"{Fore.GREEN}{service_name} setup and started.{Style.RESET_ALL}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to setup {service_name}: {str(e)}")
        raise RuntimeError(f"Failed to setup {service_name}: {str(e)}")


def ensure_service(
    service_name="docker.binfmt",
    service_file_path="./.resources/.files/docker.binfmt.service",
):
    """
    Ensure that a service is installed and running, defaulting to the Docker binfmt service.

    Args:
        service_name (str): The name of the service to ensure. Default is "docker.binfmt".
        service_file_path (str): The path to the service file. Default is './.resources/.files/docker.binfmt.service'.
    """
    logging.info(f"Ensuring {service_name} service is installed and running.")
    try:
        setup_service(service_name=service_name, service_file_path=service_file_path)
        logging.info(
            f"{Fore.GREEN}{service_name} setup completed successfully.{Style.RESET_ALL}"
        )
    except Exception as e:
        logging.error(f"Failed to ensure {service_name} service: {str(e)}")
        raise RuntimeError(f"Failed to ensure {service_name} service: {str(e)}")


def check_required_files(
    files: list, error_message: str = None, hint_message: str = None
) -> list:
    """
    Check if required files exist and return a list of missing files.

    Args:
        files (list): List of file paths to check.
        error_message (str): Optional custom error message to display if files are missing.
        hint_message (str): Optional hint message to help the user resolve the issue.

    Returns:
        list: List of missing file paths. Empty list if all files exist.
    """
    missing_files = [f for f in files if not os.path.isfile(f)]

    if missing_files:
        if error_message:
            print(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
        else:
            print(
                f"{Fore.RED}The following required files are missing:{Style.RESET_ALL}"
            )
        for f in missing_files:
            print(f"  - {f}")
        if hint_message:
            print(f"\n{Fore.YELLOW}{hint_message}{Style.RESET_ALL}")

    return missing_files


def show_spinner(message: str, event: threading.Event):
    """
    Display a spinner animation in the console to indicate progress.

    Args:
        message (str): The message to display alongside the spinner.
        event (threading.Event): A threading event to stop the spinner.
    """
    spinner = cycle(["|", "/", "-", "\\"])
    sys.stdout.write(f"{message} ")
    sys.stdout.flush()
    while not event.is_set():
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        time.sleep(0.1)
        sys.stdout.write("\b")  # Remove the spinner character
    sys.stdout.write("\b")  # Clear the spinner when stopping
    sys.stdout.write("Done\n")  # Print a completion message
    sys.stdout.flush()


def get_active_profiles(user_config_path_or_dict) -> list[str]:
    """Return the list of Docker Compose profile names to activate.

    Reads the user config to decide which infrastructure profiles are needed:
      - ``monitoring`` when watchtower is enabled
      - ``dashboard``  when the web dashboard is enabled
      - ``proxy``      when proxies are enabled
    """
    from utils.loader import load_json_config

    cfg = load_json_config(user_config_path_or_dict)
    profiles: list[str] = []
    if cfg.get("watchtower", {}).get("enabled", True):
        profiles.append("monitoring")
    if cfg.get("m4b_dashboard", {}).get("enabled", False):
        profiles.append("dashboard")
    if cfg.get("proxies", {}).get("enabled", False):
        profiles.append("proxy")
    return profiles
