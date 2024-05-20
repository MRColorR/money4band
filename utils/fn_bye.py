import os
import argparse
import logging
import locale
import time
from typing import Dict, Any
from colorama import Fore, Back, Style, just_fix_windows_console
from utils import load, detect
from utils.cls import cls
import random
import sys

def main(app_config:dict,m4b_config:dict):
    cls()
    print('Qutting the app')
    time.sleep(m4b_config['system']['sleep_time'])
    print(random.choice(['Have a great day........','If you see this then sam probably suceeded making this yay!!!','Look at the eyes deeper they never lie!!','Enjoy the rest of your day','The world will be never with you when you need it the most :(']))
    time.sleep(m4b_config['system']['sleep_time'])
    sys.exit()