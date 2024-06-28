import os
import argparse
import logging
import time
import docker
from utils.cls import cls
import json

def stop_containers_from_file(containers_file: str):
    client = docker.from_env()
    try:
        with open(containers_file, 'r') as f:
            data = json.load(f)
        containers = data.get('containers', {})
        proxy_container = data.get('proxy', {})

        for app, container_list in containers.items():
            for container_info in container_list:
                container_name = container_info['container_name']
                try:
                    container = client.containers.get(container_name)
                    container.stop()
                    print(f"Stopped container: {container_name}")
                except Exception as e:
                    print(f"Failed to stop container {container_name}: {e}")

        if proxy_container:
            try:
                container_name = proxy_container['container_name']
                container = client.containers.get(container_name)
                container.stop()
                print(f"Stopped proxy container: {container_name}")
            except Exception as e:
                print(f"Failed to stop proxy container {container_name}: {e}")

        # Clear the containers file after stopping them
        with open(containers_file, 'w') as f:
            json.dump({'containers': {}}, f)
    except Exception as e:
        logging.error(f"An error occurred while stopping containers: {str(e)}")
        raise

def main(app_config_path: str, m4b_config_path: str, user_config_path: str, containers_file: str = './containers.json') -> None:
    """
    Main function to stop all running Docker containers.

    Parameters:
    app_config_path -- The path to the app configuration file.
    m4b_config_path -- The path to the m4b configuration file.
    user_config_path -- The path to the user configuration file.
    containers_file -- The path to the containers JSON file.
    """
    cls()
    stop_containers_from_file(containers_file)
    logging.info("All Docker containers stopped successfully")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the module standalone.')
    parser.add_argument('--app-config', type=str, required=False, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=True, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config', type=str, required=False, help='Path to user_config JSON file')
    parser.add_argument('--containers-file', type=str, default='./containers.json', help='Path to containers JSON file')
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
        main(app_config_path=args.app_config, m4b_config_path=args.m4b_config, user_config_path=args.user_config, containers_file=args.containers_file)
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
