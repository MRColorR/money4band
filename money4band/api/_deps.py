"""Shared dependencies for API routers.

Provides config-path resolution via a singleton that is configured once at
startup (``configure_paths()``) and consumed by router endpoints through
FastAPI's ``Depends()`` mechanism.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from money4band.core.loader import load_json_config


@dataclass(slots=True)
class ConfigPaths:
    """Holds resolved paths to the three main config files."""

    config_dir: str = ""
    m4b_config: str = ""
    app_config: str = ""
    user_config: str = ""
    base_dir: str = ""


# ---------------------------------------------------------------------------
# File-mtime config cache - avoids re-reading JSON on every request.
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _CacheEntry:
    data: dict = field(default_factory=dict)
    mtime: float = 0.0


class _ConfigCache:
    """Thin cache keyed by file path; reloads only when mtime changes."""

    def __init__(self) -> None:
        self._entries: dict[str, _CacheEntry] = {}

    def load(self, path: str) -> dict:
        entry = self._entries.get(path)
        try:
            current_mtime = os.path.getmtime(path)
        except OSError:
            return load_json_config(path)

        if entry is not None and entry.mtime == current_mtime:
            return entry.data

        data = load_json_config(path)
        self._entries[path] = _CacheEntry(data=data, mtime=current_mtime)
        return data

    def invalidate(self, path: str | None = None) -> None:
        if path is None:
            self._entries.clear()
        else:
            self._entries.pop(path, None)


_cache = _ConfigCache()


# Module-level singleton - populated once by ``configure_paths``.
_paths = ConfigPaths()


def configure_paths(
    config_dir: str,
    base_dir: str,
    *,
    m4b_file: str = "m4b-config.json",
    app_file: str | None = None,
    user_file: str = "user-config.json",
) -> None:
    """Set the config paths for the API lifetime.

    The catalog envelope lives in ``m4b-config.json`` under a
    ``catalog`` key, so ``app_config`` aliases ``m4b_config``.
    The ``app_file`` kwarg is accepted but ignored - catalog reads go
    through :func:`money4band.core.loader.load_app_config_with_overlays`.
    """
    del app_file
    _paths.config_dir = config_dir
    _paths.base_dir = base_dir
    _paths.m4b_config = os.path.join(config_dir, m4b_file)
    _paths.app_config = _paths.m4b_config
    _paths.user_config = os.path.join(config_dir, user_file)


def get_paths() -> ConfigPaths:
    """Return the resolved config paths (use as a FastAPI dependency)."""
    return _paths


def load_m4b_config() -> dict:
    """Load and return m4b-config.json (cached by file mtime)."""
    return _cache.load(_paths.m4b_config)


def load_app_config() -> dict:
    """Return the aggregated catalog dict (cached by m4b-config mtime).

    The envelope lives under ``m4b-config.json -> catalog``; this helper
    returns the aggregated shape
    (``{supported: {active, entries: [...]}, ...}``) via
    :func:`load_app_config_with_overlays`.
    """
    from money4band.core.loader import load_app_config_with_overlays

    path = _paths.m4b_config
    cache_key = f"app::{path}"
    entry = _cache._entries.get(cache_key)  # noqa: SLF001
    try:
        current_mtime = os.path.getmtime(path)
    except OSError:
        return load_app_config_with_overlays(path)
    if entry is not None and entry.mtime == current_mtime:
        return entry.data
    data = load_app_config_with_overlays(path)
    _cache._entries[cache_key] = _CacheEntry(  # noqa: SLF001
        data=data, mtime=current_mtime
    )
    return data


def load_user_config() -> dict:
    """Load and return user-config.json (cached by file mtime)."""
    return _cache.load(_paths.user_config)


# Keys that are never category containers.
_NON_CATEGORY_KEYS = frozenset({"app_config_version"})


def get_app_categories(app_config: dict | None = None) -> dict:
    """Return the ``{category_name: {active, entries}}`` mapping.

    Supports two config layouts:
    * Wrapped:  ``{"categories": {"supported": {...}, ...}}``
    * Flat:     ``{"supported": {...}, "deprecated": {...}, ...}``
    """
    if app_config is None:
        app_config = load_app_config()

    # Prefer explicit "categories" envelope when present.
    cats = app_config.get("categories")
    if isinstance(cats, dict) and cats:
        return cats

    # Fall back to flat layout - every top-level dict with an "entries" key.
    return {
        k: v
        for k, v in app_config.items()
        if k not in _NON_CATEGORY_KEYS and isinstance(v, dict) and "entries" in v
    }


def iter_all_apps(
    app_config: dict | None = None,
) -> list[tuple[str, dict, dict]]:
    """Yield ``(category_name, category_data, app_entry)`` for every app.

    Avoids duplicating the nested category->entries loop in every consumer.
    """
    categories = get_app_categories(app_config)
    return [
        (cat_name, cat_data, app)
        for cat_name, cat_data in categories.items()
        for app in cat_data.get("entries", [])
    ]


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------
#
# ``source`` describes *where* a catalog entry came from:
#   * ``builtin``   - shipped inside the core catalog envelope.
#   * ``community`` - user overlay from ``config/apps.d/*.json``.
#   * ``remote``    - fetched from a remote catalog source.
#   * ``local``     - user-local override.
#
# Entries loaded through ``iter_all_apps`` default to ``builtin``;
# the resolver below is the single seam where other sources override
# the provenance.


def resolve_source(entry: dict) -> str:
    """Return the catalog source for a single app entry."""
    explicit = entry.get("_source")
    if isinstance(explicit, str) and explicit:
        return explicit
    return "builtin"


def is_managed_by_m4b(category: str, source: str) -> bool:
    """Return True when M4B ships + maintains this entry.

    Only ``supported`` entries from the ``builtin`` catalog are considered
    fully managed. Newcomers, deprecated, and overlay entries are not.
    """
    return category == "supported" and source == "builtin"


def get_picked_referrals() -> dict[str, str]:
    """Return the ``settings.picked_referrals`` map from user-config.

    Returns an empty dict when the section is absent so callers can treat
    "no sticky pick" uniformly.
    """
    user = load_user_config()
    settings = user.get("settings") if isinstance(user, dict) else None
    if not isinstance(settings, dict):
        return {}
    picked = settings.get("picked_referrals")
    if not isinstance(picked, dict):
        return {}
    return {str(k): str(v) for k, v in picked.items() if isinstance(v, str)}


def _weights_path() -> str:
    """Resolve the path to the repo's ``config/weights.json`` artifact."""
    from money4band.apps.contributor_pool import WEIGHTS_RELATIVE_PATH

    base = _paths.base_dir or os.getcwd()
    return os.path.join(base, WEIGHTS_RELATIVE_PATH)


