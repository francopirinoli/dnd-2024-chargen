#!/usr/bin/env python3
"""
Pytest tests for Rogue class and subclass features.
"""

import pytest
from modules.character_builder import CharacterBuilder


def build_rogue(level, subclass=None):
    """Helper to build a Rogue character at a given level."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_background("Criminal")
    builder.set_class("Rogue", level)
    if subclass and level >= 3:
        builder.set_subclass(subclass)
    return builder.to_character()


class TestRogueBaseFeatures:
    """Test Rogue base class features."""

    def test_hit_die(self):
        character = build_rogue(1)
        assert character["class_data"]["hit_die"] == 8

    def test_saving_throw_proficiencies(self):
        character = build_rogue(1)
        saves = character["proficiencies"]["saving_throws"]
        assert "Dexterity" in saves
        assert "Intelligence" in saves

    def test_armor_proficiencies(self):
        character = build_rogue(1)
        assert "Light armor" in character["proficiencies"]["armor"]

    def test_weapon_proficiencies(self):
        character = build_rogue(1)
        weapons = character["proficiencies"]["weapons"]
        assert "Simple weapons" in weapons
        assert "Martial weapons with Finesse or Light property" in weapons

    def test_level_1_sneak_attack(self):
        character = build_rogue(1)
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Sneak Attack" in names

    def test_level_1_expertise(self):
        character = build_rogue(1)
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Expertise" in names

    def test_level_1_thieves_cant_grants_language(self):
        character = build_rogue(1)
        languages = character["proficiencies"]["languages"]
        assert "Thieves' Cant" in languages

    def test_level_1_weapon_mastery(self):
        character = build_rogue(1)
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Weapon Mastery" in names

    def test_level_2_cunning_action(self):
        character = build_rogue(2)
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Cunning Action" in names

    def test_level_3_steady_aim(self):
        character = build_rogue(3, "Thief")
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Steady Aim" in names

    def test_level_5_cunning_strike(self):
        character = build_rogue(5, "Thief")
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Cunning Strike" in names

    def test_level_5_uncanny_dodge(self):
        character = build_rogue(5, "Thief")
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Uncanny Dodge" in names

    def test_level_6_expertise(self):
        character = build_rogue(6, "Thief")
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        # Builder deduplicates features by name, so only one "Expertise" appears
        # but the effect from level 6 is still applied
        assert "Expertise" in names

    def test_level_7_evasion(self):
        character = build_rogue(7, "Thief")
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Evasion" in names

    def test_level_7_reliable_talent(self):
        character = build_rogue(7, "Thief")
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Reliable Talent" in names

    def test_level_11_improved_cunning_strike(self):
        character = build_rogue(11, "Thief")
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Improved Cunning Strike" in names

    def test_level_14_devious_strikes(self):
        character = build_rogue(14, "Thief")
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Devious Strikes" in names

    def test_level_15_slippery_mind_save_proficiency(self):
        character = build_rogue(15, "Thief")
        saves = character["proficiencies"]["saving_throws"]
        assert "Wisdom" in saves
        assert "Charisma" in saves

    def test_level_15_slippery_mind_feature(self):
        character = build_rogue(15, "Thief")
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Slippery Mind" in names

    def test_level_18_elusive(self):
        character = build_rogue(18, "Thief")
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Elusive" in names

    def test_level_20_stroke_of_luck(self):
        character = build_rogue(20, "Thief")
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        assert "Stroke of Luck" in names

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (1, ["Expertise", "Sneak Attack", "Thieves' Cant", "Weapon Mastery"]),
            (2, ["Cunning Action"]),
            (3, ["Steady Aim"]),
            (5, ["Cunning Strike", "Uncanny Dodge"]),
            (7, ["Evasion", "Reliable Talent"]),
            (14, ["Devious Strikes"]),
            (18, ["Elusive"]),
            (20, ["Stroke of Luck"]),
        ],
    )
    def test_rogue_feature_progression(self, level, expected_features):
        character = build_rogue(level, "Thief" if level >= 3 else None)
        class_features = character["features"]["class"]
        names = [f["name"] for f in class_features]
        for feature_name in expected_features:
            assert feature_name in names, f"Expected '{feature_name}' at level {level}"


class TestThiefFeatures:
    """Test Thief subclass features."""

    def test_level_3_fast_hands(self):
        character = build_rogue(3, "Thief")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Fast Hands" in names

    def test_level_3_second_story_work(self):
        character = build_rogue(3, "Thief")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Second-Story Work" in names

    def test_level_9_supreme_sneak(self):
        character = build_rogue(9, "Thief")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Supreme Sneak" in names

    def test_level_13_use_magic_device(self):
        character = build_rogue(13, "Thief")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Use Magic Device" in names

    def test_level_17_thiefs_reflexes(self):
        character = build_rogue(17, "Thief")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Thief's Reflexes" in names

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Fast Hands", "Second-Story Work"]),
            (9, ["Supreme Sneak"]),
            (13, ["Use Magic Device"]),
            (17, ["Thief's Reflexes"]),
        ],
    )
    def test_thief_feature_progression(self, level, expected_features):
        character = build_rogue(level, "Thief")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        for feature_name in expected_features:
            assert feature_name in names, f"Expected '{feature_name}' at level {level}"


class TestAssassinFeatures:
    """Test Assassin subclass features."""

    def test_level_3_assassinate(self):
        character = build_rogue(3, "Assassin")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Assassinate" in names

    def test_level_3_assassins_tools_proficiency(self):
        character = build_rogue(3, "Assassin")
        tools = character["proficiencies"]["tools"]
        assert "Disguise Kit" in tools
        assert "Poisoner's Kit" in tools

    def test_level_9_infiltration_expertise(self):
        character = build_rogue(9, "Assassin")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Infiltration Expertise" in names

    def test_level_13_envenom_weapons(self):
        character = build_rogue(13, "Assassin")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Envenom Weapons" in names

    def test_level_17_death_strike(self):
        character = build_rogue(17, "Assassin")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Death Strike" in names

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Assassinate", "Assassin's Tools"]),
            (9, ["Infiltration Expertise"]),
            (13, ["Envenom Weapons"]),
            (17, ["Death Strike"]),
        ],
    )
    def test_assassin_feature_progression(self, level, expected_features):
        character = build_rogue(level, "Assassin")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        for feature_name in expected_features:
            assert feature_name in names, f"Expected '{feature_name}' at level {level}"


class TestArcaneTricksterFeatures:
    """Test Arcane Trickster subclass features and spellcasting."""

    def test_level_3_spellcasting_feature(self):
        character = build_rogue(3, "Arcane Trickster")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Spellcasting" in names

    def test_level_3_mage_hand_legerdemain(self):
        character = build_rogue(3, "Arcane Trickster")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Mage Hand Legerdemain" in names

    def test_level_3_spellcasting_ability(self):
        character = build_rogue(3, "Arcane Trickster")
        stats = character["spellcasting_stats"]
        assert stats["spellcasting_ability"] == "Intelligence"

    def test_level_3_spell_slots(self):
        character = build_rogue(3, "Arcane Trickster")
        spell_slots = character["spell_slots"]
        # At level 3, third-casters get 2 level-1 slots
        assert spell_slots.get("1st") == 2

    def test_level_3_max_cantrips_prepared(self):
        character = build_rogue(3, "Arcane Trickster")
        stats = character["spellcasting_stats"]
        assert stats["max_cantrips_prepared"] == 2

    def test_level_7_spell_slots(self):
        character = build_rogue(7, "Arcane Trickster")
        spell_slots = character["spell_slots"]
        # At level 7, third-casters get 4/2 slots
        assert spell_slots.get("1st") == 4
        assert spell_slots.get("2nd") == 2

    def test_level_10_max_cantrips_prepared(self):
        character = build_rogue(10, "Arcane Trickster")
        stats = character["spellcasting_stats"]
        assert stats["max_cantrips_prepared"] == 3

    def test_level_9_magical_ambush(self):
        character = build_rogue(9, "Arcane Trickster")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Magical Ambush" in names

    def test_level_13_versatile_trickster(self):
        character = build_rogue(13, "Arcane Trickster")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Versatile Trickster" in names

    def test_level_17_spell_thief(self):
        character = build_rogue(17, "Arcane Trickster")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Spell Thief" in names

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Spellcasting", "Mage Hand Legerdemain"]),
            (9, ["Magical Ambush"]),
            (13, ["Versatile Trickster"]),
            (17, ["Spell Thief"]),
        ],
    )
    def test_arcane_trickster_feature_progression(self, level, expected_features):
        character = build_rogue(level, "Arcane Trickster")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        for feature_name in expected_features:
            assert feature_name in names, f"Expected '{feature_name}' at level {level}"


class TestSoulknifeFeatures:
    """Test Soulknife subclass features."""

    def test_level_3_psionic_power(self):
        character = build_rogue(3, "Soulknife")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Psionic Power" in names

    def test_level_3_psychic_blades(self):
        character = build_rogue(3, "Soulknife")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Psychic Blades" in names

    def test_level_9_soul_blades(self):
        character = build_rogue(9, "Soulknife")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Soul Blades" in names

    def test_level_13_psychic_veil(self):
        character = build_rogue(13, "Soulknife")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Psychic Veil" in names

    def test_level_17_rend_mind(self):
        character = build_rogue(17, "Soulknife")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Rend Mind" in names

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Psionic Power", "Psychic Blades"]),
            (9, ["Soul Blades"]),
            (13, ["Psychic Veil"]),
            (17, ["Rend Mind"]),
        ],
    )
    def test_soulknife_feature_progression(self, level, expected_features):
        character = build_rogue(level, "Soulknife")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        for feature_name in expected_features:
            assert feature_name in names, f"Expected '{feature_name}' at level {level}"


class TestRogueEffects:
    """Test that Rogue effects are correctly applied."""

    def test_slippery_mind_adds_saves_at_level_15(self):
        """Slippery Mind at level 15 should add Wisdom and Charisma save proficiencies."""
        character = build_rogue(15, "Thief")
        saves = character["proficiencies"]["saving_throws"]
        # Base Rogue saves + Slippery Mind
        assert "Dexterity" in saves
        assert "Intelligence" in saves
        assert "Wisdom" in saves
        assert "Charisma" in saves

    def test_slippery_mind_not_at_level_14(self):
        """At level 14, should only have base Rogue saves."""
        character = build_rogue(14, "Thief")
        saves = character["proficiencies"]["saving_throws"]
        assert "Dexterity" in saves
        assert "Intelligence" in saves
        assert "Wisdom" not in saves
        assert "Charisma" not in saves

    def test_thieves_cant_language(self):
        """Thieves' Cant grants the Thieves' Cant language."""
        character = build_rogue(1)
        languages = character["proficiencies"]["languages"]
        assert "Thieves' Cant" in languages

    def test_thieves_cant_additional_language_choice_in_features(self):
        """Thieves' Cant exposes a single language choice in class features."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Criminal")
        builder.set_class("Rogue", 1)
        features = builder.get_class_features_and_choices()
        lang_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "thieves_cant_language"),
            None,
        )
        assert lang_choice is not None
        assert lang_choice["count"] == 1

    def test_thieves_cant_language_choice_includes_rare_languages(self):
        """The language choice pool for Thieves' Cant includes rare languages."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Criminal")
        builder.set_class("Rogue", 1)
        features = builder.get_class_features_and_choices()
        lang_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "thieves_cant_language"),
            None,
        )
        assert lang_choice is not None
        options = lang_choice["options"]
        assert "Elvish" in options
        assert "Abyssal" in options
        assert "Sylvan" in options

    def test_thieves_cant_additional_language_applied(self):
        """Chosen Thieves' Cant additional language is added as a proficiency."""
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
            "thieves_cant_language": "Elvish",
        })
        character = builder.to_character()
        languages = character["proficiencies"]["languages"]
        assert "Thieves' Cant" in languages
        assert "Elvish" in languages

    def test_thieves_cant_rare_language_choice_applied(self):
        """A rare language (e.g. Sylvan) can be selected as the Thieves' Cant additional language."""
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
            "thieves_cant_language": "Sylvan",
        })
        character = builder.to_character()
        languages = character["proficiencies"]["languages"]
        assert "Thieves' Cant" in languages
        assert "Sylvan" in languages

    def test_assassin_tool_proficiency(self):
        """Assassin grants Disguise Kit and Poisoner's Kit."""
        character = build_rogue(3, "Assassin")
        tools = character["proficiencies"]["tools"]
        assert "Disguise Kit" in tools
        assert "Poisoner's Kit" in tools

    def test_arcane_trickster_has_spellcasting(self):
        """Arcane Trickster should have Intelligence-based spellcasting."""
        character = build_rogue(3, "Arcane Trickster")
        stats = character["spellcasting_stats"]
        assert stats["has_spellcasting"] is True
        assert stats["spellcasting_ability"] == "Intelligence"

    def test_arcane_trickster_prepared_spells_count(self):
        """Arcane Trickster at level 3 should have 3 max prepared spells."""
        character = build_rogue(3, "Arcane Trickster")
        stats = character["spellcasting_stats"]
        assert stats["max_spells_prepared"] == 3


