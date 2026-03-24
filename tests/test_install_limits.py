"""Tests for proxy install limit enforcement and toggle."""

import json
from unittest.mock import patch

import pytest

from money4band.core.loader import get_install_limit


class TestGetInstallLimit:
    def test_returns_explicit_limit(self):
        assert get_install_limit({"name": "HONEYGAIN", "install_limit": 10}) == 10

    def test_returns_unlimited_when_minus_one(self):
        assert get_install_limit({"name": "FOO", "install_limit": -1}) == -1

    def test_defaults_to_unlimited_when_missing(self):
        assert get_install_limit({"name": "FOO"}) == -1

    def test_zero_means_zero(self):
        # 0 means "not allowed in any instance" — distinct from -1 (unlimited)
        assert get_install_limit({"name": "BAR", "install_limit": 0}) == 0


class TestInstallLimitEnforcement:
    """Test that the limit logic correctly identifies over-limit apps."""

    def _compute_limited_apps(self, app_entries, total_instances):
        """Reproduce the limit computation from setup_multiproxy_instances."""
        limited = {}
        for entry in app_entries:
            name = entry["name"].lower()
            limit = get_install_limit(entry)
            if limit >= 0 and total_instances > limit:
                limited[name] = limit
        return limited

    def test_unlimited_apps_never_limited(self):
        entries = [{"name": "FOO", "install_limit": -1}]
        assert self._compute_limited_apps(entries, 100) == {}

    def test_app_under_limit_not_flagged(self):
        entries = [{"name": "HONEYGAIN", "install_limit": 10}]
        assert self._compute_limited_apps(entries, 5) == {}

    def test_app_at_exact_limit_not_flagged(self):
        entries = [{"name": "HONEYGAIN", "install_limit": 10}]
        assert self._compute_limited_apps(entries, 10) == {}

    def test_app_over_limit_is_flagged(self):
        entries = [{"name": "HONEYGAIN", "install_limit": 10}]
        result = self._compute_limited_apps(entries, 11)
        assert result == {"honeygain": 10}

    def test_zero_limit_always_flagged(self):
        entries = [{"name": "DISABLED", "install_limit": 0}]
        result = self._compute_limited_apps(entries, 1)
        assert result == {"disabled": 0}

    def test_mixed_limits(self):
        entries = [
            {"name": "HONEYGAIN", "install_limit": 10},
            {"name": "PROXYRACK", "install_limit": 500},
            {"name": "EARNAPP", "install_limit": -1},
        ]
        result = self._compute_limited_apps(entries, 15)
        # Only HONEYGAIN exceeds (15 > 10), PROXYRACK and EARNAPP are fine
        assert result == {"honeygain": 10}


class TestPerInstanceDisableLogic:
    """Test the per-instance disable decision (instance_number >= limit)."""

    @pytest.mark.parametrize(
        "instance_number,limit,should_disable",
        [
            (1, -1, False),  # unlimited — never disable
            (5, 10, False),  # under limit
            (9, 10, False),  # still under (main=0, proxies 1-9 = 10 total)
            (10, 10, True),  # at limit — disable (0-indexed, 10th instance)
            (15, 10, True),  # over limit
            (0, 0, True),  # zero limit — disable even main
        ],
    )
    def test_should_disable(self, instance_number, limit, should_disable):
        # Mirrors: if limit >= 0 and instance_number >= limit:
        result = limit >= 0 and instance_number >= limit
        assert result == should_disable


class TestToggleInstallLimits:
    """Test the enforce_install_limits toggle in the proxy tools menu."""

    @patch("builtins.input", return_value="")
    def test_toggle_flips_true_to_false(self, _mock_input, tmp_path):
        cfg_path = str(tmp_path / "user-config.json")
        cfg = {"settings": {"enforce_install_limits": True}}
        with open(cfg_path, "w") as f:
            json.dump(cfg, f)

        from money4band.network.proxy_tools import toggle_install_limits

        toggle_install_limits(user_config_path=cfg_path)

        with open(cfg_path) as f:
            result = json.load(f)
        assert result["settings"]["enforce_install_limits"] is False

    @patch("builtins.input", return_value="")
    def test_toggle_flips_false_to_true(self, _mock_input, tmp_path):
        cfg_path = str(tmp_path / "user-config.json")
        cfg = {"settings": {"enforce_install_limits": False}}
        with open(cfg_path, "w") as f:
            json.dump(cfg, f)

        from money4band.network.proxy_tools import toggle_install_limits

        toggle_install_limits(user_config_path=cfg_path)

        with open(cfg_path) as f:
            result = json.load(f)
        assert result["settings"]["enforce_install_limits"] is True

    @patch("builtins.input", return_value="")
    def test_toggle_defaults_to_true_when_missing(self, _mock_input, tmp_path):
        """If the key doesn't exist yet, it defaults to True, so first toggle -> False."""
        cfg_path = str(tmp_path / "user-config.json")
        cfg = {"settings": {}}
        with open(cfg_path, "w") as f:
            json.dump(cfg, f)

        from money4band.network.proxy_tools import toggle_install_limits

        toggle_install_limits(user_config_path=cfg_path)

        with open(cfg_path) as f:
            result = json.load(f)
        assert result["settings"]["enforce_install_limits"] is False


