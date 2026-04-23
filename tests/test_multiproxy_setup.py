"""Tests for money4band.network.multiproxy — subnet math, directory management."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import patch

from money4band.network.multiproxy import (
    calculate_subnet,
    cleanup_multiproxy_instances_dir,
    int_to_ipv4,
    ipv4_to_int,
    regenerate_uuids_for_apps,
    remove_readonly,
    safe_rmtree,
)

# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


class TestIpv4ToInt:
    def test_zeros(self) -> None:
        assert ipv4_to_int("0.0.0.0") == 0

    def test_ones(self) -> None:
        assert ipv4_to_int("255.255.255.255") == (2**32) - 1

    def test_known_value(self) -> None:
        assert ipv4_to_int("192.168.1.0") == (192 << 24) + (168 << 16) + (1 << 8)

    def test_loopback(self) -> None:
        assert ipv4_to_int("127.0.0.1") == (127 << 24) + 1


class TestIntToIpv4:
    def test_zeros(self) -> None:
        assert int_to_ipv4(0) == "0.0.0.0"

    def test_ones(self) -> None:
        assert int_to_ipv4((2**32) - 1) == "255.255.255.255"

    def test_roundtrip(self) -> None:
        ip = "172.19.7.0"
        assert int_to_ipv4(ipv4_to_int(ip)) == ip


class TestCalculateSubnet:
    def test_offset_zero(self) -> None:
        assert calculate_subnet("172.19.7.0", 27, 0) == "172.19.7.0"

    def test_offset_one_slash27(self) -> None:
        # /27 = 32-host subnet, offset 1 => +32
        assert calculate_subnet("172.19.7.0", 27, 1) == "172.19.7.32"

    def test_offset_two_slash27(self) -> None:
        assert calculate_subnet("172.19.7.0", 27, 2) == "172.19.7.64"

    def test_offset_one_slash24(self) -> None:
        # /24 = 256-host subnet, offset 1 => +256
        assert calculate_subnet("10.0.0.0", 24, 1) == "10.0.1.0"

    def test_large_offset(self) -> None:
        result = calculate_subnet("172.19.0.0", 27, 10)
        assert result == "172.19.1.64"  # 10 * 32 = 320 => 1*256+64


# ---------------------------------------------------------------------------
# Directory management
# ---------------------------------------------------------------------------


class TestSafeRmtree:
    def test_removes_directory(self, tmp_path: Path) -> None:
        d = tmp_path / "target"
        d.mkdir()
        (d / "file.txt").write_text("x")
        assert safe_rmtree(str(d)) is True
        assert not d.exists()

    def test_nonexistent_silent_success(self, tmp_path: Path) -> None:
        # safe_rmtree only returns False on PermissionError; missing dirs succeed silently
        assert safe_rmtree(str(tmp_path / "nope")) is True


class TestRemoveReadonly:
    def test_clears_readonly_and_removes(self, tmp_path: Path) -> None:
        f = tmp_path / "readonly.txt"
        f.write_text("x")
        f.chmod(stat.S_IREAD)
        remove_readonly(os.unlink, str(f), None)
        assert not f.exists()


class TestCleanupMultiproxyInstancesDir:
    def test_no_dir_noop(self, tmp_path: Path) -> None:
        cleanup_multiproxy_instances_dir(str(tmp_path / "nope"))

    def test_empty_dir_removed(self, tmp_path: Path) -> None:
        d = tmp_path / "instances"
        d.mkdir()
        cleanup_multiproxy_instances_dir(str(d))
        assert not d.exists()

    def test_nonempty_dir_backed_up(self, tmp_path: Path) -> None:
        d = tmp_path / "instances"
        d.mkdir()
        (d / "inst1").mkdir()
        (d / "inst1" / ".env").write_text("KEY=val\n")
        backup = tmp_path / "backup"
        cleanup_multiproxy_instances_dir(str(d), str(backup))
        assert not d.exists()
        assert backup.exists()


# ---------------------------------------------------------------------------
# UUID regeneration
# ---------------------------------------------------------------------------


class TestRegenerateUuidsForApps:
    @patch(
        "money4band.network.multiproxy.get_active_app_categories",
        return_value=["supported"],
    )
    @patch("money4band.network.multiproxy.get_category_entries")
    def test_regenerates_uuid(self, mock_entries, mock_cats) -> None:
        mock_entries.return_value = [
            {
                "name": "EARNAPP",
                "flags": {"uuid": {"length": 32, "prefix": "sdk-node-"}},
            }
        ]
        user_config = {
            "apps": {
                "earnapp": {"enabled": True, "uuid": "sdk-node-old"},
            }
        }
        regenerate_uuids_for_apps(user_config, {})
        new_uuid = user_config["apps"]["earnapp"]["uuid"]
        assert new_uuid.startswith("sdk-node-")
        assert new_uuid != "sdk-node-old"

    @patch(
        "money4band.network.multiproxy.get_active_app_categories",
        return_value=["supported"],
    )
    @patch("money4band.network.multiproxy.get_category_entries")
    def test_skips_disabled(self, mock_entries, mock_cats) -> None:
        mock_entries.return_value = [
            {"name": "EARNAPP", "flags": {"uuid": {"length": 32}}},
        ]
        user_config = {"apps": {"earnapp": {"enabled": False, "uuid": "old"}}}
        regenerate_uuids_for_apps(user_config, {})
        assert user_config["apps"]["earnapp"]["uuid"] == "old"
