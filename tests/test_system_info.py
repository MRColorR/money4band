"""Tests for centralised DNS configuration and system info dashboard."""

import copy
import json
import os
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_M4B_CONFIG = {
    "project": {"project_version": "5.0.0"},
    "system": {
        "dns": {
            "mode": "default",
            "servers": ["1.1.1.1", "8.8.8.8"],
            "available_modes": [
                "default", "cloudflare", "cloudflare-security",
                "google", "quad9", "quad9-unfiltered",
                "opendns", "dns4eu", "dns4eu-unfiltered", "custom",
            ],
            "presets": {
                "cloudflare": ["1.1.1.1", "1.0.0.1"],
                "cloudflare-security": ["1.1.1.2", "1.0.0.2"],
                "google": ["8.8.8.8", "8.8.4.4"],
                "quad9": ["9.9.9.9", "149.112.112.112"],
                "quad9-unfiltered": ["9.9.9.10", "149.112.112.10"],
                "opendns": ["208.67.222.222", "208.67.220.220"],
                "dns4eu": ["86.54.11.1"],
                "dns4eu-unfiltered": ["86.54.11.100"],
            },
            "default_servers": ["1.1.1.1", "8.8.8.8"],
        },
        "default_docker_platform": "linux/amd64",
        "arch_map": {"amd64": "amd64"},
        "os_map": {"linux": "Linux"},
    },
    "resource_profiles": {
        "active": "low",
        "profiles": {
            "low": {"description": "Default", "cpu_factor": 1.0, "ram_pct": 0.1875},
        },
    },
}

_APP_CONFIG = {
    "supported-apps": {
        "active": True,
        "entries": [
            {
                "name": "TESTAPP",
                "dashboard": "https://example.com",
                "link": "https://example.com",
                "compose_config": {
                    "container_name": "test",
                    "image": "test:latest",
                    "restart": "always",
                },
                "compose_config_proxy": {},
                "flags": {},
                "install_limit": -1,
                "compose_layer": "residential",
            }
        ],
    }
}

_USER_CONFIG = {
    "device_info": {
        "os_type": "Linux",
        "detected_architecture": "amd64",
        "detected_docker_arch": "amd64",
    },
    "apps": {"testapp": {"enabled": True, "docker_platform": "linux/amd64"}},
    "m4b_dashboard": {"enabled": False},
    "watchtower": {"enabled": True},
    "proxies": {"enabled": False},
    "notifications": {"enabled": False},
    "resource_limits": {},
    "compose_config_common": {
        "network": {"driver": "bridge", "subnet": "172.20.0.0", "netmask": "16"},
    },
}


# ---------------------------------------------------------------------------
# DNS config read/write
# ---------------------------------------------------------------------------


