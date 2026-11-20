"""HTTP routes and static delivery. Guards and headers live in security.py."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .ai import AiUnavailableError, configured, personalize
from .data import ProviderError, fetch_air, search_locations
from .models import AskRequest, Location, PlanRequest, Snapshot
from .policy import generate_policy
from .security import RateGate, apply_headers, reject_unsafe_request

__all__ = ["RateGate", "app", "gate"]

STATIC = Path(__file__).resolve().parent.parent / "static"
CITY_QUERY = Query(min_length=3, max_length=90, pattern=r"^[^<>\x00-\x1f]+$")

app = FastAPI(title="AirWise API", version="1.0.0", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
gate = RateGate()


@app.middleware("http")
async def guard(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    response = reject_unsafe_request(request) or await call_next(request)
    return apply_headers(response, request.url.path)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse({"error": "Invalid request. Check input fields and limits."}, status_code=422)


def limit(request: Request, scope: str) -> None:
    client = request.client.host if request.client else "unknown"
    if not gate.check(f"{scope}:{client}", config.RATE_LIMITS[scope], config.RATE_WINDOW_S):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try later.",
            headers={"Retry-After": str(config.RATE_WINDOW_S)},
        )


def ai_budget(started: float) -> float:
    """Seconds left for Gemini so the whole request ends before the browser gives up."""
    return config.REQUEST_BUDGET_S - (time.monotonic() - started)


async def snapshot_or_503(location: Location, detail: str) -> Snapshot:
    try:
        return await fetch_air(location)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=detail) from exc


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "ai_configured": configured(), "source": "Open-Meteo/CAMS modeled air quality"}


@app.get("/api/geo")
async def geocode(request: Request, q: str = CITY_QUERY) -> dict[str, Any]:
    limit(request, "geo")
    try:
        return {"results": [loc.model_dump() for loc in await search_locations(q)]}
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail="City search unavailable; try a city shortcut.") from exc


@app.post("/api/air")
async def air(request: Request, location: Location) -> dict[str, Any]:
    limit(request, "air")
    snapshot = await snapshot_or_503(location, "Live forecast unavailable; no readings were estimated.")
    return snapshot.model_dump()


@app.post("/api/plan")
async def plan(request: Request, body: PlanRequest) -> dict[str, Any]:
    started = time.monotonic()
    limit(request, "plan")
    snapshot = await snapshot_or_503(
        body.location, "Forecast unavailable. Cannot generate a data-grounded plan."
    )
    policy = generate_policy(snapshot, body.profile)
    ai, ai_status = None, "not_requested"
    if body.ai_consent:
        ai_status = "unavailable"
        try:
            limit(request, "ai")
            if ai_budget(started) >= config.MIN_AI_BUDGET_S:
                reply = await personalize(snapshot, body.profile, policy, budget_s=ai_budget(started))
                ai, ai_status = reply.model_dump(), "generated"
        except (AiUnavailableError, HTTPException):
            pass
    return {
        "snapshot": snapshot.model_dump(),
        "policy": policy.model_dump(),
        "ai": ai,
        "ai_status": ai_status,
        "ai_configured": configured(),
    }


@app.post("/api/ask")
async def ask(request: Request, body: AskRequest) -> dict[str, Any]:
    started = time.monotonic()
    limit(request, "ai")
    if not body.ai_consent:
        raise HTTPException(status_code=400, detail="Explicit AI consent is required.")
    if not configured():
        raise HTTPException(status_code=503, detail="GenAI is not configured on this deployment.")
    snapshot = await snapshot_or_503(body.location, "Cannot answer without a valid air-quality forecast.")
    policy = generate_policy(snapshot, body.profile)
    unavailable = HTTPException(
        status_code=503, detail="GenAI is temporarily unavailable. Use the rule-based action cards."
    )
    if ai_budget(started) < config.MIN_AI_BUDGET_S:
        raise unavailable
    try:
        reply = await personalize(
            snapshot, body.profile, policy, question=body.question, budget_s=ai_budget(started)
        )
    except AiUnavailableError as exc:
        raise unavailable from exc
    return {
        "ai": reply.model_dump(),
        "ai_status": "generated",
        "as_of": snapshot.model_time,
        "source": snapshot.source,
        "scale": snapshot.scale,
    }
