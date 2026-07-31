"""Tests for structured logging helpers."""

from __future__ import annotations

import json
import logging

from parrts.logging_utils import JsonFormatter, get_correlation_id, set_correlation_id


def test_correlation_id_set_and_get():
    cid = set_correlation_id("abc123deadbe")
    assert cid == "abc123deadbe"
    assert get_correlation_id() == "abc123deadbe"


def test_json_formatter_emits_json():
    set_correlation_id("cid-test-1")
    fmt = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.event = "unit.test"
    record.duration_ms = 1.5
    out = fmt.format(record)
    data = json.loads(out)
    assert data["msg"] == "hello"
    assert data["event"] == "unit.test"
    assert data["correlation_id"] == "cid-test-1"
    assert data["level"] == "INFO"
