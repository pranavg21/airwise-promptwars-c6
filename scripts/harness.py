"""Shared fixtures for the browser walkthroughs: synthetic data, mocks, a local server and helpers.

Nothing here contacts Open-Meteo or Gemini: the forecast, city search and Gemini are replaced in-process.
"""

from __future__ import annotations

import asyncio
import os
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, patch

import uvicorn
from playwright.async_api import Browser, Page, Response, Route, async_playwright

from airwise import main
from airwise.data import ProviderError, parse_air
from airwise.models import AiResponse, Location, Snapshot

WAIT_S = 5
CITIES = [
    Location(name="Pune", country="India", region="Maharashtra", latitude=18.5204, longitude=73.8567),
    Location(name="Pune Cantonment", country="India", region="Maharashtra", latitude=18.5, longitude=73.88),
]
ST_JOHNS = Location(
    name="St. John's", country="Canada", region="Newfoundland and Labrador", latitude=47.56, longitude=-52.71
)
BRIEF = AiResponse(
    summary="Keep the morning outing gentle and move strenuous play to a cleaner hour.",
    steps=["Switch off the engine while waiting at the school gate.", "Avoid incense and candles indoors."],
    rationale="These steps reduce exposure and remove avoidable smoke without new purchases.",
)


def incomplete_forecast() -> tuple[list[str], list[int]]:
    """One hour missing, and a much lower reading exactly 24 hours after the model time."""
    times, values = [], []
    for offset in range(25):
        if offset == 4:
            continue
        day, hour = divmod(6 + offset, 24)
        times.append(f"2026-11-{19 + day}T{hour:02}:00")
        values.append(20 if offset == 24 else 80)
    return times, values


async def synthetic_air(location: Location) -> Snapshot:
    """Mumbai is an outage, Bengaluru an incomplete forecast, Pune 180 and anything else 84."""
    if location.name == "Mumbai":
        raise ProviderError("Simulated provider outage")
    if location.name == "Bengaluru":
        times, values = incomplete_forecast()
        current = {"time": times[0], "us_aqi": 80}
        hourly = {"time": times, "us_aqi": values, "pm2_5": [30] * len(times)}
    else:
        value = 180 if location.name == "Pune" else 84
        times = [f"2026-11-19T{hour:02}:00" for hour in range(24)]
        current = {"time": times[6], "us_aqi": value}
        hourly = {"time": times, "us_aqi": [value] * 24, "pm2_5": list(range(24, 0, -1))}
    return parse_air({"timezone": "Asia/Kolkata", "current": current, "hourly": hourly}, location)


@dataclass
class Mocks:
    search: AsyncMock
    gemini: AsyncMock


@asynccontextmanager
async def served_app(cities: list[Location], reply: AiResponse = BRIEF) -> AsyncIterator[tuple[str, Mocks]]:
    """Run the real app on a free local port with synthetic data; yields its URL and the mocks."""
    mocks = Mocks(search=AsyncMock(return_value=cities), gemini=AsyncMock(return_value=reply))
    with (
        socket.socket() as sock,
        patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-key"}),
        patch.object(main, "fetch_air", synthetic_air),
        patch.object(main, "search_locations", mocks.search),
        patch.object(main, "personalize", mocks.gemini),
    ):
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(main.app, log_level="error"))
        task = asyncio.create_task(server.serve(sockets=[sock]))
        try:
            yield f"http://127.0.0.1:{sock.getsockname()[1]}", mocks
        finally:
            server.should_exit = True
            await task


@asynccontextmanager
async def chromium() -> AsyncIterator[Browser]:
    """Chromium from Playwright, or the binary named by CHROMIUM_PATH."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
        try:
            yield browser
        finally:
            await browser.close()


def watch_for_errors(page: Page) -> list[str]:
    """Collect script errors and failed page assets (API errors are expected in outage scenarios)."""
    problems: list[str] = []

    def on_response(response: Response) -> None:
        if response.status >= 400 and "/api/" not in response.url:
            problems.append(f"HTTP {response.status} for {response.url}")

    page.on("pageerror", lambda error: problems.append(f"Script error: {error}"))
    page.on("response", on_response)
    return problems


@dataclass
class HeldResponse:
    """Holds one matching response until `deliver`, so a test can change the page in between."""

    started: asyncio.Event = field(default_factory=asyncio.Event)
    released: asyncio.Event = field(default_factory=asyncio.Event)
    delivered: asyncio.Event = field(default_factory=asyncio.Event)

    async def handle(self, route: Route) -> None:
        response = await route.fetch()
        self.started.set()
        await self.released.wait()
        await route.fulfill(response=response)
        self.delivered.set()

    async def wait_until_requested(self) -> None:
        await asyncio.wait_for(self.started.wait(), WAIT_S)

    async def deliver(self) -> None:
        self.released.set()
        await asyncio.wait_for(self.delivered.wait(), WAIT_S)


async def hold_responses(page: Page, pattern: str) -> HeldResponse:
    held = HeldResponse()
    await page.route(pattern, held.handle)
    return held
