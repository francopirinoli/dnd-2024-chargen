#!/usr/bin/env python3
"""
Unit tests for dual-wielding (two-weapon fighting) system.

Tests the automatic detection of dual-wielding scenarios and
offhand damage calculation for characters with two light weapons.
"""

import pytest
from modules.character_builder import CharacterBuilder


class TestDualWielding:
    """Test dual-wielding detection and offhand damage calculation."""

    @pytest.fixture
    def dual_wielding_fighter(self):
        """Create a Fighter with two light weapons."""
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
    def single_weapon_fighter(self):
        """Create a Fighter with one weapon."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Single Wielder",
            "species": "Human",
            "class": "Fighter",
            "level": 3,
            "background": "Soldier",
            "ability_scores": {
                "Strength": 16,
                "Dexterity": 14,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 12,
                "Charisma": 10,
            },
            "skill_choices": ["Athletics", "Intimidation"],
            "Fighting Style": "Dueling",
            "equipment_selections": {
                "class_equipment": "option_a",  # Gets Longsword and Shield
                "background_equipment": "option_a",
            },
        }
        builder.apply_choices(choices)
        return builder

    def test_dual_wielding_detection(self, dual_wielding_fighter):
        """Test that two light weapons trigger combination cards."""
        weapon_data = dual_wielding_fighter.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])
        combinations = weapon_data.get("combinations", [])

        # Find light weapons
        light_weapons = [atk for atk in attacks if "Light" in atk.get("properties", [])]

        assert len(light_weapons) >= 2, "Should have at least 2 light weapons"
        assert len(combinations) >= 1, "Should have at least 1 dual-wield combination"

        # Check combination structure
        for combo in combinations:
            assert "mainhand" in combo, "Combination should have mainhand"
            assert "offhand" in combo, "Combination should have offhand"
            assert "name" in combo, "Combination should have name"

    def test_dual_wield_combinations_are_server_ranked(self, dual_wielding_fighter):
        """Server ranks dual-wield combinations for frontend display."""
        combinations = dual_wielding_fighter.calculate_weapon_attacks().get("combinations", [])

        assert combinations
        assert combinations[0]["recommended"] is True
        assert combinations[0]["rank"] == 1
        scores = [
            (
                combo["mainhand"]["avg_damage"] + combo["offhand"]["avg_damage"],
                combo["mainhand"]["attack_bonus"] + combo["offhand"]["attack_bonus"],
            )
            for combo in combinations
        ]
        assert scores == sorted(scores, reverse=True)

    def test_single_weapon_no_offhand(self, single_weapon_fighter):
        """Test that single weapon doesn't get combination cards."""
        weapon_data = single_weapon_fighter.calculate_weapon_attacks()
        weapon_data.get("attacks", [])
        combinations = weapon_data.get("combinations", [])

        # Should have no combinations with only one weapon
        assert len(combinations) == 0, "Single weapon should not have combinations"

    def test_offhand_damage_no_ability_modifier(self):
        """Test offhand damage is dice-only (no positive ability mod)."""
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
            "Fighting Style": "Dueling",  # NOT Two-Weapon Fighting
            "equipment_selections": {
                "class_equipment": "option_b",  # Gets Scimitar and Shortsword
                "background_equipment": "option_a",
            },
        }
        builder.apply_choices(choices)

        weapon_data = builder.calculate_weapon_attacks()
        combinations = weapon_data.get("combinations", [])

        assert len(combinations) >= 1, "Should have at least one dual-wield combination"

        for combo in combinations:
            offhand = combo.get("offhand", {})
            offhand_dmg = offhand.get("damage", "")
            # Should be just dice (e.g., "1d4" or "1d6"), not "1d4 + 3"
            # Without Two-Weapon Fighting, offhand doesn't get positive ability mod
            assert "+" not in offhand_dmg, (
                "Offhand shouldn't add positive ability mod without Two-Weapon Fighting"
            )

    def test_offhand_damage_with_negative_modifier(self):
        """Test offhand damage includes negative ability modifier."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Dual Wielder",
            "species": "Human",
            "class": "Fighter",
            "level": 3,
            "background": "Soldier",
            "ability_scores": {
                "Strength": 8,  # enforce negative modifier
                "Dexterity": 8,  # enforce negative modifier
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 12,
                "Charisma": 10,
            },
            "skill_choices": ["Athletics", "Acrobatics"],
            "Fighting Style": "Dueling",  # Use Dueling to avoid Two-Weapon Fighting bonuses
            "equipment_selections": {
                "class_equipment": "option_b",  # Gets Scimitar and Shortsword
                "background_equipment": "option_a",
            },
        }
        builder.apply_choices(choices)

        weapon_data = builder.calculate_weapon_attacks()
        combinations = weapon_data.get("combinations", [])

        assert len(combinations) >= 1, "Should have at least one dual-wield combination"

        for combo in combinations:
            offhand = combo.get("offhand", {})
            offhand_dmg = offhand.get("damage", "")
            # Should include negative modifier (e.g., "1d4 - 1") since DEX is 8 (-1 mod)
            assert "-" in offhand_dmg, "Offhand should subtract negative modifier"

    def test_offhand_average_damage_calculation(self, dual_wielding_fighter):
        """Test offhand average damage is calculated correctly."""
        weapon_data = dual_wielding_fighter.calculate_weapon_attacks()
        combinations = weapon_data.get("combinations", [])

        assert len(combinations) >= 1, "Should have at least one dual-wield combination"

        for combo in combinations:
            offhand = combo.get("offhand", {})
            avg_offhand = offhand.get("avg_damage")

            assert avg_offhand is not None, "Offhand should have average damage"
            assert isinstance(avg_offhand, (int, float))
            assert avg_offhand > 0, "Average damage should be positive"

    def test_mixed_weapons_only_light_get_offhand(self):
        """Test that only light weapons appear in dual-wield combinations."""

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

        weapon_data = builder.calculate_weapon_attacks()
        attacks = weapon_data.get("attacks", [])
        combinations = weapon_data.get("combinations", [])

        # Find light weapons
        light_weapons = [atk for atk in attacks if "Light" in atk.get("properties", [])]

        # Should have 2+ light weapons to trigger dual-wielding
        if len(light_weapons) >= 2:
            assert len(combinations) >= 1, (
                "Should have at least one dual-wield combination"
            )

            # All weapons in combinations should be light weapons
            for combo in combinations:
                mainhand_name = combo.get("mainhand", {}).get("name")
                offhand_name = combo.get("offhand", {}).get("name")

                # Check both weapons are in the light weapons list
                light_weapon_names = [w.get("name") for w in light_weapons]
                assert mainhand_name in light_weapon_names, (
                    f"{mainhand_name} should be a light weapon"
                )
                assert offhand_name in light_weapon_names, (
                    f"{offhand_name} should be a light weapon"
                )

    def test_offhand_damage_in_character_export(self, dual_wielding_fighter):
        """Test dual-wield combinations appear in character export."""
        char_data = dual_wielding_fighter.to_character()

        attack_combinations = char_data.get("attack_combinations", [])

        assert len(attack_combinations) >= 1, (
            "Should have at least one dual-wield combination"
        )

        for combo in attack_combinations:
            assert "mainhand" in combo, "Combination should have mainhand"
            assert "offhand" in combo, "Combination should have offhand"

            offhand = combo.get("offhand", {})
            assert "damage" in offhand, "Offhand should have damage"
            assert "avg_damage" in offhand, "Offhand should have average damage"
