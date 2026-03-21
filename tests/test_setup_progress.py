"""Tests for setup_progress module."""

import json
import os

import pytest

from utils.setup_progress import (
    clear_progress,
    is_step_done,
    load_progress,
    save_progress,
)


@pytest.fixture(autouse=True)
def _isolate_progress_file(tmp_path, monkeypatch):
    """Point the progress file at a temp directory so tests don't touch real config."""
    progress_file = str(tmp_path / ".setup_progress.json")
    monkeypatch.setattr("utils.setup_progress.PROGRESS_FILE", progress_file)
    yield progress_file


def test_load_progress_returns_empty_when_no_file(_isolate_progress_file):
    assert load_progress() == {}


def test_save_and_load_roundtrip(_isolate_progress_file):
    save_progress([1, 3, 5])
    data = load_progress()
    assert data["completed_steps"] == [1, 3, 5]


def test_save_deduplicates_and_sorts(_isolate_progress_file):
    save_progress([3, 1, 3, 5, 1])
    data = load_progress()
    assert data["completed_steps"] == [1, 3, 5]


def test_clear_progress_removes_file(_isolate_progress_file):
    save_progress([1])
    assert os.path.isfile(_isolate_progress_file)
    clear_progress()
    assert not os.path.isfile(_isolate_progress_file)


def test_clear_progress_noop_when_no_file(_isolate_progress_file):
    # Should not raise
    clear_progress()


def test_is_step_done_true():
    progress = {"completed_steps": [1, 2, 3]}
    assert is_step_done(progress, 2) is True


def test_is_step_done_false():
    progress = {"completed_steps": [1, 3]}
    assert is_step_done(progress, 2) is False


def test_is_step_done_empty_progress():
    assert is_step_done({}, 1) is False


def test_load_progress_handles_corrupt_file(_isolate_progress_file):
    with open(_isolate_progress_file, "w") as f:
        f.write("not valid json {{{")
    assert load_progress() == {}
