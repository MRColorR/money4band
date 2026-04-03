from __future__ import annotations

"""Shared HTTP session factory with retry-on-failure and configurable timeouts.

Every module that makes HTTP requests should use ``get_session()`` from here
instead of creating bare ``requests.get()`` calls.  This guarantees consistent
retry behaviour, timeouts, and back-off across the whole codebase.
"""

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)
# ── Defaults (overridable via configure()) ──────────────────────────────
REQUEST_TIMEOUT: int = 15  # seconds
MAX_RETRIES: int = 3
BACKOFF_FACTOR: float = 1.0  # → 1 s, 2 s, 4 s between retries
_STATUS_FORCELIST: tuple[int, ...] = (429, 500, 502, 503, 504)


def configure(m4b_config: dict[str, Any]) -> None:
    """Read *timeout* and *max_retries* from the ``system`` section of m4b-config."""
    global REQUEST_TIMEOUT, MAX_RETRIES  # noqa: PLW0603
    system = m4b_config.get("system", {})
    REQUEST_TIMEOUT = system.get("registry_request_timeout", REQUEST_TIMEOUT)
    MAX_RETRIES = system.get("registry_max_retries", MAX_RETRIES)
    logger.debug(
        "HTTP client configured: timeout=%ss, max_retries=%s",
        REQUEST_TIMEOUT,
        MAX_RETRIES,
    )


def get_session() -> requests.Session:
    """Return a :class:`requests.Session` wired with retry + back-off."""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=list(_STATUS_FORCELIST),
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
