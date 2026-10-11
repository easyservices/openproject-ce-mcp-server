# Installation

The project is developed and deployed from a source checkout. All Python
development and production commands must run inside the project-local `.venv`.
The independent project package is named `openproject-ce-mcp-server`; do not
install the similarly named upstream project by mistake.

## Requirements

| Requirement | Supported setup |
| --- | --- |
| Python | 3.11 or newer |
| uv | Current stable release |
| OpenProject | Community Edition with API v3 enabled; this release targets 17.9.1 |

## Development installation

From the project checkout:

```bash
uv sync --dev
uv run openproject-ce-mcp-server --help
uv run pytest
```

`uv sync --dev` creates `.venv` and installs the pinned runtime and development
dependencies. If you do not use `uv`, the equivalent is:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

On Windows, use `.venv\\Scripts\\python.exe` and the corresponding executable
under `.venv\\Scripts`.

## Configure local stdio mode

Copy `.env.example` to `.env` and set `MCP_TRANSPORT=stdio`,
`OPENPROJECT_BASE_URL`, and `OPENPROJECT_API_TOKEN`. Then register the local
server with a supported MCP client:

```bash
uv run openproject-ce-mcp-server configure
```

The command can also diagnose or remove its client registration:

```bash
uv run openproject-ce-mcp-server doctor
uv run openproject-ce-mcp-server configure --uninstall
```

## Configure remote HTTP mode

For a server on another host, copy `.env.example` on the MCP host and set
`MCP_TRANSPORT=streamable-http`, the bind and public URL settings, and the
OpenProject URL. OpenProject may run on a different machine. Each Codex user
supplies their own API token with `bearer_token_env_var`. See
[Configuration](configuration.md) for the complete `.env` reference and
[Codex](codex.md) for client registration.

HTTP without TLS is allowed only for development. Production requires
`MCP_ENVIRONMENT=production`, an HTTPS `MCP_PUBLIC_URL`, and a TLS endpoint in
front of the server.

## Production Python environment

On the deployment host, create a project-local `.venv` with runtime dependencies
only:

```bash
uv sync --no-dev --frozen
uv run openproject-ce-mcp-server
```

Keep `.env` readable only by the service account. See [Production deployment](deployment.md)
for the systemd example, permissions, log rotation, and network setup.

## GitHub releases

The project is hosted on GitHub and does not publish to PyPI. GitHub Releases
may include source distributions and wheels for downloading, but the supported
installation path is from a project checkout using the `.venv` instructions
above.

## See also

- [Documentation hub](README.md)
- [Codex connection](codex.md)
- [Configuration](configuration.md)
- [Troubleshooting](troubleshooting.md)
