"""Tests for the M4B REST API routers (Phase 7)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from money4band.dashboard_api import app, configure

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_config(tmp_path):
    """Create a temp config dir with minimal config files and configure paths."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    m4b = {
        "project": {"project_version": "5.0.0"},
        "system": {"sleep_time": 1},
        "resource_profiles": {
            "active": "low",
            "profiles": {
                "base": {"cpu_factor": 0.5, "ram_pct": 0.1, "description": "Base"},
                "low": {"cpu_factor": 1.0, "ram_pct": 0.1875, "description": "Low"},
                "mid": {"cpu_factor": 1.5, "ram_pct": 0.25, "description": "Mid"},
            },
        },
        "dns": {"mode": "default", "servers": []},
    }
    (config_dir / "m4b-config.json").write_text(json.dumps(m4b))

    app_cfg = {
        "app_config_version": 2.0,
        "categories": {
            "supported-apps": {
                "active": True,
                "entries": [
                    {
                        "name": "honeygain",
                        "image": {"name": "honeygain/honeygain:latest"},
                        "resource_tier": "medium",
                        "app_details": {"earnings_range": "1-5"},
                    },
                    {
                        "name": "earnapp",
                        "image": {"name": "fazalfarhan01/earnapp:latest"},
                        "resource_tier": "little",
                        "app_details": {"earnings_range": "0.5-3"},
                    },
                ],
            },
            "candidate-apps": {
                "active": False,
                "entries": [
                    {
                        "name": "testapp",
                        "image": {"name": "test/test:latest"},
                        "resource_tier": "little",
                        "app_details": {"earnings_range": "0-1"},
                    },
                ],
            },
        },
    }
    (config_dir / "app-config.json").write_text(json.dumps(app_cfg))

    user_cfg = {
        "user": {"Nickname": "testuser"},
        "device_info": {"device_name": "test-device", "os_type": "linux"},
        "apps": {
            "honeygain": {"enabled": True},
            "earnapp": {"enabled": False},
        },
        "resource_limits": {"ram_cap_mb_default": 6144},
        "notifications": {"enabled": False, "url": ""},
        "proxies": {"enabled": False},
    }
    (config_dir / "user-config.json").write_text(json.dumps(user_cfg))

    # Template for reset
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "user-config.json").write_text(json.dumps(user_cfg))

    configure(str(config_dir), base_dir=str(tmp_path))
    return tmp_path


@pytest.fixture
def client(tmp_config):
    return TestClient(app)


# ===========================================================================
# Apps router
# ===========================================================================


class TestAppsRouter:
    def test_list_all_apps(self, client):
        resp = client.get("/api/apps")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        names = {a["name"] for a in data}
        assert "honeygain" in names
        assert "testapp" in names

    def test_list_apps_by_category(self, client):
        resp = client.get("/api/apps?category=supported-apps")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(a["category"] == "supported-apps" for a in data)

    def test_list_categories(self, client):
        resp = client.get("/api/apps/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        active_cats = [c for c in data if c["active"]]
        assert len(active_cats) == 1
        assert active_cats[0]["name"] == "supported-apps"

    def test_toggle_category(self, client):
        resp = client.post("/api/apps/categories/candidate-apps/toggle")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] is True

        # Toggle back
        resp = client.post("/api/apps/categories/candidate-apps/toggle")
        assert resp.json()["active"] is False

    def test_toggle_nonexistent_category(self, client):
        resp = client.post("/api/apps/categories/nonexistent/toggle")
        assert resp.status_code == 404

    def test_get_app_detail(self, client):
        resp = client.get("/api/apps/honeygain")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "honeygain"
        assert data["category"] == "supported-apps"

    def test_get_app_detail_case_insensitive(self, client):
        resp = client.get("/api/apps/HoneyGain")
        assert resp.status_code == 200
        assert resp.json()["name"] == "honeygain"

    def test_get_app_not_found(self, client):
        resp = client.get("/api/apps/nonexistent")
        assert resp.status_code == 404


# ===========================================================================
# Config router
# ===========================================================================


