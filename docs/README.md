# Documentation

Documentation for **OpenProject CE MCP Server** (`openproject-ce-mcp-server`).
Choose a section by task. Start with the [project overview](../README.md) for
the supported transports and a quick start.

## Install and operate

- [Installation](installation.md) — development and production `.venv` setup,
  local stdio mode, remote HTTP mode, and GitHub Release artifacts.
- [Production deployment](deployment.md) — Docker Compose and GHCR image,
  separately hosted HTTP service, API-token authentication, systemd,
  permissions, and audit log forwarding.
- [Configuration](configuration.md) — `.env` reference, tool scopes,
  audit event schema, error classification, and log rotation.
- [Troubleshooting](troubleshooting.md) — diagnostics and common errors.

## MCP clients

- [Codex](codex.md) — remote Streamable HTTP setup and per-user API token,
  plus local stdio configuration.
- [Client overview](clients.md) — choose a client and understand supported
  connection modes.
- [Claude / Claude Code](claude.md)
- [Claude Desktop](claude-desktop.md)
- [Cursor](cursor.md)
- [VS Code / GitHub Copilot](github.md)
- [Continue](continue.md)

## Use the tools

- [Tool reference](tools.md) — typed tools, generic API access, write
  confirmation, and error categories.
- [Work package filters](filters.md) — supported filter fields and operators.
- [Field hiding](field-hiding.md) — entity fields that can be hidden.

## Agent instructions

- [OpenProject project management agent](agents/AGENTS.md) — agent mission,
  operating principles, and how to add skills. The directory also contains its
  primary [OpenProject MCP skill](agents/SKILL.md).

## Develop and maintain

- [Development guide](../CONTRIBUTING.md) — virtual environment, code standards,
  checks, and contribution workflow.
- [Architecture](architecture.md) — modules, request flow, and security layers.
- [Context efficiency](context-efficiency.md) — response-size measurement.
- [API coverage tools](../tools/api-check/README.md) — compare API behavior and
  fields with OpenProject releases.

## Policies

- [Security policy](../SECURITY.md)
- [Code of conduct](../CODE_OF_CONDUCT.md)
- [License and project provenance](../LICENSE.md)
