from __future__ import annotations

"""Dashboard setup, API-key management, and PID helpers for M4B."""

import logging
import secrets
from typing import Any

from colorama import Fore, Style

from money4band.ui.prompt import ask_question_yn

logger = logging.getLogger(__name__)

DEFAULT_DASHBOARD_PORT = 8088


def print_dashboard_status(config_dir: str) -> None:
    """Print a one-line dashboard status summary (running/stopped + auto-start)."""
    import os

    from money4band.core.loader import load_json_config

    pid = read_dashboard_pid(config_dir)
    user_cfg_path = os.path.join(config_dir, "user-config.json")
    try:
        cfg = load_json_config(user_cfg_path)
        dash = cfg.get("m4b_dashboard", {})
    except Exception:  # noqa: BLE001
        dash = {}

    port = dash.get("port", DEFAULT_DASHBOARD_PORT)
    autostart = dash.get("enabled", True)
    autostart_tag = (
        f"{Fore.GREEN}on{Style.RESET_ALL}"
        if autostart
        else f"{Fore.YELLOW}off{Style.RESET_ALL}"
    )

    if pid:
        print(
            f"  {Fore.GREEN}* Dashboard + API running{Style.RESET_ALL} "
            f"(PID {pid}) on port {port}  "
            f"[auto-start: {autostart_tag}]"
        )
        print(f"    http://localhost:{port}/  |  http://localhost:{port}/api/docs")
    else:
        print(
            f"  {Fore.YELLOW}o Dashboard + API stopped{Style.RESET_ALL}  "
            f"[auto-start: {autostart_tag}]"
        )


# ---------------------------------------------------------------------------
# API-key management (shared between wizard, dashboard_api, CLI)
# ---------------------------------------------------------------------------


def ensure_api_key_in_config(user_config: dict[str, Any]) -> str:
    """Ensure user_config has an API key.

    Generates a new key if missing or empty.  Operates on the **in-memory**
    dict - the caller is responsible for persisting.

    Returns the (possibly freshly-created) key.
    """
    dash = user_config.setdefault("m4b_dashboard", {})
    key: str = dash.get("api_key", "")
    if not key:
        key = secrets.token_urlsafe(32)
        dash["api_key"] = key
        logger.info("Generated new dashboard API key")
    return key


def ensure_api_key_on_disk(config_dir: str) -> str:
    """Generate and persist an API key if one doesn't exist yet.

    Loads the user-config from *config_dir*, ensures a key exists, and
    writes back if changed.

    Returns the active key, or ``""`` on failure.
    """
    import os

    user_cfg_path = os.path.join(config_dir, "user-config.json")
    try:
        from money4band.core.dumper import write_json
        from money4band.core.loader import load_json_config

        cfg = load_json_config(user_cfg_path)
        old_key = cfg.get("m4b_dashboard", {}).get("api_key", "")
        key = ensure_api_key_in_config(cfg)
        if key != old_key:
            write_json(cfg, user_cfg_path)
        return key
    except Exception:  # noqa: BLE001
        logger.debug("Could not generate API key", exc_info=True)
        return ""


def regenerate_api_key_on_disk(config_dir: str) -> str:
    """Force-generate a new API key, replacing any existing one.

    Returns the new key, or ``""`` on failure.
    """
    import os

    user_cfg_path = os.path.join(config_dir, "user-config.json")
    try:
        from money4band.core.dumper import write_json
        from money4band.core.loader import load_json_config

        cfg = load_json_config(user_cfg_path)
        dash = cfg.setdefault("m4b_dashboard", {})
        new_key = secrets.token_urlsafe(32)
        dash["api_key"] = new_key
        write_json(cfg, user_cfg_path)
        logger.info("Regenerated dashboard API key")
        return new_key
    except Exception:  # noqa: BLE001
        logger.debug("Could not regenerate API key", exc_info=True)
        return ""


def setup_m4b_dashboard(user_config: dict[str, Any]) -> None:
    """
    Set up the M4B dashboard configuration.

    The web dashboard is now served directly by the FastAPI dashboard
    server (``m4b dashboard``), so there is no separate container - only
    an enabled/disabled toggle and an optional preferred port.

    Args:
        user_config (dict): The user configuration dictionary.
    """
    dashboard_config = user_config["m4b_dashboard"]
    current_enabled = dashboard_config.get("enabled", True)

    if current_enabled:
        print("The M4B web dashboard is currently enabled.")
        if not ask_question_yn("Do you want to change the dashboard settings?"):
            print("Keeping existing dashboard settings.")
            logger.info("User chose to keep existing dashboard settings.")
            return

    if ask_question_yn(
        "Do you want to enable the M4B web dashboard? "
        "(A simple local web page to access apps dashboards)",
        default=True,
    ):
        logger.info("User decided to enable the M4B web dashboard.")
        dashboard_config["enabled"] = True

        # Preferred port - validated at startup via find_dashboard_port().
        port = _ask_port(dashboard_config.get("port", DEFAULT_DASHBOARD_PORT))
        dashboard_config["port"] = port

        print(
            f"{Fore.GREEN}M4B dashboard will be available via "
            f"'m4b dashboard' (port {port}).{Style.RESET_ALL}"
        )

        # Ensure an API key exists for remote access.
        ensure_api_key_in_config(user_config)
    else:
        dashboard_config["enabled"] = False
        print("M4B dashboard disabled.")
        logger.info("User chose not to enable the M4B dashboard.")


def _ask_port(current: int) -> int:
    """Prompt the user for a dashboard port, defaulting to *current*."""
    from money4band.ui.prompt import ask_question_num

    return ask_question_num(
        f"Dashboard port (default {current}): ",
        default=current,
        min_val=1024,
        max_val=65535,
    )


# ---------------------------------------------------------------------------
# PID-file helpers (shared between CLI and interactive menu)
# ---------------------------------------------------------------------------


def dashboard_pid_file(config_dir: str) -> str:
    """Return the path to the dashboard PID file."""
    import os

    return os.path.join(config_dir, ".dashboard.pid")


def dashboard_owner_file(config_dir: str) -> str:
    """Return the path to the dashboard owner sidecar file.

    The owner file records who spawned the running dashboard so the
    lifecycle hooks know whether to kill it on m4b exit:

    * ``auto``   -- spawned by ``auto_start_dashboard`` for an interactive
      m4b session; bound to this process's lifetime.
    * ``manual`` -- spawned by an explicit ``m4b dashboard start -b``;
      persistent service that outlives this m4b run.
    """
    import os

    return os.path.join(config_dir, ".dashboard.owner")


def write_dashboard_owner(config_dir: str, owner: str) -> None:
    """Persist the dashboard owner tag (``auto`` or ``manual``)."""
    try:
        with open(dashboard_owner_file(config_dir), "w") as f:
            f.write(owner)
    except OSError:
        logger.debug("Could not write dashboard owner file", exc_info=True)


def read_dashboard_owner(config_dir: str) -> str | None:
    """Return the dashboard owner tag, or ``None`` if not recorded."""
    import os

    path = dashboard_owner_file(config_dir)
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            value = f.read().strip()
    except OSError:
        return None
    return value or None


def remove_dashboard_owner(config_dir: str) -> None:
    """Remove the dashboard owner sidecar file."""
    import os

    try:
        os.remove(dashboard_owner_file(config_dir))
    except OSError:
        pass


def _is_pid_alive(pid: int) -> bool:
    """Return True if a process with *pid* exists (cross-platform)."""
    import sys

    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(
            0x1000, False, pid
        )  # PROCESS_QUERY_LIMITED_INFORMATION
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False

    # POSIX: signal 0 checks existence without sending a real signal.
    import os

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def read_dashboard_pid(config_dir: str) -> int | None:
    """Read the stored PID, return it if the process is still alive."""
    import os

    pid_path = dashboard_pid_file(config_dir)
    if not os.path.isfile(pid_path):
        return None
    try:
        with open(pid_path) as f:
            pid = int(f.read().strip())
    except (ValueError, OSError):
        return None
    if _is_pid_alive(pid):
        return pid
    # Stale PID file - process is gone, clean up.
    try:
        os.remove(pid_path)
    except OSError:
        pass
    return None


