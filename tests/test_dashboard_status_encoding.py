"""Regression tests for the dashboard status Unicode crash on Windows cp1252.

`print_dashboard_status` prints the ``●`` (U+25CF) and ``○`` (U+25CB) glyphs.
On Windows consoles with the cp1252 code page (default for many setups),
plain ``print`` would raise ``UnicodeEncodeError: 'charmap' codec can't
encode character '\\u25cb'`` before the fix landed in ``main.py``.

The fix forces ``sys.stdout`` to UTF-8 with ``errors="replace"`` at app
entry. These tests pin both the entry-point preamble (sentinel) and the
end-to-end behaviour under a simulated strict-cp1252 stdout.
"""

from __future__ import annotations

import ast
import io
import sys
from pathlib import Path

import pytest

from money4band.dashboard import setup as dashboard_setup


@pytest.fixture
def cp1252_strict_stdout(monkeypatch):
    """Replace sys.stdout with a strict cp1252 buffer so any unencodable
    glyph raises immediately. Use this to prove print paths emit only
    cp1252-safe bytes OR have been swapped to error-tolerant encoding.
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
        """The ○ glyph in the stopped-state print used to UnicodeEncodeError."""
        # Use a tmp config_dir so the function doesn't look at a real install.
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        # No user-config.json → dash defaults to {} → autostart=True branch.
        try:
            dashboard_setup.print_dashboard_status(str(cfg_dir))
        except UnicodeEncodeError as exc:
            pytest.fail(
                f"print_dashboard_status crashed under strict cp1252: {exc!r}. "
                "The main.py UTF-8 reconfigure was supposed to prevent this."
            )

    def test_status_running_does_not_crash_under_cp1252_strict(
        self, tmp_path, cp1252_strict_stdout, monkeypatch
    ):
        """The ● glyph in the running-state print path is also Unicode."""
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        monkeypatch.setattr(
            dashboard_setup, "read_dashboard_pid", lambda _: 1234
        )
        try:
            dashboard_setup.print_dashboard_status(str(cfg_dir))
        except UnicodeEncodeError as exc:
            pytest.fail(f"running-state print crashed: {exc!r}")


class TestMainPyUtf8Reconfigure:
    """Sentinel that the UTF-8 reconfigure block stays in main.py."""

    def test_main_reconfigures_stdout_on_windows(self):
        src = Path(__file__).resolve().parents[1] / "main.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))

        found_reconfigure_call = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "reconfigure"
                and any(
                    kw.arg == "encoding"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value == "utf-8"
                    for kw in node.keywords
                )
            ):
                found_reconfigure_call = True
                break

        assert found_reconfigure_call, (
            "main.py must call sys.stdout.reconfigure(encoding='utf-8', ...) "
            "early in the boot to prevent UnicodeEncodeError on Windows cp1252. "
            "See tests/test_dashboard_status_encoding.py for the regression "
            "this guards against."
        )

    def test_main_reconfigure_guarded_for_non_win32_or_failure(self):
        """The reconfigure must be guarded so non-win32 + non-TextIOWrapper
        streams (piped output, embedded interpreters) don't blow up."""
        src = (Path(__file__).resolve().parents[1] / "main.py").read_text(
            encoding="utf-8"
        )
        # Quick text check — the block must live under a sys.platform guard
        # and wrap the call in try/except.
        assert 'sys.platform == "win32"' in src
        assert "AttributeError" in src or "OSError" in src
