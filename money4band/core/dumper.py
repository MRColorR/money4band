from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any

from money4band.core.crypto import encrypt_dict, is_file_encrypted

logger = logging.getLogger(__name__)


def write_json(data: dict[str, Any], filename: str) -> None:
    """Atomically write *data* to a JSON file.

    Uses write-to-temp + ``os.replace`` to prevent corruption on crash or
    power loss.  If *filename* already exists and is encrypted, the new data
    is written back in encrypted form.
    """
    try:
        should_encrypt = os.path.isfile(filename) and is_file_encrypted(filename)

        dir_name = os.path.dirname(os.path.abspath(filename))
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as tmp_file:
                if should_encrypt:
                    tmp_file.write(encrypt_dict(data))
                else:
                    json.dump(data, tmp_file, indent=4)
            os.replace(tmp_path, filename)
        except BaseException:
            # Clean up temp file on any failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        logger.info("Data written to %s successfully!", filename)
    except Exception as e:
        logger.error("Error writing to %s: %s", filename, e)
        raise
