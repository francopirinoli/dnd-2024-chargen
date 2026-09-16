#!/usr/bin/env python3
"""
Unit tests for the Dragonborn species implementation.
Tests all features, effects, and mechanics specific to the Dragonborn species.
"""

import json
from pathlib import Path

import pytest

from modules.character_builder import CharacterBuilder


@pytest.fixture
def dragonborn_builder():
    """Fixture providing a fresh CharacterBuilder with Dragonborn species setup."""
    builder = CharacterBuilder()
    builder.set_species("Dragonborn")
    return builder


class TestDragonbornSpecies:
    """Test Dragonborn species implementation."""

    def test_dragonborn_basic_traits(self, dragonborn_builder):
        """Test basic dragonborn species setup."""
        char_data = dragonborn_builder.character_data

        assert char_data["species"] == "Dragonborn"
        assert char_data["speed"] == 30
        assert char_data["darkvision"] == 60

        languages = char_data["proficiencies"]["languages"]
        assert "Common" in languages
        assert "Draconic" not in languages

    def test_dragonborn_features_present(self, dragonborn_builder):
        """Test that all dragonborn features are present."""
        char_data = dragonborn_builder.character_data
        species_features = char_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]

        assert "Draconic Ancestry" in feature_names
        assert "Breath Weapon" in feature_names
        assert "Damage Resistance" in feature_names
        assert "Darkvision" in feature_names
        assert "Draconic Flight" in feature_names
        assert len(feature_names) == 5

    def test_darkvision_feature(self, dragonborn_builder):
        """Test Darkvision feature implementation."""
        char_data = dragonborn_builder.character_data

        assert char_data["darkvision"] == 60

        species_features = char_data["features"]["species"]
        darkvision_feature = next(
            f for f in species_features if f["name"] == "Darkvision"
        )
        assert "60 feet" in darkvision_feature["description"]

    def test_draconic_ancestry_choice_mechanics(self, dragonborn_builder):
        """Test Draconic Ancestry trait has correct choice structure."""
        species_data = dragonborn_builder.character_data.get("species_data", {})
        ancestry_trait = species_data["traits"]["Draconic Ancestry"]

        assert ancestry_trait["type"] == "choice"
        assert ancestry_trait["choices"]["type"] == "select_single"

        options = ancestry_trait["choices"]["source"]["options"]
        assert len(options) == 10

        expected_options = [
            "Black (Acid)",
            "Blue (Lightning)",
            "Brass (Fire)",
            "Bronze (Lightning)",
            "Copper (Acid)",
            "Gold (Fire)",
            "Green (Poison)",
            "Red (Fire)",
            "Silver (Cold)",
            "White (Cold)",
        ]
        for option in expected_options:
            assert option in options

    def test_damage_resistance_with_red_ancestry(self):
        """Test damage resistance resolves to Fire for Red (Fire) ancestry."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Dragonborn",
            "level": 1,
            "species": "Dragonborn",
            "class": "Fighter",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 16, "Dexterity": 12, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 10, "Charisma": 13,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
            "species_trait_Draconic Ancestry": "Red (Fire)",
        })
        character = builder.to_character()

        assert "Fire" in character["resistances"]

    def test_damage_resistance_with_green_ancestry(self):
        """Test damage resistance resolves to Poison for Green (Poison) ancestry."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Dragonborn",
            "level": 1,
            "species": "Dragonborn",
            "class": "Fighter",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 16, "Dexterity": 12, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 10, "Charisma": 13,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
            "species_trait_Draconic Ancestry": "Green (Poison)",
        })
        character = builder.to_character()

        assert "Poison" in character["resistances"]

    def test_damage_resistance_with_silver_ancestry(self):
        """Test damage resistance resolves to Cold for Silver (Cold) ancestry."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Dragonborn",
            "level": 1,
            "species": "Dragonborn",
            "class": "Fighter",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 16, "Dexterity": 12, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 10, "Charisma": 13,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
            "species_trait_Draconic Ancestry": "Silver (Cold)",
        })
        character = builder.to_character()

        assert "Cold" in character["resistances"]

    def test_damage_resistance_description_substitution(self):
        """Test Damage Resistance description has correct damage type substituted."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Dragonborn",
            "level": 1,
            "species": "Dragonborn",
            "class": "Fighter",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 16, "Dexterity": 12, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 10, "Charisma": 13,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
            "species_trait_Draconic Ancestry": "Red (Fire)",
        })
        character = builder.to_character()

        dr_feature = next(
            f for f in character["features"]["species"]
            if f["name"] == "Damage Resistance"
        )
        assert "Fire" in dr_feature["description"]
        assert "{damage_type}" not in dr_feature["description"]

    def test_breath_weapon_description_substitution(self):
        """Test Breath Weapon description has damage type substituted from ancestry."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Dragonborn",
            "level": 1,
            "species": "Dragonborn",
            "class": "Fighter",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 16, "Dexterity": 12, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 10, "Charisma": 13,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
            "species_trait_Draconic Ancestry": "Red (Fire)",
        })
        character = builder.to_character()

        bw_feature = next(
            f for f in character["features"]["species"]
            if f["name"] == "Breath Weapon"
        )
        assert "Fire" in bw_feature["description"]
        assert "{damage_type}" not in bw_feature["description"]

    def test_draconic_flight_text_only(self, dragonborn_builder):
        """Test Draconic Flight is a text-only feature with correct keywords."""
        char_data = dragonborn_builder.character_data
        species_features = char_data["features"]["species"]

        flight_feature = next(
            f for f in species_features if f["name"] == "Draconic Flight"
        )
        description = flight_feature["description"]

        assert "Bonus Action" in description
        assert "Fly Speed" in description
        assert "10 minutes" in description
        assert "Long Rest" in description
        assert "level 5" in description

    def test_dragonborn_no_resistance_without_choice(self, dragonborn_builder):
        """Test that resistances are empty when no ancestry is chosen."""
        assert dragonborn_builder.character_data["resistances"] == []

    def test_dragonborn_effects_without_choice(self, dragonborn_builder):
        """Test applied effects before ancestry choice is made."""
        applied_effects = dragonborn_builder.applied_effects

        effect_types = [e["effect"]["type"] for e in applied_effects]
        assert "grant_darkvision" in effect_types
        assert "grant_damage_resistance" in effect_types

        # Darkvision effect should be fully resolved
        darkvision_effect = next(
            e for e in applied_effects
            if e["effect"]["type"] == "grant_darkvision"
        )
        assert darkvision_effect["effect"]["range"] == 60
        assert darkvision_effect["source"] == "Darkvision"
        assert darkvision_effect["source_type"] == "species"

    def test_dragonborn_effects_with_choice(self):
        """Test applied effects after ancestry choice resolves resistance."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Dragonborn",
            "level": 1,
            "species": "Dragonborn",
            "class": "Fighter",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 16, "Dexterity": 12, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 10, "Charisma": 13,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
            "species_trait_Draconic Ancestry": "Red (Fire)",
        })
        character = builder.to_character()

        species_effects = [
            e for e in character.get("effects", [])
            if e.get("source_type") == "species"
        ]
        effect_types = [e["type"] for e in species_effects]
        assert "grant_darkvision" in effect_types
        assert "grant_damage_resistance" in effect_types

    def test_dragonborn_feature_descriptions_non_empty(self, dragonborn_builder):
        """Test that all dragonborn features have non-empty descriptions."""
        species_features = dragonborn_builder.character_data["features"]["species"]

        for feature in species_features:
            assert "description" in feature
            assert isinstance(feature["description"], str)
            assert len(feature["description"]) > 0

    def test_dragonborn_with_fighter_integration(self, dragonborn_builder):
        """Test dragonborn integration with Fighter class."""
        dragonborn_builder.set_class("Fighter", 1)
        char_data = dragonborn_builder.character_data

        assert char_data["class"] == "Fighter"
        assert char_data["species"] == "Dragonborn"
        assert char_data["level"] == 1

        # Dragonborn traits should persist
        assert char_data["darkvision"] == 60
        languages = char_data["proficiencies"]["languages"]
        assert "Common" in languages
        assert "Draconic" not in languages

        feature_names = [f["name"] for f in char_data["features"]["species"]]
        assert "Draconic Ancestry" in feature_names
        assert "Breath Weapon" in feature_names

    def test_draconic_ancestry_feature_shows_choice(self):
        """Test that chosen ancestry appears in the Draconic Ancestry feature name."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Dragonborn",
            "level": 1,
            "species": "Dragonborn",
            "class": "Fighter",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 16, "Dexterity": 12, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 10, "Charisma": 13,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
            "species_trait_Draconic Ancestry": "Red (Fire)",
        })
        character = builder.to_character()

        ancestry_features = [
            f for f in character["features"]["species"]
            if f["name"].startswith("Draconic Ancestry")
        ]
        assert len(ancestry_features) == 1
        assert "Red (Fire)" in ancestry_features[0]["name"]


class TestDragonbornSpeciesValidation:
    """Test dragonborn species data validation and edge cases."""

    def test_dragonborn_data_file_structure(self):
        """Test that dragonborn data file has correct structure."""
        dragonborn_file = Path("data/species/dragonborn.json")
        assert dragonborn_file.exists(), "Dragonborn data file should exist"

        with open(dragonborn_file, "r") as f:
            data = json.load(f)

        assert data["name"] == "Dragonborn"
        assert "description" in data
        assert data["creature_type"] == "Humanoid"
        assert data["size"] == "Medium"
        assert data["size_description"] == "about 5-7 feet tall"
        assert data["speed"] == 30
        assert "traits" in data
        assert "languages" in data

    def test_dragonborn_data_all_traits_present(self):
        """Test that all 5 traits are present in data file."""
        with open("data/species/dragonborn.json", "r") as f:
            data = json.load(f)

        traits = data["traits"]
        assert "Draconic Ancestry" in traits
        assert "Breath Weapon" in traits
        assert "Damage Resistance" in traits
        assert "Darkvision" in traits
        assert "Draconic Flight" in traits
        assert len(traits) == 5

    def test_dragonborn_data_damage_resistance_effects(self):
        """Test that Damage Resistance trait has effects with grant_damage_resistance."""
        with open("data/species/dragonborn.json", "r") as f:
            data = json.load(f)

        dr_trait = data["traits"]["Damage Resistance"]
        assert "effects" in dr_trait
        assert len(dr_trait["effects"]) == 1

        effect = dr_trait["effects"][0]
        assert effect["type"] == "grant_damage_resistance"
        assert "damage_type_from_choice" in effect
        assert effect["damage_type_from_choice"] == "Draconic Ancestry"

    def test_dragonborn_data_darkvision_effects(self):
        """Test that Darkvision trait has effects with grant_darkvision."""
        with open("data/species/dragonborn.json", "r") as f:
            data = json.load(f)

        dv_trait = data["traits"]["Darkvision"]
        assert "effects" in dv_trait
        assert len(dv_trait["effects"]) == 1

        effect = dv_trait["effects"][0]
        assert effect["type"] == "grant_darkvision"
        assert effect["range"] == 60

    def test_dragonborn_data_ancestry_choices(self):
        """Test that Draconic Ancestry has correct choice structure."""
        with open("data/species/dragonborn.json", "r") as f:
            data = json.load(f)

        ancestry = data["traits"]["Draconic Ancestry"]
        assert ancestry["type"] == "choice"
        assert ancestry["choices"]["type"] == "select_single"
        assert ancestry["choices"]["count"] == 1

        options = ancestry["choices"]["source"]["options"]
        assert len(options) == 10

    def test_dragonborn_data_breath_weapon_has_substitutions(self):
        """Test that Breath Weapon has choice_substitutions."""
        with open("data/species/dragonborn.json", "r") as f:
            data = json.load(f)

        bw_trait = data["traits"]["Breath Weapon"]
        assert "choice_substitutions" in bw_trait
        assert bw_trait["choice_substitutions"]["damage_type"] == "Draconic Ancestry"

    def test_dragonborn_data_draconic_flight_is_string(self):
        """Test that Draconic Flight is a text-only string (no effects)."""
        with open("data/species/dragonborn.json", "r") as f:
            data = json.load(f)

        flight_trait = data["traits"]["Draconic Flight"]
        assert isinstance(flight_trait, str)

    def test_dragonborn_data_languages(self):
        """Test that languages are Common and Draconic."""
        with open("data/species/dragonborn.json", "r") as f:
            data = json.load(f)

        assert data["languages"] == ["Common", "Draconic"]

    def test_dragonborn_species_loading_error_handling(self):
        """Test error handling when loading species."""
        builder = CharacterBuilder()

        result = builder.set_species("InvalidSpecies")
        assert result is False

        result = builder.set_species("Dragonborn")
        assert result is True

    def test_dragonborn_set_species_idempotent(self):
        """Test setting Dragonborn species twice doesn't duplicate features."""
        builder = CharacterBuilder()
        builder.set_species("Dragonborn")
        builder.set_species("Dragonborn")

        feature_names = [
            f["name"] for f in builder.character_data["features"]["species"]
        ]
        assert feature_names.count("Darkvision") == 1
        assert feature_names.count("Breath Weapon") == 1
