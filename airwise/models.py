"""Validated boundaries for every externally supplied value."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from .aqi import Concern, band
from .forecast import lowest_aqi_hour, upcoming_hours

Priority = Literal["school", "commute", "exercise", "home", "community"]
STEP_MIN_CHARS = 4
STEP_MAX_CHARS = 300


def default_priorities() -> list[Priority]:
    """Priorities used when a request chooses none: commute and home."""
    return ["commute", "home"]


class StrictModel(BaseModel):
    """Base for every API model: unknown fields are rejected and strings are trimmed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Location(StrictModel):
    """A place chosen by the user: display name and WGS84 coordinates."""

    name: str = Field(min_length=2, max_length=90)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    country: str = Field(default="", max_length=70)
    region: str = Field(default="", max_length=70)


class Profile(StrictModel):
    """The household and routine choices that select recommendations."""

    persona: Literal["family", "commuter", "outdoor", "community"] = "family"
    children: bool = False
    older_adult: bool = False
    respiratory_sensitivity: bool = False
    outdoor_minutes: int = Field(default=45, ge=0, le=480)
    start_hour: int = Field(default=8, ge=0, le=23)
    budget: Literal["none", "low", "flexible"] = "low"
    priorities: list[Priority] = Field(default_factory=default_priorities, max_length=5)
    language: Literal["en", "hi"] = "en"

    @field_validator("priorities")
    @classmethod
    def no_duplicates(cls, v: list[str]) -> list[str]:
        """Reject a priority listed more than once."""
        if len(v) != len(set(v)):
            raise ValueError("Priorities must not be repeated")
        return v


class Hour(StrictModel):
    """One hourly forecast point; values missing upstream stay None."""

    time: str
    us_aqi: float | None = Field(default=None, ge=0, le=700)
    pm2_5: float | None = Field(default=None, ge=0, le=3000)
    pm10: float | None = Field(default=None, ge=0, le=3000)


class Snapshot(StrictModel):
    """A validated forecast for one place, with its source, scale and derived outlook."""

    location: Location
    retrieved_at: str
    model_time: str
    timezone: str
    us_aqi: float | None = Field(default=None, ge=0, le=700)
    pm2_5: float | None = Field(default=None, ge=0, le=3000)
    pm10: float | None = Field(default=None, ge=0, le=3000)
    ozone: float | None = Field(default=None, ge=0, le=3000)
    nitrogen_dioxide: float | None = Field(default=None, ge=0, le=3000)
    hourly: list[Hour] = Field(default_factory=list, max_length=72)
    source: str = "Open-Meteo / CAMS model forecast"
    scale: str = "US EPA AQI (NOT CPCB India AQI)"
    data_kind: str = "Modeled estimate / forecast, not a local monitor measurement"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def category(self) -> str:
        """US EPA category of the current AQI, shared with the policy engine."""
        return band(self.us_aqi).label

    @computed_field  # type: ignore[prop-decorator]
    @property
    def category_key(self) -> str:
        """Stable key the browser uses to colour the category."""
        return band(self.us_aqi).key

    @computed_field  # type: ignore[prop-decorator]
    @property
    def outlook(self) -> list[Hour]:
        """The next 24 hours by elapsed time; the dashboard and the planner both use exactly these."""
        return upcoming_hours(self.model_time, self.hourly)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def outlook_lowest(self) -> Hour | None:
        """Earliest outlook hour with the lowest modeled US AQI."""
        return lowest_aqi_hour(self.outlook)


class PlanRequest(StrictModel):
    """Body of /api/plan: place, profile and explicit AI consent."""

    location: Location
    profile: Profile
    ai_consent: bool = False


class AskRequest(PlanRequest):
    """Body of /api/ask: a plan request plus the user's question."""

    question: str = Field(min_length=5, max_length=600)


class Advice(StrictModel):
    """One recommendation. Frozen because catalog entries are shared between plans."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    id: str
    title: str
    detail: str
    why: str
    priority: Literal["now", "today", "routine"]
    reference: str


class Shift(StrictModel):
    """A better start time for the whole planned activity, with its modeled PM2.5 comparison."""

    current_time: str
    recommended_time: str
    original_pm25: float
    alternate_pm25: float
    duration_min: int
    relative_difference_pct: float
    caution: str


class PolicyResult(StrictModel):
    """The deterministic plan returned by /api/plan."""

    category: str
    concern: Concern
    headline: str
    sensitive: bool
    cards: list[Advice]
    swaps: list[Advice]
    best_window: Hour | None
    lowest_aqi: float | None
    shift: Shift | None
    trace: list[str]
    disclaimer: str


class AiResponse(StrictModel):
    """Gemini's structured reply, validated before it is shown."""

    summary: str = Field(min_length=5, max_length=900)
    steps: list[str] = Field(min_length=2, max_length=5)
    rationale: str = Field(min_length=5, max_length=900)

    @field_validator("steps")
    @classmethod
    def short_steps(cls, v: list[str]) -> list[str]:
        """Each step must be between 4 and 300 characters."""
        if any(not STEP_MIN_CHARS <= len(s) <= STEP_MAX_CHARS for s in v):
            raise ValueError("Steps must be concise")
        return v
