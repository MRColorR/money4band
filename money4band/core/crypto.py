from __future__ import annotations

import json
import logging
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

MAGIC_PREFIX = "M4B_ENCRYPTED:"

logger = logging.getLogger(__name__)


def get_key_path() -> Path:
    """Return the path to the master encryption key file (~/.m4b/master.key)."""
    return Path.home() / ".m4b" / "master.key"


def get_or_create_key() -> bytes:
    """Load the master key from disk, or generate and persist a new one."""
    key_path = get_key_path()

    if key_path.is_file():
        logger.debug("Loading existing encryption key from %s", key_path)
        return key_path.read_bytes().strip()

    logger.info("Generating new encryption key at %s", key_path)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    # Write key with restricted permissions (owner-only read/write)
    fd = os.open(str(key_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, key)
    finally:
        os.close(fd)
    # Reinforce permissions (effective on Unix; best-effort on Windows)
    try:
        key_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        logger.debug("Could not set strict permissions on %s (Windows)", key_path)

    return key


def is_encrypted(content: str) -> bool:
    """Check whether a string starts with the encryption magic prefix."""
    return content.startswith(MAGIC_PREFIX)


def is_file_encrypted(filepath: str) -> bool:
    """Check whether a file on disk is encrypted (has the magic prefix)."""
    try:
        with open(filepath) as f:
            header = f.read(len(MAGIC_PREFIX))
        return header == MAGIC_PREFIX
    except (OSError, UnicodeDecodeError):
        return False


def encrypt_dict(data: dict[str, Any]) -> str:
    """Serialize a dict to JSON and return an encrypted string with magic prefix."""
    key = get_or_create_key()
    fernet = Fernet(key)
    json_bytes = json.dumps(data, indent=4).encode("utf-8")
    token = fernet.encrypt(json_bytes)
    return MAGIC_PREFIX + token.decode("ascii")


def decrypt_to_dict(content: str) -> dict[str, Any]:
    """Decrypt an encrypted string (with magic prefix) back to a dict."""
    if not is_encrypted(content):
        raise ValueError("Content is not encrypted (missing magic prefix)")
    key = get_or_create_key()
    fernet = Fernet(key)
    token = content[len(MAGIC_PREFIX) :].encode("ascii")
    try:
        json_bytes = fernet.decrypt(token)
    except InvalidToken as err:
        raise ValueError(
            "Decryption failed — wrong key or corrupted data. "
            "Check that ~/.m4b/master.key matches the key used to encrypt."
        ) from err
    return json.loads(json_bytes)


def encrypt_file(filepath: str) -> None:
    """Encrypt a plaintext JSON config file in-place (atomic)."""
    if is_file_encrypted(filepath):
        logger.debug("%s is already encrypted, skipping", filepath)
        return

    logger.info("Encrypting config file: %s", filepath)
    with open(filepath) as f:
        data = json.load(f)

    encrypted_content = encrypt_dict(data)
    _atomic_write(filepath, encrypted_content)


def decrypt_file(filepath: str) -> None:
    """Decrypt an encrypted config file back to plaintext JSON (atomic)."""
    if not is_file_encrypted(filepath):
        logger.debug("%s is not encrypted, skipping", filepath)
        return

    logger.info("Decrypting config file: %s", filepath)
    with open(filepath) as f:
        content = f.read()

    data = decrypt_to_dict(content)
    _atomic_write(filepath, json.dumps(data, indent=4))


def _atomic_write(filepath: str, content: str) -> None:
    """Write *content* to *filepath* atomically via temp file + os.replace()."""
    dir_name = os.path.dirname(os.path.abspath(filepath))
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as tmp_file:
            tmp_file.write(content)
        os.replace(tmp_path, filepath)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def ensure_config_encrypted(filepath: str) -> None:
    """Ensure a config file is encrypted. Migrates plaintext files automatically."""
    if not os.path.isfile(filepath):
        return
    if is_file_encrypted(filepath):
        logger.debug("Config %s is already encrypted", filepath)
        return

    logger.info("Migrating plaintext config to encrypted: %s", filepath)
    encrypt_file(filepath)
