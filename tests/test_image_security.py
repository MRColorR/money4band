"""Tests for image_security module: stale checks, digest logging, CVE scan."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from money4band.docker.image_security import (
    _docker_available,
    _get_image_names,
    _scout_available,
    check_stale_images,
    log_image_digests,
    run_scout_cves,
    validate_images,
)

_SAMPLE_CONFIG = {
    "supported": {
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
    "deprecated": {
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
    "newcomers": {
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
    @patch("money4band.docker.image_security._docker_inspect_image")
    def test_returns_digests(self, mock_inspect):
        mock_inspect.return_value = {
            "RepoDigests": ["honeygain/honeygain@sha256:abc123def456"],
        }
        digests = log_image_digests(_SAMPLE_CONFIG)
        assert len(digests) > 0
        assert any(d["digest"].startswith("honeygain/") for d in digests)

    @patch("money4band.docker.image_security._docker_inspect_image")
    def test_handles_missing_image(self, mock_inspect):
        mock_inspect.return_value = None
        digests = log_image_digests(_SAMPLE_CONFIG)
        assert digests == []

    @patch("money4band.docker.image_security._docker_inspect_image")
    def test_handles_no_repo_digests(self, mock_inspect):
        mock_inspect.return_value = {"RepoDigests": []}
        digests = log_image_digests(_SAMPLE_CONFIG)
        for d in digests:
            assert d["digest"] == "none"


class TestRunScoutCves:
    @patch("subprocess.run")
    def test_returns_output_on_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="2 critical vulnerabilities found"
        )
        result = run_scout_cves("nginx:alpine")
        assert "critical" in result

    @patch("subprocess.run")
    def test_returns_stderr_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="scout error")
        result = run_scout_cves("nginx:alpine")
        assert result == "scout error"

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_returns_none_on_missing_scout(self, _mock):
        assert run_scout_cves("nginx:alpine") is None


class TestDockerAvailable:
    @patch("subprocess.run")
    def test_available(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert _docker_available() is True

    @patch("subprocess.run")
    def test_not_available(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert _docker_available() is False

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_exception(self, _mock):
        assert _docker_available() is False


class TestScoutAvailable:
    @patch("subprocess.run")
    def test_available(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert _scout_available() is True

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_not_available(self, _mock):
        assert _scout_available() is False


class TestGetImageNamesSubServices:
    """Verify sub-service images are extracted alongside main images."""

    def test_sub_service_image_included(self):
        config = {
            "apps": {
                "active": True,
                "entries": [
                    {
                        "name": "MYAPP",
                        "compose_config": {"image": "myapp:latest"},
                        "service": {
                            "sidecar": {
                                "compose_config": {"image": "sidecar:v1"},
                            }
                        },
                    },
                ],
            },
        }
        pairs = _get_image_names(config)
        images = [p[1] for p in pairs]
        assert "myapp:latest" in images
        assert "sidecar:v1" in images

    def test_no_service_key_still_works(self):
        config = {
            "apps": {
                "active": True,
                "entries": [
                    {"name": "SIMPLE", "compose_config": {"image": "simple:1"}},
                ],
            },
        }
        pairs = _get_image_names(config)
        assert len(pairs) == 1
        assert pairs[0] == ("SIMPLE", "simple:1")


class TestDockerInspectImage:
    @patch("subprocess.run")
    def test_parses_json_output(self, mock_run):
        from money4band.docker.image_security import _docker_inspect_image

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"RepoDigests": ["nginx@sha256:abc"]}',
        )
        result = _docker_inspect_image("nginx:alpine")
        assert result is not None
        assert result["RepoDigests"] == ["nginx@sha256:abc"]

    @patch("subprocess.run")
    def test_returns_none_on_failure(self, mock_run):
        from money4band.docker.image_security import _docker_inspect_image

        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert _docker_inspect_image("missing:image") is None

    @patch("subprocess.run", side_effect=Exception("timeout"))
    def test_returns_none_on_exception(self, _mock):
        from money4band.docker.image_security import _docker_inspect_image

        assert _docker_inspect_image("bad:image") is None


class TestValidateImagesWithScout:
    """Cover validate_images with scout available — lines 164-193."""

    @patch("money4band.docker.image_security._scout_available", return_value=True)
    @patch("money4band.docker.image_security.run_scout_cves")
    @patch("money4band.docker.image_security._docker_inspect_image")
    @patch("money4band.docker.image_security._docker_available", return_value=True)
    def test_scout_scans_non_deprecated_images(
        self, _docker, mock_inspect, mock_scout, _scout_avail, capsys
    ):
        mock_inspect.return_value = {"RepoDigests": ["img@sha256:abc"]}
        mock_scout.return_value = "1 critical vulnerability found"

        validate_images(_SAMPLE_CONFIG, run_cves=True)
        captured = capsys.readouterr()
        assert "Scanning" in captured.out
        assert "critical" in captured.out.lower()

    @patch("money4band.docker.image_security._scout_available", return_value=False)
    @patch("money4band.docker.image_security._docker_inspect_image", return_value=None)
    @patch("money4band.docker.image_security._docker_available", return_value=True)
    def test_no_scout_prints_install_hint(self, _docker, _inspect, _scout, capsys):
        validate_images(_SAMPLE_CONFIG, run_cves=True)
        captured = capsys.readouterr()
        assert "Scout not available" in captured.out or "not available" in captured.out

    @patch("money4band.docker.image_security._docker_available", return_value=False)
    def test_no_docker_prints_error(self, _docker, capsys):
        validate_images(_SAMPLE_CONFIG)
        captured = capsys.readouterr()
        assert "not available" in captured.out.lower()


class TestValidateImages:
    @patch("money4band.docker.image_security._docker_available", return_value=False)
    def test_exits_early_without_docker(self, _mock, capsys):
        validate_images(_SAMPLE_CONFIG)
        captured = capsys.readouterr()
        assert "not available" in captured.out

    @patch("money4band.docker.image_security._scout_available", return_value=False)
    @patch("money4band.docker.image_security._docker_inspect_image", return_value=None)
    @patch("money4band.docker.image_security._docker_available", return_value=True)
    def test_runs_without_scout(self, _docker, _inspect, _scout, capsys):
        validate_images(_SAMPLE_CONFIG, run_cves=True)
        captured = capsys.readouterr()
        assert "Stale Image Check" in captured.out
        assert "Scout not available" in captured.out
