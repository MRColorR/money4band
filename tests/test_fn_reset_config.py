"""Tests for money4band.fn_reset_config — config reset logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from money4band.fn_reset_config import main, reset_config


class TestResetConfig:
    def test_copies_source_to_dest(self, tmp_path: Path) -> None:
        src = tmp_path / "template.json"
        src.write_text(json.dumps({"clean": True}))
        dest = tmp_path / "config" / "user-config.json"
        reset_config(str(src), str(dest))
        assert json.loads(dest.read_text()) == {"clean": True}

    def test_creates_dest_dir(self, tmp_path: Path) -> None:
        src = tmp_path / "template.json"
        src.write_text("{}")
        dest = tmp_path / "deep" / "nested" / "config.json"
        reset_config(str(src), str(dest))
        assert dest.exists()

    def test_raises_on_missing_source(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            reset_config(str(tmp_path / "nope.json"), str(tmp_path / "out.json"))

    def test_overwrites_existing_dest(self, tmp_path: Path) -> None:
        src = tmp_path / "template.json"
        src.write_text(json.dumps({"version": 2}))
        dest = tmp_path / "user-config.json"
        dest.write_text(json.dumps({"version": 1, "custom": True}))
        reset_config(str(src), str(dest))
        assert json.loads(dest.read_text()) == {"version": 2}


class TestMain:
    def test_delegates_to_reset_config(self, tmp_path: Path) -> None:
        src = tmp_path / "template.json"
        src.write_text(json.dumps({"reset": True}))
        dest = tmp_path / "dest.json"
        main("a.json", "m.json", "u.json", src_path=str(src), dest_path=str(dest))
        assert json.loads(dest.read_text()) == {"reset": True}
