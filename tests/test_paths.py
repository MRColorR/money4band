"""Tests for the M4B data-directory resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from money4band.core import paths


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("M4B_DATA_DIR", raising=False)


def test_env_var_overrides_everything(tmp_path, monkeypatch):
    target = tmp_path / "custom"
    monkeypatch.setenv("M4B_DATA_DIR", str(target))
    monkeypatch.setattr(paths, "_LEGACY_DATA_DIR", tmp_path / "legacy")
    monkeypatch.setattr(paths, "_install_dir", lambda: tmp_path / "install")
    (tmp_path / "legacy").mkdir()
    (tmp_path / "legacy" / "master.key").write_bytes(b"legacy-key")

    resolved = paths.get_m4b_data_dir()

    assert resolved == target
    assert target.is_dir()


def test_install_dir_used_when_already_populated(tmp_path, monkeypatch):
    install = tmp_path / "install"
    legacy = tmp_path / "legacy"
    install_data = install / ".m4b"
    install_data.mkdir(parents=True)
    (install_data / "master.key").write_bytes(b"install-key")
    legacy.mkdir()
    (legacy / "master.key").write_bytes(b"legacy-key")

    monkeypatch.setattr(paths, "_LEGACY_DATA_DIR", legacy)
    monkeypatch.setattr(paths, "_install_dir", lambda: install)

    assert paths.get_m4b_data_dir() == install_data


def test_legacy_used_when_install_empty(tmp_path, monkeypatch):
    install = tmp_path / "install"
    install.mkdir()
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "master.key").write_bytes(b"legacy-key")

    monkeypatch.setattr(paths, "_LEGACY_DATA_DIR", legacy)
    monkeypatch.setattr(paths, "_install_dir", lambda: install)

    assert paths.get_m4b_data_dir() == legacy


def test_fresh_install_prefers_portable(tmp_path, monkeypatch):
    install = tmp_path / "install"
    install.mkdir()
    legacy = tmp_path / "legacy"

    monkeypatch.setattr(paths, "_LEGACY_DATA_DIR", legacy)
    monkeypatch.setattr(paths, "_install_dir", lambda: install)

    resolved = paths.get_m4b_data_dir()

    assert resolved == install / ".m4b"
    assert resolved.is_dir()
    assert not legacy.exists()


def test_falls_back_to_legacy_when_install_unwritable(tmp_path, monkeypatch):
    install = tmp_path / "install"
    install.mkdir()
    legacy = tmp_path / "legacy"

    monkeypatch.setattr(paths, "_LEGACY_DATA_DIR", legacy)
    monkeypatch.setattr(paths, "_install_dir", lambda: install)
    monkeypatch.setattr(paths, "_is_writable", lambda _p: False)

    resolved = paths.get_m4b_data_dir()

    assert resolved == legacy
    assert legacy.is_dir()


def test_install_dir_resolves_from_module_layout():
    """``_install_dir()`` returns the repo root in source mode."""
    install = paths._install_dir()
    # Repo root must contain the money4band package directory.
    assert (install / "money4band").is_dir()


# ---------------------------------------------------------------------------
# migrate_data_dir
# ---------------------------------------------------------------------------


def _make_legacy(src: Path) -> None:
    src.mkdir(parents=True, exist_ok=True)
    (src / "master.key").write_bytes(b"legacy-key")
    (src / "session.salt").write_bytes(b"legacy-salt")
    backups = src / "backups"
    backups.mkdir()
    (backups / "user-config.20260101T000000Z.bak").write_bytes(b"backup-A")
    (backups / "user-config.20260201T000000Z.bak").write_bytes(b"backup-B")


def test_migrate_copies_all_entries(tmp_path):
    src = tmp_path / "legacy"
    tgt = tmp_path / "install" / ".m4b"
    _make_legacy(src)

    result = paths.migrate_data_dir(source=src, target=tgt)

    assert (tgt / "master.key").read_bytes() == b"legacy-key"
    assert (tgt / "session.salt").read_bytes() == b"legacy-salt"
    assert (
        tgt / "backups" / "user-config.20260101T000000Z.bak"
    ).read_bytes() == b"backup-A"
    assert (
        tgt / "backups" / "user-config.20260201T000000Z.bak"
    ).read_bytes() == b"backup-B"
    assert set(result.copied) >= {"master.key", "session.salt"}
    assert result.removed_source is False
    # Source still present (default remove_source=False).
    assert (src / "master.key").is_file()


def test_migrate_is_idempotent(tmp_path):
    src = tmp_path / "legacy"
    tgt = tmp_path / "install" / ".m4b"
    _make_legacy(src)

    paths.migrate_data_dir(source=src, target=tgt)
    second = paths.migrate_data_dir(source=src, target=tgt)

    # Second run sees identical bytes and skips everything.
    assert second.copied == []
    assert "master.key" in second.skipped
    assert "session.salt" in second.skipped


def test_migrate_refuses_divergent_target_without_force(tmp_path):
    src = tmp_path / "legacy"
    tgt = tmp_path / "install" / ".m4b"
    _make_legacy(src)
    tgt.mkdir(parents=True)
    (tgt / "master.key").write_bytes(b"PORTABLE-KEY-DIFFERENT")

    with pytest.raises(FileExistsError):
        paths.migrate_data_dir(source=src, target=tgt)

    # Original portable key untouched.
    assert (tgt / "master.key").read_bytes() == b"PORTABLE-KEY-DIFFERENT"


def test_migrate_force_overwrites_divergent(tmp_path):
    src = tmp_path / "legacy"
    tgt = tmp_path / "install" / ".m4b"
    _make_legacy(src)
    tgt.mkdir(parents=True)
    (tgt / "master.key").write_bytes(b"PORTABLE-KEY-DIFFERENT")

    paths.migrate_data_dir(source=src, target=tgt, force=True)

    assert (tgt / "master.key").read_bytes() == b"legacy-key"


def test_migrate_remove_source_wipes_legacy_after_verify(tmp_path):
    src = tmp_path / "legacy"
    tgt = tmp_path / "install" / ".m4b"
    _make_legacy(src)

    result = paths.migrate_data_dir(source=src, target=tgt, remove_source=True)

    assert result.removed_source is True
    assert not (src / "master.key").exists()
    assert not (src / "session.salt").exists()
    assert not (src / "backups").exists()
    # Source dir itself stays (only migratable entries removed).
    assert src.is_dir()


def test_migrate_missing_source_raises(tmp_path):
    src = tmp_path / "nope"
    tgt = tmp_path / "install" / ".m4b"

    with pytest.raises(FileNotFoundError):
        paths.migrate_data_dir(source=src, target=tgt)


def test_migrate_same_source_and_target_rejected(tmp_path):
    src = tmp_path / "data"
    _make_legacy(src)

    with pytest.raises(ValueError):
        paths.migrate_data_dir(source=src, target=src)
