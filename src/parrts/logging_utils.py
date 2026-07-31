"""Structured JSON logging for parrts + backend surfaces."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    cid = _correlation_id.get()
    if not cid:
        cid = uuid.uuid4().hex[:12]
        _correlation_id.set(cid)
    return cid


def set_correlation_id(cid: Optional[str] = None) -> str:
    value = cid or uuid.uuid4().hex[:12]
    _correlation_id.set(value)
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None) or get_correlation_id(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key in ("event", "duration_ms", "path", "method", "status", "extra"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)


def configure_logging(level: Optional[str] = None, json_logs: Optional[bool] = None) -> None:
    """Idempotent logging setup. JSON when PARRTS_JSON_LOGS=1 (default in prod-ish)."""
    if json_logs is None:
        json_logs = os.environ.get("PARRTS_JSON_LOGS", "1") not in {"0", "false", "False"}
    lvl = getattr(logging, (level or os.environ.get("LOG_LEVEL", "INFO")).upper(), logging.INFO)

    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
    root.addHandler(handler)
    root.setLevel(lvl)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class log_span:
    """Context manager that logs duration for an event."""

    def __init__(self, logger: logging.Logger, event: str, **extra: Any) -> None:
        self.logger = logger
        self.event = event
        self.extra = extra
        self.t0 = 0.0

    def __enter__(self) -> "log_span":
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        ms = (time.perf_counter() - self.t0) * 1000
        self.logger.info(
            self.event,
            extra={
                "event": self.event,
                "duration_ms": round(ms, 2),
                "extra": self.extra,
                "correlation_id": get_correlation_id(),
            },
        )
