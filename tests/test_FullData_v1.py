import pytest
from httpx import AsyncClient
from main import app
from tests.conftest import BASE_URL

# Test cases for FullData API endpoint

@pytest.mark.asyncio(loop_scope="session")
async def test_FullData_authenticated(get_auth_headers,transport):
    headers =  get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/FullData/?tn=2163734606", headers=headers)
        assert resp.status_code == 200

@pytest.mark.asyncio(loop_scope="session")
async def test_FullData_missing_params_authenticated(get_auth_headers,transport):
    headers =  get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/FullData/", headers=headers)
        assert resp.status_code == 422
        
@pytest.mark.asyncio(loop_scope="session")
async def test_FullData_invalid_params_authenticated(get_auth_headers,transport):
    headers =  get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/FullData/?tn=123456", headers=headers)
        assert resp.status_code == 422                