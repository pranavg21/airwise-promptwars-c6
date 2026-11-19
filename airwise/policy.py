"""Transparent, deterministic advice engine. GenAI cannot overwrite the facts."""
from __future__ import annotations

from datetime import datetime, timedelta
from dataclasses import dataclass
from .models import Advice, Hour, PolicyResult, Profile, Shift, Snapshot

REFERENCE_WHO = "https://www.who.int/news-room/questions-and-answers/item/air-pollution-personal-interventions-and-risk-communication"
REFERENCE_EPA = "https://www.epa.gov/wildfire-smoke-course/strategies-reduce-exposure-indoors"
REFERENCE_AQI = "https://open-meteo.com/en/docs/air-quality-api"
REFERENCE_TRANSPORT = "https://www.epa.gov/transportation-air-pollution-and-climate-change/what-you-can-do-reduce-pollution-vehicles-and"
REFERENCE_SCHOOL = "https://www.epa.gov/schools/idle-free-schools-toolkit-healthy-school-environment"
REFERENCE_INDOOR = "https://www.epa.gov/indoor-air-quality-iaq/sources-indoor-particulate-matter-pm"


def classify(value: float | None) -> tuple[str, str]:
    """US EPA AQI categories, not India's CPCB categories."""
    if value is None:
        return "Unavailable", "unknown"
    if value <= 50:
        return "Good", "low"
    if value <= 100:
        return "Moderate", "moderate"
    if value <= 150:
        return "Unhealthy for sensitive groups", "high"
    if value <= 200:
        return "Unhealthy", "high"
    if value <= 300:
        return "Very unhealthy", "very_high"
    return "Hazardous", "very_high"


def upcoming_hours(snapshot: Snapshot, hours: int = 24) -> list[Hour]:
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
    by_time = dict(zip(times, hours))
    if len(by_time) != len(times):
        return []  # Repeated local hour (e.g. clock change) is ambiguous.
    windows = []
    for start in times:
        total = peak = 0.0
        for minute in range(0, duration, 60):
            hour = by_time.get(start + timedelta(minutes=minute))
            if hour is None or hour.us_aqi is None or hour.pm2_5 is None:
                break
            total += hour.pm2_5 * min(60, duration - minute)
            peak = max(peak, hour.us_aqi)
        else:
            windows.append(ActivityWindow(by_time[start], total / duration, peak))
    return windows


def find_lower_hour(snapshot: Snapshot, profile: Profile) -> tuple[Hour | None, Shift | None]:
    hours = upcoming_hours(snapshot)
    minimum = min((h for h in hours if h.us_aqi is not None), key=lambda h: h.us_aqi, default=None)
    windows = activity_windows(hours, profile.outdoor_minutes)
    planned = next((w for w in windows if datetime.fromisoformat(w.start.time).hour == profile.start_hour), None)
    if planned is None or planned.mean_pm25 == 0:
        return minimum, None
    alternate = min((w for w in windows if w.peak_aqi <= planned.peak_aqi),
                    key=lambda w: w.mean_pm25)
    difference = (1 - alternate.mean_pm25 / planned.mean_pm25) * 100
    if difference < 5:
        return minimum, None
    return minimum, Shift(
        current_time=planned.start.time, recommended_time=alternate.start.time,
        original_pm25=round(planned.mean_pm25, 1), alternate_pm25=round(alternate.mean_pm25, 1),
        duration_min=profile.outdoor_minutes, relative_difference_pct=round(difference, 1),
        caution="Duration-weighted modeled outdoor PM2.5. Not a personal dose or health-risk reduction; check whether the timing is practical."
    )


