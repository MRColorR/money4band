"""Merge per-app ``user_config_template`` slices from the catalog into user-config.

Each catalog entry carries a ``user_config_template`` field - the default
user-config slice for that app.  This module provides the single seam that
materialises those defaults into the live ``user-config.json``.

The merge is **non-destructive**:

* Existing user values are never overwritten.
* Only missing keys are filled in from the template.
* Apps already present in user-config keep all their keys (including
  credentials, ports, sidecar flags) - so removing or moving an app out
  of the catalog does not orphan its stored credentials.

Usage:

    >>> from money4band.apps.user_config_merger import apply_user_config_templates
    >>> apply_user_config_templates(user_config, app_config)

The function mutates ``user_config`` in place and returns the number of
keys that were newly populated (useful for logging on first-run).
"""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _iter_catalog_entries(app_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten all catalog entries across the v2.0 categories."""
    out: list[dict[str, Any]] = []
    for cat in ("supported", "newcomers", "deprecated"):
        block = app_config.get(cat)
        if not isinstance(block, dict):
            continue
        entries = block.get("entries")
        if isinstance(entries, list):
            out.extend(e for e in entries if isinstance(e, dict) and "name" in e)
    return out


def apply_user_config_templates(
    user_config: dict[str, Any],
    app_config: dict[str, Any],
) -> int:
    """Populate missing per-app slices in ``user_config`` from the catalog.

    Parameters
    ----------
    user_config
        The live user-config dictionary.  Mutated in place.
    app_config
        The aggregated catalog dict (from ``m4b-config.json``).  Read-only.

    Returns
    -------
    int
        Number of apps that gained a brand-new slice (i.e. apps previously
        absent from ``user_config["apps"]``).  Apps that already existed
        but gained new keys are counted in log output, not the return.
    """
    apps = user_config.setdefault("apps", {})
    if not isinstance(apps, dict):
        logger.warning("user_config['apps'] is not a dict; resetting to empty dict")
        apps = {}
        user_config["apps"] = apps

    new_app_count = 0
    filled_key_count = 0

    for entry in _iter_catalog_entries(app_config):
        app_name = str(entry["name"]).lower()
        template = entry.get("user_config_template")
        if not isinstance(template, dict):
            # Apps without a template (no credentials, no ports, no sidecar)
            # still get an ``{"enabled": false}`` stub.
            template = {"enabled": False}

        current = apps.get(app_name)
        if not isinstance(current, dict):
            # Brand-new app - deep-copy the template so later mutations do
            # not alias back into the catalog.
            apps[app_name] = copy.deepcopy(template)
            new_app_count += 1
            continue

        # Fill only missing keys; never overwrite existing user values.
        for key, default in template.items():
            if key not in current:
                current[key] = copy.deepcopy(default)
                filled_key_count += 1

    if new_app_count or filled_key_count:
        logger.info(
            "Applied user_config_template defaults: %d new app slice(s), "
            "%d missing key(s) filled",
            new_app_count,
            filled_key_count,
        )
    return new_app_count
