"""Tests for API endpoint response patterns & defaults.

Covers every router endpoint to verify they return sensible data shapes
and handle empty/missing data gracefully — the "defaults" contract.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from money4band.api.server import app, configure

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def _flat_config(tmp_path):
    """Create a config using the FLAT layout (no ``categories`` wrapper)."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    m4b = {
        "project": {"project_version": "5.0.0"},
        "system": {"sleep_time": 1},
        "resource_profiles": {
            "profiles": {
                "conservative": {"cpu_pct": 0.40, "ram_pct": 0.25, "description": "Conservative"},
                "standard": {"cpu_pct": 0.60, "ram_pct": 0.40, "description": "Standard"},
            },
        },
    }
    (config_dir / "m4b-config.json").write_text(json.dumps(m4b))

    app_cfg = {
        "app_config_version": 1.2,
        "supported-apps": {
            "active": True,
            "entries": [
                {
                    "name": "EARNAPP",
                    "dashboard": "https://earnapp.com/dashboard",
                    "compose_config": {
                        "container_name": "m4b_earnapp",
                        "image": "earnapp:latest",
                        "cpus": "${APP_CPU_LIMIT_LITTLE}",
                    },
                    "compose_layer": "residential",
                    "app_details": {
                        "status": "active",
                        "earnings": {"avg_monthly_residential_usd": "0.5-3"},
                    },
                },
                {
                    "name": "honeygain",
                    "dashboard": "https://dashboard.honeygain.com/",
                    "compose_config": {
                        "container_name": "m4b_honeygain",
                        "image": "honeygain:latest",
                        "cpus": "${APP_CPU_LIMIT_MEDIUM}",
                    },
                    "compose_layer": "residential",
                    "app_details": {
                        "status": "active",
                        "earnings": {"avg_monthly_residential_usd": "1-5"},
                    },
                },
            ],
        },
        "deprecated-apps": {
            "active": False,
            "entries": [
                {
                    "name": "oldapp",
                    "compose_config": {
                        "container_name": "m4b_oldapp",
                        "image": "old:latest",
                        "cpus": "${APP_CPU_LIMIT_LITTLE}",
                    },
                    "compose_layer": "datacenter",
                    "app_details": {"status": "deprecated"},
                },
            ],
        },
    }
    (config_dir / "app-config.json").write_text(json.dumps(app_cfg))

    user_cfg = {
        "user": {"Nickname": "tester"},
        "device_info": {"device_name": "test-device", "os_type": "linux"},
        "apps": {"honeygain": {"enabled": True}},
        "resource_limits": {},
        "notifications": {"enabled": False, "url": ""},
        "proxies": {"enabled": False},
    }
    (config_dir / "user-config.json").write_text(json.dumps(user_cfg))

    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "user-config.json").write_text(json.dumps(user_cfg))

    configure(str(config_dir), base_dir=str(tmp_path))
    return tmp_path


