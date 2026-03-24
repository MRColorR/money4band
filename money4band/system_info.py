from __future__ import annotations

"""Centralised system information dashboard and DNS management."""

import ipaddress
import os
import shutil
import sys
from typing import Any

from colorama import Fore, Style, just_fix_windows_console

from money4band import detector
from money4band.cls import cls
from money4band.dumper import write_json
from money4band.loader import load_json_config
from money4band.updater import check_for_update

# ---------------------------------------------------------------------------
# DNS helpers — all data lives in m4b-config.json (system.dns section).
# ---------------------------------------------------------------------------


def _dns_section(m4b_config: dict[str, Any]) -> dict[str, Any]:
    """Return the ``system.dns`` section from *m4b_config*."""
    return m4b_config.get("system", {}).get("dns", {})


def get_dns_modes(m4b_config: dict[str, Any]) -> tuple[str, ...]:
    """Return the available DNS modes from config."""
    return tuple(_dns_section(m4b_config).get("available_modes", ()))


def get_dns_presets(m4b_config: dict[str, Any]) -> dict[str, list[str]]:
    """Return DNS presets from config."""
    return dict(_dns_section(m4b_config).get("presets", {}))


def get_default_servers(m4b_config: dict[str, Any]) -> list[str]:
    """Return the default DNS servers from config."""
    return list(_dns_section(m4b_config).get("default_servers", []))


def is_valid_ipv4(address: str) -> bool:
    """Return True if *address* is a valid IPv4 address."""
    try:
        ipaddress.IPv4Address(address)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def compose_regen_reminder() -> None:
    """Print a reminder to regenerate compose files after a config change."""
    print(
        f"\n{Fore.YELLOW}Compose files need regenerating for this change to take effect.{Style.RESET_ALL}"
    )
    print(
        f"  Use {Fore.CYAN}'Regenerate files from config'{Style.RESET_ALL} in the menu "
        f"or {Fore.CYAN}m4b generate{Style.RESET_ALL} from the CLI."
    )
    input(f"\nPress {Fore.CYAN}Enter{Style.RESET_ALL} to continue...")


def get_dns_config(m4b_config: dict[str, Any]) -> dict[str, Any]:
    """Return the DNS section from the system config."""
    return m4b_config.get("system", {}).get(
        "dns", {"mode": "default", "servers": get_default_servers(m4b_config)}
    )


def set_dns_mode(
    m4b_config_path: str, mode: str, servers: list[str] | None = None
) -> None:
    """Persist a DNS mode (and optional server list) to m4b-config.json."""
    cfg = load_json_config(m4b_config_path)
    valid_modes = get_dns_modes(cfg)
    if mode not in valid_modes:
        raise ValueError(
            f"Invalid DNS mode '{mode}'. Choose from: {', '.join(valid_modes)}"
        )
    if servers is not None:
        invalid = [s for s in servers if not is_valid_ipv4(s)]
        if invalid:
            raise ValueError(f"Invalid IPv4 address(es): {', '.join(invalid)}")
    dns = cfg.setdefault("system", {}).setdefault("dns", {})
    dns["mode"] = mode
    if servers is not None:
        dns["servers"] = servers
    else:
        presets = get_dns_presets(cfg)
        if mode in presets:
            dns["servers"] = presets[mode]
    write_json(cfg, m4b_config_path)


def show_dns_status(m4b_config: dict[str, Any]) -> None:
    """Print the current DNS configuration."""
    just_fix_windows_console()
    dns = get_dns_config(m4b_config)
    mode = dns.get("mode", "default")
    servers = dns.get("servers", [])
    print(f"\n{Fore.CYAN}DNS Configuration{Style.RESET_ALL}")
    print(f"  Mode:    {Fore.GREEN}{mode}{Style.RESET_ALL}")
    if mode == "custom":
        print(f"  Servers: {', '.join(servers)}")
    else:
        print("  Servers: (host default — Docker inherits from the host resolver)")


