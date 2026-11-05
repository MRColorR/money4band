"""Tests for money4band.apps.contributor_pool - weighted picker."""

from __future__ import annotations

import json
import random
from pathlib import Path

from money4band.apps.contributor_pool import (
    load_weights,
    pick_weighted,
    resolve_referral_url,
    weight_for,
)


class TestLoadWeights:
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert load_weights(tmp_path / "nope.json") == {}

    def test_malformed_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "weights.json"
        p.write_text("{not json", encoding="utf-8")
        assert load_weights(p) == {}

    def test_non_object_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "weights.json"
        p.write_text("[1, 2, 3]", encoding="utf-8")
        assert load_weights(p) == {}

    def test_coerces_numeric_strings(self, tmp_path: Path) -> None:
        p = tmp_path / "weights.json"
        p.write_text(json.dumps({"alice": "2.5", "bob": 4, "carol": "bad"}))
        assert load_weights(p) == {"alice": 2.5, "bob": 4.0}

    def test_drops_negatives(self, tmp_path: Path) -> None:
        p = tmp_path / "weights.json"
        p.write_text(json.dumps({"alice": -1.0, "bob": 3.0}))
        assert load_weights(p) == {"bob": 3.0}


class TestWeightFor:
    def test_known_contributor(self) -> None:
        assert weight_for("alice", {"alice": 4.0, "bob": 1.0}) == 4.0

    def test_unknown_contributor_returns_zero(self) -> None:
        assert weight_for("dave", {"alice": 4.0}) == 0.0

    def test_empty_name_returns_zero(self) -> None:
        assert weight_for("", {"alice": 9.0}) == 0.0

    def test_explicit_zero_stays_zero(self) -> None:
        # Hand-edited 0.0 in weights.json means "never pick" - honored.
        assert weight_for("alice", {"alice": 0.0}) == 0.0

    def test_case_insensitive_lookup(self) -> None:
        # Catalog entries use display-case names like "MRColorr"; the
        # weights.json artifact is all-lowercase. They must resolve
        # to the same bucket.
        assert weight_for("MRColorr", {"mrcolorr": 5.0}) == 5.0
        assert weight_for("  Mr  Colorr ", {"mr colorr": 3.0}) == 3.0

    def test_load_weights_normalizes_keys(self, tmp_path: Path) -> None:
        from money4band.apps.contributor_pool import load_weights

        p = tmp_path / "weights.json"
        p.write_text(json.dumps({"MRColorr": 4.2, "Bob": 1.0}))
        loaded = load_weights(p)
        assert loaded == {"mrcolorr": 4.2, "bob": 1.0}


class TestPickWeighted:
    def test_empty_pool_returns_none(self) -> None:
        assert pick_weighted([]) is None

    def test_only_malformed_entries_returns_none(self) -> None:
        pool = [{}, {"url": ""}, {"url": None}, "string", 42]  # type: ignore[list-item]
        assert pick_weighted(pool) is None  # type: ignore[arg-type]

    def test_single_entry_always_chosen(self) -> None:
        pool = [{"url": "https://a", "contributor": "alice"}]
        assert pick_weighted(pool, {"alice": 1.0}, rng=random.Random(0)) == pool[0]

    def test_deterministic_with_seeded_rng(self) -> None:
        pool = [
            {"url": "https://a", "contributor": "alice"},
            {"url": "https://b", "contributor": "bob"},
        ]
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        weights = {"alice": 2.0, "bob": 1.0}
        assert pick_weighted(pool, weights, rng=rng1) == pick_weighted(
            pool, weights, rng=rng2
        )

    def test_weight_distribution_heavily_skews(self) -> None:
        pool = [
            {"url": "https://a", "contributor": "alice"},
            {"url": "https://b", "contributor": "bob"},
        ]
        weights = {"alice": 1000.0, "bob": 0.1}
        rng = random.Random(123)
        counts = {"https://a": 0, "https://b": 0}
        for _ in range(500):
            pick = pick_weighted(pool, weights, rng=rng)
            counts[pick["url"]] += 1
        # Alice should win vastly more than bob.
        assert counts["https://a"] > counts["https://b"] * 50

    def test_non_contributors_locked_out_when_contributor_present(self) -> None:
        # mrcolorr has weight, alice + bob do not -> mrcolorr always wins.
        pool = [
            {"url": "https://mr", "contributor": "mrcolorr"},
            {"url": "https://a", "contributor": "alice"},
            {"url": "https://b", "contributor": "bob"},
        ]
        weights = {"mrcolorr": 100.0}
        rng = random.Random(0)
        for _ in range(50):
            assert pick_weighted(pool, weights, rng=rng)["url"] == "https://mr"

    def test_all_non_contributors_falls_back_to_uniform(self) -> None:
        # No contributor in weights.json -> all weights 0 -> uniform pick.
        pool = [
            {"url": "https://a", "contributor": "x"},
            {"url": "https://b", "contributor": "y"},
        ]
        rng = random.Random(7)
        chosen = pick_weighted(pool, {}, rng=rng)
        assert chosen in pool


class TestResolveReferralUrl:
    def test_sticky_wins(self) -> None:
        pool = [{"url": "https://pool", "contributor": "alice"}]
        got = resolve_referral_url(
            "MyApp",
            pool,
            weights={"alice": 1.0},
            sticky={"myapp": "https://sticky"},
        )
        assert got == "https://sticky"

    def test_sticky_case_insensitive(self) -> None:
        pool = [{"url": "https://pool", "contributor": "alice"}]
        got = resolve_referral_url(
            "EarnApp",
            pool,
            sticky={"EarnApp": "https://mixed"},
        )
        assert got == "https://mixed"

    def test_falls_back_to_weighted_pick(self) -> None:
        pool = [{"url": "https://only", "contributor": "alice"}]
        got = resolve_referral_url(
            "X", pool, weights={"alice": 1.0}, rng=random.Random(0)
        )
        assert got == "https://only"

    def test_empty_pool_returns_empty_string(self) -> None:
        assert resolve_referral_url("X", [], weights={}, sticky={}) == ""

    def test_ignores_blank_sticky(self) -> None:
        pool = [{"url": "https://fallback", "contributor": "x"}]
        got = resolve_referral_url(
            "App", pool, sticky={"app": "   "}, rng=random.Random(0)
        )
        assert got == "https://fallback"
