from __future__ import annotations

import base64

import httpx
import pytest

from openproject_ce_mcp_server import server as server_module
from openproject_ce_mcp_server.api_token_auth import OpenProjectApiTokenVerifier
from openproject_ce_mcp_server.config import Settings
from openproject_ce_mcp_server.server import AppContext, create_app


def _settings(**extra: str) -> Settings:
    env = {
        "OPENPROJECT_BASE_URL": "https://op.example.test",
        "MCP_TRANSPORT": "streamable-http",
        "MCP_PUBLIC_URL": "http://localhost:8000",
        **extra,
    }
    return Settings.from_env(env)


@pytest.mark.asyncio
async def test_openproject_api_token_verifier_checks_current_user_with_basic_api_token_auth() -> None:
    expected = "Basic " + base64.b64encode(b"apikey:personal-api-token").decode()

    def upstream(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v3/users/me"
        assert request.headers["Authorization"] == expected
        return httpx.Response(200, json={"id": 42})

    verifier = OpenProjectApiTokenVerifier(_settings(), transport=httpx.MockTransport(upstream))
    access_token = await verifier.verify_token("personal-api-token")
    await verifier.aclose()

    assert access_token is not None
    assert access_token.token == "personal-api-token"
    assert access_token.subject == "42"
    assert access_token.scopes == ["api_v3"]


@pytest.mark.asyncio
async def test_invalid_openproject_api_token_is_rejected_and_audited_safely(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "openproject_ce_mcp_server.api_token_auth.emit_audit_record", lambda record, *, level: events.append(record)
    )
    secret = "secret-personal-token"
    verifier = OpenProjectApiTokenVerifier(
        _settings(), transport=httpx.MockTransport(lambda request: httpx.Response(401))
    )

    assert await verifier.verify_token(secret) is None
    await verifier.aclose()

    assert len(events) == 1
    assert events[0]["event_type"] == "authentication"
    assert events[0]["error_code"] == "API_TOKEN_INVALID"
    assert secret not in str(events)


def test_remote_http_configuration_needs_no_auth_credentials_or_server_token() -> None:
    settings = _settings()
    server = create_app(settings)

    assert server._auth_server_provider is None
    assert server._token_verifier is not None
    assert settings.api_token is None


@pytest.mark.asyncio
async def test_app_context_keeps_distinct_api_tokens_on_distinct_openproject_clients(monkeypatch) -> None:
    clients = []

    class FakeClient:
        def __init__(self, settings: Settings, *, api_token: str) -> None:
            self.api_token = api_token
            self.closed = False
            clients.append(self)

        async def initialize(self) -> None:
            pass

        async def aclose(self) -> None:
            self.closed = True

    monkeypatch.setattr(server_module, "OpenProjectClient", FakeClient)

    class FakeVerifier:
        async def aclose(self) -> None:
            pass

    context = AppContext(settings=_settings(), client=None, api_token_verifier=FakeVerifier())

    first = await context.client_for_api_token("42", "first-token")
    second = await context.client_for_api_token("73", "second-token")
    same = await context.client_for_api_token("42", "first-token")
    await context.aclose()

    assert first is same
    assert first is not second
    assert first.api_token == "first-token"
    assert second.api_token == "second-token"
    assert all(client.closed for client in clients)
