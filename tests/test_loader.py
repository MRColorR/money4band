"""Tests for loader.py — real file I/O, no mock_open."""

import json
import os
import tempfile
import types
import unittest

from money4band.loader import (
    get_active_app_categories,
    get_all_app_categories,
    get_category_entries,
    get_install_limit,
    load_json_config,
    load_module_from_file,
    load_modules_from_directory,
)


class TestLoadJsonConfig(unittest.TestCase):
    """Test load_json_config with real files on disk."""

    def test_loads_valid_json_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
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
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{bad json!!")
            path = f.name
        try:
            with self.assertRaises(json.JSONDecodeError):
                load_json_config(path)
        finally:
            os.unlink(path)

    def test_empty_file_raises(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
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
            json.dump({"emoji": "\U0001f680", "lang": "日本語"}, f, ensure_ascii=False)
            path = f.name
        try:
            cfg = load_json_config(path)
            self.assertEqual(cfg["emoji"], "\U0001f680")
        finally:
            os.unlink(path)


class TestLoadModuleFromFile(unittest.TestCase):
    """Test dynamic module loading with real .py files."""

    def test_loads_module_with_function(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write("def greet(name):\n    return f'hello {name}'\n")
            path = f.name
        try:
            mod = load_module_from_file("_test_greet", path)
            self.assertIsInstance(mod, types.ModuleType)
            self.assertEqual(mod.greet("world"), "hello world")
        finally:
            os.unlink(path)

    def test_missing_file_raises(self):
        with self.assertRaises(Exception):
            load_module_from_file("_gone", "/no/such/module.py")


class TestLoadModulesFromDirectory(unittest.TestCase):
    """Test directory-based multi-module loading with real files."""

    def test_loads_all_py_except_init(self):
        with tempfile.TemporaryDirectory() as d:
            # Create two normal modules + __init__.py + non-py file
            for name, body in [
                ("alpha.py", "VALUE = 1\ndef main(*a): pass\n"),
                ("beta.py", "VALUE = 2\ndef main(*a): pass\n"),
                ("__init__.py", ""),
                ("readme.txt", "not python"),
            ]:
                with open(os.path.join(d, name), "w") as f:
                    f.write(body)

            modules = load_modules_from_directory(d)
            self.assertIn("alpha", modules)
            self.assertIn("beta", modules)
            self.assertNotIn("__init__", modules)
            self.assertNotIn("readme", modules)
            self.assertEqual(modules["alpha"].VALUE, 1)
            self.assertEqual(modules["beta"].VALUE, 2)

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as d:
            modules = load_modules_from_directory(d)
            self.assertEqual(modules, {})


class TestCategoryHelpers(unittest.TestCase):
    """Test app-config category query helpers."""

    SAMPLE = {
        "supported-apps": {
            "active": True,
            "entries": [{"name": "a", "install_limit": 2}],
        },
        "deprecated-apps": {
            "active": False,
            "entries": [{"name": "b"}],
        },
        "candidate-apps": {
            "active": True,
            "entries": [],
        },
        "project": {"version": "5.0"},
    }

    def test_get_all_app_categories(self):
        cats = get_all_app_categories(self.SAMPLE)
        self.assertIn("supported-apps", cats)
        self.assertIn("deprecated-apps", cats)
        self.assertIn("candidate-apps", cats)
        self.assertNotIn("project", cats)

    def test_get_active_app_categories(self):
        cats = get_active_app_categories(self.SAMPLE)
        self.assertIn("supported-apps", cats)
        self.assertIn("candidate-apps", cats)
        self.assertNotIn("deprecated-apps", cats)

    def test_get_category_entries(self):
        entries = get_category_entries(self.SAMPLE, "supported-apps")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["name"], "a")

    def test_get_category_entries_missing(self):
        self.assertEqual(get_category_entries(self.SAMPLE, "nonexistent"), [])

    def test_get_install_limit_present(self):
        self.assertEqual(get_install_limit({"install_limit": 3}), 3)

    def test_get_install_limit_default(self):
        self.assertEqual(get_install_limit({}), -1)


if __name__ == "__main__":
    unittest.main()
