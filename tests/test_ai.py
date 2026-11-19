import json
import pytest
from unittest.mock import AsyncMock, patch
from airwise.ai import AiUnavailable, build_context, configured, personalize
from airwise.models import Profile
from airwise.policy import generate_policy


def test_ai_context_minimizes_user_data(snapshot):
    profile=Profile(children=True, priorities=["school"])
    ctx=build_context(snapshot,profile,generate_policy(snapshot,profile),"Is school okay?")
    encoded=json.dumps(ctx)
    assert 'example.com' not in encoded
    assert "street_address" not in encoded
    assert "US AQI - NOT India CPCB" in encoded
    assert "question" in encoded


@pytest.mark.asyncio
async def test_ai_not_configured_has_no_fake_model_output(snapshot,monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY",raising=False)
    profile=Profile()
    assert not configured()
    with pytest.raises(AiUnavailable):
        await personalize(snapshot,profile,generate_policy(snapshot,profile))


@pytest.mark.asyncio
async def test_gemini_success_response_is_schema_validated(snapshot,monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","test-only-key")
    profile=Profile()
    expected={"summary":"Bring your planned walk indoors if possible.",
              "steps":["Try a less polluted time.","Avoid indoor smoke sources."],
              "rationale":"The forecast reports elevated particulate estimates."}
    fake=AsyncMock()
    fake.status_code=200
    fake.content=b'{}'
    fake.json=lambda:{"candidates":[{"content":{"parts":[{"text":json.dumps(expected)}]}}]}
    fake.raise_for_status=lambda:None
    with patch('airwise.ai.httpx.AsyncClient') as client:
        client.return_value.__aenter__.return_value.post=AsyncMock(return_value=fake)
        result=await personalize(snapshot,profile,generate_policy(snapshot,profile))
    assert result.summary==expected['summary']
    assert len(result.steps)==2


@pytest.mark.asyncio
async def test_gemini_invalid_json_fails_closed(snapshot,monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","test-only-key")
    profile=Profile()
    fake=AsyncMock()
    fake.content=b'{}';fake.raise_for_status=lambda:None
    fake.json=lambda:{"candidates":[{"content":{"parts":[{"text":'{garbage'}]}}]}
    with patch('airwise.ai.httpx.AsyncClient') as client:
        client.return_value.__aenter__.return_value.post=AsyncMock(return_value=fake)
        with pytest.raises(AiUnavailable):await personalize(snapshot,profile,generate_policy(snapshot,profile))


@pytest.mark.asyncio
async def test_model_id_configuration_rejected_before_network(snapshot,monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test-only-key')
    monkeypatch.setenv('GEMINI_MODEL','../bad/path')
    p=Profile()
    with pytest.raises(AiUnavailable):await personalize(snapshot,p,generate_policy(snapshot,p))


@pytest.mark.asyncio
async def test_ai_response_too_verbose_rejected(snapshot,monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test-only-key')
    monkeypatch.setenv('GEMINI_MODEL','gemini-3.5-flash-lite')
    p=Profile()
    fake=AsyncMock()
    fake.content=b'{}';fake.raise_for_status=lambda:None
    fake.json=lambda:{'candidates':[{'content':{'parts':[{'text':json.dumps({'summary':'x'*1000,'steps':['good step','another good step'],'rationale':'good reason'})}]}}]}
    with patch('airwise.ai.httpx.AsyncClient') as client:
        client.return_value.__aenter__.return_value.post=AsyncMock(return_value=fake)
        with pytest.raises(AiUnavailable):await personalize(snapshot,p,generate_policy(snapshot,p))


@pytest.mark.asyncio
async def test_ai_claiming_unverified_percentage_is_rejected(snapshot,monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test-only-key')
    monkeypatch.setenv('GEMINI_MODEL','gemini-3.5-flash-lite')
    p=Profile()
    fake=AsyncMock()
    fake.content=b'{}';fake.raise_for_status=lambda:None
    fake.json=lambda:{'candidates':[{'content':{'parts':[{'text':json.dumps({'summary':'This will improve lung health by 80%.','steps':['Try a cleaner hour.','Avoid unnecessary burning.'],'rationale':'The pollutant model is uncertain.'})}]}}]}
    with patch('airwise.ai.httpx.AsyncClient') as client:
        client.return_value.__aenter__.return_value.post=AsyncMock(return_value=fake)
        with pytest.raises(AiUnavailable):await personalize(snapshot,p,generate_policy(snapshot,p))
