import httpx

from openclaw_gateway.schemas.media import RyotProbeResponse


class RyotGraphQLError(Exception):
    pass


class RyotClient:
    def __init__(self, base_url: str, admin_access_token: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._admin_access_token = admin_access_token
        self._timeout = httpx.Timeout(timeout_seconds)

    async def probe(self) -> RyotProbeResponse:
        payload = await self._graphql(
            query="query OpenClawRyotProbe { __typename }",
            variables={},
        )
        return RyotProbeResponse(
            status="ok",
            service="ryot",
            typename=str(payload.get("__typename", "")),
        )

    async def _graphql(self, query: str, variables: dict) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/backend/graphql",
                headers={
                    "Authorization": f"Bearer {self._admin_access_token}",
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables},
            )
            response.raise_for_status()

        payload = response.json()
        if payload.get("errors"):
            raise RyotGraphQLError("ryot graphql error")

        data = payload.get("data")
        if not isinstance(data, dict):
            raise RyotGraphQLError("ryot graphql response missing data")

        return data
