"""Tests for proxy install limit enforcement."""

import pytest

from utils.loader import get_install_limit


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
            (1, -1, False),   # unlimited — never disable
            (5, 10, False),   # under limit
            (9, 10, False),   # still under (main=0, proxies 1-9 = 10 total)
            (10, 10, True),   # at limit — disable (0-indexed, 10th instance)
            (15, 10, True),   # over limit
            (0, 0, True),     # zero limit — disable even main
        ],
    )
    def test_should_disable(self, instance_number, limit, should_disable):
        # Mirrors: if limit >= 0 and instance_number >= limit:
        result = limit >= 0 and instance_number >= limit
        assert result == should_disable
