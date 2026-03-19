import unittest
from unittest.mock import patch

from utils.detector import detect_architecture, detect_os

# Shared arch_map matching config/m4b-config.json
ARCH_MAP = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
    "armv7l": "arm/v7",
    "armv6l": "arm/v6",
}


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

    def _run_arch_test(self, machine_value, expected_dkarch):
        """Helper: mock platform.machine and assert detect_architecture result."""
        with (
            patch("utils.detector.load_json_config") as mock_load,
            patch("platform.machine", return_value=machine_value),
        ):
            mock_load.return_value = {"system": {"arch_map": ARCH_MAP}}
            result = detect_architecture("dummy")
            self.assertEqual(result["arch"], machine_value.lower())
            self.assertEqual(result["dkarch"], expected_dkarch)

    def test_detect_architecture_x86_64(self):
        self._run_arch_test("x86_64", "amd64")

    def test_detect_architecture_aarch64(self):
        self._run_arch_test("aarch64", "arm64")

    def test_detect_architecture_arm64(self):
        self._run_arch_test("arm64", "arm64")

    def test_detect_architecture_armv7l(self):
        """ARM 32-bit (Raspberry Pi 2/3/4 in 32-bit OS)."""
        self._run_arch_test("armv7l", "arm/v7")

    def test_detect_architecture_armv6l(self):
        """ARM v6 (Raspberry Pi Zero / original Pi)."""
        self._run_arch_test("armv6l", "arm/v6")

    def test_detect_architecture_unknown(self):
        """Unknown architecture falls back to 'unknown'."""
        self._run_arch_test("sparc64", "unknown")


if __name__ == "__main__":
    unittest.main()
