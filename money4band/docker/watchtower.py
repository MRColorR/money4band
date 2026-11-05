from __future__ import annotations

"""Watchtower auto-update setup for M4B."""

import logging
from typing import Any

from colorama import Fore, Style

from money4band.ui.prompt import ask_question_yn

logger = logging.getLogger(__name__)


def setup_watchtower(user_config: dict[str, Any]) -> None:
    """
    Set up the Watchtower auto-update configuration.

    Asks the user if they want M4B to manage container auto-updates via its
    built-in Watchtower service. Disable only if another Watchtower instance
    is already running on the host.

    Args:
        user_config (dict): The user configuration dictionary.
    """
    watchtower_config = user_config.setdefault("watchtower", {})
    current_enabled = watchtower_config.get("enabled", True)

    if current_enabled:
        print("The M4B built-in Watchtower (auto-updater) is currently enabled.")
        if not ask_question_yn("Do you want to change the Watchtower settings?"):
            print("Keeping existing Watchtower settings.")
            logger.info("User chose to keep existing Watchtower settings.")
            return
    else:
        print("The M4B built-in Watchtower (auto-updater) is currently disabled.")
        if not ask_question_yn("Do you want to change the Watchtower settings?"):
            print("Keeping existing Watchtower settings (Watchtower remains disabled).")
            logger.info("User chose to keep existing Watchtower settings (disabled).")
            return

    if ask_question_yn(
        "Do you want M4B to manage container auto-updates via its built-in Watchtower?\n"
        "(Disable only if another Watchtower instance is already running on this host)",
        default=True,
    ):
        watchtower_config["enabled"] = True
        print("M4B built-in Watchtower enabled. Container images will be auto-updated.")
        logger.info("User enabled M4B built-in Watchtower.")
    else:
        watchtower_config["enabled"] = False
        print(
            f"{Fore.YELLOW}M4B Watchtower disabled. "
            f"Ensure another Watchtower instance is managing updates.{Style.RESET_ALL}"
        )
        logger.info("User disabled M4B built-in Watchtower.")
