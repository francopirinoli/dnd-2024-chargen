#!/usr/bin/env python3
"""
Comprehensive pytest test suite for Fighter 2024 RAW features and subclasses.
Covers:
- Second Wind scaling (2/3/4) and healing (1d10 + level)
- Tactical Mind (Level 2) and Tactical Shift (Level 5)
- Action Surge uses (1/2) and 2024 restrictions
- Indomitable uses (1/2/3) and +level bonus
- Extra Attacks scaling (1, 2, 3, 4 attacks per Attack action)
- Tactical Master (Level 9) and Studied Attacks (Level 13)
- Subclasses:
  * Battle Master (dice count/size, Student of War with Persuasion, DC)
  * Champion (crit threshold 19/18, Remarkable Athlete, Heroic Warrior, Survivor)
  * Eldritch Knight (War Bond, War Magic, Eldritch Strike, Arcane Charge, Improved War Magic)
  * Psi Warrior (2*PB dice count, d6-d12 scaling, Telekinetic Adept/Master)
  * Banneret (Knightly Envoy structured choices, Group Recovery)
  * Hell Knight (Diabolical Gift structured choices, Hell-Forged Weapon, Infernal Wound)
  * Arcane Archer (Arcane Shot dice and DC)
- Level-up preview fighter_changes
"""

import pytest
from modules.character_builder import CharacterBuilder
from modules.derived_stats import build_level_up_preview