def write_dashboard_pid(config_dir: str, pid: int) -> None:
    """Persist the dashboard PID so stop can find it later.

    Uses a cross-platform file lock to prevent two processes from
    writing the PID file simultaneously (e.g. cron + user start).
    """
    import sys

    pid_path = dashboard_pid_file(config_dir)

    if sys.platform == "win32":
        # Windows: use msvcrt file locking.
        import msvcrt

        f = open(pid_path, "w")  # noqa: SIM115
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            f.close()
            logger.warning("Dashboard PID file is locked by another process.")
            return
        try:
            f.write(str(pid))
            f.flush()
        finally:
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            f.close()
    else:
        # POSIX: use fcntl advisory locking.
        import fcntl

        f = open(pid_path, "w")  # noqa: SIM115
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.close()
            logger.warning("Dashboard PID file is locked by another process.")
            return
        try:
            f.write(str(pid))
            f.flush()
        finally:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            f.close()


def remove_dashboard_pid(config_dir: str) -> None:
    """Remove the PID file."""
    import os

    try:
        os.remove(dashboard_pid_file(config_dir))
    except OSError:
        pass
    remove_dashboard_owner(config_dir)


def spawn_dashboard_background(
    config_dir: str,
    base_dir: str,
    *,
    host: str = "127.0.0.1",
    port: int,
    owner: str = "manual",
) -> int:
    """Spawn the dashboard in a detached background process (cross-platform).

    Returns the PID of the spawned process.  Handles Windows
    ``DETACHED_PROCESS`` and POSIX ``start_new_session`` transparently
    so callers don't need platform-specific code.

    *owner* is recorded in a sidecar file so the lifecycle hooks know
    whether to terminate the dashboard on m4b exit (``auto``) or leave
    it running as a persistent service (``manual``).
    """
    import os
    import subprocess
    import sys

    if getattr(sys, "frozen", False):
        # Frozen build: sys.executable IS the m4b binary and does not
        # interpret `-c` as Python code - relaunch it with the internal
        # `dashboard serve` subcommand instead.
        cmd = [
            sys.executable,
            "--config-dir",
            config_dir,
            "dashboard",
            "serve",
            "--host",
            host,
            "--port",
            str(port),
        ]
    else:
        cmd = [
            sys.executable,
            "-c",
            (
                "from money4band.api.server import configure, start_server; "
                f"configure({config_dir!r}, base_dir={base_dir!r}); "
                f"start_server(host={host!r}, port={port})"
            ),
        ]
    # Strip the parent's PyInstaller env so the frozen child extracts its
    # own bundle instead of reusing the parent's _MEI dir, which the parent
    # deletes on exit.
    env = os.environ.copy()
    for pyi_var in (
        "_MEIPASS2",
        "_PYI_APPLICATION_HOME_DIR",
        "_PYI_PARENT_PROCESS_LEVEL",
    ):
        env.pop(pyi_var, None)

    popen_kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "env": env,
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
    write_dashboard_owner(config_dir, owner)
    return proc.pid


def set_dashboard_state(
    config_dir: str, *, enabled: bool, port: int | None = None
) -> None:
    """Persist the dashboard ``enabled`` flag (and optionally *port*) to disk.

    Called automatically when the dashboard starts or stops so that
    ``m4b_dashboard.enabled`` always reflects reality.
    """
    import os

    user_cfg_path = os.path.join(config_dir, "user-config.json")
    try:
        from money4band.core.dumper import write_json
        from money4band.core.loader import load_json_config

        cfg = load_json_config(user_cfg_path)
        dash = cfg.setdefault("m4b_dashboard", {})
        dash["enabled"] = enabled
        if port is not None:
            dash["port"] = port
        write_json(cfg, user_cfg_path)
        logger.debug("Dashboard state persisted: enabled=%s, port=%s", enabled, port)
    except Exception:  # noqa: BLE001
        logger.debug("Could not persist dashboard state", exc_info=True)


