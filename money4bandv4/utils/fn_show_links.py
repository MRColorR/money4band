import json
import argparse
from typing import Dict, Any
from colorama import Fore, Back, Style, just_fix_windows_console

from money4bandv4.utils.cls import cls


def main(app_config: Dict=None, m4b_config=None, system_info=None ):
    """
    Show the links of the apps.

    Arguments:
    app_config -- the app config dictionary
    m4b_config -- the m4b config dictionary (not used)
    system_info -- the system info dictionary (not used)
    """
    try:
        cls()
        just_fix_windows_console()
        print("Use CTRL+Click to open links or copy them:")

        # Iterate over all app types and apps
        for app_type, apps in app_config.items():
            print(f"{Back.YELLOW}---{app_type.upper()}---{Back.RESET}")
            for app in apps:
                print(f"{Fore.GREEN}{app['name'].upper()}: {Fore.CYAN}{app['link']}{Style.RESET_ALL}")

        input("Press Enter to go back to mainmenu")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the module standalone.')
    parser.add_argument('--app_config', type=str, required=False, help='Path to app_config JSON file')
    parser.add_argument('--m4b_config', type=str, required=False, help='Path to m4b_config JSON file')
    parser.add_argument('--system_info', type=str, required=False, help='Path to system_info JSON file')

    args = parser.parse_args()

    with open(args.app_config, 'r') as f:
        app_config = json.load(f)

    with open(args.m4b_config, 'r') as f:
        m4b_config = json.load(f)

    with open(args.system_info, 'r') as f:
        system_info = json.load(f)

    main(app_config, m4b_config, system_info)
