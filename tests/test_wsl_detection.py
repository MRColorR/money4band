"""Tests for WSL environment detection functions in detector module."""

import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

from money4band.system.detector import (
    detect_wsl_environment,
    get_wsl_networking_mode,
    get_wsl_version,
    is_running_in_wsl,
)

# ---------------------------------------------------------------------------
# is_running_in_wsl
# ---------------------------------------------------------------------------


class TestIsRunningInWSL(unittest.TestCase):
    """Detection via WSL_DISTRO_NAME env var and /proc/version fallback."""

    @patch.dict(os.environ, {"WSL_DISTRO_NAME": "Ubuntu"})
    def test_detected_when_env_var_set(self):
        self.assertTrue(is_running_in_wsl())

    @patch.dict(os.environ, {"WSL_DISTRO_NAME": "Debian"})
    def test_detected_with_different_distro(self):
        """Any non-empty WSL_DISTRO_NAME value should detect WSL."""
        self.assertTrue(is_running_in_wsl())

    @patch.dict(os.environ, {"WSL_DISTRO_NAME": ""}, clear=False)
    @patch(
        "builtins.open",
        mock_open(read_data="Linux version 5.15.146.1-microsoft-standard-WSL2"),
    )
    def test_detected_via_proc_version_microsoft(self):
        """Falls back to /proc/version when env var is empty."""
        self.assertTrue(is_running_in_wsl())

    @patch.dict(os.environ, {}, clear=True)
    @patch(
        "builtins.open",
        mock_open(read_data="Linux version 5.10.0-microsoft-WSL2 (gcc)"),
    )
    def test_detected_via_proc_version_wsl_string(self):
        """Detects 'wsl' substring in /proc/version."""
        self.assertTrue(is_running_in_wsl())

    @patch.dict(os.environ, {}, clear=True)
    @patch(
        "builtins.open",
        mock_open(read_data="Linux version 6.8.0-40-generic (Ubuntu 6.8.0)"),
    )
    def test_native_linux_not_detected(self):
        """Regular Linux is not mistaken for WSL."""
        self.assertFalse(is_running_in_wsl())

    @patch.dict(os.environ, {}, clear=True)
    @patch("builtins.open", side_effect=OSError("No such file"))
    def test_non_linux_os_not_detected(self, _mock_open):
        """Windows/macOS where /proc/version doesn't exist."""
        self.assertFalse(is_running_in_wsl())

    @patch.dict(os.environ, {}, clear=True)
    @patch("builtins.open", side_effect=PermissionError)
    def test_permission_error_not_detected(self, _mock_open):
        """PermissionError inherits from OSError - should be safe."""
        self.assertFalse(is_running_in_wsl())


# ---------------------------------------------------------------------------
# get_wsl_version
# ---------------------------------------------------------------------------


class TestGetWSLVersion(unittest.TestCase):
    """Parsing wsl.exe --version output."""

    def _mock_run_result(self, stdout: str) -> MagicMock:
        result = MagicMock()
        result.stdout = stdout
        return result

    @patch("subprocess.run")
    def test_parses_standard_output(self, mock_run):
        mock_run.return_value = self._mock_run_result(
            "WSL version: 2.4.4.0\nKernel version: 5.15.146.1\n"
        )
        self.assertEqual(get_wsl_version(), "2.4.4.0")

    @patch("subprocess.run")
    def test_handles_null_bytes(self, mock_run):
        """Real wsl.exe output often contains \\x00 (UTF-16-LE leftovers)."""
        mock_run.return_value = self._mock_run_result(
            "W\x00S\x00L\x00 \x00v\x00e\x00r\x00s\x00i\x00o\x00n\x00:\x00 2.0.0\n"
        )
        # After replace("\x00", "") -> "WSL version: 2.0.0"
        self.assertEqual(get_wsl_version(), "2.0.0")

    @patch("subprocess.run")
    def test_case_insensitive_header(self, mock_run):
        mock_run.return_value = self._mock_run_result("wsl Version: 1.2.3\n")
        self.assertEqual(get_wsl_version(), "1.2.3")

    @patch("subprocess.run")
    def test_no_version_line_returns_none(self, mock_run):
        mock_run.return_value = self._mock_run_result("some unrelated output\n")
        self.assertIsNone(get_wsl_version())

    @patch("subprocess.run")
    def test_empty_output_returns_none(self, mock_run):
        mock_run.return_value = self._mock_run_result("")
        self.assertIsNone(get_wsl_version())

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_wsl_not_installed(self, _mock):
        """wsl.exe not on PATH - e.g. native Linux."""
        self.assertIsNone(get_wsl_version())

    @patch("subprocess.run", side_effect=TimeoutError)
    def test_timeout_returns_none(self, _mock):
        self.assertIsNone(get_wsl_version())


# ---------------------------------------------------------------------------
# get_wsl_networking_mode
# ---------------------------------------------------------------------------


