"""
Integration tests for the 12 sample character fixtures in ``test_characters/``.

Each test builds a character via ``CharacterBuilder.apply_choices`` using
the ``classes[]`` format, calls ``to_character()``, and asserts a focused set
of expected values covering class identity, skill proficiencies, spellcasting,
darkvision, and key features.

These correspond to the sample characters exposed in
``frontend/src/data/sampleCharacters.ts``.
"""

from __future__ import annotations

import json
from pathlib import Path

from modules.character_builder import CharacterBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_CHARACTERS_DIR = PROJECT_ROOT / "test_characters"


def _load(filename: str) -> dict:
    path = TEST_CHARACTERS_DIR / filename
    return json.loads(path.read_text())["choices_made"]


def _build(choices: dict) -> dict:
    builder = CharacterBuilder()
    ok = builder.apply_choices(choices)
    assert ok, "CharacterBuilder.apply_choices returned False"
    return builder.to_character()


class TestSampleCharacters:

    # ------------------------------------------------------------------
    # 1. Barbarian — Kragor Stonefist (Goliath, Path of the Berserker)
    # ------------------------------------------------------------------

    def test_01_barbarian_kragor(self):
        choices = _load("barbarian_goliath_berserker.json")
        character = _build(choices)

        assert character["class"] == "Barbarian"
        assert character["subclass"] == "Path of the Berserker"
        assert "Athletics" in character["proficiencies"]["skills"]
        assert "Intimidation" in character["proficiencies"]["skills"]
        assert character["spellcasting_stats"]["has_spellcasting"] is False
        assert any(
            "Rage" in f["name"]
            for f in character["features"]["class"]
        )

    # ------------------------------------------------------------------
    # 2. Bard — Vexa Nightsong (Tiefling, College of Valor)
    # ------------------------------------------------------------------

    def test_02_bard_vexa(self):
        choices = _load("bard_tiefling_valor.json")
        character = _build(choices)

        assert character["class"] == "Bard"
        assert character["subclass"] == "College of Valor"
        assert "Performance" in character["proficiencies"]["skills"]
        assert "Persuasion" in character["proficiencies"]["skills"]
        assert character["spellcasting_stats"]["has_spellcasting"] is True
        assert character["spell_slots"]

    # ------------------------------------------------------------------
    # 3. Cleric — Torvin Ironvow (Dwarf, War Domain)
    # ------------------------------------------------------------------

    def test_03_cleric_torvin(self):
        choices = _load("cleric_dwarf_war.json")
        character = _build(choices)

        assert character["class"] == "Cleric"
        assert character["subclass"] == "War Domain"
        assert "History" in character["proficiencies"]["skills"]
        assert "Religion" in character["proficiencies"]["skills"]
        assert character["spellcasting_stats"]["has_spellcasting"] is True
        assert any(
            f["name"] in ("Guided Strike", "War Priest")
            for f in character["features"]["subclass"]
        )

    # ------------------------------------------------------------------
    # 4. Druid — Sylara Dawnwhisper (Wood Elf, Circle of the Moon)
    # ------------------------------------------------------------------

    def test_04_druid_sylara(self):
        choices = _load("druid_elf_moon.json")
        character = _build(choices)

        assert character["class"] == "Druid"
        assert character["subclass"] == "Circle of the Moon"
        assert "Insight" in character["proficiencies"]["skills"]
        assert "Perception" in character["proficiencies"]["skills"]
        assert character["spellcasting_stats"]["has_spellcasting"] is True
        assert character["darkvision"] >= 60

    # ------------------------------------------------------------------
    # 5. Fighter — Valdris Ashenbrow (Human, Battle Master)
    # ------------------------------------------------------------------

    def test_05_fighter_valdris(self):
        choices = _load("fighter_human_battle_master.json")
        character = _build(choices)

        assert character["class"] == "Fighter"
        assert character["subclass"] == "Battle Master"
        assert "Athletics" in character["proficiencies"]["skills"]
        assert "Intimidation" in character["proficiencies"]["skills"]
        assert character["spellcasting_stats"]["has_spellcasting"] is False
        assert character["features"]["subclass"]

    # ------------------------------------------------------------------
    # 6. Monk — Scale-of-Jade (Dragonborn, Warrior of Mercy)
    # ------------------------------------------------------------------

    def test_06_monk_scale_of_jade(self):
        choices = _load("monk_dragonborn_mercy.json")
        character = _build(choices)

        assert character["class"] == "Monk"
        assert character["subclass"] == "Warrior of Mercy"
        assert "Acrobatics" in character["proficiencies"]["skills"]
        assert "Insight" in character["proficiencies"]["skills"]
        assert any(
            f["name"] in ("Martial Arts", "Unarmored Defense")
            for f in character["features"]["class"]
        )

    # ------------------------------------------------------------------
    # 7. Paladin — Seraphel Ashveil (Infernal Tiefling, Oath of Vengeance)
    # ------------------------------------------------------------------

    def test_07_paladin_seraphel(self):
        choices = _load("paladin_tiefling_vengeance.json")
        character = _build(choices)

        assert character["class"] == "Paladin"
        assert character["subclass"] == "Oath of Vengeance"
        assert "Athletics" in character["proficiencies"]["skills"]
        assert "Persuasion" in character["proficiencies"]["skills"]
        assert character["spellcasting_stats"]["has_spellcasting"] is True
        assert character["darkvision"] >= 60

    # ------------------------------------------------------------------
    # 8. Ranger — Senna Nightbough (Wood Elf, Gloom Stalker)
    # ------------------------------------------------------------------

    def test_08_ranger_senna(self):
        choices = _load("ranger_elf_gloom_stalker.json")
        character = _build(choices)

        assert character["class"] == "Ranger"
        assert character["subclass"] == "Gloom Stalker"
        assert "Stealth" in character["proficiencies"]["skills"]
        assert "Perception" in character["proficiencies"]["skills"]
        assert character["spellcasting_stats"]["has_spellcasting"] is True
        assert character["darkvision"] >= 60

    # ------------------------------------------------------------------
    # 9. Rogue — Zara'lyn (Drow Elf, Assassin)
    # ------------------------------------------------------------------

    def test_09_rogue_zara(self):
        choices = _load("rogue_elf_assassin.json")
        character = _build(choices)

        assert character["class"] == "Rogue"
        assert character["subclass"] == "Assassin"
        assert "Stealth" in character["proficiencies"]["skills"]
        assert "Deception" in character["proficiencies"]["skills"]
        assert "Stealth" in character.get("skill_expertise", [])
        assert character["spellcasting_stats"]["has_spellcasting"] is False

    # ------------------------------------------------------------------
    # 10. Sorcerer — Seraphine Dusk (Aasimar, Draconic Sorcery)
    # ------------------------------------------------------------------

    def test_10_sorcerer_seraphine(self):
        choices = _load("sorcerer_aasimar_draconic.json")
        character = _build(choices)

        assert character["class"] == "Sorcerer"
        assert character["subclass"] == "Draconic Sorcery"
        assert "Arcana" in character["proficiencies"]["skills"]
        assert character["spellcasting_stats"]["has_spellcasting"] is True
        assert character["spell_slots"]
        assert character["darkvision"] >= 60

    # ------------------------------------------------------------------
    # 11. Warlock — Grax the Bound (Orc, The Fiend)
    # ------------------------------------------------------------------

    def test_11_warlock_grax(self):
        choices = _load("warlock_orc_fiend.json")
        character = _build(choices)

        assert character["class"] == "Warlock"
        assert character["subclass"] == "The Fiend"
        assert "Intimidation" in character["proficiencies"]["skills"]
        assert character["spellcasting_stats"]["has_spellcasting"] is True
        assert character["pact_magic_slots"]  # Warlocks use Pact Magic, not standard spell slots

    # ------------------------------------------------------------------
    # 12. Wizard — Pip Runebright (Forest Gnome, Evoker)
    # ------------------------------------------------------------------

    def test_12_wizard_pip(self):
        choices = _load("wizard_gnome_evoker.json")
        character = _build(choices)

        assert character["class"] == "Wizard"
        assert character["subclass"] == "Evoker"
        assert "Arcana" in character["proficiencies"]["skills"]
        assert character["spellcasting_stats"]["has_spellcasting"] is True
        assert character["spell_slots"]
        assert character["darkvision"] >= 60
