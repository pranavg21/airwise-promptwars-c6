"""User journeys in Chromium with synthetic air data, mocked city search and mocked Gemini.

Run from the project root: python -m scripts.browser_check
Requires Playwright and Chromium. Set CHROMIUM_PATH to use a system browser.
"""

import asyncio
from unittest.mock import AsyncMock

from playwright.async_api import Browser, Page, expect

from airwise.ai import AiUnavailableError
from airwise.models import AiResponse
from scripts.harness import ST_JOHNS, chromium, hold_responses, served_app, watch_for_errors

LATE_ANSWER = AiResponse(
    summary="This answer belongs to the earlier settings.",
    steps=["Switch off the engine while waiting.", "Avoid incense indoors."],
    rationale="It must not appear after the settings change.",
)


async def plan_and_persona(page: Page) -> None:
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


async def late_plan_after_outage(page: Page) -> None:
    """A plan for the previous city must not appear after switching to a city whose data is down."""
    held = await hold_responses(page, "**/api/plan")
    await page.locator("#generateBtn").click()
    await held.wait_until_requested()
    await page.locator('[data-city="mumbai"]').click()
    await expect(page.locator("#feedStatus")).to_have_text("DATA UNAVAILABLE")
    await held.deliver()
    await expect(page.locator("#generateBtn")).to_be_enabled()
    await expect(page.locator("#aqiValue")).to_have_text("—")
    await expect(page.locator("#emptyGenerate")).to_be_visible()
    await expect(page.locator("#printBtn")).to_be_disabled()
    await expect(page.locator("#hourlyTable tr")).to_have_count(0)
    await page.unroute("**/api/plan")


async def outlook_stays_within_24_hours(page: Page, base: str) -> None:
    """The dashboard must not offer a lower AQI from outside the window the planner uses."""
    await page.goto(base)
    await page.locator('[data-city="bengaluru"]').click()
    await expect(page.locator("#aqiValue")).to_have_text("80")
    await expect(page.locator("#bestAQI")).to_have_text("80")
    await expect(page.locator("#hourlyTable tr")).to_have_count(23)


async def apostrophe_city_search(page: Page, base: str, searched: AsyncMock) -> None:
    await page.goto(base)
    await page.locator("#citySearch").fill("St. John's")
    await page.locator("#citySearch").press("Enter")
    await expect(page.locator("#cityResults button").first).to_contain_text("St. John's")
    assert searched.await_args.args[0] == "St. John's", searched.await_args


async def late_answer_is_discarded(page: Page, base: str) -> None:
    """A Gemini answer for earlier settings must not appear after the settings change."""
    await page.goto(base)
    await page.locator('[data-city="pune"]').click()
    await expect(page.locator("#aqiValue")).to_have_text("180")
    await page.locator("#aiConsent").check()
    await page.locator("#question").fill("How can we reduce idling at school pickup?")
    held = await hold_responses(page, "**/api/ask")
    await page.locator("#askBtn").click()
    await held.wait_until_requested()
    await page.locator("#persona").select_option("commuter")
    await held.deliver()
    await expect(page.locator("#askBtn")).to_be_enabled()
    await expect(page.locator("#askAnswer")).not_to_contain_text(LATE_ANSWER.summary)
    await page.unroute("**/api/ask")


async def failed_answer_points_to_rule_based_plan(page: Page, base: str, gemini: AsyncMock) -> None:
    """When Gemini cannot answer (for example, out of quota), offer guidance that does not use it."""
    gemini.side_effect = AiUnavailableError("quota exhausted")
    calls = gemini.await_count
    try:
        await page.goto(base)
        await page.locator('[data-city="pune"]').click()
        await expect(page.locator("#aqiValue")).to_have_text("180")
        await page.locator("#aiConsent").check()
        await page.locator("#question").fill("Should my child play outside today?")
        fallback = page.locator("#askAnswer button")
        await page.locator("#askBtn").click()
        await expect(fallback).to_have_text("Build plan without Gemini")
        await fallback.click()
        await expect(page.locator("#recommendations")).to_contain_text("Build a cleaner-air room")
        await page.locator("#askBtn").click()
        await expect(fallback).to_have_text("Go to my rule-based plan")
        await fallback.click()
        await expect(page.locator("#recommendations")).to_be_focused()
        # Two questions reached Gemini; the fallback plan did not, although consent was still on.
        assert gemini.await_count == calls + 2, gemini.await_count
    finally:
        gemini.side_effect = None


async def walkthrough(browser: Browser, base: str, width: int) -> None:
    page = await browser.new_page(viewport={"width": width, "height": 860}, reduced_motion="reduce")
    problems = watch_for_errors(page)
    await page.goto(base)
    await plan_and_persona(page)
    await late_plan_after_outage(page)
    assert not problems, problems
    await page.close()
    print(f"PASS {width}px: city selection, profile change, outage, delayed plan, no page or asset errors")


async def run() -> None:
    async with served_app([ST_JOHNS], reply=LATE_ANSWER) as (base, mocks), chromium() as browser:
        for width in (1366, 390):
            await walkthrough(browser, base, width)
        page = await browser.new_page()
        problems = watch_for_errors(page)
        await outlook_stays_within_24_hours(page, base)
        await apostrophe_city_search(page, base, mocks.search)
        await late_answer_is_discarded(page, base)
        await failed_answer_points_to_rule_based_plan(page, base, mocks.gemini)
        assert not problems, problems
        await page.close()
        print(
            "PASS outlook within 24 hours, apostrophe city search, late Gemini answer discarded,"
            " failed answer offers the rule-based plan"
        )


if __name__ == "__main__":
    asyncio.run(run())
