"""Unit tests for Artificer 2024 RAW stats, feature calculations, and subclass mechanics."""

import pytest
from modules.character_builder import CharacterBuilder
from modules.derived_stats import build_level_up_preview


def test_artificer_stats_empty_for_non_artificer():
    """Characters without Artificer levels must return default inactive stats."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Fighter")
    builder.apply_choice("level", 3)
    stats = builder.calculate_artificer_stats()
    assert stats["is_artificer"] is False
    assert stats["artificer_level"] == 0
    assert stats["flash_of_genius"]["active"] is False


def test_artificer_core_progression_scaling():
    """Validate core Artificer features across key progression milestones (levels 1, 3, 6, 7, 10, 11, 14, 18, 20)."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 1)
    builder.apply_choice("ability_scores", {
        "Strength": 10,
        "Dexterity": 12,
        "Constitution": 14,
        "Intelligence": 18,
        "Wisdom": 12,
        "Charisma": 8,
    })

    # Level 1
    char1 = builder.to_character()
    stats1 = char1.get("artificer_stats", {})
    assert stats1["is_artificer"] is True
    assert stats1["artificer_level"] == 1
    assert stats1["magical_tinkering"]["active"] is True
    assert stats1["magical_tinkering"]["max_objects"] == 4  # INT mod 4
    assert stats1["magic_item_attunement"]["max_attuned_items"] == 3
    assert stats1["the_right_tool"]["active"] is False
    assert stats1["tool_expertise"]["active"] is False
    assert stats1["flash_of_genius"]["active"] is False

    # Level 3
    builder.apply_choice("level", 3)
    stats3 = builder.calculate_artificer_stats()
    assert stats3["the_right_tool"]["active"] is True
    assert stats3["tool_expertise"]["active"] is False

    # Level 6
    builder.apply_choice("level", 6)
    stats6 = builder.calculate_artificer_stats()
    assert stats6["tool_expertise"]["active"] is True
    assert stats6["magic_item_attunement"]["max_attuned_items"] == 4

    # Level 7: Flash of Genius
    builder.apply_choice("level", 7)
    stats7 = builder.calculate_artificer_stats()
    assert stats7["flash_of_genius"]["active"] is True
    assert stats7["flash_of_genius"]["uses_max"] == 4  # INT mod 4
    assert stats7["flash_of_genius"]["bonus"] == 4

    # Level 10: Magic Item Adept
    builder.apply_choice("level", 10)
    stats10 = builder.calculate_artificer_stats()
    assert stats10["magic_item_attunement"]["max_attuned_items"] == 5
    assert stats10["magic_item_attunement"]["magic_item_adept"] is True

    # Level 11: Spell-Storing Item
    builder.apply_choice("level", 11)
    stats11 = builder.calculate_artificer_stats()
    assert stats11["spell_storing_item"]["active"] is True
    assert stats11["spell_storing_item"]["max_activations"] == 8  # 2 * 4

    # Level 14: Advanced Artifice
    builder.apply_choice("level", 14)
    stats14 = builder.calculate_artificer_stats()
    assert stats14["magic_item_attunement"]["advanced_artifice"] is True

    # Level 18: Magic Item Master
    builder.apply_choice("level", 18)
    stats18 = builder.calculate_artificer_stats()
    assert stats18["magic_item_attunement"]["max_attuned_items"] == 6
    assert stats18["magic_item_attunement"]["magic_item_master"] is True

    # Level 20: Soul of Artifice
    builder.apply_choice("level", 20)
    stats20 = builder.calculate_artificer_stats()
    assert stats20["soul_of_artifice"]["active"] is True
    assert stats20["soul_of_artifice"]["bonus_per_attuned"] == 1


