"""Follow-up question endpoint: success, provider failures and upstream quota rejection.

Gemini is never called. The real `personalize` adapter runs against an in-process
mock transport so the HTTP status handling is exercised end to end.
"""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from airwise import ai, main
from airwise.data import ProviderError
from airwise.models import AiResponse, Hour, Location, Snapshot

QUOTA_BODY = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                        "message": "Quota exceeded for metric: generate_requests_per_model_per_day"}}
ANSWER = {"summary": "Switch off the engine while waiting at the gate.",
          "steps": ["Coordinate shared pickups with nearby families.", "Wait away from queues of idling vehicles."],
          "rationale": "Less idling means less exhaust where children gather."}
REAL_CLIENT = httpx.AsyncClient


def gemini_returning(response: httpx.Response, seen: list[httpx.Request]):
    """Build an AsyncClient factory whose requests are answered in-process."""
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return response
    return lambda *args, **kwargs: REAL_CLIENT(transport=httpx.MockTransport(handler))


class AskEndpoint(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = REAL_CLIENT(transport=httpx.ASGITransport(app=main.app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        loc = Location(name="Pune", country="India", latitude=18.52, longitude=73.86)
        hours = [Hour(time=f"2026-11-20T{h:02}:00", us_aqi=120, pm2_5=40) for h in range(8, 12)]
        self.snapshot = Snapshot(location=loc, model_time="2026-11-20T08:00", retrieved_at="2026-11-20T02:30Z",
                                 timezone="Asia/Kolkata", us_aqi=120, pm2_5=40, hourly=hours)
        self.body = {"location": loc.model_dump(), "ai_consent": True,
                     "question": "How can we reduce idling at school pickup?",
                     "profile": {"children": True, "budget": "none", "priorities": ["school", "home"]}}
        self.air = AsyncMock(return_value=self.snapshot)
        self.enterContext(patch.object(main, "fetch_air", self.air))
        self.enterContext(patch.object(main, "gate", main.RateGate()))
        self.enterContext(patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-key", "GEMINI_MODEL": "gemini-2.5-flash"}))

    async def test_answer_is_returned_with_source_labels(self):
        mock = AsyncMock(return_value=AiResponse(**ANSWER))
        with patch.object(main, "personalize", mock):
            response = await self.client.post("/api/ask", json=self.body)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["ai_status"], "generated")
        self.assertEqual(data["ai"]["summary"], ANSWER["summary"])
        self.assertEqual(data["as_of"], "2026-11-20T08:00")
        self.assertIn("NOT CPCB", data["scale"])
        self.assertEqual(mock.await_args.kwargs["question"], self.body["question"])
        self.assertEqual(mock.await_args.args[1].budget, "none")

    async def test_real_adapter_success_through_endpoint(self):
        seen: list[httpx.Request] = []
        envelope = {"candidates": [{"content": {"parts": [{"text": json.dumps(ANSWER)}]}}]}
        with patch.object(ai.httpx, "AsyncClient", side_effect=gemini_returning(httpx.Response(200, json=envelope), seen)):
            response = await self.client.post("/api/ask", json=self.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ai"]["steps"], ANSWER["steps"])
        self.assertEqual(len(seen), 1)
        self.assertTrue(seen[0].url.path.endswith("/gemini-2.5-flash:generateContent"))
        sent = json.loads(seen[0].content)
        self.assertIn(self.body["question"], sent["contents"][0]["parts"][0]["text"])

    async def test_upstream_quota_rejection_returns_503_without_leaking_details(self):
        seen: list[httpx.Request] = []
        with patch.object(ai.httpx, "AsyncClient", side_effect=gemini_returning(httpx.Response(429, json=QUOTA_BODY), seen)):
            response = await self.client.post("/api/ask", json=self.body)
        self.assertEqual(response.status_code, 503)
        self.assertIn("temporarily unavailable", response.json()["detail"])
        for secret_or_upstream in ("test-only-key", "RESOURCE_EXHAUSTED", "Quota"):
            self.assertNotIn(secret_or_upstream, response.text)
        self.assertEqual(len(seen), 1)

    async def test_upstream_quota_rejection_keeps_rule_based_plan(self):
        seen: list[httpx.Request] = []
        with patch.object(ai.httpx, "AsyncClient", side_effect=gemini_returning(httpx.Response(429, json=QUOTA_BODY), seen)):
            response = await self.client.post("/api/plan", json={k: v for k, v in self.body.items() if k != "question"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["ai_status"], "unavailable")
        self.assertIsNone(data["ai"])
        self.assertIn("school", [c["id"] for c in data["policy"]["cards"]])

    async def test_truncated_generation_is_unavailable_not_partial(self):
        seen: list[httpx.Request] = []
        envelope = {"candidates": [{"finishReason": "MAX_TOKENS",
                                    "content": {"parts": [{"text": '{"summary": "Switch off the eng'}]}}]}
        with patch.object(ai.httpx, "AsyncClient", side_effect=gemini_returning(httpx.Response(200, json=envelope), seen)):
            response = await self.client.post("/api/ask", json=self.body)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("Switch off", response.text)

    async def test_forecast_outage_never_reaches_gemini(self):
        self.air.side_effect = ProviderError("offline")
        with patch.object(main, "personalize") as mock:
            response = await self.client.post("/api/ask", json=self.body)
        self.assertEqual(response.status_code, 503)
        self.assertIn("forecast", response.json()["detail"])
        mock.assert_not_called()

    async def test_unconfigured_deployment_reports_it(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}), patch.object(main, "personalize") as mock:
            response = await self.client.post("/api/ask", json=self.body)
        self.assertEqual(response.status_code, 503)
        self.assertIn("not configured", response.json()["detail"])
        mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
