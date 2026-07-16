from __future__ import annotations

"""Environment file generation - builds .env from configuration.

Security design (v5):
    Credentials live encrypted in ``user-config.json`` (Fernet AES-128-CBC).
    The ``.env`` file is a **derived, ephemeral** artifact used only during
    ``docker compose up`` and securely wiped afterwards.  Non-sensitive
    metadata (``COMPOSE_PROJECT_NAME``, ``DEVICE_NAME``) is persisted in a
    separate ``.env.meta`` file so that stop/restart operations can find the
    running stack without exposing credentials on disk.
"""

import logging
import os
import stat
import tempfile
import threading
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from money4band.core.loader import (
    get_active_app_categories,
    get_category_entries,
    load_json_config,
    resolve_catalog_config,
)
from money4band.docker.helper import show_spinner

logger = logging.getLogger(__name__)

# Keys whose values are safe to persist in unencrypted .env.meta.
_META_KEYS = frozenset(
    {
        "COMPOSE_PROJECT_NAME",
        "DEVICE_NAME",
        "PROJECT_VERSION",
        "PROJECT_NAME",
        "M4B_WATCHTOWER_LABELS",
        "M4B_WATCHTOWER_SCOPE",
    }
)


# ---------------------------------------------------------------------------
# Pure functions - no I/O, no side-effects
# ---------------------------------------------------------------------------


def build_env_lines(
    m4b_config: dict[str, Any],
    app_config: dict[str, Any],
    user_config: dict[str, Any],
    is_main_instance: bool = False,
) -> list[str]:
    """Build Docker-Compose env key=value lines from loaded config dicts.

    This is a pure function: it performs no file I/O and has no side-effects.
    Call it directly when you need the env content in memory (e.g. for
    ephemeral env files or for extracting metadata).
    """
    env_lines: list[str] = []

    # Add project and system configurations
    project_config = m4b_config.get("project", {})
    for key, value in project_config.items():
        env_lines.append(f"{key.upper()}={value}")

    # Add resource limits configurations
    resource_limits_config = user_config.get("resource_limits", {})
    for key, value in resource_limits_config.items():
        env_lines.append(f"{key.upper()}={value}")

    # Add network configurations
    network_config = m4b_config.get("network", {})
    for key, value in network_config.items():
        env_lines.append(f"NETWORK_{key.upper()}={value}")

    # Add user and device configurations
    device_info = user_config.get("device_info", {})
    for key, value in device_info.items():
        env_lines.append(f"{key.upper()}={value}")

    # Add proxy configurations
    proxy_config = user_config.get("proxies", {})
    for key, value in proxy_config.items():
        env_lines.append(f"STACK_PROXY_{key.upper()}={value}")

    # Add notification configurations if enabled
    notifications_config = user_config.get("notifications", {})
    if notifications_config.get("enabled"):
        for key, value in notifications_config.items():
            env_lines.append(f"WATCHTOWER_NOTIFICATION_{key.upper()}={value}")

    # Add Watchtower label scoping configuration
    watchtower_labels_enabled = user_config.get("watchtower", {}).get(
        "enable_labels", True
    )
    watchtower_scope = m4b_config.get("watchtower", {}).get("scope", "money4band")
    env_lines.append(
        f"M4B_WATCHTOWER_LABELS={'true' if watchtower_labels_enabled else 'false'}"
    )
    env_lines.append(f"M4B_WATCHTOWER_SCOPE={watchtower_scope}")

    # Add app-specific configurations only if the app is enabled
    apps_categories = get_active_app_categories(app_config)
    for category in apps_categories:
        for app in get_category_entries(app_config, category):
            app_name = app["name"].upper()
            app_lower = app["name"].lower()
            app_flags = app.get("flags", {})
            app_user_config = user_config["apps"].get(app_lower, {})
            if app_user_config.get("enabled", False):
                for flag_name in app_flags.keys():
                    if flag_name in app_user_config:
                        env_var_name = f"{app_name}_{flag_name.upper()}"
                        env_var_value = app_user_config[flag_name]
                        env_lines.append(f"{env_var_name}={env_var_value}")

                # Add ports configurations for apps that have them
                if "ports" in app_user_config:
                    # Ports are always stored as a list
                    ports = app_user_config["ports"]
                    if not isinstance(ports, list):
                        ports = [ports]  # Convert to list for consistency
                    for i, port in enumerate(ports):
                        env_lines.append(f"{app_name.upper()}_PORT_{i + 1}={port}")
                        # For backward compatibility, also add non-indexed variable for single port
                        if len(ports) == 1:
                            env_lines.append(f"{app_name.upper()}_PORT={port}")
                            env_lines.append(f"{app_lower.upper()}_PORT={port}")

    return env_lines


