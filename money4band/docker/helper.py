from __future__ import annotations

import getpass
import logging
import os
import platform
import subprocess
import sys
import threading
import time
from itertools import cycle
from typing import Any

from colorama import Fore, Style

logger = logging.getLogger(__name__)


def read_env_var(env_file: str, key: str) -> str | None:
    """Read *key* from an env file, falling back to ``.env.meta``.

    The ``.env.meta`` sidecar (non-sensitive metadata) persists after the
    full ``.env`` has been securely deleted post compose-up, so every
    consumer of COMPOSE_PROJECT_NAME / DEVICE_NAME must use this reader
    rather than parsing ``.env`` directly.

    Args:
        env_file: Path to the .env file (or a compose file path, which is
                  automatically converted to the sibling .env path).
        key: The env var name to look up (exact match).

    Returns:
        The value, or None if not found in either file.
    """
    # Handle if compose file was passed instead of .env
    env_file = (
        os.path.join(os.path.dirname(env_file), ".env")
        if not env_file.endswith(".env")
        else env_file
    )

    # Try .env first, then fall back to .env.meta (persists after secure delete).
    meta_file = os.path.join(os.path.dirname(os.path.abspath(env_file)), ".env.meta")
    prefix = f"{key}="

    for candidate in (env_file, meta_file):
        try:
            if os.path.isfile(candidate):
                with open(candidate) as f:
                    for line in f:
                        if line.startswith(prefix):
                            from money4band.docker.env_builder import (
                                decode_env_value,
                            )

                            value = decode_env_value(line.strip().split("=", 1)[1])
                            logger.info("Found %s in %s: %s", key, candidate, value)
                            return value
        except Exception as e:
            logger.error("Error reading %s from %s: %s", key, candidate, e)

    return None


def get_compose_project_name(env_file: str) -> str | None:
    """Extract COMPOSE_PROJECT_NAME from an env file (with .env.meta fallback)."""
    return read_env_var(env_file, "COMPOSE_PROJECT_NAME")


def is_user_root() -> bool:
    """
    Check if the current user is the root user on Linux.
    On macOS and Windows, it always returns False since we don't manage Docker groups.
    """
    return os.geteuid() == 0 if platform.system().lower() == "linux" else False


def is_user_in_docker_group() -> bool:
    """
    Check if the current user is in the Docker group on Linux.
    This function is skipped on Windows and macOS.
    """
    if platform.system().lower() != "linux":
        return True
    # use getpass.getuser() instead of os.getlogin() as it is more robust
    user = getpass.getuser()
    logger.info(f"Detected user: {user}")
    logger.info(f"Checking if user '{user}' is in the Docker group...")
    groups = subprocess.run(
        ["groups", user], check=False, capture_output=True, text=True
    )
    return "docker" in groups.stdout


def create_docker_group_if_needed() -> None:
    """
    Create the Docker group if it doesn't exist and add the current user to it on Linux.
    This function is skipped on Windows and macOS.
    """
    if platform.system().lower() != "linux":
        return

    try:
        if (
            subprocess.run(
                ["getent", "group", "docker"], check=False, capture_output=True
            ).returncode
            != 0
        ):
            logger.info(
                f"{Fore.YELLOW}Docker group does not exist. Creating it...{Style.RESET_ALL}"
            )
            subprocess.run(["sudo", "groupadd", "docker"], check=True)
            logger.info(
                f"{Fore.GREEN}Docker group created successfully.{Style.RESET_ALL}"
            )

        # use getpass.getuser() instead of os.getlogin() as it is more robust
        user = getpass.getuser()
        logger.info(f"Adding user '{user}' to Docker group...")
        subprocess.run(["sudo", "usermod", "-aG", "docker", user], check=True)
        logger.info(
            f"{Fore.GREEN}User '{user}' added to Docker group. Please log out and log back in.{Style.RESET_ALL}"
        )
    except subprocess.CalledProcessError as e:
        logger.error(
            f"{Fore.RED}Failed to add user to Docker group: {e}{Style.RESET_ALL}"
        )
        raise RuntimeError("Failed to add user to Docker group.") from e


def is_docker_daemon_running() -> bool:
    """Check whether the Docker daemon is reachable."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def is_multiarch_emulation_available() -> bool:
    """Check whether Docker multiarch emulation (QEMU/binfmt) is available.

    Uses three detection strategies in order so it works on every OS:

    1. **buildx inspect** (all platforms) - when buildx reports >=2 distinct
       CPU architectures the underlying binfmt_misc/QEMU handlers must be
       registered.  Works on Docker Desktop (Windows/macOS) and Linux.
    2. **binfmt_misc procfs** (Linux only) - directly scans
       ``/proc/sys/fs/binfmt_misc/`` for ``qemu-*`` entries.  Useful on
       Linux hosts where buildx is not installed.
    3. **docker info** (all platforms) - Docker Desktop always injects a
       ``binfmt_misc`` line into ``docker info`` when QEMU is available.
       Serves as a last-resort check on Windows/macOS if buildx is absent.
    """
    # --- 1. Primary: ask buildx which platforms the builder supports ---
    try:
        result = subprocess.run(
            ["docker", "buildx", "inspect", "--bootstrap"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            known_archs = {
                "amd64",
                "arm64",
                "arm/v7",
                "386",
                "ppc64le",
                "s390x",
                "riscv64",
            }
            for line in result.stdout.splitlines():
                if "platforms:" in line.lower():
                    lower = line.lower()
                    found = {a for a in known_archs if a in lower}
                    if len(found) >= 2:
                        return True
    except Exception:
        pass

    # --- 2. Fallback (Linux): check binfmt_misc directly ---
    binfmt_dir = "/proc/sys/fs/binfmt_misc"
    if os.path.isdir(binfmt_dir):
        try:
            entries = os.listdir(binfmt_dir)
            qemu_entries = [e for e in entries if e.startswith("qemu-")]
            if qemu_entries:
                return True
        except OSError:
            pass

    # --- 3. Last resort (all platforms): parse docker info ---
    try:
        result = subprocess.run(
            ["docker", "info"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            text = result.stdout.lower()
            # Docker Desktop reports QEMU/binfmt support in the info output
            if "binfmt_misc" in text or "qemu" in text:
                return True
    except Exception:
        pass

    return False


def check_docker_ready() -> None:
    """Pre-flight check: ensure Docker is usable before any Docker operation.

    On Linux, verifies the daemon is running, the user is root or in the
    docker group, and offers to fix group membership automatically.
    On other platforms, only checks that the daemon responds.

    Raises RuntimeError with an actionable message when Docker is not ready.
    """
    if platform.system().lower() == "linux":
        # Check daemon first
        if not is_docker_daemon_running():
            msg = (
                "Docker daemon is not running. "
                "Start it with: sudo systemctl start docker"
            )
            logger.error(msg)
            print(f"{Fore.RED}{msg}{Style.RESET_ALL}")
            raise RuntimeError(msg)
        # Check permissions
        if not is_user_root() and not is_user_in_docker_group():
            user = getpass.getuser()
            msg = (
                f"User '{user}' is not in the docker group and is not root.\n"
                "Docker commands will fail with 'permission denied'."
            )
            logger.warning(msg)
            print(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")
            print(
                f"{Fore.GREEN}Attempting to fix: adding '{user}' to docker group...{Style.RESET_ALL}"
            )
            create_docker_group_if_needed()
    elif not is_docker_daemon_running():
        msg = (
            "Docker daemon is not running or Docker is not installed. "
            "Please start Docker Desktop or install Docker first."
        )
        logger.error(msg)
        print(f"{Fore.RED}{msg}{Style.RESET_ALL}")
        raise RuntimeError(msg)


def run_docker_command(command: list[str], use_sudo: bool = False) -> int:
    """
    Run a Docker command, optionally using sudo, and handle errors gracefully.

    Args:
        command (list): The Docker command to run.
        use_sudo (bool): Whether to prepend 'sudo' to the command.

    Returns:
        int: The exit code of the command.
    """
    if use_sudo and platform.system().lower() == "linux":
        command.insert(0, "sudo")

    logger.info(f"Running command: {' '.join(command)}")

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logger.info(result.stdout)
        else:
            logger.error(f"Command failed with exit code {result.returncode}")
            logger.error(result.stderr)
            print(f"{Fore.RED}Error: {result.stderr.strip()}{Style.RESET_ALL}")
        return result.returncode
    except Exception as e:
        logger.error("Failed to run command: %s", e)
        print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
        raise RuntimeError(f"Command failed: {e}") from e


def _default_binfmt_path() -> str:
    from money4band.resources import get_path

    return str(get_path("files", "docker.binfmt.service"))


def setup_service(
    service_name: str = "docker.binfmt",
    service_file_path: str | None = None,
) -> None:
    """
    Set up a service on Linux systems, defaulting to setting up the Docker binfmt service.

    Args:
        service_name (str): The name of the service to set up. Default is "docker.binfmt".
        service_file_path (str | None): The path to the service file. Defaults to the
            bundled ``docker.binfmt.service`` inside ``money4band/resources/files/``.
    """
    if service_file_path is None:
        service_file_path = _default_binfmt_path()
    systemd_service_file = f"/etc/systemd/system/{service_name}.service"
    sysv_init_file = f"/etc/init.d/{service_name}"

    try:
        # Check if the service is already enabled and running
        if platform.system().lower() == "linux":
            if os.path.exists("/etc/systemd/system"):
                result = subprocess.run(
                    ["systemctl", "is-active", service_name],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.stdout.strip() == "active":
                    logger.info(
                        f"{Fore.GREEN}{service_name} is already active and running.{Style.RESET_ALL}"
                    )
                    return
            elif os.path.exists("/etc/init.d"):
                result = subprocess.run(
                    ["service", service_name, "status"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if "running" in result.stdout:
                    logger.info(
                        f"{Fore.GREEN}{service_name} is already active and running.{Style.RESET_ALL}"
                    )
                    return

        # Copy service file and enable service
        if os.path.exists("/etc/systemd/system"):
            if not os.path.exists(systemd_service_file):
                logger.info(f"Copying service file to {systemd_service_file}")
                subprocess.run(
                    ["sudo", "cp", service_file_path, systemd_service_file], check=True
                )
                subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                subprocess.run(
                    ["sudo", "systemctl", "enable", service_name], check=True
                )
            subprocess.run(["sudo", "systemctl", "start", service_name], check=False)
        elif os.path.exists("/etc/init.d"):
            if not os.path.exists(sysv_init_file):
                logger.info(f"Copying service file to {sysv_init_file}")
                subprocess.run(
                    ["sudo", "cp", service_file_path, sysv_init_file], check=True
                )
                subprocess.run(["sudo", "chmod", "+x", sysv_init_file], check=True)
                subprocess.run(
                    ["sudo", "update-rc.d", service_name, "defaults"], check=True
                )
            subprocess.run(["sudo", "service", service_name, "start"], check=False)

        logger.info(f"{Fore.GREEN}{service_name} setup and started.{Style.RESET_ALL}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to setup {service_name}: {str(e)}")
        raise RuntimeError(f"Failed to setup {service_name}: {str(e)}") from e


def ensure_service(
    service_name: str = "docker.binfmt",
    service_file_path: str | None = None,
) -> None:
    """
    Ensure that a service is installed and running, defaulting to the Docker binfmt service.

    Args:
        service_name (str): The name of the service to ensure. Default is "docker.binfmt".
        service_file_path (str | None): The path to the service file. Defaults to the
            bundled ``docker.binfmt.service`` inside ``money4band/resources/files/``.
    """
    logger.info(f"Ensuring {service_name} service is installed and running.")
    try:
        setup_service(service_name=service_name, service_file_path=service_file_path)
        logger.info(
            f"{Fore.GREEN}{service_name} setup completed successfully.{Style.RESET_ALL}"
        )
    except Exception as e:
        logger.error(f"Failed to ensure {service_name} service: {str(e)}")
        raise RuntimeError(f"Failed to ensure {service_name} service: {str(e)}") from e


def check_required_files(
    files: list[str], error_message: str | None = None, hint_message: str | None = None
) -> list[str]:
    """
    Check if required files exist and return a list of missing files.

    Args:
        files (list): List of file paths to check.
        error_message (str): Optional custom error message to display if files are missing.
        hint_message (str): Optional hint message to help the user resolve the issue.

    Returns:
        list: List of missing file paths. Empty list if all files exist.
    """
    missing_files = [f for f in files if not os.path.isfile(f)]

    if missing_files:
        if error_message:
            logger.error(error_message)
            print(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
        else:
            print(
                f"{Fore.RED}The following required files are missing:{Style.RESET_ALL}"
            )
        for f in missing_files:
            print(f"  - {f}")
        if hint_message:
            print(f"\n{Fore.YELLOW}{hint_message}{Style.RESET_ALL}")

    return missing_files


def show_spinner(message: str, event: threading.Event) -> None:
    """
    Display a spinner animation in the console to indicate progress.

    Args:
        message (str): The message to display alongside the spinner.
        event (threading.Event): A threading event to stop the spinner.
    """
    spinner = cycle(["|", "/", "-", "\\"])
    sys.stdout.write(f"{message} ")
    sys.stdout.flush()
    while not event.is_set():
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        time.sleep(0.1)
        sys.stdout.write("\b")  # Remove the spinner character
    sys.stdout.write("\b")  # Clear the spinner when stopping
    sys.stdout.write("Done\n")  # Print a completion message
    sys.stdout.flush()


def get_active_profiles(
    user_config_path_or_dict: str | dict[str, Any],
    app_config_path_or_dict: str | dict[str, Any] | None = None,
) -> list[str]:
    """Return Docker Compose profile names to activate for the current config.

    Every generated service carries a ``profiles:`` array, so default
    ``docker compose up`` starts nothing unless the activated set covers
    them. Resolves:

    - Tier profiles (``residential`` / ``datacenter`` / ``universal``
      / ``service``) from each enabled app's bundle ``profile`` field.
      When ``app_config_path_or_dict`` is None this step is skipped.
    - ``monitoring`` when watchtower is enabled in user-config.
    - ``proxy`` when ``proxies.enabled`` is true.

    Returns a sorted, de-duplicated list for stable CLI invocations.
    """
    from money4band.core.loader import (
        get_active_app_categories,
        get_category_entries,
        load_app_config_with_overlays,
        load_json_config,
    )

    cfg = load_json_config(user_config_path_or_dict)
    profiles: set[str] = set()

    enabled_app_names = {
        name.lower()
        for name, slice_ in cfg.get("apps", {}).items()
        if isinstance(slice_, dict) and slice_.get("enabled")
    }

    if app_config_path_or_dict is not None:
        try:
            # A path is the m4b-config file: the catalog lives folded under
            # its "catalog" key, so it MUST go through the overlay aggregator.
            # A plain load_json_config would yield zero categories and every
            # tier profile would silently drop (no app would ever start).
            if isinstance(app_config_path_or_dict, str):
                app_cfg = load_app_config_with_overlays(app_config_path_or_dict)
            else:
                app_cfg = load_json_config(app_config_path_or_dict)
            for category in get_active_app_categories(app_cfg):
                for entry in get_category_entries(app_cfg, category):
                    if entry.get("name", "").lower() in enabled_app_names:
                        tier = entry.get("profile")
                        if isinstance(tier, str) and tier:
                            profiles.add(tier)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to discover app tier profiles: %s; "
                "infra profiles will still be added.",
                exc,
            )
        if enabled_app_names and not profiles:
            logger.error(
                "No tier profile resolved for enabled apps %s - the stack "
                "would start no earning app. Check the catalog aggregation.",
                sorted(enabled_app_names),
            )

    if cfg.get("watchtower", {}).get("enabled", True):
        profiles.add("monitoring")
    if cfg.get("proxies", {}).get("enabled", False):
        profiles.add("proxy")
    return sorted(profiles)
