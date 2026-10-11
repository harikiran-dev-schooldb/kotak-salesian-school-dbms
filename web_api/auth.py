from __future__ import annotations

import hmac
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request, status


@dataclass(frozen=True, slots=True)
class Principal:
    role: str
    name: str


def _matches(candidate: str, expected: str) -> bool:
    return bool(candidate and expected and hmac.compare_digest(candidate, expected))


async def current_principal(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> Principal:
    settings = request.app.state.settings
    if settings.auth_disabled:
        return Principal(role="admin", name="local-development")
    if _matches(x_api_key or "", settings.admin_api_key):
        return Principal(role="admin", name="administrator")
    if _matches(x_api_key or "", settings.viewer_api_key):
        return Principal(role="viewer", name="viewer")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="A valid API key is required",
    )


async def require_admin(request: Request, x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> Principal:
    principal = await current_principal(request, x_api_key)
    if principal.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    return principal

