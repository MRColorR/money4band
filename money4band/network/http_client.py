from __future__ import annotations

"""Shared HTTP client factory with retry-on-failure and configurable timeouts.

Every module that makes HTTP requests should use ``get_client()`` from here
instead of creating bare ``httpx.get()`` calls.  This guarantees consistent
retry behaviour, timeouts, and back-off across the whole codebase.

Retry policy
------------

Two layers, both method-agnostic (apply to GET, POST, PUT, DELETE alike):

1. **Connection retries** - handled by the underlying ``httpx.HTTPTransport``
   (`retries=MAX_RETRIES`). Cover socket errors, DNS failures, TLS handshake
   resets, etc.
2. **Status-code retries** - handled by an ``httpx`` event hook installed in
   ``get_client``. When a response status is in ``_STATUS_FORCELIST``
   (429 / 5xx), the request is re-issued up to ``MAX_RETRIES`` times with
   exponential back-off (``BACKOFF_FACTOR * 2**attempt`` seconds).

Idempotency note: callers using POST for read-only queries (e.g. the
``ip-api.com/batch`` batch lookup) get retries safely because the endpoint
is side-effect-free. Callers issuing POSTs against state-mutating endpoints
should bypass this client or design their handler to tolerate a retry.
"""

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)
# -- Defaults (overridable via configure()) ------------------------------
REQUEST_TIMEOUT: int = 15  # seconds
MAX_RETRIES: int = 3
BACKOFF_FACTOR: float = 1.0  # -> 1 s, 2 s, 4 s between retries
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


class _StatusRetryTransport(httpx.BaseTransport):
    """Wraps a transport to retry on status-forcelist responses.

    httpx's built-in ``retries=`` on ``HTTPTransport`` only retries on
    connection-level errors. This wrapper adds response-status retries so
    that 429 / 5xx replies trigger an exponential-back-off retry - for
    every method, not just GET.
    """

    def __init__(
        self,
        inner: httpx.BaseTransport,
        max_retries: int,
        backoff_factor: float,
        status_forcelist: tuple[int, ...],
        sleep: Any = time.sleep,
    ) -> None:
        self._inner = inner
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._status_forcelist = status_forcelist
        self._sleep = sleep

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        attempts = 0
        while True:
            response = self._inner.handle_request(request)
            if (
                response.status_code not in self._status_forcelist
                or attempts >= self._max_retries
            ):
                return response
            response.close()
            delay = self._backoff_factor * (2**attempts)
            logger.debug(
                "HTTP %s %s -> %s; retry %d/%d in %.1fs",
                request.method,
                request.url,
                response.status_code,
                attempts + 1,
                self._max_retries,
                delay,
            )
            self._sleep(delay)
            attempts += 1

    def close(self) -> None:
        self._inner.close()


def get_client() -> httpx.Client:
    """Return an :class:`httpx.Client` wired with retry + back-off.

    Combines transport-level connection retries with response-status retries
    on the ``_STATUS_FORCELIST`` for every HTTP method.
    """
    inner = httpx.HTTPTransport(retries=MAX_RETRIES)
    transport = _StatusRetryTransport(
        inner=inner,
        max_retries=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=_STATUS_FORCELIST,
    )
    return httpx.Client(
        transport=transport,
        timeout=httpx.Timeout(REQUEST_TIMEOUT),
        follow_redirects=True,
    )
