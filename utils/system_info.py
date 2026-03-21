"""Centralised system information dashboard and DNS management."""

import os
import shutil
from typing import Any

from colorama import Fore, Style, just_fix_windows_console

from utils import detector
from utils.dumper import write_json
from utils.loader import load_json_config
from utils.updater import check_for_update

# ---------------------------------------------------------------------------
# DNS helpers
# ---------------------------------------------------------------------------

DNS_MODES = ("default", "custom")
_DEFAULT_SERVERS = ["1.1.1.1", "8.8.8.8"]


def get_dns_config(m4b_config: dict) -> dict:
    """Return the DNS section from the system config."""
    return m4b_config.get("system", {}).get("dns", {"mode": "default", "servers": _DEFAULT_SERVERS})


def set_dns_mode(m4b_config_path: str, mode: str, servers: list[str] | None = None) -> None:
    """Persist a DNS mode (and optional server list) to m4b-config.json."""
    if mode not in DNS_MODES:
        raise ValueError(f"Invalid DNS mode '{mode}'. Choose from: {', '.join(DNS_MODES)}")
    cfg = load_json_config(m4b_config_path)
    dns = cfg.setdefault("system", {}).setdefault("dns", {})
    dns["mode"] = mode
    if servers is not None:
        dns["servers"] = servers
    write_json(cfg, m4b_config_path)


def show_dns_status(m4b_config: dict) -> None:
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
    current_mode = dns.get("mode", "default")

    print(f"\n{Fore.YELLOW}Choose DNS mode:{Style.RESET_ALL}")
    print("  1. default  — containers use the host machine's DNS (recommended)")
    print("  2. custom   — inject specific DNS servers into every container")
    choice = input("Select [1/2] (Enter to keep current): ").strip()

    if choice == "1":
        set_dns_mode(m4b_config_path, "default")
        print(f"{Fore.GREEN}DNS set to 'default'.{Style.RESET_ALL}")
    elif choice == "2":
        current_servers = dns.get("servers", _DEFAULT_SERVERS)
        raw = input(
            f"Enter DNS servers (comma-separated) [{', '.join(current_servers)}]: "
        ).strip()
        if raw:
            servers = [s.strip() for s in raw.split(",") if s.strip()]
        else:
            servers = current_servers
        set_dns_mode(m4b_config_path, "custom", servers)
        print(f"{Fore.GREEN}DNS set to 'custom' with servers: {', '.join(servers)}{Style.RESET_ALL}")
    else:
        print("No changes made.")

    print(
        f"\n{Fore.YELLOW}Run 'generate' to rebuild compose files with the "
        f"new DNS setting.{Style.RESET_ALL}"
    )


# ---------------------------------------------------------------------------
# System info dashboard
# ---------------------------------------------------------------------------


def show_system_info(
    m4b_config: dict,
    app_config: dict,
    user_config: dict,
) -> None:
    """Print a comprehensive system information dashboard."""
    just_fix_windows_console()

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
        name for name, cfg in apps_cfg.items()
        if isinstance(cfg, dict) and cfg.get("enabled", False)
    ]
    total_supported = 0
    for cat_key, cat in app_config.items():
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

    # ---- Compose files ----
    from utils.compose_builder import get_compose_files
    compose_files = get_compose_files(".")
    compose_mode = "layered" if len(compose_files) > 1 else ("monolithic" if compose_files else "none")

    # ---- Print ----
    w = 22  # label column width
    print(f"\n{Fore.CYAN}{'=' * 50}")
    print(f"  M4B System Information")
    print(f"{'=' * 50}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}Version & Updates{Style.RESET_ALL}")
    print(f"  {'Version:':<{w}} {Fore.GREEN}v{version}{Style.RESET_ALL}")
    print(f"  {'Update:':<{w}} {update_str}")

    print(f"\n{Fore.CYAN}System{Style.RESET_ALL}")
    print(f"  {'OS:':<{w}} {os_type}")
    print(f"  {'Architecture:':<{w}} {arch}")
    print(f"  {'Docker arch:':<{w}} {dk_arch}")
    print(f"  {'Default platform:':<{w}} {dk_platform}")
    print(f"  {'Docker installed:':<{w}} {'yes' if docker_ok else Fore.RED + 'no' + Style.RESET_ALL}")
    if total_mem:
        print(f"  {'RAM:':<{w}} {total_mem:.0f} MB")
        print(f"  {'CPU cores:':<{w}} {cores}")

    print(f"\n{Fore.CYAN}Resource Profile{Style.RESET_ALL}")
    print(f"  {'Active profile:':<{w}} {Fore.GREEN}{active_profile}{Style.RESET_ALL}")
    print(f"  {'Description:':<{w}} {profile_def.get('description', '')}")

    print(f"\n{Fore.CYAN}DNS{Style.RESET_ALL}")
    print(f"  {'Mode:':<{w}} {Fore.GREEN}{dns_mode}{Style.RESET_ALL}")
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
    m4b_config = load_json_config(m4b_config_path)
    app_config = load_json_config(app_config_path)
    user_config = load_json_config(user_config_path)

    show_system_info(m4b_config, app_config, user_config)

    print(f"{Fore.YELLOW}Would you like to configure DNS?{Style.RESET_ALL}")
    choice = input("[y/N]: ").strip().lower()
    if choice in ("y", "yes"):
        dns_interactive(m4b_config_path)

    input("Press Enter to return to the menu...")

