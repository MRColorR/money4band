"""End-to-end portability test for the M4B data dir.

Covers the P4.E acceptance criterion:
- Encryption material (master.key) lands in `<install>/.m4b/`, not in `~/.m4b/`.
- After moving the install dir to a new location with its `.m4b/` carried
  along, encrypted blobs still decrypt with the same key.
- The legacy `~/.m4b/` location is not created or modified.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from money4band.core import paths
from money4band.core.backup import create_backup
from money4band.core.crypto import decrypt_to_dict, encrypt_dict, get_or_create_key


@pytest.fixture(autouse=True)
def _isolated_env(tmp_path, monkeypatch):
    """Point HOME and the install dir at clean tmp locations."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.delenv("M4B_DATA_DIR", raising=False)
    monkeypatch.setattr(paths, "_LEGACY_DATA_DIR", fake_home / ".m4b")


def _patch_install(monkeypatch, install: Path) -> None:
    monkeypatch.setattr(paths, "_install_dir", lambda: install)


def test_fresh_install_lands_in_portable_dir(tmp_path, monkeypatch):
    install_a = tmp_path / "install_a"
    install_a.mkdir()
    _patch_install(monkeypatch, install_a)

    key = get_or_create_key()

    portable = install_a / ".m4b" / "master.key"
    assert portable.is_file()
    assert portable.read_bytes().strip() == key

    legacy = paths._LEGACY_DATA_DIR / "master.key"
    assert not legacy.exists()


def test_encrypted_blob_roundtrips_after_install_relocation(tmp_path, monkeypatch):
    """Move the install dir; encrypted data still decrypts.

    Simulates the PyInstaller-on-USB scenario: install_b is install_a copied
    to a new path. The `.m4b/` directory rides along, so the key is preserved.
    """
    install_a = tmp_path / "install_a"
    install_a.mkdir()
    _patch_install(monkeypatch, install_a)

    payload = {"api_key": "secret-abc", "ports": {"base": 50000}}
    blob = encrypt_dict(payload)
    assert (install_a / ".m4b" / "master.key").is_file()

    install_b = tmp_path / "install_b"
    shutil.copytree(install_a, install_b)
    _patch_install(monkeypatch, install_b)

    assert decrypt_to_dict(blob) == payload
    assert (install_b / ".m4b" / "master.key").is_file()
    assert not paths._LEGACY_DATA_DIR.exists()


def test_backup_lands_in_portable_dir(tmp_path, monkeypatch):
    install = tmp_path / "install"
    install.mkdir()
    _patch_install(monkeypatch, install)

    config_path = install / "config" / "user-config.json"
    config_path.parent.mkdir()
    config_path.write_text('{"foo": "bar"}')

    backup_path = create_backup(str(config_path))

    assert backup_path.parent == install / ".m4b" / "backups"
    assert backup_path.is_file()
    assert not paths._LEGACY_DATA_DIR.exists()


def test_env_var_redirects_to_external_dir(tmp_path, monkeypatch):
    """`$M4B_DATA_DIR` outranks both portable and legacy locations."""
    install = tmp_path / "install"
    install.mkdir()
    _patch_install(monkeypatch, install)

    external = tmp_path / "external_data"
    monkeypatch.setenv("M4B_DATA_DIR", str(external))

    key = get_or_create_key()
    assert (external / "master.key").read_bytes().strip() == key
    assert not (install / ".m4b" / "master.key").exists()
    assert not paths._LEGACY_DATA_DIR.exists()


def test_legacy_dir_picked_up_if_already_populated(tmp_path, monkeypatch):
    """Existing legacy users keep working - install dir is not auto-promoted."""
    install = tmp_path / "install"
    install.mkdir()
    legacy = tmp_path / "home" / ".m4b"
    legacy.mkdir(parents=True)
    monkeypatch.setattr(paths, "_LEGACY_DATA_DIR", legacy)
    _patch_install(monkeypatch, install)

    seeded_key = b"existing-legacy-key-bytes-do-not-touch"
    (legacy / "master.key").write_bytes(seeded_key)

    resolved = paths.get_m4b_data_dir()

    assert resolved == legacy
    # No portable dir auto-created.
    assert not (install / ".m4b" / "master.key").exists()


def test_migrate_then_load_uses_portable(tmp_path, monkeypatch):
    """Legacy user runs migrate-data-dir; subsequent loads see portable copy."""
    install = tmp_path / "install"
    install.mkdir()
    legacy = tmp_path / "home" / ".m4b"
    legacy.mkdir(parents=True)
    monkeypatch.setattr(paths, "_LEGACY_DATA_DIR", legacy)
    _patch_install(monkeypatch, install)

    seeded_key = b"existing-legacy-key-bytes-32-aaaa"
    (legacy / "master.key").write_bytes(seeded_key)
    (legacy / "session.salt").write_bytes(b"deadbeef" * 4)

    paths.migrate_data_dir(remove_source=True)

    portable = install / ".m4b"
    assert (portable / "master.key").read_bytes() == seeded_key
    assert (portable / "session.salt").read_bytes() == b"deadbeef" * 4
    assert not (legacy / "master.key").exists()

    # Subsequent resolution now points at the portable dir.
    assert paths.get_m4b_data_dir() == portable
