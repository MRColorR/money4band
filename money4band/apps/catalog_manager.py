"""Catalog-source management — the single API behind the CLI/TUI/REST surfaces.

Every mutation of the ``m4b-config.json → catalog.catalog_sources[]`` list
or ``catalog.categories.<name>.active`` flag goes through the functions
defined here so CLI, API, and TUI behave identically.

Design contract
---------------

The envelope lives under ``m4b-config.json``'s ``catalog`` key::

    {
      "catalog": {
        "app_config_version": 2.0,
        "catalog_sources": [
          {"type": "local",  "name": "builtin",   "path": "catalog",
           "default_source": "builtin",  "enabled": true},
          {"type": "remote", "name": "community", "url":  "https://...",
           "default_source": "community", "enabled": false,
           "cache_path": "catalog/community", "timeout": 5.0}
        ],
        "categories": {
          "supported":  {"active": true},
          "newcomers":  {"active": true},
          "deprecated": {"active": false}
        }
      }
    }

All functions in this module:

- take ``m4b_config_path`` (string or :class:`pathlib.Path`)
- read the folded or standalone envelope transparently via
  :mod:`money4band.core.catalog_store`
- write the envelope back in whatever shape was read
- return structured dicts (never print), so the same call sites can be
  wrapped by a colour CLI formatter, a JSON-serialising router, or a
  TUI menu handler.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from money4band.apps.remote_cache import (
    ETAG_FILENAME,
    FETCHED_AT_FILENAME,
    read_etag,
)
from money4band.apps.sources import (
    LocalSource,
    RemoteSource,
    build_sources,
)
from money4band.core.catalog_store import (
    CATEGORIES,
    is_folded,
    set_category_active,
)

SOURCE_TYPES = ("local", "remote")


# ---------------------------------------------------------------------------
# Low-level envelope I/O
# ---------------------------------------------------------------------------


def _load_payload(m4b_config_path: str | Path) -> dict[str, Any]:
    path = Path(m4b_config_path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_payload(m4b_config_path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(m4b_config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        # Match project convention (core.dumper.write_json uses indent=4).
        json.dump(payload, f, indent=4, ensure_ascii=False)
        f.write("\n")


def _envelope(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a reference to the catalog envelope inside *payload*.

    Mutations to the returned dict will be visible in *payload* (and
    therefore persisted by :func:`_write_payload`).
    """
    return payload["catalog"] if is_folded(payload) else payload


# ---------------------------------------------------------------------------
# Public queries (read-only)
# ---------------------------------------------------------------------------


def list_sources(m4b_config_path: str | Path) -> list[dict[str, Any]]:
    """Return a copy of ``catalog_sources[]`` from the envelope."""
    payload = _load_payload(m4b_config_path)
    env = _envelope(payload)
    raw = env.get("catalog_sources") or []
    return [dict(s) for s in raw if isinstance(s, dict)]


def list_categories(m4b_config_path: str | Path) -> dict[str, dict[str, Any]]:
    """Return the ``categories`` map (``{name: {active: bool}}``)."""
    payload = _load_payload(m4b_config_path)
    env = _envelope(payload)
    cats = env.get("categories") or {}
    out: dict[str, dict[str, Any]] = {}
    for name in CATEGORIES:
        meta = cats.get(name) or {}
        out[name] = {"active": bool(meta.get("active", True))}
    return out


