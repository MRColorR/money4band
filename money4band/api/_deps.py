"""Shared dependencies for API routers.

Provides config-path resolution via a singleton that is configured once at
startup (``configure_paths()``) and consumed by router endpoints through
FastAPI's ``Depends()`` mechanism.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from money4band.loader import load_json_config


@dataclass(slots=True)
class ConfigPaths:
    """Holds resolved paths to the three main config files."""

    config_dir: str = ""
    m4b_config: str = ""
    app_config: str = ""
    user_config: str = ""
    base_dir: str = ""


# Module-level singleton — populated once by ``configure_paths``.
_paths = ConfigPaths()


def configure_paths(
    config_dir: str,
    base_dir: str,
    *,
    m4b_file: str = "m4b-config.json",
    app_file: str = "app-config.json",
    user_file: str = "user-config.json",
) -> None:
    """Set the config paths for the API lifetime."""
    _paths.config_dir = config_dir
    _paths.base_dir = base_dir
    _paths.m4b_config = os.path.join(config_dir, m4b_file)
    _paths.app_config = os.path.join(config_dir, app_file)
    _paths.user_config = os.path.join(config_dir, user_file)


def get_paths() -> ConfigPaths:
    """Return the resolved config paths (use as a FastAPI dependency)."""
    return _paths


def load_m4b_config() -> dict:
    """Load and return m4b-config.json."""
    return load_json_config(_paths.m4b_config)


def load_app_config() -> dict:
    """Load and return app-config.json."""
    return load_json_config(_paths.app_config)


def load_user_config() -> dict:
    """Load and return user-config.json."""
    return load_json_config(_paths.user_config)
