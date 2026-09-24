"""Tests for Paladin class features and subclass effects (D&D 2024)."""

import pytest
from modules.character_builder import CharacterBuilder


# ==================== Helpers & Fixtures ====================


def _build_paladin(level=1, subclass=None):
    """Helper to build a Paladin character at a given level."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Paladin", level)
    if subclass and level >= 3:
        builder.set_subclass(subclass)
    return builder


def _build_full_paladin(level=1, subclass=None, ability_scores=None, background_bonuses=None, choices_extra=None):
    """Helper to build a full Paladin character via apply_choices."""
    builder = CharacterBuilder()
    choices = {
        "character_name": "Test Paladin",
        "level": level,
        "species": "Human",
        "class": "Paladin",
        "background": "Acolyte",
        "ability_scores": ability_scores or {
            "Strength": 16, "Dexterity": 10, "Constitution": 14,
            "Intelligence": 8, "Wisdom": 12, "Charisma": 16
        },
        "background_bonuses": background_bonuses if background_bonuses is not None else {
            "Strength": 2, "Charisma": 1
        },
    }
    if subclass and level >= 3:
        choices["subclass"] = subclass
    if choices_extra:
        choices.update(choices_extra)
    builder.apply_choices(choices)
    return builder


@pytest.fixture
def paladin_choices():
    """Base Paladin choices template."""
    return {
        "character_name": "Test Paladin",
        "level": 3,
        "species": "Human",
        "class": "Paladin",
        "subclass": "Oath of Devotion",
        "background": "Acolyte",
        "ability_scores": {
            "Strength": 16, "Dexterity": 10, "Constitution": 14,
            "Intelligence": 8, "Wisdom": 12, "Charisma": 15
        },
        "background_bonuses": {"Strength": 2, "Charisma": 1},
    }


# ==================== Base Class Feature Tests ====================


class TestPaladinClassFeatures:

    def test_paladin_class_features_level_1(self):
        """Lay On Hands, Spellcasting, and Weapon Mastery appear at level 1."""
        builder = _build_paladin(level=1)
        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Lay On Hands" in names
        assert "Spellcasting" in names
        assert "Weapon Mastery" in names

    def test_paladin_fighting_style_level_2(self):
        """Fighting Style feature appears at level 2."""
        builder = _build_paladin(level=2)
        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Fighting Style" in names

    def test_paladin_smite_always_prepared(self):
        """At level 2+, Divine Smite should be in always_prepared spells."""
        builder = _build_paladin(level=2)
        always_prepared = builder.character_data["spells"]["always_prepared"]
        assert "Divine Smite" in always_prepared

    def test_paladin_channel_divinity_level_3(self):
        """Channel Divinity feature appears at level 3."""
        builder = _build_paladin(level=3, subclass="Oath of Devotion")
        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Channel Divinity" in names

    def test_paladin_extra_attack_level_5(self):
        """Extra Attack feature appears at level 5."""
        builder = _build_paladin(level=5, subclass="Oath of Devotion")
        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Extra Attack" in names

    def test_paladin_faithful_steed_always_prepared(self):
        """At level 5+, Find Steed should be in always_prepared."""
        builder = _build_paladin(level=5, subclass="Oath of Devotion")
        always_prepared = builder.character_data["spells"]["always_prepared"]
        assert "Find Steed" in always_prepared

    def test_paladin_aura_of_protection_level_6(self):
        """Aura of Protection feature appears at level 6."""
        builder = _build_paladin(level=6, subclass="Oath of Devotion")
        features = builder.character_data["features"]["class"]
        names = [f["name"] for f in features]
        assert "Aura of Protection" in names


# ==================== Oath of Devotion Tests ====================


class TestOathOfDevotion:

    def test_devotion_oath_spells_level_3(self):
        """Protection from Evil and Good, Shield of Faith in always_prepared at level 3."""
        builder = _build_paladin(level=3, subclass="Oath of Devotion")
        always_prepared = builder.character_data["spells"]["always_prepared"]
        assert "Protection from Evil and Good" in always_prepared
        assert "Shield of Faith" in always_prepared

    def test_devotion_oath_spells_level_5(self):
        """Aid, Zone of Truth also in always_prepared at level 5+."""
        builder = _build_paladin(level=5, subclass="Oath of Devotion")
        always_prepared = builder.character_data["spells"]["always_prepared"]
        assert "Aid" in always_prepared
        assert "Zone of Truth" in always_prepared
        # Level 3 spells should still be present
        assert "Protection from Evil and Good" in always_prepared
        assert "Shield of Faith" in always_prepared

    def test_devotion_sacred_weapon_feature(self):
        """Sacred Weapon feature present at level 3."""
        builder = _build_paladin(level=3, subclass="Oath of Devotion")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Sacred Weapon" in names

    def test_devotion_aura_charmed_immunity(self):
        """At level 7+, 'Charmed' in condition_immunities."""
        builder = _build_paladin(level=7, subclass="Oath of Devotion")
        condition_immunities = builder.character_data.get("condition_immunities", [])
        assert "Charmed" in condition_immunities

    def test_devotion_smite_of_protection(self):
        """At level 15, Smite of Protection feature present."""
        builder = _build_paladin(level=15, subclass="Oath of Devotion")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Smite of Protection" in names


# ==================== Oath of Glory Tests ====================


class TestOathOfGlory:

    def test_glory_oath_spells_level_3(self):
        """Guiding Bolt, Heroism in always_prepared at level 3."""
        builder = _build_paladin(level=3, subclass="Oath of Glory")
        always_prepared = builder.character_data["spells"]["always_prepared"]
        assert "Guiding Bolt" in always_prepared
        assert "Heroism" in always_prepared

    def test_glory_speed_increase(self):
        """At level 7+, speed is 40 (30 base + 10 from Aura of Alacrity)."""
        builder = _build_paladin(level=7, subclass="Oath of Glory")
        assert builder.character_data["speed"] == 40

    def test_glory_peerless_athlete_feature(self):
        """Peerless Athlete feature at level 3."""
        builder = _build_paladin(level=3, subclass="Oath of Glory")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Peerless Athlete" in names

    def test_glory_oath_spells_level_17(self):
        """Legend Lore, Yolande's Regal Presence (NOT Commune/Flame Strike) at level 17."""
        builder = _build_paladin(level=17, subclass="Oath of Glory")
        always_prepared = builder.character_data["spells"]["always_prepared"]
        assert "Legend Lore" in always_prepared
        assert "Yolande's Regal Presence" in always_prepared
        # These are Devotion spells, not Glory
        assert "Commune" not in always_prepared
        assert "Flame Strike" not in always_prepared


