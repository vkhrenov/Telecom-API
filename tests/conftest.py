import pytest
import pytest_asyncio
import src.databases.redis_cache
from httpx import AsyncClient

class DummyAsyncRedisClient:
    async def hincrby(self, *args, **kwargs):
        return 1

src.databases.redis_cache.redis_client = DummyAsyncRedisClient()

BASE_URL = "http://testserver/"

@pytest_asyncio.fixture(scope="function")
def transport():
    from main import app
    from httpx import ASGITransport
    return ASGITransport(app=app)

@pytest_asyncio.fixture(scope="function")
async def get_auth_headers(transport):
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        login_data = {"login": "test", "password": "test"}
        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
