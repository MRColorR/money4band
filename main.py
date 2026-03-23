from __future__ import annotations

import argparse
import atexit
import locale
import logging
import os
import signal
import subprocess

# Ensure the parent directory is in the sys.path
import sys
import time
from logging.handlers import RotatingFileHandler

from colorama import Fore, Style, just_fix_windows_console

from money4band import detector, dumper, loader
from money4band.backup import (
    cleanup_backups,
    create_backup,
    list_backups,
    restore_backup,
)
from money4band.cls import cls
from money4band.crypto import ensure_config_encrypted
from money4band.fn_reset_config import main as reset_main
from money4band.updater import check_update_available, show_update_banner

logger = logging.getLogger(__name__)

# Handle PyInstaller frozen executable path resolution
if getattr(sys, "frozen", False):
    # Running as compiled executable (PyInstaller)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Change working directory to script location to ensure relative paths work
os.chdir(BASE_DIR)

parent_dir = os.path.dirname(BASE_DIR)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import the module from the parent directory


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _resolve_paths(args: argparse.Namespace) -> tuple[str, str, str]:
    """Compute the three config paths + utils dir from parsed args."""
    m4b_config_path = os.path.join(args.config_dir, args.config_m4b_file)
    apps_config_path = os.path.join(args.config_dir, args.config_app_file)
    user_config_path = os.path.join(args.config_dir, args.config_usr_file)
    return m4b_config_path, apps_config_path, user_config_path


def _ensure_user_config(args: argparse.Namespace, user_config_path: str) -> None:
    """Create user config from template if missing, then encrypt if needed.

    Also detects template-default configs (all placeholder values) and
    prompts the user to run setup.
    """
    if not os.path.exists(user_config_path):
        logger.info("User config not found. Resetting from template...")
        reset_main(
            app_config_path=None,
            m4b_config_path=None,
            user_config_path=user_config_path,
            src_path=args.template_user_config_path,
            dest_path=user_config_path,
        )
    ensure_config_encrypted(user_config_path)
    register_encryption_hooks(user_config_path)


def _has_template_defaults(user_config_path: str) -> bool:
    """Return True if the user config still contains placeholder values.

    Only checks *enabled* apps — disabled apps are expected to keep
    their placeholder credentials until the user decides to enable them.
    """
    try:
        cfg = loader.load_json_config(user_config_path)
    except Exception:
        return False
    apps = cfg.get("apps", {})
    if not apps:
        return True
    # If no app is enabled at all, treat as first-run
    enabled = {
        name: app_cfg
        for name, app_cfg in apps.items()
        if isinstance(app_cfg, dict) and app_cfg.get("enabled", False)
    }
    if not enabled:
        return True
    # Check only enabled apps for leftover placeholders
    for app_cfg in enabled.values():
        for key, val in app_cfg.items():
            if key == "enabled":
                continue
            if isinstance(val, str) and val.lower().startswith("your"):
                return True
    return False


# ---------------------------------------------------------------------------
# Credential encryption lifecycle
# ---------------------------------------------------------------------------

_encrypt_on_exit_paths: list[str] = []


def _encrypt_on_exit() -> None:
    """Best-effort encrypt all registered config paths."""
    for path in _encrypt_on_exit_paths:
        try:
            ensure_config_encrypted(path)
        except Exception:
            pass  # Best-effort during shutdown


def _sigterm_handler(signum: int, frame: object) -> None:
    """Handle SIGTERM by encrypting configs before exit."""
    _encrypt_on_exit()
    sys.exit(128 + signum)


def register_encryption_hooks(user_config_path: str) -> None:
    """Register atexit + SIGTERM handlers to auto-encrypt config on exit."""
    if user_config_path in _encrypt_on_exit_paths:
        return
    _encrypt_on_exit_paths.append(user_config_path)

    if len(_encrypt_on_exit_paths) == 1:
        atexit.register(_encrypt_on_exit)
        signal.signal(signal.SIGTERM, _sigterm_handler)


# ---------------------------------------------------------------------------
# Interactive menu (default when no subcommand given)
# ---------------------------------------------------------------------------


