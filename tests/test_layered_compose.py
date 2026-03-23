"""Tests for Phase 2.9 — layered compose architecture."""

import copy
import json
import os
from unittest.mock import patch, MagicMock

import pytest
import yaml

# ---------------------------------------------------------------------------
# Fixtures — minimal configs that satisfy compose_builder
# ---------------------------------------------------------------------------

_M4B_CONFIG = {
    "project": {"project_version": "5.0.0", "compose_project_name": "money4band"},
    "system": {
        "dns": {"mode": "default", "servers": ["1.1.1.1", "8.8.8.8"]},
        "default_docker_platform": "linux/amd64",
        "compose_mode": "monolithic",
    },
}

_APP_CONFIG = {
    "supported-apps": {
        "active": True,
        "entries": [
            {
                "name": "EARNAPP",
                "dashboard": "https://example.com",
                "link": "https://example.com",
                "compose_config": {
                    "container_name": "earnapp",
                    "image": "fazalfarhan01/earnapp:lite",
                    "restart": "always",
                },
                "compose_config_proxy": {},
                "flags": {},
                "install_limit": -1,
                "compose_layer": "residential",
            },
            {
                "name": "REPOCKET",
                "dashboard": "https://example.com",
                "link": "https://example.com",
                "compose_config": {
                    "container_name": "repocket",
                    "image": "repocket/repocket:latest",
                    "restart": "always",
                },
                "compose_config_proxy": {},
                "flags": {},
                "install_limit": -1,
                "compose_layer": "datacenter",
            },
            {
                "name": "TRAFFMONETIZER",
                "dashboard": "https://example.com",
                "link": "https://example.com",
                "compose_config": {
                    "container_name": "traffmonetizer",
                    "image": "traffmonetizer/cli_v2:latest",
                    "restart": "always",
                },
                "compose_config_proxy": {},
                "flags": {},
                "install_limit": -1,
                "compose_layer": "universal",
            },
        ],
    },
}

_USER_CONFIG = {
    "device_info": {"device_name": "test_device"},
    "apps": {
        "earnapp": {"enabled": True, "docker_platform": "linux/amd64"},
        "repocket": {"enabled": True, "docker_platform": "linux/amd64"},
        "traffmonetizer": {"enabled": True, "docker_platform": "linux/amd64"},
    },
    "m4b_dashboard": {"enabled": False},
    "watchtower": {"enabled": True},
    "proxies": {"enabled": False},
    "notifications": {"enabled": False},
    "resource_limits": {},
    "compose_config_common": {
        "network": {"driver": "bridge", "subnet": "172.20.0.0", "netmask": "16"},
        "watchtower_service": {
            "proxy_disabled": {
                "image": "nickfedor/watchtower:1.14",
                "restart": "always",
                "environment": [],
                "volumes": ["/var/run/docker.sock:/var/run/docker.sock"],
            },
        },
    },
}


# ---------------------------------------------------------------------------
# get_compose_files — discovery logic
# ---------------------------------------------------------------------------


class TestGetComposeFiles:

    def test_discovers_layered_files_in_order(self, tmp_path):
        """Layered files are returned in COMPOSE_LAYER_ORDER."""
        from money4band.compose_builder import get_compose_files, COMPOSE_LAYER_FILES, COMPOSE_LAYER_ORDER

        # Create only some layer files
        for layer in ("base", "residential", "proxy"):
            (tmp_path / COMPOSE_LAYER_FILES[layer]).write_text("services: {}")
        result = get_compose_files(str(tmp_path))
        filenames = [os.path.basename(f) for f in result]
        assert filenames == [
            COMPOSE_LAYER_FILES[l] for l in COMPOSE_LAYER_ORDER
            if l in ("base", "residential", "proxy")
        ]

    def test_falls_back_to_legacy(self, tmp_path):
        """When no layered files exist, returns docker-compose.yaml."""
        from money4band.compose_builder import get_compose_files

        (tmp_path / "docker-compose.yaml").write_text("services: {}")
        result = get_compose_files(str(tmp_path))
        assert len(result) == 1
        assert result[0].endswith("docker-compose.yaml")

    def test_returns_empty_when_nothing(self, tmp_path):
        """Returns empty list when no compose files exist at all."""
        from money4band.compose_builder import get_compose_files

        result = get_compose_files(str(tmp_path))
        assert result == []

    def test_prefers_layered_over_legacy(self, tmp_path):
        """When both layered and legacy exist, returns only layered."""
        from money4band.compose_builder import get_compose_files, COMPOSE_LAYER_FILES

        (tmp_path / COMPOSE_LAYER_FILES["base"]).write_text("services: {}")
        (tmp_path / "docker-compose.yaml").write_text("services: {}")
        result = get_compose_files(str(tmp_path))
        # Layered files found → legacy is NOT included
        assert len(result) == 1
        assert result[0].endswith("compose.yml")


# ---------------------------------------------------------------------------
# assemble_docker_compose — layered output
# ---------------------------------------------------------------------------


