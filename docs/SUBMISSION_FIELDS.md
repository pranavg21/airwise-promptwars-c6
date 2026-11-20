# Hack2Skill submission form — verified deployment packet

**Challenge:** Challenge 6 — Urban Air Quality Assistant

**Public GitHub Repository Link:** `https://github.com/pranavg21/airwise-promptwars-c6`

**Project Deployed Link:** `https://airwise-promptwars-c6-897669266422.asia-south1.run.app`

**Project Demo Video Submission:** https://youtu.be/TvnFK4hocVI

---

### Describe the changes/updates made in the deployed version (max 1,024 characters)
*Character count: 930 characters*

AirWise helps families, commuters, outdoor workers and neighbourhood groups plan around winter smog with Open-Meteo/CAMS modeled air data, labelled as US AQI rather than India's CPCB index. Ordered rules choose routines, indoor actions and low-emission swaps, each with its direct mechanism, and compare the whole planned activity across start times. This version defines the 24-hour outlook once, so the dashboard and the plan always use the same hours; accepts city names with apostrophes; and discards late AI answers after settings change. The code is split into single-purpose modules checked in CI by ruff, mypy strict, strict TypeScript, ESLint and Prettier, with 100% branch coverage and a planted-bug check. Gemini calls have a 40-second budget and a 15-minute answer cache. CodeQL, dependency audits, pinned actions and strict security headers protect the service; axe-core and Lighthouse report no accessibility issues.

---

### Mention GenAI services utilized and where you used them (max 1,024 characters)
*Character count: 1009 characters*

Google Gemini Developer API (gemini-2.5-flash) is used server-side, only after the user opts in, for a personalized daily air-quality briefing and for follow-up questions. The FastAPI /api/plan and /api/ask endpoints send Gemini a minimized summary of Open-Meteo/CAMS modeled air data, the user's routine preferences and the action cards already selected by deterministic rules. Pydantic validates Gemini's structured JSON before the browser renders it as plain text. AQI and PM2.5 values, the timing comparison, safety limits and sustainable swaps come from code, not the model. Generated prose containing digits or percentage claims is rejected, and exact readings are shown separately with their source and time. If Gemini is unavailable, rate-limited or returns invalid output, the app says so and the rule-based plan still works. Identical requests reuse a validated answer for 15 minutes, and an optional fallback model is tried if the first fails. The key stays in Secret Manager, never in the browser.

---

### LinkedIn Post URL

Submitted in the portal with Attempt 2. Reuse the same published post URL for any later attempt.

#### Draft LinkedIn post (in Pranav Ghadge's voice)

Built **AirWise** for Hack2Skill's PromptWars Virtual — Challenge 6: Urban Air Quality Assistant. 🌿

Winter smog in our cities isn't just an abstract AQI number on a dashboard. It dictates whether children can play outside, how commuters handle traffic congestion, and whether homes should seal windows or maintain ventilation.

AirWise bridges real Open-Meteo/CAMS modeled air-quality data with auditable, deterministic decision logic, actionable low-emission swaps, and an opt-in Google Gemini personalization layer.

What makes AirWise distinct:
1. Data Integrity: Grounded in modeled CAMS forecasts with explicit US EPA AQI labeling (transparently distinguished from India's CPCB scale). No invented sensors or hallucinated numbers.
2. Transparent Policy Engine: Deterministic rule cards explaining the direct physical mechanism behind every indoor and commute recommendation.
3. Responsible GenAI: Gemini 2.5 Flash writes the narrative only after opt-in. Its structured output is schema-validated on the server, and prose containing digits or percentages is rejected. If AI is off or unavailable, the rule-based plan still works.
4. Honest Exposure Comparison: Uses duration-weighted local PM2.5 forecast shifts while clearly stating it does not predict personal inhaled dose.

Live application: https://airwise-promptwars-c6-897669266422.asia-south1.run.app
Public repository: https://github.com/pranavg21/airwise-promptwars-c6
Demo video: https://youtu.be/TvnFK4hocVI

#PromptWars #Hack2Skill #GoogleCloud #GeminiAPI #CloudRun #AirQuality #FastAPI #ResponsibleAI #Python
