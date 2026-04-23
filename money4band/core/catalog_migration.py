"""Generic catalog v1 → v2 migration (monolithic → per-file layout).

Idempotent. Safe to call on every load — it detects whether migration is
needed and no-ops otherwise. The first call on a legacy repo:

1. Backs up the monolithic ``config/app-config.json`` to
   ``config/app-config.json.v1.bak`` (once — never overwritten).
2. Splits each entry into ``config/catalog/<category>/<NAME>.json``.
3. Replaces ``config/app-config.json`` with the v2 envelope
   (``app_config_version`` + ``catalog_sources`` + ``categories.active``).

The migration is intentionally offline-only: no network, no user prompts,
no re-encryption. User credentials live in ``user-config.json`` and are
untouched. See also :mod:`scripts.migrate_catalog_v1_to_v2` — a thin CLI
wrapper around :func:`migrate_catalog_file`.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from money4band.core.catalog_store import (
    is_envelope,
    is_legacy_monolithic,
    split_monolithic,
    write_envelope,
)

logger = logging.getLogger(__name__)

LEGACY_BACKUP_SUFFIX = ".v1.bak"


def migrate_catalog_file(config_path: str | Path) -> bool:
    """Migrate *config_path* from monolithic v1 to per-file v2 layout.

    Returns ``True`` if the file was migrated, ``False`` if it was already
    in the new layout (or the file does not exist).
    """
    path = Path(config_path)
    if not path.is_file():
        return False

    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Cannot read %s for catalog migration: %s", path, exc)
        return False

    if not isinstance(payload, dict):
        return False

    # Already migrated — nothing to do.
    if is_envelope(payload) and not is_legacy_monolithic(payload):
        return False

    if not is_legacy_monolithic(payload):
        # Neither envelope nor monolithic — unknown/empty file; skip.
        return False

    # Keep a one-time backup of the pre-migration monolithic file.
    backup = path.with_suffix(path.suffix + LEGACY_BACKUP_SUFFIX)
    if not backup.exists():
        shutil.copy2(str(path), str(backup))
        logger.info("Backed up legacy app-config to %s", backup)

    envelope, count = split_monolithic(payload, path)
    write_envelope(envelope, path)
    logger.info(
        "Migrated %d catalog entries from monolithic to per-file layout under %s",
        count,
        path.parent / "catalog",
    )
    return True


__all__ = ["migrate_catalog_file", "LEGACY_BACKUP_SUFFIX"]
