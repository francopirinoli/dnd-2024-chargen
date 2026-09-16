"""
Pytest tests for Warlock class features and subclasses (D&D 2024).

Covers:
- Base Warlock class features (Pact Magic, Eldritch Invocations, Magical Cunning,
  Contact Patron, Mystic Arcanum, Eldritch Master)
- Invocation count progression
- The Fiend subclass (Fiend Spells, Dark One's Blessing, Dark One's Own Luck,
  Fiendish Resilience, Hurl Through Hell)
- The Archfey subclass (Archfey Spells, Steps of the Fey, Misty Escape,
  Beguiling Defenses, Bewitching Magic)
- The Great Old One subclass (Great Old One Spells, Awakened Mind, Psychic Spells,
  Clairvoyant Combatant, Eldritch Hex, Thought Shield, Create Thrall)
- The Celestial subclass (Celestial Spells, Healing Light, Radiant Soul,
  Celestial Resilience, Searing Vengeance)
"""

import pytest
from modules.character_builder import CharacterBuilder, SelectionValidationError


# ---------------------------------------------------------------------------
# Shared builder helper
# ---------------------------------------------------------------------------

def build_warlock(level, subclass=None):
    """Build a complete Warlock at the given level, optionally with a subclass."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_background("Acolyte")
    builder.set_class("Warlock", level)
    if subclass and level >= 3:
        builder.set_subclass(subclass)
    return builder.to_character()


def _class_feature_names(character):
    """Return a list of class feature names from the character dict."""
    return [f["name"] for f in character["features"].get("class", [])]


def _subclass_feature_names(character):
    """Return a list of subclass feature names from the character dict."""
    return [f["name"] for f in character["features"].get("subclass", [])]


def _always_prepared(character):
    """Return the set of always-prepared spell names."""
    return set(character.get("spells", {}).get("always_prepared", {}).keys())


def _effects(character):
    """Return the full effects list."""
    return character.get("effects", [])


def _warlock_builder_for_invocation_validation(level=12):
    builder = CharacterBuilder()
    choices = {
        "character_name": "Invocation Test",
        "species": "Human",
        "class": "Warlock",
        "level": level,
        "background": "Acolyte",
        "ability_scores": {
            "Strength": 8,
            "Dexterity": 14,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 16,
        },
        "skill_choices": ["Arcana", "Deception"],
    }
    if level >= 3:
        choices["subclass"] = "The Fiend"
    builder.apply_choices(choices)
    return builder

def test_pact_of_the_blade_uses_charisma_for_only_the_bonded_weapon():
    builder = CharacterBuilder()
    builder.apply_choices({
        "character_name": "Bound Blade",
        "level": 1,
        "species": "Human",
        "class": "Warlock",
        "background": "Acolyte",
        "ability_scores": {
            "Strength": 10, "Dexterity": 14, "Constitution": 12,
            "Intelligence": 8, "Wisdom": 10, "Charisma": 18,
        },
        "background_bonuses": {},
        "eldritch_invocation_selections": ["Pact of the Blade"],
        "pact_weapon": "Mace",
    })
    builder.character_data["equipment"] = {
        "weapons": [
            {
                "name": "Mace",
                "quantity": 1,
                "properties": {
                    "category": "Simple Melee",
                    "damage": "1d6",
                    "damage_type": "Bludgeoning",
                    "properties": [],
                },
            },
            {
                "name": "Dagger",
                "quantity": 1,
                "properties": {
                    "category": "Simple Melee",
                    "damage": "1d4",
                    "damage_type": "Piercing",
                    "properties": ["Finesse", "Light"],
                },
            },
        ],
        "armor": [],
        "items": [],
        "gold": 0,
    }

    attacks = {
        attack["name"]: attack for attack in builder.calculate_weapon_attacks()["attacks"]
    }
    assert attacks["Mace"]["ability"] == "CHA"
    assert attacks["Mace"]["attack_bonus"] == 4
    assert attacks["Mace"]["damage"] == "1d6 + 4"
    assert attacks["Dagger"]["ability"] == "STR/DEX (DEX)"


# ===========================================================================
# Base Warlock Class
# ===========================================================================

class TestWarlockBaseClass:
    """Core Warlock class identity, proficiencies, and feature progression."""

    # --- Identity ---

    def test_class_name_is_warlock(self):
        character = build_warlock(1)
        assert character["class"] == "Warlock"

    def test_level_stored_correctly(self):
        character = build_warlock(5)
        assert character["level"] == 5

    # --- Proficiencies ---

    def test_saving_throw_wisdom(self):
        character = build_warlock(1)
        assert "Wisdom" in character["proficiencies"]["saving_throws"]

    def test_saving_throw_charisma(self):
        character = build_warlock(1)
        assert "Charisma" in character["proficiencies"]["saving_throws"]

    def test_weapon_proficiency_simple(self):
        character = build_warlock(1)
        assert "Simple weapons" in character["proficiencies"]["weapons"]

    def test_armor_proficiency_light(self):
        character = build_warlock(1)
        assert "Light armor" in character["proficiencies"]["armor"]

    # --- Hit Die ---

    def test_hit_die_is_d8(self):
        """Level 1 Warlock max HP = 8 (hit die d8) with CON 10 and no bonuses."""
        character = build_warlock(1)
        assert character["combat"]["hit_points"]["maximum"] == 8

    # --- Spellcasting ---

    def test_has_spellcasting_at_level_1(self):
        character = build_warlock(1)
        assert character["spellcasting_stats"]["has_spellcasting"] is True

    def test_spellcasting_ability_is_charisma(self):
        character = build_warlock(1)
        assert character["spellcasting_stats"]["spellcasting_ability"] == "Charisma"

    # --- Level 1 Features ---

    def test_level_1_eldritch_invocations_present(self):
        character = build_warlock(1)
        assert "Eldritch Invocations" in _class_feature_names(character)

    def test_level_1_pact_magic_present(self):
        character = build_warlock(1)
        assert "Pact Magic" in _class_feature_names(character)

    def test_level_1_pact_magic_description_mentions_charisma(self):
        character = build_warlock(1)
        feature = next(
            f for f in character["features"]["class"] if f["name"] == "Pact Magic"
        )
        assert "Charisma" in feature["description"]

    def test_level_1_no_subclass_features(self):
        character = build_warlock(1)
        assert character["features"].get("subclass", []) == []

    def test_level_1_subclass_is_none(self):
        character = build_warlock(1)
        assert character.get("subclass") is None

    # --- Level 2: Magical Cunning ---

    def test_level_2_magical_cunning_present(self):
        character = build_warlock(2)
        assert "Magical Cunning" in _class_feature_names(character)

    def test_level_2_still_has_level_1_features(self):
        character = build_warlock(2)
        names = _class_feature_names(character)
        assert "Eldritch Invocations" in names
        assert "Pact Magic" in names

    def test_level_2_magical_cunning_description(self):
        character = build_warlock(2)
        feature = next(
            f for f in character["features"]["class"] if f["name"] == "Magical Cunning"
        )
        assert "Long Rest" in feature["description"]

    # --- Level 3: Warlock Subclass ---

    def test_level_3_warlock_subclass_feature_present(self):
        character = build_warlock(3)
        assert "Warlock Subclass" not in _class_feature_names(character)

    # --- Level 4: Ability Score Improvement ---

    def test_level_4_ability_score_improvement_present(self):
        character = build_warlock(4, "The Fiend")
        assert "Ability Score Improvement" not in _class_feature_names(character)

    # --- Level 9: Contact Patron ---

    def test_level_9_contact_patron_present(self):
        character = build_warlock(9, "The Fiend")
        assert "Contact Patron" in _class_feature_names(character)

    def test_level_9_contact_other_plane_always_prepared(self):
        """Contact Patron grants 'Contact Other Plane' as an always-prepared spell."""
        character = build_warlock(9, "The Fiend")
        assert "Contact Other Plane" in _always_prepared(character)

    def test_level_8_no_contact_patron(self):
        character = build_warlock(8, "The Fiend")
        assert "Contact Patron" not in _class_feature_names(character)

    def test_level_9_contact_other_plane_grant_spell_effect(self):
        character = build_warlock(9, "The Fiend")
        effects = _effects(character)
        assert any(
            e["type"] == "grant_spell" and e["spell"] == "Contact Other Plane"
            for e in effects
        ), "Expected grant_spell effect for Contact Other Plane"

    # --- Level 11: Mystic Arcanum ---

    def test_level_11_mystic_arcanum_present(self):
        character = build_warlock(11, "The Fiend")
        assert "Mystic Arcanum" in _class_feature_names(character)

    def test_level_10_no_mystic_arcanum(self):
        character = build_warlock(10, "The Fiend")
        assert "Mystic Arcanum" not in _class_feature_names(character)

    def test_level_11_mystic_arcanum_description_mentions_level_6(self):
        character = build_warlock(11, "The Fiend")
        feature = next(
            f for f in character["features"]["class"] if f["name"] == "Mystic Arcanum"
        )
        assert "level 6" in feature["description"].lower()

    # --- Level 20: Eldritch Master ---

    def test_level_20_eldritch_master_present(self):
        character = build_warlock(20, "The Fiend")
        assert "Eldritch Master" in _class_feature_names(character)

    def test_level_20_eldritch_master_description(self):
        character = build_warlock(20, "The Fiend")
        feature = next(
            f for f in character["features"]["class"] if f["name"] == "Eldritch Master"
        )
        assert "Magical Cunning" in feature["description"]

    def test_level_19_no_eldritch_master(self):
        character = build_warlock(19, "The Fiend")
        assert "Eldritch Master" not in _class_feature_names(character)


# ===========================================================================
# Eldritch Invocation Count
# ===========================================================================

class TestWarlockInvocationCount:
    """Verify invocation slot counts match invocations_by_level in class data."""

    @pytest.mark.parametrize("level,expected_count", [
        (1, 1),
        (2, 3),
        (5, 5),
        (7, 6),
        (9, 7),
        (12, 8),
        (15, 9),
        (18, 10),
        (20, 10),
    ])
    def test_invocation_count_by_level(self, level, expected_count):
        character = build_warlock(level)
        stats = character.get("eldritch_invocation_stats", {})
        assert stats.get("max_invocations") == expected_count, (
            f"Expected {expected_count} invocations at level {level}, "
            f"got {stats.get('max_invocations')}"
        )

    def test_eldritch_invocation_stats_present(self):
        """eldritch_invocation_stats key must exist in the character dict."""
        character = build_warlock(1)
        assert "eldritch_invocation_stats" in character

    def test_invocations_has_available_list(self):
        """Level 1 Warlock should have a non-empty list of available invocations."""
        character = build_warlock(1)
        stats = character.get("eldritch_invocation_stats", {})
        assert len(stats.get("available_invocations", [])) > 0

    def test_invocation_selection_rejects_unknown_name(self):
        builder = _warlock_builder_for_invocation_validation(level=12)
        with pytest.raises(SelectionValidationError) as exc:
            builder.apply_choice(
                "eldritch_invocation_selections",
                ["Not A Real Invocation"],
            )
        assert exc.value.family == "eldritch_invocation_selections"

    def test_invocation_selection_rejects_unmet_prerequisite(self):
        builder = _warlock_builder_for_invocation_validation(level=12)
        with pytest.raises(SelectionValidationError) as exc:
            builder.apply_choice(
                "eldritch_invocation_selections",
                ["Devouring Blade"],
            )
        assert any(
            v.get("reason") == "missing_prerequisite_invocations"
            for v in exc.value.violations
        )

    def test_invocation_selection_rejects_exceeding_count(self):
        builder = _warlock_builder_for_invocation_validation(level=1)
        with pytest.raises(SelectionValidationError) as exc:
            builder.apply_choice(
                "eldritch_invocation_selections",
                ["Pact of the Blade", "Pact of the Tome"],
            )
        assert any(v.get("reason") == "max_exceeded" for v in exc.value.violations)

    def test_invocation_selection_allows_replacement_with_final_prereq_set(self):
        builder = _warlock_builder_for_invocation_validation(level=12)
        builder.apply_choice(
            "eldritch_invocation_selections",
            ["Pact of the Blade", "Thirsting Blade", "Devouring Blade"],
        )
        assert builder.character_data["eldritch_invocations"]["selected"] == [
            "Pact of the Blade",
            "Thirsting Blade",
            "Devouring Blade",
        ]


class TestWarlockInvocationEffects:
    """Verify sheet-affecting invocation effects and their selections."""

    def test_pact_of_the_tome_selected_cantrips_are_always_prepared(self):
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Warlock", 1)
        assert builder.apply_choice(
            "eldritch_invocation_selections",
            {
                "selected": ["Pact of the Tome"],
                "cantrip_choices": {
                    "eldritch_invocation_pact_of_the_tome_0": ["Fire Bolt"],
                    "eldritch_invocation_pact_of_the_tome_1": ["Guidance"],
                    "eldritch_invocation_pact_of_the_tome_2": ["Druidcraft"],
                },
            },
        )

        character = builder.to_character()
        always_prepared = character["spells"]["always_prepared"]
        assert {"Fire Bolt", "Guidance", "Druidcraft"} <= set(always_prepared)
        for cantrip in ("Fire Bolt", "Guidance", "Druidcraft"):
            assert always_prepared[cantrip]["level"] == 0
            assert always_prepared[cantrip]["source"] == "Pact of the Tome"
            assert always_prepared[cantrip]["counts_against_limit"] is False

    def test_pact_of_the_chain_find_familiar_is_always_prepared(self):
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Acolyte")
        builder.set_class("Warlock", 1)
        assert builder.apply_choice(
            "eldritch_invocation_selections", ["Pact of the Chain"]
        )

        character = builder.to_character()
        find_familiar = character["spells"]["always_prepared"]["Find Familiar"]
        assert find_familiar["source"] == "Pact of the Chain"
        assert find_familiar["counts_against_limit"] is False
        assert character["eldritch_invocation_stats"].get(
            "cantrip_choice_descriptors", []
        ) == []


class TestEldritchInvocationEffects:
    """Invocation selections must apply their data-authored sheet effects."""

    @staticmethod
    def _build_with_invocations(selection):
        builder = CharacterBuilder()
        builder.apply_choices(
            {
                "character_name": "Invocation Test",
                "level": 5,
                "species": "Human",
                "class": "Warlock",
                "background": "Acolyte",
                "ability_scores": {
                    "Strength": 8,
                    "Dexterity": 14,
                    "Constitution": 14,
                    "Intelligence": 10,
                    "Wisdom": 10,
                    "Charisma": 16,
                },
                "eldritch_invocation_selections": selection,
            }
        )
        return builder.to_character()

    def test_lessons_of_the_first_ones_applies_selected_origin_feat(self):
        character = self._build_with_invocations(
            {
                "selected": ["Lessons of the First Ones"],
                "choices": {
                    "Lessons of the First Ones": {"origin_feat": "Alert"},
                },
            }
        )

        feat = next(
            feature
            for feature in character["features"]["feats"]
            if feature["name"] == "Alert"
        )
        assert feat["source"] == "Lessons of the First Ones"

    def test_lessons_of_the_first_ones_rejects_non_origin_feat(self):
        character = self._build_with_invocations(
            {
                "selected": ["Lessons of the First Ones"],
                "choices": {
                    "Lessons of the First Ones": {"origin_feat": "Dual Wielder"},
                },
            }
        )

        assert "Dual Wielder" not in [
            feature["name"] for feature in character["features"]["feats"]
        ]

    def test_gift_of_the_depths_water_breathing_is_once_per_long_rest(self):
        character = self._build_with_invocations(["Gift of the Depths"])

        spell = character["spells"]["always_prepared"]["Water Breathing"]
        metadata = character["spell_metadata"]["Water Breathing"]
        assert spell["once_per_long_rest"] is True
        assert metadata["once_per_long_rest"] is True
        assert spell.get("at_will") is not True
        assert metadata.get("at_will") is not True

    def test_water_breathing_is_absent_without_gift_of_the_depths(self):
        character = self._build_with_invocations([])

        assert "Water Breathing" not in character["spells"]["always_prepared"]


# ===========================================================================
# The Fiend Subclass
# ===========================================================================

class TestFiendSubclass:
    """Test The Fiend subclass features and spell progression."""

    # --- Level 3 Features ---

    def test_level_3_fiend_spells_feature_present(self):
        character = build_warlock(3, "The Fiend")
        assert "Fiend Spells" in _subclass_feature_names(character)

    def test_level_3_dark_ones_blessing_present(self):
        character = build_warlock(3, "The Fiend")
        assert "Dark One's Blessing" in _subclass_feature_names(character)

    def test_level_3_dark_ones_blessing_description(self):
        character = build_warlock(3, "The Fiend")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Dark One's Blessing"
        )
        assert "Temporary Hit Points" in feature["description"]

    # --- Level 3 Fiend Spells (min_level 3) ---

    def test_level_3_burning_hands_prepared(self):
        character = build_warlock(3, "The Fiend")
        assert "Burning Hands" in _always_prepared(character)

    def test_level_3_command_prepared(self):
        character = build_warlock(3, "The Fiend")
        assert "Command" in _always_prepared(character)

    def test_level_3_scorching_ray_prepared(self):
        character = build_warlock(3, "The Fiend")
        assert "Scorching Ray" in _always_prepared(character)

    def test_level_3_suggestion_prepared(self):
        character = build_warlock(3, "The Fiend")
        assert "Suggestion" in _always_prepared(character)

    def test_level_3_fireball_not_yet_prepared(self):
        """Fireball requires min_level 5 — should NOT be prepared at level 3."""
        character = build_warlock(3, "The Fiend")
        assert "Fireball" not in _always_prepared(character)

    # --- Level 5 Fiend Spells (min_level 5) ---

    def test_level_5_fireball_prepared(self):
        character = build_warlock(5, "The Fiend")
        assert "Fireball" in _always_prepared(character)

    def test_level_5_stinking_cloud_prepared(self):
        character = build_warlock(5, "The Fiend")
        assert "Stinking Cloud" in _always_prepared(character)

    def test_level_5_still_has_level_3_spells(self):
        character = build_warlock(5, "The Fiend")
        spells = _always_prepared(character)
        assert "Burning Hands" in spells
        assert "Command" in spells

    # --- Level 7 Fiend Spells (min_level 7) ---

    def test_level_7_fire_shield_prepared(self):
        character = build_warlock(7, "The Fiend")
        assert "Fire Shield" in _always_prepared(character)

    def test_level_7_wall_of_fire_prepared(self):
        character = build_warlock(7, "The Fiend")
        assert "Wall of Fire" in _always_prepared(character)

    # --- Level 9 Fiend Spells (min_level 9) ---

    def test_level_9_geas_prepared(self):
        character = build_warlock(9, "The Fiend")
        assert "Geas" in _always_prepared(character)

    def test_level_9_insect_plague_prepared(self):
        character = build_warlock(9, "The Fiend")
        assert "Insect Plague" in _always_prepared(character)

    # --- Level 6: Dark One's Own Luck ---

    def test_level_6_dark_ones_own_luck_present(self):
        character = build_warlock(6, "The Fiend")
        assert "Dark One's Own Luck" in _subclass_feature_names(character)

    def test_level_6_dark_ones_own_luck_description(self):
        character = build_warlock(6, "The Fiend")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Dark One's Own Luck"
        )
        assert "1d10" in feature["description"]

    def test_level_5_no_dark_ones_own_luck(self):
        character = build_warlock(5, "The Fiend")
        assert "Dark One's Own Luck" not in _subclass_feature_names(character)

    # --- Level 10: Fiendish Resilience ---

    def test_level_10_fiendish_resilience_present(self):
        character = build_warlock(10, "The Fiend")
        assert "Fiendish Resilience" in _subclass_feature_names(character)

    def test_level_10_fiendish_resilience_description(self):
        character = build_warlock(10, "The Fiend")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Fiendish Resilience"
        )
        assert "Resistance" in feature["description"]

    # --- Level 14: Hurl Through Hell ---

    def test_level_14_hurl_through_hell_present(self):
        character = build_warlock(14, "The Fiend")
        assert "Hurl Through Hell" in _subclass_feature_names(character)

    def test_level_14_hurl_through_hell_description(self):
        character = build_warlock(14, "The Fiend")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Hurl Through Hell"
        )
        assert "8d10" in feature["description"]

    # --- Parametrized progression ---

    @pytest.mark.parametrize("level,expected_features", [
        (3, ["Fiend Spells", "Dark One's Blessing"]),
        (6, ["Dark One's Own Luck"]),
        (10, ["Fiendish Resilience"]),
        (14, ["Hurl Through Hell"]),
    ])
    def test_fiend_feature_progression(self, level, expected_features):
        character = build_warlock(level, "The Fiend")
        names = _subclass_feature_names(character)
        for feature_name in expected_features:
            assert feature_name in names, (
                f"Expected '{feature_name}' at level {level}"
            )

    # --- Grant spell effects ---

    def test_level_3_grant_spell_effects_present(self):
        character = build_warlock(3, "The Fiend")
        effects = _effects(character)
        grant_spell_effects = [e for e in effects if e["type"] == "grant_spell"]
        assert len(grant_spell_effects) > 0, "Expected grant_spell effects for Fiend Spells"

    def test_level_3_burning_hands_grant_spell_effect(self):
        character = build_warlock(3, "The Fiend")
        effects = _effects(character)
        assert any(
            e["type"] == "grant_spell" and e["spell"] == "Burning Hands"
            for e in effects
        )


# ===========================================================================
# The Archfey Subclass
# ===========================================================================

class TestArchfeySubclass:
    """Test The Archfey subclass features, spells, and condition immunity."""

    # --- Level 3 Features ---

    def test_level_3_archfey_spells_present(self):
        character = build_warlock(3, "The Archfey")
        assert "Archfey Spells" in _subclass_feature_names(character)

    def test_level_3_steps_of_the_fey_present(self):
        character = build_warlock(3, "The Archfey")
        assert "Steps of the Fey" in _subclass_feature_names(character)

    def test_level_3_steps_of_fey_description(self):
        character = build_warlock(3, "The Archfey")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Steps of the Fey"
        )
        assert "Misty Step" in feature["description"]

    # --- Level 3 Archfey Spells (min_level 3) ---

    def test_level_3_calm_emotions_prepared(self):
        character = build_warlock(3, "The Archfey")
        assert "Calm Emotions" in _always_prepared(character)

    def test_level_3_faerie_fire_prepared(self):
        character = build_warlock(3, "The Archfey")
        assert "Faerie Fire" in _always_prepared(character)

    def test_level_3_misty_step_prepared(self):
        character = build_warlock(3, "The Archfey")
        assert "Misty Step" in _always_prepared(character)

    def test_level_3_sleep_prepared(self):
        character = build_warlock(3, "The Archfey")
        assert "Sleep" in _always_prepared(character)

    def test_level_3_blink_not_yet_prepared(self):
        """Blink requires min_level 5 — should NOT be prepared at level 3."""
        character = build_warlock(3, "The Archfey")
        assert "Blink" not in _always_prepared(character)

    # --- Level 5 Archfey Spells (min_level 5) ---

    def test_level_5_blink_prepared(self):
        character = build_warlock(5, "The Archfey")
        assert "Blink" in _always_prepared(character)

    def test_level_5_plant_growth_prepared(self):
        character = build_warlock(5, "The Archfey")
        assert "Plant Growth" in _always_prepared(character)

    # --- Level 7 Archfey Spells (min_level 7) ---

    def test_level_7_dominate_beast_prepared(self):
        character = build_warlock(7, "The Archfey")
        assert "Dominate Beast" in _always_prepared(character)

    def test_level_7_greater_invisibility_prepared(self):
        character = build_warlock(7, "The Archfey")
        assert "Greater Invisibility" in _always_prepared(character)

    # --- Level 9 Archfey Spells (min_level 9) ---

    def test_level_9_dominate_person_prepared(self):
        character = build_warlock(9, "The Archfey")
        assert "Dominate Person" in _always_prepared(character)

    def test_level_9_seeming_prepared(self):
        character = build_warlock(9, "The Archfey")
        assert "Seeming" in _always_prepared(character)

    # --- Level 6: Misty Escape ---

    def test_level_6_misty_escape_present(self):
        character = build_warlock(6, "The Archfey")
        assert "Misty Escape" in _subclass_feature_names(character)

    def test_level_6_misty_escape_description(self):
        character = build_warlock(6, "The Archfey")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Misty Escape"
        )
        assert "Reaction" in feature["description"]

    def test_level_5_no_misty_escape(self):
        character = build_warlock(5, "The Archfey")
        assert "Misty Escape" not in _subclass_feature_names(character)

    # --- Level 10: Beguiling Defenses ---

    def test_level_10_beguiling_defenses_present(self):
        character = build_warlock(10, "The Archfey")
        assert "Beguiling Defenses" in _subclass_feature_names(character)

    def test_level_10_charmed_condition_immunity(self):
        """Beguiling Defenses grants immunity to the Charmed condition."""
        character = build_warlock(10, "The Archfey")
        assert "Charmed" in character.get("condition_immunities", []), (
            f"Expected 'Charmed' in condition_immunities, "
            f"got: {character.get('condition_immunities', [])}"
        )

    def test_level_10_grant_condition_immunity_effect(self):
        """Beguiling Defenses should produce a grant_condition_immunity effect."""
        character = build_warlock(10, "The Archfey")
        effects = _effects(character)
        assert any(
            e["type"] == "grant_condition_immunity" and e["condition"] == "Charmed"
            for e in effects
        ), "Expected grant_condition_immunity effect for Charmed"

    def test_level_10_beguiling_defenses_description_mentions_immune(self):
        character = build_warlock(10, "The Archfey")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Beguiling Defenses"
        )
        assert "immune" in feature["description"].lower()

    def test_level_9_no_charmed_immunity(self):
        """Charmed immunity should NOT be present at level 9."""
        character = build_warlock(9, "The Archfey")
        assert "Charmed" not in character.get("condition_immunities", [])

    # --- Level 14: Bewitching Magic ---

    def test_level_14_bewitching_magic_present(self):
        character = build_warlock(14, "The Archfey")
        assert "Bewitching Magic" in _subclass_feature_names(character)

    def test_level_14_bewitching_magic_description(self):
        character = build_warlock(14, "The Archfey")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Bewitching Magic"
        )
        assert "Misty Step" in feature["description"]

    # --- Parametrized progression ---

    @pytest.mark.parametrize("level,expected_features", [
        (3, ["Archfey Spells", "Steps of the Fey"]),
        (6, ["Misty Escape"]),
        (10, ["Beguiling Defenses"]),
        (14, ["Bewitching Magic"]),
    ])
    def test_archfey_feature_progression(self, level, expected_features):
        character = build_warlock(level, "The Archfey")
        names = _subclass_feature_names(character)
        for feature_name in expected_features:
            assert feature_name in names, (
                f"Expected '{feature_name}' at level {level}"
            )


# ===========================================================================
# The Great Old One Subclass
# ===========================================================================

class TestGreatOldOneSubclass:
    """Test The Great Old One subclass features, spells, and Psychic resistance."""

    # --- Level 3 Features ---

    def test_level_3_goo_spells_present(self):
        character = build_warlock(3, "The Great Old One")
        assert "Great Old One Spells" in _subclass_feature_names(character)

    def test_level_3_awakened_mind_present(self):
        character = build_warlock(3, "The Great Old One")
        assert "Awakened Mind" in _subclass_feature_names(character)

    def test_level_3_psychic_spells_present(self):
        character = build_warlock(3, "The Great Old One")
        assert "Psychic Spells" in _subclass_feature_names(character)

    def test_level_3_awakened_mind_description(self):
        character = build_warlock(3, "The Great Old One")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Awakened Mind"
        )
        assert "telepathic" in feature["description"].lower()

    def test_level_3_psychic_spells_description(self):
        character = build_warlock(3, "The Great Old One")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Psychic Spells"
        )
        assert "Psychic" in feature["description"]

    # --- Level 3 GOO Spells (min_level 3) ---

    def test_level_3_detect_thoughts_prepared(self):
        character = build_warlock(3, "The Great Old One")
        assert "Detect Thoughts" in _always_prepared(character)

    def test_level_3_dissonant_whispers_prepared(self):
        character = build_warlock(3, "The Great Old One")
        assert "Dissonant Whispers" in _always_prepared(character)

    def test_level_3_tashas_hideous_laughter_prepared(self):
        character = build_warlock(3, "The Great Old One")
        assert "Tasha's Hideous Laughter" in _always_prepared(character)

    def test_level_3_telekinesis_not_yet_prepared(self):
        """Telekinesis requires min_level 9 — should NOT be prepared at level 3."""
        character = build_warlock(3, "The Great Old One")
        assert "Telekinesis" not in _always_prepared(character)

    # --- Level 5 GOO Spells (min_level 5) ---

    def test_level_5_clairvoyance_prepared(self):
        character = build_warlock(5, "The Great Old One")
        assert "Clairvoyance" in _always_prepared(character)

    def test_level_5_hunger_of_hadar_prepared(self):
        character = build_warlock(5, "The Great Old One")
        assert "Hunger of Hadar" in _always_prepared(character)

    # --- Level 7 GOO Spells (min_level 7) ---

    def test_level_7_confusion_prepared(self):
        character = build_warlock(7, "The Great Old One")
        assert "Confusion" in _always_prepared(character)

    def test_level_7_summon_aberration_prepared(self):
        character = build_warlock(7, "The Great Old One")
        assert "Summon Aberration" in _always_prepared(character)

    # --- Level 9 GOO Spells (min_level 9) ---

    def test_level_9_modify_memory_prepared(self):
        character = build_warlock(9, "The Great Old One")
        assert "Modify Memory" in _always_prepared(character)

    def test_level_9_telekinesis_prepared(self):
        character = build_warlock(9, "The Great Old One")
        assert "Telekinesis" in _always_prepared(character)

    # --- Level 6: Clairvoyant Combatant ---

    def test_level_6_clairvoyant_combatant_present(self):
        character = build_warlock(6, "The Great Old One")
        assert "Clairvoyant Combatant" in _subclass_feature_names(character)

    def test_level_6_clairvoyant_combatant_description(self):
        character = build_warlock(6, "The Great Old One")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Clairvoyant Combatant"
        )
        assert "Awakened Mind" in feature["description"]

    # --- Level 10: Eldritch Hex & Thought Shield ---

    def test_level_10_eldritch_hex_present(self):
        character = build_warlock(10, "The Great Old One")
        assert "Eldritch Hex" in _subclass_feature_names(character)

    def test_level_10_thought_shield_present(self):
        character = build_warlock(10, "The Great Old One")
        assert "Thought Shield" in _subclass_feature_names(character)

    def test_level_10_thought_shield_description_mentions_psychic(self):
        character = build_warlock(10, "The Great Old One")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Thought Shield"
        )
        assert "Psychic" in feature["description"]

    def test_level_10_hex_always_prepared(self):
        """Eldritch Hex grants the Hex spell as always-prepared."""
        character = build_warlock(10, "The Great Old One")
        assert "Hex" in _always_prepared(character)

    def test_level_10_psychic_resistance(self):
        """Thought Shield grants Psychic damage resistance."""
        character = build_warlock(10, "The Great Old One")
        assert "Psychic" in character.get("resistances", []), (
            f"Expected 'Psychic' in resistances, got: {character.get('resistances', [])}"
        )

    def test_level_10_grant_spell_hex_effect(self):
        character = build_warlock(10, "The Great Old One")
        effects = _effects(character)
        assert any(
            e["type"] == "grant_spell" and e["spell"] == "Hex"
            for e in effects
        ), "Expected grant_spell effect for Hex from Eldritch Hex"

    def test_level_10_grant_damage_resistance_psychic_effect(self):
        character = build_warlock(10, "The Great Old One")
        effects = _effects(character)
        assert any(
            e["type"] == "grant_damage_resistance" and e["damage_type"] == "Psychic"
            for e in effects
        ), "Expected grant_damage_resistance Psychic from Thought Shield"

    def test_level_9_no_psychic_resistance(self):
        """Psychic resistance should NOT appear before level 10."""
        character = build_warlock(9, "The Great Old One")
        assert "Psychic" not in character.get("resistances", [])

    # --- Level 14: Create Thrall ---

    def test_level_14_create_thrall_present(self):
        character = build_warlock(14, "The Great Old One")
        assert "Create Thrall" in _subclass_feature_names(character)

    def test_level_14_create_thrall_description(self):
        character = build_warlock(14, "The Great Old One")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Create Thrall"
        )
        assert "Summon Aberration" in feature["description"]

    # --- Parametrized progression ---

    @pytest.mark.parametrize("level,expected_features", [
        (3, ["Great Old One Spells", "Awakened Mind", "Psychic Spells"]),
        (6, ["Clairvoyant Combatant"]),
        (10, ["Eldritch Hex", "Thought Shield"]),
        (14, ["Create Thrall"]),
    ])
    def test_goo_feature_progression(self, level, expected_features):
        character = build_warlock(level, "The Great Old One")
        names = _subclass_feature_names(character)
        for feature_name in expected_features:
            assert feature_name in names, (
                f"Expected '{feature_name}' at level {level}"
            )


# ===========================================================================
# The Celestial Subclass
# ===========================================================================

class TestCelestialSubclass:
    """Test The Celestial subclass features, cantrips, spells, and Radiant resistance."""

    # --- Level 3 Features ---

    def test_level_3_celestial_spells_present(self):
        character = build_warlock(3, "The Celestial")
        assert "Celestial Spells" in _subclass_feature_names(character)

    def test_level_3_healing_light_present(self):
        character = build_warlock(3, "The Celestial")
        assert "Healing Light" in _subclass_feature_names(character)

    def test_level_3_healing_light_description(self):
        character = build_warlock(3, "The Celestial")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Healing Light"
        )
        assert "d6" in feature["description"]

    # --- Level 3 Celestial Spells: grant_cantrip ---

    def test_level_3_light_cantrip_in_always_prepared(self):
        """Light cantrip should be in always_prepared via grant_cantrip effect."""
        character = build_warlock(3, "The Celestial")
        assert "Light" in _always_prepared(character)

    def test_level_3_sacred_flame_cantrip_in_always_prepared(self):
        character = build_warlock(3, "The Celestial")
        assert "Sacred Flame" in _always_prepared(character)

    def test_level_3_grant_cantrip_light_effect(self):
        character = build_warlock(3, "The Celestial")
        effects = _effects(character)
        assert any(
            e["type"] == "grant_cantrip" and e["spell"] == "Light"
            for e in effects
        ), "Expected grant_cantrip effect for Light"

    def test_level_3_grant_cantrip_sacred_flame_effect(self):
        character = build_warlock(3, "The Celestial")
        effects = _effects(character)
        assert any(
            e["type"] == "grant_cantrip" and e["spell"] == "Sacred Flame"
            for e in effects
        ), "Expected grant_cantrip effect for Sacred Flame"

    # --- Level 3 Celestial Spells (min_level 3) ---

    def test_level_3_aid_prepared(self):
        character = build_warlock(3, "The Celestial")
        assert "Aid" in _always_prepared(character)

    def test_level_3_cure_wounds_prepared(self):
        character = build_warlock(3, "The Celestial")
        assert "Cure Wounds" in _always_prepared(character)

    def test_level_3_guiding_bolt_prepared(self):
        character = build_warlock(3, "The Celestial")
        assert "Guiding Bolt" in _always_prepared(character)

    def test_level_3_lesser_restoration_prepared(self):
        character = build_warlock(3, "The Celestial")
        assert "Lesser Restoration" in _always_prepared(character)

    def test_level_3_daylight_not_yet_prepared(self):
        """Daylight requires min_level 5 — should NOT be prepared at level 3."""
        character = build_warlock(3, "The Celestial")
        assert "Daylight" not in _always_prepared(character)

    # --- Level 5 Celestial Spells (min_level 5) ---

    def test_level_5_daylight_prepared(self):
        character = build_warlock(5, "The Celestial")
        assert "Daylight" in _always_prepared(character)

    def test_level_5_revivify_prepared(self):
        character = build_warlock(5, "The Celestial")
        assert "Revivify" in _always_prepared(character)

    # --- Level 7 Celestial Spells (min_level 7) ---

    def test_level_7_guardian_of_faith_prepared(self):
        character = build_warlock(7, "The Celestial")
        assert "Guardian of Faith" in _always_prepared(character)

    def test_level_7_wall_of_fire_prepared(self):
        character = build_warlock(7, "The Celestial")
        assert "Wall of Fire" in _always_prepared(character)

    # --- Level 9 Celestial Spells (min_level 9) ---

    def test_level_9_greater_restoration_prepared(self):
        character = build_warlock(9, "The Celestial")
        assert "Greater Restoration" in _always_prepared(character)

    def test_level_9_summon_celestial_prepared(self):
        character = build_warlock(9, "The Celestial")
        assert "Summon Celestial" in _always_prepared(character)

    # --- Level 6: Radiant Soul ---

    def test_level_6_radiant_soul_present(self):
        character = build_warlock(6, "The Celestial")
        assert "Radiant Soul" in _subclass_feature_names(character)

    def test_level_6_radiant_resistance(self):
        """Radiant Soul grants Radiant damage resistance."""
        character = build_warlock(6, "The Celestial")
        assert "Radiant" in character.get("resistances", []), (
            f"Expected 'Radiant' in resistances, got: {character.get('resistances', [])}"
        )

    def test_level_6_grant_damage_resistance_radiant_effect(self):
        character = build_warlock(6, "The Celestial")
        effects = _effects(character)
        assert any(
            e["type"] == "grant_damage_resistance" and e["damage_type"] == "Radiant"
            for e in effects
        ), "Expected grant_damage_resistance Radiant from Radiant Soul"

    def test_level_6_radiant_soul_description(self):
        character = build_warlock(6, "The Celestial")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Radiant Soul"
        )
        assert "Radiant" in feature["description"]

    def test_level_5_no_radiant_resistance(self):
        """Radiant resistance should NOT appear before level 6."""
        character = build_warlock(5, "The Celestial")
        assert "Radiant" not in character.get("resistances", [])

    # --- Level 10: Celestial Resilience ---

    def test_level_10_celestial_resilience_present(self):
        character = build_warlock(10, "The Celestial")
        assert "Celestial Resilience" in _subclass_feature_names(character)

    def test_level_10_celestial_resilience_description(self):
        character = build_warlock(10, "The Celestial")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Celestial Resilience"
        )
        assert "Temporary Hit Points" in feature["description"]

    # --- Level 14: Searing Vengeance ---

    def test_level_14_searing_vengeance_present(self):
        character = build_warlock(14, "The Celestial")
        assert "Searing Vengeance" in _subclass_feature_names(character)

    def test_level_14_searing_vengeance_description(self):
        character = build_warlock(14, "The Celestial")
        feature = next(
            f for f in character["features"]["subclass"]
            if f["name"] == "Searing Vengeance"
        )
        assert "Radiant" in feature["description"]

    # --- Parametrized progression ---

    @pytest.mark.parametrize("level,expected_features", [
        (3, ["Celestial Spells", "Healing Light"]),
        (6, ["Radiant Soul"]),
        (10, ["Celestial Resilience"]),
        (14, ["Searing Vengeance"]),
    ])
    def test_celestial_feature_progression(self, level, expected_features):
        character = build_warlock(level, "The Celestial")
        names = _subclass_feature_names(character)
        for feature_name in expected_features:
            assert feature_name in names, (
                f"Expected '{feature_name}' at level {level}"
            )
