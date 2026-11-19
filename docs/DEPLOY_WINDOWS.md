# Windows PowerShell — Public GitHub and Google Cloud Run Deployment

The previous challenge submission and the new AirWise project must be **different services and repositories**.

## 1. Publish to GitHub

1. Source root: `C:\Users\21pra\Downloads\AirWise-Challenge6\airwise-challenge6`
2. Remote: `https://github.com/pranavg21/airwise-promptwars-c6.git`
3. Branch: `main` (strictly single branch)
4. Verify repository from an incognito window: public visibility, ~79 KiB size (< 10 MB limit).

## 2. Deploy to Google Cloud Run

```powershell
gcloud run deploy airwise-promptwars-c6 `
  --source . `
  --region asia-south1 `
  --project venueflow-maps `
  --platform managed `
  --allow-unauthenticated `
  --port 8080 `
  --service-account airwise-runner@venueflow-maps.iam.gserviceaccount.com `
  --set-secrets GEMINI_API_KEY=airwise-gemini-api-key:latest `
  --set-env-vars GEMINI_MODEL=gemini-2.5-flash `
  --min-instances 0 `
  --max-instances 2
```

1. Secret `airwise-gemini-api-key` is securely injected from Secret Manager into container memory; no secret is exposed in client-side code, Git, or logs.
2. Verified live URL: `https://airwise-promptwars-c6-897669266422.asia-south1.run.app`
3. Health check: `/api/health` returns `status: ok` and `ai_configured: true`.
4. Run live smoke test: `python scripts/smoke_host.py https://airwise-promptwars-c6-897669266422.asia-south1.run.app --ai`.
