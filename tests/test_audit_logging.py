from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from openproject_ce_mcp_server.config import ConfigError, Settings, configure_logging
from openproject_ce_mcp_server.logging_support import emit_audit_record, make_tool_call_record


def test_audit_rotation_settings_come_from_environment() -> None:
    settings = Settings.from_env(
        {
            "OPENPROJECT_BASE_URL": "https://op.example.test",
            "OPENPROJECT_API_TOKEN": "test-token",
            "MCP_AUDIT_LOG_FILE": "/tmp/openproject-audit/events.jsonl",
            "MCP_AUDIT_LOG_MAX_BYTES": "2048",
            "MCP_AUDIT_LOG_BACKUP_COUNT": "3",
        }
    )
    assert settings.audit_log_file == "/tmp/openproject-audit/events.jsonl"
    assert settings.audit_log_max_bytes == 2048
    assert settings.audit_log_backup_count == 3


def test_audit_rotation_rejects_unreasonably_small_limit() -> None:
    with pytest.raises(ConfigError):
        Settings.from_env(
            {
                "OPENPROJECT_BASE_URL": "https://op.example.test",
                "OPENPROJECT_API_TOKEN": "test-token",
                "MCP_AUDIT_LOG_MAX_BYTES": "16",
            }
        )


def test_audit_log_rotates_at_configured_size_and_retains_user_id(tmp_path: Path) -> None:
    audit_path = tmp_path / "logs" / "audit.jsonl"
    logger = logging.getLogger("openproject_mcp.audit")
    previous_handlers = list(logger.handlers)
    try:
        for handler in previous_handlers:
            logger.removeHandler(handler)
        configure_logging("WARNING", audit_file=str(audit_path), audit_max_bytes=1024, audit_backup_count=2)
        record = make_tool_call_record(
            user_id="713",
            tool="list_projects",
            status="success",
            duration_ms=8,
            error_code=None,
            layer=None,
            http_requests=1,
            project_scope=None,
            policy_decision=None,
            request_id="req-1",
        )
        for _ in range(8):
            emit_audit_record(record, level=logging.INFO)

        assert audit_path.exists()
        rotated = Path(f"{audit_path}.1")
        assert rotated.exists()
        events = [json.loads(line) for path in (audit_path, rotated) for line in path.read_text().splitlines()]
        assert events
        assert all(event["user_id"] == "713" for event in events)
        assert all(event["tool"] == "list_projects" for event in events)
        assert all(event["schema_version"] == 2 for event in events)
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            if handler not in previous_handlers:
                handler.close()
        for handler in previous_handlers:
            logger.addHandler(handler)
