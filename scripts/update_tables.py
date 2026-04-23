#!/usr/bin/env python3
"""Regenerate the app tables in README.md and docs/APPS.md from app-config.json.

Usage (from project root):
    python scripts/update_tables.py [--check]

Flags:
    --check   Verify tables are up-to-date without writing (exit 1 if stale).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Force UTF-8 on stdout/stderr so emoji/unicode logging works under Windows cp1252.
for _stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(_stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from money4band.core.loader import load_app_config_with_overlays  # noqa: E402
from money4band.readme_generator import update_apps_md, update_readme  # noqa: E402


def load_app_config() -> dict:
    config_path = ROOT / "config" / "app-config.json"
    return load_app_config_with_overlays(str(config_path))


def files_changed(readme: Path, apps_md: Path) -> tuple[str, str]:
    """Return (before, after) content for both files."""
    return readme.read_text(encoding="utf-8"), apps_md.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate app tables in docs")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if tables are stale (CI mode)",
    )
    args = parser.parse_args()

    app_config = load_app_config()

    readme_path = ROOT / "README.md"
    apps_md_path = ROOT / "docs" / "APPS.md"

    if args.check:
        # Snapshot current content
        readme_before = readme_path.read_text(encoding="utf-8")
        apps_md_before = (
            apps_md_path.read_text(encoding="utf-8") if apps_md_path.exists() else ""
        )

        # Regenerate in place
        update_readme(app_config, readme_path)
        if apps_md_path.exists():
            update_apps_md(app_config, apps_md_path)

        readme_after = readme_path.read_text(encoding="utf-8")
        apps_md_after = (
            apps_md_path.read_text(encoding="utf-8") if apps_md_path.exists() else ""
        )

        # Restore originals
        readme_path.write_text(readme_before, encoding="utf-8")
        if apps_md_path.exists():
            apps_md_path.write_text(apps_md_before, encoding="utf-8")

        stale = False
        if readme_before != readme_after:
            print("❌ README.md app table is stale")
            stale = True
        if apps_md_before != apps_md_after:
            print("❌ docs/APPS.md app table is stale")
            stale = True

        if stale:
            print("\nRun: python scripts/update_tables.py")
            return 1

        print("✅ All app tables are up-to-date")
        return 0

    # Normal mode: update in place
    ok = True
    if update_readme(app_config, readme_path):
        print(f"✅ Updated {readme_path}")
    else:
        print(f"⚠  Could not update {readme_path}")
        ok = False

    if apps_md_path.exists():
        if update_apps_md(app_config, apps_md_path):
            print(f"✅ Updated {apps_md_path}")
        else:
            print(f"⚠  Could not update {apps_md_path}")
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
