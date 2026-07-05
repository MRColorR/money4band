"""Migrate a monolithic ``referral-offers.json`` into ``offers.d/``.

Idempotent. On first run this splits the legacy file into one JSON per
offer under ``config/offers.d/<SLUG>.json`` and renames the legacy file
to ``referral-offers.json.v1.bak``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from money4band.core.offers_store import offers_root, write_offer

logger = logging.getLogger(__name__)

LEGACY_OFFERS_FILENAME = "referral-offers.json"
LEGACY_BACKUP_SUFFIX = ".v1.bak"


def migrate_offers_file(config_path: str | Path) -> bool:
    """Split legacy ``referral-offers.json`` sibling to *config_path*.

    *config_path* is the anchor used to locate the ``config/`` directory
    - typically ``config/m4b-config.json``. Returns ``True`` if a
    migration happened, ``False`` otherwise.
    """
    anchor = Path(config_path)
    legacy = anchor.parent / LEGACY_OFFERS_FILENAME
    if not legacy.is_file():
        return False

    try:
        with open(legacy, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Cannot read legacy offers file %s: %s", legacy, exc)
        return False

    if not isinstance(payload, dict):
        return False
    offers = payload.get("offers")
    if not isinstance(offers, list):
        return False

    root = offers_root(anchor)
    count = 0
    for offer in offers:
        if not isinstance(offer, dict) or not offer.get("name"):
            continue
        write_offer(offer, root)
        count += 1

    backup = legacy.with_suffix(legacy.suffix + LEGACY_BACKUP_SUFFIX)
    if backup.exists():
        try:
            legacy.unlink()
        except OSError:
            pass
    else:
        try:
            legacy.rename(backup)
        except OSError as exc:
            logger.warning("Could not rename %s -> %s: %s", legacy, backup, exc)

    logger.info("Migrated %d offers from %s to %s", count, legacy.name, root)
    return True


__all__ = ["migrate_offers_file", "LEGACY_OFFERS_FILENAME", "LEGACY_BACKUP_SUFFIX"]