class TestDNSConfig:
    def test_get_dns_config_default(self):
        from money4band.system_info import get_dns_config

        cfg = copy.deepcopy(_M4B_CONFIG)
        dns = get_dns_config(cfg)
        assert dns["mode"] == "default"
        assert "1.1.1.1" in dns["servers"]

    def test_get_dns_config_missing_returns_default(self):
        from money4band.system_info import get_dns_config

        cfg = {"system": {}}
        dns = get_dns_config(cfg)
        assert dns["mode"] == "default"

    def test_set_dns_mode_custom(self, tmp_path):
        from money4band.system_info import set_dns_mode

        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(copy.deepcopy(_M4B_CONFIG)))

        set_dns_mode(str(cfg_path), "custom", ["9.9.9.9", "149.112.112.112"])

        result = json.loads(cfg_path.read_text())
        assert result["system"]["dns"]["mode"] == "custom"
        assert result["system"]["dns"]["servers"] == ["9.9.9.9", "149.112.112.112"]

    def test_set_dns_mode_default(self, tmp_path):
        from money4band.system_info import set_dns_mode

        cfg = copy.deepcopy(_M4B_CONFIG)
        cfg["system"]["dns"]["mode"] = "custom"
        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(cfg))

        set_dns_mode(str(cfg_path), "default")

        result = json.loads(cfg_path.read_text())
        assert result["system"]["dns"]["mode"] == "default"

    def test_set_dns_mode_invalid_raises(self, tmp_path):
        from money4band.system_info import set_dns_mode

        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(copy.deepcopy(_M4B_CONFIG)))

        with pytest.raises(ValueError, match="Invalid DNS mode"):
            set_dns_mode(str(cfg_path), "invalid")

    def test_set_dns_mode_rejects_invalid_ipv4(self, tmp_path):
        from money4band.system_info import set_dns_mode

        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(copy.deepcopy(_M4B_CONFIG)))

        with pytest.raises(ValueError, match="Invalid IPv4"):
            set_dns_mode(str(cfg_path), "custom", ["not-an-ip"])

    def test_set_dns_mode_rejects_partial_bad_list(self, tmp_path):
        from money4band.system_info import set_dns_mode

        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(copy.deepcopy(_M4B_CONFIG)))

        with pytest.raises(ValueError, match="999.999.999.999"):
            set_dns_mode(str(cfg_path), "custom", ["1.1.1.1", "999.999.999.999"])

    def test_set_dns_mode_rejects_empty_string(self, tmp_path):
        from money4band.system_info import set_dns_mode

        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(copy.deepcopy(_M4B_CONFIG)))

        with pytest.raises(ValueError, match="Invalid IPv4"):
            set_dns_mode(str(cfg_path), "custom", [""])

    def test_set_dns_mode_rejects_hostname(self, tmp_path):
        from money4band.system_info import set_dns_mode

        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(copy.deepcopy(_M4B_CONFIG)))

        with pytest.raises(ValueError, match="Invalid IPv4"):
            set_dns_mode(str(cfg_path), "custom", ["dns.google.com"])

    def test_set_dns_mode_accepts_valid_ips(self, tmp_path):
        from money4band.system_info import set_dns_mode

        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(copy.deepcopy(_M4B_CONFIG)))

        set_dns_mode(str(cfg_path), "custom", ["8.8.4.4", "208.67.222.222"])

        result = json.loads(cfg_path.read_text())
        assert result["system"]["dns"]["servers"] == ["8.8.4.4", "208.67.222.222"]


# ---------------------------------------------------------------------------
# IPv4 validation unit tests
# ---------------------------------------------------------------------------


class TestIPv4Validation:
    @pytest.mark.parametrize(
        "ip",
        [
            "1.1.1.1",
            "8.8.8.8",
            "0.0.0.0",
            "255.255.255.255",
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "127.0.0.1",
        ],
    )
    def test_valid_ipv4(self, ip):
        from money4band.system_info import is_valid_ipv4

        assert is_valid_ipv4(ip) is True

    @pytest.mark.parametrize(
        "ip",
        [
            "",
            "not-an-ip",
            "256.1.1.1",
            "1.2.3.4.5",
            "1.2.3",
            "1.2.3.999",
            "dns.google.com",
            "::1",
            "2001:4860:4860::8888",
            "1.1.1.1:53",
            " 1.1.1.1",
            "1.1.1.1 ",
            "abc",
        ],
    )
    def test_invalid_ipv4(self, ip):
        from money4band.system_info import is_valid_ipv4

        assert is_valid_ipv4(ip) is False


# ---------------------------------------------------------------------------
# compose_builder DNS injection
# ---------------------------------------------------------------------------


class TestComposeDNSInjection:
    def _assemble(self, m4b_config, tmp_path):
        """Helper: run assemble_docker_compose with given m4b_config."""
        from money4band.compose_builder import assemble_docker_compose

        app_cfg = copy.deepcopy(_APP_CONFIG)
        usr_cfg = copy.deepcopy(_USER_CONFIG)
        output = str(tmp_path / "docker-compose.yaml")

        with (
            patch(
                "money4band.compose_builder.check_img_arch_support", return_value=True
            ),
            patch("money4band.compose_builder.get_compatible_tag", return_value=None),
            patch("money4band.compose_builder.show_spinner"),
        ):
            files = assemble_docker_compose(
                m4b_config,
                app_cfg,
                usr_cfg,
                compose_output_path=output,
                is_main_instance=False,
            )
        return files

    def test_default_mode_strips_dns(self, tmp_path):
        """When mode=default, no 'dns' key should appear in services."""
        import yaml

        cfg = copy.deepcopy(_M4B_CONFIG)
        cfg["system"]["dns"]["mode"] = "default"
        files = self._assemble(cfg, tmp_path)

        with open(files[0]) as f:
            compose = yaml.safe_load(f)
        for svc_name, svc in compose["services"].items():
            assert "dns" not in svc, f"Service '{svc_name}' should not have dns key"

    def test_custom_mode_injects_dns(self, tmp_path):
        """When mode=custom, every service should have the configured DNS servers."""
        import yaml

        cfg = copy.deepcopy(_M4B_CONFIG)
        cfg["system"]["dns"] = {"mode": "custom", "servers": ["9.9.9.9"]}
        files = self._assemble(cfg, tmp_path)

        with open(files[0]) as f:
            compose = yaml.safe_load(f)
        for svc_name, svc in compose["services"].items():
            assert svc.get("dns") == ["9.9.9.9"], (
                f"Service '{svc_name}' should have custom DNS"
            )

    def test_custom_mode_multiple_servers(self, tmp_path):
        import yaml

        servers = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
        cfg = copy.deepcopy(_M4B_CONFIG)
        cfg["system"]["dns"] = {"mode": "custom", "servers": servers}
        files = self._assemble(cfg, tmp_path)

        with open(files[0]) as f:
            compose = yaml.safe_load(f)
        for svc in compose["services"].values():
            assert svc["dns"] == servers


