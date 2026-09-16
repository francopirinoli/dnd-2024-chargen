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
