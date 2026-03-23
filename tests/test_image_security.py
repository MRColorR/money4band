"""Tests for image_security module: stale checks, digest logging, CVE scan."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from money4band.image_security import (
    _get_image_names,
    check_stale_images,
    log_image_digests,
)


_SAMPLE_CONFIG = {
    "supported-apps": {
        "active": True,
        "entries": [
            {
                "name": "EARNAPP",
                "compose_config": {"image": "fazalfarhan01/earnapp:lite"},
                "app_details": {
                    "docker": {"last_update": "2023-06"},
                },
            },
            {
                "name": "HONEYGAIN",
                "compose_config": {"image": "honeygain/honeygain:latest"},
                "app_details": {
                    "docker": {"last_update": "2026-03"},
                },
            },
        ],
    },
    "deprecated-apps": {
        "active": False,
        "entries": [
            {
                "name": "GRASS",
                "compose_config": {"image": "ghcr.io/xterna/grass-node"},
                "app_details": {
                    "docker": {"last_update": "2024-01"},
                },
            },
        ],
    },
    "candidate-apps": {
        "active": False,
        "entries": [
            {
                "name": "SPIDE",
                "compose_config": {},
                "app_details": {},
            },
        ],
    },
}


class TestGetImageNames:
    def test_returns_apps_with_images(self):
        pairs = _get_image_names(_SAMPLE_CONFIG)
        names = [p[0] for p in pairs]
        assert "EARNAPP" in names
        assert "HONEYGAIN" in names
        assert "GRASS" in names

    def test_skips_apps_without_images(self):
        pairs = _get_image_names(_SAMPLE_CONFIG)
        names = [p[0] for p in pairs]
        assert "SPIDE" not in names


class TestCheckStaleImages:
    def test_finds_stale_images(self):
        stale = check_stale_images(_SAMPLE_CONFIG)
        stale_names = [s["app"] for s in stale]
        assert "EARNAPP" in stale_names  # 2023-06 is very old
        assert "GRASS" in stale_names  # 2024-01 is old

    def test_fresh_images_not_flagged(self):
        stale = check_stale_images(_SAMPLE_CONFIG)
        stale_names = [s["app"] for s in stale]
        assert "HONEYGAIN" not in stale_names  # 2026-03 is recent

    def test_returns_days_old(self):
        stale = check_stale_images(_SAMPLE_CONFIG)
        for s in stale:
            assert "days_old" in s
            assert s["days_old"] > 90


class TestLogImageDigests:
    @patch("money4band.image_security._docker_inspect_image")
    def test_returns_digests(self, mock_inspect):
        mock_inspect.return_value = {
            "RepoDigests": ["honeygain/honeygain@sha256:abc123def456"],
        }
        digests = log_image_digests(_SAMPLE_CONFIG)
        assert len(digests) > 0
        assert any(d["digest"].startswith("honeygain/") for d in digests)

    @patch("money4band.image_security._docker_inspect_image")
    def test_handles_missing_image(self, mock_inspect):
        mock_inspect.return_value = None
        digests = log_image_digests(_SAMPLE_CONFIG)
        assert digests == []

    @patch("money4band.image_security._docker_inspect_image")
    def test_handles_no_repo_digests(self, mock_inspect):
        mock_inspect.return_value = {"RepoDigests": []}
        digests = log_image_digests(_SAMPLE_CONFIG)
        for d in digests:
            assert d["digest"] == "none"
