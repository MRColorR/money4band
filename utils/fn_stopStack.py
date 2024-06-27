import os
import argparse
import logging
import locale
import time
import subprocess
from typing import Dict, Any
from colorama import Fore, Back, Style, just_fix_windows_console
from utils import loader, detector
from utils.cls import cls
import json
import subprocess
import random
import docker

def stop_all_containers():
    client = docker.from_env()
    try:
        containers = client.containers.list()
        for container in containers:
            container.stop()
            print(f"Stopped container: {container.name}")
    except Exception as e:
        logging.error(f"An error occurred while stopping containers: {str(e)}")
        raise

def main(app_config: dict, m4b_config: dict, user_config: dict):
    """
    Main function to stop all running Docker containers.

    Parameters:
    app_config -- The application configuration dictionary.
    m4b_config -- The m4b configuration dictionary.
    user_config -- The user configuration dictionary.
    """
    try:
        logging.info("Stopping all Docker containers")
        cls()
        stop_all_containers()
        logging.info("All Docker containers stopped successfully")
    except Exception as e:
        logging.error(f"An error occurred while stopping Docker containers: {str(e)}")
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the module standalone.')
    parser.add_argument('--app-config', type=str, required=False, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=True, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config', type=str, required=False, help='Path to user_config JSON file')
    parser.add_argument('--log-dir', default='./logs', help='Set the logging directory')
    parser.add_argument('--log-file', default='fn_stopStack.log', help='Set the logging file name')
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

    logging.info("Starting fn_stopStack script...")

    try:
        # Load the app_config JSON file
        app_config = {}
        if args.app_config:
            with open(args.app_config, 'r') as f:
                app_config = json.load(f)

        # Load the m4b_config JSON file
        with open(args.m4b_config, 'r') as f:
            m4b_config = json.load(f)

        # Load the user_config JSON file
        user_config = {}
        if args.user_config:
            with open(args.user_config, 'r') as f:
                user_config = json.load(f)

        main(app_config=app_config, m4b_config=m4b_config, user_config=user_config)
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
