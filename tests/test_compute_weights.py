"""Tests for scripts/compute_weights.py — contributor weights."""

from __future__ import annotations

import importlib.util
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "_compute_weights",
    HERE.parent / "scripts" / "compute_weights.py",
)
assert _SPEC is not None and _SPEC.loader is not None
cw = importlib.util.module_from_spec(_SPEC)
sys.modules["_compute_weights"] = cw
_SPEC.loader.exec_module(cw)

Commit = cw._Commit

# A fixed reference point used by tests; the algorithm itself is
# anchored to ``max(c.ts)`` so this is only the *latest* commit ts.
REF = datetime(2026, 4, 24, tzinfo=timezone.utc)


def _ts(days_before_ref: float, *, base: datetime | None = None) -> int:
    base = base or REF
    return int((base - timedelta(days=days_before_ref)).timestamp())


def _anchor() -> Commit:
    """Latest-commit anchor at REF. Inside cooldown -> never weighted."""
    return Commit(author="__anchor__", ts=int(REF.timestamp()), value=0.0)


@pytest.fixture(autouse=True)
def _algo_threshold(monkeypatch):
    """Test the algorithm math regardless of the prod ``MIN_WEIGHT``."""
    monkeypatch.setattr(cw, "MIN_WEIGHT", 0.0)


class TestComputeWeights:
    def test_no_commits_returns_empty(self) -> None:
        assert cw.compute_weights([]) == {}

    def test_commits_inside_cooldown_dropped(self) -> None:
        # Only commits within AGE_FLOOR_DAYS of the latest commit ->
        # in_window is empty -> {}.
        commits = [
            Commit(author="alice", ts=_ts(0), value=5.0),
            Commit(author="alice", ts=_ts(3), value=5.0),
        ]
        assert cw.compute_weights(commits) == {}

    def test_commits_older_than_window_dropped(self) -> None:
        # Anchor at REF, alice's commit is 400 days before -> outside
        # the 365-day window -> dropped -> {}.
        commits = [
            _anchor(),
            Commit(author="alice", ts=_ts(400), value=10.0),
        ]
        assert cw.compute_weights(commits) == {}

    def test_single_mature_commit_decays_from_reference(self) -> None:
        # alice's commit is exactly one half-life before the anchor.
        commits = [
            _anchor(),
            Commit(author="alice", ts=_ts(180), value=10.0),
        ]
        out = cw.compute_weights(commits)
        # value 10 -> clamped to daily cap 8, decayed one half-life.
        assert math.isclose(out["alice"], 4.0, rel_tol=1e-3)

    def test_daily_cap_clamps_same_day_commits(self) -> None:
        ts = _ts(30)
        commits = [
            _anchor(),
            Commit(author="alice", ts=ts, value=10.0),
            Commit(author="alice", ts=ts, value=10.0),
            Commit(author="alice", ts=ts, value=10.0),
        ]
        out = cw.compute_weights(commits)
        decay = math.exp(-math.log(2) * 30 / 180)
        expected = round(8.0 * decay, 4)
        assert math.isclose(out["alice"], expected, abs_tol=1e-3)

    def test_daily_cap_per_author_not_global(self) -> None:
        ts = _ts(30)
        commits = [
            _anchor(),
            Commit(author="alice", ts=ts, value=10.0),
            Commit(author="bob", ts=ts, value=10.0),
        ]
        out = cw.compute_weights(commits)
        assert set(out.keys()) == {"alice", "bob"}
        assert math.isclose(out["alice"], out["bob"], abs_tol=1e-6)

    def test_min_weight_drops_trivial_contributors(self, monkeypatch) -> None:
        monkeypatch.setattr(cw, "MIN_WEIGHT", 1.0)
        # alice's contribution decays well below 1.0 -> dropped.
        commits = [
            _anchor(),
            Commit(author="alice", ts=_ts(300), value=0.5),
        ]
        assert "alice" not in cw.compute_weights(commits)

    def test_output_ordered_descending(self) -> None:
        ts = _ts(30)
        commits = [
            _anchor(),
            Commit(author="bob", ts=ts, value=1.0),
            Commit(author="alice", ts=ts, value=5.0),
            Commit(author="carol", ts=ts, value=3.0),
        ]
        out = cw.compute_weights(commits)
        assert list(out.keys()) == ["alice", "carol", "bob"]

    def test_multiple_days_sum(self) -> None:
        commits = [
            _anchor(),
            Commit(author="alice", ts=_ts(30), value=8.0),
            Commit(author="alice", ts=_ts(60), value=8.0),
        ]
        out = cw.compute_weights(commits)
        expected = 8.0 * math.exp(-math.log(2) * 30 / 180) + 8.0 * math.exp(
            -math.log(2) * 60 / 180
        )
        assert math.isclose(out["alice"], round(expected, 4), abs_tol=1e-3)

    def test_window_anchored_to_latest_commit_not_wall_clock(self) -> None:
        # All commits are years before "now" but cluster tightly around
        # their own latest. Anchored to that latest, alice survives.
        base = datetime(2020, 1, 1, tzinfo=timezone.utc)
        commits = [
            Commit(author="alice", ts=_ts(0, base=base), value=8.0),
            Commit(author="alice", ts=_ts(30, base=base), value=8.0),
            Commit(author="alice", ts=_ts(60, base=base), value=8.0),
        ]
        out = cw.compute_weights(commits)
        # Latest commit (age 0) is in cooldown so it doesn't contribute,
        # but the 30d + 60d ones do, decayed from that latest.
        assert "alice" in out
        assert out["alice"] > cw.MIN_WEIGHT


class TestReadGitCommits:
    def test_happy_path_parses_commits(self, tmp_path: Path, monkeypatch) -> None:
        fake_output = (
            "@COMMIT@abc|1700000000|alice|alice@example.com\n"
            "5\t2\tpath/one.py\n"
            "10\t0\tpath/two.py\n"
            "@COMMIT@def|1700100000|bob|bob@example.com\n"
            "-\t-\tbinary.png\n"
            "3\t1\tpath/three.py\n"
        )

        def fake_run(cmd, **kwargs):  # noqa: ARG001
            class R:
                stdout = fake_output
                returncode = 0
                stderr = ""

            return R()

        monkeypatch.setattr(cw.subprocess, "run", fake_run)
        out = cw.read_git_commits(tmp_path)
        assert len(out) == 2
        # alice: 15 insertions + 2 deletions*0.5 = 16 -> capped to 10
        assert out[0].author == "alice"
        assert out[0].value == 10.0
        # bob: 3 + 0.5 = 3.5, binary ignored
        assert out[1].author == "bob"
        assert math.isclose(out[1].value, 3.5)