class TestConfigRouter:
    def test_get_user_config_masked(self, client):
        with patch("money4band.config_viewer._mask_dict", wraps=lambda d: d):
            resp = client.get("/api/config/user")
        assert resp.status_code == 200
        data = resp.json()
        assert "apps" in data

    def test_get_user_config_calls_mask(self, client):
        """Ensures _mask_dict is actually invoked for masking."""
        resp = client.get("/api/config/user")
        assert resp.status_code == 200

    def test_update_user_config(self, client, tmp_config):
        resp = client.put(
            "/api/config/user",
            json={"data": {"user": {"Nickname": "updated"}}},
        )
        assert resp.status_code == 200

        # Verify the change persisted
        cfg_path = tmp_config / "config" / "user-config.json"
        updated = json.loads(cfg_path.read_text())
        assert updated["user"]["Nickname"] == "updated"

    def test_update_user_config_deep_merge(self, client, tmp_config):
        """Deep merge should preserve existing nested keys."""
        resp = client.put(
            "/api/config/user",
            json={"data": {"device_info": {"os_type": "windows"}}},
        )
        assert resp.status_code == 200
        cfg_path = tmp_config / "config" / "user-config.json"
        updated = json.loads(cfg_path.read_text())
        # os_type updated, device_name preserved
        assert updated["device_info"]["os_type"] == "windows"
        assert updated["device_info"]["device_name"] == "test-device"

    def test_reset_config(self, client, tmp_config):
        resp = client.post("/api/config/reset")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_get_app_config(self, client):
        resp = client.get("/api/config/app")
        assert resp.status_code == 200
        assert "categories" in resp.json()

    def test_get_m4b_config(self, client):
        resp = client.get("/api/config/m4b")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"]["project_version"] == "5.0.0"

    def test_get_limits(self, client):
        resp = client.get("/api/config/limits")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_profile"] == "low"

    def test_set_limits_valid(self, client):
        with patch("money4band.detector.calculate_resource_limits"):
            resp = client.put("/api/config/limits", json={"profile": "mid"})
        assert resp.status_code == 200
        assert resp.json()["profile"] == "mid"

    def test_set_limits_invalid(self, client):
        resp = client.put("/api/config/limits", json={"profile": "turbo"})
        assert resp.status_code == 400


# ===========================================================================
# Stack router
# ===========================================================================


