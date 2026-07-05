"""Tests for the notification system (utils/notifier.py + hooks)."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from money4band.notifier import (
    ALL_EVENTS,
    EVENT_STACK_ERROR,
    EVENT_STACK_START,
    EVENT_STACK_STOP,
    EVENT_TEST,
    EVENT_UPDATE_AVAILABLE,
    is_enabled,
    is_event_enabled,
    notify,
    send_test,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def enabled_config():
    """User config with notifications fully enabled."""
    return {
        "notifications": {
            "enabled": True,
            "url": "discord://token@webhook",
            "events": {
                "stack_start": True,
                "stack_stop": True,
                "stack_error": True,
                "update_available": True,
            },
        }
    }


@pytest.fixture()
def disabled_config():
    """User config with notifications disabled."""
    return {
        "notifications": {
            "enabled": False,
            "url": "discord://token@webhook",
            "events": {"stack_start": True},
        }
    }


@pytest.fixture()
def partial_config():
    """Notifications enabled, but only some events on."""
    return {
        "notifications": {
            "enabled": True,
            "url": "discord://token@webhook",
            "events": {
                "stack_start": True,
                "stack_stop": False,
                "stack_error": True,
                "update_available": False,
            },
        }
    }


@pytest.fixture()
def legacy_config():
    """Notifications enabled, but no 'events' key (legacy config)."""
    return {
        "notifications": {
            "enabled": True,
            "url": "discord://token@webhook",
        }
    }


@pytest.fixture()
def no_url_config():
    """Notifications enabled but URL is empty."""
    return {
        "notifications": {
            "enabled": True,
            "url": "",
        }
    }


# ---------------------------------------------------------------------------
# is_enabled / is_event_enabled
# ---------------------------------------------------------------------------


class TestIsEnabled:
    def test_enabled_with_url(self, enabled_config):
        assert is_enabled(enabled_config) is True

    def test_disabled(self, disabled_config):
        assert is_enabled(disabled_config) is False

    def test_empty_url(self, no_url_config):
        assert is_enabled(no_url_config) is False

    def test_missing_notifications_block(self):
        assert is_enabled({}) is False

    def test_whitespace_url(self):
        cfg = {"notifications": {"enabled": True, "url": "   "}}
        assert is_enabled(cfg) is False


class TestIsEventEnabled:
    def test_event_on(self, enabled_config):
        assert is_event_enabled(enabled_config, EVENT_STACK_START) is True

    def test_event_off(self, partial_config):
        assert is_event_enabled(partial_config, EVENT_STACK_STOP) is False

    def test_event_missing_from_dict(self, enabled_config):
        # EVENT_TEST is not in the events dict -> should be False
        assert is_event_enabled(enabled_config, EVENT_TEST) is False

    def test_legacy_no_events_key(self, legacy_config):
        # Legacy: no events dict -> all events considered enabled
        assert is_event_enabled(legacy_config, EVENT_STACK_START) is True
        assert is_event_enabled(legacy_config, EVENT_UPDATE_AVAILABLE) is True

    def test_disabled_config_always_false(self, disabled_config):
        assert is_event_enabled(disabled_config, EVENT_STACK_START) is False


# ---------------------------------------------------------------------------
# notify()
# ---------------------------------------------------------------------------


class TestNotify:
    @patch("money4band.notifier._send_shoutrrr", return_value=True)
    def test_blocking_sends(self, mock_send, enabled_config):
        result = notify(enabled_config, EVENT_STACK_START, "Started!", blocking=True)
        assert result is True
        mock_send.assert_called_once()
        assert "[M4B]" in mock_send.call_args[0][1]

    @patch("money4band.notifier._send_shoutrrr", return_value=True)
    def test_fire_and_forget_returns_none(self, mock_send, enabled_config):
        result = notify(enabled_config, EVENT_STACK_START, "Started!")
        assert result is None
        # Give thread a moment to execute
        import time

        time.sleep(0.2)
        mock_send.assert_called_once()

    @patch("money4band.notifier._send_shoutrrr")
    def test_skips_disabled_event(self, mock_send, partial_config):
        result = notify(partial_config, EVENT_STACK_STOP, "Stopped!", blocking=True)
        assert result is False
        mock_send.assert_not_called()

    @patch("money4band.notifier._send_shoutrrr")
    def test_skips_disabled_notifications(self, mock_send, disabled_config):
        result = notify(disabled_config, EVENT_STACK_START, "Started!", blocking=True)
        assert result is False
        mock_send.assert_not_called()

    @patch("money4band.notifier._send_shoutrrr")
    def test_skips_no_url(self, mock_send, no_url_config):
        result = notify(no_url_config, EVENT_STACK_START, "test", blocking=True)
        assert result is False
        mock_send.assert_not_called()

    @patch("money4band.notifier._send_shoutrrr", return_value=True)
    def test_test_event_always_sends(self, mock_send, enabled_config):
        """EVENT_TEST bypasses the event filter (always sends if URL exists)."""
        result = notify(enabled_config, EVENT_TEST, "Test!", blocking=True)
        assert result is True
        mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# _send_shoutrrr
# ---------------------------------------------------------------------------


class TestSendShoutrrr:
    @patch("money4band.notifier.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        from money4band.notifier import _send_shoutrrr

        assert _send_shoutrrr("discord://token@hook", "hello") is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "docker" in cmd
        assert "containrrr/shoutrrr" in cmd

    @patch("money4band.notifier.subprocess.run")
    def test_failure_nonzero(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="error")
        from money4band.notifier import _send_shoutrrr

        assert _send_shoutrrr("discord://token@hook", "hello") is False

    @patch("money4band.notifier.subprocess.run", side_effect=FileNotFoundError)
    def test_docker_missing(self, mock_run):
        from money4band.notifier import _send_shoutrrr

        assert _send_shoutrrr("discord://token@hook", "hello") is False

    @patch(
        "money4band.notifier.subprocess.run",
        side_effect=subprocess.TimeoutExpired("cmd", 30),
    )
    def test_timeout(self, mock_run):
        from money4band.notifier import _send_shoutrrr

        assert _send_shoutrrr("discord://token@hook", "hello") is False


# ---------------------------------------------------------------------------
# send_test
# ---------------------------------------------------------------------------


class TestSendTest:
    @patch("money4band.notifier._send_shoutrrr", return_value=True)
    def test_success(self, mock_send, enabled_config):
        assert send_test(enabled_config) is True
        assert "Test notification" in mock_send.call_args[0][1]

    def test_no_url(self):
        assert send_test({"notifications": {"url": ""}}) is False
        assert send_test({}) is False


# ---------------------------------------------------------------------------
# ALL_EVENTS constant
# ---------------------------------------------------------------------------


class TestConstants:
    def test_all_events_complete(self):
        assert EVENT_STACK_START in ALL_EVENTS
        assert EVENT_STACK_STOP in ALL_EVENTS
        assert EVENT_STACK_ERROR in ALL_EVENTS
        assert EVENT_UPDATE_AVAILABLE in ALL_EVENTS
        assert EVENT_TEST in ALL_EVENTS
        assert len(ALL_EVENTS) == 5


# ---------------------------------------------------------------------------
# CLI dispatch: 'notify' subcommand exists
# ---------------------------------------------------------------------------


class TestNotifySubcommand:
    def test_notify_in_dispatch(self):
        from main import _SUBCOMMAND_DISPATCH

        assert "notify" in _SUBCOMMAND_DISPATCH

    def test_notify_parser_exists(self):
        import argparse

        from main import _build_parser

        parser = _build_parser()
        sub_action = next(
            a
            for a in parser._subparsers._group_actions
            if isinstance(a, argparse._SubParsersAction)
        )
        assert "notify" in sub_action.choices

    def test_notify_test_subcommand(self):
        from main import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["notify", "test"])
        assert args.command == "notify"
        assert args.notify_action == "test"


# ---------------------------------------------------------------------------
# Hook integration: _notify_event helper exists in start/stop modules
# ---------------------------------------------------------------------------


class TestHookHelpers:
    def test_start_stack_has_notify_helper(self):
        from money4band.docker.start import _notify_event

        assert callable(_notify_event)

    def test_stop_stack_has_notify_helper(self):
        from money4band.docker.stop import _notify_event

        assert callable(_notify_event)


# ---------------------------------------------------------------------------
# Template: events field in user-config template
# ---------------------------------------------------------------------------


class TestTemplate:
    def test_template_has_events_field(self):
        import json
        import os

        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "template",
            "user-config.json",
        )
        with open(template_path) as f:
            tpl = json.load(f)
        notif = tpl["notifications"]
        assert "events" in notif
        assert notif["events"]["stack_start"] is True
        assert notif["events"]["stack_stop"] is True
        assert notif["events"]["stack_error"] is True
        assert notif["events"]["update_available"] is True
