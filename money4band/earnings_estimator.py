from __future__ import annotations

import logging
import re
from typing import Any

from colorama import Fore, Style

logger = logging.getLogger(__name__)

_RANGE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$")


def parse_earnings_range(value: Any) -> tuple[float, float] | None:
    """Parse an earnings range string like ``'1-9'`` into ``(1.0, 9.0)``.

    Returns ``None`` for null, ``'unknown'``, ``'undocumented'``, or
    unparseable values.
    """
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("unknown", "undocumented", "none", ""):
        return None
    m = _RANGE_RE.match(s)
    if m:
        return float(m.group(1)), float(m.group(2))
    # Try a single number
    try:
        v = float(s)
        return v, v
    except ValueError:
        return None


def get_app_earnings(
    app_config: dict[str, Any],
    ip_type: str = "residential",
) -> list[dict[str, Any]]:
    """Extract per-app earnings estimates for active apps.

    *ip_type* is ``'residential'`` or ``'datacenter'``.

    Returns a list of dicts with keys:
    ``name``, ``model``, ``range_low``, ``range_high``, ``min_payout``.
    Apps with unknown earnings are included with ``range_low=0, range_high=0``.
    """
    field = f"avg_monthly_{ip_type}_usd"
    results: list[dict[str, Any]] = []

    categories = [
        k for k, v in app_config.items()
        if isinstance(v, dict) and v.get("active") and "entries" in v
    ]

    for cat in categories:
        for entry in app_config[cat].get("entries", []):
            details = entry.get("app_details", {})
            earnings = details.get("earnings", {})
            rng = parse_earnings_range(earnings.get(field))
            results.append({
                "name": entry.get("name", "?"),
                "model": earnings.get("model", "unknown"),
                "range_low": rng[0] if rng else 0.0,
                "range_high": rng[1] if rng else 0.0,
                "min_payout": earnings.get("min_payout", "unknown"),
            })

    return results


def display_earnings_summary(
    app_config: dict[str, Any],
    ip_type: str = "residential",
) -> None:
    """Print a formatted earnings estimation table to stdout."""
    rows = get_app_earnings(app_config, ip_type=ip_type)
    if not rows:
        print(f"{Fore.YELLOW}No active apps found.{Style.RESET_ALL}")
        return

    label = ip_type.capitalize()
    print(f"\n{Fore.CYAN}--- Estimated Monthly Earnings ({label} IP) ---{Style.RESET_ALL}")
    print(f"  {'App':<20} {'Model':<30} {'Est. $/month':<18} {'Min Payout'}")
    print(f"  {'-'*20} {'-'*30} {'-'*18} {'-'*18}")

    total_low = 0.0
    total_high = 0.0

    for r in sorted(rows, key=lambda x: x["range_high"], reverse=True):
        low, high = r["range_low"], r["range_high"]
        total_low += low
        total_high += high
        if low == 0 and high == 0:
            est = f"{Fore.YELLOW}{'unknown':<18}{Style.RESET_ALL}"
        elif low == high:
            est = f"${low:.2f}"
        else:
            est = f"${low:.2f} - ${high:.2f}"
        print(f"  {r['name']:<20} {r['model']:<30} {est:<18} {r['min_payout']}")

    print(f"  {'-'*20} {'-'*30} {'-'*18}")
    if total_high > 0:
        print(
            f"  {'TOTAL':<20} {'':<30} "
            f"{Fore.GREEN}${total_low:.2f} - ${total_high:.2f}{Style.RESET_ALL}"
        )
    else:
        print(f"  {'TOTAL':<20} {'':<30} {Fore.YELLOW}No data{Style.RESET_ALL}")
    print()
