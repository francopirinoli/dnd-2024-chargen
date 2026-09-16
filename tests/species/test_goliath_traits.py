#!/usr/bin/env python3
"""
Unit tests for the Goliath species implementation.
Tests all features, effects, and mechanics specific to the Goliath species.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def goliath_builder():
    """Fixture providing a fresh CharacterBuilder with Goliath species setup"""
    builder = CharacterBuilder()
    builder.set_species("Goliath")
    return builder


class TestGoliathBasicTraits:
    """Test Goliath basic species properties"""

    def test_goliath_species_name(self, goliath_builder):
        """Test species is set correctly"""
        char_data = goliath_builder.character_data
        assert char_data["species"] == "Goliath"

    def test_goliath_speed(self, goliath_builder):
        """Test Goliath speed is 35 (faster than most species)"""
        char_data = goliath_builder.character_data
        assert char_data["speed"] == 35

    def test_goliath_size(self, goliath_builder):
        """Test Goliath default size is Medium"""
        species_data = goliath_builder.character_data["species_data"]
        assert species_data["size"] == "Medium"

    def test_goliath_no_darkvision(self, goliath_builder):
        """Test Goliath has no darkvision"""
        char_data = goliath_builder.character_data
        assert char_data["darkvision"] == 0

    def test_goliath_creature_type(self, goliath_builder):
        """Test Goliath creature type is Humanoid"""
        species_data = goliath_builder.character_data["species_data"]
        assert species_data["creature_type"] == "Humanoid"


class TestGoliathLanguages:
    """Test Goliath language proficiencies"""

    def test_goliath_knows_common(self, goliath_builder):
        """Test Goliath knows Common"""
        languages = goliath_builder.character_data["proficiencies"]["languages"]
        assert "Common" in languages

    def test_goliath_knows_giant(self, goliath_builder):
        """Test Goliath no longer gets Giant automatically."""
        languages = goliath_builder.character_data["proficiencies"]["languages"]
        assert "Giant" not in languages

    def test_goliath_language_count(self, goliath_builder):
        """Test baseline starts with Common only before language choices."""
        languages = goliath_builder.character_data["proficiencies"]["languages"]
        assert len(languages) == 1


class TestGoliathFeaturesPresent:
    """Test that all Goliath species features are present"""

    def test_goliath_has_giant_ancestry(self, goliath_builder):
        """Test Giant Ancestry feature is present"""
        species_features = goliath_builder.character_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]
        assert "Giant Ancestry" in feature_names

    def test_goliath_has_large_form(self, goliath_builder):
        """Test Large Form feature is present"""
        species_features = goliath_builder.character_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]
        assert "Large Form" in feature_names

    def test_goliath_has_powerful_build(self, goliath_builder):
        """Test Powerful Build feature is present"""
        species_features = goliath_builder.character_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]
        assert "Powerful Build" in feature_names

    def test_goliath_feature_count(self, goliath_builder):
        """Test Goliath has exactly 3 species features"""
        species_features = goliath_builder.character_data["features"]["species"]
        assert len(species_features) == 3


class TestGoliathFeatureDescriptions:
    """Test that all Goliath features have proper descriptions"""

    def test_all_features_have_descriptions(self, goliath_builder):
        """Test every feature has a non-empty description string"""
        species_features = goliath_builder.character_data["features"]["species"]
        for feature in species_features:
            assert "description" in feature
            assert isinstance(feature["description"], str)
            assert len(feature["description"]) > 0

    def test_large_form_description_mentions_level_5(self, goliath_builder):
        """Test Large Form description mentions the level 5 prerequisite"""
        species_features = goliath_builder.character_data["features"]["species"]
        large_form = next(f for f in species_features if f["name"] == "Large Form")
        assert "character level 5" in large_form["description"]

    def test_large_form_description_mentions_large(self, goliath_builder):
        """Test Large Form description mentions Large size"""
        species_features = goliath_builder.character_data["features"]["species"]
        large_form = next(f for f in species_features if f["name"] == "Large Form")
        assert "Large" in large_form["description"]

    def test_large_form_description_mentions_bonus_action(self, goliath_builder):
        """Test Large Form description mentions Bonus Action"""
        species_features = goliath_builder.character_data["features"]["species"]
        large_form = next(f for f in species_features if f["name"] == "Large Form")
        assert "Bonus Action" in large_form["description"]

    def test_large_form_description_mentions_long_rest(self, goliath_builder):
        """Test Large Form description mentions Long Rest"""
        species_features = goliath_builder.character_data["features"]["species"]
        large_form = next(f for f in species_features if f["name"] == "Large Form")
        assert "Long Rest" in large_form["description"]

    def test_powerful_build_description_mentions_grappled(self, goliath_builder):
        """Test Powerful Build description mentions Grappled condition"""
        species_features = goliath_builder.character_data["features"]["species"]
        powerful_build = next(
            f for f in species_features if f["name"] == "Powerful Build"
        )
        assert "Grappled" in powerful_build["description"]

    def test_powerful_build_description_mentions_carrying_capacity(self, goliath_builder):
        """Test Powerful Build description mentions carrying capacity"""
        species_features = goliath_builder.character_data["features"]["species"]
        powerful_build = next(
            f for f in species_features if f["name"] == "Powerful Build"
        )
        assert "carrying capacity" in powerful_build["description"]


class TestGoliathGiantAncestryChoice:
    """Test Giant Ancestry choice structure"""

    def test_giant_ancestry_is_choice_trait(self, goliath_builder):
        """Test Giant Ancestry appears in species trait choices"""
        choices = goliath_builder.get_species_trait_choices()
        assert "Giant Ancestry" in choices

    def test_giant_ancestry_has_six_options(self, goliath_builder):
        """Test Giant Ancestry has exactly 6 ancestry options"""
        choices = goliath_builder.get_species_trait_choices()
        options = choices["Giant Ancestry"]["options"]
        assert len(options) == 6

    def test_giant_ancestry_has_clouds_jaunt(self, goliath_builder):
        """Test Cloud's Jaunt option is available"""
        choices = goliath_builder.get_species_trait_choices()
        options = choices["Giant Ancestry"]["options"]
        assert any("Cloud's Jaunt" in opt for opt in options)

    def test_giant_ancestry_has_fires_burn(self, goliath_builder):
        """Test Fire's Burn option is available"""
        choices = goliath_builder.get_species_trait_choices()
        options = choices["Giant Ancestry"]["options"]
        assert any("Fire's Burn" in opt for opt in options)

    def test_giant_ancestry_has_frosts_chill(self, goliath_builder):
        """Test Frost's Chill option is available"""
        choices = goliath_builder.get_species_trait_choices()
        options = choices["Giant Ancestry"]["options"]
        assert any("Frost's Chill" in opt for opt in options)

    def test_giant_ancestry_has_hills_tumble(self, goliath_builder):
        """Test Hill's Tumble option is available"""
        choices = goliath_builder.get_species_trait_choices()
        options = choices["Giant Ancestry"]["options"]
        assert any("Hill's Tumble" in opt for opt in options)

    def test_giant_ancestry_has_stones_endurance(self, goliath_builder):
        """Test Stone's Endurance option is available"""
        choices = goliath_builder.get_species_trait_choices()
        options = choices["Giant Ancestry"]["options"]
        assert any("Stone's Endurance" in opt for opt in options)

    def test_giant_ancestry_has_storms_thunder(self, goliath_builder):
        """Test Storm's Thunder option is available"""
        choices = goliath_builder.get_species_trait_choices()
        options = choices["Giant Ancestry"]["options"]
        assert any("Storm's Thunder" in opt for opt in options)


