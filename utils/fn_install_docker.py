import os
import subprocess
import logging
import argparse
import json
from typing import Dict, Any
import sys
import time

# Ensure the parent directory is in the sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)

# Import the module from the parent directory
from utils.detector import detect_os, detect_architecture
from utils.downloader import download_file
from utils.cls import cls
from utils.loader import load_json_config
from utils.prompt_helper import ask_question_yn

def is_docker_installed(m4b_config: Dict[str, Any]) -> bool:
    """Check if Docker is already installed."""
    try:
        result = subprocess.run(["docker", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, universal_newlines=True)
        os_info = detect_os(m4b_config)
        arch_info = detect_architecture(m4b_config)
        os_type = os_info["os_type"]
        dkarch = arch_info["dkarch"]
        sleep_time = m4b_config.get("system", {}).get("sleep_time", 1)
        msg = f"Docker is already installed on {os_type} with {dkarch} architecture"
        logging.info(msg)
        print(msg)
        time.sleep(sleep_time)
        return True
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise

def install_docker_linux(files_path: str):
    """Install Docker on a Linux system."""
    try:
        logging.info("Starting Docker for Linux auto installation script")

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

        installer_url = "https://desktop.docker.com/win/stable/Docker%20Desktop%20Installer.exe"
        installer_path = os.path.join(files_path, "DockerInstaller.exe")

        # Download Docker Installer
        download_file(installer_url, installer_path)

        # Install Docker
        result = subprocess.run(
            [installer_path, "install", "--accept-license", "--quiet"],  # quiet suppress lots of messages and disable the docker GUI
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True,
            check=True  # Raise error if the subprocess returns non-zero exit code
        )

        # Print stdout and stderr
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())

        # Print installation success message
        msg = "Docker installed successfully on Windows"
        logging.info(msg)
        print(f"{msg}\nPlease ensure that Docker autostarts with your system by checking it in the Docker settings")

        # Clean-up
        os.remove(installer_path)
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
        print(f"{msg}\nPlease ensure that Docker autostarts with your system by checking it in the Docker settings")
    except subprocess.CalledProcessError as e:
        logging.error(f"An error occurred during Docker installation on macOS: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred during Docker installation on macOS: {str(e)}")
        raise

def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Main function to install Docker based on the operating system.

    Parameters:
    app_config_path -- The path to the app configuration file.
    m4b_config_path -- The path to the m4b configuration file.
    user_config_path -- The path to the user configuration file.
    """
    m4b_config = load_json_config(m4b_config_path)
    cls()

    # Detect OS and architecture using the detect module
    os_info = detect_os(m4b_config)
    arch_info = detect_architecture(m4b_config)
    
    os_type = os_info["os_type"].lower()
    dkarch = arch_info["dkarch"].lower()
    files_path = m4b_config.get('files_path', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp'))

    # Check if Docker is already installed
    if is_docker_installed(m4b_config):
        return

    if not ask_question_yn(f"Do you wish to proceed with the Docker for {os_type} automatic installation?"):
        msg = "Docker installation canceled by user"
        logging.info(msg)
        print(msg)
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
        main(app_config_path=args.app_config, m4b_config_path=args.m4b_config, user_config_path=args.user_config)
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