# ==================== Oath of the Ancients Tests ====================


class TestOathOfTheAncients:

    def test_ancients_oath_spells_level_3(self):
        """Ensnaring Strike, Speak with Animals in always_prepared at level 3."""
        builder = _build_paladin(level=3, subclass="Oath of the Ancients")
        always_prepared = builder.character_data["spells"]["always_prepared"]
        assert "Ensnaring Strike" in always_prepared
        assert "Speak with Animals" in always_prepared

    def test_ancients_aura_of_warding_resistances(self):
        """At level 7+, Necrotic, Psychic, Radiant in resistances."""
        builder = _build_paladin(level=7, subclass="Oath of the Ancients")
        resistances = builder.character_data["resistances"]
        assert "Necrotic" in resistances
        assert "Psychic" in resistances
        assert "Radiant" in resistances

    def test_ancients_nature_wrath_feature(self):
        """Nature's Wrath feature at level 3."""
        builder = _build_paladin(level=3, subclass="Oath of the Ancients")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Nature's Wrath" in names


# ==================== Oath of Vengeance Tests ====================


class TestOathOfVengeance:

    def test_vengeance_oath_spells_level_3(self):
        """Bane, Hunter's Mark in always_prepared at level 3."""
        builder = _build_paladin(level=3, subclass="Oath of Vengeance")
        always_prepared = builder.character_data["spells"]["always_prepared"]
        assert "Bane" in always_prepared
        assert "Hunter's Mark" in always_prepared

    def test_vengeance_vow_of_enmity_feature(self):
        """Vow of Enmity feature at level 3."""
        builder = _build_paladin(level=3, subclass="Oath of Vengeance")
        features = builder.character_data["features"]["subclass"]
        names = [f["name"] for f in features]
        assert "Vow of Enmity" in names

    def test_vengeance_oath_spells_level_5(self):
        """Hold Person, Misty Step in always_prepared at level 5+."""
        builder = _build_paladin(level=5, subclass="Oath of Vengeance")
        always_prepared = builder.character_data["spells"]["always_prepared"]
        assert "Hold Person" in always_prepared
        assert "Misty Step" in always_prepared
        # Level 3 spells should still be present
        assert "Bane" in always_prepared
        assert "Hunter's Mark" in always_prepared


