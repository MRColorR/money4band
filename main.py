from __future__ import annotations

import argparse
import atexit
import locale
import logging
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from logging.handlers import RotatingFileHandler

from colorama import Fore, Style, just_fix_windows_console

from money4band.core import dumper, loader
from money4band.core.backup import (
    cleanup_backups,
    create_backup,
    list_backups,
    restore_backup,
)
from money4band.core.crypto import ensure_config_encrypted
from money4band.core.reset import main as reset_main
from money4band.system import detector
from money4band.ui.cls import cls
from money4band.updater import check_update_available, show_update_banner

logger = logging.getLogger(__name__)


# User state that must never be seeded out of the bundle into config/.
# user-config.json there holds credentials encrypted with the *building*
# machine's master.key: a copy baked into the binary is unreadable on any
# other machine (Fernet InvalidToken on first run) and leaks the
# builder's data. The real config/user-config.json is always created from
# template/user-config.json by _ensure_user_config - so this filter must
# NOT be applied when seeding template/, where that file is the
# legitimate placeholder skeleton.
_NEVER_SEED_INTO_CONFIG = ("user-config.json", ".dashboard.pid", ".dashboard.owner")


def _seed_bundled_dir(
    dest: str,
    name: str,
    *,
    refresh: bool = False,
    ignore: tuple[str, ...] = (),
) -> None:
    """Copy a data dir bundled in the frozen binary to *dest*.

    Onefile builds carry ``config/`` and ``template/`` inside the
    executable, but that data must live on disk to survive restarts and
    self-updates.

    With *refresh* the bundled copy always wins - use it for read-only
    reference data (``template/``): a self-update replaces only the
    executable, so a first-run-only copy would pin the templates of the
    version first installed and "Reset config" would restore a stale
    skeleton forever. Without it (``config/``) the directory is seeded
    once and user edits are never clobbered.

    *ignore* holds glob patterns to skip (see
    :data:`_NEVER_SEED_INTO_CONFIG`).
    """
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if not bundle_dir:
        return
    src = os.path.join(bundle_dir, name)
    if not os.path.isdir(src):
        return
    if os.path.isdir(dest) and not refresh:
        return
    import shutil as _shutil

    try:
        _shutil.copytree(
            src,
            dest,
            ignore=_shutil.ignore_patterns(*ignore) if ignore else None,
            dirs_exist_ok=refresh,
        )
    except OSError as exc:  # pragma: no cover - disk issues
        print(f"WARNING: could not seed {name} into {dest}: {exc}", file=sys.stderr)


# Handle PyInstaller frozen executable path resolution
if getattr(sys, "frozen", False):
    # Running as compiled executable (PyInstaller)
    BASE_DIR = os.path.dirname(sys.executable)
    # config/: seed once, never clobber user edits, never carry user state.
    _seed_bundled_dir(
        os.path.join(BASE_DIR, "config"), "config", ignore=_NEVER_SEED_INTO_CONFIG
    )
    # template/: read-only reference data - always refresh so a
    # self-updated binary resets from ITS templates, not v5.0.0's.
    _seed_bundled_dir(os.path.join(BASE_DIR, "template"), "template", refresh=True)
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Change working directory to script location to ensure relative paths work
os.chdir(BASE_DIR)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _resolve_paths(args: argparse.Namespace) -> tuple[str, str, str]:
    """Compute the three config paths from parsed args.

    The catalog envelope lives folded under ``m4b-config.json -> catalog``.
    The ``apps_config_path`` slot is kept for call-site compatibility and
    always aliases the m4b-config path. Callers that need the aggregated
    catalog shape should use
    :func:`money4band.core.loader.load_app_config_with_overlays`.
    """
    m4b_config_path = os.path.join(args.config_dir, args.config_m4b_file)
    apps_config_path = m4b_config_path
    user_config_path = os.path.join(args.config_dir, args.config_usr_file)
    return m4b_config_path, apps_config_path, user_config_path


def _ensure_config_dir(args: argparse.Namespace) -> None:
    """Seed a frozen build's bundled config into a custom --config-dir.

    Startup seeding only populates ``<exe_dir>/config``; a user pointing
    ``--config-dir`` elsewhere would otherwise hit an unhandled
    FileNotFoundError on m4b-config.json.
    """
    config_dir = getattr(args, "config_dir", "")
    if not config_dir or os.path.isdir(config_dir):
        return
    _seed_bundled_dir(config_dir, "config", ignore=_NEVER_SEED_INTO_CONFIG)


