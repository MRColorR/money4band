import os
import argparse
import logging
import json
import subprocess
from typing import Dict
from utils.detect import detect_os, detect_architecture

def fn_install_docker(m4b_config: Dict) -> None:
    """
    Install Docker on different operating systems.

    Arguments:
    m4b_config -- The m4b config dictionary.
    """
    try:
        logging.info("Docker installation function started")

        os_info = detect_os(m4b_config)
        arch_info = detect_architecture(m4b_config)

        yn = input("Do you wish to proceed with the Docker automatic installation? (Y/N): ").lower()
        if yn not in ['y', 'yes']:
            logging.info("Docker installation canceled by user")
            print("Docker installation canceled")
            return

        if os_info["os_type"] == "linux":
            logging.info("Starting Docker for Linux auto installation script")
            subprocess.run(["curl", "-fsSL", "https://get.docker.com", "-o", "get-docker.sh"], check=True)
            subprocess.run(["sudo", "sh", "get-docker.sh"], check=True)
        elif os_info["os_type"] == "windows":
            logging.info("Starting Docker for Windows auto installation script")
            # Implement Windows installation logic here
        elif os_info["os_type"] == "macos":
            logging.info("Starting Docker for MacOS auto installation script")
            # Implement MacOS installation logic here
        else:
            logging.error("Unsupported operating system")
            print("Unsupported operating system")

    except Exception as e:
        logging.error(f"An error occurred during Docker installation: {str(e)}")
        raise

def main(m4b_config: Dict) -> None:
    """
    Main function to call the fn_install_docker function.

    Arguments:
    m4b_config -- the m4b config dictionary
    """
    try:
        fn_install_docker(m4b_config)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the Docker installation function.')
    parser.add_argument('--m4b-config', type=str, required=True, help='Path to m4b_config JSON file')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    log_dir = os.path.join(script_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_file = f"{script_name}.log"
    logging.basicConfig(filename=os.path.join(log_dir, log_file),
                        format='%(asctime)s - [%(levelname)s] - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)

    logging.info(f"Starting {script_name} script...")

    try:
        m4b_config = json.load(open(args.m4b_config))
        main(m4b_config)
        logging.info(f"{script_name} script completed successfully")
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        print(f"File not found: {str(e)}")
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        print(f"Error decoding JSON: {str(e)}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        print(f"An unexpected error occurred: {str(e)}")
