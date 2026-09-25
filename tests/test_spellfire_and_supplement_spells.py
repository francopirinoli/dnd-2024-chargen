"""
Tests for Spellfire Sorcery and supplement subclass spell lists (Genie Spells, Winter Walker Spells).
Verifies:
1. Spellfire Sorcery 2024 RAW mechanics:
   - Spellfire Burst (Bolstering Flames, Radiant Fire)
   - Spellfire Spells (HTML table format, always prepared spells)
   - Absorb Spells at Level 6 (Counterspell prepared, 1d4 SP recovery, correct description, no duplicate table)
   - Honed Spellfire at Level 14 (scaling THP and damage die)
   - Crown of Spellfire at Level 18
   - calculate_sorcerer_stats subclass_details, actions, and active_perks
2. Oath of the Noble Genies:
   - Genie Spells HTML table format and always-prepared spells (including cantrip Elementalism)
3. Winter Walker:
   - Winter Walker Spells HTML table format and always-prepared spells
   - Frigid Explorer Cold damage resistance
"""

import pytest
from modules.character_builder import CharacterBuilder


class TestSpellfireSorcery:
    def test_spellfire_spells_level_3(self):
        cb = CharacterBuilder()
        cb.set_class("Sorcerer", 3)
        cb.set_subclass("Spellfire Sorcery")

        subclass_features = {f["name"]: f for f in cb.character_data["features"]["subclass"]}
        assert "Spellfire Spells" in subclass_features
        spellfire_desc = subclass_features["Spellfire Spells"]["description"]

        # Verifies table is rendered
        assert '<table class="table table-sm table-bordered mt-2">' in spellfire_desc
        assert "Cure Wounds" in spellfire_desc
        assert "Guiding Bolt" in spellfire_desc
        assert "Lesser Restoration" in spellfire_desc
        assert "Scorching Ray" in spellfire_desc
        assert "Aura of Vitality" in spellfire_desc
        assert "Dispel Magic" in spellfire_desc
        assert "Fire Shield" in spellfire_desc
        assert "Wall of Fire" in spellfire_desc
        assert "Greater Restoration" in spellfire_desc
        assert "Flame Strike" in spellfire_desc

        # Level 3 row should be unlocked, level 5+ locked
        assert '<tr class="table-success"><td>3</td><td>✓ Cure Wounds, Guiding Bolt, Lesser Restoration, Scorching Ray</td></tr>' in spellfire_desc
        assert '<tr class="table-secondary"><td>5</td>' in spellfire_desc

        # Always prepared spells at level 3
        always_prep = cb.character_data["spells"]["always_prepared"]
        assert "Cure Wounds" in always_prep
        assert "Guiding Bolt" in always_prep
        assert "Lesser Restoration" in always_prep
        assert "Scorching Ray" in always_prep
        assert "Aura of Vitality" not in always_prep
        assert "Counterspell" not in always_prep

    def test_absorb_spells_level_6(self):
        cb = CharacterBuilder()
        cb.set_class("Sorcerer", 6)
        cb.set_subclass("Spellfire Sorcery")

        subclass_features = {f["name"]: f for f in cb.character_data["features"]["subclass"]}
        assert "Absorb Spells" in subclass_features
        absorb_desc = subclass_features["Absorb Spells"]["description"]

        # Verify correct 2024 RAW description and NOT copy-pasted Spellfire Spells
        assert "Counterspell" in absorb_desc
        assert "regain 1d4 Sorcery Points" in absorb_desc
        assert "When you reach a Sorcerer level specified in the Spellfire Spells table" not in absorb_desc

        # Verify Counterspell is granted in always_prepared spells
        always_prep = cb.character_data["spells"]["always_prepared"]
        assert "Counterspell" in always_prep
        assert "Aura of Vitality" in always_prep
        assert "Dispel Magic" in always_prep

        # Verify Spellfire Spells table has level 3 and 5 unlocked
        spellfire_desc = subclass_features["Spellfire Spells"]["description"]
        assert '<tr class="table-success"><td>3</td>' in spellfire_desc
        assert '<tr class="table-success"><td>5</td>' in spellfire_desc
        assert '<tr class="table-secondary"><td>7</td>' in spellfire_desc

    def test_spellfire_sorcerer_stats_and_actions(self):
        cb = CharacterBuilder()
        cb.set_class("Sorcerer", 6)
        cb.set_subclass("Spellfire Sorcery")

        stats = cb.calculate_sorcerer_stats()
        details = stats["subclass_details"]
        assert details["name"] == "Spellfire Sorcery"
        assert details["spellfire_burst"] is True
        assert details["spellfire_burst_die"] == "1d4"
        assert details["absorb_spells"] is True
        assert details["honed_spellfire"] is False

        action_names = [a["name"] for a in stats["actions"]]
        assert "Spellfire Burst" in action_names
        assert "Absorb Spells" in action_names

        perks = " ".join(stats["active_perks"])
        assert "Spellfire Burst" in perks
        assert "Spellfire Spells" in perks
        assert "Absorb Spells" in perks

    def test_spellfire_honed_and_crown_scaling(self):
        cb = CharacterBuilder()
        cb.set_class("Sorcerer", 18)
        cb.set_subclass("Spellfire Sorcery")

        stats = cb.calculate_sorcerer_stats()
        details = stats["subclass_details"]
        assert details["honed_spellfire"] is True
        assert details["spellfire_burst_die"] == "1d8"
        assert details["crown_of_spellfire"] is True

        action_names = [a["name"] for a in stats["actions"]]
        assert "Crown of Spellfire" in action_names

        perks = " ".join(stats["active_perks"])
        assert "Honed Spellfire" in perks
        assert "Crown of Spellfire" in perks


class TestSupplementSubclassSpells:
    def test_genie_spells_paladin(self):
        cb = CharacterBuilder()
        cb.set_class("Paladin", 3)
        cb.set_subclass("Oath of the Noble Genies")

        subclass_features = {f["name"]: f for f in cb.character_data["features"]["subclass"]}
        assert "Genie Spells" in subclass_features
        desc = subclass_features["Genie Spells"]["description"]

        assert '<table class="table table-sm table-bordered mt-2">' in desc
        assert "Chromatic Orb" in desc
        assert "Elementalism" in desc
        assert "Thunderous Smite" in desc
        assert "Mirror Image" in desc
        assert "Phantasmal Force" in desc
        assert "Fly" in desc
        assert "Gaseous Form" in desc
        assert "Conjure Minor Elementals" in desc
        assert "Summon Elemental" in desc
        assert "Banishing Smite" in desc
        assert "Contact Other Plane" in desc

        always_prep = cb.character_data["spells"]["always_prepared"]
        assert "Chromatic Orb" in always_prep
        assert "Elementalism" in always_prep
        assert "Thunderous Smite" in always_prep

    def test_winter_walker_ranger(self):
        cb = CharacterBuilder()
        cb.set_class("Ranger", 3)
        cb.set_subclass("Winter Walker")

        subclass_features = {f["name"]: f for f in cb.character_data["features"]["subclass"]}
        assert "Winter Walker Spells" in subclass_features
        desc = subclass_features["Winter Walker Spells"]["description"]

        assert '<table class="table table-sm table-bordered mt-2">' in desc
        assert "Ice Knife" in desc
        assert "Hold Person" in desc
        assert "Remove Curse" in desc
        assert "Ice Storm" in desc
        assert "Cone of Cold" in desc

        always_prep = cb.character_data["spells"]["always_prepared"]
        assert "Ice Knife" in always_prep

        # Check Cold resistance from Frigid Explorer
        assert "Cold" in cb.character_data.get("resistances", [])
