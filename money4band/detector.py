from __future__ import annotations

import logging
import os
import platform

# Ensure the parent directory is in the sys.path
import sys
from typing import Any

import psutil

from money4band.dumper import write_json
from money4band.loader import load_json_config

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import the module from the parent directory


def detect_os(m4b_config_path_or_dict: Any) -> dict[str, str]:
    """
    Detect the operating system based on the system's platform and map it according to the m4b configuration.

    Args:
        m4b_config_path_or_dict (Any): The path to the m4b config file or the config dictionary.

    Returns:
        Dict[str, str]: A dictionary containing the detected OS type.

    Raises:
        Exception: If an error occurs during OS detection or if the OS is not recognized.
    """
    try:
        m4b_config = load_json_config(m4b_config_path_or_dict)

        logger.debug("Detecting OS type")
        os_map = m4b_config.get("system", {}).get("os_map", {})

        # Get the OS type from the platform module and convert it to lowercase
        detected_os = platform.system().lower()
        logger.info(f"Detected OS: {detected_os}")

        # Map the detected OS using the os_map from the config
        mapped_os = os_map.get(detected_os, "unknown")

        if mapped_os == "unknown":
            raise ValueError(
                f"OS type '{detected_os}' is not recognized in the provided os_map."
            )

        logger.info(f"Mapped OS: {mapped_os}")
        return {"os_type": mapped_os}

    except KeyError as e:
        logger.error(f"KeyError in configuration: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"An error occurred while detecting OS: {str(e)}")
        raise


def detect_architecture(m4b_config_path_or_dict: Any) -> dict[str, str]:
    """
    Detect the system architecture and return its type.

    Args:
        m4b_config_path_or_dict (Any): The path to the m4b config file or the config dictionary.

    Returns:
        Dict[str, str]: A dictionary containing the detected architecture and Docker architecture.

    Raises:
        Exception: If an error occurs during architecture detection.
    """
    try:
        m4b_config = load_json_config(m4b_config_path_or_dict)

        logger.debug("Detecting system architecture")
        arch_map = m4b_config.get("system", {}).get("arch_map", {})
        arch = platform.machine().lower()
        dkarch = arch_map.get(arch, "unknown")
        logger.info(
            f"System architecture detected: {arch}, Docker architecture has been set to {dkarch}"
        )
        return {"arch": arch, "dkarch": dkarch}
    except Exception as e:
        logger.error(f"An error occurred while detecting architecture: {str(e)}")
        raise


def get_system_memory_and_cores() -> tuple[float, int | None]:
    logger.debug("Retrieving system memory and cores")
    total_memory = psutil.virtual_memory().total / (1024**2)
    cores = psutil.cpu_count(logical=False)
    logger.debug(f"Total RAM: {total_memory:.2f} MB, CPU cores: {cores}")
    return total_memory, cores


# ---------------------------------------------------------------------------
# Resource-limit profiles
# ---------------------------------------------------------------------------

# Per-app tier multipliers applied on top of the profile base.
# Keys match the LITTLE/MEDIUM/BIG/HUGE tiers used in app-config.json.
_TIER_MULTIPLIERS = {
    "little": {"mem_reserv": 0.2, "mem_limit": 0.4, "cpu": 0.2},
    "medium": {"mem_reserv": 0.4, "mem_limit": 0.6, "cpu": 0.4},
    "big": {"mem_reserv": 0.6, "mem_limit": 0.8, "cpu": 0.6},
    "huge": {"mem_reserv": 0.8, "mem_limit": 1.0, "cpu": 0.8},
}

# Absolute minimums so containers always get something usable.
_MIN_MEM = {"reserv": 64, "limit": 128}
_MIN_CPU = {"little": 0.8, "medium": 1.0, "big": 1.0, "huge": 1.0}

VALID_PROFILES = ("base", "min", "low", "mid", "max")


def get_active_profile(m4b_config: dict[str, Any]) -> str:
    """Return the currently active resource profile name."""
    return m4b_config.get("resource_profiles", {}).get("active", "low")


def get_profile_definition(
    m4b_config: dict[str, Any], name: str | None = None
) -> dict[str, Any]:
    """Return the profile dict for *name* (defaults to active)."""
    rp = m4b_config.get("resource_profiles", {})
    name = name or rp.get("active", "low")
    return rp.get("profiles", {}).get(name, {"cpu_factor": 1.0, "ram_pct": 0.1875})


def calculate_resource_limits(
    user_config_path_or_dict: Any,
    m4b_config: dict[str, Any] | None = None,
) -> None:
    """Compute per-tier resource limits using the active profile and system specs.

    The active profile in ``m4b_config["resource_profiles"]["active"]``
    determines the base CPU/RAM allocation via ``cpu_factor`` (multiplied by
    detected cores) and ``ram_pct`` (fraction of total RAM).  Per-app tiers
    (LITTLE / MEDIUM / BIG / HUGE) then scale these bases with fixed
    multipliers so heavier apps get proportionally more.
    """
    logger.debug("Determining resource limits")
    user_config = load_json_config(user_config_path_or_dict)
    total_memory, cores = get_system_memory_and_cores()

    # Resolve the active profile's base values.
    if m4b_config is None:
        m4b_config = {}
    profile = get_profile_definition(m4b_config)
    base_ram_mb = total_memory * profile.get("ram_pct", 0.1875)
    base_cpu = cores * profile.get("cpu_factor", 1.0)

    resource_limits = {}
    for tier, mult in _TIER_MULTIPLIERS.items():
        mem_r = int(max(base_ram_mb * mult["mem_reserv"], _MIN_MEM["reserv"]))
        mem_l = int(max(base_ram_mb * mult["mem_limit"], _MIN_MEM["limit"]))
        cpu = round(max(base_cpu * mult["cpu"], _MIN_CPU[tier]), 1)
        resource_limits[f"app_mem_reserv_{tier}"] = f"{mem_r}m"
        resource_limits[f"app_mem_limit_{tier}"] = f"{mem_l}m"
        resource_limits[f"app_cpu_limit_{tier}"] = cpu

    # Preserve the ram_cap_mb_default key for backward compat.
    resource_limits["ram_cap_mb_default"] = user_config.get("resource_limits", {}).get(
        "ram_cap_mb_default", 6144
    )

    user_config.setdefault("resource_limits", {}).update(resource_limits)
    write_json(user_config, user_config_path_or_dict)
    logger.debug(
        "Resource limits updated (profile=%s, base_ram=%.0f MB, base_cpu=%.1f)",
        get_active_profile(m4b_config),
        base_ram_mb,
        base_cpu,
    )


def show_resource_profile_info(
    m4b_config: dict[str, Any],
    user_config: dict[str, Any],
) -> None:
    """Print the active profile, system stats, and per-tier limits."""
    from colorama import Fore, Style

    total_mem, cores = get_system_memory_and_cores()
    active = get_active_profile(m4b_config)
    profile = get_profile_definition(m4b_config, active)

    print(f"\n{Fore.CYAN}Resource Profile: {Fore.GREEN}{active}{Style.RESET_ALL}")
    print(f"  {profile.get('description', '')}")
    print(f"  System: {total_mem:.0f} MB RAM, {cores} cores")
    print(
        f"  Base allocation: "
        f"{total_mem * profile.get('ram_pct', 0):.0f} MB RAM, "
        f"{cores * profile.get('cpu_factor', 0):.1f} CPUs"
    )

    rl = user_config.get("resource_limits", {})
    print(f"\n  {'Tier':<8} {'Mem Limit':<12} {'Mem Reserv':<12} {'CPU Limit'}")
    print(f"  {'-' * 8} {'-' * 12} {'-' * 12} {'-' * 9}")
    for tier in ("little", "medium", "big", "huge"):
        ml = rl.get(f"app_mem_limit_{tier}", "?")
        mr = rl.get(f"app_mem_reserv_{tier}", "?")
        cl = rl.get(f"app_cpu_limit_{tier}", "?")
        print(f"  {tier.upper():<8} {ml:<12} {mr:<12} {cl}")

    profiles = m4b_config.get("resource_profiles", {}).get("profiles", {})
    print(f"\n  Available profiles: {', '.join(profiles)}")
    print(f"  Change with: {Fore.YELLOW}m4b limit <profile>{Style.RESET_ALL}\n")
