import os
import sys
import re
import logging
from colorama import Fore, Style

# Ensure the parent directory is in the sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
from utils.generator import validate_uuid


def ask_question_yn(question: str, default: bool = False) -> bool:
    """
    Ask a yes/no question and return the answer as a boolean.

    Args:
        question (str): The question to ask the user.
        default (bool, optional): The default response value if the user enters an empty string. Defaults to False.

    Returns:
        bool: True if the user answered yes, False if the user answered no.
    """
    yes = {'yes', 'y'}
    no = {'no', 'n'}
    done = None

    while done is None:
        choice = input(f"{Fore.GREEN}{question} (y/n) (default: {Fore.YELLOW}{'yes' if default else 'no'}{Fore.GREEN}):{Style.RESET_ALL} ").lower().strip()
        if not choice:
            done = default
        elif choice in yes:
            done = True
        elif choice in no:
            done = False
        else:
            print(f"{Fore.RED}Please respond with 'yes' or 'no'{Style.RESET_ALL}")
    logging.info(f"User response to '{question}': {choice}")
    return done


def ask_string(prompt: str, default: str = "", show_default: bool = True) -> str:
    """
    Ask the user for a string and return it.

    Args:
        prompt (str): The prompt to display to the user.
        default (str, optional): The default value if the user enters an empty string. Defaults to "".
        show_default (bool, optional): Whether to show the default value in the prompt. Defaults to True.

    Returns:
        str: The string entered by the user.
    """
    prompt_text = f"{Fore.GREEN}{prompt}"
    if show_default:
        prompt_text += f" (default/current value: {Fore.YELLOW}{default}{Fore.GREEN})"
    prompt_text += f":{Style.RESET_ALL} "

    while True:
        response = input(prompt_text).strip()
        if not response:
            response = default
        if not response: # As default is empty if not specified then we throw this error
            print(f"{Fore.RED}Input cannot be empty.{Style.RESET_ALL}")
            continue
        logging.info(f"User response to '{prompt}': {response}")
        return response


def ask_email(prompt: str, default: str = "", show_default: bool = True) -> str:
    """
    Ask the user for an email address and validate it.

    Args:
        prompt (str): The prompt to display to the user.
        default (str, optional): The default value if the user enters an empty string. Defaults to "".
        show_default (bool, optional): Whether to show the default value in the prompt. Defaults to True.

    Returns:
        str: The validated email address.
    """
    prompt_text = f"{Fore.GREEN}{prompt}"
    if show_default:
        prompt_text += f" (default/current value: {Fore.YELLOW}{default}{Fore.GREEN})"
    prompt_text += f":{Style.RESET_ALL} "

    while True:
        email = input(prompt_text).strip()
        if not email:
            email = default
        if not email: # As default is empty if not specified then we throw this error
            print(f"{Fore.RED}Email address cannot be empty.{Style.RESET_ALL}")
            continue
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            print(f"{Fore.RED}Invalid email address.{Style.RESET_ALL}")
            continue
        else:
            logging.info(f"User entered email: {email}")
            return email


def ask_uuid(prompt: str, length: int, default: str = "", show_default: bool = True) -> str:
    """
    Ask the user for a UUID and validate it.

    Args:
        prompt (str): The prompt to display to the user.
        length (int): The expected length of the UUID.
        default (str, optional): The default value if the user enters an empty string. Defaults to "".
        show_default (bool, optional): Whether to show the default value in the prompt. Defaults to True.

    Returns:
        str: The validated UUID.
    """
    prompt_text = f"{Fore.GREEN}{prompt}"
    if show_default:
        prompt_text += f" (default/current value: {Fore.YELLOW}{default}{Fore.GREEN})"
    prompt_text += f":{Style.RESET_ALL} "

    while True:
        uuid = input(prompt_text).lower().strip()
        if not uuid:
            uuid = default
        if not uuid: # As default is empty if not specified then we throw this error
            print(f"{Fore.RED}UUID cannot be empty.{Style.RESET_ALL}")
            continue
        elif len(uuid) != length:
            print(f"{Fore.RED}Invalid UUID length.{Style.RESET_ALL}")
            logging.warning(f"Invalid UUID length. Expected: {length}, Got: {len(uuid)}")
        elif not validate_uuid(uuid, length):
            print(f"{Fore.RED}Invalid UUID format.{Style.RESET_ALL}")
        else:
            logging.info(f"User entered UUID: {uuid}")
            return uuid


def main() -> None:
    """
    Main function to run the prompt helper standalone.
    """
    pass


if __name__ == "__main__":
    main()