def auto_start_dashboard(config_dir: str, base_dir: str) -> None:
    """Start the dashboard in background if ``m4b_dashboard.enabled`` is True.

    Called from ``main()`` on every M4B launch so the dashboard is always
    available when the user expects it.  Skipped silently when the
    dashboard is already running or disabled in config.
    """
    import os
    import time

    from money4band.core.loader import load_json_config

    user_cfg_path = os.path.join(config_dir, "user-config.json")
    try:
        user_config = load_json_config(user_cfg_path)
    except Exception:  # noqa: BLE001
        return

    dash_cfg = user_config.get("m4b_dashboard", {})
    if not dash_cfg.get("enabled", True):
        return

    if read_dashboard_pid(config_dir) is not None:
        logger.debug("Dashboard already running - skipping auto-start.")
        return

    preferred_port = dash_cfg.get("port", DEFAULT_DASHBOARD_PORT)
    try:
        from money4band.api.server import configure, find_dashboard_port

        configure(config_dir, base_dir=base_dir)
        port = find_dashboard_port(preferred_port)
    except Exception:  # noqa: BLE001
        logger.debug("Could not resolve dashboard port", exc_info=True)
        return

    api_key = ensure_api_key_on_disk(config_dir)

    pid = spawn_dashboard_background(config_dir, base_dir, port=port, owner="auto")
    _register_auto_dashboard_cleanup(config_dir, pid)

    from money4band.network.networker import is_port_in_use

    started = False
    for _ in range(15):
        time.sleep(0.2)
        if is_port_in_use(port):
            started = True
            break

    if started:
        print(
            f"{Fore.GREEN}Dashboard + API auto-started on port {port}.{Style.RESET_ALL}"
        )
        print(f"  Dashboard: http://localhost:{port}/")
        print(
            f"  {Fore.CYAN}Will stop automatically when m4b exits.{Style.RESET_ALL}"
            f"  Run {Fore.CYAN}m4b dashboard start -b{Style.RESET_ALL} "
            f"for a persistent service."
        )
        if api_key:
            print(f"  API key:   {api_key}")
    else:
        print(
            f"{Fore.YELLOW}Dashboard + API spawned (PID {pid}) - "
            f"may still be starting.{Style.RESET_ALL}"
        )
    logger.info("Dashboard + API auto-started (PID %d, port %d).", pid, port)


# ---------------------------------------------------------------------------
# Lifecycle binding for auto-started dashboards
# ---------------------------------------------------------------------------


_CLEANUP_REGISTERED = False


def _register_auto_dashboard_cleanup(config_dir: str, pid: int) -> None:
    """Bind an auto-started dashboard's lifetime to this m4b process.

    Registers an :mod:`atexit` hook plus SIGINT/SIGTERM handlers that
    terminate the spawned dashboard PID and clean up the PID + owner
    files when m4b exits. Only ``owner=auto`` dashboards are affected;
    dashboards spawned via explicit ``m4b dashboard start -b`` are
    tagged ``owner=manual`` and survive.
    """
    global _CLEANUP_REGISTERED
    if _CLEANUP_REGISTERED:
        return
    _CLEANUP_REGISTERED = True

    import atexit
    import signal as _signal

    def _shutdown(*_args: object) -> None:
        # Re-read the owner; user may have promoted it via "dashboard stop"
        # then "dashboard start -b" within the same session.
        owner = read_dashboard_owner(config_dir)
        if owner != "auto":
            return
        current_pid = read_dashboard_pid(config_dir)
        if current_pid is None or current_pid != pid:
            return
        try:
            import os

            os.kill(pid, _signal.SIGTERM)
        except OSError:
            pass
        remove_dashboard_pid(config_dir)

    atexit.register(_shutdown)

    def _signal_handler(signum: int, _frame: object) -> None:
        _shutdown()
        # Restore default and re-raise so the process actually exits with
        # the conventional 128+signum status.
        try:
            _signal.signal(signum, _signal.SIG_DFL)
            import os

            os.kill(os.getpid(), signum)
        except OSError:
            raise SystemExit(128 + signum) from None

    for _sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(_signal, _sig_name, None)
        if sig is None:
            continue
        try:
            _signal.signal(sig, _signal_handler)
        except (ValueError, OSError):
            # Not in main thread or signal not supported on platform.
            pass
