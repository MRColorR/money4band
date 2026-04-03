#!/usr/bin/env python3
"""Synchronise requirements.txt and requirements-dev.txt from uv.lock.

Usage (from project root):
    python scripts/sync_requirements.py            # overwrite files
    python scripts/sync_requirements.py --check     # exit 1 if stale (CI / pre-commit)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS: list[tuple[Path, list[str]]] = [
    (
        ROOT / "requirements.txt",
        ["uv", "export", "--format", "requirements-txt", "--no-hashes", "--no-emit-project", "--frozen"],
    ),
    (
        ROOT / "requirements-dev.txt",
        ["uv", "export", "--format", "requirements-txt", "--no-hashes", "--no-emit-project", "--frozen", "--group", "dev"],
    ),
]


def _generate(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=ROOT)  # noqa: S603
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync requirements from uv.lock")
    parser.add_argument("--check", action="store_true", help="Exit 1 if files are stale (CI mode)")
    args = parser.parse_args()

    stale = False
    for path, cmd in TARGETS:
        expected = _generate(cmd)
        current = path.read_text(encoding="utf-8") if path.exists() else ""

        if current == expected:
            continue

        if args.check:
            print(f"\u274c {path.name} is out-of-date")
            stale = True
        else:
            path.write_text(expected, encoding="utf-8")
            print(f"\u2705 Updated {path.name}")

    if args.check and stale:
        print("\nRun: python scripts/sync_requirements.py")
        return 1

    if not stale and args.check:
        print("\u2705 All requirements files are up-to-date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