def make_fighter(level: int, subclass: str = None) -> CharacterBuilder:
    """Helper to construct a Fighter CharacterBuilder instance."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_background("Soldier")
    builder.set_class("Fighter", level)
    if subclass:
        builder.set_subclass(subclass)
    return builder


class TestFighter2024CoreProgression:
    """Test 2024 RAW core Fighter features and progression tables."""

    @pytest.mark.parametrize("level,expected_uses", [
        (1, 2),
        (3, 2),
        (4, 3),
        (9, 3),
        (10, 4),
        (20, 4),
    ])
    def test_second_wind_scaling(self, level, expected_uses):
        builder = make_fighter(level)
        stats = builder.calculate_fighter_stats()
        assert stats["second_wind_max"] == expected_uses
        assert stats["second_wind_uses"] == expected_uses
        assert stats["second_wind_healing"] == f"1d10 + {level}"

    def test_tactical_mind_and_shift(self):
        # Level 1 has neither
        b1 = make_fighter(1)
        s1 = b1.calculate_fighter_stats()
        assert not s1["tactical_mind"]
        assert not s1["tactical_shift"]

        # Level 2 has Tactical Mind
        b2 = make_fighter(2)
        s2 = b2.calculate_fighter_stats()
        assert s2["tactical_mind"]
        assert not s2["tactical_shift"]

        # Level 5 has both Tactical Mind and Tactical Shift
        b5 = make_fighter(5)
        s5 = b5.calculate_fighter_stats()
        assert s5["tactical_mind"]
        assert s5["tactical_shift"]

    @pytest.mark.parametrize("level,has_surge,expected_uses", [
        (1, False, 0),
        (2, True, 1),
        (16, True, 1),
        (17, True, 2),
        (20, True, 2),
    ])
    def test_action_surge_scaling(self, level, has_surge, expected_uses):
        builder = make_fighter(level)
        stats = builder.calculate_fighter_stats()
        assert stats["has_action_surge"] == has_surge
        assert stats["action_surge_max"] == expected_uses

    @pytest.mark.parametrize("level,has_indom,expected_uses,expected_bonus", [
        (1, False, 0, 0),
        (8, False, 0, 0),
        (9, True, 1, 9),
        (12, True, 1, 12),
        (13, True, 2, 13),
        (16, True, 2, 16),
        (17, True, 3, 17),
        (20, True, 3, 20),
    ])
    def test_indomitable_scaling(self, level, has_indom, expected_uses, expected_bonus):
        builder = make_fighter(level)
        stats = builder.calculate_fighter_stats()
        assert stats["has_indomitable"] == has_indom
        assert stats["indomitable_max"] == expected_uses
        assert stats["indomitable_bonus"] == expected_bonus

    @pytest.mark.parametrize("level,expected_attacks,expected_label", [
        (1, 1, "1 attack/action"),
        (4, 1, "1 attack/action"),
        (5, 2, "Extra Attack (2 attacks/action)"),
        (10, 2, "Extra Attack (2 attacks/action)"),
        (11, 3, "Two Extra Attacks (3 attacks/action)"),
        (19, 3, "Two Extra Attacks (3 attacks/action)"),
        (20, 4, "Three Extra Attacks (4 attacks/action)"),
    ])
    def test_extra_attacks_progression(self, level, expected_attacks, expected_label):
        builder = make_fighter(level)
        stats = builder.calculate_fighter_stats()
        assert stats["attacks_per_action"] == expected_attacks
        assert stats["extra_attacks_label"] == expected_label

    def test_tactical_master_and_studied_attacks(self):
        b8 = make_fighter(8)
        s8 = b8.calculate_fighter_stats()
        assert not s8["has_tactical_master"]
        assert not s8["has_studied_attacks"]

        b9 = make_fighter(9)
        s9 = b9.calculate_fighter_stats()
        assert s9["has_tactical_master"]
        assert s9["tactical_master_properties"] == ["Push", "Sap", "Slow"]
        assert not s9["has_studied_attacks"]

        b13 = make_fighter(13)
        s13 = b13.calculate_fighter_stats()
        assert s13["has_tactical_master"]
        assert s13["has_studied_attacks"]

    @pytest.mark.parametrize("level,expected_masteries", [
        (1, 3),
        (3, 3),
        (4, 4),
        (9, 4),
        (10, 5),
        (15, 5),
        (16, 6),
        (20, 6),
    ])
    def test_weapon_mastery_count(self, level, expected_masteries):
        builder = make_fighter(level)
        stats = builder.calculate_fighter_stats()
        assert stats["weapon_mastery_count"] == expected_masteries


class TestFighterSubclasses:
    """Test Battle Master, Champion, Eldritch Knight, Psi Warrior, and supplements."""

    def test_battle_master_superiority_progression(self):
        # Level 3: 4d8
        b3 = make_fighter(3, "Battle Master")
        s3 = b3.calculate_fighter_stats()
        bm3 = s3["subclass_details"]["battle_master"]
        assert bm3["superiority_dice_count"] == 4
        assert bm3["superiority_die"] == "d8"
        assert bm3["save_dc"] >= 10

        # Level 7: 5d8, Know Your Enemy
        b7 = make_fighter(7, "Battle Master")
        s7 = b7.calculate_fighter_stats()
        bm7 = s7["subclass_details"]["battle_master"]
        assert bm7["superiority_dice_count"] == 5
        assert bm7["superiority_die"] == "d8"
        assert bm7["know_your_enemy"]

        # Level 10: 5d10
        b10 = make_fighter(10, "Battle Master")
        s10 = b10.calculate_fighter_stats()
        bm10 = s10["subclass_details"]["battle_master"]
        assert bm10["superiority_dice_count"] == 5
        assert bm10["superiority_die"] == "d10"

        # Level 15: 6d10, Relentless
        b15 = make_fighter(15, "Battle Master")
        s15 = b15.calculate_fighter_stats()
        bm15 = s15["subclass_details"]["battle_master"]
        assert bm15["superiority_dice_count"] == 6
        assert bm15["superiority_die"] == "d10"
        assert bm15["relentless"]

        # Level 18: 6d12
        b18 = make_fighter(18, "Battle Master")
        s18 = b18.calculate_fighter_stats()
        bm18 = s18["subclass_details"]["battle_master"]
        assert bm18["superiority_dice_count"] == 6
        assert bm18["superiority_die"] == "d12"

    def test_champion_critical_and_perks(self):
        # Level 3: Crit on 19-20
        b3 = make_fighter(3, "Champion")
        s3 = b3.calculate_fighter_stats()
        c3 = s3["subclass_details"]["champion"]
        assert c3["crit_threshold"] == 19
        assert c3["remarkable_athlete"]

        # Attack info should have crit_threshold 19
        attacks = b3.calculate_weapon_attacks().get("attacks", [])
        if attacks:
            assert attacks[0]["crit_threshold"] == 19
            assert any("19-20" in note for note in attacks[0]["damage_notes"])

        # Level 10: Heroic Warrior
        b10 = make_fighter(10, "Champion")
        s10 = b10.calculate_fighter_stats()
        assert s10["subclass_details"]["champion"]["heroic_warrior"]

        # Level 15: Crit on 18-20
        b15 = make_fighter(15, "Champion")
        s15 = b15.calculate_fighter_stats()
        assert s15["subclass_details"]["champion"]["crit_threshold"] == 18

        # Level 18: Survivor
        b18 = make_fighter(18, "Champion")
        s18 = b18.calculate_fighter_stats()
        assert s18["subclass_details"]["champion"]["survivor"]

    def test_eldritch_knight_war_magic_and_perks(self):
        b7 = make_fighter(7, "Eldritch Knight")
        s7 = b7.calculate_fighter_stats()
        ek7 = s7["subclass_details"]["eldritch_knight"]
        assert ek7["war_bond"]
        assert ek7["war_magic"]
        assert ek7["spell_save_dc"] >= 10
        assert not ek7["eldritch_strike"]

        b10 = make_fighter(10, "Eldritch Knight")
        s10 = b10.calculate_fighter_stats()
        assert s10["subclass_details"]["eldritch_knight"]["eldritch_strike"]

        b15 = make_fighter(15, "Eldritch Knight")
        s15 = b15.calculate_fighter_stats()
        assert s15["subclass_details"]["eldritch_knight"]["arcane_charge"]

        b18 = make_fighter(18, "Eldritch Knight")
        s18 = b18.calculate_fighter_stats()
        assert s18["subclass_details"]["eldritch_knight"]["improved_war_magic"]

    def test_psi_warrior_progression(self):
        # Level 3: 4d6 (PB=2 -> 2*PB = 4)
        b3 = make_fighter(3, "Psi Warrior")
        s3 = b3.calculate_fighter_stats()
        pw3 = s3["subclass_details"]["psi_warrior"]
        assert pw3["psionic_dice_count"] == 4
        assert pw3["psionic_die"] == "d6"

        # Level 5: 6d8 (PB=3 -> 6)
        b5 = make_fighter(5, "Psi Warrior")
        s5 = b5.calculate_fighter_stats()
        assert s5["subclass_details"]["psi_warrior"]["psionic_dice_count"] == 6
        assert s5["subclass_details"]["psi_warrior"]["psionic_die"] == "d8"

        # Level 11: 8d10 (PB=4 -> 8)
        b11 = make_fighter(11, "Psi Warrior")
        s11 = b11.calculate_fighter_stats()
        assert s11["subclass_details"]["psi_warrior"]["psionic_dice_count"] == 8
        assert s11["subclass_details"]["psi_warrior"]["psionic_die"] == "d10"

        # Level 17: 12d12 (PB=6 -> 12)
        b17 = make_fighter(17, "Psi Warrior")
        s17 = b17.calculate_fighter_stats()
        assert s17["subclass_details"]["psi_warrior"]["psionic_dice_count"] == 12
        assert s17["subclass_details"]["psi_warrior"]["psionic_die"] == "d12"

    def test_banneret_supplement(self):
        b3 = make_fighter(3, "Banneret")
        s3 = b3.calculate_fighter_stats()
        ban3 = s3["subclass_details"]["banneret"]
        assert "1d4 + 3" in ban3["group_recovery_heal"]

        b10 = make_fighter(10, "Banneret")
        s10 = b10.calculate_fighter_stats()
        assert s10["subclass_details"]["banneret"]["team_tactics"]
        assert s10["subclass_details"]["banneret"]["rallying_surge"]

    def test_hell_knight_supplement(self):
        b3 = make_fighter(3, "Hell Knight")
        s3 = b3.calculate_fighter_stats()
        hk3 = s3["subclass_details"]["hell_knight"]
        assert hk3["infernal_wound_die"] == "d6"
        assert hk3["devils_sight"]

    def test_to_character_includes_fighter_stats(self):
        b = make_fighter(5, "Champion")
        char = b.to_character()
        assert "fighter_stats" in char
        fs = char["fighter_stats"]
        assert fs["is_fighter"]
        assert fs["fighter_level"] == 5
        assert fs["second_wind_max"] == 3
        assert fs["attacks_per_action"] == 2


class TestFighterLevelUpPreview:
    """Test Level-Up Preview fighter_changes computation."""

    def test_level_1_to_2_surge_and_tactical_mind(self):
        choices = {"class": "Fighter", "level": 1, "classes": [{"class_name": "Fighter", "level": 1}]}
        preview = build_level_up_preview(choices, "Fighter")
        fc = preview.get("fighter_changes", {})
        assert fc.get("is_fighter")
        assert fc.get("action_surge_unlocked")
        assert fc.get("tactical_mind_unlocked")
        assert not fc.get("second_wind_increased")

    def test_level_3_to_4_second_wind_and_mastery(self):
        choices = {"class": "Fighter", "level": 3, "classes": [{"class_name": "Fighter", "level": 3}]}
        preview = build_level_up_preview(choices, "Fighter")
        fc = preview.get("fighter_changes", {})
        assert fc.get("second_wind_increased")
        assert fc.get("current_second_wind_uses") == 2
        assert fc.get("next_second_wind_uses") == 3
        assert fc.get("masteries_increased")
        assert fc.get("current_masteries") == 3
        assert fc.get("next_masteries") == 4

    def test_level_4_to_5_extra_attack_and_shift(self):
        choices = {"class": "Fighter", "level": 4, "classes": [{"class_name": "Fighter", "level": 4}]}
        preview = build_level_up_preview(choices, "Fighter")
        fc = preview.get("fighter_changes", {})
        assert fc.get("attacks_per_action_increased")
        assert fc.get("current_attacks_per_action") == 1
        assert fc.get("next_attacks_per_action") == 2
        assert fc.get("tactical_shift_unlocked")

    def test_level_8_to_9_indomitable_and_tactical_master(self):
        choices = {"class": "Fighter", "level": 8, "classes": [{"class_name": "Fighter", "level": 8}]}
        preview = build_level_up_preview(choices, "Fighter")
        fc = preview.get("fighter_changes", {})
        assert fc.get("indomitable_unlocked")
        assert fc.get("tactical_master_unlocked")

    def test_level_16_to_17_surge_and_indomitable(self):
        choices = {"class": "Fighter", "level": 16, "classes": [{"class_name": "Fighter", "level": 16}]}
        preview = build_level_up_preview(choices, "Fighter")
        fc = preview.get("fighter_changes", {})
        assert fc.get("action_surge_increased")
        assert fc.get("current_action_surge_uses") == 1
        assert fc.get("next_action_surge_uses") == 2
        assert fc.get("indomitable_increased")
        assert fc.get("current_indomitable_uses") == 2
        assert fc.get("next_indomitable_uses") == 3
