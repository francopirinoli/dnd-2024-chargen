"""Tests for Bard class features and subclasses (D&D 2024)."""

import json
from pathlib import Path

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def bard_builder():
    """Fixture providing a fresh CharacterBuilder."""
    return CharacterBuilder()


def _build_bard(level=1, subclass=None):
    """Helper to build a Bard character at a given level."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Bard", level)
    if subclass and level >= 3:
        builder.set_subclass(subclass)
    return builder


def _build_full_bard(level=3, subclass=None, ability_scores=None,
                     background_bonuses=None):
    """Helper to build a full Bard character with apply_choices."""
    if ability_scores is None:
        ability_scores = {
            "Strength": 8, "Dexterity": 14, "Constitution": 12,
            "Intelligence": 13, "Wisdom": 10, "Charisma": 15
        }
    if background_bonuses is None:
        background_bonuses = {"Charisma": 2, "Dexterity": 1}

    choices = {
        "character_name": "Test Bard",
        "level": level,
        "species": "Human",
        "class": "Bard",
        "background": "Entertainer",
        "ability_scores": ability_scores,
        "background_bonuses": background_bonuses,
    }
    if subclass and level >= 3:
        choices["subclass"] = subclass

    builder = CharacterBuilder()
    builder.apply_choices(choices)
    return builder


# ==================== Base Bard Class ====================


class TestBardBasicSetup:

    def test_bard_basic_setup(self, bard_builder):
        """Level 1 Bard: class name, saving throws, weapon/armor profs, spellcasting."""
        builder = bard_builder
        builder.set_species("Human")
        builder.set_class("Bard", 1)

        data = builder.character_data
        assert data["class"] == "Bard"
        assert data["level"] == 1

        # Saving throw proficiencies
        saves = data["proficiencies"]["saving_throws"]
        assert "Dexterity" in saves
        assert "Charisma" in saves

        # Weapon proficiencies
        weapons = data["proficiencies"]["weapons"]
        assert "Simple weapons" in weapons

        # Armor proficiencies
        armor = data["proficiencies"]["armor"]
        assert "Light armor" in armor

        # Spellcasting ability
        spell_stats = builder.calculate_spellcasting_stats()
        assert spell_stats["spellcasting_ability"] == "Charisma"

    def test_bard_class_features(self, bard_builder):
        """Level 1 Bard should have Bardic Inspiration and Spellcasting."""
        builder = bard_builder
        builder.set_species("Human")
        builder.set_class("Bard", 1)

        class_features = builder.character_data["features"]["class"]
        feature_names = [f["name"] for f in class_features]

        assert "Bardic Inspiration" in feature_names
        assert "Spellcasting" in feature_names

    def test_bard_level_2_features(self, bard_builder):
        """Level 2 Bard should gain Expertise and Jack of all Trades."""
        builder = bard_builder
        builder.set_species("Human")
        builder.set_class("Bard", 2)

        class_features = builder.character_data["features"]["class"]
        feature_names = [f["name"] for f in class_features]

        assert "Expertise" in feature_names
        assert "Jack of all Trades" in feature_names
        # Level 1 features should still be present
        assert "Bardic Inspiration" in feature_names
        assert "Spellcasting" in feature_names

    def test_bard_subclass_at_level_3(self):
        """Bard subclass is applied at level 3, not level 1."""
        builder_l1 = _build_bard(level=1)
        subclass_features_l1 = builder_l1.character_data["features"].get("subclass", [])
        assert len(subclass_features_l1) == 0, "No subclass features at level 1"

        builder_l3 = _build_bard(level=3, subclass="College of Lore")
        subclass_features_l3 = builder_l3.character_data["features"].get("subclass", [])
        assert len(subclass_features_l3) > 0, "Should have subclass features at level 3"


# ==================== College of Dance ====================


class TestCollegeOfDance:

    def test_dazzling_footwork_feature_present(self):
        """Level 3 College of Dance should have Dazzling Footwork."""
        builder = _build_bard(level=3, subclass="College of Dance")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Dazzling Footwork" in feature_names

    def test_dazzling_footwork_alternative_ac(self):
        """Dazzling Footwork provides alternative AC: 10 + DEX + CHA (no armor).

        DEX 14 + 1 background = 15 → +2 mod.
        CHA 15 + 2 background = 17 → +3 mod.
        Expected AC = 10 + 2 + 3 = 15.
        """
        builder = _build_full_bard(
            level=3,
            subclass="College of Dance",
            ability_scores={
                "Strength": 8, "Dexterity": 14, "Constitution": 12,
                "Intelligence": 13, "Wisdom": 10, "Charisma": 15,
            },
            background_bonuses={"Charisma": 2, "Dexterity": 1},
        )
        character = builder.to_character()
        ac_options = character.get("ac_options", [])

        # Find the Dazzling Footwork / alternative AC option
        dance_ac = [
            opt for opt in ac_options
            if any(
                "Dazzling Footwork" in note or "Unarmored Defense" in note
                for note in opt.get("notes", [])
            )
        ]
        assert len(dance_ac) >= 1, (
            f"Expected Dazzling Footwork AC option, got: {ac_options}"
        )
        assert dance_ac[0]["ac"] == 15, (
            f"Expected AC 15, got {dance_ac[0]['ac']}"
        )

    def test_level_6_features(self):
        """Level 6 College of Dance should have Inspiring Movement and Tandem Footwork."""
        builder = _build_bard(level=6, subclass="College of Dance")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Inspiring Movement" in feature_names
        assert "Tandem Footwork" in feature_names

    def test_level_14_features(self):
        """Level 14 College of Dance should have Leading Evasion."""
        builder = _build_bard(level=14, subclass="College of Dance")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Leading Evasion" in feature_names


# ==================== College of Glamour ====================


class TestCollegeOfGlamour:

    def test_glamour_features_present(self):
        """L3 College of Glamour should have Beguiling Magic and Mantle of Inspiration."""
        builder = _build_bard(level=3, subclass="College of Glamour")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Beguiling Magic" in feature_names
        assert "Mantle of Inspiration" in feature_names

    def test_beguiling_magic_spells(self):
        """At L3, Beguiling Magic grants Charm Person and Mirror Image always prepared."""
        builder = _build_full_bard(level=3, subclass="College of Glamour")
        always_prepared = builder.character_data["spells"]["always_prepared"]

        assert "Charm Person" in always_prepared, (
            f"Charm Person should be always prepared, got: {list(always_prepared.keys()) if isinstance(always_prepared, dict) else always_prepared}"
        )
        assert "Mirror Image" in always_prepared, (
            f"Mirror Image should be always prepared, got: {list(always_prepared.keys()) if isinstance(always_prepared, dict) else always_prepared}"
        )

    def test_mantle_of_majesty_spell(self):
        """At L6, Mantle of Majesty grants Command always prepared."""
        builder = _build_full_bard(level=6, subclass="College of Glamour")
        always_prepared = builder.character_data["spells"]["always_prepared"]

        assert "Command" in always_prepared, (
            f"Command should be always prepared at L6, got: {list(always_prepared.keys()) if isinstance(always_prepared, dict) else always_prepared}"
        )

    def test_mantle_of_majesty_not_at_level_3(self):
        """Command from Mantle of Majesty should NOT be granted at L3."""
        builder = _build_full_bard(level=3, subclass="College of Glamour")
        always_prepared = builder.character_data["spells"]["always_prepared"]

        assert "Command" not in always_prepared, (
            "Command should not be always prepared at L3"
        )

    def test_unbreakable_majesty_at_level_14(self):
        """L14 College of Glamour should have Unbreakable Majesty."""
        builder = _build_bard(level=14, subclass="College of Glamour")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Unbreakable Majesty" in feature_names


# ==================== College of Lore ====================


class TestCollegeOfLore:

    def test_bonus_proficiencies_feature(self):
        """L3 College of Lore should have Bonus Proficiencies feature."""
        builder = _build_bard(level=3, subclass="College of Lore")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Bonus Proficiencies" in feature_names

    def test_cutting_words_feature(self):
        """L3 College of Lore should have Cutting Words."""
        builder = _build_bard(level=3, subclass="College of Lore")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Cutting Words" in feature_names

    def test_lore_features_at_level_6(self):
        """L6 College of Lore should have Magical Discoveries."""
        builder = _build_bard(level=6, subclass="College of Lore")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Magical Discoveries" in feature_names

    def test_lore_features_at_level_14(self):
        """L14 College of Lore should have Peerless Skill."""
        builder = _build_bard(level=14, subclass="College of Lore")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Peerless Skill" in feature_names


# ==================== College of Valor ====================


class TestCollegeOfValor:

    def test_valor_features_present(self):
        """L3 College of Valor should have Combat Inspiration and Martial Training."""
        builder = _build_bard(level=3, subclass="College of Valor")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Combat Inspiration" in feature_names
        assert "Martial Training" in feature_names

    def test_martial_training_weapon_proficiency(self):
        """At L3, Martial Training grants Martial weapons proficiency."""
        builder = _build_full_bard(level=3, subclass="College of Valor")
        weapons = builder.character_data["proficiencies"]["weapons"]

        assert "Martial weapons" in weapons, (
            f"Expected 'Martial weapons' in weapon proficiencies, got: {weapons}"
        )

    def test_martial_training_armor_proficiency(self):
        """At L3, Martial Training grants Medium armor and Shields proficiency."""
        builder = _build_full_bard(level=3, subclass="College of Valor")
        armor = builder.character_data["proficiencies"]["armor"]

        assert "Medium armor" in armor, (
            f"Expected 'Medium armor' in armor proficiencies, got: {armor}"
        )
        assert "Shields" in armor, (
            f"Expected 'Shields' in armor proficiencies, got: {armor}"
        )

    def test_extra_attack_feature(self):
        """L6 College of Valor should have Extra Attack."""
        builder = _build_bard(level=6, subclass="College of Valor")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Extra Attack" in feature_names

    def test_battle_magic_feature(self):
        """L14 College of Valor should have Battle Magic."""
        builder = _build_bard(level=14, subclass="College of Valor")
        subclass_features = builder.character_data["features"]["subclass"]
        feature_names = [f["name"] for f in subclass_features]

        assert "Battle Magic" in feature_names


# ==================== Spell List Completeness (Issue Fix) ====================


class TestBardSpellList:
    """Regression tests for GitHub Issue: Bard spell list incomplete."""

    DATA_DIR = Path(__file__).parent.parent.parent / "data"

    def _load_bard_spell_list(self):
        path = self.DATA_DIR / "spells" / "class_lists" / "bard.json"
        with open(path) as f:
            return json.load(f)

    def test_bard_has_cantrips(self):
        """Bard spell list must include cantrips."""
        data = self._load_bard_spell_list()
        assert len(data.get("cantrips", [])) >= 10, (
            "Expected at least 10 Bard cantrips"
        )

    def test_bard_cantrips_include_key_spells(self):
        """Key Bard cantrips (Vicious Mockery, Minor Illusion) are present."""
        data = self._load_bard_spell_list()
        cantrips = data.get("cantrips", [])
        assert "Vicious Mockery" in cantrips
        assert "Minor Illusion" in cantrips

    def test_bard_has_all_spell_levels(self):
        """Bard spell list must have spells at levels 1 through 9."""
        data = self._load_bard_spell_list()
        spells_by_level = data.get("spells_by_level", {})
        for level in range(1, 10):
            assert str(level) in spells_by_level, (
                f"Missing Bard spells for level {level}"
            )
            assert len(spells_by_level[str(level)]) > 0, (
                f"No spells listed for Bard level {level}"
            )

    def test_bard_level1_includes_key_spells(self):
        """Level 1 Bard spells must include Healing Word and Dissonant Whispers."""
        data = self._load_bard_spell_list()
        level1 = data["spells_by_level"]["1"]
        assert "Healing Word" in level1
        assert "Dissonant Whispers" in level1
        assert "Thunderwave" in level1

    def test_bard_level3_includes_hypnotic_pattern(self):
        """Level 3 Bard spells must include Hypnotic Pattern."""
        data = self._load_bard_spell_list()
        assert "Hypnotic Pattern" in data["spells_by_level"]["3"]

    def test_bard_level5_includes_dominate_person(self):
        """Level 5 Bard spells must include Dominate Person."""
        data = self._load_bard_spell_list()
        assert "Dominate Person" in data["spells_by_level"]["5"]

    def test_bard_level9_includes_power_word_kill(self):
        """Level 9 Bard spells must include Power Word Kill."""
        data = self._load_bard_spell_list()
        assert "Power Word Kill" in data["spells_by_level"]["9"]

    def test_spell_definitions_exist_for_bard_spells(self):
        """All spells in the Bard list must have a definition file."""
        data = self._load_bard_spell_list()
        definitions_dir = self.DATA_DIR / "spells" / "definitions"

        def _to_filename(spell_name: str) -> str:
            return (
                spell_name.lower()
                .replace("'", "")
                .replace("/", "_")
                .replace(" ", "_")
            )

        missing = []
        for spell in data.get("cantrips", []):
            fname = _to_filename(spell) + ".json"
            if not (definitions_dir / fname).exists():
                missing.append(f"cantrip: {spell} ({fname})")

        for level, spells in data.get("spells_by_level", {}).items():
            for spell in spells:
                fname = _to_filename(spell) + ".json"
                if not (definitions_dir / fname).exists():
                    missing.append(f"level {level}: {spell} ({fname})")

        assert missing == [], (
            f"Missing spell definition files:\n" + "\n".join(missing)
        )

    def test_bard_spellcasting_available_spells_populated(self):
        """CharacterBuilder should expose all 9 levels of Bard spells via spellcasting stats."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Bard", 20)
        stats = builder.calculate_spellcasting_stats()

        available = stats.get("available_spells", {})
        for level in range(1, 10):
            assert level in available, (
                f"Bard available_spells missing level {level}"
            )
            assert len(available[level]) > 0, (
                f"Bard available_spells empty for level {level}"
            )


