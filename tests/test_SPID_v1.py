import pytest
from httpx import AsyncClient
from main import app
from tests.conftest import BASE_URL

# Test cases for SPID API endpoint

@pytest.mark.asyncio(loop_scope="session")
async def test_spid_authenticated(get_auth_headers, transport):
    headers = get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/SPID/?tn=2163734600", headers=headers)
        assert resp.status_code == 200

@pytest.mark.asyncio(loop_scope="session")
async def test_spid_missing_params_authenticated(get_auth_headers, transport):
    headers = get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/SPID/", headers=headers)
        assert resp.status_code == 422

@pytest.mark.asyncio(loop_scope="session")
async def test_spid_invalid_params_authenticated(get_auth_headers, transport):
    headers = get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/SPID/?tn=123456", headers=headers)
        assert resp.status_code == 422