def generate_policy(snapshot: Snapshot, profile: Profile) -> PolicyResult:
    category, concern = classify(snapshot.us_aqi)
    sensitive = bool(profile.children or profile.older_adult or profile.respiratory_sensitivity)
    minimum, shift = find_lower_hour(snapshot, profile)
    cards: list[Advice] = []
    swaps: list[Advice] = []
    trace = ["Pollution level is based on US AQI from Open-Meteo/CAMS, not CPCB station measurements."]
    def add(id_: str, title: str, detail: str, why: str, priority: str, ref: str = REFERENCE_WHO) -> None:
        cards.append(Advice(id=id_, title=title, detail=detail, why=why, priority=priority, reference=ref))
    if concern in {"high", "very_high"}:
        add("outdoor", "Reduce strenuous outdoor exposure", "Shift vigorous workouts indoors or shorten nonessential outdoor exertion. For unavoidable travel, reduce time near heavy traffic.", "Elevated air pollution and prolonged outdoor exertion can increase exposure; balance activity benefits with your circumstances.", "now")
        trace.append(f"AQI {snapshot.us_aqi:g} is in a US AQI category of concern.")
    elif concern == "moderate" and sensitive:
        add("outdoor", "Adapt outdoor activity for sensitive people", "Keep an eye on symptoms and consider shorter or less intense outdoor sessions; use the hourly outlook to choose timing.", "Sensitive groups may experience more discomfort even when other adults do not.", "today")
        trace.append("Sensitive household profile + moderate AQI triggers additional precautions.")
    elif concern == "low":
        add("activity", "Keep your routine, watch for changes", "Outdoor activity can usually continue. Check the next-day trend before prolonged activity.", "The modeled US AQI is in the Good range.", "routine")
    else:
        add("activity", "Choose lower-exposure times when practical", "Use hourly forecast patterns as a guide, not a guarantee of clean air. Limit traffic-adjacent waiting where possible.", "Local pollution levels may change quickly.", "today")

    if "home" in profile.priorities or profile.persona == "family" or sensitive:
        add("home", "Build a cleaner-air room", "Avoid indoor smoke, incense and unnecessary frying. During severe outdoor episodes, limit polluted-air entry when feasible while keeping adequate ventilation and safe indoor temperatures. A properly sized HEPA cleaner may help reduce particles.", "Outdoor air is not the only source of indoor pollution; ventilation and filtration decisions depend on the building.", "today", REFERENCE_EPA)
        trace.append("Family/home priority adds low-cost indoor-source controls and conditional filtration advice.")
    if profile.children or "school" in profile.priorities:
        add("school", "Plan the school run", "Prefer less congested pickup points and avoid idling vehicles; coordinate indoor alternatives for strenuous outdoor school activities during severe episodes.", "Children may be more susceptible to short-term pollution exposure.", "today")
        trace.append("School or children preference activates school-run guidance.")
    if "commute" in profile.priorities or profile.persona == "commuter":
        add("commute", "Reduce exposure along your commute", "If feasible, travel outside peak congestion or avoid waiting beside idling exhaust. On high-pollution days use vehicle recirculation briefly when appropriate; ensure adequate ventilation and never ignore vehicle safety guidance.", "Time, location and activity can change exposure; this app has no street-level route sensors.", "today")
    if "exercise" in profile.priorities:
        add("exercise", "Protect exercise benefits", "Keep moving where possible: use a cleaner indoor space or choose a lower-pollution hour rather than automatically cancelling all exercise.", "Activity brings health benefits; timing and location can reduce pollution exposure.", "today")
    if profile.persona == "outdoor":
        add("worker", "Protect essential outdoor work", "Use employer safety procedures, arrange breaks in cleaner indoor air if possible, and avoid prolonged traffic-adjacent idling. Seek occupational guidance for suitable respirators and fit.", "Work-related controls must not be replaced with a generic consumer recommendation.", "now")
    if profile.persona == "community" or "community" in profile.priorities:
        add("community", "Coordinate a neighborhood response", "Share a source-labeled update, reduce vehicle idling near shared entrances, plan low-emission errands together, and prioritize accessible indoor alternatives for vulnerable residents.", "Collective source reduction and equitable access matter more than shifting all responsibility to individuals.", "today")
    if profile.budget == "none":
        add("budget", "No-purchase protection first", "Start with avoiding indoor smoke, reducing unnecessary exposure, and adjusting timing before buying equipment. Do not assume a sealed room has safe air without ventilation.", "Behavioral changes may be more accessible than expensive filtration.", "routine")
    if profile.respiratory_sensitivity:
        add("medical", "Follow your personal care plan", "Keep prescribed treatment and clinician instructions unchanged. If breathing becomes severely difficult, seek urgent medical care; this app cannot assess symptoms or prescribe treatment.", "People with respiratory conditions require individualized medical guidance.", "now")
    if minimum and minimum.us_aqi is not None:
        trace.append(f"Lowest modeled US AQI in the next available 24 hours is {minimum.us_aqi:g} at {minimum.time} local time; this does not make that hour safe.")
    if shift:
        trace.append("Timing comparison uses same-location hourly modeled PM2.5 only; does not predict personal inhaled dose.")
    # Everyday sustainable swaps have explicit mechanisms, not fabricated CO2 or AQI savings.
    if "commute" in profile.priorities or profile.persona == "commuter":
        swaps.append(Advice(id="trip-swap", title="Replace one avoidable car trip",
            detail="Combine nearby errands or use a practical bus/metro option rather than an extra solo-car journey. When pollution is high, avoid substituting a long roadside walk without considering exposure.",
            why="One actually avoided vehicle journey can avoid that journey's direct tailpipe emissions; the amount is unmeasured here and depends on the vehicle and alternative.",
            priority="routine", reference=REFERENCE_TRANSPORT))
    if "home" in profile.priorities or profile.persona == "family":
        swaps.append(Advice(id="combustion-swap", title="Swap indoor burning for no-flame alternatives",
            detail="Replace incense and scented candles with unscented or non-burning options. Avoid waste burning. Prefer damp-dusting to dispersing settled particles.",
            why="Eliminating an indoor combustion source avoids emissions from that source; it does not guarantee clean indoor air.",
            priority="routine", reference=REFERENCE_INDOOR))
    if "school" in profile.priorities or profile.children:
        swaps.append(Advice(id="pickup-swap", title="A cleaner school-pickup habit",
            detail="Where safe and allowed, switch off parked engines rather than idling near the school gate; coordinate shared pickups when practical.",
            why="Reducing unnecessary engine idling reduces exhaust directly at the pickup point. Exact reductions are not measured.",
            priority="today", reference=REFERENCE_SCHOOL))
    if profile.persona == "community" or "community" in profile.priorities:
        swaps.append(Advice(id="shared-swap", title="Make cleaner routines a neighborhood habit",
            detail="Try a voluntary no-idling zone at apartment entrances and consolidate nonurgent delivery/pickup trips. Include residents who need accessible transport.",
            why="Avoided idling and unnecessary trips can reduce local emissions, but effects depend on real participation.",
            priority="routine", reference=REFERENCE_TRANSPORT))
    if not swaps:
        swaps.append(Advice(id="universal-swap", title="Avoid unnecessary combustion",
            detail="Reduce nonessential idling and open burning when under your control; prioritize practical low- or no-cost habits.",
            why="Removing combustion sources prevents emissions from those activities without pretending to measure citywide AQI changes.",
            priority="routine", reference=REFERENCE_TRANSPORT))
    trace.append("Sustainable swaps report direct mechanisms only; no unsupported individual CO₂ or health-risk percentage claims.")
    headline = (
        "Take precautions for outdoor exposure" if concern in {"high", "very_high"} else
        "Extra care for sensitive household members" if sensitive and concern == "moderate" else
        "Air data missing — avoid unsupported assumptions" if concern == "unknown" else
        "Make small shifts for cleaner daily routines"
    )
    return PolicyResult(
        category=category, concern=concern, headline=headline, sensitive=sensitive,
        cards=cards, swaps=swaps, best_window=minimum, lowest_aqi=minimum.us_aqi if minimum else None,
        shift=shift, trace=trace,
        disclaimer=("Decision-support information only; not a diagnosis, a local sensor reading, "
                    "a guarantee of safe outdoor exposure, or an official CPCB AQI alert. "
                    "Follow local authorities and personal medical advice.")
    )
