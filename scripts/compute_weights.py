"""Compute per-contributor weights from the repo's git history.

Phase-8.6 of the catalog split plan. Writes ``weights.json`` at the
repo root, consumed by :mod:`money4band.apps.contributor_pool`.

Algorithm (locked in plan.md)
-----------------------------

- ALL commits count (any file, any path) — the more you contribute to
  the repo the more weight your referral link earns.
- Per-commit value::

      value(c) = min(10, insertions(c) + 0.5 * deletions(c))

- Per-author per-day **cap**: 8 points total. This discourages
  artificial commit-spam; a real author's day caps naturally.
- Age **floor**: commits younger than 7 days do not count yet (gives
  PRs a short grace period and avoids CI-loop double-counting).
- Age **decay** (half-life 180 days)::

      decay(age_days) = exp(-ln2 * age_days / 180)

- Total weight::

      weight(author) = max(0.1, sum(value(c) * decay(age(c))))

The same script is shipped verbatim in each of the three M4B repos
(``money4band``, ``money4band-community-catalog``,
``openpassivehub-catalog``) so weights can be computed independently
for each repo.

Usage
-----

.. code-block:: bash

    python scripts/compute_weights.py                   # writes weights.json at cwd
    python scripts/compute_weights.py --root <dir>      # work in another repo
    python scripts/compute_weights.py --output <path>   # custom output path
    python scripts/compute_weights.py --check           # fail if on-disk is stale
    python scripts/compute_weights.py --dry-run         # print to stdout, no write
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

#: Maximum raw value a single commit can contribute.
PER_COMMIT_CAP: float = 10.0

#: Maximum raw value a single author can accumulate in one UTC day.
PER_AUTHOR_DAILY_CAP: float = 8.0

#: Minimum age (in days) before a commit is counted at all.
AGE_FLOOR_DAYS: int = 7

#: Half-life of a commit's contribution to the weight.
HALF_LIFE_DAYS: float = 180.0

#: Floor applied to the final per-author weight.
WEIGHT_FLOOR: float = 0.1


@dataclass(frozen=True)
class _Commit:
    author: str
    ts: int  # unix timestamp (author date)
    value: float  # raw per-commit value, already capped at PER_COMMIT_CAP


def _run(cmd: list[str], *, cwd: Path) -> str:
    """Run ``cmd`` in *cwd* and return stdout as text."""
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
    """Return the canonical key used to aggregate per-author weights.

    Lowercased + whitespace-collapsed so casing variants of the same
    git author name (e.g. ``MRColorr`` / ``MRColorR`` / ``mrcolorr``)
    collapse into a single bucket. This is deliberately simple: no
    email lookup, no manual alias map. Contributors who want their
    commits counted together should use a consistent ``user.name``.
    """
    return " ".join(name.split()).lower()


def read_git_commits(root: Path) -> list[_Commit]:
    """Parse ``git log --numstat`` output into per-commit records.

    Each commit contributes one ``_Commit`` with the **already-capped**
    per-commit value. The author field is the lowercase, whitespace-
    normalized ``author.name`` (see :func:`_normalize_author`).
    """
    out = _run(
        [
            "git",
            "log",
            "--no-merges",
            "--numstat",
            "--pretty=format:@COMMIT@%H|%at|%an",
        ],
        cwd=root,
    )
    commits: list[_Commit] = []
    author = ""
    ts = 0
    ins_total = 0
    del_total = 0
    have_header = False

    def flush() -> None:
        if have_header and author:
            raw = ins_total + 0.5 * del_total
            capped = min(PER_COMMIT_CAP, raw)
            commits.append(_Commit(author=author, ts=ts, value=float(capped)))

    for line in out.splitlines():
        line = line.rstrip()
        if line.startswith("@COMMIT@"):
            flush()
            payload = line[len("@COMMIT@") :]
            try:
                _sha, ts_s, author = payload.split("|", 2)
                ts = int(ts_s)
                author = _normalize_author(author)
                ins_total = 0
                del_total = 0
                have_header = True
            except ValueError:
                have_header = False
            continue
        if not have_header or not line:
            continue
        # numstat lines: "<ins>\t<del>\t<path>"; binary files report "-".
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


def compute_weights(
    commits: list[_Commit],
    *,
    now: datetime | None = None,
) -> dict[str, float]:
    """Aggregate *commits* into per-author weights using the locked formula."""
    now = now or datetime.now(tz=timezone.utc)
    now_ts = int(now.timestamp())

    # First pass: apply per-author per-day cap by summing raw values per
    # (author, utc_day) bucket and clamping each bucket at
    # PER_AUTHOR_DAILY_CAP.
    daily: dict[tuple[str, str], list[_Commit]] = defaultdict(list)
    for c in commits:
        daily[(c.author, _utc_day(c.ts))].append(c)

    totals: dict[str, float] = defaultdict(float)
    for (author, _day), bucket in daily.items():
        raw_sum = 0.0
        representative_ts = bucket[0].ts
        # Iterate in chronological order so the cap truncates the most
        # recent commits last (irrelevant for totals but intuitive).
        for c in sorted(bucket, key=lambda x: x.ts):
            remaining = PER_AUTHOR_DAILY_CAP - raw_sum
            if remaining <= 0:
                break
            take = min(remaining, c.value)
            raw_sum += take
            representative_ts = c.ts

        age_seconds = max(0, now_ts - representative_ts)
        age_days = age_seconds / 86400.0
        if age_days < AGE_FLOOR_DAYS:
            continue
        decay = math.exp(-math.log(2) * age_days / HALF_LIFE_DAYS)
        totals[author] += raw_sum * decay

    # Apply the floor and round for stable JSON diffs.
    out: dict[str, float] = {}
    for author, raw in totals.items():
        out[author] = round(max(WEIGHT_FLOOR, raw), 4)
    # Stable ordering: highest first, then alphabetical for ties.
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def _render(weights: dict[str, float]) -> str:
    return json.dumps(weights, indent=2, sort_keys=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="Repository root (default: cwd)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (default: <root>/weights.json)",
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
    output = Path(args.output) if args.output else root / "weights.json"

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
