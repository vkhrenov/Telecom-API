import pytest
from httpx import AsyncClient
from main import app
from tests.conftest import BASE_URL

# Test cases for jurisdiction API endpoint

@pytest.mark.asyncio(loop_scope="session")
async def test_jurisdiction_authenticated(get_auth_headers,transport):
    headers =  get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/jurisdiction/?dial_code=330405&dialing_code=216401", headers=headers)
        assert resp.status_code == 200

@pytest.mark.asyncio(loop_scope="session")
async def test_jurisdiction_missing_params_authenticated(get_auth_headers,transport):
    headers =  get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/jurisdiction/", headers=headers)
        assert resp.status_code == 422
        
@pytest.mark.asyncio(loop_scope="session")
async def test_jurisdiction_invalid_params_authenticated(get_auth_headers,transport):
    headers =  get_auth_headers
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/v1/jurisdiction/?dial_code=invalid&dialing_code=216XXX", headers=headers)
        assert resp.status_code == 422        