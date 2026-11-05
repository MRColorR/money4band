from __future__ import annotations

import logging
import os
import platform
from typing import Any

import psutil

from money4band.core.dumper import write_json
from money4band.core.loader import load_json_config

logger = logging.getLogger(__name__)


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


def _get_tiers(m4b_config: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Return tier multipliers from ``resource_profiles.tiers`` in *m4b_config*."""
    tiers: dict[str, dict[str, float]] = m4b_config["resource_profiles"]["tiers"]
    return tiers


def _get_minimums(
    m4b_config: dict[str, Any],
) -> tuple[dict[str, dict[str, int]], dict[str, float]]:
    """Return ``(min_mem, min_cpu)`` from ``resource_profiles.minimums`` in *m4b_config*.

    ``min_mem`` maps ``"reserv"`` and ``"limit"`` to per-tier dicts
    (e.g. ``{"little": 32, "medium": 64, ...}``).
    """
    mins = m4b_config["resource_profiles"]["minimums"]
    raw_reserv = mins["mem_reserv_mb"]
    raw_limit = mins["mem_limit_mb"]
    # Support both legacy scalar and new per-tier dict formats.
    if isinstance(raw_reserv, dict):
        min_mem = {"reserv": raw_reserv, "limit": raw_limit}
    else:
        min_mem = {
            "reserv": dict.fromkeys(("little", "medium", "big", "huge"), raw_reserv),
            "limit": dict.fromkeys(("little", "medium", "big", "huge"), raw_limit),
        }
    min_cpu = mins["cpu"]
    return min_mem, min_cpu


def get_valid_profiles(m4b_config: dict[str, Any]) -> tuple[str, ...]:
    """Return the valid profile names from *m4b_config*."""
    keys = m4b_config.get("resource_profiles", {}).get("profiles", {}).keys()
    return tuple(keys) if keys else ()


def get_active_profile(user_config: dict[str, Any]) -> str:
    """Return the currently active resource profile name."""
    return str(user_config.get("settings", {}).get("resource_profile", "standard"))


def get_profile_definition(
    m4b_config: dict[str, Any],
    name: str | None = None,
    *,
    user_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the profile dict for *name* defaulting to standard."""
    rp = m4b_config.get("resource_profiles", {})
    if name is None:
        name = get_active_profile(user_config) if user_config else "standard"
    profile: dict[str, Any] = rp.get("profiles", {}).get(
        name, {"cpu_pct": 0.60, "ram_pct": 0.40}
    )
    return profile


def calculate_resource_limits(
    user_config_path_or_dict: Any,
    m4b_config: dict[str, Any] | None = None,
) -> None:
    """Compute per-tier resource limits using the active profile and system specs.

    The active profile determines the base CPU/RAM allocation via ``cpu_pct``
    (fraction of detected cores) and ``ram_pct`` (fraction of total RAM).
    Per-app tiers (LITTLE / MEDIUM / BIG / HUGE) then scale these bases with
    fixed multipliers so heavier apps get proportionally more.
    """
    logger.debug("Determining resource limits")
    user_config = load_json_config(user_config_path_or_dict)
    total_memory, cores = get_system_memory_and_cores()

    # Resolve the active profile's base values.
    if m4b_config is None:
        raise ValueError("m4b_config is required for resource limit calculation")
    profile = get_profile_definition(m4b_config, user_config=user_config)
    base_ram_mb = total_memory * profile.get("ram_pct", 0.40)
    base_cpu = cores * profile.get("cpu_pct", 0.60)

    tiers = _get_tiers(m4b_config)
    min_mem, min_cpu = _get_minimums(m4b_config)

    resource_limits = {}
    for tier, mult in tiers.items():
        mem_r = int(
            max(base_ram_mb * mult["mem_reserv"], min_mem["reserv"].get(tier, 64))
        )
        mem_l = int(
            max(base_ram_mb * mult["mem_limit"], min_mem["limit"].get(tier, 128))
        )
        cpu = round(max(base_cpu * mult["cpu"], min_cpu.get(tier, 0.5)), 1)
        resource_limits[f"app_mem_reserv_{tier}"] = f"{mem_r}m"
        resource_limits[f"app_mem_limit_{tier}"] = f"{mem_l}m"
        resource_limits[f"app_cpu_limit_{tier}"] = cpu

    user_config.setdefault("resource_limits", {}).update(resource_limits)
    write_json(user_config, user_config_path_or_dict)
    logger.debug(
        "Resource limits updated (profile=%s, base_ram=%.0f MB, base_cpu=%.1f)",
        get_active_profile(user_config),
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
    active = get_active_profile(user_config)
    profile = get_profile_definition(m4b_config, active)

    print(
        f"\n{Fore.CYAN}System:{Style.RESET_ALL} {total_mem:.0f} MB RAM, {cores} cores"
    )
    print(
        f"{Fore.CYAN}Active profile:{Style.RESET_ALL} {Fore.GREEN}{active}{Style.RESET_ALL} - {profile.get('description', '')}"
    )

    rl = user_config.get("resource_limits", {})
    print(f"\n  {'Tier':<8} {'Mem Limit':<12} {'Mem Reserv':<12} {'CPU Limit'}")
    print(f"  {'-' * 8} {'-' * 12} {'-' * 12} {'-' * 9}")
    for tier in ("little", "medium", "big", "huge"):
        ml = rl.get(f"app_mem_limit_{tier}", "?")
        mr = rl.get(f"app_mem_reserv_{tier}", "?")
        cl = rl.get(f"app_cpu_limit_{tier}", "?")
        print(f"  {tier.upper():<8} {ml:<12} {mr:<12} {cl}")

    # Show what each profile would allocate on THIS device
    profiles = m4b_config.get("resource_profiles", {}).get("profiles", {})
    print(f"\n  {Fore.CYAN}Profile comparison on this device:{Style.RESET_ALL}")
    print(f"  {'Profile':<14} {'CPU%':<6} {'RAM%':<6} {'Base CPUs':<11} {'Base RAM'}")
    print(f"  {'-' * 14} {'-' * 6} {'-' * 6} {'-' * 11} {'-' * 10}")
    for pname, pdef in profiles.items():
        cpu_pct = pdef.get("cpu_pct", 0)
        ram_pct = pdef.get("ram_pct", 0)
        marker = f" {Fore.GREEN}<-{Style.RESET_ALL}" if pname == active else ""
        print(
            f"  {pname:<14} {cpu_pct:<6.0%} {ram_pct:<6.0%} "
            f"{cores * cpu_pct:<11.1f} {total_mem * ram_pct:.0f} MB{marker}"
        )


# ---------------------------------------------------------------------------
# WSL detection
# ---------------------------------------------------------------------------


def is_running_in_wsl() -> bool:
    """Return ``True`` when the current process is inside a WSL distribution."""
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        with open("/proc/version") as fh:
            version_text = fh.read().lower()
        return "microsoft" in version_text or "wsl" in version_text
    except OSError:
        return False


def get_wsl_version() -> str | None:
    """Return the WSL kernel version string, or ``None`` if unavailable.

    Parses the output of ``wsl.exe --version`` which shows lines like
    ``WSL version: 2.4.4.0``.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["wsl.exe", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for raw_line in result.stdout.replace("\x00", "").splitlines():
            stripped = raw_line.strip()
            lower = stripped.lower()
            if lower.startswith("wsl version"):
                parts = stripped.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
        return None
    except Exception:
        return None


def get_wsl_networking_mode() -> str:
    """Detect the WSL networking mode from ``.wslconfig``.

    Returns:
        ``"mirrored"``, ``"nat"`` (explicit setting), or ``"not_set"``
        (no .wslconfig or no networkingMode line found).
    """
    import subprocess

    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "echo", "%USERPROFILE%"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        win_profile = result.stdout.strip().replace("\r", "")
        if not win_profile or "%" in win_profile:
            return "not_set"

        result2 = subprocess.run(
            ["wslpath", win_profile],
            capture_output=True,
            text=True,
            timeout=5,
        )
        wsl_profile = result2.stdout.strip()
        if not wsl_profile:
            return "not_set"

        config_path = os.path.join(wsl_profile, ".wslconfig")
        if not os.path.isfile(config_path):
            return "not_set"

        with open(config_path) as fh:
            for line in fh:
                stripped = line.strip().lower()
                if stripped.startswith("networkingmode"):
                    _, _, value = stripped.partition("=")
                    value = value.strip()
                    if value == "mirrored":
                        return "mirrored"
                    return value or "not_set"

        return "not_set"
    except Exception:
        return "not_set"


def detect_wsl_environment() -> dict[str, object]:
    """Collect WSL environment details.

    Returns a dict with keys:
    - ``is_wsl``: bool
    - ``wsl_version``: str | None
    - ``networking_mode``: ``"mirrored"`` | ``"nat"`` | ``"not_set"``
    - ``distro``: str | None (WSL_DISTRO_NAME)
    """
    in_wsl = is_running_in_wsl()
    if not in_wsl:
        return {
            "is_wsl": False,
            "wsl_version": None,
            "networking_mode": "not_set",
            "distro": None,
        }

    return {
        "is_wsl": True,
        "wsl_version": get_wsl_version(),
        "networking_mode": get_wsl_networking_mode(),
        "distro": os.environ.get("WSL_DISTRO_NAME"),
    }
