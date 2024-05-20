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
            cls()
