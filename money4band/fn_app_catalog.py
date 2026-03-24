from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from typing import Any

from colorama import Back, Fore, Style, just_fix_windows_console

from money4band.cls import cls
from money4band.dumper import write_json
from money4band.loader import (
    get_all_app_categories,
    get_category_entries,
    is_category_active,
    load_json_config,
)

logger = logging.getLogger(__name__)


def _display_catalog(app_config: dict[str, Any]) -> None:
    """Print the full app catalog grouped by category.

    Every app shows the same fields regardless of category.
    Adapts to terminal width so referral links are **never** truncated
    and remain fully clickable (Ctrl+Click).

    Wide  (table fits): ``Name  Link  Layer  Payout`` on one line.
    Compact (narrow):   ``Name  Layer  Payout`` on line 1,
                        full link indented on line 2.

    Decorators use only broadly-supported characters:
    ``->`` link prefix, ``>>`` removal reason, ``-`` separator.
    """
    term_width = shutil.get_terminal_size((120, 24)).columns

    all_cats = get_all_app_categories(app_config)
    active_cats = [c for c in all_cats if is_category_active(app_config, c)]
    inactive_cats = [c for c in all_cats if not is_category_active(app_config, c)]

    for category in active_cats + inactive_cats:
        apps = get_category_entries(app_config, category)
        if not apps:
            continue

        active = is_category_active(app_config, category)
        status = (
            f"{Fore.GREEN}ACTIVE{Style.RESET_ALL}"
            if active
            else f"{Fore.RED}INACTIVE{Style.RESET_ALL}"
        )
        print(
            f"\n{Back.YELLOW}{Fore.BLACK}--- {category.upper()} [{status}{Back.YELLOW}{Fore.BLACK}] ---{Style.RESET_ALL}"
        )

        # Collect rows
        rows: list[dict[str, str]] = []
        for app in apps:
            rows.append(
                {
                    "name": app["name"],
                    "link": app.get("link", ""),
                    "payout": app.get("app_details", {})
                    .get("earnings", {})
                    .get("min_payout", "-"),
                    "layer": app.get("compose_layer", "-"),
                    "reason": app.get("removal_reason", ""),
                }
            )

        # Column widths (data-driven)
        w_name = max((len(r["name"]) for r in rows), default=4)
        w_name = max(w_name, 4)
        w_link = max((len(r["link"]) for r in rows), default=4)
        w_link = max(w_link, 4)
        w_layer = max((len(r["layer"]) for r in rows), default=5)
        w_layer = max(w_layer, 5)
        w_payout = max((len(r["payout"]) for r in rows), default=6)
        w_payout = max(w_payout, 6)

        # Can all four columns fit on one line?
        #   2 (indent) + name + 2 + link + 2 + layer + 2 + payout
        full_width = 2 + w_name + 2 + w_link + 2 + w_layer + 2 + w_payout
        compact = full_width > term_width

        if not compact:
            # -- Wide mode: single-line rows --
            header = (
                f"  {Fore.CYAN}{'Name':<{w_name}}  {'Link':<{w_link}}  "
                f"{'Layer':<{w_layer}}  {'Payout':<{w_payout}}{Style.RESET_ALL}"
            )
            separator = (
                f"  {'-' * w_name}  {'-' * w_link}  {'-' * w_layer}  {'-' * w_payout}"
            )
            print(header)
            print(separator)

            for row in rows:
                print(
                    f"  {Fore.GREEN}{row['name']:<{w_name}}{Style.RESET_ALL}  "
                    f"{Fore.CYAN}{row['link']:<{w_link}}{Style.RESET_ALL}  "
                    f"{row['layer']:<{w_layer}}  {row['payout']}"
                )
                if row["reason"]:
                    print(f"    {Fore.YELLOW}>> {row['reason']}{Style.RESET_ALL}")
        else:
            # -- Compact mode: name/layer/payout line + link on its own line --
            header = (
                f"  {Fore.CYAN}{'Name':<{w_name}}  "
                f"{'Layer':<{w_layer}}  {'Payout':<{w_payout}}{Style.RESET_ALL}"
            )
            separator = f"  {'-' * w_name}  {'-' * w_layer}  {'-' * w_payout}"
            print(header)
            print(separator)

            for row in rows:
                print(
                    f"  {Fore.GREEN}{row['name']:<{w_name}}{Style.RESET_ALL}  "
                    f"{row['layer']:<{w_layer}}  {row['payout']}"
                )
                if row["link"]:
                    print(f"    {Fore.CYAN}-> {row['link']}{Style.RESET_ALL}")
                if row["reason"]:
                    print(f"    {Fore.YELLOW}>> {row['reason']}{Style.RESET_ALL}")

        print()


