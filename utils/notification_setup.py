"""Notification setup for M4B (Shoutrrr-compatible webhook URLs)."""

import logging
import re
from typing import Any

from utils.prompt_helper import ask_question_yn, ask_string

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
