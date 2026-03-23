from __future__ import annotations

"""Tests for utils.readme_generator — auto-generation of README/APPS.md app tables."""

from pathlib import Path
from typing import Any

from money4band.readme_generator import (
    _BEGIN_MARKER,
    _END_MARKER,
    _bool_md,
    _collect_apps,
    _effective_status,
    _extract_referral_code,
    _format_devices,
    _format_earnings,
    _format_payout,
    _replace_between_markers,
    generate_apps_md_table,
    generate_readme_table,
    update_apps_md,
    update_readme,
)

# ---------------------------------------------------------------------------
# Sample config fixture
# ---------------------------------------------------------------------------

_SAMPLE_CONFIG: dict[str, Any] = {
    "app_config_version": 1.2,
    "supported-apps": {
        "active": True,
        "entries": [
            {
                "name": "TESTAPP",
                "link": "https://example.com/ref/123",
                "app_details": {
                    "official_name": "TestApp",
                    "status": "active",
                    "ip_policy": {"residential": True, "datacenter": False},
                    "device_limits": {
                        "max_devices_per_account": 10,
                        "max_devices_per_ip": 1,
                    },
                    "earnings": {
                        "payout_methods": ["PayPal", "crypto"],
                        "avg_monthly_residential_usd": "1-5",
                    },
                },
            },
            {
                "name": "UNSTABLEAPP",
                "link": "https://example.com/signup?code=ABC123",
                "app_details": {
                    "official_name": "UnstableApp",
                    "status": "unstable",
                    "ip_policy": {"residential": True, "datacenter": "partial"},
                    "device_limits": {
                        "max_devices_per_account": "unlimited",
                        "max_devices_per_ip": "undocumented",
                    },
                    "earnings": {
                        "payout_methods": ["undocumented"],
                        "avg_monthly_residential_usd": "unknown",
                    },
                },
            },
        ],
    },
    "deprecated-apps": {
        "active": False,
        "entries": [
            {
                "name": "OLDAPP",
                "link": "https://old.example.com",
                "removal_reason": "Service discontinued",
                "app_details": {
                    "official_name": "OldApp",
                    "status": "deprecated",
                    "ip_policy": {"residential": False, "datacenter": False},
                    "device_limits": {
                        "max_devices_per_account": "N/A",
                        "max_devices_per_ip": "N/A",
                    },
                    "earnings": {
                        "payout_methods": None,
                        "avg_monthly_residential_usd": "N/A",
                    },
                },
            },
        ],
    },
    "candidate-apps": {
        "active": False,
        "entries": [
            {
                "name": "NEWAPP",
                "link": "https://new.example.com",
                "app_details": {
                    "official_name": "NewApp",
                    "status": "active",
                    "ip_policy": {"residential": True, "datacenter": True},
                    "device_limits": {
                        "max_devices_per_account": "unlimited",
                        "max_devices_per_ip": -1,
                    },
                    "earnings": {
                        "payout_methods": ["crypto"],
                        "avg_monthly_residential_usd": None,
                    },
                },
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# _bool_md
# ---------------------------------------------------------------------------


class TestBoolMd:
    def test_true(self) -> None:
        assert _bool_md(True) == "\u2705"

    def test_false(self) -> None:
        assert _bool_md(False) == "\u274c"

    def test_none(self) -> None:
        assert _bool_md(None) == "\u2014"

    def test_string(self) -> None:
        assert _bool_md("partial") == "\u2014"


# ---------------------------------------------------------------------------
# _effective_status
# ---------------------------------------------------------------------------


class TestEffectiveStatus:
    def test_active(self) -> None:
        assert _effective_status("supported-apps", {"status": "active"}) == "active"

    def test_unstable(self) -> None:
        assert _effective_status("supported-apps", {"status": "unstable"}) == "unstable"

    def test_deprecated(self) -> None:
        assert (
            _effective_status("deprecated-apps", {"status": "deprecated"})
            == "deprecated"
        )

    def test_candidate(self) -> None:
        assert _effective_status("candidate-apps", {"status": "active"}) == "candidate"


# ---------------------------------------------------------------------------
# _extract_referral_code
# ---------------------------------------------------------------------------


class TestExtractReferralCode:
    def test_short_code(self) -> None:
        assert (
            _extract_referral_code("https://example.com/signup?code=ABC123") == "ABC123"
        )

    def test_long_code_rejected(self) -> None:
        assert (
            _extract_referral_code("https://example.com/?code=ABCDEFGHIJKLMNOP") is None
        )

    def test_no_code_param(self) -> None:
        assert _extract_referral_code("https://example.com/?ref=abc") is None

    def test_empty_url(self) -> None:
        assert _extract_referral_code("") is None


# ---------------------------------------------------------------------------
# _format_devices / _format_payout / _format_earnings
# ---------------------------------------------------------------------------


class TestFormatHelpers:
    def test_devices_int(self) -> None:
        assert _format_devices(10) == "10"

    def test_devices_unlimited_int(self) -> None:
        assert _format_devices(-1) == "\u221e"

    def test_devices_unlimited_str(self) -> None:
        assert _format_devices("unlimited") == "Unlimited"

    def test_devices_undocumented(self) -> None:
        assert _format_devices("undocumented") == "\u2014"

    def test_devices_none(self) -> None:
        assert _format_devices(None) == "\u2014"

    def test_payout_normal(self) -> None:
        assert _format_payout(["PayPal", "crypto"]) == "PayPal, crypto"

    def test_payout_undocumented(self) -> None:
        assert _format_payout(["undocumented"]) == "\u2014"

    def test_payout_none(self) -> None:
        assert _format_payout(None) == "\u2014"

    def test_payout_empty(self) -> None:
        assert _format_payout([]) == "\u2014"

    def test_earnings_normal(self) -> None:
        assert _format_earnings("1-5") == "$1-5"

    def test_earnings_unknown(self) -> None:
        assert _format_earnings("unknown") == "\u2014"

    def test_earnings_na(self) -> None:
        assert _format_earnings("N/A") == "\u2014"

    def test_earnings_none(self) -> None:
        assert _format_earnings(None) == "\u2014"

    def test_earnings_unknown_prefix(self) -> None:
        assert _format_earnings("unknown (early stage)") == "\u2014"


# ---------------------------------------------------------------------------
# _collect_apps
# ---------------------------------------------------------------------------


class TestCollectApps:
    def test_count(self) -> None:
        apps = _collect_apps(_SAMPLE_CONFIG)
        assert len(apps) == 4

    def test_order(self) -> None:
        apps = _collect_apps(_SAMPLE_CONFIG)
        names = [a["name"] for a in apps]
        assert names == ["TestApp", "UnstableApp", "NewApp", "OldApp"]

    def test_candidate_status(self) -> None:
        apps = _collect_apps(_SAMPLE_CONFIG)
        candidate = [a for a in apps if a["category"] == "candidate-apps"][0]
        assert candidate["status"] == "candidate"


# ---------------------------------------------------------------------------
# generate_readme_table
# ---------------------------------------------------------------------------


class TestGenerateReadmeTable:
    def test_header(self) -> None:
        table = generate_readme_table(_SAMPLE_CONFIG)
        lines = table.split("\n")
        assert "| App | Residential | VPS/DC | Payout |" in lines[0]

    def test_row_count(self) -> None:
        table = generate_readme_table(_SAMPLE_CONFIG)
        data_rows = [l for l in table.split("\n") if l.startswith(("| [", "| **"))]
        assert len(data_rows) == 4

    def test_active_app_row(self) -> None:
        table = generate_readme_table(_SAMPLE_CONFIG)
        assert "[**TestApp**](https://example.com/ref/123)" in table
        assert "\u2705" in table  # residential = True
        assert "\u274c" in table  # datacenter = False

    def test_payout_in_row(self) -> None:
        table = generate_readme_table(_SAMPLE_CONFIG)
        assert "PayPal, crypto" in table

    def test_undocumented_payout_dash(self) -> None:
        table = generate_readme_table(_SAMPLE_CONFIG)
        # UnstableApp has payout_methods=["undocumented"] -> should show —
        lines = [l for l in table.split("\n") if "UnstableApp" in l]
        assert len(lines) == 1
        assert "\u2014" in lines[0]


# ---------------------------------------------------------------------------
# generate_apps_md_table
# ---------------------------------------------------------------------------


class TestGenerateAppsMdTable:
    def test_header(self) -> None:
        table = generate_apps_md_table(_SAMPLE_CONFIG)
        assert "| App | Link | M4B Status |" in table

    def test_status_emojis(self) -> None:
        table = generate_apps_md_table(_SAMPLE_CONFIG)
        assert "\U0001f7e2" in table  # active
        assert "\U0001f7e1" in table  # unstable
        assert "\U0001f51c" in table  # candidate
        assert "\U0001f534" in table  # deprecated

    def test_referral_code(self) -> None:
        table = generate_apps_md_table(_SAMPLE_CONFIG)
        assert "code: `ABC123`" in table

    def test_device_limits(self) -> None:
        table = generate_apps_md_table(_SAMPLE_CONFIG)
        assert "| 10 |" in table  # max_devices_per_account for TestApp

    def test_earnings_column(self) -> None:
        table = generate_apps_md_table(_SAMPLE_CONFIG)
        assert "$1-5" in table

    def test_unlimited_devices(self) -> None:
        table = generate_apps_md_table(_SAMPLE_CONFIG)
        assert "\u221e" in table  # NewApp max_devices_per_ip = -1


# ---------------------------------------------------------------------------
# _replace_between_markers
# ---------------------------------------------------------------------------


class TestReplaceBetweenMarkers:
    def test_replaces_content(self) -> None:
        text = f"before\n{_BEGIN_MARKER}\nold content\n{_END_MARKER}\nafter"
        result = _replace_between_markers(text, "new content")
        assert result is not None
        assert "new content" in result
        assert "old content" not in result
        assert "before" in result
        assert "after" in result

    def test_no_markers_returns_none(self) -> None:
        assert _replace_between_markers("no markers here", "content") is None

    def test_preserves_surrounding(self) -> None:
        text = f"line1\n{_BEGIN_MARKER}\nstuff\n{_END_MARKER}\nline2"
        result = _replace_between_markers(text, "replaced")
        assert result is not None
        assert result.startswith("line1\n")
        assert result.endswith("\nline2")


# ---------------------------------------------------------------------------
# update_readme / update_apps_md (file-level integration)
# ---------------------------------------------------------------------------


class TestUpdateFiles:
    def test_update_readme(self, tmp_path: Path) -> None:
        readme = tmp_path / "README.md"
        readme.write_text(
            f"# Title\n\n**30+ apps** tracked.\n\n{_BEGIN_MARKER}\nold table\n{_END_MARKER}\n\nfooter\n",
            encoding="utf-8",
        )
        result = update_readme(_SAMPLE_CONFIG, readme)
        assert result is True
        content = readme.read_text(encoding="utf-8")
        assert "TestApp" in content
        assert "old table" not in content
        assert "**4 apps** tracked" in content

    def test_update_apps_md(self, tmp_path: Path) -> None:
        apps_md = tmp_path / "APPS.md"
        apps_md.write_text(
            f"# Apps\n\n{_BEGIN_MARKER}\nold\n{_END_MARKER}\n\nfooter\n",
            encoding="utf-8",
        )
        result = update_apps_md(_SAMPLE_CONFIG, apps_md)
        assert result is True
        content = apps_md.read_text(encoding="utf-8")
        assert "TestApp" in content
        assert "old" not in content or "OldApp" in content

    def test_missing_markers(self, tmp_path: Path) -> None:
        readme = tmp_path / "README.md"
        readme.write_text("no markers", encoding="utf-8")
        result = update_readme(_SAMPLE_CONFIG, readme)
        assert result is False

    def test_missing_file(self, tmp_path: Path) -> None:
        result = update_readme(_SAMPLE_CONFIG, tmp_path / "nonexistent.md")
        assert result is False

    def test_idempotent(self, tmp_path: Path) -> None:
        readme = tmp_path / "README.md"
        readme.write_text(
            f"**30+ apps** tracked.\n\n{_BEGIN_MARKER}\nold\n{_END_MARKER}\n",
            encoding="utf-8",
        )
        update_readme(_SAMPLE_CONFIG, readme)
        content1 = readme.read_text(encoding="utf-8")
        update_readme(_SAMPLE_CONFIG, readme)
        content2 = readme.read_text(encoding="utf-8")
        assert content1 == content2
