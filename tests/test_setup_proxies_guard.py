"""Regression sentinels for P1-3: proxies.txt guard in setup wizard.

The proxy-configuration step in ``money4band.apps.setup`` used to call
``open("proxies.txt")`` unconditionally and crash with a bare
``FileNotFoundError`` on first-run setups where the file was absent. The
fix added (a) an explicit ``os.path.isfile`` check that prints a friendly
message and aborts the step, and (b) an ``except OSError`` around the
read for non-existence failures (permissions, locked file).

These are sentinel tests - they don't drive the interactive setup
wizard, they pin the structural guards in source so a regression to
the bare ``open()`` form is caught in CI.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import money4band.apps.setup as _setup_mod


def _setup_source() -> str:
    return Path(_setup_mod.__file__).read_text(encoding="utf-8")


def test_setup_has_isfile_guard_for_proxies_txt():
    src = _setup_source()
    # Guard before the open(): explicit isfile() check.
    assert re.search(
        r'os\.path\.isfile\(\s*[\'"]proxies\.txt[\'"]\s*\)',
        src,
    ), "proxies.txt isfile() guard is missing - re-introduces P1-3 crash"


def test_setup_wraps_proxies_open_in_oserror_handler():
    src = _setup_source()
    # The open() must live inside a try/except OSError block.
    tree = ast.parse(src)
    found_guarded_open = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        body_src = ast.unparse(node.body) if hasattr(ast, "unparse") else ""
        if "proxies.txt" not in body_src:
            continue
        for handler in node.handlers:
            if handler.type is None:
                continue
            handler_name = ast.unparse(handler.type)
            if "OSError" in handler_name or "FileNotFoundError" in handler_name:
                found_guarded_open = True
                break
    assert found_guarded_open, (
        "open('proxies.txt') must be wrapped in try/except OSError "
        "to keep first-run setup from crashing on a missing/unreadable file."
    )


def test_setup_does_not_have_bare_proxies_open():
    """No naked ``open("proxies.txt")`` outside the guarded try block."""
    src = inspect.getsource(_setup_mod)
    tree = ast.parse(src)

    bare_open_lines: list[int] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self._in_try_with_oserror = 0

        def visit_Try(self, node: ast.Try) -> None:
            has_oserror = any(
                h.type is not None
                and ("OSError" in ast.unparse(h.type) or "FileNotFoundError" in ast.unparse(h.type))
                for h in node.handlers
            )
            if has_oserror:
                self._in_try_with_oserror += 1
                for child in node.body:
                    self.visit(child)
                self._in_try_with_oserror -= 1
                for handler in node.handlers:
                    for child in handler.body:
                        self.visit(child)
                if node.orelse:
                    for child in node.orelse:
                        self.visit(child)
                if node.finalbody:
                    for child in node.finalbody:
                        self.visit(child)
            else:
                self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "open"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "proxies.txt"
                and self._in_try_with_oserror == 0
            ):
                bare_open_lines.append(node.lineno)
            self.generic_visit(node)

    Visitor().visit(tree)
    assert not bare_open_lines, (
        f"Found unguarded open('proxies.txt') at line(s) {bare_open_lines} - "
        "wrap in try/except OSError to prevent first-run crashes."
    )
