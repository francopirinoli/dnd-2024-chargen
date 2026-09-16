"""Tests for the Point Buy ability score system."""

import pytest
from modules.ability_scores import (
    POINT_BUY_COSTS,
    POINT_BUY_TOTAL,
    POINT_BUY_MIN,
    POINT_BUY_MAX,
    validate_point_buy,
)
from modules.character_builder import CharacterBuilder


# ── validate_point_buy unit tests ─────────────────────────────────────────────

def _scores(**kwargs):
    """Build a full scores dict with all abilities, defaulting to POINT_BUY_MIN."""
    abilities = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
    base = {a: POINT_BUY_MIN for a in abilities}
    base.update(kwargs)
    return base


def test_all_min_is_valid():
    """All scores at 8 spends 0 points — always valid."""
    valid, msg = validate_point_buy(_scores())
    assert valid is True
    assert msg == ""


def test_exactly_27_points_valid():
    """Spending exactly 27 points is valid (15,15,15,8,8,8 = 9+9+9 = 27)."""
    scores = _scores(Strength=15, Dexterity=15, Constitution=15)
    valid, msg = validate_point_buy(scores)
    assert valid is True


def test_one_over_budget_invalid():
    """Exceeding 27 points is rejected."""
    # 15+15+15+9 = 9+9+9+1 = 28 > 27
    scores = _scores(Strength=15, Dexterity=15, Constitution=15, Intelligence=9)
    valid, msg = validate_point_buy(scores)
    assert valid is False
    assert "exceed" in msg.lower() or "limit" in msg.lower()


def test_score_below_min_invalid():
    """Score below minimum (8) is rejected."""
    scores = _scores(Strength=7)
    valid, msg = validate_point_buy(scores)
    assert valid is False
    assert "Strength" in msg


def test_score_above_max_invalid():
    """Score above maximum (15) is rejected."""
    scores = _scores(Wisdom=16)
    valid, msg = validate_point_buy(scores)
    assert valid is False
    assert "Wisdom" in msg


def test_missing_ability_invalid():
    """Missing an ability returns invalid."""
    abilities = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom"]
    scores = {a: POINT_BUY_MIN for a in abilities}  # Charisma missing
    valid, msg = validate_point_buy(scores)
    assert valid is False
    assert "Charisma" in msg


def test_cost_table_values():
    """Spot-check the published D&D 2024 cost values."""
    assert POINT_BUY_COSTS[8] == 0
    assert POINT_BUY_COSTS[9] == 1
    assert POINT_BUY_COSTS[13] == 5
    assert POINT_BUY_COSTS[14] == 7
    assert POINT_BUY_COSTS[15] == 9


# ── CharacterBuilder integration tests ───────────────────────────────────────

@pytest.fixture
def fighter_point_buy():
    """A Fighter built using point buy (15,14,13,12,10,8 — same total as standard array but via PB)."""
    # 15+14+13+12+10+8 costs 9+7+5+4+2+0 = 27 — exactly within budget
    builder = CharacterBuilder()
    builder.apply_choices({
        "character_name": "Gawain",
        "level": 1,
        "species": "Human",
        "class": "Fighter",
        "subclass": "Champion",
        "background": "Soldier",
        "ability_scores": {
            "Strength": 15,
            "Dexterity": 14,
            "Constitution": 13,
            "Intelligence": 12,
            "Wisdom": 10,
            "Charisma": 8,
        },
        "background_bonuses": {"Strength": 2, "Constitution": 1},
        "ability_scores_method": "point_buy",
    })
    return builder


def test_point_buy_character_ability_scores(fighter_point_buy):
    """Base ability scores are stored correctly when set via point buy."""
    char = fighter_point_buy.to_character()
    scores = char["ability_scores"]
    # After background bonuses: STR 15+2=17, CON 13+1=14
    assert scores["Strength"] == 17
    assert scores["Constitution"] == 14
    assert scores["Dexterity"] == 14


def test_point_buy_method_choice_stores_correctly():
    """apply_choice('ability_scores_method', 'point_buy') does not error and marks method."""
    builder = CharacterBuilder()
    builder.set_class("Fighter", 1)
    result = builder.apply_choice("ability_scores_method", "point_buy")
    assert result is True


def test_point_buy_apply_scores_then_method():
    """Scores set via 'ability_scores' key work independently of method marker."""
    builder = CharacterBuilder()
    builder.set_class("Wizard", 1)
    scores = _scores(Intelligence=15, Constitution=14, Dexterity=13, Wisdom=12, Charisma=10, Strength=8)
    builder.apply_choice("ability_scores", scores)
    builder.apply_choice("ability_scores_method", "point_buy")

    char = builder.to_character()
    assert char["ability_scores"]["Intelligence"] == 15
    assert char["ability_scores"]["Strength"] == 8
