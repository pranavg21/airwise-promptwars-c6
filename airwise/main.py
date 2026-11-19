"""Hardened HTTP boundary and static delivery."""
from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
import time

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .ai import AiUnavailable, configured, personalize
from .data import ProviderError, fetch_air, search_locations
from .models import AskRequest, Location, PlanRequest
from .policy import generate_policy

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
app = FastAPI(title="AirWise API", version="1.0.0", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


class RateGate:
    """Bounded abuse mitigation, per-process only (use edge/WAF quotas at scale)."""
    def __init__(self) -> None:
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, max_requests: int, window_sec: float) -> bool:
        now = time.monotonic()
        bucket = self.requests[key]
        while bucket and bucket[0] <= now - window_sec:
            bucket.popleft()
        if len(bucket) >= max_requests:
            return False
        bucket.append(now)
        if len(self.requests) > 5000:
            self.requests = defaultdict(deque, {k: v for k, v in self.requests.items() if v and v[-1] > now - 3600})
        return True


gate = RateGate()


@app.middleware("http")
async def add_headers(request: Request, call_next):  # noqa: ANN001, ANN201
    if request.method in ("POST", "PUT", "PATCH"):
        if request.headers.get("content-length"):
            try:
                if int(request.headers["content-length"]) > 12_000:
                    response = JSONResponse({"error": "Request too large"}, status_code=413)
                    return apply_headers(response, request)
            except ValueError:
                response = JSONResponse({"error": "Invalid content length"}, status_code=400)
                return apply_headers(response, request)
        if request.url.path.startswith("/api/") and request.headers.get("content-type", "").split(";")[0] != "application/json":
            response = JSONResponse({"error": "JSON required"}, status_code=415)
            return apply_headers(response, request)
    response = await call_next(request)
    return apply_headers(response, request)


def apply_headers(response, request):  # noqa: ANN001, ANN201
    """Consistent security headers, including short-circuited error responses."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; "
        "frame-ancestors 'none'; object-src 'none'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, _exc: RequestValidationError):
    return JSONResponse({"error": "Invalid request. Check input fields and limits."}, status_code=422)


def limit(request: Request, scope: str, max_requests: int, window: int = 600) -> None:
    client = request.client.host if request.client else "unknown"
    if not gate.check(f"{scope}:{client}", max_requests, window):
        raise HTTPException(status_code=429, detail="Too many requests. Try later.")


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "ai_configured": configured(), "source": "Open-Meteo/CAMS modeled air quality"}


@app.get("/api/geo")
async def geocode(request: Request, q: str = Query(min_length=3, max_length=90, pattern=r"^[^<>\x00-\x1f]+$")):
    limit(request, "geo", 80)
    try:
        return {"results": [loc.model_dump() for loc in await search_locations(q)]}
    except ProviderError:
        raise HTTPException(status_code=503, detail="City search unavailable; try a city shortcut.")


@app.post("/api/air")
async def air(request: Request, location: Location):
    limit(request, "air", 80)
    try:
        return (await fetch_air(location)).model_dump()
    except ProviderError:
        raise HTTPException(status_code=503, detail="Live forecast unavailable; no readings were estimated.")


@app.post("/api/plan")
async def plan(request: Request, body: PlanRequest):
    limit(request, "plan", 45)
    try:
        snapshot = await fetch_air(body.location)
    except ProviderError:
        raise HTTPException(status_code=503, detail="Forecast unavailable. Cannot generate a data-grounded plan.")
    policy = generate_policy(snapshot, body.profile)
    ai = None
    ai_status = "not_requested"
    if body.ai_consent:
        try:
            limit(request, "ai", 12)
            ai = (await personalize(snapshot, body.profile, policy)).model_dump()
            ai_status = "generated"
        except (AiUnavailable, HTTPException):
            ai_status = "unavailable"
    return {"snapshot": snapshot.model_dump(), "policy": policy.model_dump(), "ai": ai,
            "ai_status": ai_status, "ai_configured": configured()}


@app.post("/api/ask")
async def ask(request: Request, body: AskRequest):
    limit(request, "ai", 12)
    if not body.ai_consent:
        raise HTTPException(status_code=400, detail="Explicit AI consent is required.")
    if not configured():
        raise HTTPException(status_code=503, detail="GenAI is not configured on this deployment.")
    try:
        snapshot = await fetch_air(body.location)
        policy = generate_policy(snapshot, body.profile)
        ai = await personalize(snapshot, body.profile, policy, question=body.question)
        return {"ai": ai.model_dump(), "ai_status": "generated", "as_of": snapshot.model_time,
                "source": snapshot.source, "scale": snapshot.scale}
    except ProviderError:
        raise HTTPException(status_code=503, detail="Cannot answer without a valid air-quality forecast.")
    except AiUnavailable:
        raise HTTPException(status_code=503, detail="GenAI is temporarily unavailable. Use the rule-based action cards.")
