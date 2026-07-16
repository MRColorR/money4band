from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any

from money4band.core.crypto import decrypt_to_dict, is_encrypted

if TYPE_CHECKING:
    from money4band.apps.schema import CatalogEntry

logger = logging.getLogger(__name__)


def load_json_config(config_path_or_dict: Any) -> dict[str, Any]:
    """
    Load JSON config variables from a file or dictionary.

    If the file is encrypted (M4B_ENCRYPTED: prefix), it is decrypted
    transparently before parsing.

    Arguments:
    config_path_or_dict -- the config file path or dictionary

    Returns:
    Dict[str, Any] -- The loaded configuration dictionary.

    Raises:
    FileNotFoundError -- If the config file is not found.
    JSONDecodeError -- If there is an error decoding the JSON file.
    ValueError -- If the config type is invalid or decryption fails.
    """
    if isinstance(config_path_or_dict, str):
        # If config is a string, assume it's a file path and load the JSON file
        try:
            with open(config_path_or_dict, encoding="utf-8") as f:
                logger.debug("Loading config from file: %s", config_path_or_dict)
                content = f.read()

            if is_encrypted(content):
                logger.debug("Decrypting encrypted config: %s", config_path_or_dict)
                return decrypt_to_dict(content)

            parsed: dict[str, Any] = json.loads(content)
            return parsed
        except FileNotFoundError:
            logger.error("Config file %s not found.", config_path_or_dict)
            raise
        except json.JSONDecodeError:
            logger.error("Error decoding JSON from %s", config_path_or_dict)
            raise
        except Exception as e:
            logger.error(
                "An unexpected error occurred when loading %s: %s",
                config_path_or_dict,
                e,
            )
            raise
    elif isinstance(config_path_or_dict, dict):
        # If config is a dictionary, assume it's already loaded and return it directly
        logger.debug("Using provided config dictionary")
        return config_path_or_dict
    else:
        raise ValueError(
            "Invalid config type. Config must be a file path or a dictionary."
        )


def get_all_app_categories(app_config: dict[str, Any]) -> list[str]:
    """Return *all* category keys that carry an ``entries`` list."""
    return [
        key
        for key, val in app_config.items()
        if isinstance(val, dict) and "entries" in val
    ]


def load_app_config_with_overlays(
    config_path: str,
    apps_d_dir: str | None = None,
    user_config_path: str | None = None,
) -> dict[str, Any]:
    """Load the catalog envelope + per-file bundles and merge community apps.

    Aggregation pipeline:

    1. If *config_path* still points at a legacy standalone envelope
       file, one-shot auto-migrate it: first to the per-file layout,
       then fold the envelope into ``m4b-config.json -> catalog``. The
       legacy file is renamed with a ``.v1.bak`` suffix.
    2. Read the payload and extract its envelope (unwrap the
       ``catalog`` key if it's an m4b-config payload).
    3. Overlay user-owned catalog overrides from
       ``user-config.json -> catalog_overrides`` (source enable/disable,
       custom user-added sources, category activation, removals).
    4. Expand the envelope into the in-memory shape
       ``{<category>: {"active": bool, "entries": [...]}}`` by reading
       ``config/catalog/<category>/*.json`` via the pluggable
       ``CatalogSource`` interface.
    5. Overlay hand-written community apps from ``config/apps.d/``
       (falls back to ``os.path.dirname(config_path) + "/apps.d"``).

    Consumers that access ``app_config["supported"]["entries"]`` keep
    working unchanged - the shape is identical.
    """
    from money4band.apps.sources import aggregate_from_sources
    from money4band.core.catalog_migration import (
        fold_legacy_envelope_into_m4b,
        migrate_catalog_file,
    )
    from money4band.core.catalog_overrides import (
        apply_overrides,
        load_user_overrides,
    )
    from money4band.core.catalog_store import (
        extract_envelope,
        is_envelope,
        is_legacy_monolithic,
    )

    # One-shot migrations. Load the payload once and only re-read after a
    # migration actually rewrote the file - migrate_catalog_file used to
    # fully parse m4b-config.json a second time on EVERY load just to
    # conclude "already migrated".
    payload = load_json_config(config_path)
    if is_legacy_monolithic(payload) and not is_envelope(payload):
        migrate_catalog_file(config_path)
        payload = load_json_config(config_path)
    if fold_legacy_envelope_into_m4b(config_path):
        payload = load_json_config(config_path)

    # Either already an envelope / folded m4b-config (normal path) or
    # still monolithic (migration skipped - e.g. tests that pass an
    # in-memory dict directly).
    if is_envelope(payload):
        envelope = extract_envelope(payload)
        # Apply user-owned overrides before aggregation so the shaped
        # output reflects the effective state.
        if user_config_path is None:
            sibling = os.path.join(os.path.dirname(config_path), "user-config.json")
            if os.path.isfile(sibling):
                user_config_path = sibling
        overrides = load_user_overrides(user_config_path)
        if overrides:
            envelope = apply_overrides(envelope, overrides)
        config = aggregate_from_sources(envelope, config_path)
    else:
        config = payload

    if apps_d_dir is None:
        apps_d_dir = os.path.join(os.path.dirname(config_path), "apps.d")

    if os.path.isdir(apps_d_dir):
        from money4band.apps.schema import merge_community_apps

        config = merge_community_apps(config, apps_d_dir)

    return config


