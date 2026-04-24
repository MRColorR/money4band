"""Generic catalog migrations (monolithic → per-file → folded).

All migrations are idempotent and safe to call on every load.

* :func:`migrate_catalog_file` converts a monolithic
  ``config/app-config.json`` into the per-file layout
  ``config/catalog/<category>/<NAME>.json`` and rewrites the source file
  as a v2 envelope.
* :func:`fold_legacy_envelope_into_m4b` takes that standalone envelope
  file and folds it under the ``catalog`` key of ``m4b-config.json``,
  renaming the legacy file with a ``.v1.bak`` suffix.

Both migrations are offline-only: no network, no user prompts, no
re-encryption. User credentials live in ``user-config.json`` and are
untouched. See also :mod:`scripts.migrate_catalog_v1_to_v2` — a thin
CLI wrapper around :func:`migrate_catalog_file`.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from money4band.core.catalog_store import (
    is_envelope,
    is_folded,
    is_legacy_monolithic,
    split_monolithic,
    write_envelope,
)

logger = logging.getLogger(__name__)

LEGACY_BACKUP_SUFFIX = ".v1.bak"
LEGACY_APP_CONFIG_FILENAME = "app-config.json"


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


__all__ = [
    "fold_legacy_envelope_into_m4b",
    "migrate_catalog_file",
    "LEGACY_BACKUP_SUFFIX",
    "LEGACY_APP_CONFIG_FILENAME",
]


def fold_legacy_envelope_into_m4b(config_path: str | Path) -> bool:
    """Fold a sibling legacy ``app-config.json`` into ``m4b-config.json``.

    When *config_path* points to ``config/m4b-config.json`` and a
    legacy envelope file ``config/app-config.json`` still exists, this:

    1. Migrates the legacy file to per-file layout if still monolithic.
    2. Splices the resulting envelope under ``m4b-config.json → catalog``
       (leaves any existing folded envelope untouched). Creates
       ``m4b-config.json`` with an otherwise-empty payload when it
       doesn't exist yet — this handles fresh test fixtures and users
       who only have the legacy file.
    3. Renames the legacy file to ``app-config.json.v1.bak`` (or
       removes it silently if the backup already exists).

    Returns ``True`` when a fold happened, ``False`` otherwise. Safe to
    call on every startup — no-ops when there is nothing to do.
    """
    m4b_path = Path(config_path)
    # Only fold when we were invoked against m4b-config.json itself; any
    # other path is treated as a direct envelope file and skipped.
    if m4b_path.name != "m4b-config.json":
        return False

    legacy = m4b_path.parent / LEGACY_APP_CONFIG_FILENAME
    if not legacy.is_file():
        return False

    # Normalise the legacy file first (monolithic → envelope).
    migrate_catalog_file(legacy)

    try:
        with open(legacy, encoding="utf-8") as f:
            legacy_payload = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Cannot read legacy envelope %s: %s", legacy, exc)
        return False

    if not is_envelope(legacy_payload) or is_folded(legacy_payload):
        # Unrecognised content — leave the file alone.
        return False

    m4b_payload: dict = {}
    if m4b_path.is_file():
        try:
            with open(m4b_path, encoding="utf-8") as f:
                m4b_payload = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Cannot read m4b-config for folding: %s", exc)
            return False
        if not isinstance(m4b_payload, dict):
            return False

    if is_folded(m4b_payload):
        # Already folded — just retire the legacy file.
        _retire_legacy_file(legacy)
        return False

    m4b_payload["catalog"] = legacy_payload
    write_envelope(m4b_payload, m4b_path)
    _retire_legacy_file(legacy)
    logger.info("Folded legacy %s into %s (key: catalog)", legacy.name, m4b_path.name)
    return True


def _retire_legacy_file(legacy: Path) -> None:
    """Move *legacy* aside as ``<name>.v1.bak`` (or delete if backup exists)."""
    backup = legacy.with_suffix(legacy.suffix + LEGACY_BACKUP_SUFFIX)
    if backup.exists():
        try:
            legacy.unlink()
        except OSError:
            pass
        return
    try:
        legacy.rename(backup)
    except OSError as exc:
        logger.warning("Could not rename %s -> %s: %s", legacy, backup, exc)
