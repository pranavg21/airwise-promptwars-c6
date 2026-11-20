# AirWise Demo Script (target 3:35–3:45, hard limit under 4:00)

## Before recording

- Record after the Gemini daily quota resets (midnight Pacific time; 1:30 PM IST in November). First check today's usage in Google AI Studio for the project that owns the deployed key. Other traffic on that project uses the same allowance.
- Use a fresh signed-out or private browser window on the public deployment: `https://airwise-promptwars-c6-897669266422.asia-south1.run.app`. Do not record on localhost.
- Open `/api/health` and confirm `status: ok` and `ai_configured: true`. This does not call Gemini. Do not make test AI calls before the take.
- Keep credentials, consoles and unrelated tabs off screen.
- Every value on screen is live. Do not read numbers from this script or from earlier rehearsals. Quote what the app shows during the take.

## Gemini budget for one take

Exactly three Gemini calls: one briefing and two questions. Everything before that runs with Gemini **off**.

Two UI behaviors decide the call count:

- Changing any sidebar setting, including the Gemini switch, clears the current plan. A new plan must be built.
- Typing in the city search clears the plan as well. Copy the community brief **before** the invalid-city test.

If a Gemini panel shows unavailable, do not retry immediately. Check the provider status and the project's quota in AI Studio first. Response time alone does not identify the cause.

## Shot list

| Time | On screen | Narration (adapt to the live values) |
|---|---|---|
| 0:00–0:20 | Open the app. Point to the "Read the scale correctly" notice and the model timestamp. | "AirWise helps families plan around winter smog. It uses modeled Open-Meteo and CAMS data and labels it as US AQI, not India's official CPCB index." |
| 0:20–0:45 | Type `Pune` in the city search, press Enter, select **Pune, Maharashtra, India**. Show current US AQI, PM2.5, PM10, the 24-hour chart and the data stamp. | "These readings come from the forecast service with their source and time. The language model never produces these numbers." |
| 0:45–1:10 | Confirm **Enable Gemini personalization is off**. Set persona **Family & household**, tick **Children in household**, priorities **School** and **Home**, budget **No new purchases**, outdoor hour **08:00**, outdoor minutes **90**. Click **Build my protection plan**. | "A Pune family with children, a ninety-minute outing at eight, a fixed school pickup and no budget for new equipment." |
| 1:10–1:40 | Show the **What if you shift?** card. Read the live percentage, the two times and the two PM2.5 averages. | "Over the whole ninety minutes, the later start has a lower average modeled outdoor PM2.5. That is a forecast difference, not a personal dose or a health-risk reduction." |
| 1:40–2:05 | Show the action cards. Open one **Why this matters** on the school or home card. Scroll to the sustainable swaps: no-flame alternatives and switching off a parked engine at pickup. | "Each action states its direct mechanism. No invented emission savings." |
| 2:05–2:20 | Click **Copy community brief** and paste it into a text editor. | "The public brief carries the city, source, time and a community action. Household health choices are excluded." |
| 2:20–2:35 | Type `Xyzzyville` in the city search and press Enter. Show "No matching city found". Click the **Pune** shortcut. | "An unknown city produces no invented location or readings." |
| 2:35–3:35 | Turn **Enable Gemini personalization** on. Click **Build my protection plan** (call 1). Pause on the briefing. Ask `How can we reduce idling at school pickup?` (call 2). Pause on the answer. Ask `We cannot buy a purifier. Which indoor smoke sources can we remove?` (call 3). Pause on the answer. | "With consent, Gemini turns the verified plan into a briefing and answers follow-up questions. The rule-based plan stays the source of truth if AI is unavailable." |
| 3:35–3:45 | Show the public GitHub repository and its passing Actions run. | "AirWise runs on Cloud Run; the code and tests are public." |

Keep questions free of digits so the model has no number to repeat; prose containing digits is rejected by the server.

Optional if time allows, before the Gemini segment and with Gemini still off: switch persona to **Outdoor worker**, rebuild, show the occupational card, then switch back to **Family & household**. This costs no Gemini calls but adds about 15 seconds.

## After recording

Trim to under 4:00 if needed. Upload as unlisted YouTube or a publicly shared Drive file and play it in a signed-out window before using the URL.
