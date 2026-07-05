from __future__ import annotations

"""Resolve the M4B runtime data directory.

Houses the master encryption key, session salt, and config backups.

Three-tier precedence (highest first):

1. ``$M4B_DATA_DIR`` env var.
2. ``<install_dir>/.m4b/`` when already populated, OR when the install dir is
   writable and no legacy ``~/.m4b/`` exists. This is the portable default for
   fresh installs - the binary or git clone carries its own runtime state,
   so moving the install folder between machines or running multiple installs
   side-by-side does not collide on a single global key.
3. ``~/.m4b/`` legacy fallback - preserves continuity for users upgrading from
   versions that wrote there, and acts as a last resort when the install dir
   is read-only (e.g. system-installed binary in /usr/local/bin).
"""

import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_LEGACY_DATA_DIR = Path.home() / ".m4b"
_DATA_SUBDIR = ".m4b"

# Files (and directories) migrated by ``migrate_data_dir``. Keep in sync with
# the writers in ``money4band.core.crypto`` / ``money4band.core.backup`` /
# ``money4band.api.server``.
_MIGRATABLE_ENTRIES: tuple[str, ...] = ("master.key", "session.salt", "backups")


def _install_dir() -> Path:
    """Return the M4B install root.

    Frozen (PyInstaller) -> the directory containing the executable.
    Source -> the repo root (parent of the ``money4band`` package).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # money4band/core/paths.py -> money4band/core/ -> money4band/ -> repo root
    return Path(__file__).resolve().parent.parent.parent


def _is_writable(path: Path) -> bool:
    """Return True if a sentinel file can be created in *path*."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        sentinel = path / ".write_test"
        sentinel.touch()
        sentinel.unlink()
        return True
    except OSError:
        return False


def get_m4b_data_dir() -> Path:
    """Return the resolved M4B data directory, creating it if needed.

    See module docstring for precedence rules.
    """
    env = os.environ.get("M4B_DATA_DIR")
    if env:
        path = Path(env).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    install_data = _install_dir() / _DATA_SUBDIR
    legacy_populated = (_LEGACY_DATA_DIR / "master.key").is_file()
    install_populated = (install_data / "master.key").is_file()

    if install_populated:
        return install_data

    if legacy_populated:
        if install_data.is_dir():
            logger.debug(
                "Both portable (%s) and legacy (%s) data dirs exist; "
                "using legacy because it has the master key.",
                install_data,
                _LEGACY_DATA_DIR,
            )
        return _LEGACY_DATA_DIR

    if _is_writable(install_data):
        return install_data

    _LEGACY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _LEGACY_DATA_DIR


class MigrationResult:
    """Outcome of a ``migrate_data_dir`` invocation."""

    __slots__ = ("source", "target", "copied", "skipped", "removed_source")

    def __init__(
        self,
        source: Path,
        target: Path,
        copied: list[str],
        skipped: list[str],
        removed_source: bool,
    ) -> None:
        self.source = source
        self.target = target
        self.copied = copied
        self.skipped = skipped
        self.removed_source = removed_source


def migrate_data_dir(
    *,
    source: Path | None = None,
    target: Path | None = None,
    remove_source: bool = False,
    force: bool = False,
) -> MigrationResult:
    """Copy legacy ``~/.m4b/`` contents into the portable install data dir.

    Idempotent: re-running with the same source/target is a no-op once the
    target already contains the entries. When ``force`` is False and an entry
    already exists at the target with **different** bytes, raises FileExistsError
    rather than silently clobbering a divergent file.

    ``remove_source=True`` wipes migrated entries from the source only after
    every copy has been verified by byte-comparison.
    """
    src = source if source is not None else _LEGACY_DATA_DIR
    tgt = target if target is not None else _install_dir() / _DATA_SUBDIR

    if not src.is_dir():
        raise FileNotFoundError(f"Source data dir does not exist: {src}")
    if src.resolve() == tgt.resolve():
        raise ValueError(
            f"Source and target are the same path ({src}); nothing to migrate."
        )

    tgt.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    skipped: list[str] = []

    for name in _MIGRATABLE_ENTRIES:
        src_entry = src / name
        tgt_entry = tgt / name
        if not src_entry.exists():
            continue
        if src_entry.is_dir():
            _migrate_directory(src_entry, tgt_entry, force, copied, skipped)
        else:
            _migrate_file(src_entry, tgt_entry, force, copied, skipped)

    removed = False
    if remove_source:
        _verify_copies(src, tgt)
        _remove_source_entries(src)
        removed = True

    logger.info(
        "Data-dir migration %s -> %s: copied=%d skipped=%d removed_source=%s",
        src,
        tgt,
        len(copied),
        len(skipped),
        removed,
    )
    return MigrationResult(src, tgt, copied, skipped, removed)


def _migrate_file(
    src: Path, tgt: Path, force: bool, copied: list[str], skipped: list[str]
) -> None:
    if tgt.exists():
        if tgt.is_file() and tgt.read_bytes() == src.read_bytes():
            skipped.append(str(tgt.name))
            return
        if not force:
            raise FileExistsError(
                f"Target {tgt} already exists and differs from source. "
                "Re-run with force=True to overwrite."
            )
    tgt.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(tgt))
    try:
        # Preserve 0o600 for sensitive files where applicable.
        mode = src.stat().st_mode & 0o777
        os.chmod(tgt, mode)
    except OSError:
        logger.debug("chmod failed on %s (likely Windows)", tgt)
    copied.append(str(tgt.name))


def _migrate_directory(
    src: Path, tgt: Path, force: bool, copied: list[str], skipped: list[str]
) -> None:
    tgt.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        if entry.is_dir():
            _migrate_directory(entry, tgt / entry.name, force, copied, skipped)
        else:
            _migrate_file(entry, tgt / entry.name, force, copied, skipped)


def _verify_copies(src: Path, tgt: Path) -> None:
    """Byte-compare every migrated entry. Raises if any mismatch."""
    for name in _MIGRATABLE_ENTRIES:
        src_entry = src / name
        tgt_entry = tgt / name
        if not src_entry.exists():
            continue
        if src_entry.is_file():
            if (
                not tgt_entry.is_file()
                or src_entry.read_bytes() != tgt_entry.read_bytes()
            ):
                raise RuntimeError(
                    f"Verification failed for {name}; refusing to remove source."
                )
        elif src_entry.is_dir():
            for s in src_entry.rglob("*"):
                if s.is_file():
                    rel = s.relative_to(src_entry)
                    t = tgt_entry / rel
                    if not t.is_file() or s.read_bytes() != t.read_bytes():
                        raise RuntimeError(
                            f"Verification failed for {name}/{rel}; refusing to remove source."
                        )


def _remove_source_entries(src: Path) -> None:
    for name in _MIGRATABLE_ENTRIES:
        entry = src / name
        if not entry.exists():
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()
