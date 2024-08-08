import os
import sys
from typing import List, Dict
import urllib.request
import json
import logging
from datetime import datetime
from colorama import Fore, Back, Style, just_fix_windows_console

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
from utils.loader import load_json_config


class Version():
    """
    A class to represent a version number in the format major.minor.patch.
    Supports comparison operators (==, !=, <, >, <=, >=) and can be created from a string or individual components.
    """

    @staticmethod
    def from_string(version_str: str):
        """
        Create a Version object from a string in the format major.minor.patch.
        """
        version_str = version_str.strip().lower().replace('v.', '').replace('v', '')
        version_parts = version_str.split('.')
        if len(version_parts) != 3:
            raise ValueError("Invalid version string format")
        try:
            major = int(version_parts[0])
            minor = int(version_parts[1])
            patch = int(version_parts[2])
        except ValueError:
            raise ValueError("Invalid version string format")
        return Version(major, minor, patch)
    
    def __init__(self, major: int, minor: int, patch: int):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def __lt__(self, other):
        if self.major < other.major:
            return True
        elif self.major > other.major:
            return False
        else: # major is equal
            if self.minor < other.minor:
                return True
            elif self.minor > other.minor:
                return False
            else: # minor is equal
                return self.patch < other.patch

    def __gt__(self, other):
        return not self.__lt__(other) and not self.__eq__(other)

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __ne__(self, other):
        return not self.__eq__(other)


def get_latest_releases(count: int = 5) -> List[Dict]:
    owner = 'MRColorR'
    repo = 'money4band'
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read().decode()
            releases = json.loads(data)
            releases = releases[:count]
            stripped_releases = []
            for release in releases:
                if release['prerelease']:
                    continue
                if release['draft']:
                    continue
                name = release['name']
                if name == '':
                    name = release['tag_name']
                if name == '':
                    continue
                version = Version.from_string(name)
                url = release['html_url']
                published_at = release['published_at']
                published_at = datetime.strptime(
                    published_at, '%Y-%m-%dT%H:%M:%SZ')
                stripped_releases.append({
                    'name': name,
                    'version': version,
                    'url': url,
                    'published_at': published_at
                })
            return stripped_releases
    except urllib.error.HTTPError as e:
        raise Exception(f"Failed to fetch releases. HTTP Error: {e.code}")
    except urllib.error.URLError as e:
        raise Exception(f"Failed to fetch releases. URL Error: {e.reason}")
    except json.JSONDecodeError:
        raise Exception("Failed to parse JSON response.")
    except Exception as e:
        raise Exception(f"An error occurred: {e}")


def check_update_available(m4b_config_path_or_dict: str | dict) -> None:
    just_fix_windows_console()
    m4b_config = load_json_config(m4b_config_path_or_dict)
    try:
        current_version = m4b_config.get('project',{}).get('project_version', "0.0.0")
        current_version = Version.from_string(current_version)
        latest_release = get_latest_releases()
        latest_release.sort(key=lambda x: x['version'], reverse=True)
        latest_release = latest_release[0]
        if current_version < latest_release['version']:
            print(f"{Fore.YELLOW}New version available: {latest_release['version']}, published at {latest_release['published_at']}")
            print(f"Download URL: {Style.RESET_ALL}{latest_release['url']}")
    except Exception as e:
        logging.error(e)
        print(f"Error checking for updates: {e}")

def main():
    releases = get_latest_releases()
    for release in releases:
        print(release)

if __name__ == '__main__':
    main()
