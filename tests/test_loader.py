import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import json
import os
from utils.loader import (
    load_json_config,
    load_module_from_file,
    load_modules_from_directory,
)


class TestModuleLoader(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data='{"key": "value"}')
    def test_load_json_config_file(self, mock_file):
        """
        Test loading JSON config from a file.
        """
        config_path = "/path/to/config.json"
        expected_config = {"key": "value"}

        config = load_json_config(config_path)
        self.assertEqual(config, expected_config)
        mock_file.assert_called_once_with(config_path, "r")

    def test_load_json_config_dict(self):
        """
        Test loading JSON config from a dictionary.
        """
        config_dict = {"key": "value"}

        config = load_json_config(config_dict)
        self.assertEqual(config, config_dict)

    def test_load_json_config_invalid_type(self):
        """
        Test loading JSON config with an invalid type.
        """
        with self.assertRaises(ValueError):
            load_json_config(123)

    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    def test_load_module_from_file(
        self, mock_module_from_spec, mock_spec_from_file_location
    ):
        """
        Test dynamically loading a module from a file.
        """
        mock_spec = MagicMock()
        mock_spec.loader.exec_module = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec
        mock_module = MagicMock()
        mock_module_from_spec.return_value = mock_module

        module_name = "test_module"
        file_path = "/path/to/module.py"

        module = load_module_from_file(module_name, file_path)
        self.assertEqual(module, mock_module)
        mock_spec_from_file_location.assert_called_once_with(module_name, file_path)
        mock_spec.loader.exec_module.assert_called_once_with(mock_module)

    @patch(
        "os.listdir",
        return_value=["module1.py", "module2.py", "__init__.py", "not_a_module.txt"],
    )
    @patch("utils.loader.load_module_from_file")
    def test_load_modules_from_directory(
        self, mock_load_module_from_file, mock_listdir
    ):
        """
        Test dynamically loading all modules in a directory.
        """
        mock_load_module_from_file.side_effect = lambda name, path: {name: path}

        directory_path = "/path/to/modules"
        modules = load_modules_from_directory(directory_path)

        expected_modules = {
            "module1": {"module1": os.path.join(directory_path, "module1.py")},
            "module2": {"module2": os.path.join(directory_path, "module2.py")},
        }
        self.assertEqual(modules, expected_modules)


if __name__ == "__main__":
    unittest.main()
