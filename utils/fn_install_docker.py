import os
import platform
import subprocess
import logging
import argparse
import json
from typing import Dict, Any
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)

from utils.detector import detect_os, detect_architecture
from utils.downloader import download_file
from utils.loader import load_json_config
from utils.cls import cls
import time

def is_docker_installed(m4b_config: Dict[str, Any] = None) -> bool:
    # Detect OS and architecture using the detect module
    os_info = detect_os(m4b_config)
    arch_info = detect_architecture(m4b_config)
    os_type = os_info["os_type"]
    dkarch = arch_info["dkarch"]
    sleep_time = m4b_config.get("system").get("sleep_time")
    """Check if Docker is already installed."""
    try:
        subprocess.run(["docker", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        msg = f"Docker is already installed on {os_type} with {dkarch} architecture"
        logging.info(msg)
        print(msg)
        time.sleep(sleep_time)
        return True
    except subprocess.CalledProcessError:
        return False

def install_docker_linux(files_path: str):
    """Install Docker on a Linux system."""
    try:
        logging.info("Starting Docker for Linux auto installation script")
        if is_docker_installed():
            return

        installer_url = "https://get.docker.com"
        installer_path = os.path.join(files_path, "get-docker.sh")

        # Download Docker Installer
        download_file(installer_url, installer_path)

        # Install Docker
        subprocess.run(["sudo", "sh", installer_path], check=True)
        logging.info("Docker installed successfully on Linux")

        # Clean-up
        os.remove(installer_path)
    except subprocess.CalledProcessError as e:
        logging.error(f"An error occurred during Docker installation on Linux: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred during Docker installation on Linux: {str(e)}")
        raise

def install_docker_windows(files_path: str):
    """Install Docker on a Windows system."""
    try:
        logging.info("Starting Docker for Windows auto installation script")
        if is_docker_installed():
            return

        installer_url = "https://desktop.docker.com/win/stable/Docker%20Desktop%20Installer.exe"
        installer_path = os.path.join(files_path, "DockerInstaller.exe")

        # Download Docker Installer
        download_file(installer_url, installer_path)

        # Install Docker
        subprocess.run(["start", "/wait", installer_path, "install", "--accept-license", "--quiet"], shell=True, check=True)
        msg = "Docker installed successfully on Windows"
        logging.info(msg)
        print(f"{msg}\nPlease Ensure that Docker autostarts with your system by checking it in the Docker settings")
        os.remove(installer_path)  # Clean-up
        subprocess.run([os.path.join(os.getenv("ProgramFiles"), "Docker", "Docker", "Docker Desktop.exe")], shell=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"An error occurred during Docker installation on Windows: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred during Docker installation on Windows: {str(e)}")
        raise

def install_docker_macos(files_path: str, intel_cpu: bool):
    """Install Docker on a macOS system."""
    try:
        logging.info("Starting Docker for macOS auto installation script")
        if is_docker_installed():
            return

        if intel_cpu:
            installer_url = "https://desktop.docker.com/mac/main/amd64/Docker.dmg"
        else:
            installer_url = "https://desktop.docker.com/mac/main/arm64/Docker.dmg"

        installer_path = os.path.join(files_path, "Docker.dmg")

        # Download Docker Installer
        download_file(installer_url, installer_path)

        # Mount DMG and Install Docker
        subprocess.run(["hdiutil", "attach", installer_path], check=True)
        subprocess.run(["sudo", "/Volumes/Docker/Docker.app/Contents/MacOS/install", "--accept-license"], check=True)
        subprocess.run(["hdiutil", "detach", "/Volumes/Docker"], check=True)
        subprocess.run(["open", "/Applications/Docker.app"], check=True)
        msg = "Docker installed successfully on macOS"
        logging.info(msg)
        print(f"{msg}\nPlease Ensure that Docker autostarts with your system by checking it in the Docker settings")
    except subprocess.CalledProcessError as e:
        logging.error(f"An error occurred during Docker installation on macOS: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred during Docker installation on macOS: {str(e)}")
        raise

def main(app_config: dict, m4b_config: dict, user_config: dict):
    """
    Main function to install Docker based on the operating system.

    Parameters:
    app_config -- The application configuration dictionary.
    m4b_config -- The m4b configuration dictionary.
    user_config -- The user configuration dictionary.
    """
    try:
        logging.info("Docker installation function started")
        cls()

        # Detect OS and architecture using the detect module
        os_info = detect_os(m4b_config)
        arch_info = detect_architecture(m4b_config)
        
        os_type = os_info["os_type"]
        dkarch = arch_info["dkarch"]
        files_path = m4b_config.get('files_path', 'tmp')

        # Check if Docker is already installed
        if is_docker_installed(m4b_config):
            return

        yn = input("Do you wish to proceed with the Docker automatic installation? (Y/N): ").lower()
        if yn not in ['y', 'yes']:
            logging.info("Docker installation canceled by user")
            print("Docker installation canceled")
            return

        if os_type == "linux":
            install_docker_linux(files_path)
        elif os_type == "windows":
            install_docker_windows(files_path)
        elif os_type == "darwin":  # macOS
            if dkarch == "arm64":
                install_docker_macos(files_path, intel_cpu=False)
            elif dkarch == "amd64":
                install_docker_macos(files_path, intel_cpu=True)
            else:
                logging.error("Unsupported architecture for macOS")
        else:
            logging.error(f"Unsupported operating system: {os_type}")

    except Exception as e:
        logging.error(f"An error occurred during Docker installation: {str(e)}")
        raise

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser(description='Run the module standalone.')
    parser.add_argument('--app-config', type=str, required=False, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=True, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config', type=str, required=False, help='Path to user_config JSON file')
    parser.add_argument('--log-dir', default=os.path.join(script_dir, 'logs'), help='Set the logging directory')
    parser.add_argument('--log-file', default=f"{script_name}.log", help='Set the logging file name')
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

    logging.info(f"Starting {script_name} script...")

    try:
        # Load the app_config JSON file
        app_config = {}
        if args.app_config:
            logging.debug("Loading app_config JSON file")
            with open(args.app_config, 'r') as f:
                app_config = json.load(f)
            logging.info("app_config JSON file loaded successfully")

        # Load the m4b_config JSON file if provided
        m4b_config = {}
        if args.m4b_config:
            logging.debug("Loading m4b_config JSON file")
            with open(args.m4b_config, 'r') as f:
                m4b_config = json.load(f)
            logging.info("m4b_config JSON file loaded successfully")
        else:
            logging.info("No m4b_config JSON file provided, proceeding without it")

        # Load the user_config JSON file if provided
        user_config = {}
        if args.user_config:
            logging.debug("Loading user_config JSON file")
            with open(args.user_config, 'r') as f:
                user_config = json.load(f)
            logging.info("user_config JSON file loaded successfully")
        else:
            logging.info("No user_config JSON file provided, proceeding without it")

        # Call the main function
        main(app_config=app_config, m4b_config=m4b_config, user_config=user_config)

        logging.info(f"{script_name} script completed successfully")
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise
