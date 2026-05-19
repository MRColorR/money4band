from __future__ import annotations

"""Auto-generate app tables in README.md and docs/APPS.md from m4b-config.json."""

import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from money4band.core.loader import get_all_app_categories, get_category_entries

logger = logging.getLogger(__name__)

# Marker comments used to delimit auto-generated sections
_BEGIN_MARKER = "<!-- BEGIN:APPS_TABLE -->"
_END_MARKER = "<!-- END:APPS_TABLE -->"

# Category → display order (lower = first)
_CATEGORY_ORDER = {"supported": 0, "newcomers": 1, "deprecated": 2}

# Status → emoji mapping (lifecycle state inside its source)
_STATUS_EMOJI: dict[str, str] = {
    "active": "\U0001f7e2",  # 🟢
    "unstable": "\U0001f7e1",  # 🟡
    "candidate": "\U0001f51c",  # 🔜
    "deprecated": "\U0001f534",  # 🔴
    "discontinued": "\U0001f534",  # 🔴
}

# Per-source row indicator used in the unified README table.
# Category overrides source for the "needs attention" buckets.
_SOURCE_EMOJI: dict[str, str] = {
    "core": "\U0001f7e2",  # 🟢 — ships in core, works out-of-box
    "community": "\U0001f4dc",  # 📜 — needs `m4b catalog sources enable community`
    "openpassivehub": "\U0001f331",  # 🌱 — newcomer, no Docker yet
}


def _row_indicator(source: str, category: str) -> str:
    """Single emoji shown in the README ``Type`` column for an entry."""
    if category == "deprecated":
        return "\U0001f534"  # 🔴
    if category == "newcomers":
        return "\U0001f331"  # 🌱
    return _SOURCE_EMOJI.get(source, "—")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _bool_md(val: Any) -> str:
    """Convert a boolean-ish value to a markdown icon."""
    if val is True:
        return "\u2705"  # ✅
    if val is False:
        return "\u274c"  # ❌
    return "\u2014"  # —


def _effective_status(category: str, details: dict[str, Any]) -> str:
    """Derive display status from category + app_details.status."""
    if category == "deprecated":
        return details.get("status", "deprecated")
    if category == "newcomers":
        return "candidate"
    return details.get("status", "active")


def _extract_referral_code(url: str) -> str | None:
    """Extract a short referral code from a URL query string (code= param only, max 10 chars)."""
    try:
        qs = parse_qs(urlparse(url).query)
        codes = qs.get("code", [])
        if codes and len(codes[0]) <= 10:
            return codes[0]
    except Exception:  # noqa: BLE001
        pass
    return None


def _format_devices(val: Any) -> str:
    """Format a device limit value for markdown."""
    if val is None or str(val).lower() in ("undocumented", "unknown", "n/a"):
        return "\u2014"
    if isinstance(val, int):
        if val == -1:
            return "\u221e"  # \u221e
        return str(val)
    s = str(val).lower()
    if s == "unlimited":
        return "Unlimited"
    return str(val)


def _format_payout(methods: list[str] | None) -> str:
    if not methods:
        return "\u2014"
    cleaned = [
        m
        for m in methods
        if m.lower() not in ("undocumented", "unknown", "n/a", "none")
    ]
    if not cleaned:
        return "\u2014"
    return ", ".join(cleaned)


def _format_earnings(val: str | None) -> str:
    if not val:
        return "\u2014"
    low = val.lower().strip()
    if low in ("n/a", "unknown", "undocumented") or low.startswith("unknown"):
        return "\u2014"
    return f"${val}"


def _collect_apps(app_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect all apps with metadata, sorted by category order then config order.

    Each catalog entry may carry an optional ``_source`` field (set by
    the multi-source merger in ``scripts/update_tables.py``) identifying
    which repo it came from (``"core"``, ``"community"``,
    ``"openpassivehub"``). Entries without it default to ``"core"``.
    """
    apps: list[dict[str, Any]] = []
    for cat in get_all_app_categories(app_config):
        order = _CATEGORY_ORDER.get(cat, 99)
        for entry in get_category_entries(app_config, cat):
            details = entry.get("app_details", {})
            referrals = entry.get("referrals") or []
            primary_link = (
                referrals[0].get("url", "")
                if referrals and isinstance(referrals[0], dict)
                else ""
            )
            source = entry.get("_source", "core")
            apps.append(
                {
                    "entry": entry,
                    "details": details,
                    "category": cat,
                    "order": order,
                    "name": details.get("official_name", entry.get("name", "?")),
                    "link": primary_link,
                    "status": _effective_status(cat, details),
                    "source": source,
                    "indicator": _row_indicator(source, cat),
                }
            )
    apps.sort(key=lambda a: (a["order"], a["name"].lower()))
    return apps


# ---------------------------------------------------------------------------
# README table: compact (App | Residential | VPS/DC | Payout)
# ---------------------------------------------------------------------------


def generate_readme_table(app_config: dict[str, Any]) -> str:
    """Generate the compact markdown table for README.md.

    Includes a ``Type`` column whose emoji is driven by
    :func:`_row_indicator` (🟢 core · 📜 community · 🌱 newcomer · 🔴
    deprecated). When the config only contains core entries the column
    still renders, all rows just show 🟢.
    """
    apps = _collect_apps(app_config)

    lines = [
        "| Type | App | Residential | VPS/DC | Payout |",
        "|:----:|-----|:-----------:|:------:|--------|",
    ]

    for app in apps:
        ip = app["details"].get("ip_policy", {})
        earnings = app["details"].get("earnings", {})
        name = app["name"]
        link = app["link"]

        app_cell = f"[**{name}**]({link})" if link else f"**{name}**"
        resi = _bool_md(ip.get("residential"))
        dc = _bool_md(ip.get("datacenter"))
        payout = _format_payout(earnings.get("payout_methods"))

        lines.append(f"| {app['indicator']} | {app_cell} | {resi} | {dc} | {payout} |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# APPS.md table: full detail
# ---------------------------------------------------------------------------


def generate_apps_md_table(app_config: dict[str, Any]) -> str:
    """Generate the full app-details markdown table for docs/APPS.md."""
    apps = _collect_apps(app_config)

    lines = [
        "| Type | App | Link | M4B Status | Residential | VPS/DC | Devices/Account | Devices/IP | Payout Methods | Est. Monthly (USD) |",
        "|:----:|-----|------|:----------:|:-----------:|:------:|:---------------:|:----------:|----------------|:------------------:|",
    ]

    for app in apps:
        details = app["details"]
        ip = details.get("ip_policy", {})
        earnings = details.get("earnings", {})
        limits = details.get("device_limits", {})
        name = app["name"]
        link = app["link"]

        if link:
            link_cell = f"[Visit]({link})"
            code = _extract_referral_code(link)
            if code:
                link_cell += f" \u00b7 code: `{code}`"
        else:
            link_cell = "\u2014"

        status_emoji = _STATUS_EMOJI.get(app["status"], "\u2014")
        resi = _bool_md(ip.get("residential"))
        dc = _bool_md(ip.get("datacenter"))
        dev_acct = _format_devices(limits.get("max_devices_per_account"))
        dev_ip = _format_devices(limits.get("max_devices_per_ip"))
        payout = _format_payout(earnings.get("payout_methods"))
        est = _format_earnings(earnings.get("avg_monthly_residential_usd"))

        lines.append(
            f"| {app['indicator']} | **{name}** | {link_cell} | {status_emoji} | {resi} | {dc} "
            f"| {dev_acct} | {dev_ip} | {payout} | {est} |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File updaters (marker-based section replacement)
# ---------------------------------------------------------------------------


def _replace_between_markers(text: str, new_content: str) -> str | None:
    """Replace content between BEGIN/END markers. Returns None if markers not found."""
    pattern = re.compile(
        re.escape(_BEGIN_MARKER) + r"\n.*?\n" + re.escape(_END_MARKER),
        re.DOTALL,
    )
    replacement = f"{_BEGIN_MARKER}\n{new_content}\n{_END_MARKER}"
    result, count = pattern.subn(replacement, text)
    if count == 0:
        return None
    return result


def update_readme(app_config: dict[str, Any], readme_path: str | Path) -> bool:
    """Regenerate the apps table in README.md between markers. Returns True on success."""
    path = Path(readme_path)
    if not path.exists():
        logger.error("README not found: %s", path)
        return False

    text = path.read_text(encoding="utf-8")
    table = generate_readme_table(app_config)
    updated = _replace_between_markers(text, table)
    if updated is None:
        logger.warning(
            "Markers %s / %s not found in %s", _BEGIN_MARKER, _END_MARKER, path
        )
        return False

    path.write_text(updated, encoding="utf-8")

    # Update the app count line just above the table
    app_count = len(_collect_apps(app_config))
    updated = path.read_text(encoding="utf-8")
    updated = re.sub(
        r"\*\*\d+\+?\s+apps?\*\*\s+tracked",
        f"**{app_count} apps** tracked",
        updated,
    )
    path.write_text(updated, encoding="utf-8")

    logger.info("README updated: %s (%d apps)", path, app_count)
    return True


def update_apps_md(app_config: dict[str, Any], apps_md_path: str | Path) -> bool:
    """Regenerate the app table in docs/APPS.md between markers. Returns True on success."""
    path = Path(apps_md_path)
    if not path.exists():
        logger.error("APPS.md not found: %s", path)
        return False

    text = path.read_text(encoding="utf-8")
    table = generate_apps_md_table(app_config)
    updated = _replace_between_markers(text, table)
    if updated is None:
        logger.warning(
            "Markers %s / %s not found in %s", _BEGIN_MARKER, _END_MARKER, path
        )
        return False

    path.write_text(updated, encoding="utf-8")
    logger.info("APPS.md updated: %s", path)
    return True
