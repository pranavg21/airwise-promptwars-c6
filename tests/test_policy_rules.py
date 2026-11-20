"""Which recommendations each persona receives, in order, and that shared catalog entries stay fixed."""

import pytest
from pydantic import ValidationError

from airwise import catalog
from airwise.models import Profile
from airwise.policy import generate_policy

EXPECTED = {
    # persona: (card ids, swap ids) for an unhealthy forecast and default priorities (commute, home)
    "family": (["outdoor", "home", "commute"], ["trip-swap", "combustion-swap"]),
    "commuter": (["outdoor", "home", "commute"], ["trip-swap", "combustion-swap"]),
    "outdoor": (["outdoor", "home", "commute", "worker"], ["trip-swap", "combustion-swap"]),
    "community": (
        ["outdoor", "home", "commute", "community"],
        ["trip-swap", "combustion-swap", "shared-swap"],
    ),
}


@pytest.mark.parametrize("persona", EXPECTED)
def test_persona_cards_and_order(snapshot, persona):
    policy = generate_policy(snapshot, Profile(persona=persona))
    assert ([c.id for c in policy.cards], [s.id for s in policy.swaps]) == EXPECTED[persona]


def test_family_with_children_and_no_budget(snapshot):
    profile = Profile(children=True, budget="none", priorities=["school", "home"])
    policy = generate_policy(snapshot, profile)
    assert [c.id for c in policy.cards] == ["outdoor", "home", "school", "budget"]
    assert [s.id for s in policy.swaps] == ["combustion-swap", "pickup-swap"]
    assert policy.trace[1] == "AQI 182 is in a US AQI category of concern."


def test_universal_swap_only_when_nothing_else_matches(snapshot):
    policy = generate_policy(snapshot, Profile(persona="outdoor", priorities=["exercise"]))
    assert [s.id for s in policy.swaps] == ["universal-swap"]


def test_catalog_entries_cannot_be_modified():
    with pytest.raises(ValidationError):
        catalog.HOME.title = "Changed"


def test_moderate_air_with_sensitive_household(snapshot):
    moderate = snapshot.model_copy(update={"us_aqi": 75.0})
    policy = generate_policy(moderate, Profile(older_adult=True, priorities=[]))
    assert policy.headline == catalog.HEADLINE_SENSITIVE
    assert policy.cards[0] == catalog.OUTDOOR_SENSITIVE
    assert catalog.TRACE_SENSITIVE_MODERATE in policy.trace
