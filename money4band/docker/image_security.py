from __future__ import annotations

"""Docker image security checks: stale image warnings, digest logging, CVE scanning."""

import json
import logging
import subprocess
from datetime import datetime, timezone
from typing import Any

from colorama import Fore, Style, just_fix_windows_console

from money4band.core.loader import get_all_app_categories, get_category_entries

logger = logging.getLogger(__name__)

_STALE_DAYS = 90


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_image_names(app_config: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (app_name, image) pairs for all apps that have an image."""
    pairs: list[tuple[str, str]] = []
    for cat in get_all_app_categories(app_config):
        for entry in get_category_entries(app_config, cat):
            name = entry.get("name", "?")
            image = entry.get("compose_config", {}).get("image")
            if image:
                pairs.append((name, image))
    # Addon bundles: one image per addon, parallel to apps.
    for addon in app_config.get("addons") or []:
        if not isinstance(addon, dict):
            continue
        parent = addon.get("parent_id", "?")
        img = addon.get("compose_config", {}).get("image")
        if img:
            pairs.append((f"{parent} (addon)", img))
    return pairs


def _docker_inspect_image(image: str) -> dict[str, Any] | None:
    """Run ``docker image inspect`` and return parsed JSON or None."""
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["docker", "image", "inspect", image, "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if result.returncode != 0:
            return None
        parsed: dict[str, Any] = json.loads(result.stdout)
        return parsed
    except Exception:
        return None


def _docker_available() -> bool:
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _scout_available() -> bool:
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["docker", "scout", "version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_stale_images(app_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Check all app images for staleness (>90 days since last update).

    Uses ``app_details.docker.last_update`` from config as the reference date.
    Returns a list of dicts with keys: app, image, last_update, days_old.
    """
    stale: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for cat in get_all_app_categories(app_config):
        for entry in get_category_entries(app_config, cat):
            details = entry.get("app_details", {})
            docker_info = details.get("docker", {})
            last_update = docker_info.get("last_update")
            image = entry.get("compose_config", {}).get("image", "")
            name = entry.get("name", "?")

            if not last_update or not image:
                continue

            try:
                # Handles "YYYY-MM" format
                dt = datetime.strptime(last_update, "%Y-%m").replace(
                    tzinfo=timezone.utc
                )
                days = (now - dt).days
                if days > _STALE_DAYS:
                    stale.append(
                        {
                            "app": name,
                            "image": image,
                            "last_update": last_update,
                            "days_old": days,
                        }
                    )
            except ValueError:
                continue

    return stale


def log_image_digests(app_config: dict[str, Any]) -> list[dict[str, str]]:
    """Log image digests for all pulled app images. Returns digest records."""
    digests: list[dict[str, str]] = []
    for app_name, image in _get_image_names(app_config):
        info = _docker_inspect_image(image)
        if info is None:
            continue
        repo_digests = info.get("RepoDigests", [])
        digest = repo_digests[0] if repo_digests else "none"
        record = {"app": app_name, "image": image, "digest": digest}
        digests.append(record)
        logger.info("Image digest: %s -> %s", image, digest)
    return digests


def run_scout_cves(image: str) -> str | None:
    """Run ``docker scout cves`` on an image. Returns output or None if unavailable."""
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["docker", "scout", "cves", image, "--only-severity", "critical,high"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if result.returncode == 0:
            return result.stdout
        return result.stderr or None
    except Exception:
        return None


def validate_images(app_config: dict[str, Any], run_cves: bool = True) -> None:
    """Run full image validation: stale check, digest logging, optional CVE scan."""
    just_fix_windows_console()

    if not _docker_available():
        print(
            f"{Fore.RED}Docker is not available. Cannot validate images.{Style.RESET_ALL}"
        )
        return

    # 1. Stale image check
    print(
        f"{Fore.CYAN}--- Stale Image Check (>{_STALE_DAYS} days) ---{Style.RESET_ALL}"
    )
    stale = check_stale_images(app_config)
    if stale:
        for s in stale:
            print(
                f"  {Fore.YELLOW}! {s['app']:<20} {s['image']:<40} last updated: {s['last_update']} ({s['days_old']} days){Style.RESET_ALL}"
            )
    else:
        print(f"  {Fore.GREEN}All images within freshness threshold.{Style.RESET_ALL}")
    print()

    # 2. Digest logging
    print(f"{Fore.CYAN}--- Image Digests ---{Style.RESET_ALL}")
    digests = log_image_digests(app_config)
    if digests:
        for d in digests:
            digest_short = d["digest"][-20:] if len(d["digest"]) > 20 else d["digest"]
            print(f"  {d['app']:<20} {d['image']:<40} ...{digest_short}")
    else:
        print(f"  {Fore.YELLOW}No pulled images found locally.{Style.RESET_ALL}")
    print()

    # 3. CVE scanning (optional)
    if run_cves:
        has_scout = _scout_available()
        if has_scout:
            print(f"{Fore.CYAN}--- CVE Scan (docker scout) ---{Style.RESET_ALL}")
            for app_name, image in _get_image_names(app_config):
                if "deprecated" in app_name.lower():
                    continue
                print(f"  Scanning {image}...")
                output = run_scout_cves(image)
                if output:
                    # Show summary line only
                    for line in output.splitlines():
                        if (
                            "critical" in line.lower()
                            or "high" in line.lower()
                            or "vulnerabilities" in line.lower()
                        ):
                            print(f"    {line.strip()}")
            print()
        else:
            print(
                f"{Fore.YELLOW}Docker Scout not available. Skipping CVE scan.{Style.RESET_ALL}"
            )
            print("  Install: https://docs.docker.com/scout/install/")
            print()
