"""Tests for scripts/compute_weights.py — contributor weights."""

from __future__ import annotations

import importlib.util
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


def _ts(days_ago: float, *, base: datetime | None = None) -> int:
    base = base or datetime(2026, 4, 24, tzinfo=timezone.utc)
    return int((base - timedelta(days=days_ago)).timestamp())


class TestComputeWeights:
    def test_no_commits_returns_empty(self) -> None:
        assert cw.compute_weights([]) == {}

    def test_young_commits_dropped(self) -> None:
        # Commit 3 days ago is below the 7-day age floor.
        commits = [Commit(author="alice", ts=_ts(3), value=5.0)]
        out = cw.compute_weights(
            commits, now=datetime(2026, 4, 24, tzinfo=timezone.utc)
        )
        assert out == {}

    def test_single_mature_commit_applies_decay_and_floor(self) -> None:
        now = datetime(2026, 4, 24, tzinfo=timezone.utc)
        commits = [Commit(author="alice", ts=_ts(180, base=now), value=10.0)]
        out = cw.compute_weights(commits, now=now)
        # value 10 -> clamped to daily cap 8, decayed exactly one half-life.
        assert math.isclose(out["alice"], 4.0, rel_tol=1e-3)

    def test_commit_cap_enforced_in_pipeline(self) -> None:
        # _Commit.value is already capped at PER_COMMIT_CAP=10 by
        # read_git_commits, so a pathological raw=25 should still only
        # contribute up to 10 when the daily cap permits.
        now = datetime(2026, 4, 24, tzinfo=timezone.utc)
        # Simulate read_git_commits capping: value is 10, not 25.
        commits = [Commit(author="alice", ts=_ts(10, base=now), value=10.0)]
        out = cw.compute_weights(commits, now=now)
        # Capped by daily cap (8.0), decayed over 10 days: 8 * exp(-ln2 * 10/180)
        expected = 8.0 * math.exp(-math.log(2) * 10 / 180)
        assert math.isclose(out["alice"], round(expected, 4), abs_tol=1e-3)

    def test_daily_cap_clamps_same_day_commits(self) -> None:
        now = datetime(2026, 4, 24, tzinfo=timezone.utc)
        # Three 10-point commits in the same UTC day -> capped at 8.0 total.
        ts = _ts(30, base=now)
        commits = [
            Commit(author="alice", ts=ts, value=10.0),
            Commit(author="alice", ts=ts, value=10.0),
            Commit(author="alice", ts=ts, value=10.0),
        ]
        out = cw.compute_weights(commits, now=now)
        decay = math.exp(-math.log(2) * 30 / 180)
        expected = round(8.0 * decay, 4)
        assert math.isclose(out["alice"], expected, abs_tol=1e-3)

    def test_daily_cap_per_author_not_global(self) -> None:
        now = datetime(2026, 4, 24, tzinfo=timezone.utc)
        ts = _ts(30, base=now)
        commits = [
            Commit(author="alice", ts=ts, value=10.0),
            Commit(author="bob", ts=ts, value=10.0),
        ]
        out = cw.compute_weights(commits, now=now)
        assert set(out.keys()) == {"alice", "bob"}
        # Each author hits daily cap independently.
        assert math.isclose(out["alice"], out["bob"], abs_tol=1e-6)

    def test_weight_floor_applied(self) -> None:
        # A very old, tiny commit decays essentially to 0 but must floor.
        now = datetime(2026, 4, 24, tzinfo=timezone.utc)
        commits = [Commit(author="alice", ts=_ts(10000, base=now), value=0.001)]
        out = cw.compute_weights(commits, now=now)
        assert out["alice"] == cw.WEIGHT_FLOOR

    def test_output_ordered_descending(self) -> None:
        now = datetime(2026, 4, 24, tzinfo=timezone.utc)
        ts = _ts(30, base=now)
        commits = [
            Commit(author="bob", ts=ts, value=1.0),
            Commit(author="alice", ts=ts, value=5.0),
            Commit(author="carol", ts=ts, value=3.0),
        ]
        out = cw.compute_weights(commits, now=now)
        ordered = list(out.keys())
        assert ordered == ["alice", "carol", "bob"]

    def test_multiple_days_sum(self) -> None:
        now = datetime(2026, 4, 24, tzinfo=timezone.utc)
        commits = [
            Commit(author="alice", ts=_ts(30, base=now), value=8.0),
            Commit(author="alice", ts=_ts(60, base=now), value=8.0),
        ]
        out = cw.compute_weights(commits, now=now)
        expected = 8.0 * math.exp(-math.log(2) * 30 / 180) + 8.0 * math.exp(
            -math.log(2) * 60 / 180
        )
        assert math.isclose(out["alice"], round(expected, 4), abs_tol=1e-3)


class TestReadGitCommits:
    def test_happy_path_parses_commits(self, tmp_path: Path, monkeypatch) -> None:
        fake_output = (
            "@COMMIT@abc|1700000000|alice\n"
            "5\t2\tpath/one.py\n"
            "10\t0\tpath/two.py\n"
            "@COMMIT@def|1700100000|bob\n"
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
