from __future__ import annotations

"""Setup wizard facade -- orchestrates app configuration, notifications, dashboard,
watchtower, and multiproxy setup.

This module delegates to focused sub-modules and re-exports their public API
for backward compatibility. New code should import from the sub-modules directly.
"""

import json
import logging
import os
import platform
from collections.abc import Callable
from typing import Any

from colorama import Fore, Style

from money4band.apps.configurator import (  # noqa: F401
    _configure_apps,
    configure_apikey,
    configure_apps,
    configure_cid,
    configure_code,
    configure_email,
    configure_manual,
    configure_password,
    configure_token,
    configure_userid,
    configure_uuid,
    flag_function_mapper,
)
from money4band.core import loader
from money4band.core.dumper import write_json
from money4band.core.progress import (
    clear_progress,
    is_step_done,
    load_progress,
    save_progress,
)
from money4band.docker.generator import (
    assemble_docker_compose,
    generate_device_name,
    generate_env_file,
)
from money4band.docker.watchtower import setup_watchtower  # noqa: F401
from money4band.network.multiproxy import (  # noqa: F401
    calculate_subnet,
    cleanup_multiproxy_instances_dir,
    int_to_ipv4,
    ipv4_to_int,
    regenerate_uuids_for_apps,
    remove_readonly,
    safe_rmtree,
    setup_multiproxy_instances,
)
from money4band.network.networker import validate_proxy_list

# -- Re-exports for backward compatibility ------------------------------------
# External code may import these from money4band.fn_setupApps; keep them available.
from money4band.network.port_manager import (  # noqa: F401
    DEFAULT_PORT_BASE,
    PORT_OFFSET_PER_APP,
    PORT_OFFSET_PER_INSTANCE,
    assign_app_ports,
    collect_assigned_ports,
)
from money4band.ui.notification_setup import (  # noqa: F401
    SUPPORTED_NOTIFICATION_SERVICES,
    setup_notifications,
    validate_notification_url,
)
from money4band.ui.prompt import ask_question_yn
from money4band.ui.summary import generate_setup_summary

logger = logging.getLogger(__name__)
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)

m4b_config_path = os.path.join(parent_dir, "config", "m4b-config.json")

TOTAL_SETUP_STEPS = 6


def _print_step(step: int, description: str) -> None:
    """Display a 'Step X of N' progress indicator to the user."""
    print(
        f"\n{Fore.CYAN}[Step {step}/{TOTAL_SETUP_STEPS}]{Style.RESET_ALL} {description}"
    )


def collect_user_info(user_config: dict[str, Any], m4b_config: dict[str, Any]) -> None:
    """
    Collect user information and update the user configuration.

    Args:
        user_config (dict): The user configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
    """
    from money4band.ui.banner import ensure_nickname

    # Resolve nickname from OS account (replaces placeholder if needed).
    ensure_nickname(user_config)

    # Fetch the existing device name from the configuration, use 'yourDeviceName' as placeholder
    device_name = user_config["device_info"].get("device_name", "yourDeviceName")

    # If the device name is 'yourDeviceName', try using the system's hostname, otherwise generate a random name
    if device_name.lower() == ("yourDeviceName").lower():
        try:
            device_name = platform.node()  # Default to system hostname
        except Exception:
            logger.warning("Unable to retrieve hostname for device name.")
            device_name = generate_device_name(  # Generate random name if hostname is not available
                m4b_config["word_lists"]["adjectives"],
                m4b_config["word_lists"]["animals"],
                use_uuid_suffix=False,
            )

    # Ask the user if they want to keep the current device name or change it
    if ask_question_yn(
        f'The current device name is "{device_name}". Do you want to change it?'
    ):
        # Prompt for new device name or leave blank to auto-generate
        new_device_name = input(
            "Enter your new device name (or leave blank to generate one randomly): "
        ).strip()

        # Generate the device name based on input or generate randomly
        device_name = generate_device_name(
            m4b_config["word_lists"]["adjectives"],
            m4b_config["word_lists"]["animals"],
            device_name=new_device_name,
            use_uuid_suffix=False,
        )

    # Set the final device name in the user configuration
    user_config["device_info"]["device_name"] = device_name
    logger.info(f"Device name set to: {device_name}")


def main(
    app_config_path: str,
    m4b_config_path: str,
    user_config_path: str,
    *,
    resume: bool = False,
) -> None:
    """
    Main function for setting up user configurations.

    Args:
        app_config_path (str): Path to the app configuration file.
        m4b_config_path (str): Path to the m4b configuration file.
        user_config_path (str): Path to the user configuration file.
        resume (bool): If True, skip steps that were completed in a previous run.
    """
    try:
        # app_config_path aliases m4b-config.json where the catalog is folded
        # under the ``catalog`` key. Use the overlay loader so categories and
        # entries are aggregated to top level; a plain load yields no apps.
        app_config = loader.load_app_config_with_overlays(app_config_path)
        user_config = loader.load_json_config(user_config_path)
        m4b_config = loader.load_json_config(m4b_config_path)
        logger.info("Setup apps started")

        # Display M4B header banner
        from colorama import just_fix_windows_console

        from money4band.ui.banner import ensure_nickname, print_banner
        from money4band.ui.cls import cls

        just_fix_windows_console()
        cls()
        nickname = ensure_nickname(user_config)
        print_banner(
            m4b_config,
            nickname=nickname,
            greeting=(
                f"It seems this is your first time running Money4Band. "
                f"Let's get you set up!"
                f"\n\n{Fore.CYAN}=== Setup Wizard ==={Style.RESET_ALL}"
            ),
        )

        progress = load_progress() if resume else {}
        completed: list[int] = list(progress.get("completed_steps", []))

        if resume and completed:
            print(
                f"{Fore.YELLOW}Resuming setup - skipping already-completed "
                f"steps: {completed}{Style.RESET_ALL}"
            )

        def _run_step(
            step: int,
            description: str,
            func: Callable[..., Any],
            *args: Any,
            **kwargs: Any,
        ) -> None:
            """Execute *func* for *step* unless already completed."""
            if is_step_done(progress, step):
                print(
                    f"{Fore.YELLOW}[Step {step}/{TOTAL_SETUP_STEPS}] "
                    f"{description} - skipped (already done){Style.RESET_ALL}"
                )
                return
            _print_step(step, description)
            func(*args, **kwargs)
            completed.append(step)
            save_progress(completed)

        # Step 1: Collect user information
        _run_step(
            1, "Collecting user information", collect_user_info, user_config, m4b_config
        )
        # Step 2: Configure apps
        _run_step(
            2, "Configuring apps", configure_apps, user_config, app_config, m4b_config
        )
        # Step 3: Set up Watchtower auto-updates
        _run_step(
            3, "Setting up Watchtower auto-updates", setup_watchtower, user_config
        )
        # Step 4: Set up notifications
        if not is_step_done(progress, 4):
            _print_step(4, "Setting up notifications")
            if user_config.get("watchtower", {}).get("enabled", True):
                setup_notifications(user_config)
            else:
                user_config.setdefault("notifications", {})["enabled"] = False
                logger.info("Skipping notification setup: Watchtower is disabled.")
            completed.append(4)
            save_progress(completed)
        else:
            print(
                f"{Fore.YELLOW}[Step 4/{TOTAL_SETUP_STEPS}] "
                f"Setting up notifications - skipped (already done){Style.RESET_ALL}"
            )
        # Step 5: Save the user configuration
        _print_step(5, "Saving user configuration")
        write_json(user_config, user_config_path)
        if 5 not in completed:
            completed.append(5)
            save_progress(completed)
        # Step 6: Set up proxy if the user chooses to
        if not is_step_done(progress, 6):
            _print_step(6, "Proxy configuration")
            proxy_setup = ask_question_yn("Do you want to enable (multi)proxy?")
            if proxy_setup:
                logger.info("Multiproxy setup selected")
                print(
                    "Create a proxies.txt file in the same folder and add proxies in the following format: protocol://user:pass@ip:port (one proxy per line)"
                )
                input(f"\nPress {Fore.CYAN}Enter{Style.RESET_ALL} to continue...")
                if not os.path.isfile("proxies.txt"):
                    print(
                        f"{Fore.RED}proxies.txt not found. "
                        f"Create it with one proxy per line and re-run setup.{Style.RESET_ALL}"
                    )
                    logger.error("Setup aborted: proxies.txt not found.")
                    return
                try:
                    with open("proxies.txt", encoding="utf-8") as file:
                        proxies = [line.strip() for line in file if line.strip()]
                except OSError as exc:
                    print(
                        f"{Fore.RED}Failed to read proxies.txt: {exc}{Style.RESET_ALL}"
                    )
                    logger.error("Setup aborted: could not read proxies.txt: %s", exc)
                    return

                # Validate proxy URLs
                validation = validate_proxy_list(
                    proxies, check_connectivity=True, timeout=5.0
                )
                invalid = [r for r in validation if not r["valid"]]
                unreachable = [
                    r for r in validation if r["valid"] and r["reachable"] is False
                ]
                if invalid:
                    print(f"\n{Fore.RED}Invalid proxy URLs:{Style.RESET_ALL}")
                    for r in invalid:
                        print(
                            f"  {Fore.RED}X{Style.RESET_ALL} {r['url']} - {r['reason']}"
                        )
                    print(
                        f"\n{Fore.RED}Fix proxies.txt and re-run setup.{Style.RESET_ALL}"
                    )
                    logger.error("Setup aborted: invalid proxy URLs found.")
                    return
                if unreachable:
                    print(f"\n{Fore.YELLOW}Unreachable proxies:{Style.RESET_ALL}")
                    for r in unreachable:
                        print(
                            f"  {Fore.YELLOW}!{Style.RESET_ALL} {r['url']} - {r['reason']}"
                        )
                    if not ask_question_yn(
                        "Some proxies are unreachable. Continue anyway?", default=False
                    ):
                        logger.info("User aborted setup due to unreachable proxies.")
                        return

                user_config["proxies"]["url"] = proxies.pop(-1)
                user_config["proxies"]["enabled"] = True
                write_json(user_config, user_config_path)
                assemble_docker_compose(
                    m4b_config_path_or_dict=m4b_config,
                    app_config_path_or_dict=app_config,
                    user_config_path_or_dict=user_config,
                    compose_output_path="./docker-compose.yaml",
                    is_main_instance=True,
                )
                generate_env_file(
                    m4b_config_path_or_dict=m4b_config,
                    app_config_path_or_dict=app_config,
                    user_config_path_or_dict=user_config,
                    env_output_path="./.env",
                    is_main_instance=True,
                )
                setup_multiproxy_instances(user_config, app_config, m4b_config, proxies)
                logger.info("Multiproxy instances setup completed")
            else:
                logger.info("Multiproxy setup not selected")
                if user_config["proxies"].get("enabled"):
                    user_config["proxies"]["url"] = ""
                    user_config["proxies"]["enabled"] = False
                    write_json(user_config, user_config_path)
                cleanup_multiproxy_instances_dir()
                # Pass loaded dicts (not paths): app_config holds the
                # overlay-aggregated catalog; reloading the m4b-config path raw
                # would drop all app categories and emit an empty stack.
                assemble_docker_compose(
                    m4b_config,
                    app_config,
                    user_config,
                    compose_output_path="./docker-compose.yaml",
                    is_main_instance=True,
                )
                generate_env_file(
                    m4b_config,
                    app_config,
                    user_config,
                    env_output_path="./.env",
                    is_main_instance=True,
                )
            completed.append(6)
            save_progress(completed)
        else:
            print(
                f"{Fore.YELLOW}[Step 6/{TOTAL_SETUP_STEPS}] "
                f"Proxy configuration - skipped (already done){Style.RESET_ALL}"
            )

        # All steps complete - clean up progress file
        clear_progress()

        # Mark setup as completed so the first-run wizard doesn't re-trigger
        user_config = loader.load_json_config(user_config_path)
        user_config.setdefault("settings", {})["setup_completed"] = True
        write_json(user_config, user_config_path)

        # Generate and display post-setup summary
        generate_setup_summary(user_config, app_config)
        logger.info("Setup completed")
        input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")

    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"An error occurred in main setup apps process: {str(e)}")
        raise