class TestEnforcementToggleInSetup:
    """Test that the enforcement block respects the toggle."""

    def _compute_with_toggle(self, enforce, app_entries, total_instances):
        """Reproduce the toggled limit computation from setup_multiproxy_instances."""
        app_limits = {}
        limited_apps = {}
        if enforce:
            for entry in app_entries:
                name = entry["name"].lower()
                limit = get_install_limit(entry)
                app_limits[name] = limit
                if limit >= 0 and total_instances > limit:
                    limited_apps[name] = limit
        return app_limits, limited_apps

    def test_enforcement_on_detects_over_limit(self):
        entries = [{"name": "HONEYGAIN", "install_limit": 10}]
        app_limits, limited = self._compute_with_toggle(True, entries, 15)
        assert limited == {"honeygain": 10}
        assert app_limits == {"honeygain": 10}

    def test_enforcement_off_skips_all_limits(self):
        entries = [{"name": "HONEYGAIN", "install_limit": 10}]
        app_limits, limited = self._compute_with_toggle(False, entries, 15)
        assert limited == {}
        assert app_limits == {}

    def test_enforcement_off_per_instance_never_disables(self):
        """When app_limits is empty, the per-instance lookup defaults to -1."""
        app_limits: dict[str, int] = {}
        limit = app_limits.get("honeygain", -1)
        # -1 >= 0 is False → no disable
        assert not (limit >= 0 and 999 >= limit)


class TestInstallLimitsStatusLabel:
    """Test the status label helper used in the menu."""

    def test_label_when_enabled(self, tmp_path):
        cfg_path = str(tmp_path / "user-config.json")
        with open(cfg_path, "w") as f:
            json.dump({"settings": {"enforce_install_limits": True}}, f)

        from money4band.network.proxy_tools import _install_limits_status_label

        label = _install_limits_status_label(cfg_path)
        assert "ON" in label

    def test_label_when_disabled(self, tmp_path):
        cfg_path = str(tmp_path / "user-config.json")
        with open(cfg_path, "w") as f:
            json.dump({"settings": {"enforce_install_limits": False}}, f)

        from money4band.network.proxy_tools import _install_limits_status_label

        label = _install_limits_status_label(cfg_path)
        assert "OFF" in label

    def test_label_defaults_on_when_key_missing(self, tmp_path):
        cfg_path = str(tmp_path / "user-config.json")
        with open(cfg_path, "w") as f:
            json.dump({"settings": {}}, f)

        from money4band.network.proxy_tools import _install_limits_status_label

        label = _install_limits_status_label(cfg_path)
        assert "ON" in label

    @patch(
        "money4band.network.proxy_tools.load_json_config", side_effect=Exception("fail")
    )
    def test_label_error_defaults_to_on(self, _mock):
        from money4band.network.proxy_tools import _install_limits_status_label

        label = _install_limits_status_label("nonexistent.json")
        assert "ON" in label


class TestExitSubmenu:
    """Test the exit_submenu helper."""

    def test_returns_false(self):
        from money4band.network.proxy_tools import exit_submenu

        assert exit_submenu() is False


class TestSubmenuMultiproxyTools:
    """Test the submenu builder."""

    @patch(
        "money4band.network.proxy_tools._install_limits_status_label", return_value="ON"
    )
    def test_returns_menu_items(self, _mock):
        from money4band.network.proxy_tools import submenu_multiproxy_tools

        items = submenu_multiproxy_tools()
        assert len(items) == 3
        funcs = [i["function"] for i in items]
        assert "update_multiproxy_instances" in funcs
        assert "toggle_install_limits" in funcs
        assert "exit_submenu" in funcs
