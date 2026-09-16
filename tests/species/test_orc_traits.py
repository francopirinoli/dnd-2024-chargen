#!/usr/bin/env python3
"""
Unit tests for the Orc species implementation.
Tests all features, effects, and mechanics specific to the Orc species.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def orc_builder():
    """Fixture providing a fresh CharacterBuilder with Orc species setup"""
    builder = CharacterBuilder()
    builder.set_species("Orc")
    return builder


class TestOrcSpecies:
    """Test Orc species implementation"""

    def test_orc_basic_traits(self, orc_builder):
        """Test basic orc species setup: name, speed, size, darkvision, creature type"""
        char_data = orc_builder.character_data

        assert char_data["species"] == "Orc"
        assert char_data["speed"] == 30
        assert char_data["darkvision"] == 120

        species_data = char_data["species_data"]
        assert species_data["size"] == "Medium"
        assert species_data["creature_type"] == "Humanoid"

    def test_orc_languages(self, orc_builder):
        """Test Orc baseline language is Common before language choices."""
        char_data = orc_builder.character_data
        languages = char_data["proficiencies"]["languages"]

        assert "Common" in languages
        assert "Orc" not in languages

    def test_orc_all_features_present(self, orc_builder):
        """Test that all 3 orc features are present"""
        char_data = orc_builder.character_data
        species_features = char_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]

        assert "Adrenaline Rush" in feature_names
        assert "Darkvision" in feature_names
        assert "Relentless Endurance" in feature_names
        assert len(species_features) == 3

    def test_orc_feature_descriptions_nonempty(self, orc_builder):
        """Test that all orc feature descriptions are non-empty"""
        char_data = orc_builder.character_data
        species_features = char_data["features"]["species"]

        for feature in species_features:
            assert feature["description"], f"Feature '{feature['name']}' has empty description"

    def test_orc_darkvision_effect(self, orc_builder):
        """Test Darkvision effect: grant_darkvision with range 120"""
        char_data = orc_builder.character_data
        assert char_data["darkvision"] == 120

        applied_effects = getattr(orc_builder, "applied_effects", [])
        darkvision_effects = [
            e for e in applied_effects
            if e["effect"].get("type") == "grant_darkvision"
        ]
        assert len(darkvision_effects) == 1
        assert darkvision_effects[0]["effect"]["range"] == 120

    def test_orc_exactly_one_applied_effect(self, orc_builder):
        """Test that only 1 effect is applied (Darkvision's grant_darkvision)"""
        applied_effects = getattr(orc_builder, "applied_effects", [])
        assert len(applied_effects) == 1
        assert applied_effects[0]["effect"]["type"] == "grant_darkvision"

    def test_adrenaline_rush_description(self, orc_builder):
        """Test Adrenaline Rush description contains key D&D terms"""
        char_data = orc_builder.character_data
        species_features = char_data["features"]["species"]

        feature = next(f for f in species_features if f["name"] == "Adrenaline Rush")
        desc = feature["description"]

        assert "Dash" in desc
        assert "Bonus Action" in desc
        assert "Temporary Hit Points" in desc
        assert "Proficiency Bonus" in desc
        assert "Short or Long Rest" in desc

    def test_relentless_endurance_description(self, orc_builder):
        """Test Relentless Endurance description contains key D&D terms"""
        char_data = orc_builder.character_data
        species_features = char_data["features"]["species"]

        feature = next(f for f in species_features if f["name"] == "Relentless Endurance")
        desc = feature["description"]

        assert "0 Hit Points" in desc
        assert "1 Hit Point" in desc
        assert "Long Rest" in desc

    def test_orc_no_resistances(self, orc_builder):
        """Test that Orcs have no damage resistances"""
        char_data = orc_builder.character_data
        assert char_data["resistances"] == []

    def test_orc_no_condition_immunities(self, orc_builder):
        """Test that Orcs have no condition immunities"""
        char_data = orc_builder.character_data
        assert char_data["condition_immunities"] == []

    def test_orc_with_class_preserves_traits(self, orc_builder):
        """Test that setting a class preserves Orc traits and darkvision"""
        orc_builder.set_class("Barbarian", 1)
        char_data = orc_builder.character_data

        assert char_data["species"] == "Orc"
        assert char_data["darkvision"] == 120
        assert char_data["speed"] == 30

        species_features = char_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]
        assert "Adrenaline Rush" in feature_names
        assert "Darkvision" in feature_names
        assert "Relentless Endurance" in feature_names

        languages = char_data["proficiencies"]["languages"]
        assert "Common" in languages
        assert "Orc" not in languages
