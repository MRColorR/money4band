"""Compute per-contributor weights from the repo's git history.

Writes ``config/weights.json`` consumed by
:mod:`money4band.apps.contributor_pool`.

Algorithm: sliding window ``[reference_ts - WINDOW_DAYS, reference_ts
- AGE_FLOOR_DAYS]`` anchored to the latest commit timestamp (never to
wall clock — the pool stays non-empty even after long quiet periods).
The ``AGE_FLOOR_DAYS`` cooldown drops the most recent commits so a
last-minute push-burst can't inflate weights. Inside the window, each
commit is worth ``min(10, insertions + 0.5*deletions)``, capped at
``8`` per author per UTC day, then half-life-decayed (180d) toward
``reference_ts``. Authors under ``MIN_WEIGHT`` are dropped (no floor —
stale contributors fall out instead of pinning at a fixed minimum).

Identity: the script aggregates by lowercased + whitespace-collapsed
author name (``%aN``). ``--use-mailmap`` is passed to ``git log`` so a
future ``.mailmap`` (none today) would take effect transparently. Bots
(``[bot]`` in name or email) are filtered before aggregation.

Usage
-----

.. code-block:: bash

    python scripts/compute_weights.py                   # writes <root>/config/weights.json
    python scripts/compute_weights.py --root <dir>      # work in another repo
    python scripts/compute_weights.py --output <path>   # custom output path
    python scripts/compute_weights.py --check           # fail if on-disk is stale
    python scripts/compute_weights.py --dry-run         # print to stdout, no write
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PER_COMMIT_CAP: float = 10.0
PER_AUTHOR_DAILY_CAP: float = 8.0
HALF_LIFE_DAYS: float = 180.0
WINDOW_DAYS: int = 365
AGE_FLOOR_DAYS: int = 7
MIN_WEIGHT: float = 10.0

_BOT_PATTERN: re.Pattern[str] = re.compile(r"\[bot\]", re.IGNORECASE)


@dataclass(frozen=True)
class _Commit:
    author: str
    ts: int
    value: float


def _run(cmd: list[str], *, cwd: Path) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def _normalize_author(name: str) -> str:
    return " ".join(name.split()).lower()


def _is_bot(name: str, email: str) -> bool:
    return bool(_BOT_PATTERN.search(name) or _BOT_PATTERN.search(email))


def read_git_commits(root: Path) -> list[_Commit]:
    out = _run(
        [
            "git",
            "log",
            "--no-merges",
            "--use-mailmap",
            "--numstat",
            "--pretty=format:@COMMIT@%H|%at|%aN|%aE",
        ],
        cwd=root,
    )
    commits: list[_Commit] = []
    author = ""
    ts = 0
    ins_total = 0
    del_total = 0
    have_header = False
    skip_commit = False

    def flush() -> None:
        if have_header and author and not skip_commit:
            raw = ins_total + 0.5 * del_total
            capped = min(PER_COMMIT_CAP, raw)
            commits.append(_Commit(author=author, ts=ts, value=float(capped)))

    for line in out.splitlines():
        line = line.rstrip()
        if line.startswith("@COMMIT@"):
            flush()
            payload = line[len("@COMMIT@") :]
            try:
                _sha, ts_s, raw_name, raw_email = payload.split("|", 3)
                ts = int(ts_s)
                skip_commit = _is_bot(raw_name, raw_email)
                author = _normalize_author(raw_name)
                ins_total = 0
                del_total = 0
                have_header = True
            except ValueError:
                have_header = False
            continue
        if not have_header or not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        try:
            ins = 0 if parts[0] in {"-", ""} else int(parts[0])
            dele = 0 if parts[1] in {"-", ""} else int(parts[1])
        except ValueError:
            continue
        ins_total += ins
        del_total += dele
    flush()
    return commits


def _utc_day(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def compute_weights(commits: list[_Commit]) -> dict[str, float]:
    """Aggregate *commits* into per-author weights using the sliding window.

    Window and decay are anchored to ``max(c.ts for c in commits)`` so
    the pool is never empty even after long quiet periods.
    """
    if not commits:
        return {}

    reference_ts = max(c.ts for c in commits)
    oldest_ts = reference_ts - WINDOW_DAYS * 86400
    newest_ts = reference_ts - AGE_FLOOR_DAYS * 86400

    in_window = [c for c in commits if oldest_ts <= c.ts <= newest_ts]
    if not in_window:
        return {}

    daily: dict[tuple[str, str], list[_Commit]] = defaultdict(list)
    for c in in_window:
        daily[(c.author, _utc_day(c.ts))].append(c)

    totals: dict[str, float] = defaultdict(float)
    for (author, _day), bucket in daily.items():
        raw_sum = 0.0
        representative_ts = bucket[0].ts
        for c in sorted(bucket, key=lambda x: x.ts):
            remaining = PER_AUTHOR_DAILY_CAP - raw_sum
            if remaining <= 0:
                break
            take = min(remaining, c.value)
            raw_sum += take
            representative_ts = c.ts

        age_days = max(0, reference_ts - representative_ts) / 86400.0
        decay = math.exp(-math.log(2) * age_days / HALF_LIFE_DAYS)
        totals[author] += raw_sum * decay

    out: dict[str, float] = {}
    for author, raw in totals.items():
        if raw < MIN_WEIGHT:
            continue
        out[author] = round(raw, 4)
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def _render(weights: dict[str, float]) -> str:
    return json.dumps(weights, indent=2, sort_keys=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="Repository root (default: cwd)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (default: <root>/config/weights.json)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if the on-disk weights.json is stale",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print to stdout instead of writing",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    output = Path(args.output) if args.output else root / "config" / "weights.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        commits = read_git_commits(root)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"error: git log failed: {exc}", file=sys.stderr)
        return 1

    weights = compute_weights(commits)
    rendered = _render(weights)

    if args.dry_run:
        sys.stdout.write(rendered)
        return 0

    if args.check:
        if not output.is_file():
            print(f"error: {output} missing", file=sys.stderr)
            return 1
        existing = output.read_text(encoding="utf-8")
        if existing.strip() != rendered.strip():
            print(f"error: {output} is stale", file=sys.stderr)
            return 1
        print(f"{output}: up to date")
        return 0

    output.write_text(rendered, encoding="utf-8")
    print(f"wrote {output} ({len(weights)} contributors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
