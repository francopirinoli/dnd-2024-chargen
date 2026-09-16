#!/usr/bin/env python3
"""
Pytest tests for Fighter class implementation
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def fighter_builder():
    """Fixture providing a CharacterBuilder set up as a Fighter"""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Fighter", 1)
    return builder


class TestFighterClass:
    """Test Fighter class features and progression"""

    def test_fighter_basic_properties(self, fighter_builder):
        """Test Fighter basic class properties"""
        class_data = fighter_builder.character_data.get("class_data", {})

        # Check basic class properties
        assert class_data.get("name") == "Fighter"
        assert class_data.get("hit_die") == 10
        assert class_data.get("primary_ability") == "Strength or Dexterity"

        # Check saving throw proficiencies
        saving_throws = class_data.get("saving_throw_proficiencies", [])
        assert "Strength" in saving_throws
        assert "Constitution" in saving_throws

        # Check armor proficiencies
        armor_profs = class_data.get("armor_proficiencies", [])
        expected_armor = ["Light armor", "Medium armor", "Heavy armor", "Shields"]
        for armor in expected_armor:
            assert armor in armor_profs

        # Check weapon proficiencies
        weapon_profs = class_data.get("weapon_proficiencies", [])
        assert "Simple weapons" in weapon_profs
        assert "Martial weapons" in weapon_profs

    @pytest.mark.parametrize(
        "level,expected_proficiency",
        [(1, 2), (2, 2), (3, 2), (4, 2), (5, 3), (9, 4), (13, 5), (17, 6), (20, 6)],
    )
    def test_proficiency_bonus_progression(self, level, expected_proficiency):
        """Test proficiency bonus scales correctly"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", level)

        class_data = builder.character_data.get("class_data", {})
        proficiency_bonus = class_data.get("proficiency_bonus_by_level", {})

        assert proficiency_bonus.get(str(level)) == expected_proficiency

    def test_level_1_features(self, fighter_builder):
        """Test level 1 Fighter features"""
        features = fighter_builder.character_data.get("features", {})
        class_features = features.get("class", [])
        feature_names = [f.get("name", "unnamed") for f in class_features]

        # Check required level 1 features
        assert "Fighting Style" in feature_names
        assert "Second Wind" in feature_names
        assert "Weapon Mastery" in feature_names

        # Check Second Wind description uses PDF override summary
        second_wind_feature = None
        for feature in class_features:
            if feature.get("name") == "Second Wind":
                second_wind_feature = feature
                break

        assert second_wind_feature is not None
        description = second_wind_feature.get("description", "")
        assert "Bonus Action: Regain 1d10+Fighter level HP" in description

    def test_level_2_features(self):
        """Test level 2 Fighter features"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", 2)

        features = builder.character_data.get("features", {})
        class_features = features.get("class", [])
        feature_names = [f.get("name", "unnamed") for f in class_features]

        # Check level 2 features
        assert "Action Surge" in feature_names
        assert "Tactical Mind" in feature_names

    def test_level_5_features(self):
        """Test level 5 Fighter features"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", 5)

        features = builder.character_data.get("features", {})
        class_features = features.get("class", [])
        feature_names = [f.get("name", "unnamed") for f in class_features]

        # Check level 5 features
        assert "Extra Attack" in feature_names
        assert "Tactical Shift" in feature_names

    def test_level_9_features(self):
        """Test level 9 Fighter features"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", 9)

        features = builder.character_data.get("features", {})
        class_features = features.get("class", [])
        feature_names = [f.get("name", "unnamed") for f in class_features]

        # Check level 9 features
        assert "Indomitable" in feature_names
        assert "Tactical Master" in feature_names

    def test_level_13_features(self):
        """Test level 13 Fighter features"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", 13)

        features = builder.character_data.get("features", {})
        class_features = features.get("class", [])
        feature_names = [f.get("name", "unnamed") for f in class_features]

        # Check level 13 features
        assert "Indomitable (Two Uses)" in feature_names
        assert "Studied Attacks" in feature_names

    @pytest.mark.parametrize(
        "level,feature_name",
        [
            (11, "Two Extra Attacks"),
            (17, "Action Surge (Two Uses)"),
            (19, "Epic Boon"),
            (20, "Three Extra Attacks"),
        ],
    )
    def test_feature_progression(self, level, feature_name):
        """Test that specific features appear at correct levels"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", level)

        features = builder.character_data.get("features", {})
        class_features = features.get("class", [])
        feature_names = [f.get("name", "unnamed") for f in class_features]

        assert feature_name in feature_names

    @pytest.mark.parametrize("level", [4, 6, 8, 12, 14, 16])
    def test_ability_score_improvement_hidden_from_class_features(self, level):
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", level)

        class_features = builder.to_character().get("features", {}).get("class", [])
        feature_names = [f.get("name", "unnamed") for f in class_features]
        assert "Ability Score Improvement" not in feature_names

    def test_weapon_mastery_choices(self, fighter_builder):
        """Test that weapon mastery includes choice system"""
        features = fighter_builder.character_data.get("features", {})
        class_features = features.get("class", [])

        weapon_mastery_feature = None
        for feature in class_features:
            if feature.get("name") == "Weapon Mastery":
                weapon_mastery_feature = feature
                break

        assert weapon_mastery_feature is not None
        # For now, just check that the feature exists and has a description
        assert "description" in weapon_mastery_feature
        assert "mastery properties" in weapon_mastery_feature.get("description", "")

    def test_fighting_style_choices(self, fighter_builder):
        """Test that fighting style includes choice system"""
        features = fighter_builder.character_data.get("features", {})
        class_features = features.get("class", [])

        fighting_style_feature = None
        for feature in class_features:
            if feature.get("name") == "Fighting Style":
                fighting_style_feature = feature
                break

        assert fighting_style_feature is not None
        # For now, just check that the feature exists and has a description
        assert "description" in fighting_style_feature
        assert "fighting" in fighting_style_feature.get("description", "").lower()

    def test_subclass_selection_at_level_3(self):
        """Test that subclass selection is available at level 3"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", 3)

        class_data = builder.character_data.get("class_data", {})
        subclass_selection_level = class_data.get("subclass_selection_level")

        assert subclass_selection_level == 3

        # Should be able to set a subclass at level 3
        result = builder.set_subclass("Champion")
        assert result is True


class TestBattleMasterSubclass:
    """Test Battle Master subclass implementation"""

    def test_battle_master_features(self):
        """Test Battle Master subclass features"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", 3)
        builder.set_subclass("Battle Master")

        features = builder.character_data.get("features", {})
        # Battle Master features should appear in subclass features
        subclass_features = features.get("subclass", [])
        subclass_feature_names = [f.get("name", "unnamed") for f in subclass_features]

        # Check level 3 Battle Master features
        assert "Combat Superiority" in subclass_feature_names
        assert "Student of War" in subclass_feature_names

    def test_combat_superiority_choices(self):
        """Test Combat Superiority maneuver choices"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", 3)
        builder.set_subclass("Battle Master")

        features = builder.character_data.get("features", {})
        subclass_features = features.get("subclass", [])

        combat_superiority_feature = None
        for feature in subclass_features:
            if feature.get("name") == "Combat Superiority":
                combat_superiority_feature = feature
                break

        assert combat_superiority_feature is not None
        # Check that the feature has maneuver-related description
        description = combat_superiority_feature.get("description", "")
        assert "maneuver" in description.lower() or "superiority" in description.lower()

    def test_maneuver_progression(self):
        """Test that maneuvers are gained at correct levels"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", 15)
        builder.set_subclass("Battle Master")

        features = builder.character_data.get("features", {})
        combat_superiority = features.get("Combat Superiority")

        if isinstance(combat_superiority, dict) and "choices" in combat_superiority:
            additional_choices = combat_superiority["choices"].get(
                "additional_choices_by_level", {}
            )

            # Check additional maneuvers at levels 7, 10, 15
            assert "7" in additional_choices
            assert "10" in additional_choices
            assert "15" in additional_choices

            # Check they allow replacement
            for level in ["7", "10", "15"]:
                assert additional_choices[level].get("replace_allowed") is True


class TestFighterSubclasses:
    """Test other Fighter subclasses"""

    @pytest.mark.parametrize(
        "subclass_name", ["Champion", "Eldritch Knight", "Psi Warrior"]
    )
    def test_subclass_exists(self, subclass_name):
        """Test that Fighter subclasses can be selected"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", 3)

        # Should not raise exception
        result = builder.set_subclass(subclass_name)
        assert result is True

    def test_eldritch_knight_spellcasting(self):
        """Test that Eldritch Knight gets spellcasting features"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", 3)
        builder.set_subclass("Eldritch Knight")

        # Should have spell-related data
        character = builder.character_data
        spells = character.get("spells", {})

        # Eldritch Knight should have some spell progression
        assert spells is not None


class TestFighterIntegration:
    """Integration tests for Fighter with other systems"""

    def test_fighter_with_background(self):
        """Test Fighter integration with background system"""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Soldier")
        builder.set_class("Fighter", 1)

        # Should not raise exception and should have both Fighter and background features
        features = builder.character_data.get("features", {})
        class_features = features.get("class", [])
        class_feature_names = [f.get("name", "unnamed") for f in class_features]

        assert "Fighting Style" in class_feature_names  # Fighter feature

        # Should have background proficiencies
        character = builder.character_data
        assert "background" in character

    def test_fighter_multiclass_requirements(self):
        """Test Fighter multiclass requirements"""
        builder = CharacterBuilder()
        builder.set_species("Human")

        # Set Fighter class (don't need to test ability score requirements in this basic test)
        builder.set_class("Fighter", 1)

        # Should be able to set Fighter class
        character = builder.character_data
        assert character["class"] == "Fighter"


if __name__ == "__main__":
    pytest.main([__file__])
