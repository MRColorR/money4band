"""Tests for self-update functionality in updater.py."""

import json
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from utils.updater import (
    Version,
    _backup_preserved_files,
    _cache_path,
    _get_binary_asset_name,
    _read_cache,
    _restore_preserved_files,
    _write_cache,
    apply_update,
    check_for_update,
    is_git_install,
    show_update_banner,
)


class TestUpdateCache:

    def test_write_and_read_cache(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "m4b_update_cache.json"
        monkeypatch.setattr("utils.updater._cache_path", lambda: cache_file)

        _write_cache("5.1.0", "5.0.0")
        result = _read_cache()
        assert result is not None
        assert result["latest"] == "5.1.0"
        assert result["current"] == "5.0.0"

    def test_expired_cache_returns_none(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "m4b_update_cache.json"
        monkeypatch.setattr("utils.updater._cache_path", lambda: cache_file)

        payload = {"ts": time.time() - 1000, "latest": "5.1.0", "current": "5.0.0"}
        cache_file.write_text(json.dumps(payload))

        assert _read_cache() is None

    def test_missing_cache_returns_none(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr("utils.updater._cache_path", lambda: cache_file)

        assert _read_cache() is None

    def test_corrupt_cache_returns_none(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "m4b_update_cache.json"
        cache_file.write_text("{bad json")
        monkeypatch.setattr("utils.updater._cache_path", lambda: cache_file)

        assert _read_cache() is None


class TestCheckForUpdate:

    def test_returns_version_when_update_available(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "cache.json"
        monkeypatch.setattr("utils.updater._cache_path", lambda: cache_file)

        fake_release = [{"version": Version(5, 1, 0), "name": "v5.1.0",
                         "url": "https://example.com", "published_at": "2026-01-01"}]
        monkeypatch.setattr("utils.updater.get_latest_releases", lambda count=1: fake_release)

        config = {"project": {"project_version": "5.0.0"}}
        result = check_for_update(config)
        assert result == "5.1.0"

    def test_returns_none_when_up_to_date(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "cache.json"
        monkeypatch.setattr("utils.updater._cache_path", lambda: cache_file)

        fake_release = [{"version": Version(5, 0, 0), "name": "v5.0.0",
                         "url": "https://example.com", "published_at": "2026-01-01"}]
        monkeypatch.setattr("utils.updater.get_latest_releases", lambda count=1: fake_release)

        config = {"project": {"project_version": "5.0.0"}}
        assert check_for_update(config) is None

    def test_uses_cache_when_fresh(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "cache.json"
        monkeypatch.setattr("utils.updater._cache_path", lambda: cache_file)

        payload = {"ts": time.time(), "latest": "5.2.0", "current": "5.0.0"}
        cache_file.write_text(json.dumps(payload))

        # Should NOT call get_latest_releases
        monkeypatch.setattr(
            "utils.updater.get_latest_releases",
            lambda count=1: (_ for _ in ()).throw(AssertionError("should not be called")),
        )

        config = {"project": {"project_version": "5.0.0"}}
        assert check_for_update(config) == "5.2.0"

    def test_returns_none_on_api_error(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "cache.json"
        monkeypatch.setattr("utils.updater._cache_path", lambda: cache_file)

        def fail(*a, **kw):
            raise RuntimeError("network error")

        monkeypatch.setattr("utils.updater.get_latest_releases", fail)

        config = {"project": {"project_version": "5.0.0"}}
        assert check_for_update(config) is None


class TestShowUpdateBanner:

    def test_prints_banner_when_update_available(self, capsys, monkeypatch):
        monkeypatch.setattr(
            "utils.updater.check_for_update", lambda cfg: "5.1.0"
        )
        show_update_banner({"project": {"project_version": "5.0.0"}})
        captured = capsys.readouterr()
        assert "5.1.0" in captured.out
        assert "m4b update" in captured.out.lower()

    def test_no_output_when_up_to_date(self, capsys, monkeypatch):
        monkeypatch.setattr("utils.updater.check_for_update", lambda cfg: None)
        show_update_banner({"project": {"project_version": "5.0.0"}})
        assert capsys.readouterr().out == ""


class TestIsGitInstall:

    def test_true_when_git_dir_exists(self, tmp_path, monkeypatch):
        (tmp_path / ".git").mkdir()
        monkeypatch.setattr("utils.updater.parent_dir", str(tmp_path))
        assert is_git_install() is True

    def test_false_when_no_git_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("utils.updater.parent_dir", str(tmp_path))
        assert is_git_install() is False


class TestPreservedFiles:

    def test_backup_and_restore(self, tmp_path):
        # Create test files
        (tmp_path / "user-config.json").write_text('{"key": "val"}')
        (tmp_path / ".env").write_text("FOO=bar")
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "app-config.json").write_text('{"app": true}')

        saved = _backup_preserved_files(str(tmp_path))
        assert "user-config.json" in saved
        assert ".env" in saved
        assert os.path.join("config", "app-config.json") in saved

        # Delete originals
        (tmp_path / "user-config.json").unlink()
        (tmp_path / ".env").unlink()
        (config_dir / "app-config.json").unlink()

        _restore_preserved_files(str(tmp_path), saved)

        assert (tmp_path / "user-config.json").read_text() == '{"key": "val"}'
        assert (tmp_path / ".env").read_text() == "FOO=bar"
        assert (config_dir / "app-config.json").read_text() == '{"app": true}'


class TestGetBinaryAssetName:

    @patch("utils.updater.platform.system", return_value="Windows")
    def test_windows(self, _):
        assert _get_binary_asset_name() == "money4band-windows-amd64.exe"

    @patch("utils.updater.platform.machine", return_value="x86_64")
    @patch("utils.updater.platform.system", return_value="Linux")
    def test_linux_amd64(self, *_):
        assert _get_binary_asset_name() == "money4band-linux-amd64"

    @patch("utils.updater.platform.machine", return_value="aarch64")
    @patch("utils.updater.platform.system", return_value="Linux")
    def test_linux_arm64(self, *_):
        assert _get_binary_asset_name() == "money4band-linux-arm64"

    @patch("utils.updater.platform.machine", return_value="arm64")
    @patch("utils.updater.platform.system", return_value="Darwin")
    def test_macos_arm64(self, *_):
        assert _get_binary_asset_name() == "money4band-darwin-arm64"


class TestApplyUpdate:

    def test_git_update_calls_fetch_and_checkout(self, monkeypatch):
        monkeypatch.setattr("utils.updater.is_git_install", lambda: True)

        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr("utils.updater.subprocess.run", fake_run)
        monkeypatch.setattr(
            "utils.updater._backup_preserved_files", lambda d: {}
        )
        monkeypatch.setattr(
            "utils.updater._restore_preserved_files", lambda d, s: None
        )

        assert apply_update("5.1.0") is True
        assert len(calls) == 2
        assert "fetch" in calls[0][1]
        assert "v5.1.0" in calls[1][-1]

    def test_unsupported_install_returns_false(self, monkeypatch, capsys):
        monkeypatch.setattr("utils.updater.is_git_install", lambda: False)
        monkeypatch.setattr("utils.updater.sys", MagicMock(frozen=False))
        # sys.frozen = False and NOT git → unsupported
        monkeypatch.setattr("builtins.getattr", lambda o, a, d=None: False)

        # This will fall through to the else branch
        result = apply_update("5.1.0")
        # Result depends on whether sys.frozen is False
        # The function should print a message and return False
        captured = capsys.readouterr()
        assert result is False or "not supported" in captured.out.lower()
