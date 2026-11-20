# Architecture — boundaries, provenance and logic

## Main flows

```mermaid
sequenceDiagram
 participant User
 participant UI as Browser
 participant API as FastAPI
 participant Open as Open-Meteo/CAMS
 participant Rules as Policy Engine
 participant AI as Gemini
 User->>UI: Choose city, persona, priorities, budget
 UI->>API: GET /api/geo?q=... (city lookup)
 API->>Open: Geocoding (fixed upstream URL)
 Open-->>API: Coordinates
 API-->>UI: Validated location options
 UI->>API: POST /api/plan (location, profile, opt-in)
 API->>Open: Air-quality API (fixed upstream URL; 8m cache)
 Open-->>API: Model current + hourly
 API->>Rules: Validated modeled Snapshot + Profile
 Rules-->>API: Rule-based actions, trace and swaps
 opt User has opted into AI
 API->>AI: Context-restricted JSON generation request
 AI-->>API: JSON narrative
 API->>API: Strict Pydantic validation
 end
 API-->>UI: Facts + rules + verified AI status / optional narrative
 UI-->>User: Source-labeled air dashboard and decisions
```

## Data contracts

`Location` accepts name, optional country/region and WGS84 latitude/longitude, not arbitrary URLs. `Profile` accepts only four personas, five priorities, three budget bands, two languages, boolean sensitivity flags and bounded outdoor activity time. Unknown fields are rejected by default.

`Snapshot` carries `model_time`, `retrieved_at`, provider source, AQI index type, the five current modeled parameters and at most 72 `Hour` records. The API makes no promise of an individual street-level or inside-home reading.

`PolicyResult` contains `category`, `concern`, `sensitive`, `cards`, `swaps`, optional best hour and shift, trace statements, and a fixed safety disclaimer. These are authored by a deterministic engine and never overwritten by the generative model.

`AiResponse` carries three plain-text outputs — summary, 2–5 steps and rationale — within strict length limits. The UI always uses `textContent` and DOM nodes to render them.

## AQI interpretation

Open-Meteo exposes **US EPA AQI** indices. The project uses the following categories: Good 0–50; Moderate 51–100; Unhealthy for Sensitive Groups 101–150; Unhealthy 151–200; Very Unhealthy 201–300; Hazardous ≥301. **These are US scale categories, not India's CPCB six-category AQI system.**

CAMS global modeled data have coarse horizontal resolution (documentation identifies around 45 km grid scale). On a road corner, schools' entrances or inside apartments, the actual air can differ substantially. `model_time` is a model point's valid time, not a promise of physical sensor observation. `retrieved_at` is when our server fetched it.

## Timing engine

The engine reports the lowest modeled hourly US AQI separately from the activity comparison. For the latter, it averages modeled PM2.5 across the selected duration, weighting the final hour by its occupied minutes. It compares complete windows within the next 24 hours and requires an equal or lower peak AQI and at least 5% lower mean PM2.5. This threshold is a display rule. The model cannot establish personal dose, route conditions, or whether the user can change schedules.

`relative_difference_pct = 100 × (1 - alternative_pm25 / planned_pm25)`

The calculation is suppressed when PM2.5 is missing, the comparison is unfavorable, the difference is <5%, or planned outdoor minutes are zero. There is no unvalidated indoor infiltration multiplier, street-by-street forecast, breathing-rate assumption or personal health-risk ratio.

## Low-emission choices and direct impact

- Commuting: avoid unnecessary solo-car trips, consolidate errands, consider public transportation. Direct mechanism: avoided vehicle journey can avoid tailpipe emissions *from that journey*; no emissions total is claimed.
- Household: eliminate unnecessary incense/candle/open burning sources. Direct mechanism: prevent emissions from that source, without promising a clean indoor room.
- School: switch off safely parked engines rather than idling at pickup. Direct mechanism: less exhaust produced beside the gate.
- Community: accessible shared no-idling norms, combined deliveries and transparent public notices. Direct mechanism: fewer unnecessary combustion events, contingent on participation.

Actions for vulnerable residents are more precautionary but avoid replacing personal clinician advice. In high or very high US AQI categories, the tool discourages vigorous outdoor exercise and suggests feasible alternatives; it does not suggest avoiding all movement in every case. Where indoor air is unhealthy or a house needs ventilation, the message explicitly notes the tradeoff.

## AI boundary and observability

`/api/plan` returns rule guidance without Gemini when `ai_consent=false`. With opt-in, Gemini gets the city name, current modeled values, profile flags and already-authorized advice. The API key stays on server-side `os.environ`; model identifier is allowlisted. The prompt includes no exact street address, account identifiers or browsing data.

If Gemini is missing, times out, returns bad JSON or fails validation, API returns `ai=null` with `ai_status=unavailable`; it **does not impersonate successful generation**. Users can still act on the rules. `/api/ask` refuses requests without opt-in or when a key is unavailable.

The service uses short timeouts, limited request sizes, bounded cache entries, a short in-memory rate limit and static host allowlisting for upstream queries. For horizontally scaled production, replace process-local throttling with edge/WAF and centralized quotas before opening to high public traffic.

## Deployment topology

Single Python process, static assets served from `/static`, API served under `/api`, Docker image using unprivileged app user. Health route provides API readiness and AI configuration boolean; it does not expose credentials. Hosting must be HTTPS. Free-tier suspension/cold starts are a product risk and should be accounted for before judges review.

## Test inventory

- AQI classification boundaries and missing values
- Family/school, commuter, worker and community persona differentiation
- School and respiratory sensitivity
- Budget/no-purchase rules
- Hourly forecast filtering and proper denominator in timing calculation
- Sustainable swaps with no invented quantitative savings
- Partial/malformed/unavailable upstream data
- SSRF prevention via fixed URL allowlist
- Geocoding validation and TTL cache
- Gemini opt-in and structured-output validation
- `/api/ask` success, forecast outage, missing key, truncated output, and an upstream quota (HTTP 429) rejection on both AI routes
- Model identifier validation, missing key, malformed/overlong AI output
- API request-body, unknown-field, coordinate and media-type rejection
- CSP and security response headers, rate limiting, publicly accessible UI

Note: all sample values in automated tests are **synthetic fixtures**, not live pollution readings.
