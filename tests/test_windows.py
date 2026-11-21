"""Regression cases for advisories whose duration crosses an hourly boundary."""

import unittest

from airwise.ai import AiUnavailableError, validate_brief_text
from airwise.models import Hour, Location, Profile, Snapshot
from airwise.policy import find_lower_hour


def compare(pm, aqi, duration):
    hours = [
        Hour(time=f"2026-11-19T{8 + i:02}:00", pm2_5=p, us_aqi=a)
        for i, (p, a) in enumerate(zip(pm, aqi, strict=True))
    ]
    snapshot = Snapshot(
        location=Location(name="Pune", latitude=18.52, longitude=73.86),
        retrieved_at="2026-11-19T08:00Z",
        model_time=hours[0].time,
        timezone="Asia/Kolkata",
        hourly=hours,
    )
    return find_lower_hour(snapshot, Profile(start_hour=8, outdoor_minutes=duration))


def whole_day(pm, start_hour, duration):
    """A 24-hour forecast from local midnight with a flat AQI, so only PM2.5 decides."""
    hours = [Hour(time=f"2026-11-21T{hour:02}:00", pm2_5=value, us_aqi=80) for hour, value in enumerate(pm)]
    snapshot = Snapshot(
        location=Location(name="Pune", latitude=18.52, longitude=73.86),
        retrieved_at="2026-11-20T18:30Z",
        model_time=hours[0].time,
        timezone="Asia/Kolkata",
        hourly=hours,
    )
    return find_lower_hour(snapshot, Profile(start_hour=start_hour, outdoor_minutes=duration))


def pre_dawn_clean_day():
    """Cleanest at 04:00-05:59; a smaller daytime dip at 09:00-10:59; otherwise 60 µg/m³."""
    pm = [60.0] * 24
    pm[4] = pm[5] = 10.0
    pm[9] = pm[10] = 40.0
    return pm


class WakingHourTests(unittest.TestCase):
    def test_daytime_plan_is_not_moved_before_dawn(self):
        _, shift = whole_day(pre_dawn_clean_day(), 6, 120)
        self.assertEqual(shift.recommended_time, "2026-11-21T09:00")
        self.assertEqual(shift.alternate_pm25, 40)

    def test_plan_outside_waking_hours_may_move_anywhere(self):
        _, shift = whole_day(pre_dawn_clean_day(), 2, 60)
        self.assertEqual(shift.recommended_time, "2026-11-21T04:00")

    def test_alternative_must_end_by_the_evening_limit(self):
        pm = [60.0] * 24
        pm[21] = 10.0
        self.assertTrue(whole_day(pm, 8, 60)[1].recommended_time.endswith("21:00"))  # ends at 22:00
        pm[22] = 10.0
        # 21:00 + 90 minutes would end after 22:00, so the best window that ends in time starts at 20:00.
        self.assertTrue(whole_day(pm, 8, 90)[1].recommended_time.endswith("20:00"))

    def test_no_daytime_improvement_means_no_suggestion(self):
        pm = [60.0] * 24
        pm[3] = 5.0
        self.assertIsNone(whole_day(pm, 8, 60)[1])


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
            with self.subTest(prose=prose), self.assertRaises(AiUnavailableError):
                validate_brief_text(prose)

    def test_pollutant_names_allowed(self):
        validate_brief_text("PM2.5 and PM₁₀ are modeled outdoor concentrations.")
