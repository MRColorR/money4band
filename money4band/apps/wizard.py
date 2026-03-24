from __future__ import annotations

import json
import logging
import os
from typing import Any

from colorama import Fore, Style

from money4band.apps.schema import validate_app_entry

logger = logging.getLogger(__name__)

_AUTH_TYPES = {
    "1": ("email", "Email + Password"),
    "2": ("token", "API Token"),
    "3": ("uuid", "UUID"),
    "4": ("userid", "User ID / CID"),
    "5": ("manual", "Manual (browser-based)"),
}

_LAYER_CHOICES = {
    "1": "residential",
    "2": "universal",
    "3": "datacenter",
}


def _prompt(msg: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    suffix = f" [{default}]" if default else ""
    val = input(f"{Fore.GREEN}{msg}{suffix}:{Style.RESET_ALL} ").strip()
    return val or default


def _prompt_choice(msg: str, choices: dict[str, tuple[str, str]]) -> str:
    """Prompt user to choose from numbered options. Returns the key."""
    print(f"\n{Fore.CYAN}{msg}{Style.RESET_ALL}")
    for num, (_, label) in sorted(choices.items()):
        print(f"  {num}. {label}")
    while True:
        val = input(f"{Fore.GREEN}Select:{Style.RESET_ALL} ").strip()
        if val in choices:
            return val
        print(
            f"{Fore.RED}Invalid choice. Enter {'/'.join(sorted(choices))}.{Style.RESET_ALL}"
        )


def run_app_wizard(apps_d_dir: str) -> dict[str, Any] | None:
    """Run the interactive app-add wizard.

    Creates a community app JSON file in *apps_d_dir*.
    Returns the app entry dict, or ``None`` if the user cancels.
    """
    print(f"\n{Fore.CYAN}{'=' * 50}")
    print("  M4B — Add New App Wizard")
    print(f"{'=' * 50}{Style.RESET_ALL}\n")

    # --- Name ---
    name = _prompt("App name (UPPERCASE, e.g. MYAPP)").upper().replace(" ", "_")
    if not name:
        print(f"{Fore.RED}Cancelled — no name provided.{Style.RESET_ALL}")
        return None

    # --- Docker image ---
    image = _prompt("Docker image (e.g. publisher/app:latest)")
    if not image:
        print(f"{Fore.RED}Cancelled — no image provided.{Style.RESET_ALL}")
        return None

    # --- Auth type ---
    choice = _prompt_choice("Authentication type:", _AUTH_TYPES)
    auth_key = _AUTH_TYPES[choice][0]

    flags: dict[str, Any] = {}
    if auth_key == "email":
        flags["email"] = {}
        flags["password"] = {}
    elif auth_key == "token":
        flags["token"] = {}
    elif auth_key == "uuid":
        length = _prompt("UUID length", "32")
        flags["uuid"] = {"length": int(length)}
    elif auth_key == "userid":
        flags["userid"] = {}
    else:
        flags["manual_onboard"] = True

    # --- Compose layer ---
    layer_choice = _prompt_choice(
        "Network tier:",
        {
            "1": ("residential", "Residential (home IP required)"),
            "2": ("universal", "Universal (any IP type)"),
            "3": ("datacenter", "Datacenter / VPS"),
        },
    )
    compose_layer = _LAYER_CHOICES[layer_choice]

    # --- Install limit ---
    limit_str = _prompt("Install limit (-1 = unlimited)", "-1")
    try:
        install_limit = int(limit_str)
    except ValueError:
        install_limit = -1

    # --- Optional fields ---
    dashboard = _prompt("Dashboard URL (optional, press Enter to skip)") or None
    link = _prompt("Registration/referral link (optional)") or None

    # --- Build entry ---
    entry: dict[str, Any] = {
        "name": name,
        "compose_config": {
            "container_name": f"${{DEVICE_NAME}}_{name.lower()}",
            "hostname": f"${{DEVICE_NAME}}_{name.lower()}",
            "image": image,
            "environment": [],
            "labels": [
                "com.centurylinklabs.watchtower.enable=true",
                "com.centurylinklabs.watchtower.scope=${M4B_WATCHTOWER_SCOPE}",
            ],
            "restart": "always",
            "cpus": "${APP_CPU_LIMIT_MEDIUM}",
            "mem_reservation": "${APP_MEM_RESERV_MEDIUM}",
            "mem_limit": "${APP_MEM_LIMIT_MEDIUM}",
            "logging": {
                "driver": "json-file",
                "options": {"max-size": "10m", "max-file": "3"},
            },
            "healthcheck": {
                "test": ["CMD-SHELL", f"pgrep -f {name.lower()} || exit 1"],
                "interval": "120s",
                "timeout": "10s",
                "retries": 3,
                "start_period": "60s",
            },
        },
        "compose_config_proxy": {
            "network_mode": "service:proxy",
            "hostname": None,
        },
        "flags": flags,
        "install_limit": install_limit,
        "compose_layer": compose_layer,
    }
    if dashboard:
        entry["dashboard"] = dashboard
    if link:
        entry["link"] = link

    # --- Validate ---
    errors = validate_app_entry(entry)
    if errors:
        print(f"\n{Fore.RED}Validation errors:{Style.RESET_ALL}")
        for e in errors:
            print(f"  - {e}")
        return None

    # --- Write to apps.d/ ---
    os.makedirs(apps_d_dir, exist_ok=True)
    filepath = os.path.join(apps_d_dir, f"{name}.json")
    if os.path.exists(filepath):
        overwrite = (
            input(
                f"{Fore.YELLOW}{filepath} already exists. Overwrite? (y/N):{Style.RESET_ALL} "
            )
            .strip()
            .lower()
        )
        if overwrite not in ("y", "yes"):
            print("Cancelled.")
            return None

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=4, ensure_ascii=False)

    print(f"\n{Fore.GREEN}App '{name}' saved to {filepath}{Style.RESET_ALL}")
    print(
        f"{Fore.CYAN}It will be merged into candidate-apps on next startup.{Style.RESET_ALL}"
    )

    return entry
