"""Tests for Sorcerer class features and subclasses (D&D 2024)."""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def sorcerer_builder():
    """Fixture providing a fresh CharacterBuilder."""
    return CharacterBuilder()


def _build_sorcerer(level=1, subclass=None):
    """Helper to build a Sorcerer character at a given level."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Sorcerer", level)
    if subclass and level >= 3:
        builder.set_subclass(subclass)
    return builder


def _build_full_sorcerer(level=3, subclass=None, ability_scores=None,
                         background_bonuses=None):
    """Helper to build a full Sorcerer character with apply_choices."""
    if ability_scores is None:
        ability_scores = {
            "Strength": 8, "Dexterity": 14, "Constitution": 14,
            "Intelligence": 10, "Wisdom": 12, "Charisma": 16
        }
    if background_bonuses is None:
        background_bonuses = {"Charisma": 2, "Constitution": 1}

    choices = {
        "character_name": "Test Sorcerer",
        "level": level,
        "species": "Human",
        "class": "Sorcerer",
        "background": "Acolyte",
        "ability_scores": ability_scores,
        "background_bonuses": background_bonuses,
    }
    if subclass and level >= 3:
        choices["subclass"] = subclass

    builder = CharacterBuilder()
    builder.apply_choices(choices)
    return builder


# ==================== Base Sorcerer Class ====================


class TestSorcererBasicSetup:

    def test_sorcerer_basic_setup(self, sorcerer_builder):
        """Level 1 Sorcerer: class name, saving throws, weapon/armor profs, spellcasting."""
        builder = sorcerer_builder
        builder.set_species("Human")
        builder.set_class("Sorcerer", 1)

        data = builder.character_data
        assert data["class"] == "Sorcerer"
        assert data["level"] == 1

        # Saving throw proficiencies
        saves = data["proficiencies"]["saving_throws"]
        assert "Constitution" in saves
        assert "Charisma" in saves

        # Weapon proficiencies
        weapons = data["proficiencies"]["weapons"]
        assert "Simple weapons" in weapons

        # No armor proficiencies
        assert data["proficiencies"]["armor"] == []

        # Spellcasting ability
        spell_stats = builder.calculate_spellcasting_stats()
        assert spell_stats["spellcasting_ability"] == "Charisma"

    def test_sorcerer_class_features(self, sorcerer_builder):
        """Level 1 Sorcerer should have Spellcasting and Innate Sorcery."""
        builder = sorcerer_builder
        builder.set_species("Human")
        builder.set_class("Sorcerer", 1)

        class_features = builder.character_data["features"]["class"]
        feature_names = [f["name"] for f in class_features]

        assert "Spellcasting" in feature_names
        assert "Innate Sorcery" in feature_names

    def test_sorcerer_level_progression(self, sorcerer_builder):
        """Level 2 Sorcerer should gain Font of Magic and Metamagic."""
        builder = sorcerer_builder
        builder.set_species("Human")
        builder.set_class("Sorcerer", 2)

        class_features = builder.character_data["features"]["class"]
        feature_names = [f["name"] for f in class_features]

        assert "Font of Magic" in feature_names
        assert "Metamagic" in feature_names
        # Level 1 features should still be present
        assert "Spellcasting" in feature_names
        assert "Innate Sorcery" in feature_names

    def test_sorcerer_subclass_at_level_3(self):
        """Sorcerer subclass is applied at level 3, not level 1."""
        builder_l1 = _build_sorcerer(level=1)
        subclass_features_l1 = builder_l1.character_data["features"].get("subclass", [])
        assert len(subclass_features_l1) == 0, "No subclass features at level 1"

        builder_l3 = _build_sorcerer(level=3, subclass="Draconic Sorcery")
        subclass_features_l3 = builder_l3.character_data["features"].get("subclass", [])
        assert len(subclass_features_l3) > 0, "Should have subclass features at level 3"


# ==================== Draconic Sorcery ====================


class TestDraconicSorcery:

    def test_draconic_resilience_hp_bonus(self):
        """Draconic Resilience grants +1 HP per level (bonus_hp per_level).

        L3 Sorcerer, CON 14 (+2 base, +1 background = 15 → +2 mod):
        HP = 6 (L1 max) + 2*4 (avg d6+1 for L2-L3) + 3*2 (CON mod) + 3 (Draconic Resilience) = 23
        """
        builder = _build_full_sorcerer(level=3, subclass="Draconic Sorcery")
        character = builder.to_character()
        hp = character["combat"]["hit_points"]["maximum"]
        # 6 (base) + 8 (2 levels * 4) + 6 (3 * CON +2) + 3 (Draconic Resilience 1/level) = 23
        assert hp == 23, f"Expected 23 HP at L3, got {hp}"

    def test_draconic_resilience_hp_scales(self):
        """HP bonus from Draconic Resilience scales with level.

        L6 Sorcerer, CON 14 (+1 background = 15 → +2 mod):
        HP = 6 + 5*4 + 6*2 + 6 = 6 + 20 + 12 + 6 = 44
        """
        builder_l6 = _build_full_sorcerer(level=6, subclass="Draconic Sorcery")
        char_l6 = builder_l6.to_character()
        hp_l6 = char_l6["combat"]["hit_points"]["maximum"]
        assert hp_l6 == 44, f"Expected 44 HP at L6, got {hp_l6}"

        builder_l3 = _build_full_sorcerer(level=3, subclass="Draconic Sorcery")
        char_l3 = builder_l3.to_character()
        hp_l3 = char_l3["combat"]["hit_points"]["maximum"]
        assert hp_l3 == 23, f"Expected 23 HP at L3, got {hp_l3}"

        # Difference: L6 vs L3
        # Extra levels: 3 levels * 4 (avg d6+1) + 3 * 2 (CON) + 3 (Draconic Resilience) = 12 + 6 + 3 = 21
        assert hp_l6 - hp_l3 == 21, (
            f"HP difference L6-L3 should be 21, got {hp_l6 - hp_l3}"
        )

    def test_draconic_resilience_alternative_ac(self):
        """Draconic Resilience provides alternative AC: 10 + DEX + CHA (unarmored).

        DEX 14 → +2, CHA 16 + 2 background = 18 → +4.
        Expected AC = 10 + 2 + 4 = 16.
        """
        builder = _build_full_sorcerer(
            level=3,
            subclass="Draconic Sorcery",
            ability_scores={
                "Strength": 8, "Dexterity": 14, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 16,
            },
            background_bonuses={"Charisma": 2, "Constitution": 1},
        )
        character = builder.to_character()
        ac_options = character.get("ac_options", [])

        # Find the Draconic Resilience AC option
        draconic_ac = [
            opt for opt in ac_options
            if any("Draconic Resilience" in note for note in opt.get("notes", []))
        ]
        assert len(draconic_ac) >= 1, (
            f"Expected Draconic Resilience AC option, got: {ac_options}"
        )
        assert draconic_ac[0]["ac"] == 16, (
            f"Expected AC 16, got {draconic_ac[0]['ac']}"
        )

    def test_draconic_spells_granted(self):
        """At L3: Alter Self, Chromatic Orb, Command, Dragon's Breath always prepared.
        At L5: Fear, Fly added."""
        builder_l3 = _build_full_sorcerer(level=3, subclass="Draconic Sorcery")
        spells_l3 = builder_l3.character_data["spells"]["always_prepared"]

        for spell in ["Alter Self", "Chromatic Orb", "Command", "Dragon's Breath"]:
            assert spell in spells_l3, f"{spell} should be always prepared at L3"

        # Fear and Fly should NOT be at L3 (min_level 5)
        assert "Fear" not in spells_l3, "Fear should not be prepared at L3"
        assert "Fly" not in spells_l3, "Fly should not be prepared at L3"

        builder_l5 = _build_full_sorcerer(level=5, subclass="Draconic Sorcery")
        spells_l5 = builder_l5.character_data["spells"]["always_prepared"]

        for spell in ["Fear", "Fly"]:
            assert spell in spells_l5, f"{spell} should be always prepared at L5"

    def test_draconic_spells_progression(self):
        """L3 only has L3 spells. L7 adds Arcane Eye and Charm Monster."""
        builder_l3 = _build_full_sorcerer(level=3, subclass="Draconic Sorcery")
        spells_l3 = builder_l3.character_data["spells"]["always_prepared"]

        # L7 spells should not be present at L3
        assert "Arcane Eye" not in spells_l3
        assert "Charm Monster" not in spells_l3

        builder_l7 = _build_full_sorcerer(level=7, subclass="Draconic Sorcery")
        spells_l7 = builder_l7.character_data["spells"]["always_prepared"]

        assert "Arcane Eye" in spells_l7, "Arcane Eye should be prepared at L7"
        assert "Charm Monster" in spells_l7, "Charm Monster should be prepared at L7"

    def test_elemental_affinity_choice(self):
        """Choosing draconic_element 'Fire' should store the choice.

        Note: The damage_type_from_choice effect for Elemental Affinity
        currently requires the choice to be made before the subclass effect
        is applied, or a manual re-application. This test verifies the choice
        is recorded correctly in choices_made.
        """
        builder = _build_full_sorcerer(level=6, subclass="Draconic Sorcery")
        builder.apply_choice("draconic_element", "Fire")

        # The choice should be stored
        choices_made = builder.character_data.get("choices_made", {})
        assert choices_made.get("draconic_element") == "Fire"

    def test_draconic_features_present(self):
        """L3 Draconic Sorcery should have Draconic Resilience and Draconic Spells."""
        builder = _build_sorcerer(level=3, subclass="Draconic Sorcery")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Draconic Resilience" in feature_names
        assert "Draconic Spells" in feature_names


# ==================== Aberrant Sorcery ====================


class TestAberrantSorcery:

    def test_psionic_spells_at_level_3(self):
        """L3 Aberrant: Mind Sliver cantrip + 4 always-prepared spells."""
        builder = _build_full_sorcerer(level=3, subclass="Aberrant Sorcery")
        spells = builder.character_data["spells"]
        always_prepared = spells.get("always_prepared", {})

        # Mind Sliver should be granted as a cantrip (appears in always_prepared)
        assert "Mind Sliver" in always_prepared, (
            f"Mind Sliver should be always prepared, got: {list(always_prepared.keys())}"
        )

        # L3 spells
        for spell in ["Arms of Hadar", "Calm Emotions", "Detect Thoughts",
                       "Dissonant Whispers"]:
            assert spell in always_prepared, (
                f"{spell} should be always prepared at L3"
            )

    def test_psychic_defenses_resistance(self):
        """L6 Aberrant: Psychic damage resistance."""
        builder = _build_full_sorcerer(level=6, subclass="Aberrant Sorcery")
        resistances = builder.character_data.get("resistances", [])
        assert "Psychic" in resistances, (
            f"Expected Psychic resistance at L6, got: {resistances}"
        )

    def test_psychic_defenses_save_advantage(self):
        """L6 Aberrant: advantage on saves vs Charmed/Frightened."""
        builder = _build_full_sorcerer(level=6, subclass="Aberrant Sorcery")
        save_advantages = builder.character_data.get("save_advantages", [])

        charmed_frightened = None
        for entry in save_advantages:
            if "Charmed" in entry.get("condition", "") or "Charmed" in entry.get("display", ""):
                charmed_frightened = entry
                break

        assert charmed_frightened is not None, (
            f"Expected save advantage for Charmed/Frightened, got: {save_advantages}"
        )

    def test_aberrant_features_present(self):
        """L3: Psionic Spells, Telepathic Speech. L6: Psionic Sorcery, Psychic Defenses."""
        builder_l3 = _build_sorcerer(level=3, subclass="Aberrant Sorcery")
        features_l3 = builder_l3.character_data["features"]["subclass"]
        names_l3 = [f["name"] for f in features_l3]

        assert "Psionic Spells" in names_l3
        assert "Telepathic Speech" in names_l3

        builder_l6 = _build_full_sorcerer(level=6, subclass="Aberrant Sorcery")
        features_l6 = builder_l6.character_data["features"]["subclass"]
        names_l6 = [f["name"] for f in features_l6]

        assert "Psionic Sorcery" in names_l6
        assert "Psychic Defenses" in names_l6

    def test_psionic_spells_progression(self):
        """L5: Hunger of Hadar, Sending. L7: Evard's Black Tentacles, Summon Aberration."""
        builder_l3 = _build_full_sorcerer(level=3, subclass="Aberrant Sorcery")
        spells_l3 = builder_l3.character_data["spells"]["always_prepared"]

        # L5 spells should not be at L3
        assert "Hunger of Hadar" not in spells_l3
        assert "Sending" not in spells_l3

        builder_l5 = _build_full_sorcerer(level=5, subclass="Aberrant Sorcery")
        spells_l5 = builder_l5.character_data["spells"]["always_prepared"]

        assert "Hunger of Hadar" in spells_l5
        assert "Sending" in spells_l5

        builder_l7 = _build_full_sorcerer(level=7, subclass="Aberrant Sorcery")
        spells_l7 = builder_l7.character_data["spells"]["always_prepared"]

        assert "Evard's Black Tentacles" in spells_l7
        assert "Summon Aberration" in spells_l7


