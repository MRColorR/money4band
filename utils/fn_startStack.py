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

def main(app_config: Dict[str, Any], m4b_config: Dict[str, Any]) -> None:
    user_config = loader.load_json_config('./config/user-config.json')
    for app in app_config['apps']:
        app_name = app.get('name', '').lower()

        if user_config['apps'].get(app_name, {}).get('enabled', False):
            logging.info(f'Starting setup for enabled {app_name.title()} app')
            app_image = app.get('image')
            if app_image is None:
                logging.error(f'No image for {app_name}')
                continue
            
            app_flags = app.get('flags', {})
            app_additional_args = app.get('additional_args', {})

            print(f'Pulling {app_name.title()} container')
            subprocess.run(['docker', 'pull', app_image])
            time.sleep(m4b_config['system']['sleep_time'])

            # Now run the app with appropriate args
            extra_global = {'device_name': 'device_info'}
            run_command = ['docker', 'run', '-d', '--name', app_name, app_image]

            for flag, value in app_flags.items():
                run_command.extend([value, user_config["apps"][app_name].get(flag, '')])

            for arg, value in app_additional_args.items():
                if arg in extra_global:
                    run_command.extend([value, user_config[extra_global[arg]].get(arg, '')])
                else:
                    run_command.extend([value])

            print(run_command)
            subprocess.run(run_command, shell=True)
            cls()
