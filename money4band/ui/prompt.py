from __future__ import annotations

import logging
import re
import sys

from colorama import Fore, Style

from money4band.docker.generator import validate_uuid

logger = logging.getLogger(__name__)


class SkipAppError(Exception):
    """Cancel the current app's pending setup without aborting the wizard."""


def _read_response(message: str, *, allow_skip: bool = False) -> str:
    response = input(message).strip()
    if allow_skip and response == "/skip":
        raise SkipAppError
    return response


def wait_for_enter(message: str, *, allow_skip: bool = False) -> None:
    """Wait for Enter, with an explicit cancellation command during app setup."""
    while _read_response(message, allow_skip=allow_skip):
        print(
            "Press Enter to continue."
            + (" Type /skip to skip this app." if allow_skip else "")
        )


def pause(message: str) -> None:
    """Wait for the user to press a key before continuing.

    Skipped when stdin is not a terminal (piped/scripted runs) so
    commands that finished their work do not die with a spurious
    EOF-driven non-zero exit at a purely cosmetic prompt.
    """
    if sys.stdin is None or not sys.stdin.isatty():
        return
    try:
        input(message)
    except EOFError:
        pass


def ask_question_yn(question: str, default: bool = False) -> bool:
    """
    Ask a yes/no question and return the answer as a boolean.

    Args:
        question (str): The question to ask the user.
        default (bool, optional): The default response value if the user enters an empty string. Defaults to False.

    Returns:
        bool: True if the user answered yes, False if the user answered no.
    """
    yes = {"yes", "y"}
    no = {"no", "n"}
    done = None

    while done is None:
        choice = (
            input(
                f"{Fore.GREEN}{question} (y/n) (default: {Fore.YELLOW}{'yes' if default else 'no'}{Fore.GREEN}):{Style.RESET_ALL} "
            )
            .lower()
            .strip()
        )
        if not choice:
            done = default
        elif choice in yes:
            done = True
        elif choice in no:
            done = False
        else:
            print(f"{Fore.RED}Please respond with 'yes' or 'no'{Style.RESET_ALL}")
    logger.info(f"User response to '{question}': {choice}")
    return done


def _format_text_prompt(
    prompt: str, default: str, show_default: bool, *, allow_skip: bool = False
) -> str:
    """Own the delimiter so labels supplied by callers never duplicate it."""
    prompt_text = f"{Fore.GREEN}{prompt.rstrip().rstrip(':')}"
    if show_default:
        prompt_text += f" (default/current value: {Fore.YELLOW}{default}{Fore.GREEN})"
        if allow_skip and default:
            prompt_text += " (Enter to keep)"
    elif allow_skip and default and not default.startswith("your"):
        prompt_text += " (current: ********; Enter to keep)"
    return prompt_text + f":{Style.RESET_ALL} "


def ask_string(
    prompt: str,
    default: str = "",
    show_default: bool = True,
    *,
    allow_skip: bool = False,
) -> str:
    """
    Ask the user for a string and return it.

    Args:
        prompt (str): The prompt to display to the user.
        default (str, optional): The default value if the user enters an empty string. Defaults to "".
        show_default (bool, optional): Whether to show the default value in the prompt. Defaults to True.
        allow_skip: Raise SkipAppError on /skip during app credential collection.

    Returns:
        str: The string entered by the user.
    """
    prompt_text = _format_text_prompt(
        prompt, default, show_default, allow_skip=allow_skip
    )

    while True:
        response = _read_response(prompt_text, allow_skip=allow_skip)
        if not response:
            response = default
        if (
            not response
        ):  # As default is empty if not specified then we throw this error
            print(f"{Fore.RED}Input cannot be empty.{Style.RESET_ALL}")
            continue
        return response


def ask_email(
    prompt: str,
    default: str = "",
    show_default: bool = True,
    *,
    allow_skip: bool = False,
) -> str:
    """
    Ask the user for an email address and validate it.

    Args:
        prompt (str): The prompt to display to the user.
        default (str, optional): The default value if the user enters an empty string. Defaults to "".
        show_default (bool, optional): Whether to show the default value in the prompt. Defaults to True.
        allow_skip: Raise SkipAppError on /skip during app credential collection.

    Returns:
        str: The validated email address.
    """
    prompt_text = _format_text_prompt(
        prompt, default, show_default, allow_skip=allow_skip
    )

    while True:
        email = _read_response(prompt_text, allow_skip=allow_skip)
        if not email:
            email = default
        if not email:  # As default is empty if not specified then we throw this error
            print(f"{Fore.RED}Email address cannot be empty.{Style.RESET_ALL}")
            continue
        elif not re.match(
            r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9]"
            r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
            r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$",
            email,
        ):
            print(f"{Fore.RED}Invalid email address.{Style.RESET_ALL}")
            continue
        else:
            logger.debug(f"User entered email: {email}")
            return email


def ask_uuid(
    prompt: str,
    length: int,
    default: str = "",
    show_default: bool = True,
    *,
    allow_skip: bool = False,
) -> str:
    """
    Ask the user for a UUID and validate it.

    Args:
        prompt (str): The prompt to display to the user.
        length (int): The expected length of the UUID.
        default (str, optional): The default value if the user enters an empty string. Defaults to "".
        show_default (bool, optional): Whether to show the default value in the prompt. Defaults to True.
        allow_skip: Raise SkipAppError on /skip during app credential collection.

    Returns:
        str: The validated UUID.
    """
    prompt_text = _format_text_prompt(
        prompt, default, show_default, allow_skip=allow_skip
    )

    while True:
        uuid = _read_response(prompt_text, allow_skip=allow_skip).lower()
        if not uuid:
            uuid = default
        if not uuid:  # As default is empty if not specified then we throw this error
            print(f"{Fore.RED}UUID cannot be empty.{Style.RESET_ALL}")
            continue
        elif len(uuid) != length:
            print(f"{Fore.RED}Invalid UUID length.{Style.RESET_ALL}")
            logger.warning(f"Invalid UUID length. Expected: {length}, Got: {len(uuid)}")
        elif not validate_uuid(uuid, length):
            print(f"{Fore.RED}Invalid UUID format.{Style.RESET_ALL}")
        else:
            logger.debug(f"User entered UUID: {uuid}")
            return uuid


def ask_question_num(
    prompt: str,
    default: int = 0,
    min_val: int | None = None,
    max_val: int | None = None,
) -> int:
    """Ask the user for an integer, with optional range enforcement.

    Args:
        prompt: The prompt text.
        default: Value returned when the user presses Enter.
        min_val: Minimum accepted value (inclusive).
        max_val: Maximum accepted value (inclusive).

    Returns:
        The integer entered by the user.
    """
    while True:
        raw = input(
            f"{Fore.GREEN}{prompt} "
            f"(default: {Fore.YELLOW}{default}{Fore.GREEN})"
            f":{Style.RESET_ALL} "
        ).strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print(f"{Fore.RED}Please enter a valid integer.{Style.RESET_ALL}")
            continue
        if min_val is not None and value < min_val:
            print(f"{Fore.RED}Value must be >= {min_val}.{Style.RESET_ALL}")
            continue
        if max_val is not None and value > max_val:
            print(f"{Fore.RED}Value must be <= {max_val}.{Style.RESET_ALL}")
            continue
        return value