# ==================== Clockwork Sorcery ====================


class TestClockworkSorcery:

    def test_clockwork_spells_at_level_3(self):
        """L3 Clockwork: Aid, Alarm, Lesser Restoration, Protection from Evil and Good."""
        builder = _build_full_sorcerer(level=3, subclass="Clockwork Sorcery")
        spells = builder.character_data["spells"]["always_prepared"]

        for spell in ["Aid", "Alarm", "Lesser Restoration",
                       "Protection from Evil and Good"]:
            assert spell in spells, f"{spell} should be always prepared at L3"

    def test_clockwork_spells_progression(self):
        """Clockwork spells at L5, L7, L9."""
        # L5: Dispel Magic, Protection from Energy
        builder_l5 = _build_full_sorcerer(level=5, subclass="Clockwork Sorcery")
        spells_l5 = builder_l5.character_data["spells"]["always_prepared"]
        assert "Dispel Magic" in spells_l5
        assert "Protection from Energy" in spells_l5

        # L7: Freedom of Movement, Summon Construct
        builder_l7 = _build_full_sorcerer(level=7, subclass="Clockwork Sorcery")
        spells_l7 = builder_l7.character_data["spells"]["always_prepared"]
        assert "Freedom of Movement" in spells_l7
        assert "Summon Construct" in spells_l7

        # L9: Greater Restoration, Wall of Force
        builder_l9 = _build_full_sorcerer(level=9, subclass="Clockwork Sorcery")
        spells_l9 = builder_l9.character_data["spells"]["always_prepared"]
        assert "Greater Restoration" in spells_l9
        assert "Wall of Force" in spells_l9

    def test_clockwork_features_present(self):
        """L3: Clockwork Spells, Restore Balance."""
        builder = _build_sorcerer(level=3, subclass="Clockwork Sorcery")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Clockwork Spells" in feature_names
        assert "Restore Balance" in feature_names


