from __future__ import annotations

import logging
import os

import httpx

from money4band.network import http_client
from money4band.network.http_client import get_client

logger = logging.getLogger(__name__)

# Longer timeout for large file downloads (Docker Desktop ~600 MB)
_DOWNLOAD_TIMEOUT = 300  # seconds


def download_file(url: str, dest_path: str) -> None:
    """Download a file from *url* and save it to *dest_path*.

    Uses the shared HTTP client (retry + back-off) from :mod:`utils.http_client`.
    A generous timeout is applied because some installers are several hundred MB.

    Raises:
        httpx.HTTPError: On any network / HTTP error.
        OSError: If writing to *dest_path* fails.
    """
    client = get_client()
    timeout = max(_DOWNLOAD_TIMEOUT, http_client.REQUEST_TIMEOUT)
    try:
        logger.info("Starting download from %s", url)
        with client.stream("GET", url, timeout=timeout) as response:
            response.raise_for_status()

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            with open(dest_path, "wb") as file:
                for chunk in response.iter_bytes(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
        logger.info("File downloaded successfully from %s to %s", url, dest_path)
    except httpx.HTTPError as e:
        logger.error("Download failed for %s: %s", url, e)
        raise
    except OSError as e:
        logger.error("Error writing file to %s: %s", dest_path, e)
        raise
