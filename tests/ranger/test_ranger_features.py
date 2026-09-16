#!/usr/bin/env python3
"""
Pytest tests for Ranger class features and all four subclasses:
Hunter, Beast Master, Gloom Stalker, Fey Wanderer.
"""

import pytest
from modules.character_builder import CharacterBuilder


def build_ranger(level, subclass):
    """Helper to build a complete Ranger character at a given level with a subclass."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_background("Soldier")
    builder.set_class("Ranger", level)
    builder.set_subclass(subclass)
    return builder.to_character()


def build_ranger_with_choices(
    level,
    deft_explorer_expertise=None,
    expertise_skills=None,
    fighting_style="Archery",
    druidic_warrior_cantrips=None,
):
    """Build a Ranger via apply_choices so expertise selections are honored."""
    builder = CharacterBuilder()
    choices = {
        "character_name": "Test Ranger",
        "level": level,
        "class": "Ranger",
        "species": "Human",
        "background": "Soldier",
        "skill_choices": ["Stealth", "Perception", "Survival"],
        "fighting_style": fighting_style,
        "ability_scores": {
            "Strength": 10,
            "Dexterity": 15,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 14,
            "Charisma": 8,
        },
        "background_bonuses": {"Strength": 2, "Constitution": 1},
    }
    if level >= 3:
        choices["subclass"] = "Hunter"
        choices["hunters_prey"] = "Colossus Slayer"
    if level >= 7:
        choices["defensive_tactics"] = "Escape the Horde"
    if deft_explorer_expertise is not None:
        choices["deft_explorer_expertise"] = deft_explorer_expertise
    if expertise_skills is not None:
        choices["expertise_skills"] = expertise_skills
    if druidic_warrior_cantrips is not None:
        choices["Druidic Warrior_bonus_cantrip"] = druidic_warrior_cantrips

    builder.apply_choices(choices)
    return builder


# ---------------------------------------------------------------------------
# Base class features (use Hunter as default subclass)
# ---------------------------------------------------------------------------

class TestRangerBaseFeatures:
    """Test Ranger base class features across all levels."""

    def test_level_1_spellcasting_has_spellcasting(self):
        character = build_ranger(1, "Hunter")
        assert character["spellcasting_stats"]["has_spellcasting"] is True

    def test_level_1_spellcasting_ability(self):
        character = build_ranger(1, "Hunter")
        assert character["spellcasting_stats"]["spellcasting_ability"] == "Wisdom"

    def test_level_1_spell_slots(self):
        character = build_ranger(1, "Hunter")
        spell_slots = character["spell_slots"]
        assert spell_slots.get("1st") == 2

    def test_level_1_favored_enemy(self):
        """Favored Enemy grants Hunter's Mark as always prepared."""
        character = build_ranger(1, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Favored Enemy" in class_features
        always_prepared = character["spells"]["always_prepared"]
        assert "Hunter's Mark" in always_prepared

    def test_level_1_weapon_mastery(self):
        character = build_ranger(1, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Weapon Mastery" in class_features

    def test_level_2_deft_explorer(self):
        character = build_ranger(2, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Deft Explorer" in class_features

    def test_level_2_fighting_style(self):
        character = build_ranger(2, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Fighting Style" in class_features

    def test_level_3_ranger_subclass(self):
        character = build_ranger(3, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Ranger Subclass" not in class_features
        # Subclass features should be present
        subclass_features = character["features"]["subclass"]
        assert len(subclass_features) > 0

    def test_level_5_extra_attack(self):
        character = build_ranger(5, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Extra Attack" in class_features

    def test_level_6_roving(self):
        character = build_ranger(6, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Roving" in class_features

    def test_level_6_roving_speed_effect(self):
        """Roving should apply an increase_speed effect."""
        character = build_ranger(6, "Hunter")
        effects = character.get("effects", [])
        assert any(
            e["type"] == "increase_speed" for e in effects
        ), "Expected increase_speed effect from Roving"

    def test_level_9_expertise(self):
        character = build_ranger(9, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Expertise" in class_features

    def test_level_10_tireless(self):
        character = build_ranger(10, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Tireless" in class_features

    def test_level_13_relentless_hunter(self):
        character = build_ranger(13, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Relentless Hunter" in class_features

    def test_level_13_relentless_hunter_description(self):
        character = build_ranger(13, "Hunter")
        feature = next(
            f for f in character["features"]["class"] if f["name"] == "Relentless Hunter"
        )
        assert "Concentration" in feature["description"]

    def test_level_14_natures_veil(self):
        character = build_ranger(14, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Nature's Veil" in class_features

    def test_level_14_natures_veil_description(self):
        character = build_ranger(14, "Hunter")
        feature = next(
            f for f in character["features"]["class"] if f["name"] == "Nature's Veil"
        )
        assert "Invisible" in feature["description"]

    def test_level_17_precise_hunter(self):
        character = build_ranger(17, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Precise Hunter" in class_features

    def test_level_18_feral_senses(self):
        character = build_ranger(18, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Feral Senses" in class_features

    def test_level_18_feral_senses_description(self):
        character = build_ranger(18, "Hunter")
        feature = next(
            f for f in character["features"]["class"] if f["name"] == "Feral Senses"
        )
        assert "Blindsight" in feature["description"]

    def test_level_19_epic_boon(self):
        character = build_ranger(19, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Epic Boon" in class_features

    def test_level_20_foe_slayer(self):
        character = build_ranger(20, "Hunter")
        class_features = [f["name"] for f in character["features"]["class"]]
        assert "Foe Slayer" in class_features

    def test_level_20_foe_slayer_description(self):
        character = build_ranger(20, "Hunter")
        feature = next(
            f for f in character["features"]["class"] if f["name"] == "Foe Slayer"
        )
        assert "d10" in feature["description"]


class TestRangerExpertiseChoices:
    """Regression tests for Issue #114 Ranger expertise choices."""

    def test_level_2_has_deft_explorer_expertise_choice(self):
        builder = build_ranger_with_choices(2)
        features = builder.get_class_features_and_choices()

        deft_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "deft_explorer_expertise"),
            None,
        )
        assert deft_choice is not None
        assert deft_choice["count"] == 1

    def test_level_2_deft_explorer_expertise_options_match_proficient_skills(self):
        """Expertise picker options must equal the character's proficient skills (not empty)."""
        builder = build_ranger_with_choices(2)
        features = builder.get_class_features_and_choices()

        deft_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "deft_explorer_expertise"),
            None,
        )
        assert deft_choice is not None, "deft_explorer_expertise choice not found"
        char = builder.to_character()
        proficient_skills = set(char["proficiencies"]["skills"])
        assert len(proficient_skills) > 0, "Test setup must produce at least one proficient skill"
        assert len(deft_choice["options"]) > 0, "Expertise options must not be empty"
        assert set(deft_choice["options"]) == proficient_skills

    def test_level_2_deft_explorer_expertise_options_fallback_when_no_proficiencies(self):
        """When no proficiencies are resolved yet, options fall back to class skill options."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test",
            "level": 2,
            "class": "Ranger",
            "ability_scores": {
                "Strength": 10, "Dexterity": 15, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 14, "Charisma": 8,
            },
        })
        features = builder.get_class_features_and_choices()
        deft_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "deft_explorer_expertise"),
            None,
        )
        assert deft_choice is not None
        assert len(deft_choice["options"]) > 0, "Fallback must produce non-empty options"

    def test_level_2_deft_explorer_choice_applies_expertise(self):
        character = build_ranger_with_choices(
            2,
            deft_explorer_expertise="Stealth",
        ).to_character()

        assert "Stealth" in character.get("skill_expertise", [])
        assert character["skills"]["stealth"]["expertise"] is True

    def test_level_2_deft_explorer_choice_titles_are_human_readable(self):
        """Regression: choice titles must show display_name, not raw key (e.g. 'Expertise' not 'deft_explorer_expertise')."""
        builder = build_ranger_with_choices(2)
        features = builder.get_class_features_and_choices()

        expertise_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "deft_explorer_expertise"),
            None,
        )
        assert expertise_choice is not None
        assert "deft_explorer_expertise" not in expertise_choice["title"]
        assert "Expertise" in expertise_choice["title"]

        language_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "deft_explorer_languages"),
            None,
        )
        assert language_choice is not None
        assert "deft_explorer_languages" not in language_choice["title"]
        assert "Languages" in language_choice["title"]

    def test_fey_wanderer_otherworldly_glamour_placeholder_not_exposed(self):
        """Regression test for Issue #189: unresolved placeholders must not leak into expertise options."""
        builder = CharacterBuilder()
        builder.apply_choices(
            {
                "character_name": "Test Ranger",
                "level": 3,
                "class": "Ranger",
                "subclass": "Fey Wanderer",
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
            }
        )

        features = builder.get_class_features_and_choices()
        deft_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "deft_explorer_expertise"),
            None,
        )

        assert deft_choice is not None
        assert "__otherworldly_glamour_skill__" not in deft_choice["options"]
        assert "__otherworldly_glamour_skill__" not in builder.to_character()["proficiencies"]["skills"]

    def test_level_9_has_expertise_choice(self):
        builder = build_ranger_with_choices(9)
        features = builder.get_class_features_and_choices()

        expertise_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "expertise_skills"),
            None,
        )
        assert expertise_choice is not None
        assert expertise_choice["count"] == 2

    def test_level_9_expertise_choices_apply_to_both_selected_skills(self):
        character = build_ranger_with_choices(
            9,
            deft_explorer_expertise="Athletics",
            expertise_skills=["Stealth", "Perception"],
        ).to_character()

        assert "Stealth" in character.get("skill_expertise", [])
        assert "Perception" in character.get("skill_expertise", [])
        assert character["skills"]["stealth"]["expertise"] is True
        assert character["skills"]["perception"]["expertise"] is True


class TestRangerDruidicWarrior:
    """Tests for Ranger Druidic Warrior fighting style option."""

    def test_level_2_fighting_style_options_include_druidic_warrior(self):
        builder = build_ranger_with_choices(2)
        features = builder.get_class_features_and_choices()
        fighting_style_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "fighting_style"),
            None,
        )
        druidic_cantrip_choice = next(
            (c for c in features["choices"] if c.get("feature_name") == "Druidic Warrior_bonus_cantrip"),
            None,
        )

        assert fighting_style_choice is not None
        assert "Druidic Warrior" in fighting_style_choice["options"]
        assert druidic_cantrip_choice is not None
        assert druidic_cantrip_choice["count"] == 2
        # depends_on must match the choice_key used in choicesMade so the UI
        # correctly shows/hides the cantrip picker (regression for depends_on bug)
        assert druidic_cantrip_choice.get("depends_on") == "fighting_style", (
            f"depends_on should be 'fighting_style', got {druidic_cantrip_choice.get('depends_on')!r}"
        )
        assert druidic_cantrip_choice.get("depends_on_value") == "Druidic Warrior"

    def test_druidic_warrior_grants_druidic_and_two_druid_cantrips(self):
        character = build_ranger_with_choices(
            2,
            fighting_style="Druidic Warrior",
            druidic_warrior_cantrips=["Guidance", "Shillelagh"],
        ).to_character()

        assert "Druidic" in character["proficiencies"]["languages"]
        always_prepared = character["spells"]["always_prepared"]
        assert "Guidance" in always_prepared
        assert "Shillelagh" in always_prepared


class TestRangerDeftExplorerLanguages:
    """Tests for Deft Explorer language choices (Ranger level 2)."""

    def test_level_2_has_deft_explorer_language_choice(self):
        """Deft Explorer exposes a 2-language choice in class features."""
        builder = build_ranger_with_choices(2)
        features = builder.get_class_features_and_choices()

        lang_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "deft_explorer_languages"),
            None,
        )
        assert lang_choice is not None
        assert lang_choice["count"] == 2

    def test_level_2_deft_explorer_language_choice_includes_rare_languages(self):
        """The language choice pool includes rare languages."""
        builder = build_ranger_with_choices(2)
        features = builder.get_class_features_and_choices()

        lang_choice = next(
            (c for c in features["choices"] if c.get("choice_key") == "deft_explorer_languages"),
            None,
        )
        assert lang_choice is not None
        options = lang_choice["options"]
        # Standard languages present
        assert "Elvish" in options
        # Rare languages present
        assert "Abyssal" in options
        assert "Sylvan" in options

    def test_level_2_deft_explorer_language_grant_applies(self):
        """Chosen Deft Explorer languages are added as proficiencies."""
        builder = CharacterBuilder()
        choices = {
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
            "deft_explorer_languages": ["Elvish", "Abyssal"],
        }
        builder.apply_choices(choices)
        character = builder.to_character()
        languages = character["proficiencies"]["languages"]
        assert "Elvish" in languages
        assert "Abyssal" in languages

    def test_level_2_deft_explorer_language_rare_language_allowed(self):
        """Rare languages (e.g. Sylvan, Undercommon) can be chosen via Deft Explorer."""
        builder = CharacterBuilder()
        choices = {
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
            "deft_explorer_languages": ["Sylvan", "Undercommon"],
        }
        builder.apply_choices(choices)
        character = builder.to_character()
        languages = character["proficiencies"]["languages"]
        assert "Sylvan" in languages
        assert "Undercommon" in languages


# ---------------------------------------------------------------------------
# Spell slot progression
# ---------------------------------------------------------------------------

class TestRangerSpellProgression:
    """Test Ranger spell slot progression at key levels."""

    def test_level_1_spell_slots(self):
        character = build_ranger(1, "Hunter")
        slots = character["spell_slots"]
        assert slots.get("1st") == 2

    def test_level_5_spell_slots(self):
        character = build_ranger(5, "Hunter")
        slots = character["spell_slots"]
        assert slots.get("1st") == 4
        assert slots.get("2nd") == 2

    def test_level_9_spell_slots(self):
        character = build_ranger(9, "Hunter")
        slots = character["spell_slots"]
        assert slots.get("3rd") == 2

    def test_level_20_spell_slots(self):
        character = build_ranger(20, "Hunter")
        slots = character["spell_slots"]
        assert slots.get("5th") == 2

    @pytest.mark.parametrize(
        "level,expected_slots",
        [
            (1, {"1st": 2}),
            (5, {"1st": 4, "2nd": 2}),
            (9, {"1st": 4, "2nd": 3, "3rd": 2}),
            (13, {"1st": 4, "2nd": 3, "3rd": 3, "4th": 1}),
            (17, {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 1}),
            (20, {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2}),
        ],
    )
    def test_spell_slot_progression(self, level, expected_slots):
        character = build_ranger(level, "Hunter")
        slots = character["spell_slots"]
        for slot_level, count in expected_slots.items():
            assert slots.get(slot_level) == count, (
                f"Level {level}: expected {slot_level}={count}, got {slots.get(slot_level)}"
            )


# ---------------------------------------------------------------------------
# Hunter subclass
# ---------------------------------------------------------------------------

class TestHunterFeatures:
    """Test Hunter subclass features."""

    def test_level_3_hunters_lore(self):
        character = build_ranger(3, "Hunter")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Hunter's Lore" in subclass_features

    def test_level_3_hunters_prey(self):
        character = build_ranger(3, "Hunter")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Hunter's Prey" in subclass_features

    def test_level_7_defensive_tactics(self):
        character = build_ranger(7, "Hunter")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Defensive Tactics" in subclass_features

    def test_level_11_superior_hunters_prey(self):
        character = build_ranger(11, "Hunter")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Superior Hunter's Prey" in subclass_features

    def test_level_15_superior_hunters_defense(self):
        character = build_ranger(15, "Hunter")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Superior Hunter's Defense" in subclass_features

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Hunter's Lore", "Hunter's Prey"]),
            (7, ["Defensive Tactics"]),
            (11, ["Superior Hunter's Prey"]),
            (15, ["Superior Hunter's Defense"]),
        ],
    )
    def test_hunter_feature_progression(self, level, expected_features):
        character = build_ranger(level, "Hunter")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        for feature_name in expected_features:
            assert feature_name in subclass_features, (
                f"Expected '{feature_name}' at level {level}"
            )


