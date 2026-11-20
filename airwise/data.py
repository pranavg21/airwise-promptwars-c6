"""Bounded, cached, server-side retrieval of Open-Meteo geocoding and air-quality data.

Callers never supply a URL: only the two constants below can be fetched.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import ValidationError

from . import config
from .cache import TTLCache
from .models import Hour, Location, Snapshot

__all__ = ["ProviderError", "TTLCache", "fetch_air", "fetch_json", "finite", "parse_air", "search_locations"]

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
ALLOWED_URLS = frozenset({GEO_URL, AIR_URL})
USER_AGENT = "AirWise-PromptWars/1.0"


class ProviderError(Exception):
    """External dataset is unavailable or malformed; do not fabricate values."""


geo_cache: TTLCache[list[Location]] = TTLCache(config.GEO_CACHE_TTL_S, config.CACHE_MAX_ENTRIES)
air_cache: TTLCache[Snapshot] = TTLCache(config.AIR_CACHE_TTL_S, config.CACHE_MAX_ENTRIES)


def finite(value: Any) -> float | None:
    """A non-negative finite number, or None for anything else (including booleans)."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    result = float(value)
    if not math.isfinite(result) or result < 0:
        return None
    return result


async def fetch_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET one of the two allowed Open-Meteo URLs and return its JSON object, or raise ProviderError."""
    if url not in ALLOWED_URLS:
        raise ProviderError("Unexpected upstream host")
    timeout = httpx.Timeout(config.FORECAST_READ_TIMEOUT_S, connect=config.FORECAST_CONNECT_TIMEOUT_S)
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=False, headers={"User-Agent": USER_AGENT}
        ) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            if len(response.content) > config.MAX_FORECAST_BYTES:
                raise ProviderError("Upstream payload exceeded allowed size")
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError("Air data provider could not be reached") from exc
    if not isinstance(payload, dict) or payload.get("error"):
        raise ProviderError("Upstream declined request")
    return payload


def _location(city: dict[str, Any]) -> Location | None:
    """A validated place from one geocoding result, or None when it is incomplete or out of range."""
    try:
        return Location(
            name=city["name"],
            latitude=city["latitude"],
            longitude=city["longitude"],
            country=city.get("country", ""),
            region=city.get("admin1", ""),
        )
    except (KeyError, TypeError, ValueError):
        return None


async def search_locations(query: str) -> list[Location]:
    """Up to six validated places for a typed name, cached for a day per normalized query."""
    key = query.strip().lower()
    cached = await geo_cache.get(key)
    if cached is not None:
        return cached
    raw = await fetch_json(
        GEO_URL, {"name": query, "count": config.GEOCODING_RESULTS, "language": "en", "format": "json"}
    )
    results = raw.get("results") or []
    if not isinstance(results, list):
        raise ProviderError("Geocoding provider returned malformed results")
    locations = [loc for loc in map(_location, results[: config.GEOCODING_RESULTS]) if loc is not None]
    await geo_cache.put(key, locations)
    return locations


def _value_at(hourly: dict[str, Any], key: str, index: int) -> float | None:
    """The finite, non-negative value at `index` of an hourly series, or None."""
    values = hourly.get(key)
    return finite(values[index]) if isinstance(values, list) and index < len(values) else None


def _hourly_points(hourly: dict[str, Any]) -> list[Hour]:
    """Hourly forecast points; missing upstream values stay missing, never imputed."""
    times = hourly.get("time")
    if not isinstance(times, list) or not times:
        raise ProviderError("Hourly forecast unavailable")
    points = []
    for index, when in enumerate(times[: config.MAX_FORECAST_HOURS]):
        if not isinstance(when, str):
            continue
        try:
            points.append(
                Hour(
                    time=when,
                    us_aqi=_value_at(hourly, "us_aqi", index),
                    pm2_5=_value_at(hourly, "pm2_5", index),
                    pm10=_value_at(hourly, "pm10", index),
                )
            )
        except ValueError:
            continue
    return points


def parse_air(raw: dict[str, Any], location: Location) -> Snapshot:
    """Validated snapshot of current values and the hourly forecast."""
    current, hourly = raw.get("current"), raw.get("hourly")
    if not isinstance(current, dict) or not isinstance(hourly, dict):
        raise ProviderError("Current air readings or hourly forecast missing")
    model_time = current.get("time")
    if not isinstance(model_time, str):
        raise ProviderError("Current data timestamp missing")
    points = _hourly_points(hourly)
    if finite(current.get("us_aqi")) is None and all(p.us_aqi is None for p in points):
        raise ProviderError("No AQI predictions in upstream response")
    try:
        return Snapshot(
            location=location,
            retrieved_at=datetime.now(UTC).isoformat(),
            model_time=model_time,
            timezone=str(raw.get("timezone", "Unknown"))[:60],
            us_aqi=finite(current.get("us_aqi")),
            pm2_5=finite(current.get("pm2_5")),
            pm10=finite(current.get("pm10")),
            ozone=finite(current.get("ozone")),
            nitrogen_dioxide=finite(current.get("nitrogen_dioxide")),
            hourly=points,
        )
    except ValidationError as exc:
        raise ProviderError("Upstream air values are outside validated bounds") from exc


def location_key(location: Location) -> str:
    """Rounded coordinates, so nearby requests share one upstream call."""
    places = config.LOCATION_CACHE_DECIMALS
    return f"{location.latitude:.{places}f}:{location.longitude:.{places}f}"


async def fetch_air(location: Location) -> Snapshot:
    """Current and hourly modeled air quality for a place, cached for eight minutes per rounded location."""
    key = location_key(location)
    cached = await air_cache.get(key)
    if cached is not None:
        return cached.model_copy(update={"location": location})
    places = config.UPSTREAM_COORDINATE_DECIMALS
    raw = await fetch_json(
        AIR_URL,
        {
            "latitude": round(location.latitude, places),
            "longitude": round(location.longitude, places),
            "current": "us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide",
            "hourly": "us_aqi,pm2_5,pm10",
            "timezone": "auto",
            "forecast_days": config.FORECAST_DAYS,
        },
    )
    snapshot = parse_air(raw, location)
    await air_cache.put(key, snapshot)
    return snapshot
