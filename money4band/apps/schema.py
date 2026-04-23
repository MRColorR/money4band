from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

logger = logging.getLogger(__name__)

# Minimal required fields for a valid app entry
_REQUIRED_FIELDS = {"name", "compose_config", "flags", "install_limit", "compose_layer"}
_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
_VALID_LAYERS = {"residential", "datacenter", "universal", "service"}
_VALID_RESTART = {"always", "unless-stopped", "on-failure", "no"}


def validate_app_entry(entry: dict[str, Any]) -> list[str]:
    """Validate a single app entry against the M4B app schema.

    Returns a list of error strings.  Empty list means the entry is valid.
    """
    errors: list[str] = []

    # Required top-level fields
    for field in _REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"Missing required field: '{field}'")

    name = entry.get("name", "")
    if name and not _NAME_RE.match(name):
        errors.append(
            f"Invalid name '{name}': must be uppercase letters, digits, underscores"
        )

    # compose_config checks
    cc = entry.get("compose_config")
    if isinstance(cc, dict):
        if "image" not in cc:
            errors.append("compose_config: missing required field 'image'")
        if cc.get("restart") and cc["restart"] not in _VALID_RESTART:
            errors.append(f"compose_config.restart: invalid value '{cc['restart']}'")
    elif cc is not None:
        errors.append("compose_config: must be an object")

    # compose_layer
    layer = entry.get("compose_layer")
    if layer and layer not in _VALID_LAYERS:
        errors.append(f"compose_layer: invalid value '{layer}'")

    # install_limit
    limit = entry.get("install_limit")
    if limit is not None and not isinstance(limit, int):
        errors.append(f"install_limit: must be an integer, got {type(limit).__name__}")

    # flags must be a dict
    flags = entry.get("flags")
    if flags is not None and not isinstance(flags, dict):
        errors.append("flags: must be an object")

    return errors


