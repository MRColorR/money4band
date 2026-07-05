"""Catalog-source management - the single API behind the CLI/TUI/REST surfaces.

Mutations of the ``catalog_sources[]`` list or ``categories.<name>.active``
flag are persisted to ``user-config.json -> catalog_overrides``, leaving
``m4b-config.json`` untouched. That separation means updates can safely
overwrite the shipped envelope without clobbering user toggles.

Design contract
---------------

Shipped defaults live in ``m4b-config.json`` under the ``catalog`` key::

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

User overrides live in ``user-config.json`` under ``catalog_overrides``
(see :mod:`money4band.core.catalog_overrides` for the schema). Every
reader below serves the *merged* view; every writer mutates only the
user config.

All functions in this module:

- take ``m4b_config_path`` (string or :class:`pathlib.Path`); the sibling
  ``user-config.json`` is discovered automatically and can be overridden
  via the ``user_config_path`` kwarg
- return structured dicts (never print), so the same call sites can be
  wrapped by a colour CLI formatter, a JSON-serialising router, or a
  TUI menu handler.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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
from money4band.core.catalog_overrides import (
    apply_overrides,
    load_user_overrides,
    save_user_overrides,
)
from money4band.core.catalog_store import (
    CATEGORIES,
    is_folded,
)

SOURCE_TYPES = ("local", "remote")


def _sibling_user_config(m4b_config_path: str | Path) -> Path:
    """Return the default ``user-config.json`` path next to *m4b_config_path*."""
    return Path(m4b_config_path).parent / "user-config.json"


def _resolve_user_config_path(
    m4b_config_path: str | Path,
    user_config_path: str | Path | None,
) -> Path:
    """Return *user_config_path* if provided, else the sibling default."""
    if user_config_path:
        return Path(user_config_path)
    return _sibling_user_config(m4b_config_path)


def _normalize_remote_manifest_url(url: str) -> str:
    """Normalize common GitHub URLs to a raw ``manifest.json`` URL.

    Accepted inputs include:
    - ``https://github.com/<owner>/<repo>``
    - ``https://github.com/<owner>/<repo>/blob/<branch>/manifest.json``
    - ``https://raw.githubusercontent.com/<owner>/<repo>/<branch>/manifest.json``
    """
    raw = (url or "").strip()
    if not raw:
        return raw

    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    parts = [p for p in parsed.path.split("/") if p]

    if host == "github.com" and len(parts) >= 2:
        owner, repo = parts[0], parts[1]
        # github.com/<owner>/<repo>/blob/<branch>/manifest.json
        if len(parts) >= 5 and parts[2] == "blob" and parts[-1] == "manifest.json":
            branch = parts[3]
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/manifest.json"
        # github.com/<owner>/<repo> -> default to main/manifest.json
        return f"https://raw.githubusercontent.com/{owner}/{repo}/main/manifest.json"

    if host == "raw.githubusercontent.com" and len(parts) >= 2:
        # raw.githubusercontent.com/<owner>/<repo>
        if len(parts) == 2:
            owner, repo = parts[0], parts[1]
            return (
                f"https://raw.githubusercontent.com/{owner}/{repo}/main/manifest.json"
            )
        # Ensure manifest file suffix when pointing to branch root.
        if len(parts) == 3:
            owner, repo, branch = parts
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/manifest.json"

    return raw


# ---------------------------------------------------------------------------
# Low-level envelope I/O
# ---------------------------------------------------------------------------


def _load_payload(m4b_config_path: str | Path) -> dict[str, Any]:
    path = Path(m4b_config_path)
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def _envelope(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a reference to the catalog envelope inside *payload*."""
    return payload["catalog"] if is_folded(payload) else payload


