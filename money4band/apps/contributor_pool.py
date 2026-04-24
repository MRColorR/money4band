"""Weighted referral picker — the unified pool used everywhere in M4B.

One module, one algorithm, used by the CLI, TUI setup wizard, and
REST API.

Design contract
---------------

- Each catalog entry carries a ``referrals`` pool::

      [{"url": "...", "contributor": "alice", "added": "2026-01-01",
        "verified": true, "verified_by": ["bob", "carol"]}, ...]

- Each of the three M4B catalog repos ships a ``weights.json`` file
  that maps ``contributor -> weight`` (float >= 0.1). The file is
  regenerated weekly in CI by :mod:`scripts.compute_weights`.

- The picker selects one referral by **weighted random** where every
  referral's weight equals the contributor's weight, falling back to
  ``DEFAULT_WEIGHT`` when the contributor is absent from
  ``weights.json``.

- A **sticky** override lives in
  ``user-config.settings.picked_referrals[<app_name.lower()>]``: once
  a URL is committed there (e.g. by the setup wizard) the picker
  returns it deterministically and skips the weighted lottery.

- The picker is **pure**: callers seed a ``random.Random`` instance
  for reproducibility in tests and deterministic rotation where
  needed.

The module has zero I/O beyond a single JSON read in
:func:`load_weights`; weighted selection itself is pure arithmetic.
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: Fallback weight for a contributor missing from ``weights.json``.
#: Matches the floor used by :mod:`scripts.compute_weights` so a new
#: contributor always has *some* chance to be picked.
DEFAULT_WEIGHT: float = 0.1

#: Canonical file name of the weights artifact shipped in every repo.
WEIGHTS_FILENAME: str = "weights.json"


def load_weights(path: str | Path) -> dict[str, float]:
    """Load ``weights.json`` from *path*.

    Returns an empty dict when the file is missing or malformed so
    callers can treat "no weights shipped" as "everyone is equal".
    """
    p = Path(path)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("weights.json at %s is unreadable: %s", p, exc)
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, float] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            continue
        try:
            weight = float(value)
        except (TypeError, ValueError):
            continue
        if weight < 0:
            continue
        out[key] = weight
    # Second pass: normalize keys to the same lowercase/whitespace-collapsed
    # form emitted by ``scripts/compute_weights.py`` so a catalog entry
    # with ``"contributor": "MRColorr"`` matches a weights.json key
    # ``"mrcolorr"`` transparently.
    normalized: dict[str, float] = {}
    for key, weight in out.items():
        canonical = " ".join(key.split()).lower()
        # If both a canonical and a cased key exist, keep the max —
        # defensive in case a human hand-edits the file.
        if canonical in normalized:
            normalized[canonical] = max(normalized[canonical], weight)
        else:
            normalized[canonical] = weight
    return normalized


def _canonical(contributor: str) -> str:
    return " ".join(contributor.split()).lower()


def weight_for(contributor: str, weights: dict[str, float]) -> float:
    """Return the weight for *contributor*, falling back to the default.

    Lookup is case- and whitespace-insensitive: ``"MRColorr"``,
    ``"mrcolorr"`` and ``"  MR Colorr  "`` all resolve to the same
    bucket in ``weights.json``.
    """
    if not isinstance(contributor, str) or not contributor.strip():
        return DEFAULT_WEIGHT
    key = _canonical(contributor)
    return max(DEFAULT_WEIGHT, float(weights.get(key, DEFAULT_WEIGHT)))


def pick_weighted(
    referrals: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any] | None:
    """Pick one referral by weighted random.

    Parameters
    ----------
    referrals:
        A list of referral dicts (see module docstring). Malformed
        entries (missing/empty ``url``) are skipped silently.
    weights:
        Contributor -> weight mapping. ``None`` or empty means every
        referral gets :data:`DEFAULT_WEIGHT` (equal chance).
    rng:
        Optional :class:`random.Random` instance for deterministic
        testing. Defaults to ``random`` module-level RNG.

    Returns
    -------
    dict | None
        The selected referral dict, or ``None`` when the pool has no
        usable entries.
    """
    valid = [
        r
        for r in (referrals or [])
        if isinstance(r, dict) and isinstance(r.get("url"), str) and r["url"].strip()
    ]
    if not valid:
        return None
    w = weights or {}
    computed = [weight_for(str(r.get("contributor") or ""), w) for r in valid]
    total = sum(computed)
    if total <= 0:
        # All zeros would collapse to uniform anyway; pick uniformly.
        picker = rng or random
        return picker.choice(valid)
    picker = rng or random
    threshold = picker.random() * total
    running = 0.0
    for ref, weight in zip(valid, computed, strict=True):
        running += weight
        if running >= threshold:
            return ref
    return valid[-1]  # pragma: no cover — numerical safety net


def resolve_referral_url(
    app_name: str,
    referrals: list[dict[str, Any]],
    *,
    weights: dict[str, float] | None = None,
    sticky: dict[str, str] | None = None,
    rng: random.Random | None = None,
) -> str:
    """High-level picker used by CLI / API / TUI.

    Preference order:
      1. ``sticky[app_name.lower()]`` or ``sticky[app_name]`` when set.
      2. Weighted-random pick across ``referrals`` using ``weights``.
      3. Empty string when the pool is empty.
    """
    if sticky:
        pinned = sticky.get(app_name.lower()) or sticky.get(app_name)
        if isinstance(pinned, str) and pinned.strip():
            return pinned.strip()
    chosen = pick_weighted(referrals, weights, rng=rng)
    if chosen is None:
        return ""
    url = chosen.get("url")
    return url.strip() if isinstance(url, str) else ""