# ---------------------------------------------------------------------------
# No hardcoded DNS in app-config.json
# ---------------------------------------------------------------------------


class TestNoHardcodedDNS:
    def test_no_dns_in_app_entries(self):
        """No app or sidecar compose_config should have a hardcoded dns field."""
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "app-config.json"
        )
        with open(config_path) as f:
            app_config = json.load(f)

        for category in app_config.values():
            if not isinstance(category, dict):
                continue
            for entry in category.get("entries", []):
                cc = entry.get("compose_config", {})
                assert "dns" not in cc, (
                    f"{entry['name']} compose_config should not have hardcoded dns"
                )
                # Check sidecars too
                svc = entry.get("service", {})
                if svc:
                    svc_cc = svc.get("compose_config", {})
                    assert "dns" not in svc_cc, (
                        f"{entry['name']} sidecar compose_config should not have hardcoded dns"
                    )

    def test_no_dns_in_proxy_template(self):
        """The proxy service template should not have hardcoded dns."""
        template_path = os.path.join(
            os.path.dirname(__file__), "..", "template", "user-config.json"
        )
        with open(template_path) as f:
            user_cfg = json.load(f)

        proxy = user_cfg.get("compose_config_common", {}).get("proxy_service", {})
        assert "dns" not in proxy, (
            "proxy_service template should not have hardcoded dns"
        )


# ---------------------------------------------------------------------------
# System info dashboard (smoke test)
# ---------------------------------------------------------------------------