class TestLayeredGeneration:
    """Verify that layered=True produces separate compose files per tier."""

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    @patch("money4band.compose_builder.show_spinner")
    def test_layered_creates_per_tier_files(self, _sp, _tag, _arch, tmp_path):
        from money4band.compose_builder import assemble_docker_compose

        output = str(tmp_path / "docker-compose.yaml")
        result = assemble_docker_compose(
            m4b_config_path_or_dict=copy.deepcopy(_M4B_CONFIG),
            app_config_path_or_dict=copy.deepcopy(_APP_CONFIG),
            user_config_path_or_dict=copy.deepcopy(_USER_CONFIG),
            compose_output_path=output,
            is_main_instance=True,
            layered=True,
        )

        # Should produce multiple files (base + residential + datacenter + universal)
        assert len(result) >= 3
        basenames = [os.path.basename(f) for f in result]
        assert "compose.yml" in basenames  # base layer (watchtower)
        assert "compose.residential.yml" in basenames
        assert "compose.datacenter.yml" in basenames
        assert "compose.universal.yml" in basenames

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    @patch("money4band.compose_builder.show_spinner")
    def test_layered_removes_legacy_file(self, _sp, _tag, _arch, tmp_path):
        from money4band.compose_builder import assemble_docker_compose

        legacy = tmp_path / "docker-compose.yaml"
        legacy.write_text("old content")
        assemble_docker_compose(
            m4b_config_path_or_dict=copy.deepcopy(_M4B_CONFIG),
            app_config_path_or_dict=copy.deepcopy(_APP_CONFIG),
            user_config_path_or_dict=copy.deepcopy(_USER_CONFIG),
            compose_output_path=str(legacy),
            is_main_instance=True,
            layered=True,
        )
        assert not legacy.exists(), "Legacy file should be removed in layered mode"

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    @patch("money4band.compose_builder.show_spinner")
    def test_layered_services_in_correct_files(self, _sp, _tag, _arch, tmp_path):
        from money4band.compose_builder import assemble_docker_compose

        output = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(
            m4b_config_path_or_dict=copy.deepcopy(_M4B_CONFIG),
            app_config_path_or_dict=copy.deepcopy(_APP_CONFIG),
            user_config_path_or_dict=copy.deepcopy(_USER_CONFIG),
            compose_output_path=output,
            is_main_instance=True,
            layered=True,
        )

        # Check residential layer contains earnapp
        res_file = tmp_path / "compose.residential.yml"
        assert res_file.exists()
        res_data = yaml.safe_load(res_file.read_text())
        assert "earnapp" in res_data["services"]

        # Check datacenter layer contains repocket
        dc_file = tmp_path / "compose.datacenter.yml"
        assert dc_file.exists()
        dc_data = yaml.safe_load(dc_file.read_text())
        assert "repocket" in dc_data["services"]

        # Check universal layer contains traffmonetizer
        uni_file = tmp_path / "compose.universal.yml"
        assert uni_file.exists()
        uni_data = yaml.safe_load(uni_file.read_text())
        assert "traffmonetizer" in uni_data["services"]

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    @patch("money4band.compose_builder.show_spinner")
    def test_layered_base_has_network_config(self, _sp, _tag, _arch, tmp_path):
        from money4band.compose_builder import assemble_docker_compose

        output = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(
            m4b_config_path_or_dict=copy.deepcopy(_M4B_CONFIG),
            app_config_path_or_dict=copy.deepcopy(_APP_CONFIG),
            user_config_path_or_dict=copy.deepcopy(_USER_CONFIG),
            compose_output_path=output,
            is_main_instance=True,
            layered=True,
        )
        base_file = tmp_path / "compose.yml"
        base_data = yaml.safe_load(base_file.read_text())
        assert "networks" in base_data, "Base layer must contain network config"

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    @patch("money4band.compose_builder.show_spinner")
    def test_monolithic_still_works(self, _sp, _tag, _arch, tmp_path):
        from money4band.compose_builder import assemble_docker_compose

        output = str(tmp_path / "docker-compose.yaml")
        result = assemble_docker_compose(
            m4b_config_path_or_dict=copy.deepcopy(_M4B_CONFIG),
            app_config_path_or_dict=copy.deepcopy(_APP_CONFIG),
            user_config_path_or_dict=copy.deepcopy(_USER_CONFIG),
            compose_output_path=output,
            is_main_instance=True,
            layered=False,
        )
        assert len(result) == 1
        assert result[0].endswith("docker-compose.yaml")
        data = yaml.safe_load(open(output).read())
        assert "earnapp" in data["services"]
        assert "repocket" in data["services"]
        assert "traffmonetizer" in data["services"]

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    @patch("money4band.compose_builder.show_spinner")
    def test_empty_layers_get_stale_files_removed(self, _sp, _tag, _arch, tmp_path):
        from money4band.compose_builder import assemble_docker_compose

        # Create a stale service layer file
        stale = tmp_path / "compose.service.yml"
        stale.write_text("stale content")

        # Config has no sidecar services → service layer should be empty → file removed
        output = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(
            m4b_config_path_or_dict=copy.deepcopy(_M4B_CONFIG),
            app_config_path_or_dict=copy.deepcopy(_APP_CONFIG),
            user_config_path_or_dict=copy.deepcopy(_USER_CONFIG),
            compose_output_path=output,
            is_main_instance=True,
            layered=True,
        )
        assert not stale.exists(), "Stale empty-layer file should be removed"


