"""Recommendation text, sources and fixed messages.

The conditions that select these entries live in policy.py. Wording here is user-facing:
change it deliberately, and keep each entry's mechanism and limitation explicit.
"""

from __future__ import annotations

from .models import Advice

REFERENCE_WHO = (
    "https://www.who.int/news-room/questions-and-answers/item/"
    "air-pollution-personal-interventions-and-risk-communication"
)
REFERENCE_EPA = "https://www.epa.gov/wildfire-smoke-course/strategies-reduce-exposure-indoors"
REFERENCE_TRANSPORT = (
    "https://www.epa.gov/transportation-air-pollution-and-climate-change/"
    "what-you-can-do-reduce-pollution-vehicles-and"
)
REFERENCE_SCHOOL = "https://www.epa.gov/schools/idle-free-schools-toolkit-healthy-school-environment"
REFERENCE_INDOOR = "https://www.epa.gov/indoor-air-quality-iaq/sources-indoor-particulate-matter-pm"

# Exposure: exactly one of these opens every plan.
OUTDOOR_HIGH = Advice(
    id="outdoor",
    title="Reduce strenuous outdoor exposure",
    detail="Shift vigorous workouts indoors or shorten nonessential outdoor exertion. "
    "For unavoidable travel, reduce time near heavy traffic.",
    why="Elevated air pollution and prolonged outdoor exertion can increase exposure; "
    "balance activity benefits with your circumstances.",
    priority="now",
    reference=REFERENCE_WHO,
)
OUTDOOR_SENSITIVE = Advice(
    id="outdoor",
    title="Adapt outdoor activity for sensitive people",
    detail="Keep an eye on symptoms and consider shorter or less intense outdoor sessions; "
    "use the hourly outlook to choose timing.",
    why="Sensitive groups may experience more discomfort even when other adults do not.",
    priority="today",
    reference=REFERENCE_WHO,
)
ACTIVITY_GOOD = Advice(
    id="activity",
    title="Keep your routine, watch for changes",
    detail="Outdoor activity can usually continue. Check the next-day trend before prolonged activity.",
    why="The modeled US AQI is in the Good range.",
    priority="routine",
    reference=REFERENCE_WHO,
)
ACTIVITY_DEFAULT = Advice(
    id="activity",
    title="Choose lower-exposure times when practical",
    detail="Use hourly forecast patterns as a guide, not a guarantee of clean air. "
    "Limit traffic-adjacent waiting where possible.",
    why="Local pollution levels may change quickly.",
    priority="today",
    reference=REFERENCE_WHO,
)

# Situation-specific actions.
HOME = Advice(
    id="home",
    title="Build a cleaner-air room",
    detail="Avoid indoor smoke, incense and unnecessary frying. During severe outdoor episodes, "
    "limit polluted-air entry when feasible while keeping adequate ventilation and safe indoor "
    "temperatures. A properly sized HEPA cleaner may help reduce particles.",
    why="Outdoor air is not the only source of indoor pollution; ventilation and filtration "
    "decisions depend on the building.",
    priority="today",
    reference=REFERENCE_EPA,
)
SCHOOL = Advice(
    id="school",
    title="Plan the school run",
    detail="Prefer less congested pickup points and avoid idling vehicles; coordinate indoor "
    "alternatives for strenuous outdoor school activities during severe episodes.",
    why="Children may be more susceptible to short-term pollution exposure.",
    priority="today",
    reference=REFERENCE_WHO,
)
COMMUTE = Advice(
    id="commute",
    title="Reduce exposure along your commute",
    detail="If feasible, travel outside peak congestion or avoid waiting beside idling exhaust. "
    "On high-pollution days use vehicle recirculation briefly when appropriate; ensure adequate "
    "ventilation and never ignore vehicle safety guidance.",
    why="Time, location and activity can change exposure; this app has no street-level route sensors.",
    priority="today",
    reference=REFERENCE_WHO,
)
EXERCISE = Advice(
    id="exercise",
    title="Protect exercise benefits",
    detail="Keep moving where possible: use a cleaner indoor space or choose a lower-pollution hour "
    "rather than automatically cancelling all exercise.",
    why="Activity brings health benefits; timing and location can reduce pollution exposure.",
    priority="today",
    reference=REFERENCE_WHO,
)
WORKER = Advice(
    id="worker",
    title="Protect essential outdoor work",
    detail="Use employer safety procedures, arrange breaks in cleaner indoor air if possible, and "
    "avoid prolonged traffic-adjacent idling. Seek occupational guidance for suitable respirators and fit.",
    why="Work-related controls must not be replaced with a generic consumer recommendation.",
    priority="now",
    reference=REFERENCE_WHO,
)
COMMUNITY = Advice(
    id="community",
    title="Coordinate a neighborhood response",
    detail="Share a source-labeled update, reduce vehicle idling near shared entrances, plan "
    "low-emission errands together, and prioritize accessible indoor alternatives for vulnerable residents.",
    why="Collective source reduction and equitable access matter more than shifting all responsibility "
    "to individuals.",
    priority="today",
    reference=REFERENCE_WHO,
)
BUDGET = Advice(
    id="budget",
    title="No-purchase protection first",
    detail="Start with avoiding indoor smoke, reducing unnecessary exposure, and adjusting timing before "
    "buying equipment. Do not assume a sealed room has safe air without ventilation.",
    why="Behavioral changes may be more accessible than expensive filtration.",
    priority="routine",
    reference=REFERENCE_WHO,
)
MEDICAL = Advice(
    id="medical",
    title="Follow your personal care plan",
    detail="Keep prescribed treatment and clinician instructions unchanged. If breathing becomes severely "
    "difficult, seek urgent medical care; this app cannot assess symptoms or prescribe treatment.",
    why="People with respiratory conditions require individualized medical guidance.",
    priority="now",
    reference=REFERENCE_WHO,
)

