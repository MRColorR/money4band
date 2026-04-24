"""Tests for utils.app_schema — validation and community app loading."""

from __future__ import annotations

import json
import os

from money4band.apps.schema import (
    SOURCE_BUILTIN,
    SOURCE_COMMUNITY,
    Addon,
    AppMetadata,
    CatalogEntry,
    DeploymentSpec,
    Referral,
    load_community_apps,
    merge_community_apps,
    validate_app_entry,
)

# ---------------------------------------------------------------------------
# validate_app_entry
# ---------------------------------------------------------------------------


class TestValidateAppEntry:
    def _minimal(self, **overrides):
        entry = {
            "name": "TESTAPP",
            "compose_config": {"image": "test/img:latest", "restart": "always"},
            "flags": {},
            "install_limit": -1,
            "compose_layer": "residential",
        }
        entry.update(overrides)
        return entry

    def test_valid_minimal(self):
        assert validate_app_entry(self._minimal()) == []

    def test_missing_name(self):
        e = self._minimal()
        del e["name"]
        errors = validate_app_entry(e)
        assert any("name" in err for err in errors)

    def test_invalid_name_lowercase(self):
        errors = validate_app_entry(self._minimal(name="badName"))
        assert any("name" in err.lower() or "Invalid" in err for err in errors)

    def test_missing_image(self):
        e = self._minimal()
        del e["compose_config"]["image"]
        errors = validate_app_entry(e)
        assert any("image" in err for err in errors)

    def test_invalid_restart(self):
        e = self._minimal()
        e["compose_config"]["restart"] = "invalid"
        errors = validate_app_entry(e)
        assert any("restart" in err for err in errors)

    def test_invalid_layer(self):
        errors = validate_app_entry(self._minimal(compose_layer="wrong"))
        assert any("compose_layer" in err for err in errors)

    def test_invalid_install_limit_type(self):
        errors = validate_app_entry(self._minimal(install_limit="five"))
        assert any("install_limit" in err for err in errors)

    def test_valid_with_optional_fields(self):
        entry = self._minimal(
            dashboard="https://example.com",
            referrals=[{"url": "https://example.com/ref", "contributor": "MRColorR"}],
            app_details={"official_name": "Test App"},
        )
        assert validate_app_entry(entry) == []


# ---------------------------------------------------------------------------
# load_community_apps
# ---------------------------------------------------------------------------


class TestLoadCommunityApps:
    def _write_app(self, d, name, **overrides):
        entry = {
            "name": name,
            "compose_config": {"image": "test/img:latest", "restart": "always"},
            "flags": {},
            "install_limit": -1,
            "compose_layer": "residential",
        }
        entry.update(overrides)
        with open(os.path.join(d, f"{name}.json"), "w") as f:
            json.dump(entry, f)
        return entry

    def test_empty_directory(self, tmp_path):
        assert load_community_apps(str(tmp_path)) == []

    def test_nonexistent_directory(self):
        assert load_community_apps("/nonexistent/path") == []

    def test_loads_valid_files(self, tmp_path):
        self._write_app(str(tmp_path), "ALPHA")
        self._write_app(str(tmp_path), "BETA")
        result = load_community_apps(str(tmp_path))
        names = {e["name"] for e in result}
        assert names == {"ALPHA", "BETA"}

    def test_skips_invalid_json(self, tmp_path):
        (tmp_path / "BAD.json").write_text("not json")
        self._write_app(str(tmp_path), "GOOD")
        result = load_community_apps(str(tmp_path))
        assert len(result) == 1
        assert result[0]["name"] == "GOOD"

    def test_skips_invalid_schema(self, tmp_path):
        with open(tmp_path / "NONAME.json", "w") as f:
            json.dump({"compose_config": {"image": "x"}}, f)
        self._write_app(str(tmp_path), "VALID")
        result = load_community_apps(str(tmp_path))
        assert len(result) == 1

    def test_ignores_non_json(self, tmp_path):
        (tmp_path / "readme.txt").write_text("ignore me")
        self._write_app(str(tmp_path), "APP")
        assert len(load_community_apps(str(tmp_path))) == 1


# ---------------------------------------------------------------------------
# merge_community_apps
# ---------------------------------------------------------------------------