class TestGoliathNoPassiveEffects:
    """Test that Goliath has no passive mechanical effects"""

    def test_goliath_no_applied_effects(self, goliath_builder):
        """Test Goliath has no applied effects (all traits are resource-based)"""
        applied_effects = getattr(goliath_builder, "applied_effects", [])
        assert len(applied_effects) == 0

    def test_goliath_no_resistances(self, goliath_builder):
        """Test Goliath has no damage resistances"""
        char_data = goliath_builder.character_data
        assert len(char_data.get("resistances", [])) == 0

    def test_goliath_no_condition_immunities(self, goliath_builder):
        """Test Goliath has no condition immunities"""
        char_data = goliath_builder.character_data
        assert len(char_data.get("condition_immunities", [])) == 0


class TestGoliathClassIntegration:
    """Test Goliath integration with classes"""

    def test_goliath_fighter_preserves_traits(self):
        """Test setting Fighter class preserves Goliath traits"""
        builder = CharacterBuilder()
        builder.set_species("Goliath")
        builder.set_class("Fighter", 1)
        char_data = builder.character_data

        assert char_data["class"] == "Fighter"
        assert char_data["species"] == "Goliath"
        assert char_data["speed"] == 35
        assert char_data["darkvision"] == 0

    def test_goliath_barbarian_preserves_traits(self):
        """Test setting Barbarian class preserves Goliath traits"""
        builder = CharacterBuilder()
        builder.set_species("Goliath")
        builder.set_class("Barbarian", 1)
        char_data = builder.character_data

        assert char_data["class"] == "Barbarian"
        assert char_data["species"] == "Goliath"
        assert char_data["speed"] == 35

        # Languages still present
        languages = char_data["proficiencies"]["languages"]
        assert "Common" in languages
        assert "Giant" not in languages

    def test_goliath_with_class_features_intact(self):
        """Test Goliath species features remain after setting a class"""
        builder = CharacterBuilder()
        builder.set_species("Goliath")
        builder.set_class("Fighter", 5)
        char_data = builder.character_data

        species_features = char_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]
        assert "Giant Ancestry" in feature_names
        assert "Large Form" in feature_names
        assert "Powerful Build" in feature_names