def test_artificer_alchemist_subclass():
    """Validate Alchemist features at levels 3, 5, 9, and 15."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 3)
    builder.apply_choice("subclass", "Alchemist")
    builder.apply_choice("ability_scores", {
        "Strength": 8, "Dexterity": 14, "Constitution": 14,
        "Intelligence": 16, "Wisdom": 12, "Charisma": 10,
    })

    stats = builder.calculate_artificer_stats()
    sub = stats["subclass_details"]
    assert sub["experimental_elixir"]["active"] is True
    assert sub["experimental_elixir"]["free_elixirs"] == 2
    assert len(sub["experimental_elixir"]["table"]) == 6

    # Level 5: Alchemical Savant
    builder.apply_choice("level", 5)
    stats5 = builder.calculate_artificer_stats()
    assert stats5["subclass_details"]["alchemical_savant"]["bonus"] == 3

    # Level 9: Restorative Reagents
    builder.apply_choice("level", 9)
    stats9 = builder.calculate_artificer_stats()
    assert stats9["subclass_details"]["restorative_reagents"]["free_lesser_restoration_uses"] == 3

    # Level 15: Chemical Mastery
    builder.apply_choice("level", 15)
    stats15 = builder.calculate_artificer_stats()
    assert "Acid" in stats15["subclass_details"]["chemical_mastery"]["resistances"]
    assert "Poison" in stats15["subclass_details"]["chemical_mastery"]["resistances"]


def test_artificer_armorer_weapons_and_features():
    """Validate Armorer Arcane Armor, weapon INT scaling, and models."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 3)
    builder.apply_choice("subclass", "Armorer")
    builder.apply_choice("ability_scores", {
        "Strength": 10, "Dexterity": 10, "Constitution": 14,
        "Intelligence": 18, "Wisdom": 12, "Charisma": 8,
    })
    builder.character_data["equipment"] = {
        "weapons": [
            {"name": "Thunder Gauntlets", "properties": {"category": "Simple Melee", "damage": "1d8", "damage_type": "Thunder", "properties": []}, "equipped": True},
            {"name": "Lightning Launcher", "properties": {"category": "Simple Ranged", "damage": "1d6", "damage_type": "Lightning", "properties": ["Ammunition"]}, "equipped": True},
        ],
        "armor": [],
        "items": [],
        "gold": 0,
    }

    char = builder.to_character()
    attacks = {atk["name"]: atk for atk in char.get("attacks", [])}
    assert "Thunder Gauntlets" in attacks
    assert attacks["Thunder Gauntlets"]["ability"] == "INT"
    assert attacks["Thunder Gauntlets"]["attack_bonus"] == 6  # +4 INT + 2 PB
    assert attacks["Thunder Gauntlets"]["damage_bonus"] == 4

    assert "Lightning Launcher" in attacks
    assert attacks["Lightning Launcher"]["ability"] == "INT"
    assert attacks["Lightning Launcher"]["attack_bonus"] == 6

    # Improved Armorer at Level 9
    builder.apply_choice("level", 9)
    stats9 = builder.calculate_artificer_stats()
    assert stats9["subclass_details"]["improved_armorer"]["extra_infusions"] == 2


