import pytest
from httpx import AsyncClient
from main import app
from tests.conftest import BASE_URL

# Test cases for FullDataCoSpec API endpoint

@pytest.mark.asyncio(loop_scope="session")
async def test_FullDataCoSpec_authenticated(get_auth_headers,transport):
    headers =  get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/FullDataCoSpec/?tn=2163734606", headers=headers)
        assert resp.status_code == 200

@pytest.mark.asyncio(loop_scope="session")
async def test_FullDataCoSpec_missing_params_authenticated(get_auth_headers,transport):
    headers =  get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/FullDataCoSpec/", headers=headers)
        assert resp.status_code == 422
        
@pytest.mark.asyncio(loop_scope="session")
async def test_FullDataCoSpec_invalid_params_authenticated(get_auth_headers,transport):
    headers =  get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/FullDataCoSpec/?tn=123456", headers=headers)
        assert resp.status_code == 422                