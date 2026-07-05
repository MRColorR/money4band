from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
from typing import Any

from colorama import Back, Fore, Style, just_fix_windows_console

from money4band.core.loader import (
    get_all_app_categories,
    get_category_entries,
    is_category_active,
    load_app_config_with_overlays,
)
from money4band.ui.cls import cls

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
            referrals = app.get("referrals") or []
            primary_link = (
                referrals[0].get("url", "")
                if referrals and isinstance(referrals[0], dict)
                else ""
            )
            rows.append(
                {
                    "name": app["name"],
                    "link": primary_link,
                    "payout": app.get("app_details", {})
                    .get("earnings", {})
                    .get("min_payout", "-"),
                    "layer": app.get("profile", "-"),
                    "reason": app.get("additional_details", ""),
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

    print(f"\n  {Fore.CYAN}b{Style.RESET_ALL} Back")
    choice = input("Select: ").strip().lower()

    if choice in ("b", "0", ""):
        return

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
        # Write only the envelope's active flag - per-file bundles are
        # not rewritten here.
        from money4band.core.catalog_store import set_category_active

        set_category_active(app_config_path, cat_key, new_status)
        logger.info("Saved category status change: %s -> active=%s", cat_key, new_status)
        print(f"{Fore.GREEN}Saved to {app_config_path}{Style.RESET_ALL}")
    else:
        logger.warning("No app_config_path provided - change not persisted")


def fn_app_catalog(
    app_config: dict[str, Any],
    app_config_path: str | None = None,
    m4b_config_path: str | None = None,
) -> bool:
    """Display the app catalog and handle sub-actions.

    Returns True if the caller should reload and re-display (e.g. after a
    category toggle or a sources change), False to return to the parent menu.
    """
    try:
        logger.info("Displaying app catalog")
        cls()
        just_fix_windows_console()

        _display_catalog(app_config)

        print("Info: Use CTRL+Click to open links or copy them")
        print()
        has_sources = m4b_config_path is not None
        if has_sources:
            print(
                f"  {Fore.CYAN}m{Style.RESET_ALL} Manage categories  |  "
                f"{Fore.CYAN}c{Style.RESET_ALL} Catalog sources  |  "
                f"{Fore.CYAN}b{Style.RESET_ALL} Back"
            )
        else:
            print(
                f"  {Fore.CYAN}m{Style.RESET_ALL} Manage categories  |  "
                f"{Fore.CYAN}b{Style.RESET_ALL} Back"
            )
        choice = input("Select: ").strip().lower()
        if choice == "m":
            _manage_categories(app_config, app_config_path)
            return True
        if choice == "c" and has_sources:
            _manage_sources(m4b_config_path)
            return True
        return False  # b or anything else -> back
    except Exception as e:
        logger.error(f"An error occurred in fn_app_catalog: {str(e)}")
        raise


def _manage_sources(m4b_config_path: str) -> None:
    """Interactive submenu for catalog source management (TUI parity)."""
    from money4band.apps import catalog_manager as cm

    while True:
        cls()
        print(f"{Fore.CYAN}--- Catalog Sources ---{Style.RESET_ALL}\n")
        try:
            status = cm.source_status(m4b_config_path)
        except Exception as exc:  # noqa: BLE001
            print(f"{Fore.RED}Error: {exc}{Style.RESET_ALL}")
            input("\nPress Enter to continue...")
            return

        if not status:
            print("  (no sources declared)")
        else:
            for info in status:
                name = info.get("name", "?")
                stype = info.get("type", "?")
                enabled = "enabled" if info.get("enabled") else "disabled"
                badge = Fore.GREEN if info.get("enabled") else Fore.YELLOW
                print(f"  {name} [{stype}] {badge}{enabled}{Style.RESET_ALL}")
                if info.get("url"):
                    print(f"    url:      {info['url']}")
                if info.get("path"):
                    print(f"    path:     {info['path']}")
                if info.get("cached_entries") is not None:
                    print(f"    entries:  {info['cached_entries']}")
                if info.get("fetched_at"):
                    print(f"    fetched:  {cm.humanize_fetched_at(info['fetched_at'])}")

        print()
        print(
            f"  {Fore.CYAN}a{Style.RESET_ALL} Add  |  "
            f"{Fore.CYAN}r{Style.RESET_ALL} Remove  |  "
            f"{Fore.CYAN}t{Style.RESET_ALL} Toggle  |  "
            f"{Fore.CYAN}f{Style.RESET_ALL} Refresh  |  "
            f"{Fore.CYAN}b{Style.RESET_ALL} Back"
        )
        choice = input("Select: ").strip().lower()

        if choice in ("b", ""):
            return
        if choice == "a":
            _prompt_add_source(m4b_config_path)
        elif choice == "r":
            name = input("Name to remove: ").strip()
            if name:
                ok = cm.remove_source(m4b_config_path, name)
                print(
                    f"{Fore.GREEN}Removed{Style.RESET_ALL}"
                    if ok
                    else f"{Fore.YELLOW}Not found{Style.RESET_ALL}"
                )
                input("\nPress Enter to continue...")
        elif choice == "t":
            name = input("Name to toggle: ").strip()
            if name:
                current = {s["name"]: s for s in cm.list_sources(m4b_config_path)}
                if name not in current:
                    print(f"{Fore.YELLOW}Not found{Style.RESET_ALL}")
                else:
                    new_val = not current[name].get("enabled", True)
                    cm.set_source_enabled(m4b_config_path, name, new_val)
                    print(
                        f"{Fore.GREEN}{'Enabled' if new_val else 'Disabled'} "
                        f"{name}{Style.RESET_ALL}"
                    )
                input("\nPress Enter to continue...")
        elif choice == "f":
            name = input("Name (blank = all remotes): ").strip() or None
            try:
                results = cm.refresh_source(m4b_config_path, name)
            except cm.CatalogSourceError as exc:
                print(f"{Fore.RED}{exc}{Style.RESET_ALL}")
                input("\nPress Enter to continue...")
                continue
            for r in results:
                status = r.get("status", "?")
                color = {
                    "refreshed": Fore.GREEN,
                    "skipped": Fore.YELLOW,
                    "disabled": Fore.YELLOW,
                    "error": Fore.RED,
                }.get(status, "")
                extra = ""
                if status == "refreshed":
                    extra = f"{r.get('cached_entries', 0)} entries"
                elif status == "error":
                    extra = str(r.get("error") or "")
                print(
                    f"  {color}{status.upper():<10}{Style.RESET_ALL}"
                    f"{r.get('name', '?')}: {extra}"
                )
            input("\nPress Enter to continue...")


def _prompt_add_source(m4b_config_path: str) -> None:
    """Collect fields for a new catalog source interactively."""
    from money4band.apps import catalog_manager as cm

    name = input("Name: ").strip()
    if not name:
        return
    stype = input("Type [local/remote] (default: remote): ").strip().lower() or "remote"
    if stype not in cm.SOURCE_TYPES:
        print(f"{Fore.RED}Invalid type{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return

    url: str | None = None
    path: str | None = None
    if stype == "remote":
        url = input("URL: ").strip() or None
    else:
        path = input("Path (relative to m4b-config.json): ").strip() or None
    default_source = input("Default source (default: community): ").strip() or None
    enabled_raw = input("Enabled? (Y/n): ").strip().lower()
    enabled = enabled_raw != "n"

    try:
        cm.add_source(
            m4b_config_path,
            name=name,
            type=stype,
            url=url,
            path=path,
            default_source=default_source,
            enabled=enabled,
        )
        print(f"{Fore.GREEN}Added source {name}{Style.RESET_ALL}")
    except cm.CatalogSourceError as exc:
        print(f"{Fore.RED}{exc}{Style.RESET_ALL}")
    input("\nPress Enter to continue...")


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Main function to display the app catalog.

    Arguments:
    app_config_path -- the path to the app configuration file
    m4b_config_path -- the path to the m4b configuration file
    user_config_path -- the path to the user configuration file
    """
    while True:
        app_config = load_app_config_with_overlays(app_config_path)
        if not fn_app_catalog(app_config, app_config_path, m4b_config_path):
            break


if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the module standalone.")
    parser.add_argument(
        "--app-config",
        type=str,
        required=True,
        help="Path to catalog JSON file (m4b-config.json envelope)",
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
