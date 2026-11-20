# Security and data-handling model

## Data minimization

No users are asked to register or log in. The application has no persistent profile database, analytics scripts, advertising trackers or location-permission requests. It accepts only a chosen city and coarse coordinates, profile priorities and optional follow-up question. The modeled air API gets the coordinates; Google Gemini receives a minimised city/profile/fact summary **only after the user opts in**. Hosting vendors and Google can retain service metadata under their own applicable terms. Users should not submit personal health details beyond the high-level toggles if they prefer not to send them to Gemini.

## Threats, mitigations and open risks

| Threat | Implemented mitigation | Open limitation |
|---|---|---|
| API key stolen from browser bundle | `GEMINI_API_KEY` only in server environment; no client Gemini SDK | Hosting environment operator has access; protect deployment access |
| SSRF through arbitrary geocode/AQI URL | Fixed HTTPS upstream host constants, no redirect following, strict coordinate validation | External provider compromise is outside application control |
| XSS via city names or AI output | `textContent`, `createElement`, escaped JSON serialization; CSP disallows inline scripts and inline styles | Browser extensions and hosting-level injections remain outside scope |
| Downgrade, framing and cross-origin leaks | HSTS, `X-Frame-Options: DENY`, `frame-ancestors 'none'`, COOP and CORP `same-origin` on every response (`airwise/security.py`, `tests/test_security.py`) | HSTS takes effect only over HTTPS |
| Cross-site request forgery against the API | API writes require `application/json`; requests a browser marks `Sec-Fetch-Site: cross-site` are rejected with 403 | Non-browser clients do not send fetch metadata; rate limits still apply |
| Vulnerable dependencies | Exact pins; CI fails on any `pip-audit` or `npm audit` finding. FastAPI 0.162.0 and Starlette 1.9.0 replace versions with published Starlette advisories | New advisories can appear after a release; rerun the audits before redeploying |
| Malformed AI structured output | Strict JSON schema prompt plus server-side Pydantic length/shape validation | A structurally valid model answer may still be incorrect; vet content and ground only in provided facts |
| Unwanted Gemini use | Opt-in boolean enforced on both routes, clear `ai_status` statuses | Users must understand provider data-processing terms |
| Prompt injection through user question | Explicit untrusted-data instruction and bounded, audited context | LLM prompt-injection risk cannot be eliminated by prompts alone |
| Cost/quota abuse | 12 AI calls/10 min per client address per process, with `Retry-After`; JSON request size limit; 22-second total AI budget; identical AI requests reuse a cached answer for 15 minutes | The binding limit is the Gemini daily quota of the key-owning Google Cloud project, shared by all traffic on that project. The in-memory gate is not global across replicas, and behind a proxy the visible client address may be shared by many visitors. Add gateway limits, budgets and alerts for larger audiences |
| Private data in third-party logs | No app-level profile persistence; Gemini failures are logged only as model, failure reason and HTTP status, never the key, prompt, question or reply (`tests/test_ai_resilience.py`) | Infrastructure may log request metadata; observe provider retention policies |
| Inaccurate pollution information | No fabricated readings, explicit model provenance and US vs India index distinction | Forecasts may disagree with measured station values; official alerts take priority |
| Elevated medical-risk advice | No diagnosis or treatment changes, sensitivity-based rules, safety disclaimer | Professional medical care not replaced |

## Secrets checklist

1. Never paste secrets in a LinkedIn post, video, Git commit, `.env.example` or frontend source.
2. Use the host secret store only (Secret Manager on Cloud Run); limit deployment access.
3. Verify `git grep 'AIzaSy'` (if it matches a real key, revoke the key before publishing).
4. Run `python scripts/audit_repo.py`; also inspect Git history before submission.
5. Apply server side API quotas, monitor costs, rotate exposed credentials.
6. Do not expose the API via a proxy that permits arbitrary CORS origins or forwards private metadata in the URL.

## Safety disclaimer

AirWise offers general pollution avoidance and source reduction guidance. It is not a medical device, an official emergency-alert service, a neighborhood monitoring station, or a substitute for local public-health authorities.

## Reporting concerns

Report confirmed issues privately to the repository maintainer rather than creating a public issue with personal data or secrets.
