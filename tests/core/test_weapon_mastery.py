#!/usr/bin/env python3
"""
Unit tests for weapon mastery system.

Tests the weapon mastery tracking, selection, and application system
introduced for classes that have weapon mastery (Fighter, Rogue, Paladin, Ranger).
"""

import pytest
from pathlib import Path
from modules.character_builder import CharacterBuilder, SelectionValidationError


class TestWeaponMasterySystem:
    """Test weapon mastery tracking and calculations."""

    @pytest.fixture
    def fighter_builder(self):
        """Create a Fighter with weapon mastery."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Test Fighter",
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
        }
        builder.apply_choices(choices)
        return builder

    @pytest.fixture
    def rogue_builder(self):
        """Create a Rogue with weapon mastery."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Test Rogue",
            "species": "Halfling",
            "class": "Rogue",
            "level": 1,
            "background": "Criminal",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 16,
                "Constitution": 12,
                "Intelligence": 14,
                "Wisdom": 12,
                "Charisma": 10,
            },
            "skill_choices": ["Stealth", "Acrobatics", "Sleight of Hand", "Perception"],
        }
        builder.apply_choices(choices)
        return builder

    def test_fighter_mastery_count_by_level(self, fighter_builder):
        """Test Fighter weapon mastery count scales correctly."""
        stats = fighter_builder.calculate_weapon_mastery_stats()

        assert stats["has_mastery"] is True
        assert stats["max_masteries"] == 3  # Level 3 Fighter

        # Test scaling at different levels
        test_levels = [
            (1, 3),
            (3, 3),
            (4, 4),
            (9, 4),
            (10, 5),
            (15, 5),
            (16, 6),
            (20, 6),
        ]

        for level, expected_count in test_levels:
            builder = CharacterBuilder()
            choices = {
                "character_name": "Test Fighter",
                "species": "Human",
                "class": "Fighter",
                "level": level,
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
            }
            builder.apply_choices(choices)
            stats = builder.calculate_weapon_mastery_stats()
            assert stats["max_masteries"] == expected_count, (
                f"Level {level} should have {expected_count} masteries"
            )

    def test_rogue_mastery_constant(self, rogue_builder):
        """Test Rogue weapon mastery stays at 2."""
        stats = rogue_builder.calculate_weapon_mastery_stats()

        assert stats["has_mastery"] is True
        assert stats["max_masteries"] == 2

        # Test at higher level
        builder = CharacterBuilder()
        choices = {
            "character_name": "Test Rogue",
            "species": "Halfling",
            "class": "Rogue",
            "level": 10,
            "background": "Criminal",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 18,
                "Constitution": 12,
                "Intelligence": 14,
                "Wisdom": 12,
                "Charisma": 10,
            },
            "skill_choices": ["Stealth", "Acrobatics", "Sleight of Hand", "Perception"],
            "subclass": "Thief",
        }
        builder.apply_choices(choices)
        stats = builder.calculate_weapon_mastery_stats()
        assert stats["max_masteries"] == 2  # Still 2 at level 10

    def test_mastery_selection_and_storage(self, fighter_builder):
        """Test mastery selection is stored correctly."""
        # Apply mastery selections
        mastery_choices = ["Longsword", "Longbow", "Greatsword"]
        fighter_builder.character_data["weapon_masteries"]["selected"] = mastery_choices

        stats = fighter_builder.calculate_weapon_mastery_stats()
        assert stats["current_masteries"] == mastery_choices
        assert len(stats["current_masteries"]) == 3

    def test_mastery_export_import(self):
        """Test mastery selections survive export/import."""
        # Create character with masteries
        builder = CharacterBuilder()
        choices = {
            "character_name": "Test Fighter",
            "species": "Human",
            "class": "Fighter",
            "level": 5,
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
            "weapon_mastery_selections": ["Longsword", "Longbow", "Greatsword"],
        }
        builder.apply_choices(choices)

        # Export to JSON
        exported = builder.to_json()
        assert "weapon_mastery_selections" in exported["choices_made"]
        assert exported["choices_made"]["weapon_mastery_selections"] == [
            "Longsword",
            "Longbow",
            "Greatsword",
        ]

        # Reimport
        builder2 = CharacterBuilder()
        builder2.apply_choices(exported["choices_made"])
        stats = builder2.calculate_weapon_mastery_stats()
        assert stats["current_masteries"] == ["Longsword", "Longbow", "Greatsword"]

    def test_non_mastery_class(self):
        """Test classes without mastery return correct stats."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Test Wizard",
            "species": "Human",
            "class": "Wizard",
            "level": 3,
            "background": "Sage",
            "ability_scores": {
                "Strength": 8,
                "Dexterity": 12,
                "Constitution": 14,
                "Intelligence": 16,
                "Wisdom": 12,
                "Charisma": 10,
            },
            "skill_choices": ["Arcana", "History"],
        }
        builder.apply_choices(choices)

        stats = builder.calculate_weapon_mastery_stats()
        assert stats["has_mastery"] is False
        assert stats["max_masteries"] == 0
        assert stats["current_masteries"] == []

    def test_mastery_available_weapons(self, fighter_builder):
        """Test masterable weapons list is available."""
        stats = fighter_builder.calculate_weapon_mastery_stats()
        assert "available_weapons" in stats
        # Fighter should have extensive weapon list
        assert len(stats["available_weapons"]) > 0

    def test_mastery_properties_loaded(self):
        """Test mastery property definitions are loaded."""
        CharacterBuilder()
        # Check that mastery definitions exist
        mastery_file = Path("data/equipment/weapon_masteries.json")
        assert mastery_file.exists()

        import json

        with open(mastery_file, "r") as f:
            masteries = json.load(f)

        # Check for expected mastery properties
        expected_masteries = [
            "Cleave",
            "Graze",
            "Nick",
            "Push",
            "Sap",
            "Slow",
            "Topple",
            "Vex",
        ]
        for mastery in expected_masteries:
            assert mastery in masteries
            assert "name" in masteries[mastery]
            assert "description" in masteries[mastery]

    def test_mastery_management_view_includes_properties(self, fighter_builder):
        """build_mastery_management_view includes mastery_properties with description and weapons."""
        from modules.derived_stats import build_mastery_management_view

        result = build_mastery_management_view(fighter_builder)

        assert "mastery_properties" in result
        props = result["mastery_properties"]
        # At least one property should exist given a Fighter's weapon list
        assert len(props) > 0

        # Each property entry must have name, description, and weapons
        for prop_name, prop in props.items():
            assert prop["name"] == prop_name
            assert isinstance(prop["description"], str) and len(prop["description"]) > 0
            assert isinstance(prop["weapons"], list) and len(prop["weapons"]) > 0
            # Every weapon listed must be in the fighter's available weapons
            for w in prop["weapons"]:
                assert w in result["available_weapons"]

    def test_mastery_rejects_unavailable_weapon(self, fighter_builder):
        with pytest.raises(SelectionValidationError) as exc:
            fighter_builder.apply_choice("weapon_mastery_selections", ["Dagger", "Quarterstaff", "Wand"])
        assert exc.value.family == "weapon_mastery_selections"
        assert exc.value.code == "invalid_selection"

    def test_mastery_rejects_exceeding_limit(self, fighter_builder):
        with pytest.raises(SelectionValidationError) as exc:
            fighter_builder.apply_choice(
                "weapon_mastery_selections",
                ["Dagger", "Quarterstaff", "Longsword", "Longbow"],
            )
        assert any(v.get("reason") == "max_exceeded" for v in exc.value.violations)

    def test_mastery_rejects_duplicates(self, fighter_builder):
        with pytest.raises(SelectionValidationError) as exc:
            fighter_builder.apply_choice("weapon_mastery_selections", ["Dagger", "Dagger"])
        assert exc.value.code == "duplicate_selection"
