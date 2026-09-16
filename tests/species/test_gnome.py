#!/usr/bin/env python3
"""
Unit tests for the Gnome species implementation.
Tests all features, effects, lineages, and mechanics specific to the Gnome species.
"""

import pytest
from modules.character_builder import CharacterBuilder
from modules.variant_manager import VariantManager


@pytest.fixture
def gnome_builder():
    """Fixture providing a fresh CharacterBuilder with Gnome species setup"""
    builder = CharacterBuilder()
    builder.set_species("Gnome")
    return builder


@pytest.fixture
def variant_manager():
    """Fixture providing a VariantManager instance"""
    return VariantManager()


class TestGnomeSpecies:
    """Test base Gnome species implementation"""

    def test_gnome_basic_traits(self, gnome_builder):
        """Test basic gnome species setup: speed, darkvision, size, languages"""
        char_data = gnome_builder.character_data

        assert char_data["species"] == "Gnome"
        assert char_data["speed"] == 30
        assert char_data["darkvision"] == 60

        # Size (stored in species_data)
        species_data = char_data.get("species_data", {})
        assert species_data.get("size") == "Small"

        # Languages
        languages = char_data["proficiencies"]["languages"]
        assert "Common" in languages
        assert "Gnomish" not in languages

    def test_gnome_features_present(self, gnome_builder):
        """Test that all gnome features are present"""
        char_data = gnome_builder.character_data
        species_features = char_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]

        assert "Darkvision" in feature_names
        assert "Gnomish Cunning" in feature_names
        assert "Gnomish Lineage" in feature_names

    def test_darkvision_feature(self, gnome_builder):
        """Test Darkvision feature: range=60, description mentions 60 feet"""
        char_data = gnome_builder.character_data

        assert char_data["darkvision"] == 60

        species_features = char_data["features"]["species"]
        darkvision_feature = None
        for feature in species_features:
            if feature["name"] == "Darkvision":
                darkvision_feature = feature
                break

        assert darkvision_feature is not None
        description = darkvision_feature["description"]
        assert "Darkvision" in description
        assert "60 feet" in description

    def test_gnomish_cunning_effects(self, gnome_builder):
        """Test Gnomish Cunning grants save advantage on INT, WIS, CHA"""
        applied_effects = getattr(gnome_builder, "applied_effects", [])

        save_advantage_effects = [
            e for e in applied_effects
            if e["effect"].get("type") == "grant_save_advantage"
        ]

        assert len(save_advantage_effects) >= 1

        cunning_effect = save_advantage_effects[0]["effect"]
        assert "Intelligence" in cunning_effect["abilities"]
        assert "Wisdom" in cunning_effect["abilities"]
        assert "Charisma" in cunning_effect["abilities"]

    def test_gnomish_cunning_display(self, gnome_builder):
        """Test Gnomish Cunning display text"""
        applied_effects = getattr(gnome_builder, "applied_effects", [])

        save_advantage_effects = [
            e for e in applied_effects
            if e["effect"].get("type") == "grant_save_advantage"
        ]

        assert len(save_advantage_effects) >= 1
        display = save_advantage_effects[0]["effect"].get("display", "")
        assert "INT" in display
        assert "WIS" in display
        assert "CHA" in display

    def test_gnomish_cunning_in_save_advantages(self, gnome_builder):
        """Test Gnomish Cunning appears in save_advantages output"""
        char_data = gnome_builder.character_data
        save_advantages = char_data.get("save_advantages", [])

        assert len(save_advantages) >= 1
        # Find the gnomish cunning save advantage
        found = any(
            "Intelligence" in sa.get("abilities", [])
            and "Wisdom" in sa.get("abilities", [])
            and "Charisma" in sa.get("abilities", [])
            for sa in save_advantages
        )
        assert found, "Expected save advantage for INT, WIS, CHA in save_advantages"

    def test_gnome_feature_descriptions(self, gnome_builder):
        """Test all features have non-empty descriptions"""
        char_data = gnome_builder.character_data
        species_features = char_data["features"]["species"]

        for feature in species_features:
            assert "description" in feature, f"Feature {feature['name']} missing description"
            assert len(feature["description"]) > 0, (
                f"Feature {feature['name']} has empty description"
            )

    def test_gnome_effects_system_integration(self, gnome_builder):
        """Test correct number and types of effects applied"""
        applied_effects = getattr(gnome_builder, "applied_effects", [])
        effect_types = [e["effect"]["type"] for e in applied_effects]

        # Should have grant_darkvision from Darkvision trait
        assert "grant_darkvision" in effect_types
        # Should have grant_save_advantage from Gnomish Cunning
        assert "grant_save_advantage" in effect_types

        # Should be exactly 2 base species effects (darkvision + cunning)
        assert len(applied_effects) == 2

    def test_gnome_creature_type(self, gnome_builder):
        """Test Gnome creature type is Humanoid"""
        char_data = gnome_builder.character_data
        species_data = char_data.get("species_data", {})
        assert species_data.get("creature_type") == "Humanoid"

    def test_gnome_lineage_feature_is_choice(self, gnome_builder):
        """Test Gnomish Lineage feature indicates it's a choice"""
        char_data = gnome_builder.character_data
        species_features = char_data["features"]["species"]

        lineage_feature = None
        for feature in species_features:
            if feature["name"] == "Gnomish Lineage":
                lineage_feature = feature
                break

        assert lineage_feature is not None
        description = lineage_feature["description"]
        assert "Intelligence" in description
        assert "Wisdom" in description
        assert "Charisma" in description