def build_rogue_with_choices(level, expertise_1=None, expertise_6=None, subclass=None):
    """Build a Rogue using apply_choices so expertise selections are honoured."""
    builder = CharacterBuilder()
    choices = {
        "character_name": "Test Rogue",
        "level": level,
        "class": "Rogue",
        "species": "Human",
        "background": "Criminal",
        "skill_choices": ["Stealth", "Perception", "Deception", "Athletics"],
        "ability_scores": {
            "Strength": 10,
            "Dexterity": 15,
            "Constitution": 14,
            "Intelligence": 12,
            "Wisdom": 10,
            "Charisma": 8,
        },
        "background_bonuses": {"Dexterity": 2, "Intelligence": 1},
    }
    if subclass and level >= 3:
        choices["subclass"] = subclass
    if expertise_1:
        choices["rogue_expertise_skills_1"] = expertise_1
    if expertise_6:
        choices["rogue_expertise_skills_6"] = expertise_6
    builder.apply_choices(choices)
    return builder.to_character()


class TestRogueExpertise:
    """Regression tests for GitHub Issue: Rogue level 1 Expertise choice not offered."""

    def test_level_1_expertise_applied_from_choice(self):
        """Level-1 Expertise choice fills skill_expertise when submitted."""
        character = build_rogue_with_choices(1, expertise_1=["Stealth", "Perception"])
        assert "Stealth" in character["skill_expertise"]
        assert "Perception" in character["skill_expertise"]

    def test_level_1_expertise_doubles_proficiency_bonus(self):
        """Stealth with Expertise should show expertise=True in skills dict."""
        character = build_rogue_with_choices(1, expertise_1=["Stealth", "Perception"])
        assert character["skills"]["stealth"]["expertise"] is True
        assert character["skills"]["perception"]["expertise"] is True

    def test_level_1_no_expertise_without_choice(self):
        """Without a choice, skill_expertise should remain empty."""
        character = build_rogue_with_choices(1)
        assert character.get("skill_expertise", []) == []

    def test_level_6_both_expertise_tiers_applied(self):
        """Level-6 Rogue with both choices should have all four skills marked as Expertise."""
        character = build_rogue_with_choices(
            6,
            expertise_1=["Stealth", "Perception"],
            expertise_6=["Deception", "Athletics"],
            subclass="Thief",
        )
        expertise = character.get("skill_expertise", [])
        assert "Stealth" in expertise
        assert "Perception" in expertise
        assert "Deception" in expertise
        assert "Athletics" in expertise

    def test_level_6_only_level1_choice_applied(self):
        """If only the level-1 choice is submitted at level 6, only those two are added."""
        character = build_rogue_with_choices(
            6,
            expertise_1=["Stealth", "Perception"],
            subclass="Thief",
        )
        expertise = character.get("skill_expertise", [])
        assert "Stealth" in expertise
        assert "Perception" in expertise
        # Level-6 choice not submitted yet → zero extras
        assert "Deception" not in expertise
        assert "Athletics" not in expertise

    def test_expertise_choice_picker_in_nested_choices_level_1(self):
        """preview-step API should include an Expertise picker at level 1."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test",
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
        })
        features = builder.get_class_features_and_choices()
        choice_keys = [c.get("choice_key") for c in features["choices"]]
        assert "rogue_expertise_skills_1" in choice_keys

    def test_expertise_picker_options_limited_to_proficient_skills(self):
        """The Expertise picker's options must be exactly the character's skill proficiencies."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test",
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
        })
        features = builder.get_class_features_and_choices()
        expertise_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "rogue_expertise_skills_1"),
            None,
        )
        assert expertise_choice is not None, "Expertise picker not found in nested_choices"
        # Options must be a subset of the character's skill proficiencies
        char = builder.to_character()
        proficient_skills = set(char["proficiencies"]["skills"])
        assert set(expertise_choice["options"]) == proficient_skills

    def test_expertise_choice_picker_in_nested_choices_level_6(self):
        """preview-step API should include an Expertise picker for level 6 too."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test",
            "level": 6,
            "class": "Rogue",
            "subclass": "Thief",
            "species": "Human",
            "background": "Criminal",
            "skill_choices": ["Stealth", "Perception", "Deception", "Athletics"],
            "ability_scores": {
                "Strength": 10, "Dexterity": 15, "Constitution": 14,
                "Intelligence": 12, "Wisdom": 10, "Charisma": 8,
            },
            "background_bonuses": {"Dexterity": 2, "Intelligence": 1},
        })
        features = builder.get_class_features_and_choices()
        choice_keys = [c.get("choice_key") for c in features["choices"]]
        assert "rogue_expertise_skills_1" in choice_keys
        assert "rogue_expertise_skills_6" in choice_keys

    def test_expertise_count_is_two(self):
        """Each Expertise picker must require exactly 2 selections."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test",
            "level": 6,
            "class": "Rogue",
            "subclass": "Thief",
            "species": "Human",
            "background": "Criminal",
            "skill_choices": ["Stealth", "Perception", "Deception", "Athletics"],
            "ability_scores": {
                "Strength": 10, "Dexterity": 15, "Constitution": 14,
                "Intelligence": 12, "Wisdom": 10, "Charisma": 8,
            },
            "background_bonuses": {"Dexterity": 2, "Intelligence": 1},
        })
        features = builder.get_class_features_and_choices()
        for choice in features["choices"]:
            if choice.get("choice_key") in (
                "rogue_expertise_skills_1", "rogue_expertise_skills_6"
            ):
                assert choice["count"] == 2