class TestMergeCommunityApps:
    def _base_config(self):
        return {
            "app_config_version": 1.2,
            "supported": {
                "active": True,
                "entries": [
                    {
                        "name": "EXISTING",
                        "compose_config": {"image": "x"},
                        "flags": {},
                        "install_limit": 1,
                        "compose_layer": "residential",
                    }
                ],
            },
            "newcomers": {"active": False, "entries": []},
        }

    def test_merge_adds_to_candidates(self, tmp_path):
        entry = {
            "name": "NEWAPP",
            "compose_config": {"image": "new/app:latest", "restart": "always"},
            "flags": {},
            "install_limit": -1,
            "compose_layer": "universal",
        }
        with open(tmp_path / "NEWAPP.json", "w") as f:
            json.dump(entry, f)

        config = self._base_config()
        merge_community_apps(config, str(tmp_path))

        candidates = config["newcomers"]["entries"]
        names = {e["name"] for e in candidates}
        assert "NEWAPP" in names

    def test_skips_duplicate(self, tmp_path):
        entry = {
            "name": "EXISTING",
            "compose_config": {"image": "dup/app:latest", "restart": "always"},
            "flags": {},
            "install_limit": -1,
            "compose_layer": "residential",
        }
        with open(tmp_path / "EXISTING.json", "w") as f:
            json.dump(entry, f)

        config = self._base_config()
        merge_community_apps(config, str(tmp_path))

        # Should NOT add duplicate to candidates
        candidates = config["newcomers"]["entries"]
        assert len(candidates) == 0

    def test_creates_candidate_category_if_missing(self, tmp_path):
        entry = {
            "name": "NEWBIE",
            "compose_config": {"image": "n/img:latest", "restart": "always"},
            "flags": {},
            "install_limit": -1,
            "compose_layer": "datacenter",
        }
        with open(tmp_path / "NEWBIE.json", "w") as f:
            json.dump(entry, f)

        config = {
            "app_config_version": 1.2,
            "supported": {"active": True, "entries": []},
        }
        merge_community_apps(config, str(tmp_path))

        assert "newcomers" in config
        assert len(config["newcomers"]["entries"]) == 1

    def test_no_community_dir_returns_unchanged(self):
        config = {"supported": {"active": True, "entries": []}}
        result = merge_community_apps(config, "/nonexistent")
        assert result is config


# ---------------------------------------------------------------------------
# Typed catalog model
# ---------------------------------------------------------------------------


class TestReferral:
    def test_from_string(self):
        r = Referral.from_raw("https://example.com/r/abc")
        assert r.url == "https://example.com/r/abc"
        assert r.contributor == "MRColorR"
        assert r.verified is False
        assert r.verified_by == ()

    def test_from_full_dict(self):
        r = Referral.from_raw(
            {
                "url": "https://example.com/r/x",
                "contributor": "alice",
                "added": "2026-03-01",
                "verified": True,
                "verified_by": ["bob", "carol"],
            }
        )
        assert r.url == "https://example.com/r/x"
        assert r.contributor == "alice"
        assert r.added == "2026-03-01"
        assert r.verified is True
        assert r.verified_by == ("bob", "carol")

    def test_missing_contributor_defaults(self):
        r = Referral.from_raw({"url": "https://x"})
        assert r.contributor == "MRColorR"


