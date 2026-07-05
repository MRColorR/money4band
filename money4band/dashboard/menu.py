"""Interactive menu handler for Dashboard Management."""

from __future__ import annotations

import logging
import os
import signal as sig
import time

from colorama import Fore, Style

from money4band.core.loader import load_json_config
from money4band.ui.cls import cls

logger = logging.getLogger(__name__)

_script_dir = os.path.dirname(os.path.abspath(__file__))
_BASE_DIR = os.path.dirname(os.path.dirname(_script_dir))
_DEFAULT_PORT = 8088


def _config_dir_from_user_cfg(user_config_path: str) -> str:
    return os.path.dirname(user_config_path)


def _get_port(user_config_path: str) -> int:
    try:
        cfg = load_json_config(user_config_path)
        return int(cfg.get("m4b_dashboard", {}).get("port", _DEFAULT_PORT))
    except Exception:  # noqa: BLE001
        return _DEFAULT_PORT


# ------------------------------------------------------------------
# Sub-menu actions
# ------------------------------------------------------------------


def _action_start_foreground(config_dir: str, port: int) -> None:
    from money4band.api.server import configure, find_dashboard_port, start_server
    from money4band.dashboard.setup import (
        ensure_api_key_on_disk,
        read_dashboard_pid,
        set_dashboard_state,
    )

    existing = read_dashboard_pid(config_dir)
    if existing:
        from money4band.dashboard.setup import print_dashboard_status

        print(
            f"{Fore.YELLOW}Dashboard + API is already running "
            f"(PID {existing}).{Style.RESET_ALL}"
        )
        print_dashboard_status(config_dir)
        return

    configure(config_dir, base_dir=_BASE_DIR)
    port = find_dashboard_port(port)
    api_key = ensure_api_key_on_disk(config_dir)
    set_dashboard_state(config_dir, enabled=True, port=port)

    print(
        f"{Fore.GREEN}Starting M4B Dashboard + API on 127.0.0.1:{port}...{Style.RESET_ALL}"
    )
    print(f"  Dashboard: http://localhost:{port}/")
    print(f"  API docs:  http://localhost:{port}/api/docs")
    if api_key:
        print(f"  API key:   {api_key}")
    print(f"{Fore.YELLOW}Press Ctrl+C to stop.{Style.RESET_ALL}")
    start_server(host="127.0.0.1", port=port)


def _action_start_background(config_dir: str, port: int) -> None:
    from money4band.api.server import configure, find_dashboard_port
    from money4band.dashboard.setup import (
        ensure_api_key_on_disk,
        read_dashboard_pid,
        set_dashboard_state,
    )

    configure(config_dir, base_dir=_BASE_DIR)

    existing = read_dashboard_pid(config_dir)
    if existing:
        print(
            f"{Fore.YELLOW}Dashboard + API already running (PID {existing}).  "
            f"Stop it first.{Style.RESET_ALL}"
        )
        return

    port = find_dashboard_port(port)
    api_key = ensure_api_key_on_disk(config_dir)
    set_dashboard_state(config_dir, enabled=True, port=port)

    from money4band.dashboard.setup import spawn_dashboard_background

    pid = spawn_dashboard_background(config_dir, _BASE_DIR, port=port)

    from money4band.network.networker import is_port_in_use

    print(
        f"{Fore.CYAN}Waiting for dashboard to start...{Style.RESET_ALL}",
        end="",
        flush=True,
    )
    started = False
    for _ in range(15):
        time.sleep(0.2)
        if is_port_in_use(port):
            started = True
            break
        print(".", end="", flush=True)

    if started:
        print(
            f"\n{Fore.GREEN}Dashboard + API running in background "
            f"(PID {pid}).{Style.RESET_ALL}"
        )
        print(f"  Dashboard: http://localhost:{port}/")
        print(f"  API docs:  http://localhost:{port}/api/docs")
        if api_key:
            print(f"  API key:   {api_key}")
    else:
        print(
            f"\n{Fore.YELLOW}Dashboard + API spawned (PID {pid}) but port "
            f"{port} not yet responding.{Style.RESET_ALL}"
        )


