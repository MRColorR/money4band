"""Tests for utils.earnings_estimator."""

from __future__ import annotations

from money4band.apps.earnings import (
    display_earnings_summary,
    get_app_earnings,
    parse_earnings_range,
)


class TestParseEarningsRange:
    def test_normal_range(self):
        assert parse_earnings_range("1-9") == (1.0, 9.0)

    def test_decimal_range(self):
        assert parse_earnings_range("0.5-2") == (0.5, 2.0)

    def test_single_number(self):
        assert parse_earnings_range("5") == (5.0, 5.0)

    def test_unknown(self):
        assert parse_earnings_range("unknown") is None

    def test_undocumented(self):
        assert parse_earnings_range("undocumented") is None

    def test_none(self):
        assert parse_earnings_range(None) is None

    def test_empty(self):
        assert parse_earnings_range("") is None

    def test_spaced_range(self):
        assert parse_earnings_range("0.5 - 1.5") == (0.5, 1.5)


class TestGetAppEarnings:
    def _config(self, earnings=None):
        return {
            "supported": {
                "active": True,
                "entries": [
                    {
                        "name": "APP1",
                        "app_details": {
                            "earnings": earnings
                            or {
                                "model": "per-GB",
                                "avg_monthly_residential_usd": "1-5",
                                "avg_monthly_datacenter_usd": "0.5-2",
                                "min_payout": "$5",
                            }
                        },
                    }
                ],
            }
        }

    def test_residential(self):
        rows = get_app_earnings(self._config(), ip_type="residential")
        assert len(rows) == 1
        assert rows[0]["range_low"] == 1.0
        assert rows[0]["range_high"] == 5.0

    def test_datacenter(self):
        rows = get_app_earnings(self._config(), ip_type="datacenter")
        assert rows[0]["range_low"] == 0.5

    def test_unknown_earnings(self):
        rows = get_app_earnings(
            self._config({"model": "x", "avg_monthly_residential_usd": "unknown"})
        )
        assert rows[0]["range_low"] == 0.0
        assert rows[0]["range_high"] == 0.0

    def test_skips_inactive_categories(self):
        cfg = {
            "supported": {
                "active": True,
                "entries": [
                    {
                        "name": "A",
                        "app_details": {
                            "earnings": {"avg_monthly_residential_usd": "1-2"}
                        },
                    }
                ],
            },
            "deprecated": {
                "active": False,
                "entries": [
                    {
                        "name": "B",
                        "app_details": {
                            "earnings": {"avg_monthly_residential_usd": "3-4"}
                        },
                    }
                ],
            },
        }
        rows = get_app_earnings(cfg)
        assert len(rows) == 1
        assert rows[0]["name"] == "A"


class TestDisplayEarningsSummary:
    def test_prints_without_error(self, capsys):
        cfg = {
            "supported": {
                "active": True,
                "entries": [
                    {
                        "name": "TESTAPP",
                        "app_details": {
                            "earnings": {
                                "model": "per-GB",
                                "avg_monthly_residential_usd": "2-8",
                                "min_payout": "$5",
                            }
                        },
                    }
                ],
            }
        }
        display_earnings_summary(cfg)
        out = capsys.readouterr().out
        assert "TESTAPP" in out
        assert "$2.00" in out
        assert "TOTAL" in out

    def test_no_active_apps(self, capsys):
        display_earnings_summary({"deprecated": {"active": False, "entries": []}})
        out = capsys.readouterr().out
        assert "No active apps" in out