def _ensure_user_config(args: argparse.Namespace, user_config_path: str) -> None:
    """Create user config from template if missing, then encrypt if needed.

    Also detects template-default configs (all placeholder values) and
    prompts the user to run setup.
    """
    _ensure_config_dir(args)
    if not os.path.exists(user_config_path):
        logger.info("User config not found. Resetting from template...")
        reset_main(
            app_config_path=None,
            m4b_config_path=None,
            user_config_path=user_config_path,
            src_path=args.template_user_config_path,
            dest_path=user_config_path,
        )
        # Auto-set nickname from OS account so the greeting works immediately.
        from money4band.ui.banner import ensure_nickname

        try:
            cfg = loader.load_json_config(user_config_path)
            ensure_nickname(cfg)
            dumper.write_json(cfg, user_config_path)
        except Exception:  # noqa: BLE001
            pass  # best-effort - setup wizard will fix it
    # The template ships an EMPTY resource_limits map, and the compose
    # file references ${APP_CPU_LIMIT_*}/${APP_MEM_*} unconditionally.
    # Without this backfill a CLI-only user (wizard -> stack start, never
    # opening the interactive menu that used to compute them) generated a
    # .env with no limit vars and docker compose failed to interpolate
    # ("strconv.ParseFloat: parsing \"\"") on every start.
    try:
        cfg = loader.load_json_config(user_config_path)
        if not cfg.get("resource_limits"):
            m4b_cfg = loader.load_json_config(
                os.path.join(args.config_dir, args.config_m4b_file)
            )
            detector.calculate_resource_limits(user_config_path, m4b_config=m4b_cfg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not backfill resource limits: %s", exc)
    ensure_config_encrypted(user_config_path)
    register_encryption_hooks(user_config_path)


def _has_template_defaults(user_config_path: str) -> bool:
    """Return True if the user config still needs initial setup.

    ``settings.setup_completed`` is the single source of truth: the
    template ships it ``false`` and the wizard only flips it after every
    step succeeds (money4band/apps/setup.py). Deliberately NOT inferred
    from "some app is enabled" - the wizard enables apps before it
    finishes, so an interrupted run would look complete and the stack
    would start with placeholder credentials. The old placeholder scan
    is gone too: it misfired on legitimate secrets starting with "your".
    """
    try:
        cfg = loader.load_json_config(user_config_path)
    except Exception:
        return False
    return not cfg.get("settings", {}).get("setup_completed", False)


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


def _stop_dashboard_best_effort() -> None:
    """Best-effort stop the background dashboard using its PID file."""
    try:
        from money4band.dashboard.setup import read_dashboard_pid, remove_dashboard_pid

        for path in _encrypt_on_exit_paths:
            config_dir = os.path.dirname(path)
            pid = read_dashboard_pid(config_dir)
            if pid is not None:
                os.kill(pid, signal.SIGTERM)
                remove_dashboard_pid(config_dir)
                break
    except Exception:  # noqa: BLE001
        pass  # best-effort; don't block exit


def _sigterm_handler(signum: int, frame: object) -> None:
    """Handle SIGTERM by stopping dashboard and encrypting configs before exit."""
    _stop_dashboard_best_effort()
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
) -> None:
    """
    Main menu of the script.

    Arguments:
    m4b_config_path -- the path to the m4b config file
    apps_config_path -- the path to the apps config file
    user_config_path -- the path to the user config file
    """
    # Static dispatch table - replaces dynamic load_modules_from_directory()
    from money4band.apps.catalog import main as _fn_app_catalog
    from money4band.apps.setup import main as _fn_setup_apps
    from money4band.core.reset import main as _fn_reset_config
    from money4band.dashboard.menu import main as _fn_dashboard
    from money4band.docker.generator import main as _generator
    from money4band.docker.install import main as _fn_install_docker
    from money4band.docker.start import main as _fn_start_stack
    from money4band.docker.stop import main as _fn_stop_stack
    from money4band.network.proxy_tools import main as _fn_multiproxy_tools
    from money4band.system.info import main as _system_info
    from money4band.system.resource_profiles import main as _fn_resource_profiles
    from money4band.ui.bye import main as _fn_bye

    def _fn_restart_stack(
        app_config_path: str, m4b_config_path: str, user_config_path: str
    ) -> None:
        _fn_stop_stack(app_config_path, m4b_config_path, user_config_path)
        _fn_start_stack(app_config_path, m4b_config_path, user_config_path)

    # Handlers may return a status (e.g. generator returns bool for the
    # CLI); the menu loop ignores it.
    menu_dispatch: dict[str, Callable[[str, str, str], object]] = {
        "system_info": _system_info,
        "fn_app_catalog": _fn_app_catalog,
        "fn_install_docker": _fn_install_docker,
        "fn_setupApps": _fn_setup_apps,
        "fn_startStack": _fn_start_stack,
        "fn_stopStack": _fn_stop_stack,
        "fn_restartStack": _fn_restart_stack,
        "fn_reset_config": _fn_reset_config,
        "generator": _generator,
        "fn_dashboard": _fn_dashboard,
        "fn_multiproxy_tools": _fn_multiproxy_tools,
        "fn_resource_profiles": _fn_resource_profiles,
        "fn_bye": _fn_bye,
    }
    try:
        logger.debug("Initializing colorama")
        just_fix_windows_console()
        logger.info("Colorama initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing colorama: {str(e)}")
        raise

    # Configs are (re)loaded lazily: a full load means a Fernet decrypt of
    # the credentials file, so it happens once up front and again only
    # after a menu action ran (actions mutate config on disk) - not on
    # every keystroke iteration. The hardware stamp is refreshed with the
    # same cadence: an action like "Reset config" restores the template's
    # placeholder device_info, which must be re-detected before the next
    # menu render (detection is local and cheap; the decrypt is not).
    config_stale = True
    m4b_config: dict = {}
    user_config: dict = {}

    while True:
        if config_stale:
            try:
                logger.info("Loading configurations")
                m4b_config = loader.load_json_config(m4b_config_path)
                user_config = loader.load_json_config(user_config_path)
                logger.info("Configurations loaded successfully")

                logger.debug("Detecting OS and architecture")
                system_info = {
                    **detector.detect_os(m4b_config),
                    **detector.detect_architecture(m4b_config),
                }

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
                # calculate_resource_limits writes user-config on disk.
                user_config = loader.load_json_config(user_config_path)
                config_stale = False
            except FileNotFoundError as e:
                logger.error(f"File not found: {str(e)}")
                raise
            except Exception as e:
                logger.error(
                    f"An error occurred while loading configurations: {str(e)}"
                )
                raise

        try:
            logger.debug("Loading main menu")
            sleep_time = m4b_config.get("system", {}).get("sleep_time", 2)

            cls()
            from money4band.ui.banner import ensure_nickname, print_banner

            nickname = ensure_nickname(user_config)
            print_banner(m4b_config, nickname=nickname)
            check_update_available(m4b_config)

            # Dashboard status line below the banner.
            try:
                from money4band.dashboard.setup import print_dashboard_status

                print_dashboard_status(os.path.dirname(user_config_path))
            except Exception:  # noqa: BLE001
                pass
            print()  # blank line before menu
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
                    menu_dispatch["fn_bye"](
                        apps_config_path, m4b_config_path, user_config_path
                    )
                return

            try:
                choice_num = int(choice)
            except ValueError:
                print(
                    f"{Fore.YELLOW}Invalid selection. Choose 1-{len(menu_options)} or a shortcut.{Style.RESET_ALL}"
                )
                time.sleep(sleep_time)
                continue

            if 1 <= choice_num <= len(menu_options):
                function_label = menu_options[choice_num - 1]["label"]
                function_name = menu_options[choice_num - 1]["function"]
                logger.info(
                    f"User selected menu option number {choice_num} that corresponds to menu item {function_label}"
                )
                handler = menu_dispatch.get(function_name)
                if handler:
                    handler(apps_config_path, m4b_config_path, user_config_path)
                    # Menu actions mutate the configs on disk - reload on
                    # the next iteration.
                    config_stale = True
                else:
                    print(
                        f"{Fore.RED}Unknown menu function: {function_name}{Style.RESET_ALL}"
                    )
                    time.sleep(sleep_time)
            else:
                print(
                    f"{Fore.YELLOW}Invalid selection. Choose 1-{len(menu_options)} or a shortcut.{Style.RESET_ALL}"
                )
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Interrupted.{Style.RESET_ALL}")
            # Graceful shutdown - stop dashboard & exit cleanly.
            try:
                menu_dispatch["fn_bye"](
                    apps_config_path, m4b_config_path, user_config_path
                )
            except SystemExit:
                pass
            return
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
            f"\n{Fore.YELLOW}It looks like this is your first run - "
            f"the config still has placeholder values.{Style.RESET_ALL}"
        )
        print("Running the setup wizard to configure your apps...\n")
        _auto_backup(user_config_path)
        from money4band.apps.setup import main as setup_main

        setup_main(apps_config_path, m4b_config_path, user_config_path)

    mainmenu(
        m4b_config_path=m4b_config_path,
        apps_config_path=apps_config_path,
        user_config_path=user_config_path,
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

    from money4band.docker.helper import check_docker_ready

    check_docker_ready()

    from money4band.apps.setup import main as setup_main

    setup_main(
        apps_config_path,
        m4b_config_path,
        user_config_path,
        resume=getattr(args, "resume", False),
    )


def _cmd_stack(args: argparse.Namespace) -> None:
    """Start, stop, or restart the Docker Compose stack."""
    action = getattr(args, "stack_action", None)
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)

    if action in ("start", "restart") and _has_template_defaults(user_config_path):
        just_fix_windows_console()
        print(
            f"{Fore.YELLOW}Warning: Config contains placeholder values. "
            f"Run 'setup' first to configure your apps.{Style.RESET_ALL}"
        )
        return

    if action in ("start", "restart"):
        from money4band.docker.helper import check_docker_ready

        check_docker_ready()

    if action == "start":
        from money4band.docker.start import main as start_main

        if not start_main(apps_config_path, m4b_config_path, user_config_path):
            sys.exit(1)
    elif action == "stop":
        from money4band.docker.stop import main as stop_main

        if not stop_main(apps_config_path, m4b_config_path, user_config_path):
            sys.exit(1)
    elif action == "restart":
        from money4band.docker.start import main as start_main
        from money4band.docker.stop import main as stop_main

        stopped = stop_main(apps_config_path, m4b_config_path, user_config_path)
        started = start_main(apps_config_path, m4b_config_path, user_config_path)
        if not (stopped and started):
            sys.exit(1)
    else:
        just_fix_windows_console()
        print(
            f"Usage: m4b stack {{start|stop|restart}}\n"
            f"  {Fore.CYAN}start{Style.RESET_ALL}    Start the Docker Compose stack\n"
            f"  {Fore.CYAN}stop{Style.RESET_ALL}     Stop the Docker Compose stack\n"
            f"  {Fore.CYAN}restart{Style.RESET_ALL}  Stop then start the stack"
        )


