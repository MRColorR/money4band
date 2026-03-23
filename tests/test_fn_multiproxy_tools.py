"""Tests for money4band.fn_multiproxy_tools — multiproxy utilities."""

from __future__ import annotations

import json
from unittest.mock import patch

from money4band.fn_multiproxy_tools import (
    _install_limits_status_label,
    exit_submenu,
    submenu_multiproxy_tools,
    toggle_install_limits,
    update_multiproxy_instances,
)


class TestToggleInstallLimits:
    def test_toggles_on_to_off(self, tmp_path, capsys):
        cfg = {"system": {"enforce_install_limits": True}}
        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(cfg))

        with patch("builtins.input", return_value=""):
            toggle_install_limits(str(cfg_path))

        result = json.loads(cfg_path.read_text())
        assert result["system"]["enforce_install_limits"] is False
        captured = capsys.readouterr()
        assert "DISABLED" in captured.out

    def test_toggles_off_to_on(self, tmp_path, capsys):
        cfg = {"system": {"enforce_install_limits": False}}
        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(cfg))

        with patch("builtins.input", return_value=""):
            toggle_install_limits(str(cfg_path))

        result = json.loads(cfg_path.read_text())
        assert result["system"]["enforce_install_limits"] is True
        captured = capsys.readouterr()
        assert "ENABLED" in captured.out


class TestInstallLimitsStatusLabel:
    def test_enabled_shows_on(self, tmp_path):
        cfg = {"system": {"enforce_install_limits": True}}
        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(cfg))
        label = _install_limits_status_label(str(cfg_path))
        assert "ON" in label

    def test_disabled_shows_off(self, tmp_path):
        cfg = {"system": {"enforce_install_limits": False}}
        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(cfg))
        label = _install_limits_status_label(str(cfg_path))
        assert "OFF" in label

    def test_missing_file_defaults_on(self):
        label = _install_limits_status_label("/nonexistent/m4b-config.json")
        assert "ON" in label


class TestSubmenuMultiproxyTools:
    def test_returns_menu_items(self, tmp_path):
        cfg = {"system": {"enforce_install_limits": True}}
        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(cfg))
        items = submenu_multiproxy_tools(str(cfg_path))
        assert len(items) >= 2
        labels = [i["label"] for i in items]
        assert any("Update" in l for l in labels)
        assert any("Toggle" in l for l in labels)


class TestExitSubmenu:
    def test_returns_false(self, capsys):
        assert exit_submenu() is False
        captured = capsys.readouterr()
        assert "Exiting" in captured.out


class TestUpdateMultiproxyInstances:
    @patch("money4band.fn_multiproxy_tools.ask_question_yn", return_value=False)
    @patch("builtins.input", return_value="")
    def test_user_cancels(self, _inp, _ask, capsys):
        update_multiproxy_instances()
        captured = capsys.readouterr()
        assert "canceled" in captured.out.lower()

    @patch("money4band.fn_multiproxy_tools.ask_question_yn", return_value=True)
    def test_missing_proxies_file(self, _ask, capsys):
        update_multiproxy_instances(proxies_file="/nonexistent/proxies.txt")
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    @patch("money4band.fn_multiproxy_tools.start_all_stacks")
    @patch("money4band.fn_multiproxy_tools.stop_all_stacks")
    @patch("money4band.fn_multiproxy_tools.generate_env_file")
    @patch("money4band.fn_multiproxy_tools.assemble_docker_compose")
    @patch("money4band.fn_multiproxy_tools.write_json")
    @patch("money4band.fn_multiproxy_tools.ask_question_yn", return_value=True)
    @patch("time.sleep")
    def test_updates_main_and_instances(
        self,
        _sleep,
        _ask,
        mock_write,
        mock_compose,
        mock_env,
        mock_stop,
        mock_start,
        tmp_path,
    ):
        # Create proxies file
        proxies = tmp_path / "proxies.txt"
        proxies.write_text("socks5://proxy1:9050\nsocks5://proxy2:9050\n")

        # Create user config
        user_cfg = {
            "proxies": {"url": "old", "enabled": False},
            "apps": {},
        }
        user_cfg_path = tmp_path / "user-config.json"
        user_cfg_path.write_text(json.dumps(user_cfg))

        # Create m4b config
        m4b_cfg_path = tmp_path / "m4b-config.json"
        m4b_cfg_path.write_text(json.dumps({"system": {}}))

        # Create app config
        app_cfg_path = tmp_path / "app-config.json"
        app_cfg_path.write_text(json.dumps({}))

        # Create instance dir
        inst_dir = tmp_path / "instances" / "inst1"
        inst_dir.mkdir(parents=True)
        inst_user_cfg = {"proxies": {"url": "old2", "enabled": False}}
        (inst_dir / "user-config.json").write_text(json.dumps(inst_user_cfg))
        (inst_dir / "m4b-config.json").write_text(json.dumps({}))
        (inst_dir / "app-config.json").write_text(json.dumps({}))

        update_multiproxy_instances(
            proxies_file=str(proxies),
            instances_dir=str(tmp_path / "instances"),
            user_config_path=str(user_cfg_path),
            m4b_config_path=str(m4b_cfg_path),
            app_config_path=str(app_cfg_path),
            sleep_time=0,
        )

        # Main updated + 1 instance
        mock_stop.assert_called_once()
        mock_start.assert_called_once()
        assert mock_compose.call_count >= 2  # main + instance