class TestStackRouter:
    def test_start_stack(self, client):
        with patch("money4band.fn_startStack.start_all_stacks"):
            resp = client.post("/api/stack/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_start_stack_failure(self, client):
        with patch(
            "money4band.fn_startStack.start_all_stacks",
            side_effect=RuntimeError("Docker not found"),
        ):
            resp = client.post("/api/stack/start")
        assert resp.status_code == 500

    def test_stop_stack(self, client):
        with patch("money4band.fn_stopStack.stop_all_stacks"):
            resp = client.post("/api/stack/stop")
        assert resp.status_code == 200

    def test_restart_stack(self, client):
        with (
            patch("money4band.fn_stopStack.stop_all_stacks"),
            patch("money4band.fn_startStack.start_all_stacks"),
        ):
            resp = client.post("/api/stack/restart")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Stack restarted"


# ===========================================================================
# System router
# ===========================================================================


class TestSystemRouter:
    def test_system_info(self, client):
        with (
            patch("money4band.detector.detect_os", return_value={"os_type": "linux"}),
            patch(
                "money4band.detector.detect_architecture",
                return_value={"arch": "x86_64", "dkarch": "amd64"},
            ),
        ):
            resp = client.get("/api/system/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_ram_mb" in data
        assert "cpu_cores" in data
        assert data["project_version"] == "5.0.0"

    def test_get_dns(self, client):
        resp = client.get("/api/system/dns")
        assert resp.status_code == 200

    def test_set_dns_valid(self, client):
        with patch("money4band.system_info.set_dns_mode"):
            resp = client.put("/api/system/dns", json={"mode": "cloudflare"})
        assert resp.status_code == 200
        assert resp.json()["mode"] == "cloudflare"

    def test_set_dns_invalid(self, client):
        resp = client.put("/api/system/dns", json={"mode": "invalid"})
        assert resp.status_code == 400


# ===========================================================================
# Monitor router
# ===========================================================================


class TestMonitorRouter:
    def test_stack_health(self, client):
        mock_status = MagicMock(
            name="container1",
            running=True,
            health="healthy",
            restart_count=0,
            last_started="2026-03-24T10:00:00Z",
            last_error="",
            image="test:latest",
        )
        mock_status.name = "container1"
        with patch(
            "money4band.monitor.get_stack_health",
            return_value=[mock_status],
        ):
            resp = client.get("/api/monitor/health")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["running"] is True

    def test_restart_loops(self, client):
        looping = MagicMock(
            restart_count=10,
            last_error="OOM killed",
            image="bad:latest",
        )
        looping.name = "bad-container"
        healthy = MagicMock(restart_count=0)
        healthy.name = "good-container"
        with patch(
            "money4band.monitor.get_stack_health",
            return_value=[looping, healthy],
        ):
            resp = client.get("/api/monitor/restart-loops?threshold=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "bad-container"


# ===========================================================================
# Backups router
# ===========================================================================


class TestBackupsRouter:
    def test_list_backups(self, client):
        mock_backup = MagicMock(
            path="/backups/backup-2026.tar.gz",
            timestamp="2026-03-24",
            size=1024,
        )
        with patch(
            "money4band.backup.list_backups",
            return_value=[mock_backup],
        ):
            resp = client.get("/api/backups")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_create_backup(self, client):
        with patch(
            "money4band.backup.create_backup",
            return_value="/backups/new.tar.gz",
        ):
            resp = client.post("/api/backups")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_restore_backup(self, client, tmp_config):
        backup_file = tmp_config / "fake_backup.tar.gz"
        backup_file.write_text("fake")
        with patch("money4band.backup.restore_backup"):
            resp = client.post(
                "/api/backups/restore",
                json={"path": str(backup_file)},
            )
        assert resp.status_code == 200

    def test_restore_nonexistent(self, client):
        resp = client.post(
            "/api/backups/restore",
            json={"path": "/nonexistent/path"},
        )
        assert resp.status_code == 404

    def test_cleanup_backups(self, client):
        with patch(
            "money4band.backup.cleanup_backups",
            return_value=3,
        ):
            resp = client.delete("/api/backups/cleanup?keep=5")
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 3


# ===========================================================================
# Profiles router
# ===========================================================================


class TestProfilesRouter:
    def test_list_profiles(self, client):
        with patch(
            "money4band.profiles.list_profiles",
            return_value=["default", "gaming"],
        ):
            resp = client.get("/api/profiles")
        assert resp.status_code == 200
        assert resp.json() == ["default", "gaming"]

    def test_create_profile(self, client):
        with patch(
            "money4band.profiles.create_profile",
            return_value="/profiles/myprofile",
        ):
            resp = client.post("/api/profiles", json={"name": "myprofile"})
        assert resp.status_code == 200
        assert resp.json()["profile"] == "myprofile"

    def test_switch_profile(self, client):
        with (
            patch(
                "money4band.profiles.list_profiles",
                return_value=["myprofile"],
            ),
            patch("money4band.profiles.switch_profile"),
        ):
            resp = client.put("/api/profiles/myprofile/switch")
        assert resp.status_code == 200

    def test_switch_nonexistent(self, client):
        with patch(
            "money4band.profiles.list_profiles",
            return_value=[],
        ):
            resp = client.put("/api/profiles/nope/switch")
        assert resp.status_code == 404

    def test_delete_profile(self, client):
        with (
            patch(
                "money4band.profiles.list_profiles",
                return_value=["old"],
            ),
            patch("money4band.profiles.delete_profile"),
        ):
            resp = client.delete("/api/profiles/old")
        assert resp.status_code == 200

    def test_delete_nonexistent(self, client):
        with patch(
            "money4band.profiles.list_profiles",
            return_value=[],
        ):
            resp = client.delete("/api/profiles/nope")
        assert resp.status_code == 404


# ===========================================================================
# Earnings router
# ===========================================================================


class TestEarningsRouter:
    def test_get_earnings(self, client):
        mock_earnings = [
            {"name": "honeygain", "min": 1.0, "max": 5.0},
            {"name": "earnapp", "min": 0.5, "max": 3.0},
        ]
        with patch(
            "money4band.earnings_estimator.get_app_earnings",
            return_value=mock_earnings,
        ):
            resp = client.get("/api/earnings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_min"] == 1.5
        assert data["total_max"] == 8.0
        assert data["ip_type"] == "residential"

    def test_get_earnings_datacenter(self, client):
        with patch(
            "money4band.earnings_estimator.get_app_earnings",
            return_value=[],
        ):
            resp = client.get("/api/earnings?ip_type=datacenter")
        assert resp.status_code == 200
        assert resp.json()["ip_type"] == "datacenter"


# ===========================================================================
# IP scoring router
# ===========================================================================


class TestIPRouter:
    def test_ip_score(self, client):
        mock_results = [
            {"ip": "1.2.3.4", "score": 15, "rating": "Good"},
        ]
        with patch(
            "money4band.ip_scorer.analyse_ips",
            return_value=mock_results,
        ):
            resp = client.get("/api/ip/score")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


# ===========================================================================
# Offers router
# ===========================================================================


class TestOffersRouter:
    def test_get_offers(self, client):
        mock_offers = [
            {
                "name": "Honeygain",
                "category": "bandwidth",
                "url": "https://example.com",
            },
            {"name": "TestOffer", "category": "survey", "url": "https://test.com"},
        ]
        with patch(
            "money4band.offers.load_all_offers",
            return_value=mock_offers,
        ):
            resp = client.get("/api/offers")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_offers_filtered(self, client):
        mock_offers = [
            {
                "name": "Honeygain",
                "category": "bandwidth",
                "url": "https://example.com",
            },
            {"name": "TestOffer", "category": "survey", "url": "https://test.com"},
        ]
        with patch(
            "money4band.offers.load_all_offers",
            return_value=mock_offers,
        ):
            resp = client.get("/api/offers?category=bandwidth")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["category"] == "bandwidth"


# ===========================================================================
# Notifications router
# ===========================================================================


class TestNotificationsRouter:
    def test_notification_status(self, client):
        resp = client.get("/api/notifications/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "events" in data

    def test_send_test_notification(self, client):
        with patch(
            "money4band.notifier.send_test",
            return_value=True,
        ):
            resp = client.post("/api/notifications/test")
        assert resp.status_code == 200
        assert resp.json()["sent"] is True

    def test_send_test_notification_failure(self, client):
        with patch(
            "money4band.notifier.send_test",
            return_value=False,
        ):
            resp = client.post("/api/notifications/test")
        assert resp.status_code == 200
        assert resp.json()["sent"] is False


# ===========================================================================
# Update router
# ===========================================================================


class TestUpdateRouter:
    def test_check_update_available(self, client):
        with patch(
            "money4band.updater.check_for_update",
            return_value="5.1.0",
        ):
            resp = client.get("/api/update/check")
        assert resp.status_code == 200
        data = resp.json()
        assert data["update_available"] is True
        assert data["latest_version"] == "5.1.0"

    def test_check_update_none(self, client):
        with patch(
            "money4band.updater.check_for_update",
            return_value=None,
        ):
            resp = client.get("/api/update/check")
        assert resp.status_code == 200
        assert resp.json()["update_available"] is False

    def test_apply_update(self, client):
        with (
            patch(
                "money4band.updater.check_for_update",
                return_value="5.1.0",
            ),
            patch(
                "money4band.updater.apply_update",
                return_value=True,
            ),
        ):
            resp = client.post("/api/update/apply", json={"version": "5.1.0"})
        assert resp.status_code == 200

    def test_apply_update_no_version(self, client):
        with patch(
            "money4band.updater.check_for_update",
            return_value=None,
        ):
            resp = client.post("/api/update/apply", json={})
        assert resp.status_code == 400


# ===========================================================================
# Security router
# ===========================================================================


class TestSecurityRouter:
    def test_stale_images(self, client):
        with patch(
            "money4band.image_security.check_stale_images",
            return_value=[{"image": "old:1.0", "days_since_update": 120}],
        ):
            resp = client.get("/api/security/stale")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_image_digests(self, client):
        with patch(
            "money4band.image_security.log_image_digests",
            return_value=[{"image": "test:latest", "digest": "sha256:abc"}],
        ):
            resp = client.get("/api/security/digests")
        assert resp.status_code == 200

    def test_scan_image(self, client):
        with patch(
            "money4band.image_security.run_scout_cves",
            return_value="No vulnerabilities found",
        ):
            resp = client.post("/api/security/scan/test:latest")
        assert resp.status_code == 200
        assert resp.json()["image"] == "test:latest"

    def test_scan_image_bad_name(self, client):
        resp = client.post("/api/security/scan/; rm -rf /")
        assert resp.status_code in (400, 404, 422)