def test_artificer_artillerist_subclass():
    """Validate Artillerist Eldritch Cannon options and scaling."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 3)
    builder.apply_choice("subclass", "Artillerist")
    builder.apply_choice("ability_scores", {
        "Strength": 8, "Dexterity": 14, "Constitution": 14,
        "Intelligence": 16, "Wisdom": 12, "Charisma": 10,
    })

    stats = builder.calculate_artificer_stats()
    sub = stats["subclass_details"]
    assert sub["eldritch_cannon"]["active"] is True
    assert sub["eldritch_cannon"]["cannon_ac"] == 18
    assert sub["eldritch_cannon"]["cannon_hp"] == 15
    assert "Flamethrower" in sub["eldritch_cannon"]["options"]
    assert "Force Ballista" in sub["eldritch_cannon"]["options"]
    assert "Protector" in sub["eldritch_cannon"]["options"]

    # Level 9: Explosive Cannon
    builder.apply_choice("level", 9)
    stats9 = builder.calculate_artificer_stats()
    assert stats9["subclass_details"]["explosive_cannon"]["bonus_damage_die"] == "1d8"

    # Level 15: Fortified Position
    builder.apply_choice("level", 15)
    stats15 = builder.calculate_artificer_stats()
    assert stats15["subclass_details"]["fortified_position"]["dual_cannons"] is True


def test_artificer_battle_smith_and_magic_weapons():
    """Validate Battle Smith Battle Ready INT weapon attack bonus and Steel Defender."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 3)
    builder.apply_choice("subclass", "Battle Smith")
    builder.apply_choice("ability_scores", {
        "Strength": 10, "Dexterity": 12, "Constitution": 14,
        "Intelligence": 16, "Wisdom": 12, "Charisma": 8,
    })
    builder.character_data["equipment"] = {
        "weapons": [
            {"name": "Longsword +1", "properties": {"category": "Martial Melee", "damage": "1d8", "damage_type": "Slashing", "properties": ["Versatile"]}, "attack_bonus": 1, "damage_bonus": 1, "equipped": True, "is_magic": True},
            {"name": "Mundane Greatsword", "properties": {"category": "Martial Melee", "damage": "2d6", "damage_type": "Slashing", "properties": ["Heavy", "Two-Handed"]}, "equipped": True},
        ],
        "armor": [],
        "items": [],
        "gold": 0,
    }

    char = builder.to_character()
    attacks = {atk["name"]: atk for atk in char.get("attacks", [])}
    # Magic weapon uses INT
    assert attacks["Longsword +1"]["ability"] == "INT"
    assert attacks["Longsword +1"]["attack_bonus"] == 6  # 3 INT + 2 PB + 1 weapon = 6
    assert attacks["Longsword +1"]["damage_bonus"] == 4  # 3 INT + 1 weapon = 4

    # Mundane weapon uses STR (STR 10 -> mod 0, PB 2 -> to hit 2, damage bonus 0)
    assert attacks["Mundane Greatsword"]["ability"] == "STR"
    assert attacks["Mundane Greatsword"]["attack_bonus"] == 2
    assert attacks["Mundane Greatsword"]["damage_bonus"] == 0

    stats = char["artificer_stats"]
    defender = stats["subclass_details"]["steel_defender"]
    assert defender["active"] is True
    assert defender["ac"] == 17  # 15 + 2 PB
    assert defender["hp"] == 20  # 2 + 3 INT + 5 * 3


def test_artificer_cartographer_subclass():
    """Validate Cartographer Adventurer's Atlas and Mapping Magic."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 3)
    builder.apply_choice("subclass", "Cartographer")
    builder.apply_choice("ability_scores", {
        "Strength": 8, "Dexterity": 14, "Constitution": 14,
        "Intelligence": 18, "Wisdom": 12, "Charisma": 10,
    })

    stats = builder.calculate_artificer_stats()
    sub = stats["subclass_details"]
    assert sub["adventurers_atlas"]["max_map_holders"] == 5  # 1 + 4 INT
    assert sub["mapping_magic"]["free_faerie_fire_uses"] == 4

    # Level 5: Guided Precision
    builder.apply_choice("level", 5)
    stats5 = builder.calculate_artificer_stats()
    assert stats5["subclass_details"]["guided_precision"]["damage_bonus"] == 4

    # Level 9: Ingenious Movement
    builder.apply_choice("level", 9)
    stats9 = builder.calculate_artificer_stats()
    assert stats9["subclass_details"]["ingenious_movement"]["teleport_range_feet"] == 30


def test_artificer_level_up_preview_artificer_changes():
    """Level up preview from level 6 to 7 must flag flash_of_genius_unlocked."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 6)
    builder.apply_choice("subclass", "Battle Smith")

    preview = build_level_up_preview(builder.character_data.get("choices_made", {}))
    art_changes = preview.get("artificer_changes", {})
    assert art_changes.get("is_artificer") is True
    assert art_changes.get("flash_of_genius_unlocked") is True
    assert art_changes.get("spell_storing_item_unlocked") is False