# ==================== Spell Progression Test ====================


class TestPaladinSpellProgression:

    def test_paladin_spell_progression(self):
        """At level 9, check spells include levels 3, 5, 9 Oath spells."""
        builder = _build_paladin(level=9, subclass="Oath of Devotion")
        always_prepared = builder.character_data["spells"]["always_prepared"]
        # Level 3 oath spells
        assert "Protection from Evil and Good" in always_prepared
        assert "Shield of Faith" in always_prepared
        # Level 5 oath spells
        assert "Aid" in always_prepared
        assert "Zone of Truth" in always_prepared
        # Level 9 oath spells
        assert "Beacon of Hope" in always_prepared
        assert "Dispel Magic" in always_prepared


# ==================== 2024 Paladin Audit & Mechanics Tests ====================


class TestPaladinMechanics2024:

    def test_level_1_paladin_has_two_first_level_spell_slots(self):
        """2024 Paladin gains 2 level 1 spell slots at level 1."""
        builder = _build_paladin(level=1)
        slots = builder.character_data["class_data"]["spell_slots_by_level"]["1"]
        assert slots[0] == 2
        char = builder.to_character()
        assert char["spell_slots"]["1st"] == 2

    def test_blessed_warrior_fighting_style_grants_cleric_cantrips(self):
        """Blessed Warrior fighting style grants 2 Cleric cantrips using Charisma."""
        builder = _build_full_paladin(
            level=2,
            choices_extra={
                "Fighting Style": "Blessed Warrior",
                "Blessed Warrior_bonus_cantrip": ["Guidance", "Sacred Flame"],
            },
        )
        character = builder.to_character()

        # Both cantrips should be in cantrips or always_prepared
        cantrip_names = [
            s.get("name") if isinstance(s, dict) else s
            for s in character.get("spells", {}).get("cantrips", [])
        ] + list(character.get("spells", {}).get("always_prepared", {}).keys())
        assert "Guidance" in cantrip_names
        assert "Sacred Flame" in cantrip_names

    def test_calculate_paladin_stats_level_1(self):
        """Level 1 Paladin has Lay on Hands pool = 5 and cures Poisoned."""
        builder = _build_paladin(level=1)
        stats = builder.calculate_paladin_stats()
        assert stats["is_paladin"] is True
        assert stats["has_lay_on_hands"] is True
        assert stats["lay_on_hands_pool"] == 5
        assert stats["conditions_cured"] == ["Poisoned"]
        assert stats["has_channel_divinity"] is False

    def test_calculate_paladin_stats_channel_divinity_level_3(self):
        """Level 3 Paladin has 2 Channel Divinity uses and Divine Sense."""
        builder = _build_paladin(level=3, subclass="Oath of Devotion")
        stats = builder.calculate_paladin_stats()
        assert stats["has_channel_divinity"] is True
        assert stats["channel_divinity_max"] == 2
        assert stats["channel_divinity_save_dc"] > 0
        cd_names = [opt["name"] for opt in stats["channel_divinity_options"]]
        assert "Divine Sense" in cd_names
        assert "Sacred Weapon" in cd_names

    def test_calculate_paladin_stats_abjure_foes_level_9(self):
        """Level 9 Paladin gains Abjure Foes Channel Divinity option."""
        builder = _build_paladin(level=9, subclass="Oath of Devotion")
        stats = builder.calculate_paladin_stats()
        cd_names = [opt["name"] for opt in stats["channel_divinity_options"]]
        assert "Abjure Foes" in cd_names

    def test_channel_divinity_uses_level_11(self):
        """At level 11+, Channel Divinity uses increase to 3."""
        builder = _build_paladin(level=11, subclass="Oath of Devotion")
        stats = builder.calculate_paladin_stats()
        assert stats["channel_divinity_max"] == 3

    def test_faithful_steed_free_cast_level_5(self):
        """At level 5+, Find Steed is prepared and has a free cast."""
        builder = _build_paladin(level=5, subclass="Oath of Devotion")
        stats = builder.calculate_paladin_stats()
        assert stats["faithful_steed_free_cast"] is True

    def test_aura_of_protection_applies_to_saving_throws(self):
        """Level 6+ Paladin gains Aura of Protection bonus (+CHA mod, min 1) to all saves."""
        builder = _build_full_paladin(
            level=6,
            subclass="Oath of Devotion",
            ability_scores={
                "Strength": 16, "Dexterity": 10, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 12, "Charisma": 16
            },
            background_bonuses={"Strength": 0, "Charisma": 0},
        )
        character = builder.to_character()
        paladin_stats = character.get("paladin_stats", {})
        aura = paladin_stats.get("aura_of_protection", {})
        assert aura.get("active") is True
        assert aura.get("bonus") == 3
        assert aura.get("range") == "10 ft"

        # CHA mod is +3. All saving throws should include +3 from aura
        abilities = character["abilities"]
        # Dex mod is 0, not proficient (PB=3), so save is 0 + 0 + 3 (aura) = 3
        assert abilities["dexterity"]["saving_throw"] == 3
        assert abilities["dexterity"]["aura_bonus"] == 3

    def test_aura_of_courage_level_10(self):
        """Level 10+ Paladin gains Aura of Courage and Frightened condition immunity."""
        builder = _build_paladin(level=10, subclass="Oath of Devotion")
        character = builder.to_character()
        paladin_stats = character.get("paladin_stats", {})
        assert paladin_stats.get("aura_of_courage", {}).get("active") is True
        assert "Frightened" in character.get("condition_immunities", [])

    def test_radiant_strikes_level_11(self):
        """Level 11+ Paladin adds +1d8 Radiant to melee weapon and unarmed attacks."""
        builder = _build_full_paladin(
            level=11,
            subclass="Oath of Devotion",
            ability_scores={
                "Strength": 16, "Dexterity": 10, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 12, "Charisma": 14
            },
            background_bonuses={"Strength": 0, "Charisma": 0},
        )
        builder.character_data["equipment"] = {
            "weapons": [{"name": "Longsword", "equipped": True, "properties": {"category": "Martial Melee"}}],
            "armor": [],
            "items": [],
            "gold": 0,
        }
        character = builder.to_character()
        paladin_stats = character.get("paladin_stats", {})
        assert paladin_stats.get("radiant_strikes", {}).get("active") is True

        attacks = character.get("attacks", [])
        longsword = next(a for a in attacks if a["name"] == "Longsword")
        assert any("+1d8 Radiant (Radiant Strikes)" in note for note in longsword.get("damage_notes", []))

        unarmed = next(a for a in attacks if a["name"] == "Unarmed Strike")
        assert any("+1d8 Radiant (Radiant Strikes)" in note for note in unarmed.get("damage_notes", []))

    def test_restoring_touch_level_14(self):
        """Level 14 Paladin can cure 6 additional conditions with Lay on Hands."""
        builder = _build_paladin(level=14, subclass="Oath of Devotion")
        stats = builder.calculate_paladin_stats()
        cured = stats["conditions_cured"]
        for cond in ["Poisoned", "Blinded", "Charmed", "Deafened", "Frightened", "Paralyzed", "Stunned"]:
            assert cond in cured

    def test_aura_expansion_level_18(self):
        """Level 18+ Paladin expands Aura of Protection and Courage to 30 ft."""
        builder = _build_paladin(level=18, subclass="Oath of Devotion")
        stats = builder.calculate_paladin_stats()
        assert stats["aura_of_protection"]["range"] == "30 ft"
        assert stats["aura_of_courage"]["range"] == "30 ft"


# ==================== Oath of the Noble Genies Tests ====================


class TestOathOfTheNobleGenies:

    def test_genies_splendor_alternative_ac_unarmored_and_shield(self):
        """Genie's Splendor: unarmored AC equals 10 + DEX + CHA, shields allowed."""
        builder = _build_full_paladin(
            level=3,
            subclass="Oath of the Noble Genies",
            ability_scores={
                "Strength": 14, "Dexterity": 14, "Constitution": 12,
                "Intelligence": 10, "Wisdom": 10, "Charisma": 16
            },
            background_bonuses={"Strength": 0, "Charisma": 0},
        )
        # DEX mod = +2, CHA mod = +3 -> Unarmored AC = 10 + 2 + 3 = 15
        ac_options = builder.calculate_ac_options()
        genie_option = next((opt for opt in ac_options if "Genie's Splendor" in opt.get("notes", [])), None)
        assert genie_option is not None
        assert genie_option["ac"] == 15

        # With Shield equipped: AC should be 15 + 2 = 17
        builder.character_data["equipment"] = {
            "weapons": [],
            "armor": [{"name": "Shield", "category": "Shield", "equipped": True}],
            "items": [],
            "gold": 0,
        }
        ac_options_shield = builder.calculate_ac_options()
        genie_shield_option = next((opt for opt in ac_options_shield if "Genie's Splendor" in opt.get("notes", [])), None)
        assert genie_shield_option is not None
        assert genie_shield_option["ac"] == 17

    def test_genies_splendor_skill_choice(self):
        """Genie's Splendor grants proficiency in one of Acrobatics, Intimidation, Performance, Persuasion."""
        builder = _build_full_paladin(
            level=3,
            subclass="Oath of the Noble Genies",
            choices_extra={"genies_splendor_skill": "Performance"},
        )
        character = builder.to_character()
        assert "Performance" in character["proficiencies"]["skills"]

    def test_noble_genies_channel_divinity_elemental_smite(self):
        """Oath of the Noble Genies has Elemental Smite Channel Divinity option."""
        builder = _build_paladin(level=3, subclass="Oath of the Noble Genies")
        stats = builder.calculate_paladin_stats()
        cd_names = [opt["name"] for opt in stats["channel_divinity_options"]]
        assert "Elemental Smite" in cd_names

    def test_noble_genies_higher_levels(self):
        """Level 7, 15, 20 features for Noble Genies."""
        builder = _build_full_paladin(
            level=20,
            subclass="Oath of the Noble Genies",
            ability_scores={
                "Strength": 16, "Dexterity": 10, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 12, "Charisma": 18
            },
            background_bonuses={"Strength": 0, "Charisma": 0},
        )
        stats = builder.calculate_paladin_stats()
        perk_text = " ".join(stats["active_perks"])
        assert "Aura of Elemental Shielding" in perk_text
        action_names = [act["name"] for act in stats["actions"]]
        assert "Elemental Rebuke" in action_names
        assert "Noble Scion" in action_names
        assert "Elemental Rebuke" in stats["subclass_resources"]

