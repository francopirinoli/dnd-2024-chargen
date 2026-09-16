#!/usr/bin/env python3
"""
Unit tests for Unarmed Fighting fighting style.

Tests that Unarmed Fighting modifies unarmed strike damage.
"""

import pytest
from modules.character_builder import CharacterBuilder


class TestUnarmedFighting:
    """Test Unarmed Fighting fighting style functionality."""

    @pytest.fixture
    def fighter_with_unarmed_fighting_no_weapons(self):
        """Create a Fighter with Unarmed Fighting and no weapons equipped."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Unarmed Fighter",
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
            "Fighting Style": "Unarmed Fighting",
            "equipment_selections": {
                "class_equipment": "option_a",
                "background_equipment": "option_a",
            },
        }
        builder.apply_choices(choices)

        # Remove all weapons to test the "no weapons" case
        builder.character_data["equipment"]["weapons"] = []

        return builder

    @pytest.fixture
    def fighter_with_unarmed_fighting_with_weapons(self):
        """Create a Fighter with Unarmed Fighting and weapons equipped."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Armed Fighter",
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
            "Fighting Style": "Unarmed Fighting",
            "equipment_selections": {
                "class_equipment": "option_a",  # Has weapons
                "background_equipment": "option_a",
            },
        }
        builder.apply_choices(choices)
        return builder

    @pytest.fixture
    def fighter_without_unarmed_fighting(self):
        """Create a Fighter without Unarmed Fighting."""
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
            "Fighting Style": "Defense",
            "equipment_selections": {
                "class_equipment": "option_a",
                "background_equipment": "option_a",
            },
        }
        builder.apply_choices(choices)
        return builder

    def test_unarmed_strike_always_present(self, fighter_without_unarmed_fighting):
        """Test that unarmed strike is always in the attacks list."""
        weapon_data = fighter_without_unarmed_fighting.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])

        unarmed = next((a for a in attacks if a["name"] == "Unarmed Strike"), None)
        assert unarmed is not None, "Unarmed Strike should always be present"

    def test_base_unarmed_strike_damage(self, fighter_without_unarmed_fighting):
        """Test base unarmed strike damage without Unarmed Fighting."""
        weapon_data = fighter_without_unarmed_fighting.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])

        unarmed = next((a for a in attacks if a["name"] == "Unarmed Strike"), None)
        assert unarmed is not None

        # Base unarmed: 1 + STR modifier (1 + 3 = 4)
        assert unarmed["damage"] == "4", (
            f"Base unarmed damage should be 4, got {unarmed['damage']}"
        )
        assert unarmed["avg_damage"] == 4.0, (
            f"Base unarmed avg should be 4.0, got {unarmed['avg_damage']}"
        )

    def test_unarmed_fighting_no_weapons_uses_1d8(
        self, fighter_with_unarmed_fighting_no_weapons
    ):
        """Test that Unarmed Fighting uses 1d8 when no weapons equipped."""
        weapon_data = (
            fighter_with_unarmed_fighting_no_weapons.calculate_weapon_attacks()
        )
        attacks = weapon_data.get("attacks", [])

        unarmed = next((a for a in attacks if a["name"] == "Unarmed Strike"), None)
        assert unarmed is not None

        # Should be 1d8 + STR (1d8 + 3)
        assert "1d8" in unarmed["damage"], (
            f"Should use 1d8 with no weapons, got {unarmed['damage']}"
        )
        assert unarmed["damage"] == "1d8 + 3"

        # 1d8 avg = 4.5, + 3 = 7.5
        assert unarmed["avg_damage"] == 7.5, (
            f"Expected 7.5 avg, got {unarmed['avg_damage']}"
        )

    def test_unarmed_fighting_with_weapons_uses_1d6(
        self, fighter_with_unarmed_fighting_with_weapons
    ):
        """Test that Unarmed Fighting uses 1d6 when weapons are equipped."""
        weapon_data = (
            fighter_with_unarmed_fighting_with_weapons.calculate_weapon_attacks()
        )
        attacks = weapon_data.get("attacks", [])

        unarmed = next((a for a in attacks if a["name"] == "Unarmed Strike"), None)
        assert unarmed is not None

        # Should be 1d6 + STR (1d6 + 3)
        assert "1d6" in unarmed["damage"], (
            f"Should use 1d6 with weapons, got {unarmed['damage']}"
        )
        assert unarmed["damage"] == "1d6 + 3"

        # 1d6 avg = 3.5, + 3 = 6.5
        assert unarmed["avg_damage"] == 6.5, (
            f"Expected 6.5 avg, got {unarmed['avg_damage']}"
        )

    def test_unarmed_fighting_has_grapple_note(
        self, fighter_with_unarmed_fighting_no_weapons
    ):
        """Test that Unarmed Fighting adds grapple damage note."""
        weapon_data = (
            fighter_with_unarmed_fighting_no_weapons.calculate_weapon_attacks()
        )
        attacks = weapon_data.get("attacks", [])

        unarmed = next((a for a in attacks if a["name"] == "Unarmed Strike"), None)
        assert unarmed is not None

        damage_notes = unarmed.get("damage_notes", [])
        assert any("grappled" in note.lower() for note in damage_notes), (
            f"Should mention grappled damage, got notes: {damage_notes}"
        )
        assert any("1d4" in note for note in damage_notes), (
            f"Should mention 1d4 grapple damage, got notes: {damage_notes}"
        )

    def test_unarmed_fighting_attack_bonus(
        self, fighter_with_unarmed_fighting_no_weapons
    ):
        """Test that unarmed strike gets proper attack bonus."""
        weapon_data = (
            fighter_with_unarmed_fighting_no_weapons.calculate_weapon_attacks()
        )
        attacks = weapon_data.get("attacks", [])

        unarmed = next((a for a in attacks if a["name"] == "Unarmed Strike"), None)
        assert unarmed is not None

        # STR mod (+3) + proficiency bonus (+2 at level 1) = +5
        assert unarmed["attack_bonus"] == 5, (
            f"Expected attack bonus +5, got {unarmed['attack_bonus']}"
        )
        assert unarmed["attack_bonus_display"] == "+5"

    def test_unarmed_strike_in_character_export(
        self, fighter_with_unarmed_fighting_no_weapons
    ):
        """Test that unarmed strike appears in character export."""
        char_data = fighter_with_unarmed_fighting_no_weapons.to_character()
        attacks = char_data.get("attacks", [])

        unarmed = next((a for a in attacks if a["name"] == "Unarmed Strike"), None)
        assert unarmed is not None, "Unarmed Strike should be in character export"

        # Verify it has all required fields
        assert "damage" in unarmed
        assert "avg_damage" in unarmed
        assert "attack_bonus" in unarmed
        assert unarmed["damage_type"] == "Bludgeoning"

    def test_base_unarmed_strike_damage_negative_str_mod(self):
        """Test base unarmed strike damage with a negative STR modifier floors at 0."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Weakling",
            "species": "Human",
            "class": "Fighter",
            "level": 1,
            "background": "Soldier",
            "ability_scores": {
                "Strength": 8,  # -1 modifier
                "Dexterity": 14,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 12,
                "Charisma": 10,
            },
            "skill_choices": ["Athletics", "Acrobatics"],
            "Fighting Style": "Defense",
            "equipment_selections": {
                "class_equipment": "option_a",
                "background_equipment": "option_a",
            },
        }
        builder.apply_choices(choices)
        weapon_data = builder.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])

        unarmed = next((a for a in attacks if a["name"] == "Unarmed Strike"), None)
        assert unarmed is not None

        # 1 + (-1) = 0; floor is 0, not 1
        assert unarmed["damage"] == "0", (
            f"Unarmed damage with STR 8 should be 0, got {unarmed['damage']}"
        )
        assert unarmed["avg_damage"] == 0.0, (
            f"Unarmed avg_damage with STR 8 should be 0.0, got {unarmed['avg_damage']}"
        )

    def test_unarmed_better_than_base(
        self, fighter_with_unarmed_fighting_no_weapons, fighter_without_unarmed_fighting
    ):
        """Test that Unarmed Fighting is better than base unarmed strike."""
        # With Unarmed Fighting
        weapon_data_with = (
            fighter_with_unarmed_fighting_no_weapons.calculate_weapon_attacks()
        )
        attacks_with = weapon_data_with.get("attacks", [])
        unarmed_with = next(
            (a for a in attacks_with if a["name"] == "Unarmed Strike"), None
        )

        # Without Unarmed Fighting
        weapon_data_without = (
            fighter_without_unarmed_fighting.calculate_weapon_attacks()
        )
        attacks_without = weapon_data_without.get("attacks", [])
        unarmed_without = next(
            (a for a in attacks_without if a["name"] == "Unarmed Strike"), None
        )

        # Unarmed Fighting should deal more damage
        assert unarmed_with["avg_damage"] > unarmed_without["avg_damage"], (
            f"Unarmed Fighting ({unarmed_with['avg_damage']}) should be better than base ({unarmed_without['avg_damage']})"
        )
