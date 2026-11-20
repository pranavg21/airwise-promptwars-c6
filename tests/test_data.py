import httpx
import pytest

from airwise.data import AIR_URL, GEO_URL, ProviderError, TTLCache, fetch_json, finite, parse_air


def test_parse_preserves_scale_and_provenance(payload, location):
    s = parse_air(payload, location)
    assert s.us_aqi == 182
    assert s.pm2_5 == 90
    assert "NOT CPCB" in s.scale
    assert "not a local monitor" in s.data_kind
    assert len(s.hourly) == 72


def test_no_fabricated_current_when_upstream_null(payload, location):
    payload["current"]["us_aqi"] = None
    assert parse_air(payload, location).us_aqi is None


def test_reject_unusable_current_and_forecast(payload, location):
    payload["current"]["us_aqi"] = None
    payload["hourly"]["us_aqi"] = [None] * 72
    with pytest.raises(ProviderError):
        parse_air(payload, location)


def test_nonfinite_numbers_are_discarded():
    assert finite(float("nan")) is None
    assert finite(float("inf")) is None
    assert finite(-1) is None
    assert finite(True) is None
    assert finite(3.2) == 3.2


@pytest.mark.asyncio
async def test_cache_hits_and_eviction():
    cache = TTLCache(ttl=10, limit=2)
    await cache.put("one", 1)
    await cache.put("two", 2)
    assert await cache.get("one") == 1
    await cache.put("three", 3)
    assert await cache.get("one") is None
    assert await cache.get("three") == 3


@pytest.mark.asyncio
async def test_user_supplied_hostname_cannot_be_fetched():
    with pytest.raises(ProviderError):
        await fetch_json("http://127.0.0.1/private", {})


@pytest.mark.asyncio
async def test_geocoding_data_validated_and_cached(monkeypatch):
    from airwise.data import search_locations

    calls = []

    async def dummy_fetch(url, params):
        calls.append(url)
        return {
            "results": [
                {
                    "name": "Pune",
                    "latitude": 18.5204,
                    "longitude": 73.8567,
                    "country": "India",
                    "admin1": "Maharashtra",
                },
                {"name": "Broken", "latitude": 999, "longitude": 999},
                {"name": "Missing latitude"},
            ]
        }

    monkeypatch.setattr("airwise.data.fetch_json", dummy_fetch)
    results = await search_locations("Pune P. Test")
    again = await search_locations("PUNE P. TEST")
    assert len(results) == 1
    assert results[0].name == "Pune"
    assert results == again
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_air_data_cached_and_no_upstream_spam(monkeypatch, location, payload):
    from airwise.data import fetch_air

    calls = []

    async def dummy_fetch(url, params):
        calls.append(params)
        return payload

    monkeypatch.setattr("airwise.data.fetch_json", dummy_fetch)
    # Use unique coordinates to avoid other tests affecting this memoized cache.
    distinct = location.model_copy(update={"latitude": 28.65234, "longitude": 77.12345})
    first = await fetch_air(distinct)
    second = await fetch_air(distinct)
    assert first.model_time == second.model_time
    assert len(calls) == 1
    assert calls[0]["current"].startswith("us_aqi")


def test_upstream_current_outlier_returns_provider_error(payload, location):
    payload["current"]["us_aqi"] = 999999
    with pytest.raises(ProviderError):
        parse_air(payload, location)


@pytest.mark.asyncio
async def test_malformed_geocode_result_is_handled(monkeypatch):
    from airwise.data import search_locations

    async def malformed(url, params):
        return {"results": {"not": "a list"}}

    monkeypatch.setattr("airwise.data.fetch_json", malformed)
    with pytest.raises(ProviderError):
        await search_locations("No Such Place")


def mocked_upstream(monkeypatch, response):
    real = httpx.AsyncClient
    monkeypatch.setattr(
        "airwise.data.httpx.AsyncClient",
        lambda *a, **k: real(transport=httpx.MockTransport(lambda request: response)),
    )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, json={}),
        httpx.Response(200, json={"error": True, "reason": "Invalid coordinates"}),
        httpx.Response(200, content=b"not json"),
        httpx.Response(200, content=b"[" + b"0," * 300_000 + b"0]"),
    ],
    ids=["http-error", "declined", "not-json", "oversized"],
)
async def test_upstream_failures_become_provider_errors(monkeypatch, response):
    mocked_upstream(monkeypatch, response)
    with pytest.raises(ProviderError):
        await fetch_json(AIR_URL, {"latitude": 18.52, "longitude": 73.86})


async def test_upstream_payload_is_returned_when_valid(monkeypatch):
    mocked_upstream(monkeypatch, httpx.Response(200, json={"results": []}))
    assert await fetch_json(GEO_URL, {"name": "Pune"}) == {"results": []}
