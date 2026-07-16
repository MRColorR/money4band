from __future__ import annotations

import json
import logging
import os
import platform
import re
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from colorama import Fore, Style, just_fix_windows_console

from money4band.core.loader import load_json_config
from money4band.network import http_client
from money4band.network.http_client import get_client

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)

# ---------------------------------------------------------------------------
# Update cache - avoids hitting GitHub API more than once per 15 minutes
# ---------------------------------------------------------------------------

_CACHE_TTL = 900  # seconds (15 minutes)


def _cache_path() -> Path:
    """Return path to the update-check cache file.

    Lives in the per-user M4B data dir (0700, same place as master.key) -
    a fixed world-shared /tmp path let any local user pre-create the file
    and poison the trusted "latest" field indefinitely.
    """
    from money4band.core.paths import get_m4b_data_dir

    return get_m4b_data_dir() / "update_cache.json"


def _read_cache() -> dict[str, Any] | None:
    """Read the cached update check result if still valid and well-formed."""
    path = _cache_path()
    if not path.is_file():
        return None
    try:
        data: dict[str, Any] = json.loads(path.read_text())
        # Validate the shape before trusting it - fall back to a live
        # check on anything unexpected.
        if not isinstance(data, dict):
            return None
        ts = data.get("ts")
        latest = data.get("latest")
        if not isinstance(ts, (int, float)):
            return None
        if latest is not None and not isinstance(latest, str):
            return None
        if time.time() - ts < _CACHE_TTL:
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _write_cache(latest_version: str | None, current_version: str) -> None:
    """Persist the update check result with a timestamp."""
    payload = {
        "ts": time.time(),
        "latest": latest_version,
        "current": current_version,
    }
    try:
        _cache_path().write_text(json.dumps(payload))
    except OSError:
        pass


class Version:
    """
    A class to represent a version number in the format major.minor.patch.
    Supports comparison operators (==, !=, <, >, <=, >=) and can be created from a string or individual components.
    """

    version_regex = re.compile(
        r"(?:(?:v|version)?\s*)?(\d+)\.(\d+)\.(\d+)", re.IGNORECASE
    )

    @staticmethod
    def from_string(version_str: str) -> Version:
        """
        Create a Version object by extracting version numbers from a string.
        """
        version_str = version_str.strip()
        match = Version.version_regex.search(version_str)
        if not match:
            raise ValueError(f"Invalid version string format: '{version_str}'")
        major, minor, patch = match.groups()
        return Version(int(major), int(minor), int(patch))

    def __init__(self, major: int, minor: int, patch: int):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return False
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch))

    def __lt__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        if self.major < other.major:
            return True
        elif self.major > other.major:
            return False
        elif self.minor < other.minor:
            return True
        elif self.minor > other.minor:
            return False
        else:  # minor is equal
            return self.patch < other.patch

    def __gt__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return not self.__lt__(other) and not self.__eq__(other)

    def __le__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return not self.__lt__(other)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)


def get_latest_releases(count: int = 5) -> list[dict[str, Any]]:
    owner = "MRColorR"
    repo = "money4band"
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    client = get_client()
    try:
        response = client.get(url, timeout=http_client.REQUEST_TIMEOUT)
        response.raise_for_status()
        releases = response.json()
        stripped_releases = []
        for release in releases:
            if release["prerelease"] or release["draft"]:
                continue
            name = release["name"] or release["tag_name"]
            if not name:
                continue
            try:
                version = Version.from_string(name)
            except ValueError:
                logger.warning("Skipping release with unparseable version: '%s'", name)
                continue
            published_at = datetime.strptime(
                release["published_at"], "%Y-%m-%dT%H:%M:%SZ"
            )
            stripped_releases.append(
                {
                    "name": name,
                    "version": version,
                    "url": release["html_url"],
                    "published_at": published_at,
                }
            )
        stripped_releases.sort(key=lambda x: x["version"], reverse=True)
        return stripped_releases[:count]
    except httpx.ConnectError as e:
        raise RuntimeError(f"Cannot reach GitHub API: {e}") from e
    except httpx.TimeoutException as e:
        raise RuntimeError(
            f"GitHub API timed out after {http_client.REQUEST_TIMEOUT}s"
        ) from e
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"GitHub API HTTP error: {e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError("Failed to parse GitHub API response") from e


def check_update_available(m4b_config_path_or_dict: str | dict[str, Any]) -> None:
    just_fix_windows_console()
    m4b_config = load_json_config(m4b_config_path_or_dict)
    try:
        current_version_str = m4b_config.get("project", {}).get(
            "project_version", "0.0.0"
        )
        current_version = Version.from_string(current_version_str)
        latest_releases = get_latest_releases()
        if not latest_releases:
            print(f"{Fore.YELLOW}No releases found.")
            return
        latest_release = latest_releases[0]
        if current_version < latest_release["version"]:
            print(
                f"{Fore.YELLOW}New version available: {latest_release['version']}, published at {latest_release['published_at']}"
            )
            print(f"Download URL: {Style.RESET_ALL}{latest_release['url']}")
    except Exception as e:
        logger.error(e)
        print(f"Error checking for updates: {e}")


