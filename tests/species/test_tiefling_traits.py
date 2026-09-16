#!/usr/bin/env python3
"""
Unit tests for the Tiefling species implementation.
Tests all features, effects, lineages (Abyssal, Chthonic, Infernal),
and mechanics specific to the Tiefling species.
"""

import pytest
from modules.character_builder import CharacterBuilder
from modules.variant_manager import VariantManager


@pytest.fixture
def tiefling_builder():
    """Fixture providing a fresh CharacterBuilder with Tiefling species setup."""
    builder = CharacterBuilder()
    builder.set_species("Tiefling")
    return builder


@pytest.fixture
def variant_manager():
    """Fixture providing a VariantManager instance."""
    return VariantManager()


class TestTieflingBasicTraits:
    """Test base Tiefling species traits and properties."""

    def test_tiefling_basic_properties(self, tiefling_builder):
        """Test basic Tiefling species setup: name, speed, darkvision, creature type."""
        char_data = tiefling_builder.character_data

        assert char_data["species"] == "Tiefling"
        assert char_data["speed"] == 30
        assert char_data["darkvision"] == 60

    def test_tiefling_languages(self, tiefling_builder):
        """Test that Tiefling starts with Common before language choices."""
        char_data = tiefling_builder.character_data
        languages = char_data["proficiencies"]["languages"]

        assert "Common" in languages
        assert "Infernal" not in languages

    def test_tiefling_features_present(self, tiefling_builder):
        """Test that all base Tiefling features are present."""
        char_data = tiefling_builder.character_data
        species_features = char_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]

        assert "Darkvision" in feature_names
        assert "Fiendish Legacy" in feature_names
        assert "Otherworldly Presence" in feature_names

    def test_darkvision_effect(self, tiefling_builder):
        """Test Darkvision effect: grant_darkvision with range 60."""
        char_data = tiefling_builder.character_data
        assert char_data["darkvision"] == 60

        species_features = char_data["features"]["species"]
        darkvision_feature = None
        for feature in species_features:
            if feature["name"] == "Darkvision":
                darkvision_feature = feature
                break

        assert darkvision_feature is not None
        assert "60 feet" in darkvision_feature["description"]

    def test_otherworldly_presence_grants_thaumaturgy(self, tiefling_builder):
        """Test Otherworldly Presence grants Thaumaturgy cantrip."""
        char_data = tiefling_builder.character_data

        always_prepared = char_data["spells"]["always_prepared"]
        assert "Thaumaturgy" in always_prepared

        applied_effects = getattr(tiefling_builder, "applied_effects", [])
        cantrip_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_cantrip"
        ]

        thaumaturgy_effect = None
        for effect in cantrip_effects:
            if effect["effect"]["spell"] == "Thaumaturgy":
                thaumaturgy_effect = effect
                break

        assert thaumaturgy_effect is not None
        assert thaumaturgy_effect["source_type"] == "species"

    def test_fiendish_legacy_is_choice_trait(self, tiefling_builder):
        """Test Fiendish Legacy appears as a choice with Int/Wis/Cha options."""
        trait_choices = tiefling_builder.get_species_trait_choices()

        assert "Fiendish Legacy" in trait_choices
        choice_data = trait_choices["Fiendish Legacy"]
        options = choice_data["options"]

        assert "Intelligence" in options
        assert "Wisdom" in options
        assert "Charisma" in options
        assert len(options) == 3

    def test_tiefling_has_lineages(self, variant_manager):
        """Test that Tiefling has 3 available lineages."""
        assert variant_manager.has_variants("Tiefling")
        lineages = variant_manager.get_available_variants("Tiefling")

        assert "Abyssal Tiefling" in lineages
        assert "Chthonic Tiefling" in lineages
        assert "Infernal Tiefling" in lineages
        assert len(lineages) == 3


