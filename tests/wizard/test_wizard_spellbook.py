#!/usr/bin/env python3
"""
Tests for Wizard Spellbook system according to D&D 2024 rules:
- Differentiating known (spellbook) spells and prepared spells
- Base spellbook progression (6 at L1, +2 per level)
- Subclass Savant school bonuses (2 at L3-4, +1 at each new slot tier: L5, 7, 9, 11, 13, 15, 17)
- Prepared spells must be drawn from the spellbook
- Backward compatibility: auto-populating spellbook when omitted
- build_spell_management_view metadata
"""

import pytest
from modules.character_builder import CharacterBuilder, SelectionValidationError
from modules.derived_stats import build_spell_management_view, calculate_wizard_spellbook_stats


class TestWizardSpellbookStats:
    """Test spellbook progression and Savant bonus calculations."""

    def test_level_1_wizard_spellbook_stats(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Novice Wizard",
            "class": "Wizard",
            "level": 1,
            "species": "Human",
            "background": "Sage",
            "ability_scores": {"Strength": 8, "Dexterity": 14, "Constitution": 14, "Intelligence": 16, "Wisdom": 12, "Charisma": 10},
        })
        stats = calculate_wizard_spellbook_stats(builder, 1)
        assert stats["base_spells"] == 6
        assert stats["savant_spells"] == 0
        assert stats["total_spells"] == 6
        assert stats["savant_school"] is None

    def test_level_3_wizard_without_subclass_spellbook_stats(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Generalist Wizard",
            "class": "Wizard",
            "level": 3,
            "species": "Human",
            "background": "Sage",
            "ability_scores": {"Strength": 8, "Dexterity": 14, "Constitution": 14, "Intelligence": 16, "Wisdom": 12, "Charisma": 10},
        })
        stats = calculate_wizard_spellbook_stats(builder, 3)
        assert stats["base_spells"] == 10  # 6 + (3-1)*2
        assert stats["savant_spells"] == 0
        assert stats["total_spells"] == 10

    @pytest.mark.parametrize(
        "subclass_name,expected_school",
        [
            ("Evoker", "Evocation"),
            ("Evocation", "Evocation"),
            ("Abjurer", "Abjuration"),
            ("Abjuration", "Abjuration"),
            ("Diviner", "Divination"),
            ("Divination", "Divination"),
            ("Illusionist", "Illusion"),
            ("Illusion", "Illusion"),
        ],
    )
    def test_level_3_savant_schools(self, subclass_name, expected_school):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Specialist Wizard",
            "class": "Wizard",
            "level": 3,
            "subclass": subclass_name,
            "species": "Human",
            "background": "Sage",
            "ability_scores": {"Strength": 8, "Dexterity": 14, "Constitution": 14, "Intelligence": 16, "Wisdom": 12, "Charisma": 10},
        })
        stats = calculate_wizard_spellbook_stats(builder, 3)
        assert stats["savant_school"] == expected_school
        assert stats["savant_spells"] == 2
        assert stats["base_spells"] == 10
        assert stats["total_spells"] == 12

    @pytest.mark.parametrize(
        "level,expected_base,expected_savant,expected_total",
        [
            (3, 10, 2, 12),
            (4, 12, 2, 14),
            (5, 14, 3, 17),   # 3rd level slots
            (6, 16, 3, 19),
            (7, 18, 4, 22),   # 4th level slots
            (9, 22, 5, 27),   # 5th level slots
            (11, 26, 6, 32),  # 6th level slots
            (13, 30, 7, 37),  # 7th level slots
            (15, 34, 8, 42),  # 8th level slots
            (17, 38, 9, 47),  # 9th level slots
            (20, 44, 9, 53),
        ],
    )
    def test_evoker_savant_progression(self, level, expected_base, expected_savant, expected_total):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Evoker",
            "class": "Wizard",
            "level": level,
            "subclass": "Evoker",
            "species": "Human",
            "background": "Sage",
            "ability_scores": {"Strength": 8, "Dexterity": 14, "Constitution": 14, "Intelligence": 16, "Wisdom": 12, "Charisma": 10},
        })
        stats = calculate_wizard_spellbook_stats(builder, level)
        assert stats["base_spells"] == expected_base
        assert stats["savant_spells"] == expected_savant
        assert stats["total_spells"] == expected_total


