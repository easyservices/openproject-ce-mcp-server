# Troubleshooting


## Quick diagnosis: `doctor`

For a local stdio setup, if the server doesn't appear in your MCP client after
configuration, run the built-in diagnostic command inside the project's
virtual environment:

```bash
uv run openproject-ce-mcp-server doctor
```

The `doctor` command checks the local stdio setup and reports what's working
and what needs fixing:

1. **Binary and version** — verifies the installed package and resolved binary
   path
2. **Client configs** — discovers MCP client configurations (Claude Code, Claude
   Desktop, VS Code, Codex, Cursor)
3. **Config parsing** — validates that your client configs are readable and
   contain a valid `openproject` entry
4. **Environment** — loads and validates `OPENPROJECT_*` environment variables
   from your client config or shell
5. **API connectivity** — tests your base URL and API token with a live
   connection to OpenProject
6. **Tool registration** — previews which MCP tools will be registered based on
   your read/write permissions

Example output:

```text
Running OpenProject MCP diagnostics...

[OK] Binary: /opt/openproject-ce-mcp-server/.venv/bin/openproject-ce-mcp-server (v0.1.0)
[OK] Clients: 2 configs found
  - Claude Code (global, detected): ~/.claude.json
  - Claude Desktop (global, detected): ~/Library/.../claude_desktop_config.json
[OK] Config parsing: all openproject entries valid
[OK] Environment: loaded from client configs
[OK] API: connected (Your Name)
[OK] Tools: 127 registered
  create_work_package, list_projects, update_work_package, ...

Restart needed for:
  - Claude Desktop: quit and reopen (window reload not enough)

All checks passed.
```

If a check fails, doctor prints a `[FAIL]` message with details and suggestions.

**Exit codes**: `0` = all checks passed, `1` = one or more checks failed

## Common issues

| Symptom | Likely cause and fix |
| --- | --- |
| Server / tools don't appear | Client not restarted, or the config is in the wrong file. Reload the client and confirm the file, location, and root key match your client's row in [Clients](clients.md#file-layout-per-client) — `configure` writes to whatever directory it was launched from, so also check that matches the folder your client has open, and re-run `configure` from there if not. |
| `[AUTHENTICATION_FAILED]` on the first call | In stdio mode, check `OPENPROJECT_API_TOKEN`; in HTTP mode, check that Codex can read the user's `OPENPROJECT_API_TOKEN` environment variable and that the token is valid. In both modes, verify `OPENPROJECT_BASE_URL` has no trailing `/api/v3`. |
| Tools appear but writes fail | The project-scope allowlists are the real write gate, not the write-category flags (which default on). Make sure the target project is in **both** `OPENPROJECT_READ_PROJECTS` and `OPENPROJECT_WRITE_PROJECTS`, and check that the corresponding write-category flag such as `OPENPROJECT_ENABLE_WORK_PACKAGE_WRITE` hasn't been explicitly set to `false` — see [Configuration](configuration.md#tool-groups). |
| Missing env vars | For stdio, add `OPENPROJECT_BASE_URL` and `OPENPROJECT_API_TOKEN` to the MCP entry's `env`. For remote HTTP, check the server's `.env` and restart its process after edits. |
| Auth failure | For stdio, check the API token. For HTTP, set a valid personal API token in the environment that launches Codex and restart Codex. |
| Cannot connect | Verify `OPENPROJECT_BASE_URL` is reachable from the MCP host. For HTTP, also verify the Codex-facing `MCP_PUBLIC_URL`, `MCP_HOST`, `MCP_PORT`, `MCP_PATH`, reverse proxy, allowed host list, and TLS configuration. |
| No configs found | Run `openproject-ce-mcp-server configure` to register the server with your MCP clients — see [Installation](installation.md) and [Clients](clients.md). |
| Codex CLI shows the server, IDE extension doesn't | First check the basics: the project is trusted, the IDE extension and CLI are pointed at the same project directory, and the file (`.codex/config.toml` vs. `~/.codex/config.toml`) matches the scope you configured — see [Clients](clients.md#file-layout-per-client). If those all check out and `codex mcp list` (CLI) shows the server but the IDE extension still doesn't, reload the editor window or restart the IDE; if it still doesn't appear, this may be a known upstream Codex extension-detection gap (tracked as Codex GitHub issue #6465) rather than a problem with this server's config — check the upstream issue for its current status. |

Every MCP tool failure also carries a stable, machine-readable category as a
leading `[category]` prefix on the error message — see the [error
reference](tools.md#errors) for the full list.

## See also

- [Documentation hub](README.md) — full documentation index
- [Installation](installation.md) — install, update, and uninstall the package
- [Clients](clients.md) — client config file locations
- [Configuration](configuration.md) — the full environment variable reference
