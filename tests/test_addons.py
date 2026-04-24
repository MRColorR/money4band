"""Addon bundles with parent_id merge.

Covers:
* catalog_store.read_addons_dir (filesystem reader).
* LocalSource.load_addons / RemoteSource.load_addons.
* aggregate_from_sources → top-level ``addons`` list (first-wins).
* money4band.apps.addons.get_addons_for lookup.
* remote_cache.split_addons_from_manifest + replace_entries(addons=...).
"""

from __future__ import annotations

import json
from pathlib import Path

from money4band.apps.addons import get_addons_for
from money4band.apps.remote_cache import (
    replace_entries,
    split_addons_from_manifest,
)
from money4band.apps.sources import LocalSource, aggregate_from_sources
from money4band.core.catalog_store import (
    ADDONS_DIRNAME,
    read_addons_dir,
)


def _seed_catalog(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "supported").mkdir(exist_ok=True)
    (root / "supported" / "HONEYGAIN.json").write_text(
        json.dumps(
            {
                "name": "HONEYGAIN",
                "compose_config": {"image": "honeygain/honeygain:latest"},
            }
        ),
        encoding="utf-8",
    )
    (root / ADDONS_DIRNAME).mkdir(exist_ok=True)
    (root / ADDONS_DIRNAME / "HONEYGAIN_POT.json").write_text(
        json.dumps(
            {
                "name": "HONEYGAIN_POT",
                "parent_id": "HONEYGAIN",
                "description": "pot",
                "compose_config": {"image": "ghcr.io/xterna/honeygain-pot:latest"},
            }
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# read_addons_dir
# ---------------------------------------------------------------------------


class TestReadAddonsDir:
    def test_missing_dir_returns_empty(self, tmp_path):
        assert read_addons_dir(tmp_path) == []

    def test_reads_valid_addons(self, tmp_path):
        _seed_catalog(tmp_path)
        addons = read_addons_dir(tmp_path)
        assert len(addons) == 1
        assert addons[0]["name"] == "HONEYGAIN_POT"
        assert addons[0]["parent_id"] == "HONEYGAIN"

    def test_skips_addon_missing_parent_id(self, tmp_path):
        (tmp_path / ADDONS_DIRNAME).mkdir()
        (tmp_path / ADDONS_DIRNAME / "BROKEN.json").write_text(
            json.dumps({"name": "BROKEN", "compose_config": {"image": "x"}}),
            encoding="utf-8",
        )
        assert read_addons_dir(tmp_path) == []


# ---------------------------------------------------------------------------
# LocalSource.load_addons
# ---------------------------------------------------------------------------


class TestLocalSourceAddons:
    def test_load_addons_when_enabled(self, tmp_path):
        # Layout: tmp_path / config / m4b-config.json, tmp_path / config / catalog/
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        _seed_catalog(config_dir / "catalog")
        config_path = config_dir / "m4b-config.json"
        config_path.write_text("{}", encoding="utf-8")

        src = LocalSource(path="catalog", name="builtin", enabled=True)
        addons = src.load_addons(config_path)
        assert len(addons) == 1
        assert addons[0]["name"] == "HONEYGAIN_POT"

    def test_load_addons_when_disabled(self, tmp_path):
        config_path = tmp_path / "m4b-config.json"
        config_path.write_text("{}", encoding="utf-8")
        src = LocalSource(path="catalog", name="builtin", enabled=False)
        assert src.load_addons(config_path) == []


# ---------------------------------------------------------------------------
# aggregate_from_sources
# ---------------------------------------------------------------------------


class TestAggregateIncludesAddons:
    def test_addons_exposed_at_top_level(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        _seed_catalog(config_dir / "catalog")
        config_path = config_dir / "m4b-config.json"
        config_path.write_text("{}", encoding="utf-8")

        envelope = {
            "app_config_version": 2.0,
            "catalog_sources": [
                {
                    "type": "local",
                    "name": "builtin",
                    "path": "catalog",
                    "enabled": True,
                }
            ],
            "categories": {
                "supported": {"active": True},
                "newcomers": {"active": False},
                "deprecated": {"active": False},
            },
        }
        result = aggregate_from_sources(envelope, config_path)
        assert "addons" in result
        assert len(result["addons"]) == 1
        assert result["addons"][0]["name"] == "HONEYGAIN_POT"

    def test_addons_deduped_first_wins(self, tmp_path):
        # Two sibling catalogs, both shipping the same addon.
        a = tmp_path / "a"
        b = tmp_path / "b"
        _seed_catalog(a)
        _seed_catalog(b)
        # Force source 'a' to win: different name.
        (a / ADDONS_DIRNAME / "HONEYGAIN_POT.json").write_text(
            json.dumps(
                {
                    "name": "HONEYGAIN_POT",
                    "parent_id": "HONEYGAIN",
                    "compose_config": {"image": "a-image"},
                }
            ),
            encoding="utf-8",
        )
        (b / ADDONS_DIRNAME / "HONEYGAIN_POT.json").write_text(
            json.dumps(
                {
                    "name": "HONEYGAIN_POT",
                    "parent_id": "HONEYGAIN",
                    "compose_config": {"image": "b-image"},
                }
            ),
            encoding="utf-8",
        )
        config_path = tmp_path / "m4b-config.json"
        config_path.write_text("{}", encoding="utf-8")
        envelope = {
            "app_config_version": 2.0,
            "catalog_sources": [
                {"type": "local", "name": "a", "path": "a", "enabled": True},
                {"type": "local", "name": "b", "path": "b", "enabled": True},
            ],
            "categories": {
                "supported": {"active": True},
                "newcomers": {"active": False},
                "deprecated": {"active": False},
            },
        }
        result = aggregate_from_sources(envelope, config_path)
        assert len(result["addons"]) == 1
        assert result["addons"][0]["compose_config"]["image"] == "a-image"


# ---------------------------------------------------------------------------
# get_addons_for lookup
# ---------------------------------------------------------------------------


class TestGetAddonsFor:
    def test_matches_by_parent_id_case_insensitive(self):
        config = {
            "addons": [
                {"name": "HONEYGAIN_POT", "parent_id": "HONEYGAIN"},
                {"name": "PACKETSHARE_POT", "parent_id": "PACKETSHARE"},
            ]
        }
        assert get_addons_for("honeygain", config) == [config["addons"][0]]
        assert get_addons_for("HONEYGAIN", config) == [config["addons"][0]]

    def test_returns_empty_when_no_match(self):
        config = {"addons": [{"name": "X", "parent_id": "HONEYGAIN"}]}
        assert get_addons_for("traffmonetizer", config) == []

    def test_returns_empty_when_no_addons_key(self):
        assert get_addons_for("honeygain", {}) == []


# ---------------------------------------------------------------------------
# remote_cache: manifest splitting and caching
# ---------------------------------------------------------------------------


class TestRemoteCacheAddons:
    def test_split_addons_aggregated_shape(self):
        payload = {
            "supported": {"entries": []},
            "addons": {
                "entries": [
                    {
                        "name": "HONEYGAIN_POT",
                        "parent_id": "HONEYGAIN",
                        "compose_config": {"image": "x"},
                    }
                ]
            },
        }
        assert len(split_addons_from_manifest(payload)) == 1

    def test_split_addons_flat_shape(self):
        payload = {
            "entries": [
                {
                    "name": "HONEYGAIN_POT",
                    "parent_id": "HONEYGAIN",
                    "category": "addons",
                    "compose_config": {"image": "x"},
                },
                {
                    "name": "OTHER",
                    "category": "supported",
                    "compose_config": {"image": "y"},
                },
            ]
        }
        out = split_addons_from_manifest(payload)
        assert len(out) == 1
        assert out[0]["name"] == "HONEYGAIN_POT"

    def test_split_addons_drops_missing_parent_id(self):
        payload = {
            "addons": [
                {"name": "BROKEN", "compose_config": {"image": "x"}},
            ]
        }
        assert split_addons_from_manifest(payload) == []

    def test_replace_entries_writes_addons_files(self, tmp_path):
        addon = {
            "name": "HONEYGAIN_POT",
            "parent_id": "HONEYGAIN",
            "compose_config": {"image": "x"},
        }
        written = replace_entries(tmp_path, {"supported": []}, [addon])
        assert written == 1
        path = tmp_path / ADDONS_DIRNAME / "HONEYGAIN_POT.json"
        assert path.is_file()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["parent_id"] == "HONEYGAIN"