# ---------------------------------------------------------------------------
# Beast Master subclass
# ---------------------------------------------------------------------------

class TestBeastMasterFeatures:
    """Test Beast Master subclass features."""

    def test_level_3_primal_companion(self):
        character = build_ranger(3, "Beast Master")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Primal Companion" in subclass_features

    def test_level_7_exceptional_training(self):
        character = build_ranger(7, "Beast Master")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Exceptional Training" in subclass_features

    def test_level_11_bestial_fury(self):
        character = build_ranger(11, "Beast Master")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Bestial Fury" in subclass_features

    def test_level_15_share_spells(self):
        character = build_ranger(15, "Beast Master")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Share Spells" in subclass_features

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Primal Companion"]),
            (7, ["Exceptional Training"]),
            (11, ["Bestial Fury"]),
            (15, ["Share Spells"]),
        ],
    )
    def test_beast_master_feature_progression(self, level, expected_features):
        character = build_ranger(level, "Beast Master")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        for feature_name in expected_features:
            assert feature_name in subclass_features, (
                f"Expected '{feature_name}' at level {level}"
            )


# ---------------------------------------------------------------------------
# Gloom Stalker subclass
# ---------------------------------------------------------------------------

class TestGloomStalkerFeatures:
    """Test Gloom Stalker subclass features."""

    def test_level_3_dread_ambusher(self):
        character = build_ranger(3, "Gloom Stalker")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Dread Ambusher" in subclass_features

    def test_level_3_gloom_stalker_spells(self):
        character = build_ranger(3, "Gloom Stalker")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Gloom Stalker Spells" in subclass_features

    def test_level_3_umbral_sight(self):
        character = build_ranger(3, "Gloom Stalker")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Umbral Sight" in subclass_features

    def test_level_3_disguise_self_always_prepared(self):
        """Gloom Stalker Spells grants Disguise Self at level 3."""
        character = build_ranger(3, "Gloom Stalker")
        always_prepared = character["spells"]["always_prepared"]
        assert "Disguise Self" in always_prepared

    def test_level_3_darkvision(self):
        """Umbral Sight grants 60 ft darkvision."""
        character = build_ranger(3, "Gloom Stalker")
        assert character.get("darkvision", 0) >= 60

    def test_level_5_rope_trick_always_prepared(self):
        character = build_ranger(5, "Gloom Stalker")
        always_prepared = character["spells"]["always_prepared"]
        assert "Rope Trick" in always_prepared

    def test_level_7_iron_mind(self):
        character = build_ranger(7, "Gloom Stalker")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Iron Mind" in subclass_features

    def test_level_7_iron_mind_wisdom_save(self):
        """Iron Mind grants Wisdom saving throw proficiency."""
        character = build_ranger(7, "Gloom Stalker")
        saves = character["proficiencies"]["saving_throws"]
        assert "Wisdom" in saves

    def test_level_9_fear_always_prepared(self):
        character = build_ranger(9, "Gloom Stalker")
        always_prepared = character["spells"]["always_prepared"]
        assert "Fear" in always_prepared

    def test_level_11_stalkers_flurry(self):
        character = build_ranger(11, "Gloom Stalker")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Stalker's Flurry" in subclass_features

    def test_level_13_greater_invisibility_always_prepared(self):
        character = build_ranger(13, "Gloom Stalker")
        always_prepared = character["spells"]["always_prepared"]
        assert "Greater Invisibility" in always_prepared

    def test_level_15_shadowy_dodge(self):
        character = build_ranger(15, "Gloom Stalker")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Shadowy Dodge" in subclass_features

    def test_level_17_seeming_always_prepared(self):
        character = build_ranger(17, "Gloom Stalker")
        always_prepared = character["spells"]["always_prepared"]
        assert "Seeming" in always_prepared

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Dread Ambusher", "Gloom Stalker Spells", "Umbral Sight"]),
            (7, ["Iron Mind"]),
            (11, ["Stalker's Flurry"]),
            (15, ["Shadowy Dodge"]),
        ],
    )
    def test_gloom_stalker_feature_progression(self, level, expected_features):
        character = build_ranger(level, "Gloom Stalker")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        for feature_name in expected_features:
            assert feature_name in subclass_features, (
                f"Expected '{feature_name}' at level {level}"
            )

    @pytest.mark.parametrize(
        "level,expected_spell",
        [
            (3, "Disguise Self"),
            (5, "Rope Trick"),
            (9, "Fear"),
            (13, "Greater Invisibility"),
            (17, "Seeming"),
        ],
    )
    def test_gloom_stalker_spell_progression(self, level, expected_spell):
        character = build_ranger(level, "Gloom Stalker")
        always_prepared = character["spells"]["always_prepared"]
        assert expected_spell in always_prepared, (
            f"Expected '{expected_spell}' always prepared at level {level}"
        )


