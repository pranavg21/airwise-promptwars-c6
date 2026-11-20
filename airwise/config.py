"""Runtime configuration and operating limits, defined in one place.

Environment variables are read at call time so a deployment (or a test) can change them
without reloading modules. Every other value here is a named limit with its unit.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

# Gemini
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.5-flash"
MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,70}$")
GEMINI_TEMPERATURE = 0.25
GEMINI_MAX_OUTPUT_TOKENS = 2500

# Time budgets in seconds. The browser abandons any request after 45 s (static/js/transport.js),
# so each AI-backed request must finish, or give up on AI, before then.
# A live Gemini 2.5 Flash briefing took 21.7 s on 20 Nov 2026, too close to the earlier 22 s budget.
REQUEST_BUDGET_S = 40.0
MIN_AI_BUDGET_S = 3.0
GEMINI_CONNECT_TIMEOUT_S = 5.0
FORECAST_CONNECT_TIMEOUT_S = 3.0
FORECAST_READ_TIMEOUT_S = 8.0

# Size limits in bytes.
MAX_REQUEST_BYTES = 12_000
MAX_FORECAST_BYTES = 500_000
MAX_GEMINI_BYTES = 120_000

# Cache lifetimes in seconds, and entries kept per cache.
GEO_CACHE_TTL_S = 24 * 60 * 60
AIR_CACHE_TTL_S = 8 * 60
AI_CACHE_TTL_S = 15 * 60
CACHE_MAX_ENTRIES = 128

# Requests allowed per client address and process within one window.
RATE_WINDOW_S = 600
RATE_LIMITS = {"geo": 80, "air": 80, "plan": 45, "ai": 12}
RATE_GATE_MAX_KEYS = 5000

# Forecast handling.
FORECAST_DAYS = 3
MAX_FORECAST_HOURS = 72
OUTLOOK_HOURS = 24
GEOCODING_RESULTS = 6
LOCATION_CACHE_DECIMALS = 3
UPSTREAM_COORDINATE_DECIMALS = 5


class ConfigurationError(ValueError):
    """The deployment's AI settings are missing or malformed."""


@dataclass(frozen=True)
class GeminiSettings:
    api_key: str
    models: tuple[str, ...]  # Primary model first, then the optional fallback.


def gemini_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def gemini_settings() -> GeminiSettings:
    """Validated Gemini settings; raises ConfigurationError rather than guessing."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError("GEMINI_API_KEY is not set")
    primary = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip()
    fallback = os.environ.get("GEMINI_FALLBACK_MODEL", "").strip()
    models = (primary, fallback) if fallback and fallback != primary else (primary,)
    if not all(MODEL_ID_PATTERN.fullmatch(model) for model in models):
        raise ConfigurationError("Gemini model identifier is invalid")
    return GeminiSettings(api_key=api_key, models=models)
