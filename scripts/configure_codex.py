"""Register the remote Streamable HTTP endpoint with the local Codex CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values


def main() -> int:
    values = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
    name = (values.get("MCP_SERVER_NAME") or "").strip()
    public_url = (values.get("MCP_PUBLIC_URL") or "").strip().rstrip("/")
    path = (values.get("MCP_PATH") or "/mcp").strip()
    if not name or not public_url:
        print("Set MCP_SERVER_NAME and MCP_PUBLIC_URL in .env first.", file=sys.stderr)
        return 2
    parsed = urlparse(public_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        print("MCP_PUBLIC_URL in .env must be an absolute HTTP(S) URL.", file=sys.stderr)
        return 2
    if not path.startswith("/") or "?" in path or "#" in path:
        print("MCP_PATH in .env must be an absolute path, such as /mcp.", file=sys.stderr)
        return 2
    endpoint = f"{public_url}{path}"
    result = subprocess.run(
        ["codex", "mcp", "add", name, "--url", endpoint, "--bearer-token-env-var", "OPENPROJECT_API_TOKEN"],
        check=False,
    )
    if result.returncode == 0:
        print(f"Added {name} at {endpoint}.")
        print("Set OPENPROJECT_API_TOKEN in the environment that launches Codex, then restart Codex.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
