#!/usr/bin/env python3
"""Regenerate the app tables in README.md and docs/APPS.md.

Merges three sources so the README reflects the **full ecosystem**, not
just the core repo:

1. ``money4band`` core - `config/m4b-config.json` (15 supported apps).
2. ``money4band-community-catalog`` - sibling repo's `manifest.json`
   (community-supported + community-deprecated + addons).
3. ``openpassivehub-catalog`` - sibling repo's `manifest.json`
   (newcomers with no Docker image yet).

Each merged entry is tagged with a ``_source`` field so the table
generator can render the per-row indicator emoji
([ok] core | [com] community | [new] newcomer | [x] deprecated).

Sibling repos are looked up at ``<money4band-parent>/<sibling>/manifest.json``.
Missing siblings are skipped silently with a one-line warning - the
script still produces a core-only table in that case.

Usage (from project root):
    python scripts/update_tables.py [--check] [--core-only]

Flags:
    --check       Verify tables are up-to-date without writing (exit 1 if stale).
    --core-only   Skip sibling sources (regenerate from core m4b-config.json only).
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from money4band.core.loader import load_app_config_with_overlays  # noqa: E402
from money4band.readme_generator import update_apps_md, update_readme  # noqa: E402

# Sibling repos to fold into the table. Looked up relative to the M4B
# parent directory (``ROOT.parent``).
_SIBLING_SOURCES: dict[str, str] = {
    "community": "money4band-community-catalog",
    "openpassivehub": "openpassivehub-catalog",
}

# Categories whose entries we want in the README/APPS table. ``addons``
# (sidecars) are excluded - they're infrastructure helpers, not apps.
_TABLE_CATEGORIES: tuple[str, ...] = ("supported", "newcomers", "deprecated")


def load_core_config() -> dict[str, Any]:
    config_path = ROOT / "config" / "m4b-config.json"
    return load_app_config_with_overlays(str(config_path))


def _tag_entries(config: dict[str, Any], source: str) -> dict[str, Any]:
    """Return a deep copy of *config* with ``_source`` injected on each entry."""
    tagged = copy.deepcopy(config)
    for cat in _TABLE_CATEGORIES:
        cat_block = tagged.get(cat)
        if not isinstance(cat_block, dict):
            continue
        for entry in cat_block.get("entries") or []:
            if isinstance(entry, dict):
                entry["_source"] = source
    return tagged


def _merge_sibling(combined: dict[str, Any], sibling_manifest: dict[str, Any]) -> None:
    """Append sibling-tagged entries into the combined config's per-category lists."""
    for cat in _TABLE_CATEGORIES:
        block = sibling_manifest.get(cat)
        if not isinstance(block, dict):
            continue
        sibling_entries = block.get("entries") or []
        if not sibling_entries:
            continue
        combined.setdefault(cat, {"active": False, "entries": []})
        target = combined[cat].setdefault("entries", [])
        target.extend(sibling_entries)


def load_combined_config(*, core_only: bool = False) -> dict[str, Any]:
    """Build the merged multi-source app_config used by the generators."""
    combined = _tag_entries(load_core_config(), "core")
    if core_only:
        return combined

    parent = ROOT.parent
    for source_label, sibling_dir in _SIBLING_SOURCES.items():
        manifest_path = parent / sibling_dir / "manifest.json"
        if not manifest_path.is_file():
            print(f"[!]  Sibling missing: {manifest_path} - skipping {source_label}")
            continue
        try:
            sibling_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"[!]  Could not read {manifest_path}: {exc}")
            continue
        _merge_sibling(combined, _tag_entries(sibling_raw, source_label))

    return combined


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate app tables in docs")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if tables are stale (CI mode)",
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Skip sibling community/openpassivehub manifests",
    )
    args = parser.parse_args()

    app_config = load_combined_config(core_only=args.core_only)

    readme_path = ROOT / "README.md"
    apps_md_path = ROOT / "docs" / "APPS.md"

    if args.check:
        readme_before = readme_path.read_text(encoding="utf-8")
        apps_md_before = (
            apps_md_path.read_text(encoding="utf-8") if apps_md_path.exists() else ""
        )

        update_readme(app_config, readme_path)
        if apps_md_path.exists():
            update_apps_md(app_config, apps_md_path)

        readme_after = readme_path.read_text(encoding="utf-8")
        apps_md_after = (
            apps_md_path.read_text(encoding="utf-8") if apps_md_path.exists() else ""
        )

        readme_path.write_text(readme_before, encoding="utf-8")
        if apps_md_path.exists():
            apps_md_path.write_text(apps_md_before, encoding="utf-8")

        stale = False
        if readme_before != readme_after:
            print("[x] README.md app table is stale")
            stale = True
        if apps_md_before != apps_md_after:
            print("[x] docs/APPS.md app table is stale")
            stale = True

        if stale:
            print("\nRun: python scripts/update_tables.py")
            return 1

        print("[ok] All app tables are up-to-date")
        return 0

    ok = True
    if update_readme(app_config, readme_path):
        print(f"[ok] Updated {readme_path}")
    else:
        print(f"[!]  Could not update {readme_path}")
        ok = False

    if apps_md_path.exists():
        if update_apps_md(app_config, apps_md_path):
            print(f"[ok] Updated {apps_md_path}")
        else:
            print(f"[!]  Could not update {apps_md_path}")
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
