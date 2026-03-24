"""Tests for money4band.compose_builder — Docker Compose assembly."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from money4band.compose_builder import (
    COMPOSE_LAYER_FILES,
    assemble_docker_compose,
    get_compose_files,
    substitute_port_placeholders,
)

# ---------------------------------------------------------------------------
# get_compose_files
# ---------------------------------------------------------------------------


class TestGetComposeFiles:
    def test_returns_layered_files_in_order(self, tmp_path: Path) -> None:
        for layer in ("base", "residential", "service"):
            (tmp_path / COMPOSE_LAYER_FILES[layer]).write_text("services: {}")
        result = get_compose_files(str(tmp_path))
        assert len(result) == 3
        # base must come before service
        assert result.index(str(tmp_path / "compose.yml")) < result.index(
            str(tmp_path / "compose.service.yml")
        )

    def test_falls_back_to_legacy(self, tmp_path: Path) -> None:
        (tmp_path / "docker-compose.yaml").write_text("services: {}")
        result = get_compose_files(str(tmp_path))
        assert len(result) == 1
        assert "docker-compose.yaml" in result[0]

    def test_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        assert get_compose_files(str(tmp_path)) == []

    def test_layered_takes_priority_over_legacy(self, tmp_path: Path) -> None:
        (tmp_path / COMPOSE_LAYER_FILES["base"]).write_text("services: {}")
        (tmp_path / "docker-compose.yaml").write_text("services: {}")
        result = get_compose_files(str(tmp_path))
        assert len(result) == 1
        assert "compose.yml" in result[0]


# ---------------------------------------------------------------------------
# substitute_port_placeholders
# ---------------------------------------------------------------------------


class TestSubstitutePortPlaceholders:
    def test_substitutes_env_placeholder(self) -> None:
        result = substitute_port_placeholders(["${APP_PORT}:8080"], [9090])
        assert result == ["9090:8080"]

    def test_non_placeholder_kept(self) -> None:
        result = substitute_port_placeholders(["3000:3000"], [9090])
        assert result == ["3000:3000"]

    def test_wraps_around_ports(self) -> None:
        result = substitute_port_placeholders(
            ["${A}:80", "${B}:443", "${C}:8080"], [9000, 9001]
        )
        assert result == ["9000:80", "9001:443", "9000:8080"]

    def test_empty_ports_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            substitute_port_placeholders(["${A}:80"], [])


# ---------------------------------------------------------------------------
# assemble_docker_compose — minimal configs, mocked arch checks
# ---------------------------------------------------------------------------


def _make_configs(tmp_path: Path) -> tuple[dict, dict, dict]:
    """Build minimal m4b, app, and user configs for assembly tests."""
    m4b = {
        "system": {
            "default_docker_platform": "linux/amd64",
            "sleep_time": 0,
            "dns": {"mode": "default"},
        },
        "project": {"project_version": "5.0.0"},
    }
    app = {
        "supported-apps": {
            "active": True,
            "entries": [
                {
                    "name": "EARNAPP",
                    "compose_config": {
                        "image": "fazalfarhan01/earnapp:lite",
                        "restart": "unless-stopped",
                    },
                    "compose_layer": "residential",
                },
            ],
        },
    }
    user = {
        "apps": {
            "earnapp": {
                "enabled": True,
                "docker_platform": "linux/amd64",
            },
        },
        "proxies": {"enabled": False},
        "watchtower": {"enabled": True},
        "notifications": {"enabled": False},
        "m4b_dashboard": {"enabled": False},
        "compose_config_common": {
            "watchtower_service": {
                "proxy_disabled": {
                    "image": "containrrr/watchtower:latest",
                    "restart": "unless-stopped",
                    "environment": [],
                    "labels": [],
                },
                "proxy_enabled": {
                    "image": "containrrr/watchtower:latest",
                    "restart": "unless-stopped",
                    "environment": [],
                    "labels": [],
                },
            },
            "proxy_service": {
                "image": "tun2socks:latest",
                "restart": "unless-stopped",
            },
            "network": {
                "driver": "bridge",
                "subnet": "172.28.0.0",
                "netmask": "16",
            },
        },
    }
    return m4b, app, user


class TestAssembleDockerCompose:
    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.http_client")
    def test_monolithic_output(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        result = assemble_docker_compose(m4b, app, user, out, is_main_instance=True)
        assert len(result) == 1
        assert os.path.isfile(out)
        data = yaml.safe_load(Path(out).read_text())
        assert "earnapp" in data["services"]

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.http_client")
    def test_layered_output(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        result = assemble_docker_compose(
            m4b, app, user, out, is_main_instance=True, layered=True
        )
        assert len(result) >= 1
        for f in result:
            assert os.path.isfile(f)

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.http_client")
    def test_watchtower_added_for_main(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=True)
        data = yaml.safe_load(Path(out).read_text())
        assert "watchtower" in data["services"]

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.http_client")
    def test_watchtower_not_added_for_non_main(
        self, _http, _arch, tmp_path: Path
    ) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        assert "watchtower" not in data["services"]

    @patch("money4band.compose_builder.check_img_arch_support", return_value=None)
    @patch("money4band.compose_builder.http_client")
    def test_arch_unknown_falls_back_to_default_platform(
        self, _http, _arch, tmp_path: Path
    ) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        with patch(
            "money4band.compose_builder.check_img_arch_support", return_value=None
        ):
            assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        assert data["services"]["earnapp"]["platform"] == "linux/amd64"

    @patch("money4band.compose_builder.check_img_arch_support", return_value=False)
    @patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    @patch("money4band.compose_builder.write_json")
    @patch("money4band.compose_builder.http_client")
    def test_incompatible_arch_disables_app(
        self, _http, _write, _tag, _arch, tmp_path: Path
    ) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        assert "earnapp" not in data.get("services", {})

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.http_client")
    def test_security_opt_added(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        for svc in data["services"].values():
            assert "no-new-privileges:true" in svc.get("security_opt", [])

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.http_client")
    def test_dashboard_not_in_compose(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        user["m4b_dashboard"]["enabled"] = True
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=True)
        data = yaml.safe_load(Path(out).read_text())
        assert "m4bwebdashboard" not in data["services"]

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.http_client")
    def test_custom_dns_applied(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        m4b["system"]["dns"] = {"mode": "custom", "servers": ["1.1.1.1", "8.8.8.8"]}
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        for svc in data["services"].values():
            assert svc["dns"] == ["1.1.1.1", "8.8.8.8"]

    @patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @patch("money4band.compose_builder.http_client")
    def test_network_config_present(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        assert "networks" in data
        assert "default" in data["networks"]
        assert data["networks"]["default"]["driver"] == "bridge"
