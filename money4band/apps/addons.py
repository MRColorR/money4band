"""Addon lookup helpers.

Addons are companion containers (auto-claim sidecars, etc.) attached to
a parent app via ``parent_id``. They live in per-file bundles under
``config/catalog/addons/<NAME>.json`` and are loaded alongside regular
category entries by the :class:`CatalogSource` pipeline.

This module provides the single lookup point used by both the
configurator (to prompt the user for ``service_enabled``) and the
compose builder (to inject the addon service when the parent is
enabled AND the user opted in). Keeping the lookup centralised ensures
all three interaction surfaces (CLI, menu, REST) observe the same
resolution order.
"""

from __future__ import annotations

from typing import Any


def get_addons_for(
    app_name: str, app_config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return every addon attached to *app_name* (case-insensitive).

    *app_name* is matched against ``addon["parent_id"]`` after upper-casing
    both sides. Empty when the catalog has no addons section or no matches.
    """
    if not app_name:
        return []
    target = app_name.upper()
    addons = app_config.get("addons") or []
    if not isinstance(addons, list):
        return []
    return [
        addon
        for addon in addons
        if isinstance(addon, dict)
        and str(addon.get("parent_id", "")).upper() == target
    ]


__all__ = ["get_addons_for"]
