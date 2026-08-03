from __future__ import annotations

import logging
import os
import time
from typing import Any

from colorama import Fore, Style, just_fix_windows_console

from money4band.core.dumper import write_json
from money4band.core.loader import load_json_config
from money4band.docker.generator import assemble_docker_compose, generate_env_file
from money4band.docker.start import start_all_stacks
from money4band.docker.stop import stop_all_stacks
from money4band.network.networker import validate_proxy_list
from money4band.ui.cls import cls
from money4band.ui.prompt import ask_question_yn

logger = logging.getLogger(__name__)


def toggle_install_limits(
    user_config_path: str = "./config/user-config.json",
    **_kwargs: Any,
) -> None:
    """Toggle the enforce_install_limits flag in user-config.json.

    When enabled, proxy setup respects the per-app install_limit values.
    When disabled, all apps are allowed on every proxy instance regardless
    of the limits defined in the catalog.
    """
    user_config = load_json_config(user_config_path)
    settings = user_config.setdefault("settings", {})
    current = settings.get("enforce_install_limits", True)
    new_value = not current
    settings["enforce_install_limits"] = new_value
    write_json(user_config, user_config_path)

    state_label = (
        f"{Fore.GREEN}ENABLED{Style.RESET_ALL}"
        if new_value
        else f"{Fore.YELLOW}DISABLED{Style.RESET_ALL}"
    )
    print(f"Install-limit enforcement is now {state_label}.")
    if not new_value:
        print(
            f"{Fore.YELLOW}Warning: apps will no longer be capped per instance. "
            f"Some providers may ban accounts that exceed their proxy limits."
            f"{Style.RESET_ALL}"
        )
    logger.info("enforce_install_limits toggled to %s", new_value)
    input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")


def update_multiproxy_instances(
    proxies_file: str = "proxies.txt",
    instances_dir: str = "m4b_proxy_instances",
    user_config_path: str = "./config/user-config.json",
    m4b_config_path: str = "./config/m4b-config.json",
    app_config_path: str = "./config/m4b-config.json",
    sleep_time: int = 3,
) -> None:
    """
    Update multiproxy instances with new proxies from the proxies.txt file.

    Args:
        proxies_file (str): Path to the file containing the list of proxies.
        instances_dir (str): Directory containing the multiproxy instances.
        user_config_path (str): Path to the main user-config file.
        m4b_config_path (str): Path to the main m4b-config file.
        app_config_path (str): Path to the config file holding the folded
            catalog envelope - this aliases the m4b-config file; the
            argument is kept for call-site clarity.
        sleep_time (int): Time to wait between operations.
    """

    # Ask for confirmation using prompt_helper
    if not ask_question_yn(
        "This will update all multiproxy instances with new proxies. Do you want to proceed?",
        default=False,
    ):
        print("Operation canceled.")
        logger.info("User canceled the update of multiproxy instances.")
        input(f"\n  Press {Fore.CYAN}b{Style.RESET_ALL} to go back...")
        return

    # Ensure proxies.txt exists
    if not os.path.isfile(proxies_file):
        logger.error(f"Proxies file '{proxies_file}' not found.")
        print(
            f"{Fore.RED}Proxies file '{proxies_file}' not found. Please create it and add proxies.{Style.RESET_ALL}"
        )
        return

    # Load proxies from file
    with open(proxies_file) as file:
        proxies = [line.strip() for line in file if line.strip()]

    if not proxies:
        logger.error("No proxies found in proxies file.")
        print(
            f"{Fore.RED}No proxies found in proxies file. Please add proxies.{Style.RESET_ALL}"
        )
        return
    # Tell the user how many proxies where found.
    logger.info(f"Found {len(proxies)} proxies in '{proxies_file}'.")
    print(
        f"{Fore.GREEN}Found {len(proxies)} proxies in '{proxies_file}'.{Style.RESET_ALL}"
    )

    # Validate proxy URLs before proceeding
    validation = validate_proxy_list(proxies, check_connectivity=True, timeout=5.0)
    invalid = [r for r in validation if not r["valid"]]
    unreachable = [r for r in validation if r["valid"] and r["reachable"] is False]
    if invalid:
        print(f"\n{Fore.RED}Invalid proxy URLs:{Style.RESET_ALL}")
        for r in invalid:
            print(f"  {Fore.RED}X{Style.RESET_ALL} {r['url']} - {r['reason']}")
        print(
            f"\n{Fore.RED}Fix the invalid proxies before proceeding.{Style.RESET_ALL}"
        )
        return
    if unreachable:
        print(f"\n{Fore.YELLOW}Unreachable proxies:{Style.RESET_ALL}")
        for r in unreachable:
            print(f"  {Fore.YELLOW}!{Style.RESET_ALL} {r['url']} - {r['reason']}")
        if not ask_question_yn(
            "Some proxies are unreachable. Continue anyway?", default=False
        ):
            print("Operation canceled.")
            return

    stop_all_stacks(skip_questions=True)

    try:
        logger.info(f"Updating main instance proxy with {proxies[0]}")
        print(
            f"{Fore.GREEN}Updating main instance proxy with {proxies[0]}{Style.RESET_ALL}"
        )
        user_config = load_json_config(user_config_path)
        old_proxy = user_config.get("proxies", {}).get("url", "None")
        new_proxy = proxies.pop(0)
        user_config["proxies"]["url"] = new_proxy
        user_config["proxies"]["enabled"] = True

        write_json(user_config, user_config_path)

        logger.info(f"Updated main instance proxy URL: {old_proxy} -> {new_proxy}")
        print(
            f"{Fore.GREEN}Updated main instance proxy URL: {old_proxy} -> {new_proxy}{Style.RESET_ALL}"
        )

        # app_config_path aliases m4b-config.json: aggregate it via the
        # overlay loader, or the regenerated compose/.env drop every app.
        from money4band.core.loader import load_app_config_with_overlays

        app_config = load_app_config_with_overlays(
            app_config_path, user_config_path=user_config_path
        )
        assemble_docker_compose(
            m4b_config_path,
            app_config,
            user_config_path,
            compose_output_path="./docker-compose.yaml",
            is_main_instance=True,
        )
        generate_env_file(
            m4b_config_path, app_config, user_config_path, env_output_path="./.env"
        )
    except Exception as e:
        logger.error(f"Failed to update main instance proxy: {str(e)}")
        print(
            f"{Fore.RED}Failed to update main instance proxy: {str(e)}{Style.RESET_ALL}"
        )
        return

    # Iterate over multiproxy instances and update proxies
    if not os.path.isdir(instances_dir):
        os.makedirs(instances_dir, exist_ok=True)

    # Check if there are any instances in the instances directory.
    instances = os.listdir(instances_dir)
    if not instances:
        logger.error(f"No instances found in instances directory '{instances_dir}'.")
        print(
            f"{Fore.RED}No instances found in instances directory '{instances_dir}'. Please setup instances by following the main setup first.{Style.RESET_ALL}"
        )
        return
    # Tell the user how many instances are in the instances directory.
    logger.info(f"Found {len(instances)} instances in '{instances_dir}'.")
    print(
        f"{Fore.GREEN}Found {len(instances)} instances in '{instances_dir}'.{Style.RESET_ALL}"
    )
    # Fewer proxies than instances is not fatal: the surplus instances keep
    # their currently assigned proxy instead of being reassigned.
    if len(proxies) < len(instances):
        logger.warning(
            f"Not enough proxies for all instances. {len(instances)} instances found, {len(proxies)} proxies available."
        )
        print(
            f"{Fore.YELLOW}Not enough proxies for all instances. {len(instances)} instances found, {len(proxies)} proxies available.{Style.RESET_ALL}"
        )
        print(
            f"{Fore.YELLOW}The remaining instances will not be updated.{Style.RESET_ALL}"
        )

    for instance in instances:
        if not proxies:
            logger.warning("No more proxies available to assign.")
            print(
                f"{Fore.YELLOW}No more proxies available to assign. Remaining instances will not be updated.{Style.RESET_ALL}"
            )
            break

        instance_dir = os.path.join(instances_dir, instance)
        instance_user_config_path = os.path.join(instance_dir, "user-config.json")
        instance_m4b_config_path = os.path.join(instance_dir, "m4b-config.json")
        instance_app_config_path = os.path.join(instance_dir, "app-config.json")

        if not os.path.isfile(instance_user_config_path):
            logger.warning(
                f"User config not found for instance '{instance}'. Skipping."
            )
            continue

        # Load user-config for the instance
        instance_user_config = load_json_config(instance_user_config_path)

        # Update proxy URL
        old_proxy = instance_user_config.get("proxies", {}).get("url", "None")
        new_proxy = proxies.pop(0)
        instance_user_config["proxies"]["url"] = new_proxy
        instance_user_config["proxies"]["enabled"] = True

        # Write updated user-config
        write_json(instance_user_config, instance_user_config_path)

        # Log the update
        logger.info(
            f"Updated instance '{instance}' proxy URL: {old_proxy} -> {new_proxy}"
        )
        print(
            f"{Fore.GREEN}Updated instance '{instance}' proxy URL: {old_proxy} -> {new_proxy}{Style.RESET_ALL}"
        )

        # Regenerate docker-compose.yaml and .env files for the instance
        assemble_docker_compose(
            instance_m4b_config_path,
            instance_app_config_path,
            instance_user_config_path,
            compose_output_path=os.path.join(instance_dir, "docker-compose.yaml"),
        )
        generate_env_file(
            instance_m4b_config_path,
            instance_app_config_path,
            instance_user_config_path,
            env_output_path=os.path.join(instance_dir, ".env"),
        )

        time.sleep(sleep_time)

    # Start all stacks
    start_all_stacks(skip_questions=True)

    print(f"{Fore.GREEN}Multiproxy instances updated successfully.{Style.RESET_ALL}")
    logger.info("Multiproxy instances updated successfully.")


def _install_limits_status_label(user_config_path: str) -> str:
    """Return a coloured ON/OFF label for the current enforce_install_limits state."""
    try:
        cfg = load_json_config(user_config_path)
        enabled = cfg.get("settings", {}).get("enforce_install_limits", True)
    except Exception:
        enabled = True
    if enabled:
        return f"{Fore.GREEN}ON{Style.RESET_ALL}"
    return f"{Fore.YELLOW}OFF{Style.RESET_ALL}"


def submenu_multiproxy_tools(
    user_config_path: str = "./config/user-config.json",
) -> list[dict[str, str]]:
    status = _install_limits_status_label(user_config_path)
    return [
        {
            "label": "Update Proxies for Multiproxy Instances",
            "function": "update_multiproxy_instances",
        },
        {
            "label": f"Toggle Install-Limit Enforcement [{status}]",
            "function": "toggle_install_limits",
        },
    ]


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Multiproxy tools function to handle operations like updating multiproxy instances.

    Args:
        app_config_path (str): Path to the app-config file.
        m4b_config_path (str): Path to the m4b-config file.
        user_config_path (str): Path to the user-config file.
    """
    logger.info("Starting multiproxy tools...")
    just_fix_windows_console()

    # Load sleep time from configuration
    m4b_config = load_json_config(m4b_config_path)
    sleep_time = m4b_config.get("system", {}).get("sleep_time", 3)

    while True:
        menu_options = submenu_multiproxy_tools(user_config_path)
        cls()
        print(f"{Fore.YELLOW}\nMultiproxy Tools Menu:{Style.RESET_ALL}")
        print(
            f"{Fore.YELLOW}----------------------------------------------{Style.RESET_ALL}"
        )

        for i, option in enumerate(menu_options, start=1):
            print(f"{i}. {option['label']}")
        print(f"\n  {Fore.CYAN}b{Style.RESET_ALL} Back")

        choice = input("Select: ").strip().lower()

        if choice == "b":
            break

        try:
            choice_index = int(choice)
        except ValueError:
            print(
                f"{Fore.YELLOW}Invalid selection. Choose 1-{len(menu_options)} or a shortcut.{Style.RESET_ALL}"
            )
            time.sleep(sleep_time)
            continue

        if 1 <= choice_index <= len(menu_options):
            selected_option = menu_options[choice_index - 1]
            logger.info(f"User selected menu option: {selected_option['label']}")

            globals()[selected_option["function"]](
                app_config_path=app_config_path,
                m4b_config_path=m4b_config_path,
                user_config_path=user_config_path,
            )
        else:
            print(
                f"{Fore.YELLOW}Invalid selection. Choose 1-{len(menu_options)} or a shortcut.{Style.RESET_ALL}"
            )
            time.sleep(sleep_time)

    logger.info("Multiproxy tools completed.")
