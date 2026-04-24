"""Aggregate per-file catalog bundles into a single ``manifest.json``.

This script is the shared wire-format builder for all three M4B catalog
repositories:

- ``money4band``                  — core, ToS-compliant apps
- ``money4band-community-catalog`` — community apps + addons
- ``openpassivehub-catalog``      — broad public ecosystem listing

Each repo keeps its catalog as one JSON file per entry under
``catalog/<category>/<NAME>.json`` (and optionally ``addons/<NAME>.json``).
This script walks that tree and emits a single aggregated ``manifest.json``
that :class:`money4band.apps.sources.RemoteSource` can fetch in one HTTP
round-trip with ``ETag`` / ``If-None-Match`` caching.

Usage
-----

.. code-block:: bash

    python scripts/build_manifest.py                    # writes manifest.json at repo root
    python scripts/build_manifest.py --root <dir>       # override repo root
    python scripts/build_manifest.py --output <path>    # override output path
    python scripts/build_manifest.py --check            # fail if on-disk manifest is stale

The output shape mirrors the category-envelope form that
``RemoteSource`` understands natively, so no translation is needed on
the client side::

    {
      "app_config_version": 2.0,
      "generated_at": "2026-04-24T00:00:00Z",
      "source": "money4band-community-catalog",
      "supported":  {"entries": [...]},
      "newcomers":  {"entries": [...]},
      "deprecated": {"entries": [...]},
      "addons":     {"entries": [...]}
    }

The ``addons`` key is optional and only present when an ``addons/``
directory exists at the repo root.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

APP_CONFIG_VERSION = 2.0
CATEGORIES: tuple[str, ...] = ("supported", "newcomers", "deprecated")
ADDONS_DIR = "addons"


def _load_bundles(root: Path) -> list[dict]:
    """Load every ``*.json`` file in ``root`` (non-recursive).

    Returns a list of parsed JSON dicts, sorted by filename so the
    manifest is byte-reproducible across runs.
    """
    if not root.is_dir():
        return []
    out: list[dict] = []
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"warn: skipping {path}: {exc}", file=sys.stderr)
            continue
        if isinstance(data, dict):
            out.append(data)
    return out


def build_manifest(root: Path, *, source_name: str | None = None) -> dict:
    """Walk ``root`` and produce the aggregated manifest payload."""
    payload: dict = {
        "app_config_version": APP_CONFIG_VERSION,
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "source": source_name or root.name,
    }
    catalog_dir = root / "catalog"
    for cat in CATEGORIES:
        payload[cat] = {"entries": _load_bundles(catalog_dir / cat)}
    addons = _load_bundles(root / ADDONS_DIR)
    if addons:
        payload[ADDONS_DIR] = {"entries": addons}
    return payload


def _dump(payload: dict) -> str:
    """Serialize manifest with stable formatting."""
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root containing catalog/ (default: cwd)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file (default: <root>/manifest.json)",
    )
    parser.add_argument(
        "--source-name",
        default=None,
        help="Logical source name (default: repo directory name)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if the on-disk manifest is stale",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    output = Path(args.output) if args.output else root / "manifest.json"

    payload = build_manifest(root, source_name=args.source_name)

    # Strip volatile fields for --check comparison (generated_at changes each run).
    def _stable(p: dict) -> dict:
        return {k: v for k, v in p.items() if k != "generated_at"}

    rendered = _dump(payload)

    if args.check:
        if not output.is_file():
            print(f"error: {output} is missing", file=sys.stderr)
            return 1
        existing = json.loads(output.read_text(encoding="utf-8"))
        if _stable(existing) != _stable(payload):
            print(f"error: {output} is stale — run build_manifest.py", file=sys.stderr)
            return 1
        print(f"{output}: up to date")
        return 0

    output.write_text(rendered, encoding="utf-8")
    total = sum(len(payload.get(c, {}).get("entries", [])) for c in CATEGORIES)
    if "addons" in payload:
        total += len(payload["addons"]["entries"])
    print(f"wrote {output} ({total} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