def load_community_apps(apps_d_dir: str) -> list[dict[str, Any]]:
    """Load community app definitions from ``apps.d/`` directory.

    Each ``.json`` file is expected to contain a single app entry object.
    Files are loaded alphabetically; invalid files are logged and skipped.

    Returns a list of validated app entries.
    """
    entries: list[dict[str, Any]] = []

    if not os.path.isdir(apps_d_dir):
        return entries

    for filename in sorted(os.listdir(apps_d_dir)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(apps_d_dir, filename)
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping invalid community app file %s: %s", filename, exc)
            continue

        errors = validate_app_entry(data)
        if errors:
            logger.warning(
                "Community app %s has validation errors: %s",
                filename,
                "; ".join(errors),
            )
            continue

        entries.append(data)
        logger.info("Loaded community app: %s from %s", data.get("name", "?"), filename)

    return entries


def merge_community_apps(app_config: dict[str, Any], apps_d_dir: str) -> dict[str, Any]:
    """Merge community app definitions into *app_config*.

    Community apps are placed into the ``newcomers`` category.
    Duplicate names (already present in any category) are skipped.

    Mutates and returns *app_config*.
    """
    community = load_community_apps(apps_d_dir)
    if not community:
        return app_config

    # Collect all existing names across all categories
    existing_names: set[str] = set()
    for _key, val in app_config.items():
        if isinstance(val, dict) and "entries" in val:
            for e in val["entries"]:
                if isinstance(e, dict) and "name" in e:
                    existing_names.add(e["name"].upper())

    # Ensure newcomers category exists
    if "newcomers" not in app_config:
        app_config["newcomers"] = {"active": False, "entries": []}
    candidates = app_config["newcomers"]
    if "entries" not in candidates:
        candidates["entries"] = []

    added = 0
    for entry in community:
        name = entry["name"].upper()
        if name in existing_names:
            logger.info("Skipping duplicate community app: %s", name)
            continue
        candidates["entries"].append(entry)
        existing_names.add(name)
        added += 1

    if added:
        logger.info("Merged %d community app(s) into newcomers", added)

    return app_config


# ---------------------------------------------------------------------------
# Typed catalog model (phase-8.1)
# ---------------------------------------------------------------------------
#
# These dataclasses are the canonical in-memory representation of a catalog
# entry.  They map 1:1 onto the ``app-config.json`` v2.0 shape; no legacy
# v1.2 tolerance is attempted — a dedicated migration ran once at the schema
# bump and no long-lived dual-stack code is carried.
#
# Shape contract (v2.0):
#   * Top-level categories are ``supported`` / ``newcomers`` / ``deprecated``.
#   * Per-entry ``referrals`` is a list of ``{url, contributor, ...}`` dicts
#     (may be empty).  No single ``link`` string is accepted.
#   * Per-entry ``additional_details`` is an optional Markdown note usable
#     in any category (replaces the old ``removal_reason``).
#   * ``app_details`` remains the bag of descriptive metadata and is kept
#     intact inside :class:`AppMetadata.raw`.

# Canonical catalog source types (see ``catalog_sources[].type``).
SOURCE_LOCAL = "local"
SOURCE_REMOTE = "remote"
SOURCE_COMMUNITY = "community"  # user-overlay apps from ``config/apps.d/``
SOURCE_BUILTIN = "builtin"  # apps shipped inside ``config/app-config.json``

# Canonical v2.0 category keys.
CATEGORY_SUPPORTED = "supported"
CATEGORY_NEWCOMERS = "newcomers"
CATEGORY_DEPRECATED = "deprecated"
VALID_CATEGORIES: frozenset[str] = frozenset(
    {CATEGORY_SUPPORTED, CATEGORY_NEWCOMERS, CATEGORY_DEPRECATED}
)


@dataclass(frozen=True)
class Referral:
    """A single referral/affiliate URL contributed by a catalog author.

    Multiple referrals form a *pool* that the contributor-weighted picker
    (phase-8.6) rotates through.  Only ``url`` and ``contributor`` are
    required; the remaining fields are optional provenance hints.
    """

    url: str
    contributor: str = "MRColorR"
    added: str | None = None  # ISO-8601 date the entry was added
    verified: bool = False
    verified_by: tuple[str, ...] = ()

    @classmethod
    def from_raw(cls, data: Any) -> Referral:
        """Build a :class:`Referral` from a string URL or full dict."""
        if isinstance(data, str):
            return cls(url=data)
        if isinstance(data, dict):
            url = str(data.get("url", "")).strip()
            contributor = str(data.get("contributor") or "MRColorR")
            added = data.get("added")
            verified = bool(data.get("verified", False))
            verified_by_raw = data.get("verified_by") or ()
            if isinstance(verified_by_raw, list | tuple):
                verified_by = tuple(str(x) for x in verified_by_raw)
            else:
                verified_by = ()
            return cls(
                url=url,
                contributor=contributor,
                added=added if isinstance(added, str) else None,
                verified=verified,
                verified_by=verified_by,
            )
        raise TypeError(f"Cannot build Referral from {type(data).__name__}")


@dataclass
class AppMetadata:
    """Presentational / informational fields for an app entry.

    The full ``app_details`` blob is retained verbatim in ``raw`` so every
    existing reader (UI cards, info screens, docs generator) keeps working
    without modification.
    """

    official_name: str | None = None
    publisher: str | None = None
    description: str | None = None
    dashboard_url: str | None = None
    referrals: list[Referral] = dc_field(default_factory=list)
    raw: dict[str, Any] = dc_field(default_factory=dict)


@dataclass
class DeploymentSpec:
    """Docker Compose deployment contract for an app entry.

    Mirrors the v2.0 compose-side fields verbatim; callers that still want
    the raw dict can use ``raw`` unchanged.
    """

    compose_config: dict[str, Any] = dc_field(default_factory=dict)
    compose_config_proxy: dict[str, Any] | None = None
    flags: dict[str, Any] = dc_field(default_factory=dict)
    install_limit: int = -1
    compose_layer: str = "residential"
    raw: dict[str, Any] = dc_field(default_factory=dict)


@dataclass
class CatalogEntry:
    """Typed view over a single v2.0 catalog app entry.

    ``raw`` preserves the original dict so no information is lost when the
    entry is round-tripped through :meth:`from_raw`.
    """

    id: str  # uppercase canonical name
    source: str  # one of SOURCE_* constants
    category: str  # one of VALID_CATEGORIES
    metadata: AppMetadata
    deployment: DeploymentSpec
    additional_details: str | None = None  # generic Markdown note (any category)
    raw: dict[str, Any] = dc_field(default_factory=dict)

    @property
    def name(self) -> str:
        """Alias for ``id`` — compatibility with ``entry["name"]`` readers."""
        return self.id

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        *,
        source: str = SOURCE_BUILTIN,
        category: str = CATEGORY_SUPPORTED,
    ) -> CatalogEntry:
        """Construct a :class:`CatalogEntry` from a v2.0 dict.

        Unknown keys are preserved via ``raw`` so future schema extensions
        do not require code changes here.
        """
        if not isinstance(raw, dict):
            raise TypeError(
                f"CatalogEntry.from_raw expects a dict, got {type(raw).__name__}"
            )

        name = str(raw.get("name", "")).strip()
        if not name:
            raise ValueError("CatalogEntry.from_raw: entry is missing 'name'")
        entry_id = name.upper()

        # Metadata ----------------------------------------------------------
        app_details = raw.get("app_details")
        details_dict = app_details if isinstance(app_details, dict) else {}

        referrals: list[Referral] = []
        referrals_raw = raw.get("referrals")
        if isinstance(referrals_raw, list):
            for item in referrals_raw:
                try:
                    referrals.append(Referral.from_raw(item))
                except (TypeError, ValueError) as exc:
                    logger.warning("Skipping invalid referral in %s: %s", entry_id, exc)

        metadata = AppMetadata(
            official_name=details_dict.get("official_name") or name,
            publisher=details_dict.get("publisher"),
            description=raw.get("description") or details_dict.get("description"),
            dashboard_url=raw.get("dashboard"),
            referrals=referrals,
            raw=details_dict,
        )

        # Deployment --------------------------------------------------------
        compose_config = raw.get("compose_config") or {}
        compose_config_proxy = raw.get("compose_config_proxy")
        flags = raw.get("flags") or {}
        install_limit_raw = raw.get("install_limit", -1)
        try:
            install_limit = int(install_limit_raw)
        except (TypeError, ValueError):
            install_limit = -1
        compose_layer = str(raw.get("compose_layer") or "residential")

        deployment = DeploymentSpec(
            compose_config=compose_config if isinstance(compose_config, dict) else {},
            compose_config_proxy=compose_config_proxy
            if isinstance(compose_config_proxy, dict)
            else None,
            flags=flags if isinstance(flags, dict) else {},
            install_limit=install_limit,
            compose_layer=compose_layer,
            raw=raw,
        )

        additional_raw = raw.get("additional_details")
        additional = (
            additional_raw.strip()
            if isinstance(additional_raw, str) and additional_raw.strip()
            else None
        )

        return cls(
            id=entry_id,
            source=source,
            category=category,
            metadata=metadata,
            deployment=deployment,
            additional_details=additional,
            raw=raw,
        )


