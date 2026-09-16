"""Tests for class-level ASI / general feat picker (Issue: ClassStep shows no ASI / general feat picker at level 4)."""
import pytest
from modules.character_builder import CharacterBuilder

BASE_CHOICES = {
    "character_name": "ASI Test",
    "species": "Human",
    "background": "Soldier",
    "ability_scores": {
        "Strength": 15, "Dexterity": 13, "Constitution": 14,
        "Intelligence": 10, "Wisdom": 12, "Charisma": 8
    },
    "background_bonuses": {"Strength": 2, "Constitution": 1},
}

CLASSES = ["Fighter", "Wizard", "Ranger", "Barbarian", "Bard", "Cleric",
           "Druid", "Monk", "Paladin", "Rogue", "Sorcerer", "Warlock"]


class TestClassFeatPickerInChoices:
    """get_class_features_and_choices() returns a feat picker choice at level 4+."""

    @pytest.mark.parametrize("class_name", CLASSES)
    def test_level_4_feat_picker_present(self, class_name):
        builder = CharacterBuilder()
        builder.apply_choices({**BASE_CHOICES, "class": class_name, "level": 4})
        data = builder.get_class_features_and_choices()
        keys = [c.get("choice_key") for c in data["choices"]]
        assert "class_feat_4" in keys, f"{class_name}: no class_feat_4 choice"

    @pytest.mark.parametrize("class_name", CLASSES)
    def test_level_4_options_include_asi(self, class_name):
        builder = CharacterBuilder()
        builder.apply_choices({**BASE_CHOICES, "class": class_name, "level": 4})
        data = builder.get_class_features_and_choices()
        feat_choice = next(
            (c for c in data["choices"] if c.get("choice_key") == "class_feat_4"), None
        )
        assert feat_choice is not None
        assert "Ability Score Improvement" in feat_choice["options"]


class TestClassFeatEffectsApplied:
    """Selecting a feat at class level applies effects."""

    def test_asi_plus_2_applied_via_class_feat(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            **BASE_CHOICES,
            "class": "Fighter",
            "level": 4,
            "class_feat_4": "Ability Score Improvement",
            "class_feat_4_ability_plus_2": "Strength",
        })
        char = builder.to_character()
        str_score = char["abilities"]["strength"]["score"]
        # Base 15, bg bonus 2, ASI +2 = 19
        assert str_score == 19

    def test_asi_feat_appears_in_features_feats(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            **BASE_CHOICES,
            "class": "Fighter",
            "level": 4,
            "class_feat_4": "Ability Score Improvement",
        })
        char = builder.to_character()
        feat_names = [f["name"] for f in char.get("features", {}).get("feats", [])]
        assert "Ability Score Improvement" in feat_names

    def test_level_8_separate_from_level_4(self):
        """Two ASI slots are independent."""
        builder = CharacterBuilder()
        builder.apply_choices({
            **BASE_CHOICES,
            "class": "Fighter",
            "level": 8,
            "class_feat_4": "Ability Score Improvement",
            "class_feat_4_ability_plus_2": "Strength",
            "class_feat_8": "Ability Score Improvement",
            "class_feat_8_ability_plus_2": "Dexterity",
        })
        char = builder.to_character()
        str_score = char["abilities"]["strength"]["score"]
        dex_score = char["abilities"]["dexterity"]["score"]
        # STR: 15 + 2(bg) + 2(ASI) = 19
        assert str_score == 19
        # DEX: 13 + 2(ASI) = 15
        assert dex_score == 15

    def test_asi_plus_1_to_two_abilities_applied_via_class_feat(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            **BASE_CHOICES,
            "class": "Fighter",
            "level": 4,
            "class_feat_4": "Ability Score Improvement",
            "class_feat_4_asi_option": "+1 to two abilities",
            "class_feat_4_abilities_plus_1": ["Dexterity", "Wisdom"],
        })
        char = builder.to_character()
        assert char["abilities"]["dexterity"]["score"] == 14
        assert char["abilities"]["wisdom"]["score"] == 13

    def test_asi_stale_opposite_branch_values_are_ignored(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            **BASE_CHOICES,
            "class": "Fighter",
            "level": 4,
            "class_feat_4": "Ability Score Improvement",
            "class_feat_4_asi_option": "+2 to one ability",
            "class_feat_4_ability_plus_2": "Strength",
            "class_feat_4_abilities_plus_1": ["Dexterity", "Wisdom"],
        })
        char = builder.to_character()
        assert char["abilities"]["strength"]["score"] == 19
        assert char["abilities"]["dexterity"]["score"] == 13
        assert char["abilities"]["wisdom"]["score"] == 12


class TestClassFeatSubChoicesInNestedChoices:
    """When a class-level feat is selected, sub-choices appear in get_class_features_and_choices()."""

    def test_asi_sub_choices_appear_when_feat_selected(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            **BASE_CHOICES,
            "class": "Fighter",
            "level": 4,
            "class_feat_4": "Ability Score Improvement",
        })
        data = builder.get_class_features_and_choices()
        keys = [c.get("choice_key") for c in data["choices"]]
        # ASI sub-choices should now appear
        assert any(k and k.startswith("class_feat_4_") for k in keys)
        by_key = {c.get("choice_key"): c for c in data["choices"]}
        assert by_key["class_feat_4_ability_plus_2"]["depends_on"] == "class_feat_4_asi_option"
        assert by_key["class_feat_4_ability_plus_2"]["depends_on_value"] == "+2 to one ability"
        assert by_key["class_feat_4_abilities_plus_1"]["depends_on"] == "class_feat_4_asi_option"
        assert by_key["class_feat_4_abilities_plus_1"]["depends_on_value"] == "+1 to two abilities"
