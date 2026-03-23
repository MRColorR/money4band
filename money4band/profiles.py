"""Configuration profiles — save/switch between deployment contexts.

Profiles are stored under ``config/profiles/{name}/`` with copies of
``user-config.json`` and ``.env``.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from typing import Any

from colorama import Fore, Style

logger = logging.getLogger(__name__)


def _profiles_dir(config_dir: str) -> str:
    return os.path.join(config_dir, "profiles")


def list_profiles(config_dir: str) -> list[str]:
    """Return names of all saved profiles."""
    pdir = _profiles_dir(config_dir)
    if not os.path.isdir(pdir):
        return []
    return sorted(
        d for d in os.listdir(pdir)
        if os.path.isdir(os.path.join(pdir, d))
    )


def create_profile(
    name: str,
    config_dir: str,
    base_dir: str,
    user_config_path: str,
) -> str:
    """Save current config as a named profile.

    Copies ``user-config.json`` and ``.env`` into
    ``config/profiles/{name}/``.

    Returns the profile directory path.
    """
    profile_dir = os.path.join(_profiles_dir(config_dir), name)
    os.makedirs(profile_dir, exist_ok=True)

    # Copy user-config.json
    if os.path.isfile(user_config_path):
        shutil.copy2(user_config_path, os.path.join(profile_dir, "user-config.json"))

    # Copy .env if it exists
    env_path = os.path.join(base_dir, ".env")
    if os.path.isfile(env_path):
        shutil.copy2(env_path, os.path.join(profile_dir, ".env"))

    logger.info("Profile '%s' saved to %s", name, profile_dir)
    return profile_dir


def switch_profile(
    name: str,
    config_dir: str,
    base_dir: str,
    user_config_path: str,
) -> bool:
    """Load a saved profile, overwriting current config.

    Copies ``user-config.json`` and ``.env`` from the profile directory
    back to their active locations.

    Returns ``True`` if successful, ``False`` if profile doesn't exist.
    """
    profile_dir = os.path.join(_profiles_dir(config_dir), name)
    if not os.path.isdir(profile_dir):
        return False

    # Restore user-config.json
    src_user = os.path.join(profile_dir, "user-config.json")
    if os.path.isfile(src_user):
        shutil.copy2(src_user, user_config_path)

    # Restore .env
    src_env = os.path.join(profile_dir, ".env")
    env_path = os.path.join(base_dir, ".env")
    if os.path.isfile(src_env):
        shutil.copy2(src_env, env_path)

    logger.info("Switched to profile '%s'", name)
    return True


def delete_profile(name: str, config_dir: str) -> bool:
    """Delete a saved profile directory. Returns True on success."""
    profile_dir = os.path.join(_profiles_dir(config_dir), name)
    if not os.path.isdir(profile_dir):
        return False
    shutil.rmtree(profile_dir)
    logger.info("Deleted profile '%s'", name)
    return True


def display_profiles(config_dir: str) -> None:
    """Print a list of saved profiles to stdout."""
    profiles = list_profiles(config_dir)
    if not profiles:
        print(f"{Fore.YELLOW}No saved profiles.{Style.RESET_ALL}")
        print(f"  Create one with: m4b profile create <name>")
        return

    print(f"\n{Fore.CYAN}--- Saved Profiles ---{Style.RESET_ALL}")
    for p in profiles:
        pdir = os.path.join(_profiles_dir(config_dir), p)
        has_user = os.path.isfile(os.path.join(pdir, "user-config.json"))
        has_env = os.path.isfile(os.path.join(pdir, ".env"))
        files = []
        if has_user:
            files.append("user-config.json")
        if has_env:
            files.append(".env")
        print(f"  {Fore.GREEN}{p}{Style.RESET_ALL}  ({', '.join(files) or 'empty'})")
    print()
