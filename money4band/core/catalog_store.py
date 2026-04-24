"""Catalog store — read/write the per-file catalog layout.

Layout (v2.1):

    config/m4b-config.json      ← project config + catalog envelope
                                  (``"catalog": {app_config_version,
                                   catalog_sources, categories}``)
    config/catalog/
        supported/<NAME>.json   ← one CatalogEntry per file
        newcomers/<NAME>.json
        deprecated/<NAME>.json

Envelope shape (lives under ``m4b-config.json → catalog``)::

    {
        "app_config_version": 2.0,
        "catalog_sources": [
            {"type": "local", "path": "catalog",
             "default_source": "builtin", "enabled": true}
        ],
        "categories": {
            "supported":  {"active": true},
            "newcomers":  {"active": false},
            "deprecated": {"active": false}
        }
    }

The loader aggregates per-file bundles back into the in-memory shape
``{<category>: {"active": bool, "entries": [...]}}`` so every consumer
keeps working unchanged.

For backward compatibility the store still understands a standalone
envelope file and the older monolithic format. Both paths funnel
through the same loader.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


CATALOG_DIRNAME = "catalog"
CATEGORIES = ("supported", "newcomers", "deprecated")
ADDONS_DIRNAME = "addons"


def catalog_root(config_path: str | Path) -> Path:
    """Return the catalog directory sibling of *config_path*."""
    return Path(config_path).parent / CATALOG_DIRNAME


def _entry_filename(name: str) -> str:
    """Return the per-file bundle filename for an entry name."""
    return f"{name.upper()}.json"


def is_envelope(payload: dict[str, Any]) -> bool:
    """Return ``True`` if *payload* looks like a v2 envelope (post-migration).

    An envelope carries ``categories`` (active flags only) and does *not*
    carry per-category ``entries`` at the top level.

    Also returns ``True`` when *payload* is an m4b-config file that
    contains a folded-in ``catalog`` envelope.
    """
    if isinstance(payload.get("catalog"), dict):
        return is_envelope(payload["catalog"])
    if "categories" not in payload:
        return False
    # If any legacy top-level category dict carries "entries", it's still
    # monolithic — not an envelope yet.
    for cat in CATEGORIES:
        cat_val = payload.get(cat)
        if isinstance(cat_val, dict) and "entries" in cat_val:
            return False
    return True


def extract_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the envelope subtree — unwraps ``payload["catalog"]`` if present.

    When the envelope is folded into ``m4b-config.json`` it lives under
    the ``catalog`` key. For legacy standalone envelope files the payload
    *is* the envelope.
    """
    inner = payload.get("catalog")
    if isinstance(inner, dict) and "categories" in inner:
        return inner
    return payload


def is_folded(payload: dict[str, Any]) -> bool:
    """Return ``True`` when *payload* carries a folded ``catalog`` envelope."""
    inner = payload.get("catalog")
    return isinstance(inner, dict) and "categories" in inner


def is_legacy_monolithic(payload: dict[str, Any]) -> bool:
    """Return ``True`` if *payload* is the pre-8.3b monolithic format."""
    for cat in CATEGORIES:
        cat_val = payload.get(cat)
        if isinstance(cat_val, dict) and "entries" in cat_val:
            return True
    return False


