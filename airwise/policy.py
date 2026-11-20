"""Transparent, deterministic advice engine. GenAI cannot overwrite the facts.

Recommendation text lives in catalog.py; this module decides which entries apply.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from . import catalog, config
from .aqi import Concern, classify
from .models import Advice, Hour, PolicyResult, Profile, Shift, Snapshot

__all__ = ["classify", "find_lower_hour", "generate_policy", "upcoming_hours"]

MINUTES_PER_HOUR = 60
# Display rule, not a clinical threshold: smaller modeled differences are not worth a schedule change.
MIN_SHIFT_DIFFERENCE_PCT = 5.0


def upcoming_hours(snapshot: Snapshot, hours: int = config.OUTLOOK_HOURS) -> list[Hour]:
    """Compare matching local timestamps; never compare a past forecast to the present."""
    try:
        now = datetime.fromisoformat(snapshot.model_time)
        end = now + timedelta(hours=hours)
        return sorted(
            (h for h in snapshot.hourly if now <= datetime.fromisoformat(h.time) < end),
            key=lambda h: h.time,
        )
    except (ValueError, TypeError):
        return []


@dataclass(frozen=True)
class ActivityWindow:
    start: Hour
    mean_pm25: float
    peak_aqi: float


def activity_windows(hours: list[Hour], duration: int) -> list[ActivityWindow]:
    """Weight each forecast value by minutes spent in that hour; require complete data."""
    if duration <= 0:
        return []
    times = [datetime.fromisoformat(h.time) for h in hours]
    by_time = dict(zip(times, hours, strict=True))
    if len(by_time) != len(times):
        return []  # Repeated local hour (e.g. clock change) is ambiguous.
    windows = []
    for start in times:
        total = peak = 0.0
        for minute in range(0, duration, MINUTES_PER_HOUR):
            hour = by_time.get(start + timedelta(minutes=minute))
            if hour is None or hour.us_aqi is None or hour.pm2_5 is None:
                break
            total += hour.pm2_5 * min(MINUTES_PER_HOUR, duration - minute)
            peak = max(peak, hour.us_aqi)
        else:
            windows.append(ActivityWindow(by_time[start], total / duration, peak))
    return windows


def lowest_aqi_hour(hours: list[Hour]) -> Hour | None:
    """The earliest hour with the lowest modeled US AQI; hours without AQI are ignored."""
    rated = [(h.us_aqi, index, h) for index, h in enumerate(hours) if h.us_aqi is not None]
    return min(rated)[2] if rated else None


def find_lower_hour(snapshot: Snapshot, profile: Profile) -> tuple[Hour | None, Shift | None]:
    """Lowest-AQI hour, and a better start time for the whole activity when one clearly exists."""
    hours = upcoming_hours(snapshot)
    minimum = lowest_aqi_hour(hours)
    windows = activity_windows(hours, profile.outdoor_minutes)
    planned = next(
        (w for w in windows if datetime.fromisoformat(w.start.time).hour == profile.start_hour), None
    )
    if planned is None or planned.mean_pm25 == 0:
        return minimum, None
    alternate = min((w for w in windows if w.peak_aqi <= planned.peak_aqi), key=lambda w: w.mean_pm25)
    difference = (1 - alternate.mean_pm25 / planned.mean_pm25) * 100
    if difference < MIN_SHIFT_DIFFERENCE_PCT:
        return minimum, None
    return minimum, Shift(
        current_time=planned.start.time,
        recommended_time=alternate.start.time,
        original_pm25=round(planned.mean_pm25, 1),
        alternate_pm25=round(alternate.mean_pm25, 1),
        duration_min=profile.outdoor_minutes,
        relative_difference_pct=round(difference, 1),
        caution=catalog.SHIFT_CAUTION,
    )


@dataclass(frozen=True)
class Situation:
    """The facts a rule may depend on."""

    profile: Profile
    concern: Concern
    sensitive: bool

    def prioritises(self, priority: str) -> bool:
        return priority in self.profile.priorities

    def is_persona(self, persona: str) -> bool:
        return self.profile.persona == persona


@dataclass(frozen=True)
class Rule:
    """Adds `advice` when `applies` holds; `trace` explains the decision and may use {aqi}."""

    advice: Advice
    applies: Callable[[Situation], bool]
    trace: str | None = None


# Exactly one exposure rule applies: the first match, in this order.
EXPOSURE_RULES: tuple[Rule, ...] = (
    Rule(catalog.OUTDOOR_HIGH, lambda s: s.concern in {"high", "very_high"}, catalog.TRACE_HIGH_CONCERN),
    Rule(
        catalog.OUTDOOR_SENSITIVE,
        lambda s: s.concern == "moderate" and s.sensitive,
        catalog.TRACE_SENSITIVE_MODERATE,
    ),
    Rule(catalog.ACTIVITY_GOOD, lambda s: s.concern == "low"),
    Rule(catalog.ACTIVITY_DEFAULT, lambda s: True),
)

# Every matching rule adds its card, in this order, after the exposure card.
ACTION_RULES: tuple[Rule, ...] = (
    Rule(
        catalog.HOME,
        lambda s: s.prioritises("home") or s.is_persona("family") or s.sensitive,
        catalog.TRACE_HOME,
    ),
    Rule(catalog.SCHOOL, lambda s: s.profile.children or s.prioritises("school"), catalog.TRACE_SCHOOL),
    Rule(catalog.COMMUTE, lambda s: s.prioritises("commute") or s.is_persona("commuter")),
    Rule(catalog.EXERCISE, lambda s: s.prioritises("exercise")),
    Rule(catalog.WORKER, lambda s: s.is_persona("outdoor")),
    Rule(catalog.COMMUNITY, lambda s: s.is_persona("community") or s.prioritises("community")),
    Rule(catalog.BUDGET, lambda s: s.profile.budget == "none"),
    Rule(catalog.MEDICAL, lambda s: s.profile.respiratory_sensitivity),
)

# Every matching swap is offered; the universal swap applies only when none match.
SWAP_RULES: tuple[Rule, ...] = (
    Rule(catalog.TRIP_SWAP, lambda s: s.prioritises("commute") or s.is_persona("commuter")),
    Rule(catalog.COMBUSTION_SWAP, lambda s: s.prioritises("home") or s.is_persona("family")),
    Rule(catalog.PICKUP_SWAP, lambda s: s.prioritises("school") or s.profile.children),
    Rule(catalog.SHARED_SWAP, lambda s: s.is_persona("community") or s.prioritises("community")),
)


def headline(situation: Situation) -> str:
    if situation.concern in {"high", "very_high"}:
        return catalog.HEADLINE_HIGH
    if situation.sensitive and situation.concern == "moderate":
        return catalog.HEADLINE_SENSITIVE
    if situation.concern == "unknown":
        return catalog.HEADLINE_UNKNOWN
    return catalog.HEADLINE_DEFAULT


def decision_trace(
    snapshot: Snapshot, selected: list[Rule], minimum: Hour | None, shift: Shift | None
) -> list[str]:
    """Why each recommendation appeared, in the order the rules fired."""
    trace = [catalog.TRACE_SOURCE]
    trace += [rule.trace.format(aqi=snapshot.us_aqi) for rule in selected if rule.trace]
    if minimum and minimum.us_aqi is not None:
        trace.append(catalog.TRACE_LOWEST_HOUR.format(aqi=minimum.us_aqi, time=minimum.time))
    if shift:
        trace.append(catalog.TRACE_SHIFT)
    trace.append(catalog.TRACE_SWAPS)
    return trace


def generate_policy(snapshot: Snapshot, profile: Profile) -> PolicyResult:
    """Deterministic plan: exposure card, matching actions and swaps, with a decision trace."""
    category, concern = classify(snapshot.us_aqi)
    situation = Situation(
        profile=profile,
        concern=concern,
        sensitive=bool(profile.children or profile.older_adult or profile.respiratory_sensitivity),
    )
    exposure = next(rule for rule in EXPOSURE_RULES if rule.applies(situation))
    selected = [exposure, *(rule for rule in ACTION_RULES if rule.applies(situation))]
    swaps = [rule.advice for rule in SWAP_RULES if rule.applies(situation)] or [catalog.UNIVERSAL_SWAP]
    minimum, shift = find_lower_hour(snapshot, profile)
    return PolicyResult(
        category=category,
        concern=concern,
        headline=headline(situation),
        sensitive=situation.sensitive,
        cards=[rule.advice for rule in selected],
        swaps=swaps,
        best_window=minimum,
        lowest_aqi=minimum.us_aqi if minimum else None,
        shift=shift,
        trace=decision_trace(snapshot, selected, minimum, shift),
        disclaimer=catalog.DISCLAIMER,
    )