class TestAbyssalTiefling:
    """Test Abyssal Tiefling lineage implementation."""

    def test_set_lineage_returns_true(self):
        """Test that setting Abyssal Tiefling lineage succeeds."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        result = builder.set_lineage("Abyssal Tiefling")

        assert result is True

    def test_lineage_name_stored(self):
        """Test that lineage name is stored correctly."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Abyssal Tiefling")

        assert builder.character_data["lineage"] == "Abyssal Tiefling"

    def test_poison_resistance(self):
        """Test Abyssal Tiefling grants Poison damage resistance."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Abyssal Tiefling")
        char_data = builder.character_data

        assert "Poison" in char_data["resistances"]

    def test_poison_spray_cantrip(self):
        """Test Abyssal Tiefling grants Poison Spray cantrip."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Abyssal Tiefling")
        char_data = builder.character_data

        always_prepared = char_data["spells"]["always_prepared"]
        assert "Poison Spray" in always_prepared

    def test_poison_spray_cantrip_effect_source(self):
        """Test Poison Spray cantrip effect has lineage source type."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Abyssal Tiefling")

        applied_effects = getattr(builder, "applied_effects", [])
        cantrip_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_cantrip"
        ]

        poison_spray_effect = None
        for effect in cantrip_effects:
            if effect["effect"]["spell"] == "Poison Spray":
                poison_spray_effect = effect
                break

        assert poison_spray_effect is not None
        assert poison_spray_effect["source_type"] == "lineage"

    def test_ray_of_sickness_level3_spell(self):
        """Test Abyssal Tiefling has Ray of Sickness as level 3 spell."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Abyssal Tiefling")

        applied_effects = getattr(builder, "applied_effects", [])
        spell_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_spell"
        ]

        ray_effect = None
        for effect in spell_effects:
            if effect["effect"]["spell"] == "Ray of Sickness":
                ray_effect = effect
                break

        assert ray_effect is not None
        assert ray_effect["effect"]["min_level"] == 3

    def test_hold_person_level5_spell(self):
        """Test Abyssal Tiefling has Hold Person as level 5 spell."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Abyssal Tiefling")

        applied_effects = getattr(builder, "applied_effects", [])
        spell_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_spell"
        ]

        hold_effect = None
        for effect in spell_effects:
            if effect["effect"]["spell"] == "Hold Person":
                hold_effect = effect
                break

        assert hold_effect is not None
        assert hold_effect["effect"]["min_level"] == 5


class TestChthonicTiefling:
    """Test Chthonic Tiefling lineage implementation."""

    def test_set_lineage_returns_true(self):
        """Test that setting Chthonic Tiefling lineage succeeds."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        result = builder.set_lineage("Chthonic Tiefling")

        assert result is True

    def test_lineage_name_stored(self):
        """Test that lineage name is stored correctly."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Chthonic Tiefling")

        assert builder.character_data["lineage"] == "Chthonic Tiefling"

    def test_necrotic_resistance(self):
        """Test Chthonic Tiefling grants Necrotic damage resistance."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Chthonic Tiefling")
        char_data = builder.character_data

        assert "Necrotic" in char_data["resistances"]

    def test_chill_touch_cantrip(self):
        """Test Chthonic Tiefling grants Chill Touch cantrip."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Chthonic Tiefling")
        char_data = builder.character_data

        always_prepared = char_data["spells"]["always_prepared"]
        assert "Chill Touch" in always_prepared

    def test_chill_touch_cantrip_effect_source(self):
        """Test Chill Touch cantrip effect has lineage source type."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Chthonic Tiefling")

        applied_effects = getattr(builder, "applied_effects", [])
        cantrip_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_cantrip"
        ]

        chill_touch_effect = None
        for effect in cantrip_effects:
            if effect["effect"]["spell"] == "Chill Touch":
                chill_touch_effect = effect
                break

        assert chill_touch_effect is not None
        assert chill_touch_effect["source_type"] == "lineage"

    def test_false_life_level3_spell(self):
        """Test Chthonic Tiefling has False Life as level 3 spell."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Chthonic Tiefling")

        applied_effects = getattr(builder, "applied_effects", [])
        spell_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_spell"
        ]

        false_life_effect = None
        for effect in spell_effects:
            if effect["effect"]["spell"] == "False Life":
                false_life_effect = effect
                break

        assert false_life_effect is not None
        assert false_life_effect["effect"]["min_level"] == 3

    def test_ray_of_enfeeblement_level5_spell(self):
        """Test Chthonic Tiefling has Ray of Enfeeblement as level 5 spell."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Chthonic Tiefling")

        applied_effects = getattr(builder, "applied_effects", [])
        spell_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_spell"
        ]

        ray_effect = None
        for effect in spell_effects:
            if effect["effect"]["spell"] == "Ray of Enfeeblement":
                ray_effect = effect
                break

        assert ray_effect is not None
        assert ray_effect["effect"]["min_level"] == 5


