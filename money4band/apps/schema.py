from __future__ import annotations

import json
import logging
import os
import re
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

    Community apps are placed into the ``candidate-apps`` category.
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

    # Ensure candidate-apps category exists
    if "candidate-apps" not in app_config:
        app_config["candidate-apps"] = {"active": False, "entries": []}
    candidates = app_config["candidate-apps"]
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
        logger.info("Merged %d community app(s) into candidate-apps", added)

    return app_config
