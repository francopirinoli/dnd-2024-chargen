#!/usr/bin/env python3
"""
Tests for get_language_options — standard/rare language splitting and
the rare_base_languages key introduced for the language wizard step.
"""

import pytest
from modules.character_builder import CharacterBuilder


class TestGetLanguageOptionsRareBaseLanguages:
    """Tests for rare_base_languages in get_language_options."""

    def test_returns_rare_base_languages_key(self):
        """get_language_options always returns a rare_base_languages key."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Fighter", 1)
        opts = builder.get_language_options()
        assert "rare_base_languages" in opts

    def test_no_rare_languages_for_non_rogue(self):
        """A Fighter without rare-language features has no rare_base_languages."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Fighter", 1)
        opts = builder.get_language_options()
        assert opts["rare_base_languages"] == []

    def test_rogue_thieves_cant_in_rare_base_languages(self):
        """Thieves' Cant (granted automatically by Rogue level 1) appears in rare_base_languages."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Criminal")
        builder.set_class("Rogue", 1)
        opts = builder.get_language_options()
        assert "Thieves' Cant" in opts["rare_base_languages"]
        # Must NOT appear in standard base_languages
        assert "Thieves' Cant" not in opts["base_languages"]

    def test_rogue_thieves_cant_not_in_available_languages(self):
        """Thieves' Cant must not be offered as a standard pick-able language."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Criminal")
        builder.set_class("Rogue", 1)
        opts = builder.get_language_options()
        assert "Thieves' Cant" not in opts["available_languages"]

    def test_common_not_in_rare_base_languages(self):
        """Common is always in base_languages, never in rare_base_languages."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Criminal")
        builder.set_class("Rogue", 1)
        opts = builder.get_language_options()
        assert "Common" in opts["base_languages"]
        assert "Common" not in opts["rare_base_languages"]

    def test_deft_explorer_chosen_rare_language_in_rare_base_languages(self):
        """A rare language chosen via Deft Explorer appears in rare_base_languages."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Ranger",
            "level": 2,
            "class": "Ranger",
            "species": "Human",
            "background": "Soldier",
            "skill_choices": ["Stealth", "Perception", "Survival"],
            "fighting_style": "Archery",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 15,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 14,
                "Charisma": 8,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
            "deft_explorer_expertise": "Stealth",
            "deft_explorer_languages": ["Sylvan", "Abyssal"],
        })
        opts = builder.get_language_options()
        assert "Sylvan" in opts["rare_base_languages"]
        assert "Abyssal" in opts["rare_base_languages"]
        # They must NOT be offered as additional standard picks
        assert "Sylvan" not in opts["available_languages"]
        assert "Abyssal" not in opts["available_languages"]

    def test_deft_explorer_standard_language_in_base_languages(self):
        """A standard language chosen via Deft Explorer appears in base_languages."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Ranger",
            "level": 2,
            "class": "Ranger",
            "species": "Human",
            "background": "Soldier",
            "skill_choices": ["Stealth", "Perception", "Survival"],
            "fighting_style": "Archery",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 15,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 14,
                "Charisma": 8,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
            "deft_explorer_expertise": "Stealth",
            "deft_explorer_languages": ["Elvish", "Draconic"],
        })
        opts = builder.get_language_options()
        assert "Elvish" in opts["base_languages"]
        assert "Draconic" in opts["base_languages"]
        # Already known → not in available picks
        assert "Elvish" not in opts["available_languages"]
        assert "Draconic" not in opts["available_languages"]

    def test_thieves_cant_additional_language_choice_grants_language(self):
        """The chosen Thieves' Cant additional language is tracked in the character."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Rogue",
            "level": 1,
            "class": "Rogue",
            "species": "Human",
            "background": "Criminal",
            "skill_choices": ["Stealth", "Perception", "Deception", "Athletics"],
            "ability_scores": {
                "Strength": 10, "Dexterity": 15, "Constitution": 14,
                "Intelligence": 12, "Wisdom": 10, "Charisma": 8,
            },
            "background_bonuses": {"Dexterity": 2, "Intelligence": 1},
            "thieves_cant_language": "Gnomish",
        })
        opts = builder.get_language_options()
        # Standard language chosen via Thieves' Cant → in base_languages
        assert "Gnomish" in opts["base_languages"]
        # Should not be offered again
        assert "Gnomish" not in opts["available_languages"]


