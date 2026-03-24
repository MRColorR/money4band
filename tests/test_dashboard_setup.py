"""Tests for money4band.dashboard_setup — dashboard & watchtower setup."""

from __future__ import annotations

import copy
from unittest.mock import patch

from money4band.dashboard_setup import setup_m4b_dashboard, setup_watchtower

_USER_CONFIG = {
    "m4b_dashboard": {"enabled": False},
    "watchtower": {"enabled": True},
}


class TestSetupM4bDashboard:
    def test_enable_dashboard(self):
        cfg = copy.deepcopy(_USER_CONFIG)
        with patch("money4band.dashboard_setup.ask_question_yn", return_value=True):
            setup_m4b_dashboard(cfg)
        assert cfg["m4b_dashboard"]["enabled"] is True

    def test_disable_dashboard(self):
        cfg = copy.deepcopy(_USER_CONFIG)
        with patch("money4band.dashboard_setup.ask_question_yn", return_value=False):
            setup_m4b_dashboard(cfg)
        assert cfg["m4b_dashboard"]["enabled"] is False

    def test_keep_existing_when_already_enabled(self, capsys):
        cfg = copy.deepcopy(_USER_CONFIG)
        cfg["m4b_dashboard"]["enabled"] = True
        # First ask_question_yn: "change settings?" → No
        with patch("money4band.dashboard_setup.ask_question_yn", return_value=False):
            setup_m4b_dashboard(cfg)
        assert cfg["m4b_dashboard"]["enabled"] is True
        captured = capsys.readouterr()
        assert "Keeping" in captured.out


class TestSetupWatchtower:
    def test_enable_watchtower(self, capsys):
        cfg = copy.deepcopy(_USER_CONFIG)
        cfg["watchtower"]["enabled"] = False
        # First ask: "change settings?" → Yes, Second ask: "enable?" → Yes
        with patch(
            "money4band.dashboard_setup.ask_question_yn", side_effect=[True, True]
        ):
            setup_watchtower(cfg)
        assert cfg["watchtower"]["enabled"] is True
        captured = capsys.readouterr()
        assert "enabled" in captured.out.lower()

    def test_disable_watchtower(self, capsys):
        cfg = copy.deepcopy(_USER_CONFIG)
        # Currently enabled → ask "change?" → Yes, then "enable?" → No
        with patch(
            "money4band.dashboard_setup.ask_question_yn", side_effect=[True, False]
        ):
            setup_watchtower(cfg)
        assert cfg["watchtower"]["enabled"] is False
        captured = capsys.readouterr()
        assert "disabled" in captured.out.lower()

    def test_keep_existing_when_enabled(self, capsys):
        cfg = copy.deepcopy(_USER_CONFIG)
        # Currently enabled → ask "change?" → No
        with patch("money4band.dashboard_setup.ask_question_yn", return_value=False):
            setup_watchtower(cfg)
        assert cfg["watchtower"]["enabled"] is True
        captured = capsys.readouterr()
        assert "Keeping" in captured.out

    def test_keep_existing_when_disabled(self, capsys):
        cfg = copy.deepcopy(_USER_CONFIG)
        cfg["watchtower"]["enabled"] = False
        # Currently disabled → ask "change?" → No
        with patch("money4band.dashboard_setup.ask_question_yn", return_value=False):
            setup_watchtower(cfg)
        assert cfg["watchtower"]["enabled"] is False
        captured = capsys.readouterr()
        assert "Keeping" in captured.out
