"""CLI presenter for ``m4b catalog``.

Thin wrapper around :mod:`money4band.apps.catalog_manager`. The manager
owns all mutation logic; this module is responsible for argparse
dispatch and colourised terminal output.
"""

from __future__ import annotations

import argparse

from colorama import Fore, Style, just_fix_windows_console

from money4band.apps import catalog_manager as cm
from money4band.apps.catalog_manager import CatalogSourceError


def handle_catalog_action(
    action: str | None,
    args: argparse.Namespace,
    m4b_config_path: str,
) -> int:
    """Dispatch one of the ``catalog`` subcommands. Returns an exit code."""
    just_fix_windows_console()
    if action in (None, "list"):
        return _cmd_list(m4b_config_path)
    if action == "status":
        return _cmd_status(m4b_config_path)
    if action == "add":
        return _cmd_add(args, m4b_config_path)
    if action == "remove":
        return _cmd_remove(args, m4b_config_path)
    if action == "enable":
        return _cmd_toggle(args, m4b_config_path, enabled=True)
    if action == "disable":
        return _cmd_toggle(args, m4b_config_path, enabled=False)
    if action == "refresh":
        return _cmd_refresh(args, m4b_config_path)
    if action == "category":
        return _cmd_category(args, m4b_config_path)
    print(f"{Fore.RED}Unknown action: {action}{Style.RESET_ALL}")
    return 2


# ---------------------------------------------------------------------------
# list / status
# ---------------------------------------------------------------------------


def _cmd_list(m4b_config_path: str) -> int:
    sources = cm.list_sources(m4b_config_path)
    if not sources:
        print(f"{Fore.YELLOW}No catalog sources configured.{Style.RESET_ALL}")
        return 0

    print(f"{Fore.CYAN}--- Catalog Sources ---{Style.RESET_ALL}")
    print(f"{'Name':<16} {'Type':<8} {'Enabled':<8} Default    Target")
    print("-" * 70)
    for s in sources:
        name = str(s.get("name", ""))
        stype = str(s.get("type", ""))
        enabled = "yes" if s.get("enabled", True) else "no"
        default = str(s.get("default_source") or "")
        target = s.get("url") or s.get("path") or ""
        en_col = Fore.GREEN if enabled == "yes" else Fore.YELLOW
        print(
            f"{name:<16} {stype:<8} "
            f"{en_col}{enabled:<8}{Style.RESET_ALL} "
            f"{default:<10} {target}"
        )
    return 0


def _cmd_status(m4b_config_path: str) -> int:
    rows = cm.source_status(m4b_config_path)
    if not rows:
        print(f"{Fore.YELLOW}No catalog sources configured.{Style.RESET_ALL}")
        return 0

    print(f"{Fore.CYAN}--- Catalog Source Status ---{Style.RESET_ALL}")
    for row in rows:
        name = row.get("name")
        enabled = row.get("enabled")
        flag = (
            f"{Fore.GREEN}enabled{Style.RESET_ALL}"
            if enabled
            else f"{Fore.YELLOW}disabled{Style.RESET_ALL}"
        )
        print(f"\n  {Fore.CYAN}{name}{Style.RESET_ALL} [{row.get('type')}] {flag}")
        if row.get("url"):
            print(f"    url:      {row['url']}")
        if row.get("path"):
            print(f"    path:     {row['path']}")
        if row.get("resolved_path"):
            print(f"    resolved: {row['resolved_path']}")
        if row.get("cache_dir"):
            print(f"    cache:    {row['cache_dir']}")
        if "etag" in row:
            print(f"    etag:     {row.get('etag') or '(none)'}")
        if "fetched_at" in row:
            human = cm.humanize_fetched_at(row.get("fetched_at"))
            print(f"    fetched:  {row.get('fetched_at') or 'never'} ({human})")
        if "cached_entries" in row:
            print(f"    entries:  {row['cached_entries']}")
    print()

    cats = cm.list_categories(m4b_config_path)
    print(f"{Fore.CYAN}--- Categories ---{Style.RESET_ALL}")
    for cat, meta in cats.items():
        active = meta.get("active")
        col = Fore.GREEN if active else Fore.YELLOW
        status = "active" if active else "inactive"
        print(f"  {cat:<12} {col}{status}{Style.RESET_ALL}")
    return 0


# ---------------------------------------------------------------------------
# add / remove / toggle
# ---------------------------------------------------------------------------


