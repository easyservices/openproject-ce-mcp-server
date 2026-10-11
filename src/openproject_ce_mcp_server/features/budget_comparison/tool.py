"""MCP tool for planned-versus-consumed project budget reporting."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context

from ...app.errors import ProjectScopeDeniedError
from ...app.policies.project_policy import ensure_project_read_allowed
from ...tools_runtime import _client_from_context, register_tool


@register_tool
async def compare_project_budgets(
    ctx: Context,
    project_ids: list[int],
    include_subprojects: bool = True,
) -> dict[str, Any]:
    """Compare planned budgets and actual costs for project IDs and optionally their descendants.

    Projects without the current OpenProject user's view_budgets,
    view_cost_rates, and view_hourly_rates permissions are excluded.
    `remaining` is planned minus
    spent; the percentage is undefined (null) for a zero budget.
    """
    if not project_ids or len(project_ids) > 50 or any(type(item) is not int or item < 1 for item in project_ids):
        raise ValueError("project_ids must contain between 1 and 50 positive project IDs.")
    client = _client_from_context(ctx)
    user = await client.get_authenticated_user_id()
    # Resolve each root through the authenticated REST API first. This also
    # enforces instance and project visibility before the database read.
    for project_id in project_ids:
        await client.project.get(str(project_id))
    app_context: Any = ctx.request_context.lifespan_context
    repository = getattr(app_context, "budget_repository", None)
    if repository is None:
        raise RuntimeError("Budget comparison is not configured.")
    rows = await repository.compare(project_ids, int(user), include_subprojects)
    output = []
    for row in rows:
        try:
            ensure_project_read_allowed(
                {"id": row["id"], "identifier": row["identifier"]},
                project_ref=str(row["id"]),
                settings=app_context.settings,
                project_id_to_identifier={},
            )
        except ProjectScopeDeniedError:
            continue
        planned = float(row["planned"])
        spent = float(row["spent"])
        output.append(
            {
                "project_id": row["id"],
                "project_name": row["name"],
                "parent_id": row["parent_id"],
                "depth": row["depth"],
                "planned": planned,
                "spent": spent,
                "remaining": planned - spent,
                "consumed_percent": (spent / planned * 100) if planned else None,
            }
        )
    return {
        "projects": output,
        "total": {
            "planned": sum(item["planned"] for item in output),
            "spent": sum(item["spent"] for item in output),
            "remaining": sum(item["remaining"] for item in output),
        },
    }
