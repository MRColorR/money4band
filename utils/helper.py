# helper.py
import os
import platform
import subprocess
import logging
from colorama import Fore, Style

def is_user_root():
    """
    Check if the current user is the root user on Linux.
    On macOS and Windows, it always returns False since we don't manage Docker groups.
    """
    return os.geteuid() == 0 if platform.system().lower() == 'linux' else False

def is_user_in_docker_group():
    """
    Check if the current user is in the Docker group on Linux.
    This function is skipped on Windows and macOS.
    """
    if platform.system().lower() != 'linux':
        return True

    user = os.getlogin()
    groups = subprocess.run(["groups", user], capture_output=True, text=True)
    return "docker" in groups.stdout

def create_docker_group_if_needed():
    """
    Create the Docker group if it doesn't exist and add the current user to it on Linux.
    This function is skipped on Windows and macOS.
    """
    if platform.system().lower() != 'linux':
        return

    try:
        if subprocess.run(["getent", "group", "docker"], capture_output=True).returncode != 0:
            logging.info(f"{Fore.YELLOW}Docker group does not exist. Creating it...{Style.RESET_ALL}")
            subprocess.run(["sudo", "groupadd", "docker"], check=True)
            logging.info(f"{Fore.GREEN}Docker group created successfully.{Style.RESET_ALL}")

        user = os.getlogin()
        logging.info(f"Adding user '{user}' to Docker group...")
        subprocess.run(["sudo", "usermod", "-aG", "docker", user], check=True)
        logging.info(f"{Fore.GREEN}User '{user}' added to Docker group. Please log out and log back in.{Style.RESET_ALL}")
    except subprocess.CalledProcessError as e:
        logging.error(f"{Fore.RED}Failed to add user to Docker group: {e}{Style.RESET_ALL}")
        raise RuntimeError("Failed to add user to Docker group.") from e

def run_docker_command(command, use_sudo=False):
    """
    Run a Docker command, optionally using sudo.

    Args:
        command (list): The Docker command to run.
        use_sudo (bool): Whether to prepend 'sudo' to the command.

    Returns:
        subprocess.CompletedProcess: The result of the subprocess run.
    """
    if use_sudo and platform.system().lower() == 'linux':
        command.insert(0, "sudo")
    return subprocess.run(command, check=True, capture_output=True, text=True)