# ==================== Wild Magic Sorcery ====================


class TestWildMagicSorcery:

    def test_wild_magic_features_present(self):
        """Wild Magic features at various levels."""
        # L3: Wild Magic Surge, Tides of Chaos
        builder_l3 = _build_sorcerer(level=3, subclass="Wild Magic Sorcery")
        features_l3 = builder_l3.character_data["features"]["subclass"]
        names_l3 = [f["name"] for f in features_l3]
        assert "Wild Magic Surge" in names_l3
        assert "Tides of Chaos" in names_l3

        # L6: Bend Luck
        builder_l6 = _build_sorcerer(level=6, subclass="Wild Magic Sorcery")
        features_l6 = builder_l6.character_data["features"]["subclass"]
        names_l6 = [f["name"] for f in features_l6]
        assert "Bend Luck" in names_l6

        # L14: Controlled Chaos
        builder_l14 = _build_sorcerer(level=14, subclass="Wild Magic Sorcery")
        features_l14 = builder_l14.character_data["features"]["subclass"]
        names_l14 = [f["name"] for f in features_l14]
        assert "Controlled Chaos" in names_l14

        # L18: Tamed Surge
        builder_l18 = _build_sorcerer(level=18, subclass="Wild Magic Sorcery")
        features_l18 = builder_l18.character_data["features"]["subclass"]
        names_l18 = [f["name"] for f in features_l18]
        assert "Tamed Surge" in names_l18

    def test_wild_magic_no_mechanical_effects(self):
        """Wild Magic Sorcery has purely narrative features — no resistances, no alt AC."""
        builder = _build_full_sorcerer(level=6, subclass="Wild Magic Sorcery")
        char_data = builder.character_data

        # No resistances from Wild Magic (Human has none innately either)
        resistances = char_data.get("resistances", [])
        assert len(resistances) == 0, (
            f"Wild Magic should have no resistances, got: {resistances}"
        )

        # No alternative AC effects
        character = builder.to_character()
        ac_options = character.get("ac_options", [])
        alt_ac = [
            opt for opt in ac_options
            if opt.get("notes") and any(
                "Wild Magic" in note for note in opt["notes"]
            )
        ]
        assert len(alt_ac) == 0, "Wild Magic should have no alternative AC options"

        # No save advantages from subclass
        save_advantages = char_data.get("save_advantages", [])
        wild_magic_saves = [
            sa for sa in save_advantages
            if "Wild Magic" in sa.get("condition", "")
        ]
        assert len(wild_magic_saves) == 0