class TestCatalogEntryFromRaw:
    def _v12(self, **overrides):
        entry = {
            "name": "TESTAPP",
            "dashboard": "https://test.example/dashboard",
            "referrals": [
                {
                    "url": "https://test.example/r/mrcolorr",
                    "contributor": "MRColorR",
                }
            ],
            "compose_config": {"image": "test/img:latest", "restart": "always"},
            "compose_config_proxy": {"network_mode": "service:proxy"},
            "flags": {"uuid": {"length": 32}},
            "install_limit": 3,
            "compose_layer": "residential",
            "app_details": {
                "official_name": "Test App",
                "publisher": "TestCo",
            },
        }
        entry.update(overrides)
        return entry

    def test_builds_from_v2_shape(self):
        entry = CatalogEntry.from_raw(
            self._v12(), source=SOURCE_BUILTIN, category="supported"
        )
        assert entry.id == "TESTAPP"
        assert entry.source == SOURCE_BUILTIN
        assert entry.category == "supported"
        assert entry.name == "TESTAPP"

    def test_referrals_pool_populated(self):
        entry = CatalogEntry.from_raw(
            self._v12(), source=SOURCE_BUILTIN, category="supported"
        )
        assert len(entry.metadata.referrals) == 1
        ref = entry.metadata.referrals[0]
        assert ref.url == "https://test.example/r/mrcolorr"
        assert ref.contributor == "MRColorR"

    def test_referrals_pool_multi_entry(self):
        raw = self._v12(
            referrals=[
                {"url": "https://a", "contributor": "alice"},
                "https://b",
            ]
        )
        entry = CatalogEntry.from_raw(raw, category="supported")
        assert [r.url for r in entry.metadata.referrals] == ["https://a", "https://b"]
        assert entry.metadata.referrals[0].contributor == "alice"
        assert entry.metadata.referrals[1].contributor == "MRColorR"

    def test_metadata_fields_populated(self):
        entry = CatalogEntry.from_raw(self._v12(), category="supported")
        assert entry.metadata.official_name == "Test App"
        assert entry.metadata.publisher == "TestCo"
        assert entry.metadata.dashboard_url == "https://test.example/dashboard"
        # app_details preserved verbatim in .raw
        assert entry.metadata.raw["official_name"] == "Test App"

    def test_deployment_fields_preserved(self):
        entry = CatalogEntry.from_raw(self._v12(), category="supported")
        assert entry.deployment.compose_config["image"] == "test/img:latest"
        assert entry.deployment.compose_config_proxy == {
            "network_mode": "service:proxy"
        }
        assert entry.deployment.flags == {"uuid": {"length": 32}}
        assert entry.deployment.install_limit == 3
        assert entry.deployment.compose_layer == "residential"
        # full raw dict preserved
        assert entry.deployment.raw["name"] == "TESTAPP"

    def test_additional_details_preserved(self):
        raw = self._v12(additional_details="Service discontinued")
        entry = CatalogEntry.from_raw(raw, category="deprecated")
        assert entry.additional_details == "Service discontinued"
        assert entry.category == "deprecated"

    def test_no_referrals_produces_empty_pool(self):
        raw = self._v12()
        del raw["referrals"]
        entry = CatalogEntry.from_raw(raw, category="supported")
        assert entry.metadata.referrals == []

    def test_install_limit_non_int_falls_back(self):
        raw = self._v12(install_limit="bogus")
        entry = CatalogEntry.from_raw(raw, category="supported")
        assert entry.deployment.install_limit == -1

    def test_missing_name_raises(self):
        raw = self._v12()
        del raw["name"]
        try:
            CatalogEntry.from_raw(raw, category="supported")
        except ValueError as exc:
            assert "name" in str(exc)
        else:
            raise AssertionError("expected ValueError")

    def test_non_dict_raises(self):
        try:
            CatalogEntry.from_raw("not a dict", category="supported")  # type: ignore[arg-type]
        except TypeError:
            pass
        else:
            raise AssertionError("expected TypeError")

    def test_raw_preserves_unknown_fields(self):
        raw = self._v12(future_key="preserved", nested={"deep": 1})
        entry = CatalogEntry.from_raw(raw, category="supported")
        assert entry.raw["future_key"] == "preserved"
        assert entry.raw["nested"] == {"deep": 1}


class TestAddonFromRaw:
    def test_valid_addon(self):
        raw = {
            "name": "HONEYGAIN_POT",
            "parent_id": "HONEYGAIN",
            "compose_config": {"image": "pot/img:latest"},
            "install_limit": 1,
            "compose_layer": "service",
        }
        addon = Addon.from_raw(raw, source=SOURCE_COMMUNITY)
        assert addon.id == "HONEYGAIN_POT"
        assert addon.parent_id == "HONEYGAIN"
        assert addon.source == SOURCE_COMMUNITY
        assert addon.deployment.compose_layer == "service"
        assert addon.deployment.install_limit == 1

    def test_missing_parent_raises(self):
        raw = {"name": "ORPHAN", "compose_config": {}}
        try:
            Addon.from_raw(raw)
        except ValueError as exc:
            assert "parent_id" in str(exc)
        else:
            raise AssertionError("expected ValueError")


class TestDataclassDefaults:
    def test_metadata_defaults(self):
        m = AppMetadata()
        assert m.referrals == []
        assert m.raw == {}

    def test_deployment_defaults(self):
        d = DeploymentSpec()
        assert d.compose_config == {}
        assert d.compose_config_proxy is None
        assert d.flags == {}
        assert d.install_limit == -1
        assert d.compose_layer == "residential"
