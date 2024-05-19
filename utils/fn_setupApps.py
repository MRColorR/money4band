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
def main(user_config:dict,m4b_config:dict):
    advance_setup = input('Do you want to go with advanced setup?(y/n)')
    if advance_setup.lower().strip(' ') == 'y':
        "For the pros who prefer quick setup"
        pass
    else:
        "The same previous setup method"


