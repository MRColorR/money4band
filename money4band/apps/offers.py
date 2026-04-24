from __future__ import annotations

import logging
import os
from typing import Any

from colorama import Fore, Style

from money4band.core.loader import (
    get_all_app_categories,
    get_category_entries,
    load_json_config,
)
from money4band.core.offers_store import read_offers_dir

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_external_offers(offers_path: str) -> list[dict[str, Any]]:
    """Load external (non-app) referral offers.

    *offers_path* may be either the ``config/offers.d/`` directory
    (current layout) or the legacy ``config/referral-offers.json`` file
    (auto-migrated on first access when its sibling m4b-config triggers
    the migration path). When a monolithic JSON file is passed and no
    ``offers.d/`` sibling exists yet, its ``offers[]`` array is read
    directly — this keeps ad-hoc/test callers working.
    """
    if os.path.isdir(offers_path):
        return read_offers_dir(offers_path)
    parent = os.path.dirname(offers_path) or "."
    sibling_dir = os.path.join(parent, "offers.d")
    if os.path.isdir(sibling_dir):
        return read_offers_dir(sibling_dir)
    if os.path.isfile(offers_path):
        # Legacy monolithic JSON — read directly as a last resort.
        try:
            data = load_json_config(offers_path)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to read monolithic offers file: %s", offers_path)
            return []
        entries = data.get("offers") if isinstance(data, dict) else None
        return [e for e in entries if isinstance(e, dict)] if entries else []
    logger.warning("Offers directory not found: %s", offers_path)
    return []


def _app_offers_from_config(app_config_path: str) -> list[dict[str, Any]]:
    """Derive referral offers from the catalog — single source of truth.

    Each supported app with a non-empty ``referrals`` pool becomes an
    offer entry with ``m4b_app=True``.  Earnings metadata is pulled from
    ``app_details`` when available.
    """
    if not os.path.isfile(app_config_path):
        return []
    try:
        app_config = load_json_config(app_config_path)
    except Exception:  # noqa: BLE001
        logger.error("Failed to load app config for offers: %s", app_config_path)
        return []

    offers: list[dict[str, Any]] = []
    for cat in get_all_app_categories(app_config):
        if cat == "deprecated":
            continue  # skip deprecated apps in offers
        for entry in get_category_entries(app_config, cat):
            referrals = entry.get("referrals") or []
            link = (
                referrals[0].get("url")
                if referrals and isinstance(referrals[0], dict)
                else None
            )
            if not link:
                continue
            details = entry.get("app_details", {})
            earnings = details.get("earnings", {})
            layer = entry.get("compose_layer", "")

            # Determine category from layer
            if layer in ("residential", "universal"):
                cat_label = "bandwidth"
            else:
                cat_label = "compute"

            payout_methods = earnings.get("payout_methods", [])
            bonus_parts: list[str] = []
            model = earnings.get("model", "")
            if model:
                bonus_parts.append(model)
            if payout_methods:
                cleaned = [
                    m
                    for m in payout_methods
                    if m.lower() not in ("undocumented", "unknown", "n/a", "none")
                ]
                if cleaned:
                    bonus_parts.append(", ".join(cleaned))
            bonus = " — ".join(bonus_parts) if bonus_parts else "Earn per GB shared"

            ip = details.get("ip_policy", {})
            notes_parts: list[str] = []
            if ip.get("residential") and not ip.get("datacenter"):
                notes_parts.append("Residential IP required")
            elif ip.get("datacenter"):
                notes_parts.append("Works on VPS/datacenter")

            offers.append(
                {
                    "name": details.get("official_name", entry.get("name", "?")),
                    "url": link,
                    "bonus": bonus,
                    "category": cat_label,
                    "m4b_app": True,
                    "notes": "; ".join(notes_parts) if notes_parts else None,
                }
            )
    return offers


def load_all_offers(
    app_config_path: str,
    offers_path: str,
) -> list[dict[str, Any]]:
    """Merge M4B app offers (from the catalog) with external offers.

    App offers appear first, followed by external offers.  This is the
    single entry-point for ``m4b offers`` and the dashboard Offers tab.
    """
    app_offers = _app_offers_from_config(app_config_path)
    external = load_external_offers(offers_path)
    return app_offers + external


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


def display_offers(
    offers_path: str,
    category_filter: str | None = None,
    *,
    app_config_path: str | None = None,
) -> None:
    """Print referral offers table to stdout.

    When *app_config_path* is provided, M4B app reflinks are derived
    from the catalog (single source of truth) and merged with
    external offers from *offers_path*.

    *category_filter* can be ``'bandwidth'``, ``'compute'``, ``'vpn'``,
    ``'proxy'``, ``'affiliate'``, ``'crypto-exchange'``, ``'survey'``,
    or any custom category string.
    """
    if app_config_path:
        offers = load_all_offers(app_config_path, offers_path)
    else:
        offers = load_external_offers(offers_path)

    if not offers:
        print(f"{Fore.YELLOW}No referral offers found.{Style.RESET_ALL}")
        return

    if category_filter:
        offers = [
            o
            for o in offers
            if o.get("category", "").lower() == category_filter.lower()
        ]
        if not offers:
            print(
                f"{Fore.YELLOW}No offers in category '{category_filter}'.{Style.RESET_ALL}"
            )
            return

    print(f"\n{Fore.CYAN}--- Referral & Passive Income Offers ---{Style.RESET_ALL}")
    print(f"  {'Name':<20} {'Category':<16} {'Bonus':<35} {'Source':<6} {'Notes'}")
    print(f"  {'-' * 20} {'-' * 16} {'-' * 35} {'-' * 6} {'-' * 20}")

    for o in offers:
        name = o.get("name", "?")
        cat = o.get("category", "other")
        bonus = o.get("bonus", "")[:35]
        source = f"{Fore.GREEN}M4B{Style.RESET_ALL}" if o.get("m4b_app") else "ext"
        notes = o.get("notes") or ""
        url = o.get("url")
        stub = "" if url else f" {Fore.YELLOW}[STUB]{Style.RESET_ALL}"
        print(f"  {name:<20} {cat:<16} {bonus:<35} {source:<6} {notes}{stub}")
        if url:
            print(f"    {Fore.BLUE}{url}{Style.RESET_ALL}")

    # Summary with category breakdown
    categories = sorted({o.get("category", "other") for o in offers})
    m4b_count = sum(1 for o in offers if o.get("m4b_app"))
    ext_count = len(offers) - m4b_count
    print(
        f"\n  {Fore.CYAN}{len(offers)} offer(s) listed{Style.RESET_ALL}"
        f" ({m4b_count} M4B apps, {ext_count} external)"
    )
    print(f"  Categories: {', '.join(categories)}")
    print(
        f"  {Fore.YELLOW}App reflinks come from the catalog (single source of truth){Style.RESET_ALL}"
    )
    print(
        f"  {Fore.YELLOW}Add external offers in config/offers.d/ (one JSON per offer){Style.RESET_ALL}\n"
    )
