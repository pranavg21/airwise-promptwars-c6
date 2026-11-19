"""Exercise the real HTTP handlers with a controlled environmental provider."""
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from airwise import main
from airwise.data import ProviderError
from airwise.models import Location, Snapshot


class PlanWorkflow(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        loc = Location(name="Pune", latitude=18.52, longitude=73.86)
        self.body = {"location": loc.model_dump(), "profile": {"children": True}, "ai_consent": True}
        snapshot = Snapshot(location=loc, model_time="2026-11-19T08:00", retrieved_at="2026-11-19T02:30Z",
                            timezone="Asia/Kolkata", us_aqi=180)
        self.air = AsyncMock(return_value=snapshot)
        self.enterContext(patch.object(main, "fetch_air", self.air))
        self.enterContext(patch.object(main, "gate", main.RateGate()))

    async def test_quota_preserves_deterministic_plan(self):
        with patch.object(main.gate, "check", side_effect=[True, False]), patch.object(main, "personalize") as ai:
            response = await self.client.post("/api/plan", json=self.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ai_status"], "unavailable")
        self.assertIn("school", [c["id"] for c in response.json()["policy"]["cards"]])
        ai.assert_not_called()

    async def test_no_consent_keeps_question_off_provider(self):
        response = await self.client.post("/api/ask", json={**self.body, "ai_consent": False, "question": "School run?"})
        self.assertEqual(response.status_code, 400)
        self.air.assert_not_awaited()

    async def test_outage_has_no_advisory_payload(self):
        self.air.side_effect = ProviderError("offline")
        response = await self.client.post("/api/plan", json=self.body)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("policy", response.json())

    async def test_preferences_reach_gemini_only_with_consent(self):
        from airwise.models import AiResponse
        mock = AsyncMock(return_value=AiResponse(summary="Combine errands.", steps=["Avoid idling.", "Check the forecast."],
                                                 rationale="Fewer trips can reduce emissions."))
        with patch.object(main, "personalize", mock):
            for consent in [False, True]:
                result = await self.client.post("/api/plan", json={**self.body, "ai_consent": consent})
                self.assertEqual(result.json()["ai_status"], "generated" if consent else "not_requested")
        mock.assert_awaited_once()
        self.assertTrue(mock.await_args.args[1].children)
