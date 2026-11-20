"""Realistic but clearly synthetic CAMS-shaped fixtures for deterministic testing."""

import pytest

from airwise import ai, data
from airwise.data import parse_air
from airwise.models import Location


@pytest.fixture(autouse=True)
def isolated_caches():
    """Every test starts without cached forecasts, places or AI replies."""
    for cache in (ai.response_cache, data.air_cache, data.geo_cache):
        cache.clear()
    yield


@pytest.fixture
def location():
    return Location(name="Delhi", region="Delhi", country="India", latitude=28.6139, longitude=77.209)


@pytest.fixture
def payload():
    hours = [f"2026-11-{17 + i // 24:02d}T{i % 24:02d}:00" for i in range(72)]
    aqi = [165.0] * 72
    pm = [92.0] * 72
    aqi[8] = 225
    pm[8] = 180
    aqi[15] = 110
    pm[15] = 46
    return {
        "timezone": "Asia/Kolkata",
        "current": {
            "time": "2026-11-17T06:00",
            "us_aqi": 182,
            "pm2_5": 90,
            "pm10": 140,
            "ozone": 32,
            "nitrogen_dioxide": 18,
        },
        "hourly": {"time": hours, "us_aqi": aqi, "pm2_5": pm, "pm10": [140.0] * 72},
    }


@pytest.fixture
def snapshot(payload, location):
    return parse_air(payload, location)