# Sustainable swaps state direct mechanisms, never invented CO2 or AQI savings.
TRIP_SWAP = Advice(
    id="trip-swap",
    title="Replace one avoidable car trip",
    detail="Combine nearby errands or use a practical bus/metro option rather than an extra solo-car "
    "journey. When pollution is high, avoid substituting a long roadside walk without considering exposure.",
    why="One actually avoided vehicle journey can avoid that journey's direct tailpipe emissions; the "
    "amount is unmeasured here and depends on the vehicle and alternative.",
    priority="routine",
    reference=REFERENCE_TRANSPORT,
)
COMBUSTION_SWAP = Advice(
    id="combustion-swap",
    title="Swap indoor burning for no-flame alternatives",
    detail="Replace incense and scented candles with unscented or non-burning options. Avoid waste "
    "burning. Prefer damp-dusting to dispersing settled particles.",
    why="Eliminating an indoor combustion source avoids emissions from that source; it does not "
    "guarantee clean indoor air.",
    priority="routine",
    reference=REFERENCE_INDOOR,
)
PICKUP_SWAP = Advice(
    id="pickup-swap",
    title="A cleaner school-pickup habit",
    detail="Where safe and allowed, switch off parked engines rather than idling near the school gate; "
    "coordinate shared pickups when practical.",
    why="Reducing unnecessary engine idling reduces exhaust directly at the pickup point. "
    "Exact reductions are not measured.",
    priority="today",
    reference=REFERENCE_SCHOOL,
)
SHARED_SWAP = Advice(
    id="shared-swap",
    title="Make cleaner routines a neighborhood habit",
    detail="Try a voluntary no-idling zone at apartment entrances and consolidate nonurgent "
    "delivery/pickup trips. Include residents who need accessible transport.",
    why="Avoided idling and unnecessary trips can reduce local emissions, but effects depend on "
    "real participation.",
    priority="routine",
    reference=REFERENCE_TRANSPORT,
)
UNIVERSAL_SWAP = Advice(
    id="universal-swap",
    title="Avoid unnecessary combustion",
    detail="Reduce nonessential idling and open burning when under your control; prioritize practical "
    "low- or no-cost habits.",
    why="Removing combustion sources prevents emissions from those activities without pretending to "
    "measure citywide AQI changes.",
    priority="routine",
    reference=REFERENCE_TRANSPORT,
)

# Decision trace. Templates may use {aqi} and {time}.
TRACE_SOURCE = "Pollution level is based on US AQI from Open-Meteo/CAMS, not CPCB station measurements."
TRACE_HIGH_CONCERN = "AQI {aqi:g} is in a US AQI category of concern."
TRACE_SENSITIVE_MODERATE = "Sensitive household profile + moderate AQI triggers additional precautions."
TRACE_HOME = "Family/home priority adds low-cost indoor-source controls and conditional filtration advice."
TRACE_SCHOOL = "School or children preference activates school-run guidance."
TRACE_LOWEST_HOUR = (
    "Lowest modeled US AQI in the next available 24 hours is {aqi:g} at {time} local time; "
    "this does not make that hour safe."
)
TRACE_SHIFT = (
    "Timing comparison uses same-location hourly modeled PM2.5 only; does not predict personal inhaled dose."
)
TRACE_SWAPS = (
    "Sustainable swaps report direct mechanisms only; no unsupported individual CO₂ or "
    "health-risk percentage claims."
)

HEADLINE_HIGH = "Take precautions for outdoor exposure"
HEADLINE_SENSITIVE = "Extra care for sensitive household members"
HEADLINE_UNKNOWN = "Air data missing — avoid unsupported assumptions"
HEADLINE_DEFAULT = "Make small shifts for cleaner daily routines"

SHIFT_CAUTION = (
    "Duration-weighted modeled outdoor PM2.5. Not a personal dose or health-risk reduction; "
    "check whether the timing is practical."
)
DISCLAIMER = (
    "Decision-support information only; not a diagnosis, a local sensor reading, "
    "a guarantee of safe outdoor exposure, or an official CPCB AQI alert. "
    "Follow local authorities and personal medical advice."
)
