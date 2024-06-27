import os
import argparse
import logging
import locale
import time
from typing import Dict, Any
from colorama import Fore, Back, Style, just_fix_windows_console
from utils import loader, detector
from utils.cls import cls
import random
import docker
import secrets
import string

def generate_salt(length: int = 8) -> str:
    """Generate a secure random alphanumeric salt."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_device_name(adjectives: list, animals: list) -> str:
    """Generate a device name from given word lists."""
    adjective = secrets.choice(adjectives)
    animal = secrets.choice(animals)
    return f"{adjective}_{animal}"

def proxy_container(proxy, rand_id, client):
    # Environment variables
    environment = {
        'LOGLEVEL': 'info',
        'PROXY': proxy,
        'EXTRA_COMMANDS': 'ip rule add iif lo ipproto udp dport 53 lookup main;'
    }

    # DNS settings
    dns = ["1.1.1.1", "8.8.8.8", "1.0.0.1", "8.8.4.4"]

    # Volume mappings
    volumes = {
        '/dev/net/tun': {'bind': '/dev/net/tun', 'mode': 'rw'}
    }

    # Container name and hostname
    container_name = f"my_tun2socks2_{rand_id}"
    hostname = f"my_tun2socks2_{rand_id}"

    try:
        # Pull the image
        image = 'xjasonlyu/tun2socks'
        client.images.pull(image)

        # Run the container
        container = client.containers.run(
            image,
            detach=True,
            name=container_name,
            hostname=hostname,
            cap_add=["NET_ADMIN"],
            network="bridge",
            dns=dns,
            environment=environment,
            volumes=volumes,
            restart_policy={"Name": "always"},
            #log_config={"type": "none"}
        )

        print(f"Container {container_name} started successfully.")
        with open('containers.txt', 'a') as f:
            f.write(f'{container_name}\n')

    except Exception as e:
        print(f"An error occurred: {e}")

    return f'container:{container_name}'

def run_container(cmd, client, image_name, container_name, user_data, order, adjectives, animals, network_name=None, log_level=None):
    # Environment variables
    environment = {}

    # Container name and network
    container_name = container_name
    network_name = network_name
    cmd_list = cmd.split() if cmd else []
    cmd = ''
    last = False
    for index in range(len(cmd_list)):

        # makes sure the environment variable does not get added to cmd 
        if last:
            last = False
            continue
        i = cmd_list[index]

        if i == '-e':
            environment[cmd_list[index+1]] = user_data[order.pop(0)]
            last = True
        elif i == '{}':
            # assuming that you can always add some random stuff if it's not available in userdata
            if user_data[order[0]] == '':
                cmd += generate_device_name(adjectives, animals)
            else:
                cmd += user_data[order.pop(0)]
        elif i == '-v':
            pass
        else:
            cmd += i.strip() 
        
        cmd += ' '

    try:
        # Pull the image
        client.images.pull(image_name)

        kwargs = {
            "image": image_name,
            "detach": True,
            "name": container_name,
            "environment": environment,
            "restart_policy": {"Name": "always"},
            "command": cmd if cmd else None,
        }
        if not log_level:
            kwargs["log_config"] = {"type": "none"}

        if network_name:
            kwargs["network"] = network_name
        # Run the container
        print(kwargs)
        time.sleep(5)
        container = client.containers.run(**kwargs)

        print(f"Container {container_name} started successfully.")
        with open('containers.txt', 'a') as f:
            f.write(f'{container_name}\n')

        #print(container.logs().decode('utf-8'))

    except Exception as e:
        print(f"An error occurred: {e}")

def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    app_config = loader.load_json_config(app_config_path)
    m4b_config = loader.load_json_config(m4b_config_path)
    user_config = loader.load_json_config(user_config_path)

    adjectives = m4b_config['word_lists']['adjectives']
    animals = m4b_config['word_lists']['animals']

    # try to load sleep time and give it a default if not set
    try:
        sleep_time = m4b_config['system'].get('sleep_time', 2)
    except KeyError:
        sleep_time = 2

    try:
        with open('./containers.txt') as f:
            lines = [line for line in f if line.strip()]
            if lines:
                print("* Note there are already running containers. You may want to stop them.")
                if input('Do you still want to continue? (y/n): ').lower().strip() != 'y':
                    return
    except FileNotFoundError:
        print('No previously running container found')
    
    try:
        client = docker.from_env()
    except docker.errors.DockerException as e:
        print("Docker does not seem to be running or is not reachable. Please check Docker and try again.")
        logging.error(f"Docker is not running: {str(e)}")
        time.sleep(sleep_time)
        return

    if not user_config['proxies']['multiproxy']:
        rand_id = generate_salt()

        if user_config['proxies']['enabled']:
            network = proxy_container(user_config['proxies']['proxy'], rand_id, client=client)
        else:
            network = None

        for app in app_config['apps']:
            app_name = app['name'].lower()

            if user_config['apps'][app_name]['enabled']:
                print(f'running {app_name.title()} container')
                # format the command with the needed variables
                cmd = app.get('cmd', None)
                run_container(cmd=cmd, network_name=network, client=client, image_name=app['image'], container_name=f'{app_name}_{rand_id}', user_data=user_config['apps'][app_name], order=list(app.get('order', [])), adjectives=adjectives, animals=animals, log_level='INFO')
                time.sleep(sleep_time)
            cls()

    else:
        # Multi instancing
        with open('./proxies.txt') as f:
            proxies = f.readlines()
            proxies = [i for i in proxies if i != '\n']

        # custom progress bar
        progress = 0
        total = len(proxies)

        for proxy in proxies:
            cls()
            progress_bar = '█' * int((progress / total) * 40) + '.' * (40 - int(progress / total * 40))
            print(f'progress {progress}/{total} |{progress_bar}|')
            proxy = proxy.rstrip('\n')
            rand_id = generate_salt()

            network = proxy_container(proxy, rand_id, client)

            for app in app_config['apps']:
                app_name = app['name'].lower()

                if user_config['apps'][app_name]['enabled']:
                    print(f'running {app_name.title()} container')

                    cmd = app.get('cmd', None)
                    run_container(cmd=cmd, network_name=network, client=client, image_name=app['image'], container_name=f'{app_name}_{rand_id}', user_data=user_config['apps'][app_name], order=list(app.get('order', [])), adjectives=adjectives, animals=animals)
                    time.sleep(sleep_time)
                    cls()

            progress += 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the module standalone.')
    parser.add_argument('--app-config', type=str, required=True, help='Path to app_config JSON file')
    parser.add_argument('--m4b-config', type=str, required=True, help='Path to m4b_config JSON file')
    parser.add_argument('--user-config', type=str, required=True, help='Path to user_config JSON file')
    parser.add_argument('--log-dir', default='./logs', help='Set the logging directory')
    parser.add_argument('--log-file', default='fn_startStack.log', help='Set the logging file name')
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

    logging.info("Starting fn_startStack script...")

    try:
        main(app_config_path=args.app_config, m4b_config_path=args.m4b_config, user_config_path=args.user_config)
        logging.info("fn_startStack script completed successfully")
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise
