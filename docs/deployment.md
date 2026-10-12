# Production deployment

This guide covers running the Streamable HTTP server with Docker Compose or
from a project checkout with a dedicated Linux account and systemd. The MCP
server may be hosted separately from OpenProject.

## Docker Compose

The published image is `ghcr.io/easyservices/openproject-ce-mcp-server`. Each
GitHub release publishes a version tag (for example, `0.1.0`) and updates
`latest`. The image includes the optional PostgreSQL driver for budget
comparison; the feature remains disabled unless explicitly enabled. If the
GHCR package is private, authenticate on the Docker host before pulling it:

```bash
docker login ghcr.io
```

Add the service from
[`docker/production/compose.yml`](../docker/production/compose.yml) to your
existing Compose project. It uses the `mcp_web` and `openproject_backend`
networks from your Compose file, reaches the API at `http://openproject`, and
publishes host port `8766` to container port `8000`. Merge the service into the
existing file or use it as a Compose overlay:

```bash
docker compose \
  -f /path/to/openproject/compose.yml \
  -f /path/to/openproject-ce-mcp-server/docker/production/compose.yml \
  up -d
```

### Adding it to a stack that already has OpenProject and PostgreSQL MCP

The OpenProject connector is a separate service. Add the `openproject-mcp`
service from the production Compose file to your existing `services:` section;
keep the other MCP service there as well. In particular, the API connection
uses the OpenProject service name (`openproject` below), not the PostgreSQL MCP
service name. The PostgreSQL connector does not need to be changed.

For a minimal in-file example, the relevant part of the existing Compose file
looks like this (retain your current image, volumes, environment, and other
settings for `openproject` and `postgres-mcp`):

```yaml
services:
  openproject:
    # Your existing OpenProject service
    networks:
      - openproject_backend

  postgres-mcp:
    # Your existing PostgreSQL MCP service
    networks:
      - mcp_web

  openproject-mcp:
    image: ghcr.io/easyservices/openproject-ce-mcp-server:${MCP_IMAGE_TAG:-latest}
    depends_on:
      - openproject
    ports:
      - "8766:8000"
    environment:
      MCP_TRANSPORT: streamable-http
      MCP_ENVIRONMENT: "${MCP_ENVIRONMENT:-development}"
      MCP_HOST: 0.0.0.0
      MCP_PORT: "8000"
      MCP_PUBLIC_URL: "${MCP_PUBLIC_URL:-http://localhost:8766}"
      MCP_SERVER_NAME: openproject
      MCP_PATH: /mcp
      MCP_ALLOWED_HOSTS: "${MCP_ALLOWED_HOSTS:-localhost:8766,127.0.0.1:8766}"
      OPENPROJECT_BASE_URL: http://openproject
      MCP_AUDIT_LOG_FILE: /app/logs/audit.jsonl
    volumes:
      - ./data/mcp-audit:/app/logs
    networks:
      - mcp_web
      - openproject_backend
    restart: unless-stopped

networks:
  mcp_web:
  openproject_backend:
```

Use the actual Compose network keys from your stack in place of
`mcp_web`/`openproject_backend`, and attach `openproject-mcp` to the network
that can reach OpenProject. Compose service DNS (`http://openproject`) works
only when both services share a network and `openproject` is the OpenProject
service name. If you use the provided overlay instead, its network names must
match the top-level network keys in the base file. For networks managed outside
this Compose project, declare them as `external: true` and set their actual
Docker network names with `name:`.

The audit directory is relative to the Compose project directory. Create it
and grant write access to the container user (UID/GID `10001`) before starting
the service; the commands are in the next paragraph. Add the
`OPENPROJECT_DB_*` settings from the full production Compose example only if
you enable the optional budget comparison feature; it connects directly to
PostgreSQL, so its DB host must also be reachable from the `openproject-mcp`
container. This is independent of the PostgreSQL MCP service.

After creating the audit directory using the commands in the next paragraph,
start or update the stack. If you use the overlay, include both `-f` options
from the first example in this section:

```bash
docker compose up -d openproject-mcp
```

Set the MCP endpoint in your client to `http://<docker-host>:8766/mcp` (or to
the HTTPS URL configured on your reverse proxy). Each user supplies their own
OpenProject API token in their MCP client; do not add a shared token to
Compose. For production, configure TLS and the production environment values
described above.

Create the audit-log directory next to the base Compose file and give the
container's unprivileged user access to it:

```bash
mkdir -p /path/to/openproject/data/mcp-audit
sudo chown 10001:10001 /path/to/openproject/data/mcp-audit
```

Compose reads variable substitutions from the `.env` file beside the base
Compose file. For direct HTTP access on a trusted network, use the defaults or
set `MCP_PUBLIC_URL` to the address clients use, such as
`http://mcp.example.lan:8766`, and set `MCP_ALLOWED_HOSTS` to the matching
host and port. This direct HTTP setup uses development mode. For production,
put the service behind a TLS reverse proxy, set `MCP_ENVIRONMENT=production`,
set `MCP_PUBLIC_URL` to its HTTPS URL, and set `MCP_ALLOWED_HOSTS` to that
URL's host. The MCP container can remain reachable by the proxy on port 8766.

Each remote MCP user supplies their own OpenProject API token to their MCP
client; do not put a shared user token in Compose. To enable budget comparison,
set `OPENPROJECT_BUDGET_COMPARISON_ENABLED=true` and configure
`OPENPROJECT_DB_NAME`, `OPENPROJECT_DB_USER`, and `OPENPROJECT_DB_PASSWORD`
for a dedicated read-only PostgreSQL account. The default DB host is
`openproject`, port `5432`, and SSL mode `prefer`; adjust these if your
database is hosted elsewhere. See [Configuration](configuration.md#database-grants-and-schema-access)
for the required grants.

To build the image locally from the repository root instead of pulling a
release image, run `docker build -t ghcr.io/easyservices/openproject-ce-mcp-server:local .`
and set `MCP_IMAGE_TAG=local` in the Compose `.env` file. To update to a
release, set `MCP_IMAGE_TAG` to its version (or `latest`) and run
`docker compose pull openproject-mcp` followed by
`docker compose up -d openproject-mcp`.

The runtime image is built for `linux/amd64` by the release workflow. Local
builds use the host's default architecture.

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
