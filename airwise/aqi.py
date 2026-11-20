"""US EPA AQI categories: the single definition used by the API, the policy engine and the browser.

These are US EPA categories, not India's CPCB categories.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

Concern = Literal["low", "moderate", "high", "very_high", "unknown"]


@dataclass(frozen=True)
class AqiBand:
    key: str  # Stable identifier the browser maps to a colour.
    label: str  # Category name shown to people.
    concern: Concern  # Level the policy engine uses to choose precautions.
    upper: float  # Inclusive upper bound of the band.


BANDS: tuple[AqiBand, ...] = (
    AqiBand("good", "Good", "low", 50),
    AqiBand("moderate", "Moderate", "moderate", 100),
    AqiBand("sensitive", "Unhealthy for sensitive groups", "high", 150),
    AqiBand("unhealthy", "Unhealthy", "high", 200),
    AqiBand("very-unhealthy", "Very unhealthy", "very_high", 300),
    AqiBand("hazardous", "Hazardous", "very_high", math.inf),
)
UNAVAILABLE = AqiBand("unavailable", "Unavailable", "unknown", math.nan)


def band(value: float | None) -> AqiBand:
    """Return the band containing a US AQI value, or UNAVAILABLE when there is no value."""
    if value is None:
        return UNAVAILABLE
    return next(b for b in BANDS if value <= b.upper)


def classify(value: float | None) -> tuple[str, Concern]:
    """Category label and concern level for a US AQI value."""
    found = band(value)
    return found.label, found.concern