def _cmd_status(args: argparse.Namespace) -> None:
    """Show running containers and health status."""
    from money4band.docker.compose_builder import get_compose_files
    from money4band.docker.helper import get_compose_project_name

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

    # get_compose_project_name falls back to .env.meta, which survives
    # the post-start secure wipe of .env.
    project_name = get_compose_project_name(env_file)
    cmd = ["docker", "compose"]
    if project_name:
        cmd.extend(["-p", project_name])
    if project_name and not os.path.isfile(env_file):
        # .env was securely wiped after a successful start; loading the
        # compose file without it fails ${APP_*} interpolation. `ps` by
        # project name alone lists every container of the project.
        pass
    else:
        for cf in compose_files:
            cmd.extend(["-f", cf])
        # Show ALL services (including profiled infrastructure) for visibility.
        for profile in ("monitoring", "proxy"):
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
    from money4band.docker.monitor import get_stack_health

    statuses = get_stack_health(project_filter=project_name)
    if statuses:
        print(f"{Fore.GREEN}--- Health Summary ---{Style.RESET_ALL}")
        for s in statuses:
            icon = f"{Fore.GREEN}OK" if s.ok else f"{Fore.RED}X"
            health_tag = s.health if s.health != "none" else "no-healthcheck"
            line = f"  {icon} {s.name:<35}{Style.RESET_ALL} {health_tag:<16} restarts={s.restart_count}"
            if s.last_error:
                line += f"  {Fore.YELLOW}err: {s.last_error[:80]}{Style.RESET_ALL}"
            if s.restart_count >= 5:
                line += f"  {Fore.RED}[RESTART LOOP]{Style.RESET_ALL}"
            print(line)
        print()

    # Earnings estimation
    app_config = loader.load_app_config_with_overlays(apps_config_path)
    from money4band.apps.earnings import display_earnings_summary

    display_earnings_summary(app_config)


def _cmd_generate(args: argparse.Namespace) -> None:
    """Regenerate docker-compose.yaml and .env from config."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)

    if getattr(args, "docs", False):
        from money4band.core.loader import load_app_config_with_overlays
        from money4band.readme_generator import update_apps_md, update_readme

        app_config = load_app_config_with_overlays(apps_config_path)
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
    from money4band.docker.generator import main as gen_main

    if not gen_main(apps_config_path, m4b_config_path, user_config_path):
        sys.exit(1)


def _cmd_links(args: argparse.Namespace) -> None:
    """Show app dashboard and referral links."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    from money4band.apps.catalog import main as links_main

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


def _cmd_clean(args: argparse.Namespace) -> None:
    """Prune orphan containers + networks (+ volumes opt-in) for this M4B project."""
    from money4band.docker.clean import clean_orphans
    from money4band.docker.helper import get_compose_project_name

    just_fix_windows_console()
    env_file = os.path.join(BASE_DIR, ".env")
    project = get_compose_project_name(env_file)
    if not project:
        print(
            f"{Fore.RED}Could not resolve COMPOSE_PROJECT_NAME from {env_file} or "
            f".env.meta. Run `m4b generate` first.{Style.RESET_ALL}"
        )
        sys.exit(1)

    include_volumes = bool(getattr(args, "volumes", False))
    dry_run = bool(getattr(args, "dry_run", False))
    skip_confirm = bool(getattr(args, "yes", False))

    label = "dry-run preview" if dry_run else "remove"
    scope = ["stopped containers", "unused networks"]
    if include_volumes:
        scope.append(f"{Fore.RED}volumes (DESTRUCTIVE){Style.RESET_ALL}")
    print(
        f"{Fore.CYAN}m4b clean - project '{project}' - will {label}: "
        f"{', '.join(scope)}{Style.RESET_ALL}"
    )

    if not dry_run and not skip_confirm:
        if include_volumes:
            print(
                f"{Fore.YELLOW}--volumes wipes per-app persistent state "
                f"(e.g. mystnode keystore). This cannot be undone.{Style.RESET_ALL}"
            )
        from money4band.ui.prompt import ask_question_yn

        if not ask_question_yn("Proceed?", default=False):
            print("Aborted.")
            return

    result = clean_orphans(project, include_volumes=include_volumes, dry_run=dry_run)

    print(f"{Fore.GREEN}{'Would remove' if dry_run else 'Removed'}:{Style.RESET_ALL}")
    print(f"  containers: {len(result.containers_removed)}")
    for name in result.containers_removed:
        print(f"    - {name}")
    print(f"  networks  : {len(result.networks_removed)}")
    for name in result.networks_removed:
        print(f"    - {name}")
    if include_volumes:
        print(f"  volumes   : {len(result.volumes_removed)}")
        for name in result.volumes_removed:
            print(f"    - {name}")
    if result.errors:
        print(f"{Fore.RED}Errors ({len(result.errors)}):{Style.RESET_ALL}")
        for err in result.errors:
            print(f"  - {err}")
        sys.exit(2)


def _cmd_proxy(args: argparse.Namespace) -> None:
    """Launch multiproxy tools."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    from money4band.network.proxy_tools import main as proxy_main

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
        f"{Fore.YELLOW}Update available: v{current} -> v{new_version}{Style.RESET_ALL}"
    )

    force = getattr(args, "force", False)
    if not force:
        from money4band.ui.prompt import ask_question_yn

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

    if profile_name not in detector.get_valid_profiles(m4b_config):
        print(
            f"{Fore.RED}Invalid profile '{profile_name}'. "
            f"Choose from: {', '.join(detector.get_valid_profiles(m4b_config))}{Style.RESET_ALL}"
        )
        return

    # Switch profile.
    user_config = loader.load_json_config(user_config_path)
    user_config.setdefault("settings", {})["resource_profile"] = profile_name
    dumper.write_json(user_config, user_config_path)

    # Recalculate limits with the new profile.
    detector.calculate_resource_limits(user_config_path, m4b_config=m4b_config)

    # Regenerate .env so Docker picks up the new limits. The app-config
    # argument must be the overlay-aggregated catalog - passing the raw
    # m4b-config path yields zero app categories and strips every APP_*
    # var from the regenerated .env.
    from money4band.docker.generator import generate_env_file

    app_config = loader.load_app_config_with_overlays(
        m4b_config_path, user_config_path=user_config_path
    )
    generate_env_file(
        m4b_config_path,
        app_config,
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
    from money4band.network.ip_scorer import analyse_ips

    analyse_ips()


def _cmd_info(args: argparse.Namespace) -> None:
    """Display system information dashboard."""
    m4b_config_path, apps_config_path, user_config_path = _resolve_paths(args)
    _ensure_user_config(args, user_config_path)
    just_fix_windows_console()

    m4b_config = loader.load_json_config(m4b_config_path)
    app_config = loader.load_app_config_with_overlays(apps_config_path)
    user_config = loader.load_json_config(user_config_path)

    # Refresh detected OS/arch before displaying: the template ships
    # placeholder device_info (Linux/amd64), so a fresh install would show
    # the wrong platform until the interactive menu ran once.
    try:
        system_info = {
            **detector.detect_os(m4b_config),
            **detector.detect_architecture(m4b_config),
        }
        device_info = user_config.setdefault("device_info", {})
        device_info["os_type"] = system_info.get("os_type")
        device_info["detected_architecture"] = system_info.get("arch")
        device_info["detected_docker_arch"] = system_info.get("dkarch")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not refresh detected system info: %s", exc)

    from money4band.system.info import show_system_info

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

    app_config = loader.load_app_config_with_overlays(apps_config_path)

    app_name = getattr(args, "app_name", None)
    if app_name:
        from money4band.apps.info import show_app_detail

        if not show_app_detail(app_config, app_name):
            sys.exit(1)
    else:
        from money4band.apps.info import list_apps

        category = getattr(args, "category", None)
        list_apps(app_config, category_filter=category)


def _cmd_validate(args: argparse.Namespace) -> None:
    """Run Docker image security checks."""
    _, apps_config_path, _ = _resolve_paths(args)

    app_config = loader.load_app_config_with_overlays(apps_config_path)

    from money4band.docker.image_security import validate_images

    skip_cves = getattr(args, "skip_cves", False)
    validate_images(app_config, run_cves=not skip_cves)


def _cmd_app(args: argparse.Namespace) -> None:
    """App plugin management - add or validate community apps."""
    action = getattr(args, "app_action", None)
    config_dir = getattr(args, "config_dir", os.path.join(BASE_DIR, "config"))
    apps_d_dir = os.path.join(config_dir, "apps.d")

    if action == "add":
        from money4band.apps.wizard import run_app_wizard

        run_app_wizard(apps_d_dir)
    elif action == "validate":
        from money4band.apps.schema import load_community_apps, validate_app_entry

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
                print(f"{Fore.RED}X {name}:{Style.RESET_ALL}")
                for e in errors:
                    print(f"    {e}")
            else:
                print(f"{Fore.GREEN}OK {name}{Style.RESET_ALL}")
        if all_ok:
            print(
                f"\n{Fore.GREEN}All {len(entries)} community app(s) valid.{Style.RESET_ALL}"
            )
    else:
        print("Usage: m4b app {add,validate}")
        print("  add       Interactive wizard to add a new community app")
        print("  validate  Check all apps.d/ files against the schema")


def _cmd_dashboard(args: argparse.Namespace) -> None:
    """Manage the web dashboard & API server."""
    from money4band.dashboard.cli import handle_dashboard_action

    handle_dashboard_action(
        action=getattr(args, "dashboard_action", None),
        config_dir=getattr(args, "config_dir", os.path.join(BASE_DIR, "config")),
        base_dir=BASE_DIR,
        host=getattr(args, "host", "127.0.0.1"),
        port=getattr(args, "port", 8088),
        background=getattr(args, "background", False),
    )


def _cmd_catalog(args: argparse.Namespace) -> None:
    """Manage catalog sources (local & remote) and category flags."""
    from money4band.apps.catalog_cli import handle_catalog_action

    m4b_config_path, _apps, _user = _resolve_paths(args)
    action = getattr(args, "catalog_action", None)
    rc = handle_catalog_action(action, args, m4b_config_path)
    if rc:
        raise SystemExit(rc)


def _cmd_profile(args: argparse.Namespace) -> None:
    """Manage configuration profiles."""
    _, _, user_config_path = _resolve_paths(args)
    config_dir = getattr(args, "config_dir", os.path.join(BASE_DIR, "config"))
    just_fix_windows_console()

    action = getattr(args, "profile_action", None)
    name = getattr(args, "profile_name", None)

    from money4band.core.profiles import (
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
    m4b_config_path, _, user_config_path = _resolve_paths(args)
    just_fix_windows_console()

    dns_action = getattr(args, "dns_action", None)

    if dns_action == "list":
        from money4band.system.info import show_dns_presets

        m4b_config = loader.load_json_config(m4b_config_path)
        user_config = loader.load_json_config(user_config_path)
        show_dns_presets(m4b_config, user_config)
    elif dns_action == "set":
        mode = args.mode
        servers = (
            [s.strip() for s in args.servers.split(",") if s.strip()]
            if getattr(args, "servers", None)
            else None
        )
        from money4band.system.info import set_dns_mode

        set_dns_mode(m4b_config_path, user_config_path, mode, servers)
        print(f"{Fore.GREEN}DNS mode set to '{mode}'.{Style.RESET_ALL}")
        if servers:
            print(f"  Servers: {', '.join(servers)}")
        elif mode not in ("default", "custom"):
            from money4band.system.info import get_dns_presets

            presets = get_dns_presets(loader.load_json_config(m4b_config_path))
            if mode in presets:
                print(f"  Servers: {', '.join(presets[mode])}")
        print(f"{Fore.YELLOW}Run 'generate' to rebuild compose files.{Style.RESET_ALL}")
    else:
        user_config = loader.load_json_config(user_config_path)
        from money4band.system.info import show_dns_status

        show_dns_status(user_config)


def _cmd_config(args: argparse.Namespace) -> None:
    """View or edit encrypted user config."""
    _, _, user_config_path = _resolve_paths(args)
    action = getattr(args, "config_action", None)

    if action == "view":
        from money4band.core.viewer import view_masked

        view_masked(user_config_path)
    elif action == "edit":
        from money4band.core.viewer import edit_config

        register_encryption_hooks(user_config_path)
        edit_config(user_config_path)
    elif action == "migrate-data-dir":
        _cmd_config_migrate_data_dir(args)
    else:
        just_fix_windows_console()
        print(
            f"{Fore.YELLOW}Usage: m4b config {{view,edit,migrate-data-dir}}{Style.RESET_ALL}"
        )


def _cmd_config_migrate_data_dir(args: argparse.Namespace) -> None:
    """Handle `m4b config migrate-data-dir`."""
    from money4band.core.paths import migrate_data_dir

    just_fix_windows_console()
    try:
        result = migrate_data_dir(
            remove_source=bool(getattr(args, "remove_source", False)),
            force=bool(getattr(args, "force", False)),
        )
    except FileNotFoundError as exc:
        print(f"{Fore.YELLOW}{exc}{Style.RESET_ALL}")
        return
    except (FileExistsError, RuntimeError, ValueError) as exc:
        print(f"{Fore.RED}Migration aborted: {exc}{Style.RESET_ALL}")
        sys.exit(1)

    print(f"{Fore.GREEN}Migrated data dir:{Style.RESET_ALL}")
    print(f"  source : {result.source}")
    print(f"  target : {result.target}")
    if result.copied:
        print(f"  copied : {', '.join(result.copied)}")
    if result.skipped:
        print(f"  skipped: {', '.join(result.skipped)} (already identical)")
    if result.removed_source:
        print(f"{Fore.YELLOW}  source wiped per --remove-source.{Style.RESET_ALL}")
    else:
        print(
            f"{Fore.CYAN}  source kept. Re-run with --remove-source after verifying.{Style.RESET_ALL}"
        )


# ---------------------------------------------------------------------------
# CLI parser construction
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with subcommands."""
    script_dir = BASE_DIR

    parser = argparse.ArgumentParser(
        prog="m4b",
        description="Money4Band - Docker orchestrator for passive income apps",
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
    parser.add_argument(
        "--dashboard",
        type=lambda v: v.lower() in ("true", "1", "yes"),
        default=None,
        metavar="true|false",
        help="Auto-start the dashboard in background on startup (default: value from config)",
    )

    # ---- subcommands ----
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="Run the interactive setup wizard").add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Resume a previously interrupted setup, skipping completed steps",
    )
    stack_parser = sub.add_parser(
        "stack", help="Start, stop, or restart the Docker Compose stack"
    )
    stack_sub = stack_parser.add_subparsers(dest="stack_action")
    stack_sub.add_parser("start", help="Start the Docker Compose stack")
    stack_sub.add_parser("stop", help="Stop the Docker Compose stack")
    stack_sub.add_parser("restart", help="Stop then start the Docker Compose stack")
    sub.add_parser("status", help="Show running containers and health")
    gen_parser = sub.add_parser(
        "generate", help="Regenerate docker-compose.yaml and .env"
    )
    gen_parser.add_argument(
        "--docs",
        action="store_true",
        help="Regenerate README.md and docs/APPS.md app tables from m4b-config.json",
    )
    sub.add_parser("links", help="Show app dashboard and referral links")
    sub.add_parser("reset", help="Reset user-config to template defaults")
    clean_parser = sub.add_parser(
        "clean",
        help="Prune orphan M4B containers + unused networks (opt-in volumes)",
    )
    clean_parser.add_argument(
        "--volumes",
        action="store_true",
        default=False,
        help="Also remove project volumes (DESTRUCTIVE - wipes per-app persistent state)",
    )
    clean_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="List what would be removed without actually removing anything",
    )
    clean_parser.add_argument(
        "--yes",
        action="store_true",
        default=False,
        help="Skip confirmation prompt",
    )
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
    migrate_parser = config_sub.add_parser(
        "migrate-data-dir",
        help="Move ~/.m4b/{master.key,session.salt,backups} into <install>/.m4b/",
    )
    migrate_parser.add_argument(
        "--remove-source",
        action="store_true",
        default=False,
        help="After verified copy, wipe migrated entries from ~/.m4b/",
    )
    migrate_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite target files that exist with different content",
    )

    limit_parser = sub.add_parser(
        "limit", help="Show or change the active resource limit profile"
    )
    limit_parser.add_argument(
        "profile",
        nargs="?",
        default=None,
        help="Profile name to switch to (minimal/conservative/standard/performance). Omit to show current.",
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

    dashboard_parser = sub.add_parser(
        "dashboard", help="Manage the web dashboard & API server"
    )
    dash_sub = dashboard_parser.add_subparsers(dest="dashboard_action")

    # m4b dashboard start [--port] [--host] [-b]
    dash_start = dash_sub.add_parser("start", help="Start the dashboard server")
    dash_start.add_argument(
        "--port",
        type=int,
        default=8088,
        help="Port for the dashboard API server (default: 8088)",
    )
    dash_start.add_argument(
        "--host",
        default="127.0.0.1",
        help=(
            "Bind address (default: 127.0.0.1, localhost only). "
            "Use 0.0.0.0 to web-expose (requires API key)"
        ),
    )
    dash_start.add_argument(
        "-b",
        "--background",
        action="store_true",
        default=False,
        help="Run the dashboard in the background and return immediately",
    )

    # m4b dashboard serve (internal): foreground server run, used by
    # spawn_dashboard_background on frozen builds where `python -c` is
    # unavailable (sys.executable is the frozen binary itself).
    dash_serve = dash_sub.add_parser("serve")
    dash_serve.add_argument("--port", type=int, default=8088)
    dash_serve.add_argument("--host", default="127.0.0.1")

    # m4b dashboard stop
    dash_sub.add_parser("stop", help="Stop a background dashboard process")

    # m4b dashboard restart [--port] [--host]
    dash_restart = dash_sub.add_parser(
        "restart", help="Restart a background dashboard process"
    )
    dash_restart.add_argument(
        "--port",
        type=int,
        default=8088,
        help="Port for the dashboard API server (default: 8088)",
    )
    dash_restart.add_argument(
        "--host",
        default="127.0.0.1",
        help=(
            "Bind address (default: 127.0.0.1, localhost only). "
            "Use 0.0.0.0 to web-expose (requires API key)"
        ),
    )

    # m4b dashboard status
    dash_sub.add_parser("status", help="Check whether the dashboard is running")

    # m4b dashboard show-key
    dash_sub.add_parser("show-key", help="Print the dashboard API key")

    # m4b dashboard regenerate-key
    dash_sub.add_parser(
        "regenerate-key", help="Generate a new API key (invalidates the old one)"
    )

    # m4b dashboard enable / disable
    dash_sub.add_parser("enable", help="Enable dashboard auto-start on M4B launch")
    dash_sub.add_parser("disable", help="Disable dashboard auto-start on M4B launch")

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
    dns_sub.add_parser("list", help="List available DNS presets")
    dns_set = dns_sub.add_parser("set", help="Set DNS mode and servers")
    dns_set.add_argument(
        "mode",
        help=(
            "DNS mode: 'default' (host DNS), 'custom' (specify --servers), "
            "or a preset name (e.g. cloudflare, google, quad9). "
            "Run 'dns list' to see all presets."
        ),
    )
    dns_set.add_argument(
        "--servers",
        default=None,
        help="Comma-separated DNS servers (e.g. '1.1.1.1,8.8.8.8'). Only used with 'custom' mode.",
    )

    # m4b catalog: manage catalog sources (local & remote) + category flags.
    catalog_parser = sub.add_parser(
        "catalog",
        help="Manage catalog sources (local & remote) and category flags",
    )
    cat_sub = catalog_parser.add_subparsers(dest="catalog_action")

    cat_sub.add_parser("list", help="List configured catalog sources")
    cat_sub.add_parser(
        "status",
        help="Show per-source cache status (ETag, last fetch, entry count)",
    )

    cat_add = cat_sub.add_parser("add", help="Add a catalog source")
    cat_add.add_argument("name", help="Unique source name (e.g. 'community')")
    cat_add.add_argument(
        "--type",
        required=True,
        choices=["local", "remote"],
        help="Source type: local (filesystem) or remote (HTTPS manifest)",
    )
    cat_add.add_argument("--url", default=None, help="URL (required for --type remote)")
    cat_add.add_argument(
        "--path", default=None, help="Filesystem path (required for --type local)"
    )
    cat_add.add_argument(
        "--default-source",
        dest="default_source",
        default=None,
        help="Default provenance label applied to entries (builtin/community/...)",
    )
    cat_add.add_argument(
        "--cache-path",
        dest="cache_path",
        default=None,
        help="Custom cache dir for remote sources (default: catalog/community)",
    )
    cat_add.add_argument(
        "--timeout", type=float, default=None, help="Remote fetch timeout in seconds"
    )
    cat_add.add_argument(
        "--disabled",
        action="store_true",
        help="Create the source in the disabled state",
    )

    cat_rm = cat_sub.add_parser("remove", help="Remove a catalog source by name")
    cat_rm.add_argument("name")

    cat_en = cat_sub.add_parser("enable", help="Enable a catalog source")
    cat_en.add_argument("name")
    cat_di = cat_sub.add_parser("disable", help="Disable a catalog source")
    cat_di.add_argument("name")

    cat_rf = cat_sub.add_parser(
        "refresh",
        help="Force-refresh remote source caches (clears ETag and re-fetches)",
    )
    cat_rf.add_argument(
        "name", nargs="?", default=None, help="Specific source (omit for all)"
    )

    cat_cat = cat_sub.add_parser("category", help="Toggle or list catalog categories")
    cat_cat_sub = cat_cat.add_subparsers(dest="category_action")
    cat_cat_sub.add_parser("list", help="List categories and their active flag")
    cat_cat_en = cat_cat_sub.add_parser("enable", help="Activate a category")
    cat_cat_en.add_argument("category_name", help="supported | newcomers | deprecated")
    cat_cat_di = cat_cat_sub.add_parser("disable", help="Deactivate a category")
    cat_cat_di.add_argument("category_name", help="supported | newcomers | deprecated")

    return parser


# ---------------------------------------------------------------------------
# Logging bootstrap
# ---------------------------------------------------------------------------

_SUBCOMMAND_DISPATCH = {
    "setup": _cmd_setup,
    "stack": _cmd_stack,
    "status": _cmd_status,
    "generate": _cmd_generate,
    "links": _cmd_links,
    "reset": _cmd_reset,
    "clean": _cmd_clean,
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
    "dashboard": _cmd_dashboard,
    "profile": _cmd_profile,
    "catalog": _cmd_catalog,
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

    # Rotating file handler - captures everything at the configured level
    rotating_handler = RotatingFileHandler(
        log_file_path, maxBytes=1 * 1024 * 1024, backupCount=3
    )
    rotating_handler.setLevel(log_level)

    # Use JSON formatter for file output, plain text for console
    from money4band.structured_logging import JSONFormatter

    rotating_handler.setFormatter(JSONFormatter())

    # Console (stderr) handler - only WARNING+ to avoid polluting CLI output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    )
    console_handler.setLevel(logging.WARNING)

    logging.basicConfig(level=log_level, handlers=[rotating_handler, console_handler])

    # Attach credential scrubbing filter to root logger
    logging.getLogger().addFilter(_CredentialScrubFilter())


# ---------------------------------------------------------------------------
# Dashboard auto-start
# ---------------------------------------------------------------------------


def _handle_dashboard_auto_start(args: argparse.Namespace) -> None:
    """Auto-start (or skip) the background dashboard on M4B launch.

    Behaviour:
    * ``--dashboard true``  -> persist ``enabled=True``, start in background.
    * ``--dashboard false`` -> persist ``enabled=False``, do NOT start.
    * No flag               -> honour the saved ``m4b_dashboard.enabled`` value.

    The ``m4b_dashboard.enabled`` config value is the single source of truth.
    It can also be toggled via ``m4b dashboard enable|disable`` or the
    interactive dashboard menu.

    Auto-start runs **only when entering the interactive menu** (no
    subcommand). One-shot CLI invocations (e.g. ``m4b apps``, ``m4b status``)
    do not spin up a web server they would never use. Auto-started
    dashboards are tagged ``owner=auto`` and bound to this m4b process's
    lifetime via :func:`money4band.dashboard.setup._register_auto_dashboard_cleanup`,
    so they shut down cleanly when the menu exits. For a persistent
    service, use ``m4b dashboard start -b``.

    Skipped entirely when the user invoked the explicit ``dashboard``
    subcommand (that handles its own lifecycle).
    """
    # Don't interfere with the explicit "m4b dashboard" command.
    if getattr(args, "command", None) == "dashboard":
        return

    # Only auto-start for interactive menu sessions, not one-shot CLI.
    # The dashboard is tied to the m4b process lifetime, so spinning it
    # up for a 200ms `m4b status` invocation is pointless noise.
    if getattr(args, "command", None) is not None:
        return

    config_dir = getattr(args, "config_dir", os.path.join(BASE_DIR, "config"))
    user_cfg_path = os.path.join(config_dir, "user-config.json")
    if not os.path.isfile(user_cfg_path):
        # First launch, create user-config from template so the dashboard
        # can honour the default enabled=True on the very first run.
        _ensure_user_config(args, user_cfg_path)
        if not os.path.isfile(user_cfg_path):
            return  # template missing or creation failed

    just_fix_windows_console()

    flag = getattr(args, "dashboard", None)  # True / False / None

    # If flag was explicitly passed, persist it to config.
    if flag is not None:
        from money4band.dashboard.setup import set_dashboard_state

        set_dashboard_state(config_dir, enabled=flag)

    # Read the (possibly just-updated) config to decide whether to start.
    try:
        cfg = loader.load_json_config(user_cfg_path)
    except Exception:  # noqa: BLE001
        return

    dash_cfg = cfg.get("m4b_dashboard", {})
    enabled = dash_cfg.get("enabled", True)

    if not enabled:
        print(
            f"{Fore.CYAN}Dashboard + API auto-start is off.{Style.RESET_ALL}  "
            f"Enable with {Fore.CYAN}m4b --dashboard true{Style.RESET_ALL} "
            f"or start manually with {Fore.CYAN}m4b dashboard{Style.RESET_ALL}."
        )
        return

    # Dashboard is enabled - start it in background.
    from money4band.dashboard.setup import auto_start_dashboard

    auto_start_dashboard(config_dir, BASE_DIR)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _run_cli() -> None:
    try:
        locale.setlocale(locale.LC_ALL, "C")
    except locale.Error:
        pass
    parser = _build_parser()
    args = parser.parse_args()

    _setup_logging(args)

    from money4band.structured_logging import RUN_ID

    script_name = (
        os.path.basename(__file__)
        if not getattr(sys, "frozen", False)
        else "Money4Band"
    )
    logger.info(
        "Starting %s [%s] command=%s", script_name, RUN_ID, args.command or "menu"
    )

    # Handle dashboard auto-start based on --dashboard true|false flag
    # or the persisted enabled state in user-config.json.
    _handle_dashboard_auto_start(args)

    handler = _SUBCOMMAND_DISPATCH.get(args.command)
    if handler:
        handler(args)
    else:
        # No subcommand -> show update banner, then launch interactive menu
        try:
            m4b_config_path = os.path.join(args.config_dir, args.config_m4b_file)
            if os.path.isfile(m4b_config_path):
                m4b_config = loader.load_json_config(m4b_config_path)
                show_update_banner(m4b_config)
        except Exception:
            pass  # Best-effort - don't block startup
        _cmd_menu(args)


def main() -> None:
    """CLI entry point - shared by ``python main.py``, the frozen binary,
    and the ``m4b`` console script (pyproject ``[project.scripts]``).

    The interrupt/EOF handling must live here rather than under the
    ``__main__`` guard: the console script imports and calls ``main()``
    directly, so a guard-only handler would leave ``m4b`` crashing with
    a raw traceback on Ctrl+C or closed stdin.
    """
    try:
        _run_cli()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Interrupted.{Style.RESET_ALL}", file=sys.stderr)
        sys.exit(130)
    except EOFError:
        print(
            f"{Fore.YELLOW}Input closed while waiting for a prompt - exiting. "
            f"Interactive commands need a terminal; scriptable subcommands "
            f"do not prompt.{Style.RESET_ALL}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
