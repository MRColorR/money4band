"""Shared dependencies for API routers.

Provides config-path resolution via a singleton that is configured once at
startup (``configure_paths()``) and consumed by router endpoints through
FastAPI's ``Depends()`` mechanism.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from money4band.loader import load_json_config


@dataclass(slots=True)
class ConfigPaths:
    """Holds resolved paths to the three main config files."""

    config_dir: str = ""
    m4b_config: str = ""
    app_config: str = ""
    user_config: str = ""
    base_dir: str = ""


# ---------------------------------------------------------------------------
# File-mtime config cache — avoids re-reading JSON on every request.
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


# Module-level singleton — populated once by ``configure_paths``.
_paths = ConfigPaths()


def configure_paths(
    config_dir: str,
    base_dir: str,
    *,
    m4b_file: str = "m4b-config.json",
    app_file: str = "app-config.json",
    user_file: str = "user-config.json",
) -> None:
    """Set the config paths for the API lifetime."""
    _paths.config_dir = config_dir
    _paths.base_dir = base_dir
    _paths.m4b_config = os.path.join(config_dir, m4b_file)
    _paths.app_config = os.path.join(config_dir, app_file)
    _paths.user_config = os.path.join(config_dir, user_file)


def get_paths() -> ConfigPaths:
    """Return the resolved config paths (use as a FastAPI dependency)."""
    return _paths


def load_m4b_config() -> dict:
    """Load and return m4b-config.json (cached by file mtime)."""
    return _cache.load(_paths.m4b_config)


def load_app_config() -> dict:
    """Load and return app-config.json (cached by file mtime)."""
    return _cache.load(_paths.app_config)


def load_user_config() -> dict:
    """Load and return user-config.json (cached by file mtime)."""
    return _cache.load(_paths.user_config)


# Keys that are never category containers.
_NON_CATEGORY_KEYS = frozenset({"app_config_version"})


def get_app_categories(app_config: dict | None = None) -> dict:
    """Return the ``{category_name: {active, entries}}`` mapping.

    Supports two config layouts:
    * Wrapped:  ``{"categories": {"supported-apps": {...}, ...}}``
    * Flat:     ``{"supported-apps": {...}, "deprecated-apps": {...}, ...}``
    """
    if app_config is None:
        app_config = load_app_config()

    # Prefer explicit "categories" envelope when present.
    cats = app_config.get("categories")
    if isinstance(cats, dict) and cats:
        return cats

    # Fall back to flat layout — every top-level dict with an "entries" key.
    return {
        k: v
        for k, v in app_config.items()
        if k not in _NON_CATEGORY_KEYS and isinstance(v, dict) and "entries" in v
    }


def iter_all_apps(
    app_config: dict | None = None,
) -> list[tuple[str, dict, dict]]:
    """Yield ``(category_name, category_data, app_entry)`` for every app.

    Avoids duplicating the nested category→entries loop in every consumer.
    """
    categories = get_app_categories(app_config)
    return [
        (cat_name, cat_data, app)
        for cat_name, cat_data in categories.items()
        for app in cat_data.get("entries", [])
    ]