class TestWizardSpellManagementView:
    """Test derived view-model for spell management on Wizards."""

    def test_build_spell_management_view_for_wizard(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "View Test Wizard",
            "class": "Wizard",
            "level": 3,
            "subclass": "Evoker",
            "species": "Human",
            "background": "Sage",
            "ability_scores": {"Strength": 8, "Dexterity": 14, "Constitution": 14, "Intelligence": 16, "Wisdom": 12, "Charisma": 10},
            "spell_selections": {
                "cantrips": ["Fire Bolt", "Light", "Mage Hand"],
                "spellbook": ["Burning Hands", "Magic Missile", "Shield", "Detect Magic", "Mage Armor", "Sleep"],
                "spells": ["Burning Hands", "Magic Missile", "Shield"],
            },
        })
        view = build_spell_management_view(builder)
        assert view["has_spellbook"] is True
        assert view["spellbook_limits"]["savant_school"] == "Evocation"
        assert view["spellbook_limits"]["savant_spells"] == 2
        assert view["spellbook_limits"]["total_spells"] == 12

        spellbook_names = [s["name"] for s in view["spellbook"]]
        assert "Burning Hands" in spellbook_names
        assert "Shield" in spellbook_names

        assert view["current_selections"]["spellbook"] == [
            "Burning Hands", "Magic Missile", "Shield", "Detect Magic", "Mage Armor", "Sleep"
        ]
        assert view["current_selections"]["spells"] == ["Burning Hands", "Magic Missile", "Shield"]
        assert view["available_spellbook_spells"] is not None


class TestWizardSpellValidation:
    """Test validation of spellbook and prepared spells for Wizards."""

    def test_wizard_prepared_spells_must_be_in_spellbook(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test",
            "class": "Wizard",
            "level": 1,
            "species": "Human",
            "background": "Sage",
            "ability_scores": {"Strength": 8, "Dexterity": 14, "Constitution": 14, "Intelligence": 16, "Wisdom": 12, "Charisma": 10},
        })

        # Try to prepare a spell that is NOT in the spellbook
        with pytest.raises(SelectionValidationError) as exc_info:
            builder.apply_choice("spell_selections", {
                "cantrips": ["Fire Bolt", "Light", "Mage Hand"],
                "spellbook": ["Burning Hands", "Mage Armor", "Detect Magic"],
                "spells": ["Magic Missile"],  # not in spellbook!
            })

        err = exc_info.value
        violations = err.violations
        assert any(v.get("reason") == "not_in_spellbook" and "Magic Missile" in v.get("selections", []) for v in violations)

    def test_wizard_spellbook_rejects_non_class_spells(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test",
            "class": "Wizard",
            "level": 1,
            "species": "Human",
            "background": "Sage",
            "ability_scores": {"Strength": 8, "Dexterity": 14, "Constitution": 14, "Intelligence": 16, "Wisdom": 12, "Charisma": 10},
        })

        # Try to add Cure Wounds (Cleric spell, not on Wizard list) to Wizard spellbook
        with pytest.raises(SelectionValidationError) as exc_info:
            builder.apply_choice("spell_selections", {
                "cantrips": ["Fire Bolt", "Light", "Mage Hand"],
                "spellbook": ["Cure Wounds"],
                "spells": [],
            })

        err = exc_info.value
        assert any(v.get("field") == "spell_selections.spellbook" and "Cure Wounds" in v.get("selections", []) for v in err.violations)

    def test_backward_compatibility_auto_populates_spellbook(self):
        """When spellbook is omitted in spell_selections, it should auto-populate from spells."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Legacy Wizard",
            "class": "Wizard",
            "level": 1,
            "species": "Human",
            "background": "Sage",
            "ability_scores": {"Strength": 8, "Dexterity": 14, "Constitution": 14, "Intelligence": 16, "Wisdom": 12, "Charisma": 10},
            "spell_selections": {
                "cantrips": ["Fire Bolt", "Light", "Mage Hand"],
                "spells": ["Burning Hands", "Magic Missile"],
            },
        })
        char = builder.to_character()
        # Should not raise, and spellbook should contain the prepared spells
        assert "Burning Hands" in char["spells"]["spellbook"]
        assert "Magic Missile" in char["spells"]["spellbook"]
        assert char["choices_made"]["spell_selections"]["spellbook"] == ["Burning Hands", "Magic Missile"]
