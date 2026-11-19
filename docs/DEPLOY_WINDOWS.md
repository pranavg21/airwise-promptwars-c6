# Windows PowerShell — public GitHub and Render deployment

The previous challenge submission and the new AirWise project must be **different GitHub repositories**. Do not overwrite the earlier entry.

## First publish to GitHub

1. Extract the AirWise ZIP into a folder on your Windows PC, for example `C:\Projects\airwise-promptwars-c6`.
2. Open PowerShell in the extracted folder that contains `README.md`, `airwise`, `static` and `Dockerfile`.
3. Create an empty GitHub repository called `airwise-promptwars-c6`. It must be **Public**. **Do not** initialize GitHub with an extra README, .gitignore or license because these already exist in the source.
4. Run:

```powershell
git init -b main
git add .
git status --short
git commit -m "Build source-grounded AirWise Challenge 6 assistant"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/airwise-promptwars-c6.git
git push -u origin main
```

GitHub password-only HTTPS authentication is not supported. Use Git Credential Manager in the browser or an approved token if prompted; never paste credentials in a chat or commit.

5. Verify the repository from an **incognito browser** (without being signed into your GitHub account). Verify there is only a `main` branch and no API keys or large binaries.

## Host

1. Open https://dashboard.render.com and create a new Docker Web Service/Blueprint connected to the public repo.
2. The repo includes `render.yaml` and `Dockerfile`. Choose the appropriate compute plan. Free plans can cold-start; an always-on paid option is safer for judging.
3. Create environment variable `GEMINI_API_KEY` in Render's secure environment settings; set its value to a valid Google AI Studio key. Set `GEMINI_MODEL=gemini-3.5-flash-lite` if necessary.
4. Wait until Render reports deployment successful. Copy the real `https://....onrender.com` URL.
5. Verify `https://YOUR-DEPLOYMENT/api/health` returns `status: ok` and `ai_configured: true`.
6. Navigate to your app in incognito, choose Pune, generate with AI consent, ask a question and confirm a live response.
7. Record the <4 minute demonstration from the deployed URL, post it publicly/unlisted and open the video in incognito.

**Do not submit before these checks pass.** You have a limited number of evaluation attempts.
