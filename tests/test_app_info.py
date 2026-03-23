"""Tests for app_info module: detail card and app listing."""

from __future__ import annotations

from money4band.app_info import _find_app, list_apps, show_app_detail

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAMPLE_CONFIG = {
    "supported-apps": {
        "active": True,
        "entries": [
            {
                "name": "EARNAPP",
                "link": "https://earnapp.com/i/ref123",
                "install_limit": 1,
                "compose_layer": "residential",
                "compose_config": {"image": "fazalfarhan01/earnapp:lite"},
                "app_details": {
                    "official_name": "EarnApp",
                    "publisher": "Bright Data",
                    "official_url": "https://earnapp.com",
                    "tos_url": "https://earnapp.com/eula",
                    "status": "active",
                    "device_limits": {
                        "max_devices_per_account": 15,
                        "max_devices_per_ip": 1,
                        "max_ips_per_account": "undocumented",
                        "notes": "1 device per IP",
                    },
                    "ip_policy": {
                        "residential": True,
                        "datacenter": False,
                        "vps": False,
                        "mobile": True,
                        "geo_restrictions": "none known",
                        "quality_notes": "IP reputation scoring",
                    },
                    "earnings": {
                        "model": "per-GB",
                        "payout_methods": ["PayPal", "crypto"],
                        "min_payout": "$2.50",
                        "avg_monthly_residential_usd": "1-9",
                        "avg_monthly_datacenter_usd": None,
                    },
                    "docker": {
                        "image_official": False,
                        "image_maintained": False,
                        "last_update": "2023-06",
                    },
                    "warnings": ["Third-party Docker image"],
                    "confidence": "high",
                    "last_verified": "2026-03-21",
                },
            },
            {
                "name": "HONEYGAIN",
                "link": "https://honeygain.com/ref",
                "install_limit": -1,
                "compose_layer": "residential",
                "compose_config": {"image": "honeygain/honeygain"},
                "app_details": {
                    "official_name": "Honeygain",
                    "publisher": "Honeygain",
                    "official_url": "https://honeygain.com",
                    "ip_policy": {"residential": True, "datacenter": False},
                    "earnings": {"payout_methods": ["PayPal", "crypto"]},
                    "docker": {"image_official": True, "image_maintained": True},
                },
            },
        ],
    },
    "deprecated-apps": {
        "active": False,
        "entries": [
            {
                "name": "WIPTER",
                "link": "https://wipter.com",
                "install_limit": -1,
                "compose_layer": "residential",
                "compose_config": {"image": "wipter/wipter"},
                "app_details": {
                    "official_name": "Wipter",
                    "publisher": "Wipter",
                    "official_url": "https://wipter.com",
                    "ip_policy": {"residential": True, "datacenter": False},
                    "earnings": {"payout_methods": ["crypto"]},
                    "docker": {},
                },
            },
        ],
    },
    "candidate-apps": {
        "active": False,
        "entries": [
            {
                "name": "SPIDE",
                "link": "https://spide.network",
                "install_limit": -1,
                "compose_config": {"image": "spide/spide"},
                "app_details": {
                    "official_name": "Spide",
                    "publisher": "Spide",
                    "official_url": "https://spide.network",
                    "ip_policy": {"residential": True, "datacenter": True},
                    "earnings": {"payout_methods": ["PayPal", "crypto"]},
                    "docker": {},
                },
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# _find_app
# ---------------------------------------------------------------------------


class TestFindApp:
    def test_find_exact_name(self):
        entry, cat = _find_app(_SAMPLE_CONFIG, "EARNAPP")
        assert entry is not None
        assert entry["name"] == "EARNAPP"
        assert cat == "supported-apps"

    def test_find_case_insensitive(self):
        entry, cat = _find_app(_SAMPLE_CONFIG, "earnapp")
        assert entry is not None
        assert entry["name"] == "EARNAPP"

    def test_find_with_whitespace(self):
        entry, _ = _find_app(_SAMPLE_CONFIG, "  honeygain  ")
        assert entry is not None
        assert entry["name"] == "HONEYGAIN"

    def test_find_deprecated(self):
        entry, cat = _find_app(_SAMPLE_CONFIG, "wipter")
        assert entry is not None
        assert cat == "deprecated-apps"

    def test_find_candidate(self):
        entry, cat = _find_app(_SAMPLE_CONFIG, "spide")
        assert entry is not None
        assert cat == "candidate-apps"

    def test_not_found(self):
        entry, cat = _find_app(_SAMPLE_CONFIG, "nonexistent")
        assert entry is None
        assert cat == ""


# ---------------------------------------------------------------------------
# show_app_detail
# ---------------------------------------------------------------------------


class TestShowAppDetail:
    def test_found_returns_true(self, capsys):
        result = show_app_detail(_SAMPLE_CONFIG, "earnapp")
        assert result is True
        output = capsys.readouterr().out
        assert "EarnApp" in output
        assert "Bright Data" in output

    def test_not_found_returns_false(self, capsys):
        result = show_app_detail(_SAMPLE_CONFIG, "doesnotexist")
        assert result is False
        output = capsys.readouterr().out
        assert "not found" in output

    def test_displays_ip_policy(self, capsys):
        show_app_detail(_SAMPLE_CONFIG, "earnapp")
        output = capsys.readouterr().out
        assert "Residential" in output
        assert "Datacenter" in output

    def test_displays_earnings(self, capsys):
        show_app_detail(_SAMPLE_CONFIG, "earnapp")
        output = capsys.readouterr().out
        assert "per-GB" in output
        assert "PayPal" in output
        assert "$2.50" in output

    def test_displays_docker_info(self, capsys):
        show_app_detail(_SAMPLE_CONFIG, "earnapp")
        output = capsys.readouterr().out
        assert "fazalfarhan01/earnapp:lite" in output
        assert "2023-06" in output

    def test_displays_warnings(self, capsys):
        show_app_detail(_SAMPLE_CONFIG, "earnapp")
        output = capsys.readouterr().out
        assert "Third-party Docker image" in output

    def test_displays_device_limits(self, capsys):
        show_app_detail(_SAMPLE_CONFIG, "earnapp")
        output = capsys.readouterr().out
        assert "15" in output
        assert "Per IP" in output

    def test_displays_install_limit(self, capsys):
        show_app_detail(_SAMPLE_CONFIG, "earnapp")
        output = capsys.readouterr().out
        assert "Install limit:" in output
        assert "1" in output

    def test_displays_confidence(self, capsys):
        show_app_detail(_SAMPLE_CONFIG, "earnapp")
        output = capsys.readouterr().out
        assert "high" in output

    def test_deprecated_badge(self, capsys):
        show_app_detail(_SAMPLE_CONFIG, "wipter")
        output = capsys.readouterr().out
        assert "DEPRECATED" in output

    def test_candidate_badge(self, capsys):
        show_app_detail(_SAMPLE_CONFIG, "spide")
        output = capsys.readouterr().out
        assert "CANDIDATE" in output

    def test_suggest_similar(self, capsys):
        show_app_detail(_SAMPLE_CONFIG, "earn")
        output = capsys.readouterr().out
        assert "EARNAPP" in output or "Did you mean" in output


# ---------------------------------------------------------------------------
# list_apps
# ---------------------------------------------------------------------------


class TestListApps:
    def test_lists_all_apps(self, capsys):
        list_apps(_SAMPLE_CONFIG)
        output = capsys.readouterr().out
        assert "EarnApp" in output
        assert "Honeygain" in output
        assert "Wipter" in output
        assert "Spide" in output

    def test_category_filter(self, capsys):
        list_apps(_SAMPLE_CONFIG, category_filter="deprecated")
        output = capsys.readouterr().out
        assert "Wipter" in output
        assert "EarnApp" not in output

    def test_shows_status(self, capsys):
        list_apps(_SAMPLE_CONFIG)
        output = capsys.readouterr().out
        assert "active" in output
        assert "deprecated" in output
        assert "candidate" in output

    def test_shows_payout(self, capsys):
        list_apps(_SAMPLE_CONFIG)
        output = capsys.readouterr().out
        assert "PayPal" in output

    def test_empty_config(self, capsys):
        list_apps({})
        output = capsys.readouterr().out
        # Should print header but no apps
        assert "Name" in output
