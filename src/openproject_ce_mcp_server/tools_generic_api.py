"""Generic OpenAPI operations for endpoints without a dedicated MCP tool."""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from mcp.server.mcpserver import Context, MCPServer

from .client import OpenProjectClient, OpenProjectError, QueryParamValue
from .tools_runtime import _categorize_tool_errors, _client_from_context

_ALLOWED_METHODS = {"GET", "POST", "PATCH", "PUT", "DELETE", "HEAD", "OPTIONS"}
_READ_METHODS = {"GET", "HEAD", "OPTIONS"}


def _operation_id(method: str, operation: dict[str, Any], path: str) -> str:
    return str(operation.get("operationId") or f"{method.lower()} {path}")


def _resolve_schema_reference(specification: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    reference = schema.get("$ref")
    if not isinstance(reference, str) or not reference.startswith("#/components/schemas/"):
        return schema
    target = specification.get("components", {}).get("schemas", {}).get(reference.rsplit("/", 1)[-1])
    return target if isinstance(target, dict) else schema


def _operations(specification: dict[str, Any]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for path, path_item in specification["paths"].items():
        if path not in {"/api/v3"} and (not isinstance(path, str) or not path.startswith("/api/v3/")):
            continue
        if not isinstance(path_item, dict):
            continue
        for raw_method, operation in path_item.items():
            method = str(raw_method).upper()
            if method not in _ALLOWED_METHODS or not isinstance(operation, dict):
                continue
            parameters = [*path_item.get("parameters", []), *operation.get("parameters", [])]
            request_body = operation.get("requestBody", {})
            content = request_body.get("content", {})
            json_schema = content.get("application/json", {}).get("schema", {})
            if not json_schema:
                json_schema = content.get("application/hal+json", {}).get("schema", {})
            if not json_schema:
                json_schema = content.get("multipart/form-data", {}).get("schema", {})
            if isinstance(json_schema, dict):
                json_schema = _resolve_schema_reference(specification, json_schema)
            operations.append(
                {
                    "operation_id": _operation_id(method, operation, path),
                    "method": method,
                    "path": path,
                    "summary": operation.get("summary", ""),
                    "parameters": [
                        {
                            "name": item.get("name"),
                            "in": item.get("in"),
                            "required": bool(item.get("required")),
                            "description": item.get("description", ""),
                        }
                        for item in parameters
                        if isinstance(item, dict)
                    ],
                    "request_body_required": bool(request_body.get("required")),
                    "request_body_content_types": sorted(content),
                    "request_body_type": json_schema.get("type"),
                    "request_body_schema_ref": json_schema.get("$ref"),
                    "request_body_properties": sorted(json_schema.get("properties", {}).keys()),
                    "request_body_required_fields": json_schema.get("required", []),
                }
            )
    return sorted(operations, key=lambda item: (item["path"], item["method"]))


def _indexed_operations(
    client: OpenProjectClient,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Build and retain normalized operations once for this client's spec."""
    cached = client._generic_api_operation_index
    if cached is None:
        operations = _operations(client._api_specification or {})
        cached = (operations, {item["operation_id"]: item for item in operations})
        client._generic_api_operation_index = cached
    return cached


def _query_items(query: dict[str, Any] | None) -> list[tuple[str, QueryParamValue]] | None:
    if not query:
        return None
    pairs: list[tuple[str, QueryParamValue]] = []
    for key, value in query.items():
        if isinstance(value, dict) or (
            isinstance(value, list) and any(isinstance(item, (dict, list)) for item in value)
        ):
            pairs.append((key, json.dumps(value, separators=(",", ":"), ensure_ascii=False)))
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            if item is None:
                continue
            elif isinstance(item, bool):
                encoded = str(item).lower()
            else:
                encoded = str(item)
            pairs.append((key, encoded))
    return pairs


def _expand_path(path: str, values: dict[str, str | int] | None) -> str:
    values = values or {}
    expected = []
    output = path
    while "{" in output:
        start = output.find("{")
        end = output.find("}", start + 1)
        if end < 0:
            raise ValueError("OpenAPI operation path contains an invalid parameter placeholder.")
        name = output[start + 1 : end]
        if not name or name not in values:
            raise ValueError(f"Missing path parameter: {name or '(empty)'}.")
        expected.append(name)
        output = output[:start] + quote(str(values[name]), safe="") + output[end + 1 :]
    unknown = set(values) - set(expected)
    if unknown:
        raise ValueError(f"Unexpected path parameter(s): {', '.join(sorted(unknown))}.")
    if output != "/api/v3" and not output.startswith("/api/v3/"):
        raise ValueError("Operation path must remain inside the OpenProject API v3.")
    if ".." in output.split("/"):
        raise ValueError("Operation path must remain inside the OpenProject API v3.")
    return output


def register_generic_api_tools(mcp: MCPServer, client_for_context: Callable[[Context], OpenProjectClient]) -> None:
    def register_tool(fn):
        return mcp.tool(structured_output=False)(_categorize_tool_errors(fn))

    @register_tool
    async def list_api_operations(
        ctx: Context,
        query: str = "",
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Browse OpenProject API v3 operations from this instance's OpenAPI specification."""
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("offset must be non-negative and limit must be between 1 and 100.")
        client: OpenProjectClient = client_for_context(ctx)
        await client.get_api_specification()
        operations, _ = _indexed_operations(client)
        needle = query.strip().casefold()
        if needle:
            operations = [
                operation
                for operation in operations
                if needle
                in " ".join(
                    [operation["operation_id"], operation["method"], operation["path"], operation["summary"]]
                ).casefold()
            ]
        return {
            "total": len(operations),
            "offset": offset,
            "next_offset": offset + limit if offset + limit < len(operations) else None,
            "operations": operations[offset : offset + limit],
        }

    @register_tool
    async def call_api_operation(
        ctx: Context,
        operation_id: str,
        path_parameters: dict[str, str | int] | None = None,
        query_parameters: dict[str, Any] | None = None,
        body: Any = None,
        multipart_fields: dict[str, Any] | None = None,
        multipart_files: list[dict[str, str]] | None = None,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Call an OpenAPI operation by ID; mutations require confirm=true."""
        client: OpenProjectClient = client_for_context(ctx)
        await client.get_api_specification()
        _, operations_by_id = _indexed_operations(client)
        operation = operations_by_id.get(operation_id)
        if operation is None:
            raise ValueError("Unknown operation ID; use list_api_operations to find available operations.")
        method = operation["method"]
        path = _expand_path(operation["path"], path_parameters)
        is_write = method not in _READ_METHODS
        if is_write and not confirm:
            return {
                "confirmed": False,
                "operation_id": operation_id,
                "method": method,
                "path": path,
                "query_parameters": query_parameters or {},
                "body": body,
                "multipart_field_names": sorted((multipart_fields or {}).keys()),
                "multipart_file_names": [item.get("file_name", "") for item in multipart_files or []],
                "message": "Review this request, then repeat it with confirm=true to execute the mutation.",
            }
        request_types = operation["request_body_content_types"]
        multipart: list[tuple[str, tuple[str | None, str | bytes, str]]] = []
        if multipart_fields or multipart_files:
            if "multipart/form-data" not in request_types:
                raise ValueError("This operation does not accept multipart/form-data.")
            for name, value in (multipart_fields or {}).items():
                is_json_part = isinstance(value, (dict, list)) or name == "metadata"
                if isinstance(value, (dict, list)):
                    encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
                elif value is None:
                    encoded = ""
                else:
                    encoded = str(value)
                part_type = "application/json" if is_json_part else "text/plain; charset=utf-8"
                multipart.append((name, (None, encoded, part_type)))
            total_bytes = 0
            for item in multipart_files or []:
                required = {"field_name", "file_name", "content_type", "content_base64"}
                if required - item.keys():
                    raise ValueError(
                        "Each multipart file requires field_name, file_name, content_type, and content_base64."
                    )
                try:
                    data = base64.b64decode(item["content_base64"], validate=True)
                except (ValueError, binascii.Error) as exc:
                    raise ValueError("content_base64 must contain valid base64 data.") from exc
                total_bytes += len(data)
                if total_bytes > 2 * 1024 * 1024:
                    raise ValueError("Combined multipart file data cannot exceed 2 MiB.")
                multipart.append((item["field_name"], (item["file_name"], data, item["content_type"])))
        elif operation["request_body_required"] and body is None:
            raise ValueError("This operation requires a request body.")
        elif body is not None and not ({"application/json", "application/hal+json"} & set(request_types)):
            raise ValueError("This operation's request body requires a content type not supported by this tool.")

        try:
            result = await client.call_api_operation(
                method,
                path,
                params=_query_items(query_parameters),
                json_body=body,
                multipart=multipart or None,
                content_type="application/hal+json" if "application/hal+json" in request_types else None,
            )
        except OpenProjectError as exc:
            exc.operation_id = operation_id
            raise
        return {"confirmed": True, "operation_id": operation_id, "method": method, "path": path, **result}


def register_generic_api(mcp: MCPServer) -> None:
    # A tiny adapter keeps this module's operation logic independent from MCP's
    # Context implementation while preserving the normal request-scoped client.
    def resolve_client(ctx: Context) -> OpenProjectClient:
        return _client_from_context(ctx)

    register_generic_api_tools(mcp, resolve_client)
