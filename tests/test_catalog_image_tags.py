"""Catalog hygiene: every app image must carry an explicit tag.

A tagless image (e.g. ``bearshare/bearshare``) is ambiguous (Docker would
imply ``:latest``) and previously crashed compose assembly. Pin an explicit
tag - ``:latest`` or a fixed version - on every catalog entry.
"""

from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONFIG_DIR = _REPO_ROOT / "config"


def _image_of(data: object) -> str | None:
    if isinstance(data, dict):
        cc = data.get("compose_config")
        if isinstance(cc, dict):
            img = cc.get("image")
            if isinstance(img, str) and img:
                return img
    return None


def _has_tag(image: str) -> bool:
    # A tag is present only when ':' appears in the final path segment
    # (after the last '/'); a ':' before that belongs to a registry host:port.
    return ":" in image.rsplit("/", 1)[-1]


def test_every_catalog_image_has_explicit_tag():
    offenders: list[str] = []
    checked = 0
    for path in _CONFIG_DIR.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        image = _image_of(data)
        if image is None:
            continue
        checked += 1
        if not _has_tag(image):
            offenders.append(f"{path.relative_to(_REPO_ROOT).as_posix()}: {image}")

    assert checked > 0, "no catalog images found to validate"
    assert not offenders, (
        "Catalog images without an explicit tag (add ':latest' or a pinned "
        "version):\n" + "\n".join(offenders)
    )
