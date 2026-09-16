#!/usr/bin/env python3
"""
Tests for supplement feats ASI and sub-choice generation and application.
Verifies that Death Knight Initiate and other supplement feats provide
the expected ability choices and that selecting them properly applies ability bonuses.
"""

import pytest
from modules.character_builder import CharacterBuilder


class TestSupplementFeatASI:
    """Tests for ASI sub-choices on supplement feats."""

    def test_death_knight_initiate_has_asi_choices(self):
        """Death Knight Initiate must define ability choices between Strength and Charisma."""
        builder = CharacterBuilder()
        feat_data = builder._load_feat_data("Death Knight Initiate")
        assert feat_data is not None
        choices = feat_data.get("choices", [])
        ability_choice = next((c for c in choices if c.get("name") == "ability"), None)
        assert ability_choice is not None
        assert set(ability_choice["source"]["options"]) == {"Strength", "Charisma"}

    def test_death_knight_initiate_applies_asi_bonus(self):
        """Selecting Death Knight Initiate and picking Charisma increases Charisma score by 1."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Villain",
            "class": "Paladin",
            "level": 4,
            "species": "Human",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 15, "Dexterity": 10, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 12, "Charisma": 14,
            },
            "class_feat_4": "Death Knight Initiate",
            "class_feat_4_ability": "Charisma",
        })
        char = builder.to_character()
        assert char["abilities"]["charisma"]["score"] == 15

    def test_harbinger_of_doom_has_three_asi_choices(self):
        """Harbinger of Doom offers Strength, Constitution, or Charisma."""
        builder = CharacterBuilder()
        feat_data = builder._load_feat_data("Harbinger of Doom")
        assert feat_data is not None
        choices = feat_data.get("choices", [])
        ability_choice = next((c for c in choices if c.get("name") == "ability"), None)
        assert ability_choice is not None
        assert set(ability_choice["source"]["options"]) == {"Strength", "Constitution", "Charisma"}

    def test_boon_of_the_bandit_king_offers_all_six_abilities(self):
        """Epic Boon of the Bandit King allows increasing any one ability score."""
        builder = CharacterBuilder()
        feat_data = builder._load_feat_data("Boon of the Bandit King")
        assert feat_data is not None
        choices = feat_data.get("choices", [])
        ability_choice = next((c for c in choices if c.get("name") == "ability"), None)
        assert ability_choice is not None
        assert len(ability_choice["source"]["options"]) == 6

    def test_dragonscarred_has_both_asi_and_resistance_choices(self):
        """Dragonscarred offers Constitution/Charisma ASI and damage resistance choice."""
        builder = CharacterBuilder()
        feat_data = builder._load_feat_data("Dragonscarred")
        assert feat_data is not None
        choices = feat_data.get("choices", [])
        choice_names = [c.get("name") for c in choices]
        assert "ability" in choice_names
        assert "damage_resistance" in choice_names

    def test_harper_agent_has_instrument_choice(self):
        """Harper Agent offers a musical instrument tool choice."""
        builder = CharacterBuilder()
        feat_data = builder._load_feat_data("Harper Agent")
        assert feat_data is not None
        choices = feat_data.get("choices", [])
        choice_names = [c.get("name") for c in choices]
        assert "musical_instrument" in choice_names

    def test_synthesizer_fallback_for_synthetic_feat(self):
        """Even if a feat data dictionary has no choices, _synthesize_feat_asi synthesizes them."""
        raw_feat = {
            "name": "Custom Feat",
            "benefits": [
                "Ability Score Increase: Increase your Wisdom or Intelligence score by 1, to a maximum of 20."
            ]
        }
        synthesized = CharacterBuilder._synthesize_feat_asi(raw_feat)
        assert "choices" in synthesized
        assert synthesized["choices"][0]["name"] == "ability"
        assert set(synthesized["choices"][0]["source"]["options"]) == {"Wisdom", "Intelligence"}
        assert "choice_effects" in synthesized
