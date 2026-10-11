---
name: openproject-ce-mcp-server
description: Use the openproject-ce-mcp-server MCP connector to inspect and manage OpenProject projects, work packages, time entries, costs, and budgets. Apply when OpenProject work should use this MCP server.
---

# OpenProject through the MCP connector

Use this skill when the user asks you to retrieve or change OpenProject data through `openproject-ce-mcp-server`.

## Connect and establish context

- Use the OpenProject MCP tools available in the current session. Do not claim to have queried the instance if those tools are unavailable or the call fails.
- If the connector is not available, consult the repository's [Codex setup](../codex.md) and [troubleshooting guide](../troubleshooting.md). For a remote Streamable HTTP server, the URL and server name are configured in the connector's `.env`; each Codex user supplies their OpenProject API token through `OPENPROJECT_API_TOKEN` in the local Codex environment.
- Begin an analysis with `get_current_user` to establish which OpenProject identity and permissions apply. Use that identity's visible projects and records; do not assume administrator access.
- If authentication fails, report the connector error and the specific next step. Never ask the user to paste an API token or `.env` contents into chat.
- When a read fails with `[PROJECT_SCOPE_DENIED]`, explain that the MCP server has its own fail-closed `OPENPROJECT_READ_PROJECTS` allowlist in addition to OpenProject permissions. Ask for the project identifier if needed; the server operator must add that identifier (or a deliberate glob) to the MCP server's `.env` and restart it. `*` permits all projects visible to the signed-in OpenProject user and should be used only when intended. Never suggest bypassing the scope with the generic API.

## Select tools and handle results

- Discover current tool names and schemas from the active MCP session. The server can gate tools by configuration, so do not assume every documented tool is enabled.
- If a dedicated create/read/update/delete tool is missing, check whether `list_api_operations` and `call_api_operation` are available. These generic tools are opt-in (`OPENPROJECT_ENABLE_GENERIC_API=true`) and expose operations advertised by the connected instance's OpenAPI specification.
- For a requested object creation through the generic API, search `list_api_operations` for the resource's collection `POST` operation. Read its operation ID, path parameters, required body schema, and documented response before calling it. Build the body only from the user's requirements and values actually obtained from OpenProject; ask for missing required values rather than inventing them. Do not assume that every OpenProject object has a create endpoint.
- Generic API support means using an operation the server advertises, not that every OpenProject feature is available over the API. Respect endpoint/method support and OpenProject edition limits. In particular, Community Edition does not provide API creation or modification for work-package types, statuses, workflows, enabled modules, or custom-field definitions; those are configured in the OpenProject web UI.
- Use `list_projects` to find a project, then `get_project` when its parent/ancestor context or detail is needed. Prefer project IDs returned by the connector over guessing identifiers.
- `list_types` accepts an optional project filter: omit `project` for instance-wide types; when specifying a project, it must be included in `OPENPROJECT_READ_PROJECTS`.
- For work-package questions, use `search_work_packages` for subject/ID searches, or `list_work_packages` with the appropriate project and status filters. Use `get_work_packages` for a known set of IDs where available. Request only fields needed for the task when a `select` argument is supported.
- For actual effort/cost data, use the available time-entry and cost tools and preserve their distinction: time spent, monetary cost, and budget are different measures. State units and date ranges in summaries.
- Paginated lists may be bounded. Check returned pagination/truncation information and fetch further pages when needed before presenting totals or claiming completeness.
- OpenProject permissions still apply per authenticated user. A missing record may be inaccessible; do not infer that it does not exist solely from an empty result.

## Compare project budgets

- Prefer `compare_project_budgets` when it is present. It is an optional PostgreSQL-backed module, enabled by server configuration, because the REST API does not currently provide all of the required totals.
- Supply the requested project IDs and include descendants only when the user asks to include subprojects. Clearly identify which project rows were included and avoid double-counting a parent aggregate if the returned result already includes separate descendants.
- Explain the measure as lifetime planned budget compared with lifetime consumed cost, using the returned amounts and currency/units. Do not describe it as period-specific or as time-entry hours unless the tool result says so.
- If the tool is missing, explain that budget comparison is optional and may not be enabled on this MCP server. Do not fall back to direct SQL or invent totals. Consult [budget module configuration](../configuration.md#optional-budget-comparison-openproject-179x) only when helping the user configure the connector.

## Make changes safely

- Treat reads as the default. Before any write, verify the target project and summarize the exact fields or records to change.
- OpenProject write tools use a preview/validation call followed by a second call with `confirm=true`. Inspect the preview, then execute only when the user has explicitly requested that change and the preview matches it.
- Never set `confirm=true` on the first call. Never broaden project scope, change unrelated records, or retry a mutation after an ambiguous result without checking current state first.
- Generic API calls can bypass this MCP server's `OPENPROJECT_READ_PROJECTS` and `OPENPROJECT_WRITE_PROJECTS` project allowlists. OpenProject permissions for the signed-in user still apply. Before using a generic mutation, verify that the user explicitly requested it, that the exact API operation and payload match the request, and that the allowlist bypass is within the request's intended scope. If this broader access is not clearly intended, stop and use a dedicated tool or explain that the server operator must enable/configure the needed capability; do not silently use generic calls to get around a scope denial.
- For a generic mutation, call `call_api_operation` first without `confirm=true` and inspect its preview/validation result. Execute the second call with `confirm=true` only if the preview confirms the exact intended operation, target, and payload. If the operation is destructive, has broad/instance-wide impact, or the preview is ambiguous, ask the user before confirming.
- For deletes, account/user changes, or broad instance-wide operations, state the scope and impact and require a clear user request before execution.

## Report findings

- Distinguish facts returned by OpenProject from calculations or interpretation. Show calculation inputs and formulas for derived totals.
- Mention unavailable fields, permission limits, pagination limits, and disabled optional tools when they affect completeness.
- Do not include secrets or unnecessary personal data in the response. The connector's server-side audit log is for operational traceability; do not claim it contains a particular user/action unless verified.

## Project references

- [Tool catalog](../tools.md) for tool behavior and optional tool groups.
- [Codex connection setup](../codex.md) for API-token and Streamable HTTP setup.
- [Configuration](../configuration.md) for server-side `.env` settings and the optional read-only budget database module.
- [Troubleshooting](../troubleshooting.md) for connection and authentication failures.
