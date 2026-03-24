"""CLI logic for the ``m4b dashboard`` subcommand.

Extracted from ``main.py`` so the entry point stays thin and
all dashboard-related orchestration lives in the ``money4band`` package.
"""

from __future__ import annotations

import logging
import os
import signal as sig
import time

from colorama import Fore, Style

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Top-level dispatch — called from main._cmd_dashboard
# ---------------------------------------------------------------------------


def handle_dashboard_action(
    action: str | None,
    config_dir: str,
    base_dir: str,
    *,
    host: str = "127.0.0.1",
    port: int = 8088,
    background: bool = False,
) -> None:
    """Dispatch a ``m4b dashboard <action>`` CLI invocation.

    ``main._cmd_dashboard`` extracts args and delegates here so that
    all dashboard CLI logic lives in the ``dashboard`` package.
    """
    from colorama import just_fix_windows_console

    if action is None:
        print("usage: m4b dashboard <command> [options]\n")
        print("Commands:")
        print("  start           Start the Dashboard + API server")
        print("  stop            Stop a background Dashboard + API process")
        print("  restart         Restart a background Dashboard + API process")
        print("  status          Show Dashboard + API status")
        print("  show-key        Print the Dashboard API key")
        print("  regenerate-key  Generate a new API key")
        print("  enable          Enable Dashboard + API auto-start on M4B launch")
        print("  disable         Disable Dashboard + API auto-start on M4B launch")
        print("\nRun 'm4b dashboard <command> --help' for details.")
        return

    if action in ("enable", "disable"):
        from money4band.dashboard.setup import set_dashboard_state

        enabled = action == "enable"
        set_dashboard_state(config_dir, enabled=enabled)
        just_fix_windows_console()
        state = f"{Fore.GREEN}enabled" if enabled else f"{Fore.YELLOW}disabled"
        print(f"Dashboard + API auto-start {state}.{Style.RESET_ALL}")
        return

    kwargs: dict = {"config_dir": config_dir, "base_dir": base_dir}
    if action == "start":
        kwargs.update(host=host, preferred_port=port, background=background)
    elif action == "stop":
        kwargs["stop"] = True
    elif action == "restart":
        kwargs["restart"] = True
        kwargs.update(host=host, preferred_port=port)
    elif action == "status":
        kwargs["status_check"] = True
    elif action == "show-key":
        kwargs["show_key"] = True
    elif action == "regenerate-key":
        kwargs["regenerate_key"] = True

    run_dashboard_command(**kwargs)


# ---------------------------------------------------------------------------
# Public entry point — called from handle_dashboard_action
# ---------------------------------------------------------------------------


