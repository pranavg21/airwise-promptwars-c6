"""Bounded, cached, server-side external data retrieval (no user-defined URLs)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import math
import time
from typing import Any

from pydantic import ValidationError

import httpx

from .models import Hour, Location, Snapshot

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

class ProviderError(Exception):
    """External dataset is unavailable or malformed; do not fabricate values."""


class TTLCache:
    def __init__(self, ttl: int, limit: int = 128) -> None:
        self.ttl = ttl
        self.limit = limit
        self._items: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            value = self._items.get(key)
            if value is None:
                return None
            if value[0] < time.monotonic():
                del self._items[key]
                return None
            return value[1]

    async def put(self, key: str, value: Any) -> None:
        async with self._lock:
            if len(self._items) >= self.limit:
                oldest = min(self._items, key=lambda k: self._items[k][0])
                del self._items[oldest]
            self._items[key] = (time.monotonic() + self.ttl, value)


geo_cache = TTLCache(ttl=24 * 3600)
air_cache = TTLCache(ttl=8 * 60)


def finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not math.isfinite(result) or result < 0:
        return None
    return result


async def fetch_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    # SSRF prevention: caller may never pass a URL; URL is one of two constants.
    if url not in {GEO_URL, AIR_URL}:
        raise ProviderError("Unexpected upstream host")
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(8.0, connect=3.0), follow_redirects=False,
            headers={"User-Agent": "AirWise-PromptWars/1.0"}
        ) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            if len(response.content) > 500_000:
                raise ProviderError("Upstream payload exceeded allowed size")
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("error"):
                raise ProviderError("Upstream declined request")
            return payload
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError("Air data provider could not be reached") from exc


async def search_locations(query: str) -> list[Location]:
    key = query.strip().lower()
    cached = await geo_cache.get(key)
    if cached is not None:
        return cached
    raw = await fetch_json(GEO_URL, {"name": query, "count": 6, "language": "en", "format": "json"})
    items = []
    results = raw.get("results") or []
    if not isinstance(results, list):
        raise ProviderError("Geocoding provider returned malformed results")
    for city in results[:6]:
        try:
            items.append(Location(
                name=city["name"], latitude=city["latitude"],
                longitude=city["longitude"], country=city.get("country", ""),
                region=city.get("admin1", "")
            ))
        except (KeyError, TypeError, ValueError):
            continue
    await geo_cache.put(key, items)
    return items


def parse_air(raw: dict[str, Any], location: Location) -> Snapshot:
    """Never use imputed or synthetic values when upstream values are absent."""
    current = raw.get("current")
    hourly = raw.get("hourly")
    if not isinstance(current, dict) or not isinstance(hourly, dict):
        raise ProviderError("Current air readings or hourly forecast missing")
    times = hourly.get("time")
    if not isinstance(times, list) or len(times) == 0:
        raise ProviderError("Hourly forecast unavailable")
    model_time = current.get("time")
    if not isinstance(model_time, str):
        raise ProviderError("Current data timestamp missing")
    points: list[Hour] = []
    for idx, when in enumerate(times[:72]):
        if not isinstance(when, str):
            continue
        def at(key: str) -> float | None:
            values = hourly.get(key)
            return finite(values[idx]) if isinstance(values, list) and idx < len(values) else None
        try:
            points.append(Hour(time=when, us_aqi=at("us_aqi"), pm2_5=at("pm2_5"), pm10=at("pm10")))
        except ValueError:
            continue
    if finite(current.get("us_aqi")) is None and not any(p.us_aqi is not None for p in points):
        raise ProviderError("No AQI predictions in upstream response")
    try:
        return Snapshot(
        location=location, retrieved_at=datetime.now(timezone.utc).isoformat(),
        model_time=model_time, timezone=str(raw.get("timezone", "Unknown"))[:60],
        us_aqi=finite(current.get("us_aqi")), pm2_5=finite(current.get("pm2_5")),
        pm10=finite(current.get("pm10")), ozone=finite(current.get("ozone")),
        nitrogen_dioxide=finite(current.get("nitrogen_dioxide")), hourly=points
        )
    except ValidationError as exc:
        raise ProviderError("Upstream air values are outside validated bounds") from exc


async def fetch_air(location: Location) -> Snapshot:
    # Rounded location keys avoid redundant full-precision calls; cache is ephemeral.
    key = f"{location.latitude:.3f}:{location.longitude:.3f}"
    cached = await air_cache.get(key)
    if cached is not None:
        return cached.model_copy(update={"location": location})
    raw = await fetch_json(AIR_URL, {
        "latitude": round(location.latitude, 5), "longitude": round(location.longitude, 5),
        "current": "us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide",
        "hourly": "us_aqi,pm2_5,pm10",
        "timezone": "auto", "forecast_days": 3
    })
    snapshot = parse_air(raw, location)
    await air_cache.put(key, snapshot)
    return snapshot
