"""Local Chromium walkthrough with synthetic upstream air and no Gemini calls.

Run from the project root: python -m scripts.browser_check
Requires Playwright and Chromium. Set CHROMIUM_PATH to use a system browser.
"""
import asyncio
import os
import socket
from unittest.mock import patch

import uvicorn
from playwright.async_api import async_playwright, expect

from airwise import main
from airwise.data import ProviderError, parse_air


async def synthetic_air(location):
    if location.name == "Mumbai":
        raise ProviderError("Simulated provider outage")
    value = 180 if location.name == "Pune" else 84
    hours = [f"2026-11-19T{hour:02}:00" for hour in range(24)]
    raw = {"timezone": "Asia/Kolkata", "current": {"time": hours[6], "us_aqi": value},
           "hourly": {"time": hours, "us_aqi": [value]*24, "pm2_5": list(range(24, 0, -1))}}
    return parse_air(raw, location)


async def walkthrough(browser, base, width):
    page = await browser.new_page(viewport={"width": width, "height": 860}, reduced_motion="reduce")
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    await page.goto(base)
    await expect(page.locator("#aqiValue")).to_have_text("84")
    await page.locator('[data-city="pune"]').click()
    await expect(page.locator("#aqiValue")).to_have_text("180")
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
    with socket.socket() as sock, patch.object(main, "fetch_air", synthetic_air):
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(main.app, log_level="error"))
        task = asyncio.create_task(server.serve(sockets=[sock]))
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
                for width in [1366, 390]:
                    await walkthrough(browser, f"http://127.0.0.1:{sock.getsockname()[1]}", width)
                await browser.close()
        finally:
            server.should_exit = True
            await task


if __name__ == "__main__":
    asyncio.run(run())
