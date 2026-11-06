#!/usr/bin/env python3
"""Record GitHub's aggregate star count and render a static SVG."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date, datetime, timezone
from http.client import HTTPSConnection
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
HISTORY = DOCS / "stargazers.json"
CHART = DOCS / "stargazers.svg"


def fetch_count() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY", "MRColorR/money4band")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise ValueError("Invalid GitHub repository")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "money4band-star-chart",
    }
    credential = os.environ.get("GH_TOKEN")
    if credential:
        headers["Authorization"] = f"Bearer {credential}"
    connection = HTTPSConnection("api.github.com", timeout=20)
    try:
        connection.request("GET", f"/repos/{repository}", headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"GitHub repository lookup returned {response.status}")
        count = json.load(response)["stargazers_count"]
    finally:
        connection.close()
    if type(count) is not int or count < 0:
        raise ValueError("Invalid star count")
    return count


def render(history: dict[str, int]) -> str:
    points = [
        (date.fromisoformat(day), count) for day, count in sorted(history.items())
    ]
    if any(type(count) is not int or count < 0 for _, count in points):
        raise ValueError("Invalid recorded star count")
    first, latest = points[0][0], points[-1][0]
    days = max(1, (latest - first).days)
    maximum = max(count for _, count in points) or 1
    coords = [
        (64 + 590 * (day - first).days / days, 140 - 78 * count / maximum)
        for day, count in points
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    x, y = coords[-1]
    start_label = (
        f'      <text x="64" y="162">{first}</text>\n' if first != latest else ""
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 180"
    role="img" aria-labelledby="title description">
  <title id="title">Money4Band GitHub stars</title>
  <desc id="description">Recorded aggregate star counts from {first} to {latest}. Latest count: {points[-1][1]}.</desc>
  <rect x="1" y="1" width="718" height="178" rx="12" fill="#f8fafc" stroke="#cbd5e1"/>
  <g font-family="system-ui, sans-serif" fill="#172033">
    <text x="32" y="33" font-size="19" font-weight="600">Money4Band GitHub stars</text>
    <text x="688" y="33" text-anchor="end" font-size="17">{points[-1][1]:,} stars</text>
    <g font-size="12" fill="#475569">
      <text x="54" y="66" text-anchor="end">{maximum:,}</text>
      <text x="54" y="144" text-anchor="end">0</text>
{start_label}      <text x="654" y="162" text-anchor="end">{latest}</text>
    </g>
  </g>
  <path d="M64 62 H654 M64 140 H654" stroke="#cbd5e1"/>
  <polyline points="{line}" fill="none" stroke="#2563eb" stroke-width="3"/>
  <circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#2563eb"/>
</svg>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check without fetching")
    args = parser.parse_args()
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    if args.check:
        if CHART.read_text(encoding="utf-8") != render(history):
            print("The star chart is stale. Run python scripts/update_star_chart.py.")
            return 1
        return 0

    today = datetime.now(timezone.utc).date().isoformat()
    history[today] = fetch_count()
    svg = render(history)
    HISTORY.write_text(
        json.dumps(history, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    CHART.write_text(svg, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
