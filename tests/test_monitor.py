"""Tests for monitor module: container health and restart detection."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from money4band.docker.monitor import (
    HealthStatus,
    check_container_health,
    detect_restart_loops,
    get_stack_health,
)


class TestHealthStatus:
    def test_ok_when_running_and_healthy(self):
        s = HealthStatus(name="test", running=True, health="healthy")
        assert s.ok is True

    def test_ok_when_running_no_healthcheck(self):
        s = HealthStatus(name="test", running=True, health="none")
        assert s.ok is True

    def test_not_ok_when_unhealthy(self):
        s = HealthStatus(name="test", running=True, health="unhealthy")
        assert s.ok is False

    def test_not_ok_when_not_running(self):
        s = HealthStatus(name="test", running=False, health="healthy")
        assert s.ok is False

    def test_defaults(self):
        s = HealthStatus(name="x")
        assert s.running is False
        assert s.health == "unknown"
        assert s.restart_count == 0


class TestCheckContainerHealth:
    def _mock_inspect(self, data):
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps(data)
        return result

    @patch("money4band.docker.monitor.subprocess.run")
    def test_returns_unknown_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        status = check_container_health("mycontainer")
        assert status.name == "mycontainer"
        assert status.running is False
        assert status.health == "unknown"

    @patch("money4band.docker.monitor.subprocess.run")
    def test_parses_healthy_container(self, mock_run):
        mock_run.return_value = self._mock_inspect(
            {
                "State": {
                    "Running": True,
                    "StartedAt": "2026-03-20T10:00:00Z",
                    "Health": {"Status": "healthy", "Log": []},
                },
                "RestartCount": 0,
                "Config": {"Image": "myimage:latest"},
            }
        )
        status = check_container_health("test")
        assert status.running is True
        assert status.health == "healthy"
        assert status.restart_count == 0
        assert status.image == "myimage:latest"
        assert status.ok is True

    @patch("money4band.docker.monitor.subprocess.run")
    def test_parses_unhealthy_with_error(self, mock_run):
        mock_run.return_value = self._mock_inspect(
            {
                "State": {
                    "Running": True,
                    "Health": {
                        "Status": "unhealthy",
                        "Log": [{"ExitCode": 1, "Output": "connection refused"}],
                    },
                },
                "RestartCount": 3,
                "Config": {"Image": "img"},
            }
        )
        status = check_container_health("test")
        assert status.health == "unhealthy"
        assert status.last_error == "connection refused"
        assert status.restart_count == 3

    @patch("money4band.docker.monitor.subprocess.run")
    def test_oom_killed(self, mock_run):
        mock_run.return_value = self._mock_inspect(
            {
                "State": {"Running": False, "OOMKilled": True},
                "RestartCount": 1,
                "Config": {"Image": "img"},
            }
        )
        status = check_container_health("test")
        assert status.last_error == "OOMKilled"

    @patch("money4band.docker.monitor.subprocess.run")
    def test_no_healthcheck(self, mock_run):
        mock_run.return_value = self._mock_inspect(
            {
                "State": {"Running": True},
                "RestartCount": 0,
                "Config": {"Image": "img"},
            }
        )
        status = check_container_health("test")
        assert status.health == "none"
        assert status.ok is True


class TestDetectRestartLoops:
    @patch("money4band.docker.monitor.check_container_health")
    def test_detects_loop(self, mock_health):
        mock_health.return_value = HealthStatus(name="x", restart_count=7)
        assert detect_restart_loops("x", threshold=5) is True

    @patch("money4band.docker.monitor.check_container_health")
    def test_no_loop(self, mock_health):
        mock_health.return_value = HealthStatus(name="x", restart_count=2)
        assert detect_restart_loops("x", threshold=5) is False

    @patch("money4band.docker.monitor.check_container_health")
    def test_exact_threshold(self, mock_health):
        mock_health.return_value = HealthStatus(name="x", restart_count=5)
        assert detect_restart_loops("x", threshold=5) is True


class TestGetStackHealth:
    @patch("money4band.docker.monitor.check_container_health")
    @patch("money4band.docker.monitor._docker_ps_names")
    def test_returns_list(self, mock_names, mock_health):
        mock_names.return_value = ["a", "b"]
        mock_health.side_effect = [
            HealthStatus(name="a", running=True, health="healthy"),
            HealthStatus(name="b", running=True, health="none"),
        ]
        result = get_stack_health()
        assert len(result) == 2
        assert result[0].name == "a"
        assert result[1].name == "b"

    @patch("money4band.docker.monitor._docker_ps_names")
    def test_empty_when_no_containers(self, mock_names):
        mock_names.return_value = []
        assert get_stack_health() == []
