"""Tests for JSON writing in dumper.py."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from money4band.dumper import write_json


class TestDumperWriteJson(unittest.TestCase):
    def test_write_plaintext(self):
        data = {"key": "value", "nested": {"a": 1}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            write_json(data, path)
            with open(path) as f:
                loaded = json.load(f)
            self.assertEqual(loaded, data)
        finally:
            os.unlink(path)

    @patch("money4band.dumper.is_file_encrypted", return_value=True)
    @patch("money4band.dumper.encrypt_dict", return_value="M4B_ENCRYPTED:ciphertext")
    def test_write_encrypted(self, mock_encrypt, mock_is_enc):
        data = {"secret": "password123"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("placeholder")
            path = f.name
        try:
            write_json(data, path)
            with open(path) as f:
                content = f.read()
            self.assertEqual(content, "M4B_ENCRYPTED:ciphertext")
            mock_encrypt.assert_called_once_with(data)
        finally:
            os.unlink(path)

    def test_write_new_file_plaintext(self):
        path = os.path.join(tempfile.mkdtemp(), "new.json")
        try:
            write_json({"a": 1}, path)
            with open(path) as f:
                self.assertEqual(json.load(f), {"a": 1})
        finally:
            os.unlink(path)

    def test_overwrite_preserves_on_error(self):
        """Atomic write should not corrupt existing file if serialization fails."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"existing": true}')
            path = f.name
        try:
            bad_data = {"bad": object()}
            with self.assertRaises(TypeError):
                write_json(bad_data, path)
            # Original should be intact
            with open(path) as f:
                loaded = json.load(f)
            self.assertEqual(loaded, {"existing": True})
        finally:
            os.unlink(path)

    def test_write_overwrites_existing(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"old": True}, f)
            path = f.name
        try:
            write_json({"new": True}, path)
            with open(path) as f:
                loaded = json.load(f)
            self.assertEqual(loaded, {"new": True})
        finally:
            os.unlink(path)

    def test_write_creates_valid_indented_json(self):
        path = os.path.join(tempfile.mkdtemp(), "fmt.json")
        try:
            write_json({"a": 1, "b": [1, 2]}, path)
            raw = open(path).read()
            self.assertIn("\n", raw)
            self.assertEqual(json.loads(raw), {"a": 1, "b": [1, 2]})
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