class TestRogueSleightOfHandExpertise:
    """Regression tests: 'Sleight of Hand' expertise not applied due to name normalisation."""

    def _build(self, expertise_1=None):
        """Build a Rogue with Investigation/Stealth/Perception/Sleight of Hand as skill choices."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Test Rogue",
            "level": 1,
            "class": "Rogue",
            "species": "Human",
            "background": "Criminal",
            "skill_choices": ["Investigation", "Stealth", "Perception", "Sleight of Hand"],
            "ability_scores": {
                "Strength": 10, "Dexterity": 15, "Constitution": 14,
                "Intelligence": 12, "Wisdom": 10, "Charisma": 8,
            },
            "background_bonuses": {"Dexterity": 2, "Intelligence": 1},
        }
        if expertise_1:
            choices["rogue_expertise_skills_1"] = expertise_1
        builder.apply_choices(choices)
        return builder.to_character()

    def test_sleight_of_hand_marked_proficient(self):
        """Sleight of Hand selected as a class skill should appear as proficient in the skills dict."""
        char = self._build()
        assert "Sleight of Hand" in char["proficiencies"]["skills"]
        assert char["skills"]["sleight_of_hand"]["proficient"] is True

    def test_sleight_of_hand_expertise_applied(self):
        """Selecting 'Sleight of Hand' for expertise should mark it expert in the skills dict."""
        char = self._build(expertise_1=["Sleight of Hand", "Stealth"])
        assert "Sleight of Hand" in char.get("skill_expertise", [])
        assert char["skills"]["sleight_of_hand"]["expertise"] is True
        # Stealth should also work (regression guard)
        assert char["skills"]["stealth"]["expertise"] is True

    def test_sleight_of_hand_expertise_bonus_doubled(self):
        """Expertise on Sleight of Hand must double the proficiency bonus."""
        char = self._build(expertise_1=["Sleight of Hand", "Stealth"])
        prof_bonus = char["proficiency_bonus"]
        dex_mod = char["abilities"]["dexterity"]["modifier"]
        expected = dex_mod + prof_bonus * 2
        assert char["skills"]["sleight_of_hand"]["bonus"] == expected

    def test_expertise_picker_includes_sleight_of_hand(self):
        """The expertise picker options must include 'Sleight of Hand' when the character is proficient."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test",
            "level": 1,
            "class": "Rogue",
            "species": "Human",
            "background": "Criminal",
            "skill_choices": ["Investigation", "Stealth", "Perception", "Sleight of Hand"],
            "ability_scores": {
                "Strength": 10, "Dexterity": 15, "Constitution": 14,
                "Intelligence": 12, "Wisdom": 10, "Charisma": 8,
            },
            "background_bonuses": {"Dexterity": 2, "Intelligence": 1},
        })
        features = builder.get_class_features_and_choices()
        expertise_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "rogue_expertise_skills_1"),
            None,
        )
        assert expertise_choice is not None, "Expertise picker not found"
        assert "Sleight of Hand" in expertise_choice["options"]
        # All options must be from the character's skill proficiencies
        char = builder.to_character()
        proficient_skills = set(char["proficiencies"]["skills"])
        assert set(expertise_choice["options"]) == proficient_skills
