import pytest
from httpx import AsyncClient
from main import app
from tests.conftest import BASE_URL

# Test cases for LRNjurisdiction API endpoint

@pytest.mark.asyncio(loop_scope="session")
async def test_lrn_jurisdiction_authenticated(get_auth_headers, transport):
    headers = get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/LRNjurisdiction/?tn=2163734600&cn=3305622000", headers=headers)
        assert resp.status_code == 200

@pytest.mark.asyncio(loop_scope="session")
async def test_lrn_jurisdiction_missing_params_authenticated(get_auth_headers, transport):
    headers = get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/LRNjurisdiction/", headers=headers)
        assert resp.status_code == 422

@pytest.mark.asyncio(loop_scope="session")
async def test_lrn_jurisdiction_invalid_params_authenticated(get_auth_headers, transport):
    headers = get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/LRNjurisdiction/?tn=123456&cn=330562200", headers=headers)
        assert resp.status_code == 422