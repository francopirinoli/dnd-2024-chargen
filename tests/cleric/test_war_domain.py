#!/usr/bin/env python3
"""
Unit tests for the War Domain cleric subclass.
Tests all features, effects, and mechanics specific to the War Domain.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def war_cleric_builder():
    """Fixture providing a fresh CharacterBuilder with War Domain cleric setup"""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Cleric", 3)
    builder.set_subclass("War Domain")
    return builder


class TestWarDomain:
    """Test War Domain subclass implementation"""

    def test_war_domain_level_3_features(self, war_cleric_builder):
        """Test War Domain features are present at level 3"""
        char_data = war_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Guided Strike" in feature_names
        assert "War Domain Spells" in feature_names
        assert "War Priest" in feature_names

    def test_guided_strike_feature(self, war_cleric_builder):
        """Test Guided Strike Channel Divinity feature description"""
        char_data = war_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]

        guided_feature = next(
            f for f in subclass_features if f["name"] == "Guided Strike"
        )
        description = guided_feature["description"]
        assert "channel divinity" in description.lower()
        assert "+10 bonus" in description.lower()

    def test_war_priest_feature(self, war_cleric_builder):
        """Test War Priest feature description"""
        char_data = war_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]

        war_priest_feature = next(
            f for f in subclass_features if f["name"] == "War Priest"
        )
        description = war_priest_feature["description"]
        assert "bonus action" in description.lower()
        assert "attack" in description.lower()

    def test_war_domain_level_3_spells(self, war_cleric_builder):
        """Test War Domain spells at level 3"""
        char_data = war_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        assert "Guiding Bolt" in always_prepared
        assert "Magic Weapon" in always_prepared
        assert "Shield of Faith" in always_prepared
        assert "Spiritual Weapon" in always_prepared

    def test_war_domain_level_5_spells(self, war_cleric_builder):
        """Test War Domain gains level 5 domain spells"""
        war_cleric_builder.set_class("Cleric", 5)
        char_data = war_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        # Should still have level 3 spells
        assert "Guiding Bolt" in always_prepared
        assert "Shield of Faith" in always_prepared

        # Should now have level 5 domain spells
        assert "Crusader's Mantle" in always_prepared
        assert "Spirit Guardians" in always_prepared

    def test_war_domain_level_7_spells(self, war_cleric_builder):
        """Test War Domain gains level 7 domain spells"""
        war_cleric_builder.set_class("Cleric", 7)
        char_data = war_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        assert "Fire Shield" in always_prepared
        assert "Freedom of Movement" in always_prepared

    def test_war_domain_level_9_spells(self, war_cleric_builder):
        """Test War Domain gains level 9 domain spells"""
        war_cleric_builder.set_class("Cleric", 9)
        char_data = war_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        assert "Hold Monster" in always_prepared
        assert "Steel Wind Strike" in always_prepared

    def test_war_gods_blessing_at_level_6(self, war_cleric_builder):
        """Test War God's Blessing feature appears at level 6"""
        war_cleric_builder.set_class("Cleric", 6)
        char_data = war_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "War God's Blessing" in feature_names

        blessing_feature = next(
            f for f in subclass_features if f["name"] == "War God's Blessing"
        )
        description = blessing_feature["description"]
        assert "channel divinity" in description.lower()
        assert "shield of faith" in description.lower()

    def test_avatar_of_battle_at_level_17(self, war_cleric_builder):
        """Test Avatar of Battle feature appears at level 17"""
        war_cleric_builder.set_class("Cleric", 17)
        char_data = war_cleric_builder.character_data
        subclass_features = char_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Avatar of Battle" in feature_names

        avatar_feature = next(
            f for f in subclass_features if f["name"] == "Avatar of Battle"
        )
        assert "resistance" in avatar_feature["description"].lower()

    def test_avatar_of_battle_grants_resistances(self, war_cleric_builder):
        """Test Avatar of Battle grants Bludgeoning, Piercing, Slashing resistance"""
        war_cleric_builder.set_class("Cleric", 17)
        char_data = war_cleric_builder.character_data
        resistances = char_data["resistances"]

        assert "Bludgeoning" in resistances
        assert "Piercing" in resistances
        assert "Slashing" in resistances

    def test_avatar_of_battle_resistances_not_before_17(self, war_cleric_builder):
        """Test that physical damage resistances are NOT present before level 17"""
        war_cleric_builder.set_class("Cleric", 16)
        char_data = war_cleric_builder.character_data
        resistances = char_data["resistances"]

        assert "Bludgeoning" not in resistances
        assert "Piercing" not in resistances
        assert "Slashing" not in resistances

    def test_war_domain_spell_progression_cumulative(self, war_cleric_builder):
        """Test that all previous domain spells remain when leveling up"""
        war_cleric_builder.set_class("Cleric", 9)
        char_data = war_cleric_builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        # All domain spells from levels 3 through 9 should be present
        expected_spells = [
            "Guiding Bolt", "Magic Weapon", "Shield of Faith", "Spiritual Weapon",
            "Crusader's Mantle", "Spirit Guardians",
            "Fire Shield", "Freedom of Movement",
            "Hold Monster", "Steel Wind Strike",
        ]
        for spell in expected_spells:
            assert spell in always_prepared, f"{spell} missing at level 9"
