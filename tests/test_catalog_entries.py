"""Tests for the typed catalog loader helper (phase-8.1)."""

from __future__ import annotations

from money4band.apps.schema import SOURCE_BUILTIN, CatalogEntry
from money4band.core.loader import load_catalog_entries


def _entry(name: str, **over):
    e = {
        "name": name,
        "compose_config": {"image": f"{name.lower()}/img:latest"},
        "flags": {},
        "install_limit": -1,
        "compose_layer": "residential",
    }
    e.update(over)
    return e


def _config():
    return {
        "app_config_version": 2.0,
        "supported": {
            "active": True,
            "entries": [
                _entry(
                    "ALPHA",
                    referrals=[
                        {
                            "url": "https://example/r/alpha",
                            "contributor": "MRColorR",
                        }
                    ],
                ),
                _entry("BRAVO"),
            ],
        },
        "newcomers": {
            "active": False,
            "entries": [_entry("CHARLIE")],
        },
        "deprecated": {
            "active": False,
            "entries": [_entry("DELTA", additional_details="dead")],
        },
    }


class TestLoadCatalogEntries:
    def test_returns_typed_entries(self):
        entries = load_catalog_entries(_config())
        assert all(isinstance(e, CatalogEntry) for e in entries)
        ids = {e.id for e in entries}
        assert ids == {"ALPHA", "BRAVO", "CHARLIE", "DELTA"}

    def test_categories_normalized(self):
        entries = load_catalog_entries(_config())
        by_id = {e.id: e for e in entries}
        assert by_id["ALPHA"].category == "supported"
        assert by_id["CHARLIE"].category == "newcomers"
        assert by_id["DELTA"].category == "deprecated"

    def test_source_is_builtin_by_default(self):
        entries = load_catalog_entries(_config())
        assert all(e.source == SOURCE_BUILTIN for e in entries)

    def test_filter_by_categories(self):
        entries = load_catalog_entries(_config(), categories=["supported"])
        assert {e.id for e in entries} == {"ALPHA", "BRAVO"}

    def test_referrals_pool_populated(self):
        entries = load_catalog_entries(_config())
        alpha = next(e for e in entries if e.id == "ALPHA")
        assert len(alpha.metadata.referrals) == 1
        assert alpha.metadata.referrals[0].url == "https://example/r/alpha"
        assert alpha.metadata.referrals[0].contributor == "MRColorR"

    def test_additional_details_preserved(self):
        entries = load_catalog_entries(_config())
        delta = next(e for e in entries if e.id == "DELTA")
        assert delta.additional_details == "dead"

    def test_bravo_has_empty_referrals(self):
        entries = load_catalog_entries(_config())
        bravo = next(e for e in entries if e.id == "BRAVO")
        assert bravo.metadata.referrals == []

    def test_skips_non_dict_entries(self):
        cfg = _config()
        cfg["supported"]["entries"].append("garbage")  # type: ignore[arg-type]
        entries = load_catalog_entries(cfg)
        assert {e.id for e in entries} == {"ALPHA", "BRAVO", "CHARLIE", "DELTA"}

    def test_empty_config(self):
        assert load_catalog_entries({}) == []