def mainmenu(
    m4b_config_path: str,
    apps_config_path: str,
    user_config_path: str,
    modules_dir_path: str,
) -> None:
    """
    Main menu of the script.

    Arguments:
    m4b_config_path -- the path to the m4b config file
    apps_config_path -- the path to the apps config file
    user_config_path -- the path to the user config file
    modules_dir_path -- the path to the money4band modules directory
    """
    try:
        logger.debug("Initializing colorama")
        just_fix_windows_console()
        logger.info("Colorama initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing colorama: {str(e)}")
        raise

    while True:
        try:
            logger.info("Loading configurations")
            m4b_config = loader.load_json_config(m4b_config_path)
            user_config = loader.load_json_config(user_config_path)
            logger.info("Configurations loaded successfully")
        except FileNotFoundError as e:
            logger.error(f"File not found: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"An error occurred while loading configurations: {str(e)}")
            raise

        try:
            logger.debug("Loading main menu")
            sleep_time = m4b_config.get("system", {}).get("sleep_time", 2)

            logger.debug("Detecting OS and architecture")
            system_info = {
                **detector.detect_os(m4b_config_path),
                **detector.detect_architecture(m4b_config_path),
            }

            # Update user_config with detected OS, architecture, and docker architecture
            device_info = user_config.setdefault("device_info", {})
            device_info["os_type"] = system_info.get("os_type")
            device_info["detected_architecture"] = system_info.get("arch")
            device_info["detected_docker_arch"] = system_info.get("dkarch")

            # Add default platform for apps if not already present
            for app_name in user_config.get("apps", {}):
                app_config = user_config["apps"].setdefault(app_name, {})
                if "docker_platform" not in app_config:
                    app_config["docker_platform"] = (
                        f"linux/{device_info['detected_docker_arch']}"
                    )

            dumper.write_json(user_config, user_config_path)
            logger.info(f"System info and default platform stored: {device_info}")

            logger.debug("Calculating resources limits based on system")
            detector.calculate_resource_limits(
                user_config_path_or_dict=user_config_path,
                m4b_config=m4b_config,
            )

            # Load the functions from the passed tools dir
            logger.debug(f"Loading modules from {modules_dir_path}")
            m4b_tools_modules = loader.load_modules_from_directory(modules_dir_path)
            logger.info(f"Successfully loaded modules from {modules_dir_path}")
            cls()
            print(f"{Fore.GREEN}----------------------------------------------")
            print(
                f"{Fore.GREEN}MONEY4BAND v{m4b_config.get('project')['project_version']}{Style.RESET_ALL}"
            )
            check_update_available(m4b_config)
            print(
                f"{Fore.GREEN}----------------------------------------------{Style.RESET_ALL}"
            )
            print(
                f"{Fore.YELLOW}Support the M4B development <3 check the donation options in the README, on GitHub or in our Discord. Every bit helps!"
            )
            print(
                f"{Fore.MAGENTA}Join our Discord community for updates, help and discussions: {m4b_config.get('project')['ds_project_server_url']}{Style.RESET_ALL}"
            )
            print("----------------------------------------------")
        except Exception as e:
            logger.error(f"An error occurred while setting up the menu: {str(e)}")
            raise
        try:
            logger.debug("Loading menu options from config file")
            menu_options = m4b_config["menu"]

            for i, option in enumerate(menu_options, start=1):
                print(f"{i}. {option['label']}")
            print(f"\n  {Fore.CYAN}q{Style.RESET_ALL} Quit")

            choice = input("Select: ").strip().lower()

            if choice == "q":
                # Dispatch to fn_bye the same way the numbered "Quit" entry would
                bye_entry = next(
                    (o for o in menu_options if o["function"] == "fn_bye"), None
                )
                if bye_entry:
                    m4b_tools_modules["fn_bye"].main(
                        apps_config_path, m4b_config_path, user_config_path
                    )
                return

            try:
                choice_num = int(choice)
            except ValueError:
                print(
                    f"{Fore.YELLOW}Invalid selection. Choose 1\u2013{len(menu_options)} or a shortcut.{Style.RESET_ALL}"
                )
                time.sleep(sleep_time)
                continue

            if 1 <= choice_num <= len(menu_options):
                function_label = menu_options[choice_num - 1]["label"]
                function_name = menu_options[choice_num - 1]["function"]
                logger.info(
                    f"User selected menu option number {choice_num} that corresponds to menu item {function_label}"
                )
                m4b_tools_modules[function_name].main(
                    apps_config_path, m4b_config_path, user_config_path
                )
            else:
                print(
                    f"{Fore.YELLOW}Invalid selection. Choose 1\u2013{len(menu_options)} or a shortcut.{Style.RESET_ALL}"
                )
                time.sleep(sleep_time)
        except Exception as e:
            logger.error(f"An error occurred while processing the menu: {str(e)}")
            raise


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _cmd_menu(args: argparse.Namespace) -> None:
    """Launch the interactive menu (default behaviour)."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)

    if _has_template_defaults(user_config_path):
        just_fix_windows_console()
        print(
            f"\n{Fore.YELLOW}It looks like this is your first run — "
            f"the config still has placeholder values.{Style.RESET_ALL}"
        )
        print("Running the setup wizard to configure your apps...\n")
        _auto_backup(user_config_path)
        from money4band.fn_setupApps import main as setup_main

        setup_main(apps_config_path, m4b_config_path, user_config_path)

    mainmenu(
        m4b_config_path=m4b_config_path,
        apps_config_path=apps_config_path,
        user_config_path=user_config_path,
        modules_dir_path=args.modules_dir,
    )


def _auto_backup(user_config_path: str) -> None:
    """Create a backup before destructive operations (best-effort)."""
    try:
        if os.path.isfile(user_config_path):
            create_backup(user_config_path)
            cleanup_backups()
    except Exception:
        logger.warning("Auto-backup failed", exc_info=True)


def _cmd_setup(args: argparse.Namespace) -> None:
    """Run the interactive setup wizard."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    _auto_backup(user_config_path)

    from money4band.helper import check_docker_ready

    check_docker_ready()

    from money4band.fn_setupApps import main as setup_main

    setup_main(
        apps_config_path,
        m4b_config_path,
        user_config_path,
        resume=getattr(args, "resume", False),
    )


def _cmd_start(args: argparse.Namespace) -> None:
    """Start the Docker Compose stack."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)

    if _has_template_defaults(user_config_path):
        just_fix_windows_console()
        print(
            f"{Fore.YELLOW}Warning: Config contains placeholder values. "
            f"Run 'setup' first to configure your apps.{Style.RESET_ALL}"
        )
        return

    from money4band.helper import check_docker_ready

    check_docker_ready()

    from money4band.fn_startStack import main as start_main

    start_main(apps_config_path, m4b_config_path, user_config_path)


def _cmd_stop(args: argparse.Namespace) -> None:
    """Stop the Docker Compose stack."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    from money4band.fn_stopStack import main as stop_main

    stop_main(apps_config_path, m4b_config_path, user_config_path)


def _cmd_status(args: argparse.Namespace) -> None:
    """Show running containers and health status."""
    from money4band.compose_builder import get_compose_files
    from money4band.helper import get_compose_project_name

    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)

    compose_files = get_compose_files(BASE_DIR)
    env_file = os.path.join(BASE_DIR, ".env")

    if not compose_files:
        print(
            f"{Fore.YELLOW}No compose files found. "
            f"Run 'setup' or 'generate' first.{Style.RESET_ALL}"
        )
        return

    cmd = ["docker", "compose"]
    if os.path.isfile(env_file):
        project_name = get_compose_project_name(env_file)
        if project_name:
            cmd.extend(["-p", project_name])
    for cf in compose_files:
        cmd.extend(["-f", cf])
    # Show ALL services (including profiled infrastructure) for visibility.
    for profile in ("monitoring", "dashboard", "proxy"):
        cmd.extend(["--profile", profile])
    cmd.extend(["ps", "--format", "table"])

    just_fix_windows_console()
    print(f"{Fore.GREEN}--- M4B Stack Status ---{Style.RESET_ALL}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"{Fore.RED}Error:{Style.RESET_ALL} {result.stderr.strip()}")

    # Health summary from Docker inspect
    from money4band.monitor import get_stack_health

    project_name = None
    if os.path.isfile(env_file):
        project_name = get_compose_project_name(env_file)
    statuses = get_stack_health(project_filter=project_name)
    if statuses:
        print(f"{Fore.GREEN}--- Health Summary ---{Style.RESET_ALL}")
        for s in statuses:
            icon = f"{Fore.GREEN}\u2713" if s.ok else f"{Fore.RED}\u2717"
            health_tag = s.health if s.health != "none" else "no-healthcheck"
            line = f"  {icon} {s.name:<35}{Style.RESET_ALL} {health_tag:<16} restarts={s.restart_count}"
            if s.last_error:
                line += f"  {Fore.YELLOW}err: {s.last_error[:80]}{Style.RESET_ALL}"
            if s.restart_count >= 5:
                line += f"  {Fore.RED}[RESTART LOOP]{Style.RESET_ALL}"
            print(line)
        print()

    # Earnings estimation
    app_config = loader.load_json_config(apps_config_path)
    from money4band.earnings_estimator import display_earnings_summary

    display_earnings_summary(app_config)


def _cmd_generate(args: argparse.Namespace) -> None:
    """Regenerate docker-compose.yaml and .env from config."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)

    if getattr(args, "docs", False):
        from money4band.loader import load_json_config
        from money4band.readme_generator import update_apps_md, update_readme

        app_config = load_json_config(apps_config_path)
        readme_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "README.md"
        )
        apps_md_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "docs", "APPS.md"
        )
        ok_readme = update_readme(app_config, readme_path)
        ok_apps = update_apps_md(app_config, apps_md_path)
        if ok_readme:
            print(f"{Fore.GREEN}README.md app table updated.{Style.RESET_ALL}")
        if ok_apps:
            print(f"{Fore.GREEN}docs/APPS.md app table updated.{Style.RESET_ALL}")
        if not ok_readme and not ok_apps:
            print(
                f"{Fore.YELLOW}No marker sections found in target files.{Style.RESET_ALL}"
            )
        return

    _ensure_user_config(args, user_config_path)
    _auto_backup(user_config_path)
    from money4band.generator import main as gen_main

    gen_main(apps_config_path, m4b_config_path, user_config_path)


def _cmd_links(args: argparse.Namespace) -> None:
    """Show app dashboard and referral links."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    from money4band.fn_app_catalog import main as links_main

    links_main(apps_config_path, m4b_config_path, user_config_path)


def _cmd_reset(args: argparse.Namespace) -> None:
    """Reset user-config.json from template."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _auto_backup(user_config_path)
    reset_main(
        app_config_path=apps_config_path,
        m4b_config_path=m4b_config_path,
        user_config_path=user_config_path,
        src_path=args.template_user_config_path,
        dest_path=user_config_path,
    )
    print(f"{Fore.GREEN}User config reset to template defaults.{Style.RESET_ALL}")


def _cmd_proxy(args: argparse.Namespace) -> None:
    """Launch multiproxy tools."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    from money4band.fn_multiproxy_tools import main as proxy_main

    proxy_main(apps_config_path, m4b_config_path, user_config_path)


def _cmd_backup(args: argparse.Namespace) -> None:
    """Create a manual config backup."""
    _, _, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    just_fix_windows_console()
    backup_path = create_backup(user_config_path)
    cleanup_backups()
    print(f"{Fore.GREEN}Backup saved: {backup_path}{Style.RESET_ALL}")


def _cmd_restore(args: argparse.Namespace) -> None:
    """Restore user-config from a backup."""
    _, _, user_config_path = _resolve_paths(args)
    just_fix_windows_console()
    backups = list_backups()
    if not backups:
        print(f"{Fore.YELLOW}No backups found.{Style.RESET_ALL}")
        return

    print(f"{Fore.GREEN}Available backups:{Style.RESET_ALL}")
    for i, b in enumerate(backups, 1):
        print(f"  {i}. {b.path.name}  ({b.timestamp:%Y-%m-%d %H:%M:%S UTC})")

    print(f"  Press {Fore.CYAN}Enter{Style.RESET_ALL} to cancel.")
    choice = input("Select: ").strip()
    if not choice:
        return
    try:
        idx = int(choice) - 1
        if not 0 <= idx < len(backups):
            raise ValueError
    except ValueError:
        print(f"{Fore.RED}Invalid selection.{Style.RESET_ALL}")
        return

    # Back up current config before overwriting
    _auto_backup(user_config_path)
    restore_backup(backups[idx].path, user_config_path)
    print(f"{Fore.GREEN}Restored: {backups[idx].path.name}{Style.RESET_ALL}")


def _cmd_update(args: argparse.Namespace) -> None:
    """Check for updates and optionally apply them."""
    m4b_config_path, _, _ = _resolve_paths(args)
    just_fix_windows_console()
    m4b_config = loader.load_json_config(m4b_config_path)

    from money4band.updater import apply_update, check_for_update

    new_version = check_for_update(m4b_config)
    if not new_version:
        print(f"{Fore.GREEN}M4B is up to date.{Style.RESET_ALL}")
        return

    current = m4b_config.get("project", {}).get("project_version", "?")
    print(
        f"{Fore.YELLOW}Update available: v{current} → v{new_version}{Style.RESET_ALL}"
    )

    force = getattr(args, "force", False)
    if not force:
        from money4band.prompt_helper import ask_question_yn

        if not ask_question_yn("Apply update now?", default=False):
            print("Update cancelled.")
            return

    print(f"{Fore.CYAN}Applying update to v{new_version}...{Style.RESET_ALL}")
    if apply_update(new_version):
        print(
            f"{Fore.GREEN}Updated to v{new_version}. "
            f"Please restart M4B.{Style.RESET_ALL}"
        )
    else:
        print(f"{Fore.RED}Update failed. See logs for details.{Style.RESET_ALL}")


def _cmd_limit(args: argparse.Namespace) -> None:
    """Show or change the active resource limit profile."""
    m4b_config_path, _, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    just_fix_windows_console()

    m4b_config = loader.load_json_config(m4b_config_path)
    user_config = loader.load_json_config(user_config_path)
    profile_name = getattr(args, "profile", None)

    if not profile_name:
        # Show current profile + stats.
        detector.show_resource_profile_info(m4b_config, user_config)
        return

    if profile_name not in detector.VALID_PROFILES:
        print(
            f"{Fore.RED}Invalid profile '{profile_name}'. "
            f"Choose from: {', '.join(detector.VALID_PROFILES)}{Style.RESET_ALL}"
        )
        return

    # Switch profile.
    m4b_config.setdefault("resource_profiles", {})["active"] = profile_name
    dumper.write_json(m4b_config, m4b_config_path)

    # Recalculate limits with the new profile.
    detector.calculate_resource_limits(user_config_path, m4b_config=m4b_config)

    # Regenerate .env so Docker picks up the new limits.
    from money4band.generator import generate_env_file

    apps_config_path = os.path.join(args.config_dir, args.config_app_file)
    generate_env_file(
        m4b_config_path,
        apps_config_path,
        user_config_path,
        env_output_path=os.path.join(BASE_DIR, ".env"),
    )

    # Reload user_config to show updated values.
    user_config = loader.load_json_config(user_config_path)
    print(f"{Fore.GREEN}Switched to profile: {profile_name}{Style.RESET_ALL}")
    detector.show_resource_profile_info(m4b_config, user_config)
    print(
        f"\n{Fore.YELLOW}Restart your stack (`m4b start`) "
        f"for new limits to take effect.{Style.RESET_ALL}"
    )


def _cmd_ip(args: argparse.Namespace) -> None:
    """Analyse IP quality for real IP and configured proxies."""
    just_fix_windows_console()
    from money4band.ip_scorer import analyse_ips

    analyse_ips()


def _cmd_info(args: argparse.Namespace) -> None:
    """Display system information dashboard."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    just_fix_windows_console()

    m4b_config = loader.load_json_config(m4b_config_path)
    app_config = loader.load_json_config(apps_config_path)
    user_config = loader.load_json_config(user_config_path)

    from money4band.system_info import show_system_info

    show_system_info(m4b_config, app_config, user_config)


def _cmd_notify(args: argparse.Namespace) -> None:
    """Send a test notification or show notification status."""
    _, _, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    just_fix_windows_console()

    user_config = loader.load_json_config(user_config_path)
    action = getattr(args, "notify_action", None)

    if action == "test":
        from money4band.notifier import is_enabled, send_test

        if not is_enabled(user_config):
            print(
                f"{Fore.RED}Notifications are not enabled. "
                f"Run 'm4b setup' to configure them.{Style.RESET_ALL}"
            )
            return
        print(f"{Fore.CYAN}Sending test notification...{Style.RESET_ALL}")
        if send_test(user_config):
            print(f"{Fore.GREEN}Test notification sent successfully!{Style.RESET_ALL}")
        else:
            print(
                f"{Fore.RED}Failed to send test notification. "
                f"Check your URL and Docker availability.{Style.RESET_ALL}"
            )
    else:
        from money4band.notifier import ALL_EVENTS, is_enabled, is_event_enabled

        cfg = user_config.get("notifications", {})
        status = "enabled" if is_enabled(user_config) else "disabled"
        print(f"Notifications: {Fore.CYAN}{status}{Style.RESET_ALL}")
        if cfg.get("url"):
            masked = cfg["url"][:12] + "..." if len(cfg["url"]) > 12 else cfg["url"]
            print(f"  URL: {masked}")
        print("  Events:")
        for evt in sorted(ALL_EVENTS - {"test"}):
            on = is_event_enabled(user_config, evt)
            mark = (
                f"{Fore.GREEN}ON{Style.RESET_ALL}"
                if on
                else f"{Fore.RED}OFF{Style.RESET_ALL}"
            )
            print(f"    {evt}: {mark}")


def _cmd_apps(args: argparse.Namespace) -> None:
    """List apps or show detail for a specific app."""
    _, apps_config_path, _ = _resolve_paths(args)
    just_fix_windows_console()

    app_config = loader.load_json_config(apps_config_path)

    app_name = getattr(args, "app_name", None)
    if app_name:
        from money4band.app_info import show_app_detail

        show_app_detail(app_config, app_name)
    else:
        from money4band.app_info import list_apps

        category = getattr(args, "category", None)
        list_apps(app_config, category_filter=category)


def _cmd_validate(args: argparse.Namespace) -> None:
    """Run Docker image security checks."""
    _, apps_config_path, _ = _resolve_paths(args)

    app_config = loader.load_json_config(apps_config_path)

    from money4band.image_security import validate_images

    skip_cves = getattr(args, "skip_cves", False)
    validate_images(app_config, run_cves=not skip_cves)


def _cmd_app(args: argparse.Namespace) -> None:
    """App plugin management — add or validate community apps."""
    action = getattr(args, "app_action", None)
    config_dir = getattr(args, "config_dir", os.path.join(BASE_DIR, "config"))
    apps_d_dir = os.path.join(config_dir, "apps.d")

    if action == "add":
        from money4band.app_wizard import run_app_wizard

        run_app_wizard(apps_d_dir)
    elif action == "validate":
        from money4band.app_schema import load_community_apps, validate_app_entry

        just_fix_windows_console()
        entries = load_community_apps(apps_d_dir)
        if not entries:
            print(
                f"{Fore.YELLOW}No community apps found in {apps_d_dir}{Style.RESET_ALL}"
            )
            return
        all_ok = True
        for entry in entries:
            errors = validate_app_entry(entry)
            name = entry.get("name", "?")
            if errors:
                all_ok = False
                print(f"{Fore.RED}\u2717 {name}:{Style.RESET_ALL}")
                for e in errors:
                    print(f"    {e}")
            else:
                print(f"{Fore.GREEN}\u2713 {name}{Style.RESET_ALL}")
        if all_ok:
            print(
                f"\n{Fore.GREEN}All {len(entries)} community app(s) valid.{Style.RESET_ALL}"
            )
    else:
        print("Usage: m4b app {add,validate}")
        print("  add       Interactive wizard to add a new community app")
        print("  validate  Check all apps.d/ files against the schema")


def _cmd_offers(args: argparse.Namespace) -> None:
    """Show referral and passive income offers."""
    just_fix_windows_console()
    config_dir = getattr(args, "config_dir", os.path.join(BASE_DIR, "config"))
    offers_path = os.path.join(config_dir, "referral-offers.json")
    apps_config_path = os.path.join(config_dir, "app-config.json")
    category = getattr(args, "offer_category", None)

    from money4band.offers import display_offers

    display_offers(
        offers_path, category_filter=category, app_config_path=apps_config_path
    )


def _cmd_dashboard(args: argparse.Namespace) -> None:
    """Start the web dashboard API server."""
    config_dir = getattr(args, "config_dir", os.path.join(BASE_DIR, "config"))
    port = getattr(args, "port", 8088)

    from money4band.dashboard_api import configure, start_server

    configure(config_dir)
    print(f"{Fore.GREEN}Starting M4B Dashboard API on port {port}...{Style.RESET_ALL}")
    print(f"  API docs: http://localhost:{port}/api/docs")
    print(f"  Status:   http://localhost:{port}/api/status")
    start_server(port=port)


def _cmd_profile(args: argparse.Namespace) -> None:
    """Manage configuration profiles."""
    _, _, user_config_path = _resolve_paths(args)
    config_dir = getattr(args, "config_dir", os.path.join(BASE_DIR, "config"))
    just_fix_windows_console()

    action = getattr(args, "profile_action", None)
    name = getattr(args, "profile_name", None)

    from money4band.profiles import (
        create_profile,
        delete_profile,
        display_profiles,
        switch_profile,
    )

    if action == "create":
        if not name:
            print(f"{Fore.RED}Profile name required.{Style.RESET_ALL}")
            return
        path = create_profile(name, config_dir, BASE_DIR, user_config_path)
        print(f"{Fore.GREEN}Profile '{name}' saved to {path}{Style.RESET_ALL}")
    elif action == "switch":
        if not name:
            print(f"{Fore.RED}Profile name required.{Style.RESET_ALL}")
            return
        if switch_profile(name, config_dir, BASE_DIR, user_config_path):
            print(f"{Fore.GREEN}Switched to profile '{name}'.{Style.RESET_ALL}")
            print(
                f"{Fore.YELLOW}Run 'generate' to rebuild compose files.{Style.RESET_ALL}"
            )
        else:
            print(f"{Fore.RED}Profile '{name}' not found.{Style.RESET_ALL}")
    elif action == "delete":
        if not name:
            print(f"{Fore.RED}Profile name required.{Style.RESET_ALL}")
            return
        if delete_profile(name, config_dir):
            print(f"{Fore.GREEN}Profile '{name}' deleted.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Profile '{name}' not found.{Style.RESET_ALL}")
    else:
        display_profiles(config_dir)


def _cmd_dns(args: argparse.Namespace) -> None:
    """View or configure DNS settings for containers."""
    m4b_config_path, _, _ = _resolve_paths(args)
    just_fix_windows_console()

    dns_action = getattr(args, "dns_action", None)

    if dns_action == "set":
        mode = args.mode
        servers = args.servers.split(",") if getattr(args, "servers", None) else None
        from money4band.system_info import set_dns_mode

        set_dns_mode(m4b_config_path, mode, servers)
        print(f"{Fore.GREEN}DNS mode set to '{mode}'.{Style.RESET_ALL}")
        if servers:
            print(f"  Servers: {', '.join(servers)}")
        print(f"{Fore.YELLOW}Run 'generate' to rebuild compose files.{Style.RESET_ALL}")
    else:
        m4b_config = loader.load_json_config(m4b_config_path)
        from money4band.system_info import show_dns_status

        show_dns_status(m4b_config)


def _cmd_config(args: argparse.Namespace) -> None:
    """View or edit encrypted user config."""
    _, _, user_config_path = _resolve_paths(args)
    action = getattr(args, "config_action", None)

    if action == "view":
        from money4band.config_viewer import view_masked

        view_masked(user_config_path)
    elif action == "edit":
        from money4band.config_viewer import edit_config

        register_encryption_hooks(user_config_path)
        edit_config(user_config_path)
    else:
        just_fix_windows_console()
        print(f"{Fore.YELLOW}Usage: m4b config {{view,edit}}{Style.RESET_ALL}")


# ---------------------------------------------------------------------------
# CLI parser construction
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with subcommands."""
    script_dir = BASE_DIR

    parser = argparse.ArgumentParser(
        prog="m4b",
        description="Money4Band — Docker orchestrator for passive income apps",
    )

    # ---- global flags (shared by all subcommands) ----
    parser.add_argument(
        "--config-dir",
        default=os.path.join(script_dir, "config"),
        help="Set the config directory",
    )
    parser.add_argument(
        "--config-m4b-file",
        default="m4b-config.json",
        help="Set the m4b config file name",
    )
    parser.add_argument(
        "--config-usr-file",
        default="user-config.json",
        help="Set the user config file name",
    )
    parser.add_argument(
        "--config-app-file",
        default="app-config.json",
        help="Set the apps config file name",
    )
    parser.add_argument(
        "--modules-dir",
        default=os.path.join(script_dir, "money4band"),
        help="Set the m4b tools directory",
    )
    parser.add_argument(
        "--requirements-path",
        default=os.path.join(script_dir, "requirements.toml"),
        help="Set the requirements path",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    parser.add_argument(
        "--log-dir",
        default=os.path.join(script_dir, "logs"),
        help="Set the logging directory",
    )
    parser.add_argument(
        "--log-file", default="m4b.log", help="Set the logging file name"
    )
    parser.add_argument(
        "--template-user-config-path",
        default=os.path.join(script_dir, "template", "user-config.json"),
        help="Set the template user config file path",
    )

    # ---- subcommands ----
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="Run the interactive setup wizard").add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Resume a previously interrupted setup, skipping completed steps",
    )
    sub.add_parser("start", help="Start the Docker Compose stack")
    sub.add_parser("stop", help="Stop the Docker Compose stack")
    sub.add_parser("status", help="Show running containers and health")
    gen_parser = sub.add_parser(
        "generate", help="Regenerate docker-compose.yaml and .env"
    )
    gen_parser.add_argument(
        "--docs",
        action="store_true",
        help="Regenerate README.md and docs/APPS.md app tables from app-config.json",
    )
    sub.add_parser("links", help="Show app dashboard and referral links")
    sub.add_parser("reset", help="Reset user-config to template defaults")
    sub.add_parser("proxy", help="Multi-proxy management tools")
    sub.add_parser("backup", help="Create a config backup")
    sub.add_parser("restore", help="Restore config from a backup")

    update_parser = sub.add_parser("update", help="Check for and apply M4B updates")
    update_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Apply update without confirmation prompt",
    )

    config_parser = sub.add_parser("config", help="View or edit encrypted config")
    config_sub = config_parser.add_subparsers(dest="config_action")
    config_sub.add_parser("view", help="Display config with masked credentials")
    config_sub.add_parser("edit", help="Edit config in $EDITOR, re-encrypts on save")

    limit_parser = sub.add_parser(
        "limit", help="Show or change the active resource limit profile"
    )
    limit_parser.add_argument(
        "profile",
        nargs="?",
        default=None,
        help="Profile name to switch to (base/min/low/mid/max). Omit to show current.",
    )

    sub.add_parser("ip", help="Analyse IP quality for real IP and proxies")

    sub.add_parser("info", help="Show system information dashboard")

    apps_parser = sub.add_parser("apps", help="List apps or show app detail card")
    apps_parser.add_argument(
        "app_name",
        nargs="?",
        default=None,
        help="App name to show detail for. Omit to list all apps.",
    )
    apps_parser.add_argument(
        "--category",
        "-c",
        default=None,
        choices=["supported", "deprecated", "candidate"],
        help="Filter listing by category",
    )

    validate_parser = sub.add_parser(
        "validate", help="Run Docker image security checks"
    )
    validate_parser.add_argument(
        "--skip-cves",
        action="store_true",
        default=False,
        help="Skip CVE scanning (only run stale check and digest logging)",
    )

    app_parser = sub.add_parser("app", help="App plugin management (add/validate)")
    app_parser.add_argument(
        "app_action",
        nargs="?",
        default=None,
        choices=["add", "validate"],
        help="Action: 'add' to create a new community app, 'validate' to check apps.d/ files",
    )

    offers_parser = sub.add_parser(
        "offers", help="Show referral & passive income offers"
    )
    offers_parser.add_argument(
        "--category",
        "-c",
        dest="offer_category",
        default=None,
        choices=["bandwidth", "compute", "survey", "other"],
        help="Filter by offer category",
    )

    dashboard_parser = sub.add_parser(
        "dashboard", help="Start the web dashboard API server"
    )
    dashboard_parser.add_argument(
        "--port",
        type=int,
        default=8088,
        help="Port for the dashboard API server (default: 8088)",
    )

    profile_parser = sub.add_parser("profile", help="Manage configuration profiles")
    profile_parser.add_argument(
        "profile_action",
        nargs="?",
        default=None,
        choices=["create", "switch", "delete"],
        help="Action: create/switch/delete a named profile. Omit to list profiles.",
    )
    profile_parser.add_argument(
        "profile_name",
        nargs="?",
        default=None,
        help="Profile name (e.g. 'home', 'vps')",
    )

    notify_parser = sub.add_parser("notify", help="Notification status and testing")
    notify_sub = notify_parser.add_subparsers(dest="notify_action")
    notify_sub.add_parser("test", help="Send a test notification")

    dns_parser = sub.add_parser("dns", help="View or configure container DNS")
    dns_sub = dns_parser.add_subparsers(dest="dns_action")
    dns_set = dns_sub.add_parser("set", help="Set DNS mode and servers")
    dns_set.add_argument(
        "mode",
        choices=["default", "custom"],
        help="DNS mode: 'default' uses host DNS, 'custom' injects specified servers",
    )
    dns_set.add_argument(
        "--servers",
        default=None,
        help="Comma-separated DNS servers (e.g. '1.1.1.1,8.8.8.8'). Only used with 'custom' mode.",
    )

    return parser


