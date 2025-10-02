import argparse
import getpass
import json
import logging
import os
import platform
import re
import shutil
import stat
import sys
import time
from copy import deepcopy
from typing import Any

from colorama import Fore, Style

from utils import loader
from utils.cls import cls
from utils.dumper import write_json
from utils.fn_stopStack import stop_all_stacks
from utils.generator import (
    assemble_docker_compose,
    generate_device_name,
    generate_env_file,
    generate_uuid,
)
from utils.networker import find_next_available_port
from utils.prompt_helper import ask_email, ask_question_yn, ask_string, ask_uuid

# Ensure the parent directory is in the sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


# Global config loading and global variables
m4b_config_path = os.path.join(parent_dir, "config", "m4b-config.json")
try:
    m4b_config = loader.load_json_config(m4b_config_path)
except FileNotFoundError:
    m4b_config = {}  # Fallback to empty config if not found
    logging.warning("Configuration file not found. Using default values.")

# Set global sleep time
sleep_time = m4b_config.get("system", {}).get(
    "sleep_time", 3
)  # Default to 3 seconds if not specified

# Port assignment constants
DEFAULT_PORT_BASE = 50000  # Base port for default assignments
PORT_OFFSET_PER_APP = 100  # Port offset multiplier per app
PORT_OFFSET_PER_INSTANCE = 10  # Port offset for multiproxy instances


def remove_readonly(func, path, excinfo):
    """
    Error handler for Windows readonly file removal.

    Args:
        func: The function that raised the exception
        path: The path to the file/directory
        excinfo: Exception information
    """
    # Clear the readonly bit and reattempt the removal
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        logging.warning(f"Could not remove {path}: {str(e)}")


