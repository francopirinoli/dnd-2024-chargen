#!/usr/bin/env python3
"""
Unit tests for the Trickery Domain cleric subclass.
Tests all features, effects, and mechanics specific to the Trickery Domain.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def trickery_cleric_builder():
    """Fixture providing a fresh CharacterBuilder with Trickery Domain cleric setup"""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Cleric", 3)
    builder.set_subclass("Trickery Domain")
    return builder


class TestTrickeryDomain:
    """Test Trickery Domain subclass implementation"""

    def test_trickery_domain_level_3_features(self, trickery_cleric_builder):
        """Test Trickery Domain features are present at level 3"""
        char_data = trickery_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Blessing of the Trickster" in feature_names
        assert "Trickery Domain Spells" in feature_names
        assert "Invoke Duplicity" in feature_names

    def test_blessing_of_the_trickster_feature(self, trickery_cleric_builder):
        """Test Blessing of the Trickster feature description"""
        char_data = trickery_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]

        blessing_feature = next(
            f for f in subclass_features if f["name"] == "Blessing of the Trickster"
        )
        description = blessing_feature["description"]
        assert "advantage" in description.lower()
        assert "stealth" in description.lower()

    def test_invoke_duplicity_feature(self, trickery_cleric_builder):
        """Test Invoke Duplicity Channel Divinity feature"""
        char_data = trickery_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]

        invoke_feature = next(
            f for f in subclass_features if f["name"] == "Invoke Duplicity"
        )
        description = invoke_feature["description"]
        assert "channel divinity" in description.lower()
        assert "illusion" in description.lower()

    def test_trickery_domain_level_3_spells(self, trickery_cleric_builder):
        """Test Trickery Domain spells at level 3"""
        char_data = trickery_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        assert "Charm Person" in always_prepared
        assert "Disguise Self" in always_prepared
        assert "Invisibility" in always_prepared
        assert "Pass without Trace" in always_prepared

    def test_trickery_domain_level_5_spells(self, trickery_cleric_builder):
        """Test Trickery Domain gains level 5 domain spells"""
        trickery_cleric_builder.set_class("Cleric", 5)
        char_data = trickery_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        # Should still have level 3 spells
        assert "Charm Person" in always_prepared
        assert "Disguise Self" in always_prepared

        # Should now have level 5 domain spells
        assert "Hypnotic Pattern" in always_prepared
        assert "Nondetection" in always_prepared

    def test_trickery_domain_level_7_spells(self, trickery_cleric_builder):
        """Test Trickery Domain gains level 7 domain spells"""
        trickery_cleric_builder.set_class("Cleric", 7)
        char_data = trickery_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        assert "Confusion" in always_prepared
        assert "Dimension Door" in always_prepared

    def test_trickery_domain_level_9_spells(self, trickery_cleric_builder):
        """Test Trickery Domain gains level 9 domain spells"""
        trickery_cleric_builder.set_class("Cleric", 9)
        char_data = trickery_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        assert "Dominate Person" in always_prepared
        assert "Modify Memory" in always_prepared

    def test_tricksters_transposition_at_level_6(self, trickery_cleric_builder):
        """Test Trickster's Transposition feature appears at level 6"""
        trickery_cleric_builder.set_class("Cleric", 6)
        char_data = trickery_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Trickster's Transposition" in feature_names

        transposition_feature = next(
            f for f in subclass_features if f["name"] == "Trickster's Transposition"
        )
        assert "teleport" in transposition_feature["description"].lower()

    def test_improved_duplicity_at_level_17(self, trickery_cleric_builder):
        """Test Improved Duplicity feature appears at level 17"""
        trickery_cleric_builder.set_class("Cleric", 17)
        char_data = trickery_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Improved Duplicity" in feature_names

        improved_feature = next(
            f for f in subclass_features if f["name"] == "Improved Duplicity"
        )
        description = improved_feature["description"]
        assert "advantage" in description.lower()
        assert "hit points" in description.lower()

    def test_trickery_domain_spell_progression_cumulative(self, trickery_cleric_builder):
        """Test that all previous domain spells remain when leveling up"""
        trickery_cleric_builder.set_class("Cleric", 9)
        char_data = trickery_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        # All domain spells from levels 3 through 9 should be present
        expected_spells = [
            "Charm Person", "Disguise Self", "Invisibility", "Pass without Trace",
            "Hypnotic Pattern", "Nondetection",
            "Confusion", "Dimension Door",
            "Dominate Person", "Modify Memory",
        ]
        for spell in expected_spells:
            assert spell in always_prepared, f"{spell} missing at level 9"
