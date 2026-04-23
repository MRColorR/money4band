"""Tests for the M4B REST API routers (Phase 7)."""

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
def tmp_config(tmp_path):
    """Create a temp config dir with minimal config files and configure paths."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    m4b = {
        "project": {"project_version": "5.0.0"},
        "system": {
            "sleep_time": 1,
            "dns": {
                "mode": "default",
                "servers": [],
                "available_modes": [
                    "default",
                    "cloudflare",
                    "cloudflare-security",
                    "google",
                    "quad9",
                    "quad9-unfiltered",
                    "opendns",
                    "dns4eu",
                    "dns4eu-unfiltered",
                    "custom",
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
        },
        "resource_profiles": {
            "profiles": {
                "conservative": {
                    "cpu_pct": 0.40,
                    "ram_pct": 0.25,
                    "description": "Conservative",
                },
                "standard": {
                    "cpu_pct": 0.60,
                    "ram_pct": 0.40,
                    "description": "Standard",
                },
                "performance": {
                    "cpu_pct": 0.85,
                    "ram_pct": 0.65,
                    "description": "Performance",
                },
            },
        },
    }
    # m4b-config written below once the catalog envelope is known.

    app_cfg = {
        "app_config_version": 2.0,
        "categories": {
            "supported": {
                "active": True,
                "entries": [
                    {
                        "name": "honeygain",
                        "dashboard": "https://dashboard.honeygain.com/",
                        "referrals": [
                            {
                                "url": "https://r.honeygain.me/TEST",
                                "contributor": "MRColorR",
                            }
                        ],
                        "compose_config": {
                            "container_name": "m4b_honeygain",
                            "image": "honeygain/honeygain:latest",
                            "cpus": "${APP_CPU_LIMIT_MEDIUM}",
                        },
                        "compose_layer": "residential",
                        "app_details": {
                            "status": "active",
                            "earnings": {
                                "avg_monthly_residential_usd": "1-5",
                            },
                        },
                    },
                    {
                        "name": "earnapp",
                        "dashboard": "https://earnapp.com/dashboard",
                        "referrals": [
                            {
                                "url": "https://earnapp.com/i/TEST",
                                "contributor": "MRColorR",
                            }
                        ],
                        "compose_config": {
                            "container_name": "m4b_earnapp",
                            "image": "fazalfarhan01/earnapp:latest",
                            "cpus": "${APP_CPU_LIMIT_LITTLE}",
                        },
                        "compose_layer": "residential",
                        "app_details": {
                            "status": "active",
                            "earnings": {
                                "avg_monthly_residential_usd": "0.5-3",
                            },
                        },
                    },
                ],
            },
            "newcomers": {
                "active": False,
                "entries": [
                    {
                        "name": "testapp",
                        "compose_config": {
                            "container_name": "m4b_testapp",
                            "image": "test/test:latest",
                            "cpus": "${APP_CPU_LIMIT_LITTLE}",
                        },
                        "compose_layer": "datacenter",
                        "app_details": {
                            "status": "candidate",
                            "earnings": {
                                "avg_monthly_residential_usd": "0-1",
                            },
                        },
                    },
                ],
            },
        },
    }
    # Phase-8.4.1: fold envelope under m4b-config.json → catalog
    m4b["catalog"] = app_cfg
    (config_dir / "m4b-config.json").write_text(json.dumps(m4b))

    user_cfg = {
        "user": {"Nickname": "testuser"},
        "device_info": {"device_name": "test-device", "os_type": "linux"},
        "apps": {
            "honeygain": {"enabled": True},
            "earnapp": {"enabled": False},
        },
        "resource_limits": {},
        "settings": {
            "setup_completed": True,
            "resource_profile": "standard",
            "dns_mode": "default",
            "dns_servers": [],
            "enforce_install_limits": True,
        },
        "notifications": {"enabled": False, "url": ""},
        "proxies": {"enabled": False},
        "m4b_dashboard": {
            "enabled": True,
            "api_key": "original-secret-key",
            "port": 8088,
        },
    }
    (config_dir / "user-config.json").write_text(json.dumps(user_cfg))

    # Template for reset
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "user-config.json").write_text(json.dumps(user_cfg))

    configure(str(config_dir), base_dir=str(tmp_path))
    return tmp_path


_TEST_API_KEY = "original-secret-key"


@pytest.fixture
def client(tmp_config):
    return TestClient(app, headers={"Authorization": f"Bearer {_TEST_API_KEY}"})


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
        resp = client.get("/api/apps?category=supported")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(a["category"] == "supported" for a in data)

    def test_list_categories(self, client):
        resp = client.get("/api/apps/categories")
        assert resp.status_code == 200
        data = resp.json()
        # v2 envelope always exposes all three canonical categories.
        assert len(data) == 3
        active_cats = [c for c in data if c["active"]]
        assert len(active_cats) == 1
        assert active_cats[0]["name"] == "supported"

    def test_toggle_category(self, client):
        resp = client.post("/api/apps/categories/newcomers/toggle")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] is True

        # Toggle back
        resp = client.post("/api/apps/categories/newcomers/toggle")
        assert resp.json()["active"] is False

    def test_toggle_nonexistent_category(self, client):
        resp = client.post("/api/apps/categories/nonexistent/toggle")
        assert resp.status_code == 404

    def test_get_app_detail(self, client):
        resp = client.get("/api/apps/honeygain")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "honeygain"
        assert data["category"] == "supported"

    def test_get_app_detail_case_insensitive(self, client):
        resp = client.get("/api/apps/HoneyGain")
        assert resp.status_code == 200
        assert resp.json()["name"] == "honeygain"

    def test_get_app_not_found(self, client):
        resp = client.get("/api/apps/nonexistent")
        assert resp.status_code == 404


# ===========================================================================
# Apps router — provenance fields (phase-8.2)
# ===========================================================================


class TestAppsProvenance:
    """Verify source, managed_by_m4b, referrals[] and picked_referral_url."""

    def test_list_exposes_provenance_fields(self, client):
        resp = client.get("/api/apps")
        assert resp.status_code == 200
        data = resp.json()
        for entry in data:
            assert "source" in entry
            assert "managed_by_m4b" in entry
            assert "referrals" in entry
            assert "picked_referral_url" in entry
            assert isinstance(entry["referrals"], list)

    def test_default_source_is_builtin(self, client):
        resp = client.get("/api/apps")
        data = resp.json()
        assert all(a["source"] == "builtin" for a in data)

    def test_supported_builtin_is_managed_by_m4b(self, client):
        resp = client.get("/api/apps?category=supported")
        data = resp.json()
        assert data and all(a["managed_by_m4b"] is True for a in data)

    def test_newcomers_not_managed_by_m4b(self, client):
        resp = client.get("/api/apps?category=newcomers")
        data = resp.json()
        assert data and all(a["managed_by_m4b"] is False for a in data)

    def test_referrals_normalized_from_pool(self, client):
        resp = client.get("/api/apps/honeygain")
        data = resp.json()
        assert data["referrals"] == [
            {
                "url": "https://r.honeygain.me/TEST",
                "contributor": "MRColorR",
                "added": None,
                "verified": False,
                "verified_by": [],
            }
        ]

    def test_picked_referral_url_falls_back_to_first_pool_entry(self, client):
        resp = client.get("/api/apps/honeygain")
        data = resp.json()
        assert data["picked_referral_url"] == "https://r.honeygain.me/TEST"

    def test_picked_referral_url_uses_user_setting_when_set(self, tmp_config):
        """A sticky pick in user-config wins over the first pool entry."""
        import json as _json

        user_cfg_path = tmp_config / "config" / "user-config.json"
        user_cfg = _json.loads(user_cfg_path.read_text())
        user_cfg["settings"]["picked_referrals"] = {
            "honeygain": "https://r.honeygain.me/STICKY",
        }
        user_cfg_path.write_text(_json.dumps(user_cfg))

        # Invalidate the config cache so the test reads fresh data.
        from money4band.api._deps import _cache

        _cache.invalidate()

        c = TestClient(app, headers={"Authorization": f"Bearer {_TEST_API_KEY}"})
        resp = c.get("/api/apps/honeygain")
        assert resp.json()["picked_referral_url"] == "https://r.honeygain.me/STICKY"

    def test_app_without_referrals_pool_returns_empty(self, client):
        resp = client.get("/api/apps/testapp")
        data = resp.json()
        assert data["referrals"] == []
        assert data["picked_referral_url"] == ""


# ===========================================================================
# Config router
# ===========================================================================


class TestConfigRouter:
    def test_get_user_config_masked(self, client):
        with patch("money4band.core.viewer._mask_dict", wraps=lambda d: d):
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
            json={"data": {"device_info": {"Nickname": "updated"}}},
        )
        assert resp.status_code == 200

        # Verify the change persisted
        cfg_path = tmp_config / "config" / "user-config.json"
        updated = json.loads(cfg_path.read_text())
        assert updated["device_info"]["Nickname"] == "updated"

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

    def test_update_user_config_rejects_unknown_keys(self, client, tmp_config):
        """Keys that don't exist in the current config should be rejected."""
        resp = client.put(
            "/api/config/user",
            json={"data": {"malicious_key": {"evil": True}}},
        )
        assert resp.status_code == 400
        assert "Unknown config keys" in resp.json()["detail"]

    def test_update_cannot_overwrite_api_key(self, client, tmp_config):
        """The api_key inside m4b_dashboard must be immutable via the config API."""
        resp = client.put(
            "/api/config/user",
            json={"data": {"m4b_dashboard": {"api_key": "attacker-key"}}},
        )
        assert resp.status_code == 200
        # Verify the api_key was NOT changed on disk
        cfg_path = tmp_config / "config" / "user-config.json"
        updated = json.loads(cfg_path.read_text())
        assert updated["m4b_dashboard"]["api_key"] == "original-secret-key"

    def test_update_allows_non_immutable_dashboard_keys(self, client, tmp_config):
        """Other m4b_dashboard fields (e.g. port) should still be updatable."""
        resp = client.put(
            "/api/config/user",
            json={"data": {"m4b_dashboard": {"port": 9090}}},
        )
        assert resp.status_code == 200
        cfg_path = tmp_config / "config" / "user-config.json"
        updated = json.loads(cfg_path.read_text())
        assert updated["m4b_dashboard"]["port"] == 9090
        # api_key still untouched
        assert updated["m4b_dashboard"]["api_key"] == "original-secret-key"

    def test_reset_config(self, client, tmp_config):
        resp = client.post("/api/config/reset")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_get_app_config(self, client):
        resp = client.get("/api/config/app")
        assert resp.status_code == 200
        data = resp.json()
        # Aggregated shape carries the 3 canonical categories at top level.
        assert "supported" in data
        assert "newcomers" in data
        assert "deprecated" in data

    def test_get_m4b_config(self, client):
        resp = client.get("/api/config/m4b")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"]["project_version"] == "5.0.0"

    def test_get_limits(self, client):
        resp = client.get("/api/config/limits")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_profile"] == "standard"
        assert "available_profiles" in data
        assert "standard" in data["available_profiles"]
        assert data["available_profiles"]["standard"]["cpu_pct"] == 0.60

    def test_set_limits_valid(self, client):
        with patch("money4band.system.detector.calculate_resource_limits"):
            resp = client.put("/api/config/limits", json={"profile": "performance"})
        assert resp.status_code == 200
        assert resp.json()["profile"] == "performance"

    def test_set_limits_invalid(self, client):
        resp = client.put("/api/config/limits", json={"profile": "turbo"})
        assert resp.status_code == 400