def safe_rmtree(directory: str) -> bool:
    """
    Safely remove a directory tree, handling Windows permission issues.

    Args:
        directory (str): Path to the directory to remove

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if platform.system().lower() == "windows":
            # On Windows, use onerror callback to handle readonly files
            shutil.rmtree(directory, onerror=remove_readonly)
        else:
            shutil.rmtree(directory)
        logging.info(f"Successfully removed directory: {directory}")
        return True
    except PermissionError as e:
        logging.error(f"Permission denied when removing {directory}: {str(e)}")
        print(
            f"{Fore.RED}Permission denied when removing {directory}. Please ensure no files are in use and you have proper permissions.{Style.RESET_ALL}"
        )
        return False
    except Exception as e:
        logging.error(f"Failed to remove directory {directory}: {str(e)}")
        print(
            f"{Fore.RED}Failed to remove directory {directory}: {str(e)}{Style.RESET_ALL}"
        )
        return False


def ipv4_to_int(ip_address: str) -> int:
    """
    Convert an IPv4 address string to an integer representation.

    Args:
        ip_address (str): IPv4 address in dotted decimal notation (e.g., "192.168.1.0").

    Returns:
        int: Integer representation of the IP address.
    """
    octets = ip_address.split(".")
    return sum(int(octet) << (8 * (3 - i)) for i, octet in enumerate(octets))


def int_to_ipv4(ip_int: int) -> str:
    """
    Convert an integer to an IPv4 address string.

    Args:
        ip_int (int): Integer representation of an IP address.

    Returns:
        str: IPv4 address in dotted decimal notation (e.g., "192.168.1.0").
    """
    return ".".join(str((ip_int >> (8 * (3 - i))) & 0xFF) for i in range(4))


def calculate_subnet(base_subnet: str, base_netmask: int, offset: int) -> str:
    """
    Calculate a new subnet by applying an offset to a base subnet.

    This function converts the base subnet to an integer, applies a subnet mask,
    adds an offset, and converts back to dotted decimal notation. It's used to
    generate unique subnets for multiple proxy instances.

    Args:
        base_subnet (str): Base subnet in dotted decimal notation (e.g., "172.18.0.0").
        base_netmask (int): Network mask in CIDR notation (e.g., 16 for /16).
        offset (int): Offset to add to the base subnet (typically instance number).

    Returns:
        str: New subnet address in dotted decimal notation.

    Example:
        >>> calculate_subnet("172.18.0.0", 16, 1)
        "172.19.0.0"
    """
    # Convert base subnet to integer
    base_subnet_int = ipv4_to_int(base_subnet)

    # Apply subnet mask to ensure base is correctly aligned
    subnet_mask = (pow(2, base_netmask) - 1) << (32 - base_netmask)
    base_subnet_int = subnet_mask & base_subnet_int

    # Add offset to generate new subnet
    new_subnet_int = base_subnet_int + (offset << (32 - base_netmask))

    # Convert back to dotted decimal notation
    return int_to_ipv4(new_subnet_int)


def assign_app_ports(app_name: str, app: dict, config: dict) -> list[int]:
    """
    Assign available ports for an app based on its configuration.

    Args:
        app_name (str): Name of the app
        app (dict): App configuration containing compose_config
        config (dict): User configuration for the app

    Returns:
        list[int]: List of assigned available ports
    """
    port_count = len(app["compose_config"]["ports"])
    assigned_ports = []
    default_ports = [DEFAULT_PORT_BASE + j for j in range(port_count)]

    for i in range(port_count):
        starting_port = config.get("ports", default_ports)
        # Determine the base port for this index
        if isinstance(starting_port, list):
            port_base = (
                starting_port[i] if i < len(starting_port) else DEFAULT_PORT_BASE + i
            )
        else:
            port_base = DEFAULT_PORT_BASE + i

        # Find next available port and assign it
        available_port = find_next_available_port(port_base)
        assigned_ports.append(available_port)

        # Log the port assignment
        port_placeholder = (
            app["compose_config"]["ports"][i]
            if "ports" in app["compose_config"]
            and i < len(app["compose_config"]["ports"])
            else f"port_{i + 1}"
        )
        logging.info(f"Port {port_placeholder} for {app_name} set to: {available_port}")

    return assigned_ports


def configure_email(app: dict, flag_config: dict, config: dict):
    email = ask_email(
        f"Enter your {app['name'].lower().title()} email:", default=config.get("email")
    )
    config["email"] = email


def configure_password(app: dict, flag_config: dict, config: dict):
    print(
        f"Note: If you are using login with Google, remember to set also a password for your {app['name'].lower().title()} account!"
    )
    password = ask_string(
        f"Enter your {app['name'].lower().title()} password:",
        default=config.get("password"),
    )
    config["password"] = password


def configure_apikey(app: dict, flag_config: dict, config: dict):
    print(
        f"Find/Generate your APIKey inside your {app['name'].lower().title()} dashboard/profile."
    )
    apikey = ask_string(
        f"Enter your {app['name'].lower().title()} APIKey:",
        default=config.get("apikey"),
    )
    config["apikey"] = apikey


def configure_userid(app: dict, flag_config: dict, config: dict):
    print(
        f"Find your UserID inside your {app['name'].lower().title()} dashboard/profile."
    )
    userid = ask_string(
        f"Enter your {app['name'].lower().title()} UserID:",
        default=config.get("userid"),
    )
    config["userid"] = userid


def configure_uuid(app: dict, flag_config: dict, config: dict):
    print(f"Starting UUID generation/import for {app['name'].lower().title()}")
    if "length" not in flag_config:
        print(
            f"{Fore.RED}Error: Length not specified for UUID generation/import{Style.RESET_ALL}"
        )
        logging.error("Length not specified for UUID generation/import")
        return

    length = flag_config["length"]
    if not isinstance(length, int) or length <= 0:
        print(
            f"{Fore.RED}Error: Invalid length for UUID generation/import{Style.RESET_ALL}"
        )
        logging.error(f"Invalid length for UUID generation/import: {length}")
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
            logging.error(f"Error writing claim instructions to file: {e}")
        input("Press enter to continue...")

    prefix = flag_config.get("prefix", "")
    uuid = f"{prefix}{uuid}"
    config["uuid"] = uuid


def configure_cid(app: dict, flag_config: dict, config: dict):
    print(f"Find your CID inside your {app['name'].lower().title()} dashboard/profile.")
    print(
        "Example: For packetstream you can fetch it from your dashboard https://packetstream.io/dashboard/download?linux# then click on -> Looking for linux app -> now search for CID= in the code shown in the page, you need to enter the code after -e CID= (e.g. if in the code CID=6aTk, just enter 6aTk)"
    )
    cid = ask_string(
        f"Enter your {app['name'].lower().title()} CID:", default=config.get("cid")
    )
    config["cid"] = cid


def configure_code(app: dict, flag_config: dict, config: dict):
    print(
        f"Find your code inside your {app['name'].lower().title()} dashboard/profile."
    )
    code = ask_string(
        f"Enter your {app['name'].lower().title()} code:", default=config.get("code")
    )
    config["code"] = code


def configure_token(app: dict, flag_config: dict, config: dict):
    print(
        f"Find your token inside your {app['name'].lower().title()} dashboard/profile."
    )
    token = ask_string(
        f"Enter your {app['name'].lower().title()} token:", default=config.get("token")
    )
    config["token"] = token


def configure_manual(app: dict, flag_config: dict, config: dict):
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
    input("Press enter to continue...")


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


def collect_user_info(user_config: dict[str, Any], m4b_config: dict[str, Any]) -> None:
    """
    Collect user information and update the user configuration.

    Args:
        user_config (dict): The user configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
    """
    try:
        # Get the system's current username (fallback to 'user' on exception)
        nickname = getpass.getuser()
    except Exception:
        nickname = "user"

    # Store the username in the user configuration
    user_config["user"]["Nickname"] = nickname

    # Fetch the existing device name from the configuration, use 'yourDeviceName' as placeholder
    device_name = user_config["device_info"].get("device_name", "yourDeviceName")

    # If the device name is 'yourDeviceName', try using the system's hostname, otherwise generate a random name
    if device_name.lower() == ("yourDeviceName").lower():
        try:
            device_name = platform.node()  # Default to system hostname
        except Exception:
            logging.warning("Unable to retrieve hostname for device name.")
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
    logging.info(f"Device name set to: {device_name}")


def _configure_apps(user_config: dict[str, Any], apps: dict, m4b_config: dict):
    """
    Configure apps by collecting user inputs.

    Args:
        user_config (dict): The user configuration dictionary.
        apps (dict): The app configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
    """
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
        input("When you are done press Enter to continue")
        for flag_name, flag_config in app.get("flags", {}).items():
            if flag_name in flag_function_mapper:
                flag_function_mapper[flag_name](app, flag_config, config)
            else:
                logging.error(f"Flag {flag_name} not recognized")

        # Port configuration for apps with defined ports (should have a 'ports' key in the compose_config and a <app_name>_ports key in the user_config)
        if "ports" in app["compose_config"]:
            assigned_ports = assign_app_ports(app_name, app, config)
            # Always store as list for consistency
            config["ports"] = assigned_ports
            logging.info(f"Ports for {app_name} set to: {config['ports']}")

        user_config["apps"][app_name] = config


def configure_apps(
    user_config: dict[str, Any], app_config: dict, m4b_config: dict
) -> None:
    """
    Configure apps by collecting user inputs.

    Args:
        user_config (dict): The user configuration dictionary.
        app_config (dict): The app configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
    """
    _configure_apps(user_config, app_config["apps"], m4b_config)


def configure_extra_apps(
    user_config: dict[str, Any], app_config: dict, m4b_config: dict
) -> None:
    """
    Configure extra apps by collecting user inputs.

    Args:
        user_config (dict): The user configuration dictionary.
        app_config (dict): The app configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
    """
    _configure_apps(user_config, app_config["extra-apps"], m4b_config)


# Supported services and their URL patterns
SUPPORTED_NOTIFICATION_SERVICES = {
    "bark": r"^bark://[\w\-]+@.+$",
    "discord": r"^discord://[\w\-\._]+@[\w\-\._]+$",
    "email": r"^smtp://[\w\-]+:[\w\-]+@.+:\d+/\?from=.*&to=.*$",
    "gotify": r"^gotify://.+/token$",
    "googlechat": r"^googlechat://chat\.googleapis\.com/v1/spaces/.+/messages\?key=.*&token=.*$",
    "ifttt": r"^ifttt://.+/\?events=.*$",
    "join": r"^join://shoutrrr:[\w\-]+@join/\?devices=.*$",
    "mattermost": r"^mattermost://(?:[\w\-]+@)?.+/token(?:/channel)?$",
    "matrix": r"^matrix://.+:.+@.+:\d+/\?rooms=.*$",
    "ntfy": r"^ntfy://(?:[\w\-]+:[\w\-]+@)?.+/topic$",
    "opsgenie": r"^opsgenie://.+/token\?responders=.*$",
    "pushbullet": r"^pushbullet://[\w\-]+(?:/device/#channel/[\w\-]+)?$",
    "pushover": r"^pushover://shoutrrr:[\w\-]+@[\w\-]+/\?devices=.*$",
    "rocketchat": r"^rocketchat://(?:[\w\-]+@)?.+/token(?:/channel)?$",
    "slack": r"^slack://(?:[\w\-]+@)?.+/token-a/token-b/token-c$",
    "teams": r"^teams://[\w\-]+@[\w\-]+/.+/groupOwner\?host=.*$",
    "telegram": r"^telegram://.+@telegram\?chats=.*$",
    "zulip": r"^zulip://.+:.+@zulip-domain/\?stream=.*&topic=.*$",
}


def validate_notification_url(url: str) -> bool:
    """
    Validate the notification URL against supported services.

    Args:
        url (str): The URL to validate.

    Returns:
        bool: True if the URL is valid, False otherwise.
    """
    for service, pattern in SUPPORTED_NOTIFICATION_SERVICES.items():
        if re.match(pattern, url):
            logging.info(f"Given URL {url} matches notification service {service}")
            return True
    logging.error(f"Given URL {url} does not match any supported notification service")
    return False


def setup_notifications(user_config: dict[str, Any]) -> None:
    """
    Set up notifications for app updates using a supported service.

    Args:
        user_config (dict): The user configuration dictionary.
    """
    notifications_config = user_config.get("notifications", {})

    # Check if notifications are already set up
    if notifications_config.get("enabled"):
        print(
            f"Notifications are currently enabled with the following URL: {notifications_config.get('url')}"
        )
        if not ask_question_yn(
            "Do you want to change the current notification settings?"
        ):
            print("Keeping existing notification settings.")
            logging.info("User chose to keep existing notification settings.")
            return

    # Proceed to set up or change the notification settings
    if ask_question_yn(
        "Do you want to enable notifications about apps images updates?"
    ):
        logging.info("User decided to set up notifications about apps images updates.")
        print("Setting-up notifications for images updates using Shoutrrr.")
        print("Format WATCHTOWER_NOTIFICATION_URL as: <app>://<token>@<webhook>.")
        print(
            "<app> is a supported messaging app (e.g., Discord), <token> and <webhook> are app-specific."
        )
        print("Create a webhook for your app and format its URL accordingly.")
        print(
            "For details, visit https://containrrr.dev/shoutrrr/ and select your app."
        )
        print(
            "You can also specify multiple URLs separated by spaces (e.g., 'discord://token@id slack://watchtower@token-a/token-b/token-c')."
        )
        input("Press Enter to continue...")

        while True:
            notification_url = ask_string(
                "Enter the notification URL (e.g., discord://token@id):",
                default=notifications_config.get("url", ""),
            )
            if validate_notification_url(notification_url):
                user_config["notifications"]["enabled"] = True
                user_config["notifications"]["url"] = notification_url
                logging.info(f"Notification URL set to: {notification_url}")
                break
            else:
                print(
                    "Invalid URL format. Please ensure it matches one of the supported formats."
                )
                if not ask_question_yn("Do you want to try again?"):
                    logging.info("User chose to skip notification setup.")
                    break
    else:
        user_config["notifications"]["enabled"] = False
        print("Noted: All updates will be applied automatically and silently.")
        logging.info("User chose not to enable notifications.")


def setup_multiproxy_instances(
    user_config: dict[str, Any],
    app_config: dict[str, Any],
    m4b_config: dict[str, Any],
    proxies: list,
) -> None:
    """
    Setup multiple proxy instances based on the given proxies list.

    Args:
        user_config (dict): The user configuration dictionary.
        app_config (dict): The app configuration dictionary.
        m4b_config (dict): The m4b configuration dictionary.
        proxies (list): List of proxy configurations.
    """
    instances_dir = "m4b_proxy_instances"
    os.makedirs(instances_dir, exist_ok=True)

    base_device_name = user_config["device_info"]["device_name"]
    base_project_name = m4b_config.get("project", {}).get(
        "compose_project_name", "money4band"
    )

    # Track used device names to ensure uniqueness
    used_device_names = {base_device_name}  # Start with the main device name
    # Start with the main project name
    used_project_names = {base_project_name}

    print(
        f"{Fore.BLUE}Base device name for instances: {base_device_name}{Style.RESET_ALL}"
    )
    logging.info(f"Base device name for proxy instances: {base_device_name}")

    base_subnet = m4b_config["network"]["subnet"]
    base_netmask = int(m4b_config["network"]["netmask"])

    if os.listdir(instances_dir):
        if ask_question_yn(
            f"Existing proxy instances found in '{instances_dir}'. Do you want to delete them?",
            default=True,
        ):
            stop_all_stacks(instances_dir, skip_questions=True)
            if not safe_rmtree(instances_dir):
                print(
                    f"{Fore.RED}Failed to remove existing instances. Aborting setup.{Style.RESET_ALL}"
                )
                time.sleep(sleep_time)
                return
            os.makedirs(instances_dir, exist_ok=True)
        else:
            print(
                f"{Fore.YELLOW}Keeping existing instances alongside new ones.{Style.RESET_ALL}"
            )

    for i, proxy in enumerate(proxies):
        logging.info(f"Creating instance {i + 1}/{len(proxies)} with proxy: {proxy}")
        instance_user_config = deepcopy(user_config)
        instance_m4b_config = deepcopy(m4b_config)
        instance_app_config = deepcopy(app_config)

        # Generate a unique suffix for device and project names
        while True:
            suffix = generate_uuid(4)
            instance_device_name = f"{base_device_name}_{suffix}"
            instance_project_name = f"{base_project_name}_{suffix}"

            # Ensure the device name and project name are unique
            if (
                instance_device_name not in used_device_names
                and instance_project_name not in used_project_names
            ):
                used_device_names.add(instance_device_name)
                used_project_names.add(instance_project_name)
                break

        print(
            f"{Fore.GREEN}Created proxy instance {i + 1} with device name: {instance_device_name}{Style.RESET_ALL}"
        )
        logging.info(
            f"Created proxy instance with unique device name: {instance_device_name}"
        )

        instance_dir = os.path.join(instances_dir, instance_project_name)
        os.makedirs(instance_dir, exist_ok=True)

        instance_user_config["device_info"]["device_name"] = instance_device_name
        instance_m4b_config["project"]["compose_project_name"] = instance_project_name

        instance_user_config["proxies"]["url"] = proxy
        instance_user_config["proxies"]["enabled"] = True

        # Calculate unique subnet for this instance
        new_subnet = calculate_subnet(base_subnet, base_netmask, i + 1)

        instance_m4b_config["network"]["subnet"] = new_subnet

        # Update all enabled apps with unique ports to avoid conflicts
        app_index = 0
        for app_category in ["apps", "extra-apps"]:
            for app_details in instance_app_config.get(app_category, []):
                app_name = app_details["name"].lower()
                app_config_entry = instance_user_config["apps"].get(app_name, {})

                # Only process enabled apps
                if app_details.get("enabled", False) or (
                    app_config_entry and app_config_entry.get("enabled", False)
                ):
                    logging.info(
                        f"Processing port assignments for {app_name} in instance {instance_project_name}"
                    )

                    # If app isn't in user_config yet, initialize it
                    if not app_config_entry:
                        instance_user_config["apps"][app_name] = {"enabled": True}
                        app_config_entry = instance_user_config["apps"][app_name]

                    # Check if this app has ports defined in compose_config
                    has_ports = False
                    if (
                        "compose_config" in app_details
                        and "ports" in app_details["compose_config"]
                    ):
                        has_ports = True

                    # Or check if it already has ports in user_config
                    if "ports" in app_config_entry:
                        has_ports = True

                    # If app uses ports, ensure they're unique for this instance
                    if has_ports:
                        # Get base port from user config or default
                        base_port = app_config_entry.get(
                            "ports", [DEFAULT_PORT_BASE + app_index * PORT_OFFSET_PER_APP]
                        )
                        # Always ensure we have a list
                        if not isinstance(base_port, list):
                            base_port = [base_port]
                        
                        # Update all ports with unique values for this instance
                        app_config_entry["ports"] = [
                            find_next_available_port(
                                port + (i + 1) * PORT_OFFSET_PER_INSTANCE
                            )
                            for port in base_port
                        ]
                        logging.info(
                            f"Updated ports for {app_name} in instance "
                            f"{instance_project_name} to {app_config_entry['ports']}"
                        )

                    # Increment app index for each enabled app processed
                    app_index += 1

        # Properly disable dashboard for multiproxy instances to avoid port conflicts
        if "m4b_dashboard" in instance_user_config:
            instance_user_config["m4b_dashboard"]["enabled"] = False
            # Remove dashboard port to ensure it's not included anywhere in multiproxy instances
            if "ports" in instance_user_config["m4b_dashboard"]:
                del instance_user_config["m4b_dashboard"]["ports"]

            # Also completely remove dashboard port from proxy_service configuration ports
            if (
                "compose_config_common" in instance_user_config
                and "proxy_service" in instance_user_config["compose_config_common"]
                and "ports"
                in instance_user_config["compose_config_common"]["proxy_service"]
            ):
                # Get ports configuration
                ports = instance_user_config["compose_config_common"]["proxy_service"][
                    "ports"
                ]

                # Filter out any dashboard port references
                if isinstance(ports, list):
                    dashboard_port = "${M4B_DASHBOARD_PORT}:80"
                    ports = [port for port in ports if port != dashboard_port]
                    instance_user_config["compose_config_common"]["proxy_service"][
                        "ports"
                    ] = ports
                    logging.info(
                        f"Filtered out dashboard port from proxy_service configuration for multiproxy instance {instance_project_name}"
                    )

            logging.info(
                f"Completely disabled dashboard for multiproxy instance {instance_project_name} to avoid port conflicts"
            )

        # Regenerate UUIDs for apps that require them
        regenerate_uuids_for_apps(instance_user_config, instance_app_config)

        instance_user_config_path = os.path.join(instance_dir, "user-config.json")
        instance_m4b_config_path = os.path.join(instance_dir, "m4b-config.json")
        instance_app_config_path = os.path.join(instance_dir, "app-config.json")

        write_json(instance_user_config, instance_user_config_path)
        write_json(instance_m4b_config, instance_m4b_config_path)
        write_json(instance_app_config, instance_app_config_path)

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

    print(
        f"{Fore.GREEN}Created {len(proxies)} proxy instances with unique device names.{Style.RESET_ALL}"
    )
    print(f"{Fore.GREEN}Multiproxy instances setup completed.{Style.RESET_ALL}")
    time.sleep(sleep_time)


def regenerate_uuids_for_apps(
    user_config: dict[str, Any], app_config: dict[str, Any]
) -> None:
    """
    Regenerate UUIDs for apps that require them, preserving prefixes or postfixes if defined.

    Args:
        user_config (dict): The user configuration dictionary.
        app_config (dict): The app configuration dictionary.
    """
    for app_category in ["apps", "extra-apps"]:
        for app in app_config.get(app_category, []):
            app_name = app["name"].lower()
            app_user_config = user_config["apps"].get(app_name, {})

            # Check if the app has a UUID flag and is enabled
            if app_user_config.get("enabled") and "uuid" in app.get("flags", {}):
                uuid_length = app["flags"]["uuid"].get(
                    "length", 32
                )  # Default to 32 if not specified
                prefix = app["flags"]["uuid"].get("prefix", "")
                postfix = app["flags"]["uuid"].get("postfix", "")

                # Generate the new UUID part
                new_uuid_part = generate_uuid(uuid_length)
                new_uuid = f"{prefix}{new_uuid_part}{postfix}"

                app_user_config["uuid"] = new_uuid
                logging.info(f"Generated new UUID for {app_name}: {new_uuid}")


def main(app_config_path: str, m4b_config_path: str, user_config_path: str) -> None:
    """
    Main function for setting up user configurations.

    Args:
        app_config_path (str): Path to the app configuration file.
        m4b_config_path (str): Path to the m4b configuration file.
        user_config_path (str): Path to the user configuration file.
    """
    try:
        app_config = loader.load_json_config(app_config_path)
        user_config = loader.load_json_config(user_config_path)
        m4b_config = loader.load_json_config(m4b_config_path)
        logging.info("Setup apps started")

        # Step 1: Collect user information
        collect_user_info(user_config, m4b_config)
        # Step 2: Configure apps
        configure_apps(user_config, app_config, m4b_config)
        # Step 3: Configure extra apps if the user chooses to
        if ask_question_yn("Do you want to configure extra apps?"):
            logging.info("Extra apps setup selected")
            configure_extra_apps(user_config, app_config, m4b_config)
        else:  # if there are extra-apps enabled disable them
            for app in app_config["extra-apps"]:
                app_name = app["name"].lower()
                user_config["apps"][app_name]["enabled"] = False
        # Step 4: Set up notifications
        setup_notifications(user_config)
        # Step 5: Save the user configuration
        write_json(user_config, user_config_path)
        # Step 6: Set up proxy if the user chooses to
        proxy_setup = ask_question_yn("Do you want to enable (multi)proxy?")
        if proxy_setup:
            logging.info("Multiproxy setup selected")
            print(
                "Create a proxies.txt file in the same folder and add proxies in the following format: protocol://user:pass@ip:port (one proxy per line)"
            )
            input("Press enter to continue...")
            with open("proxies.txt") as file:
                proxies = [line.strip() for line in file if line.strip()]

            # Use the user config first proxy to update the base money4band docker compose and env file adding proxy
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
            logging.info("Multiproxy instances setup completed")
        else:
            # Disable proxy if proxy setup is not selected
            logging.info("Multiproxy setup not selected")
            if user_config["proxies"].get("enabled"):
                user_config["proxies"]["url"] = ""
                user_config["proxies"]["enabled"] = False
                write_json(user_config, user_config_path)
            assemble_docker_compose(
                m4b_config_path,
                app_config_path,
                user_config_path,
                compose_output_path="./docker-compose.yaml",
                is_main_instance=True,
            )
            generate_env_file(
                m4b_config_path,
                app_config_path,
                user_config_path,
                env_output_path="./.env",
                is_main_instance=True,
            )
        logging.info("Setup completed")

    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An error occurred in main setup apps process: {str(e)}")
        raise


if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Run the setup apps module standalone."
    )
    parser.add_argument(
        "--app-config", type=str, required=True, help="Path to app_config JSON file"
    )
    parser.add_argument(
        "--m4b-config", type=str, required=True, help="Path to m4b_config JSON file"
    )
    parser.add_argument(
        "--user-config-path",
        type=str,
        default="./config/user-config.json",
        help="Path to user_config JSON file",
    )
    parser.add_argument(
        "--log-dir",
        default=os.path.join(script_dir, "logs"),
        help="Set the logging directory",
    )
    parser.add_argument(
        "--log-file", default=f"{script_name}.log", help="Set the logging file name"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    args = parser.parse_args()

    # Set logging level based on command-line arguments
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    # Start logging
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.log_dir, args.log_file),
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_level,
    )

    logging.info(f"Starting {script_name} script...")

    try:
        # Call the main function
        main(
            app_config_path=args.app_config,
            m4b_config_path=args.m4b_config,
            user_config_path=args.user_config_path,
        )
        logging.info(f"{script_name} script completed successfully")
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise
