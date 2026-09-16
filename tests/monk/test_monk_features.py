"""Tests for Monk class features and effects (D&D 2024)."""

import pytest
from modules.character_builder import CharacterBuilder


# ==================== Helpers & Fixtures ====================


@pytest.fixture
def monk_builder():
    """Fresh CharacterBuilder for Monk tests."""
    return CharacterBuilder()


def _build_monk(level=1, subclass=None):
    """Helper to build a Monk character at a given level."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Monk", level)
    if subclass and level >= 3:
        builder.set_subclass(subclass)
    return builder


def _build_full_monk(level=6, subclass=None, ability_scores=None,
                     background_bonuses=None):
    """Helper to build a full Monk character via apply_choices + to_character."""
    builder = CharacterBuilder()
    choices = {
        "character_name": "Test Monk",
        "level": level,
        "species": "Human",
        "class": "Monk",
        "background": "Acolyte",
        "ability_scores": ability_scores or {
            "Strength": 10, "Dexterity": 16, "Constitution": 14,
            "Intelligence": 8, "Wisdom": 15, "Charisma": 10
        },
        "background_bonuses": background_bonuses or {
            "Dexterity": 2, "Wisdom": 1
        },
    }
    if subclass and level >= 3:
        choices["subclass"] = subclass
    builder.apply_choices(choices)
    return builder


# ==================== Base Class Tests ====================


class TestMonkBasicSetup:

    def test_monk_class_setup(self, monk_builder):
        builder = monk_builder
        builder.set_species("Human")
        builder.set_class("Monk", 1)

        data = builder.character_data
        assert data["class"] == "Monk"
        assert data["level"] == 1

        # Saving throws
        saves = data["proficiencies"]["saving_throws"]
        assert "Strength" in saves
        assert "Dexterity" in saves

        # Weapons — 2024 Monk
        weapons = data["proficiencies"]["weapons"]
        assert "Simple weapons" in weapons
        assert "Martial weapons that have the Light property" in weapons

        # No armor proficiency
        assert data["proficiencies"]["armor"] == []

    def test_monk_features_level_1(self, monk_builder):
        builder = monk_builder
        builder.set_species("Human")
        builder.set_class("Monk", 1)

        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Martial Arts" in names
        assert "Unarmored Defense" in names

    def test_monk_features_level_5(self):
        builder = _build_monk(level=5)
        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Extra Attack" in names
        assert "Stunning Strike" in names
        assert "Deflect Attacks" in names
        assert "Slow Fall" in names


class TestUnarmoredDefense:

    def test_unarmored_defense_ac_option(self):
        """Unarmored Defense: AC = 10 + DEX + WIS.

        DEX 16 + 2 background = 18 → +4, WIS 15 + 1 background = 16 → +3.
        Expected: 10 + 4 + 3 = 17.
        """
        builder = _build_full_monk(level=1)
        character = builder.to_character()
        ac_options = character.get("ac_options", [])

        unarmored_defense = [
            opt for opt in ac_options
            if any("Unarmored Defense" in note for note in opt.get("notes", []))
        ]
        assert len(unarmored_defense) >= 1, (
            f"Expected Unarmored Defense AC option, got: {ac_options}"
        )
        assert unarmored_defense[0]["ac"] == 17, (
            f"Expected AC 17, got {unarmored_defense[0]['ac']}"
        )

    def test_alternative_ac_effect_applied(self):
        builder = _build_monk(level=1)
        effects = builder.applied_effects
        alt_ac_effects = [e for e in effects if e["type"] == "alternative_ac"]
        assert len(alt_ac_effects) == 1
        assert alt_ac_effects[0]["effect"]["modifiers"] == ["dexterity", "wisdom"]


class TestUnarmoredMovement:

    def test_speed_increase_level_2(self):
        builder = _build_monk(level=2)
        assert builder.character_data["speed"] == 40  # 30 base + 10

    def test_speed_increase_level_6(self):
        builder = _build_monk(level=6)
        assert builder.character_data["speed"] == 45  # 30 + 10 + 5

    def test_speed_increase_level_10(self):
        builder = _build_monk(level=10)
        assert builder.character_data["speed"] == 50  # 30 + 10 + 5 + 5

    def test_speed_increase_level_14(self):
        builder = _build_monk(level=14)
        assert builder.character_data["speed"] == 55  # 30 + 10 + 5 + 5 + 5

    def test_speed_increase_level_18(self):
        builder = _build_monk(level=18)
        assert builder.character_data["speed"] == 60  # 30 + 10 + 5 + 5 + 5 + 5

    def test_no_speed_increase_level_1(self):
        builder = _build_monk(level=1)
        assert builder.character_data["speed"] == 30


class TestDisciplinedSurvivor:

    def test_all_save_proficiencies_at_level_14(self):
        builder = _build_monk(level=14)
        saves = builder.character_data["proficiencies"]["saving_throws"]
        for ability in ["Strength", "Dexterity", "Constitution",
                        "Intelligence", "Wisdom", "Charisma"]:
            assert ability in saves, f"Missing save proficiency: {ability}"

    def test_no_extra_saves_before_level_14(self):
        builder = _build_monk(level=13)
        saves = builder.character_data["proficiencies"]["saving_throws"]
        # Should only have Strength and Dexterity from base class
        assert "Constitution" not in saves
        assert "Intelligence" not in saves
        assert "Charisma" not in saves


class TestMartialArtsDie:
    """Tests for Monk Martial Arts die scaling (GitHub Issue: [Monk] Martial Arts die scaling)."""

    @pytest.mark.parametrize("level,expected_die", [
        (1, "1d6"),
        (4, "1d6"),
        (5, "1d8"),
        (10, "1d8"),
        (11, "1d10"),
        (16, "1d10"),
        (17, "1d12"),
        (20, "1d12"),
    ])
    def test_martial_arts_die_by_level(self, level, expected_die):
        """Martial Arts die scales with Monk level: d6→d8→d10→d12."""
        builder = _build_monk(level=level)
        assert builder.character_data.get("martial_arts_die") == expected_die, (
            f"Level {level}: expected {expected_die}, "
            f"got {builder.character_data.get('martial_arts_die')}"
        )

    @pytest.mark.parametrize("level,expected_die", [
        (1, "1d6"),
        (5, "1d8"),
        (11, "1d10"),
        (17, "1d12"),
    ])
    def test_unarmed_strike_uses_martial_arts_die(self, level, expected_die):
        """Unarmed strike damage uses the correct Martial Arts die at each breakpoint."""
        builder = _build_full_monk(level=level, ability_scores={
            "Strength": 10, "Dexterity": 16, "Constitution": 14,
            "Intelligence": 8, "Wisdom": 14, "Charisma": 10,
        }, background_bonuses={"Dexterity": 2, "Wisdom": 1})
        weapon_data = builder.calculate_weapon_attacks()
        unarmed = next(
            (a for a in weapon_data["attacks"] if a["name"] == "Unarmed Strike"), None
        )
        assert unarmed is not None
        assert expected_die in unarmed["damage"], (
            f"Level {level} Monk should use {expected_die}, got {unarmed['damage']}"
        )

    def test_unarmed_strike_uses_dex_modifier(self):
        """Monk Dexterous Attacks: unarmed strike should use DEX if higher than STR."""
        # DEX 18 (+4) > STR 10 (+0)
        builder = _build_full_monk(level=1, ability_scores={
            "Strength": 10, "Dexterity": 16, "Constitution": 14,
            "Intelligence": 8, "Wisdom": 14, "Charisma": 10,
        }, background_bonuses={"Dexterity": 2, "Wisdom": 1})
        weapon_data = builder.calculate_weapon_attacks()
        unarmed = next(
            (a for a in weapon_data["attacks"] if a["name"] == "Unarmed Strike"), None
        )
        assert unarmed is not None
        # DEX 18 = +4 mod, expected "1d6 + 4"
        assert unarmed["damage"] == "1d6 + 4", (
            f"Monk should use DEX (+4) for unarmed, got {unarmed['damage']}"
        )
        assert unarmed["ability"] == "DEX", (
            f"Monk unarmed ability should be DEX, got {unarmed['ability']}"
        )

    def test_unarmed_strike_uses_str_when_higher(self):
        """Monk unarmed strike uses STR if it's higher than DEX."""
        # STR 18 (+4) > DEX 10 (+0)
        builder = _build_full_monk(level=1, ability_scores={
            "Strength": 16, "Dexterity": 10, "Constitution": 14,
            "Intelligence": 8, "Wisdom": 14, "Charisma": 10,
        }, background_bonuses={"Strength": 2, "Wisdom": 1})
        weapon_data = builder.calculate_weapon_attacks()
        unarmed = next(
            (a for a in weapon_data["attacks"] if a["name"] == "Unarmed Strike"), None
        )
        assert unarmed is not None
        # STR 18 = +4 mod, expected "1d6 + 4"
        assert unarmed["damage"] == "1d6 + 4", (
            f"Monk should use STR (+4) for unarmed when higher, got {unarmed['damage']}"
        )
        assert unarmed["ability"] == "STR", (
            f"Monk unarmed ability should be STR when higher, got {unarmed['ability']}"
        )


class TestDexterousAttacksMonkWeapons:
    """Tests for Monk Dexterous Attacks on monk weapons (GitHub Issue:
    [Monk] Monk weapons don't use DEX for attack/damage rolls)."""

    def _build_monk_with_weapon(self, weapon_entry, str_score=8, dex_score=17, level=1):
        """Helper: build a Monk with a given weapon in inventory."""
        builder = _build_full_monk(
            level=level,
            ability_scores={
                "Strength": str_score, "Dexterity": dex_score,
                "Constitution": 14, "Intelligence": 8,
                "Wisdom": 14, "Charisma": 10,
            },
            background_bonuses={"Dexterity": 2, "Wisdom": 1},
        )
        if builder.character_data.get("equipment") is None:
            builder.character_data["equipment"] = {"weapons": [], "armor": [], "items": [], "gold": 0}
        builder.character_data["equipment"].setdefault("weapons", []).append(weapon_entry)
        return builder

    def test_monk_dexterous_attacks_effect_is_set(self):
        """Martial Arts feature should set monk_dexterous_attacks on character data."""
        builder = _build_full_monk(level=1)
        assert builder.character_data.get("monk_dexterous_attacks") is True

    def test_simple_melee_uses_dex_when_higher(self):
        """A Monk wielding a Simple Melee weapon (Spear) should use DEX when DEX > STR."""
        # STR 8 (-1), DEX 19 (+4 after background bonus)
        spear = {
            "name": "Spear",
            "quantity": 1,
            "properties": {
                "category": "Simple Melee",
                "damage": "1d6",
                "damage_type": "Piercing",
                "properties": ["Thrown", "Versatile (1d8)"],
            },
        }
        builder = self._build_monk_with_weapon(spear)
        weapon_data = builder.calculate_weapon_attacks()
        spear_attack = next(
            (a for a in weapon_data["attacks"] if a["name"] == "Spear"), None
        )
        assert spear_attack is not None, "Spear attack not found"
        # STR 8 → mod -1; DEX 17+2=19 → mod +4; expect DEX
        assert "DEX" in spear_attack["ability"], (
            f"Monk Spear should use DEX, got ability '{spear_attack['ability']}'"
        )
        # With DEX +4 the attack bonus must be higher than with STR (-1)
        assert spear_attack["attack_bonus"] > 0, (
            f"Expected positive attack bonus with DEX, got {spear_attack['attack_bonus']}"
        )

    def test_martial_melee_light_uses_dex_when_higher(self):
        """A Monk with a Martial Melee + Light weapon (shortsword) uses DEX when higher."""
        shortsword = {
            "name": "Shortsword",
            "quantity": 1,
            "properties": {
                "category": "Martial Melee",
                "damage": "1d6",
                "damage_type": "Piercing",
                "properties": ["Finesse", "Light"],
            },
        }
        builder = self._build_monk_with_weapon(shortsword)
        weapon_data = builder.calculate_weapon_attacks()
        sw_attack = next(
            (a for a in weapon_data["attacks"] if a["name"] == "Shortsword"), None
        )
        assert sw_attack is not None, "Shortsword attack not found"
        assert "DEX" in sw_attack["ability"], (
            f"Monk Shortsword should use DEX, got ability '{sw_attack['ability']}'"
        )

    def test_martial_melee_no_light_uses_str(self):
        """A Monk with a Martial Melee weapon WITHOUT Light (e.g., Longsword) uses STR."""
        longsword = {
            "name": "Longsword",
            "quantity": 1,
            "properties": {
                "category": "Martial Melee",
                "damage": "1d8",
                "damage_type": "Slashing",
                "properties": ["Versatile (1d10)"],
            },
        }
        builder = self._build_monk_with_weapon(longsword)
        weapon_data = builder.calculate_weapon_attacks()
        ls_attack = next(
            (a for a in weapon_data["attacks"] if a["name"] == "Longsword"), None
        )
        assert ls_attack is not None, "Longsword attack not found"
        assert ls_attack["ability"] == "STR", (
            f"Non-Light Martial weapon should use STR, got '{ls_attack['ability']}'"
        )

    def test_monk_weapon_uses_str_when_str_higher(self):
        """Monk with STR > DEX: monk weapon should use STR (max still picks STR)."""
        spear = {
            "name": "Spear",
            "quantity": 1,
            "properties": {
                "category": "Simple Melee",
                "damage": "1d6",
                "damage_type": "Piercing",
                "properties": ["Thrown", "Versatile (1d8)"],
            },
        }
        # STR 18 (+4), DEX 10 (+0) after background bonus
        builder = _build_full_monk(
            level=1,
            ability_scores={
                "Strength": 16, "Dexterity": 10, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 14, "Charisma": 10,
            },
            background_bonuses={"Strength": 2, "Wisdom": 1},
        )
        if builder.character_data.get("equipment") is None:
            builder.character_data["equipment"] = {"weapons": [], "armor": [], "items": [], "gold": 0}
        builder.character_data["equipment"].setdefault("weapons", []).append(spear)
        weapon_data = builder.calculate_weapon_attacks()
        spear_attack = next(
            (a for a in weapon_data["attacks"] if a["name"] == "Spear"), None
        )
        assert spear_attack is not None, "Spear attack not found"
        assert "STR" in spear_attack["ability"], (
            f"Monk Spear with higher STR should use STR, got '{spear_attack['ability']}'"
        )

    def test_non_monk_does_not_get_dexterous_attacks(self):
        """A non-Monk character should NOT have monk_dexterous_attacks set."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Fighter",
            "level": 1,
            "species": "Human",
            "class": "Fighter",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 8, "Dexterity": 17, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 10, "Charisma": 10,
            },
            "background_bonuses": {"Dexterity": 2, "Strength": 1},
        })
        assert not builder.character_data.get("monk_dexterous_attacks"), (
            "Non-Monk should not have monk_dexterous_attacks"
        )


class TestSuperiorDefense:

    def test_superior_defense_feature_exists_at_level_18(self):
        """Superior Defense should exist as a class feature at level 18."""
        builder = _build_monk(level=18)
        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Superior Defense" in names

    def test_no_passive_resistances_at_level_18(self):
        """Superior Defense is an activated ability (3 FP, 1 minute), NOT passive.

        It should NOT grant permanent resistances.
        """
        builder = _build_monk(level=18)
        resistances = builder.character_data["resistances"]
        assert len(resistances) == 0, (
            f"Human Monk should have no passive resistances, got: {resistances}"
        )

    def test_no_resistances_before_level_18(self):
        builder = _build_monk(level=17)
        # Human has no innate resistances
        resistances = builder.character_data["resistances"]
        assert len(resistances) == 0


class TestBodyAndMind:

    def test_ability_bonuses_at_level_20(self):
        builder = _build_monk(level=20)
        bonuses = builder.character_data.get("ability_bonuses", [])
        dex_bonus = [b for b in bonuses if b["ability"] == "Dexterity"]
        wis_bonus = [b for b in bonuses if b["ability"] == "Wisdom"]
        assert len(dex_bonus) >= 1
        assert dex_bonus[0]["value"] == 4
        assert len(wis_bonus) >= 1
        assert wis_bonus[0]["value"] == 4


# ==================== Subclass Tests ====================


class TestWarriorOfMercy:

    def test_implements_of_mercy_proficiencies(self):
        builder = _build_monk(level=3, subclass="Warrior of Mercy")
        skills = builder.character_data["proficiencies"]["skills"]
        assert "Insight" in skills
        assert "Medicine" in skills

    def test_features_present(self):
        builder = _build_monk(level=3, subclass="Warrior of Mercy")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Hand of Healing" in names
        assert "Hand of Harm" in names


class TestWarriorOfShadow:

    def test_shadow_arts_darkvision(self):
        builder = _build_monk(level=3, subclass="Warrior of Shadow")
        assert builder.character_data["darkvision"] >= 60

    def test_shadow_arts_cantrip(self):
        builder = _build_monk(level=3, subclass="Warrior of Shadow")
        spells = builder.character_data["spells"]["always_prepared"]
        assert "Minor Illusion" in spells

    def test_features_present(self):
        builder = _build_monk(level=6, subclass="Warrior of Shadow")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Shadow Step" in names


class TestWarriorOfTheElements:

    def test_manipulate_elements_cantrip(self):
        builder = _build_monk(level=3, subclass="Warrior of the Elements")
        spells = builder.character_data["spells"]["always_prepared"]
        assert "Elementalism" in spells

    def test_features_present(self):
        builder = _build_monk(level=3, subclass="Warrior of the Elements")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Elemental Attunement" in names


class TestWarriorOfTheOpenHand:

    def test_open_hand_technique(self):
        builder = _build_monk(level=3, subclass="Warrior of the Open Hand")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Open Hand Technique" in names

    def test_high_level_features(self):
        builder = _build_monk(level=17, subclass="Warrior of the Open Hand")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Quivering Palm" in names
        assert "Fleet Step" in names
        assert "Wholeness of Body" in names


# ==================== Full Character Build Tests ====================


class TestMonkFullBuild:

    def test_full_character_build(self):
        builder = CharacterBuilder()
        result = builder.apply_choices({
            "character_name": "Shadow Monk",
            "level": 10,
            "species": "Human",
            "class": "Monk",
            "subclass": "Warrior of Shadow",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 10, "Dexterity": 16, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 15, "Charisma": 12
            },
            "background_bonuses": {"Dexterity": 2, "Wisdom": 1},
        })
        assert result is True

        character = builder.to_character()
        assert character["class"] == "Monk"
        assert character["level"] == 10
        assert character["speed"] >= 50  # 30 + 10(L2) + 5(L6) + 5(L10)

        # Should have darkvision from Shadow Arts
        assert character.get("darkvision", 0) >= 60

        # Should have Minor Illusion
        spells = character.get("spells", {}).get("always_prepared", {})
        assert "Minor Illusion" in spells


class TestWarriorOfMercyFullBuild:
    """Full character build tests for Warrior of Mercy at level 6."""

    @pytest.fixture
    def mercy_character(self):
        builder = _build_full_monk(level=6, subclass="Warrior of Mercy")
        return builder.to_character()

    def test_class_and_level(self, mercy_character):
        assert mercy_character["class"] == "Monk"
        assert mercy_character["level"] == 6
        assert mercy_character["subclass"] == "Warrior of Mercy"

    def test_skill_proficiencies(self, mercy_character):
        skills = mercy_character["proficiencies"]["skills"]
        assert "Insight" in skills, "Implements of Mercy should grant Insight"
        assert "Medicine" in skills, "Implements of Mercy should grant Medicine"

    def test_all_features_present(self, mercy_character):
        class_features = [f["name"] for f in mercy_character["features"]["class"]]
        subclass_features = [f["name"] for f in mercy_character["features"]["subclass"]]

        # Core class features through level 6
        assert "Martial Arts" in class_features
        assert "Unarmored Defense" in class_features
        assert "Extra Attack" in class_features

        # Subclass features
        assert "Hand of Healing" in subclass_features
        assert "Hand of Harm" in subclass_features
        assert "Physician's Touch" in subclass_features

    def test_hp_calculation(self, mercy_character):
        """L6 Monk, CON 14 → +2 modifier.

        HP = 8 (L1 max d8) + 5*5 (avg d8=5, levels 2-6) + 6*2 (CON) = 45.
        """
        hp = mercy_character["combat"]["hit_points"]["maximum"]
        assert hp == 45, f"Expected 45 HP at L6, got {hp}"

    def test_speed(self, mercy_character):
        """L6 Monk: 30 base + 10 (L2) + 5 (L6) = 45."""
        assert mercy_character["speed"] == 45

    def test_ac_includes_unarmored_defense(self, mercy_character):
        """Unarmored Defense: 10 + DEX(18→+4) + WIS(16→+3) = 17."""
        ac_options = mercy_character.get("ac_options", [])
        unarmored_defense = [
            opt for opt in ac_options
            if any("Unarmored Defense" in note for note in opt.get("notes", []))
        ]
        assert len(unarmored_defense) >= 1
        assert unarmored_defense[0]["ac"] == 17


class TestWarriorOfShadowFullBuild:
    """Full character build tests for Warrior of Shadow at level 6."""

    @pytest.fixture
    def shadow_character(self):
        builder = _build_full_monk(level=6, subclass="Warrior of Shadow")
        return builder.to_character()

    def test_class_and_level(self, shadow_character):
        assert shadow_character["class"] == "Monk"
        assert shadow_character["level"] == 6
        assert shadow_character["subclass"] == "Warrior of Shadow"

    def test_darkvision(self, shadow_character):
        assert shadow_character.get("darkvision", 0) >= 60

    def test_minor_illusion_cantrip(self, shadow_character):
        spells = shadow_character.get("spells", {}).get("always_prepared", {})
        assert "Minor Illusion" in spells

    def test_shadow_step_feature(self, shadow_character):
        subclass_features = [
            f["name"] for f in shadow_character["features"]["subclass"]
        ]
        assert "Shadow Step" in subclass_features

    def test_all_features_present(self, shadow_character):
        class_features = [f["name"] for f in shadow_character["features"]["class"]]
        subclass_features = [
            f["name"] for f in shadow_character["features"]["subclass"]
        ]

        assert "Martial Arts" in class_features
        assert "Unarmored Defense" in class_features
        assert "Extra Attack" in class_features
        assert "Shadow Arts" in subclass_features
        assert "Shadow Step" in subclass_features

    def test_hp_calculation(self, shadow_character):
        """L6, CON 14 → +2. HP = 8 + 5*5 + 6*2 = 45."""
        hp = shadow_character["combat"]["hit_points"]["maximum"]
        assert hp == 45, f"Expected 45 HP at L6, got {hp}"

    def test_speed(self, shadow_character):
        assert shadow_character["speed"] == 45

    def test_ac_includes_unarmored_defense(self, shadow_character):
        ac_options = shadow_character.get("ac_options", [])
        unarmored_defense = [
            opt for opt in ac_options
            if any("Unarmored Defense" in note for note in opt.get("notes", []))
        ]
        assert len(unarmored_defense) >= 1
        assert unarmored_defense[0]["ac"] == 17


class TestWarriorOfTheElementsFullBuild:
    """Full character build tests for Warrior of the Elements at level 6."""

    @pytest.fixture
    def elements_character(self):
        builder = _build_full_monk(level=6, subclass="Warrior of the Elements")
        return builder.to_character()

    def test_class_and_level(self, elements_character):
        assert elements_character["class"] == "Monk"
        assert elements_character["level"] == 6
        assert elements_character["subclass"] == "Warrior of the Elements"

    def test_elementalism_cantrip(self, elements_character):
        spells = elements_character.get("spells", {}).get("always_prepared", {})
        assert "Elementalism" in spells

    def test_all_features_present(self, elements_character):
        class_features = [f["name"] for f in elements_character["features"]["class"]]
        subclass_features = [
            f["name"] for f in elements_character["features"]["subclass"]
        ]

        assert "Martial Arts" in class_features
        assert "Unarmored Defense" in class_features
        assert "Extra Attack" in class_features
        assert "Elemental Attunement" in subclass_features
        assert "Elemental Burst" in subclass_features

    def test_hp_calculation(self, elements_character):
        hp = elements_character["combat"]["hit_points"]["maximum"]
        assert hp == 45, f"Expected 45 HP at L6, got {hp}"

    def test_speed(self, elements_character):
        assert elements_character["speed"] == 45

    def test_ac_includes_unarmored_defense(self, elements_character):
        ac_options = elements_character.get("ac_options", [])
        unarmored_defense = [
            opt for opt in ac_options
            if any("Unarmored Defense" in note for note in opt.get("notes", []))
        ]
        assert len(unarmored_defense) >= 1
        assert unarmored_defense[0]["ac"] == 17


class TestWarriorOfTheOpenHandFullBuild:
    """Full character build tests for Warrior of the Open Hand at level 6."""

    @pytest.fixture
    def open_hand_character(self):
        builder = _build_full_monk(level=6, subclass="Warrior of the Open Hand")
        return builder.to_character()

    def test_class_and_level(self, open_hand_character):
        assert open_hand_character["class"] == "Monk"
        assert open_hand_character["level"] == 6
        assert open_hand_character["subclass"] == "Warrior of the Open Hand"

    def test_all_features_present(self, open_hand_character):
        class_features = [f["name"] for f in open_hand_character["features"]["class"]]
        subclass_features = [
            f["name"] for f in open_hand_character["features"]["subclass"]
        ]

        assert "Martial Arts" in class_features
        assert "Unarmored Defense" in class_features
        assert "Extra Attack" in class_features
        assert "Open Hand Technique" in subclass_features
        assert "Wholeness of Body" in subclass_features

    def test_hp_calculation(self, open_hand_character):
        hp = open_hand_character["combat"]["hit_points"]["maximum"]
        assert hp == 45, f"Expected 45 HP at L6, got {hp}"

    def test_speed(self, open_hand_character):
        assert open_hand_character["speed"] == 45

    def test_ac_includes_unarmored_defense(self, open_hand_character):
        ac_options = open_hand_character.get("ac_options", [])
        unarmored_defense = [
            opt for opt in ac_options
            if any("Unarmored Defense" in note for note in opt.get("notes", []))
        ]
        assert len(unarmored_defense) >= 1
        assert unarmored_defense[0]["ac"] == 17


class TestMonkToolProficiencyChoice:
    """Regression tests for GitHub Issue: Monk tool proficiency choice not offered at level 1."""

    def test_monk_tool_options_available_in_class_data(self):
        """Monk class data should expose tool_proficiencies_count and tool_options."""
        builder = CharacterBuilder()
        class_data = builder._load_class_data("Monk")
        assert class_data is not None
        assert "tool_proficiencies_count" in class_data
        assert class_data["tool_proficiencies_count"] == 1
        assert "tool_options" in class_data
        assert len(class_data["tool_options"]) > 0
        # Should include at least one artisan's tool and one musical instrument
        artisan = [t for t in class_data["tool_options"] if "Tools" in t or "Supplies" in t or "Utensils" in t]
        musical = [t for t in class_data["tool_options"] if t in ["Bagpipes", "Drum", "Dulcimer", "Flute", "Horn", "Lute", "Lyre", "Pan Flute", "Shawm", "Viol"]]
        assert len(artisan) > 0, "Monk tool options should include artisan's tools"
        assert len(musical) > 0, "Monk tool options should include musical instruments"

    def test_monk_tool_choice_appears_in_class_features(self):
        """get_class_features_and_choices() should include a tool proficiency choice for Monk."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Monk", 1)
        feature_data = builder.get_class_features_and_choices()
        choices = feature_data["choices"]
        tool_choices = [c for c in choices if c.get("type") == "tools"]
        assert len(tool_choices) == 1
        tc = tool_choices[0]
        assert tc["count"] == 1
        assert "Flute" in tc["options"]
        assert "Carpenter's Tools" in tc["options"]

    def test_apply_tool_choice_adds_to_proficiencies(self):
        """Applying tool_choices should add the tool to proficiencies['tools']."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Monk", 1)
        builder.apply_choice("tool_choices", ["Flute"])
        character = builder.to_character()
        assert "Flute" in character["proficiencies"]["tools"]

    def test_apply_tool_choice_carpenters_tools(self):
        """Choosing Carpenter's Tools should add them to proficiencies['tools']."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Monk", 1)
        builder.apply_choice("tool_choices", ["Carpenter's Tools"])
        character = builder.to_character()
        assert "Carpenter's Tools" in character["proficiencies"]["tools"]

    def test_no_duplicate_tool_proficiency(self):
        """Applying the same tool choice twice should not duplicate proficiencies."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Monk", 1)
        builder.apply_choice("tool_choices", ["Lute"])
        builder.apply_choice("tool_choices", ["Lute"])
        character = builder.to_character()
        assert character["proficiencies"]["tools"].count("Lute") == 1

    def test_tool_choice_via_apply_choices(self):
        """apply_choices with tool_choices key should grant the proficiency."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Monk",
            "level": 1,
            "species": "Human",
            "class": "Monk",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 10, "Dexterity": 16, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 15, "Charisma": 10,
            },
            "background_bonuses": {"Dexterity": 2, "Wisdom": 1},
            "tool_choices": ["Smith's Tools"],
        })
        character = builder.to_character()
        assert "Smith's Tools" in character["proficiencies"]["tools"]

    def test_tool_proficiency_source_tracked(self):
        """The source of the monk tool proficiency should be tracked as the class."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Monk", 1)
        builder.apply_choice("tool_choices", ["Drum"])
        sources = builder.character_data["proficiency_sources"]["tools"]
        assert sources.get("Drum") == "Monk"
