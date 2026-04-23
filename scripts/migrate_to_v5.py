#!/usr/bin/env python3
"""Migrate Money4Band v4.x configuration to v5.0 encrypted format.

Reads legacy .env and config/user-config.json, converts them to
the v5 encrypted user-config.json, and preserves originals as .bak.

Usage:
    python scripts/migrate_to_v5.py [--project-dir /path/to/money4band] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_PROJECT_DIR = os.getcwd()
TEMPLATE_PATH = "template/user-config.json"
APP_CONFIG_PATH = "config/app-config.json"
USER_CONFIG_PATH = "config/user-config.json"
ENV_PATH = ".env"

# V4 .env keys that map to device_info
DEVICE_INFO_MAP: dict[str, str] = {
    "DEVICE_NAME": "device_name",
    "OS_TYPE": "os_type",
    "DETECTED_ARCHITECTURE": "detected_architecture",
    "DETECTED_DOCKER_ARCH": "detected_docker_arch",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse a .env file into a key→value dict, skipping comments and blanks."""
    env_vars: dict[str, str] = {}
    with open(env_path, encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)", line)
            if match:
                key, value = match.group(1), match.group(2)
                # Strip surrounding quotes if any
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                env_vars[key] = value
    return env_vars


def build_app_flag_map(app_config: dict) -> dict[str, list[str]]:
    """Build a map of app_name_lower → list of flag keys from app-config.json.

    This lets us know which .env vars to look for per app.
    """
    flag_map: dict[str, list[str]] = {}
    for category_key in ("supported", "deprecated", "newcomers"):
        category = app_config.get(category_key, {})
        entries = (
            category.get("entries", category)
            if isinstance(category, dict)
            else category
        )
        if isinstance(entries, dict):
            entries = entries.get("entries", [])
        for app in entries:
            name = app.get("name", "").lower()
            flags = app.get("flags", {})
            if name and flags:
                flag_map[name] = list(flags.keys())
    return flag_map


def map_env_to_apps(
    env_vars: dict[str, str],
    flag_map: dict[str, list[str]],
) -> dict[str, dict[str, object]]:
    """Map .env credential variables to v5 user-config app entries.

    Convention: {APP_NAME_UPPER}_{FLAG_UPPER} → apps.{app_lower}.{flag_lower}
    """
    apps: dict[str, dict[str, object]] = {}
    for app_name, flags in flag_map.items():
        app_upper = app_name.upper()
        app_entry: dict[str, object] = {}
        has_credentials = False
        for flag in flags:
            env_key = f"{app_upper}_{flag.upper()}"
            if env_key in env_vars:
                val = env_vars[env_key]
                # Skip placeholder values
                if val and not val.startswith("your"):
                    app_entry[flag] = val
                    has_credentials = True
        # If we found real credentials, enable the app
        if has_credentials:
            app_entry["enabled"] = True
        apps[app_name] = app_entry
    return apps


def merge_v4_user_config(
    v5_config: dict,
    v4_config: dict,
) -> None:
    """Merge v4 user-config.json fields into the v5 config dict (in-place)."""
    # v4 might have simple app enable/disable flags
    v4_apps = v4_config.get("apps", {})
    v5_apps = v5_config.setdefault("apps", {})

    for app_name, v4_app in v4_apps.items():
        app_lower = app_name.lower()
        if app_lower not in v5_apps:
            v5_apps[app_lower] = {}
        # Merge all fields from v4, but don't overwrite env-derived credentials
        for k, v in v4_app.items():
            if k not in v5_apps[app_lower]:
                v5_apps[app_lower][k] = v

    # Copy user info if present
    if "user" in v4_config:
        v5_config.setdefault("user", {}).update(v4_config["user"])
    if "device_info" in v4_config:
        v5_config.setdefault("device_info", {}).update(v4_config["device_info"])


def build_v5_config(
    template: dict,
    env_vars: dict[str, str],
    flag_map: dict[str, list[str]],
    v4_user_config: dict | None,
) -> dict:
    """Build a complete v5 user-config from template + env + v4 config."""
    import copy

    config = copy.deepcopy(template)

    # 1. Map device info from .env
    device_info = config.setdefault("device_info", {})
    for env_key, config_key in DEVICE_INFO_MAP.items():
        if env_key in env_vars:
            device_info[config_key] = env_vars[env_key]

    # 2. Map app credentials from .env
    env_apps = map_env_to_apps(env_vars, flag_map)
    v5_apps = config.setdefault("apps", {})
    for app_name, env_entry in env_apps.items():
        if app_name not in v5_apps:
            v5_apps[app_name] = {"enabled": False}
        v5_apps[app_name].update(env_entry)

    # 3. Map infrastructure settings from .env
    if "M4B_DASHBOARD_PORT" in env_vars:
        dashboard = config.setdefault("m4b_dashboard", {})
        try:
            dashboard["port"] = int(env_vars["M4B_DASHBOARD_PORT"])
        except ValueError:
            pass

    if "STACK_PROXY_ENABLED" in env_vars:
        proxies = config.setdefault("proxies", {})
        proxies["enabled"] = env_vars["STACK_PROXY_ENABLED"].lower() in (
            "true",
            "1",
            "yes",
        )
    if "STACK_PROXY_URL" in env_vars and env_vars["STACK_PROXY_URL"]:
        config.setdefault("proxies", {})["url"] = env_vars["STACK_PROXY_URL"]

    # 4. Merge v4 user-config if available
    if v4_user_config:
        merge_v4_user_config(config, v4_user_config)

    return config


