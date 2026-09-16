#!/usr/bin/env python3
"""
Unit tests for the Light Domain cleric subclass.
Tests all features, effects, and mechanics specific to the Light Domain.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def light_cleric_builder():
    """Fixture providing a fresh CharacterBuilder with Light Domain cleric setup"""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Cleric", 3)
    builder.set_subclass("Light Domain")
    return builder


class TestLightDomain:
    """Test Light Domain subclass implementation"""

    def test_light_domain_effects(self, light_cleric_builder):
        """Test Light Domain specific effects"""
        char_data = light_cleric_builder.character_data

        # Check domain spells — all four min_level:3 spells at level 3
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Burning Hands" in always_prepared
        assert "Faerie Fire" in always_prepared
        assert "Scorching Ray" in always_prepared
        assert "See Invisibility" in always_prepared

    def test_light_domain_features(self, light_cleric_builder):
        """Test Light Domain specific features are present"""
        char_data = light_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        # Light Domain should have these features at level 3
        assert "Light Domain Spells" in feature_names
        assert "Warding Flare" in feature_names
        assert "Radiance of the Dawn" in feature_names

    def test_warding_flare_feature(self, light_cleric_builder):
        """Test Warding Flare feature"""
        char_data = light_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]

        warding_flare_feature = None
        for feature in subclass_features:
            if feature["name"] == "Warding Flare":
                warding_flare_feature = feature
                break

        assert warding_flare_feature is not None
        description = warding_flare_feature["description"]
        assert "reaction" in description.lower()
        assert "disadvantage" in description.lower()

    def test_radiance_of_the_dawn_feature(self, light_cleric_builder):
        """Test Radiance of the Dawn Channel Divinity feature at level 3"""
        char_data = light_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]

        radiance_feature = None
        for feature in subclass_features:
            if feature["name"] == "Radiance of the Dawn":
                radiance_feature = feature
                break

        assert radiance_feature is not None
        description = radiance_feature["description"]
        assert "channel divinity" in description.lower()
        assert "radiant damage" in description.lower()
        assert "constitution saving throw" in description.lower()

    def test_light_domain_spell_progression(self, light_cleric_builder):
        """Test Light Domain spell progression at different levels"""
        # At level 3, should have all min_level:3 domain spells
        char_data = light_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Burning Hands" in always_prepared
        assert "Faerie Fire" in always_prepared
        assert "Scorching Ray" in always_prepared
        assert "See Invisibility" in always_prepared

        # Level up to 5, should gain level 5 domain spells
        light_cleric_builder.set_class("Cleric", 5)
        char_data = light_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        # Should still have level 3 spells
        assert "Burning Hands" in always_prepared
        assert "Faerie Fire" in always_prepared

        # Should now have level 5 domain spells
        assert "Daylight" in always_prepared
        assert "Fireball" in always_prepared

    def test_light_domain_level_7_spells(self, light_cleric_builder):
        """Test Light Domain gains level 7 domain spells"""
        light_cleric_builder.set_class("Cleric", 7)
        char_data = light_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        assert "Arcane Eye" in always_prepared
        assert "Wall of Fire" in always_prepared

    def test_light_domain_level_9_spells(self, light_cleric_builder):
        """Test Light Domain gains level 9 domain spells"""
        light_cleric_builder.set_class("Cleric", 9)
        char_data = light_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        assert "Flame Strike" in always_prepared
        assert "Scrying" in always_prepared

    def test_improved_warding_flare_at_level_6(self, light_cleric_builder):
        """Test Improved Warding Flare feature appears at level 6"""
        light_cleric_builder.set_class("Cleric", 6)
        char_data = light_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Improved Warding Flare" in feature_names

        improved_feature = next(
            f for f in subclass_features if f["name"] == "Improved Warding Flare"
        )
        assert "temporary hit points" in improved_feature["description"].lower()

    def test_corona_of_light_at_level_17(self, light_cleric_builder):
        """Test Corona of Light feature appears at level 17"""
        light_cleric_builder.set_class("Cleric", 17)
        char_data = light_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Corona of Light" in feature_names

        corona_feature = next(
            f for f in subclass_features if f["name"] == "Corona of Light"
        )
        assert "sunlight" in corona_feature["description"].lower()
        assert "bright light" in corona_feature["description"].lower()