@dataclass
class Addon:
    """A sidecar/companion container attached to a parent app entry.

    Introduced in phase-8.1 as a typed placeholder; the loader that
    resolves addons against their ``parent_id`` will land in phase-8.8.
    """

    id: str
    parent_id: str
    source: str
    deployment: DeploymentSpec
    raw: dict[str, Any] = dc_field(default_factory=dict)

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        *,
        source: str = SOURCE_BUILTIN,
    ) -> Addon:
        if not isinstance(raw, dict):
            raise TypeError(f"Addon.from_raw expects a dict, got {type(raw).__name__}")
        name = str(raw.get("name", "")).strip()
        parent_id = str(raw.get("parent_id", "")).strip()
        if not name:
            raise ValueError("Addon.from_raw: entry is missing 'name'")
        if not parent_id:
            raise ValueError(f"Addon.from_raw: entry {name} is missing 'parent_id'")

        # Reuse DeploymentSpec extraction — addons have identical compose shape.
        compose_config = raw.get("compose_config") or {}
        install_limit_raw = raw.get("install_limit", -1)
        try:
            install_limit = int(install_limit_raw)
        except (TypeError, ValueError):
            install_limit = -1

        raw_flags = raw.get("flags")
        flags_dict: dict[str, Any] = raw_flags if isinstance(raw_flags, dict) else {}
        raw_proxy = raw.get("compose_config_proxy")
        proxy_dict = raw_proxy if isinstance(raw_proxy, dict) else None

        deployment = DeploymentSpec(
            compose_config=compose_config if isinstance(compose_config, dict) else {},
            compose_config_proxy=proxy_dict,
            flags=flags_dict,
            install_limit=install_limit,
            compose_layer=str(raw.get("compose_layer") or "service"),
            raw=raw,
        )

        return cls(
            id=name.upper(),
            parent_id=parent_id.upper(),
            source=source,
            deployment=deployment,
            raw=raw,
        )
