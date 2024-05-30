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


def generate_salt(length:int=8):
    chars = 'abcdefghijklmnopqrstuvwxyz'
    salt = ''
    for i in range(length):
        salt += random.choice(chars)
    return salt


def proxy_container(proxy,id,client):
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
    container_name = f"my_tun2socks2_{id}"
    hostname = f"my_tun2socks2_{id}"

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
            restart_policy={"Name": "always"}
        )

        print(f"Container {container_name} started successfully.")
        print(container.logs().decode('utf-8'))

    except Exception as e:

        print(f"An error occurred: {e}")

    return f'container:{container_name}'

def run_container(cmd,network_name,client,image_name,container_name,user_data,order):
    # Environment variables
    environment = {}

    # Container name and network
    container_name = container_name
    network_name = network_name
    cmd_list = cmd.split()
    cmd = ''
    last = False
    for index in range(len(cmd_list)):
        # makes sure the environmen variable does not gets added to cmd 
        if last:
            last = False
            continue
        i = cmd_list[index]

        if i == '-e':
            environment[cmd_list[index+1]] = user_data[order.pop(0)]
            last = True
        elif i == '{}':
            cmd += user_data[order.pop(0)]
        elif i == '-v':
            pass
        else:
            cmd += i 
        
        cmd += ' '



    try:
        # Pull the image
        client.images.pull(image_name)

        # Run the container
        print(environment)
        container = client.containers.run(
            image_name,
            detach=True,
            name=container_name,
            network=network_name,
            environment=environment,
            restart_policy={"Name": "always"},
            command = cmd
        )

        print(f"Container {container_name} started successfully.")
        print(container.logs().decode('utf-8'))

    except Exception as e:
        print(f"An error occurred: {e}")

def main(app_config: dict, m4b_config: dict, user_config: dict = load.load_json_config('./config/user-config.json')):
    user_config = load.load_json_config('./config/user-config.json')
    if not user_config['proxies']['multiproxy']:

        for app in app_config['apps']:

            app_name = app['name'].lower()

            if user_config['apps'][app_name]['enabled']:

                print(f'Pulling {app_name.title()} container')
                subprocess.run(f'docker pull {app["image"]}', shell=True)
                time.sleep(m4b_config['system']['sleep_time'])

                # now run the app with appropriate args
                extra_global = {'device_name': 'device_info'}
                run_command = ['docker', 'run', '-d', '--name', app_name]

                run_command.append(app['image'])
                for i in app['flags']:
                    run_command.append(app['flags'][i])
                    run_command.append(user_config['apps'][app_name][i])

                for i in app['additional_args']:
                    if i in extra_global:
                        run_command.append(app['additional_args'][i])
                        run_command.append(user_config[extra_global[i]][i])
                    else:
                        run_command.append(app['additional_args'][i])

                print(run_command)
                subprocess.run(run_command, shell=True)
                cls()
    else:
        # Multi instancing
        client = docker.from_env()

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
            id = generate_salt()

            network = proxy_container(proxy,id,client)

            for app in app_config['apps']:
                app_name = app['name'].lower()

                if user_config['apps'][app_name]['enabled']:
                    print(f'running {app_name.title()} container')

                    args = {'device_name': 'device_info', 'name': f'{app_name}_{id}', 'network': f'container:my_tun2socks2_{id}', 'img': app['image']}

                    # format the command with the needed variables
                    cmd = app['cmd']
         
                    run_container(cmd,network,client,app['image'],f'{app_name}_{id}',user_config['apps'][app_name],list(app['order']))
                    '''change to system default sleep time'''
                    progress += 1
                    time.sleep(5)
                    cls()
