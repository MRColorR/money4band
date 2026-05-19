from __future__ import annotations

"""Per-app detail card and app listing from app_details metadata."""

import logging
import sys
from typing import Any

from colorama import Fore, Style, just_fix_windows_console

from money4band.core.loader import (
    get_all_app_categories,
    get_category_entries,
    is_category_active,
)

logger = logging.getLogger(__name__)


def _ensure_utf8_stdout() -> None:
    """Reconfigure stdout to UTF-8 so Unicode symbols render on Windows."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_app(
    app_config: dict[str, Any], name: str
) -> tuple[dict[str, Any] | None, str]:
    """Find an app entry by name (case-insensitive). Returns (entry, category) or (None, "")."""
    target = name.strip().upper()
    for cat in get_all_app_categories(app_config):
        for entry in get_category_entries(app_config, cat):
            if entry.get("name", "").upper() == target:
                return entry, cat
    return None, ""


def _bool_icon(val: Any) -> str:
    if val is True:
        return f"{Fore.GREEN}\u2713{Style.RESET_ALL}"
    if val is False:
        return f"{Fore.RED}\u2717{Style.RESET_ALL}"
    return f"{Fore.YELLOW}?{Style.RESET_ALL}"


def _category_badge(app_config: dict[str, Any], category: str) -> str:
    if category == "deprecated":
        return f"{Fore.RED}DEPRECATED{Style.RESET_ALL}"
    if category == "newcomers":
        return f"{Fore.YELLOW}CANDIDATE{Style.RESET_ALL}"
    if is_category_active(app_config, category):
        return f"{Fore.GREEN}ACTIVE{Style.RESET_ALL}"
    return f"{Fore.RED}INACTIVE{Style.RESET_ALL}"


# ---------------------------------------------------------------------------
# Detail card
# ---------------------------------------------------------------------------


def show_app_detail(app_config: dict[str, Any], app_name: str) -> bool:
    """Print a rich detail card for a single app. Returns True if found."""
    just_fix_windows_console()
    _ensure_utf8_stdout()

    entry, category = _find_app(app_config, app_name)
    if entry is None:
        print(f"{Fore.RED}App '{app_name}' not found.{Style.RESET_ALL}")
        _suggest_similar(app_config, app_name)
        return False

    details: dict[str, Any] = entry.get("app_details", {})
    name = details.get("official_name", entry.get("name", app_name))
    badge = _category_badge(app_config, category)

    w = 24
    print(f"\n{Fore.CYAN}{'=' * 54}")
    print(f"  {name}  [{badge}{Fore.CYAN}]")
    print(f"{'=' * 54}{Style.RESET_ALL}")

    # Identity
    publisher = details.get("publisher", "—")
    referrals = entry.get("referrals") or []
    primary_referral = (
        referrals[0].get("url", "")
        if referrals and isinstance(referrals[0], dict)
        else ""
    )
    url = details.get("official_url", primary_referral or "—")
    print(f"\n{Fore.CYAN}Identity{Style.RESET_ALL}")
    print(f"  {'Publisher:':<{w}} {publisher}")
    print(f"  {'Website:':<{w}} {url}")

    tos = details.get("tos_url")
    if tos:
        print(f"  {'Terms of Service:':<{w}} {tos}")

    if primary_referral:
        print(f"  {'Referral link:':<{w}} {primary_referral}")

    # IP Policy
    ip_policy = details.get("ip_policy", {})
    if ip_policy:
        print(f"\n{Fore.CYAN}IP Policy{Style.RESET_ALL}")
        for key in ("residential", "datacenter", "vps", "vpn", "proxy", "mobile"):
            val = ip_policy.get(key)
            if val is not None:
                print(f"  {key.capitalize() + ':':<{w}} {_bool_icon(val)}")
        geo = ip_policy.get("geo_restrictions")
        if geo and geo != "none known":
            print(f"  {'Geo restrictions:':<{w}} {geo}")
        notes = ip_policy.get("quality_notes")
        if notes:
            print(f"  {'Notes:':<{w}} {notes}")

    # Device Limits
    limits = details.get("device_limits", {})
    if limits:
        print(f"\n{Fore.CYAN}Device Limits{Style.RESET_ALL}")
        for field, label in [
            ("max_devices_per_account", "Per account"),
            ("max_devices_per_ip", "Per IP"),
            ("max_ips_per_account", "IPs per account"),
        ]:
            val = limits.get(field)
            if val is not None:
                print(f"  {label + ':':<{w}} {val}")
        notes = limits.get("notes")
        if notes:
            print(f"  {'Notes:':<{w}} {notes}")

    # Earnings
    earnings = details.get("earnings", {})
    if earnings:
        print(f"\n{Fore.CYAN}Earnings{Style.RESET_ALL}")
        model = earnings.get("model", "—")
        print(f"  {'Model:':<{w}} {model}")
        payout = earnings.get("payout_methods", [])
        if payout:
            print(f"  {'Payout methods:':<{w}} {', '.join(payout)}")
        min_p = earnings.get("min_payout")
        if min_p:
            print(f"  {'Min payout:':<{w}} {min_p}")
        res = earnings.get("avg_monthly_residential_usd")
        if res:
            print(f"  {'Avg/month (resi):':<{w}} ${res}")
        dc = earnings.get("avg_monthly_datacenter_usd")
        if dc:
            print(f"  {'Avg/month (DC):':<{w}} ${dc}")

    # Docker
    docker = details.get("docker", {})
    if docker:
        print(f"\n{Fore.CYAN}Docker Image{Style.RESET_ALL}")
        img = entry.get("compose_config", {}).get("image", "—")
        print(f"  {'Image:':<{w}} {img}")
        print(f"  {'Official:':<{w}} {_bool_icon(docker.get('image_official'))}")
        print(f"  {'Maintained:':<{w}} {_bool_icon(docker.get('image_maintained'))}")
        upd = docker.get("last_update")
        if upd:
            print(f"  {'Last update:':<{w}} {upd}")

    # Install limit
    install_limit = entry.get("install_limit", -1)
    limit_str = "unlimited" if install_limit == -1 else str(install_limit)
    print(f"\n{Fore.CYAN}Configuration{Style.RESET_ALL}")
    print(f"  {'Install limit:':<{w}} {limit_str}")
    layer = entry.get("profile", "—")
    print(f"  {'Compose layer:':<{w}} {layer}")

    # Warnings
    warnings = details.get("warnings", [])
    if warnings:
        print(f"\n{Fore.YELLOW}Warnings{Style.RESET_ALL}")
        for warn in warnings:
            print(f"  {Fore.YELLOW}! {warn}{Style.RESET_ALL}")

    # Confidence & verification
    confidence = details.get("confidence")
    verified = details.get("last_verified")
    if confidence or verified:
        print(f"\n{Fore.CYAN}Data Quality{Style.RESET_ALL}")
        if confidence:
            print(f"  {'Confidence:':<{w}} {confidence}")
        if verified:
            print(f"  {'Last verified:':<{w}} {verified}")

    print()
    return True


def _suggest_similar(app_config: dict[str, Any], name: str) -> None:
    """Suggest apps with similar names."""
    target = name.strip().upper()
    matches = []
    for cat in get_all_app_categories(app_config):
        for entry in get_category_entries(app_config, cat):
            app_name = entry.get("name", "").upper()
            if target in app_name or app_name in target:
                matches.append(entry.get("name", ""))
    if matches:
        print(f"Did you mean: {', '.join(matches)}?")


# ---------------------------------------------------------------------------
# App listing
# ---------------------------------------------------------------------------


def list_apps(app_config: dict[str, Any], category_filter: str | None = None) -> None:
    """Print a compact app listing with key details from app_details."""
    just_fix_windows_console()
    _ensure_utf8_stdout()

    print(
        f"\n{Fore.CYAN}{'Name':<20} {'Status':<14} {'Resi':>4} {'DC':>4} {'Payout':<22} {'Limit':>7}{Style.RESET_ALL}"
    )
    print(f"{'-' * 73}")

    for cat in get_all_app_categories(app_config):
        if category_filter and category_filter.lower() not in cat.lower():
            continue
        for entry in get_category_entries(app_config, cat):
            details = entry.get("app_details", {})
            name = details.get("official_name", entry.get("name", "?"))
            ip = details.get("ip_policy", {})
            earnings = details.get("earnings", {})
            payout = ", ".join(earnings.get("payout_methods", [])) or "—"
            resi = _bool_icon(ip.get("residential"))
            dc = _bool_icon(ip.get("datacenter"))

            install_limit = entry.get("install_limit", -1)
            limit_str = "\u221e" if install_limit == -1 else str(install_limit)

            # Status color
            if cat == "deprecated":
                status = f"{Fore.RED}deprecated{Style.RESET_ALL}"
            elif cat == "newcomers":
                status = f"{Fore.YELLOW}candidate{Style.RESET_ALL}"
            else:
                status = f"{Fore.GREEN}active{Style.RESET_ALL}"

            print(
                f"  {name:<18} {status:<23} {resi:>13} {dc:>13} {payout:<22} {limit_str:>5}"
            )

            # Show removal reason for deprecated apps
            additional = entry.get("additional_details", "")
            if additional and cat == "deprecated":
                print(f"    {Fore.YELLOW}↳ {additional}{Style.RESET_ALL}")

    print()