# ---------------------------------------------------------------------------
# Update detection and application
# ---------------------------------------------------------------------------

# Files that MUST be preserved across updates (never overwritten).
_PRESERVED_FILES = frozenset({"user-config.json", ".env", "proxies.txt"})

_OWNER = "MRColorR"
_REPO = "money4band"


def is_git_install() -> bool:
    """Return True if the current installation is a git clone."""
    git_dir = os.path.join(parent_dir, ".git")
    return os.path.isdir(git_dir)


def check_for_update(m4b_config: dict[str, Any]) -> str | None:
    """Check whether a newer version is available, using the 15-min cache.

    Returns the latest version string if an update is available, else None.
    """
    current_str = m4b_config.get("project", {}).get("project_version", "0.0.0")
    current = Version.from_string(current_str)

    cached = _read_cache()
    if cached is not None:
        latest_str: str | None = cached.get("latest")
        if latest_str is None:
            return None
        try:
            if current < Version.from_string(latest_str):
                return latest_str
        except ValueError:
            pass
        return None

    try:
        releases = get_latest_releases(count=1)
    except RuntimeError:
        _write_cache(None, str(current))
        return None

    if not releases:
        _write_cache(None, str(current))
        return None

    latest = releases[0]["version"]
    _write_cache(str(latest), str(current))

    if current < latest:
        return str(latest)
    return None


def show_update_banner(m4b_config: dict[str, Any]) -> None:
    """Print a one-line banner if an update is available (called at startup)."""
    new_version = check_for_update(m4b_config)
    if new_version:
        just_fix_windows_console()
        print(
            f"{Fore.YELLOW}M4B v{new_version} available! "
            f"Run 'm4b update' to upgrade.{Style.RESET_ALL}"
        )
        _notify_update_available(new_version)


def _notify_update_available(version: str) -> None:
    """Fire-and-forget notification about an available update."""
    try:
        user_cfg_path = os.path.join(parent_dir, "config", "user-config.json")
        if not os.path.isfile(user_cfg_path):
            return
        user_config = load_json_config(user_cfg_path)
        from money4band.notifier import notify

        notify(
            user_config,
            "update_available",
            f"M4B v{version} is available! Run 'm4b update' to upgrade.",
        )
    except Exception:
        logger.debug("Update notification failed (non-critical).", exc_info=True)


# ---------------------------------------------------------------------------
# Update preservation policy:
#
# config/m4b-config.json is *not* preserved across updates - it is a
# shipped-defaults file owned by the release. User-mutable catalog state
# (source enable/disable, custom remote sources, category toggles) lives
# in user-config.json under catalog_overrides (see
# money4band.core.catalog_overrides) and rides along on user-config
# preservation below.
# ---------------------------------------------------------------------------

_M4B_CONFIG_RELPATH = os.path.join("config", "m4b-config.json")


def _backup_preserved_files(base_dir: str) -> dict[str, tuple[bytes, int]]:
    """Read preserved files and their permissions into memory before a destructive update."""
    saved: dict[str, tuple[bytes, int]] = {}
    for name in _PRESERVED_FILES:
        path = os.path.join(base_dir, name)
        if os.path.isfile(path):
            mode = stat.S_IMODE(os.stat(path).st_mode)
            with open(path, "rb") as f:
                saved[name] = (f.read(), mode)
    # Also backup config/ directory files EXCEPT m4b-config.json which is
    # release-owned and must reflect the newly shipped defaults.
    config_dir = os.path.join(base_dir, "config")
    if os.path.isdir(config_dir):
        for fname in os.listdir(config_dir):
            fpath = os.path.join(config_dir, fname)
            if not os.path.isfile(fpath):
                continue
            key = os.path.join("config", fname)
            if key == _M4B_CONFIG_RELPATH:
                continue
            mode = stat.S_IMODE(os.stat(fpath).st_mode)
            with open(fpath, "rb") as f:
                saved[key] = (f.read(), mode)
    return saved


