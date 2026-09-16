#!/usr/bin/env python3
"""
Unit tests for Thrown Weapon Fighting fighting style.

Tests that Thrown Weapon Fighting adds +2 damage to ranged attacks with thrown weapons.
"""

import pytest
from modules.character_builder import CharacterBuilder


class TestThrownWeaponFighting:
    """Test Thrown Weapon Fighting fighting style functionality."""

    @pytest.fixture
    def fighter_with_thrown_weapon_fighting(self):
        """Create a Fighter with Thrown Weapon Fighting style."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Spear Thrower",
            "species": "Human",
            "class": "Fighter",
            "level": 1,
            "background": "Soldier",
            "ability_scores": {
                "Strength": 16,
                "Dexterity": 14,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 12,
                "Charisma": 10,
            },
            "skill_choices": ["Athletics", "Acrobatics"],
            "Fighting Style": "Thrown Weapon Fighting",
            "equipment_selections": {
                "class_equipment": "option_a",
                "background_equipment": "option_a",  # Gets Spear
            },
        }
        builder.apply_choices(choices)
        return builder

    @pytest.fixture
    def fighter_without_thrown_weapon_fighting(self):
        """Create a Fighter without Thrown Weapon Fighting style."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Regular Fighter",
            "species": "Human",
            "class": "Fighter",
            "level": 1,
            "background": "Soldier",
            "ability_scores": {
                "Strength": 16,
                "Dexterity": 14,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 12,
                "Charisma": 10,
            },
            "skill_choices": ["Athletics", "Acrobatics"],
            "Fighting Style": "Defense",  # Different fighting style
            "equipment_selections": {
                "class_equipment": "option_a",
                "background_equipment": "option_a",  # Gets Spear
            },
        }
        builder.apply_choices(choices)
        return builder

    def test_thrown_weapon_fighting_adds_damage_to_thrown_weapons(
        self, fighter_with_thrown_weapon_fighting
    ):
        """Test that Thrown Weapon Fighting adds +2 damage to thrown weapon attacks."""
        weapon_data = fighter_with_thrown_weapon_fighting.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])

        # Find the Spear (has Thrown property)
        spear = next((a for a in attacks if a["name"] == "Spear"), None)
        assert spear is not None, "Should have Spear in weapon attacks"

        # Check that Thrown property is present
        assert any("Thrown" in prop for prop in spear.get("properties", [])), (
            "Spear should have Thrown property"
        )

        # Spear is a melee weapon with Thrown property
        # Main damage should be melee (STR +3)
        damage = spear.get("damage", "")
        assert damage == "1d6 + 3", (
            f"Spear melee damage should be 1d6 + 3 (STR), got: {damage}"
        )

        # Throw damage should include TWF bonus (+2)
        throw_damage = spear.get("throw_damage", "")
        assert throw_damage == "1d6 + 5", (
            f"Spear throw damage should be 1d6 + 5 (STR +3, TWF +2), got: {throw_damage}"
        )

        # Check throw average damage reflects the bonus
        avg_throw_damage = spear.get("avg_throw_damage")
        # 1d6 average = 3.5, + 3 (STR) + 2 (TWF) = 8.5
        assert avg_throw_damage == 8.5, (
            f"Expected throw average damage 8.5, got {avg_throw_damage}"
        )

    def test_without_thrown_weapon_fighting_no_bonus(
        self, fighter_without_thrown_weapon_fighting
    ):
        """Test that without Thrown Weapon Fighting, thrown weapons don't get +2 damage."""
        weapon_data = fighter_without_thrown_weapon_fighting.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])

        # Find the Spear
        spear = next((a for a in attacks if a["name"] == "Spear"), None)
        assert spear is not None, "Should have Spear in weapon attacks"

        # Check damage is just STR modifier
        damage = spear.get("damage", "")
        # Should be "1d6 + 3" (STR +3 only)
        assert damage == "1d6 + 3", (
            f"Spear should have +3 damage (STR only), got: {damage}"
        )

        # Check average damage
        avg_damage = spear.get("avg_damage")
        # 1d6 average = 3.5, + 3 (STR) = 6.5
        assert avg_damage == 6.5, f"Expected average damage 6.5, got {avg_damage}"

    def test_thrown_weapon_fighting_in_character_export(
        self, fighter_with_thrown_weapon_fighting
    ):
        """Test that Thrown Weapon Fighting bonus appears correctly in character export."""
        char_data = fighter_with_thrown_weapon_fighting.to_character()
        attacks = char_data.get("attacks", [])

        # Find the Spear
        spear = next((a for a in attacks if a["name"] == "Spear"), None)
        assert spear is not None, "Should have Spear in exported attacks"

        # Melee damage should not have TWF
        damage = spear.get("damage", "")
        assert damage == "1d6 + 3", (
            f"Spear melee damage should be 1d6 + 3, got: {damage}"
        )

        # Throw damage should include TWF bonus
        throw_damage = spear.get("throw_damage", "")
        assert throw_damage == "1d6 + 5", (
            f"Exported Spear throw damage should be 1d6 + 5, got: {throw_damage}"
        )

        # Check throw average damage
        avg_throw_damage = spear.get("avg_throw_damage")
        assert avg_throw_damage == 8.5, (
            f"Exported throw average damage should be 8.5, got {avg_throw_damage}"
        )
