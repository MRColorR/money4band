"""Tests for structured_logging module: JSON formatter and correlation IDs."""

from __future__ import annotations

import json
import logging

import pytest

from money4band.structured_logging import (
    JSONFormatter,
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)


class TestCorrelationId:
    def test_new_returns_string(self):
        cid = new_correlation_id()
        assert isinstance(cid, str)
        assert len(cid) == 12

    def test_get_returns_current(self):
        cid = new_correlation_id()
        assert get_correlation_id() == cid

    def test_set_explicit(self):
        set_correlation_id("abc123")
        assert get_correlation_id() == "abc123"

    def test_successive_calls_differ(self):
        a = new_correlation_id()
        b = new_correlation_id()
        assert a != b


class TestJSONFormatter:
    @pytest.fixture()
    def formatter(self):
        return JSONFormatter()

    @pytest.fixture()
    def record(self):
        return logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )

    def test_output_is_valid_json(self, formatter, record):
        output = formatter.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_contains_required_fields(self, formatter, record):
        parsed = json.loads(formatter.format(record))
        for key in ("timestamp", "level", "logger", "message", "module", "funcName", "lineno"):
            assert key in parsed

    def test_message_is_formatted(self, formatter, record):
        parsed = json.loads(formatter.format(record))
        assert parsed["message"] == "hello world"

    def test_level_name(self, formatter, record):
        parsed = json.loads(formatter.format(record))
        assert parsed["level"] == "INFO"

    def test_correlation_id_included_when_set(self, formatter, record):
        set_correlation_id("test-cid-123")
        parsed = json.loads(formatter.format(record))
        assert parsed["correlation_id"] == "test-cid-123"

    def test_correlation_id_absent_when_empty(self, formatter, record):
        set_correlation_id("")
        parsed = json.loads(formatter.format(record))
        assert "correlation_id" not in parsed

    def test_exception_included(self, formatter):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="test", level=logging.ERROR, pathname="test.py",
                lineno=1, msg="fail", args=(), exc_info=sys.exc_info(),
            )
        parsed = json.loads(formatter.format(record))
        assert "exception" in parsed
        assert "boom" in parsed["exception"]
