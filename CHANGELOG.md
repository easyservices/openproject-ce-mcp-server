# Changelog

Release history for the independent **OpenProject CE MCP Server** project begins
here. The project uses its own package identity and version sequence; history
from the MIT-licensed source project is not represented as releases of this
project. See [LICENSE.md](LICENSE.md) for provenance and attribution.

## [0.1.0] - Unreleased

### Added

- Remote Streamable HTTP transport for deployments separate from OpenProject.
- Per-user OpenProject API-token authorization for remote MCP clients.
- Generic OpenAPI operation discovery and invocation for API v3 coverage.
- Structured audit events for tool calls and API-token authentication failures, with account
  identifiers when available and size-based log rotation.
- Classified errors, retry metadata, opaque internal-error references, and safe
  stack coordinates for maintenance and incident investigation.
- Codex remote HTTP registration helper and deployment documentation.

### Changed

- Renamed the distribution, Python package, and command line to
  `openproject-ce-mcp-server` / `openproject_ce_mcp_server`.
- Documented local stdio and remote HTTP modes, with source installations and
  production execution isolated in a project-local `.venv`.
