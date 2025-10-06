import os
import tempfile
import unittest

from utils.fn_reset_config import main as reset_config_main


class TestResetConfig(unittest.TestCase):
    def setUp(self):
        """Set up test environment using temporary directories."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.src_dir = os.path.join(self.test_dir.name, "template")
        self.dest_dir = os.path.join(self.test_dir.name, "config")
        os.makedirs(self.src_dir, exist_ok=True)
        os.makedirs(self.dest_dir, exist_ok=True)
        with open(os.path.join(self.src_dir, "test-config.json"), "w") as f:
            f.write('{"test_key": "test_value"}')

    def tearDown(self):
        """Clean up test environment by removing temporary directories."""
        self.test_dir.cleanup()

    def test_reset_config(self):
        """Test the reset_config function."""
        src_path = os.path.join(self.src_dir, "test-config.json")
        dest_path = os.path.join(self.dest_dir, "test-config.json")

        reset_config_main(
            app_config=None,
            m4b_config=None,
            user_config=None,
            src_path=src_path,
            dest_path=dest_path,
        )

        self.assertTrue(os.path.exists(dest_path))
        with open(dest_path) as f:
            data = f.read()
            self.assertIn("test_key", data)
            self.assertIn("test_value", data)


if __name__ == "__main__":
    unittest.main()
