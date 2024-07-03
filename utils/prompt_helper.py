import os
import sys
import re
from colorama import Fore, Style

# Ensure the parent directory is in the sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
from utils.fn_uuid_generator import validate_uuid


def ask_question_yn(question, default=False) -> bool:
    """
    Ask a yes/no question and return the answer as a boolean.

    Args:
        question (str): The question to ask the user.
        default (bool, optional): The default value if the user enters an empty string. Defaults to False.

    Returns:
        bool: True if the user answered yes, False if the user answered no.
    """
    yes = {'yes', 'y'}
    no = {'no', 'n'}
    done = None

    while done is None:
        choice = input(f"{question} ").lower()
        if not choice:
            done = default
        elif choice in yes:
            done = True
        elif choice in no:
            done = False
        else:
            print(f"{Fore.RED}Please respond with 'yes' or 'no'{Style.RESET_ALL}")

    return done

def ask_string(prompt: str, empty_allowed: bool = False) -> str:
    """
    Ask the user for a string and return it.

    Args:
        prompt (str): The prompt to display to the user.

    Returns:
        str: The string entered by the user.
    """
    while True:
        response = input(f"{prompt} ")
        if not response and not empty_allowed:
            print(f"{Fore.RED}Input cannot be empty.{Style.RESET_ALL}")
            continue
        return response

def ask_email(prompt: str):
    """
    Ask the user for an email address and validate it.

    Returns:
        str: The validated email address.
    """
    while True:
        email = input(f"{prompt} ")
        if not email:
            print(f"{Fore.RED}Email address cannot be empty.{Style.RESET_ALL}")
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            print(f"{Fore.RED}Invalid email address.{Style.RESET_ALL}")
        else:
            return email
        
def ask_uuid(prompt : str, length : int):
    """
    Ask the user for a UUID and validate it.

    Returns:
        str: The validated UUID.
    """
    while True:
        uuid = input(f"{prompt} ").lower().strip()
        if not uuid:
            print(f"{Fore.RED}UUID cannot be empty.{Style.RESET_ALL}")
        elif len(uuid) != length:
            print(f"{Fore.RED}Invalid UUID length.{Style.RESET_ALL}")
        elif not validate_uuid(uuid, length):
            print(f"{Fore.RED}Invalid UUID format.{Style.RESET_ALL}")
        else:
            return uuid

def main() -> None:
    """
    Main function to run the load module standalone.
    """
    pass

if __name__ == "__main__":
    main()
