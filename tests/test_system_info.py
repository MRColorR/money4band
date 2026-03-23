"""Tests for system info DNS helpers and dashboard in system_info.py."""

import unittest
from unittest.mock import patch

from money4band.system_info import get_dns_config, set_dns_mode


class TestSystemInfoDNS(unittest.TestCase):
    def test_get_dns_config_present(self):
        cfg = {"system": {"dns": {"mode": "custom", "servers": ["8.8.8.8"]}}}
        result = get_dns_config(cfg)
        self.assertEqual(result["mode"], "custom")
        self.assertEqual(result["servers"], ["8.8.8.8"])

    def test_get_dns_config_missing(self):
        result = get_dns_config({})
        self.assertEqual(result["mode"], "default")

    @patch("money4band.system_info.write_json")
    @patch(
        "money4band.system_info.load_json_config",
        return_value={"system": {"dns": {"mode": "default", "servers": ["1.1.1.1"]}}},
    )
    def test_set_dns_mode_custom(self, _load, mock_write):
        set_dns_mode("/fake/path.json", "custom", ["8.8.8.8", "8.8.4.4"])
        written = mock_write.call_args[0][0]
        self.assertEqual(written["system"]["dns"]["mode"], "custom")
        self.assertEqual(written["system"]["dns"]["servers"], ["8.8.8.8", "8.8.4.4"])

    @patch("money4band.system_info.write_json")
    @patch(
        "money4band.system_info.load_json_config",
        return_value={"system": {"dns": {"mode": "custom", "servers": ["8.8.8.8"]}}},
    )
    def test_set_dns_mode_default_preserves_servers(self, _load, mock_write):
        set_dns_mode("/fake/path.json", "default")
        written = mock_write.call_args[0][0]
        self.assertEqual(written["system"]["dns"]["mode"], "default")
        # servers key should still be present (not deleted)
        self.assertIn("servers", written["system"]["dns"])

    def test_set_dns_mode_invalid(self):
        with self.assertRaises(ValueError):
            set_dns_mode("/fake/path.json", "invalid_mode")


class TestShowSystemInfo(unittest.TestCase):
    """Verify the system info dashboard prints Docker running status."""

    @patch("money4band.compose_builder.get_compose_files", return_value=[])
    @patch("money4band.system_info.detector")
    @patch("money4band.system_info.check_for_update", return_value=None)
    @patch("money4band.system_info.shutil")
    @patch("money4band.helper.is_docker_daemon_running", return_value=True)
    def test_docker_running_shown_when_installed(
        self, _daemon, mock_shutil, _upd, mock_detector, _compose
    ):
        """When Docker is installed, 'Docker running:' line must appear."""
        from io import StringIO
        from contextlib import redirect_stdout

        mock_shutil.which.return_value = "/usr/bin/docker"
        mock_detector.get_active_profile.return_value = "low"
        mock_detector.get_profile_definition.return_value = {"description": "Default"}
        mock_detector.get_system_memory_and_cores.return_value = (8192, 4)

        m4b = {"project": {"project_version": "5.0.0"}, "system": {}}
        app = {}
        user = {"device_info": {"os_type": "Linux", "detected_architecture": "amd64",
                                "detected_docker_arch": "amd64"}, "apps": {}}

        buf = StringIO()
        with redirect_stdout(buf):
            from money4band.system_info import show_system_info
            show_system_info(m4b, app, user)

        output = buf.getvalue()
        self.assertIn("Docker installed:", output)
        self.assertIn("Docker running:", output)

    @patch("money4band.compose_builder.get_compose_files", return_value=[])
    @patch("money4band.system_info.detector")
    @patch("money4band.system_info.check_for_update", return_value=None)
    @patch("money4band.system_info.shutil")
    def test_docker_running_not_shown_when_not_installed(
        self, mock_shutil, _upd, mock_detector, _compose
    ):
        """When Docker is NOT installed, 'Docker running:' line must NOT appear."""
        from io import StringIO
        from contextlib import redirect_stdout

        mock_shutil.which.return_value = None
        mock_detector.get_active_profile.return_value = "low"
        mock_detector.get_profile_definition.return_value = {"description": "Default"}
        mock_detector.get_system_memory_and_cores.return_value = (8192, 4)

        m4b = {"project": {"project_version": "5.0.0"}, "system": {}}
        app = {}
        user = {"device_info": {"os_type": "Linux", "detected_architecture": "amd64",
                                "detected_docker_arch": "amd64"}, "apps": {}}

        buf = StringIO()
        with redirect_stdout(buf):
            from money4band.system_info import show_system_info
            show_system_info(m4b, app, user)

        output = buf.getvalue()
        self.assertIn("Docker installed:", output)
        self.assertNotIn("Docker running:", output)


if __name__ == "__main__":
    unittest.main()
