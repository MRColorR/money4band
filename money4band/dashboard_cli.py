"""CLI logic for the ``m4b dashboard`` subcommand.

Extracted from ``main.py`` so the entry point stays thin and
all dashboard-related orchestration lives in the ``money4band`` package.
"""

from __future__ import annotations

import logging
import os
import signal as sig
import subprocess
import sys
import time

from colorama import Fore, Style

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point — called from main._cmd_dashboard
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
    status_check: bool = False,
    regenerate_key: bool = False,
) -> None:
    """Execute the ``m4b dashboard`` subcommand.

    Handles --stop, --status, --show-key, --regenerate-key flags and
    both foreground / background server startup.
    """
    from money4band.dashboard_api import configure, find_dashboard_port, start_server
    from money4band.dashboard_setup import (
        ensure_api_key_on_disk,
        read_dashboard_pid,
        regenerate_api_key_on_disk,
        remove_dashboard_pid,
        write_dashboard_pid,
    )

    configure(config_dir, base_dir=base_dir)

    # --stop: kill a running background dashboard.
    if stop:
        _handle_stop(config_dir, read_dashboard_pid, remove_dashboard_pid)
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

    print(f"{Fore.GREEN}Starting M4B Dashboard on {host}:{port}...{Style.RESET_ALL}")
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

    if background:
        _start_background(
            config_dir,
            base_dir,
            host=host,
            port=port,
            read_dashboard_pid=read_dashboard_pid,
            write_dashboard_pid=write_dashboard_pid,
        )
        return

    start_server(host=host, port=port)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _handle_stop(config_dir, read_pid_fn, remove_pid_fn) -> None:  # type: ignore[no-untyped-def]
    pid = read_pid_fn(config_dir)
    if pid is None:
        print(f"{Fore.YELLOW}No running dashboard found.{Style.RESET_ALL}")
        return
    try:
        os.kill(pid, sig.SIGTERM)
        print(f"{Fore.GREEN}Dashboard (PID {pid}) stopped.{Style.RESET_ALL}")
    except OSError as exc:
        print(f"{Fore.RED}Failed to stop PID {pid}: {exc}{Style.RESET_ALL}")
    remove_pid_fn(config_dir)


def _handle_status(config_dir, read_pid_fn) -> None:  # type: ignore[no-untyped-def]
    pid = read_pid_fn(config_dir)
    if pid:
        print(f"{Fore.GREEN}Dashboard is running (PID {pid}).{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}Dashboard is not running.{Style.RESET_ALL}")


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
    read_dashboard_pid,  # type: ignore[no-untyped-def]
    write_dashboard_pid,  # type: ignore[no-untyped-def]
) -> None:
    """Spawn the dashboard in a detached subprocess."""
    existing_pid = read_dashboard_pid(config_dir)
    if existing_pid:
        print(
            f"{Fore.YELLOW}Dashboard already running "
            f"(PID {existing_pid}).  Use --stop first.{Style.RESET_ALL}"
        )
        return

    cmd = [
        sys.executable,
        "-c",
        (
            "from money4band.dashboard_api import configure, start_server; "
            f"configure({config_dir!r}, base_dir={base_dir!r}); "
            f"start_server(host={host!r}, port={port})"
        ),
    ]
    popen_kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
            | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        )
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **popen_kwargs)  # noqa: S603
    write_dashboard_pid(config_dir, proc.pid)

    # Poll the port briefly to confirm uvicorn actually started.
    from money4band.networker import is_port_in_use

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
            f"\n{Fore.GREEN}Dashboard running in background "
            f"(PID {proc.pid}).{Style.RESET_ALL}"
        )
        print(f"  Stop with: {Fore.CYAN}m4b dashboard --stop{Style.RESET_ALL}")
    else:
        print(
            f"\n{Fore.YELLOW}Dashboard spawned (PID {proc.pid}) but port "
            f"{port} not yet responding — it may still be starting up."
            f"{Style.RESET_ALL}"
        )
        print(f"  Check with: {Fore.CYAN}m4b dashboard --status{Style.RESET_ALL}")
        print(f"  Stop with:  {Fore.CYAN}m4b dashboard --stop{Style.RESET_ALL}")
