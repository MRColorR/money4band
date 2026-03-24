"""Tests for utils.app_schema — validation and community app loading."""

from __future__ import annotations

import json
import os

from money4band.apps.schema import (
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
            link="https://example.com/ref",
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
            "supported-apps": {
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
            "candidate-apps": {"active": False, "entries": []},
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

        candidates = config["candidate-apps"]["entries"]
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
        candidates = config["candidate-apps"]["entries"]
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
            "supported-apps": {"active": True, "entries": []},
        }
        merge_community_apps(config, str(tmp_path))

        assert "candidate-apps" in config
        assert len(config["candidate-apps"]["entries"]) == 1

    def test_no_community_dir_returns_unchanged(self):
        config = {"supported-apps": {"active": True, "entries": []}}
        result = merge_community_apps(config, "/nonexistent")
        assert result is config
