"""Tests for the pluggable catalog source interface (phase-8.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from money4band.apps.sources import (
    CatalogSource,
    LocalSource,
    RemoteSource,
    aggregate_from_sources,
    build_sources,
)
from money4band.core.catalog_store import (
    default_envelope,
    write_entry,
    write_envelope,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config_with_bundles(tmp_path: Path) -> Path:
    """Create a minimal envelope + a few per-file bundles on disk."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "app-config.json"

    envelope = default_envelope()
    # Activate newcomers so we can exercise non-default flags too.
    envelope["categories"]["newcomers"]["active"] = True
    write_envelope(envelope, config_path)

    write_entry(
        {"name": "ALPHA", "app_details": {"docker": "alpha/alpha"}},
        config_path,
        "supported",
    )
    write_entry(
        {"name": "BETA", "app_details": {"docker": "beta/beta"}},
        config_path,
        "supported",
    )
    write_entry(
        {"name": "GAMMA", "app_details": {"docker": "gamma/gamma"}},
        config_path,
        "newcomers",
    )
    write_entry(
        {"name": "OMEGA", "app_details": {"docker": "omega/omega"}},
        config_path,
        "deprecated",
    )
    return config_path


# ---------------------------------------------------------------------------
# LocalSource
# ---------------------------------------------------------------------------


