"""Tests for utils.dashboard_api — FastAPI dashboard backend."""

from __future__ import annotations

import json
from unittest import mock

import pytest

from money4band.dashboard_api import _ALLOWED_ACTIONS, app, configure


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    return TestClient(app)


class TestDashboardAPI:
    def test_get_status(self, client):
        docker_output = "container1\tUp 2 hours\trunning\t0.0.0.0:8080->80/tcp"
        with mock.patch("money4band.dashboard_api._run_docker") as m:
            m.return_value = mock.Mock(returncode=0, stdout=docker_output)
            resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "container1"
        assert data[0]["state"] == "running"

    def test_get_status_docker_error(self, client):
        with mock.patch("money4band.dashboard_api._run_docker") as m:
            m.return_value = mock.Mock(returncode=1, stdout="")
            resp = client.get("/api/status")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_health(self, client):
        ps_out = "abc123\ndef456"
        inspect_out = (
            '{"name":"/c1","running":true,"health":"healthy","restarts":0}\n'
            '{"name":"/c2","running":false,"health":"none","restarts":3}'
        )
        with mock.patch("money4band.dashboard_api._run_docker") as m:
            m.side_effect = [
                mock.Mock(returncode=0, stdout=ps_out),
                mock.Mock(returncode=0, stdout=inspect_out),
            ]
            resp = client.get("/api/health")
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "c1"  # leading / stripped
        assert data[0]["running"] is True

    def test_get_stats(self, client):
        docker_output = "container1\t5.23%\t50MiB / 512MiB\t9.77%"
        with mock.patch("money4band.dashboard_api._run_docker") as m:
            m.return_value = mock.Mock(returncode=0, stdout=docker_output)
            resp = client.get("/api/stats")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["cpu_percent"] == "5.23%"

    def test_container_action_start(self, client):
        with mock.patch("money4band.dashboard_api._run_docker") as m:
            m.return_value = mock.Mock(returncode=0)
            resp = client.post("/api/action/my_container/start")
        assert resp.status_code == 200
        assert resp.json()["action"] == "start"

    def test_container_action_invalid(self, client):
        resp = client.post("/api/action/my_container/delete")
        assert resp.status_code == 400

    def test_container_action_bad_name(self, client):
        resp = client.post("/api/action/; rm -rf /start")
        assert resp.status_code in (400, 404, 422)

    def test_get_app_config(self, client, tmp_path):
        config = {
            "app_config_version": 1.2,
            "supported-apps": {"active": True, "entries": []},
        }
        config_file = tmp_path / "app-config.json"
        config_file.write_text(json.dumps(config))
        configure(str(tmp_path))
        resp = client.get("/api/config")
        assert resp.status_code == 200
        assert resp.json()["app_config_version"] == 1.2

    def test_get_app_config_missing(self, client, tmp_path):
        configure(str(tmp_path / "nonexistent"))
        resp = client.get("/api/config")
        assert resp.status_code == 404

    def test_allowed_actions(self):
        assert _ALLOWED_ACTIONS == {"start", "stop", "restart"}