class TestBardToolProficiencyChoice:
    """Regression tests: Bard gets Three Musical Instruments as a tool proficiency choice."""

    def test_bard_tool_options_in_class_data(self):
        """Bard class data should expose tool_proficiencies_count=3 and musical instrument options."""
        builder = CharacterBuilder()
        class_data = builder._load_class_data("Bard")
        assert class_data is not None
        assert class_data.get("tool_proficiencies_count") == 3
        tool_options = class_data.get("tool_options", [])
        assert len(tool_options) >= 10
        assert "Lute" in tool_options
        assert "Flute" in tool_options

    def test_bard_tool_choice_in_class_features(self):
        """get_class_features_and_choices() should include a tool proficiency choice (count=3) for Bard."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Bard", 1)
        feature_data = builder.get_class_features_and_choices()
        choices = feature_data["choices"]
        tool_choices = [c for c in choices if c.get("type") == "tools"]
        assert len(tool_choices) == 1
        tc = tool_choices[0]
        assert tc["count"] == 3
        assert "Lute" in tc["options"]

    def test_bard_apply_three_instrument_choices(self):
        """Applying tool_choices for three instruments should add all to proficiencies."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test Bard",
            "level": 1,
            "species": "Human",
            "class": "Bard",
            "background": "Entertainer",
            "ability_scores": {
                "Strength": 8, "Dexterity": 14, "Constitution": 12,
                "Intelligence": 13, "Wisdom": 10, "Charisma": 15,
            },
            "background_bonuses": {"Charisma": 2, "Dexterity": 1},
            "tool_choices": ["Lute", "Flute", "Drum"],
        })
        character = builder.to_character()
        tools = character["proficiencies"]["tools"]
        assert "Lute" in tools
        assert "Flute" in tools
        assert "Drum" in tools
