"""Pluggable catalog sources (phase-8.4).

A :class:`CatalogSource` yields catalog entries grouped by category.
The envelope file (``config/app-config.json``) lists the sources under
``catalog_sources[]`` and the per-category ``active`` flags under
``categories.<name>.active``. This module turns those declarations into
concrete :class:`CatalogSource` objects and merges their output into the
historical in-memory shape consumed by the rest of the codebase::

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

This phase ships two concrete sources:

* :class:`LocalSource` — reads per-file bundles from a catalog directory
  on disk (the default ``config/catalog`` layout introduced in 8.3b).
* :class:`RemoteSource` — stub placeholder. Real HTTP fetch arrives in
  phase-8.5; for now it is always unavailable and yields nothing.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from money4band.core.catalog_store import CATEGORIES, read_entries_dir

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

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<{type(self).__name__} name={self.name!r} "
            f"enabled={self.enabled} default_source={self.default_source!r}>"
        )


class LocalSource(CatalogSource):
    """On-disk catalog source reading per-file bundles.

    ``path`` is resolved relative to the envelope file's parent directory
    when not absolute, so ``"catalog"`` from ``.../config/app-config.json``
    points to ``.../config/catalog``. Missing category directories yield
    empty lists — they are not errors.
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


class RemoteSource(CatalogSource):
    """Remote catalog source stub (phase-8.4).

    The real HTTP fetch, ETag cache, and offline fallback arrive in
    phase-8.5. For now the source is always unavailable, ``load()``
    yields nothing, and a one-time debug log records that it was skipped.
    """

    type = "remote"

    def __init__(
        self,
        *,
        url: str,
        name: str = "remote",
        default_source: str = "community",
        enabled: bool = False,
        timeout: float = 5.0,
    ) -> None:
        super().__init__(name=name, default_source=default_source, enabled=enabled)
        self.url = url
        self.timeout = timeout

    def available(self) -> bool:
        # Remote fetch not yet implemented — never available.
        return False

    def load(self, config_path: str | Path) -> dict[str, list[dict[str, Any]]]:
        if self.enabled:
            logger.info(
                "RemoteSource %r enabled but remote fetch is not yet "
                "implemented (phase-8.5); skipping %s",
                self.name,
                self.url,
            )
        return {cat: [] for cat in CATEGORIES}


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
                    timeout=float(decl.get("timeout", 5.0)),
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

    return result


__all__ = [
    "CatalogSource",
    "LocalSource",
    "RemoteSource",
    "aggregate_from_sources",
    "build_sources",
]
