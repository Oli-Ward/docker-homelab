import httpx
import pytest

from openclaw_gateway.main import create_app


@pytest.mark.asyncio
async def test_health_is_public():
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
