# Production deployment

This guide runs the Streamable HTTP server from the project checkout with a
dedicated Linux account and systemd. The MCP server may be hosted separately
from OpenProject.

## Prepare the application

Place a checkout of this independent project at `/opt/openproject-ce-mcp-server`
and assign it to a dedicated account. Then create the runtime virtual
environment and secure its `.env` file:

```bash
sudo install -d -o op-mcp -g op-mcp /opt/openproject-ce-mcp-server
cd /opt/openproject-ce-mcp-server
sudo -u op-mcp uv sync --no-dev --frozen
sudo -u op-mcp cp .env.example .env
sudo chown op-mcp:op-mcp .env
sudo chmod 600 .env
```

Edit `.env` with deployment values. Set `MCP_TRANSPORT=streamable-http`,
`MCP_ENVIRONMENT=production`, the public HTTPS URL, bind host and port,
`MCP_SERVER_NAME`, `MCP_PATH`, and the OpenProject URL. Put TLS termination
and network access controls in front of the MCP service.

Remote users keep their API tokens in their local Codex environment. The MCP
server validates tokens against OpenProject and does not store them in its
deployment configuration. Each API token retains its owner's permissions.

Set `MCP_AUDIT_LOG_FILE` to a path writable by the service account. The JSON
Lines audit log is the required trace of MCP calls and API-token authentication failures; forward
it to your central log collector. `MCP_AUDIT_LOG_MAX_BYTES` configures the
rotation threshold and `MCP_AUDIT_LOG_BACKUP_COUNT` controls retained files.
Never place a remote user's token in the server `.env` or share one token among
remote users.

For the optional budget comparison, install its driver with
`uv sync --no-dev --extra budget-comparison --frozen`, then set
`OPENPROJECT_BUDGET_COMPARISON_ENABLED=true`
and the `OPENPROJECT_DB_*` variables in `.env`. Grant the dedicated DB user
read-only access to the tables listed in [Configuration](configuration.md#database-grants-and-schema-access),
use TLS for remote database connections (`OPENPROJECT_DB_SSLMODE=verify-full`),
and allow outbound MCP-host-to-PostgreSQL traffic through the firewall. The
feature is disabled by default and does not need DB credentials when disabled.

## systemd service

Create `/etc/systemd/system/openproject-ce-mcp-server.service`:

```ini
[Unit]
Description=OpenProject CE MCP Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=op-mcp
Group=op-mcp
WorkingDirectory=/opt/openproject-ce-mcp-server
EnvironmentFile=/opt/openproject-ce-mcp-server/.env
ExecStart=/opt/openproject-ce-mcp-server/.venv/bin/openproject-ce-mcp-server
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/openproject-ce-mcp-server/logs

[Install]
WantedBy=multi-user.target
```

If `MCP_AUDIT_LOG_FILE` points elsewhere, adjust `ReadWritePaths` to include
that directory. Enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now openproject-ce-mcp-server
sudo systemctl status openproject-ce-mcp-server
```

For upgrades, update the independent project checkout, run
`uv sync --no-dev --frozen` inside it, then restart the service. The project
local `.venv` can be recreated from `uv.lock` if needed.
