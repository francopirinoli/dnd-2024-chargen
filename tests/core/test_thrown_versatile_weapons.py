#!/usr/bin/env python3
"""
Unit tests for thrown and versatile weapon damage calculations.

Tests that weapons with Thrown property show separate throw damage,
and that Versatile weapons show one-handed and two-handed damage.
"""

import pytest
from modules.character_builder import CharacterBuilder


class TestThrownAndVersatileWeapons:
    """Test thrown and versatile weapon damage display."""

    @pytest.fixture
    def fighter_with_thrown_weapon_fighting(self):
        """Create a Fighter with Thrown Weapon Fighting (has Spear from background)."""
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
    def fighter_with_gwf(self):
        """Create a Fighter with Great Weapon Fighting (has Spear)."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Versatile Fighter",
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
            "Fighting Style": "Great Weapon Fighting",
            "equipment_selections": {
                "class_equipment": "option_a",
                "background_equipment": "option_a",  # Gets Spear
            },
        }
        builder.apply_choices(choices)
        return builder

    def test_thrown_weapon_shows_throw_damage(
        self, fighter_with_thrown_weapon_fighting
    ):
        """Test that thrown weapons (Spear) show separate throw damage calculation."""
        weapon_data = fighter_with_thrown_weapon_fighting.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])

        spear = next((a for a in attacks if a["name"] == "Spear"), None)
        assert spear is not None, "Should have Spear in weapon attacks"

        # Should have regular melee damage
        assert "damage" in spear
        assert spear["damage"] == "1d6 + 3", "Melee damage should be 1d6 + 3 (STR)"

        # Should have separate throw damage with Thrown Weapon Fighting bonus
        assert "throw_damage" in spear, "Spear should have throw_damage field"
        assert spear["throw_damage"] == "1d6 + 5", (
            "Throw damage should be 1d6 + 5 (STR +3, TWF +2)"
        )

        # Should have throw average damage
        assert "avg_throw_damage" in spear
        assert spear["avg_throw_damage"] == 8.5, "Throw avg should be 8.5"

    def test_versatile_weapon_shows_one_handed_and_two_handed(
        self, fighter_with_thrown_weapon_fighting
    ):
        """Test that versatile weapons (Spear) show one-handed and two-handed damage."""
        weapon_data = fighter_with_thrown_weapon_fighting.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])

        spear = next((a for a in attacks if a["name"] == "Spear"), None)
        assert spear is not None

        # Should have versatile damage options
        assert "damage_one_handed" in spear, "Spear should have one-handed damage"
        assert "damage_two_handed" in spear, "Spear should have two-handed damage"

        # One-handed should be 1d6
        assert spear["damage_one_handed"] == "1d6 + 3"
        assert spear["avg_one_handed"] == 6.5

        # Two-handed should be 1d8 (versatile die)
        assert spear["damage_two_handed"] == "1d8 + 3"
        assert spear["avg_two_handed"] == 7.5

    def test_versatile_with_gwf_affects_two_handed_damage(self, fighter_with_gwf):
        """Test that GWF increases two-handed versatile damage average."""
        weapon_data = fighter_with_gwf.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])

        spear = next((a for a in attacks if a["name"] == "Spear"), None)
        assert spear is not None

        # Two-handed with GWF should have increased average
        # 1d8 normal: 4.5, with GWF: 5.25, + 3 = 8.25 → rounds to 8.2
        assert "avg_two_handed" in spear
        avg_2h = spear["avg_two_handed"]
        assert avg_2h > 7.5, f"GWF should increase 2h avg above 7.5, got {avg_2h}"
        assert avg_2h == 8.2, f"Expected 8.2 with GWF, got {avg_2h}"

    def test_versatile_without_dueling_two_handed(self):
        """Test that Dueling bonus doesn't apply to two-handed versatile use."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Dueling Fighter",
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
            "Fighting Style": "Dueling",
            "equipment_selections": {
                "class_equipment": "option_a",
                "background_equipment": "option_a",
            },
        }
        builder.apply_choices(choices)

        weapon_data = builder.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])

        spear = next((a for a in attacks if a["name"] == "Spear"), None)
        assert spear is not None

        # One-handed should have Dueling: 1d6 + 3 (STR) + 2 (Dueling) = 1d6 + 5
        assert spear["damage_one_handed"] == "1d6 + 5"
        assert spear["avg_one_handed"] == 8.5

        # Two-handed should NOT have Dueling: 1d8 + 3 (STR only)
        assert spear["damage_two_handed"] == "1d8 + 3"
        assert spear["avg_two_handed"] == 7.5

    def test_spear_shows_all_three_damage_types(
        self, fighter_with_thrown_weapon_fighting
    ):
        """Test that Spear shows melee, throw, one-handed, and two-handed damage."""
        weapon_data = fighter_with_thrown_weapon_fighting.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])

        spear = next((a for a in attacks if a["name"] == "Spear"), None)
        assert spear is not None

        # Should have all damage calculations
        assert "damage" in spear  # Base melee
        assert "throw_damage" in spear  # Thrown version
        assert "damage_one_handed" in spear  # Versatile 1h
        assert "damage_two_handed" in spear  # Versatile 2h

        # Verify the values make sense
        # Regular damage should match one-handed (for one-handed melee weapon)
        assert spear["damage"] == spear["damage_one_handed"]

        # Throw should have TWF bonus
        assert "5" in spear["throw_damage"], "Throw damage should include TWF +2"

        # Two-handed should use larger die
        assert "1d8" in spear["damage_two_handed"]

    def test_in_character_export(self, fighter_with_thrown_weapon_fighting):
        """Test that thrown and versatile damage appear in character export."""
        char_data = fighter_with_thrown_weapon_fighting.to_character()
        attacks = char_data.get("attacks", [])

        spear = next((a for a in attacks if a["name"] == "Spear"), None)
        assert spear is not None

        # Verify all fields are in export
        assert "throw_damage" in spear
        assert "avg_throw_damage" in spear
        assert "damage_one_handed" in spear
        assert "damage_two_handed" in spear
        assert "avg_one_handed" in spear
        assert "avg_two_handed" in spear