def backup_file(path: Path) -> Path | None:
    """Create a .bak copy of a file. Returns backup path or None if source missing."""
    if not path.is_file():
        return None
    bak = path.with_suffix(path.suffix + ".bak")
    counter = 1
    while bak.exists():
        bak = path.with_suffix(f"{path.suffix}.bak{counter}")
        counter += 1
    shutil.copy2(path, bak)
    logger.info("Backed up %s → %s", path, bak)
    return bak


def validate_config(config: dict) -> list[str]:
    """Run basic validation on the migrated config. Returns list of warnings."""
    warnings: list[str] = []
    apps = config.get("apps", {})
    enabled_count = sum(1 for a in apps.values() if a.get("enabled"))
    if enabled_count == 0:
        warnings.append(
            "No apps are enabled — was the .env populated with credentials?"
        )

    device = config.get("device_info", {})
    if not device.get("device_name") or device["device_name"] == "yourDeviceName":
        warnings.append("device_name is still a placeholder")

    return warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def migrate(project_dir: str, *, dry_run: bool = False) -> bool:
    """Run the v4 → v5 migration.

    Returns True on success, False on failure.
    """
    root = Path(project_dir).resolve()

    # Load template
    template_path = root / TEMPLATE_PATH
    if not template_path.is_file():
        logger.error("Template not found: %s", template_path)
        return False
    with open(template_path, encoding="utf-8") as fh:
        template = json.load(fh)

    # Load app-config for flag map
    app_config_path = root / APP_CONFIG_PATH
    if not app_config_path.is_file():
        logger.error("app-config.json not found: %s", app_config_path)
        return False
    with open(app_config_path, encoding="utf-8") as fh:
        app_config = json.load(fh)
    flag_map = build_app_flag_map(app_config)

    # Parse legacy .env
    env_path = root / ENV_PATH
    env_vars: dict[str, str] = {}
    if env_path.is_file():
        env_vars = parse_env_file(env_path)
        logger.info("Parsed %d variables from %s", len(env_vars), env_path)
    else:
        logger.warning(
            "No .env found at %s — migrating from user-config.json only", env_path
        )

    # Load existing v4 user-config (if it exists and is plaintext JSON)
    user_config_path = root / USER_CONFIG_PATH
    v4_user_config: dict | None = None
    if user_config_path.is_file():
        raw = user_config_path.read_text(encoding="utf-8")
        if not raw.startswith("M4B_ENCRYPTED:"):
            try:
                v4_user_config = json.loads(raw)
                logger.info("Loaded v4 user-config.json (plaintext)")
            except json.JSONDecodeError:
                logger.warning(
                    "user-config.json exists but is not valid JSON — skipping"
                )
        else:
            logger.info(
                "user-config.json is already encrypted (v5 format) — skipping migration"
            )
            return True

    # Build v5 config
    v5_config = build_v5_config(template, env_vars, flag_map, v4_user_config)

    # Validate
    warnings = validate_config(v5_config)
    for w in warnings:
        logger.warning("Validation: %s", w)

    if dry_run:
        print("\n--- DRY RUN: migrated config ---")
        # Redact sensitive fields for display
        import copy

        display = copy.deepcopy(v5_config)
        for app_data in display.get("apps", {}).values():
            for key in ("password", "apikey", "token"):
                if key in app_data and app_data[key]:
                    app_data[key] = "***REDACTED***"
        print(json.dumps(display, indent=2))
        print(
            f"\nEnabled apps: {sum(1 for a in v5_config['apps'].values() if a.get('enabled'))}"
        )
        print(f"Warnings: {len(warnings)}")
        return True

    # Backup originals
    if env_path.is_file():
        backup_file(env_path)
    if user_config_path.is_file():
        backup_file(user_config_path)

    # Write v5 config (plaintext first)
    user_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(user_config_path, "w", encoding="utf-8") as fh:
        json.dump(v5_config, fh, indent=2)
    logger.info("Wrote v5 config to %s", user_config_path)

    # Encrypt the config
    try:
        # Import crypto from the project
        sys.path.insert(0, str(root))
        from money4band.core.crypto import ensure_config_encrypted

        ensure_config_encrypted(str(user_config_path))
        logger.info("Encrypted config at %s", user_config_path)
    except ImportError:
        logger.warning(
            "Could not import money4band.core.crypto — config saved as plaintext"
        )
    except Exception:
        logger.exception("Encryption failed — config saved as plaintext")

    enabled = sum(1 for a in v5_config["apps"].values() if a.get("enabled"))
    print("\n✅  Migration complete!")
    print(f"   Enabled apps: {enabled}")
    print(f"   Config: {user_config_path}")
    if warnings:
        print(f"   ⚠  {len(warnings)} warning(s) — check logs")
    print("   Originals preserved as .bak files")
    print("\n   Next: run 'm4b setup' to regenerate docker-compose.yaml and .env")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate Money4Band v4.x config to v5.0 encrypted format",
    )
    parser.add_argument(
        "--project-dir",
        default=DEFAULT_PROJECT_DIR,
        help="Path to the Money4Band project directory (default: cwd)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without writing files",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    success = migrate(args.project_dir, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
