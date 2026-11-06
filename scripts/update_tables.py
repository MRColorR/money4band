#!/usr/bin/env python3
"""Regenerate the README and app directory from the core catalog and snapshot."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from money4band.core.loader import load_app_config_with_overlays  # noqa: E402
from money4band.readme_generator import (  # noqa: E402
    merge_documentation_catalog,
    update_apps_md,
    update_readme,
)

SNAPSHOT = ROOT / "docs" / "catalog-snapshot.json"
SOURCE_URLS = {
    "community": "https://raw.githubusercontent.com/MRColorR/money4band-community-catalog/main/manifest.json",
    "openpassivehub": "https://raw.githubusercontent.com/MRColorR/openpassivehub-catalog/main/manifest.json",
}


def documentation_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Keep the public fields used by the two tables."""
    name = entry["name"]
    if not re.fullmatch(r"[A-Z][A-Z0-9_]+", name):
        raise ValueError(f"Invalid catalog app identifier: {name!r}")
    details = entry.get("app_details") or {}
    display = {
        key: details[key]
        for key in ("official_name", "official_url", "status")
        if key in details
    }
    for section, keys in (
        ("ip_policy", ("residential", "datacenter")),
        ("device_limits", ("max_devices_per_account", "max_devices_per_ip")),
        ("earnings", ("payout_methods", "avg_monthly_residential_usd")),
    ):
        values = details.get(section) or {}
        display[section] = {key: values[key] for key in keys if key in values}
    projected: dict[str, Any] = {"name": name, "app_details": display}
    referrals = entry.get("referrals") or []
    if referrals:
        projected["referrals"] = [{"url": referrals[0]["url"]}]
    return projected


def refresh_snapshot() -> None:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    with httpx.Client(timeout=20) as client:
        for source, url in SOURCE_URLS.items():
            response = client.get(url)
            response.raise_for_status()
            manifest = response.json()
            snapshot[source] = {
                category: [
                    documentation_entry(entry)
                    for entry in manifest.get(category, {}).get("entries", [])
                ]
                for category in ("supported", "newcomers", "deprecated")
            }
    SNAPSHOT.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check without writing")
    parser.add_argument(
        "--refresh", action="store_true", help="Fetch the two public catalog manifests"
    )
    parser.add_argument(
        "--core-only", action="store_true", help="Exclude external catalog entries"
    )
    args = parser.parse_args()
    if args.refresh and (args.check or args.core_only):
        parser.error("--refresh requires a full table update")
    if args.refresh:
        refresh_snapshot()

    core = load_app_config_with_overlays(
        str(ROOT / "config" / "m4b-config.json"),
        apps_d_dir="",
        user_config_path="",
    )
    combined = merge_documentation_catalog(core, SNAPSHOT, core_only=args.core_only)
    readme_ok = update_readme(combined, ROOT / "README.md", check=args.check)
    details_ok = update_apps_md(combined, ROOT / "docs" / "APPS.md", check=args.check)
    if not (readme_ok and details_ok):
        print("App tables are stale or missing. Run python scripts/update_tables.py.")
        return 1
    print("App tables are up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
