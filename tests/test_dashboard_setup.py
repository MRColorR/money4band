"""Tests for money4band.dashboard.setup — dashboard & watchtower setup."""

from __future__ import annotations

import copy
import json
from unittest.mock import patch

from money4band.dashboard.setup import (
    DEFAULT_DASHBOARD_PORT,
    set_dashboard_state,
    setup_m4b_dashboard,
)
from money4band.docker.watchtower import setup_watchtower

_USER_CONFIG = {
    "m4b_dashboard": {"enabled": False},
    "watchtower": {"enabled": True},
}


def _mock_port(port=DEFAULT_DASHBOARD_PORT):
    return patch("money4band.dashboard.setup._ask_port", return_value=port)


class TestSetupM4bDashboard:
    def test_enable_dashboard(self):
        cfg = copy.deepcopy(_USER_CONFIG)
        with (
            patch("money4band.dashboard.setup.ask_question_yn", return_value=True),
            _mock_port(),
        ):
            setup_m4b_dashboard(cfg)
        assert cfg["m4b_dashboard"]["enabled"] is True
        assert cfg["m4b_dashboard"]["port"] == DEFAULT_DASHBOARD_PORT

    def test_enable_dashboard_custom_port(self):
        cfg = copy.deepcopy(_USER_CONFIG)
        with (
            patch("money4band.dashboard.setup.ask_question_yn", return_value=True),
            _mock_port(9090),
        ):
            setup_m4b_dashboard(cfg)
        assert cfg["m4b_dashboard"]["enabled"] is True
        assert cfg["m4b_dashboard"]["port"] == 9090

    def test_disable_dashboard(self):
        cfg = copy.deepcopy(_USER_CONFIG)
        with patch("money4band.dashboard.setup.ask_question_yn", return_value=False):
            setup_m4b_dashboard(cfg)
        assert cfg["m4b_dashboard"]["enabled"] is False

    def test_keep_existing_when_already_enabled(self, capsys):
        cfg = copy.deepcopy(_USER_CONFIG)
        cfg["m4b_dashboard"]["enabled"] = True
        # First ask_question_yn: "change settings?" → No
        with patch("money4band.dashboard.setup.ask_question_yn", return_value=False):
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
            "money4band.docker.watchtower.ask_question_yn", side_effect=[True, True]
        ):
            setup_watchtower(cfg)
        assert cfg["watchtower"]["enabled"] is True
        captured = capsys.readouterr()
        assert "enabled" in captured.out.lower()

    def test_disable_watchtower(self, capsys):
        cfg = copy.deepcopy(_USER_CONFIG)
        # Currently enabled → ask "change?" → Yes, then "enable?" → No
        with patch(
            "money4band.docker.watchtower.ask_question_yn", side_effect=[True, False]
        ):
            setup_watchtower(cfg)
        assert cfg["watchtower"]["enabled"] is False
        captured = capsys.readouterr()
        assert "disabled" in captured.out.lower()

    def test_keep_existing_when_enabled(self, capsys):
        cfg = copy.deepcopy(_USER_CONFIG)
        # Currently enabled → ask "change?" → No
        with patch("money4band.docker.watchtower.ask_question_yn", return_value=False):
            setup_watchtower(cfg)
        assert cfg["watchtower"]["enabled"] is True
        captured = capsys.readouterr()
        assert "Keeping" in captured.out

    def test_keep_existing_when_disabled(self, capsys):
        cfg = copy.deepcopy(_USER_CONFIG)
        cfg["watchtower"]["enabled"] = False
        # Currently disabled → ask "change?" → No
        with patch("money4band.docker.watchtower.ask_question_yn", return_value=False):
            setup_watchtower(cfg)
        assert cfg["watchtower"]["enabled"] is False
        captured = capsys.readouterr()
        assert "Keeping" in captured.out


class TestSetDashboardState:
    def test_set_enabled_true(self, tmp_path):
        cfg_path = tmp_path / "user-config.json"
        cfg_path.write_text(json.dumps({"m4b_dashboard": {"enabled": False}}))
        set_dashboard_state(str(tmp_path), enabled=True, port=9090)
        result = json.loads(cfg_path.read_text())
        assert result["m4b_dashboard"]["enabled"] is True
        assert result["m4b_dashboard"]["port"] == 9090

    def test_set_enabled_false(self, tmp_path):
        cfg_path = tmp_path / "user-config.json"
        cfg_path.write_text(
            json.dumps({"m4b_dashboard": {"enabled": True, "port": 8088}})
        )
        set_dashboard_state(str(tmp_path), enabled=False)
        result = json.loads(cfg_path.read_text())
        assert result["m4b_dashboard"]["enabled"] is False
        assert result["m4b_dashboard"]["port"] == 8088  # port preserved

    def test_missing_config_no_error(self, tmp_path):
        # Should not raise even if user-config.json doesn't exist
        set_dashboard_state(str(tmp_path), enabled=True)
