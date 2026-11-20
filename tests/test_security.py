"""HTTP boundary: security headers, cross-site writes, request limits and rate limiting."""

import httpx
import pytest

from airwise import main
from airwise.security import SECURITY_HEADERS


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "gate", main.RateGate())
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test")


@pytest.mark.parametrize("path", ["/", "/api/health", "/static/js/app.js"])
async def test_every_response_carries_security_headers(client, path):
    async with client as c:
        response = await c.get(path)
    assert response.status_code == 200
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value
    assert "max-age=31536000" in response.headers["strict-transport-security"]


async def test_cross_site_api_write_is_rejected(client, location):
    async with client as c:
        response = await c.post(
            "/api/air", json=location.model_dump(), headers={"Sec-Fetch-Site": "cross-site"}
        )
    assert response.status_code == 403
    assert response.headers["x-frame-options"] == "DENY"


async def test_same_origin_write_passes_the_guard(client, location, monkeypatch, snapshot):
    async def fixed_air(_location):
        return snapshot

    monkeypatch.setattr(main, "fetch_air", fixed_air)
    async with client as c:
        response = await c.post(
            "/api/air", json=location.model_dump(), headers={"Sec-Fetch-Site": "same-origin"}
        )
    assert response.status_code == 200


async def test_malformed_content_length_is_rejected(client):
    async with client as c:
        response = await c.post(
            "/api/air", content=b"{}", headers={"Content-Type": "application/json", "Content-Length": "x"}
        )
    assert response.status_code == 400


async def test_rate_limit_says_when_to_retry(client, monkeypatch):
    monkeypatch.setitem(main.config.RATE_LIMITS, "geo", 1)

    async def no_results(_query):
        return []

    monkeypatch.setattr(main, "search_locations", no_results)
    async with client as c:
        first = await c.get("/api/geo", params={"q": "Pune"})
        second = await c.get("/api/geo", params={"q": "Pune"})
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["retry-after"] == str(main.config.RATE_WINDOW_S)


async def test_page_assets_all_load(client):
    """Every stylesheet, script and icon the page links must load, so no 404 reaches the console."""
    import re

    async with client as c:
        page = (await c.get("/")).text
        assets = re.findall(r'(?:href|src)="(/static/[^"]+)"', page)
        statuses = {path: (await c.get(path)).status_code for path in assets}
        favicon = await c.get("/favicon.ico")
    assert "/static/favicon.svg" in assets and "/static/js/app.js" in assets
    assert all(status == 200 for status in statuses.values()), statuses
    assert favicon.status_code == 200
    assert favicon.headers["content-type"].startswith("image/svg+xml")


@pytest.mark.parametrize("path", ["/", "/favicon.ico", "/api/health", "/static/css/base.css"])
async def test_head_requests_succeed_for_uptime_probes(client, path):
    async with client as c:
        response = await c.head(path)
    assert response.status_code == 200
    assert response.content == b""
    assert response.headers["x-content-type-options"] == "nosniff"
