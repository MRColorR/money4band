"""Tests for utils.profiles — configuration profiles."""

from __future__ import annotations

import json
import os

from money4band.core.profiles import (
    create_profile,
    delete_profile,
    display_profiles,
    list_profiles,
    switch_profile,
)


class TestListProfiles:
    def test_empty(self, tmp_path):
        assert list_profiles(str(tmp_path)) == []

    def test_no_profiles_dir(self, tmp_path):
        assert list_profiles(str(tmp_path / "nonexistent")) == []

    def test_lists_directories(self, tmp_path):
        pdir = tmp_path / "profiles"
        (pdir / "home").mkdir(parents=True)
        (pdir / "vps").mkdir()
        (pdir / "notadir.txt").write_text("x")  # should be ignored
        assert list_profiles(str(tmp_path)) == ["home", "vps"]


class TestCreateProfile:
    def test_creates_profile(self, tmp_path):
        config_dir = str(tmp_path / "config")
        base_dir = str(tmp_path)
        user_cfg = tmp_path / "config" / "user-config.json"
        os.makedirs(str(tmp_path / "config"), exist_ok=True)
        user_cfg.write_text(json.dumps({"device": "test"}))
        (tmp_path / ".env").write_text("DEVICE_NAME=test")

        path = create_profile("home", config_dir, base_dir, str(user_cfg))

        assert os.path.isdir(path)
        assert os.path.isfile(os.path.join(path, "user-config.json"))
        assert os.path.isfile(os.path.join(path, ".env"))

    def test_creates_without_env(self, tmp_path):
        config_dir = str(tmp_path / "config")
        user_cfg = tmp_path / "config" / "user-config.json"
        os.makedirs(str(tmp_path / "config"), exist_ok=True)
        user_cfg.write_text("{}")

        path = create_profile("minimal", config_dir, str(tmp_path), str(user_cfg))
        assert os.path.isfile(os.path.join(path, "user-config.json"))
        assert not os.path.isfile(os.path.join(path, ".env"))


class TestSwitchProfile:
    def test_switch_restores_files(self, tmp_path):
        config_dir = str(tmp_path / "config")
        base_dir = str(tmp_path)

        # Create a profile
        profile_dir = os.path.join(config_dir, "profiles", "vps")
        os.makedirs(profile_dir)
        with open(os.path.join(profile_dir, "user-config.json"), "w") as f:
            json.dump({"profile": "vps"}, f)
        with open(os.path.join(profile_dir, ".env"), "w") as f:
            f.write("DEVICE_NAME=vps-node")

        # Create active config
        user_cfg_path = os.path.join(config_dir, "user-config.json")
        os.makedirs(config_dir, exist_ok=True)
        with open(user_cfg_path, "w") as f:
            json.dump({"profile": "old"}, f)

        result = switch_profile("vps", config_dir, base_dir, user_cfg_path)
        assert result is True

        with open(user_cfg_path) as f:
            assert json.load(f)["profile"] == "vps"
        with open(os.path.join(base_dir, ".env")) as f:
            assert "vps-node" in f.read()

    def test_switch_nonexistent(self, tmp_path):
        assert switch_profile("nope", str(tmp_path), str(tmp_path), "x") is False


class TestDeleteProfile:
    def test_delete_existing(self, tmp_path):
        profile_dir = tmp_path / "profiles" / "old"
        profile_dir.mkdir(parents=True)
        (profile_dir / "user-config.json").write_text("{}")

        assert delete_profile("old", str(tmp_path)) is True
        assert not profile_dir.exists()

    def test_delete_nonexistent(self, tmp_path):
        assert delete_profile("nope", str(tmp_path)) is False


class TestDisplayProfiles:
    def test_no_profiles(self, tmp_path, capsys):
        display_profiles(str(tmp_path))
        out = capsys.readouterr().out
        assert "No saved profiles" in out

    def test_shows_profiles(self, tmp_path, capsys):
        pdir = tmp_path / "profiles" / "home"
        pdir.mkdir(parents=True)
        (pdir / "user-config.json").write_text("{}")
        (pdir / ".env").write_text("X=1")

        display_profiles(str(tmp_path))
        out = capsys.readouterr().out
        assert "home" in out
        assert "user-config.json" in out
        assert ".env" in out
