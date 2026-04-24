"""Unit tests for `money4band.apps.catalog_manager`.

Covers the single source of truth used by the CLI (`catalog_cli`),
the REST API (`router_catalog`), and the TUI submenu
(`fn_app_catalog → _manage_sources`) — so parity across surfaces is
verified at the one module they all share.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from money4band.apps import catalog_manager as cm


def _seed(tmp_path: Path) -> Path:
    """Write a minimal m4b-config.json with a folded catalog envelope."""
    path = tmp_path / "m4b-config.json"
    payload = {
        "project": {"project_version": "5.0.0"},
        "catalog": {
            "app_config_version": 2.0,
            "catalog_sources": [
                {
                    "type": "local",
                    "name": "builtin",
                    "path": "catalog",
                    "default_source": "builtin",
                    "enabled": True,
                }
            ],
            "categories": {
                "supported": {"active": True},
                "newcomers": {"active": False},
                "deprecated": {"active": False},
            },
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def test_list_sources_returns_copy(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    sources = cm.list_sources(cfg)
    assert len(sources) == 1
    assert sources[0]["name"] == "builtin"
    # Mutating the returned list must not affect subsequent reads.
    sources.append({"junk": True})
    assert len(cm.list_sources(cfg)) == 1


def test_list_categories(tmp_path: Path) -> None:
    cats = cm.list_categories(_seed(tmp_path))
    assert set(cats) == {"supported", "newcomers", "deprecated"}
    assert cats["supported"]["active"] is True
    assert cats["newcomers"]["active"] is False


def test_source_status_enriches_local(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    (tmp_path / "catalog" / "supported").mkdir(parents=True)
    (tmp_path / "catalog" / "supported" / "foo.json").write_text(
        json.dumps(
            {"name": "Foo", "referrals": [], "dashboard": "", "compose_config": {}}
        ),
        encoding="utf-8",
    )
    status = cm.source_status(cfg)
    assert status[0]["name"] == "builtin"
    assert status[0]["type"] == "local"
    assert status[0]["cached_entries"] == 1
    assert "resolved_path" in status[0]


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def test_add_source_persists(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    cm.add_source(
        cfg,
        name="community",
        type="remote",
        url="https://example.invalid/manifest.json",
        enabled=False,
    )
    sources = cm.list_sources(cfg)
    assert len(sources) == 2
    added = sources[1]
    assert added["name"] == "community"
    assert added["type"] == "remote"
    assert added["enabled"] is False


def test_add_source_normalizes_github_repo_url(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    cm.add_source(
        cfg,
        name="community",
        type="remote",
        url="https://github.com/MRColorR/money4band-community-catalog",
        enabled=True,
    )
    sources = cm.list_sources(cfg)
    added = next(s for s in sources if s["name"] == "community")
    assert (
        added["url"]
        == "https://raw.githubusercontent.com/MRColorR/money4band-community-catalog/main/manifest.json"
    )


def test_add_source_normalizes_github_blob_manifest_url(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    cm.add_source(
        cfg,
        name="community",
        type="remote",
        url="https://github.com/MRColorR/money4band-community-catalog/blob/main/manifest.json",
        enabled=True,
    )
    sources = cm.list_sources(cfg)
    added = next(s for s in sources if s["name"] == "community")
    assert (
        added["url"]
        == "https://raw.githubusercontent.com/MRColorR/money4band-community-catalog/main/manifest.json"
    )


def test_add_source_rejects_duplicate(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    with pytest.raises(cm.CatalogSourceError):
        cm.add_source(cfg, name="builtin", type="local", path="catalog")


def test_add_source_rejects_bad_type(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    with pytest.raises(cm.CatalogSourceError):
        cm.add_source(cfg, name="x", type="ftp", url="ftp://nope")


def test_remove_source(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    cm.add_source(cfg, name="x", type="remote", url="https://x.invalid/m.json")
    assert cm.remove_source(cfg, "x") is True
    assert cm.remove_source(cfg, "x") is False
    assert [s["name"] for s in cm.list_sources(cfg)] == ["builtin"]


def test_set_source_enabled(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    assert cm.set_source_enabled(cfg, "builtin", False) is True
    assert cm.list_sources(cfg)[0]["enabled"] is False
    assert cm.set_source_enabled(cfg, "builtin", True) is True
    assert cm.list_sources(cfg)[0]["enabled"] is True
    assert cm.set_source_enabled(cfg, "ghost", True) is False


def test_set_category(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    cm.set_category(cfg, "newcomers", True)
    assert cm.list_categories(cfg)["newcomers"]["active"] is True
    cm.set_category(cfg, "newcomers", False)
    assert cm.list_categories(cfg)["newcomers"]["active"] is False


def test_set_category_rejects_unknown(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    with pytest.raises(cm.CatalogSourceError):
        cm.set_category(cfg, "invented", True)


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


def test_refresh_source_skips_local(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    results = cm.refresh_source(cfg, None)
    # Only local source present → must be skipped, not errored.
    assert results == [{"name": "builtin", "status": "skipped"}]


def test_refresh_source_unknown_raises(tmp_path: Path) -> None:
    cfg = _seed(tmp_path)
    with pytest.raises(cm.CatalogSourceError):
        cm.refresh_source(cfg, "ghost")


# ---------------------------------------------------------------------------
# humanize
# ---------------------------------------------------------------------------


def test_humanize_fetched_at_none() -> None:
    assert cm.humanize_fetched_at(None) == "never"


def test_humanize_fetched_at_invalid() -> None:
    # Bad ISO string must not crash; falls back to a safe string.
    out = cm.humanize_fetched_at("not-a-timestamp")
    assert isinstance(out, str)
