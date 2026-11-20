"""The 24-hour outlook is defined once, so the dashboard and the planner see the same hours."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx

from airwise import main
from airwise.forecast import lowest_aqi_hour, upcoming_hours
from airwise.models import Hour, Location, Profile, Snapshot

LOCATION = Location(name="Pune", country="India", latitude=18.52, longitude=73.86)
START = datetime(2026, 11, 20, 6)


def gappy_snapshot() -> Snapshot:
    """Hour +4 missing; every in-window AQI is 80; the reading exactly 24 hours later is 20."""
    hours = [
        Hour(
            time=(START + timedelta(hours=offset)).isoformat(timespec="minutes"),
            us_aqi=20 if offset == 24 else 80,
            pm2_5=30,
        )
        for offset in range(25)
        if offset != 4
    ]
    return Snapshot(
        location=LOCATION,
        retrieved_at="2026-11-20T00:30Z",
        model_time="2026-11-20T06:00",
        timezone="Asia/Kolkata",
        us_aqi=80,
        hourly=hours,
    )


def test_outlook_counts_elapsed_hours_not_rows():
    outlook = gappy_snapshot().outlook
    assert len(outlook) == 23
    assert outlook[-1].time == "2026-11-21T05:00"
    assert all(hour.us_aqi == 80 for hour in outlook)
    assert gappy_snapshot().outlook_lowest.time == "2026-11-20T06:00"


def test_outlook_ignores_past_and_unparseable_times():
    hours = [Hour(time="2026-11-20T05:00", us_aqi=10), Hour(time="2026-11-20T06:00", us_aqi=90)]
    assert [h.time for h in upcoming_hours("2026-11-20T06:00", hours)] == ["2026-11-20T06:00"]
    assert upcoming_hours("not a time", hours) == []
    assert lowest_aqi_hour([Hour(time="2026-11-20T06:00")]) is None


async def test_dashboard_and_plan_agree_on_an_incomplete_forecast():
    body = {"location": LOCATION.model_dump(), "profile": Profile().model_dump()}
    with (
        patch.object(main, "fetch_air", AsyncMock(return_value=gappy_snapshot())),
        patch.object(main, "gate", main.RateGate()),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app), base_url="http://test"
        ) as client:
            dashboard = (await client.post("/api/air", json=LOCATION.model_dump())).json()
            plan = (await client.post("/api/plan", json=body)).json()
    assert [h["time"] for h in dashboard["outlook"]] == [h["time"] for h in plan["snapshot"]["outlook"]]
    assert len(dashboard["outlook"]) == 23
    assert dashboard["outlook_lowest"] == plan["policy"]["best_window"]
    assert dashboard["outlook_lowest"]["us_aqi"] == 80


async def test_city_names_with_apostrophes_reach_the_geocoder(monkeypatch):
    searched = AsyncMock(return_value=[])
    monkeypatch.setattr(main, "search_locations", searched)
    monkeypatch.setattr(main, "gate", main.RateGate())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app), base_url="http://test"
    ) as client:
        response = await client.get("/api/geo?q=St.+John%27s")
    assert response.status_code == 200
    searched.assert_awaited_once_with("St. John's")
