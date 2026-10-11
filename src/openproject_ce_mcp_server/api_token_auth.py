"""Validate MCP bearer tokens as OpenProject personal API tokens."""

from __future__ import annotations

import base64
import logging
from uuid import uuid4

import httpx
from mcp.server.auth.provider import AccessToken

from .config import Settings
from .logging_support import emit_audit_record, make_tool_call_record

LOGGER = logging.getLogger(__name__)


class OpenProjectApiTokenVerifier:
    """Verify a presented token against OpenProject's current-user endpoint."""

    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self._http = httpx.AsyncClient(
            timeout=settings.timeout,
            verify=settings.verify_ssl,
            transport=transport,
            follow_redirects=False,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or any(character.isspace() for character in token):
            return None
        encoded = base64.b64encode(f"apikey:{token}".encode()).decode()
        response: httpx.Response | None = None
        try:
            response = await self._http.get(
                f"{self.settings.api_base_url}/users/me",
                headers={"Authorization": f"Basic {encoded}", "Accept": "application/hal+json"},
            )
            if response.status_code in {401, 403}:
                self._audit_auth_failure("API_TOKEN_INVALID", response.status_code)
                return None
            response.raise_for_status()
            user_id = str(response.json()["id"])
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
            self._audit_auth_failure(
                "API_TOKEN_VALIDATION_FAILED", response.status_code if response is not None else None, exc
            )
            raise RuntimeError("Could not validate OpenProject API token.") from None
        return AccessToken(
            token=token,
            client_id="openproject-api-token",
            scopes=["api_v3"],
            subject=user_id,
        )

    @staticmethod
    def _audit_auth_failure(error_code: str, status: int | None, exc: BaseException | None = None) -> None:
        # Exception messages and request headers can contain credential material;
        # the closed audit schema records only the exception type and safe status.
        try:
            record = make_tool_call_record(
                tool="auth.api_token.verify",
                status="error",
                duration_ms=0,
                error_code=error_code,
                layer="authentication",
                http_requests=1,
                project_scope=None,
                policy_decision=None,
                request_id=None,
                user_id=None,
                error_id=uuid4().hex,
                error_category="authentication" if error_code == "API_TOKEN_INVALID" else "upstream",
                severity="warning" if error_code == "API_TOKEN_INVALID" else "error",
                retryable=error_code != "API_TOKEN_INVALID",
                upstream_status=status,
                operation_id="auth.api_token.verify",
                exception=exc,
                event_type="authentication",
            )
            emit_audit_record(record, level=logging.WARNING if error_code == "API_TOKEN_INVALID" else logging.ERROR)
        except Exception:
            LOGGER.exception("Could not emit API-token authentication audit event")
