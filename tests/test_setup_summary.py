"""Tests for setup_summary module."""

import os

import pytest

from money4band.setup_summary import generate_setup_summary


@pytest.fixture(autouse=True)
def _isolate_summary_path(tmp_path, monkeypatch):
    """Redirect summary output to a temp directory."""
    summary_file = str(tmp_path / "setup-summary.txt")
    monkeypatch.setattr("money4band.setup_summary.SUMMARY_PATH", summary_file)
    return summary_file


def _minimal_user_config(enabled_apps=None):
    """Build a minimal user_config for testing."""
    apps = {}
    for name in enabled_apps or []:
        apps[name] = {"enabled": True, "email": "test@example.com"}
    # Add a disabled app
    apps["disabledapp"] = {"enabled": False}
    return {
        "device_info": {
            "device_name": "test-device",
            "os_type": "Linux",
            "detected_architecture": "amd64",
        },
        "apps": apps,
        "m4b_dashboard": {"enabled": True, "ports": [8081]},
        "watchtower": {"enabled": True},
        "notifications": {"enabled": False},
        "proxies": {"enabled": False, "url": ""},
    }


def test_summary_file_created(_isolate_summary_path):
    user_cfg = _minimal_user_config(["honeygain", "earnapp"])
    path = generate_setup_summary(user_cfg, {})
    assert path == _isolate_summary_path
    assert os.path.isfile(path)


def test_summary_contains_enabled_apps(_isolate_summary_path):
    user_cfg = _minimal_user_config(["honeygain", "earnapp"])
    generate_setup_summary(user_cfg, {})
    with open(_isolate_summary_path) as f:
        content = f.read()
    assert "earnapp" in content
    assert "honeygain" in content
    assert "Enabled Apps (2)" in content


def test_summary_contains_device_info(_isolate_summary_path):
    user_cfg = _minimal_user_config()
    generate_setup_summary(user_cfg, {})
    with open(_isolate_summary_path) as f:
        content = f.read()
    assert "test-device" in content
    assert "Linux" in content


def test_summary_shows_dashboard_url(_isolate_summary_path):
    user_cfg = _minimal_user_config()
    generate_setup_summary(user_cfg, {})
    with open(_isolate_summary_path) as f:
        content = f.read()
    assert "http://localhost:8081" in content


def test_summary_proxy_disabled(_isolate_summary_path):
    user_cfg = _minimal_user_config()
    generate_setup_summary(user_cfg, {})
    with open(_isolate_summary_path) as f:
        content = f.read()
    assert "Proxy: disabled" in content
