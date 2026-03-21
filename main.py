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

from utils import detector, dumper, loader
from utils.backup import cleanup_backups, create_backup, list_backups, restore_backup
from utils.cls import cls
from utils.crypto import ensure_config_encrypted
from utils.fn_reset_config import main as reset_main
from utils.updater import check_update_available

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


def _resolve_paths(args):
    """Compute the three config paths + utils dir from parsed args."""
    m4b_config_path = os.path.join(args.config_dir, args.config_m4b_file)
    apps_config_path = os.path.join(args.config_dir, args.config_app_file)
    user_config_path = os.path.join(args.config_dir, args.config_usr_file)
    return m4b_config_path, apps_config_path, user_config_path


def _ensure_user_config(args, user_config_path: str) -> None:
    """Create user config from template if missing, then encrypt if needed.

    Also detects template-default configs (all placeholder values) and
    prompts the user to run setup.
    """
    if not os.path.exists(user_config_path):
        logging.info("User config not found. Resetting from template...")
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
    """Return True if the user config still contains placeholder values."""
    try:
        cfg = loader.load_json_config(user_config_path)
    except Exception:
        return False
    apps = cfg.get("apps", {})
    if not apps:
        return True
    # Check if any app has a credential that still starts with "your"
    for app_cfg in apps.values():
        for key, val in app_cfg.items():
            if key == "enabled":
                continue
            if isinstance(val, str) and val.lower().startswith("your"):
                return True
    return False


# ---------------------------------------------------------------------------
# Credential encryption lifecycle (Phase 2.3)
# ---------------------------------------------------------------------------

_encrypt_on_exit_paths: list[str] = []


def _encrypt_on_exit() -> None:
    """Best-effort encrypt all registered config paths."""
    for path in _encrypt_on_exit_paths:
        try:
            ensure_config_encrypted(path)
        except Exception:
            pass  # Best-effort during shutdown


def _sigterm_handler(signum, frame) -> None:
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
    utils_dir_path: str,
) -> None:
    """
    Main menu of the script.

    Arguments:
    m4b_config_path -- the path to the m4b config file
    apps_config_path -- the path to the apps config file
    user_config_path -- the path to the user config file
    utils_dir_path -- the path to the utils directory
    """
    try:
        logging.debug("Initializing colorama")
        just_fix_windows_console()
        logging.info("Colorama initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing colorama: {str(e)}")
        raise

    while True:
        try:
            logging.info("Loading configurations")
            m4b_config = loader.load_json_config(m4b_config_path)
            user_config = loader.load_json_config(user_config_path)
            logging.info("Configurations loaded successfully")
        except FileNotFoundError as e:
            logging.error(f"File not found: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"An error occurred while loading configurations: {str(e)}")
            raise

        try:
            logging.debug("Loading main menu")
            sleep_time = m4b_config.get("system", {}).get("sleep_time", 2)

            logging.debug("Detecting OS and architecture")
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
            logging.info(f"System info and default platform stored: {device_info}")

            logging.debug("Calculating resources limits based on system")
            detector.calculate_resource_limits(
                user_config_path_or_dict=user_config_path
            )

            # Load the functions from the passed tools dir
            logging.debug(f"Loading modules from {utils_dir_path}")
            m4b_tools_modules = loader.load_modules_from_directory(utils_dir_path)
            logging.info(f"Successfully loaded modules from {utils_dir_path}")
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
            print(f"Detected OS type: {system_info.get('os_type')}")
            print(f"Detected architecture: {system_info.get('arch')}")
            print(
                f"Docker {system_info.get('dkarch')} image architecture will be used if the app's image permits it"
            )
            print("----------------------------------------------")
        except Exception as e:
            logging.error(f"An error occurred while setting up the menu: {str(e)}")
            raise
        try:
            logging.debug("Loading menu options from config file")
            menu_options = m4b_config["menu"]

            for i, option in enumerate(menu_options, start=1):
                print(f"{i}. {option['label']}")

            choice = input("Select an option and press Enter: ")

            try:
                choice = int(choice)
            except ValueError:
                print(
                    f"Invalid input. Please select a menu option between 1 and {len(menu_options)}."
                )
                time.sleep(sleep_time)
                continue

            if 1 <= choice <= len(menu_options):
                function_label = menu_options[choice - 1]["label"]
                function_name = menu_options[choice - 1]["function"]
                logging.info(
                    f"User selected menu option number {choice} that corresponds to menu item {function_label}"
                )
                m4b_tools_modules[function_name].main(
                    apps_config_path, m4b_config_path, user_config_path
                )
            else:
                print(
                    f"Invalid input. Please select a menu option between 1 and {len(menu_options)}."
                )
                time.sleep(sleep_time)
        except Exception as e:
            logging.error(f"An error occurred while processing the menu: {str(e)}")
            raise


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _cmd_menu(args) -> None:
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
        from utils.fn_setupApps import main as setup_main

        setup_main(apps_config_path, m4b_config_path, user_config_path)

    mainmenu(
        m4b_config_path=m4b_config_path,
        apps_config_path=apps_config_path,
        user_config_path=user_config_path,
        utils_dir_path=args.utils_dir,
    )


def _auto_backup(user_config_path: str) -> None:
    """Create a backup before destructive operations (best-effort)."""
    try:
        if os.path.isfile(user_config_path):
            create_backup(user_config_path)
            cleanup_backups()
    except Exception:
        logging.warning("Auto-backup failed", exc_info=True)


def _cmd_setup(args) -> None:
    """Run the interactive setup wizard."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    _auto_backup(user_config_path)

    from utils.helper import check_docker_ready

    check_docker_ready()

    from utils.fn_setupApps import main as setup_main

    setup_main(
        apps_config_path,
        m4b_config_path,
        user_config_path,
        resume=getattr(args, "resume", False),
    )


def _cmd_start(args) -> None:
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

    from utils.helper import check_docker_ready

    check_docker_ready()

    from utils.fn_startStack import main as start_main

    start_main(apps_config_path, m4b_config_path, user_config_path)


def _cmd_stop(args) -> None:
    """Stop the Docker Compose stack."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    from utils.fn_stopStack import main as stop_main

    stop_main(apps_config_path, m4b_config_path, user_config_path)


def _cmd_status(args) -> None:
    """Show running containers and health status."""
    from utils.helper import get_compose_project_name

    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)

    compose_file = os.path.join(BASE_DIR, "docker-compose.yaml")
    env_file = os.path.join(BASE_DIR, ".env")

    if not os.path.isfile(compose_file):
        print(
            f"{Fore.YELLOW}No docker-compose.yaml found. "
            f"Run 'setup' or 'generate' first.{Style.RESET_ALL}"
        )
        return

    cmd = ["docker", "compose"]
    if os.path.isfile(env_file):
        project_name = get_compose_project_name(env_file)
        if project_name:
            cmd.extend(["-p", project_name])
    cmd.extend(["-f", compose_file])
    # Show ALL services (including profiled infrastructure) for visibility.
    for profile in ("monitoring", "dashboard", "proxy"):
        cmd.extend(["--profile", profile])
    cmd.extend(["ps", "--format", "table"])

    just_fix_windows_console()
    print(f"{Fore.GREEN}--- M4B Stack Status ---{Style.RESET_ALL}")
    result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"{Fore.RED}Error:{Style.RESET_ALL} {result.stderr.strip()}")


def _cmd_generate(args) -> None:
    """Regenerate docker-compose.yaml and .env from config."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    _auto_backup(user_config_path)
    from utils.generator import main as gen_main

    gen_main(apps_config_path, m4b_config_path, user_config_path)


def _cmd_links(args) -> None:
    """Show app dashboard and referral links."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    from utils.fn_app_catalog import main as links_main

    links_main(apps_config_path, m4b_config_path, user_config_path)


def _cmd_reset(args) -> None:
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


def _cmd_proxy(args) -> None:
    """Launch multiproxy tools."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    from utils.fn_multiproxy_tools import main as proxy_main

    proxy_main(apps_config_path, m4b_config_path, user_config_path)


def _cmd_backup(args) -> None:
    """Create a manual config backup."""
    _, _, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    just_fix_windows_console()
    backup_path = create_backup(user_config_path)
    cleanup_backups()
    print(f"{Fore.GREEN}Backup saved: {backup_path}{Style.RESET_ALL}")


def _cmd_restore(args) -> None:
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

    choice = input("Select backup number to restore (or press Enter to cancel): ")
    if not choice.strip():
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


def _cmd_update(args) -> None:
    """Check for M4B updates."""
    m4b_config_path, _, _ = _resolve_paths(args)
    just_fix_windows_console()
    m4b_config = loader.load_json_config(m4b_config_path)
    check_update_available(m4b_config)


def _cmd_config(args) -> None:
    """View or edit encrypted user config."""
    _, _, user_config_path = _resolve_paths(args)
    action = getattr(args, "config_action", None)

    if action == "view":
        from utils.config_viewer import view_masked

        view_masked(user_config_path)
    elif action == "edit":
        from utils.config_viewer import edit_config

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
        "--utils-dir",
        default=os.path.join(script_dir, "utils"),
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
    sub.add_parser("generate", help="Regenerate docker-compose.yaml and .env")
    sub.add_parser("links", help="Show app dashboard and referral links")
    sub.add_parser("reset", help="Reset user-config to template defaults")
    sub.add_parser("proxy", help="Multi-proxy management tools")
    sub.add_parser("backup", help="Create a config backup")
    sub.add_parser("restore", help="Restore config from a backup")
    sub.add_parser("update", help="Check for M4B updates")

    config_parser = sub.add_parser("config", help="View or edit encrypted config")
    config_sub = config_parser.add_subparsers(dest="config_action")
    config_sub.add_parser("view", help="Display config with masked credentials")
    config_sub.add_parser("edit", help="Edit config in $EDITOR, re-encrypts on save")

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
}


def _setup_logging(args) -> None:
    """Configure rotating file handler from parsed args."""
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    os.makedirs(args.log_dir, exist_ok=True)
    log_file_path = os.path.join(args.log_dir, args.log_file)
    rotating_handler = RotatingFileHandler(
        log_file_path, maxBytes=1 * 1024 * 1024, backupCount=3
    )
    rotating_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    rotating_handler.setLevel(log_level)
    logging.basicConfig(level=log_level, handlers=[rotating_handler])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    locale.setlocale(locale.LC_ALL, "C")
    parser = _build_parser()
    args = parser.parse_args()

    _setup_logging(args)

    script_name = (
        os.path.basename(__file__)
        if not getattr(sys, "frozen", False)
        else "Money4Band"
    )
    logging.info(f"Starting {script_name} script...")

    handler = _SUBCOMMAND_DISPATCH.get(args.command)
    if handler:
        handler(args)
    else:
        # No subcommand → launch interactive menu (backward compatible)
        _cmd_menu(args)


if __name__ == "__main__":
    main()
