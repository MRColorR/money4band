"""Shared M4B banner and greeting helpers.

Centralises the header that is displayed in the interactive menu, setup
wizard, and anywhere else a branded banner is needed.
"""

from __future__ import annotations

import getpass
import logging
from typing import Any

from colorama import Fore, Style

logger = logging.getLogger(__name__)

_SEPARATOR = "----------------------------------------------"


def get_system_username() -> str:
    """Return the OS account username, falling back to ``'user'``."""
    try:
        return getpass.getuser()
    except Exception:
        return "user"


def ensure_nickname(user_config: dict[str, Any]) -> str:
    """Ensure ``user_config["user"]["Nickname"]`` is set to a real value.

    If it is still the template placeholder (``yourNickname``) or empty,
    replace it with the OS account username.  Returns the resolved nickname.
    """
    user = user_config.setdefault("user", {})
    nick: str = user.get("Nickname", "")
    # Exact template placeholder only - a prefix match overwrote any
    # user-chosen nickname that happened to start with "your".
    if not nick or nick == "yourNickname":
        nick = get_system_username()
        user["Nickname"] = nick
    return nick


def print_banner(
    m4b_config: dict[str, Any],
    *,
    nickname: str = "",
    greeting: str = "",
) -> None:
    """Print the standard M4B header banner.

    Parameters
    ----------
    m4b_config:
        The loaded ``m4b-config.json`` dict (needs ``project`` section).
    nickname:
        If provided, a personalised "Hello, {nickname}!" line is printed
        after the header separator.
    greeting:
        Optional extra text printed after the nickname line (e.g. a setup
        wizard welcome message).  Omit for the plain header.
    """
    version = m4b_config.get("project", {}).get("project_version", "?")
    ds_url = m4b_config.get("project", {}).get("ds_project_server_url", "")

    print(f"{Fore.GREEN}{_SEPARATOR}")
    print(f"MONEY4BAND v{version}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{_SEPARATOR}{Style.RESET_ALL}")
    print(
        f"{Fore.YELLOW}Support the M4B development <3 check the donation "
        f"options in the README, on GitHub or in our Discord. "
        f"Every bit helps!{Style.RESET_ALL}"
    )
    if ds_url:
        print(
            f"{Fore.MAGENTA}Join our Discord community for updates, help "
            f"and discussions: {ds_url}{Style.RESET_ALL}"
        )
    print(_SEPARATOR)

    if nickname:
        print(f"Hello, {Fore.GREEN}{nickname}{Style.RESET_ALL}!")
    if greeting:
        print(greeting)
