# Hack2Skill submission form — copy and adapt after real deployment

**Challenge:** Challenge 6 — Urban Air Quality Assistant

**Public GitHub Repository Link:** `https://github.com/pranavg21/airwise-promptwars-c6`

**Project Deployed Link:** `https://YOUR-ACTUAL-DEPLOYMENT.example` (**replace with the actual HTTPS URL, verify incognito**)

**Project Demo Video Submission:** `https://YOUR-REAL-UNLISTED-YOUTUBE-OR-PUBLIC-DRIVE-VIDEO` (**only after recording and link testing**)

### Describe the changes/updates made in the deployed version (max 1,024 characters)

AirWise is a source-grounded Urban Air Quality Assistant built for families, commuters, outdoor workers and communities. It integrates Open-Meteo/CAMS modeled AQI and particulate data, city search, a 24-hour forecast chart, evidence-backed protection routines, indoor-source controls and sustainable low-emission swaps. The rules engine adapts to children, older adults, respiratory sensitivity, schedule, budget and daily priorities, with auditable reasons for every suggestion. A forecast comparison explicitly distinguishes modeled PM2.5 differences from personal health benefit. Optional server-side Gemini generates personalized daily briefs and responds to live questions. The application includes accessible charts/tables, shareable community summaries, print support, secure input validation, CI and automated testing, and clear attribution of US AQI versus India's CPCB scale.

### Mention GenAI services utilized and where you used them (max 1,024 characters)

Google Gemini Developer API (`gemini-3.5-flash-lite`, configurable) is used server-side for opt-in personalized daily air-quality briefings and contextual follow-up answers. The FastAPI `/api/plan` and `/api/ask` endpoints send Gemini a validated, minimized summary of live-modeled Open-Meteo/CAMS air data, user-selected routine preferences and independently generated policy recommendations. Gemini returns structured JSON that is validated before safe text rendering. External AQI numbers, forecast comparisons, safety boundaries and sustainable swaps come from deterministic code rather than invented model facts. When GenAI is unavailable or consent is not given, the app labels this clearly and preserves fully functional rule-based guidance. No API keys are shipped to browsers.

### LinkedIn Post URL

`https://www.linkedin.com/posts/YOUR-ACTUAL-PUBLISHED-POST` (**publish first; URL must be real**)

#### Draft LinkedIn post

Built **AirWise** for Hack2Skill's PromptWars Virtual — Challenge 6: Urban Air Quality Assistant. 🌿

Winter smog isn't just an AQI number. It changes how families plan school runs, commutes, exercise, and indoor routines.

AirWise combines source-labeled Open-Meteo/CAMS modeled air quality with explainable decision rules, practical low-emission swaps, and optional Google Gemini personalization. It distinguishes US AQI estimates from India's CPCB measurements, explains the reason behind each action, and remains usable when the GenAI service is unavailable.

What I focused on: data provenance, safe AI boundaries, meaningful tests, accessibility, privacy, and a genuinely useful family/community experience.

Live application: [ACTUAL HTTPS LINK]
Public source: [ACTUAL GITHUB LINK]
Demo: [PUBLIC VIDEO LINK]

#PromptWars #Hack2Skill #BuildWithAI #GeminiAPI #AirQuality #ResponsibleAI #Python #FastAPI

**Do not publish claims about deployment, live AI results, or test pass counts until they match the actual released version.**
