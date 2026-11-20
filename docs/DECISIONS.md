# Design decisions

Short records of choices a reviewer is likely to question, with the reason and the cost.

## 1. Show US AQI from Open-Meteo, labelled, rather than compute India's CPCB index

- **Decision:** display the modeled US EPA AQI that Open-Meteo/CAMS provides, and say on screen that it is not CPCB.
- **Why:** CPCB's index requires station averaging windows and at least three pollutants. Computing it from a coarse grid forecast would look official without being so.
- **Cost:** Indian users see an unfamiliar scale; the disclosure and methodology section explain it.

## 2. Deterministic rules decide; Gemini only narrates

- **Decision:** `airwise/policy.py` chooses every recommendation and computes the timing comparison. Gemini receives those results and writes the briefing and answers.
- **Why:** the same inputs always give the same advice, every card has a traceable reason, and an AI outage cannot remove the plan.
- **Cost:** recommendations change only when the rules or catalog change.

## 3. No invented numbers

- **Decision:** generated prose containing digits or percentage claims is rejected (`validate_brief_text`). Swaps state their mechanism, not estimated savings. The only computed comparison is the modeled PM2.5 difference for the user's own activity window.
- **Why:** personal exposure, emissions saved or health-risk reduction cannot be measured from a grid forecast, so any figure would be a guess.
- **Cost:** the impact explanations are qualitative except for the timing shift.

## 4. One container on Cloud Run, no database

- **Decision:** a single FastAPI process serves the API and static files; caches and rate limits live in memory; at most two instances.
- **Why:** no user data is stored, and the service fits a small, auditable footprint.
- **Cost:** caches and limits are per instance; a larger deployment would need shared state.

## 5. Time budgets end before the browser gives up

- **Decision:** AI work gets at most 40 seconds of each request (`REQUEST_BUDGET_S`); the browser waits 45 seconds.
- **Why:** a slow model must not cost the user the rule-based plan. A live briefing took 21.7 seconds, too close to the earlier 22-second budget.
- **Cost:** a slow answer is reported unavailable rather than waited for indefinitely.

## 6. One definition of each shared rule

- **Decision:** AQI categories (`airwise/aqi.py`) and the 24-hour outlook (`airwise/forecast.py`) are computed on the server and sent with every forecast; the browser only renders them.
- **Why:** when the browser counted 24 rows and the planner counted 24 hours, a missing upstream hour made them disagree.
- **Cost:** responses carry a few extra fields.

## 7. Plain JavaScript modules with type checking, no build step

- **Decision:** the browser code is ES modules typed with JSDoc against `static/js/types.d.ts` and checked by TypeScript in strict mode; nothing is bundled.
- **Why:** no runtime dependencies or build artifacts, while type errors still fail CI.
- **Cost:** types live in comments rather than `.ts` files.

## 8. No Dependabot

- **Decision:** dependencies are pinned and audited in CI (`pip-audit`, `npm audit`, CodeQL) and updated by hand.
- **Why:** Dependabot opens update branches, and the competition requires a single branch.
- **Cost:** updates are not proposed automatically.
