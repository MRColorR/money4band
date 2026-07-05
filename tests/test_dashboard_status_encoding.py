"""Regression tests for the Windows cp1252 UnicodeEncodeError class of bug.

History: ``print_dashboard_status`` once printed ``*`` (was U+25CF) and
``o`` (was U+25CB) status glyphs, and ``write_env_metadata`` wrote an
em-dash to ``.env.meta``. On Windows consoles / files using the cp1252 or
ascii codec, those non-ASCII characters raised
``UnicodeEncodeError: ... ordinal not in range(128)``.

The bug was originally masked with ``sys.stdout.reconfigure(encoding="utf-8")``
shims. That only papered over it per-stream and still crashed on file
writes. The real fix is to keep the source (and therefore all printed /
written output) ASCII-only, so the error can never occur on any OS.

These tests pin that contract:
  * print paths stay encodable under a strict cp1252 stdout, and
  * the source tree contains no non-ASCII characters or escaped unicode
    (the one deliberate UTF-8 round-trip fixture excepted), and
  * main.py no longer carries the stdout-reconfigure shim.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pytest

from money4band.dashboard import setup as dashboard_setup

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Files allowed to contain non-ASCII / escaped unicode (deliberate UTF-8 test).
_ASCII_EXEMPT = {"tests/test_loader.py"}

_ESCAPED_UNICODE = re.compile(r"\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}|\\N\{[^}]+\}")


@pytest.fixture
def cp1252_strict_stdout(monkeypatch):
    """Replace sys.stdout with a strict cp1252 buffer so any unencodable
    glyph raises immediately. Proves print paths emit only cp1252-safe bytes.
    """
    buf = io.BytesIO()
    stream = io.TextIOWrapper(buf, encoding="cp1252", errors="strict", newline="")
    monkeypatch.setattr(sys, "stdout", stream)
    yield stream
    stream.flush()


class TestDashboardStatusGlyphs:
    def test_status_stopped_does_not_crash_under_cp1252_strict(
        self, tmp_path, cp1252_strict_stdout
    ):
        """The stopped-state status print must be cp1252-encodable."""
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        # No user-config.json -> dash defaults to {} -> autostart=True branch.
        try:
            dashboard_setup.print_dashboard_status(str(cfg_dir))
        except UnicodeEncodeError as exc:
            pytest.fail(
                f"print_dashboard_status crashed under strict cp1252: {exc!r}. "
                "Output must be ASCII-only."
            )

    def test_status_running_does_not_crash_under_cp1252_strict(
        self, tmp_path, cp1252_strict_stdout, monkeypatch
    ):
        """The running-state status print must be cp1252-encodable."""
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        monkeypatch.setattr(dashboard_setup, "read_dashboard_pid", lambda _: 1234)
        try:
            dashboard_setup.print_dashboard_status(str(cfg_dir))
        except UnicodeEncodeError as exc:
            pytest.fail(f"running-state print crashed: {exc!r}")


class TestSourceIsAsciiOnly:
    """Root-cause guard: no non-ASCII may re-enter the source tree."""

    def _project_py_files(self):
        for path in _REPO_ROOT.rglob("*.py"):
            rel = path.relative_to(_REPO_ROOT).as_posix()
            if ".venv" in rel.split("/"):
                continue
            yield rel, path

    def test_no_literal_non_ascii_characters(self):
        offenders = []
        for rel, path in self._project_py_files():
            if rel in _ASCII_EXEMPT:
                continue
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                for ch in line:
                    if ord(ch) > 127:
                        offenders.append(f"{rel}:{lineno}: U+{ord(ch):04X} {ch!r}")
                        break
        assert not offenders, (
            "Non-ASCII characters found in source. Use plain ASCII so output "
            "never raises UnicodeEncodeError on cp1252/ascii codecs:\n"
            + "\n".join(offenders)
        )

    def test_no_escaped_unicode_literals(self):
        offenders = []
        for rel, path in self._project_py_files():
            if rel in _ASCII_EXEMPT:
                continue
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                if _ESCAPED_UNICODE.search(line):
                    offenders.append(f"{rel}:{lineno}: {line.strip()[:80]}")
        assert not offenders, (
            "Escaped unicode literals (backslash-u, backslash-U, backslash-N "
            "escapes) found. These still emit non-ASCII bytes when "
            "printed/written:\n" + "\n".join(offenders)
        )


class TestNoStdoutReconfigureShim:
    """The bug must be prevented at the source, not masked per-stream."""

    def test_main_does_not_reconfigure_stdout(self):
        src = (_REPO_ROOT / "main.py").read_text(encoding="utf-8")
        assert "reconfigure(" not in src, (
            "main.py must not reconfigure stdout/stderr encoding. The fix is "
            "ASCII-only source, not a UTF-8 shim that masks the crash."
        )
