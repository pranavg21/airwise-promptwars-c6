"""The forecast outlook, defined once for the planner and the dashboard.

"The next 24 hours" means forecast hours whose local time falls within 24 elapsed hours of the
model time. Counting rows instead would stretch the window past 24 hours whenever an hour is
missing upstream, so the dashboard could show a lower AQI than the planner considers.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Protocol

from . import config


class TimedReading(Protocol):
    time: str
    us_aqi: float | None


def upcoming_hours[R: TimedReading](
    model_time: str, hours: Sequence[R], span_hours: int = config.OUTLOOK_HOURS
) -> list[R]:
    """Hours from the model time up to, but not including, `span_hours` later, in time order."""
    try:
        start = datetime.fromisoformat(model_time)
        end = start + timedelta(hours=span_hours)
        return sorted(
            (hour for hour in hours if start <= datetime.fromisoformat(hour.time) < end),
            key=lambda hour: hour.time,
        )
    except (ValueError, TypeError):
        return []


def lowest_aqi_hour[R: TimedReading](hours: Sequence[R]) -> R | None:
    """The earliest hour with the lowest modeled US AQI; hours without AQI are ignored."""
    rated = [(hour.us_aqi, index, hour) for index, hour in enumerate(hours) if hour.us_aqi is not None]
    return min(rated)[2] if rated else None