class TestInfernalTiefling:
    """Test Infernal Tiefling lineage implementation."""

    def test_set_lineage_returns_true(self):
        """Test that setting Infernal Tiefling lineage succeeds."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        result = builder.set_lineage("Infernal Tiefling")

        assert result is True

    def test_lineage_name_stored(self):
        """Test that lineage name is stored correctly."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Infernal Tiefling")

        assert builder.character_data["lineage"] == "Infernal Tiefling"

    def test_fire_resistance(self):
        """Test Infernal Tiefling grants Fire damage resistance."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Infernal Tiefling")
        char_data = builder.character_data

        assert "Fire" in char_data["resistances"]

    def test_fire_bolt_cantrip(self):
        """Test Infernal Tiefling grants Fire Bolt cantrip."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Infernal Tiefling")
        char_data = builder.character_data

        always_prepared = char_data["spells"]["always_prepared"]
        assert "Fire Bolt" in always_prepared

    def test_fire_bolt_cantrip_effect_source(self):
        """Test Fire Bolt cantrip effect has lineage source type."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Infernal Tiefling")

        applied_effects = getattr(builder, "applied_effects", [])
        cantrip_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_cantrip"
        ]

        fire_bolt_effect = None
        for effect in cantrip_effects:
            if effect["effect"]["spell"] == "Fire Bolt":
                fire_bolt_effect = effect
                break

        assert fire_bolt_effect is not None
        assert fire_bolt_effect["source_type"] == "lineage"

    def test_hellish_rebuke_level3_spell(self):
        """Test Infernal Tiefling has Hellish Rebuke as level 3 spell."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Infernal Tiefling")

        applied_effects = getattr(builder, "applied_effects", [])
        spell_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_spell"
        ]

        hellish_effect = None
        for effect in spell_effects:
            if effect["effect"]["spell"] == "Hellish Rebuke":
                hellish_effect = effect
                break

        assert hellish_effect is not None
        assert hellish_effect["effect"]["min_level"] == 3

    def test_darkness_level5_spell(self):
        """Test Infernal Tiefling has Darkness as level 5 spell."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Infernal Tiefling")

        applied_effects = getattr(builder, "applied_effects", [])
        spell_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_spell"
        ]

        darkness_effect = None
        for effect in spell_effects:
            if effect["effect"]["spell"] == "Darkness":
                darkness_effect = effect
                break

        assert darkness_effect is not None
        assert darkness_effect["effect"]["min_level"] == 5


class TestTieflingIntegration:
    """Integration tests: Tiefling with lineage and class together."""

    def test_base_features_persist_with_lineage(self):
        """Test that base Tiefling features persist when a lineage is applied."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Infernal Tiefling")
        char_data = builder.character_data

        # Base species features should still be present
        species_features = char_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]
        assert "Darkvision" in feature_names
        assert "Otherworldly Presence" in feature_names

        # Thaumaturgy cantrip from base species should persist
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Thaumaturgy" in always_prepared

        # Darkvision should still be 60
        assert char_data["darkvision"] == 60

    def test_lineage_features_alongside_base(self):
        """Test that lineage features appear alongside base species features."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Abyssal Tiefling")
        char_data = builder.character_data

        # Lineage features should be present
        lineage_features = char_data["features"]["lineage"]
        lineage_feature_names = [f["name"] for f in lineage_features]
        assert "Abyssal Legacy" in lineage_feature_names

        # Base species features should also be present
        species_features = char_data["features"]["species"]
        species_feature_names = [f["name"] for f in species_features]
        assert "Darkvision" in species_feature_names

    def test_tiefling_with_class_preserves_effects(self):
        """Test that Tiefling + lineage + class preserves all species/lineage effects."""
        builder = CharacterBuilder()
        builder.set_species("Tiefling")
        builder.set_lineage("Infernal Tiefling")
        builder.set_class("Warlock", 1)
        char_data = builder.character_data

        # Species traits should persist
        assert char_data["species"] == "Tiefling"
        assert char_data["lineage"] == "Infernal Tiefling"
        assert char_data["darkvision"] == 60
        assert char_data["speed"] == 30

        # Languages should persist
        languages = char_data["proficiencies"]["languages"]
        assert "Common" in languages
        assert "Infernal" not in languages

        # Lineage resistance should persist
        assert "Fire" in char_data["resistances"]

        # Both base and lineage cantrips should persist
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Thaumaturgy" in always_prepared
        assert "Fire Bolt" in always_prepared

    def test_all_lineages_grant_resistance(self):
        """Test that each lineage grants the correct damage resistance."""
        expected = {
            "Abyssal Tiefling": "Poison",
            "Chthonic Tiefling": "Necrotic",
            "Infernal Tiefling": "Fire",
        }

        for lineage_name, resistance_type in expected.items():
            builder = CharacterBuilder()
            builder.set_species("Tiefling")
            builder.set_lineage(lineage_name)
            char_data = builder.character_data

            assert resistance_type in char_data["resistances"], (
                f"{lineage_name} should grant {resistance_type} resistance"
            )

    def test_all_lineages_grant_cantrip(self):
        """Test that each lineage grants the correct cantrip."""
        expected = {
            "Abyssal Tiefling": "Poison Spray",
            "Chthonic Tiefling": "Chill Touch",
            "Infernal Tiefling": "Fire Bolt",
        }

        for lineage_name, cantrip_name in expected.items():
            builder = CharacterBuilder()
            builder.set_species("Tiefling")
            builder.set_lineage(lineage_name)
            char_data = builder.character_data

            always_prepared = char_data["spells"]["always_prepared"]
            assert cantrip_name in always_prepared, (
                f"{lineage_name} should grant {cantrip_name}"
            )
