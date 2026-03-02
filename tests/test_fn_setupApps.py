import os
import tempfile
import unittest

from utils.fn_setupApps import cleanup_multiproxy_instances_dir


class TestCleanupMultiproxyInstancesDir(unittest.TestCase):
    def test_missing_instances_dir_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            instances_dir = os.path.join(tmp_dir, "m4b_proxy_instances")
            backup_root = os.path.join(tmp_dir, "m4b_proxy_instances_backup")

            cleanup_multiproxy_instances_dir(instances_dir, backup_root)

            self.assertFalse(os.path.exists(instances_dir))
            self.assertFalse(os.path.exists(backup_root))

    def test_empty_instances_dir_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            instances_dir = os.path.join(tmp_dir, "m4b_proxy_instances")
            backup_root = os.path.join(tmp_dir, "m4b_proxy_instances_backup")
            os.makedirs(instances_dir, exist_ok=True)

            cleanup_multiproxy_instances_dir(instances_dir, backup_root)

            self.assertFalse(os.path.exists(instances_dir))
            self.assertFalse(os.path.exists(backup_root))

    def test_non_empty_instances_dir_is_moved_to_backup(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            instances_dir = os.path.join(tmp_dir, "m4b_proxy_instances")
            backup_root = os.path.join(tmp_dir, "m4b_proxy_instances_backup")
            os.makedirs(instances_dir, exist_ok=True)

            instance_subdir = os.path.join(instances_dir, "money4band_1234")
            os.makedirs(instance_subdir, exist_ok=True)
            marker_file = os.path.join(instance_subdir, "docker-compose.yaml")
            with open(marker_file, "w") as f:
                f.write("services: {}")

            cleanup_multiproxy_instances_dir(instances_dir, backup_root)

            self.assertFalse(os.path.exists(instances_dir))
            self.assertTrue(os.path.isdir(backup_root))

            backup_instances_root = os.path.join(backup_root, "m4b_proxy_instances")
            self.assertTrue(os.path.isdir(backup_instances_root))

            backups = [
                entry
                for entry in os.listdir(backup_instances_root)
                if os.path.isdir(os.path.join(backup_instances_root, entry))
            ]
            self.assertEqual(len(backups), 1)

            moved_file = os.path.join(
                backup_instances_root,
                backups[0],
                "money4band_1234",
                "docker-compose.yaml",
            )
            self.assertTrue(os.path.isfile(moved_file))


if __name__ == "__main__":
    unittest.main()
