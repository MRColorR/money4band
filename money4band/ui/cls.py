from __future__ import annotations

import logging
import os

from colorama import just_fix_windows_console

logger = logging.getLogger(__name__)


def cls() -> None:
    """
    Clear the console.
    """
    try:
        just_fix_windows_console()
        # Native clear is more reliable on Windows terminals than ANSI-only.
        if os.name == "nt":
            os.system("cls")  # noqa: S605
        else:
            os.system("clear")  # noqa: S605

        # Keep ANSI clear as a fallback for terminals that ignore system clear.
        print("\033[2J\033[H", end="", flush=True)
        logger.info("Console cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing console: {str(e)}")
        raise
