"""Regression tests for the setup wizard's app-config loading.

Bug: ``money4band.apps.setup.main`` loaded the app config with a plain
``loader.load_json_config(app_config_path)``. ``app_config_path`` aliases
``m4b-config.json``, where the catalog is folded under the ``catalog`` key,
so ``get_active_app_categories`` returned ``[]``. Result: Step 2 of the
wizard listed no apps, and compose/.env generation emitted an empty stack.

Fix: load via ``loader.load_app_config_with_overlays`` so categories and
entries are aggregated to the top level.
"""

from __future__ import annotations

import ast
from pathlib import Path

from money4band.core import loader
from money4band.core.loader import get_active_app_categories, get_category_entries

_REPO_ROOT = Path(__file__).resolve().parents[1]
_M4B_CONFIG = _REPO_ROOT / "config" / "m4b-config.json"
_SETUP_PY = _REPO_ROOT / "money4band" / "apps" / "setup.py"


def test_overlay_loader_yields_apps_but_plain_load_does_not():
    """Documents why the overlay loader is mandatory for the app config.

    The plain load of m4b-config exposes no app categories (catalog is
    folded); the overlay loader aggregates them. If this premise ever
    changes, the test fails loudly so the contract is revisited.
    """
    path = str(_M4B_CONFIG)

    plain_cats = get_active_app_categories(loader.load_json_config(path))
    assert plain_cats == [], (
        "Plain load_json_config of m4b-config unexpectedly exposed app "
        f"categories {plain_cats!r}; the folded-catalog premise no longer "
        "holds and the setup loader contract should be re-checked."
    )

    overlay_cfg = loader.load_app_config_with_overlays(path)
    overlay_cats = get_active_app_categories(overlay_cfg)
    assert overlay_cats, "Overlay loader returned no active app categories."
    assert any(get_category_entries(overlay_cfg, c) for c in overlay_cats), (
        "Overlay loader exposed categories but none contained app entries."
    )


def test_setup_main_uses_overlay_loader_for_app_config():
    """``setup.main`` must build app_config via the overlay loader."""
    src = _SETUP_PY.read_text(encoding="utf-8")
    tree = ast.parse(src)

    main_fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "main"
    )
    called = {
        ast.unparse(n.func)
        for n in ast.walk(main_fn)
        if isinstance(n, ast.Call)
    }
    assert any("load_app_config_with_overlays" in c for c in called), (
        "setup.main must load app config via load_app_config_with_overlays; "
        "plain load_json_config drops the folded catalog and lists no apps."
    )

    # Guard the exact regression: app_config assigned from the plain loader.
    assert "load_json_config(app_config_path)" not in src, (
        "setup.py uses load_json_config(app_config_path); this reintroduces "
        "the empty-apps bug. Use load_app_config_with_overlays(app_config_path)."
    )
