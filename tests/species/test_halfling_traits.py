#!/usr/bin/env python3
"""
Unit tests for the Halfling species implementation.
Tests all features, effects, and mechanics specific to the Halfling species.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def halfling_builder():
    """Fixture providing a fresh CharacterBuilder with Halfling species setup"""
    builder = CharacterBuilder()
    builder.set_species("Halfling")
    return builder


class TestHalflingBasicTraits:
    """Test basic Halfling species properties"""

    def test_halfling_species_name(self, halfling_builder):
        char_data = halfling_builder.character_data
        assert char_data["species"] == "Halfling"

    def test_halfling_speed(self, halfling_builder):
        char_data = halfling_builder.character_data
        assert char_data["speed"] == 30

    def test_halfling_size_small(self, halfling_builder):
        species_data = halfling_builder.character_data["species_data"]
        assert species_data["size"] == "Small"

    def test_halfling_no_darkvision(self, halfling_builder):
        char_data = halfling_builder.character_data
        assert char_data["darkvision"] == 0

    def test_halfling_creature_type(self, halfling_builder):
        species_data = halfling_builder.character_data["species_data"]
        assert species_data["creature_type"] == "Humanoid"


class TestHalflingLanguages:
    """Test Halfling language proficiencies"""

    def test_halfling_languages(self, halfling_builder):
        char_data = halfling_builder.character_data
        languages = char_data["proficiencies"]["languages"]
        assert "Common" in languages
        assert "Halfling" not in languages

    def test_halfling_language_count(self, halfling_builder):
        char_data = halfling_builder.character_data
        languages = char_data["proficiencies"]["languages"]
        assert len(languages) == 1


class TestHalflingFeatures:
    """Test that all Halfling features are present with correct descriptions"""

    def test_all_features_present(self, halfling_builder):
        char_data = halfling_builder.character_data
        species_features = char_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]

        assert "Brave" in feature_names
        assert "Halfling Nimbleness" in feature_names
        assert "Luck" in feature_names
        assert "Naturally Stealthy" in feature_names

    def test_feature_count(self, halfling_builder):
        char_data = halfling_builder.character_data
        species_features = char_data["features"]["species"]
        assert len(species_features) == 4

    def test_all_features_have_descriptions(self, halfling_builder):
        char_data = halfling_builder.character_data
        species_features = char_data["features"]["species"]
        for feature in species_features:
            assert feature.get("description"), f"{feature['name']} has no description"
            assert len(feature["description"]) > 0

    def test_brave_description(self, halfling_builder):
        char_data = halfling_builder.character_data
        species_features = char_data["features"]["species"]
        brave = next(f for f in species_features if f["name"] == "Brave")
        assert "Frightened" in brave["description"]

    def test_halfling_nimbleness_description(self, halfling_builder):
        char_data = halfling_builder.character_data
        species_features = char_data["features"]["species"]
        nimbleness = next(
            f for f in species_features if f["name"] == "Halfling Nimbleness"
        )
        assert "size larger" in nimbleness["description"]

    def test_luck_description(self, halfling_builder):
        char_data = halfling_builder.character_data
        species_features = char_data["features"]["species"]
        luck = next(f for f in species_features if f["name"] == "Luck")
        assert "reroll" in luck["description"]
        assert "d20" in luck["description"]
        assert "D20 Test" in luck["description"]

    def test_naturally_stealthy_description(self, halfling_builder):
        char_data = halfling_builder.character_data
        species_features = char_data["features"]["species"]
        stealthy = next(
            f for f in species_features if f["name"] == "Naturally Stealthy"
        )
        assert "Hide" in stealthy["description"]


class TestHalflingBraveEffect:
    """Test Brave trait's grant_save_advantage effect"""

    def test_brave_save_advantage_applied(self, halfling_builder):
        applied_effects = getattr(halfling_builder, "applied_effects", [])
        save_advantage_effect = None
        for effect_data in applied_effects:
            effect = effect_data["effect"]
            if effect.get("type") == "grant_save_advantage":
                save_advantage_effect = effect
                break

        assert save_advantage_effect is not None

    def test_brave_save_advantage_condition(self, halfling_builder):
        applied_effects = getattr(halfling_builder, "applied_effects", [])
        save_advantage_effect = None
        for effect_data in applied_effects:
            effect = effect_data["effect"]
            if effect.get("type") == "grant_save_advantage":
                save_advantage_effect = effect
                break

        assert save_advantage_effect is not None
        assert save_advantage_effect["condition"] == "Frightened"

    def test_brave_save_advantage_display(self, halfling_builder):
        applied_effects = getattr(halfling_builder, "applied_effects", [])
        save_advantage_effect = None
        for effect_data in applied_effects:
            effect = effect_data["effect"]
            if effect.get("type") == "grant_save_advantage":
                save_advantage_effect = effect
                break

        assert save_advantage_effect is not None
        assert save_advantage_effect["display"] == "Advantage vs Frightened condition"

    def test_exactly_one_applied_effect(self, halfling_builder):
        """Only Brave has effects; the other 3 traits are descriptive only"""
        applied_effects = getattr(halfling_builder, "applied_effects", [])
        assert len(applied_effects) == 1


class TestHalflingNoResistancesOrImmunities:
    """Test that Halflings have no damage resistances or condition immunities"""

    def test_no_resistances(self, halfling_builder):
        char_data = halfling_builder.to_character()
        assert char_data.get("resistances", []) == []

    def test_no_condition_immunities(self, halfling_builder):
        char_data = halfling_builder.to_character()
        assert char_data.get("condition_immunities", []) == []


class TestHalflingClassIntegration:
    """Test that setting a class preserves Halfling species traits"""

    def test_class_preserves_halfling_traits(self):
        builder = CharacterBuilder()
        builder.set_species("Halfling")
        builder.apply_choices(
            {
                "character_name": "Test Halfling",
                "level": 1,
                "species": "Halfling",
                "class": "Rogue",
                "background": "Criminal",
                "ability_scores": {
                    "Strength": 8,
                    "Dexterity": 16,
                    "Constitution": 12,
                    "Intelligence": 10,
                    "Wisdom": 14,
                    "Charisma": 13,
                },
                "background_bonuses": {"Dexterity": 2, "Wisdom": 1},
            }
        )
        char_data = builder.to_character()

        # Species traits preserved
        assert char_data["species"] == "Halfling"
        assert char_data["speed"] == 30
        assert char_data["darkvision"] == 0

        # Languages preserved
        languages = char_data["proficiencies"]["languages"]
        assert "Common" in languages
        assert "Halfling" not in languages

        # Features preserved
        species_features = char_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]
        assert "Brave" in feature_names
        assert "Halfling Nimbleness" in feature_names
        assert "Luck" in feature_names
        assert "Naturally Stealthy" in feature_names

        # Brave effect still applied
        applied_effects = getattr(builder, "applied_effects", [])
        save_adv = [
            e
            for e in applied_effects
            if e["effect"].get("type") == "grant_save_advantage"
            and e["effect"].get("condition") == "Frightened"
        ]
        assert len(save_adv) >= 1
