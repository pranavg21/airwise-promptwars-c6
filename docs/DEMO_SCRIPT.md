# AirWise Demo Script (Target: 3:35 — 3:45)

**Recording Rules:**
- Record in a fresh browser window at the live public Cloud Run deployment: `https://airwise-promptwars-c6-897669266422.asia-south1.run.app`
- Do NOT record on localhost.
- Keep total duration between 3:30 and 3:45 (strictly under 4 minutes).
- Keep private credentials, API keys, and unrelated browser tabs off-screen.

---

### Shot-by-Shot Walkthrough (Pune Household Story)

| Timestamp | Exact Actions on Screen | Narration / Audio Script |
|---|---|---|
| **0:00 – 0:25** | Open `https://airwise-promptwars-c6-897669266422.asia-south1.run.app`. Highlight the dashboard header, model timestamp, and explicit **US EPA AQI** notice distinguishing it from India's CPCB scale. | "AirWise is a source-grounded air quality decision assistant built for PromptWars Challenge 6. It combines verified Open-Meteo and Copernicus CAMS atmospheric models with deterministic protection logic and server-side Google Gemini." |
| **0:25 – 0:50** | Click the city search box. Type `Pune`. Select `Pune, Maharashtra, India` from the live geocoding dropdown. Show the live US AQI (140), PM2.5 (41 µg/m³), PM10, Ozone, and 24-hour hourly trend chart update. | "We search for Pune. Live geocoding pulls current CAMS modeled pollution readings and a 72-hour forecast directly from external APIs. The language model never invents or paints these numbers." |
| **0:50 – 1:20** | In Household Profile: Select **Family**, check **Children**, choose priorities **School** and **Home**, select **No new purchases** budget, and set **90 outdoor minutes** starting at 8:00 AM. Click **Generate Protection Plan**. | "Meet a Pune family planning around winter smog. They have school-age children, need 90 minutes outdoors, and have zero budget for expensive air purifiers. Our deterministic rules engine personalizes guidance based on their exact vulnerabilities." |
| **1:20 – 1:55** | Scroll through the generated plan. Point to: 1) `[outdoor]` Strenuous exposure reduction, 2) `[school]` School run guidance, 3) `[home]` Cleaner-air room, 4) `[budget]` No-purchase habits first. Point out the **Timing Shift Comparison** (e.g., shifting from 8:00 AM to 3:00 PM shows a modeled 27.6% PM2.5 drop, with an explicit caveat that it is modeled particulate difference, not personal dose). | "Notice the four targeted action cards and our 24-hour timing shift. The system identifies a lower PM2.5 window tomorrow afternoon, but honestly disclaims that this is a modeled atmospheric difference, not a guarantee of safe exposure." |
| **1:55 – 2:30** | Scroll to **Sustainable Swaps**: Show `[combustion-swap]` (replacing incense/candles with non-burning options) and `[pickup-swap]` (turning off idling engines at school pickup). Explain each swap's direct physical mechanism. | "AirWise promotes emission reduction at the source. Instead of inventing fake CO2 savings percentages, it explains the direct physical mechanism behind eliminating indoor burning and turning off vehicle idling." |
| **2:30 – 3:05** | Check the **Enable Gemini Personalization** toggle. Show the live Gemini-generated briefing. Then in the follow-up box, type: `How can we reduce idling at school pickup?` Click Ask. Read the structured response. Then type a second question: `We cannot buy a purifier. Which indoor smoke sources can we remove?` Click Ask and observe the distinctly different, relevant advice. | "We opt into Gemini. Hosted server-side on Google Cloud Run with Gemini 2.5 Flash, it produces grounded briefs and answers contextual questions without fabricating sensor data or medical percentage claims." |
| **3:05 – 3:25** | In city search, type `Xyzzyville`. Press Enter. Show the clean `No matching cities found` state. Show that the dashboard does NOT invent a fake location or crash. Then click back to `Pune`. Click **Copy Community Brief**, paste into Notepad to show that private household medical flags are stripped from public notices. Briefly open **Print View**. | "Negative test: invalid searches fail gracefully without hallucinated data. When sharing a community bulletin, private household health details are stripped automatically." |
| **3:25 – 3:40** | Switch persona to **Outdoor Worker**. Click Generate. Show the cards immediately change to occupational safety (`[worker]`). Conclude by showing the public GitHub repository on branch `main` with passing CI. | "Changing personas instantly adapts the advice from family routines to occupational safety. AirWise is fully deployed on Cloud Run, open-source on GitHub, and verified for Challenge 6." |

**Total Duration:** ~3:38 (well within the 3:30–3:45 target, under 4-minute maximum).