def dns_interactive(m4b_config_path: str) -> None:
    """Interactive DNS configuration prompt."""
    just_fix_windows_console()
    m4b_config = load_json_config(m4b_config_path)
    show_dns_status(m4b_config)

    dns = get_dns_config(m4b_config)
    current_servers = dns.get("servers", get_default_servers(m4b_config))
    current_mode = dns.get("mode", "default")
    current_hint = (
        f"current: {', '.join(current_servers)}"
        if current_mode == "custom"
        else "current: host DNS"
    )

    print(
        f"\n{Fore.YELLOW}Enter up to two IPv4 DNS servers, comma-separated.{Style.RESET_ALL}"
    )
    print(f"  Example: {Fore.CYAN}1.1.1.1, 8.8.8.8{Style.RESET_ALL}")
    print(f"  Leave empty to use the host machine's DNS ({current_hint}).")

    while True:
        raw = input(f"{Fore.GREEN}DNS servers>{Style.RESET_ALL} ").strip()

        if not raw:
            set_dns_mode(m4b_config_path, "default")
            print(f"{Fore.GREEN}DNS set to host default.{Style.RESET_ALL}")
            break

        servers = [s.strip() for s in raw.split(",") if s.strip()][:2]
        invalid = [s for s in servers if not is_valid_ipv4(s)]
        if invalid:
            print(
                f"  {Fore.RED}Invalid IPv4 address(es): {', '.join(invalid)}{Style.RESET_ALL}"
            )
            continue

        set_dns_mode(m4b_config_path, "custom", servers)
        print(f"{Fore.GREEN}DNS set to custom: {', '.join(servers)}{Style.RESET_ALL}")
        break

    compose_regen_reminder()


# ---------------------------------------------------------------------------
# System info dashboard
# ---------------------------------------------------------------------------


