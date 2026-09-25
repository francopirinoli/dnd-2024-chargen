"""
Tests for Warlock 2024 RAW class audit, calculate_warlock_stats(),
subclass features, and derived stats level-up preview.
"""

import pytest
from modules.character_builder import CharacterBuilder
from modules.derived_stats import build_level_up_preview


def build_warlock_builder(level: int, subclass: str = None, cha: int = 16):
    builder = CharacterBuilder()
    builder.apply_choices({
        "character_name": "Test Warlock",
        "species": "Human",
        "class": "Warlock",
        "level": level,
        "background": "Acolyte",
        "ability_scores": {
            "Strength": 8,
            "Dexterity": 14,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": cha,
        },
        "skill_choices": ["Arcana", "Deception"],
    })
    if subclass and level >= 3:
        builder.set_subclass(subclass)
    return builder


class TestWarlockStatsCalculation:
    """Test calculate_warlock_stats() against 2024 RAW progression."""

    def test_level_1_warlock_stats(self):
        builder = build_warlock_builder(1, cha=16)
        stats = builder.calculate_warlock_stats()

        assert stats["is_warlock"] is True
        assert stats["warlock_level"] == 1
        assert stats["spellcasting_ability"] == "Charisma"
        assert stats["spell_save_dc"] == 8 + 3 + 2  # 13
        assert stats["spell_attack_bonus"] == 3 + 2  # 5

        # Pact Magic at level 1: 1 slot of 1st level
        pact = stats["pact_magic"]
        assert pact["slots"] == 1
        assert pact["slot_level"] == 1
        assert pact["cantrips_known"] == 2
        assert pact["prepared_spells_count"] == 2

        # Magical Cunning inactive at level 1
        assert stats["magical_cunning"]["active"] is False
        assert stats["contact_patron"]["active"] is False
        assert stats["mystic_arcanum"]["active"] is False
        assert stats["eldritch_master"] is False
        assert stats["invocations"]["max_invocations"] == 1

    def test_level_2_magical_cunning(self):
        builder = build_warlock_builder(2, cha=16)
        stats = builder.calculate_warlock_stats()

        assert stats["warlock_level"] == 2
        pact = stats["pact_magic"]
        assert pact["slots"] == 2
        assert pact["slot_level"] == 1

        # Magical Cunning active: regains half of 2 slots (rounded up) = 1 slot
        cunning = stats["magical_cunning"]
        assert cunning["active"] is True
        assert cunning["slots_regained"] == 1
        assert cunning["eldritch_master"] is False
        assert stats["invocations"]["max_invocations"] == 3

    def test_level_5_pact_magic_scaling(self):
        builder = build_warlock_builder(5, subclass="The Fiend", cha=16)
        stats = builder.calculate_warlock_stats()

        assert stats["warlock_level"] == 5
        pact = stats["pact_magic"]
        assert pact["slots"] == 2
        assert pact["slot_level"] == 3
        assert pact["cantrips_known"] == 3
        assert pact["prepared_spells_count"] == 6
        assert stats["invocations"]["max_invocations"] == 5

    def test_level_9_contact_patron(self):
        builder = build_warlock_builder(9, cha=16)
        stats = builder.calculate_warlock_stats()

        assert stats["warlock_level"] == 9
        pact = stats["pact_magic"]
        assert pact["slots"] == 2
        assert pact["slot_level"] == 5

        contact = stats["contact_patron"]
        assert contact["active"] is True
        assert contact["spell"] == "Contact Other Plane"
        assert contact["auto_succeed_save"] is True

        char = builder.to_character()
        assert "Contact Other Plane" in char.get("spells", {}).get("always_prepared", {})

    def test_level_11_mystic_arcanum_and_3_slots(self):
        builder = build_warlock_builder(11, cha=18)
        stats = builder.calculate_warlock_stats()

        assert stats["warlock_level"] == 11
        pact = stats["pact_magic"]
        assert pact["slots"] == 3  # Level 11 jumps to 3 slots
        assert pact["slot_level"] == 5

        arcanum = stats["mystic_arcanum"]
        assert arcanum["active"] is True
        assert arcanum["unlocked_levels"] == [6]

        # Magical Cunning with 3 slots: ceil(3 / 2) = 2 slots regained
        assert stats["magical_cunning"]["slots_regained"] == 2

    def test_level_17_mystic_arcanum_progression_and_4_slots(self):
        builder = build_warlock_builder(17, cha=20)
        stats = builder.calculate_warlock_stats()

        assert stats["warlock_level"] == 17
        pact = stats["pact_magic"]
        assert pact["slots"] == 4  # Level 17 jumps to 4 slots
        assert pact["slot_level"] == 5

        arcanum = stats["mystic_arcanum"]
        assert arcanum["active"] is True
        assert arcanum["unlocked_levels"] == [6, 7, 8, 9]

    def test_level_20_eldritch_master(self):
        builder = build_warlock_builder(20, cha=20)
        stats = builder.calculate_warlock_stats()

        assert stats["warlock_level"] == 20
        assert stats["eldritch_master"] is True
        cunning = stats["magical_cunning"]
        assert cunning["active"] is True
        assert cunning["eldritch_master"] is True
        # Eldritch Master regains ALL expended slots (4)
        assert cunning["slots_regained"] == 4


