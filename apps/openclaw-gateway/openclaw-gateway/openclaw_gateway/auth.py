from collections.abc import Awaitable, Callable
from secrets import compare_digest

from fastapi import Header, HTTPException, status

from openclaw_gateway.settings import GatewaySettings


def require_gateway_token(settings: GatewaySettings) -> Callable[[str | None], Awaitable[None]]:
    async def dependency(authorization: str | None = Header(default=None)) -> None:
        if authorization is None or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
            )

        supplied_token = authorization.removeprefix("Bearer ").strip()
        if not compare_digest(supplied_token, settings.gateway_auth_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token",
            )

    return dependency