def _effective_envelope(
    m4b_config_path: str | Path,
    user_config_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return the envelope from m4b-config overlaid with user overrides."""
    payload = _load_payload(m4b_config_path)
    envelope = _envelope(payload)
    user_path = _resolve_user_config_path(m4b_config_path, user_config_path)
    overrides = load_user_overrides(user_path)
    return apply_overrides(envelope, overrides)


def _load_overrides(
    m4b_config_path: str | Path,
    user_config_path: str | Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Return the resolved user-config path and a mutable overrides dict."""
    user_path = _resolve_user_config_path(m4b_config_path, user_config_path)
    overrides = load_user_overrides(user_path)
    # Ensure the nested containers exist; callers mutate these in place.
    overrides.setdefault("sources", {})
    overrides.setdefault("removed_sources", [])
    overrides.setdefault("categories", {})
    return user_path, overrides


def _trim_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    """Drop empty sub-dicts/lists so the override section stays tidy."""
    trimmed = dict(overrides)
    if not trimmed.get("sources"):
        trimmed.pop("sources", None)
    if not trimmed.get("removed_sources"):
        trimmed.pop("removed_sources", None)
    if not trimmed.get("categories"):
        trimmed.pop("categories", None)
    return trimmed


# ---------------------------------------------------------------------------
# Public queries (read-only)
# ---------------------------------------------------------------------------


def list_sources(
    m4b_config_path: str | Path,
    user_config_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return the effective ``catalog_sources[]`` (shipped + overrides)."""
    env = _effective_envelope(m4b_config_path, user_config_path)
    raw = env.get("catalog_sources") or []
    return [dict(s) for s in raw if isinstance(s, dict)]


def list_categories(
    m4b_config_path: str | Path,
    user_config_path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Return the effective categories map (shipped + user overrides)."""
    env = _effective_envelope(m4b_config_path, user_config_path)
    cats = env.get("categories") or {}
    out: dict[str, dict[str, Any]] = {}
    for name in CATEGORIES:
        meta = cats.get(name) or {}
        out[name] = {"active": bool(meta.get("active", True))}
    return out


def source_status(
    m4b_config_path: str | Path,
    user_config_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return per-source status enriched with cache metadata.

    Each entry contains the declaration fields (``name``, ``type``,
    ``enabled``, ``url`` or ``path``, ``default_source``) plus cache
    introspection for remote sources: ``cache_dir``, ``etag``,
    ``fetched_at`` (ISO-8601 or None), and ``cached_entries`` (count
    of bundle files under the cache dir across all categories).
    """
    sources_raw = list_sources(m4b_config_path, user_config_path)
    env = _effective_envelope(m4b_config_path, user_config_path)
    objects = build_sources(env, m4b_config_path)
    obj_by_name = {obj.name: obj for obj in objects}

    results: list[dict[str, Any]] = []
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
    addons_dir = base / "addons"
    if addons_dir.is_dir():
        total += sum(1 for _ in addons_dir.glob("*.json"))
    return total


# ---------------------------------------------------------------------------
# Public mutations
# ---------------------------------------------------------------------------


class CatalogSourceError(ValueError):
    """Raised when a mutation would produce an invalid envelope."""


def _shipped_source_names(m4b_config_path: str | Path) -> set[str]:
    """Return the set of source names shipped in m4b-config.json."""
    payload = _load_payload(m4b_config_path)
    envelope = _envelope(payload)
    shipped = envelope.get("catalog_sources") or []
    return {
        str(s.get("name")) for s in shipped if isinstance(s, dict) and s.get("name")
    }


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
    user_config_path: str | Path | None = None,
) -> dict[str, Any]:
    """Persist a new source into user-config overrides. Returns the decl.

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

    shipped = _shipped_source_names(m4b_config_path)
    user_path, overrides = _load_overrides(m4b_config_path, user_config_path)
    sources = overrides["sources"]
    removed = overrides["removed_sources"]

    if name in shipped and name not in removed:
        raise CatalogSourceError(f"source {name!r} already exists")
    if name in sources and name not in shipped:
        raise CatalogSourceError(f"source {name!r} already exists")

    decl: dict[str, Any] = {
        "type": type,
        "name": name,
        "enabled": bool(enabled),
    }
    if default_source:
        decl["default_source"] = default_source
    else:
        decl["default_source"] = "builtin" if type == "local" else name
    if type == "remote":
        decl["url"] = _normalize_remote_manifest_url(str(url))
        if cache_path:
            decl["cache_path"] = cache_path
        if timeout is not None:
            decl["timeout"] = float(timeout)
    else:
        decl["path"] = path

    # If the user is re-adding a previously removed shipped source, drop
    # it from the tombstone list so it shows up again.
    if name in removed:
        overrides["removed_sources"] = [n for n in removed if n != name]

    sources[name] = decl
    save_user_overrides(user_path, _trim_overrides(overrides))
    return dict(decl)


def remove_source(
    m4b_config_path: str | Path,
    name: str,
    user_config_path: str | Path | None = None,
) -> bool:
    """Remove the source with the given *name*. Returns True if removed.

    - Shipped sources are tombstoned via ``removed_sources``.
    - User-added sources are dropped from ``sources``.
    """
    shipped = _shipped_source_names(m4b_config_path)
    user_path, overrides = _load_overrides(m4b_config_path, user_config_path)
    sources = overrides["sources"]
    removed = overrides["removed_sources"]

    changed = False
    if name in sources:
        sources.pop(name, None)
        changed = True
    if name in shipped and name not in removed:
        overrides["removed_sources"] = [*removed, name]
        changed = True
    if not changed:
        return False
    save_user_overrides(user_path, _trim_overrides(overrides))
    return True


def set_source_enabled(
    m4b_config_path: str | Path,
    name: str,
    enabled: bool,
    user_config_path: str | Path | None = None,
) -> bool:
    """Flip ``enabled`` on the named source. Returns True if the source exists.

    Shipped sources receive a partial override; user-added sources are
    mutated in place within ``catalog_overrides.sources``.
    """
    shipped = _shipped_source_names(m4b_config_path)
    user_path, overrides = _load_overrides(m4b_config_path, user_config_path)
    sources = overrides["sources"]
    removed = set(overrides["removed_sources"])

    if name in removed:
        # The source was tombstoned - nothing to flip.
        return False

    existing = sources.get(name)
    if isinstance(existing, dict):
        existing["enabled"] = bool(enabled)
    elif name in shipped:
        sources[name] = {"enabled": bool(enabled)}
    else:
        return False

    save_user_overrides(user_path, _trim_overrides(overrides))
    return True


def refresh_source(
    m4b_config_path: str | Path,
    name: str | None = None,
    user_config_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Force-refresh the named remote source (or every remote if *name* is None).

    Clears the stored ETag first so the upstream is guaranteed to return a
    200 + body, then calls :meth:`RemoteSource.load` which rewrites the
    cache. Returns one result dict per source it attempted::

        {"name": ..., "status": "refreshed" | "skipped" | "error",
         "cached_entries": int, "error": str | None}

    Local sources are skipped with ``status="skipped"``.
    """
    env = _effective_envelope(m4b_config_path, user_config_path)
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
                addons = obj.load_addons(m4b_config_path)
                entry["status"] = "refreshed"
                entry["cached_entries"] = sum(len(v) for v in loaded.values()) + len(
                    addons
                )
            except Exception as exc:  # pragma: no cover - network errors
                entry["status"] = "error"
                entry["error"] = str(exc)
        results.append(entry)
    return results


def set_category(
    m4b_config_path: str | Path,
    category: str,
    active: bool,
    user_config_path: str | Path | None = None,
) -> None:
    """Flip ``categories.<category>.active`` in user-config overrides."""
    if category not in CATEGORIES:
        raise CatalogSourceError(
            f"unknown category {category!r} (expected one of {CATEGORIES})"
        )
    user_path, overrides = _load_overrides(m4b_config_path, user_config_path)
    cats = overrides["categories"]
    cats[category] = {"active": bool(active)}
    save_user_overrides(user_path, _trim_overrides(overrides))


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
