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

def write_json(data,filename):
    '''
    Used to write to user-config.json
    can be moved to load but I am not sure soooo yeah let it here for now
    '''
    try:
        with open(filename, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        print(f"Data written to {filename} successfully!")
    except Exception as e:
        print(f"Error writing to {filename}: {e}")

def main(app_config:dict,m4b_config:dict):
    user_config = load.load_json_config('./config/user-config.json')
    advance_setup = input('Do you want to go with advanced setup?(y/n)')
    if advance_setup.lower().strip(' ') == 'y':
        "For the pros who prefer quick setup"
        pass
    else:
        "The same previous setup method"

        nickename = input('Enter your nickname')
        #Dont think email is needed
        device_name = input('Enter your device name')

        user_config['user']['Nickname'] = nickename
        user_config['device_info']['device_name'] = device_name


        #ask proxy info lazy to code rn

        #Set up apps now
        asking = {
            'enabled': 'Do you want to run {}: ',
            'email': 'Enter your {} email : ',
            'password': 'Enter your {} password : ',
            'apikey': 'Enter your {} api key : ',
            'cid': 'Enter your {} cid : ',
            'token': 'Enter your {} token :',
            'code': 'Enter your {} code : '
        }
        for app in user_config['apps']:
            cls()
            for property in user_config['apps'][app]:
                if property in asking:
                    user_input = input(asking[property].format(app.title()))
                    print(user_input.lower().strip(' '))
                    if property == 'enabled':
                        if user_input.lower().strip(' ') !='y':
                            print(f'skipping {app}')
                            break
                        else:
                            user_config['apps'][app][property] = True
                    else:
                        user_config['apps'][app][property] = user_input

        #ask additional config settings 


        write_json(user_config,'./config/user-config.json')
                    