class TestGetLanguageOptionsAllRareLanguages:
    """Tests for all_rare_languages and rare_languages choice in get_language_options."""

    def test_returns_all_rare_languages_key(self):
        """get_language_options always returns an all_rare_languages key."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Fighter", 1)
        opts = builder.get_language_options()
        assert "all_rare_languages" in opts

    def test_all_rare_languages_contains_full_rare_set_for_fighter(self):
        """A Fighter with no rare-language grants gets the full RARE_LANGUAGE_OPTIONS list."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Fighter", 1)
        opts = builder.get_language_options()
        for lang in CharacterBuilder.RARE_LANGUAGE_OPTIONS:
            assert lang in opts["all_rare_languages"]

    def test_all_rare_languages_excludes_already_known_rare(self):
        """Rare languages already granted (e.g. Thieves' Cant) are not offered in all_rare_languages."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Criminal")
        builder.set_class("Rogue", 1)
        opts = builder.get_language_options()
        # Thieves' Cant is already granted by Rogue, so not in selectable rare list
        assert "Thieves' Cant" not in opts["all_rare_languages"]

    def test_rare_languages_choice_adds_to_proficiencies(self):
        """Applying rare_languages choice adds them to the character's language proficiencies."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Fighter", 1)
        builder.apply_choices({"rare_languages": ["Sylvan", "Abyssal"]})
        character = builder.to_character()
        assert "Sylvan" in character["languages"]
        assert "Abyssal" in character["languages"]

    def test_rare_languages_does_not_count_against_standard_selection(self):
        """Selecting rare languages leaves standard selection_count unchanged."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Fighter", 1)
        builder.apply_choices({
            "languages": ["Elvish", "Dwarvish"],
            "rare_languages": ["Sylvan"],
        })
        opts = builder.get_language_options()
        assert opts["selection_count"] == 2
        assert set(opts["selected_languages"]) == {"Elvish", "Dwarvish"}

    def test_selected_rare_languages_key_returned(self):
        """get_language_options returns selected_rare_languages reflecting current rare picks."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Fighter", 1)
        builder.apply_choices({"rare_languages": ["Celestial"]})
        opts = builder.get_language_options()
        assert "selected_rare_languages" in opts
        assert "Celestial" in opts["selected_rare_languages"]

    def test_rare_languages_choice_not_in_all_rare_languages_if_already_granted(self):
        """Feature-granted rare languages (e.g. Thieves' Cant) are not in all_rare_languages."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Criminal")
        builder.set_class("Rogue", 1)
        opts = builder.get_language_options()
        # Thieves' Cant is feature-granted, so must not be in the selectable rare pool
        assert "Thieves' Cant" not in opts["all_rare_languages"]

    def test_rare_languages_invalid_language_ignored(self):
        """Non-rare (standard) and unknown languages are ignored in rare_languages choice."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Fighter", 1)
        builder.apply_choices({"rare_languages": ["Elvish", "FakeLang"]})
        opts = builder.get_language_options()
        assert "Elvish" not in opts["selected_rare_languages"]
        assert "FakeLang" not in opts["selected_rare_languages"]

    def test_rare_languages_cleared_on_reapply(self):
        """Reapplying rare_languages replaces the previous selection."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Fighter", 1)
        builder.apply_choices({"rare_languages": ["Sylvan"]})
        builder.apply_choices({"rare_languages": ["Abyssal"]})
        opts = builder.get_language_options()
        assert "Abyssal" in opts["selected_rare_languages"]
        assert "Sylvan" not in opts["selected_rare_languages"]


class TestRareLanguagesInStandardSelection:
    """Tests for rare languages being selected as part of the unified language allowance."""

    def test_rare_language_in_available_languages(self):
        """Celestial, Sylvan, etc. appear in available_languages."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Fighter", 1)
        opts = builder.get_language_options()
        assert "Celestial" in opts["available_languages"]
        assert "Sylvan" in opts["available_languages"]

    def test_select_rare_language_counts_towards_selection_count(self):
        """Selecting a rare language in 'languages' counts against selection_count (max 2)."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Fighter", 1)
        builder.apply_choices({"languages": ["Celestial", "Elvish"]})
        opts = builder.get_language_options()
        assert opts["selection_count"] == 2
        assert set(opts["selected_languages"]) == {"Celestial", "Elvish"}
        assert opts["selected_rare_languages"] == ["Celestial"]
        char = builder.to_character()
        assert "Celestial" in char["languages"]
        assert "Elvish" in char["languages"]

    def test_cannot_select_more_than_selection_count_with_rare(self):
        """Selecting 3 languages (standard + rare) caps at selection_count = 2."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Fighter", 1)
        builder.apply_choices({"languages": ["Celestial", "Elvish", "Dwarvish"]})
        opts = builder.get_language_options()
        assert len(opts["selected_languages"]) == 2
        assert set(opts["selected_languages"]) == {"Celestial", "Elvish"}

