"""Regression cases for advisories whose duration crosses an hourly boundary."""
import unittest

from airwise.ai import AiUnavailable, validate_brief_text
from airwise.models import Hour, Location, Profile, Snapshot
from airwise.policy import find_lower_hour


def compare(pm, aqi, duration):
    hours = [Hour(time=f"2026-11-19T{8+i:02}:00", pm2_5=p, us_aqi=a)
             for i, (p, a) in enumerate(zip(pm, aqi))]
    snapshot = Snapshot(location=Location(name="Pune", latitude=18.52, longitude=73.86),
                        retrieved_at="2026-11-19T08:00Z", model_time=hours[0].time,
                        timezone="Asia/Kolkata", hourly=hours)
    return find_lower_hour(snapshot, Profile(start_hour=8, outdoor_minutes=duration))


class WindowTests(unittest.TestCase):
    def test_partial_last_hour_has_proportional_weight(self):
        best, shift = compare([100, 100, 10, 40], [100, 100, 80, 90], 90)
        self.assertEqual(shift.alternate_pm25, 20)
        self.assertEqual(shift.relative_difference_pct, 80)
        self.assertEqual(best.time, shift.recommended_time)

    def test_short_improvement_can_reverse_over_full_activity(self):
        pm, aqi = [60, 60, 1, 200], [80, 80, 70, 80]
        self.assertTrue(compare(pm, aqi, 30)[1].recommended_time.endswith("10:00"))
        self.assertTrue(compare(pm, aqi, 120)[1].recommended_time.endswith("09:00"))

    def test_missing_last_hour_cannot_win(self):
        self.assertIsNone(compare([80, 80, None], [80, 80, 20], 90)[1])

    def test_worse_peak_aqi_cannot_win(self):
        self.assertIsNone(compare([80, 10], [80, 120], 45)[1])

    def test_incomplete_planned_activity_has_no_comparison(self):
        self.assertIsNone(compare([40], [50], 120)[1])

    def test_ungrounded_digits_blocked_in_english_and_hindi(self):
        for prose in ["AQI is 37 today", "आज ४८ प्रतिशत बेहतर", "68 percent", "20 ppm"]:
            with self.subTest(prose=prose), self.assertRaises(AiUnavailable):
                validate_brief_text(prose)

    def test_pollutant_names_allowed(self):
        validate_brief_text("PM2.5 and PM₁₀ are modeled outdoor concentrations.")
