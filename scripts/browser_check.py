"""Local Chromium walkthrough with synthetic air data, mocked city search and mocked Gemini.

Run from the project root: python -m scripts.browser_check
Requires Playwright and Chromium. Set CHROMIUM_PATH to use a system browser.
"""

import asyncio
import os
import socket
from unittest.mock import AsyncMock, patch

import uvicorn
from playwright.async_api import async_playwright, expect

from airwise import main
from airwise.data import ProviderError, parse_air
from airwise.models import AiResponse, Location

LATE_ANSWER = AiResponse(
    summary="This answer belongs to the earlier settings.",
    steps=["Switch off the engine while waiting.", "Avoid incense indoors."],
    rationale="It must not appear after the settings change.",
)
ST_JOHNS = Location(
    name="St. John's", country="Canada", region="Newfoundland and Labrador", latitude=47.56, longitude=-52.71
)


def incomplete_forecast():
    """One hour missing, and a much lower reading exactly 24 hours after the model time."""
    times, values = [], []
    for offset in range(25):
        if offset == 4:
            continue
        day, hour = divmod(6 + offset, 24)
        times.append(f"2026-11-{19 + day}T{hour:02}:00")
        values.append(20 if offset == 24 else 80)
    return times, values


async def synthetic_air(location):
    if location.name == "Mumbai":
        raise ProviderError("Simulated provider outage")
    if location.name == "Bengaluru":
        times, values = incomplete_forecast()
        raw = {
            "timezone": "Asia/Kolkata",
            "current": {"time": times[0], "us_aqi": 80},
            "hourly": {"time": times, "us_aqi": values, "pm2_5": [30] * len(times)},
        }
        return parse_air(raw, location)
    value = 180 if location.name == "Pune" else 84
    hours = [f"2026-11-19T{hour:02}:00" for hour in range(24)]
    raw = {
        "timezone": "Asia/Kolkata",
        "current": {"time": hours[6], "us_aqi": value},
        "hourly": {"time": hours, "us_aqi": [value] * 24, "pm2_5": list(range(24, 0, -1))},
    }
    return parse_air(raw, location)


async def outlook_stays_within_24_hours(page, base):
    """The dashboard must not offer a lower AQI from outside the window the planner uses."""
    await page.goto(base)
    await page.locator('[data-city="bengaluru"]').click()
    await expect(page.locator("#aqiValue")).to_have_text("80")
    await expect(page.locator("#bestAQI")).to_have_text("80")
    await expect(page.locator("#hourlyTable tr")).to_have_count(23)


async def apostrophe_city_search(page, base, searched):
    await page.goto(base)
    await page.locator("#citySearch").fill("St. John's")
    await page.locator("#citySearch").press("Enter")
    await expect(page.locator("#cityResults button").first).to_contain_text("St. John's")
    assert searched.await_args.args[0] == "St. John's", searched.await_args


async def late_answer_is_discarded(page, base):
    """A Gemini answer for earlier settings must not appear after the settings change."""
    started, release, delivered = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def hold(route):
        result = await route.fetch()
        started.set()
        await release.wait()
        await route.fulfill(response=result)
        delivered.set()

    await page.goto(base)
    await page.locator('[data-city="pune"]').click()
    await expect(page.locator("#aqiValue")).to_have_text("180")
    await page.locator("#aiConsent").check()
    await page.locator("#question").fill("How can we reduce idling at school pickup?")
    await page.route("**/api/ask", hold)
    await page.locator("#askBtn").click()
    await asyncio.wait_for(started.wait(), 5)
    await page.locator("#persona").select_option("commuter")
    release.set()
    await asyncio.wait_for(delivered.wait(), 5)
    await expect(page.locator("#askBtn")).to_be_enabled()
    await expect(page.locator("#askAnswer")).not_to_contain_text(LATE_ANSWER.summary)
    await page.unroute("**/api/ask")


async def walkthrough(browser, base, width):
    page = await browser.new_page(viewport={"width": width, "height": 860}, reduced_motion="reduce")
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    await page.goto(base)
    await expect(page.locator("#aqiValue")).to_have_text("84")
    await expect(page.locator("#aqiCategory")).to_have_text("Moderate")
    await expect(page.locator("#aqiCategory")).to_have_attribute("data-band", "moderate")
    await page.locator('[data-city="pune"]').click()
    await expect(page.locator("#aqiValue")).to_have_text("180")
    await expect(page.locator("#aqiCategory")).to_have_text("Unhealthy")
    await expect(page.locator("#aqiCategory")).to_have_attribute("data-band", "unhealthy")
    await page.locator("#emptyGenerate").click()
    await expect(page.locator("#recommendations")).to_contain_text("Build a cleaner-air room")
    await page.locator("#persona").select_option("outdoor")
    await expect(page.locator("#copyBtn")).to_be_disabled()
    await page.locator("#emptyGenerate").click()
    await expect(page.locator("#recommendations")).to_contain_text("Protect essential outdoor work")
    assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")

    # Hold a completed response while the user switches to a city with an outage.
    started, release, delivered = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def hold(route):
        result = await route.fetch()
        started.set()
        await release.wait()
        await route.fulfill(response=result)
        delivered.set()

    await page.route("**/api/plan", hold)
    await page.locator("#generateBtn").click()
    await asyncio.wait_for(started.wait(), 5)
    await page.locator('[data-city="mumbai"]').click()
    await expect(page.locator("#feedStatus")).to_have_text("DATA UNAVAILABLE")
    release.set()
    await asyncio.wait_for(delivered.wait(), 5)
    await expect(page.locator("#generateBtn")).to_be_enabled()
    await expect(page.locator("#aqiValue")).to_have_text("—")
    await expect(page.locator("#emptyGenerate")).to_be_visible()
    await expect(page.locator("#printBtn")).to_be_disabled()
    await expect(page.locator("#hourlyTable tr")).to_have_count(0)
    assert not errors, errors
    await page.close()
    print(f"PASS {width}px: city selection, profile change, outage, delayed plan, no page errors")


async def run():
    searched = AsyncMock(return_value=[ST_JOHNS])
    with (
        socket.socket() as sock,
        patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-key"}),
        patch.object(main, "fetch_air", synthetic_air),
        patch.object(main, "search_locations", searched),
        patch.object(main, "personalize", AsyncMock(return_value=LATE_ANSWER)),
    ):
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(main.app, log_level="error"))
        task = asyncio.create_task(server.serve(sockets=[sock]))
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
                base = f"http://127.0.0.1:{sock.getsockname()[1]}"
                for width in [1366, 390]:
                    await walkthrough(browser, base, width)
                page = await browser.new_page()
                await outlook_stays_within_24_hours(page, base)
                await apostrophe_city_search(page, base, searched)
                await late_answer_is_discarded(page, base)
                await page.close()
                print("PASS outlook within 24 hours, apostrophe city search, late Gemini answer discarded")
                await browser.close()
        finally:
            server.should_exit = True
            await task


if __name__ == "__main__":
    asyncio.run(run())
