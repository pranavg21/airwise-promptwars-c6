from airwise.models import Profile
from airwise.policy import classify, find_lower_hour, generate_policy, upcoming_hours


def test_aqi_boundaries():
    cases = [
        (None, "Unavailable"),
        (0, "Good"),
        (50, "Good"),
        (51, "Moderate"),
        (100, "Moderate"),
        (101, "Unhealthy for sensitive groups"),
        (150, "Unhealthy for sensitive groups"),
        (151, "Unhealthy"),
        (200, "Unhealthy"),
        (201, "Very unhealthy"),
        (300, "Very unhealthy"),
        (301, "Hazardous"),
    ]
    for value, name in cases:
        assert classify(value)[0] == name


def test_sensitive_children_receive_school_specific_action(snapshot):
    policy = generate_policy(snapshot, Profile(children=True, priorities=["school", "home"]))
    assert policy.sensitive
    assert {c.id for c in policy.cards} >= {"school", "home", "outdoor"}
    assert policy.concern == "high"
    assert all(c.reference.startswith("https://") for c in policy.cards)


def test_no_budget_prefers_nonpurchase_actions(snapshot):
    policy = generate_policy(snapshot, Profile(budget="none"))
    assert "budget" in [c.id for c in policy.cards]


def test_community_is_not_just_a_family_clone(snapshot):
    family = generate_policy(snapshot, Profile(persona="family"))
    community = generate_policy(snapshot, Profile(persona="community"))
    assert "community" in [c.id for c in community.cards]
    assert "community" not in [c.id for c in family.cards]


def test_respiratory_sensitivity_requires_not_fake_medical_treatment(snapshot):
    policy = generate_policy(snapshot, Profile(respiratory_sensitivity=True))
    med = next(c for c in policy.cards if c.id == "medical")
    assert "clinician" in med.detail and "cannot" in med.detail


def test_compare_hours_uses_pm25_not_qi_as_exposure(snapshot):
    best, shift = find_lower_hour(snapshot, Profile(start_hour=8, outdoor_minutes=45))
    assert best.time == "2026-11-17T15:00"
    assert shift is not None
    assert shift.original_pm25 == 180
    assert shift.alternate_pm25 == 46
    assert round(shift.relative_difference_pct, 1) == 74.4
    assert "Not a personal dose" in shift.caution


def test_no_fabricated_shift_for_zero_time_or_unimproved_air(snapshot):
    _, shift = find_lower_hour(snapshot, Profile(start_hour=8, outdoor_minutes=0))
    assert shift is None


def test_only_future_hours_are_compared(snapshot):
    hours = upcoming_hours(snapshot)
    assert len(hours) == 24
    assert hours[0].time == "2026-11-17T06:00"


def test_missing_current_aqi_does_not_get_relabelled(snapshot):
    no_current = snapshot.model_copy(update={"us_aqi": None})
    p = generate_policy(no_current, Profile())
    assert p.concern == "unknown"
    assert p.category == "Unavailable"


def test_sustainable_swaps_have_explicit_impact_and_zero_fabricated_numbers(snapshot):
    policy = generate_policy(snapshot, Profile(children=True, priorities=["commute", "home", "school"]))
    assert {"trip-swap", "combustion-swap", "pickup-swap"} <= {s.id for s in policy.swaps}
    for swap in policy.swaps:
        assert swap.detail and swap.why
        assert "%" not in swap.why


def test_no_commute_family_persona_still_has_no_flame_swap(snapshot):
    policy = generate_policy(snapshot, Profile(persona="family", priorities=[]))
    assert [s.id for s in policy.swaps] == ["combustion-swap"]


def test_outdoor_worker_gets_occupational_guidance(snapshot):
    policy = generate_policy(snapshot, Profile(persona="outdoor", priorities=[]))
    ids = {c.id for c in policy.cards}
    assert "worker" in ids
    assert "universal-swap" in {s.id for s in policy.swaps}


def test_hazardous_outlook_is_not_described_as_safe(snapshot):
    s = snapshot.model_copy(update={"us_aqi": 350})
    policy = generate_policy(s, Profile())
    assert policy.category == "Hazardous"
    assert policy.concern == "very_high"
    assert "safe" not in policy.headline.lower()
