#!/usr/bin/env python3
"""
Unit tests for the Aasimar species implementation.
Tests all features, effects, and mechanics specific to the Aasimar species.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def aasimar_builder():
    """Fixture providing a fresh CharacterBuilder with Aasimar species setup"""
    builder = CharacterBuilder()
    builder.set_species("Aasimar")
    return builder


class TestAasimarSpecies:
    """Test Aasimar species implementation"""

    def test_aasimar_basic_traits(self, aasimar_builder):
        """Test basic aasimar species setup: name, speed, darkvision, languages"""
        char_data = aasimar_builder.character_data

        assert char_data["species"] == "Aasimar"
        assert char_data["speed"] == 30
        assert char_data["darkvision"] == 60

        languages = char_data["proficiencies"]["languages"]
        assert "Common" in languages
        assert "Celestial" not in languages

    def test_aasimar_resistances(self, aasimar_builder):
        """Test Celestial Resistance grants both Necrotic and Radiant"""
        char_data = aasimar_builder.character_data
        resistances = char_data["resistances"]

        assert "Necrotic" in resistances
        assert "Radiant" in resistances

    def test_aasimar_all_features_present(self, aasimar_builder):
        """Test that all 5 aasimar features are present in species features"""
        char_data = aasimar_builder.character_data
        species_features = char_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]

        assert "Celestial Resistance" in feature_names
        assert "Darkvision" in feature_names
        assert "Healing Hands" in feature_names
        assert "Light Bearer" in feature_names
        assert "Celestial Revelation" in feature_names

    def test_celestial_resistance_effects(self, aasimar_builder):
        """Test Celestial Resistance effects: both Necrotic and Radiant resistances"""
        char_data = aasimar_builder.character_data

        assert "Necrotic" in char_data["resistances"]
        assert "Radiant" in char_data["resistances"]

        applied_effects = getattr(aasimar_builder, "applied_effects", [])
        resistance_effects = [
            e for e in applied_effects
            if e["effect"]["type"] == "grant_damage_resistance"
        ]
        resistance_types = [e["effect"]["damage_type"] for e in resistance_effects]

        assert "Necrotic" in resistance_types
        assert "Radiant" in resistance_types

        # Both should come from Celestial Resistance
        for effect_data in resistance_effects:
            assert effect_data["source"] == "Celestial Resistance"
            assert effect_data["source_type"] == "species"

    def test_darkvision_effect(self, aasimar_builder):
        """Test Darkvision effect sets darkvision range to 60"""
        char_data = aasimar_builder.character_data
        assert char_data["darkvision"] == 60

        applied_effects = getattr(aasimar_builder, "applied_effects", [])
        darkvision_effects = [
            e for e in applied_effects
            if e["effect"]["type"] == "grant_darkvision"
        ]
        assert len(darkvision_effects) == 1
        assert darkvision_effects[0]["effect"]["range"] == 60
        assert darkvision_effects[0]["source"] == "Darkvision"

    def test_light_bearer_cantrip(self, aasimar_builder):
        """Test Light Bearer grants the Light cantrip in always_prepared spells"""
        char_data = aasimar_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        assert "Light" in always_prepared

    def test_healing_hands_feature(self, aasimar_builder):
        """Test Healing Hands is present with correct description keywords"""
        char_data = aasimar_builder.character_data
        species_features = char_data["features"]["species"]

        healing_hands = None
        for feature in species_features:
            if feature["name"] == "Healing Hands":
                healing_hands = feature
                break

        assert healing_hands is not None
        description = healing_hands["description"]
        assert "Magic action" in description or "Magic Action" in description.title()
        assert "d4" in description
        assert "Proficiency Bonus" in description
        assert "Long Rest" in description

    def test_celestial_revelation_feature(self, aasimar_builder):
        """Test Celestial Revelation feature and its 3 options"""
        char_data = aasimar_builder.character_data
        species_features = char_data["features"]["species"]

        revelation = None
        for feature in species_features:
            if feature["name"] == "Celestial Revelation":
                revelation = feature
                break

        assert revelation is not None
        description = revelation["description"]

        # Check key description elements
        assert "level 3" in description.lower() or "character level 3" in description.lower()
        assert "Bonus Action" in description
        assert "Long Rest" in description

    def test_celestial_revelation_options(self, aasimar_builder):
        """Test that Celestial Revelation has all 3 transformation options"""
        char_data = aasimar_builder.character_data
        species_features = char_data["features"]["species"]

        # Look for the options either as sub-features or within the feature description
        feature_names = [f["name"] for f in species_features]

        # The options may appear as separate features or be in the description
        revelation = None
        for feature in species_features:
            if feature["name"] == "Celestial Revelation":
                revelation = feature
                break

        assert revelation is not None

        # Check that the three options are referenced somewhere in the features
        all_text = " ".join(f.get("description", "") for f in species_features)
        all_names = [f["name"] for f in species_features]

        has_heavenly_wings = "Heavenly Wings" in all_text or "Heavenly Wings" in all_names
        has_inner_radiance = "Inner Radiance" in all_text or "Inner Radiance" in all_names
        has_necrotic_shroud = "Necrotic Shroud" in all_text or "Necrotic Shroud" in all_names

        assert has_heavenly_wings, "Heavenly Wings option should be present"
        assert has_inner_radiance, "Inner Radiance option should be present"
        assert has_necrotic_shroud, "Necrotic Shroud option should be present"

    def test_aasimar_with_class_integration(self, aasimar_builder):
        """Test aasimar traits persist when class is set"""
        aasimar_builder.set_class("Fighter", 1)
        char_data = aasimar_builder.character_data

        assert char_data["class"] == "Fighter"
        assert char_data["species"] == "Aasimar"
        assert char_data["level"] == 1

        # Aasimar traits should still be present
        assert char_data["darkvision"] == 60
        assert "Necrotic" in char_data["resistances"]
        assert "Radiant" in char_data["resistances"]
        assert "Light" in char_data["spells"]["always_prepared"]

        # Languages preserved
        languages = char_data["proficiencies"]["languages"]
        assert "Common" in languages
        assert "Celestial" not in languages

    def test_aasimar_applied_effects_summary(self, aasimar_builder):
        """Test applied_effects contains the right types from the right sources"""
        applied_effects = getattr(aasimar_builder, "applied_effects", [])

        # Should have 4 effects: 2 resistance, 1 darkvision, 1 cantrip
        assert len(applied_effects) == 4

        effect_types = [e["effect"]["type"] for e in applied_effects]
        assert effect_types.count("grant_damage_resistance") == 2
        assert "grant_darkvision" in effect_types
        assert "grant_cantrip" in effect_types

        # All effects should be species-sourced
        for effect_data in applied_effects:
            assert effect_data["source_type"] == "species"

    def test_aasimar_feature_descriptions(self, aasimar_builder):
        """Test that all aasimar features have non-empty descriptions"""
        char_data = aasimar_builder.character_data
        species_features = char_data["features"]["species"]

        for feature in species_features:
            assert "description" in feature
            assert len(feature["description"]) > 0
            assert isinstance(feature["description"], str)


class TestAasimarDataValidation:
    """Test aasimar species data file structure"""

    def test_aasimar_data_file_structure(self):
        """Test that aasimar data file has correct structure"""
        from pathlib import Path
        import json

        aasimar_file = Path("data/species/aasimar.json")
        assert aasimar_file.exists(), "Aasimar data file should exist"

        with open(aasimar_file, "r") as f:
            aasimar_data = json.load(f)

        assert aasimar_data["name"] == "Aasimar"
        assert aasimar_data["creature_type"] == "Humanoid"
        assert aasimar_data["size"] == "Medium or Small"
        assert aasimar_data["speed"] == 30
        assert aasimar_data["darkvision"] == 60

        # Check languages
        assert "Common" in aasimar_data["languages"]
        assert "Celestial" in aasimar_data["languages"]

        # Check all traits exist
        traits = aasimar_data["traits"]
        assert "Celestial Resistance" in traits
        assert "Darkvision" in traits
        assert "Healing Hands" in traits
        assert "Light Bearer" in traits
        assert "Celestial Revelation" in traits

    def test_aasimar_celestial_resistance_data(self):
        """Test Celestial Resistance trait data has correct effects"""
        from pathlib import Path
        import json

        with open(Path("data/species/aasimar.json"), "r") as f:
            aasimar_data = json.load(f)

        trait = aasimar_data["traits"]["Celestial Resistance"]
        assert "effects" in trait
        assert len(trait["effects"]) == 2

        effect_types = [(e["type"], e["damage_type"]) for e in trait["effects"]]
        assert ("grant_damage_resistance", "Necrotic") in effect_types
        assert ("grant_damage_resistance", "Radiant") in effect_types

    def test_aasimar_light_bearer_data(self):
        """Test Light Bearer trait data has grant_cantrip effect"""
        from pathlib import Path
        import json

        with open(Path("data/species/aasimar.json"), "r") as f:
            aasimar_data = json.load(f)

        trait = aasimar_data["traits"]["Light Bearer"]
        assert "effects" in trait
        assert len(trait["effects"]) == 1
        assert trait["effects"][0]["type"] == "grant_cantrip"
        assert trait["effects"][0]["spell"] == "Light"

    def test_aasimar_celestial_revelation_options(self):
        """Test Celestial Revelation trait has all 3 options in data"""
        from pathlib import Path
        import json

        with open(Path("data/species/aasimar.json"), "r") as f:
            aasimar_data = json.load(f)

        trait = aasimar_data["traits"]["Celestial Revelation"]
        assert "options" in trait
        options = trait["options"]
        assert "Heavenly Wings" in options
        assert "Inner Radiance" in options
        assert "Necrotic Shroud" in options

    def test_aasimar_species_loading(self):
        """Test that Aasimar species loads successfully"""
        builder = CharacterBuilder()
        result = builder.set_species("Aasimar")
        assert result is True
