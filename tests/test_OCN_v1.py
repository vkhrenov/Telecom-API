import pytest
from httpx import AsyncClient
from main import app
from tests.conftest import BASE_URL

# Test cases for OCN API endpoint

@pytest.mark.asyncio(loop_scope="session")
async def test_ocn_authenticated(get_auth_headers, transport):
    headers = get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/OCN/?tn=2163734600", headers=headers)
        assert resp.status_code == 200

@pytest.mark.asyncio(loop_scope="session")
async def test_ocn_missing_params_authenticated(get_auth_headers, transport):
    headers = get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/OCN/", headers=headers)
        assert resp.status_code == 422

@pytest.mark.asyncio(loop_scope="session")
async def test_ocn_invalid_params_authenticated(get_auth_headers, transport):
    headers = get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/OCN/?tn=123456", headers=headers)
        assert resp.status_code == 422