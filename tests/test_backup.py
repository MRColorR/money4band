"""Tests for config backup and restore utilities (Phase 2.3)."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from utils.backup import (
    BACKUP_DIR,
    BackupInfo,
    cleanup_backups,
    create_backup,
    list_backups,
    restore_backup,
)


@pytest.fixture(autouse=True)
def _isolated_backup_dir(monkeypatch, tmp_path):
    """Redirect BACKUP_DIR to a temp location for every test."""
    fake_dir = tmp_path / "backups"
    fake_dir.mkdir()
    monkeypatch.setattr("utils.backup.BACKUP_DIR", fake_dir)
    return fake_dir


@pytest.fixture()
def sample_config(tmp_path):
    """Create a small JSON config file and return its path."""
    cfg = tmp_path / "user-config.json"
    cfg.write_text(json.dumps({"user": {"email": "test@example.com"}}))
    return str(cfg)


# ---------------------------------------------------------------------------
# create_backup
# ---------------------------------------------------------------------------

class TestCreateBackup:

    def test_creates_file_in_backup_dir(self, sample_config, _isolated_backup_dir):
        path = create_backup(sample_config)
        assert path.exists()
        assert path.parent == _isolated_backup_dir
        assert path.suffix == ".bak"

    def test_backup_content_matches_source(self, sample_config):
        path = create_backup(sample_config)
        assert path.read_text() == Path(sample_config).read_text()

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            create_backup(str(tmp_path / "nonexistent.json"))

    def test_multiple_backups_have_unique_names(self, sample_config):
        p1 = create_backup(sample_config)
        time.sleep(1.1)  # ensure different second in timestamp
        p2 = create_backup(sample_config)
        assert p1 != p2


# ---------------------------------------------------------------------------
# list_backups
# ---------------------------------------------------------------------------

class TestListBackups:

    def test_empty_when_no_backups(self):
        assert list_backups() == []

    def test_returns_backups_newest_first(self, sample_config):
        p1 = create_backup(sample_config)
        time.sleep(1.1)
        p2 = create_backup(sample_config)
        backups = list_backups()
        assert len(backups) == 2
        assert backups[0].path == p2
        assert backups[1].path == p1

    def test_ignores_non_matching_files(self, _isolated_backup_dir):
        (_isolated_backup_dir / "random.txt").write_text("junk")
        assert list_backups() == []


# ---------------------------------------------------------------------------
# restore_backup
# ---------------------------------------------------------------------------

class TestRestoreBackup:

    def test_restore_overwrites_config(self, sample_config, tmp_path):
        backup_path = create_backup(sample_config)
        # Modify the live config
        live = Path(sample_config)
        live.write_text(json.dumps({"modified": True}))
        # Restore
        restore_backup(backup_path, sample_config)
        assert json.loads(live.read_text()) == {"user": {"email": "test@example.com"}}

    def test_raises_on_missing_backup(self, sample_config, tmp_path):
        with pytest.raises(FileNotFoundError):
            restore_backup(tmp_path / "ghost.bak", sample_config)


# ---------------------------------------------------------------------------
# cleanup_backups
# ---------------------------------------------------------------------------

class TestCleanupBackups:

    def test_keeps_specified_count(self, sample_config):
        for _ in range(4):
            create_backup(sample_config)
            time.sleep(1.1)
        assert len(list_backups()) == 4

        deleted = cleanup_backups(keep=2)
        assert deleted == 2
        assert len(list_backups()) == 2

    def test_noop_when_fewer_than_keep(self, sample_config):
        create_backup(sample_config)
        deleted = cleanup_backups(keep=5)
        assert deleted == 0
        assert len(list_backups()) == 1

    def test_cleanup_removes_oldest(self, sample_config):
        paths = []
        for _ in range(3):
            paths.append(create_backup(sample_config))
            time.sleep(1.1)
        cleanup_backups(keep=1)
        remaining = list_backups()
        assert len(remaining) == 1
        # Newest should survive
        assert remaining[0].path == paths[-1]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestBackupEdgeCases:

    def test_restore_preserves_binary_content(self, tmp_path, _isolated_backup_dir):
        """Encrypted (binary) configs must survive backup→restore round-trip."""
        cfg = tmp_path / "user-config.json"
        binary_data = bytes(range(256))  # all byte values
        cfg.write_bytes(binary_data)
        bak = create_backup(str(cfg))
        cfg.write_bytes(b"overwritten")
        restore_backup(bak, str(cfg))
        assert cfg.read_bytes() == binary_data

    def test_cleanup_with_keep_zero_removes_all(self, sample_config):
        """keep=0 should remove every backup."""
        for _ in range(3):
            create_backup(sample_config)
            time.sleep(1.1)
        deleted = cleanup_backups(keep=0)
        assert deleted == 3
        assert list_backups() == []

    def test_restore_to_nonexistent_parent_dir(self, sample_config, tmp_path):
        """Restoring to a path whose parent doesn't exist should raise."""
        bak = create_backup(sample_config)
        bad_dest = str(tmp_path / "no_such_dir" / "user-config.json")
        with pytest.raises((FileNotFoundError, OSError)):
            restore_backup(bak, bad_dest)

    def test_empty_config_file_can_be_backed_up(self, tmp_path, _isolated_backup_dir):
        """A 0-byte config file is still a valid backup target."""
        cfg = tmp_path / "user-config.json"
        cfg.write_text("")
        bak = create_backup(str(cfg))
        assert bak.read_text() == ""
        assert bak.stat().st_size == 0