def read_entries_dir(root: Path, category: str) -> list[dict[str, Any]]:
    """Read all per-file bundles in ``root/<category>/`` sorted by name."""
    cat_dir = root / category
    if not cat_dir.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(cat_dir.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Skipping unreadable catalog bundle %s: %s", path, exc)
            continue
        if not isinstance(data, dict):
            logger.warning("Skipping non-object catalog bundle: %s", path)
            continue
        entries.append(data)
    return entries


def read_addons_dir(root: Path) -> list[dict[str, Any]]:
    """Read all addon bundles in ``root/addons/`` sorted by name.

    Addons are parallel to categories: they attach to a parent app via
    ``parent_id`` and are merged into the parent's compose_config when
    the parent is enabled AND the user opted in (``service_enabled``).
    """
    addons_dir = root / ADDONS_DIRNAME
    if not addons_dir.is_dir():
        return []
    addons: list[dict[str, Any]] = []
    for path in sorted(addons_dir.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Skipping unreadable addon bundle %s: %s", path, exc)
            continue
        if not isinstance(data, dict):
            logger.warning("Skipping non-object addon bundle: %s", path)
            continue
        if not data.get("parent_id"):
            logger.warning(
                "Skipping addon bundle missing 'parent_id': %s", path
            )
            continue
        addons.append(data)
    return addons


def aggregate(envelope: dict[str, Any], config_path: str | Path) -> dict[str, Any]:
    """Expand an envelope + per-file bundles into the historical in-memory shape.

    Accepts either a raw envelope or an m4b-config payload with a folded
    ``catalog`` key; the inner envelope is used transparently.

    Output matches the pre-8.3b monolithic structure so every existing
    consumer (catalog, docker, API, tests) keeps working unchanged.
    """
    envelope = extract_envelope(envelope)
    result: dict[str, Any] = {
        "app_config_version": envelope.get("app_config_version", 2.0),
    }
    # Preserve catalog_sources / any other envelope keys for API exposure.
    for key, val in envelope.items():
        if key in ("app_config_version", "categories"):
            continue
        result[key] = val

    root = catalog_root(config_path)
    cats = envelope.get("categories") or {}
    for cat in CATEGORIES:
        meta = cats.get(cat) if isinstance(cats, dict) else None
        active = bool(meta.get("active", False)) if isinstance(meta, dict) else False
        result[cat] = {
            "active": active,
            "entries": read_entries_dir(root, cat),
        }
    result["addons"] = read_addons_dir(root)
    return result


def write_envelope(envelope: dict[str, Any], config_path: str | Path) -> None:
    """Persist the envelope back to disk (pretty-printed, UTF-8, trailing \\n)."""
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(envelope, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_entry(
    entry: dict[str, Any],
    config_path: str | Path,
    category: str,
) -> Path:
    """Write a single catalog entry to ``catalog/<category>/<NAME>.json``."""
    if category not in CATEGORIES:
        raise ValueError(f"Unknown catalog category: {category}")
    name = entry.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("Catalog entry must have a non-empty 'name' field")

    root = catalog_root(config_path)
    cat_dir = root / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    dest = cat_dir / _entry_filename(name)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return dest


def delete_entry(config_path: str | Path, category: str, name: str) -> bool:
    """Remove ``catalog/<category>/<NAME>.json``. Returns ``True`` if deleted."""
    if category not in CATEGORIES:
        raise ValueError(f"Unknown catalog category: {category}")
    path = catalog_root(config_path) / category / _entry_filename(name)
    if path.is_file():
        path.unlink()
        return True
    return False


def move_entry(
    config_path: str | Path,
    name: str,
    from_category: str,
    to_category: str,
    *,
    updates: dict[str, Any] | None = None,
) -> Path:
    """Move a bundle between categories, optionally patching fields in-place.

    Reads the source file, applies *updates* (shallow merge at top level),
    writes the destination file, then deletes the source. Fails loudly if
    the source does not exist.
    """
    if from_category not in CATEGORIES or to_category not in CATEGORIES:
        raise ValueError(f"Unknown category ({from_category} → {to_category})")
    src = catalog_root(config_path) / from_category / _entry_filename(name)
    if not src.is_file():
        raise FileNotFoundError(f"Catalog entry not found: {src}")
    with open(src, encoding="utf-8") as f:
        entry = json.load(f)
    if updates:
        entry.update(updates)
    dest = write_entry(entry, config_path, to_category)
    if src.resolve() != dest.resolve():
        src.unlink()
    return dest


def set_category_active(config_path: str | Path, category: str, active: bool) -> None:
    """Flip the ``active`` flag for *category* inside the envelope.

    Supports both the folded layout (``m4b-config.json → catalog``) and a
    standalone envelope file; writes back in whatever shape was read.
    """
    if category not in CATEGORIES:
        raise ValueError(f"Unknown catalog category: {category}")
    path = Path(config_path)
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    envelope = payload["catalog"] if is_folded(payload) else payload
    cats = envelope.setdefault("categories", {})
    cat_meta = cats.setdefault(category, {})
    cat_meta["active"] = bool(active)
    write_envelope(payload, path)


def default_envelope() -> dict[str, Any]:
    """Return a fresh envelope with default catalog sources + category flags."""
    return {
        "app_config_version": 2.0,
        "catalog_sources": [
            {
                "type": "local",
                "name": "builtin",
                "path": CATALOG_DIRNAME,
                "default_source": "builtin",
                "enabled": True,
            },
            {
                "type": "remote",
                "name": "community",
                "url": "https://raw.githubusercontent.com/MRColorR/money4band-community-catalog/main/manifest.json",
                "default_source": "community",
                "enabled": False,
                "cache_path": "catalog/community",
                "timeout": 5.0,
            }
        ],
        "categories": {
            "supported": {"active": True},
            "newcomers": {"active": False},
            "deprecated": {"active": False},
        },
    }


def split_monolithic(
    payload: dict[str, Any], config_path: str | Path
) -> tuple[dict[str, Any], int]:
    """Split a monolithic payload into envelope + per-file bundles on disk.

    Writes bundles to ``catalog/<category>/<NAME>.json`` next to
    *config_path* and returns ``(envelope, entry_count)`` without writing
    the envelope file (caller decides when to persist).
    """
    envelope = default_envelope()
    envelope["app_config_version"] = payload.get("app_config_version", 2.0)

    # Preserve any non-category top-level keys (e.g. legacy catalog_sources).
    for key, val in payload.items():
        if key in ("app_config_version", "categories", *CATEGORIES):
            continue
        envelope[key] = val

    count = 0
    for cat in CATEGORIES:
        cat_val = payload.get(cat)
        if not isinstance(cat_val, dict):
            continue
        active = bool(cat_val.get("active", envelope["categories"][cat]["active"]))
        envelope["categories"][cat] = {"active": active}
        for entry in cat_val.get("entries", []) or []:
            if not isinstance(entry, dict) or not entry.get("name"):
                continue
            write_entry(entry, config_path, cat)
            count += 1
    return envelope, count


def ensure_catalog_dirs(config_path: str | Path) -> None:
    """Create the three category directories under ``catalog/`` if missing."""
    root = catalog_root(config_path)
    for cat in CATEGORIES:
        (root / cat).mkdir(parents=True, exist_ok=True)


__all__ = [
    "CATALOG_DIRNAME",
    "CATEGORIES",
    "aggregate",
    "catalog_root",
    "default_envelope",
    "delete_entry",
    "ensure_catalog_dirs",
    "extract_envelope",
    "is_envelope",
    "is_folded",
    "is_legacy_monolithic",
    "move_entry",
    "read_entries_dir",
    "set_category_active",
    "split_monolithic",
    "write_entry",
    "write_envelope",
]


# Re-export relative path for tests/tools that need to know the dir name.
def _catalog_relpath_from_config(config_path: str | Path) -> str:
    return os.path.join(os.path.dirname(str(config_path)), CATALOG_DIRNAME)