def _action_stop(config_dir: str) -> None:
    from money4band.dashboard.setup import (
        read_dashboard_pid,
        remove_dashboard_pid,
    )

    pid = read_dashboard_pid(config_dir)
    if pid is None:
        print(f"{Fore.YELLOW}No running Dashboard + API found.{Style.RESET_ALL}")
        return
    try:
        os.kill(pid, sig.SIGTERM)
        print(f"{Fore.GREEN}Dashboard + API (PID {pid}) stopped.{Style.RESET_ALL}")
    except OSError as exc:
        print(f"{Fore.RED}Failed to stop PID {pid}: {exc}{Style.RESET_ALL}")
    remove_dashboard_pid(config_dir)


def _action_restart(config_dir: str, port: int) -> None:
    _action_stop(config_dir)
    time.sleep(0.5)
    _action_start_background(config_dir, port)


def _action_start_background_web(config_dir: str, port: int) -> None:
    from money4band.api.server import configure, find_dashboard_port
    from money4band.dashboard.setup import (
        ensure_api_key_on_disk,
        read_dashboard_pid,
        regenerate_api_key_on_disk,
        set_dashboard_state,
    )

    configure(config_dir, base_dir=_BASE_DIR)

    existing = read_dashboard_pid(config_dir)
    if existing:
        print(
            f"{Fore.YELLOW}Dashboard + API already running (PID {existing}).  "
            f"Stop it first.{Style.RESET_ALL}"
        )
        return

    port = find_dashboard_port(port)
    api_key = ensure_api_key_on_disk(config_dir)
    if not api_key:
        print(
            f"{Fore.YELLOW}No API key found - generating one automatically."
            f"{Style.RESET_ALL}"
        )
        api_key = regenerate_api_key_on_disk(config_dir)
    set_dashboard_state(config_dir, enabled=True, port=port)

    # Intentional LAN exposure; every request requires the Bearer API key.
    host = "0.0.0.0"  # noqa: S104 # nosec B104
    print(
        f"{Fore.YELLOW}WARNING: Dashboard will be reachable from the "
        f"network ({host}).{Style.RESET_ALL}"
    )
    print("  All API requests require the Bearer token.  Keep your API key secret.")

    from money4band.dashboard.setup import spawn_dashboard_background

    pid = spawn_dashboard_background(config_dir, _BASE_DIR, host=host, port=port)

    from money4band.network.networker import is_port_in_use

    print(
        f"{Fore.CYAN}Waiting for dashboard to start...{Style.RESET_ALL}",
        end="",
        flush=True,
    )
    started = False
    for _ in range(15):
        time.sleep(0.2)
        if is_port_in_use(port):
            started = True
            break
        print(".", end="", flush=True)

    if started:
        print(
            f"\n{Fore.GREEN}Dashboard + API running in background "
            f"(PID {pid}), web-exposed.{Style.RESET_ALL}"
        )
        print(f"  Dashboard: http://0.0.0.0:{port}/")
        print(f"  API docs:  http://0.0.0.0:{port}/api/docs")
        if api_key:
            print(f"  API key:   {api_key}")
    else:
        print(
            f"\n{Fore.YELLOW}Dashboard + API spawned (PID {pid}) but port "
            f"{port} not yet responding.{Style.RESET_ALL}"
        )


def _action_status(config_dir: str) -> None:
    from money4band.dashboard.setup import print_dashboard_status

    print_dashboard_status(config_dir)


def _action_show_key(config_dir: str) -> None:
    from money4band.dashboard.setup import ensure_api_key_on_disk

    key = ensure_api_key_on_disk(config_dir)
    if key:
        print(f"{Fore.CYAN}Dashboard API key:{Style.RESET_ALL} {key}")
    else:
        print(f"{Fore.YELLOW}No API key configured.{Style.RESET_ALL}")


