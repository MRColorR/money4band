import json
import os
from typing import Dict, Any
from colorama import Fore, Style , just_fix_windows_console

def run(app_config: Dict):
    """
    Show the links of the apps.

    Arguments:
    app_config -- the app config dictionary
    """
    try:
        print("Use CTRL+Click to open links or copy them:")

        # Iterate over all app types and apps
        for app_type, apps in app_config.items():
            print(f"---{app_type}---")
            for app in apps:
                print(f"{app['name']}")
                print(f"{app['link']}")

        input("Press Enter to go back to mainmenu")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
