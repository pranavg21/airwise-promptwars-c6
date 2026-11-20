"""Automated accessibility check: axe-core scans plus a keyboard walkthrough.

Run from the project root: python -m scripts.a11y_check
Requires Playwright and axe-playwright-python. Air data, city search and Gemini
are all replaced in-process, so no external service is called.
"""

import asyncio
import os
import socket
import sys
from collections import Counter
from unittest.mock import AsyncMock, patch

import uvicorn
from axe_playwright_python.async_playwright import Axe
from playwright.async_api import Page, async_playwright, expect

from airwise import main
from airwise.models import AiResponse, Location
from scripts.browser_check import synthetic_air

CITIES = [
    Location(name="Pune", country="India", region="Maharashtra", latitude=18.5204, longitude=73.8567),
    Location(name="Pune Cantonment", country="India", region="Maharashtra", latitude=18.5, longitude=73.88),
]
BRIEF = AiResponse(
    summary="Keep the morning outing gentle and move strenuous play to a cleaner hour.",
    steps=["Switch off the engine while waiting at the school gate.", "Avoid incense and candles indoors."],
    rationale="These steps reduce exposure and remove avoidable smoke without new purchases.",
)


async def scan(page: Page, label: str, results: dict[str, Counter]) -> None:
    report = await Axe().run(page)
    counts: Counter = Counter()
    for violation in report.response["violations"]:
        counts[violation["id"]] += len(violation["nodes"])
    results[label] = counts


async def built_plan(page: Page) -> None:
    await page.locator('[data-city="pune"]').click()
    await expect(page.locator("#aqiValue")).to_have_text("180")
    await page.locator("#emptyGenerate").click()
    await expect(page.locator("#recommendations .advice-card").first).to_be_visible()


async def ai_rendered(page: Page) -> None:
    await page.locator('[data-city="pune"]').click()
    await expect(page.locator("#aqiValue")).to_have_text("180")
    await page.locator("#aiConsent").check()
    await page.locator("#generateBtn").click()
    await expect(page.locator("#aiStatus")).to_contain_text("GEMINI GENERATED")
    await page.locator("#question").fill("How can we reduce idling at school pickup?")
    await page.locator("#askBtn").click()
    await expect(page.locator("#askAnswer .ask-answer")).to_be_visible()


async def tab_until(page: Page, selector: str, limit: int = 40) -> int:
    for presses in range(1, limit + 1):
        await page.keyboard.press("Tab")
        if await page.evaluate("(s) => document.activeElement?.matches(s) ?? false", selector):
            return presses
    raise AssertionError(f"{selector} not reached within {limit} Tab presses")


