"""Tests for self-update functionality in updater.py."""

import json
import os
import subprocess
import time
from unittest.mock import MagicMock, patch

import pytest

from money4band.updater import (
    Version,
    _apply_git_update,
    _backup_preserved_files,
    _get_binary_asset_name,
    _notify_update_available,
    _read_cache,
    _restore_preserved_files,
    _write_cache,
    apply_update,
    check_for_update,
    check_update_available,
    get_latest_releases,
    is_git_install,
    show_update_banner,
)


class TestUpdateCache:
    def test_write_and_read_cache(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "m4b_update_cache.json"
        monkeypatch.setattr("money4band.updater._cache_path", lambda: cache_file)

        _write_cache("5.1.0", "5.0.0")
        result = _read_cache()
        assert result is not None
        assert result["latest"] == "5.1.0"
        assert result["current"] == "5.0.0"

    def test_expired_cache_returns_none(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "m4b_update_cache.json"
        monkeypatch.setattr("money4band.updater._cache_path", lambda: cache_file)

        payload = {"ts": time.time() - 1000, "latest": "5.1.0", "current": "5.0.0"}
        cache_file.write_text(json.dumps(payload))

        assert _read_cache() is None

    def test_missing_cache_returns_none(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr("money4band.updater._cache_path", lambda: cache_file)

        assert _read_cache() is None

    def test_corrupt_cache_returns_none(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "m4b_update_cache.json"
        cache_file.write_text("{bad json")
        monkeypatch.setattr("money4band.updater._cache_path", lambda: cache_file)

        assert _read_cache() is None


class TestCheckForUpdate:
    def test_returns_version_when_update_available(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "cache.json"
        monkeypatch.setattr("money4band.updater._cache_path", lambda: cache_file)

        fake_release = [
            {
                "version": Version(5, 1, 0),
                "name": "v5.1.0",
                "url": "https://example.com",
                "published_at": "2026-01-01",
            }
        ]
        monkeypatch.setattr(
            "money4band.updater.get_latest_releases", lambda count=1: fake_release
        )

        config = {"project": {"project_version": "5.0.0"}}
        result = check_for_update(config)
        assert result == "5.1.0"

    def test_returns_none_when_up_to_date(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "cache.json"
        monkeypatch.setattr("money4band.updater._cache_path", lambda: cache_file)

        fake_release = [
            {
                "version": Version(5, 0, 0),
                "name": "v5.0.0",
                "url": "https://example.com",
                "published_at": "2026-01-01",
            }
        ]
        monkeypatch.setattr(
            "money4band.updater.get_latest_releases", lambda count=1: fake_release
        )

        config = {"project": {"project_version": "5.0.0"}}
        assert check_for_update(config) is None

    def test_uses_cache_when_fresh(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "cache.json"
        monkeypatch.setattr("money4band.updater._cache_path", lambda: cache_file)

        payload = {"ts": time.time(), "latest": "5.2.0", "current": "5.0.0"}
        cache_file.write_text(json.dumps(payload))

        # Should NOT call get_latest_releases
        monkeypatch.setattr(
            "money4band.updater.get_latest_releases",
            lambda count=1: (_ for _ in ()).throw(
                AssertionError("should not be called")
            ),
        )

        config = {"project": {"project_version": "5.0.0"}}
        assert check_for_update(config) == "5.2.0"

    def test_returns_none_on_api_error(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "cache.json"
        monkeypatch.setattr("money4band.updater._cache_path", lambda: cache_file)

        def fail(*a, **kw):
            raise RuntimeError("network error")

        monkeypatch.setattr("money4band.updater.get_latest_releases", fail)

        config = {"project": {"project_version": "5.0.0"}}
        assert check_for_update(config) is None


class TestIsGitInstall:
    def test_true_when_git_dir_exists(self, tmp_path, monkeypatch):
        (tmp_path / ".git").mkdir()
        monkeypatch.setattr("money4band.updater.parent_dir", str(tmp_path))
        assert is_git_install() is True

    def test_false_when_no_git_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("money4band.updater.parent_dir", str(tmp_path))
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

    def test_m4b_config_is_overwritten_on_update(self, tmp_path):
        """m4b-config.json is release-owned: update replaces it wholesale.

        User-mutable state (catalog source toggles, category flags,
        custom remote sources) lives in user-config.json under
        ``catalog_overrides`` and is preserved independently.
        """
        import json

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        m4b = config_dir / "m4b-config.json"
        user = config_dir / "user-config.json"

        # OLD install: user has customised m4b-config in-place (legacy behaviour
        # pre-overrides) and has written overrides into user-config.json.
        old_m4b = {
            "project": {"project_version": "5.0.0"},
            "catalog": {
                "app_config_version": 2.0,
                "catalog_sources": [
                    {"type": "local", "name": "builtin", "path": "catalog"},
                ],
            },
        }
        old_user = {
            "device_name": "mybox",
            "catalog_overrides": {
                "sources": {"builtin": {"enabled": False}},
                "categories": {"supported": {"active": False}},
            },
        }
        m4b.write_text(json.dumps(old_m4b))
        user.write_text(json.dumps(old_user))

        saved = _backup_preserved_files(str(tmp_path))

        # NEW shipped m4b-config written by the installer.
        new_m4b = {
            "project": {"project_version": "5.1.0"},
            "new_shipped_key": "hello",
            "catalog": {
                "app_config_version": 2.0,
                "catalog_sources": [
                    {"type": "local", "name": "builtin", "path": "catalog"},
                    {"type": "remote", "name": "community", "url": "https://x/m.json"},
                ],
            },
        }
        m4b.write_text(json.dumps(new_m4b))

        _restore_preserved_files(str(tmp_path), saved)

        # m4b-config.json reflects the newly shipped defaults verbatim.
        result_m4b = json.loads(m4b.read_text())
        assert result_m4b == new_m4b

        # user-config.json was preserved byte-for-byte.
        result_user = json.loads(user.read_text())
        assert result_user == old_user


class TestGetBinaryAssetName:
    @patch("money4band.updater.platform.system", return_value="Windows")
    def test_windows(self, _):
        assert _get_binary_asset_name() == "money4band-windows-amd64.exe"

    @patch("money4band.updater.platform.machine", return_value="x86_64")
    @patch("money4band.updater.platform.system", return_value="Linux")
    def test_linux_amd64(self, *_):
        assert _get_binary_asset_name() == "money4band-linux-amd64"

    @patch("money4band.updater.platform.machine", return_value="aarch64")
    @patch("money4band.updater.platform.system", return_value="Linux")
    def test_linux_arm64(self, *_):
        assert _get_binary_asset_name() == "money4band-linux-arm64"

    @patch("money4band.updater.platform.machine", return_value="arm64")
    @patch("money4band.updater.platform.system", return_value="Darwin")
    def test_macos_arm64(self, *_):
        assert _get_binary_asset_name() == "money4band-darwin-arm64"


class TestApplyUpdate:
    def test_git_update_calls_fetch_and_checkout(self, monkeypatch):
        monkeypatch.setattr("money4band.updater.is_git_install", lambda: True)

        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr("money4band.updater.subprocess.run", fake_run)
        monkeypatch.setattr("money4band.updater._backup_preserved_files", lambda d: {})
        monkeypatch.setattr(
            "money4band.updater._restore_preserved_files", lambda d, s: None
        )

        assert apply_update("5.1.0") is True
        assert len(calls) == 2
        assert "fetch" in calls[0][1]
        assert "v5.1.0" in calls[1][-1]

    def test_unsupported_install_returns_false(self, monkeypatch, capsys):
        monkeypatch.setattr("money4band.updater.is_git_install", lambda: False)
        monkeypatch.setattr("money4band.updater.sys", MagicMock(frozen=False))
        # sys.frozen = False and NOT git -> unsupported
        result = apply_update("5.1.0")

        # Unsupported install should print guidance and return False.
        captured = capsys.readouterr()
        assert result is False
        assert "not supported" in captured.out.lower()


class TestGetLatestReleases:
    def test_returns_sorted_releases(self, monkeypatch):
        api_response = [
            {
                "prerelease": False,
                "draft": False,
                "name": "v4.9.0",
                "tag_name": "v4.9.0",
                "html_url": "https://example.com/v4.9.0",
                "published_at": "2025-01-01T00:00:00Z",
            },
            {
                "prerelease": False,
                "draft": False,
                "name": "v5.0.0",
                "tag_name": "v5.0.0",
                "html_url": "https://example.com/v5.0.0",
                "published_at": "2025-06-01T00:00:00Z",
            },
        ]
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_response
        mock_client.get.return_value = mock_resp
        monkeypatch.setattr("money4band.updater.get_client", lambda: mock_client)

        releases = get_latest_releases(count=5)
        assert len(releases) == 2
        assert releases[0]["version"] > releases[1]["version"]

    def test_skips_prerelease_and_draft(self, monkeypatch):
        api_response = [
            {
                "prerelease": True,
                "draft": False,
                "name": "v6.0.0-beta",
                "tag_name": "v6.0.0-beta",
                "html_url": "https://example.com",
                "published_at": "2025-01-01T00:00:00Z",
            },
            {
                "prerelease": False,
                "draft": True,
                "name": "v5.5.0",
                "tag_name": "v5.5.0",
                "html_url": "https://example.com",
                "published_at": "2025-01-01T00:00:00Z",
            },
        ]
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_response
        mock_client.get.return_value = mock_resp
        monkeypatch.setattr("money4band.updater.get_client", lambda: mock_client)

        assert get_latest_releases() == []

    def test_connection_error_raises_runtime(self, monkeypatch):
        import httpx

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("DNS fail")
        monkeypatch.setattr("money4band.updater.get_client", lambda: mock_client)

        with pytest.raises(RuntimeError, match="Cannot reach GitHub"):
            get_latest_releases()

    def test_timeout_raises_runtime(self, monkeypatch):
        import httpx

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.TimeoutException("slow")
        monkeypatch.setattr("money4band.updater.get_client", lambda: mock_client)

        with pytest.raises(RuntimeError, match="timed out"):
            get_latest_releases()


class TestCheckUpdateAvailable:
    def test_prints_new_version(self, monkeypatch, capsys):
        fake_release = [
            {
                "version": Version(5, 2, 0),
                "name": "v5.2.0",
                "url": "https://example.com",
                "published_at": "2026-01-01",
            }
        ]
        monkeypatch.setattr(
            "money4band.updater.get_latest_releases", lambda count=5: fake_release
        )
        config = {"project": {"project_version": "5.0.0"}}
        check_update_available(config)
        captured = capsys.readouterr()
        assert "5.2.0" in captured.out

    def test_no_releases_prints_no_output(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "money4band.updater.get_latest_releases", lambda count=5: []
        )
        config = {"project": {"project_version": "5.0.0"}}
        check_update_available(config)
        captured = capsys.readouterr()
        assert "No releases" in captured.out

    def test_exception_prints_error(self, monkeypatch, capsys):
        def boom(count=5):
            raise RuntimeError("network down")

        monkeypatch.setattr("money4band.updater.get_latest_releases", boom)
        config = {"project": {"project_version": "5.0.0"}}
        check_update_available(config)
        captured = capsys.readouterr()
        assert "Error" in captured.out or "error" in captured.out


class TestApplyGitUpdate:
    def test_git_fetch_failure_returns_false(self, monkeypatch):
        monkeypatch.setattr("money4band.updater._backup_preserved_files", lambda d: {})

        def fail_run(cmd, **kw):
            raise subprocess.CalledProcessError(1, cmd, stderr="fetch error")

        monkeypatch.setattr("money4band.updater.subprocess.run", fail_run)
        assert _apply_git_update("5.1.0") is False


class TestVersionComparisons:
    """All comparison operators, repr, and parse-from-string for Version."""

    def test_from_string_with_prefix(self):
        v = Version.from_string("version 1.2.3")
        assert v == Version(1, 2, 3)

    def test_from_string_invalid(self):
        with pytest.raises(ValueError, match="Invalid version"):
            Version.from_string("not-a-version")

    def test_ne(self):
        assert Version(1, 0, 0) != Version(2, 0, 0)

    def test_le(self):
        assert Version(1, 0, 0) <= Version(1, 0, 0)
        assert Version(1, 0, 0) <= Version(2, 0, 0)

    def test_ge(self):
        assert Version(2, 0, 0) >= Version(1, 0, 0)
        assert Version(1, 0, 0) >= Version(1, 0, 0)

    def test_gt_minor(self):
        assert Version(1, 2, 0) > Version(1, 1, 0)

    def test_lt_minor(self):
        assert Version(1, 1, 0) < Version(1, 2, 0)

    def test_repr(self):
        assert repr(Version(3, 4, 5)) == "3.4.5"

    def test_not_equal_to_non_version(self):
        assert Version(1, 0, 0) != "1.0.0"

    def test_lt_not_implemented_for_non_version(self):
        assert Version(1, 0, 0).__lt__("1.0.0") is NotImplemented

    def test_gt_not_implemented_for_non_version(self):
        assert Version(1, 0, 0).__gt__("1.0.0") is NotImplemented


# ---------------------------------------------------------------------------
# _apply_binary_update — covers lines 376-419
# ---------------------------------------------------------------------------


class TestApplyBinaryUpdate:
    def test_successful_download_replaces_binary(self, monkeypatch, tmp_path):
        """Successful download should write the new binary and rename the old one."""
        from money4band.updater import _apply_binary_update

        # Create a fake "current" executable
        current_exe = tmp_path / "m4b.exe"
        current_exe.write_bytes(b"old-binary")

        monkeypatch.setattr("money4band.updater.sys.executable", str(current_exe))
        monkeypatch.setattr(
            "money4band.updater._get_binary_asset_name", lambda: "m4b.exe"
        )
        monkeypatch.setattr("money4band.updater.platform.system", lambda: "Windows")

        # Mock the HTTP response with chunked content
        mock_resp = MagicMock()
        mock_resp.iter_bytes.return_value = [b"new-binary-data"]
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        monkeypatch.setattr("money4band.updater.get_client", lambda: mock_client)

        result = _apply_binary_update("5.1.0")
        assert result is True
        # The new binary should be at the original path
        assert current_exe.read_bytes() == b"new-binary-data"
        # Backup should exist
        assert (tmp_path / "m4b.exe.bak").exists()

    def test_download_failure_returns_false(self, monkeypatch):
        """HTTP error during download should return False."""
        import httpx

        from money4band.updater import _apply_binary_update

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.HTTPError("network error")
        monkeypatch.setattr("money4band.updater.get_client", lambda: mock_client)
        monkeypatch.setattr("money4band.updater._get_binary_asset_name", lambda: "m4b")

        assert _apply_binary_update("5.1.0") is False

    def test_os_error_during_rename_rolls_back(self, monkeypatch, tmp_path):
        """OSError during file replacement should attempt rollback."""
        from money4band.updater import _apply_binary_update

        current_exe = tmp_path / "m4b.exe"
        current_exe.write_bytes(b"old")

        monkeypatch.setattr("money4band.updater.sys.executable", str(current_exe))
        monkeypatch.setattr(
            "money4band.updater._get_binary_asset_name", lambda: "m4b.exe"
        )
        monkeypatch.setattr("money4band.updater.platform.system", lambda: "Windows")

        mock_resp = MagicMock()
        mock_resp.iter_bytes.return_value = [b"new"]
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        monkeypatch.setattr("money4band.updater.get_client", lambda: mock_client)

        # Make the second rename fail (new → current)
        original_rename = os.rename
        call_count = 0

        def patched_rename(src, dst):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # second rename: tmp → current
                raise OSError("permission denied")
            return original_rename(src, dst)

        monkeypatch.setattr("os.rename", patched_rename)

        result = _apply_binary_update("5.1.0")
        assert result is False
        # Original binary should be restored from backup
        assert current_exe.exists()


# ---------------------------------------------------------------------------
# show_update_banner — covers lines 275-282
# ---------------------------------------------------------------------------


class TestShowUpdateBanner:
    def test_prints_banner_when_update_available(self, monkeypatch, capsys):
        monkeypatch.setattr("money4band.updater.check_for_update", lambda _: "6.0.0")
        monkeypatch.setattr(
            "money4band.updater._notify_update_available", lambda v: None
        )

        show_update_banner({"project": {"project_version": "5.0.0"}})
        captured = capsys.readouterr()
        assert "6.0.0" in captured.out
        assert "available" in captured.out

    def test_no_banner_when_up_to_date(self, monkeypatch, capsys):
        monkeypatch.setattr("money4band.updater.check_for_update", lambda _: None)

        show_update_banner({"project": {"project_version": "5.0.0"}})
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_notify_called_with_version(self, monkeypatch):
        """_notify_update_available is called with the new version string."""
        notified = []
        monkeypatch.setattr("money4band.updater.check_for_update", lambda _: "7.0.0")
        monkeypatch.setattr(
            "money4band.updater._notify_update_available", notified.append
        )

        show_update_banner({})
        assert notified == ["7.0.0"]


# ---------------------------------------------------------------------------
# _notify_update_available — covers lines 286-294
# ---------------------------------------------------------------------------


class TestNotifyUpdateAvailable:
    def test_calls_notify_when_config_exists(self, monkeypatch, tmp_path):
        import json as _json

        cfg_path = tmp_path / "config" / "user-config.json"
        cfg_path.parent.mkdir()
        cfg_path.write_text(_json.dumps({"notifications": {"enabled": True}}))

        monkeypatch.setattr("money4band.updater.parent_dir", str(tmp_path))

        notified = []
        monkeypatch.setattr(
            "money4band.notifier.notify",
            lambda cfg, event, msg: notified.append(event),
        )
        _notify_update_available("5.2.0")
        assert notified == ["update_available"]

    def test_silently_skips_when_no_config(self, monkeypatch, tmp_path):
        """Missing user-config.json should not raise."""
        monkeypatch.setattr("money4band.updater.parent_dir", str(tmp_path))
        _notify_update_available("5.2.0")  # should not raise

    def test_import_error_suppressed(self, monkeypatch, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "user-config.json").write_text('{"notifications": {}}')
        monkeypatch.setattr("money4band.updater.parent_dir", str(tmp_path))
        _notify_update_available("5.1.0")
