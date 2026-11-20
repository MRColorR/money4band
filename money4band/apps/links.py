"""Public provider links shared by setup, catalog and documentation views."""

from __future__ import annotations

from typing import Any


def primary_app_link(entry: dict[str, Any]) -> str:
    """Prefer the first referral, then the official site, then the dashboard."""
    referrals = entry.get("referrals") or []
    referral = (
        referrals[0].get("url")
        if isinstance(referrals, list) and referrals and isinstance(referrals[0], dict)
        else None
    )
    details = entry.get("app_details") or {}
    website = details.get("official_url") if isinstance(details, dict) else None
    for value in (referral, website, entry.get("dashboard")):
        if isinstance(value, str) and value.startswith(("https://", "http://")):
            return value
    return ""
