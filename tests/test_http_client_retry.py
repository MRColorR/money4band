"""Tests for the status-forcelist retry wrapper in ``http_client``.

P1-5: ``get_client()`` retries on 429 / 5xx responses for every method
(GET, POST, PUT, DELETE), with exponential back-off. The audit specifically
called out that POST was excluded from retries; the wrapper applied here is
method-agnostic and covers all of them.
"""

from __future__ import annotations

import httpx
import pytest

from money4band.network import http_client


def _make_response(status: int) -> httpx.Response:
    return httpx.Response(status, content=b"x")


class _RecordingInner(httpx.BaseTransport):
    """Fake transport that returns a scripted sequence of responses."""

    def __init__(self, statuses: list[int]) -> None:
        self._statuses = list(statuses)
        self.calls: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if not self._statuses:
            raise AssertionError("transport exhausted scripted responses")
        return _make_response(self._statuses.pop(0))

    def close(self) -> None:
        pass


@pytest.fixture
def no_sleep(monkeypatch):
    """Drop real sleeps so retry tests stay sub-second."""
    sleeps: list[float] = []
    monkeypatch.setattr(http_client.time, "sleep", sleeps.append)
    return sleeps


def _client(inner: httpx.BaseTransport, max_retries: int = 3) -> httpx.Client:
    transport = http_client._StatusRetryTransport(
        inner=inner,
        max_retries=max_retries,
        backoff_factor=http_client.BACKOFF_FACTOR,
        status_forcelist=http_client._STATUS_FORCELIST,
        sleep=lambda _s: None,
    )
    return httpx.Client(transport=transport)


class TestStatusRetryTransport:
    def test_post_retries_on_503_then_succeeds(self):
        inner = _RecordingInner([503, 503, 200])
        client = _client(inner)

        resp = client.post("http://x/batch", json={})

        assert resp.status_code == 200
        # 1 initial + 2 retries = 3 calls.
        assert len(inner.calls) == 3
        assert all(c.method == "POST" for c in inner.calls)

    def test_get_retries_on_429_then_succeeds(self):
        inner = _RecordingInner([429, 200])
        client = _client(inner)

        resp = client.get("http://x/")
        assert resp.status_code == 200
        assert len(inner.calls) == 2

    def test_exhausts_retries_and_returns_last_response(self):
        inner = _RecordingInner([502, 502, 502, 502])
        client = _client(inner, max_retries=3)

        resp = client.post("http://x/", json={})

        assert resp.status_code == 502
        # 1 initial + 3 retries = 4 calls (max_retries=3).
        assert len(inner.calls) == 4

    def test_non_forcelist_4xx_not_retried(self):
        inner = _RecordingInner([404])
        client = _client(inner)

        resp = client.get("http://x/")
        assert resp.status_code == 404
        assert len(inner.calls) == 1

    def test_2xx_not_retried(self):
        inner = _RecordingInner([200])
        client = _client(inner)

        resp = client.get("http://x/")
        assert resp.status_code == 200
        assert len(inner.calls) == 1

    def test_put_and_delete_also_retried(self):
        for method in ("PUT", "DELETE"):
            inner = _RecordingInner([500, 500, 204])
            client = _client(inner)
            resp = client.request(method, "http://x/")
            assert resp.status_code == 204
            assert len(inner.calls) == 3
            assert all(c.method == method for c in inner.calls)

    def test_backoff_sleeps_exponentially(self, monkeypatch):
        sleeps: list[float] = []
        inner = _RecordingInner([503, 503, 503, 200])
        transport = http_client._StatusRetryTransport(
            inner=inner,
            max_retries=3,
            backoff_factor=1.0,
            status_forcelist=http_client._STATUS_FORCELIST,
            sleep=sleeps.append,
        )
        client = httpx.Client(transport=transport)

        resp = client.post("http://x/", json={})
        assert resp.status_code == 200
        # 3 retries -> 1, 2, 4 second waits.
        assert sleeps == [1.0, 2.0, 4.0]


class TestGetClientWiring:
    def test_get_client_uses_status_retry_transport(self):
        client = http_client.get_client()
        assert isinstance(client._transport, http_client._StatusRetryTransport)
