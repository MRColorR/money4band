from __future__ import annotations

import logging
import platform
import shutil
import subprocess
from collections.abc import Callable

from colorama import Fore, Style

from money4band.cls import cls
from money4band.prompt_helper import ask_question_yn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fallback install guides (shown when the quick tool isn't available)
# ---------------------------------------------------------------------------

_INSTALL_GUIDES: dict[str, str] = {
    "linux": (
        f"{Fore.CYAN}Docker install options for Linux:{Style.RESET_ALL}\n"
        "  1. Install curl, then re-run this guide (it will auto-install Docker):\n"
        "       sudo apt install curl   (Debian/Ubuntu)\n"
        "       sudo dnf install curl   (Fedora)\n"
        "  2. Package manager:\n"
        "       sudo apt update && sudo apt install docker.io docker-compose-plugin\n"
        "  3. Full manual instructions:\n"
        "       https://docs.docker.com/engine/install/\n"
        "\n"
        "  After installing, add your user to the docker group:\n"
        "       sudo usermod -aG docker $USER  (then log out & back in)"
    ),
    "windows": (
        f"{Fore.CYAN}Docker install options for Windows:{Style.RESET_ALL}\n"
        "  1. Install winget (App Installer from the Microsoft Store),\n"
        "     then re-run this guide — it will auto-install Docker Desktop.\n"
        "  2. Download Docker Desktop manually:\n"
        "       https://docs.docker.com/desktop/setup/install/windows-install/\n"
        "\n"
        "  Make sure WSL 2 is enabled (wsl --install) and Docker Desktop\n"
        "  is set to start with Windows."
    ),
    "darwin": (
        f"{Fore.CYAN}Docker install options for macOS:{Style.RESET_ALL}\n"
        "  1. Install Homebrew (https://brew.sh), then re-run this guide\n"
        "     — it will auto-install Docker Desktop.\n"
        "  2. Download Docker Desktop manually:\n"
        "       https://docs.docker.com/desktop/setup/install/mac-install/\n"
        "\n"
        "  After installing, launch Docker Desktop at least once to\n"
        "  complete the setup."
    ),
}


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def is_docker_installed() -> bool:
    """Return True if the ``docker`` CLI is on PATH and the daemon responds."""
    return shutil.which("docker") is not None and _docker_responds()


def _docker_responds() -> bool:
    try:
        subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return True
    except Exception:
        return False


def _has_tool(name: str) -> bool:
    """Return True if *name* is on PATH."""
    return shutil.which(name) is not None


# ---------------------------------------------------------------------------
# One-command installers (per OS)
# ---------------------------------------------------------------------------


def _install_linux() -> bool:
    """Run the official get.docker.com convenience script via curl."""
    print("Running: curl -fsSL https://get.docker.com | sudo sh")
    try:
        curl = subprocess.Popen(
            ["curl", "-fsSL", "https://get.docker.com"],
            stdout=subprocess.PIPE,
        )
        subprocess.run(
            ["sudo", "sh"],
            stdin=curl.stdout,
            check=True,
        )
        curl.wait()
        print(
            f"\n{Fore.GREEN}Docker installed successfully.{Style.RESET_ALL}\n"
            "  Tip: sudo usermod -aG docker $USER  (then log out & back in)"
        )
        logger.info("Docker installed via get.docker.com convenience script")
        return True
    except (subprocess.CalledProcessError, OSError) as exc:
        logger.error("Linux auto-install failed: %s", exc)
        print(f"{Fore.RED}Auto-install failed: {exc}{Style.RESET_ALL}")
        return False


def _install_windows() -> bool:
    """Install Docker Desktop via winget."""
    print(
        "Running: winget install -e --id Docker.DockerDesktop --accept-source-agreements --accept-package-agreements"
    )
    try:
        subprocess.run(
            [
                "winget",
                "install",
                "-e",
                "--id",
                "Docker.DockerDesktop",
                "--accept-source-agreements",
                "--accept-package-agreements",
            ],
            check=True,
        )
        print(
            f"\n{Fore.GREEN}Docker Desktop installed successfully.{Style.RESET_ALL}\n"
            "  Make sure WSL 2 is enabled (wsl --install) and Docker Desktop\n"
            "  is set to start with Windows."
        )
        logger.info("Docker Desktop installed via winget")
        return True
    except (subprocess.CalledProcessError, OSError) as exc:
        logger.error("Windows auto-install failed: %s", exc)
        print(f"{Fore.RED}Auto-install failed: {exc}{Style.RESET_ALL}")
        return False


def _install_macos() -> bool:
    """Install Docker Desktop via Homebrew."""
    print("Running: brew install --cask docker")
    try:
        subprocess.run(
            ["brew", "install", "--cask", "docker"],
            check=True,
        )
        print(
            f"\n{Fore.GREEN}Docker Desktop installed successfully.{Style.RESET_ALL}\n"
            "  Launch Docker Desktop at least once to complete the setup."
        )
        logger.info("Docker Desktop installed via Homebrew")
        return True
    except (subprocess.CalledProcessError, OSError) as exc:
        logger.error("macOS auto-install failed: %s", exc)
        print(f"{Fore.RED}Auto-install failed: {exc}{Style.RESET_ALL}")
        return False


# Map: os_key → (required_tool, installer_callable, human description)
_AUTO_INSTALLERS: dict[str, tuple[str, Callable[[], bool], str]] = {
    "linux": ("curl", _install_linux, "curl -fsSL https://get.docker.com | sudo sh"),
    "windows": ("winget", _install_windows, "winget install Docker.DockerDesktop"),
    "darwin": ("brew", _install_macos, "brew install --cask docker"),
}


# ---------------------------------------------------------------------------
# Fallback guide
# ---------------------------------------------------------------------------


def show_docker_guide() -> None:
    """Print OS-specific Docker installation instructions."""
    os_key = platform.system().lower()
    guide = _INSTALL_GUIDES.get(os_key)
    if guide:
        print(f"\n{guide}\n")
    else:
        print(
            f"\n{Fore.YELLOW}Unsupported OS ({os_key}). "
            f"Visit https://docs.docker.com/engine/install/{Style.RESET_ALL}\n"
        )


# ---------------------------------------------------------------------------
# TUI entry point
# ---------------------------------------------------------------------------


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """Docker Setup — called from the TUI menu.

    1. If Docker is already installed → report version and return.
    2. If a quick install tool is available (curl / winget / brew) → offer
       to auto-install with a y/n prompt.
    3. Otherwise → show a manual-install guide.
    """
    cls()

    # Already installed?
    if is_docker_installed():
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
        )
        version = result.stdout.strip() if result.returncode == 0 else "unknown"
        print(f"{Fore.GREEN}Docker is already installed: {version}{Style.RESET_ALL}\n")
        logger.info("Docker already installed: %s", version)
        input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
        return

    print(
        f"{Fore.YELLOW}Docker is not installed or the daemon is not running.{Style.RESET_ALL}\n"
    )

    os_key = platform.system().lower()
    entry = _AUTO_INSTALLERS.get(os_key)

    if entry:
        tool, installer, description = entry
        if _has_tool(tool):
            print(f"  Auto-install available:  {description}")
            if ask_question_yn("Do you want to install Docker now?"):
                if installer():
                    input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
                    return
                # installer failed — fall through to guide
                print(
                    f"\n{Fore.YELLOW}Falling back to manual instructions.{Style.RESET_ALL}"
                )
            else:
                logger.info("User declined auto-install")

    show_docker_guide()
    logger.info("Showed Docker installation guide for %s", platform.system())
    input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
