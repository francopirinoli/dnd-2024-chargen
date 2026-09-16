#!/usr/bin/env python3
"""
Unit tests for the Life Domain cleric subclass.
Tests all features, effects, and mechanics specific to the Life Domain.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def life_cleric_builder():
    """Fixture providing a fresh CharacterBuilder with Life Domain cleric setup"""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Cleric", 3)
    builder.set_subclass("Life Domain")
    return builder


class TestLifeDomain:
    """Test Life Domain subclass implementation"""

    def test_life_domain_effects(self, life_cleric_builder):
        """Test Life Domain specific effects"""
        char_data = life_cleric_builder.character_data

        # Check domain spells - Life Domain should have Aid, Bless, Cure Wounds, Lesser Restoration at level 3
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Aid" in always_prepared
        assert "Bless" in always_prepared
        assert "Cure Wounds" in always_prepared
        assert "Lesser Restoration" in always_prepared

        # Check spell metadata (domain spells should be always prepared)
        spell_metadata = char_data.get("spell_metadata", {})
        if "Bless" in spell_metadata:
            assert spell_metadata["Bless"]["source"] == "Life Domain"

    def test_domain_spell_scaling(self, life_cleric_builder):
        """Test that domain spells are gained at appropriate levels"""
        # At level 3, should have all level 3 domain spells (in D&D 2024, Life Domain gets 4 spells at level 3)
        char_data = life_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Aid" in always_prepared
        assert "Bless" in always_prepared
        assert "Cure Wounds" in always_prepared
        assert "Lesser Restoration" in always_prepared

        # Level up to 5, should gain level 5 domain spells
        life_cleric_builder.set_class("Cleric", 5)
        char_data = life_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        # Should still have level 3 spells (all 4 domain spells are available at level 3)
        assert "Aid" in always_prepared
        assert "Bless" in always_prepared
        assert "Cure Wounds" in always_prepared
        assert "Lesser Restoration" in always_prepared

        # Should now have level 5 domain spells
        assert "Mass Healing Word" in always_prepared
        assert "Revivify" in always_prepared

    def test_life_domain_features(self, life_cleric_builder):
        """Test Life Domain specific features are present"""
        char_data = life_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        # Life Domain should have these features at level 3
        assert "Disciple of Life" in feature_names
        assert "Domain Spells" in feature_names
        assert "Preserve Life" in feature_names

    def test_disciple_of_life_feature(self, life_cleric_builder):
        """Test Disciple of Life feature details"""
        char_data = life_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]

        disciple_feature = None
        for feature in subclass_features:
            if feature["name"] == "Disciple of Life":
                disciple_feature = feature
                break

        assert disciple_feature is not None
        description = disciple_feature["description"]
        assert "restores hit points" in description.lower()
        assert "additional hit points" in description.lower()

    def test_preserve_life_feature(self, life_cleric_builder):
        """Test Preserve Life Channel Divinity feature"""
        char_data = life_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]

        preserve_life_feature = None
        for feature in subclass_features:
            if feature["name"] == "Preserve Life":
                preserve_life_feature = feature
                break

        assert preserve_life_feature is not None
        description = preserve_life_feature["description"]
        assert "channel divinity" in description.lower()
        assert "hit points" in description.lower()