class TestWarlockPatrons:
    """Test Patron subclass details and abilities in calculate_warlock_stats()."""

    def test_archfey_patron(self):
        builder = build_warlock_builder(6, subclass="The Archfey", cha=18)
        stats = builder.calculate_warlock_stats()
        sub = stats["subclass_details"]

        assert sub["name"] == "The Archfey"
        assert sub["steps_of_the_fey"] is True
        assert sub["steps_uses"] == 4  # CHA mod 4
        assert sub["misty_escape"] is True
        assert sub["beguiling_defenses"] is False  # Level 10

    def test_celestial_patron_and_spells_table(self):
        builder = build_warlock_builder(6, subclass="The Celestial", cha=16)
        stats = builder.calculate_warlock_stats()
        sub = stats["subclass_details"]

        assert sub["name"] == "The Celestial"
        assert sub["healing_light"] is True
        assert sub["healing_light_dice"] == 7  # 1 + 6
        assert sub["healing_light_max_heal_dice"] == 3  # CHA mod 3
        assert sub["radiant_soul"] is True
        assert sub["radiant_soul_bonus"] == 3

        # Verify always prepared spells include Light, Sacred Flame, Aid, Cure Wounds
        char = builder.to_character()
        always_prep = char.get("spells", {}).get("always_prepared", {})
        assert "Light" in always_prep
        assert "Sacred Flame" in always_prep
        assert "Aid" in always_prep
        assert "Cure Wounds" in always_prep

        # Check Celestial Spells feature description contains the spells table
        features = char.get("features", {}).get("subclass", [])
        celestial_spells_feat = next((f for f in features if "Celestial Spells" in f.get("name", "")), None)
        assert celestial_spells_feat is not None
        desc = celestial_spells_feat.get("description", "")
        assert "Light" in desc
        assert "Sacred Flame" in desc
        assert "Aid" in desc

    def test_fiend_patron(self):
        builder = build_warlock_builder(14, subclass="The Fiend", cha=18)
        stats = builder.calculate_warlock_stats()
        sub = stats["subclass_details"]

        assert sub["name"] == "The Fiend"
        assert sub["dark_ones_blessing"] is True
        assert sub["dark_ones_blessing_thp"] == 14 + 4  # 18
        assert sub["dark_ones_own_luck"] is True
        assert sub["dark_ones_own_luck_uses"] == 4
        assert sub["fiendish_resilience"] is True
        assert sub["hurl_through_hell"] is True

    def test_great_old_one_patron(self):
        builder = build_warlock_builder(10, subclass="The Great Old One", cha=16)
        stats = builder.calculate_warlock_stats()
        sub = stats["subclass_details"]

        assert sub["name"] == "The Great Old One"
        assert sub["awakened_mind"] is True
        assert sub["awakened_mind_miles"] == 3
        assert sub["psychic_spells"] is True
        assert sub["clairvoyant_combatant"] is True
        assert sub["eldritch_hex"] is True
        assert sub["thought_shield"] is True
        assert sub["create_thrall"] is False  # Level 14


class TestWarlockLevelUpPreview:
    """Test derived_stats calculate_level_up_preview for Warlock."""

    def test_level_up_1_to_2_warlock(self):
        choices = {
            "character_name": "Test Warlock",
            "species": "Human",
            "class": "Warlock",
            "level": 1,
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 8,
                "Dexterity": 14,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 12,
                "Charisma": 16,
            },
            "skill_choices": ["Arcana", "Deception"],
        }

        preview = build_level_up_preview(
            choices_made=choices,
            class_to_level="Warlock",
        )

        wc = preview.get("warlock_changes", {})
        assert wc["is_warlock"] is True
        assert wc["magical_cunning_unlocked"] is True
        assert wc["current_pact_slots"] == 1
        assert wc["next_pact_slots"] == 2

    def test_level_up_10_to_11_warlock(self):
        choices = {
            "character_name": "Test Warlock",
            "species": "Human",
            "class": "Warlock",
            "level": 10,
            "subclass": "The Fiend",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 8,
                "Dexterity": 14,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 12,
                "Charisma": 18,
            },
            "skill_choices": ["Arcana", "Deception"],
        }

        preview = build_level_up_preview(
            choices_made=choices,
            class_to_level="Warlock",
        )

        wc = preview.get("warlock_changes", {})
        assert wc["is_warlock"] is True
        assert wc["mystic_arcanum_unlocked"] is True
        assert wc["newest_arcanum_level"] == 6
        assert wc["current_pact_slots"] == 2
        assert wc["next_pact_slots"] == 3
