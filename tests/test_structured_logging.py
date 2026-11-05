"""Tests for structured_logging module: JSON formatter and run id."""

from __future__ import annotations

import json
import logging

import pytest

from money4band.structured_logging import RUN_ID, JSONFormatter


class TestRunId:
    def test_run_id_shape(self):
        assert isinstance(RUN_ID, str)
        assert len(RUN_ID) == 12


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
        for key in (
            "timestamp",
            "level",
            "logger",
            "message",
            "module",
            "funcName",
            "lineno",
            "run_id",
        ):
            assert key in parsed

    def test_message_is_formatted(self, formatter, record):
        parsed = json.loads(formatter.format(record))
        assert parsed["message"] == "hello world"

    def test_level_name(self, formatter, record):
        parsed = json.loads(formatter.format(record))
        assert parsed["level"] == "INFO"

    def test_run_id_stamped(self, formatter, record):
        parsed = json.loads(formatter.format(record))
        assert parsed["run_id"] == RUN_ID

    def test_exception_included(self, formatter):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="fail",
                args=(),
                exc_info=sys.exc_info(),
            )
        parsed = json.loads(formatter.format(record))
        assert "exception" in parsed
        assert "boom" in parsed["exception"]
