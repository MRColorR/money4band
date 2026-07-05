"""Tests for money4band.docker.compose_builder - single-file generation + profiles."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from money4band.docker.compose_builder import (
    RESERVED_MONITORING_PROFILE,
    RESERVED_PROXY_PROFILE,
    assemble_docker_compose,
    get_compose_files,
    split_image_ref,
    substitute_port_placeholders,
)


class TestSplitImageRef:
    """Regression: a tagless image used to crash assembly with
    'not enough values to unpack (expected 2, got 1)' via image.split(':')."""

    def test_tagless_image_defaults_to_latest(self):
        assert split_image_ref("bearshare/bearshare") == (
            "bearshare/bearshare",
            "latest",
        )
        assert split_image_ref("nezha123/titan-edge") == (
            "nezha123/titan-edge",
            "latest",
        )

    def test_tagged_image(self):
        assert split_image_ref("honeygain/honeygain:latest") == (
            "honeygain/honeygain",
            "latest",
        )
        assert split_image_ref("repo/img:v2.1") == ("repo/img", "v2.1")

    def test_registry_with_port(self):
        # The ':' in host:port must not be mistaken for a tag separator.
        assert split_image_ref("host:5000/repo/img") == (
            "host:5000/repo/img",
            "latest",
        )
        assert split_image_ref("host:5000/repo/img:v2") == (
            "host:5000/repo/img",
            "v2",
        )


# ---------------------------------------------------------------------------
# get_compose_files
# ---------------------------------------------------------------------------


class TestGetComposeFiles:
    def test_returns_single_compose_when_present(self, tmp_path: Path) -> None:
        (tmp_path / "docker-compose.yaml").write_text("services: {}")
        result = get_compose_files(str(tmp_path))
        assert result == [str(tmp_path / "docker-compose.yaml")]

    def test_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        assert get_compose_files(str(tmp_path)) == []

    def test_legacy_layer_files_ignored(self, tmp_path: Path) -> None:
        """v5 ignores leftover layered files - generator cleans them up."""
        for legacy in (
            "compose.yml",
            "compose.residential.yml",
            "compose.datacenter.yml",
        ):
            (tmp_path / legacy).write_text("services: {}")
        # No docker-compose.yaml present yet.
        result = get_compose_files(str(tmp_path))
        assert result == []


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
# assemble_docker_compose - single-file output with profiles: arrays
# ---------------------------------------------------------------------------


def _make_configs(tmp_path: Path) -> tuple[dict, dict, dict]:
    """Build minimal m4b, app, and user configs for assembly tests."""
    m4b = {
        "system": {
            "default_docker_platform": "linux/amd64",
            "sleep_time": 0,
        },
        "project": {"project_version": "5.0.0"},
    }
    app = {
        "supported": {
            "active": True,
            "entries": [
                {
                    "name": "EARNAPP",
                    "compose_config": {
                        "image": "fazalfarhan01/earnapp:lite",
                        "restart": "unless-stopped",
                    },
                    "profile": "residential",
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
    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @patch("money4band.docker.compose_builder.http_client")
    def test_single_file_output(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        result = assemble_docker_compose(m4b, app, user, out, is_main_instance=True)
        assert result == [out]
        assert os.path.isfile(out)
        data = yaml.safe_load(Path(out).read_text())
        assert "earnapp" in data["services"]

    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @patch("money4band.docker.compose_builder.http_client")
    def test_app_gets_profile_from_bundle(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        assert data["services"]["earnapp"]["profiles"] == ["residential"]

    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @patch("money4band.docker.compose_builder.http_client")
    def test_app_default_profile_when_field_missing(
        self, _http, _arch, tmp_path: Path
    ) -> None:
        m4b, app, user = _make_configs(tmp_path)
        # Drop the explicit field - generator should fall back to datacenter.
        del app["supported"]["entries"][0]["profile"]
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        assert data["services"]["earnapp"]["profiles"] == ["datacenter"]

    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @patch("money4band.docker.compose_builder.http_client")
    def test_watchtower_uses_monitoring_profile(
        self, _http, _arch, tmp_path: Path
    ) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=True)
        data = yaml.safe_load(Path(out).read_text())
        assert "watchtower" in data["services"]
        assert data["services"]["watchtower"]["profiles"] == [
            RESERVED_MONITORING_PROFILE
        ]

    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @patch("money4band.docker.compose_builder.http_client")
    def test_proxy_uses_proxy_profile(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        user["proxies"]["enabled"] = True
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=True)
        data = yaml.safe_load(Path(out).read_text())
        assert "proxy" in data["services"]
        assert data["services"]["proxy"]["profiles"] == [RESERVED_PROXY_PROFILE]

    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @patch("money4band.docker.compose_builder.http_client")
    def test_watchtower_not_added_for_non_main(
        self, _http, _arch, tmp_path: Path
    ) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        assert "watchtower" not in data["services"]

    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=None
    )
    @patch("money4band.docker.compose_builder.http_client")
    def test_arch_unknown_falls_back_to_default_platform(
        self, _http, _arch, tmp_path: Path
    ) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        with patch(
            "money4band.docker.compose_builder.check_img_arch_support",
            return_value=None,
        ):
            assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        assert data["services"]["earnapp"]["platform"] == "linux/amd64"

    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=False
    )
    @patch("money4band.docker.compose_builder.get_compatible_tag", return_value=None)
    @patch("money4band.docker.compose_builder.write_json")
    @patch("money4band.docker.compose_builder.http_client")
    def test_incompatible_arch_disables_app(
        self, _http, _write, _tag, _arch, tmp_path: Path
    ) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        assert "earnapp" not in data.get("services", {})

    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @patch("money4band.docker.compose_builder.http_client")
    def test_security_opt_added(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        for svc in data["services"].values():
            assert "no-new-privileges:true" in svc.get("security_opt", [])

    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @patch("money4band.docker.compose_builder.http_client")
    def test_dashboard_not_in_compose(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        user["m4b_dashboard"]["enabled"] = True
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=True)
        data = yaml.safe_load(Path(out).read_text())
        assert "m4bwebdashboard" not in data["services"]

    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @patch("money4band.docker.compose_builder.http_client")
    def test_custom_dns_applied(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        user["settings"] = {"dns_mode": "custom", "dns_servers": ["1.1.1.1", "8.8.8.8"]}
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        for svc in data["services"].values():
            assert svc["dns"] == ["1.1.1.1", "8.8.8.8"]

    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @patch("money4band.docker.compose_builder.http_client")
    def test_network_config_present(self, _http, _arch, tmp_path: Path) -> None:
        m4b, app, user = _make_configs(tmp_path)
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        data = yaml.safe_load(Path(out).read_text())
        assert "networks" in data
        assert "default" in data["networks"]
        assert data["networks"]["default"]["driver"] == "bridge"

    @patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @patch("money4band.docker.compose_builder.http_client")
    def test_legacy_layer_files_cleaned_up(self, _http, _arch, tmp_path: Path) -> None:
        """v4-era layered files are removed by the v5 generator."""
        m4b, app, user = _make_configs(tmp_path)
        # Seed legacy layered files from a v4 install.
        for legacy in (
            "compose.yml",
            "compose.residential.yml",
            "compose.datacenter.yml",
        ):
            (tmp_path / legacy).write_text("# stale v4-era layer file\n")
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, app, user, out, is_main_instance=False)
        # All legacy layer files gone.
        for legacy in (
            "compose.yml",
            "compose.residential.yml",
            "compose.datacenter.yml",
        ):
            assert not (tmp_path / legacy).exists()
        # Single new compose file written.
        assert os.path.isfile(out)
