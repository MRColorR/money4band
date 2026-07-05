"""Offers store - read/write the per-file offers layout.

Layout::

    config/offers.d/<SLUG>.json

Each bundle is a single offer object::

    {
        "name": "NordVPN",
        "url": null,
        "bonus": "Up to 73% off + 3 months free",
        "category": "vpn",
        "notes": "Placeholder; referral link not configured"
    }

``SLUG`` is the upper-cased kebab-case form of ``name`` (e.g. ``NORDVPN``,
``SURFSHARK``). Per-file storage mirrors the catalog/apps.d layout and
lets community contributors drop one offer per PR.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

OFFERS_DIRNAME = "offers.d"


def slugify_offer_name(name: str) -> str:
    """Return the on-disk filename stem for an offer."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug.upper() or "UNNAMED"


def offers_root(config_path: str | Path) -> Path:
    """Return the ``offers.d`` directory sibling of *config_path*."""
    return Path(config_path).parent / OFFERS_DIRNAME


def read_offers_dir(root: str | Path) -> list[dict[str, Any]]:
    """Read all per-file offer bundles sorted by filename."""
    root_path = Path(root)
    if not root_path.is_dir():
        return []
    offers: list[dict[str, Any]] = []
    for path in sorted(root_path.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Skipping unreadable offer bundle %s: %s", path, exc)
            continue
        if not isinstance(data, dict):
            logger.warning("Skipping non-object offer bundle: %s", path)
            continue
        if not data.get("name"):
            logger.warning("Skipping offer bundle missing 'name': %s", path)
            continue
        offers.append(data)
    return offers


def write_offer(offer: dict[str, Any], root: str | Path) -> Path:
    """Write *offer* to ``<root>/<SLUG>.json``."""
    name = offer.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("Offer must have a non-empty 'name' field")
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    dest = root_path / f"{slugify_offer_name(name)}.json"
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(offer, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return dest


__all__ = [
    "OFFERS_DIRNAME",
    "offers_root",
    "read_offers_dir",
    "slugify_offer_name",
    "write_offer",
]