class TestGnomeLineages:
    """Test Gnome lineage/variant implementations"""

    def test_gnome_has_lineages(self, variant_manager):
        """Test that gnome has available lineages"""
        assert variant_manager.has_variants("Gnome")
        lineages = variant_manager.get_available_variants("Gnome")

        assert "Forest Gnome" in lineages
        assert "Rock Gnome" in lineages
        assert len(lineages) == 2

    def test_forest_gnome_lineage(self):
        """Test Forest Gnome lineage grants Minor Illusion cantrip and Speak with Animals"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        result = builder.set_lineage("Forest Gnome", "Intelligence")

        assert result is True
        char_data = builder.character_data

        assert char_data["species"] == "Gnome"
        assert char_data["lineage"] == "Forest Gnome"

        # Check lineage features
        lineage_features = char_data["features"]["lineage"]
        feature_names = [f["name"] for f in lineage_features]
        assert "Natural Illusionist" in feature_names
        assert "Speak with Animals" in feature_names

        # Check applied effects include lineage effects
        applied_effects = getattr(builder, "applied_effects", [])
        effect_types = [e["effect"]["type"] for e in applied_effects]

        assert "grant_cantrip" in effect_types  # Minor Illusion
        assert "grant_spell" in effect_types  # Speak with Animals

    def test_forest_gnome_cantrip_minor_illusion(self):
        """Test Forest Gnome grants Minor Illusion cantrip via always_prepared"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        builder.set_lineage("Forest Gnome", "Intelligence")

        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Minor Illusion" in always_prepared
        assert always_prepared["Minor Illusion"]["level"] == 0

    def test_forest_gnome_cantrip_source(self):
        """Test source tracking on Minor Illusion cantrip from Forest Gnome"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        builder.set_lineage("Forest Gnome", "Intelligence")

        applied_effects = getattr(builder, "applied_effects", [])
        cantrip_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_cantrip"
        ]

        minor_illusion_effect = None
        for effect in cantrip_effects:
            if effect["effect"]["spell"] == "Minor Illusion":
                minor_illusion_effect = effect
                break

        assert minor_illusion_effect is not None
        assert minor_illusion_effect["source_type"] == "lineage"
        assert minor_illusion_effect["source"] == "Natural Illusionist"

    def test_forest_gnome_spell_always_prepared(self):
        """Test Speak with Animals is always prepared for Forest Gnome"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        builder.set_lineage("Forest Gnome", "Wisdom")

        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Speak with Animals" in always_prepared
        assert always_prepared["Speak with Animals"]["always_prepared"] is True
        assert always_prepared["Speak with Animals"]["level"] == 1

    def test_forest_gnome_speak_with_animals_min_level(self):
        """Test Speak with Animals grant_spell has min_level 1"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        builder.set_lineage("Forest Gnome", "Wisdom")

        applied_effects = getattr(builder, "applied_effects", [])
        spell_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_spell"
        ]

        swa_effect = None
        for effect in spell_effects:
            if effect["effect"]["spell"] == "Speak with Animals":
                swa_effect = effect
                break

        assert swa_effect is not None
        assert swa_effect["effect"].get("min_level", 1) == 1

    def test_rock_gnome_lineage(self):
        """Test Rock Gnome lineage grants Mending and Prestidigitation cantrips"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        result = builder.set_lineage("Rock Gnome", "Intelligence")

        assert result is True
        char_data = builder.character_data

        assert char_data["species"] == "Gnome"
        assert char_data["lineage"] == "Rock Gnome"

        # Check lineage features
        lineage_features = char_data["features"]["lineage"]
        feature_names = [f["name"] for f in lineage_features]
        assert "Tinker" in feature_names

        # Check cantrips via always_prepared
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Mending" in always_prepared
        assert "Prestidigitation" in always_prepared
        assert always_prepared["Mending"]["level"] == 0
        assert always_prepared["Prestidigitation"]["level"] == 0

    def test_rock_gnome_cantrip_source(self):
        """Test source tracking on Mending/Prestidigitation from Rock Gnome"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        builder.set_lineage("Rock Gnome", "Intelligence")

        applied_effects = getattr(builder, "applied_effects", [])
        cantrip_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_cantrip"
        ]

        cantrip_spells = [e["effect"]["spell"] for e in cantrip_effects]
        assert "Mending" in cantrip_spells
        assert "Prestidigitation" in cantrip_spells

        # Verify source is Tinker
        for effect in cantrip_effects:
            if effect["effect"]["spell"] in ("Mending", "Prestidigitation"):
                assert effect["source_type"] == "lineage"
                assert effect["source"] == "Tinker"

    def test_rock_gnome_no_tinker_tools_proficiency(self):
        """Test Rock Gnome does NOT grant Tinker's Tools proficiency (removed in 2024)"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        builder.set_lineage("Rock Gnome", "Intelligence")

        char_data = builder.character_data
        tool_profs = char_data["proficiencies"]["tools"]
        assert "Tinker's Tools" not in tool_profs

    def test_rock_gnome_no_artificers_lore(self):
        """Test Rock Gnome does NOT have Artificer's Lore feature (removed in 2024)"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        builder.set_lineage("Rock Gnome", "Intelligence")

        char_data = builder.character_data
        lineage_features = char_data["features"]["lineage"]
        feature_names = [f["name"] for f in lineage_features]
        assert "Artificer's Lore" not in feature_names

    def test_forest_gnome_no_rock_gnome_traits(self):
        """Test Forest Gnome does not get Rock Gnome traits"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        builder.set_lineage("Forest Gnome", "Intelligence")

        char_data = builder.character_data
        lineage_features = char_data["features"]["lineage"]
        feature_names = [f["name"] for f in lineage_features]

        assert "Tinker" not in feature_names

    def test_rock_gnome_no_forest_gnome_traits(self):
        """Test Rock Gnome does not get Forest Gnome traits"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        builder.set_lineage("Rock Gnome", "Intelligence")

        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        assert "Minor Illusion" not in always_prepared
        assert "Speak with Animals" not in always_prepared


class TestGnomeIntegration:
    """Test Gnome integration with classes and validation"""

    def test_gnome_with_wizard_class(self):
        """Test Gnome Wizard: combined proficiencies and spellcasting"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        builder.set_lineage("Forest Gnome", "Intelligence")
        builder.set_class("Wizard", 1)
        builder.set_background("Sage")

        character = builder.to_character()

        assert character["species"] == "Gnome"
        assert character["class"] == "Wizard"
        assert character["lineage"] == "Forest Gnome"

        # Gnome languages preserved
        assert "Common" in character["proficiencies"]["languages"]
        assert "Gnomish" not in character["proficiencies"]["languages"]

        # Gnomish Cunning save advantages preserved
        save_advantages = character.get("save_advantages", [])
        found = any(
            "Intelligence" in sa.get("abilities", [])
            and "Wisdom" in sa.get("abilities", [])
            for sa in save_advantages
        )
        assert found

        # Minor Illusion from Forest Gnome is available via always_prepared
        assert "Minor Illusion" in character["spells"]["always_prepared"]

    def test_gnome_with_fighter_class(self):
        """Test Gnome Fighter: combined proficiencies"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        builder.set_lineage("Rock Gnome", "Intelligence")
        builder.set_class("Fighter", 1)
        builder.set_background("Soldier")

        character = builder.to_character()

        assert character["species"] == "Gnome"
        assert character["class"] == "Fighter"

        # Fighter proficiencies
        assert "Heavy armor" in character["proficiencies"]["armor"]

        # Gnome darkvision preserved
        assert character["darkvision"] == 60

        # Rock Gnome cantrips available via always_prepared
        assert "Mending" in character["spells"]["always_prepared"]
        assert "Prestidigitation" in character["spells"]["always_prepared"]

    def test_gnome_invalid_lineage(self):
        """Test setting an invalid lineage returns False"""
        builder = CharacterBuilder()
        builder.set_species("Gnome")
        result = builder.set_lineage("Deep Gnome", "Intelligence")

        assert result is False
        assert builder.character_data.get("lineage") is None

    def test_gnome_size_is_small(self, gnome_builder):
        """Test that Gnome size is Small (not Medium)"""
        char_data = gnome_builder.character_data
        species_data = char_data.get("species_data", {})
        assert species_data.get("size") == "Small"

    def test_gnome_darkvision_via_effect(self, gnome_builder):
        """Test darkvision is set via grant_darkvision effect"""
        applied_effects = getattr(gnome_builder, "applied_effects", [])
        darkvision_effects = [
            e for e in applied_effects
            if e["effect"]["type"] == "grant_darkvision"
        ]

        assert len(darkvision_effects) == 1
        assert darkvision_effects[0]["effect"]["range"] == 60


class TestGnomeDataValidation:
    """Test Gnome data file integrity"""

    def test_gnome_data_loads(self):
        """Test that gnome.json loads successfully"""
        from modules.data_loader import DataLoader

        loader = DataLoader()
        species_data = loader.species.get("Gnome")

        assert species_data is not None
        assert species_data["name"] == "Gnome"

    def test_forest_gnome_variant_loads(self):
        """Test that forest_gnome.json loads successfully"""
        vm = VariantManager()
        variant = vm.get_variant_data("Forest Gnome")

        assert variant is not None
        assert variant["name"] == "Forest Gnome"
        assert variant["parent_species"] == "Gnome"

    def test_rock_gnome_variant_loads(self):
        """Test that rock_gnome.json loads successfully"""
        vm = VariantManager()
        variant = vm.get_variant_data("Rock Gnome")

        assert variant is not None
        assert variant["name"] == "Rock Gnome"
        assert variant["parent_species"] == "Gnome"

    def test_gnome_all_traits_have_correct_structure(self):
        """Test that all gnome traits have required fields"""
        from modules.data_loader import DataLoader

        loader = DataLoader()
        species_data = loader.species.get("Gnome")
        traits = species_data["traits"]

        for trait_name, trait_data in traits.items():
            if isinstance(trait_data, dict):
                assert "description" in trait_data, (
                    f"Trait {trait_name} missing description"
                )
