from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import time
from typing import Any

from colorama import Fore, Style, just_fix_windows_console

from money4band.core.loader import load_json_config
from money4band.ui.cls import cls

logger = logging.getLogger(__name__)

# Initialize colorama for Windows compatibility
just_fix_windows_console()


def fn_bye(m4b_config: dict[str, Any]) -> None:
    """
    Quit the application gracefully with a farewell message.

    Arguments:
    m4b_config -- the m4b configuration dictionary
    """
    try:
        logger.info("Exiting the application gracefully")
        cls()
        print(
            Fore.GREEN
            + "Thank you for using M4B! Please share this app with your friends!"
            + Style.RESET_ALL
        )
        print(Fore.GREEN + "Exiting the application..." + Style.RESET_ALL)

        sleep_time = m4b_config.get("system", {}).get("sleep_time", 1)
        farewell_messages = m4b_config.get(
            "farewell_messages",
            [
                "Have a fantastic day!",
                "Happy earning!",
                "Goodbye!",
                "Bye! Bye!",
                "Did you know \n if you simply click enter while setting up apps the app will be skipped ^^",
                "Did you know typing 404 while setting up apps the rest of the setup process will be skipped",
            ],
        )
        print(random.choice(farewell_messages))
        time.sleep(sleep_time)
        sys.exit(0)
    except Exception as e:
        logger.error(f"An error occurred in fn_bye: {str(e)}")
        raise


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Main function to call the fn_bye function.

    Arguments:
    app_config_path -- the path to the app configuration file
    m4b_config_path -- the path to the m4b configuration file
    user_config_path -- the path to the user configuration file
    """
    # Stop the background dashboard (if running) before exiting.
    try:
        config_dir = os.path.dirname(user_config_path)
        from money4band.dashboard.setup import read_dashboard_pid, remove_dashboard_pid

        pid = read_dashboard_pid(config_dir)
        if pid is not None:
            import signal

            os.kill(pid, signal.SIGTERM)
            remove_dashboard_pid(config_dir)
            logger.info("Stopped background dashboard (PID %d) on exit", pid)
    except Exception:  # noqa: BLE001
        pass  # best-effort; don't block exit

    m4b_config = load_json_config(m4b_config_path)
    fn_bye(m4b_config)


if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the module standalone.")
    parser.add_argument(
        "--app-config", type=str, required=False, help="Path to app_config JSON file"
    )
    parser.add_argument(
        "--m4b-config", type=str, required=True, help="Path to m4b_config JSON file"
    )
    parser.add_argument(
        "--user-config", type=str, required=False, help="Path to user_config JSON file"
    )
    parser.add_argument(
        "--log-dir",
        default=os.path.join(script_dir, "logs"),
        help="Set the logging directory",
    )
    parser.add_argument(
        "--log-file", default=f"{script_name}.log", help="Set the logging file name"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    args = parser.parse_args()

    # Set logging level based on command-line arguments
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    # Start logging
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.log_dir, args.log_file),
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_level,
    )

    logger.info(f"Starting {script_name} script...")

    try:
        # Call the main function
        main(
            app_config_path=args.app_config,
            m4b_config_path=args.m4b_config,
            user_config_path=args.user_config,
        )
        logger.info(f"{script_name} script completed successfully")
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise
