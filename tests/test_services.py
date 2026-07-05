"""Tests for money4band.services - UI-agnostic facade layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from money4band.services import (
    get_app_catalog,
    get_app_catalog_rich,
    get_discord_url,
    get_farewell_message,
    get_menu_items,
    get_project_version,
    get_system_info_structured,
    resolve_config_paths,
)

# ---------------------------------------------------------------------------
# Pure-logic functions (no mocking needed)
# ---------------------------------------------------------------------------


class TestResolveConfigPaths:
    def test_default_paths(self) -> None:
        m4b, app, user = resolve_config_paths()
        assert m4b.endswith("m4b-config.json")
        # app_config slot aliases m4b_config (envelope folded in).
        assert app == m4b
        assert user.endswith("user-config.json")

    def test_custom_config_dir(self, tmp_path) -> None:
        m4b, app, user = resolve_config_paths(str(tmp_path))
        assert str(tmp_path) in m4b


class TestGetMenuItems:
    def test_returns_menu_list(self) -> None:
        m4b = {"menu": [{"label": "Setup"}, {"label": "Exit"}]}
        assert len(get_menu_items(m4b)) == 2

    def test_empty_menu(self) -> None:
        assert get_menu_items({"menu": []}) == []

    def test_missing_menu_key(self) -> None:
        assert get_menu_items({}) == []


class TestGetProjectVersion:
    def test_returns_version(self) -> None:
        assert get_project_version({"project": {"project_version": "5.0.0"}}) == "5.0.0"

    def test_missing_returns_question_mark(self) -> None:
        assert get_project_version({}) == "?"


class TestGetDiscordUrl:
    def test_returns_url(self) -> None:
        cfg = {"project": {"ds_project_server_url": "https://discord.gg/test"}}
        assert get_discord_url(cfg) == "https://discord.gg/test"

    def test_missing_returns_empty(self) -> None:
        assert get_discord_url({}) == ""


class TestGetFarewellMessage:
    def test_returns_from_farewell_words(self) -> None:
        cfg = {"project": {"farewell_words": ["Goodbye!", "See ya!"]}}
        assert get_farewell_message(cfg) in ["Goodbye!", "See ya!"]

    def test_missing_farewell_words_uses_default(self) -> None:
        assert get_farewell_message({}) == "Goodbye!"


class TestGetAppCatalog:
    @pytest.fixture()
    def app_config(self) -> dict:
        return {
            "supported": {
                "active": True,
                "entries": [{"name": "EARNAPP", "link": "https://example.com"}],
            },
            "deprecated": {
                "active": False,
                "entries": [{"name": "WIPTER", "additional_details": "broken"}],
            },
        }

    def test_returns_dict(self, app_config: dict) -> None:
        result = get_app_catalog(app_config)
        assert isinstance(result, dict)
        assert "supported" in result

    def test_rich_returns_list(self, app_config: dict) -> None:
        result = get_app_catalog_rich(app_config)
        assert isinstance(result, list)

    def test_missing_category(self) -> None:
        result = get_app_catalog({})
        assert result["supported"] == []


# ---------------------------------------------------------------------------
# Mocked wrappers - services.py uses in-function imports, so mock the
# actual module path rather than an attribute on services.
# ---------------------------------------------------------------------------


class TestLoadConfigs:
    @patch("money4band.core.loader.load_json_config")
    def test_load_configs(self, mock_load) -> None:
        from money4band.services import load_configs

        mock_load.side_effect = [{"m4b": True}, {"app": True}, {"user": True}]
        m, a, u = load_configs("m.json", "a.json", "u.json")
        assert m == {"m4b": True}
        assert mock_load.call_count == 3


class TestIsDockerInstalled:
    @patch("money4band.docker.install.is_docker_installed", return_value=True)
    def test_true(self, _mock) -> None:
        from money4band.services import is_docker_installed

        assert is_docker_installed() is True

    @patch("money4band.docker.install.is_docker_installed", return_value=False)
    def test_false(self, _mock) -> None:
        from money4band.services import is_docker_installed

        assert is_docker_installed() is False


class TestCheckUpdate:
    @patch("money4band.updater.check_for_update", return_value="5.1.0")
    def test_returns_version(self, _mock) -> None:
        from money4band.services import check_update

        assert check_update({}) == "5.1.0"

    @patch("money4band.updater.check_for_update", return_value=None)
    def test_returns_none(self, _mock) -> None:
        from money4band.services import check_update

        assert check_update({}) is None


class TestStartStack:
    @patch("money4band.docker.start.start_stack", return_value=True)
    def test_delegates(self, mock_fn) -> None:
        from money4band.services import start_stack

        assert start_stack("compose.yml", ".env", "main") is True
        mock_fn.assert_called_once()


class TestStopStack:
    @patch("money4band.docker.stop.stop_stack", return_value=True)
    def test_delegates(self, mock_fn) -> None:
        from money4band.services import stop_stack

        assert stop_stack("compose.yml", "main") is True
        mock_fn.assert_called_once()


class TestGetHealthSummary:
    @patch("money4band.docker.monitor.get_stack_health")
    @patch("money4band.docker.helper.get_compose_project_name", return_value="m4b")
    def test_returns_list(self, _proj, mock_health) -> None:
        from money4band.services import get_health_summary

        status = MagicMock(
            name="earnapp", ok=True, health="healthy", restart_count=0, last_error=""
        )
        mock_health.return_value = [status]
        result = get_health_summary()
        assert len(result) == 1


class TestLoadM4bConfig:
    def test_loads_single_config(self, tmp_path: Path) -> None:
        from money4band.services import load_m4b_config

        p = tmp_path / "m4b.json"
        p.write_text(json.dumps({"project": {"project_version": "5.0.0"}}))
        cfg = load_m4b_config(str(p))
        assert cfg["project"]["project_version"] == "5.0.0"


class TestGetStackStatus:
    @patch("money4band.docker.compose_builder.get_compose_files", return_value=[])
    def test_no_compose_files(self, _mock_files) -> None:
        from money4band.services import get_stack_status

        result = get_stack_status()
        assert "No compose files" in result

    @patch("subprocess.run")
    @patch(
        "money4band.docker.compose_builder.get_compose_files",
        return_value=["docker-compose.yaml"],
    )
    @patch(
        "money4band.docker.helper.get_compose_project_name", return_value="money4band"
    )
    def test_returns_ps_output(self, _proj, _files, mock_run) -> None:
        from money4band.services import get_stack_status

        mock_run.return_value = MagicMock(
            returncode=0, stdout="NAME  STATUS\nwatchtower  running"
        )
        result = get_stack_status()
        assert "watchtower" in result


class TestGetGeneratorSummary:
    def test_returns_summary_dict(self, tmp_path: Path) -> None:
        from money4band.services import get_generator_summary

        user = {
            "device_info": {"device_name": "happy_cat"},
            "proxies": {"enabled": False},
            "apps": {
                "earnapp": {"enabled": True},
                "honeygain": {"enabled": False},
            },
            "m4b_dashboard": {"enabled": True, "port": 8088},
        }
        # v5.0 dropped compose_mode toggle; m4b config no longer carries it.
        m4b = {"system": {}}

        user_path = tmp_path / "user.json"
        m4b_path = tmp_path / "m4b.json"
        app_path = tmp_path / "app.json"
        user_path.write_text(json.dumps(user))
        m4b_path.write_text(json.dumps(m4b))
        app_path.write_text(json.dumps({}))

        result = get_generator_summary(str(m4b_path), str(app_path), str(user_path))
        assert result["device_name"] == "happy_cat"
        assert result["proxy_enabled"] is False
        assert "earnapp" in result["enabled_apps"]
        assert "honeygain" not in result["enabled_apps"]
        # compose_mode field removed in v5.0
        assert "compose_mode" not in result


class TestResetUserConfig:
    def test_resets_from_template(self, tmp_path: Path) -> None:
        from money4band.services import reset_user_config

        template = tmp_path / "template.json"
        template.write_text(json.dumps({"clean": True}))
        dest = tmp_path / "config" / "user-config.json"

        reset_user_config(str(dest), template_path=str(template))
        assert json.loads(dest.read_text()) == {"clean": True}


class TestGetAppCatalogRich:
    SAMPLE_APP_CFG: dict[str, Any] = {
        "supported": {
            "active": True,
            "entries": [
                {"name": "EARNAPP", "link": "https://earnapp.com"},
                {"name": "HONEYGAIN", "link": "https://honeygain.com"},
            ],
        },
        "deprecated": {
            "active": False,
            "entries": [{"name": "GRASS", "additional_details": "TOS violations"}],
        },
        "newcomers": {
            "active": True,
            "entries": [{"name": "SPIDE"}],
        },
    }

    def test_rich_sorts_active_first(self) -> None:
        result = get_app_catalog_rich(self.SAMPLE_APP_CFG)
        active_flags = [r["active"] for r in result]
        assert active_flags[0] is True

    def test_rich_contains_app_names(self) -> None:
        result = get_app_catalog_rich(self.SAMPLE_APP_CFG)
        all_names = []
        for group in result:
            all_names.extend(a["name"] for a in group["apps"])
        assert "EARNAPP" in all_names
        assert "GRASS" in all_names


class TestGetSystemInfoStructured:
    _M4B = {
        "project": {"project_version": "5.0.0"},
        "system": {"default_docker_platform": "linux/amd64"},
        "resource_profiles": {
            "profiles": {
                "standard": {
                    "description": "Standard",
                    "cpu_pct": 0.60,
                    "ram_pct": 0.40,
                }
            },
        },
    }
    _APP = {"supported": {"active": True, "entries": [{"name": "A"}]}}
    _USR = {
        "device_info": {
            "os_type": "Linux",
            "detected_architecture": "amd64",
            "detected_docker_arch": "amd64",
        },
        "apps": {"a": {"enabled": True}},
        "proxies": {"enabled": False},
        "watchtower": {"enabled": True},
        "m4b_dashboard": {"enabled": False},
    }

    @patch("money4band.docker.compose_builder.get_compose_files", return_value=[])
    @patch(
        "money4band.system.detector.get_system_memory_and_cores", return_value=(8192, 4)
    )
    @patch("money4band.updater.check_for_update", return_value=None)
    @patch("shutil.which", return_value=None)
    def test_returns_dict_with_expected_keys(self, _which, _upd, _mem, _comp):
        result = get_system_info_structured(self._M4B, self._APP, self._USR)
        assert result["version"] == "5.0.0"
        assert result["docker_installed"] is False
        assert result["enabled_apps"] == ["a"]
        # v5.0: single-file compose; compose_mode field removed entirely.
        assert "compose_mode" not in result
        assert result["compose_files"] == []

    @patch(
        "money4band.docker.compose_builder.get_compose_files",
        return_value=["docker-compose.yaml"],
    )
    @patch(
        "money4band.system.detector.get_system_memory_and_cores",
        return_value=(16384, 8),
    )
    @patch("money4band.updater.check_for_update", return_value="6.0.0")
    @patch("shutil.which", return_value="/usr/bin/docker")
    @patch("money4band.docker.helper.is_docker_daemon_running", return_value=False)
    def test_compose_files_listed_when_generated(
        self, _daemon, _which, _upd, _mem, _comp
    ):
        result = get_system_info_structured(self._M4B, self._APP, self._USR)
        assert result["new_version"] == "6.0.0"
        # v5.0: single-file compose; compose_mode removed; compose_files lists the entry.
        assert "compose_mode" not in result
        assert result["compose_files"] == ["docker-compose.yaml"]


class TestGetSystemInfoText:
    @patch("money4band.system.info.check_for_update", return_value=None)
    @patch(
        "money4band.system.info.detector.get_system_memory_and_cores",
        return_value=(8192, 4),
    )
    @patch("money4band.docker.compose_builder.get_compose_files", return_value=[])
    def test_returns_string_output(self, _comp, _mem, _upd):
        from money4band.services import get_system_info_text

        m4b = {
            "project": {"project_version": "5.0.0"},
            "system": {"default_docker_platform": "linux/amd64"},
            "resource_profiles": {
                "profiles": {
                    "standard": {
                        "description": "Standard",
                        "cpu_pct": 0.60,
                        "ram_pct": 0.40,
                    }
                },
            },
        }
        app_cfg = {"supported": {"active": True, "entries": []}}
        usr_cfg = {
            "device_info": {
                "os_type": "Linux",
                "detected_architecture": "amd64",
                "detected_docker_arch": "amd64",
            },
            "apps": {},
            "proxies": {"enabled": False},
            "watchtower": {"enabled": True},
            "m4b_dashboard": {"enabled": False},
        }
        result = get_system_info_text(m4b, app_cfg, usr_cfg)
        assert isinstance(result, str)
        assert "System Information" in result


class TestStartStopAllStacks:
    @patch("money4band.docker.start.start_stack", return_value=True)
    @patch("money4band.docker.start.is_user_in_docker_group", return_value=True)
    @patch("subprocess.run", return_value=MagicMock(stdout="", returncode=0))
    @patch("builtins.input", return_value="")
    @patch("time.sleep")
    def test_start_all_returns_string(
        self, _sleep, _inp, _sub, _group, _start, tmp_path
    ):
        from money4band.services import start_all_stacks as svc_start_all

        env_file = tmp_path / ".env"
        env_file.write_text("DEVICE_NAME=test\n")
        result = svc_start_all(main_env_file=str(env_file))
        assert isinstance(result, str)

    @patch("money4band.docker.stop.stop_stack", return_value=True)
    @patch("money4band.docker.stop.is_user_in_docker_group", return_value=True)
    @patch("builtins.input", return_value="")
    def test_stop_all_returns_string(self, _inp, _group, _stop):
        from money4band.services import stop_all_stacks as svc_stop_all

        result = svc_stop_all()
        assert isinstance(result, str)
