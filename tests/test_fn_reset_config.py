"""Tests for money4band.core.reset - config reset logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from money4band.core.reset import main, reset_config


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


class TestResetSeedsFromCatalog:
    """Verify reset applies user_config_template defaults from the catalog.

    The catalog envelope is folded into ``m4b-config.json`` and the
    per-app bundles live under ``config/catalog/<category>/``.
    """

    def test_seeds_app_slices_from_catalog_templates(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Template without per-app block - per-app defaults come from catalog.
        template = {
            "user": {"Nickname": ""},
            "apps": {},
            "settings": {"setup_completed": False},
        }
        src = tmp_path / "template" / "user-config.json"
        src.parent.mkdir()
        src.write_text(json.dumps(template))

        # Folded envelope - m4b-config.json carries the catalog key;
        # per-file bundles live under config/catalog/.
        m4b_config = {
            "project": {"project_version": "5.0.0"},
            "catalog": {
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
            },
        }
        (config_dir / "m4b-config.json").write_text(json.dumps(m4b_config))
        (config_dir / "catalog" / "supported").mkdir(parents=True)
        (config_dir / "catalog" / "supported" / "HONEYGAIN.json").write_text(
            json.dumps(
                {
                    "name": "HONEYGAIN",
                    "compose_config": {"image": "honeygain/honeygain:latest"},
                    "user_config_template": {
                        "enabled": False,
                        "email": "yourHONEYGAINMail",
                        "password": "yourHONEYGAINPw",
                        "service_enabled": False,
                    },
                }
            )
        )

        dest = config_dir / "user-config.json"
        reset_config(str(src), str(dest))

        data = json.loads(dest.read_text())
        assert data["apps"]["honeygain"] == {
            "enabled": False,
            "email": "yourHONEYGAINMail",
            "password": "yourHONEYGAINPw",
            "service_enabled": False,
        }

    def test_reset_silently_skips_seed_when_m4b_config_missing(
        self, tmp_path: Path
    ) -> None:
        """Odd filesystem layouts must not break reset."""
        src = tmp_path / "template.json"
        src.write_text(json.dumps({"apps": {}, "settings": {}}))
        dest = tmp_path / "out" / "user-config.json"
        reset_config(str(src), str(dest))
        # No m4b-config.json next to dest -> apps stays empty, no crash.
        assert json.loads(dest.read_text())["apps"] == {}