def extract_env_value(env_lines: list[str], key: str) -> str | None:
    """Extract a single value from env lines by key name (in-memory)."""
    prefix = f"{key}="
    for line in env_lines:
        if line.startswith(prefix):
            return line[len(prefix) :]
    return None


# ---------------------------------------------------------------------------
# Secure file I/O
# ---------------------------------------------------------------------------


def _write_secure(path: str, content: str) -> None:
    """Write *content* to *path* with owner-only (0o600) permissions."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    # Reinforce permissions (effective on Unix; best-effort on Windows).
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def secure_delete_env(path: str) -> None:
    """Overwrite a file with zeros and then unlink it.

    Best-effort on SSDs (wear-levelling may retain old blocks), but
    eliminates casual reads and memory-mapped leaks.
    """
    try:
        size = os.path.getsize(path)
        with open(path, "wb") as f:
            f.write(b"\0" * size)
            f.flush()
            os.fsync(f.fileno())
        os.unlink(path)
        logger.debug("Securely deleted %s", path)
    except OSError:
        # File may already be gone - not an error.
        pass


def write_env_metadata(env_lines: list[str], env_dir: str) -> None:
    """Persist only non-sensitive metadata to ``<env_dir>/.env.meta``.

    This file stores ``COMPOSE_PROJECT_NAME``, ``DEVICE_NAME``, etc. so
    that ``docker compose stop/down`` can locate the running stack
    without the full credentials file.
    """
    meta_lines = [line for line in env_lines if line.split("=", 1)[0] in _META_KEYS]
    meta_path = os.path.join(env_dir, ".env.meta")
    with open(meta_path, "w") as f:
        f.write("# Auto-generated - non-sensitive metadata only.\n")
        f.write("\n".join(meta_lines) + "\n")
    logger.debug("Wrote env metadata to %s", meta_path)


@contextmanager
def ephemeral_env_file(
    env_lines: list[str],
    env_dir: str | None = None,
) -> Generator[str, None, None]:
    """Context manager: write a short-lived ``.env`` and wipe it on exit.

    Creates the file with ``0o600`` permissions in the system temp
    directory (or *env_dir* if provided) and removes it - overwritten
    with zeros - once the caller's block finishes.

    Usage::

        with ephemeral_env_file(lines) as env_path:
            subprocess.run(["docker", "compose", "--env-file", env_path, "up", "-d"])
        # env_path is securely deleted here.

    Yields:
        The absolute path to the temporary ``.env`` file.
    """
    content = "\n".join(env_lines)
    if env_dir:
        env_path = os.path.join(env_dir, ".env")
        _write_secure(env_path, content)
        try:
            yield env_path
        finally:
            secure_delete_env(env_path)
    else:
        fd, env_path = tempfile.mkstemp(prefix="m4b-env-", suffix=".env")
        try:
            os.write(fd, content.encode())
            os.close(fd)
            os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)
            yield env_path
        finally:
            secure_delete_env(env_path)


# ---------------------------------------------------------------------------
# High-level public API (backward-compatible)
# ---------------------------------------------------------------------------


def generate_env_file(
    m4b_config_path_or_dict: Any,
    app_config_path_or_dict: Any,
    user_config_path_or_dict: Any,
    env_output_path: str = str(os.path.join(os.getcwd(), ".env")),
    is_main_instance: bool = False,
) -> None:
    """Generate a ``.env`` file with restricted (0o600) permissions.

    Also writes a ``.env.meta`` file in the same directory with only
    non-sensitive metadata (project name, device name) so that
    stop/restart operations can locate the stack.

    Args:
        m4b_config_path_or_dict: Path or loaded dict for m4b-config.json.
        app_config_path_or_dict: Path or loaded dict for the aggregated catalog.
        user_config_path_or_dict: Path or loaded dict for user-config.json.
        env_output_path: Destination path for the ``.env`` file.
        is_main_instance: Whether this is the main instance.
    """
    event = threading.Event()
    spinner_thread = threading.Thread(
        target=show_spinner, args=("Generating .env file...", event)
    )
    spinner_thread.start()

    try:
        m4b_config = load_json_config(m4b_config_path_or_dict)
        app_config = resolve_catalog_config(app_config_path_or_dict)
        user_config = load_json_config(user_config_path_or_dict)

        env_lines = build_env_lines(
            m4b_config, app_config, user_config, is_main_instance
        )

        # Write the credentials env with restricted permissions.
        _write_secure(env_output_path, "\n".join(env_lines))

        # Persist non-sensitive metadata alongside for stop/down.
        env_dir = os.path.dirname(os.path.abspath(env_output_path))
        write_env_metadata(env_lines, env_dir)

        logger.info(".env file generated and saved to %s (mode 0600)", env_output_path)
    finally:
        event.set()
        spinner_thread.join()
