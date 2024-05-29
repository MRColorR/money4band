import os
import argparse
import logging
import locale
import time
from typing import Dict, Any
from colorama import Fore, Back, Style, just_fix_windows_console
from utils import load, detect
from utils.cls import cls
import json
import subprocess

def main(app_config:dict,m4b_config:dict):
    user_config = load.load_json_config('./config/user-config.json')
    for app in app_config['apps']:

        app_name = app['name'].lower()

        if user_config['apps'][app_name]['enabled']:

            print(f'Pulling {app_name.title()} container')
            subprocess.run(f'docker pull {app['image']}')
            time.sleep(m4b_config['system']['sleep_time'])

            #now run the app with appropriate args
            extra_global = {'device_name':'device_info'}
            run_command = ['docker','run','-d','--name',app_name]

            run_command.append(app['image'])
            for i in app['flags']:
                run_command.append(f'{app['flags'][i]}')
                run_command.append(f'{user_config["apps"][app_name][i]}')
            
            for i in app['additional_args']:
                if i in extra_global:
                    run_command.append(f'{app['additional_args'][i]}')
                    run_command.append(f'{user_config[extra_global[i]][i]}')
                else:
                    run_command.append(f'{app['additional_args'][i]}')

            print(run_command)
            subprocess.run(run_command,shell=True)
            cls()