# ---------------------------------------------------------------------------
# Fey Wanderer subclass
# ---------------------------------------------------------------------------

class TestFeyWandererFeatures:
    """Test Fey Wanderer subclass features."""

    def test_level_3_dreadful_strikes(self):
        character = build_ranger(3, "Fey Wanderer")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Dreadful Strikes" in subclass_features

    def test_level_3_fey_wanderer_spells(self):
        character = build_ranger(3, "Fey Wanderer")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Fey Wanderer Spells" in subclass_features

    def test_level_3_otherworldly_glamour(self):
        character = build_ranger(3, "Fey Wanderer")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Otherworldly Glamour" in subclass_features

    def test_level_3_charm_person_always_prepared(self):
        """Fey Wanderer Spells grants Charm Person at level 3."""
        character = build_ranger(3, "Fey Wanderer")
        always_prepared = character["spells"]["always_prepared"]
        assert "Charm Person" in always_prepared

    def test_level_5_misty_step_always_prepared(self):
        character = build_ranger(5, "Fey Wanderer")
        always_prepared = character["spells"]["always_prepared"]
        assert "Misty Step" in always_prepared

    def test_level_7_beguiling_twist(self):
        character = build_ranger(7, "Fey Wanderer")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Beguiling Twist" in subclass_features

    def test_level_7_beguiling_twist_save_advantage_charmed(self):
        """Beguiling Twist grants advantage on saves against Charmed."""
        character = build_ranger(7, "Fey Wanderer")
        save_advantages = character.get("save_advantages", [])
        assert any(
            sa.get("condition") == "Charmed" for sa in save_advantages
        ), "Expected save advantage against Charmed"

    def test_level_7_beguiling_twist_save_advantage_frightened(self):
        """Beguiling Twist grants advantage on saves against Frightened."""
        character = build_ranger(7, "Fey Wanderer")
        save_advantages = character.get("save_advantages", [])
        assert any(
            sa.get("condition") == "Frightened" for sa in save_advantages
        ), "Expected save advantage against Frightened"

    def test_level_9_summon_fey_always_prepared(self):
        character = build_ranger(9, "Fey Wanderer")
        always_prepared = character["spells"]["always_prepared"]
        assert "Summon Fey" in always_prepared

    def test_level_11_fey_reinforcements(self):
        character = build_ranger(11, "Fey Wanderer")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Fey Reinforcements" in subclass_features

    def test_level_13_dimension_door_always_prepared(self):
        character = build_ranger(13, "Fey Wanderer")
        always_prepared = character["spells"]["always_prepared"]
        assert "Dimension Door" in always_prepared

    def test_level_15_misty_wanderer(self):
        character = build_ranger(15, "Fey Wanderer")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        assert "Misty Wanderer" in subclass_features

    def test_level_17_mislead_always_prepared(self):
        character = build_ranger(17, "Fey Wanderer")
        always_prepared = character["spells"]["always_prepared"]
        assert "Mislead" in always_prepared

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Dreadful Strikes", "Fey Wanderer Spells", "Otherworldly Glamour"]),
            (7, ["Beguiling Twist"]),
            (11, ["Fey Reinforcements"]),
            (15, ["Misty Wanderer"]),
        ],
    )
    def test_fey_wanderer_feature_progression(self, level, expected_features):
        character = build_ranger(level, "Fey Wanderer")
        subclass_features = [f["name"] for f in character["features"]["subclass"]]
        for feature_name in expected_features:
            assert feature_name in subclass_features, (
                f"Expected '{feature_name}' at level {level}"
            )

    @pytest.mark.parametrize(
        "level,expected_spell",
        [
            (3, "Charm Person"),
            (5, "Misty Step"),
            (9, "Summon Fey"),
            (13, "Dimension Door"),
            (17, "Mislead"),
        ],
    )
    def test_fey_wanderer_spell_progression(self, level, expected_spell):
        character = build_ranger(level, "Fey Wanderer")
        always_prepared = character["spells"]["always_prepared"]
        assert expected_spell in always_prepared, (
            f"Expected '{expected_spell}' always prepared at level {level}"
        )
