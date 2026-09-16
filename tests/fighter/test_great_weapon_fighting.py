#!/usr/bin/env python3
"""
Unit tests for Great Weapon Fighting fighting style.

Tests that GWF adjusts average damage calculations for Two-Handed/Versatile weapons.
"""

import pytest
from modules.character_builder import CharacterBuilder


class TestGreatWeaponFighting:
    """Test Great Weapon Fighting fighting style functionality."""

    @pytest.fixture
    def fighter_with_gwf(self):
        """Create a Fighter with Great Weapon Fighting and a greatsword."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Greatsword Wielder",
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
                "class_equipment": "option_a",  # Gets Greatsword
                "background_equipment": "option_a",
            },
        }
        builder.apply_choices(choices)
        return builder

    @pytest.fixture
    def fighter_without_gwf(self):
        """Create a Fighter without Great Weapon Fighting."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Regular Swordsman",
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
                "class_equipment": "option_a",  # Gets Greatsword
                "background_equipment": "option_a",
            },
        }
        builder.apply_choices(choices)
        return builder

    def test_gwf_increases_greatsword_average_damage(
        self, fighter_with_gwf, fighter_without_gwf
    ):
        """Test that GWF increases average damage for greatsword (2d6)."""
        # With GWF
        weapon_data_gwf = fighter_with_gwf.calculate_weapon_attacks()
        attacks_gwf = weapon_data_gwf.get("attacks", [])
        greatsword_gwf = next(
            (a for a in attacks_gwf if a["name"] == "Greatsword"), None
        )
        assert greatsword_gwf is not None

        # Without GWF
        weapon_data_no_gwf = fighter_without_gwf.calculate_weapon_attacks()
        attacks_no_gwf = weapon_data_no_gwf.get("attacks", [])
        greatsword_no_gwf = next(
            (a for a in attacks_no_gwf if a["name"] == "Greatsword"), None
        )
        assert greatsword_no_gwf is not None

        # GWF should increase average damage
        # 2d6 normal: 2 * 3.5 + 3 = 10.0
        # 2d6 with GWF: 2 * 4.167 + 3 = 11.333 ≈ 11.3 (rounded)
        # (each d6 with GWF: (2*3.5 + 3+4+5+6)/6 = 25/6 = 4.167)
        avg_gwf = greatsword_gwf.get("avg_damage")
        avg_no_gwf = greatsword_no_gwf.get("avg_damage")

        assert avg_gwf > avg_no_gwf, "GWF should increase average damage"
        assert avg_no_gwf == 10.0, f"Expected 10.0 without GWF, got {avg_no_gwf}"
        assert avg_gwf == 11.3, f"Expected 11.3 with GWF, got {avg_gwf}"

    def test_gwf_adds_reroll_note(self, fighter_with_gwf):
        """Test that GWF adds a note about rerolling to weapon attacks."""
        weapon_data = fighter_with_gwf.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])

        greatsword = next((a for a in attacks if a["name"] == "Greatsword"), None)
        assert greatsword is not None

        # Check for GWF note
        damage_notes = greatsword.get("damage_notes", [])
        assert any(
            "GWF" in note or "reroll" in note.lower() for note in damage_notes
        ), f"Expected GWF reroll note, got: {damage_notes}"

    def test_gwf_only_applies_to_two_handed_weapons(self, fighter_with_gwf):
        """Test that GWF only affects Two-Handed or Versatile weapons."""
        weapon_data = fighter_with_gwf.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])

        for attack in attacks:
            properties = attack.get("properties", [])
            damage_notes = attack.get("damage_notes", [])
            weapon_name = attack.get("name", "")

            # Check if weapon qualifies for GWF
            # GWF only works on melee weapons with Two-Handed or Versatile
            any("Versatile" in prop for prop in properties)

            has_gwf_note = any(
                "GWF" in note or "reroll" in note.lower() for note in damage_notes
            )

            # Greatsword, Spear (versatile) should have GWF
            # Shortbow (even though two-handed) should NOT (it's ranged)
            # Based on actual weapon properties, not checking category here
            if weapon_name == "Greatsword":
                assert has_gwf_note, (
                    f"{weapon_name} (Two-Handed melee) should have GWF note"
                )
            elif weapon_name == "Spear":
                assert has_gwf_note, (
                    f"{weapon_name} (Versatile melee) should have GWF note"
                )
            elif weapon_name == "Shortbow":
                assert not has_gwf_note, (
                    f"{weapon_name} (ranged) should NOT have GWF note"
                )

    def test_gwf_affects_crit_damage(self, fighter_with_gwf, fighter_without_gwf):
        """Test that GWF also increases average crit damage."""
        # With GWF
        weapon_data_gwf = fighter_with_gwf.calculate_weapon_attacks()
        attacks_gwf = weapon_data_gwf.get("attacks", [])
        greatsword_gwf = next(
            (a for a in attacks_gwf if a["name"] == "Greatsword"), None
        )

        # Without GWF
        weapon_data_no_gwf = fighter_without_gwf.calculate_weapon_attacks()
        attacks_no_gwf = weapon_data_no_gwf.get("attacks", [])
        greatsword_no_gwf = next(
            (a for a in attacks_no_gwf if a["name"] == "Greatsword"), None
        )

        # Check crit damage
        crit_gwf = greatsword_gwf.get("avg_crit")
        crit_no_gwf = greatsword_no_gwf.get("avg_crit")

        assert crit_gwf > crit_no_gwf, "GWF should increase average crit damage"
        # Crit doubles dice: 4d6 normal = 4 * 3.5 + 3 = 17.0
        # 4d6 with GWF = 4 * 4.167 + 3 = 19.7 (rounded)
        assert crit_no_gwf == 17.0, f"Expected 17.0 crit without GWF, got {crit_no_gwf}"
        assert crit_gwf == 19.7, f"Expected 19.7 crit with GWF, got {crit_gwf}"

    def test_gwf_in_character_export(self, fighter_with_gwf):
        """Test that GWF benefits appear in character export."""
        char_data = fighter_with_gwf.to_character()
        attacks = char_data.get("attacks", [])

        greatsword = next((a for a in attacks if a["name"] == "Greatsword"), None)
        assert greatsword is not None

        # Should have increased average damage
        avg_damage = greatsword.get("avg_damage")
        assert avg_damage == 11.3, (
            f"Expected exported avg damage 11.3, got {avg_damage}"
        )

        # Should have GWF note
        damage_notes = greatsword.get("damage_notes", [])
        assert any("GWF" in note or "reroll" in note.lower() for note in damage_notes)