@pytest.fixture
def _empty_config(tmp_path):
    """Config with no apps at all — verifies empty defaults."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    m4b = {
        "project": {"project_version": "5.0.0"},
        "system": {"sleep_time": 1},
        "resource_profiles": {"profiles": {}},
    }
    (config_dir / "m4b-config.json").write_text(json.dumps(m4b))
    (config_dir / "app-config.json").write_text(json.dumps({"app_config_version": 1.2}))

    user_cfg = {
        "user": {},
        "device_info": {},
        "apps": {},
        "resource_limits": {},
        "settings": {"resource_profile": "standard", "dns_mode": "default", "dns_servers": [], "enforce_install_limits": True, "setup_completed": True},
        "notifications": {"enabled": False, "url": ""},
        "proxies": {"enabled": False},
    }
    (config_dir / "user-config.json").write_text(json.dumps(user_cfg))

    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "user-config.json").write_text(json.dumps(user_cfg))

    configure(str(config_dir), base_dir=str(tmp_path))
    return tmp_path


@pytest.fixture
def flat_client(_flat_config):
    return TestClient(app)


@pytest.fixture
def empty_client(_empty_config):
    return TestClient(app)


# ===========================================================================
# Apps router — flat config format
# ===========================================================================


class TestAppsFlat:
    """Verify the apps router works with the flat (non-wrapped) config layout."""

    def test_list_all_apps(self, flat_client):
        resp = flat_client.get("/api/apps")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        names = {a["name"] for a in data}
        assert "EARNAPP" in names
        assert "honeygain" in names
        assert "oldapp" in names

    def test_list_categories_flat(self, flat_client):
        resp = flat_client.get("/api/apps/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        cat_names = {c["name"] for c in data}
        assert "supported-apps" in cat_names
        assert "deprecated-apps" in cat_names

    def test_category_counts(self, flat_client):
        resp = flat_client.get("/api/apps/categories")
        data = resp.json()
        supported = next(c for c in data if c["name"] == "supported-apps")
        assert supported["app_count"] == 2
        assert supported["active"] is True

    def test_filter_by_category_flat(self, flat_client):
        resp = flat_client.get("/api/apps?category=supported-apps")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(a["category"] == "supported-apps" for a in data)

    def test_filter_nonexistent_category(self, flat_client):
        resp = flat_client.get("/api/apps?category=no-such-cat")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_app_detail_flat(self, flat_client):
        resp = flat_client.get("/api/apps/honeygain")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "honeygain"
        assert data["category"] == "supported-apps"

    def test_get_app_detail_case_insensitive(self, flat_client):
        resp = flat_client.get("/api/apps/EARNAPP")
        assert resp.status_code == 200
        assert resp.json()["name"] == "EARNAPP"

    def test_toggle_category_flat(self, flat_client):
        resp = flat_client.post("/api/apps/categories/deprecated-apps/toggle")
        assert resp.status_code == 200
        assert resp.json()["active"] is True

    def test_app_response_shape(self, flat_client):
        """Every entry in the list must have all expected keys."""
        resp = flat_client.get("/api/apps")
        for item in resp.json():
            assert "name" in item
            assert "category" in item
            assert "active" in item
            assert "image" in item
            assert "resource_tier" in item
            assert "earnings_range" in item


# ===========================================================================
# Apps router — empty config
# ===========================================================================


class TestAppsEmpty:
    """Verify the apps router returns empty lists (not errors) with no data."""

    def test_list_apps_empty(self, empty_client):
        resp = empty_client.get("/api/apps")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_categories_empty(self, empty_client):
        resp = empty_client.get("/api/apps/categories")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_app_not_found_empty(self, empty_client):
        resp = empty_client.get("/api/apps/anything")
        assert resp.status_code == 404


# ===========================================================================
# Config router — response shapes
# ===========================================================================


class TestConfigDefaults:
    def test_get_app_config_returns_dict(self, flat_client):
        resp = flat_client.get("/api/config/app")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)
        assert "app_config_version" in resp.json()

    def test_get_m4b_config_returns_dict(self, flat_client):
        resp = flat_client.get("/api/config/m4b")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"]["project_version"] == "5.0.0"

    def test_get_limits_shape(self, flat_client):
        resp = flat_client.get("/api/config/limits")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_profile" in data
        assert "available_profiles" in data
        assert "resource_limits" in data

    def test_get_user_config_masked(self, flat_client):
        resp = flat_client.get("/api/config/user")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)


# ===========================================================================
# Earnings router — defaults
# ===========================================================================


class TestEarningsDefaults:
    def test_empty_earnings(self, flat_client):
        with patch(
            "money4band.apps.earnings.get_app_earnings",
            return_value=[],
        ):
            resp = flat_client.get("/api/earnings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["apps"] == []
        assert data["total_min"] == 0
        assert data["total_max"] == 0
        assert data["ip_type"] == "residential"

    def test_earnings_response_shape(self, flat_client):
        mock_apps = [{"name": "honeygain", "min": 1.0, "max": 5.0}]
        with patch(
            "money4band.apps.earnings.get_app_earnings",
            return_value=mock_apps,
        ):
            resp = flat_client.get("/api/earnings")
        data = resp.json()
        assert "ip_type" in data
        assert "apps" in data
        assert "total_min" in data
        assert "total_max" in data


# ===========================================================================
# Offers router — defaults
# ===========================================================================


class TestOffersDefaults:
    def test_empty_offers(self, flat_client):
        with patch("money4band.apps.offers.load_all_offers", return_value=[]):
            resp = flat_client.get("/api/offers")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_offers_filter_empty(self, flat_client):
        offers = [
            {"name": "A", "category": "bandwidth", "url": "https://a.com"},
        ]
        with patch("money4band.apps.offers.load_all_offers", return_value=offers):
            resp = flat_client.get("/api/offers?category=nonexistent")
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# Monitor router — defaults
# ===========================================================================


class TestMonitorDefaults:
    def test_empty_health(self, flat_client):
        with patch("money4band.docker.monitor.get_stack_health", return_value=[]):
            resp = flat_client.get("/api/monitor/health")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_empty_restart_loops(self, flat_client):
        with patch("money4band.docker.monitor.get_stack_health", return_value=[]):
            resp = flat_client.get("/api/monitor/restart-loops")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_health_response_shape(self, flat_client):
        mock_s = MagicMock(
            running=True,
            health="healthy",
            restart_count=0,
            last_started="2026-03-24T10:00:00Z",
            last_error="",
            image="test:latest",
        )
        mock_s.name = "test-container"
        with patch("money4band.docker.monitor.get_stack_health", return_value=[mock_s]):
            resp = flat_client.get("/api/monitor/health")
        data = resp.json()
        assert len(data) == 1
        entry = data[0]
        for key in (
            "name",
            "running",
            "health",
            "restart_count",
            "last_started",
            "last_error",
            "image",
        ):
            assert key in entry


# ===========================================================================
# Backups router — defaults
# ===========================================================================


class TestBackupsDefaults:
    def test_empty_backups(self, flat_client):
        with patch("money4band.core.backup.list_backups", return_value=[]):
            resp = flat_client.get("/api/backups")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_backup_response_shape(self, flat_client):
        mock_b = MagicMock(path="/backups/b1.tar.gz", timestamp="2026-03-24", size=512)
        with patch("money4band.core.backup.list_backups", return_value=[mock_b]):
            resp = flat_client.get("/api/backups")
        data = resp.json()
        assert len(data) == 1
        for key in ("path", "timestamp", "size"):
            assert key in data[0]


# ===========================================================================
# Profiles router — defaults
# ===========================================================================


class TestProfilesDefaults:
    def test_empty_profiles(self, flat_client):
        with patch("money4band.core.profiles.list_profiles", return_value=[]):
            resp = flat_client.get("/api/profiles")
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# Notifications router — defaults
# ===========================================================================


class TestNotificationsDefaults:
    def test_status_shape(self, flat_client):
        resp = flat_client.get("/api/notifications/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "url_set" in data
        assert "events" in data

    def test_disabled_notifications(self, flat_client):
        resp = flat_client.get("/api/notifications/status")
        data = resp.json()
        assert data["enabled"] is False


# ===========================================================================
# Security router — defaults
# ===========================================================================


class TestSecurityDefaults:
    def test_empty_stale_images(self, flat_client):
        with patch("money4band.docker.image_security.check_stale_images", return_value=[]):
            resp = flat_client.get("/api/security/stale")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_empty_digests(self, flat_client):
        with patch("money4band.docker.image_security.log_image_digests", return_value=[]):
            resp = flat_client.get("/api/security/digests")
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# Update router — defaults
# ===========================================================================


class TestUpdateDefaults:
    def test_no_update_available(self, flat_client):
        with patch("money4band.updater.check_for_update", return_value=None):
            resp = flat_client.get("/api/update/check")
        assert resp.status_code == 200
        data = resp.json()
        assert data["update_available"] is False
        assert data["latest_version"] is None

    def test_update_check_shape(self, flat_client):
        with patch("money4band.updater.check_for_update", return_value="6.0.0"):
            resp = flat_client.get("/api/update/check")
        data = resp.json()
        assert "current_version" in data
        assert "latest_version" in data
        assert "update_available" in data


# ===========================================================================
# System router — defaults
# ===========================================================================


class TestSystemDefaults:
    def test_info_shape(self, flat_client):
        with (
            patch("money4band.system.detector.detect_os", return_value={"os_type": "linux"}),
            patch(
                "money4band.system.detector.detect_architecture",
                return_value={"arch": "x86_64", "dkarch": "amd64"},
            ),
        ):
            resp = flat_client.get("/api/system/info")
        assert resp.status_code == 200
        data = resp.json()
        for key in (
            "platform",
            "os_type",
            "architecture",
            "total_ram_mb",
            "cpu_cores",
            "project_version",
            "enabled_apps",
        ):
            assert key in data

    def test_dns_default(self, flat_client):
        resp = flat_client.get("/api/system/dns")
        assert resp.status_code == 200


# ===========================================================================
# Stack router — defaults
# ===========================================================================


class TestStackDefaults:
    def test_start_returns_ok(self, flat_client):
        with patch("money4band.docker.start.start_all_stacks"):
            resp = flat_client.post("/api/stack/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_stop_returns_ok(self, flat_client):
        with patch("money4band.docker.stop.stop_all_stacks"):
            resp = flat_client.post("/api/stack/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_restart_returns_ok(self, flat_client):
        with (
            patch("money4band.docker.stop.stop_all_stacks"),
            patch("money4band.docker.start.start_all_stacks"),
        ):
            resp = flat_client.post("/api/stack/restart")
        assert resp.status_code == 200


# ===========================================================================
# Direct app endpoints (/api/status, /api/health, etc.)
# ===========================================================================


class TestDirectEndpointDefaults:
    def test_status_empty(self, flat_client):
        with patch("money4band.api.server._run_docker") as m:
            m.return_value = MagicMock(returncode=1, stdout="", stderr="")
            resp = flat_client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["docker_available"] is True
        assert data["containers"] == []

    def test_health_empty(self, flat_client):
        with patch("money4band.api.server._run_docker") as m:
            m.return_value = MagicMock(returncode=1, stdout="")
            resp = flat_client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_stats_empty(self, flat_client):
        with patch("money4band.api.server._run_docker") as m:
            m.return_value = MagicMock(returncode=1, stdout="")
            resp = flat_client.get("/api/stats")
        assert resp.status_code == 200
        assert resp.json() == []



    def test_action_invalid_action(self, flat_client):
        resp = flat_client.post("/api/action/mycontainer/delete")
        assert resp.status_code == 400

    def test_action_invalid_container_name(self, flat_client):
        resp = flat_client.post("/api/action/;rm -rf/start")
        assert resp.status_code in (400, 404, 422)

    def test_ip_score_empty(self, flat_client):
        with patch("money4band.network.ip_scorer.analyse_ips", return_value=[]):
            resp = flat_client.get("/api/ip/score")
        assert resp.status_code == 200
        assert resp.json() == []
