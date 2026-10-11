"""Structured stderr logging (OPM-2709).

`ToolCallLogRecord` is a closed, versioned schema for tool and authentication audit
events. It is built centrally so callers cannot accidentally add raw arguments
or assign a non-primitive value (e.g. raw tool kwargs, which could carry
a work-package body, `custom_fields`, or other caller-supplied data) without
a type-checker-visible change to this file. Every value is sourced from
something already known to be safe to log: a tool's own `__name__`, a
monotonic-clock duration, an exception's own `code`/`layer` class attributes
(app/errors.py), an HTTP-request counter, or the MCP protocol's own
per-call `request_id` -- never free-text exception messages, never kwargs,
never the API token/Authorization header (which never appears in a tool's
own kwargs at all -- see client.py's Settings-to-httpx.AsyncClient wiring).

`_JsonLogFormatter` renders BOTH structured audit records (passed via
`extra={"structured": record}`, never string-interpolated) and ordinary
free-text log calls from elsewhere in the codebase (the 8 modules with their
own `LOGGER.warning(...)`-style calls that predate this ticket) -- so
`OPENPROJECT_LOG_FORMAT=json` doesn't silently break existing log statements
that were never touched.
"""

from __future__ import annotations

import json
import logging
import traceback
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Literal, TypedDict


class ToolCallLogRecord(TypedDict):
    schema_version: int
    event_type: Literal["tool_call", "authentication"]
    user_id: str | None
    tool: str
    status: Literal["success", "error"]
    duration_ms: int
    error_code: str | None
    layer: str | None
    http_requests: int
    project_scope: str | None
    policy_decision: str | None
    request_id: str | None
    error_id: str | None
    error_category: str | None
    severity: str | None
    retryable: bool | None
    exception_type: str | None
    upstream_status: int | None
    retry_after_seconds: float | None
    operation_id: str | None
    stack_frames: list[dict[str, str | int]] | None


def safe_stack_frames(exception: BaseException, *, limit: int = 20) -> list[dict[str, str | int]]:
    """Return message-free traceback coordinates suitable for a central log."""
    frames: list[dict[str, str | int]] = []
    current: BaseException | None = exception
    depth = 0
    while current is not None and depth < 3 and len(frames) < limit:
        if depth:
            frames.append({"cause_type": type(current).__name__})
        for frame in traceback.extract_tb(current.__traceback__):
            frames.append({"file": Path(frame.filename).name, "line": int(frame.lineno or 0), "function": frame.name})
            if len(frames) >= limit:
                break
        current = current.__cause__ or current.__context__
        depth += 1
    return frames


def make_tool_call_record(
    *,
    tool: str,
    status: Literal["success", "error"],
    duration_ms: int,
    error_code: str | None,
    layer: str | None,
    http_requests: int,
    project_scope: str | None,
    policy_decision: str | None,
    request_id: str | None,
    user_id: str | None,
    error_id: str | None = None,
    error_category: str | None = None,
    severity: str | None = None,
    retryable: bool | None = None,
    upstream_status: int | None = None,
    retry_after_seconds: float | None = None,
    operation_id: str | None = None,
    exception: BaseException | None = None,
    event_type: Literal["tool_call", "authentication"] = "tool_call",
) -> ToolCallLogRecord:
    """Build the versioned safe audit schema from an exception and stable codes."""
    category = error_category or getattr(exception, "category", None)
    level = severity or getattr(exception, "severity", None)
    can_retry = retryable
    if can_retry is None and exception is not None:
        can_retry = getattr(exception, "retryable_override", None)
        if can_retry is None:
            can_retry = getattr(exception, "retryable", None)
    if status == "error" and category is None:
        category = "validation" if error_code == "VALIDATION_FAILED" else "internal"
    if status == "error" and level is None:
        level = "error" if category == "internal" else "warning"
    if status == "error" and can_retry is None:
        can_retry = False
    internal = category == "internal"
    return {
        "schema_version": 2,
        "event_type": event_type,
        "user_id": user_id,
        "tool": tool,
        "status": status,
        "duration_ms": duration_ms,
        "error_code": error_code,
        "layer": layer,
        "http_requests": http_requests,
        "project_scope": project_scope,
        "policy_decision": policy_decision,
        "request_id": request_id,
        "error_id": error_id,
        "error_category": category,
        "severity": level,
        "retryable": can_retry,
        "exception_type": type(exception).__name__ if exception else None,
        "upstream_status": upstream_status
        if upstream_status is not None
        else getattr(exception, "upstream_status", None),
        "retry_after_seconds": (
            retry_after_seconds if retry_after_seconds is not None else getattr(exception, "retry_after", None)
        ),
        "operation_id": operation_id or getattr(exception, "operation_id", None),
        "stack_frames": safe_stack_frames(exception) if internal and exception else None,
    }


class _JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        structured: ToolCallLogRecord | None = getattr(record, "structured", None)
        if structured is not None:
            payload: dict[str, Any] = {
                "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
                "level": record.levelname,
                "logger": record.name,
                **structured,
            }
        else:
            payload = {
                "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
        # LOGGER.exception(...) (the INTERNAL_ERROR sanitization backstop's own
        # local diagnostic, never sent to the client) attaches exc_info -- the
        # JSON formatter must surface it same as the plain-text formatter does
        # by default, or an operator loses the one stack trace the sanitized
        # client-facing error deliberately withholds.
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def build_formatter(log_format: str) -> logging.Formatter:
    if log_format == "json":
        return _JsonLogFormatter()
    return logging.Formatter("%(levelname)s %(name)s %(message)s")


def emit_audit_record(record: ToolCallLogRecord, *, level: int) -> None:
    """Write directly to configured audit sinks without duplicating records
    into application or test capture handlers attached to the root logger."""
    logger = logging.getLogger("openproject_mcp.audit")
    event = logger.makeRecord(logger.name, level, "", 0, "tool_call", (), None, extra={"structured": record})
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler) and event.levelno >= handler.level:
            handler.acquire()
            try:
                handler.emit(event)
            finally:
                handler.release()
