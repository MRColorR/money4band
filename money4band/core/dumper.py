from __future__ import annotations

import argparse
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


if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Write data to a JSON file.")
    parser.add_argument(
        "--data", type=str, required=True, help="The data to write in JSON format"
    )
    parser.add_argument(
        "--filename", type=str, required=True, help="The filename to write the data to"
    )
    parser.add_argument(
        "--log-dir",
        default=os.path.join(script_dir, "logs"),
        help="Set the logging directory",
    )
    parser.add_argument(
        "--log-file", default=f"{script_name}.log", help="Set the logging file name"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    args = parser.parse_args()

    # Set logging level based on command-line arguments
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    # Start logging
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.log_dir, args.log_file),
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_level,
    )

    logger.info(f"Starting {script_name} script...")

    try:
        # Load the data from the command-line argument
        data = json.loads(args.data)

        # Write data to the specified filename
        write_json(data, args.filename)

        logger.info(f"{script_name} script completed successfully")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise
