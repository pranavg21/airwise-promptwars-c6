"""Gemini adapter under failure: deadlines, answer reuse, fallback model and diagnostics.

No live calls: the real adapter talks to an in-process mock transport.
"""

import asyncio
import json
import logging
import time

import httpx
import pytest

from airwise import ai, config, main
from airwise.ai import AiUnavailableError, personalize
from airwise.models import Hour, Location, Profile, Snapshot
from airwise.policy import generate_policy

REAL_CLIENT = httpx.AsyncClient
REPLY = {
    "summary": "Move strenuous play to a cleaner hour.",
    "steps": ["Switch off the engine while waiting.", "Avoid incense indoors."],
    "rationale": "These steps reduce exposure without new purchases.",
}
QUOTA = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}}


def envelope(reply=REPLY):
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(reply)}]}}]}


@pytest.fixture
def gemini(monkeypatch):
    """Route the adapter's HTTP client to a scripted handler; returns the list of requests seen."""
    seen: list[httpx.Request] = []
    script = {"handler": lambda request: httpx.Response(200, json=envelope())}

    async def handler(request):
        seen.append(request)
        result = script["handler"](request)
        return await result if asyncio.iscoroutine(result) else result

    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    monkeypatch.setenv("GEMINI_MODEL", "primary-model")
    monkeypatch.delenv("GEMINI_FALLBACK_MODEL", raising=False)
    monkeypatch.setattr(
        ai.httpx, "AsyncClient", lambda *a, **k: REAL_CLIENT(transport=httpx.MockTransport(handler))
    )
    return seen, script


def plan_inputs(snapshot, **profile):
    profile = Profile(**profile)
    return snapshot, profile, generate_policy(snapshot, profile)


async def test_identical_requests_reuse_the_validated_answer(gemini, snapshot):
    seen, _ = gemini
    inputs = plan_inputs(snapshot)
    first = await personalize(*inputs, question="How can we reduce idling?")
    second = await personalize(*inputs, question="How can we reduce idling?")
    await personalize(*inputs, question="Which indoor smoke sources can we remove?")
    assert first == second
    assert len(seen) == 2


def pune_forecast(pm):
    """One fixed place and model time; only the hourly PM2.5 values differ between calls."""
    hours = [Hour(time=f"2026-11-19T{8 + i:02}:00", pm2_5=value, us_aqi=80) for i, value in enumerate(pm)]
    return Snapshot(
        location=Location(name="Pune", latitude=18.52, longitude=73.86),
        retrieved_at="2026-11-19T08:00Z",
        model_time=hours[0].time,
        timezone="Asia/Kolkata",
        hourly=hours,
    )


async def test_a_revised_forecast_that_changes_the_decision_is_not_served_from_cache(gemini):
    seen, _ = gemini
    profile = Profile(start_hour=8, outdoor_minutes=120)
    shifts = []
    for pm in ([60, 60, 1, 200], [60, 60, 1, 1]):
        snapshot = pune_forecast(pm)
        policy = generate_policy(snapshot, profile)
        shifts.append(policy.shift.recommended_time)
        await personalize(snapshot, profile, policy)
        sent = json.loads(json.loads(seen[-1].content)["contents"][0]["parts"][0]["text"])
        assert sent["activity_timing_recommendation"]["recommended_time"] == shifts[-1]
    assert shifts == ["2026-11-19T09:00", "2026-11-19T10:00"]
    assert len(seen) == 2


async def test_failures_are_not_cached(gemini, snapshot):
    seen, script = gemini
    script["handler"] = lambda request: httpx.Response(429, json=QUOTA)
    with pytest.raises(AiUnavailableError):
        await personalize(*plan_inputs(snapshot))
    script["handler"] = lambda request: httpx.Response(200, json=envelope())
    assert (await personalize(*plan_inputs(snapshot))).summary == REPLY["summary"]
    assert len(seen) == 2


async def test_slow_model_is_abandoned_within_the_budget(gemini, snapshot):
    _, script = gemini

    async def slow(request):
        await asyncio.sleep(5)
        return httpx.Response(200, json=envelope())

    script["handler"] = slow
    started = time.monotonic()
    with pytest.raises(AiUnavailableError):
        await personalize(*plan_inputs(snapshot), budget_s=0.2)
    assert time.monotonic() - started < 2


