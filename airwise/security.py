"""Request guards, security headers and per-client rate limiting for the HTTP boundary."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from . import config

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; "
        "frame-ancestors 'none'; object-src 'none'"
    ),
}
BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


def _error(message: str, status: int) -> JSONResponse:
    """A JSON error body with the given status."""
    return JSONResponse({"error": message}, status_code=status)


def _size_error(request: Request) -> JSONResponse | None:
    """Reject a malformed or oversized Content-Length before the body is read."""
    length = request.headers.get("content-length")
    if length is None:
        return None
    if not length.isdigit():
        return _error("Invalid content length", 400)
    if int(length) > config.MAX_REQUEST_BYTES:
        return _error("Request too large", 413)
    return None


def _api_write_error(request: Request) -> JSONResponse | None:
    """Reject cross-site or non-JSON writes to the API."""
    if request.headers.get("sec-fetch-site") == "cross-site":
        return _error("Cross-site requests are not allowed", 403)
    if request.headers.get("content-type", "").split(";")[0] != "application/json":
        return _error("JSON required", 415)
    return None


def reject_unsafe_request(request: Request) -> JSONResponse | None:
    """An error response for oversized, non-JSON or cross-site API writes; None when acceptable."""
    if request.method not in BODY_METHODS:
        return None
    rejection = _size_error(request)
    if rejection is None and request.url.path.startswith("/api/"):
        rejection = _api_write_error(request)
    return rejection


def apply_headers(response: Response, path: str) -> Response:
    """Consistent security headers, including on short-circuited error responses."""
    response.headers.update(SECURITY_HEADERS)
    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


class RateGate:
    """Sliding-window limiter, per process only (use edge or WAF quotas at scale)."""

    def __init__(self) -> None:
        """Start with no recorded requests."""
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, max_requests: int, window_sec: float) -> bool:
        """Record a request for `key`; False when it exceeds `max_requests` within `window_sec`."""
        now = time.monotonic()
        bucket = self.requests[key]
        while bucket and bucket[0] <= now - window_sec:
            bucket.popleft()
        if len(bucket) >= max_requests:
            return False
        bucket.append(now)
        if len(self.requests) > config.RATE_GATE_MAX_KEYS:
            self._forget_idle(now)
        return True

    def _forget_idle(self, now: float) -> None:
        """Drop clients idle for a whole window so memory stays bounded."""
        recent = {k: v for k, v in self.requests.items() if v and v[-1] > now - config.RATE_WINDOW_S}
        self.requests = defaultdict(deque, recent)
