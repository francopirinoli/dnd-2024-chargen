#!/usr/bin/env python3
"""
Pytest tests for CharacterBuilder functionality
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def character_builder():
    """Fixture providing a fresh CharacterBuilder for each test"""
    return CharacterBuilder()


def test_wood_elf_cantrip(character_builder):
    """Test that Wood Elf gets Druidcraft cantrip"""
    # Set species and lineage
    assert character_builder.set_species("Elf") is True
    assert (
        character_builder.set_lineage("Wood Elf", spellcasting_ability="Wisdom") is True
    )

    # Check character data
    character = character_builder.character_data
    assert character["species"] == "Elf"
    assert character["lineage"] == "Wood Elf"

    # Check that Druidcraft cantrip was added (in always_prepared from grant_cantrip effect)
    always_prepared = character.get("spells", {}).get("always_prepared", {})
    assert "Druidcraft" in always_prepared


def test_basic_character_creation(character_builder):
    """Test basic character creation flow"""
    # Test species setting
    assert character_builder.set_species("Human") is True
    assert character_builder.character_data["species"] == "Human"

    # Test class setting
    assert character_builder.set_class("Fighter", 1) is True
    assert character_builder.character_data["class"] == "Fighter"
    assert character_builder.character_data["level"] == 1


def test_level_progression(character_builder):
    """Test character level progression"""
    # Set up a basic character
    character_builder.set_species("Human")
    character_builder.set_class("Fighter", 1)

    # Test leveling up
    character_builder.set_class("Fighter", 2)
    assert character_builder.character_data["level"] == 2

    character_builder.set_class("Fighter", 5)
    assert character_builder.character_data["level"] == 5


def test_proficiencies_system(character_builder):
    """Test that proficiencies are properly applied"""
    character_builder.set_species("Human")
    character_builder.set_class("Fighter", 1)

    char_data = character_builder.character_data

    # Check that Fighter gets expected proficiencies
    armor_profs = char_data["proficiencies"]["armor"]
    assert "Heavy armor" in armor_profs

    weapon_profs = char_data["proficiencies"]["weapons"]
    assert "Martial weapons" in weapon_profs

    saving_throws = char_data["proficiencies"]["saving_throws"]
    assert "Strength" in saving_throws
    assert "Constitution" in saving_throws


def test_unknown_ability_bonus_with_minimum_does_not_crash():
    """Unknown ability bonus entries should be ignored safely."""
    builder = CharacterBuilder()
    builder.apply_choices({
        "character_name": "Unknown Ability Bonus",
        "level": 1,
        "species": "Human",
        "class": "Fighter",
        "background": "Soldier",
        "ability_scores": {
            "Strength": 15, "Dexterity": 14, "Constitution": 13,
            "Intelligence": 10, "Wisdom": 12, "Charisma": 8,
        },
        "background_bonuses": {"Strength": 2, "Constitution": 1},
    })
    baseline_abilities = {
        name: data["score"] for name, data in builder.to_character()["abilities"].items()
    }

    builder.character_data.setdefault("ability_bonuses", []).append({
        "ability": "NotAStat",
        "value": 0,
        "minimum": 1,
    })

    character = builder.to_character()
    current_abilities = {
        name: data["score"] for name, data in character["abilities"].items()
    }
    assert current_abilities == baseline_abilities


def test_paladin_recommended_ability_scores(character_builder):
    """Test that Paladin uses predefined standard_array_assignment when 'recommended' is selected"""
    # Set up a basic Paladin
    character_builder.set_class("Paladin", 1)

    # Apply recommended ability scores (should use predefined assignment from JSON)
    character_builder.apply_choice("ability_scores_method", "recommended")

    # Get the result
    result = character_builder.to_json()
    actual_scores = result["ability_scores"]

    # Expected values from data/classes/paladin.json standard_array_assignment
    expected_scores = {
        "Strength": 15,
        "Dexterity": 10,
        "Constitution": 13,
        "Intelligence": 8,
        "Wisdom": 12,
        "Charisma": 14,
    }

    # Verify all scores match
    for ability, expected_value in expected_scores.items():
        assert actual_scores.get(ability) == expected_value, (
            f"Expected {ability} to be {expected_value}, got {actual_scores.get(ability)}"
        )


@pytest.mark.parametrize(
    "class_name,expected_scores",
    [
        (
            "Wizard",
            {
                "Strength": 8,
                "Dexterity": 12,
                "Constitution": 13,
                "Intelligence": 15,
                "Wisdom": 14,
                "Charisma": 10,
            },
        ),
        (
            "Fighter",
            {
                "Strength": 15,
                "Dexterity": 14,
                "Constitution": 13,
                "Intelligence": 8,
                "Wisdom": 10,
                "Charisma": 12,
            },
        ),
        (
            "Cleric",
            {
                "Strength": 14,
                "Dexterity": 8,
                "Constitution": 13,
                "Intelligence": 10,
                "Wisdom": 15,
                "Charisma": 12,
            },
        ),
        (
            "Rogue",
            {
                "Strength": 12,
                "Dexterity": 15,
                "Constitution": 13,
                "Intelligence": 14,
                "Wisdom": 10,
                "Charisma": 8,
            },
        ),
        (
            "Paladin",
            {
                "Strength": 15,
                "Dexterity": 10,
                "Constitution": 13,
                "Intelligence": 8,
                "Wisdom": 12,
                "Charisma": 14,
            },
        ),
    ],
)
def test_class_recommended_ability_scores(class_name, expected_scores):
    """Test that all classes use their predefined standard_array_assignment correctly"""
    builder = CharacterBuilder()
    builder.set_class(class_name, 1)
    builder.apply_choice("ability_scores_method", "recommended")

    result = builder.to_json()
    actual_scores = result["ability_scores"]

    # Verify all scores match expected values from class JSON
    assert actual_scores == expected_scores, (
        f"{class_name} ability scores don't match. Expected {expected_scores}, got {actual_scores}"
    )


def test_all_classes_have_standard_array():
    """Ensure all classes define standard_array_assignment in their JSON data"""
    import json
    from pathlib import Path

    classes_dir = Path(__file__).parent.parent.parent / "data" / "classes"

    for class_file in classes_dir.glob("*.json"):
        with open(class_file, "r") as f:
            class_data = json.load(f)

        class_name = class_data.get("name")
        assert "standard_array_assignment" in class_data, (
            f"{class_name} is missing standard_array_assignment"
        )

        assignment = class_data["standard_array_assignment"]

        # Verify it has all 6 abilities
        expected_abilities = {
            "Strength",
            "Dexterity",
            "Constitution",
            "Intelligence",
            "Wisdom",
            "Charisma",
        }
        actual_abilities = set(assignment.keys())
        assert actual_abilities == expected_abilities, (
            f"{class_name} standard_array_assignment is missing abilities: {expected_abilities - actual_abilities}"
        )

        # Verify values are from standard array [15, 14, 13, 12, 10, 8]
        values = sorted(assignment.values(), reverse=True)
        expected_values = [15, 14, 13, 12, 10, 8]
        assert values == expected_values, (
            f"{class_name} standard_array_assignment has invalid values: {values}"
        )


def test_manual_ability_score_assignment():
    """Test that manual ability score assignment works correctly"""
    builder = CharacterBuilder()
    builder.set_class("Wizard", 1)

    # Manually assign ability scores
    manual_scores = {
        "Strength": 10,
        "Dexterity": 14,
        "Constitution": 12,
        "Intelligence": 15,
        "Wisdom": 13,
        "Charisma": 8,
    }

    builder.apply_choice("ability_scores", manual_scores)

    result = builder.to_json()
    actual_scores = result["ability_scores"]

    # Verify manual assignment was used
    assert actual_scores == manual_scores, (
        f"Manual ability score assignment failed. Expected {manual_scores}, got {actual_scores}"
    )


def test_ability_scores_all_use_standard_array_values():
    """Test that recommended scores always use valid standard array values"""
    standard_array = [15, 14, 13, 12, 10, 8]

    # Test multiple classes
    for class_name in ["Wizard", "Fighter", "Cleric", "Rogue", "Paladin", "Barbarian"]:
        builder = CharacterBuilder()
        builder.set_class(class_name, 1)
        builder.apply_choice("ability_scores_method", "recommended")

        result = builder.to_json()
        actual_scores = result["ability_scores"]
        actual_values = sorted(actual_scores.values(), reverse=True)

        assert actual_values == standard_array, (
            f"{class_name} recommended scores don't use standard array. Got {actual_values}"
        )


def test_ability_scores_persist_through_serialization():
    """Test that ability scores are preserved through to_json/from_json"""
    builder = CharacterBuilder()
    builder.set_class("Paladin", 1)
    builder.apply_choice("ability_scores_method", "recommended")

    # Serialize and deserialize
    json_data = builder.to_json()

    new_builder = CharacterBuilder()
    new_builder.from_json(json_data)

    # Verify scores are preserved
    expected_scores = {
        "Strength": 15,
        "Dexterity": 10,
        "Constitution": 13,
        "Intelligence": 8,
        "Wisdom": 12,
        "Charisma": 14,
    }

    restored_data = new_builder.to_json()
    assert restored_data["ability_scores"] == expected_scores, (
        f"Ability scores not preserved through serialization. Expected {expected_scores}, got {restored_data['ability_scores']}"
    )


def test_rebuild_character_with_ability_scores_and_bonuses():
    """
    Regression test for bug where rebuilding from choices_made with both
    ability_scores and ability_scores_method would incorrectly overwrite
    custom scores and fail to apply background_bonuses.
    """
    choices_made = {
        "character_name": "Brianna",
        "level": 3,
        "class": "Paladin",
        "subclass": "Oath of Vengeance",
        "species": "Tiefling",
        "lineage": "Chthonic Tiefling",
        "background": "Folk Hero",
        "ability_scores": {
            "Strength": 15,
            "Dexterity": 12,
            "Constitution": 13,
            "Intelligence": 10,
            "Wisdom": 8,
            "Charisma": 14,
        },
        "ability_scores_method": "recommended",  # Should be ignored when ability_scores is present
        "background_bonuses": {"Strength": 2, "Constitution": 1},
        "skill_choices": ["Insight", "Persuasion"],
    }

    builder = CharacterBuilder()
    builder.apply_choices(choices_made)

    result = builder.to_json()

    # Expected: custom ability_scores + background_bonuses
    expected_scores = {
        "Strength": 17,  # 15 + 2
        "Dexterity": 12,  # 12 + 0
        "Constitution": 14,  # 13 + 1
        "Intelligence": 10,  # 10 + 0
        "Wisdom": 8,  # 8 + 0
        "Charisma": 14,  # 14 + 0
    }

    assert result["ability_scores"] == expected_scores, (
        f"Expected {expected_scores}, got {result['ability_scores']}"
    )
    assert result["choices_made"]["ability_scores_method"] == "recommended"


def test_ability_scores_method_only():
    """Test that ability_scores_method works when no explicit ability_scores provided"""
    choices = {
        "class": "Wizard",
        "level": 1,
        "ability_scores_method": "recommended",
        "background": "Sage",
        "background_bonuses": {"Intelligence": 2, "Wisdom": 1},
    }

    builder = CharacterBuilder()
    builder.apply_choices(choices)

    result = builder.to_json()

    # Should use Wizard standard array + background bonuses
    # Wizard standard: STR=8, DEX=12, CON=13, INT=15, WIS=14, CHA=10
    expected_scores = {
        "Strength": 8,
        "Dexterity": 12,
        "Constitution": 13,
        "Intelligence": 17,  # 15 + 2
        "Wisdom": 15,  # 14 + 1
        "Charisma": 10,
    }

    assert result["ability_scores"] == expected_scores, (
        f"Expected {expected_scores}, got {result['ability_scores']}"
    )


def test_explicit_ability_scores_overrides_method():
    """Test that explicit ability_scores takes precedence over ability_scores_method"""
    choices = {
        "class": "Fighter",
        "level": 1,
        "ability_scores": {
            "Strength": 14,
            "Dexterity": 13,
            "Constitution": 12,
            "Intelligence": 11,
            "Wisdom": 10,
            "Charisma": 8,
        },
        "ability_scores_method": "recommended",  # Should be ignored
        "background": "Soldier",
        "background_bonuses": {"Strength": 2, "Constitution": 1},
    }

    builder = CharacterBuilder()
    builder.apply_choices(choices)

    result = builder.to_json()

    # Should use custom scores (NOT Fighter standard array) + bonuses
    expected_scores = {
        "Strength": 16,  # 14 + 2
        "Dexterity": 13,
        "Constitution": 13,  # 12 + 1
        "Intelligence": 11,
        "Wisdom": 10,
        "Charisma": 8,
    }

    assert result["ability_scores"] == expected_scores, (
        f"Expected {expected_scores}, got {result['ability_scores']}"
    )


def test_manual_ability_scores_method_tracking():
    """
    Regression test: When user selects manual ability scores,
    ability_scores_method should be set to 'manual', not left as 'recommended'
    """
    builder = CharacterBuilder()

    # User initially selects recommended
    builder.apply_choice("class", "Wizard")
    builder.apply_choice("ability_scores_method", "recommended")

    result1 = builder.to_json()
    assert result1["choices_made"]["ability_scores_method"] == "recommended"

    # User goes back and changes to manual
    manual_scores = {
        "Strength": 10,
        "Dexterity": 12,
        "Constitution": 13,
        "Intelligence": 15,
        "Wisdom": 14,
        "Charisma": 8,
    }
    builder.apply_choice("ability_scores", manual_scores)
    builder.apply_choice("ability_scores_method", "manual")

    result2 = builder.to_json()
    # Should now show 'manual', not 'recommended'
    assert result2["choices_made"]["ability_scores_method"] == "manual", (
        f"Expected 'manual' but got '{result2['choices_made']['ability_scores_method']}'"
    )

    # Verify the manual scores are used
    assert result2["ability_scores"] == manual_scores

    # Add background bonuses
    builder.apply_choice("background", "Sage")
    builder.apply_choice("background_bonuses", {"Intelligence": 2, "Wisdom": 1})

    result3 = builder.to_json()

    # Rebuild from choices_made and verify it works correctly
    builder_new = CharacterBuilder()
    builder_new.apply_choices(result3["choices_made"])

    result_rebuilt = builder_new.to_json()
    expected = {
        "Strength": 10,
        "Dexterity": 12,
        "Constitution": 13,
        "Intelligence": 17,
        "Wisdom": 15,
        "Charisma": 8,
    }

    assert result_rebuilt["ability_scores"] == expected, (
        f"Rebuild failed. Expected {expected}, got {result_rebuilt['ability_scores']}"
    )


def test_roll_ability_scores_method_tracking():
    """Roll helper method should be tracked and keep explicit scores."""
    builder = CharacterBuilder()
    builder.apply_choice("class", "Wizard")

    rolled_scores = {
        "Strength": 12,
        "Dexterity": 14,
        "Constitution": 13,
        "Intelligence": 15,
        "Wisdom": 10,
        "Charisma": 8,
    }
    builder.apply_choice("ability_scores", rolled_scores)
    builder.apply_choice("ability_scores_method", "roll")

    result = builder.to_json()
    assert result["choices_made"]["ability_scores_method"] == "roll"
    assert result["ability_scores"] == rolled_scores


def test_additional_ability_modifiers_stack_with_background_bonuses():
    """Additional modifiers should stack with background bonuses on final scores."""
    builder = CharacterBuilder()
    builder.apply_choices(
        {
            "character_name": "Stack Tester",
            "level": 1,
            "class": "Wizard",
            "species": "Human",
            "background": "Sage",
            "ability_scores": {
                "Strength": 8,
                "Dexterity": 10,
                "Constitution": 12,
                "Intelligence": 15,
                "Wisdom": 13,
                "Charisma": 14,
            },
            "background_bonuses": {"Intelligence": 2, "Wisdom": 1},
            "additional_ability_modifiers": {"Intelligence": 1, "Strength": -1},
        }
    )

    result = builder.to_character()
    assert result["ability_scores"]["Intelligence"] == 18
    assert result["ability_scores"]["Wisdom"] == 14
    assert result["ability_scores"]["Strength"] == 7
    assert result["abilities"]["intelligence"]["additional_modifier"] == 1
    assert result["abilities"]["strength"]["additional_modifier"] == -1


def test_hp_breakdown_in_combat_stats_no_feature_bonus():
    """Test that hp_breakdown is included in combat stats with no feature bonuses"""
    builder = CharacterBuilder()
    builder.apply_choices({
        "character_name": "Plain Fighter",
        "level": 5,
        "species": "Human",
        "class": "Fighter",
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16, "Dexterity": 14, "Constitution": 14,
            "Intelligence": 10, "Wisdom": 12, "Charisma": 8,
        },
        "background_bonuses": {"Strength": 2, "Constitution": 1},
    })
    character = builder.to_character()

    combat = character["combat"]
    assert "hp_breakdown" in combat

    bd = combat["hp_breakdown"]
    assert bd["total_hp"] == combat["hit_points"]["maximum"]
    assert bd["hit_die"] == 10  # Fighter uses d10
    assert bd["feature_bonus"] == 0


def test_hp_breakdown_in_combat_stats_with_feature_bonus():
    """Test that hp_breakdown shows feature bonuses (e.g. Dwarven Toughness)"""
    builder = CharacterBuilder()
    builder.apply_choices({
        "character_name": "Tough Dwarf",
        "level": 5,
        "species": "Dwarf",
        "class": "Fighter",
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16, "Dexterity": 10, "Constitution": 15,
            "Intelligence": 8, "Wisdom": 12, "Charisma": 10,
        },
        "background_bonuses": {"Strength": 2, "Constitution": 1},
    })
    character = builder.to_character()

    combat = character["combat"]
    assert "hp_breakdown" in combat

    bd = combat["hp_breakdown"]
    assert bd["feature_bonus"] > 0
    assert len(bd["feature_breakdown"]) > 0
    # Total HP should equal base + con + feature bonuses
    assert bd["total_hp"] == bd["base_hp"] + bd["constitution_bonus"] + bd["feature_bonus"]
    assert bd["total_hp"] == combat["hit_points"]["maximum"]
