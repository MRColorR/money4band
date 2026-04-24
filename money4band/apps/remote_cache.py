"""On-disk cache for ``RemoteSource`` (phase-8.5).

A minimal ETag-aware cache sitting next to the local catalog tree::

    config/catalog/community/
        .etag                      ← ETag of last successful 200 response
        .fetched_at                ← ISO-8601 timestamp (diagnostic only)
        <category>/<NAME>.json     ← one bundle per remote entry

The cache is a plain directory with the same per-file shape as
``config/catalog/<category>/<NAME>.json`` so :class:`LocalSource`-style
readers (``read_entries_dir``) work on it unchanged.

``.etag`` / ``.fetched_at`` live at the cache root (hidden) and are
never mistaken for entries by the category readers.

This module has no httpx dependency — it only deals with on-disk state.
Fetch logic lives in :class:`money4band.apps.sources.RemoteSource`.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from money4band.core.catalog_store import CATEGORIES

logger = logging.getLogger(__name__)

ETAG_FILENAME = ".etag"
FETCHED_AT_FILENAME = ".fetched_at"


def read_etag(cache_dir: Path) -> str | None:
    """Return the persisted ETag for *cache_dir*, or ``None``."""
    path = cache_dir / ETAG_FILENAME
    if not path.is_file():
        return None
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.debug("Cannot read ETag cache %s: %s", path, exc)
        return None
    return value or None


def write_etag(cache_dir: Path, etag: str) -> None:
    """Persist *etag* for *cache_dir*. Empty value clears the file."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / ETAG_FILENAME
    path.write_text(etag.strip(), encoding="utf-8")


def touch_fetched_at(cache_dir: Path) -> None:
    """Record the current UTC time as the last-fetch timestamp."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / FETCHED_AT_FILENAME).write_text(
        datetime.now(UTC).isoformat(timespec="seconds"),
        encoding="utf-8",
    )


def replace_entries(
    cache_dir: Path, entries_by_category: dict[str, list[dict[str, Any]]]
) -> int:
    """Wipe category subdirs and rewrite per-file bundles atomically.

    Only the canonical ``CATEGORIES`` subdirectories are wiped — any
    stray file under the cache root (e.g. ``.etag``, user notes) stays.
    Returns the total number of bundles written.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for cat in CATEGORIES:
        cat_dir = cache_dir / cat
        if cat_dir.exists():
            shutil.rmtree(cat_dir)
        entries = entries_by_category.get(cat) or []
        if not entries:
            continue
        cat_dir.mkdir(parents=True, exist_ok=True)
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                continue
            filename = f"{name.upper()}.json"
            (cat_dir / filename).write_text(
                json.dumps(entry, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            total += 1
    return total


def split_manifest(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Normalise a fetched manifest into ``{category: [entries...]}``.

    Accepts two shapes so upstream catalogs have flexibility:

    1. **Aggregated** (preferred) — the same envelope shape the loader
       returns in-memory: ``{supported: {entries: [...]}, ...}`` or the
       legacy flat ``{supported: [...], ...}``.
    2. **Flat list** — ``{entries: [{...category: "...", ...}, ...]}``.

    Unknown / missing categories are silently ignored; entries without a
    ``name`` are dropped.
    """
    out: dict[str, list[dict[str, Any]]] = {cat: [] for cat in CATEGORIES}
    if not isinstance(payload, dict):
        return out

    # Shape 2: flat list with per-entry "category"
    flat = payload.get("entries")
    if isinstance(flat, list):
        for entry in flat:
            if not isinstance(entry, dict):
                continue
            cat = entry.get("category")
            if isinstance(cat, str) and cat in CATEGORIES and entry.get("name"):
                out[cat].append(entry)
        return out

    # Shape 1: category-keyed envelope (both wrapped and bare forms)
    for cat in CATEGORIES:
        block = payload.get(cat)
        if isinstance(block, dict):
            items = block.get("entries") or []
        elif isinstance(block, list):
            items = block
        else:
            items = []
        for entry in items:
            if isinstance(entry, dict) and entry.get("name"):
                out[cat].append(entry)
    return out


__all__ = [
    "ETAG_FILENAME",
    "FETCHED_AT_FILENAME",
    "read_etag",
    "replace_entries",
    "split_manifest",
    "touch_fetched_at",
    "write_etag",
]
