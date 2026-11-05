"""Regression tests for port_manager config-path resolution.

Guards the off-by-one bug where ``port_manager._m4b_config_path`` used a
single ``..`` and pointed at ``money4band/config`` (inside the package,
nonexistent) instead of the project-root ``config/`` directory. That made
``_load_port_constants`` swallow a FileNotFoundError, log a spurious
"Config file not found" error, and silently fall back to hardcoded port
defaults (offset_per_app=100/instance=10) instead of the real config
values (1000/3) - causing wrong port math when enabling apps.
"""

from __future__ import annotations

import json
from pathlib import Path

from money4band.network import port_manager

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONFIG = _REPO_ROOT / "config" / "m4b-config.json"


def test_m4b_config_path_resolves_to_existing_project_config():
    """The module-level config path must point at the real project config."""
    resolved = Path(port_manager._m4b_config_path).resolve()
    assert resolved.is_file(), (
        f"port_manager._m4b_config_path does not exist: {resolved}. "
        "The relative path depth is wrong (should reach the project-root "
        "config/ dir, not money4band/config inside the package)."
    )
    assert resolved == _CONFIG.resolve()


def test_port_constants_come_from_config_not_fallback_defaults():
    """Loading must read the config file, not hit the FileNotFoundError path."""
    ports = json.loads(_CONFIG.read_text(encoding="utf-8")).get("ports", {})
    # Only assert against keys the config actually defines.
    assert ports, "config m4b-config.json has no 'ports' section to validate"

    # Reset lazy state so the load re-runs against the real config.
    port_manager._port_constants_loaded = False
    try:
        port_manager._load_port_constants()
        if "default_port_base" in ports:
            assert port_manager.DEFAULT_PORT_BASE == ports["default_port_base"]
        if "port_offset_per_app" in ports:
            assert port_manager.PORT_OFFSET_PER_APP == ports["port_offset_per_app"]
        if "port_offset_per_instance" in ports:
            assert (
                port_manager.PORT_OFFSET_PER_INSTANCE
                == ports["port_offset_per_instance"]
            )
    finally:
        # Leave the module reloaded with valid values for any later tests.
        port_manager._port_constants_loaded = False
        port_manager._load_port_constants()
