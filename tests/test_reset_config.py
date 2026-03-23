import json
import os
import tempfile
import unittest

from money4band.fn_reset_config import main as reset_config_main
from money4band.fn_reset_config import reset_config


class TestResetConfig(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.src_dir = os.path.join(self.test_dir.name, "template")
        self.dest_dir = os.path.join(self.test_dir.name, "config")
        os.makedirs(self.src_dir, exist_ok=True)
        os.makedirs(self.dest_dir, exist_ok=True)
        self.src_path = os.path.join(self.src_dir, "test-config.json")
        self.dest_path = os.path.join(self.dest_dir, "test-config.json")
        with open(self.src_path, "w") as f:
            json.dump({"test_key": "test_value"}, f)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_copies_to_new_dest(self):
        reset_config_main(
            app_config_path=None,
            m4b_config_path=None,
            user_config_path=None,
            src_path=self.src_path,
            dest_path=self.dest_path,
        )
        with open(self.dest_path) as f:
            data = json.load(f)
        self.assertEqual(data, {"test_key": "test_value"})

    def test_overwrites_existing_dest(self):
        with open(self.dest_path, "w") as f:
            json.dump({"old_key": "stale"}, f)

        reset_config(src_path=self.src_path, dest_path=self.dest_path)

        with open(self.dest_path) as f:
            data = json.load(f)
        self.assertEqual(data, {"test_key": "test_value"})
        self.assertNotIn("old_key", data)

    def test_creates_dest_dir_if_missing(self):
        nested_dest = os.path.join(self.test_dir.name, "a", "b", "cfg.json")
        reset_config(src_path=self.src_path, dest_path=nested_dest)
        self.assertTrue(os.path.isfile(nested_dest))

    def test_missing_source_raises(self):
        with self.assertRaises(FileNotFoundError):
            reset_config(
                src_path="/no/such/template.json",
                dest_path=self.dest_path,
            )


if __name__ == "__main__":
    unittest.main()