def source_status(m4b_config_path: str | Path) -> list[dict[str, Any]]:
    """Return per-source status enriched with cache metadata.

    Each entry contains the declaration fields (``name``, ``type``,
    ``enabled``, ``url`` or ``path``, ``default_source``) plus cache
    introspection for remote sources: ``cache_dir``, ``etag``,
    ``fetched_at`` (ISO-8601 or None), and ``cached_entries`` (count
    of bundle files under the cache dir across all categories).
    """
    sources_raw = list_sources(m4b_config_path)
    results: list[dict[str, Any]] = []
    # Build objects so we can reuse the source path/cache resolution logic.
    payload = _load_payload(m4b_config_path)
    env = _envelope(payload)
    objects = build_sources(env, m4b_config_path)
    obj_by_name = {obj.name: obj for obj in objects}

    for idx, decl in enumerate(sources_raw):
        # Mirror the fallback used by build_sources so the lookup key lines up.
        name = decl.get("name") or f"{decl.get('type', 'source')}-{idx}"
        info: dict[str, Any] = {
            "name": name,
            "type": decl.get("type"),
            "enabled": bool(decl.get("enabled", True)),
            "default_source": decl.get("default_source"),
        }
        if decl.get("url"):
            info["url"] = decl["url"]
        if decl.get("path"):
            info["path"] = decl["path"]

        obj = obj_by_name.get(name)
        if isinstance(obj, RemoteSource):
            cache_dir = obj._resolve_cache_dir(m4b_config_path)  # noqa: SLF001
            info["cache_dir"] = str(cache_dir)
            info["etag"] = read_etag(cache_dir) if cache_dir.is_dir() else None
            info["fetched_at"] = _read_fetched_at(cache_dir)
            info["cached_entries"] = _count_cached_entries(cache_dir)
        elif isinstance(obj, LocalSource):
            base = obj._resolve_root(m4b_config_path)  # noqa: SLF001
            info["resolved_path"] = str(base)
            info["cached_entries"] = _count_cached_entries(base)
        results.append(info)
    return results


def _read_fetched_at(cache_dir: Path) -> str | None:
    path = cache_dir / FETCHED_AT_FILENAME
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _count_cached_entries(base: Path) -> int:
    if not base.is_dir():
        return 0
    total = 0
    for cat in CATEGORIES:
        cat_dir = base / cat
        if cat_dir.is_dir():
            total += sum(1 for _ in cat_dir.glob("*.json"))
    return total


# ---------------------------------------------------------------------------
# Public mutations
# ---------------------------------------------------------------------------


class CatalogSourceError(ValueError):
    """Raised when a mutation would produce an invalid envelope."""


