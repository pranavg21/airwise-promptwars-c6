"""Boundary and failure paths at the edges of the system: forecast shapes, guards, limits and models."""

import time
from collections import deque

import httpx
import pytest
from pydantic import ValidationError
from starlette.requests import Request

from airwise import config, main
from airwise.cache import TTLCache
from airwise.data import ProviderError, parse_air
from airwise.models import AiResponse, Hour, Location, Profile, Snapshot
from airwise.policy import find_lower_hour
from airwise.security import RateGate, reject_unsafe_request

LOCATION = Location(name="Pune", country="India", latitude=18.52, longitude=73.86)


@pytest.mark.parametrize(
    "raw",
    [
        {"current": "not an object", "hourly": {"time": ["2026-11-20T06:00"]}},
        {"current": {"us_aqi": 80}, "hourly": {"time": ["2026-11-20T06:00"], "us_aqi": [80]}},
        {"current": {"time": "2026-11-20T06:00", "us_aqi": 80}, "hourly": {"time": []}},
    ],
    ids=["current-not-object", "no-timestamp", "no-hours"],
)
def test_malformed_forecasts_are_rejected_not_repaired(raw):
    with pytest.raises(ProviderError):
        parse_air(raw, LOCATION)


def test_unusable_forecast_hours_are_skipped_not_imputed():
    raw = {
        "current": {"time": "2026-11-20T06:00", "us_aqi": 80},
        "hourly": {
            "time": ["2026-11-20T06:00", 7, "2026-11-20T08:00", "2026-11-20T09:00"],
            "us_aqi": [80, 80, 5000, 90],
        },
    }
    hours = parse_air(raw, LOCATION).hourly
    assert [h.time for h in hours] == ["2026-11-20T06:00", "2026-11-20T09:00"]


def test_repeated_clock_hour_gives_no_timing_advice():
    """A repeated local hour (daylight-saving change) makes the activity window ambiguous."""
    times = ["2026-11-20T06:00", "2026-11-20T07:00", "2026-11-20T07:00", "2026-11-20T08:00"]
    hours = [Hour(time=t, us_aqi=100, pm2_5=pm) for t, pm in zip(times, [60, 60, 10, 10], strict=True)]
    snapshot = Snapshot(
        location=LOCATION,
        retrieved_at="2026-11-20T00:30Z",
        model_time="2026-11-20T06:00",
        timezone="Europe/London",
        us_aqi=100,
        hourly=hours,
    )
    _, shift = find_lower_hour(snapshot, Profile(start_hour=6, outdoor_minutes=60))
    assert shift is None


async def test_expired_cache_entries_are_dropped():
    cache: TTLCache[int] = TTLCache(ttl=-1, limit=2)
    await cache.put("stale", 1)
    assert await cache.get("stale") is None
    assert await cache.get("stale") is None


def test_rate_gate_forgets_old_requests_and_idle_clients(monkeypatch):
    gate = RateGate()
    assert gate.check("client", 1, 0)
    assert gate.check("client", 1, 0), "a zero-length window should have expired the first request"
    monkeypatch.setattr(config, "RATE_GATE_MAX_KEYS", 1)
    gate.requests["idle"] = deque([time.monotonic() - config.RATE_WINDOW_S - 1])
    assert gate.check("new", 1, 60)
    assert "idle" not in gate.requests and "new" in gate.requests


def _request(method, path, headers):
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


@pytest.mark.parametrize(
    ("method", "path", "headers", "status"),
    [
        ("POST", "/api/air", {"content-type": "application/json"}, None),
        ("GET", "/api/health", {}, None),
        ("POST", "/not-api", {"content-type": "text/plain"}, None),
        ("POST", "/api/air", {"content-type": "text/plain"}, 415),
        ("POST", "/api/air", {"content-type": "application/json", "sec-fetch-site": "cross-site"}, 403),
        ("POST", "/api/air", {"content-type": "application/json", "content-length": "-1"}, 400),
        ("POST", "/api/air", {"content-type": "application/json", "content-length": "99999"}, 413),
    ],
    ids=["chunked-json", "read", "non-api-write", "not-json", "cross-site", "bad-length", "too-large"],
)
def test_request_guard(method, path, headers, status):
    rejection = reject_unsafe_request(_request(method, path, headers))
    assert (rejection.status_code if rejection else None) == status


async def test_geocoder_outage_is_reported_without_results(monkeypatch):
    async def offline(_query):
        raise ProviderError("offline")

    monkeypatch.setattr(main, "search_locations", offline)
    monkeypatch.setattr(main, "gate", RateGate())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as c:
        response = await c.get("/api/geo", params={"q": "Pune"})
    assert response.status_code == 503
    assert "city shortcut" in response.json()["detail"]


async def test_question_is_refused_when_no_time_is_left_for_gemini(monkeypatch, snapshot):
    async def fixed_air(_location):
        return snapshot

    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    monkeypatch.setattr(config, "REQUEST_BUDGET_S", 1.0)
    monkeypatch.setattr(main, "fetch_air", fixed_air)
    monkeypatch.setattr(main, "gate", RateGate())
    body = {
        "location": LOCATION.model_dump(),
        "profile": Profile().model_dump(),
        "ai_consent": True,
        "question": "Is the morning walk safe?",
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as c:
        response = await c.post("/api/ask", json=body)
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


def test_profile_rejects_repeated_priorities():
    with pytest.raises(ValidationError):
        Profile(priorities=["home", "home"])


@pytest.mark.parametrize("step", ["no", "x" * 301])
def test_ai_steps_must_be_concise(step):
    with pytest.raises(ValidationError):
        AiResponse(summary="A short summary.", steps=[step, "Avoid incense indoors."], rationale="Because.")