def _manage_categories(app_config: dict[str, Any], app_config_path: str | None) -> None:
    """Interactive submenu to toggle category active/inactive status."""
    all_cats = get_all_app_categories(app_config)
    if not all_cats:
        print(f"{Fore.YELLOW}No categories found.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.CYAN}=== Manage Category Status ==={Style.RESET_ALL}")
    for idx, cat in enumerate(all_cats, 1):
        active = is_category_active(app_config, cat)
        badge = (
            f"{Fore.GREEN}ACTIVE{Style.RESET_ALL}"
            if active
            else f"{Fore.RED}INACTIVE{Style.RESET_ALL}"
        )
        count = len(get_category_entries(app_config, cat))
        print(f"  {idx}. {cat} [{badge}] ({count} apps)")

    print(
        f"\n  {Fore.CYAN}b{Style.RESET_ALL} Back  |  {Fore.CYAN}q{Style.RESET_ALL} Quit"
    )
    choice = input("Select: ").strip().lower()

    if choice in ("b", "0", ""):
        return
    if choice == "q":
        raise SystemExit(0)

    try:
        choice_num = int(choice)
    except ValueError:
        print(f"{Fore.YELLOW}Invalid input.{Style.RESET_ALL}")
        return

    if not 1 <= choice_num <= len(all_cats):
        print(f"{Fore.YELLOW}Invalid selection.{Style.RESET_ALL}")
        return

    cat_key = all_cats[choice_num - 1]
    old_status = app_config[cat_key]["active"]
    new_status = not old_status
    app_config[cat_key]["active"] = new_status

    new_badge = (
        f"{Fore.GREEN}ACTIVE{Style.RESET_ALL}"
        if new_status
        else f"{Fore.RED}INACTIVE{Style.RESET_ALL}"
    )
    print(f"\n{cat_key} is now [{new_badge}]")

    if app_config_path:
        write_json(app_config, app_config_path)
        logger.info("Saved category status change: %s → active=%s", cat_key, new_status)
        print(f"{Fore.GREEN}Saved to {app_config_path}{Style.RESET_ALL}")
    else:
        logger.warning("No app_config_path provided — change not persisted")


def fn_app_catalog(
    app_config: dict[str, Any], app_config_path: str | None = None
) -> bool:
    """Display the app catalog and handle sub-actions.

    Returns True if the caller should reload and re-display (e.g. after a
    category toggle), False to return to the parent menu.
    """
    try:
        logger.info("Displaying app catalog")
        cls()
        just_fix_windows_console()
        sys.stdout.reconfigure(encoding="utf-8")

        _display_catalog(app_config)

        print("Info: Use CTRL+Click to open links or copy them")
        print()
        print(
            f"  {Fore.CYAN}m{Style.RESET_ALL} Manage categories  |  "
            f"{Fore.CYAN}b{Style.RESET_ALL} Back  |  "
            f"{Fore.CYAN}q{Style.RESET_ALL} Quit"
        )
        choice = input("Select: ").strip().lower()
        if choice == "m":
            _manage_categories(app_config, app_config_path)
            return True
        if choice == "q":
            raise SystemExit(0)
        return False  # b or anything else → back
    except Exception as e:
        logger.error(f"An error occurred in fn_app_catalog: {str(e)}")
        raise


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Main function to display the app catalog.

    Arguments:
    app_config_path -- the path to the app configuration file
    m4b_config_path -- the path to the m4b configuration file
    user_config_path -- the path to the user configuration file
    """
    while True:
        app_config = load_json_config(app_config_path)
        if not fn_app_catalog(app_config, app_config_path):
            break


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

    logger.info(f"Starting {script_name} script...")

    try:
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
