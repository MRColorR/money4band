import unittest
from unittest.mock import patch

from money4band.system.detector import (
    _MIN_CPU,
    _MIN_MEM,
    _TIER_MULTIPLIERS,
    calculate_resource_limits,
    detect_architecture,
    detect_os,
    get_active_profile,
    get_profile_definition,
    get_valid_profiles,
    show_resource_profile_info,
)

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
    @patch("money4band.core.loader.load_json_config")
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
            patch("money4band.system.detector.load_json_config") as mock_load,
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


class TestResourceProfiles(unittest.TestCase):
    """Tests for the resource profile system"""

    _M4B_CFG = {
        "resource_profiles": {
            "active": "standard",
            "profiles": {
                "minimal": {"description": "Minimal", "cpu_pct": 0.20, "ram_pct": 0.10},
                "conservative": {
                    "description": "Conservative",
                    "cpu_pct": 0.40,
                    "ram_pct": 0.25,
                },
                "standard": {"description": "Standard", "cpu_pct": 0.60, "ram_pct": 0.40},
                "performance": {
                    "description": "Performance",
                    "cpu_pct": 0.85,
                    "ram_pct": 0.65,
                },
            },
        }
    }

    def test_get_active_profile_returns_configured(self):
        self.assertEqual(get_active_profile(self._M4B_CFG), "standard")

    def test_get_active_profile_defaults_to_standard(self):
        self.assertEqual(get_active_profile({}), "standard")

    def test_get_profile_definition_returns_correct(self):
        p = get_profile_definition(self._M4B_CFG, "conservative")
        self.assertEqual(p["cpu_pct"], 0.40)
        self.assertEqual(p["ram_pct"], 0.25)

    def test_get_profile_definition_active_default(self):
        p = get_profile_definition(self._M4B_CFG)
        # Active is "standard"
        self.assertEqual(p["cpu_pct"], 0.60)

    def test_valid_profiles_from_config(self):
        self.assertEqual(get_valid_profiles(self._M4B_CFG), ("minimal", "conservative", "standard", "performance"))

    @patch("money4band.system.detector.get_system_memory_and_cores", return_value=(8192.0, 4))
    @patch("money4band.system.detector.write_json")
    @patch("money4band.system.detector.load_json_config")
    def test_calculate_resource_limits_standard_profile(
        self, mock_load, mock_write, mock_sys
    ):
        """With 8 GB RAM + 4 cores on 'standard' profile, verify all tier values."""
        mock_load.return_value = {"resource_limits": {"ram_cap_mb_default": 6144}}
        calculate_resource_limits("dummy_path", m4b_config=self._M4B_CFG)

        # Verify write_json was called
        mock_write.assert_called_once()
        saved = mock_write.call_args[0][0]
        rl = saved["resource_limits"]

        # base_ram = 8192 * 0.40 = 3276.8 MB, base_cpu = 4 * 0.60 = 2.4
        base_ram = 8192 * 0.40  # 3276.8
        base_cpu = 4 * 0.60  # 2.4

        for tier, mult in _TIER_MULTIPLIERS.items():
            expected_reserv = int(
                max(base_ram * mult["mem_reserv"], _MIN_MEM["reserv"])
            )
            expected_limit = int(max(base_ram * mult["mem_limit"], _MIN_MEM["limit"]))
            expected_cpu = round(max(base_cpu * mult["cpu"], _MIN_CPU[tier]), 1)

            self.assertEqual(rl[f"app_mem_reserv_{tier}"], f"{expected_reserv}m")
            self.assertEqual(rl[f"app_mem_limit_{tier}"], f"{expected_limit}m")
            self.assertEqual(rl[f"app_cpu_limit_{tier}"], expected_cpu)

    @patch("money4band.system.detector.get_system_memory_and_cores", return_value=(2048.0, 2))
    @patch("money4band.system.detector.write_json")
    @patch("money4band.system.detector.load_json_config")
    def test_calculate_limits_minimal_profile_uses_minimums(
        self, mock_load, mock_write, mock_sys
    ):
        """Minimal profile on a 2 GB / 2-core system should hit absolute minimums for lower tiers."""
        cfg = {
            "resource_profiles": {
                "active": "minimal",
                "profiles": self._M4B_CFG["resource_profiles"]["profiles"],
            }
        }
        mock_load.return_value = {"resource_limits": {"ram_cap_mb_default": 6144}}
        calculate_resource_limits("dummy_path", m4b_config=cfg)

        saved = mock_write.call_args[0][0]
        rl = saved["resource_limits"]

        # base_ram = 2048 * 0.10 = 204.8 MB → lower tiers hit minimums for mem
        # base_cpu = 2 * 0.20 = 0.4 → all tiers hit minimum CPU
        self.assertEqual(rl["app_mem_reserv_little"], "64m")
        self.assertEqual(rl["app_mem_limit_little"], "128m")
        self.assertEqual(rl["app_cpu_limit_little"], 0.8)

    @patch("money4band.system.detector.get_system_memory_and_cores", return_value=(16384.0, 8))
    @patch("money4band.system.detector.write_json")
    @patch("money4band.system.detector.load_json_config")
    def test_calculate_limits_performance_profile(self, mock_load, mock_write, mock_sys):
        """Performance profile on a 16 GB / 8-core system."""
        cfg = {
            "resource_profiles": {
                "active": "performance",
                "profiles": self._M4B_CFG["resource_profiles"]["profiles"],
            }
        }
        mock_load.return_value = {"resource_limits": {"ram_cap_mb_default": 6144}}
        calculate_resource_limits("dummy_path", m4b_config=cfg)

        saved = mock_write.call_args[0][0]
        rl = saved["resource_limits"]

        # base_ram = 16384 * 0.65 = 10649.6, base_cpu = 8 * 0.85 = 6.8
        # HUGE tier: mem_limit = 10649.6 * 1.0 = 10649m, cpu = 6.8 * 0.8 = 5.4
        self.assertEqual(rl["app_mem_limit_huge"], "10649m")
        self.assertEqual(rl["app_cpu_limit_huge"], 5.4)

    @patch("money4band.system.detector.get_system_memory_and_cores", return_value=(8192.0, 4))
    @patch("money4band.system.detector.write_json")
    @patch("money4band.system.detector.load_json_config")
    def test_calculate_limits_no_m4b_config_defaults_to_low(
        self, mock_load, mock_write, mock_sys
    ):
        """When m4b_config is None, should use the fallback standard profile values."""
        mock_load.return_value = {"resource_limits": {"ram_cap_mb_default": 6144}}
        calculate_resource_limits("dummy_path", m4b_config=None)

        saved = mock_write.call_args[0][0]
        rl = saved["resource_limits"]

        # Fallback: cpu_pct=0.60, ram_pct=0.40 (same as "standard")
        base_ram = 8192 * 0.40
        self.assertEqual(rl["app_mem_limit_medium"], f"{int(base_ram * 0.6)}m")

    def test_ram_cap_preserved(self):
        """ram_cap_mb_default is preserved in output for backward compat."""
        with (
            patch(
                "money4band.system.detector.get_system_memory_and_cores",
                return_value=(8192.0, 4),
            ),
            patch("money4band.system.detector.write_json") as mock_write,
            patch("money4band.system.detector.load_json_config") as mock_load,
        ):
            mock_load.return_value = {"resource_limits": {"ram_cap_mb_default": 4096}}
            calculate_resource_limits("dummy_path", m4b_config=self._M4B_CFG)
            saved = mock_write.call_args[0][0]
            self.assertEqual(saved["resource_limits"]["ram_cap_mb_default"], 4096)

    @patch("money4band.system.detector.get_system_memory_and_cores", return_value=(8192.0, 4))
    def test_show_resource_profile_info_runs(self, mock_sys):
        """Smoke test: show_resource_profile_info should not raise."""
        user_config = {
            "resource_limits": {
                "app_mem_limit_little": "64m",
                "app_mem_reserv_little": "32m",
                "app_cpu_limit_little": 0.8,
                "app_mem_limit_medium": "128m",
                "app_mem_reserv_medium": "64m",
                "app_cpu_limit_medium": 1.0,
                "app_mem_limit_big": "256m",
                "app_mem_reserv_big": "128m",
                "app_cpu_limit_big": 1.0,
                "app_mem_limit_huge": "512m",
                "app_mem_reserv_huge": "256m",
                "app_cpu_limit_huge": 1.0,
            }
        }
        # Should not raise
        show_resource_profile_info(self._M4B_CFG, user_config)


if __name__ == "__main__":
    unittest.main()
