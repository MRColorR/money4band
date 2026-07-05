"""Tests for money4band.core.catalog_store and catalog_migration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from money4band.core.catalog_migration import (
    LEGACY_BACKUP_SUFFIX,
    migrate_catalog_file,
)
from money4band.core.catalog_store import (
    CATEGORIES,
    aggregate,
    catalog_root,
    default_envelope,
    delete_entry,
    is_envelope,
    is_legacy_monolithic,
    move_entry,
    read_entries_dir,
    set_category_active,
    split_monolithic,
    write_entry,
    write_envelope,
)


@pytest.fixture
def monolithic_payload() -> dict:
    return {
        "app_config_version": 2.0,
        "supported": {
            "active": True,
            "entries": [
                {"name": "HONEYGAIN", "compose_config": {"image": "honeygain:latest"}},
                {"name": "EARNAPP", "compose_config": {"image": "earnapp:latest"}},
            ],
        },
        "newcomers": {
            "active": False,
            "entries": [
                {"name": "NEWAPP", "compose_config": {"image": "newapp:latest"}}
            ],
        },
        "deprecated": {"active": False, "entries": []},
    }


class TestDetection:
    def test_monolithic_detected(self, monolithic_payload):
        assert is_legacy_monolithic(monolithic_payload)
        assert not is_envelope(monolithic_payload)

    def test_envelope_detected(self):
        env = default_envelope()
        assert is_envelope(env)
        assert not is_legacy_monolithic(env)

    def test_empty_object_is_neither(self):
        assert not is_envelope({})
        assert not is_legacy_monolithic({})


class TestWriteAndRead:
    def test_write_entry_creates_per_category_file(self, tmp_path: Path):
        config = tmp_path / "m4b-config.json"
        dest = write_entry({"name": "FOO"}, config, "supported")
        assert dest == catalog_root(config) / "supported" / "FOO.json"
        assert json.loads(dest.read_text()) == {"name": "FOO"}

    def test_write_entry_rejects_unknown_category(self, tmp_path: Path):
        with pytest.raises(ValueError):
            write_entry({"name": "X"}, tmp_path / "m4b-config.json", "nope")

    def test_write_entry_requires_name(self, tmp_path: Path):
        with pytest.raises(ValueError):
            write_entry({}, tmp_path / "m4b-config.json", "supported")

    def test_read_entries_dir_sorted(self, tmp_path: Path):
        config = tmp_path / "m4b-config.json"
        write_entry({"name": "ZULU"}, config, "supported")
        write_entry({"name": "ALPHA"}, config, "supported")
        entries = read_entries_dir(catalog_root(config), "supported")
        assert [e["name"] for e in entries] == ["ALPHA", "ZULU"]

    def test_read_entries_dir_missing_returns_empty(self, tmp_path: Path):
        assert read_entries_dir(catalog_root(tmp_path / "a.json"), "supported") == []

    def test_delete_entry(self, tmp_path: Path):
        config = tmp_path / "m4b-config.json"
        write_entry({"name": "FOO"}, config, "supported")
        assert delete_entry(config, "supported", "FOO") is True
        assert delete_entry(config, "supported", "FOO") is False


class TestMove:
    def test_move_between_categories(self, tmp_path: Path):
        config = tmp_path / "m4b-config.json"
        write_entry({"name": "X", "v": 1}, config, "newcomers")
        dest = move_entry(config, "X", "newcomers", "supported")
        assert dest.exists()
        assert not (catalog_root(config) / "newcomers" / "X.json").exists()
        assert json.loads(dest.read_text())["v"] == 1

    def test_move_with_updates(self, tmp_path: Path):
        config = tmp_path / "m4b-config.json"
        write_entry({"name": "X", "v": 1}, config, "newcomers")
        move_entry(
            config,
            "X",
            "newcomers",
            "supported",
            updates={"v": 2, "app_details": {"recommendation": "promoted"}},
        )
        moved = json.loads((catalog_root(config) / "supported" / "X.json").read_text())
        assert moved["v"] == 2
        assert moved["app_details"]["recommendation"] == "promoted"

    def test_move_missing_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            move_entry(tmp_path / "a.json", "GHOST", "newcomers", "supported")


class TestEnvelope:
    def test_set_category_active_flips_flag(self, tmp_path: Path):
        config = tmp_path / "m4b-config.json"
        write_envelope(default_envelope(), config)
        set_category_active(config, "newcomers", True)
        env = json.loads(config.read_text())
        assert env["categories"]["newcomers"]["active"] is True

    def test_default_envelope_has_all_categories(self):
        env = default_envelope()
        for cat in CATEGORIES:
            assert cat in env["categories"]
            assert "active" in env["categories"][cat]

    def test_default_envelope_includes_disabled_community_source(self):
        env = default_envelope()
        names = [s.get("name") for s in env["catalog_sources"]]
        assert "builtin" in names
        assert "community" in names
        community = next(
            s for s in env["catalog_sources"] if s.get("name") == "community"
        )
        assert community["type"] == "remote"
        assert community["enabled"] is False
        assert community["url"].startswith("https://raw.githubusercontent.com/")


class TestSplit:
    def test_split_writes_all_entries(self, tmp_path, monolithic_payload):
        config = tmp_path / "m4b-config.json"
        envelope, count = split_monolithic(monolithic_payload, config)
        assert count == 3
        assert is_envelope(envelope)
        assert envelope["categories"]["supported"]["active"] is True
        assert envelope["categories"]["newcomers"]["active"] is False
        # Per-file bundles written
        root = catalog_root(config)
        assert (root / "supported" / "HONEYGAIN.json").exists()
        assert (root / "supported" / "EARNAPP.json").exists()
        assert (root / "newcomers" / "NEWAPP.json").exists()


class TestAggregate:
    def test_roundtrip_via_split_and_aggregate(self, tmp_path, monolithic_payload):
        config = tmp_path / "m4b-config.json"
        envelope, _ = split_monolithic(monolithic_payload, config)
        write_envelope(envelope, config)

        result = aggregate(envelope, config)
        assert result["app_config_version"] == 2.0
        assert result["supported"]["active"] is True
        names = {e["name"] for e in result["supported"]["entries"]}
        assert names == {"HONEYGAIN", "EARNAPP"}
        assert result["newcomers"]["active"] is False
        assert {e["name"] for e in result["newcomers"]["entries"]} == {"NEWAPP"}
        assert result["deprecated"]["entries"] == []

    def test_preserves_catalog_sources(self, tmp_path):
        config = tmp_path / "m4b-config.json"
        env = default_envelope()
        result = aggregate(env, config)
        assert "catalog_sources" in result
        assert result["catalog_sources"][0]["type"] == "local"


class TestMigration:
    def test_migrate_writes_envelope_and_bundles(self, tmp_path, monolithic_payload):
        config = tmp_path / "m4b-config.json"
        config.write_text(json.dumps(monolithic_payload))
        assert migrate_catalog_file(config) is True

        # Envelope replaced file
        data = json.loads(config.read_text())
        assert is_envelope(data)
        # Backup created
        backup = config.with_suffix(config.suffix + LEGACY_BACKUP_SUFFIX)
        assert backup.exists()
        # Per-file bundles exist
        root = catalog_root(config)
        assert (root / "supported" / "HONEYGAIN.json").exists()

    def test_migration_is_idempotent(self, tmp_path, monolithic_payload):
        config = tmp_path / "m4b-config.json"
        config.write_text(json.dumps(monolithic_payload))
        assert migrate_catalog_file(config) is True
        # Second call: no-op
        assert migrate_catalog_file(config) is False

    def test_missing_file_returns_false(self, tmp_path):
        assert migrate_catalog_file(tmp_path / "nope.json") is False

    def test_already_envelope_returns_false(self, tmp_path):
        config = tmp_path / "m4b-config.json"
        config.write_text(json.dumps(default_envelope()))
        assert migrate_catalog_file(config) is False

    def test_backup_not_overwritten(self, tmp_path, monolithic_payload):
        config = tmp_path / "m4b-config.json"
        config.write_text(json.dumps(monolithic_payload))
        migrate_catalog_file(config)
        backup = config.with_suffix(config.suffix + LEGACY_BACKUP_SUFFIX)
        original_mtime = backup.stat().st_mtime
        # Re-migrate a fresh monolithic file - backup should stay untouched
        config.write_text(json.dumps(monolithic_payload))
        migrate_catalog_file(config)
        # Backup's mtime unchanged (not overwritten)
        # Note: after second migrate the file is envelope; the previous
        # backup from the first run must remain intact.
        assert backup.stat().st_mtime == original_mtime


class TestLoaderIntegration:
    """End-to-end: loader auto-migrates + aggregates."""

    def test_loader_migrates_monolithic_automatically(
        self, tmp_path, monolithic_payload
    ):
        from money4band.core.loader import load_app_config_with_overlays

        config = tmp_path / "m4b-config.json"
        config.write_text(json.dumps(monolithic_payload))
        result = load_app_config_with_overlays(str(config))
        # Migrated -> per-file bundles exist
        assert (catalog_root(config) / "supported" / "HONEYGAIN.json").exists()
        # In-memory shape is the historical one
        assert {e["name"] for e in result["supported"]["entries"]} == {
            "HONEYGAIN",
            "EARNAPP",
        }
        assert result["supported"]["active"] is True

    def test_loader_reads_envelope_directly_after_migration(
        self, tmp_path, monolithic_payload
    ):
        from money4band.core.loader import load_app_config_with_overlays

        config = tmp_path / "m4b-config.json"
        config.write_text(json.dumps(monolithic_payload))
        load_app_config_with_overlays(str(config))  # migrate
        # Subsequent loads: file is already an envelope
        result = load_app_config_with_overlays(str(config))
        assert {e["name"] for e in result["supported"]["entries"]} == {
            "HONEYGAIN",
            "EARNAPP",
        }