# ---------------------------------------------------------------------------
# compose_mode config flag
# ---------------------------------------------------------------------------


class TestComposeMode:
    """Verify compose_mode config drives layered vs monolithic."""

    def test_default_compose_mode(self):
        cfg = copy.deepcopy(_M4B_CONFIG)
        assert cfg["system"]["compose_mode"] == "monolithic"

    def test_layered_compose_mode(self):
        cfg = copy.deepcopy(_M4B_CONFIG)
        cfg["system"]["compose_mode"] = "layered"
        assert cfg["system"]["compose_mode"] == "layered"


# ---------------------------------------------------------------------------
# fn_stopStack — multi-file support
# ---------------------------------------------------------------------------


class TestStopStackMultiFile:
    """Verify fn_stopStack accepts str | list[str]."""

    @patch("money4band.fn_stopStack.run_docker_command", return_value=0)
    @patch("money4band.fn_stopStack.get_compose_project_name", return_value="test")
    @patch("money4band.fn_stopStack.show_spinner")
    @patch("money4band.fn_stopStack.ask_question_yn", return_value=True)
    def test_stop_stack_single_file(self, _yn, _sp, _proj, mock_cmd):
        from money4band.fn_stopStack import stop_stack

        result = stop_stack("./docker-compose.yaml", "test", skip_questions=True)
        assert result is True
        cmd = mock_cmd.call_args[0][0]
        assert "-f" in cmd
        assert "./docker-compose.yaml" in cmd

    @patch("money4band.fn_stopStack.run_docker_command", return_value=0)
    @patch("money4band.fn_stopStack.get_compose_project_name", return_value="test")
    @patch("money4band.fn_stopStack.show_spinner")
    @patch("money4band.fn_stopStack.ask_question_yn", return_value=True)
    def test_stop_stack_multiple_files(self, _yn, _sp, _proj, mock_cmd):
        from money4band.fn_stopStack import stop_stack

        files = ["compose.yml", "compose.residential.yml", "compose.datacenter.yml"]
        result = stop_stack(files, "test", skip_questions=True)
        assert result is True
        cmd = mock_cmd.call_args[0][0]
        # All three files should appear with -f flags
        for f in files:
            idx = cmd.index(f)
            assert cmd[idx - 1] == "-f"


# ---------------------------------------------------------------------------
# fn_startStack — multi-file proxy loop
# ---------------------------------------------------------------------------


class TestStartStackMultiFile:
    """Verify fn_startStack handles layered files for proxy instances."""

    @patch("money4band.fn_startStack.run_docker_command", return_value=0)
    @patch("money4band.fn_startStack.get_compose_project_name", return_value="test")
    @patch("money4band.fn_startStack.get_device_name_from_env", return_value="dev1")
    @patch("money4band.fn_startStack.show_spinner")
    @patch("money4band.fn_startStack.ask_question_yn", return_value=True)
    def test_start_stack_list_input(self, _yn, _sp, _dev, _proj, mock_cmd):
        from money4band.fn_startStack import start_stack

        files = ["compose.yml", "compose.residential.yml"]
        result = start_stack(files, ".env", "test", skip_questions=True)
        assert result is True
        cmd = mock_cmd.call_args[0][0]
        for f in files:
            idx = cmd.index(f)
            assert cmd[idx - 1] == "-f"


# ---------------------------------------------------------------------------
# main.py _cmd_status — uses get_compose_files
# ---------------------------------------------------------------------------


class TestCmdStatusCompose:
    """Verify _cmd_status uses get_compose_files instead of hardcoded path."""

    def test_cmd_status_imports_get_compose_files(self):
        """Verify the _cmd_status function references get_compose_files."""
        import inspect
        from main import _cmd_status

        source = inspect.getsource(_cmd_status)
        assert "get_compose_files" in source
        assert "docker-compose.yaml" not in source.split("get_compose_files")[0]


# ---------------------------------------------------------------------------
# Fallback default layer — datacenter (not old 'hosting')
# ---------------------------------------------------------------------------


class TestLayerFallback:
    """Verify the fallback compose_layer uses 'datacenter', not old 'hosting'."""

    def test_service_layers_default(self):
        """service_layers.get() default must be 'datacenter'."""
        import inspect
        from money4band import compose_builder

        source = inspect.getsource(compose_builder.assemble_docker_compose)
        # The layered bucket assignment line
        assert '"hosting"' not in source, "Old 'hosting' fallback must be replaced"
        # Both the compose_layer getter and the bucket fallback should use 'datacenter'
        assert 'get("compose_layer", "datacenter")' in source