def _action_regenerate_key(config_dir: str) -> None:
    from money4band.dashboard.setup import regenerate_api_key_on_disk

    new_key = regenerate_api_key_on_disk(config_dir)
    if new_key:
        print(f"{Fore.GREEN}New API key:{Style.RESET_ALL} {new_key}")
        print(
            f"{Fore.YELLOW}Note: if the Dashboard + API is running, "
            f"restart it to pick up the new key.{Style.RESET_ALL}"
        )
    else:
        print(f"{Fore.RED}Failed to regenerate API key.{Style.RESET_ALL}")


def _action_toggle_autostart(config_dir: str) -> None:
    from money4band.dashboard.setup import set_dashboard_state

    user_cfg_path = os.path.join(config_dir, "user-config.json")
    try:
        cfg = load_json_config(user_cfg_path)
        currently_enabled = cfg.get("m4b_dashboard", {}).get("enabled", True)
    except Exception:  # noqa: BLE001
        currently_enabled = True

    new_state = not currently_enabled
    set_dashboard_state(config_dir, enabled=new_state)
    label = f"{Fore.GREEN}enabled" if new_state else f"{Fore.YELLOW}disabled"
    print(f"Dashboard + API auto-start {label}.{Style.RESET_ALL}")


# ------------------------------------------------------------------
# Interactive sub-menu
# ------------------------------------------------------------------

_MENU_ITEMS = [
    ("Start Dashboard + API (foreground)", "foreground"),
    ("Start Dashboard + API (background)", "background"),
    ("Start Dashboard + API (web-exposed)", "background_web"),
    ("Stop Dashboard + API", "stop"),
    ("Restart Dashboard + API", "restart"),
    ("Toggle auto-start on M4B launch", "toggle_autostart"),
    ("Dashboard + API status", "status"),
    ("Show API key", "show_key"),
    ("Regenerate API key", "regen_key"),
]


def _dashboard_menu(config_dir: str, port: int) -> None:
    while True:
        cls()
        print(
            f"{Fore.GREEN}----------------------------------------------{Style.RESET_ALL}"
        )
        print(f"{Fore.CYAN}Dashboard + API Management{Style.RESET_ALL}")
        print(
            f"{Fore.GREEN}----------------------------------------------{Style.RESET_ALL}"
        )
        from money4band.dashboard.setup import print_dashboard_status

        print_dashboard_status(config_dir)
        print(
            f"{Fore.GREEN}----------------------------------------------{Style.RESET_ALL}"
        )
        for i, (label, _) in enumerate(_MENU_ITEMS, 1):
            print(f"  {i}. {label}")
        print(f"\n  {Fore.CYAN}b{Style.RESET_ALL} Back")

        choice = input("\nSelect: ").strip().lower()

        if choice == "b":
            return

        try:
            idx = int(choice) - 1
        except ValueError:
            print(f"{Fore.YELLOW}Invalid selection.{Style.RESET_ALL}")
            time.sleep(1)
            continue

        if idx < 0 or idx >= len(_MENU_ITEMS):
            print(f"{Fore.YELLOW}Invalid selection.{Style.RESET_ALL}")
            time.sleep(1)
            continue

        action = _MENU_ITEMS[idx][1]

        if action == "foreground":
            _action_start_foreground(config_dir, port)
            input("\nPress Enter to go back...")
        elif action == "background":
            _action_start_background(config_dir, port)
            input("\nPress Enter to go back...")
        elif action == "background_web":
            _action_start_background_web(config_dir, port)
            input("\nPress Enter to go back...")
        elif action == "stop":
            _action_stop(config_dir)
            input("\nPress Enter to go back...")
        elif action == "restart":
            _action_restart(config_dir, port)
            input("\nPress Enter to go back...")
        elif action == "toggle_autostart":
            _action_toggle_autostart(config_dir)
            input("\nPress Enter to go back...")
        elif action == "status":
            _action_status(config_dir)
            input("\nPress Enter to go back...")
        elif action == "show_key":
            _action_show_key(config_dir)
            input("\nPress Enter to go back...")
        elif action == "regen_key":
            _action_regenerate_key(config_dir)
            input("\nPress Enter to go back...")


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """Entry point called by the interactive menu dispatcher."""
    config_dir = _config_dir_from_user_cfg(user_config_path)
    port = _get_port(user_config_path)
    _dashboard_menu(config_dir, port)