def _restore_preserved_files(
    base_dir: str, saved: dict[str, tuple[bytes, int]]
) -> None:
    """Restore preserved files after an update, preserving original permissions."""
    for rel_path, (content, mode) in saved.items():
        full_path = os.path.join(base_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        fd = os.open(full_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
        try:
            os.write(fd, content)
        finally:
            os.close(fd)


def _apply_git_update(target_version: str) -> bool:
    """Update via git fetch + reset for git clone installs."""
    tag = f"v{target_version}" if not target_version.startswith("v") else target_version

    saved = _backup_preserved_files(parent_dir)

    try:
        subprocess.run(
            [
                "git",
                "fetch",
                "--depth=1",
                "origin",
                f"+refs/tags/{tag}:refs/tags/{tag}",
            ],
            cwd=parent_dir,
            check=True,
            capture_output=True,
            text=True,
        )  # noqa: S603
        subprocess.run(
            ["git", "checkout", tag],
            cwd=parent_dir,
            check=True,
            capture_output=True,
            text=True,
        )  # noqa: S603
    except subprocess.CalledProcessError as e:
        logger.error("Git update failed: %s", e.stderr)
        return False

    _restore_preserved_files(parent_dir, saved)
    return True


def _get_binary_asset_name() -> str:
    """Determine the correct binary asset name for this platform.

    MUST match the asset names produced by the release workflow
    (.github/workflows/release-on-tag.yml): single-file PyInstaller
    binaries named ``Money4Band-<os>-<arch>[.exe]``.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "armv7",
        "armv6l": "armv7",  # closest published build; no separate v6 asset
    }
    arch = arch_map.get(machine, "amd64")

    if system == "windows":
        return f"Money4Band-windows-{arch}.exe"
    elif system == "darwin":
        return f"Money4Band-macos-{arch}"
    else:
        return f"Money4Band-linux-{arch}"


def _apply_binary_update(target_version: str) -> bool:
    """Download and replace the running binary for frozen installs.

    Verifies the download against a SHA-256 checksum file published
    alongside each release (``checksums.sha256``).  Falls back to
    an unverified install with a warning if no checksum file is available.
    """
    tag = f"v{target_version}" if not target_version.startswith("v") else target_version
    asset_name = _get_binary_asset_name()
    url = f"https://github.com/{_OWNER}/{_REPO}/releases/download/{tag}/{asset_name}"
    checksum_url = (
        f"https://github.com/{_OWNER}/{_REPO}/releases/download/{tag}/checksums.sha256"
    )

    client = get_client()
    try:
        resp = client.get(url, timeout=http_client.REQUEST_TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("Binary download failed: %s", e)
        return False

    # Try to fetch the checksum file for integrity verification.
    expected_hash: str | None = None
    try:
        cs_resp = client.get(checksum_url, timeout=http_client.REQUEST_TIMEOUT)
        if cs_resp.status_code == 200:
            for line in cs_resp.text.strip().splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1].lstrip("*") == asset_name:
                    expected_hash = parts[0].lower()
                    break
    except httpx.HTTPError:
        logger.warning("Could not fetch checksums.sha256 - skipping verification.")

    current_exe = sys.executable
    backup_exe = current_exe + ".bak"

    fd, tmp_path = tempfile.mkstemp(
        suffix=os.path.splitext(current_exe)[1],
        dir=os.path.dirname(current_exe),
    )
    try:
        import hashlib

        sha256 = hashlib.sha256()
        with os.fdopen(fd, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)
                sha256.update(chunk)

        # Verify checksum if available.
        actual_hash = sha256.hexdigest()
        if expected_hash:
            if actual_hash != expected_hash:
                logger.error(
                    "Checksum mismatch! expected=%s actual=%s",
                    expected_hash,
                    actual_hash,
                )
                os.unlink(tmp_path)
                return False
            logger.info("Checksum verified: %s", actual_hash)
        else:
            logger.warning(
                "No checksum available for %s - accepting download on HTTPS trust only.",
                asset_name,
            )

        # Make executable on Unix (owner-only - this replaces our own binary)
        if platform.system() != "Windows":
            os.chmod(tmp_path, 0o700)

        # Rename current -> backup, new -> current
        if os.path.exists(backup_exe):
            os.unlink(backup_exe)
        os.rename(current_exe, backup_exe)
        os.rename(tmp_path, current_exe)
        return True
    except OSError as e:
        logger.error("Binary replacement failed: %s", e)
        # Try to restore from backup
        if os.path.exists(backup_exe) and not os.path.exists(current_exe):
            os.rename(backup_exe, current_exe)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return False


def apply_update(target_version: str) -> bool:
    """Apply an update - dispatches to git or binary strategy."""
    if is_git_install():
        return _apply_git_update(target_version)
    elif getattr(sys, "frozen", False):
        return _apply_binary_update(target_version)
    else:
        # Script install without git - can't auto-update
        just_fix_windows_console()
        print(
            f"{Fore.YELLOW}Auto-update not supported for this install type. "
            f"Please download v{target_version} manually from "
            f"https://github.com/{_OWNER}/{_REPO}/releases{Style.RESET_ALL}"
        )
        return False
