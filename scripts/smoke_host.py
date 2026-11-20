"""Verify a deployed AirWise instance. --ai makes three real Gemini requests."""

import argparse
from urllib.parse import urlsplit

import httpx


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check(base, run_ai):
    parsed = urlsplit(base)
    require(
        parsed.scheme == "https" and parsed.hostname and not (parsed.username or parsed.password),
        "Supply a public HTTPS URL without credentials.",
    )
    with httpx.Client(base_url=base.rstrip("/"), timeout=60, follow_redirects=False) as client:
        home = client.get("/").raise_for_status()
        require("AirWise" in home.text, "Unexpected homepage")
        health = client.get("/api/health").raise_for_status().json()
        require(health["status"] == "ok", "Health check failed")
        if run_ai:
            require(health["ai_configured"], "Key missing in hosted environment")
        cities = client.get("/api/geo", params={"q": "Pune"}).raise_for_status().json()["results"]
        city = next((c for c in cities if c["name"] == "Pune" and c["country"] == "India"), None)
        require(city, "Geocoding did not return Pune, India")
        body = {
            "location": city,
            "profile": {"children": True, "budget": "none", "priorities": ["school", "home"]},
            "ai_consent": run_ai,
        }
        plan = client.post("/api/plan", json=body).raise_for_status().json()
        snapshot = plan["snapshot"]
        require(snapshot["location"] == city and snapshot["model_time"], "City or timestamp missing")
        require(snapshot["us_aqi"] is not None and snapshot["pm2_5"] is not None, "Missing current values")
        require(
            any(h["us_aqi"] is not None and h["time"] >= snapshot["model_time"] for h in snapshot["hourly"]),
            "No upcoming hourly AQI",
        )
        require(
            "NOT CPCB" in snapshot["scale"] and plan["policy"]["swaps"],
            "Missing scale or sustainable actions",
        )
        print("PASS Pune search, current readings, forecast and plan at", snapshot["model_time"])
        if run_ai:
            require(plan["ai_status"] == "generated" and plan["ai"], "Gemini briefing failed")
            answers = []
            for question in [
                "How should we handle school pickup?",
                "What indoor smoke sources can we remove?",
            ]:
                reply = client.post("/api/ask", json={**body, "question": question}).raise_for_status().json()
                require(reply["ai_status"] == "generated" and reply["ai"]["steps"], "Missing Gemini answer")
                answers.append(reply["ai"]["summary"])
                print(question, answers[-1], sep="\n")
            require(answers[0] != answers[1], "Both summaries identical; review the responses")
            print("PASS briefing and two distinct summaries. Read each answer for relevance.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--ai", action="store_true")
    args = parser.parse_args()
    try:
        check(args.url, args.ai)
    except (ValueError, KeyError, httpx.HTTPError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")