class TestSystemInfo:
    def test_show_system_info_runs(self, capsys):
        """show_system_info should print without error."""
        from money4band.system_info import show_system_info

        cfg = copy.deepcopy(_M4B_CONFIG)
        app_cfg = copy.deepcopy(_APP_CONFIG)
        usr_cfg = copy.deepcopy(_USER_CONFIG)

        with (
            patch("money4band.system_info.check_for_update", return_value=None),
            patch(
                "money4band.system_info.detector.get_system_memory_and_cores",
                return_value=(8192, 4),
            ),
            patch("money4band.compose_builder.get_compose_files", return_value=[]),
        ):
            show_system_info(cfg, app_cfg, usr_cfg)

        captured = capsys.readouterr()
        assert "System Information" in captured.out
        assert "v5.0.0" in captured.out
        assert "DNS" in captured.out
        assert "default" in captured.out

    def test_show_system_info_custom_dns(self, capsys):
        from money4band.system_info import show_system_info

        cfg = copy.deepcopy(_M4B_CONFIG)
        cfg["system"]["dns"] = {"mode": "custom", "servers": ["9.9.9.9"]}
        app_cfg = copy.deepcopy(_APP_CONFIG)
        usr_cfg = copy.deepcopy(_USER_CONFIG)

        with (
            patch("money4band.system_info.check_for_update", return_value=None),
            patch(
                "money4band.system_info.detector.get_system_memory_and_cores",
                return_value=(8192, 4),
            ),
            patch("money4band.compose_builder.get_compose_files", return_value=[]),
        ):
            show_system_info(cfg, app_cfg, usr_cfg)

        captured = capsys.readouterr()
        assert "custom" in captured.out
        assert "9.9.9.9" in captured.out

    def test_show_system_info_update_available(self, capsys):
        from money4band.system_info import show_system_info

        cfg = copy.deepcopy(_M4B_CONFIG)
        app_cfg = copy.deepcopy(_APP_CONFIG)
        usr_cfg = copy.deepcopy(_USER_CONFIG)

        with (
            patch("money4band.system_info.check_for_update", return_value="6.0.0"),
            patch(
                "money4band.system_info.detector.get_system_memory_and_cores",
                return_value=(8192, 4),
            ),
            patch("money4band.compose_builder.get_compose_files", return_value=[]),
        ):
            show_system_info(cfg, app_cfg, usr_cfg)

        captured = capsys.readouterr()
        assert "6.0.0" in captured.out
        assert "available" in captured.out

    def test_show_system_info_docker_installed(self, capsys):
        """When docker is installed and running, multiarch info is shown."""
        from money4band.system_info import show_system_info

        cfg = copy.deepcopy(_M4B_CONFIG)
        app_cfg = copy.deepcopy(_APP_CONFIG)
        usr_cfg = copy.deepcopy(_USER_CONFIG)

        with (
            patch("money4band.system_info.check_for_update", return_value=None),
            patch(
                "money4band.system_info.detector.get_system_memory_and_cores",
                return_value=(16384, 8),
            ),
            patch(
                "money4band.system_info.shutil.which", return_value="/usr/bin/docker"
            ),
            patch("money4band.helper.is_docker_daemon_running", return_value=True),
            patch(
                "money4band.helper.is_multiarch_emulation_available", return_value=True
            ),
            patch(
                "money4band.compose_builder.get_compose_files",
                return_value=["compose.yml", "compose.service.yml"],
            ),
        ):
            show_system_info(cfg, app_cfg, usr_cfg)

        captured = capsys.readouterr()
        assert "Docker installed" in captured.out
        assert "Docker running" in captured.out
        assert "Multiarch" in captured.out
        assert "layered" in captured.out

    def test_show_system_info_dashboard_enabled(self, capsys):
        from money4band.system_info import show_system_info

        cfg = copy.deepcopy(_M4B_CONFIG)
        app_cfg = copy.deepcopy(_APP_CONFIG)
        usr_cfg = copy.deepcopy(_USER_CONFIG)
        usr_cfg["m4b_dashboard"]["enabled"] = True
        usr_cfg["proxies"]["enabled"] = True

        with (
            patch("money4band.system_info.check_for_update", return_value=None),
            patch(
                "money4band.system_info.detector.get_system_memory_and_cores",
                return_value=(8192, 4),
            ),
            patch("money4band.compose_builder.get_compose_files", return_value=[]),
        ):
            show_system_info(cfg, app_cfg, usr_cfg)

        captured = capsys.readouterr()
        assert "enabled" in captured.out


class TestShowDnsStatus:
    def test_default_mode(self, capsys):
        from money4band.system_info import show_dns_status

        cfg = copy.deepcopy(_M4B_CONFIG)
        show_dns_status(cfg)
        captured = capsys.readouterr()
        assert "default" in captured.out
        assert "host default" in captured.out

    def test_custom_mode_shows_servers(self, capsys):
        from money4band.system_info import show_dns_status

        cfg = copy.deepcopy(_M4B_CONFIG)
        cfg["system"]["dns"] = {"mode": "custom", "servers": ["9.9.9.9", "1.0.0.1"]}
        show_dns_status(cfg)
        captured = capsys.readouterr()
        assert "custom" in captured.out
        assert "9.9.9.9" in captured.out


class TestComposeRegenReminder:
    def test_prints_reminder(self, capsys, monkeypatch):
        from money4band.system_info import compose_regen_reminder

        monkeypatch.setattr("builtins.input", lambda _: "")
        compose_regen_reminder()
        captured = capsys.readouterr()
        assert "regenerat" in captured.out.lower()


# ---------------------------------------------------------------------------
# CLI subcommand wiring
# ---------------------------------------------------------------------------


class TestCLISubcommands:
    def test_info_subcommand_parses(self):
        from main import _build_parser

        args = _build_parser().parse_args(["info"])
        assert args.command == "info"

    def test_dns_subcommand_parses(self):
        from main import _build_parser

        args = _build_parser().parse_args(["dns"])
        assert args.command == "dns"

    def test_dns_set_custom_parses(self):
        from main import _build_parser

        args = _build_parser().parse_args(
            ["dns", "set", "custom", "--servers", "9.9.9.9,149.112.112.112"]
        )
        assert args.command == "dns"
        assert args.dns_action == "set"
        assert args.mode == "custom"
        assert args.servers == "9.9.9.9,149.112.112.112"

    def test_dns_set_default_parses(self):
        from main import _build_parser

        args = _build_parser().parse_args(["dns", "set", "default"])
        assert args.command == "dns"
        assert args.dns_action == "set"
        assert args.mode == "default"