async def test_fallback_model_answers_when_primary_is_out_of_quota(gemini, snapshot, monkeypatch):
    seen, script = gemini
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "fallback-model")
    script["handler"] = lambda request: (
        httpx.Response(429, json=QUOTA)
        if "primary-model" in request.url.path
        else httpx.Response(200, json=envelope())
    )
    reply = await personalize(*plan_inputs(snapshot))
    assert reply.summary == REPLY["summary"]
    assert [r.url.path.rsplit("/", 1)[-1] for r in seen] == [
        "primary-model:generateContent",
        "fallback-model:generateContent",
    ]


async def test_failure_reason_is_logged_without_secrets_or_content(gemini, snapshot, caplog):
    _, script = gemini
    script["handler"] = lambda request: httpx.Response(429, json=QUOTA)
    with caplog.at_level(logging.WARNING, logger="airwise.ai"), pytest.raises(AiUnavailableError):
        await personalize(*plan_inputs(snapshot), question="Private question about my asthma?")
    assert "model=primary-model reason=http_status status=429" in caplog.text
    for private in ("test-only-key", "asthma", "Pune", "Delhi"):
        assert private not in caplog.text


@pytest.mark.parametrize(
    ("reply", "reason"),
    [
        (
            {"summary": "AQI is 180 today.", "steps": ["Stay in.", "Close windows."], "rationale": "High."},
            "numeric_claim",
        ),
        ({"summary": "Too short", "steps": ["one"], "rationale": "x"}, "schema"),
    ],
)
async def test_rejected_replies_name_the_reason(gemini, snapshot, caplog, reply, reason):
    _, script = gemini
    script["handler"] = lambda request: httpx.Response(200, json=envelope(reply))
    with caplog.at_level(logging.WARNING, logger="airwise.ai"), pytest.raises(AiUnavailableError):
        await personalize(*plan_inputs(snapshot))
    assert f"reason={reason}" in caplog.text


async def test_plan_skips_ai_when_too_little_time_remains(gemini, snapshot, monkeypatch, location):
    seen, _ = gemini
    monkeypatch.setattr(config, "REQUEST_BUDGET_S", 1.0)

    async def fixed_air(_location):
        return snapshot

    monkeypatch.setattr(main, "fetch_air", fixed_air)
    monkeypatch.setattr(main, "gate", main.RateGate())
    body = {"location": location.model_dump(), "profile": Profile().model_dump(), "ai_consent": True}
    async with REAL_CLIENT(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
        response = await client.post("/api/plan", json=body)
    assert response.status_code == 200
    assert response.json()["ai_status"] == "unavailable"
    assert response.json()["policy"]["cards"]
    assert seen == []


def test_settings_validate_models_and_ignore_duplicate_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    monkeypatch.setenv("GEMINI_MODEL", "primary-model")
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "primary-model")
    assert config.gemini_settings().models == ("primary-model",)
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "../escape")
    with pytest.raises(config.ConfigurationError):
        config.gemini_settings()
    monkeypatch.delenv("GEMINI_API_KEY")
    with pytest.raises(config.ConfigurationError):
        config.gemini_settings()


def _raise(error):
    def handler(request):
        raise error(request)

    return handler


@pytest.mark.parametrize(
    ("respond", "reason"),
    [
        (lambda request: httpx.Response(200, content=b"x" * (config.MAX_GEMINI_BYTES + 1)), "oversize"),
        (_raise(lambda request: httpx.ReadTimeout("slow", request=request)), "timeout"),
        (_raise(lambda request: httpx.ConnectError("refused", request=request)), "transport_or_envelope"),
        (lambda request: httpx.Response(200, content=b"not json"), "transport_or_envelope"),
        (lambda request: httpx.Response(200, json=[]), "envelope"),
        (lambda request: httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}), "envelope"),
    ],
    ids=["oversize", "timeout", "connection", "not-json", "not-an-object", "no-candidates"],
)
async def test_every_upstream_failure_is_unavailable_with_a_reason(gemini, snapshot, caplog, respond, reason):
    _, script = gemini
    script["handler"] = respond
    with caplog.at_level(logging.WARNING, logger="airwise.ai"), pytest.raises(AiUnavailableError):
        await personalize(*plan_inputs(snapshot))
    assert f"reason={reason}" in caplog.text
