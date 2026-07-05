from __future__ import annotations

"""Fire-and-forget notification sender for M4B lifecycle events.

Uses Shoutrrr-compatible URLs from user config to deliver notifications
about stack start/stop, errors, and available updates.
"""

import logging
import subprocess
import threading
from typing import Any

logger = logging.getLogger(__name__)
# -- Event types ---------------------------------------------------------
EVENT_STACK_START = "stack_start"
EVENT_STACK_STOP = "stack_stop"
EVENT_STACK_ERROR = "stack_error"
EVENT_UPDATE_AVAILABLE = "update_available"
EVENT_TEST = "test"

ALL_EVENTS = frozenset(
    {
        EVENT_STACK_START,
        EVENT_STACK_STOP,
        EVENT_STACK_ERROR,
        EVENT_UPDATE_AVAILABLE,
        EVENT_TEST,
    }
)


def _get_notification_config(user_config: dict[str, Any]) -> dict[str, Any]:
    """Extract and return the ``notifications`` block from user config."""
    return user_config.get("notifications", {})


def is_enabled(user_config: dict[str, Any]) -> bool:
    """Return True if notifications are enabled and a URL is configured."""
    cfg = _get_notification_config(user_config)
    return bool(cfg.get("enabled")) and bool(cfg.get("url", "").strip())


def is_event_enabled(user_config: dict[str, Any], event: str) -> bool:
    """Return True if the given event type is enabled in config.

    When the ``events`` dict is missing, all events are considered enabled
    (backward-compatible default for configs created before events existed).
    """
    if not is_enabled(user_config):
        return False
    cfg = _get_notification_config(user_config)
    events = cfg.get("events")
    if events is None:
        return True  # legacy config -> all events enabled
    return bool(events.get(event, False))


def _send_shoutrrr(url: str, message: str) -> bool:
    """Send a notification via the Shoutrrr Docker container.

    Returns True on success, False otherwise.
    """
    # Validate URL against known Shoutrrr service patterns.
    from money4band.ui.notification_setup import validate_notification_url

    if not validate_notification_url(url):
        logger.warning("Refusing to send notification: URL failed validation.")
        return False

    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "containrrr/shoutrrr",
                "send",
                "--url",
                url,
                "--message",
                message,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("Notification sent successfully.")
            return True
        logger.warning(
            "Shoutrrr exited with code %d: %s",
            result.returncode,
            result.stderr.strip(),
        )
        return False
    except FileNotFoundError:
        logger.warning("Docker not found - cannot send notification via Shoutrrr.")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("Shoutrrr notification timed out after 30s.")
        return False
    except Exception as e:
        logger.error("Unexpected error sending notification: %s", e)
        return False


def notify(
    user_config: dict[str, Any],
    event: str,
    message: str,
    *,
    blocking: bool = False,
) -> bool | None:
    """Send a notification if the event type is enabled.

    Args:
        user_config: The loaded user configuration dict.
        event: One of the ``EVENT_*`` constants.
        message: Human-readable message body.
        blocking: If True, send synchronously and return success bool.
                  If False (default), fire-and-forget in a background thread
                  and return None immediately.

    Returns:
        True/False when blocking, None when fire-and-forget.
    """
    if event != EVENT_TEST and not is_event_enabled(user_config, event):
        logger.debug("Notification skipped: event '%s' not enabled.", event)
        return False if blocking else None

    url = _get_notification_config(user_config).get("url", "").strip()
    if not url:
        logger.debug("Notification skipped: no URL configured.")
        return False if blocking else None

    prefixed = f"[M4B] {message}"

    if blocking:
        return _send_shoutrrr(url, prefixed)

    thread = threading.Thread(
        target=_send_shoutrrr,
        args=(url, prefixed),
        daemon=True,
    )
    thread.start()
    return None


def send_test(user_config: dict[str, Any]) -> bool:
    """Send a blocking test notification. Returns True on success."""
    url = _get_notification_config(user_config).get("url", "").strip()
    if not url:
        logger.warning("Cannot send test notification: no URL configured.")
        return False
    return _send_shoutrrr(url, "[M4B] Test notification - your webhook is working!")


def fire_event(event: str, message: str, config_dir: str | None = None) -> None:
    """Fire-and-forget notification if enabled in user config.

    Loads user-config.json from *config_dir* (auto-detected if omitted),
    then delegates to :func:`notify`.  Any error is silently logged.
    """
    import os

    from money4band.core.loader import load_json_config

    try:
        if config_dir is None:
            config_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config",
            )
        user_cfg_path = os.path.join(config_dir, "user-config.json")
        if not os.path.isfile(user_cfg_path):
            return
        user_config = load_json_config(user_cfg_path)
        notify(user_config, event, message)
    except Exception:
        logger.debug("Notification send failed (non-critical).", exc_info=True)
