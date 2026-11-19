# Security and data-handling model

## Data minimization

No users are asked to register or log in. The application has no persistent profile database, analytics scripts, advertising trackers or location-permission requests. It accepts only a chosen city and coarse coordinates, profile priorities and optional follow-up question. The modeled air API gets the coordinates; Google Gemini receives a minimised city/profile/fact summary **only after the user opts in**. Hosting vendors and Google can retain service metadata under their own applicable terms. Users should not submit personal health details beyond the high-level toggles if they prefer not to send them to Gemini.

## Threats, mitigations and open risks

| Threat | Implemented mitigation | Open limitation |
|---|---|---|
| API key stolen from browser bundle | `GEMINI_API_KEY` only in server environment; no client Gemini SDK | Hosting environment operator has access; protect deployment access |
| SSRF through arbitrary geocode/AQI URL | Fixed HTTPS upstream host constants, no redirect following, strict coordinate validation | External provider compromise is outside application control |
| XSS via city names or AI output | `textContent`, `createElement`, escaped JSON serialization; CSP disallows inline scripts | Browser extensions and hosting-level injections remain outside scope |
| Malformed AI structured output | Strict JSON schema prompt plus server-side Pydantic length/shape validation | A structurally valid model answer may still be incorrect; vet content and ground only in provided facts |
| Unwanted Gemini use | Opt-in boolean enforced on both routes, clear `ai_status` statuses | Users must understand provider data-processing terms |
| Prompt injection through user question | Explicit untrusted-data instruction and bounded, audited context | LLM prompt-injection risk cannot be eliminated by prompts alone |
| Cost/quota abuse | 12 AI calls/10 min/IP/process; JSON request size limit, 18-second upstream timeout | In-memory rate gate is not global across multiple replicas; add gateway limits and budgets |
| Private data in third-party logs | No app-level profile persistence, no raw profile logs in application code | Infrastructure may log request metadata; observe provider retention policies |
| Inaccurate pollution information | No fabricated readings, explicit model provenance and US vs India index distinction | Forecasts may disagree with measured station values; official alerts take priority |
| Elevated medical-risk advice | No diagnosis or treatment changes, sensitivity-based rules, safety disclaimer | Professional medical care not replaced |

## Secrets checklist

1. Never paste secrets in a LinkedIn post, video, Git commit, `.env.example` or frontend source.
2. Use Render/host secret environment configuration only; limit deployment access.
3. Verify `git grep 'AIzaSy'` (if it matches a real key, revoke the key before publishing).
4. Run `python scripts/audit_repo.py`; also inspect Git history before submission.
5. Apply server side API quotas, monitor costs, rotate exposed credentials.
6. Do not expose the API via a proxy that permits arbitrary CORS origins or forwards private metadata in the URL.

## Safety disclaimer

AirWise offers general pollution avoidance and source reduction guidance. It is not a medical device, an official emergency-alert service, a neighborhood monitoring station, or a substitute for local public-health authorities.

## Reporting concerns

Report confirmed issues privately to the repository maintainer rather than creating a public issue with personal data or secrets.