# ---------------------------------------------------------------------------
# Logging bootstrap
# ---------------------------------------------------------------------------

_SUBCOMMAND_DISPATCH = {
    "setup": _cmd_setup,
    "start": _cmd_start,
    "stop": _cmd_stop,
    "status": _cmd_status,
    "generate": _cmd_generate,
    "links": _cmd_links,
    "reset": _cmd_reset,
    "proxy": _cmd_proxy,
    "backup": _cmd_backup,
    "restore": _cmd_restore,
    "update": _cmd_update,
    "config": _cmd_config,
    "limit": _cmd_limit,
    "ip": _cmd_ip,
    "info": _cmd_info,
    "dns": _cmd_dns,
    "notify": _cmd_notify,
    "apps": _cmd_apps,
    "validate": _cmd_validate,
    "app": _cmd_app,
    "offers": _cmd_offers,
    "dashboard": _cmd_dashboard,
    "profile": _cmd_profile,
}


class _CredentialScrubFilter(logging.Filter):
    """Redact common credential patterns before they reach log handlers."""

    import re as _re

    _PATTERNS = [
        _re.compile(
            r"(?i)(password|passwd|pwd|secret|token|apikey|api_key)\s*[:=]\s*\S+"
        ),
        _re.compile(r"(?i)(bearer\s+)\S+"),
        _re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    ]
    _REDACTED = "***REDACTED***"

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pat in self._PATTERNS:
            msg = pat.sub(self._REDACTED, msg)
        record.msg = msg
        record.args = None
        return True


