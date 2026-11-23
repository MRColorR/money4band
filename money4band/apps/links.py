"""Public provider links shared by setup, catalog and documentation views."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse


def extract_referral_code(url: str) -> str | None:
    """Read the short manual code used by existing catalog signup URLs."""
    try:
        codes = parse_qs(urlparse(url).query).get("code", [])
    except ValueError:
        return None
    return codes[0] if codes and len(codes[0]) <= 10 else None


def app_referral_code(entry: dict[str, Any]) -> str | None:
    """Prefer an explicit manual code, including referrals without a URL."""
    referrals = entry.get("referrals") or []
    if isinstance(referrals, list) and referrals and isinstance(referrals[0], dict):
        code = referrals[0].get("code")
        if isinstance(code, str) and code.strip():
            return code.strip()
    return extract_referral_code(primary_app_link(entry))


def app_link_text(entry: dict[str, Any]) -> str:
    """Show the public link and any code a user can enter manually."""
    link = primary_app_link(entry)
    code = app_referral_code(entry)
    return f"{link} (code: {code})" if code else link


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
