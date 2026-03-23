import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet

from money4band.crypto import (
    MAGIC_PREFIX,
    decrypt_file,
    decrypt_to_dict,
    encrypt_dict,
    encrypt_file,
    ensure_config_encrypted,
    get_key_path,
    get_or_create_key,
    is_encrypted,
    is_file_encrypted,
)
from money4band.dumper import write_json
from money4band.loader import load_json_config


class TestKeyManagement(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.key_path = Path(self.tmp_dir) / "master.key"

    def tearDown(self):
        # Clean up any created files
        if self.key_path.exists():
            self.key_path.unlink()
        os.rmdir(self.tmp_dir)

    @patch("money4band.crypto.get_key_path")
    def test_get_or_create_key_creates_new(self, mock_path):
        """First call generates a new key and writes it to disk."""
        mock_path.return_value = self.key_path
        key = get_or_create_key()

        self.assertTrue(self.key_path.exists())
        self.assertEqual(key, self.key_path.read_bytes().strip())
        # Verify the key is a valid Fernet key
        Fernet(key)

    @patch("money4band.crypto.get_key_path")
    def test_get_or_create_key_loads_existing(self, mock_path):
        """Second call loads the same key from disk."""
        mock_path.return_value = self.key_path
        key1 = get_or_create_key()
        key2 = get_or_create_key()
        self.assertEqual(key1, key2)

    @patch("money4band.crypto.get_key_path")
    def test_key_file_permissions_unix(self, mock_path):
        """On Unix, key file should have 0o600 permissions."""
        if os.name == "nt":
            self.skipTest("Unix permissions test not applicable on Windows")
        mock_path.return_value = self.key_path
        get_or_create_key()
        mode = self.key_path.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_get_key_path_returns_home_dir(self):
        """Key path should be under ~/.m4b/."""
        key_path = get_key_path()
        self.assertEqual(key_path.parent.name, ".m4b")
        self.assertEqual(key_path.name, "master.key")
        self.assertTrue(str(key_path).startswith(str(Path.home())))


class TestEncryptDecrypt(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.key_path = Path(self.tmp_dir) / "master.key"
        self.patcher = patch(
            "money4band.crypto.get_key_path", return_value=self.key_path
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if self.key_path.exists():
            self.key_path.unlink()
        os.rmdir(self.tmp_dir)

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypting then decrypting returns the original data."""
        data = {"email": "user@example.com", "api_key": "secret123", "nested": {"a": 1}}
        encrypted = encrypt_dict(data)
        decrypted = decrypt_to_dict(encrypted)
        self.assertEqual(data, decrypted)

    def test_encrypted_has_magic_prefix(self):
        """Encrypted output starts with the M4B_ENCRYPTED: prefix."""
        encrypted = encrypt_dict({"key": "value"})
        self.assertTrue(encrypted.startswith(MAGIC_PREFIX))

    def test_is_encrypted_true(self):
        """is_encrypted detects the magic prefix."""
        self.assertTrue(is_encrypted(MAGIC_PREFIX + "some_token_data"))

    def test_is_encrypted_false_json(self):
        """is_encrypted returns False for plaintext JSON."""
        self.assertFalse(is_encrypted('{"key": "value"}'))

    def test_is_encrypted_false_empty(self):
        """is_encrypted returns False for empty string."""
        self.assertFalse(is_encrypted(""))

    def test_decrypt_without_prefix_raises(self):
        """Decrypting content without magic prefix raises ValueError."""
        with self.assertRaises(ValueError):
            decrypt_to_dict('{"key": "value"}')

    def test_decrypt_wrong_key_raises(self):
        """Decrypting with a different key raises ValueError."""
        data = {"secret": "data"}
        encrypted = encrypt_dict(data)

        # Replace key with a different one
        self.key_path.write_bytes(Fernet.generate_key())

        with self.assertRaises(ValueError) as ctx:
            decrypt_to_dict(encrypted)
        self.assertIn("wrong key", str(ctx.exception).lower())

    def test_encrypt_preserves_json_structure(self):
        """Decrypted data preserves all JSON types correctly."""
        data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"a": {"b": "c"}},
        }
        encrypted = encrypt_dict(data)
        decrypted = decrypt_to_dict(encrypted)
        self.assertEqual(data, decrypted)


class TestFileOperations(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.key_path = Path(self.tmp_dir) / "master.key"
        self.config_path = os.path.join(self.tmp_dir, "user-config.json")
        self.patcher = patch(
            "money4band.crypto.get_key_path", return_value=self.key_path
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        for f in [self.key_path, Path(self.config_path)]:
            if f.exists():
                f.unlink()
        os.rmdir(self.tmp_dir)

    def _write_plaintext(self, data):
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=4)

    def test_encrypt_file_in_place(self):
        """encrypt_file converts a plaintext JSON file to encrypted."""
        data = {"email": "test@test.com", "password": "secret"}
        self._write_plaintext(data)

        encrypt_file(self.config_path)

        self.assertTrue(is_file_encrypted(self.config_path))
        # Verify we can decrypt and get original data back
        with open(self.config_path) as f:
            content = f.read()
        self.assertEqual(decrypt_to_dict(content), data)

    def test_encrypt_file_idempotent(self):
        """Encrypting an already-encrypted file is a no-op."""
        data = {"key": "value"}
        self._write_plaintext(data)
        encrypt_file(self.config_path)

        with open(self.config_path) as f:
            first_encrypted = f.read()

        encrypt_file(self.config_path)

        with open(self.config_path) as f:
            second_encrypted = f.read()

        # Content may differ (Fernet uses random IV) but should be skipped
        # Since encrypt_file skips already-encrypted files, content is identical
        self.assertEqual(first_encrypted, second_encrypted)

    def test_decrypt_file_in_place(self):
        """decrypt_file converts an encrypted file back to plaintext JSON."""
        data = {"api_key": "abc123"}
        self._write_plaintext(data)
        encrypt_file(self.config_path)

        decrypt_file(self.config_path)

        self.assertFalse(is_file_encrypted(self.config_path))
        with open(self.config_path) as f:
            restored = json.load(f)
        self.assertEqual(restored, data)

    def test_decrypt_file_plaintext_noop(self):
        """Decrypting a plaintext file is a no-op."""
        data = {"key": "value"}
        self._write_plaintext(data)

        decrypt_file(self.config_path)

        with open(self.config_path) as f:
            restored = json.load(f)
        self.assertEqual(restored, data)

    def test_is_file_encrypted_true(self):
        """is_file_encrypted returns True for encrypted files."""
        self._write_plaintext({"key": "value"})
        encrypt_file(self.config_path)
        self.assertTrue(is_file_encrypted(self.config_path))

    def test_is_file_encrypted_false(self):
        """is_file_encrypted returns False for plaintext JSON files."""
        self._write_plaintext({"key": "value"})
        self.assertFalse(is_file_encrypted(self.config_path))

    def test_is_file_encrypted_missing_file(self):
        """is_file_encrypted returns False for non-existent files."""
        self.assertFalse(is_file_encrypted("/nonexistent/path.json"))

    def test_ensure_config_encrypted_migrates_plaintext(self):
        """ensure_config_encrypted encrypts a plaintext config file."""
        data = {"credentials": {"email": "a@b.com"}}
        self._write_plaintext(data)

        ensure_config_encrypted(self.config_path)

        self.assertTrue(is_file_encrypted(self.config_path))
        with open(self.config_path) as f:
            decrypted = decrypt_to_dict(f.read())
        self.assertEqual(decrypted, data)

    def test_ensure_config_encrypted_noop_if_encrypted(self):
        """ensure_config_encrypted does nothing if already encrypted."""
        data = {"key": "value"}
        self._write_plaintext(data)
        encrypt_file(self.config_path)

        with open(self.config_path) as f:
            before = f.read()

        ensure_config_encrypted(self.config_path)

        with open(self.config_path) as f:
            after = f.read()
        self.assertEqual(before, after)

    def test_ensure_config_encrypted_missing_file_noop(self):
        """ensure_config_encrypted does nothing if file doesn't exist."""
        ensure_config_encrypted("/nonexistent/path.json")
        # Should not raise


class TestLoaderIntegration(unittest.TestCase):
    """Test that load_json_config works transparently with encrypted files."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.key_path = Path(self.tmp_dir) / "master.key"
        self.config_path = os.path.join(self.tmp_dir, "test-config.json")
        self.patcher = patch(
            "money4band.crypto.get_key_path", return_value=self.key_path
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        for f in [self.key_path, Path(self.config_path)]:
            if f.exists():
                f.unlink()
        os.rmdir(self.tmp_dir)

    def test_load_plaintext_config(self):
        """load_json_config reads plaintext JSON files as before."""
        data = {"apps": [{"name": "test"}]}
        with open(self.config_path, "w") as f:
            json.dump(data, f)

        result = load_json_config(self.config_path)
        self.assertEqual(result, data)

    def test_load_encrypted_config(self):
        """load_json_config transparently decrypts encrypted files."""
        data = {"credentials": {"email": "secret@test.com", "token": "abc"}}
        with open(self.config_path, "w") as f:
            json.dump(data, f)
        encrypt_file(self.config_path)

        result = load_json_config(self.config_path)
        self.assertEqual(result, data)


class TestDumperIntegration(unittest.TestCase):
    """Test that write_json preserves encryption state."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.key_path = Path(self.tmp_dir) / "master.key"
        self.config_path = os.path.join(self.tmp_dir, "test-config.json")
        self.patcher = patch(
            "money4band.crypto.get_key_path", return_value=self.key_path
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        for f in [self.key_path, Path(self.config_path)]:
            if f.exists():
                f.unlink()
        os.rmdir(self.tmp_dir)

    def test_write_plaintext_stays_plaintext(self):
        """Writing to a plaintext file keeps it plaintext."""
        data = {"key": "value"}
        with open(self.config_path, "w") as f:
            json.dump({"old": "data"}, f)

        write_json(data, self.config_path)

        self.assertFalse(is_file_encrypted(self.config_path))
        with open(self.config_path) as f:
            self.assertEqual(json.load(f), data)

    def test_write_encrypted_stays_encrypted(self):
        """Writing to an encrypted file keeps it encrypted."""
        original = {"email": "old@test.com"}
        with open(self.config_path, "w") as f:
            json.dump(original, f)
        encrypt_file(self.config_path)

        updated = {"email": "new@test.com"}
        write_json(updated, self.config_path)

        self.assertTrue(is_file_encrypted(self.config_path))
        result = load_json_config(self.config_path)
        self.assertEqual(result, updated)

    def test_write_new_file_is_plaintext(self):
        """Writing to a non-existent file creates plaintext JSON."""
        data = {"key": "value"}
        write_json(data, self.config_path)

        self.assertFalse(is_file_encrypted(self.config_path))
        with open(self.config_path) as f:
            self.assertEqual(json.load(f), data)

    def test_full_lifecycle(self):
        """Full lifecycle: create → encrypt → load → modify → save → load."""
        # 1. Create plaintext config
        data = {"email": "user@test.com", "apps": []}
        with open(self.config_path, "w") as f:
            json.dump(data, f)

        # 2. Migrate to encrypted (like main.py startup)
        ensure_config_encrypted(self.config_path)

        # 3. Load (transparent decryption)
        loaded = load_json_config(self.config_path)
        self.assertEqual(loaded, data)

        # 4. Modify in memory
        loaded["apps"].append({"name": "new_app"})

        # 5. Save (auto-detects encryption)
        write_json(loaded, self.config_path)

        # 6. Reload and verify
        final = load_json_config(self.config_path)
        self.assertEqual(final["apps"], [{"name": "new_app"}])
        self.assertTrue(is_file_encrypted(self.config_path))


if __name__ == "__main__":
    unittest.main()