def _setup_logging(args: argparse.Namespace) -> None:
    """Configure rotating file handler + stderr console handler from parsed args.

    - File handler: all levels, includes module name for per-module filtering
    - Console handler: WARNING+ only (keeps terminal clean for CLI output)
    - Credential scrubbing filter on root logger
    """
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    os.makedirs(args.log_dir, exist_ok=True)
    log_file_path = os.path.join(args.log_dir, args.log_file)

    # Rotating file handler — captures everything at the configured level
    rotating_handler = RotatingFileHandler(
        log_file_path, maxBytes=1 * 1024 * 1024, backupCount=3
    )
    rotating_handler.setLevel(log_level)

    # Use JSON formatter for file output, plain text for console
    from money4band.structured_logging import JSONFormatter

    rotating_handler.setFormatter(JSONFormatter())

    # Console (stderr) handler — only WARNING+ to avoid polluting CLI output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    )
    console_handler.setLevel(logging.WARNING)

    logging.basicConfig(level=log_level, handlers=[rotating_handler, console_handler])

    # Attach credential scrubbing filter to root logger
    logging.getLogger().addFilter(_CredentialScrubFilter())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    locale.setlocale(locale.LC_ALL, "C")
    parser = _build_parser()
    args = parser.parse_args()

    _setup_logging(args)

    from money4band.structured_logging import new_correlation_id

    cid = new_correlation_id()

    script_name = (
        os.path.basename(__file__)
        if not getattr(sys, "frozen", False)
        else "Money4Band"
    )
    logger.info("Starting %s [%s] command=%s", script_name, cid, args.command or "menu")

    handler = _SUBCOMMAND_DISPATCH.get(args.command)
    if handler:
        handler(args)
    else:
        # No subcommand → show update banner, then launch interactive menu
        try:
            m4b_config_path = os.path.join(args.config_dir, args.config_m4b_file)
            if os.path.isfile(m4b_config_path):
                m4b_config = loader.load_json_config(m4b_config_path)
                show_update_banner(m4b_config)
        except Exception:
            pass  # Best-effort — don't block startup
        _cmd_menu(args)


if __name__ == "__main__":
    main()