# ---------------------------------------------------------------------------
# dns_interactive — covering lines 85-122
# ---------------------------------------------------------------------------


class TestDnsInteractive:
    def test_empty_input_sets_default(self, tmp_path):
        """Empty input at the prompt should set DNS to 'default' mode."""
        from money4band.system_info import dns_interactive

        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(copy.deepcopy(_M4B_CONFIG)))

        with patch("builtins.input", side_effect=["", ""]):
            dns_interactive(str(cfg_path))

        result = json.loads(cfg_path.read_text())
        assert result["system"]["dns"]["mode"] == "default"

    def test_valid_custom_servers_persist(self, tmp_path):
        """Entering valid IPs stores them as custom DNS mode."""
        from money4band.system_info import dns_interactive

        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(copy.deepcopy(_M4B_CONFIG)))

        with patch("builtins.input", side_effect=["9.9.9.9, 1.0.0.1", ""]):
            dns_interactive(str(cfg_path))

        result = json.loads(cfg_path.read_text())
        assert result["system"]["dns"]["mode"] == "custom"
        assert result["system"]["dns"]["servers"] == ["9.9.9.9", "1.0.0.1"]

    def test_invalid_ip_retries_then_accepts_valid(self, tmp_path, capsys):
        """Invalid IP is rejected with an error, then valid input is accepted."""
        from money4band.system_info import dns_interactive

        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(copy.deepcopy(_M4B_CONFIG)))

        with patch("builtins.input", side_effect=["bad.ip", "8.8.4.4", ""]):
            dns_interactive(str(cfg_path))

        captured = capsys.readouterr()
        assert "Invalid" in captured.out
        result = json.loads(cfg_path.read_text())
        assert result["system"]["dns"]["mode"] == "custom"
        assert result["system"]["dns"]["servers"] == ["8.8.4.4"]

    def test_shows_current_custom_hint(self, tmp_path, capsys):
        """When current mode is custom, the hint shows current custom servers."""
        from money4band.system_info import dns_interactive

        cfg = copy.deepcopy(_M4B_CONFIG)
        cfg["system"]["dns"]["mode"] = "custom"
        cfg["system"]["dns"]["servers"] = ["1.2.3.4"]
        cfg_path = tmp_path / "m4b-config.json"
        cfg_path.write_text(json.dumps(cfg))

        with patch("builtins.input", side_effect=["", ""]):
            dns_interactive(str(cfg_path))

        captured = capsys.readouterr()
        assert "1.2.3.4" in captured.out


# ---------------------------------------------------------------------------
# system_info.main() — covering lines 282-301
# ---------------------------------------------------------------------------


class TestSystemInfoMain:
    @patch("money4band.system_info.dns_interactive")
    @patch("money4band.system_info.show_system_info")
    @patch("money4band.system_info.load_json_config")
    @patch("money4band.system_info.cls")
    def test_d_choice_opens_dns(self, _cls, mock_load, mock_show, mock_dns):
        """Selecting 'd' should invoke dns_interactive, then 'b' exits."""
        from money4band.system_info import main

        mock_load.return_value = copy.deepcopy(_M4B_CONFIG)
        with patch("builtins.input", side_effect=["d", "b"]):
            main("app.json", "m4b.json", "user.json")
        mock_dns.assert_called_once_with("m4b.json")

    @patch("money4band.system_info.show_system_info")
    @patch("money4band.system_info.load_json_config")
    @patch("money4band.system_info.cls")
    def test_b_choice_returns(self, _cls, mock_load, mock_show):
        """Selecting 'b' should exit the menu loop."""
        from money4band.system_info import main

        mock_load.return_value = copy.deepcopy(_M4B_CONFIG)
        with patch("builtins.input", return_value="b"):
            main("app.json", "m4b.json", "user.json")
        # Should only display once then exit
        mock_show.assert_called_once()

    @patch("money4band.system_info.show_system_info")
    @patch("money4band.system_info.load_json_config")
    @patch("money4band.system_info.cls")
    def test_q_choice_exits(self, _cls, mock_load, mock_show):
        """Selecting 'q' should raise SystemExit."""
        from money4band.system_info import main

        mock_load.return_value = copy.deepcopy(_M4B_CONFIG)
        with patch("builtins.input", return_value="q"), pytest.raises(SystemExit):
            main("app.json", "m4b.json", "user.json")
