from __future__ import annotations

from types import SimpleNamespace

import pytest
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from openproject_ce_mcp_server import tools_runtime


@pytest.mark.asyncio
async def test_activates_openproject_client_from_sdk_authenticated_user() -> None:
    client = object()

    class AppContext:
        api_token_verifier = object()

        async def client_for_api_token(self, subject: str, api_token: str) -> object:
            assert subject == "42"
            assert api_token == "op-api-token"
            return client

    token = AccessToken(
        token="op-api-token",
        client_id="openproject-api-token",
        scopes=["api_v3"],
        subject="42",
    )
    ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            request=SimpleNamespace(scope={"user": AuthenticatedUser(token)}),
            lifespan_context=AppContext(),
        )
    )

    activated = await tools_runtime._activate_user_client(ctx)
    assert activated is not None
    assert tools_runtime._ACTIVE_CLIENT.get() is client
    assert tools_runtime._ACTIVE_USER_ID.get() == "42"
    tools_runtime._ACTIVE_CLIENT.reset(activated[0])
    tools_runtime._ACTIVE_USER_ID.reset(activated[1])
