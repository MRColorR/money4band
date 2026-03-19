import json
import logging
import os
import re
import sys
from datetime import datetime

import requests
from colorama import Fore, Style, just_fix_windows_console

from utils import http_client
from utils.http_client import get_session
from utils.loader import load_json_config

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


class Version:
    """
    A class to represent a version number in the format major.minor.patch.
    Supports comparison operators (==, !=, <, >, <=, >=) and can be created from a string or individual components.
    """

    version_regex = re.compile(
        r"(?:(?:v|version)?\s*)?(\d+)\.(\d+)\.(\d+)", re.IGNORECASE
    )

    @staticmethod
    def from_string(version_str: str):
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

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if not isinstance(other, Version):
            return False
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def __lt__(self, other):
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

    def __gt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return not self.__lt__(other) and not self.__eq__(other)

    def __le__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return not self.__lt__(other)

    def __ne__(self, other):
        return not self.__eq__(other)


def get_latest_releases(count: int = 5) -> list[dict]:
    owner = "MRColorR"
    repo = "money4band"
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    session = get_session()
    try:
        response = session.get(url, timeout=http_client.REQUEST_TIMEOUT)
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
                logging.warning(
                    "Skipping release with unparseable version: '%s'", name
                )
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
    except requests.ConnectionError as e:
        raise RuntimeError(f"Cannot reach GitHub API: {e}") from e
    except requests.Timeout as e:
        raise RuntimeError(
            f"GitHub API timed out after {http_client.REQUEST_TIMEOUT}s"
        ) from e
    except requests.HTTPError as e:
        raise RuntimeError(f"GitHub API HTTP error: {e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError("Failed to parse GitHub API response") from e


def check_update_available(m4b_config_path_or_dict: str | dict) -> None:
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
        logging.error(e)
        print(f"Error checking for updates: {e}")


def main():
    releases = get_latest_releases()
    for release in releases:
        print(release)


if __name__ == "__main__":
    main()
