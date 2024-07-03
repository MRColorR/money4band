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

def generate_device_name():
    words = [
        "Panther", "Tiger", "Eagle", "Falcon", "Lion","Sucks",
        "Wolf", "Leopard", "Hawk", "Dragon", "Phoenix","Melon",
        "Cheetah", "Jaguar", "Cougar", "Raptor", "Amazon","Musk",
        "Griffin", "Orca", "Shark", "Dolphin", "Whale","Sam2029","Spiderman"
    ]
    
    # Choose two random words
    word1 = random.choice(words)
    word2 = random.choice(words)
    
    # Ensure the two words are not the same
    while word1 == word2:
        word2 = random.choice(words)
    
    # Combine them to form the device name
    device_name = f"{word1}_{word2}"
    
    return device_name

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
            restart_policy={"Name": "always"},
            #log_config={"type": "none"}
        )

        print(f"Container {container_name} started successfully.")
        with open('containers.txt','a') as f:
            f.write(f'{container_name}\n')

    except Exception as e:

        print(f"An error occurred: {e}")

    return f'container:{container_name}'

def run_container(cmd,client,image_name,container_name,user_data,order,network_name=None,log_level=None):
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
            # assuming that you can always add some random stuff if its not availabe in userdata
            if user_data[order[0]] == '':
                cmd += generate_device_name()
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
            "image":image_name,
            "detach":True,
            "name":container_name,
            "environment":environment,
            "restart_policy":{"Name": "always"},
            "command" : cmd,
            }
        if not log_level:
            kwargs["log_config"]={"type": "none"}

        if network_name:
            kwargs["network"]=network_name
        # Run the container
        print(kwargs)
        time.sleep(10)
        container = client.containers.run(**kwargs)

        print(f"Container {container_name} started successfully.")
        with open('containers.txt','a') as f:
            f.write(f'{container_name}\n')

        #print(container.logs().decode('utf-8'))

    except Exception as e:
        print(f"An error occurred: {e}")

def main(app_config: dict, m4b_config: dict, user_config: dict = loader.load_json_config('./config/user-config.json')):
    try:
        with open('./containers.txt') as f:
            lines = [line for line in f if line.strip()]
            if lines:
                print("* Note there are already running containers. You may want to stop them.")
                if input('Do you still want to continue? (y/n): ').lower().strip() != 'y':
                    return
    except FileNotFoundError:
        print('No previously running container found')
    
    if not user_config['proxies']['multiproxy']:

        client = docker.from_env()
        id = generate_salt()

        if user_config['proxies']['enabled']:
            network = proxy_container(user_config['proxies']['proxy'],client=client)
        else:
            network = None

        for app in app_config['apps']:
            app_name = app['name'].lower()

            if user_config['apps'][app_name]['enabled']:
                print(f'running {app_name.title()} container')


                # format the command with the needed variables
                cmd = app['cmd']
        
                run_container(cmd=cmd,network_name=network,client=client,image_name=app['image'],container_name=f'{app_name}_{id}',user_data=user_config['apps'][app_name],order=list(app['order']),log_level='Something')

                '''change to system default sleep time'''
                time.sleep(5)
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


                    # format the command with the needed variables
                    cmd = app['cmd']
         
                    run_container(cmd=cmd,network_name=network,client=client,image_name=app['image'],container_name=f'{app_name}_{id}',user_data=user_config['apps'][app_name],order=list(app['order']),log_level=user_config['logs'])
                    '''change to system default sleep time'''
                    time.sleep(5)
                    cls()

            progress += 1
