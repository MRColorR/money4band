import unittest
from unittest.mock import patch

from utils.detector import detect_architecture, detect_os


class TestDetector(unittest.TestCase):
    @patch("utils.loader.load_json_config")
    @patch("platform.system", return_value="Linux")
    def test_detect_os(self, mock_platform_system, mock_load_json_config):
        """
        Test detecting the operating system type.
        """
        mock_load_json_config.return_value = {
            "system": {
                "os_map": {
                    "win32nt": "Windows",
                    "windows_nt": "Windows",
                    "windows": "Windows",
                    "linux": "Linux",
                    "darwin": "MacOS",
                    "macos": "MacOS",
                    "macosx": "MacOS",
                    "mac": "MacOS",
                    "osx": "MacOS",
                    "cygwin": "Cygwin",
                    "mingw": "MinGw",
                    "msys": "Msys",
                    "freebsd": "FreeBSD",
                }
            }
        }

        expected_os_type = "Linux"
        result = detect_os({"system": {"os_map": {"linux": "Linux"}}})
        self.assertEqual(result, {"os_type": expected_os_type})
        mock_platform_system.assert_called_once()

    @patch("utils.loader.load_json_config")
    @patch("platform.machine", return_value="x86_64")
    def test_detect_architecture(self, mock_platform_machine, mock_load_json_config):
        """
        Test detecting the system architecture.
        """
        mock_load_json_config.return_value = {
            "system": {
                "arch_map": {
                    "x86_64": "amd64",
                    "amd64": "amd64",
                    "aarch64": "arm64",
                    "arm64": "arm64",
                }
            }
        }

        expected_arch = "x86_64"
        expected_dkarch = "amd64"
        result = detect_architecture({"system": {"arch_map": {"x86_64": "amd64"}}})
        self.assertEqual(result, {"arch": expected_arch, "dkarch": expected_dkarch})
        mock_platform_machine.assert_called_once()


if __name__ == "__main__":
    unittest.main()