def load_contributor_weights() -> dict[str, float]:
    """Return the cached contributor weights map (keyed by mtime)."""
    from money4band.apps.contributor_pool import load_weights

    path = _weights_path()
    cache_key = f"weights::{path}"
    try:
        current_mtime = os.path.getmtime(path)
    except OSError:
        # No weights.json shipped - picker falls back to uniform random.
        return {}
    entry = _cache._entries.get(cache_key)  # noqa: SLF001
    if entry is not None and entry.mtime == current_mtime:
        return entry.data  # type: ignore[return-value]
    data = load_weights(path)
    _cache._entries[cache_key] = _CacheEntry(  # noqa: SLF001
        data=data,  # type: ignore[arg-type]
        mtime=current_mtime,
    )
    return data


def pick_referral_url(
    app_name: str, referrals: list[dict], picked: dict[str, str]
) -> str:
    """Resolve the effective referral URL for an app.

    Preference order:
      1. ``settings.picked_referrals[<app_name lowercase>]`` when set.
      2. Weighted-random pick across the referrals pool, where every
         referral's weight is the contributor's entry in
         ``weights.json`` (``0`` when the contributor is absent;
         all-zero pools fall back to uniform random).
      3. Empty string when the pool has no usable entries.

    The picker is pure: the whole pool is considered on every call.
    Determinism comes from sticky picks stored in user-config.
    """
    from money4band.apps.contributor_pool import resolve_referral_url

    return resolve_referral_url(
        app_name,
        referrals,
        weights=load_contributor_weights(),
        sticky=picked,
    )


def normalize_referrals(raw: Any) -> list[dict]:
    """Return the referrals pool as a list of plain dicts.

    Unknown/malformed entries are dropped silently - the API contract
    only promises well-formed referrals.
    """
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        out.append(
            {
                "url": url.strip(),
                "contributor": str(item.get("contributor") or "MRColorR"),
                "added": item["added"] if isinstance(item.get("added"), str) else None,
                "verified": bool(item.get("verified", False)),
                "verified_by": [
                    str(v)
                    for v in (item.get("verified_by") or [])
                    if isinstance(v, str)
                ],
            }
        )
    return out