class TestGetWSLNetworkingMode(unittest.TestCase):
    """Parsing .wslconfig for networkingMode."""

    def _subprocess_side_effects(
        self, userprofile="C:\\Users\\test", wslpath="/mnt/c/Users/test"
    ):
        """Return a list of mock results for [cmd.exe, wslpath] subprocess calls."""
        cmd_result = MagicMock()
        cmd_result.stdout = f"{userprofile}\r\n"
        wsl_result = MagicMock()
        wsl_result.stdout = f"{wslpath}\n"
        return [cmd_result, wsl_result]

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch("builtins.open", mock_open(read_data="[wsl2]\nnetworkingMode=mirrored\n"))
    def test_mirrored_mode(self, _isfile, mock_run):
        mock_run.side_effect = self._subprocess_side_effects()
        self.assertEqual(get_wsl_networking_mode(), "mirrored")

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch("builtins.open", mock_open(read_data="[wsl2]\nnetworkingMode=nat\n"))
    def test_nat_mode(self, _isfile, mock_run):
        mock_run.side_effect = self._subprocess_side_effects()
        self.assertEqual(get_wsl_networking_mode(), "nat")

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch(
        "builtins.open", mock_open(read_data="[wsl2]\n  networkingMode = mirrored \n")
    )
    def test_whitespace_around_value(self, _isfile, mock_run):
        mock_run.side_effect = self._subprocess_side_effects()
        self.assertEqual(get_wsl_networking_mode(), "mirrored")

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch("builtins.open", mock_open(read_data="[boot]\nsystemd=true\n"))
    def test_no_networking_mode_line(self, _isfile, mock_run):
        mock_run.side_effect = self._subprocess_side_effects()
        self.assertEqual(get_wsl_networking_mode(), "not_set")

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch("builtins.open", mock_open(read_data=""))
    def test_empty_config_file(self, _isfile, mock_run):
        mock_run.side_effect = self._subprocess_side_effects()
        self.assertEqual(get_wsl_networking_mode(), "not_set")

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=False)
    def test_config_file_missing(self, _isfile, mock_run):
        mock_run.side_effect = self._subprocess_side_effects()
        self.assertEqual(get_wsl_networking_mode(), "not_set")

    @patch("subprocess.run", side_effect=Exception("cmd.exe failed"))
    def test_subprocess_failure(self, _mock):
        self.assertEqual(get_wsl_networking_mode(), "not_set")

    @patch("subprocess.run")
    def test_empty_userprofile(self, mock_run):
        """When cmd.exe returns empty or unexpanded %USERPROFILE%."""
        result = MagicMock()
        result.stdout = "%USERPROFILE%\r\n"
        mock_run.return_value = result
        self.assertEqual(get_wsl_networking_mode(), "not_set")


# ---------------------------------------------------------------------------
# detect_wsl_environment (integration of the above)
# ---------------------------------------------------------------------------


class TestDetectWSLEnvironment(unittest.TestCase):
    """Aggregate WSL environment info."""

    @patch("money4band.system.detector.is_running_in_wsl", return_value=False)
    def test_not_wsl_returns_defaults(self, _mock):
        result = detect_wsl_environment()
        self.assertFalse(result["is_wsl"])
        self.assertIsNone(result["wsl_version"])
        self.assertEqual(result["networking_mode"], "not_set")
        self.assertIsNone(result["distro"])

    @patch(
        "money4band.system.detector.get_wsl_networking_mode", return_value="mirrored"
    )
    @patch("money4band.system.detector.get_wsl_version", return_value="2.4.4.0")
    @patch("money4band.system.detector.is_running_in_wsl", return_value=True)
    @patch.dict(os.environ, {"WSL_DISTRO_NAME": "Ubuntu-24.04"})
    def test_full_wsl_environment(self, *_mocks):
        result = detect_wsl_environment()
        self.assertTrue(result["is_wsl"])
        self.assertEqual(result["wsl_version"], "2.4.4.0")
        self.assertEqual(result["networking_mode"], "mirrored")
        self.assertEqual(result["distro"], "Ubuntu-24.04")

    @patch("money4band.system.detector.get_wsl_networking_mode", return_value="not_set")
    @patch("money4band.system.detector.get_wsl_version", return_value=None)
    @patch("money4band.system.detector.is_running_in_wsl", return_value=True)
    @patch.dict(os.environ, {"WSL_DISTRO_NAME": "Debian"})
    def test_wsl_without_version_or_mirror(self, *_mocks):
        """WSL detected but version unavailable and no mirror config."""
        result = detect_wsl_environment()
        self.assertTrue(result["is_wsl"])
        self.assertIsNone(result["wsl_version"])
        self.assertEqual(result["networking_mode"], "not_set")
        self.assertEqual(result["distro"], "Debian")

    @patch("money4band.system.detector.get_wsl_networking_mode", return_value="nat")
    @patch("money4band.system.detector.get_wsl_version", return_value="2.0.0")
    @patch("money4band.system.detector.is_running_in_wsl", return_value=True)
    @patch.dict(os.environ, {"WSL_DISTRO_NAME": "Alpine"})
    def test_nat_networking_mode(self, *_mocks):
        result = detect_wsl_environment()
        self.assertEqual(result["networking_mode"], "nat")


if __name__ == "__main__":
    unittest.main()
