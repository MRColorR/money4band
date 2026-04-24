"""Tests for money4band.apps.remote_cache — phase-8.5 offline cache."""

from __future__ import annotations

import json
from pathlib import Path

from money4band.apps.remote_cache import (
    read_etag,
    replace_entries,
    split_manifest,
    touch_fetched_at,
    write_etag,
)


class TestEtag:
    def test_missing_returns_none(self, tmp_path: Path) -> None:
        assert read_etag(tmp_path) is None

    def test_round_trip(self, tmp_path: Path) -> None:
        write_etag(tmp_path, '"abc"')
        assert read_etag(tmp_path) == '"abc"'

    def test_whitespace_stripped(self, tmp_path: Path) -> None:
        (tmp_path / ".etag").write_text("  W/x  \n", encoding="utf-8")
        assert read_etag(tmp_path) == "W/x"


class TestTouchFetchedAt:
    def test_creates_timestamp(self, tmp_path: Path) -> None:
        touch_fetched_at(tmp_path)
        assert (tmp_path / ".fetched_at").is_file()


class TestReplaceEntries:
    def test_writes_bundles(self, tmp_path: Path) -> None:
        entries = {
            "supported": [{"name": "one", "compose_config": {"image": "x"}}],
            "newcomers": [],
            "deprecated": [],
        }
        n = replace_entries(tmp_path, entries)
        assert n == 1
        payload = json.loads(
            (tmp_path / "supported" / "ONE.json").read_text(encoding="utf-8")
        )
        assert payload["name"] == "one"

    def test_removes_stale_files(self, tmp_path: Path) -> None:
        (tmp_path / "supported").mkdir()
        (tmp_path / "supported" / "OLD.json").write_text("{}", encoding="utf-8")
        replace_entries(
            tmp_path,
            {"supported": [{"name": "new"}], "newcomers": [], "deprecated": []},
        )
        assert not (tmp_path / "supported" / "OLD.json").exists()
        assert (tmp_path / "supported" / "NEW.json").is_file()

    def test_preserves_dotfiles(self, tmp_path: Path) -> None:
        (tmp_path / ".etag").write_text('"abc"', encoding="utf-8")
        replace_entries(tmp_path, {"supported": [], "newcomers": [], "deprecated": []})
        assert (tmp_path / ".etag").is_file()

    def test_skips_entries_without_name(self, tmp_path: Path) -> None:
        n = replace_entries(
            tmp_path,
            {
                "supported": [{"no_name": True}, {"name": "ok"}],
                "newcomers": [],
                "deprecated": [],
            },
        )
        assert n == 1


class TestSplitManifest:
    def test_envelope_shape(self) -> None:
        out = split_manifest(
            {
                "supported": {"entries": [{"name": "a"}]},
                "newcomers": {"entries": [{"name": "b"}]},
            }
        )
        assert [e["name"] for e in out["supported"]] == ["a"]
        assert [e["name"] for e in out["newcomers"]] == ["b"]
        assert out["deprecated"] == []

    def test_bare_list_shape(self) -> None:
        out = split_manifest(
            {"supported": [{"name": "a"}], "deprecated": [{"name": "c"}]}
        )
        assert out["supported"][0]["name"] == "a"
        assert out["deprecated"][0]["name"] == "c"

    def test_flat_entries_shape(self) -> None:
        out = split_manifest(
            {
                "entries": [
                    {"name": "a", "category": "supported"},
                    {"name": "b", "category": "newcomers"},
                    {"name": "c", "category": "invalid"},  # dropped
                    {"category": "supported"},  # no name — dropped
                ]
            }
        )
        assert [e["name"] for e in out["supported"]] == ["a"]
        assert [e["name"] for e in out["newcomers"]] == ["b"]

    def test_non_dict_payload_returns_empty(self) -> None:
        out = split_manifest("not a dict")  # type: ignore[arg-type]
        assert out == {"supported": [], "newcomers": [], "deprecated": []}
