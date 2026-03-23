from __future__ import annotations

"""Structured JSON logging formatter and correlation-ID context for M4B operations."""

import contextvars
import json
import logging
import time
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# Correlation ID — one per logical operation (setup, start, generate, …)
# ---------------------------------------------------------------------------

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "m4b_correlation_id", default=""
)


def new_correlation_id() -> str:
    """Generate and set a new correlation ID for the current context."""
    cid = uuid.uuid4().hex[:12]
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    """Return the current correlation ID (empty string if none set)."""
    return _correlation_id.get()


def set_correlation_id(cid: str) -> None:
    """Explicitly set the correlation ID for the current context."""
    _correlation_id.set(cid)


# ---------------------------------------------------------------------------
# JSON log formatter
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    Fields: timestamp, level, logger, message, correlation_id, module, funcName, lineno.
    Extra dict keys from ``record.__dict__`` prefixed with ``extra.`` are included.
    """

    _BUILTIN_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
        "message", "asctime", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        record.message = record.getMessage()

        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt) if self.datefmt else
            time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }

        cid = get_correlation_id()
        if cid:
            payload["correlation_id"] = cid

        # Append any extra keys the caller attached via `logger.info("…", extra={…})`
        for key, val in record.__dict__.items():
            if key not in self._BUILTIN_ATTRS:
                payload[f"extra.{key}"] = val

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            payload["exception"] = record.exc_text

        return json.dumps(payload, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Helper: attach JSON formatter to file handler
# ---------------------------------------------------------------------------


def enable_json_file_logging(file_handler: logging.Handler) -> None:
    """Replace the formatter on *file_handler* with :class:`JSONFormatter`."""
    file_handler.setFormatter(JSONFormatter())
