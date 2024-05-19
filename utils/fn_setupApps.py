import os
import argparse
import logging
import locale
import time
from typing import Dict, Any
from colorama import Fore, Back, Style, just_fix_windows_console
from utils import load, detect
from utils.cls import cls

def write_json():
    '''
    Used to write to user-config.json
    can be moved to load but I am not sure soooo yeah let it here for now
    '''
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
        asking = {'enabled':'Do you want to run {}','email':'Enter your {} email','password':'Enter you {} password','apikey':'Enter your {} api key','cid':'Enter your {} cid','token':'Enter your {} token','code':'Enter your {} code'}

        for app in user_config['apps']:
            cls()
            for property in user_config['apps'][app]:
                if property in asking:
                    user_input = input(asking[property].format(app.title()))
                    print(user_input.lower().strip(' '))
                    if property == 'enabled' and user_input.lower().strip(' ') !='y':
                        print('skipping app')
                        break
                    







