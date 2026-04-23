"""Migrate a legacy monolithic ``app-config.json`` to per-file v2 layout.

Usage::

    python scripts/migrate_catalog_v1_to_v2.py [path/to/app-config.json]

Idempotent. The loader also auto-runs this on first load, so this script
is mostly for explicit CI / ops runs.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from money4band.core.catalog_migration import migrate_catalog_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default="config/app-config.json",
        help="Path to app-config.json (default: config/app-config.json)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    path = Path(args.path)
    if not path.is_file():
        print(f"Not found: {path}", file=sys.stderr)
        return 2

    migrated = migrate_catalog_file(path)
    if migrated:
        print(f"Migrated {path} to per-file layout.")
    else:
        print(f"No migration needed: {path} is already in v2 layout.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
