import pytest
from httpx import AsyncClient
from main import app
from tests.conftest import BASE_URL

# Test cases for LRN API endpoint

@pytest.mark.asyncio(loop_scope="session")
async def test_LRN_authenticated(get_auth_headers,transport):
    headers =  get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/LRN/?tn=2163734606", headers=headers)
        assert resp.status_code == 200

@pytest.mark.asyncio(loop_scope="session")
async def test_LRN_missing_params_authenticated(get_auth_headers,transport):
    headers =  get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/LRN/", headers=headers)
        assert resp.status_code == 422
        
@pytest.mark.asyncio(loop_scope="session")
async def test_LRN_invalid_params_authenticated(get_auth_headers,transport):
    headers =  get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/LRN/?tn=123456", headers=headers)
        assert resp.status_code == 422                