def _cmd_add(args: argparse.Namespace, m4b_config_path: str) -> int:
    try:
        decl = cm.add_source(
            m4b_config_path,
            name=args.name,
            type=args.type,
            url=getattr(args, "url", None),
            path=getattr(args, "path", None),
            default_source=getattr(args, "default_source", None),
            enabled=not getattr(args, "disabled", False),
            cache_path=getattr(args, "cache_path", None),
            timeout=getattr(args, "timeout", None),
        )
    except CatalogSourceError as exc:
        print(f"{Fore.RED}Error: {exc}{Style.RESET_ALL}")
        return 1
    print(
        f"{Fore.GREEN}Added source{Style.RESET_ALL} "
        f"{Fore.CYAN}{decl['name']}{Style.RESET_ALL} "
        f"({decl['type']})"
    )
    return 0


def _cmd_remove(args: argparse.Namespace, m4b_config_path: str) -> int:
    if cm.remove_source(m4b_config_path, args.name):
        print(f"{Fore.GREEN}Removed source{Style.RESET_ALL} {args.name}")
        return 0
    print(f"{Fore.RED}Source {args.name!r} not found{Style.RESET_ALL}")
    return 1


def _cmd_toggle(
    args: argparse.Namespace, m4b_config_path: str, *, enabled: bool
) -> int:
    if cm.set_source_enabled(m4b_config_path, args.name, enabled):
        verb = "Enabled" if enabled else "Disabled"
        print(f"{Fore.GREEN}{verb}{Style.RESET_ALL} source {args.name}")
        return 0
    print(f"{Fore.RED}Source {args.name!r} not found{Style.RESET_ALL}")
    return 1


# ---------------------------------------------------------------------------
# refresh
# ---------------------------------------------------------------------------


def _cmd_refresh(args: argparse.Namespace, m4b_config_path: str) -> int:
    try:
        results = cm.refresh_source(
            m4b_config_path, getattr(args, "name", None) or None
        )
    except CatalogSourceError as exc:
        print(f"{Fore.RED}Error: {exc}{Style.RESET_ALL}")
        return 1
    if not results:
        print(f"{Fore.YELLOW}No sources to refresh.{Style.RESET_ALL}")
        return 0
    exit_code = 0
    for row in results:
        name = row["name"]
        status = row["status"]
        if status == "refreshed":
            print(
                f"  {Fore.GREEN}OK{Style.RESET_ALL}       {name}: "
                f"{row.get('cached_entries', 0)} entries cached"
            )
        elif status == "skipped":
            print(
                f"  {Fore.YELLOW}SKIP{Style.RESET_ALL}     {name}: not a remote source"
            )
        elif status == "disabled":
            print(
                f"  {Fore.YELLOW}SKIP{Style.RESET_ALL}     {name}: source is disabled"
            )
        elif status == "error":
            print(
                f"  {Fore.RED}ERROR{Style.RESET_ALL}    {name}: "
                f"{row.get('error', 'unknown error')}"
            )
            exit_code = 1
        else:
            print(f"           {name}: {status}")
    return exit_code


# ---------------------------------------------------------------------------
# category enable/disable
# ---------------------------------------------------------------------------


def _cmd_category(args: argparse.Namespace, m4b_config_path: str) -> int:
    sub = getattr(args, "category_action", None)
    if sub == "list":
        cats = cm.list_categories(m4b_config_path)
        print(f"{Fore.CYAN}--- Categories ---{Style.RESET_ALL}")
        for cat, meta in cats.items():
            col = Fore.GREEN if meta["active"] else Fore.YELLOW
            label = "active" if meta["active"] else "inactive"
            print(f"  {cat:<12} {col}{label}{Style.RESET_ALL}")
        return 0
    if sub in ("enable", "disable"):
        name = getattr(args, "category_name", None)
        if not name:
            print(f"{Fore.RED}Category name required.{Style.RESET_ALL}")
            return 2
        try:
            cm.set_category(m4b_config_path, name, sub == "enable")
        except CatalogSourceError as exc:
            print(f"{Fore.RED}Error: {exc}{Style.RESET_ALL}")
            return 1
        verb = "Enabled" if sub == "enable" else "Disabled"
        print(f"{Fore.GREEN}{verb}{Style.RESET_ALL} category {name}")
        return 0
    print(
        f"{Fore.RED}Unknown category action: {sub}. "
        f"Use list | enable | disable.{Style.RESET_ALL}"
    )
    return 2