def add_source(
    m4b_config_path: str | Path,
    *,
    name: str,
    type: str,
    url: str | None = None,
    path: str | None = None,
    default_source: str | None = None,
    enabled: bool = True,
    cache_path: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Append a new source to ``catalog_sources[]``. Returns the stored decl.

    Raises :class:`CatalogSourceError` on invalid input (unknown type,
    duplicate name, missing url/path, etc.).
    """
    name = (name or "").strip()
    if not name:
        raise CatalogSourceError("name is required")
    if type not in SOURCE_TYPES:
        raise CatalogSourceError(f"type must be one of {SOURCE_TYPES}, got {type!r}")
    if type == "remote" and not url:
        raise CatalogSourceError("remote sources require 'url'")
    if type == "local" and not path:
        raise CatalogSourceError("local sources require 'path'")

    payload = _load_payload(m4b_config_path)
    env = _envelope(payload)
    sources = env.setdefault("catalog_sources", [])
    if any(isinstance(s, dict) and s.get("name") == name for s in sources):
        raise CatalogSourceError(f"source {name!r} already exists")

    decl: dict[str, Any] = {
        "type": type,
        "name": name,
        "enabled": bool(enabled),
    }
    if default_source:
        decl["default_source"] = default_source
    else:
        decl["default_source"] = "builtin" if type == "local" else "community"
    if type == "remote":
        decl["url"] = url
        if cache_path:
            decl["cache_path"] = cache_path
        if timeout is not None:
            decl["timeout"] = float(timeout)
    else:
        decl["path"] = path

    sources.append(decl)
    _write_payload(m4b_config_path, payload)
    return dict(decl)


def remove_source(m4b_config_path: str | Path, name: str) -> bool:
    """Remove the source with the given *name*. Returns True if removed."""
    payload = _load_payload(m4b_config_path)
    env = _envelope(payload)
    sources = env.get("catalog_sources") or []
    filtered = [
        s for s in sources if not (isinstance(s, dict) and s.get("name") == name)
    ]
    if len(filtered) == len(sources):
        return False
    env["catalog_sources"] = filtered
    _write_payload(m4b_config_path, payload)
    return True


def set_source_enabled(m4b_config_path: str | Path, name: str, enabled: bool) -> bool:
    """Flip ``enabled`` on the named source. Returns True if the source exists."""
    payload = _load_payload(m4b_config_path)
    env = _envelope(payload)
    sources = env.get("catalog_sources") or []
    for decl in sources:
        if isinstance(decl, dict) and decl.get("name") == name:
            decl["enabled"] = bool(enabled)
            _write_payload(m4b_config_path, payload)
            return True
    return False


def refresh_source(
    m4b_config_path: str | Path, name: str | None = None
) -> list[dict[str, Any]]:
    """Force-refresh the named remote source (or every remote if *name* is None).

    Clears the stored ETag first so the upstream is guaranteed to return a
    200 + body, then calls :meth:`RemoteSource.load` which rewrites the
    cache. Returns one result dict per source it attempted::

        {"name": ..., "status": "refreshed" | "skipped" | "error",
         "cached_entries": int, "error": str | None}

    Local sources are skipped with ``status="skipped"``.
    """
    payload = _load_payload(m4b_config_path)
    env = _envelope(payload)
    objects = build_sources(env, m4b_config_path)
    results: list[dict[str, Any]] = []

    targets = [obj for obj in objects if name is None or obj.name == name]
    if name is not None and not targets:
        raise CatalogSourceError(f"source {name!r} not found")

    for obj in targets:
        entry: dict[str, Any] = {"name": obj.name, "status": "skipped"}
        if isinstance(obj, RemoteSource):
            if not obj.enabled:
                entry["status"] = "disabled"
                results.append(entry)
                continue
            try:
                # Clear the ETag so the next fetch re-downloads in full.
                cache_dir = obj._resolve_cache_dir(  # noqa: SLF001
                    m4b_config_path
                )
                etag_file = cache_dir / ETAG_FILENAME
                if etag_file.is_file():
                    etag_file.unlink()
                loaded = obj.load(m4b_config_path)
                entry["status"] = "refreshed"
                entry["cached_entries"] = sum(len(v) for v in loaded.values())
            except Exception as exc:  # pragma: no cover — network errors
                entry["status"] = "error"
                entry["error"] = str(exc)
        results.append(entry)
    return results


def set_category(m4b_config_path: str | Path, category: str, active: bool) -> None:
    """Flip ``categories.<category>.active``. Raises on unknown category."""
    if category not in CATEGORIES:
        raise CatalogSourceError(
            f"unknown category {category!r} (expected one of {CATEGORIES})"
        )
    set_category_active(m4b_config_path, category, active)


# ---------------------------------------------------------------------------
# Introspection used by both CLI and API for a compact "last refresh" human
# string ("2 minutes ago" / "never"). Kept here so the CLI and API render
# the same wording.
# ---------------------------------------------------------------------------


def humanize_fetched_at(iso_ts: str | None) -> str:
    if not iso_ts:
        return "never"
    try:
        when = datetime.fromisoformat(iso_ts)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
    except ValueError:
        return iso_ts
    delta = datetime.now(tz=timezone.utc) - when
    secs = int(delta.total_seconds())
    if secs < 0:
        return iso_ts
    if secs < 60:
        return f"{secs}s ago"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"


__all__ = [
    "CatalogSourceError",
    "SOURCE_TYPES",
    "add_source",
    "humanize_fetched_at",
    "list_categories",
    "list_sources",
    "refresh_source",
    "remove_source",
    "set_category",
    "set_source_enabled",
    "source_status",
]
