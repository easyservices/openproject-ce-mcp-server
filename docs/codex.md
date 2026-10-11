# Codex


## Recommended setup

### Serve MCP remotely over HTTP

For a separately hosted MCP server, configure it in the server's `.env` and set
`MCP_TRANSPORT=streamable-http`. The OpenProject instance can be on another
host; `OPENPROJECT_BASE_URL` is the address reachable from the MCP server.
`MCP_PUBLIC_URL` must be the externally reachable MCP URL. Development permits
HTTP; production requires HTTPS.

Create the Codex entry with the helper from the project's virtual environment:

```bash
.venv/bin/python scripts/configure_codex.py
codex mcp list
```

The helper registers the URL and tells Codex to read
`OPENPROJECT_API_TOKEN` from the environment that launches Codex. Create a
personal API token in OpenProject, set that variable locally, then restart
Codex. The server validates the token and makes API requests with that user's
permissions. The token is not placed in Codex's config file or the MCP server's
`.env`.

The existing sections below describe the separate, local stdio setup.

Codex supports `env_vars` on an `mcp_servers` entry — a whitelist of environment
variable names to forward from the process that launches Codex into the server's
environment, instead of embedding their values in `.codex/config.toml`. For a
private credential like an OpenProject API token, this keeps the token out of
`.codex/config.toml`:

```toml
[mcp_servers.openproject]
command = "openproject-ce-mcp-server"
env_vars = ["OPENPROJECT_API_TOKEN"]

[mcp_servers.openproject.env]
OPENPROJECT_BASE_URL = "https://op.example.com"
OPENPROJECT_READ_PROJECTS = "my-project,other-project"
OPENPROJECT_WRITE_PROJECTS = "my-project"
```

`OPENPROJECT_API_TOKEN` must be set in the environment of the process that
launches Codex — a shell profile is enough if Codex starts from that same
initialized shell; a GUI/IDE launch may need an OS-level environment mechanism
or a secret manager instead. If the variable isn't set when Codex starts,
authentication fails when it connects. Never commit the token or paste it into
chat messages.

For manual configuration of a remote server, use:

```toml
[mcp_servers.openproject]
url = "https://mcp.example.com/mcp"
bearer_token_env_var = "OPENPROJECT_API_TOKEN"
```

Codex sends the token in the HTTP `Authorization: Bearer` header. The server
converts it to OpenProject's API-token authentication format for upstream API
requests. Codex documents this setting as
[`bearer_token_env_var`](https://learn.chatgpt.com/docs/extend/mcp#streamable-http-servers).

Codex loads project-scoped config files (`.codex/config.toml`) only when you
trust the project. You do not need the Codex CLI installed for this setup if you
use the IDE extension and edit the config file directly.

## Automatic setup provided by this package

`openproject-ce-mcp-server configure` configures local stdio use and writes its
token to the selected client configuration. For remote HTTP, use the helper
above or configure `bearer_token_env_var` manually. See
[Installation](installation.md) for installing the package first.

## Manual setup (matching this package's automatic `.codex/config.toml` output)

If you'd rather reproduce what `configure` writes automatically, create
`.codex/config.toml` in your project root:

```toml
[mcp_servers.openproject]
command = "openproject-ce-mcp-server"

[mcp_servers.openproject.env]
OPENPROJECT_BASE_URL = "https://op.example.com"
OPENPROJECT_API_TOKEN = "replace-with-your-token"
OPENPROJECT_READ_PROJECTS = "my-project,other-project"
OPENPROJECT_WRITE_PROJECTS = "my-project"
```

For local stdio mode, install from this project's checkout and point `command`
to its `.venv` executable (`.../.venv/bin/openproject-ce-mcp-server`, or
`...\\.venv\\Scripts\\openproject-ce-mcp-server.exe` on Windows). Remote HTTP
mode is the recommended setup above and does not launch a local Python process.

The full set of `env` keys is the same as every other client — see
[`.mcp.json.example`](../.mcp.json.example) or
[Configuration](configuration.md).

**CLI alternative (optional):** If you have the Codex CLI installed, you can add
the server from the terminal instead. This writes to your shared Codex
configuration:

```bash
codex mcp add openproject \
  --env OPENPROJECT_BASE_URL=https://op.example.com \
  --env OPENPROJECT_API_TOKEN=your-token \
  -- \
  openproject-ce-mcp-server
```

For remote HTTP, the helper runs `codex mcp add` with
`--bearer-token-env-var OPENPROJECT_API_TOKEN`.
See the [Codex MCP command reference](https://learn.chatgpt.com/docs/developer-commands#codex-mcp)
for the current CLI reference.

Set the token in the environment that launches Codex. The token value itself
is not saved in Codex's MCP entry.

## Protect credentials

With the `env_vars` pattern above, `.codex/config.toml` itself holds no secret.
The current automatic setup (`configure`) writes the token directly into the
file, and a manual setup that skips `env_vars` does the same — in both cases,
protect it:

```bash
chmod 600 .codex/config.toml
```

Add `.codex/config.toml` and `.codex/config.toml.bak*` to your project's
`.gitignore` so neither the file nor its timestamped backups are ever committed.

## Reload and verify

In the IDE extension:

- trust the project
- reload the editor window or restart Codex if needed
- confirm the `openproject` server appears in Codex
- confirm MCP tools are available in the session
- ask Codex to call `list_projects` (or `get_current_user`); a successful reply
  confirms the base URL and token work

If the server doesn't appear immediately, restart Codex or reload the editor
window.

---

## User-wide setup (alternative)

If you want to share one OpenProject CE MCP Server instance across all projects instead
of scoping it per project, use the user-wide `config.toml`:

- File:
  - **Windows:** `%USERPROFILE%\.codex\config.toml`
  - **macOS:** `~/.codex/config.toml`
  - **Linux:** `~/.codex/config.toml`
- **Protect credentials:** `chmod 600 ~/.codex/config.toml` on macOS/Linux; on
  Windows restrict it to your user via **Properties → Security**.

**Example:** For the recommended credential handling, use the `env_vars`
configuration from "Recommended setup" in `~/.codex/config.toml`. You can also
use the literal configuration instead, but then the file contains the token and
must be protected accordingly.

**Note:** All projects share the same credentials and permissions. For
credentials specifically, the `env_vars` pattern under "Recommended setup" above
is preferred.

---

## Notes

- Codex supports user-level configuration in `~/.codex/config.toml` and
  project-scoped overrides in `.codex/config.toml`
- Codex loads project-scoped config files only for trusted projects
- Codex shares MCP configuration between the CLI and the IDE extension
- You do not need the Codex CLI when configuring Codex through the IDE extension
- Treat the CLI flow as optional helper functionality, not as the primary Codex
  setup path
- Project-scoped setup (`.codex/config.toml`) is preferred for fine-grained
  project permissions
- `OPENPROJECT_READ_PROJECTS` accepts comma-separated identifiers, names, or
  glob patterns: `project-one,team-*`. Use `*` for all visible projects
- `OPENPROJECT_WRITE_PROJECTS` is the real write gate — the 6 core
  write-category flags (like `OPENPROJECT_ENABLE_WORK_PACKAGE_WRITE`) are on by
  default and do nothing until a project is listed here; set one to `false` to
  exclude that category instead

## See also

- [Documentation hub](README.md) — full documentation index
- [Clients](clients.md) — global vs. project-scoped, and every client's file
  layout
- [Configuration](configuration.md) — the full environment variable reference
