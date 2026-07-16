"""Tests for loader.py - real file I/O, no mock_open."""

import json
import os
import tempfile
import unittest

from money4band.core.loader import (
    get_active_app_categories,
    get_all_app_categories,
    get_category_entries,
    get_install_limit,
    is_category_active,
    load_json_config,
)


class TestLoadJsonConfig(unittest.TestCase):
    """Test load_json_config with real files on disk."""

    def test_loads_valid_json_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"hello": "world", "n": 42}, f)
            path = f.name
        try:
            cfg = load_json_config(path)
            self.assertEqual(cfg, {"hello": "world", "n": 42})
        finally:
            os.unlink(path)

    def test_passthrough_dict(self):
        d = {"already": "loaded"}
        self.assertIs(load_json_config(d), d)

    def test_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            load_json_config(123)
        with self.assertRaises(ValueError):
            load_json_config(["a", "b"])

    def test_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_json_config("/no/such/path.json")

    def test_malformed_json_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{bad json!!")
            path = f.name
        try:
            with self.assertRaises(json.JSONDecodeError):
                load_json_config(path)
        finally:
            os.unlink(path)

    def test_empty_file_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name  # 0 bytes
        try:
            with self.assertRaises(json.JSONDecodeError):
                load_json_config(path)
        finally:
            os.unlink(path)

    def test_unicode_content(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(
                {"emoji": "\U0001f680", "lang": "\u65e5\u672c\u8a9e"},
                f,
                ensure_ascii=False,
            )
            path = f.name
        try:
            cfg = load_json_config(path)
            self.assertEqual(cfg["emoji"], "\U0001f680")
        finally:
            os.unlink(path)


class TestCategoryHelpers(unittest.TestCase):
    """Test app-config category query helpers."""

    SAMPLE = {
        "supported": {
            "active": True,
            "entries": [{"name": "a", "install_limit": 2}],
        },
        "deprecated": {
            "active": False,
            "entries": [{"name": "b"}],
        },
        "newcomers": {
            "active": True,
            "entries": [],
        },
        "project": {"version": "5.0"},
    }

    def test_get_all_app_categories(self):
        cats = get_all_app_categories(self.SAMPLE)
        self.assertIn("supported", cats)
        self.assertIn("deprecated", cats)
        self.assertIn("newcomers", cats)
        self.assertNotIn("project", cats)

    def test_get_active_app_categories(self):
        cats = get_active_app_categories(self.SAMPLE)
        self.assertIn("supported", cats)
        self.assertIn("newcomers", cats)
        self.assertNotIn("deprecated", cats)

    def test_get_category_entries(self):
        entries = get_category_entries(self.SAMPLE, "supported")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["name"], "a")

    def test_get_category_entries_missing(self):
        self.assertEqual(get_category_entries(self.SAMPLE, "nonexistent"), [])

    def test_get_install_limit_present(self):
        self.assertEqual(get_install_limit({"install_limit": 3}), 3)

    def test_get_install_limit_default(self):
        self.assertEqual(get_install_limit({}), -1)


class TestIsCategoryActive(unittest.TestCase):
    """Test the is_category_active helper."""

    def test_active_true(self):
        self.assertTrue(is_category_active({"cat": {"active": True}}, "cat"))

    def test_active_false(self):
        self.assertFalse(is_category_active({"cat": {"active": False}}, "cat"))

    def test_missing_category(self):
        self.assertFalse(is_category_active({}, "cat"))


class TestLoadJsonConfigEncrypted(unittest.TestCase):
    """Test load_json_config with encrypted files."""

    def test_encrypted_file_calls_decrypt(self):
        from unittest.mock import patch

        encrypted_content = "M4B_ENCRYPTED:base64stuff"
        decrypted = {"secret": "value"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(encrypted_content)
            path = f.name
        try:
            with patch("money4band.core.loader.is_encrypted", return_value=True):
                with patch(
                    "money4band.core.loader.decrypt_to_dict", return_value=decrypted
                ) as mock_decrypt:
                    result = load_json_config(path)
                    self.assertEqual(result, decrypted)
                    mock_decrypt.assert_called_once_with(encrypted_content)
        finally:
            os.unlink(path)


class TestLoadAppConfigWithOverlays(unittest.TestCase):
    """Test load_app_config_with_overlays merging."""

    def test_loads_without_apps_d(self):
        from money4band.core.loader import load_app_config_with_overlays

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"supported": {"active": True, "entries": []}}, f)
            path = f.name
        try:
            cfg = load_app_config_with_overlays(path)
            self.assertIn("supported", cfg)
        finally:
            os.unlink(path)

    def test_loads_with_apps_d_dir(self):
        from money4band.core.loader import load_app_config_with_overlays

        with tempfile.TemporaryDirectory() as d:
            config_path = os.path.join(d, "app-config.json")
            with open(config_path, "w") as f:
                json.dump({"supported": {"active": True, "entries": []}}, f)
            apps_d = os.path.join(d, "apps.d")
            os.makedirs(apps_d)
            cfg = load_app_config_with_overlays(config_path, apps_d)
            self.assertIn("supported", cfg)


if __name__ == "__main__":
    unittest.main()
