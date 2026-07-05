"""Migrate legacy catalog config to the current layout.

Usage::

    python scripts/migrate_catalog_v1_to_v2.py [path]

The *path* may be either:

* ``config/app-config.json`` (pre-8.4.1) - monolithic or standalone
  envelope. Migrates in place to the per-file layout and then folds
  the envelope into ``m4b-config.json -> catalog``.
* ``config/m4b-config.json`` (current) - runs both the monolithic
  split on a sibling ``app-config.json`` (if present) and the fold
  step.

Idempotent. The loader also auto-runs both steps on first load, so
this script is mostly for explicit CI / ops runs.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from money4band.core.catalog_migration import (
    fold_legacy_envelope_into_m4b,
    migrate_catalog_file,
)
from money4band.core.offers_migration import migrate_offers_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default="config/m4b-config.json",
        help=(
            "Path to m4b-config.json or legacy app-config.json "
            "(default: config/m4b-config.json)"
        ),
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

    actions: list[str] = []

    if path.name == "m4b-config.json":
        legacy = path.parent / "app-config.json"
        if legacy.is_file():
            if migrate_catalog_file(legacy):
                actions.append(f"monolithic->per-file: {legacy}")
        if fold_legacy_envelope_into_m4b(path):
            actions.append(f"folded envelope into {path}")
    else:
        if migrate_catalog_file(path):
            actions.append(f"monolithic->per-file: {path}")
        # Try folding if an m4b-config sibling exists.
        m4b = path.parent / "m4b-config.json"
        if m4b.is_file() and fold_legacy_envelope_into_m4b(m4b):
            actions.append(f"folded envelope into {m4b}")

    anchor = path if path.name == "m4b-config.json" else path.parent / "m4b-config.json"
    if anchor.is_file() and migrate_offers_file(anchor):
        actions.append(f"split referral-offers.json -> {anchor.parent / 'offers.d'}")

    if actions:
        for a in actions:
            print(a)
    else:
        print(f"No migration needed: {path} already at current layout.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
