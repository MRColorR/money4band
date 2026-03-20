import argparse
import json
import logging
import os

# Ensure the parent directory is in the sys.path
import sys

from colorama import Back, Fore, Style, just_fix_windows_console

from utils.cls import cls
from utils.dumper import write_json
from utils.loader import (
    get_all_app_categories,
    get_category_entries,
    is_category_active,
    load_json_config,
)

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
# Import the module from the parent directory


def _display_catalog(app_config: dict) -> None:
    """Print the full app catalog grouped by category with status badges."""
    all_cats = get_all_app_categories(app_config)
    active_cats = [c for c in all_cats if is_category_active(app_config, c)]
    inactive_cats = [c for c in all_cats if not is_category_active(app_config, c)]

    for category in active_cats + inactive_cats:
        apps = get_category_entries(app_config, category)
        if not apps:
            continue

        active = is_category_active(app_config, category)
        status = f"{Fore.GREEN}ACTIVE{Style.RESET_ALL}" if active else f"{Fore.RED}INACTIVE{Style.RESET_ALL}"
        print(f"{Back.YELLOW}--- {category.upper()} [{status}{Back.YELLOW}] ---{Back.RESET}")

        for app in apps:
            name_line = f"{Fore.GREEN}{app['name'].upper()}: {Fore.CYAN}{app['link']}{Style.RESET_ALL}"
            reason = app.get("removal_reason")
            if reason and not active:
                name_line += f"  {Fore.YELLOW}({reason}){Style.RESET_ALL}"
            print(name_line)
        print()


def _manage_categories(app_config: dict, app_config_path: str | None) -> None:
    """Interactive submenu to toggle category active/inactive status."""
    all_cats = get_all_app_categories(app_config)
    if not all_cats:
        print(f"{Fore.YELLOW}No categories found.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.CYAN}=== Manage Category Status ==={Style.RESET_ALL}")
    for idx, cat in enumerate(all_cats, 1):
        active = is_category_active(app_config, cat)
        badge = f"{Fore.GREEN}ACTIVE{Style.RESET_ALL}" if active else f"{Fore.RED}INACTIVE{Style.RESET_ALL}"
        count = len(get_category_entries(app_config, cat))
        print(f"  {idx}. {cat} [{badge}] ({count} apps)")

    print(f"\n  0. Back")
    choice = input("Select category to toggle (number): ").strip()

    try:
        choice_num = int(choice)
    except ValueError:
        print(f"{Fore.YELLOW}Invalid input.{Style.RESET_ALL}")
        return

    if choice_num == 0:
        return

    if not 1 <= choice_num <= len(all_cats):
        print(f"{Fore.YELLOW}Invalid selection.{Style.RESET_ALL}")
        return

    cat_key = all_cats[choice_num - 1]
    old_status = app_config[cat_key]["active"]
    new_status = not old_status
    app_config[cat_key]["active"] = new_status

    new_badge = f"{Fore.GREEN}ACTIVE{Style.RESET_ALL}" if new_status else f"{Fore.RED}INACTIVE{Style.RESET_ALL}"
    print(f"\n{cat_key} is now [{new_badge}]")

    if app_config_path:
        write_json(app_config, app_config_path)
        logging.info("Saved category status change: %s → active=%s", cat_key, new_status)
        print(f"{Fore.GREEN}Saved to {app_config_path}{Style.RESET_ALL}")
    else:
        logging.warning("No app_config_path provided — change not persisted")


def fn_app_catalog(app_config: dict, app_config_path: str | None = None) -> None:
    """
    Display the app catalog: all categories with status and links.
    Optionally allows toggling category active status.

    Arguments:
    app_config -- the app config dictionary
    app_config_path -- path to app-config.json (for saving category changes)
    """
    try:
        logging.info("Displaying app catalog")
        cls()
        just_fix_windows_console()

        _display_catalog(app_config)

        print("Info: Use CTRL+Click to open links or copy them")
        print()

        manage = input(
            f"Manage category status? ({Fore.GREEN}y{Style.RESET_ALL}/{Fore.RED}n{Style.RESET_ALL}): "
        ).strip().lower()
        if manage in ("y", "yes"):
            _manage_categories(app_config, app_config_path)
        else:
            input("Press Enter to go back to main menu")
    except Exception as e:
        logging.error(f"An error occurred in fn_app_catalog: {str(e)}")
        raise


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Main function to display the app catalog.

    Arguments:
    app_config_path -- the path to the app configuration file
    m4b_config_path -- the path to the m4b configuration file
    user_config_path -- the path to the user configuration file
    """
    app_config = load_json_config(app_config_path)
    fn_app_catalog(app_config, app_config_path)


if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the module standalone.")
    parser.add_argument(
        "--app-config", type=str, required=True, help="Path to app_config JSON file"
    )
    parser.add_argument(
        "--m4b-config", type=str, required=False, help="Path to m4b_config JSON file"
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

    logging.info(f"Starting {script_name} script...")

    try:
        main(
            app_config_path=args.app_config,
            m4b_config_path=args.m4b_config,
            user_config_path=args.user_config,
        )
        logging.info(f"{script_name} script completed successfully")
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise
