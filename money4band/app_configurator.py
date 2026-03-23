"""App credential collection and configuration for M4B setup wizard."""

from __future__ import annotations

import logging
from typing import Any

from colorama import Fore, Style

from money4band.cls import cls
from money4band.generator import generate_uuid
from money4band.loader import get_active_app_categories, get_category_entries
from money4band.port_manager import assign_app_ports
from money4band.prompt_helper import ask_email, ask_question_yn, ask_string, ask_uuid

logger = logging.getLogger(__name__)


def configure_email(app: dict[str, Any], flag_config: dict[str, Any], config: dict[str, Any]) -> None:
    email = ask_email(
        f"Enter your {app['name'].lower().title()} email:", default=config.get("email")
    )
    config["email"] = email


def configure_password(app: dict[str, Any], flag_config: dict[str, Any], config: dict[str, Any]) -> None:
    print(
        f"Note: If you are using login with Google, remember to set also a password for your {app['name'].lower().title()} account!"
    )
    password = ask_string(
        f"Enter your {app['name'].lower().title()} password:",
        default=config.get("password"),
    )
    config["password"] = password


def configure_apikey(app: dict[str, Any], flag_config: dict[str, Any], config: dict[str, Any]) -> None:
    print(
        f"Find/Generate your APIKey inside your {app['name'].lower().title()} dashboard/profile."
    )
    apikey = ask_string(
        f"Enter your {app['name'].lower().title()} APIKey:",
        default=config.get("apikey"),
    )
    config["apikey"] = apikey


def configure_userid(app: dict[str, Any], flag_config: dict[str, Any], config: dict[str, Any]) -> None:
    print(
        f"Find your UserID inside your {app['name'].lower().title()} dashboard/profile."
    )
    userid = ask_string(
        f"Enter your {app['name'].lower().title()} UserID:",
        default=config.get("userid"),
    )
    config["userid"] = userid


def configure_uuid(app: dict[str, Any], flag_config: dict[str, Any], config: dict[str, Any]) -> None:
    print(f"Starting UUID generation/import for {app['name'].lower().title()}")
    if "length" not in flag_config:
        print(
            f"{Fore.RED}Error: Length not specified for UUID generation/import{Style.RESET_ALL}"
        )
        logger.error("Length not specified for UUID generation/import")
        return

    length = flag_config["length"]
    if not isinstance(length, int) or length <= 0:
        print(
            f"{Fore.RED}Error: Invalid length for UUID generation/import{Style.RESET_ALL}"
        )
        logger.error(f"Invalid length for UUID generation/import: {length}")
        return

    if ask_question_yn(
        f"Do you want to use a previously registered uuid for {app['name'].lower().title()} (current: {Fore.YELLOW}{config.get('uuid', 'not set')}{Fore.GREEN})?"
    ):
        print(
            f"{Fore.GREEN}Please enter the alphanumeric part of the existing uuid for {app['name'].lower().title()}, it should be {length} characters long."
        )
        print(
            "E.g. if existing registered node is sdk-node-b86301656baefekba8917349bdf0f3g4 then enter just b86301656baefekba8917349bdf0f3g4"
        )
        uuid = ask_uuid("Insert uuid:", length, default=config.get("uuid"))
    else:
        uuid = generate_uuid(length)
        print(f"{Fore.GREEN}Generated UUID: {uuid}{Style.RESET_ALL}")
    if "claimURLBase" in flag_config:
        print(
            f"{Fore.BLUE}Save the following instructions/link somewhere to claim/register your {app['name'].lower().title()} "
            f"node/device after completing the setup and starting the apps stack:{Style.RESET_ALL}"
        )
        print(
            f"{Fore.BLUE}{Style.BRIGHT}{flag_config['claimURLBase']}{uuid}{Style.RESET_ALL}"
        )
        try:
            with open(f"claim_instructions_{app['name'].lower()}.txt", "w") as f:
                f.write(f"{flag_config['claimURLBase']}{uuid}")
            print(
                f"{Fore.GREEN}Claim instructions written to claim_instructions_{app['name'].lower()}.txt{Style.RESET_ALL}"
            )
        except Exception as e:
            logger.error(f"Error writing claim instructions to file: {e}")
        input(f"\nPress {Fore.CYAN}Enter{Style.RESET_ALL} to continue...")

    prefix = flag_config.get("prefix", "")
    uuid = f"{prefix}{uuid}"
    config["uuid"] = uuid


def configure_cid(app: dict[str, Any], flag_config: dict[str, Any], config: dict[str, Any]) -> None:
    print(f"Find your CID inside your {app['name'].lower().title()} dashboard/profile.")
    print(
        "Example: For packetstream you can fetch it from your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page, you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)"
    )
    cid = ask_string(
        f"Enter your {app['name'].lower().title()} CID:", default=config.get("cid")
    )
    config["cid"] = cid


def configure_code(app: dict[str, Any], flag_config: dict[str, Any], config: dict[str, Any]) -> None:
    print(
        f"Find your code inside your {app['name'].lower().title()} dashboard/profile."
    )
    code = ask_string(
        f"Enter your {app['name'].lower().title()} code:", default=config.get("code")
    )
    config["code"] = code


def configure_token(app: dict[str, Any], flag_config: dict[str, Any], config: dict[str, Any]) -> None:
    print(
        f"Find your token inside your {app['name'].lower().title()} dashboard/profile."
    )
    token = ask_string(
        f"Enter your {app['name'].lower().title()} token:", default=config.get("token")
    )
    config["token"] = token


def configure_manual(app: dict[str, Any], flag_config: dict[str, Any], config: dict[str, Any]) -> None:
    if "instructions" not in flag_config:
        print(
            f"{Fore.RED}Error: Instructions not provided for manual configuration{Style.RESET_ALL}"
        )
        return
    print(
        f'{Fore.BLUE}"{app["name"].lower().title()} requires further manual configuration.{Style.RESET_ALL}'
    )
    print(f"{Fore.YELLOW}{flag_config['instructions']}{Style.RESET_ALL}")
    print(
        f"{Fore.YELLOW}Please after completing this automated setup check also the app's website for further instructions if there are any.{Style.RESET_ALL}"
    )
    input(f"\nPress {Fore.CYAN}Enter{Style.RESET_ALL} to continue...")


flag_function_mapper = {
    "email": configure_email,
    "password": configure_password,
    "apikey": configure_apikey,
    "userid": configure_userid,
    "uuid": configure_uuid,
    "cid": configure_cid,
    "code": configure_code,
    "token": configure_token,
    "manual": configure_manual,
}


def _configure_apps(
    user_config: dict[str, Any],
    apps: list[dict[str, Any]],
    m4b_config: dict[str, Any],
    app_index_offset: int = 0,
) -> None:
    """
    Configure apps by collecting user inputs.

    This function iterates through the apps, prompts the user for configuration,
    assigns ports if needed, and sets the docker_platform based on the detected
    architecture.

    Args:
        user_config (dict): The user configuration dictionary.
        apps (dict): The app configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
        app_index_offset (int): Starting port_app_index for this category.
            Defaults to 0. Only counts apps WITH ports.
    """
    # Track port_app_index separately - only incremented for apps WITH ports
    port_app_index = app_index_offset

    for app in apps:
        app_name = app["name"].lower()
        config = user_config["apps"].get(app_name, {})
        cls()
        if config.get("enabled"):
            print(f"The app {app_name} is currently enabled.")
            if ask_question_yn("Do you want to disable it?"):
                config["enabled"] = False
                continue
            print(f"Do you want to change the current {app_name} configuration?")
            for key, value in config.items():
                if key != "enabled":
                    print(f"{key}: {value}")
            if not ask_question_yn(""):
                continue

        config["enabled"] = ask_question_yn(
            f"Do you want to run {app['name'].title()}?"
        )
        if not config["enabled"]:
            continue
        print(
            f"{Fore.CYAN}Go to {app['name'].title()} {app['link']} and register{Style.RESET_ALL}"
        )
        print(
            f"{Fore.GREEN}Use CTRL+Click to open links or copy them:{Style.RESET_ALL}"
        )
        input(f"\nPress {Fore.CYAN}Enter{Style.RESET_ALL} to continue...")
        for flag_name, flag_config in app.get("flags", {}).items():
            if flag_name in flag_function_mapper:
                flag_function_mapper[flag_name](app, flag_config, config)
            else:
                logger.error(f"Flag {flag_name} not recognized")

        # Port configuration with unified offset logic (instance 0 = main)
        if "ports" in app["compose_config"]:
            assigned_ports = assign_app_ports(
                app_name, app, config, app_index=port_app_index, instance_number=0
            )
            # Always store as list for consistency
            config["ports"] = assigned_ports
            logger.info(f"Ports for {app_name} set to: {config['ports']}")
            # Only increment port_app_index for apps that actually have ports
            port_app_index += 1

        # Set docker_platform based on detected architecture if not already set
        if "docker_platform" not in config:
            detected_docker_arch = user_config.get("device_info", {}).get(
                "detected_docker_arch", "amd64"
            )
            config["docker_platform"] = f"linux/{detected_docker_arch}"
            logger.info(
                f"Docker platform for {app_name} set to: {config['docker_platform']}"
            )

        # Auto-claim sidecar prompt
        service_def = app.get("service")
        if service_def:
            sidecar_name = service_def["name"]
            description = service_def.get("description", "auto-claim sidecar")
            current = config.get("service_enabled", False)
            status = f"{Fore.GREEN}ON{Style.RESET_ALL}" if current else f"{Fore.RED}OFF{Style.RESET_ALL}"
            print(
                f"\n{Fore.CYAN}{app['name'].title()} has an auto-claim sidecar: "
                f"{sidecar_name}{Style.RESET_ALL}"
            )
            print(f"  {description}  (currently {status})")
            config["service_enabled"] = ask_question_yn(
                f"Enable {sidecar_name} for {app['name'].title()}?"
            )

        user_config["apps"][app_name] = config


def configure_apps(
    user_config: dict[str, Any], app_config: dict[str, Any], m4b_config: dict[str, Any]
) -> None:
    """
    Configure apps from all active categories.

    Args:
        user_config (dict): The user configuration dictionary.
        app_config (dict): The app configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
    """
    offset = 0
    for category in get_active_app_categories(app_config):
        entries = get_category_entries(app_config, category)
        _configure_apps(user_config, entries, m4b_config, app_index_offset=offset)
        # Advance offset by number of apps with ports in this category
        offset += sum(1 for e in entries if "ports" in e.get("compose_config", {}))
