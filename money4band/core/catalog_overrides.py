"""User-config catalog overrides.

``m4b-config.json`` ships the *default* catalog envelope (sources and
category flags). Anything the user toggles or adds at runtime — source
``enabled`` flags, custom remote sources, category activation, removals
— lives under ``user-config.json → catalog_overrides``. That split lets
updates overwrite ``m4b-config.json`` without touching user state.

Override schema (``user-config.json → catalog_overrides``)::

    {
        "sources": {
            "community": {"enabled": false},           # tweak shipped
            "mycustom":  {                             # user-added
                "type": "remote",
                "url": "...",
                "enabled": true,
                "cache_path": "catalog/mycustom",
                "timeout": 5.0,
                "default_source": "mycustom"
            }
        },
        "removed_sources": ["community"],              # shipped names
                                                        # the user deleted
        "categories": {
            "supported": {"active": false}
        }
    }

Any key may be absent — ``apply_overrides`` tolerates missing sections.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from money4band.core.crypto import decrypt_to_dict, encrypt_dict, is_encrypted

logger = logging.getLogger(__name__)

OVERRIDE_KEY = "catalog_overrides"
_SOURCE_OVERRIDE_FIELDS = ("enabled", "url", "cache_path", "timeout")


# ---------------------------------------------------------------------------
# User-config I/O (encryption-aware, but never writes plaintext back).
# ---------------------------------------------------------------------------


def _read_user_config(user_config_path: str | Path) -> dict[str, Any]:
    path = Path(user_config_path)
    if not path.is_file():
        return {}
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("catalog_overrides: cannot read %s: %s", path, exc)
        return {}
    try:
        if is_encrypted(content):
            return decrypt_to_dict(content)
        return json.loads(content)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("catalog_overrides: cannot parse %s: %s", path, exc)
        return {}


def _write_user_config(
    user_config_path: str | Path, payload: dict[str, Any]
) -> None:
    path = Path(user_config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Preserve encryption-at-rest: if the current file is encrypted, re-encrypt
    # after mutation; otherwise stay plaintext and let the usual lifecycle
    # hooks (``ensure_config_encrypted``) handle encryption on exit.
    try:
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    except OSError:
        existing = ""

    if existing and is_encrypted(existing):
        path.write_text(encrypt_dict(payload), encoding="utf-8")
        return
    path.write_text(
        json.dumps(payload, indent=4, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def load_user_overrides(user_config_path: str | Path | None) -> dict[str, Any]:
    """Return the ``catalog_overrides`` sub-dict (empty if missing/absent)."""
    if not user_config_path:
        return {}
    cfg = _read_user_config(user_config_path)
    overrides = cfg.get(OVERRIDE_KEY) or {}
    return overrides if isinstance(overrides, dict) else {}


def save_user_overrides(
    user_config_path: str | Path, overrides: dict[str, Any]
) -> None:
    """Persist ``catalog_overrides`` into the user-config file in place."""
    cfg = _read_user_config(user_config_path)
    if overrides:
        cfg[OVERRIDE_KEY] = overrides
    else:
        cfg.pop(OVERRIDE_KEY, None)
    _write_user_config(user_config_path, cfg)


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------


def apply_overrides(
    envelope: dict[str, Any],
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return a copy of *envelope* with user *overrides* applied.

    - For each shipped source whose name appears in ``overrides["sources"]``,
      fields in ``_SOURCE_OVERRIDE_FIELDS`` are overlaid (other fields in
      the override dict are ignored for shipped sources to avoid schema
      drift).
    - Source names in ``overrides["removed_sources"]`` are dropped.
    - Override entries whose name is not already shipped are appended as
      user-added sources, with all their declared fields intact.
    - For each category in ``overrides["categories"]``, the ``active``
      flag is overlaid.
    """
    merged = json.loads(json.dumps(envelope))  # deep copy
    if not overrides or not isinstance(overrides, dict):
        return merged

    src_overrides = overrides.get("sources") or {}
    removed = set(overrides.get("removed_sources") or [])
    cat_overrides = overrides.get("categories") or {}

    shipped_sources = merged.get("catalog_sources") or []
    if not isinstance(shipped_sources, list):
        shipped_sources = []

    # --- sources ---------------------------------------------------------
    result_sources: list[dict[str, Any]] = []
    shipped_names: set[str] = set()
    for src in shipped_sources:
        if not isinstance(src, dict):
            result_sources.append(src)
            continue
        name = src.get("name")
        if name in removed:
            continue
        shipped_names.add(name)
        override = src_overrides.get(name) if isinstance(src_overrides, dict) else None
        if isinstance(override, dict):
            for key in _SOURCE_OVERRIDE_FIELDS:
                if key in override:
                    src[key] = override[key]
        result_sources.append(src)

    # User-added sources (names not in shipped).
    if isinstance(src_overrides, dict):
        for name, decl in src_overrides.items():
            if name in shipped_names or not isinstance(decl, dict):
                continue
            # A user-added remote/local source needs at minimum a type + target.
            if decl.get("type") not in ("local", "remote"):
                continue
            if decl["type"] == "remote" and not decl.get("url"):
                continue
            if decl["type"] == "local" and not decl.get("path"):
                continue
            added = dict(decl)
            added["name"] = name
            added.setdefault("enabled", True)
            added.setdefault(
                "default_source",
                "builtin" if added["type"] == "local" else name,
            )
            result_sources.append(added)

    merged["catalog_sources"] = result_sources

    # --- categories ------------------------------------------------------
    merged_cats = merged.get("categories") or {}
    if isinstance(merged_cats, dict) and isinstance(cat_overrides, dict):
        for cat_name, override in cat_overrides.items():
            if not isinstance(override, dict):
                continue
            existing = merged_cats.get(cat_name)
            if not isinstance(existing, dict):
                existing = {}
                merged_cats[cat_name] = existing
            if "active" in override:
                existing["active"] = bool(override["active"])
    merged["categories"] = merged_cats

    return merged


__all__ = [
    "OVERRIDE_KEY",
    "apply_overrides",
    "load_user_overrides",
    "save_user_overrides",
]