def resolve_catalog_config(
    app_config_path_or_dict: Any,
    user_config_path: str | None = None,
) -> dict[str, Any]:
    """Return the aggregated catalog shape from a path or a loaded dict.

    Accepts either the already-aggregated shape (top-level categories with
    ``entries`` - e.g. a per-instance ``app-config.json``) or the
    m4b-config file whose catalog is folded under its ``catalog`` key. The
    folded shape MUST go through :func:`load_app_config_with_overlays` - a
    plain ``load_json_config`` on it yields zero app categories and
    consumers (compose/.env builders, profile resolution) would silently
    produce an app-less stack.
    """
    if isinstance(app_config_path_or_dict, str):
        payload = load_json_config(app_config_path_or_dict)
        if get_all_app_categories(payload):
            # Already aggregated on disk (per-instance app-config.json).
            # Do NOT route through the overlay loader: its one-shot
            # migration would treat this shape as legacy-monolithic and
            # destructively split/rename the file.
            return payload
        return load_app_config_with_overlays(
            app_config_path_or_dict, user_config_path=user_config_path
        )
    if isinstance(app_config_path_or_dict, dict):
        if "catalog" in app_config_path_or_dict and not get_all_app_categories(
            app_config_path_or_dict
        ):
            raise ValueError(
                "Raw folded m4b-config passed as app catalog - aggregate it "
                "with load_app_config_with_overlays() first, otherwise no "
                "app would be generated."
            )
        return app_config_path_or_dict
    raise ValueError(
        "Invalid app catalog: expected a config file path or a dictionary."
    )


def is_category_active(app_config: dict[str, Any], category: str) -> bool:
    """Return whether *category* is marked active."""
    cat = app_config.get(category)
    if isinstance(cat, dict):
        return bool(cat.get("active", False))
    return False


def get_active_app_categories(app_config: dict[str, Any]) -> list[str]:
    """Return the list of active app category keys from *app_config*.

    Each category is a dict with ``"active": true/false`` and
    ``"entries": [...]``.  Only categories marked active are returned.
    """
    return [
        key
        for key, val in app_config.items()
        if isinstance(val, dict) and val.get("active", False) and "entries" in val
    ]


def get_category_entries(
    app_config: dict[str, Any], category: str
) -> list[dict[str, Any]]:
    """Return the entries list for *category*, or ``[]`` if missing."""
    cat = app_config.get(category)
    if isinstance(cat, dict):
        entries: list[dict[str, Any]] = cat.get("entries", [])
        return entries
    return []


def get_install_limit(app_entry: dict[str, Any]) -> int:
    """Return the install_limit for an app entry (-1 = unlimited)."""
    return int(app_entry.get("install_limit", -1))


def load_catalog_entries(
    app_config: dict[str, Any],
    *,
    categories: list[str] | None = None,
) -> list[CatalogEntry]:
    """Return typed :class:`CatalogEntry` objects for *app_config*.

    Existing consumers that use :func:`get_category_entries` keep working
    unchanged - this function simply wraps the same dicts in dataclasses.

    Arguments:
    app_config -- previously loaded catalog config (post-overlay merge).
    categories -- explicit list of category keys to include.  When
        ``None`` (default), every category that carries an ``entries``
        list is included regardless of its ``active`` flag - callers that
        want only active ones should filter the result on ``.category``
        after calling :func:`get_active_app_categories`.
    """
    from money4band.apps.schema import SOURCE_BUILTIN, CatalogEntry

    if categories is None:
        categories = get_all_app_categories(app_config)

    out: list[CatalogEntry] = []
    for cat_key in categories:
        for raw in get_category_entries(app_config, cat_key):
            if not isinstance(raw, dict):
                continue
            try:
                out.append(
                    CatalogEntry.from_raw(raw, source=SOURCE_BUILTIN, category=cat_key)
                )
            except (TypeError, ValueError) as exc:
                logger.warning("Skipping invalid catalog entry in %s: %s", cat_key, exc)
    return out
