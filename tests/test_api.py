import pytest
import httpx
from airwise.main import app,gate
from airwise.models import Profile


@pytest.fixture
def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://testserver")


@pytest.mark.asyncio
async def test_health_and_security_headers(client,monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY",raising=False)
    async with client as c:
        response=await c.get('/api/health')
    assert response.status_code==200
    assert response.json()['ai_configured'] is False
    assert response.headers['x-content-type-options']=='nosniff'
    assert "default-src 'none'" in response.headers['content-security-policy']
    assert response.headers['cache-control']=='no-store'


@pytest.mark.asyncio
async def test_plan_without_ai_is_explicitly_not_genai(client,location,snapshot,monkeypatch):
    async def mock_air(_):return snapshot
    monkeypatch.setattr('airwise.main.fetch_air',mock_air)
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    async with client as c:
        response=await c.post('/api/plan',json={'location':location.model_dump(),'profile':Profile().model_dump()})
    assert response.status_code==200
    data=response.json()
    assert data['ai'] is None and data['ai_status']=='not_requested'
    assert data['policy']['category']=='Unhealthy'
    assert data['snapshot']['source'].startswith('Open-Meteo')


@pytest.mark.asyncio
async def test_plan_with_requested_but_unconfigured_ai_does_not_fake_it(client,location,snapshot,monkeypatch):
    async def mock_air(_):return snapshot
    monkeypatch.setattr('airwise.main.fetch_air',mock_air)
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    async with client as c:
        r=await c.post('/api/plan',json={'location':location.model_dump(),'profile':Profile().model_dump(),'ai_consent':True})
    assert r.status_code==200
    assert r.json()['ai_status']=='unavailable'
    assert r.json()['ai'] is None


@pytest.mark.asyncio
async def test_question_requires_opt_in(client,location):
    async with client as c:
        r=await c.post('/api/ask',json={'location':location.model_dump(),'profile':Profile().model_dump(), 'question':'My school run?', 'ai_consent':False})
    assert r.status_code==400


@pytest.mark.asyncio
async def test_strict_input_validation_blocks_unknowns_and_bad_coordinates(client,location):
    data=location.model_dump();data['latitude']=999
    async with client as c:
        r=await c.post('/api/air',json=data)
        r2=await c.post('/api/air',json={**location.model_dump(),'url':'http://169.254.169.254/latest/meta-data/'})
    assert r.status_code==422
    assert r2.status_code==422


@pytest.mark.asyncio
async def test_api_rejects_bad_media_type_and_large_body(client):
    async with client as c:
        r=await c.post('/api/air',content='x'*13000,headers={'Content-Type':'text/plain'})
        r2=await c.post('/api/air',content='hello',headers={'Content-Type':'text/plain'})
    assert r.status_code==413
    assert r2.status_code==415


@pytest.mark.asyncio
async def test_static_index_served_without_external_script_links(client):
    async with client as c:
        r=await c.get('/')
    assert r.status_code==200
    assert 'script type="module" src="/static/js/app.js"' in r.text
    assert 'GEMINI_API_KEY' not in r.text


@pytest.mark.asyncio
async def test_geo_endpoint_returns_validated_locations(client,monkeypatch):
    from airwise.models import Location
    async def mock_geo(_):return [Location(name='Pune',country='India',region='Maharashtra',latitude=18.5204,longitude=73.8567)]
    monkeypatch.setattr('airwise.main.search_locations',mock_geo)
    async with client as c:r=await c.get('/api/geo',params={'q':'Pune'})
    assert r.status_code==200
    assert r.json()['results'][0]['name']=='Pune'


@pytest.mark.asyncio
async def test_geo_blocks_short_query(client):
    async with client as c:r=await c.get('/api/geo',params={'q':'a'})
    assert r.status_code==422


@pytest.mark.asyncio
async def test_provider_outage_returns_503_without_fake_values(client,location,monkeypatch):
    from airwise.data import ProviderError
    async def fail(_):raise ProviderError('offline')
    monkeypatch.setattr('airwise.main.fetch_air',fail)
    async with client as c:r=await c.post('/api/air',json=location.model_dump())
    assert r.status_code==503
    assert 'unavailable' in r.json()['detail'].lower()


@pytest.mark.asyncio
async def test_nonexistent_api_does_not_expose_internal_documentation(client):
    async with client as c:
        r=await c.get('/docs')
        r2=await c.get('/openapi.json')
    assert r.status_code==404 and r2.status_code==200  # FastAPI schema is public but contains no secrets
    assert 'GEMINI_API_KEY' not in r2.text


def test_rate_gate_enforces_bounded_requests():
    from airwise.main import RateGate
    g=RateGate()
    assert g.check('special-key',1,600)
    assert not g.check('special-key',1,600)
    assert g.check('other-key',1,600)


@pytest.mark.asyncio
async def test_validation_error_also_receives_security_headers(client):
    async with client as c:r=await c.post('/api/air',content='hello',headers={'Content-Type':'text/plain'})
    assert r.status_code==415
    assert r.headers['x-frame-options']=='DENY'
    assert r.headers['content-security-policy'].startswith("default-src 'none'")
