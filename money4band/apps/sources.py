"""Pluggable catalog sources.

A :class:`CatalogSource` yields catalog entries grouped by category.
The envelope (under ``m4b-config.json → catalog``) lists the sources
under ``catalog_sources[]`` and the per-category ``active`` flags under
``categories.<name>.active``. This module turns those declarations into
concrete :class:`CatalogSource` objects and merges their output into the
in-memory shape consumed by the rest of the codebase::

    {
        "app_config_version": 2.0,
        "catalog_sources": [...],
        "supported":  {"active": bool, "entries": [...]},
        "newcomers":  {"active": bool, "entries": [...]},
        "deprecated": {"active": bool, "entries": [...]},
    }

Source ordering matters: the first enabled source that yields a given
entry name wins. Later sources cannot override earlier ones — this keeps
local/builtin entries authoritative over remote fetches.

Two concrete sources are shipped:

* :class:`LocalSource` — reads per-file bundles from a catalog directory
  on disk (the default ``config/catalog`` layout).
* :class:`RemoteSource` — HTTP fetch with on-disk caching; see
  :mod:`money4band.apps.remote_cache`.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from money4band.core.catalog_store import CATEGORIES, read_addons_dir, read_entries_dir

logger = logging.getLogger(__name__)


class CatalogSource(ABC):
    """Abstract catalog source.

    Subclasses provide entries grouped by category. They do *not* own the
    category ``active`` flag — that lives in the envelope and is applied
    by :func:`aggregate_from_sources`.
    """

    type: str = ""

    def __init__(
        self,
        *,
        name: str,
        default_source: str,
        enabled: bool = True,
    ) -> None:
        self.name = name
        self.default_source = default_source
        self.enabled = enabled

    def available(self) -> bool:
        """Return ``True`` if the source can currently be loaded."""
        return self.enabled

    @abstractmethod
    def load(self, config_path: str | Path) -> dict[str, list[dict[str, Any]]]:
        """Return ``{category: [entry_dict, ...]}`` for this source."""

    def load_addons(self, config_path: str | Path) -> list[dict[str, Any]]:
        """Return ``[addon_dict, ...]`` for this source. Default: none.

        Addons are parallel to categories (attached to parent apps via
        ``parent_id``).
        """
        return []

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<{type(self).__name__} name={self.name!r} "
            f"enabled={self.enabled} default_source={self.default_source!r}>"
        )


class LocalSource(CatalogSource):
    """On-disk catalog source reading per-file bundles.

    ``path`` is resolved relative to the envelope file's parent directory
    when not absolute, so ``"catalog"`` from
    ``.../config/m4b-config.json`` points to ``.../config/catalog``.
    Missing category directories yield empty lists — they are not errors.
    """

    type = "local"

    def __init__(
        self,
        *,
        path: str,
        name: str = "local",
        default_source: str = "builtin",
        enabled: bool = True,
    ) -> None:
        super().__init__(name=name, default_source=default_source, enabled=enabled)
        self.path = path

    def _resolve_root(self, config_path: str | Path) -> Path:
        p = Path(self.path)
        if p.is_absolute():
            return p
        return Path(config_path).parent / p

    def available(self) -> bool:
        return self.enabled

    def load(self, config_path: str | Path) -> dict[str, list[dict[str, Any]]]:
        if not self.enabled:
            return {cat: [] for cat in CATEGORIES}
        root = self._resolve_root(config_path)
        if not root.is_dir():
            logger.debug("Local catalog root missing: %s", root)
            return {cat: [] for cat in CATEGORIES}
        return {cat: read_entries_dir(root, cat) for cat in CATEGORIES}

    def load_addons(self, config_path: str | Path) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        root = self._resolve_root(config_path)
        if not root.is_dir():
            return []
        return read_addons_dir(root)


class RemoteSource(CatalogSource):
    """Remote catalog source.

    Fetches an aggregated catalog manifest over HTTPS (``httpx``),
    caches per-file bundles under ``config/catalog/community/``, and
    falls back to the on-disk cache when the fetch fails or times out.

    **Wire protocol.** A ``GET <url>`` is expected to return either:

    * a category-keyed envelope ``{supported: {entries: [...]}, ...}``
      (same shape the loader exposes in-memory), or
    * a flat list ``{entries: [{category: ..., ...}, ...]}``.

    Both forms are normalised by
    :func:`money4band.apps.remote_cache.split_manifest`.

    **Caching.** The last ETag is persisted at
    ``<cache_dir>/.etag``. Every fetch re-sends it via
    ``If-None-Match`` so well-behaved upstreams answer ``304 Not
    Modified`` and we skip the rewrite cycle.

    **Offline fallback.** On any network failure (timeout, non-2xx,
    JSON parse error) the last-known cache is used. An empty cache
    yields no entries but never raises.

    **Path resolution.** ``cache_path`` is relative to the envelope file
    when not absolute (default: ``"catalog/community"`` → sibling of
    ``config/m4b-config.json``).
    """

    type = "remote"

    DEFAULT_CACHE_PATH = "catalog/community"
    DEFAULT_TIMEOUT = 5.0

    def __init__(
        self,
        *,
        url: str,
        name: str = "remote",
        default_source: str = "community",
        enabled: bool = False,
        timeout: float | None = None,
        cache_path: str | None = None,
    ) -> None:
        super().__init__(name=name, default_source=default_source, enabled=enabled)
        self.url = url
        self.timeout = float(timeout) if timeout is not None else self.DEFAULT_TIMEOUT
        self.cache_path = cache_path or self.DEFAULT_CACHE_PATH

    def available(self) -> bool:
        return self.enabled and bool(self.url)

    def _resolve_cache_dir(self, config_path: str | Path) -> Path:
        p = Path(self.cache_path)
        return p if p.is_absolute() else Path(config_path).parent / p

    def _fetch_manifest(self, etag: str | None) -> tuple[int, dict | None, str | None]:
        """Perform the HTTP GET. Returns ``(status, payload, new_etag)``.

        * ``status=200`` + payload + etag: fresh manifest.
        * ``status=304``: no body, caller must use cache.
        * ``status=0``: network/parse failure (see log); caller falls
          back to cache.
        """
        import httpx  # local import — httpx is optional at import time in tests

        headers = {"Accept": "application/json", "User-Agent": "money4band/5.0"}
        if etag:
            headers["If-None-Match"] = etag

        try:
            with httpx.Client(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            ) as client:
                response = client.get(self.url, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning(
                "RemoteSource %r: fetch failed (%s); using offline cache",
                self.name,
                exc,
            )
            return (0, None, None)

        if response.status_code == 304:
            logger.info("RemoteSource %r: 304 Not Modified — cache fresh", self.name)
            return (304, None, None)

        if response.status_code != 200:
            logger.warning(
                "RemoteSource %r: unexpected status %s; using offline cache",
                self.name,
                response.status_code,
            )
            return (0, None, None)

        try:
            payload = response.json()
        except ValueError as exc:
            logger.warning(
                "RemoteSource %r: invalid JSON (%s); using offline cache",
                self.name,
                exc,
            )
            return (0, None, None)

        if not isinstance(payload, dict):
            logger.warning(
                "RemoteSource %r: manifest is not a JSON object; using offline cache",
                self.name,
            )
            return (0, None, None)

        new_etag = response.headers.get("ETag") or response.headers.get("etag")
        return (200, payload, new_etag)

    def load(self, config_path: str | Path) -> dict[str, list[dict[str, Any]]]:
        from money4band.apps.remote_cache import (
            read_etag,
            replace_entries,
            split_addons_from_manifest,
            split_manifest,
            touch_fetched_at,
            write_etag,
        )
        from money4band.core.catalog_store import read_entries_dir

        if not self.available():
            return {cat: [] for cat in CATEGORIES}

        cache_dir = self._resolve_cache_dir(config_path)
        etag = read_etag(cache_dir)
        status, payload, new_etag = self._fetch_manifest(etag)

        if status == 200 and payload is not None:
            entries_by_cat = split_manifest(payload)
            addons = split_addons_from_manifest(payload)
            written = replace_entries(cache_dir, entries_by_cat, addons)
            touch_fetched_at(cache_dir)
            if new_etag:
                write_etag(cache_dir, new_etag)
            logger.info(
                "RemoteSource %r: refreshed cache with %d entries", self.name, written
            )
        elif status == 304:
            touch_fetched_at(cache_dir)

        # Offline path (status=0) or cache hit — read from disk.
        if not cache_dir.is_dir():
            return {cat: [] for cat in CATEGORIES}
        return {cat: read_entries_dir(cache_dir, cat) for cat in CATEGORIES}

    def load_addons(self, config_path: str | Path) -> list[dict[str, Any]]:
        if not self.available():
            return []
        cache_dir = self._resolve_cache_dir(config_path)
        if not cache_dir.is_dir():
            return []
        return read_addons_dir(cache_dir)


def build_sources(
    envelope: dict[str, Any], config_path: str | Path
) -> list[CatalogSource]:
    """Instantiate :class:`CatalogSource` objects from an envelope."""
    decls = envelope.get("catalog_sources") or []
    sources: list[CatalogSource] = []
    for idx, decl in enumerate(decls):
        if not isinstance(decl, dict):
            logger.warning("Skipping non-dict catalog_sources[%d]: %r", idx, decl)
            continue
        stype = decl.get("type")
        enabled = bool(decl.get("enabled", True))
        default_source = decl.get("default_source", "builtin")
        name = decl.get("name") or f"{stype or 'source'}-{idx}"
        if stype == LocalSource.type:
            path = decl.get("path")
            if not path:
                logger.warning("Skipping local catalog source %r: missing 'path'", name)
                continue
            sources.append(
                LocalSource(
                    path=path,
                    name=name,
                    default_source=default_source,
                    enabled=enabled,
                )
            )
        elif stype == RemoteSource.type:
            url = decl.get("url")
            if not url:
                logger.warning("Skipping remote catalog source %r: missing 'url'", name)
                continue
            sources.append(
                RemoteSource(
                    url=url,
                    name=name,
                    default_source=default_source,
                    enabled=enabled,
                    timeout=float(decl.get("timeout", RemoteSource.DEFAULT_TIMEOUT)),
                    cache_path=decl.get("cache_path"),
                )
            )
        else:
            logger.warning("Unknown catalog source type %r at index %d", stype, idx)
    return sources


def aggregate_from_sources(
    envelope: dict[str, Any], config_path: str | Path
) -> dict[str, Any]:
    """Aggregate envelope + sources into the historical in-memory shape.

    Walks ``envelope["catalog_sources"]`` in order. Each available source
    contributes its entries; the first source to claim a given entry name
    (case-insensitive) in a given category wins. Category ``active``
    flags come from ``envelope["categories"]``.
    """
    result: dict[str, Any] = {
        "app_config_version": envelope.get("app_config_version", 2.0),
    }
    # Preserve envelope extras (catalog_sources, etc.) for API exposure.
    for key, val in envelope.items():
        if key in ("app_config_version", "categories"):
            continue
        result[key] = val

    sources = build_sources(envelope, config_path)
    cats = envelope.get("categories") or {}

    seen_names: dict[str, set[str]] = {cat: set() for cat in CATEGORIES}
    merged: dict[str, list[dict[str, Any]]] = {cat: [] for cat in CATEGORIES}

    # Inline entries (``categories.<name>.entries``) count as the first,
    # highest-priority source. Shipped envelopes keep the list empty, so
    # this is a no-op in production — but test fixtures and in-memory
    # envelopes can provide entries without touching the filesystem.
    for cat in CATEGORIES:
        meta = cats.get(cat) if isinstance(cats, dict) else None
        if not isinstance(meta, dict):
            continue
        for entry in meta.get("entries") or []:
            if not isinstance(entry, dict):
                continue
            raw_name = entry.get("name")
            if not isinstance(raw_name, str) or not raw_name:
                continue
            key = raw_name.upper()
            if key in seen_names[cat]:
                continue
            seen_names[cat].add(key)
            merged[cat].append(entry)

    for src in sources:
        if not src.available():
            continue
        try:
            yielded = src.load(config_path)
        except Exception as exc:  # noqa: BLE001 - source failures must never crash the loader
            logger.warning("Catalog source %r failed to load: %s", src.name, exc)
            continue
        for cat, entries in yielded.items():
            if cat not in CATEGORIES:
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                raw_name = entry.get("name")
                if not isinstance(raw_name, str) or not raw_name:
                    continue
                key = raw_name.upper()
                if key in seen_names[cat]:
                    logger.debug(
                        "Dropping duplicate %s/%s from source %r (earlier source won)",
                        cat,
                        raw_name,
                        src.name,
                    )
                    continue
                seen_names[cat].add(key)
                merged[cat].append(entry)

    for cat in CATEGORIES:
        meta = cats.get(cat) if isinstance(cats, dict) else None
        active = bool(meta.get("active", False)) if isinstance(meta, dict) else False
        result[cat] = {"active": active, "entries": merged[cat]}

    # Aggregate addons across sources (first-wins by NAME, like entries).
    seen_addons: set[str] = set()
    merged_addons: list[dict[str, Any]] = []
    for src in sources:
        if not src.available():
            continue
        try:
            addons = src.load_addons(config_path)
        except Exception as exc:  # noqa: BLE001 - source failures must not crash
            logger.warning(
                "Catalog source %r failed to load addons: %s", src.name, exc
            )
            continue
        for addon in addons:
            if not isinstance(addon, dict):
                continue
            raw_name = addon.get("name")
            if not isinstance(raw_name, str) or not raw_name:
                continue
            key = raw_name.upper()
            if key in seen_addons:
                continue
            seen_addons.add(key)
            merged_addons.append(addon)
    result["addons"] = merged_addons

    return result


__all__ = [
    "CatalogSource",
    "LocalSource",
    "RemoteSource",
    "aggregate_from_sources",
    "build_sources",
]
