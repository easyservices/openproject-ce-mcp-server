from __future__ import annotations

import pytest

from openproject_ce_mcp_server.client import OpenProjectClient
from openproject_ce_mcp_server.config import Settings
from openproject_ce_mcp_server.tools_generic_api import _expand_path, _indexed_operations, _operations, _query_items


def test_operations_read_standard_openapi_v3_paths_and_resolve_schemas() -> None:
    operations = _operations(
        {
            "paths": {
                "/api/v3": {"get": {"operationId": "view_root", "summary": "View root"}},
                "/api/v3/users/{id}": {
                    "parameters": [{"name": "id", "in": "path", "required": True}],
                    "get": {"operationId": "view_user", "parameters": []},
                    "trace": {"operationId": "disallowed_method"},
                },
                "/not-api": {"get": {"operationId": "not_openproject"}},
            },
            "components": {"schemas": {}},
        }
    )
    assert [operation["operation_id"] for operation in operations] == ["view_root", "view_user"]
    assert operations[1]["parameters"][0]["name"] == "id"


def test_normalized_operations_and_operation_id_index_are_cached_per_client(monkeypatch) -> None:
    client = OpenProjectClient(
        Settings.from_env(
            {"OPENPROJECT_BASE_URL": "https://op.example.test", "OPENPROJECT_API_TOKEN": "test-token"}
        )
    )
    client._api_specification = {
        "paths": {"/api/v3/projects": {"get": {"operationId": "view_projects"}}},
    }
    original_operations = _operations
    calls = 0

    def count_operations(specification):
        nonlocal calls
        calls += 1
        return original_operations(specification)

    monkeypatch.setattr("openproject_ce_mcp_server.tools_generic_api._operations", count_operations)
    first = _indexed_operations(client)
    second = _indexed_operations(client)

    assert first is second
    assert calls == 1
    assert second[1]["view_projects"] is second[0][0]


def test_path_parameters_are_encoded_and_cannot_escape_the_api() -> None:
    assert _expand_path("/api/v3/projects/{id}", {"id": "team/a?x"}) == "/api/v3/projects/team%2Fa%3Fx"
    with pytest.raises(ValueError, match="Missing path parameter"):
        _expand_path("/api/v3/projects/{id}", None)
    with pytest.raises(ValueError, match="Unexpected path parameter"):
        _expand_path("/api/v3/projects", {"id": 4})


def test_query_parameters_keep_openproject_json_filter_syntax() -> None:
    assert _query_items({"filters": [{"status": {"operator": "=", "values": [1]}}], "pageSize": 25}) == [
        ("filters", '[{"status":{"operator":"=","values":[1]}}]'),
        ("pageSize", "25"),
    ]