async def keyboard_walkthrough(page: Page, problems: list[str]) -> None:
    """Find Pune with the keyboard, dismiss the suggestions, select, continue through the form."""

    def check(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    focused = "() => document.activeElement?.id || document.activeElement?.textContent?.trim() || ''"
    await tab_until(page, "#citySearch")
    outline = await page.evaluate(
        "() => getComputedStyle(document.querySelector('.search-wrap')).outlineStyle !== 'none'"
        " || getComputedStyle(document.activeElement).outlineStyle !== 'none'"
    )
    check(outline, "City search has no visible focus indicator")

    await page.keyboard.type("Pune")
    await page.keyboard.press("Enter")
    options = page.locator("#cityResults button")
    await expect(options.first).to_be_visible()
    check(await page.locator("[aria-controls='cityResults'][aria-expanded='true']").count() == 1,
          "Open suggestions are not exposed with aria-expanded=true")

    await page.keyboard.press("ArrowDown")
    check("Pune" in await page.evaluate(focused), "ArrowDown does not move focus to the first suggestion")
    await page.keyboard.press("Escape")
    await expect(page.locator("#cityResults")).to_be_hidden()
    check(await page.evaluate(focused) == "citySearch", "Escape does not return focus to the search field")
    check(await page.locator("[aria-controls='cityResults'][aria-expanded='true']").count() == 0,
          "Dismissed suggestions still report aria-expanded=true")

    await page.keyboard.press("Enter")
    await expect(options.first).to_be_visible()
    await page.keyboard.press("ArrowDown")
    await page.keyboard.press("ArrowDown")
    await page.keyboard.press("ArrowUp")
    await page.keyboard.press("Enter")
    await expect(page.locator("#chosenCity")).to_have_text("Pune, Maharashtra, India")
    await expect(page.locator("#aqiValue")).to_have_text("180")
    check(await page.evaluate("() => document.activeElement !== document.body"),
          "Focus is lost to the page body after selecting a suggestion")

    await tab_until(page, "#persona")
    await tab_until(page, "#generateBtn")
    await page.keyboard.press("Enter")
    await expect(page.locator("#recommendations .advice-card").first).to_be_visible()


async def stale_search_dismissal(page: Page, dismiss: str, problems: list[str]) -> None:
    """Dismiss suggestions before the city search responds; the late response must stay silent."""
    started, release, delivered = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def hold(route) -> None:  # noqa: ANN001
        response = await route.fetch()
        started.set()
        await release.wait()
        await route.fulfill(response=response)
        delivered.set()

    await page.route("**/api/geo*", hold)
    await page.locator("#citySearch").focus()
    await page.keyboard.type("Pune")
    await page.keyboard.press("Enter")
    await asyncio.wait_for(started.wait(), 5)
    if dismiss == "Escape":
        await page.keyboard.press("Escape")
    else:
        await page.locator("#heroTitle").click()
    release.set()
    await asyncio.wait_for(delivered.wait(), 5)
    await page.wait_for_timeout(300)
    label = f"dismissed by {dismiss} before results arrived"
    if await page.locator("#cityResults").is_visible():
        problems.append(f"Suggestions reopen after being {label}")
    if dismiss == "Escape" and await page.evaluate("() => document.activeElement?.id") != "citySearch":
        problems.append(f"Focus leaves the search field after being {label}")
    if await page.locator("#citySearchBtn").get_attribute("aria-expanded") != "false":
        problems.append(f"aria-expanded=true after suggestions were {label}")
    status = await page.locator("#cityStatus").text_content() or ""
    if "matching" in status or "Down Arrow" in status:
        problems.append(f"Results still announced after being {label}: {status!r}")
    await page.unroute("**/api/geo*")


async def run() -> int:
    results: dict[str, Counter] = {}
    problems: list[str] = []
    gemini = AsyncMock(return_value=BRIEF)
    with (
        socket.socket() as sock,
        patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-key"}),
        patch.object(main, "fetch_air", synthetic_air),
        patch.object(main, "search_locations", AsyncMock(return_value=CITIES)),
        patch.object(main, "personalize", gemini),
    ):
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(main.app, log_level="error"))
        task = asyncio.create_task(server.serve(sockets=[sock]))
        base = f"http://127.0.0.1:{sock.getsockname()[1]}"
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
                for width in (1366, 390):
                    page = await browser.new_page(viewport={"width": width, "height": 860}, reduced_motion="reduce")
                    await page.goto(base)
                    await built_plan(page)
                    await scan(page, f"{width}px built plan", results)
                    await page.evaluate("() => document.querySelectorAll('details').forEach(d => { d.open = true; })")
                    await scan(page, f"{width}px built plan, all disclosures open", results)

                    await page.locator("#citySearch").fill("Pune")
                    await page.locator("#citySearch").press("Enter")
                    await expect(page.locator("#cityResults button").first).to_be_visible()
                    await scan(page, f"{width}px city suggestions open", results)

                    await page.goto(base)
                    await ai_rendered(page)
                    await scan(page, f"{width}px AI briefing and answer (mocked)", results)

                    await page.goto(base)
                    before = len(problems)
                    await keyboard_walkthrough(page, problems)
                    for dismiss in ("Escape", "a click outside"):
                        await page.goto(base)
                        await stale_search_dismissal(page, dismiss, problems)
                    problems[before:] = [f"{width}px: {p}" for p in problems[before:]]
                    await page.close()
                await browser.close()
        finally:
            server.should_exit = True
            await task

    failed = bool(problems)
    for label, counts in results.items():
        total = sum(counts.values())
        failed |= total > 0
        detail = ", ".join(f"{rule}={n}" for rule, n in sorted(counts.items())) or "none"
        print(f"{'PASS' if total == 0 else 'FAIL'} axe {label}: {total} violating nodes ({detail})")
    for problem in problems:
        print(f"FAIL keyboard {problem}")
    if not problems:
        print("PASS keyboard: search, suggestion navigation, Escape, selection, form continuation"
              " and dismissal of a pending search")
    print(f"Gemini mock calls: {gemini.await_count} (no live provider calls)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
