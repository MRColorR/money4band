from __future__ import annotations

"""Config viewer & editor.

Provides masked display and secure $EDITOR integration for encrypted configs.
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import tempfile
from typing import Any

from colorama import Fore, Style, just_fix_windows_console

from utils.crypto import encrypt_file, ensure_config_encrypted, is_file_encrypted
from utils.loader import load_json_config

logger = logging.getLogger(__name__)

# Keys whose string values should be displayed unmasked.
_SAFE_KEYS = frozenset({"enabled", "name", "app_name", "category"})


def _mask_value(value: str) -> str:
    """Mask a credential string, preserving first 2 and last 2 characters."""
    if len(value) <= 4:
        return "****"
    return value[:2] + "****" + value[-2:]


def _mask_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively mask sensitive string values in a config dict."""
    masked: dict[str, Any] = {}
    for key, val in data.items():
        if isinstance(val, dict):
            masked[key] = _mask_dict(val)
        elif isinstance(val, str) and key not in _SAFE_KEYS:
            masked[key] = _mask_value(val)
        else:
            masked[key] = val
    return masked


def view_masked(user_config_path: str) -> None:
    """Decrypt user-config and print with sensitive fields masked."""
    just_fix_windows_console()

    if not os.path.isfile(user_config_path):
        print(f"{Fore.RED}Config not found: {user_config_path}{Style.RESET_ALL}")
        return

    try:
        cfg = load_json_config(user_config_path)
    except Exception as e:
        print(f"{Fore.RED}Failed to load config: {e}{Style.RESET_ALL}")
        return

    masked = _mask_dict(cfg)
    print(f"{Fore.GREEN}--- User Config (credentials masked) ---{Style.RESET_ALL}")
    print(json.dumps(masked, indent=4))


def _get_editor() -> str:
    """Return the user's preferred editor, falling back to platform defaults."""
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if editor:
        return editor
    if platform.system() == "Windows":
        return "notepad"
    # Try common editors in order
    for candidate in ("nano", "vi"):
        if shutil.which(candidate):
            return candidate
    return "vi"


def edit_config(user_config_path: str) -> None:
    """Decrypt config → open in $EDITOR → re-encrypt on save."""
    just_fix_windows_console()

    if not os.path.isfile(user_config_path):
        print(f"{Fore.RED}Config not found: {user_config_path}{Style.RESET_ALL}")
        return

    try:
        cfg = load_json_config(user_config_path)
    except Exception as e:
        print(f"{Fore.RED}Failed to load config: {e}{Style.RESET_ALL}")
        return

    editor = _get_editor()

    # Write decrypted JSON to a secure temp file
    fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="m4b-config-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(cfg, f, indent=4)

        print(
            f"{Fore.CYAN}Opening config in {editor}... "
            f"Save and close to re-encrypt.{Style.RESET_ALL}"
        )

        result = subprocess.run([editor, tmp_path])  # noqa: S603
        if result.returncode != 0:
            print(
                f"{Fore.RED}Editor exited with error "
                f"(code {result.returncode}). Config unchanged.{Style.RESET_ALL}"
            )
            return

        # Validate edited JSON before overwriting
        with open(tmp_path) as f:
            edited = json.load(f)

        # Write back via dumper to preserve encryption state
        from utils.dumper import write_json

        write_json(edited, user_config_path)

        # Ensure encrypted (in case the file was previously unencrypted)
        ensure_config_encrypted(user_config_path)

        print(f"{Fore.GREEN}Config updated and encrypted.{Style.RESET_ALL}")
    except json.JSONDecodeError as e:
        print(
            f"{Fore.RED}Invalid JSON after editing: {e}\n"
            f"Config unchanged.{Style.RESET_ALL}"
        )
    finally:
        # Securely remove temp file (overwrite before delete)
        try:
            with open(tmp_path, "w") as f:
                f.write("\0" * 4096)
            os.unlink(tmp_path)
        except OSError:
            pass