def run_dashboard_command(
    config_dir: str,
    base_dir: str,
    *,
    host: str = "127.0.0.1",
    preferred_port: int = 8088,
    background: bool = False,
    show_key: bool = False,
    stop: bool = False,
    restart: bool = False,
    status_check: bool = False,
    regenerate_key: bool = False,
) -> None:
    """Execute the ``m4b dashboard`` subcommand.

    Handles --stop, --status, --show-key, --regenerate-key flags and
    both foreground / background server startup.
    """
    from money4band.api.server import configure, find_dashboard_port, start_server
    from money4band.dashboard.setup import (
        ensure_api_key_on_disk,
        read_dashboard_pid,
        regenerate_api_key_on_disk,
        remove_dashboard_pid,
        set_dashboard_state,
    )

    configure(config_dir, base_dir=base_dir)

    # --stop: kill a running background dashboard.
    if stop:
        _handle_stop(config_dir, read_dashboard_pid, remove_dashboard_pid)
        return

    # --restart: stop then start in background.
    if restart:
        _handle_stop(config_dir, read_dashboard_pid, remove_dashboard_pid)
        time.sleep(0.5)
        _start_background(config_dir, base_dir, host=host, port=find_dashboard_port(preferred_port))
        return

    # --status: check if a background dashboard is running.
    if status_check:
        _handle_status(config_dir, read_dashboard_pid)
        return

    # --show-key: print the API key and exit.
    if show_key:
        _handle_show_key(config_dir, ensure_api_key_on_disk)
        return

    # --regenerate-key: force a new API key and exit.
    if regenerate_key:
        _handle_regenerate_key(config_dir, regenerate_api_key_on_disk)
        return

    # If a background dashboard is already running, print its info and exit
    # instead of spawning a second instance (which would steal the PID file).
    existing_pid = read_dashboard_pid(config_dir)
    if existing_pid is not None:
        from money4band.dashboard.setup import print_dashboard_status

        print(
            f"{Fore.YELLOW}Dashboard + API is already running "
            f"(PID {existing_pid}).{Style.RESET_ALL}"
        )
        print_dashboard_status(config_dir)
        print(f"  Stop with: {Fore.CYAN}m4b dashboard stop{Style.RESET_ALL}")
        return

    # Resolve an available port.
    port = find_dashboard_port(preferred_port)
    if port != preferred_port:
        print(
            f"{Fore.YELLOW}Port {preferred_port} is in use — "
            f"using port {port} instead.{Style.RESET_ALL}"
        )

    # Determine if the server is exposed beyond localhost.
    exposed = host not in ("127.0.0.1", "::1", "localhost")
    display_host = "localhost" if not exposed else host

    # Ensure key exists and display on startup so user has it.
    api_key = ensure_api_key_on_disk(config_dir)

    # When exposed and no key exists, auto-generate one.
    if exposed and not api_key:
        print(
            f"{Fore.YELLOW}No API key found — generating one automatically."
            f"{Style.RESET_ALL}"
        )
        api_key = regenerate_api_key_on_disk(config_dir)

    if exposed:
        print(
            f"{Fore.YELLOW}WARNING: Dashboard will be reachable from the "
            f"network ({host}).{Style.RESET_ALL}"
        )
        print(
            "  All API requests require the Bearer token.  "
            "Keep your API key secret."
        )

    print(f"{Fore.GREEN}Starting M4B Dashboard + API on {host}:{port}...{Style.RESET_ALL}")
    print(f"  Dashboard: http://{display_host}:{port}/")
    print(f"  API docs:  http://{display_host}:{port}/api/docs")
    print(f"  Status:    http://{display_host}:{port}/api/status")
    if api_key:
        print(f"  API key:   {api_key}")
    else:
        print(
            f"  {Fore.YELLOW}API key: not configured "
            f"(use --regenerate-key){Style.RESET_ALL}"
        )

    # Persist enabled state + resolved port so system info stays accurate.
    set_dashboard_state(config_dir, enabled=True, port=port)

    if background:
        _start_background(
            config_dir,
            base_dir,
            host=host,
            port=port,
        )
        return

    start_server(host=host, port=port)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _handle_stop(config_dir, read_pid_fn, remove_pid_fn) -> None:  # type: ignore[no-untyped-def]
    pid = read_pid_fn(config_dir)
    if pid is None:
        print(f"{Fore.YELLOW}No running Dashboard + API found.{Style.RESET_ALL}")
        return
    try:
        os.kill(pid, sig.SIGTERM)
        print(f"{Fore.GREEN}Dashboard + API (PID {pid}) stopped.{Style.RESET_ALL}")
    except OSError as exc:
        print(f"{Fore.RED}Failed to stop PID {pid}: {exc}{Style.RESET_ALL}")
    remove_pid_fn(config_dir)


def _handle_status(config_dir, read_pid_fn) -> None:  # type: ignore[no-untyped-def]
    from money4band.dashboard.setup import print_dashboard_status

    print_dashboard_status(config_dir)


def _handle_show_key(config_dir, ensure_key_fn) -> None:  # type: ignore[no-untyped-def]
    key = ensure_key_fn(config_dir)
    if key:
        print(f"{Fore.CYAN}Dashboard API key:{Style.RESET_ALL} {key}")
    else:
        print(f"{Fore.YELLOW}No API key configured.{Style.RESET_ALL}")


def _handle_regenerate_key(config_dir, regen_fn) -> None:  # type: ignore[no-untyped-def]
    new_key = regen_fn(config_dir)
    if new_key:
        print(f"{Fore.GREEN}New API key:{Style.RESET_ALL} {new_key}")
    else:
        print(f"{Fore.RED}Failed to regenerate API key.{Style.RESET_ALL}")


def _start_background(
    config_dir: str,
    base_dir: str,
    *,
    host: str,
    port: int,
) -> None:
    """Spawn the dashboard in a detached subprocess."""
    from money4band.dashboard.setup import (
        read_dashboard_pid,
        spawn_dashboard_background,
    )

    existing_pid = read_dashboard_pid(config_dir)
    if existing_pid:
        print(
            f"{Fore.YELLOW}Dashboard + API already running "
            f"(PID {existing_pid}).  Use --stop first.{Style.RESET_ALL}"
        )
        return

    pid = spawn_dashboard_background(config_dir, base_dir, host=host, port=port)

    # Poll the port briefly to confirm uvicorn actually started.
    from money4band.network.networker import is_port_in_use

    print(
        f"{Fore.CYAN}Waiting for dashboard to start...{Style.RESET_ALL}",
        end="",
        flush=True,
    )
    started = False
    for _ in range(15):  # up to ~3 seconds
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
        print(f"  Stop with: {Fore.CYAN}m4b dashboard stop{Style.RESET_ALL}")
    else:
        print(
            f"\n{Fore.YELLOW}Dashboard + API spawned (PID {pid}) but port "
            f"{port} not yet responding — it may still be starting up."
            f"{Style.RESET_ALL}"
        )
        print(f"  Check with: {Fore.CYAN}m4b dashboard status{Style.RESET_ALL}")
        print(f"  Stop with:  {Fore.CYAN}m4b dashboard stop{Style.RESET_ALL}")
