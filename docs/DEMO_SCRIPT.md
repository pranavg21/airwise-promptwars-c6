# Under-four-minute live demo — shot-by-shot plan

**Record the real deployment in a fresh browser, not localhost. Type real values on-screen. Use actual GenAI API responses.** Do not display developer credentials or mock data as live.

| Timestamp | Show, without jump cuts that hide functionality | Narration / readable caption |
|---|---|---|
| **0:00–0:20** | App opens at its public HTTPS URL. Point out New Delhi, a timestamp, US AQI scale and model provenance. | "AirWise helps Indian households make cleaner everyday choices. The readings are CAMS model estimates, not government CPCB sensor measurements." |
| **0:20–0:48** | Type **Pune** in city search, select live geocode result, show AQI, PM2.5 and hourly chart update. | "Live geocoding and modeled air data drive the dashboard. Forecast data has a time and source." |
| **0:48–1:18** | Toggle **Children**, **Respiratory sensitivity**, priorities **School**, **Home**, **Commute**, set **45** outdoor minutes and select **No new purchases**. | "This is a family protecting a school run on a tight budget." |
| **1:18–1:46** | Click **Build my protection plan**. Show distinct action cards, open one "Why this matters" rationale, the forecast time-shift panel, and its limits. | "Deterministic health-aware rules and forecast comparisons decide the actions. No fabricated personal-risk percentages." |
| **1:46–2:12** | Scroll to sustainable swaps: less idling, source-free indoor alternative, fewer vehicle trips. Switch persona to Neighborhood group and rebuild; show changed recommendations. | "The app also reduces pollution at the source, with explicit mechanisms and inclusive community options." |
| **2:12–2:50** | Turn on **Gemini personalization** (key must be live), generate, point to actual `GEMINI GENERATED` state. Type **'How can our apartment help during winter smog?'** and submit; wait for a visibly different response. | "Gemini receives source-grounded facts with explicit consent. It's the personalization layer, not a substitute for readings or rules." |
| **2:50–3:10** | Search for an obviously nonexistent location and show no-results state; then return to Pune and rebuild the plan. Avoid pretending a provider outage is something it isn't. | "Bad inputs fail clearly. The app never invents air data." |
| **3:10–3:28** | Open "Why did AirWise recommend these actions?" and data sources, show accessible table. | "Every important recommendation has a trace, scientific reference, and limitation." |
| **3:28–3:43** | Click **Copy community brief**, paste into a visible document or text editor, check source is present but private profile not; briefly show print preview. | "Community messages can be shared without exposing family health selections." |
| **3:43–3:53** | Open public GitHub repo README, show test workflow/checks and one-branch repo. | "The project is tested, documented, and reproducibly deployed." |

**Total target duration: 3:53.** Maximum allowed per supplied rules: under four minutes; leave spare time for playback variance. Narration is optional, but the values, prompt and response must visibly change. If a live AI request fails, fix quota/deployment and record again. Do not insert fabricated output.

### Video quality checklist

- 1080p or above if possible, readable text zoom and visible cursor.
- Show typing, not pre-filled text, at least once; give judges time to read input.
- Show success and an edge case as separate workflows.
- No credentials, tokens, sensitive browser tabs or private user information.
- Keep under 4 minutes; edit only for clarity, without hiding nonfunctional behavior.
- Use unlisted YouTube or publicly available Google Drive with `Anyone with link` permission.
- Verify in incognito, including video playback before submitting.