class TestLocalSource:
    def test_type_is_local(self) -> None:
        src = LocalSource(path="catalog")
        assert src.type == "local"

    def test_available_honors_enabled(self) -> None:
        assert LocalSource(path="x").available() is True
        assert LocalSource(path="x", enabled=False).available() is False

    def test_load_resolves_relative_path(self, config_with_bundles: Path) -> None:
        src = LocalSource(path="catalog")
        out = src.load(config_with_bundles)
        names = {e["name"] for e in out["supported"]}
        assert names == {"ALPHA", "BETA"}
        assert [e["name"] for e in out["newcomers"]] == ["GAMMA"]
        assert [e["name"] for e in out["deprecated"]] == ["OMEGA"]

    def test_load_accepts_absolute_path(self, config_with_bundles: Path) -> None:
        abs_catalog = config_with_bundles.parent / "catalog"
        src = LocalSource(path=str(abs_catalog))
        out = src.load(config_with_bundles)
        assert {e["name"] for e in out["supported"]} == {"ALPHA", "BETA"}

    def test_load_missing_dir_returns_empty(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config" / "app-config.json"
        config_path.parent.mkdir()
        config_path.write_text("{}")
        src = LocalSource(path="catalog")
        out = src.load(config_path)
        assert out == {"supported": [], "newcomers": [], "deprecated": []}

    def test_load_disabled_returns_empty(self, config_with_bundles: Path) -> None:
        src = LocalSource(path="catalog", enabled=False)
        out = src.load(config_with_bundles)
        assert out == {"supported": [], "newcomers": [], "deprecated": []}


# ---------------------------------------------------------------------------
# RemoteSource (phase-8.5)
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: object | None = None,
        etag: str | None = None,
        raise_json: bool = False,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = {"ETag": etag} if etag else {}
        self._raise_json = raise_json

    def json(self) -> object:
        if self._raise_json:
            raise ValueError("invalid json")
        return self._payload


class _FakeClient:
    """Minimal drop-in for ``httpx.Client`` used by RemoteSource.

    ``responses`` is consumed in order per ``get()`` call; each entry can
    be a ``_FakeResponse`` or an ``Exception`` instance to raise.
    """

    last_headers: dict[str, str] | None = None

    def __init__(self, responses: list) -> None:
        self._responses = list(responses)

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def get(self, url: str, headers: dict[str, str] | None = None) -> _FakeResponse:
        _FakeClient.last_headers = dict(headers or {})
        resp = self._responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


def _patch_httpx(monkeypatch, responses: list) -> None:
    """Patch ``httpx.Client`` with a fake that yields ``responses``."""
    import httpx

    client_factory = lambda *a, **kw: _FakeClient(responses)  # noqa: E731
    monkeypatch.setattr(httpx, "Client", client_factory)


class TestRemoteSource:
    def _manifest(self) -> dict:
        return {
            "supported": {
                "entries": [{"name": "REMOTEAPP", "compose_config": {"image": "x"}}]
            },
            "newcomers": {"entries": []},
            "deprecated": {"entries": []},
        }

    def test_type_is_remote(self) -> None:
        assert RemoteSource(url="https://example/catalog").type == "remote"

    def test_available_needs_enabled_and_url(self) -> None:
        assert RemoteSource(url="https://x", enabled=True).available() is True
        assert RemoteSource(url="https://x", enabled=False).available() is False
        assert RemoteSource(url="", enabled=True).available() is False

    def test_disabled_yields_empty_and_skips_fetch(self, tmp_path: Path) -> None:
        src = RemoteSource(url="https://x", enabled=False)
        out = src.load(tmp_path / "config.json")
        assert out == {"supported": [], "newcomers": [], "deprecated": []}

    def test_successful_fetch_populates_cache(self, tmp_path, monkeypatch) -> None:
        _patch_httpx(
            monkeypatch,
            [_FakeResponse(200, self._manifest(), etag='W/"abc"')],
        )
        src = RemoteSource(
            url="https://example/catalog",
            enabled=True,
            cache_path="catalog/community",
        )
        out = src.load(tmp_path / "m4b-config.json")
        assert len(out["supported"]) == 1
        assert out["supported"][0]["name"] == "REMOTEAPP"

        cache_dir = tmp_path / "catalog" / "community"
        assert (cache_dir / "supported" / "REMOTEAPP.json").is_file()
        assert (cache_dir / ".etag").read_text(encoding="utf-8").strip() == 'W/"abc"'
        assert (cache_dir / ".fetched_at").is_file()

    def test_sends_if_none_match_header(self, tmp_path, monkeypatch) -> None:
        # Seed a pre-existing etag.
        cache_dir = tmp_path / "catalog" / "community"
        cache_dir.mkdir(parents=True)
        (cache_dir / ".etag").write_text('"seed-etag"', encoding="utf-8")

        _patch_httpx(monkeypatch, [_FakeResponse(304)])
        src = RemoteSource(url="https://example/catalog", enabled=True)
        src.load(tmp_path / "m4b-config.json")

        assert _FakeClient.last_headers is not None
        assert _FakeClient.last_headers.get("If-None-Match") == '"seed-etag"'

    def test_304_keeps_cached_entries(self, tmp_path, monkeypatch) -> None:
        cache_dir = tmp_path / "catalog" / "community"
        (cache_dir / "supported").mkdir(parents=True)
        (cache_dir / "supported" / "CACHED.json").write_text(
            '{"name": "CACHED", "compose_config": {"image": "y"}}',
            encoding="utf-8",
        )
        (cache_dir / ".etag").write_text('"etag-1"', encoding="utf-8")

        _patch_httpx(monkeypatch, [_FakeResponse(304)])
        src = RemoteSource(url="https://example/catalog", enabled=True)
        out = src.load(tmp_path / "m4b-config.json")
        assert len(out["supported"]) == 1
        assert out["supported"][0]["name"] == "CACHED"

    def test_network_failure_falls_back_to_cache(self, tmp_path, monkeypatch) -> None:
        import httpx

        cache_dir = tmp_path / "catalog" / "community"
        (cache_dir / "supported").mkdir(parents=True)
        (cache_dir / "supported" / "OFFLINE.json").write_text(
            '{"name": "OFFLINE", "compose_config": {"image": "z"}}',
            encoding="utf-8",
        )

        _patch_httpx(monkeypatch, [httpx.ConnectError("boom")])
        src = RemoteSource(url="https://example/catalog", enabled=True)
        out = src.load(tmp_path / "m4b-config.json")
        assert [e["name"] for e in out["supported"]] == ["OFFLINE"]

    def test_non_200_status_uses_cache(self, tmp_path, monkeypatch) -> None:
        _patch_httpx(monkeypatch, [_FakeResponse(503)])
        src = RemoteSource(url="https://example/catalog", enabled=True)
        out = src.load(tmp_path / "m4b-config.json")
        # No cache seeded — empty result but no raise.
        assert out == {"supported": [], "newcomers": [], "deprecated": []}

    def test_invalid_json_uses_cache(self, tmp_path, monkeypatch) -> None:
        _patch_httpx(monkeypatch, [_FakeResponse(200, raise_json=True)])
        src = RemoteSource(url="https://example/catalog", enabled=True)
        out = src.load(tmp_path / "m4b-config.json")
        assert out == {"supported": [], "newcomers": [], "deprecated": []}

    def test_refresh_replaces_stale_entries(self, tmp_path, monkeypatch) -> None:
        cache_dir = tmp_path / "catalog" / "community"
        (cache_dir / "supported").mkdir(parents=True)
        (cache_dir / "supported" / "OLD.json").write_text(
            '{"name": "OLD"}', encoding="utf-8"
        )

        _patch_httpx(monkeypatch, [_FakeResponse(200, self._manifest(), etag='"new"')])
        src = RemoteSource(url="https://example/catalog", enabled=True)
        src.load(tmp_path / "m4b-config.json")

        assert not (cache_dir / "supported" / "OLD.json").exists()
        assert (cache_dir / "supported" / "REMOTEAPP.json").is_file()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestBuildSources:
    def test_builds_local(self) -> None:
        env = {
            "catalog_sources": [
                {
                    "type": "local",
                    "path": "catalog",
                    "default_source": "builtin",
                    "enabled": True,
                }
            ]
        }
        sources = build_sources(env, "/tmp/app-config.json")
        assert len(sources) == 1
        assert isinstance(sources[0], LocalSource)
        assert sources[0].default_source == "builtin"
        assert sources[0].enabled is True

    def test_builds_remote(self) -> None:
        env = {
            "catalog_sources": [
                {
                    "type": "remote",
                    "url": "https://example/catalog",
                    "default_source": "community",
                    "enabled": False,
                    "timeout": 10,
                }
            ]
        }
        sources = build_sources(env, "/tmp/app-config.json")
        assert len(sources) == 1
        rs = sources[0]
        assert isinstance(rs, RemoteSource)
        assert rs.url == "https://example/catalog"
        assert rs.timeout == 10.0
        assert rs.default_source == "community"
        assert rs.enabled is False

    def test_skips_unknown_types(self) -> None:
        env = {
            "catalog_sources": [
                {"type": "git", "url": "https://x"},
                {"type": "local", "path": "p"},
            ]
        }
        sources = build_sources(env, "/tmp/c.json")
        assert len(sources) == 1
        assert isinstance(sources[0], LocalSource)

    def test_skips_incomplete_declarations(self) -> None:
        env = {
            "catalog_sources": [
                {"type": "local"},  # missing path
                {"type": "remote"},  # missing url
                "not-a-dict",
            ]
        }
        assert build_sources(env, "/tmp/c.json") == []

    def test_empty_envelope_yields_no_sources(self) -> None:
        assert build_sources({}, "/tmp/c.json") == []


# ---------------------------------------------------------------------------
# aggregate_from_sources
# ---------------------------------------------------------------------------


class TestAggregateFromSources:
    def test_single_local_matches_direct_read(self, config_with_bundles: Path) -> None:
        envelope = json.loads(config_with_bundles.read_text())
        result = aggregate_from_sources(envelope, config_with_bundles)

        assert result["app_config_version"] == 2.0
        assert result["supported"]["active"] is True
        assert result["newcomers"]["active"] is True
        assert result["deprecated"]["active"] is False
        assert {e["name"] for e in result["supported"]["entries"]} == {
            "ALPHA",
            "BETA",
        }
        assert [e["name"] for e in result["newcomers"]["entries"]] == ["GAMMA"]
        assert [e["name"] for e in result["deprecated"]["entries"]] == ["OMEGA"]
        # catalog_sources preserved for API exposure
        assert "catalog_sources" in result

    def test_skips_disabled_sources(self, config_with_bundles: Path) -> None:
        envelope = json.loads(config_with_bundles.read_text())
        envelope["catalog_sources"][0]["enabled"] = False
        result = aggregate_from_sources(envelope, config_with_bundles)
        assert result["supported"]["entries"] == []
        assert result["newcomers"]["entries"] == []
        assert result["deprecated"]["entries"] == []

    def test_first_source_wins_on_duplicate(
        self, tmp_path: Path, config_with_bundles: Path
    ) -> None:
        # Build a second local catalog that also declares ALPHA with a
        # different image; the first (config_with_bundles) should win.
        alt_catalog = tmp_path / "alt_catalog"
        (alt_catalog / "supported").mkdir(parents=True)
        (alt_catalog / "newcomers").mkdir()
        (alt_catalog / "deprecated").mkdir()
        (alt_catalog / "supported" / "ALPHA.json").write_text(
            json.dumps({"name": "ALPHA", "app_details": {"docker": "override/alpha"}})
        )
        (alt_catalog / "supported" / "DELTA.json").write_text(
            json.dumps({"name": "DELTA", "app_details": {"docker": "delta/delta"}})
        )

        envelope = json.loads(config_with_bundles.read_text())
        envelope["catalog_sources"].append(
            {
                "type": "local",
                "path": str(alt_catalog),
                "default_source": "community",
                "enabled": True,
            }
        )
        result = aggregate_from_sources(envelope, config_with_bundles)
        names = [e["name"] for e in result["supported"]["entries"]]
        # ALPHA comes from primary source; DELTA appended from secondary
        assert names == ["ALPHA", "BETA", "DELTA"]
        alpha = next(e for e in result["supported"]["entries"] if e["name"] == "ALPHA")
        assert alpha["app_details"]["docker"] == "alpha/alpha"

    def test_source_load_failure_is_isolated(
        self, config_with_bundles: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(self, config_path):  # type: ignore[no-untyped-def]
            raise RuntimeError("kaboom")

        monkeypatch.setattr(LocalSource, "load", boom)
        envelope = json.loads(config_with_bundles.read_text())
        # Should not raise — just log and return empty categories.
        result = aggregate_from_sources(envelope, config_with_bundles)
        assert result["supported"]["entries"] == []

    def test_remote_stub_contributes_nothing(self, config_with_bundles: Path) -> None:
        envelope = json.loads(config_with_bundles.read_text())
        envelope["catalog_sources"].append(
            {
                "type": "remote",
                "url": "https://example/catalog",
                "default_source": "community",
                "enabled": True,
            }
        )
        result = aggregate_from_sources(envelope, config_with_bundles)
        # Remote stub is never available → identical to local-only.
        assert {e["name"] for e in result["supported"]["entries"]} == {
            "ALPHA",
            "BETA",
        }


# ---------------------------------------------------------------------------
# Loader integration
# ---------------------------------------------------------------------------


class TestLoaderIntegration:
    def test_loader_uses_source_aggregation(self, config_with_bundles: Path) -> None:
        from money4band.core.loader import load_app_config_with_overlays

        config = load_app_config_with_overlays(str(config_with_bundles))
        assert {e["name"] for e in config["supported"]["entries"]} == {
            "ALPHA",
            "BETA",
        }
        assert config["supported"]["active"] is True
        assert config["newcomers"]["active"] is True


class TestAbstractBase:
    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            CatalogSource(name="x", default_source="builtin")  # type: ignore[abstract]