def show_system_info(
    m4b_config: dict[str, Any],
    app_config: dict[str, Any],
    user_config: dict[str, Any],
) -> None:
    """Print a comprehensive system information dashboard."""
    just_fix_windows_console()
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    # ---- Version & update ----
    version = m4b_config.get("project", {}).get("project_version", "?")
    new_version = check_for_update(m4b_config)
    update_str = (
        f"{Fore.YELLOW}v{new_version} available{Style.RESET_ALL}"
        if new_version
        else f"{Fore.GREEN}up to date{Style.RESET_ALL}"
    )

    # ---- OS & architecture ----
    device = user_config.get("device_info", {})
    os_type = device.get("os_type", "unknown")
    arch = device.get("detected_architecture", "unknown")
    dk_arch = device.get("detected_docker_arch", "unknown")
    dk_platform = m4b_config.get("system", {}).get(
        "default_docker_platform", "linux/amd64"
    )

    # ---- Resource profile ----
    active_profile = detector.get_active_profile(m4b_config)
    profile_def = detector.get_profile_definition(m4b_config, active_profile)
    try:
        total_mem, cores = detector.get_system_memory_and_cores()
    except Exception:
        total_mem, cores = 0, 0

    # ---- DNS ----
    dns = get_dns_config(m4b_config)
    dns_mode = dns.get("mode", "default")
    dns_servers = dns.get("servers", [])

    # ---- Apps ----
    apps_cfg = user_config.get("apps", {})
    enabled_apps = [
        name
        for name, cfg in apps_cfg.items()
        if isinstance(cfg, dict) and cfg.get("enabled", False)
    ]
    total_supported = 0
    for _cat_key, cat in app_config.items():
        if isinstance(cat, dict) and cat.get("active", False):
            total_supported += len(cat.get("entries", []))

    # ---- Proxy ----
    proxy = user_config.get("proxies", {})
    proxy_enabled = proxy.get("enabled", False)

    # ---- Watchtower ----
    wt = user_config.get("watchtower", {})
    wt_enabled = wt.get("enabled", True)

    # ---- Dashboard ----
    dash = user_config.get("m4b_dashboard", {})
    dash_enabled = dash.get("enabled", False)

    # ---- Docker availability ----
    docker_ok = shutil.which("docker") is not None
    docker_running = False
    multiarch = False
    if docker_ok:
        from money4band.helper import (
            is_docker_daemon_running,
            is_multiarch_emulation_available,
        )

        docker_running = is_docker_daemon_running()
        if docker_running:
            multiarch = is_multiarch_emulation_available()

    # ---- Compose files ----
    from money4band.compose_builder import get_compose_files

    compose_files = get_compose_files(".")
    compose_mode = (
        "layered"
        if len(compose_files) > 1
        else ("monolithic" if compose_files else "none")
    )

    # ---- Print ----
    w = 22  # label column width
    print(f"\n{Fore.CYAN}{'=' * 50}")
    print("  M4B System Information")
    print(f"{'=' * 50}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}Version & Updates{Style.RESET_ALL}")
    print(f"  {'Version:':<{w}} {Fore.GREEN}v{version}{Style.RESET_ALL}")
    print(f"  {'Update:':<{w}} {update_str}")

    print(f"\n{Fore.CYAN}System{Style.RESET_ALL}")
    print(f"  {'OS:':<{w}} {os_type}")
    print(f"  {'Architecture:':<{w}} {arch}")
    print(f"  {'Docker arch:':<{w}} {dk_arch}")
    print(f"  {'Default platform:':<{w}} {dk_platform}")
    print(
        f"  {'Docker installed:':<{w}} {'yes' if docker_ok else f'{Fore.RED}no{Style.RESET_ALL}'}"
    )
    if docker_ok:
        print(
            f"  {'Docker running:':<{w}} {'yes' if docker_running else f'{Fore.RED}no{Style.RESET_ALL}'}"
        )
        print(f"  {'Multiarch (QEMU):':<{w}} {'yes' if multiarch else 'no'}")
        if multiarch:
            print(
                f"    {Fore.GREEN}\u21b3 Cross-arch apps run via QEMU emulation{Style.RESET_ALL}"
            )
        else:
            print(
                f"    {Fore.YELLOW}\u21b3 Native {dk_arch} only \u2014 "
                f"install QEMU/binfmt or launch Docker Desktop{Style.RESET_ALL}"
            )
    print(f"  {'Image preference:':<{w}} {dk_arch} (when app image supports it)")
    if total_mem:
        print(f"  {'RAM:':<{w}} {total_mem:.0f} MB")
        print(f"  {'CPU cores:':<{w}} {cores}")

    print(f"\n{Fore.CYAN}Resource Profile{Style.RESET_ALL}")
    print(f"  {'Active profile:':<{w}} {active_profile}")
    print(f"  {'Description:':<{w}} {profile_def.get('description', '')}")

    print(f"\n{Fore.CYAN}DNS{Style.RESET_ALL}")
    print(f"  {'Mode:':<{w}} {dns_mode}")
    if dns_mode == "custom":
        print(f"  {'Servers:':<{w}} {', '.join(dns_servers)}")
    else:
        print(f"  {'Servers:':<{w}} (host default)")

    print(f"\n{Fore.CYAN}Apps & Services{Style.RESET_ALL}")
    print(f"  {'Enabled apps:':<{w}} {len(enabled_apps)}/{total_supported}")
    if enabled_apps:
        print(f"  {'Active:':<{w}} {', '.join(enabled_apps)}")
    print(f"  {'Proxy:':<{w}} {'enabled' if proxy_enabled else 'disabled'}")
    print(f"  {'Watchtower:':<{w}} {'enabled' if wt_enabled else 'disabled'}")
    print(f"  {'Dashboard:':<{w}} {'enabled' if dash_enabled else 'disabled'}")

    print(f"\n{Fore.CYAN}Compose{Style.RESET_ALL}")
    print(f"  {'Mode:':<{w}} {compose_mode}")
    if compose_files:
        for cf in compose_files:
            print(f"  {'  '}{os.path.basename(cf)}")

    print()


# ---------------------------------------------------------------------------
# Menu / module entry point
# ---------------------------------------------------------------------------


def main(
    app_config_path: str,
    m4b_config_path: str,
    user_config_path: str,
) -> None:
    """Entry point when invoked from the interactive menu or module loader."""
    while True:
        cls()
        m4b_config = load_json_config(m4b_config_path)
        app_config = load_json_config(app_config_path)
        user_config = load_json_config(user_config_path)

        show_system_info(m4b_config, app_config, user_config)

        print(
            f"\n  {Fore.CYAN}d{Style.RESET_ALL} DNS settings  |  "
            f"{Fore.CYAN}b{Style.RESET_ALL} Back  |  "
            f"{Fore.CYAN}q{Style.RESET_ALL} Quit"
        )
        choice = input("Select: ").strip().lower()
        if choice == "d":
            dns_interactive(m4b_config_path)
        elif choice == "q":
            raise SystemExit(0)
        else:
            break
