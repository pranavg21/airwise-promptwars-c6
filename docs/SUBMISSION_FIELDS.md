# Hack2Skill submission form — verified deployment packet

**Challenge:** Challenge 6 — Urban Air Quality Assistant

**Public GitHub Repository Link:** `https://github.com/pranavg21/airwise-promptwars-c6`

**Project Deployed Link:** `https://airwise-promptwars-c6-897669266422.asia-south1.run.app`

**Project Demo Video Submission:** `https://YOUR-REAL-UNLISTED-YOUTUBE-OR-PUBLIC-DRIVE-VIDEO` (replace with your published video URL)

---

### Describe the changes/updates made in the deployed version (max 1,024 characters)
*Character count: 885 characters*

AirWise is a source-grounded Urban Air Quality Assistant built for families, commuters, outdoor workers and communities. It integrates Open-Meteo/CAMS modeled AQI and particulate data, city search, a 24-hour forecast chart, evidence-backed protection routines, indoor-source controls and sustainable low-emission swaps. The rules engine adapts to children, older adults, respiratory sensitivity, schedule, budget and daily priorities, with auditable reasons for every suggestion. A forecast comparison explicitly distinguishes modeled PM2.5 differences from personal health benefit. Optional server-side Gemini generates personalized daily briefs and responds to live questions. The application includes accessible charts/tables, shareable community summaries, print support, secure input validation, CI and automated testing, and clear attribution of US AQI versus India's CPCB scale.

---

### Mention GenAI services utilized and where you used them (max 1,024 characters)
*Character count: 914 characters*

Google Gemini Developer API (gemini-2.5-flash) is used server-side, only after the user opts in, for a personalized daily air-quality briefing and for follow-up questions. The FastAPI /api/plan and /api/ask endpoints send Gemini a minimized summary of Open-Meteo/CAMS modeled air data, the user's routine preferences and the action cards already selected by deterministic rules. Gemini returns structured JSON that Pydantic validates before the browser renders it as plain text. AQI and PM2.5 values, the timing comparison, safety limits and sustainable swaps come from code, not the model. Generated prose containing digits or percentage claims is rejected, and exact readings are shown separately with their source and time. If Gemini is unavailable, rate-limited or returns invalid output, the app says so and the rule-based plan still works. The API key is held in Secret Manager and never sent to the browser.

---

### LinkedIn Post URL

`https://www.linkedin.com/posts/YOUR-ACTUAL-PUBLISHED-POST` (publish first; URL must be real)

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
Demo video: [VIDEO_LINK]

#PromptWars #Hack2Skill #GoogleCloud #GeminiAPI #CloudRun #AirQuality #FastAPI #ResponsibleAI #Python
