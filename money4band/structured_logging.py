from __future__ import annotations

"""Structured JSON logging formatter for M4B log files."""

import json
import logging
import time
import uuid
from typing import Any

# One id per process run, stamped on every JSON log line so multiple runs
# writing to the same rotated file remain distinguishable. (A contextvar
# API used to live here, but nothing ever propagated per-operation ids -
# the value was set once at startup and never changed.)
RUN_ID: str = uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# JSON log formatter
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    Fields: timestamp, level, logger, message, module, funcName, lineno,
    run_id (constant per process - see :data:`RUN_ID`).
    Extra dict keys from ``record.__dict__`` prefixed with ``extra.`` are included.
    """

    _BUILTIN_ATTRS = frozenset(
        logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
    ) | {
        "message",
        "asctime",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        record.message = record.getMessage()

        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt)
            if self.datefmt
            else time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }

        payload["run_id"] = RUN_ID

        # Append any extra keys the caller attached via `logger.info("...", extra={...})`
        for key, val in record.__dict__.items():
            if key not in self._BUILTIN_ATTRS:
                payload[f"extra.{key}"] = val

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            payload["exception"] = record.exc_text

        return json.dumps(payload, default=str, ensure_ascii=False)