# ===========================================================================
# Stack router
# ===========================================================================


class TestStackRouter:
    def test_start_stack(self, client):
        with patch("money4band.docker.start.start_all_stacks"):
            resp = client.post("/api/stack/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_start_stack_failure(self, client):
        with patch(
            "money4band.docker.start.start_all_stacks",
            side_effect=RuntimeError("Docker not found"),
        ):
            resp = client.post("/api/stack/start")
        assert resp.status_code == 500

    def test_stop_stack(self, client):
        with patch("money4band.docker.stop.stop_all_stacks"):
            resp = client.post("/api/stack/stop")
        assert resp.status_code == 200

    def test_restart_stack(self, client):
        with (
            patch("money4band.docker.stop.stop_all_stacks"),
            patch("money4band.docker.start.start_all_stacks"),
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
            patch(
                "money4band.system.detector.detect_os",
                return_value={"os_type": "linux"},
            ),
            patch(
                "money4band.system.detector.detect_architecture",
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
        with patch("money4band.system.info.set_dns_mode"):
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
            "money4band.docker.monitor.get_stack_health",
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
            "money4band.docker.monitor.get_stack_health",
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
            "money4band.core.backup.list_backups",
            return_value=[mock_backup],
        ):
            resp = client.get("/api/backups")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_create_backup(self, client):
        with patch(
            "money4band.core.backup.create_backup",
            return_value="/backups/new.tar.gz",
        ):
            resp = client.post("/api/backups")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_restore_backup(self, client, tmp_config):
        fake_backup_dir = tmp_config / "backups"
        fake_backup_dir.mkdir(exist_ok=True)
        backup_file = fake_backup_dir / "fake_backup.tar.gz"
        backup_file.write_text("fake")
        with (
            patch("money4band.api.router_backups.BACKUP_DIR", fake_backup_dir),
            patch("money4band.core.backup.restore_backup"),
        ):
            resp = client.post(
                "/api/backups/restore",
                json={"path": str(backup_file)},
            )
        assert resp.status_code == 200

    def test_restore_nonexistent(self, client, tmp_config):
        fake_backup_dir = tmp_config / "backups"
        fake_backup_dir.mkdir(exist_ok=True)
        with patch("money4band.api.router_backups.BACKUP_DIR", fake_backup_dir):
            resp = client.post(
                "/api/backups/restore",
                json={"path": str(fake_backup_dir / "nonexistent")},
            )
        assert resp.status_code == 404

    def test_restore_path_traversal(self, client, tmp_config):
        """Reject restore paths outside BACKUP_DIR."""
        outside = tmp_config / "evil.tar.gz"
        outside.write_text("evil")
        fake_backup_dir = tmp_config / "backups"
        fake_backup_dir.mkdir(exist_ok=True)
        with patch("money4band.api.router_backups.BACKUP_DIR", fake_backup_dir):
            resp = client.post(
                "/api/backups/restore",
                json={"path": str(outside)},
            )
        assert resp.status_code == 400

    def test_cleanup_backups(self, client):
        with patch(
            "money4band.core.backup.cleanup_backups",
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
            "money4band.core.profiles.list_profiles",
            return_value=["default", "gaming"],
        ):
            resp = client.get("/api/profiles")
        assert resp.status_code == 200
        assert resp.json() == ["default", "gaming"]

    def test_create_profile(self, client):
        with patch(
            "money4band.core.profiles.create_profile",
            return_value="/profiles/myprofile",
        ):
            resp = client.post("/api/profiles", json={"name": "myprofile"})
        assert resp.status_code == 200
        assert resp.json()["profile"] == "myprofile"

    def test_switch_profile(self, client):
        with (
            patch(
                "money4band.core.profiles.list_profiles",
                return_value=["myprofile"],
            ),
            patch("money4band.core.profiles.switch_profile"),
        ):
            resp = client.put("/api/profiles/myprofile/switch")
        assert resp.status_code == 200

    def test_switch_nonexistent(self, client):
        with patch(
            "money4band.core.profiles.list_profiles",
            return_value=[],
        ):
            resp = client.put("/api/profiles/nope/switch")
        assert resp.status_code == 404

    def test_delete_profile(self, client):
        with (
            patch(
                "money4band.core.profiles.list_profiles",
                return_value=["old"],
            ),
            patch("money4band.core.profiles.delete_profile"),
        ):
            resp = client.delete("/api/profiles/old")
        assert resp.status_code == 200

    def test_delete_nonexistent(self, client):
        with patch(
            "money4band.core.profiles.list_profiles",
            return_value=[],
        ):
            resp = client.delete("/api/profiles/nope")
        assert resp.status_code == 404

    def test_create_profile_path_traversal(self, client):
        """Profile names with path traversal characters should be rejected."""
        resp = client.post("/api/profiles", json={"name": "../../../etc"})
        assert resp.status_code == 422  # pydantic validation

    def test_switch_profile_path_traversal(self, client):
        resp = client.put("/api/profiles/..%5C..%5Cetc/switch")
        assert resp.status_code == 400


# ===========================================================================
# Earnings router
# ===========================================================================


class TestEarningsRouter:
    def test_get_earnings(self, client):
        mock_earnings = [
            {"name": "honeygain", "range_low": 1.0, "range_high": 5.0},
            {"name": "earnapp", "range_low": 0.5, "range_high": 3.0},
        ]
        with patch(
            "money4band.apps.earnings.get_app_earnings",
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
            "money4band.apps.earnings.get_app_earnings",
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
            "money4band.network.ip_scorer.analyse_ips",
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
            "money4band.apps.offers.load_all_offers",
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
            "money4band.apps.offers.load_all_offers",
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
                "money4band.api.router_update._LOOPBACK",
                frozenset({"127.0.0.1", "::1", "localhost", "testclient"}),
            ),
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

    def test_apply_update_rejects_remote(self, client):
        """Non-loopback clients should get 403."""
        resp = client.post("/api/update/apply", json={"version": "5.1.0"})
        assert resp.status_code == 403

    def test_apply_update_no_version(self, client):
        with (
            patch(
                "money4band.api.router_update._LOOPBACK",
                frozenset({"127.0.0.1", "::1", "localhost", "testclient"}),
            ),
            patch(
                "money4band.updater.check_for_update",
                return_value=None,
            ),
        ):
            resp = client.post("/api/update/apply", json={})
        assert resp.status_code == 400


# ===========================================================================
# Security router
# ===========================================================================


class TestSecurityRouter:
    def test_stale_images(self, client):
        with patch(
            "money4band.docker.image_security.check_stale_images",
            return_value=[{"image": "old:1.0", "days_since_update": 120}],
        ):
            resp = client.get("/api/security/stale")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_image_digests(self, client):
        with patch(
            "money4band.docker.image_security.log_image_digests",
            return_value=[{"image": "test:latest", "digest": "sha256:abc"}],
        ):
            resp = client.get("/api/security/digests")
        assert resp.status_code == 200

    def test_scan_image(self, client):
        with patch(
            "money4band.docker.image_security.run_scout_cves",
            return_value="No vulnerabilities found",
        ):
            resp = client.post("/api/security/scan/test:latest")
        assert resp.status_code == 200
        assert resp.json()["image"] == "test:latest"

    def test_scan_image_bad_name(self, client):
        resp = client.post("/api/security/scan/; rm -rf /")
        assert resp.status_code in (400, 404, 422)
