"""Tests for Barbarian class features and effects (D&D 2024)."""

import pytest
from modules.character_builder import CharacterBuilder


# ==================== Helpers & Fixtures ====================


def _build_barbarian(level=1, subclass=None):
    """Helper to build a Barbarian character at a given level."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Barbarian", level)
    if subclass and level >= 3:
        builder.set_subclass(subclass)
    return builder


def _build_full_barbarian(level=5, subclass=None, ability_scores=None,
                          background_bonuses=None):
    """Helper to build a full Barbarian character via apply_choices + to_character."""
    builder = CharacterBuilder()
    choices = {
        "character_name": "Test Barbarian",
        "level": level,
        "species": "Human",
        "class": "Barbarian",
        "background": "Soldier",
        "ability_scores": ability_scores or {
            "Strength": 16, "Dexterity": 14, "Constitution": 15,
            "Intelligence": 8, "Wisdom": 10, "Charisma": 12
        },
        "background_bonuses": background_bonuses or {
            "Strength": 2, "Constitution": 1
        },
    }
    if subclass and level >= 3:
        choices["subclass"] = subclass
    builder.apply_choices(choices)
    return builder


# ==================== Base Class Tests ====================


class TestBarbarianBasicSetup:

    def test_barbarian_class_setup(self):
        builder = _build_barbarian(level=1)
        data = builder.character_data
        assert data["class"] == "Barbarian"
        assert data["level"] == 1

        # Saving throws
        saves = data["proficiencies"]["saving_throws"]
        assert "Strength" in saves
        assert "Constitution" in saves

        # Weapons
        weapons = data["proficiencies"]["weapons"]
        assert "Simple weapons" in weapons
        assert "Martial weapons" in weapons

        # Armor
        armor = data["proficiencies"]["armor"]
        assert "Light armor" in armor
        assert "Medium armor" in armor
        assert "Shields" in armor

    def test_barbarian_features_level_1(self):
        builder = _build_barbarian(level=1)
        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Rage" in names
        assert "Unarmored Defense" in names
        assert "Weapon Mastery" in names

    def test_barbarian_features_level_5(self):
        builder = _build_barbarian(level=5)
        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Extra Attack" in names
        assert "Fast Movement" in names
        assert "Danger Sense" in names
        assert "Reckless Attack" in names

    def test_barbarian_features_level_7(self):
        builder = _build_barbarian(level=7)
        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Feral Instinct" in names
        assert "Instinctive Pounce" in names

    def test_barbarian_features_level_9(self):
        builder = _build_barbarian(level=9)
        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Brutal Strike" in names

    def test_barbarian_features_level_15(self):
        builder = _build_barbarian(level=15)
        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Relentless Rage" in names
        assert "Persistent Rage" in names


# ==================== Unarmored Defense ====================


class TestBarbarianUnarmoredDefense:

    def test_unarmored_defense_ac_option(self):
        """Unarmored Defense: AC = 10 + DEX + CON.

        STR 16+2=18, DEX 14 → +2, CON 15+1=16 → +3.
        Expected: 10 + 2 + 3 = 15.
        """
        builder = _build_full_barbarian(level=1)
        character = builder.to_character()
        ac_options = character.get("ac_options", [])

        unarmored = [
            opt for opt in ac_options
            if any("Unarmored Defense" in note for note in opt.get("notes", []))
        ]
        assert len(unarmored) >= 1, (
            f"Expected Unarmored Defense AC option, got: {ac_options}"
        )
        assert unarmored[0]["ac"] == 15, (
            f"Expected AC 15 (10+2+3), got {unarmored[0]['ac']}"
        )

    def test_alternative_ac_effect_applied(self):
        builder = _build_barbarian(level=1)
        effects = builder.applied_effects
        alt_ac = [e for e in effects if e["type"] == "alternative_ac"]
        assert len(alt_ac) == 1
        assert alt_ac[0]["effect"]["modifiers"] == ["dexterity", "constitution"]

    def test_unarmored_defense_uses_constitution_not_wisdom(self):
        """Barbarian uses CON (not WIS like Monk)."""
        builder = _build_barbarian(level=1)
        effects = builder.applied_effects
        alt_ac = [e for e in effects if e["type"] == "alternative_ac"]
        assert alt_ac[0]["effect"]["modifiers"] == ["dexterity", "constitution"]

    def test_unarmored_defense_allows_shield(self):
        """Barbarian Unarmored Defense uses 'no_armor' condition (allows shield)."""
        builder = _build_barbarian(level=1)
        effects = builder.applied_effects
        alt_ac = [e for e in effects if e["type"] == "alternative_ac"]
        assert alt_ac[0]["effect"]["condition"] == "no_armor"


# ==================== Danger Sense ====================


class TestDangerSense:

    def test_danger_sense_save_advantage(self):
        builder = _build_barbarian(level=2)
        save_advs = builder.character_data.get("save_advantages", [])
        dex_advs = [a for a in save_advs if "Dexterity" in a.get("abilities", [])]
        assert len(dex_advs) >= 1, (
            f"Expected Dexterity save advantage, got: {save_advs}"
        )

    def test_no_danger_sense_at_level_1(self):
        builder = _build_barbarian(level=1)
        save_advs = builder.character_data.get("save_advantages", [])
        dex_advs = [a for a in save_advs if "Dexterity" in a.get("abilities", [])]
        assert len(dex_advs) == 0


# ==================== Fast Movement ====================


class TestFastMovement:

    def test_speed_increase_at_level_5(self):
        builder = _build_barbarian(level=5)
        assert builder.character_data["speed"] == 40  # 30 base + 10

    def test_no_speed_increase_at_level_4(self):
        builder = _build_barbarian(level=4)
        assert builder.character_data["speed"] == 30


# ==================== Primal Champion ====================


class TestPrimalChampion:

    def test_ability_bonuses_at_level_20(self):
        builder = _build_barbarian(level=20)
        bonuses = builder.character_data.get("ability_bonuses", [])
        str_bonus = [b for b in bonuses if b["ability"] == "Strength"]
        con_bonus = [b for b in bonuses if b["ability"] == "Constitution"]
        assert len(str_bonus) >= 1
        assert str_bonus[0]["value"] == 4
        assert len(con_bonus) >= 1
        assert con_bonus[0]["value"] == 4

    def test_no_ability_bonuses_at_level_19(self):
        builder = _build_barbarian(level=19)
        bonuses = builder.character_data.get("ability_bonuses", [])
        str_bonus = [b for b in bonuses if b["ability"] == "Strength"]
        con_bonus = [b for b in bonuses if b["ability"] == "Constitution"]
        assert len(str_bonus) == 0
        assert len(con_bonus) == 0


# ==================== Subclass Tests ====================


class TestPathOfTheBerserker:

    def test_frenzy_feature(self):
        builder = _build_barbarian(level=3, subclass="Path of the Berserker")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Frenzy" in names

    def test_mindless_rage_feature(self):
        builder = _build_barbarian(level=6, subclass="Path of the Berserker")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Mindless Rage" in names

    def test_retaliation_feature(self):
        builder = _build_barbarian(level=10, subclass="Path of the Berserker")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Retaliation" in names

    def test_intimidating_presence_feature(self):
        builder = _build_barbarian(level=14, subclass="Path of the Berserker")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Intimidating Presence" in names


class TestPathOfTheWildHeart:

    def test_animal_speaker_spells(self):
        builder = _build_barbarian(level=3, subclass="Path of the Wild Heart")
        spells = builder.character_data["spells"]["always_prepared"]
        assert "Beast Sense" in spells
        assert "Speak with Animals" in spells

    def test_rage_of_the_wilds_feature(self):
        builder = _build_barbarian(level=3, subclass="Path of the Wild Heart")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Rage of the Wilds" in names

    def test_aspect_of_the_wilds_feature(self):
        builder = _build_barbarian(level=6, subclass="Path of the Wild Heart")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Aspect of the Wilds" in names

    def test_nature_speaker_spell(self):
        builder = _build_barbarian(level=10, subclass="Path of the Wild Heart")
        spells = builder.character_data["spells"]["always_prepared"]
        assert "Commune with Nature" in spells

    def test_power_of_the_wilds_feature(self):
        builder = _build_barbarian(level=14, subclass="Path of the Wild Heart")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Power of the Wilds" in names


class TestPathOfTheWorldTree:

    def test_vitality_of_the_tree_feature(self):
        builder = _build_barbarian(level=3, subclass="Path of the World Tree")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Vitality of the Tree" in names

    def test_branches_of_the_tree_feature(self):
        builder = _build_barbarian(level=6, subclass="Path of the World Tree")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Branches of the Tree" in names

    def test_battering_roots_feature(self):
        builder = _build_barbarian(level=10, subclass="Path of the World Tree")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Battering Roots" in names

    def test_travel_along_the_tree_feature(self):
        builder = _build_barbarian(level=14, subclass="Path of the World Tree")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Travel Along the Tree" in names


class TestPathOfTheZealot:

    def test_divine_fury_feature(self):
        builder = _build_barbarian(level=3, subclass="Path of the Zealot")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Divine Fury" in names

    def test_warrior_of_the_gods_feature(self):
        builder = _build_barbarian(level=3, subclass="Path of the Zealot")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Warrior of the Gods" in names

    def test_fanatical_focus_feature(self):
        builder = _build_barbarian(level=6, subclass="Path of the Zealot")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Fanatical Focus" in names

    def test_zealous_presence_feature(self):
        builder = _build_barbarian(level=10, subclass="Path of the Zealot")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Zealous Presence" in names

    def test_rage_of_the_gods_feature(self):
        builder = _build_barbarian(level=14, subclass="Path of the Zealot")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Rage of the Gods" in names


# ==================== Full Character Build Tests ====================


class TestBarbarianFullBuild:

    def test_full_character_build(self):
        builder = CharacterBuilder()
        result = builder.apply_choices({
            "character_name": "Grog",
            "level": 10,
            "species": "Human",
            "class": "Barbarian",
            "subclass": "Path of the Berserker",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 16, "Dexterity": 14, "Constitution": 15,
                "Intelligence": 8, "Wisdom": 10, "Charisma": 12
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        assert result is True

        character = builder.to_character()
        assert character["class"] == "Barbarian"
        assert character["level"] == 10
        assert character["speed"] == 40  # 30 + 10 from Fast Movement

        # Save advantages from Danger Sense
        save_advs = character.get("save_advantages", [])
        dex_advs = [a for a in save_advs if "Dexterity" in a.get("abilities", [])]
        assert len(dex_advs) >= 1

    def test_no_passive_rage_resistances(self):
        """Rage resistance is an activated ability, NOT passive.

        Should NOT grant permanent Bludgeoning/Piercing/Slashing resistance.
        """
        builder = _build_barbarian(level=5, subclass="Path of the Berserker")
        resistances = builder.character_data["resistances"]
        assert len(resistances) == 0, (
            f"Human Barbarian should have no passive resistances, got: {resistances}"
        )


class TestBerserkerFullBuild:
    """Full character build tests for Path of the Berserker at level 6."""

    @pytest.fixture
    def berserker_character(self):
        builder = _build_full_barbarian(level=6, subclass="Path of the Berserker")
        return builder.to_character()

    def test_class_and_level(self, berserker_character):
        assert berserker_character["class"] == "Barbarian"
        assert berserker_character["level"] == 6
        assert berserker_character["subclass"] == "Path of the Berserker"

    def test_all_features_present(self, berserker_character):
        class_features = [f["name"] for f in berserker_character["features"]["class"]]
        subclass_features = [f["name"] for f in berserker_character["features"]["subclass"]]

        # Core class features through level 6
        assert "Rage" in class_features
        assert "Unarmored Defense" in class_features
        assert "Extra Attack" in class_features
        assert "Fast Movement" in class_features
        assert "Danger Sense" in class_features

        # Subclass features
        assert "Frenzy" in subclass_features
        assert "Mindless Rage" in subclass_features

    def test_hp_calculation(self, berserker_character):
        """L6 Barbarian, CON 15+1=16 → +3 modifier.

        HP = 12 (L1 max d12) + 5*7 (avg d12=7, levels 2-6) + 6*3 (CON) = 65.
        """
        hp = berserker_character["combat"]["hit_points"]["maximum"]
        assert hp == 65, f"Expected 65 HP at L6, got {hp}"

    def test_speed(self, berserker_character):
        """L6 Barbarian: 30 base + 10 (L5 Fast Movement) = 40."""
        assert berserker_character["speed"] == 40

    def test_ac_includes_unarmored_defense(self, berserker_character):
        """Unarmored Defense: 10 + DEX(14→+2) + CON(16→+3) = 15."""
        ac_options = berserker_character.get("ac_options", [])
        unarmored = [
            opt for opt in ac_options
            if any("Unarmored Defense" in note for note in opt.get("notes", []))
        ]
        assert len(unarmored) >= 1
        assert unarmored[0]["ac"] == 15

    def test_saving_throw_proficiencies(self, berserker_character):
        saves = berserker_character["proficiencies"]["saving_throws"]
        assert "Strength" in saves
        assert "Constitution" in saves


class TestWildHeartFullBuild:
    """Full character build tests for Path of the Wild Heart at level 10."""

    @pytest.fixture
    def wild_heart_character(self):
        builder = _build_full_barbarian(level=10, subclass="Path of the Wild Heart")
        return builder.to_character()

    def test_class_and_level(self, wild_heart_character):
        assert wild_heart_character["class"] == "Barbarian"
        assert wild_heart_character["level"] == 10
        assert wild_heart_character["subclass"] == "Path of the Wild Heart"

    def test_animal_speaker_spells(self, wild_heart_character):
        spells = wild_heart_character.get("spells", {}).get("always_prepared", {})
        assert "Beast Sense" in spells
        assert "Speak with Animals" in spells

    def test_nature_speaker_spell(self, wild_heart_character):
        spells = wild_heart_character.get("spells", {}).get("always_prepared", {})
        assert "Commune with Nature" in spells

    def test_all_features_present(self, wild_heart_character):
        subclass_features = [
            f["name"] for f in wild_heart_character["features"]["subclass"]
        ]
        assert "Animal Speaker" in subclass_features
        assert "Rage of the Wilds" in subclass_features
        assert "Aspect of the Wilds" in subclass_features
        assert "Nature Speaker" in subclass_features


class TestWorldTreeFullBuild:
    """Full character build tests for Path of the World Tree at level 14."""

    @pytest.fixture
    def world_tree_character(self):
        builder = _build_full_barbarian(level=14, subclass="Path of the World Tree")
        return builder.to_character()

    def test_class_and_level(self, world_tree_character):
        assert world_tree_character["class"] == "Barbarian"
        assert world_tree_character["level"] == 14
        assert world_tree_character["subclass"] == "Path of the World Tree"

    def test_all_features_present(self, world_tree_character):
        subclass_features = [
            f["name"] for f in world_tree_character["features"]["subclass"]
        ]
        assert "Vitality of the Tree" in subclass_features
        assert "Branches of the Tree" in subclass_features
        assert "Battering Roots" in subclass_features
        assert "Travel Along the Tree" in subclass_features


class TestZealotFullBuild:
    """Full character build tests for Path of the Zealot at level 14."""

    @pytest.fixture
    def zealot_character(self):
        builder = _build_full_barbarian(level=14, subclass="Path of the Zealot")
        return builder.to_character()

    def test_class_and_level(self, zealot_character):
        assert zealot_character["class"] == "Barbarian"
        assert zealot_character["level"] == 14
        assert zealot_character["subclass"] == "Path of the Zealot"

    def test_all_features_present(self, zealot_character):
        subclass_features = [
            f["name"] for f in zealot_character["features"]["subclass"]
        ]
        assert "Divine Fury" in subclass_features
        assert "Warrior of the Gods" in subclass_features
        assert "Fanatical Focus" in subclass_features
        assert "Zealous Presence" in subclass_features
        assert "Rage of the Gods" in subclass_features
