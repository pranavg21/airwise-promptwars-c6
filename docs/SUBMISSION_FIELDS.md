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
*Character count: 927 characters*

Google Gemini Developer API (gemini-2.5-flash) is used server-side for opt-in personalized daily air-quality briefings and contextual follow-up answers. The FastAPI /api/plan and /api/ask endpoints send Gemini a validated, minimized summary of live-modeled Open-Meteo/CAMS air data, user-selected routine preferences and independently generated policy recommendations. Gemini returns structured JSON that is validated against strict Pydantic schemas before safe text rendering. External AQI numbers, forecast comparisons, safety boundaries and sustainable swaps come from deterministic code rather than invented model facts. Output validation suppresses fabricated digits, percentage claims, and unverified medical advice. When GenAI is unavailable or consent is not given, the app labels this clearly and preserves fully functional rule-based guidance. Keys remain securely in Secret Manager and are never shipped to browsers.

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
3. Responsible GenAI: Powered by Gemini 2.5 Flash with strict server-side JSON schema validation and zero fabricated medical or percentage risk claims. When AI is disabled, the core guidance remains 100% operational.
4. Honest Exposure Comparison: Uses duration-weighted local PM2.5 forecast shifts while clearly stating it does not predict personal inhaled dose.

Live application: https://airwise-promptwars-c6-897669266422.asia-south1.run.app
Public repository: https://github.com/pranavg21/airwise-promptwars-c6
Demo video: [VIDEO_LINK]

#PromptWars #Hack2Skill #GoogleCloud #GeminiAPI #CloudRun #AirQuality #FastAPI #ResponsibleAI #Python
