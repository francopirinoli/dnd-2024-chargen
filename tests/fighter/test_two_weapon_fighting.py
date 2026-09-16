#!/usr/bin/env python3
"""
Unit tests for Two-Weapon Fighting fighting style.

Tests that Two-Weapon Fighting adds ability modifier to offhand attack damage.
"""

import pytest
from modules.character_builder import CharacterBuilder


class TestTwoWeaponFighting:
    """Test Two-Weapon Fighting fighting style functionality."""

    @pytest.fixture
    def fighter_with_two_weapon_fighting(self):
        """Create a Fighter with Two-Weapon Fighting style."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Dual Wielder",
            "species": "Human",
            "class": "Fighter",
            "level": 3,
            "background": "Soldier",
            "ability_scores": {
                "Strength": 14,
                "Dexterity": 16,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 12,
                "Charisma": 10,
            },
            "skill_choices": ["Athletics", "Acrobatics"],
            "Fighting Style": "Two-Weapon Fighting",
            "equipment_selections": {
                "class_equipment": "option_b",  # Gets Scimitar and Shortsword
                "background_equipment": "option_a",
            },
        }
        builder.apply_choices(choices)
        return builder

    @pytest.fixture
    def fighter_without_two_weapon_fighting(self):
        """Create a Fighter without Two-Weapon Fighting style."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Dual Wielder",
            "species": "Human",
            "class": "Fighter",
            "level": 3,
            "background": "Soldier",
            "ability_scores": {
                "Strength": 14,
                "Dexterity": 16,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 12,
                "Charisma": 10,
            },
            "skill_choices": ["Athletics", "Acrobatics"],
            "Fighting Style": "Dueling",  # Different fighting style
            "equipment_selections": {
                "class_equipment": "option_b",  # Gets Scimitar and Shortsword
                "background_equipment": "option_a",
            },
        }
        builder.apply_choices(choices)
        return builder

    def test_two_weapon_fighting_adds_ability_mod_to_offhand(
        self, fighter_with_two_weapon_fighting
    ):
        """Test that Two-Weapon Fighting adds ability modifier to offhand damage."""
        weapon_data = fighter_with_two_weapon_fighting.calculate_weapon_attacks()
        combinations = weapon_data.get("combinations", [])

        assert len(combinations) >= 1, "Should have at least one dual-wield combination"

        for combo in combinations:
            offhand = combo.get("offhand", {})
            offhand_dmg = offhand.get("damage", "")

            # Should have ability modifier: "1d6 + 3" (DEX is 16, mod +3)
            assert "+" in offhand_dmg, (
                "Offhand should include positive ability modifier with Two-Weapon Fighting"
            )
            assert "3" in offhand_dmg, "Offhand should add +3 from DEX modifier"

    def test_without_two_weapon_fighting_no_ability_mod_in_offhand(
        self, fighter_without_two_weapon_fighting
    ):
        """Test that without Two-Weapon Fighting, offhand doesn't get ability modifier."""
        weapon_data = fighter_without_two_weapon_fighting.calculate_weapon_attacks()
        combinations = weapon_data.get("combinations", [])

        assert len(combinations) >= 1, "Should have at least one dual-wield combination"

        for combo in combinations:
            offhand = combo.get("offhand", {})
            offhand_dmg = offhand.get("damage", "")

            # Should be dice only: "1d6"
            assert "+" not in offhand_dmg, (
                "Offhand shouldn't include positive ability modifier without Two-Weapon Fighting"
            )

    def test_two_weapon_fighting_increases_average_damage(
        self, fighter_with_two_weapon_fighting, fighter_without_two_weapon_fighting
    ):
        """Test that Two-Weapon Fighting increases average offhand damage."""
        # Get offhand damage with Two-Weapon Fighting
        weapon_data_with = fighter_with_two_weapon_fighting.calculate_weapon_attacks()
        combos_with = weapon_data_with.get("combinations", [])
        avg_damage_with = combos_with[0]["offhand"]["avg_damage"]

        # Get offhand damage without Two-Weapon Fighting
        weapon_data_without = (
            fighter_without_two_weapon_fighting.calculate_weapon_attacks()
        )
        combos_without = weapon_data_without.get("combinations", [])
        avg_damage_without = combos_without[0]["offhand"]["avg_damage"]

        # Two-Weapon Fighting should increase average damage by ability modifier
        assert avg_damage_with > avg_damage_without, (
            "Two-Weapon Fighting should increase average offhand damage"
        )
        assert avg_damage_with == avg_damage_without + 3, (
            "Should add DEX modifier (+3) to average damage"
        )

    def test_two_weapon_fighting_in_character_export(
        self, fighter_with_two_weapon_fighting
    ):
        """Test that Two-Weapon Fighting offhand damage appears correctly in export."""
        char_data = fighter_with_two_weapon_fighting.to_character()
        attack_combinations = char_data.get("attack_combinations", [])

        assert len(attack_combinations) >= 1, (
            "Should have at least one dual-wield combination"
        )

        for combo in attack_combinations:
            offhand = combo.get("offhand", {})
            offhand_dmg = offhand.get("damage", "")

            # Should have ability modifier: "1d6 + 3"
            assert "+" in offhand_dmg, (
                "Exported offhand should include ability modifier with Two-Weapon Fighting"
            )
            assert "3" in offhand_dmg, (
                "Exported offhand should add +3 from DEX modifier"
            )
