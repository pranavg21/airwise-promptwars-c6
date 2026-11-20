"""One AQI classification for the dashboard and the plan, including boundaries and missing values."""

import math
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from airwise import main
from airwise.aqi import BANDS, UNAVAILABLE, band, classify
from airwise.models import Location, Profile, Snapshot

LOCATION = Location(name="Pune", country="India", latitude=18.52, longitude=73.86)
CASES = [
    (None, "Unavailable", "unavailable"),
    (0, "Good", "good"),
    (50, "Good", "good"),
    (50.5, "Moderate", "moderate"),
    (100, "Moderate", "moderate"),
    (101, "Unhealthy for sensitive groups", "sensitive"),
    (150, "Unhealthy for sensitive groups", "sensitive"),
    (151, "Unhealthy", "unhealthy"),
    (200, "Unhealthy", "unhealthy"),
    (201, "Very unhealthy", "very-unhealthy"),
    (300, "Very unhealthy", "very-unhealthy"),
    (301, "Hazardous", "hazardous"),
    (700, "Hazardous", "hazardous"),
]


def snapshot(aqi: float | None) -> Snapshot:
    return Snapshot(
        location=LOCATION,
        retrieved_at="2026-11-20T02:30Z",
        model_time="2026-11-20T08:00",
        timezone="Asia/Kolkata",
        us_aqi=aqi,
    )


def test_bands_are_ordered_and_cover_every_value():
    uppers = [b.upper for b in BANDS]
    assert uppers == sorted(uppers) and math.isinf(uppers[-1])
    assert len({b.key for b in (*BANDS, UNAVAILABLE)}) == len(BANDS) + 1


@pytest.mark.parametrize(("aqi", "label", "key"), CASES)
def test_snapshot_category_matches_classifier(aqi, label, key):
    assert classify(aqi)[0] == label
    assert band(aqi).key == key
    dumped = snapshot(aqi).model_dump()
    assert (dumped["category"], dumped["category_key"]) == (label, key)


@pytest.mark.asyncio
@pytest.mark.parametrize(("aqi", "label", "key"), CASES)
async def test_dashboard_and_plan_report_the_same_category(aqi, label, key):
    body = {"location": LOCATION.model_dump(), "profile": Profile().model_dump()}
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test")
    with (
        patch.object(main, "fetch_air", AsyncMock(return_value=snapshot(aqi))),
        patch.object(main, "gate", main.RateGate()),
    ):
        async with client:
            air = (await client.post("/api/air", json=LOCATION.model_dump())).json()
            plan = (await client.post("/api/plan", json=body)).json()
    assert air["category"] == plan["snapshot"]["category"] == plan["policy"]["category"] == label
    assert air["category_key"] == key
