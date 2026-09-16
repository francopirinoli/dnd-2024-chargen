#!/usr/bin/env python3
"""
Unit tests for the Dwarf species implementation.
Tests all features, effects, and mechanics specific to the Dwarf species.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def dwarf_builder():
    """Fixture providing a fresh CharacterBuilder with Dwarf species setup"""
    builder = CharacterBuilder()
    builder.set_species("Dwarf")
    return builder


class TestDwarfSpecies:
    """Test Dwarf species implementation"""

    def test_dwarf_basic_traits(self, dwarf_builder):
        """Test basic dwarf species setup"""
        char_data = dwarf_builder.character_data

        # Check basic species properties
        assert char_data["species"] == "Dwarf"
        assert char_data["speed"] == 30
        assert char_data["darkvision"] == 120

        # Check languages
        languages = char_data["proficiencies"]["languages"]
        assert "Common" in languages
        assert "Dwarvish" not in languages

        # Check resistances from Dwarven Resilience
        resistances = char_data["resistances"]
        assert "Poison" in resistances

    def test_dwarf_features_present(self, dwarf_builder):
        """Test that all dwarf features are present"""
        char_data = dwarf_builder.character_data
        species_features = char_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]

        # All dwarf features should be present
        assert "Darkvision" in feature_names
        assert "Dwarven Resilience" in feature_names
        assert "Dwarven Toughness" in feature_names
        assert "Stonecunning" in feature_names

    def test_darkvision_feature(self, dwarf_builder):
        """Test Darkvision feature implementation"""
        char_data = dwarf_builder.character_data

        # Check darkvision range is set correctly
        assert char_data["darkvision"] == 120

        # Check feature description
        species_features = char_data["features"]["species"]
        darkvision_feature = None
        for feature in species_features:
            if feature["name"] == "Darkvision":
                darkvision_feature = feature
                break

        assert darkvision_feature is not None
        description = darkvision_feature["description"]
        assert "Darkvision" in description
        assert "120 feet" in description

    def test_dwarven_resilience_effects(self, dwarf_builder):
        """Test Dwarven Resilience effects application"""
        char_data = dwarf_builder.character_data

        # Check poison resistance
        assert "Poison" in char_data["resistances"]

        # Check applied effects
        applied_effects = getattr(dwarf_builder, "applied_effects", [])

        # Should have save advantage effect
        save_advantage_effect = None
        damage_resistance_effect = None
        for effect_data in applied_effects:
            effect = effect_data["effect"]
            if effect.get("type") == "grant_save_advantage":
                save_advantage_effect = effect
            elif effect.get("type") == "grant_damage_resistance":
                damage_resistance_effect = effect

        assert save_advantage_effect is not None
        assert save_advantage_effect["abilities"] == ["Constitution"]
        assert save_advantage_effect["condition"] == "Poisoned"
        assert save_advantage_effect["display"] == "Advantage vs Poisoned condition"

        assert damage_resistance_effect is not None
        assert damage_resistance_effect["damage_type"] == "Poison"

    def test_dwarven_toughness_scaling(self, dwarf_builder):
        """Test Dwarven Toughness HP bonus scaling"""
        # Test at level 1
        dwarf_builder.set_class("Fighter", 1)
        applied_effects = getattr(dwarf_builder, "applied_effects", [])

        # Find the HP bonus effect
        hp_bonus_effect = None
        for effect_data in applied_effects:
            effect = effect_data["effect"]
            if effect.get("type") == "bonus_hp":
                hp_bonus_effect = effect
                break

        assert hp_bonus_effect is not None
        assert hp_bonus_effect["value"] == 1
        assert hp_bonus_effect["scaling"] == "per_level"

        # Test level progression - effects should remain the same as scaling is handled by HP calculator
        dwarf_builder.set_class("Fighter", 5)
        applied_effects_l5 = getattr(dwarf_builder, "applied_effects", [])

        # Should still have the same HP bonus effect
        hp_bonus_effect_l5 = None
        for effect_data in applied_effects_l5:
            effect = effect_data["effect"]
            if effect.get("type") == "bonus_hp":
                hp_bonus_effect_l5 = effect
                break

        assert hp_bonus_effect_l5 is not None
        assert hp_bonus_effect_l5["value"] == 1
        assert hp_bonus_effect_l5["scaling"] == "per_level"

    def test_stonecunning_feature(self, dwarf_builder):
        """Test Stonecunning feature details"""
        char_data = dwarf_builder.character_data
        species_features = char_data["features"]["species"]

        stonecunning_feature = None
        for feature in species_features:
            if feature["name"] == "Stonecunning":
                stonecunning_feature = feature
                break

        assert stonecunning_feature is not None
        description = stonecunning_feature["description"]

        # Check key elements of Stonecunning
        assert "Bonus Action" in description
        assert "Tremorsense" in description
        assert "60 feet" in description
        assert "10 minutes" in description
        assert "stone surface" in description
        assert "Proficiency Bonus" in description
        assert "Long Rest" in description

    def test_dwarf_with_class_integration(self, dwarf_builder):
        """Test dwarf integration with different classes"""
        # Test with Fighter
        dwarf_builder.set_class("Fighter", 1)
        char_data = dwarf_builder.character_data

        assert char_data["class"] == "Fighter"
        assert char_data["species"] == "Dwarf"
        assert char_data["level"] == 1

        # Dwarf traits should still be present
        assert char_data["darkvision"] == 120
        assert "Poison" in char_data["resistances"]

        # Test with Cleric
        dwarf_builder_cleric = CharacterBuilder()
        dwarf_builder_cleric.set_species("Dwarf")
        dwarf_builder_cleric.set_class("Cleric", 1)
        char_data_cleric = dwarf_builder_cleric.character_data

        assert char_data_cleric["class"] == "Cleric"
        assert char_data_cleric["species"] == "Dwarf"
        assert char_data_cleric["darkvision"] == 120

    def test_dwarf_feature_descriptions(self, dwarf_builder):
        """Test that all dwarf features have proper descriptions"""
        char_data = dwarf_builder.character_data
        species_features = char_data["features"]["species"]

        for feature in species_features:
            assert "description" in feature
            assert len(feature["description"]) > 0
            assert isinstance(feature["description"], str)

    def test_dwarf_effects_system_integration(self, dwarf_builder):
        """Test dwarf features work with the effects system"""
        applied_effects = getattr(dwarf_builder, "applied_effects", [])

        # Phase 9: dwarf now has 4 effects from traits (Darkvision is
        # effect-driven via grant_darkvision; Dwarven Resilience x2,
        # Dwarven Toughness x1).
        assert len(applied_effects) == 4

        effect_types = [
            effect_data["effect"]["type"] for effect_data in applied_effects
        ]
        assert "grant_save_advantage" in effect_types
        assert "grant_damage_resistance" in effect_types
        assert "bonus_hp" in effect_types
        assert "grant_darkvision" in effect_types

        # Check sources are correct
        for effect_data in applied_effects:
            assert effect_data["source_type"] == "species"
            assert effect_data["source"] in [
                "Darkvision",
                "Dwarven Resilience",
                "Dwarven Toughness",
            ]


class TestDwarfSpeciesValidation:
    """Test dwarf species data validation and edge cases"""

    def test_dwarf_data_file_structure(self):
        """Test that dwarf data file has correct structure"""
        from pathlib import Path
        import json

        dwarf_file = Path("data/species/dwarf.json")
        assert dwarf_file.exists(), "Dwarf data file should exist"

        with open(dwarf_file, "r") as f:
            dwarf_data = json.load(f)

        # Check required fields
        assert "name" in dwarf_data
        assert dwarf_data["name"] == "Dwarf"
        assert "description" in dwarf_data
        assert "creature_type" in dwarf_data
        assert dwarf_data["creature_type"] == "Humanoid"
        assert "size" in dwarf_data
        assert dwarf_data["size"] == "Medium"
        assert "speed" in dwarf_data
        assert dwarf_data["speed"] == 30
        # Phase 9: dwarf no longer carries a top-level ``darkvision`` field;
        # the canonical source is the grant_darkvision effect on the
        # ``Darkvision`` trait. Assert that effect instead.
        darkvision_trait = dwarf_data["traits"]["Darkvision"]
        assert isinstance(darkvision_trait, dict)
        dv_effects = [
            e for e in darkvision_trait.get("effects", [])
            if e.get("type") == "grant_darkvision"
        ]
        assert len(dv_effects) == 1
        assert dv_effects[0].get("range") == 120
        assert "traits" in dwarf_data
        assert "languages" in dwarf_data

        # Check traits structure
        traits = dwarf_data["traits"]
        assert "Darkvision" in traits
        assert "Dwarven Resilience" in traits
        assert "Dwarven Toughness" in traits
        assert "Stonecunning" in traits

        # Check effects in traits with effects
        dwarven_resilience = traits["Dwarven Resilience"]
        assert "effects" in dwarven_resilience
        assert len(dwarven_resilience["effects"]) == 2

        dwarven_toughness = traits["Dwarven Toughness"]
        assert "effects" in dwarven_toughness
        assert len(dwarven_toughness["effects"]) == 1
        assert dwarven_toughness["effects"][0]["type"] == "bonus_hp"
        assert dwarven_toughness["effects"][0]["scaling"] == "per_level"

    def test_dwarf_species_loading_error_handling(self):
        """Test error handling when loading dwarf species"""
        from modules.character_builder import CharacterBuilder

        builder = CharacterBuilder()

        # Test with invalid species name
        result = builder.set_species("InvalidSpecies")
        assert result is False

        # Test that valid dwarf loading works
        result = builder.set_species("Dwarf")
        assert result is True

    def test_dwarf_multiclass_compatibility(self):
        """Test dwarf works with potential multiclass scenarios"""
        builder = CharacterBuilder()
        builder.set_species("Dwarf")

        # Start as Fighter
        builder.set_class("Fighter", 1)
        char_data = builder.character_data

        # Dwarf traits should be maintained
        assert char_data["species"] == "Dwarf"
        assert char_data["darkvision"] == 120

        # Applied effects should remain consistent
        applied_effects = getattr(builder, "applied_effects", [])
        dwarf_effects = [e for e in applied_effects if e["source_type"] == "species"]
        # Phase 9: Darkvision is now an effect-driven trait (+1 over the
        # pre-migration count of 3).
        assert len(dwarf_effects) == 4
