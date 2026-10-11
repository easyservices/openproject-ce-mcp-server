# OpenProject CE MCP Server

An independent Model Context Protocol (MCP) server for OpenProject Community
Edition. It exposes OpenProject API v3 to AI assistants through local stdio or
remote Streamable HTTP.

The server supports per-user OpenProject API tokens for remote connections.
Each request runs with the permissions of the token owner. It does not use
OAuth.

## Features

- Typed MCP tools for projects, work packages, users, memberships, boards,
  meetings, time entries, attachments, and related OpenProject data.
- Optional generic API tools for discovering and calling API v3 operations.
- Preview and explicit confirmation for write operations.
- Configurable tool groups, project scopes, hidden fields, and upload paths.
- Structured JSON Lines audit events with secret and request-body redaction.
- Local stdio for a single user and remote HTTP for hosted deployments.

The generic API tools rely on OpenProject's own authorization. They do not
apply this server's project allowlists.

## Requirements

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- An OpenProject Community Edition instance and a user API token

## Quick start: local stdio

Clone the [GitHub repository](https://github.com/easyservices/openproject-ce-mcp-server),
then install it and configure a supported MCP client:

```bash
git clone https://github.com/easyservices/openproject-ce-mcp-server.git
cd openproject-ce-mcp-server
uv sync
cp .env.example .env
```

Set `OPENPROJECT_URL` and `OPENPROJECT_API_TOKEN` in `.env`. Protect the file
because it contains a credential:

```bash
chmod 600 .env
uv run openproject-ce-mcp-server configure
```

The setup command detects supported clients and writes their MCP configuration.
See [Installation](docs/installation.md) for source, package, and client
installation options.

## Quick start: remote HTTP

Install dependencies and configure the server environment:

```bash
uv sync
cp .env.example .env
```

Set `OPENPROJECT_URL`, `MCP_PUBLIC_URL`, and the host and port settings in
`.env`, then start the server:

```bash
chmod 600 .env
uv run openproject-ce-mcp-server
```

For production, set `MCP_ENVIRONMENT=production`, use an HTTPS
`MCP_PUBLIC_URL`, and configure TLS termination and access controls in front
of the service. HTTP is allowed only in development mode. Each remote MCP user
must provide their own OpenProject API token through the MCP client's
`OPENPROJECT_API_TOKEN` environment variable. For Codex, see the
[Codex connection guide](docs/codex.md) and [deployment guide](docs/deployment.md).
The deployment guide includes a Docker Compose overlay and GHCR image details.

## Configuration

Configuration is read from environment variables and an optional `.env` file.
The complete reference, including transport, authentication, scopes, tool
groups, audit logging, and optional features, is in
[Configuration](docs/configuration.md).

## Documentation

- [Documentation index](docs/README.md)
- [Installation](docs/installation.md)
- [Configuration reference](docs/configuration.md)
- [Codex setup](docs/codex.md)
- [Supported MCP clients](docs/clients.md)
- [Production deployment](docs/deployment.md)
- [Tool reference](docs/tools.md)
- [Architecture](docs/architecture.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Development

Install development dependencies and run the checks from the repository root:

```bash
uv sync --dev
uv run pytest
uv run ruff check .
```

See [Contributing](CONTRIBUTING.md) for development workflow, integration
fixtures, and contribution guidelines.

## Project information

- **GitHub repository:** [easyservices/openproject-ce-mcp-server](https://github.com/easyservices/openproject-ce-mcp-server)
- **Python package:** `openproject_ce_mcp_server`
- **Package name:** `openproject-ce-mcp-server`
- **Distribution:** source checkout and GitHub Releases; no PyPI publication
- **Development:** code produced with an OpenAI Codex agent
- **License:** MIT; see [LICENSE.md](LICENSE.md)
- **Project status:** independent community project, not an official
  OpenProject product and not endorsed by OpenProject

GitHub description: “Independent MCP server for OpenProject Community Edition,
with local stdio and remote HTTP transports.” Suggested topics:
`openproject`, `mcp`, `model-context-protocol`, `python`, `ai-agents`.
