"""Tests for money4band.ui.notification_setup - URL validation."""

from __future__ import annotations

from unittest.mock import patch

from money4band.ui.notification_setup import (
    SUPPORTED_NOTIFICATION_SERVICES,
    validate_notification_url,
)


class TestValidateNotificationUrl:
    def test_valid_discord(self) -> None:
        assert validate_notification_url("discord://token@webhookid") is True

    def test_valid_telegram(self) -> None:
        assert validate_notification_url("telegram://token@telegram?chats=123") is True

    def test_valid_ntfy(self) -> None:
        assert validate_notification_url("ntfy://ntfy.sh/topic") is True

    def test_valid_slack(self) -> None:
        assert (
            validate_notification_url("slack://hook@workspace/token-a/token-b/token-c")
            is True
        )

    def test_invalid_empty(self) -> None:
        assert validate_notification_url("") is False

    def test_invalid_garbage(self) -> None:
        assert validate_notification_url("not-a-url") is False

    def test_invalid_http(self) -> None:
        assert validate_notification_url("http://example.com") is False

    def test_supported_services_non_empty(self) -> None:
        assert len(SUPPORTED_NOTIFICATION_SERVICES) >= 15


class TestSetupNotifications:
    """Interactive notification setup flow with mocked prompts."""

    @patch("money4band.ui.notification_setup.ask_question_yn", return_value=False)
    def test_disable_notifications(self, _ask) -> None:
        from money4band.ui.notification_setup import setup_notifications

        cfg: dict = {"notifications": {}}
        setup_notifications(cfg)
        assert cfg["notifications"]["enabled"] is False

    @patch(
        "money4band.ui.notification_setup.ask_string", return_value="discord://tok@hook"
    )
    @patch(
        "money4band.ui.notification_setup.validate_notification_url", return_value=True
    )
    @patch("money4band.ui.notification_setup.ask_question_yn", return_value=True)
    @patch("builtins.input", return_value="")
    def test_enable_with_valid_url(self, _inp, _ask_yn, _validate, _ask_str) -> None:
        from money4band.ui.notification_setup import setup_notifications

        cfg: dict = {"notifications": {}}
        setup_notifications(cfg)
        assert cfg["notifications"]["enabled"] is True
        assert cfg["notifications"]["url"] == "discord://tok@hook"

    @patch("money4band.ui.notification_setup.ask_question_yn", return_value=False)
    def test_keep_existing_settings(self, _ask) -> None:
        """When user declines to change, existing enabled + URL are preserved."""
        from money4band.ui.notification_setup import setup_notifications

        cfg: dict = {"notifications": {"enabled": True, "url": "discord://existing"}}
        setup_notifications(cfg)
        assert cfg["notifications"]["enabled"] is True
        assert cfg["notifications"]["url"] == "discord://existing"

    @patch(
        "money4band.ui.notification_setup.ask_question_yn", side_effect=[True, False]
    )
    @patch(
        "money4band.ui.notification_setup.validate_notification_url", return_value=False
    )
    @patch("money4band.ui.notification_setup.ask_string", return_value="bad-url")
    @patch("builtins.input", return_value="")
    def test_invalid_url_retry_then_skip(
        self, _inp, _ask_str, _validate, _ask_yn
    ) -> None:
        """Invalid URL + user declines retry: notifications not enabled, no URL stored."""
        from money4band.ui.notification_setup import setup_notifications

        cfg: dict = {"notifications": {}}
        setup_notifications(cfg)
        assert cfg["notifications"].get("enabled") is not True
        assert "url" not in cfg["notifications"]


class TestUrlMaskingInLogs:
    """Validate that credential-bearing URLs are masked in log output."""

    def test_valid_url_logs_masked(self, caplog) -> None:
        """A matching URL should log only scheme://hostname, not credentials."""
        import logging

        with caplog.at_level(logging.INFO, logger="money4band.ui.notification_setup"):
            validate_notification_url("discord://secret-token@webhook123")

        # The raw credentials must NOT appear in the log
        for record in caplog.records:
            assert "secret-token" not in record.message
            assert "webhook123" not in record.message or "discord://" in record.message

    def test_invalid_url_logs_masked(self, caplog) -> None:
        """Even invalid URLs with credentials must not leak them in logs."""
        import logging

        with caplog.at_level(logging.ERROR, logger="money4band.ui.notification_setup"):
            validate_notification_url("smtp://user:p%40ssword@mail.example.com:587")

        for record in caplog.records:
            assert "p%40ssword" not in record.message
            assert "user:" not in record.message
