#!/usr/bin/env python3
"""
Pytest tests for Fighter subclass features: Champion, Eldritch Knight, Psi Warrior, Battle Master progression.
"""

import pytest
from modules.character_builder import CharacterBuilder


def build_fighter(level, subclass):
    """Helper to build a complete Fighter character at a given level with a subclass."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_background("Soldier")
    builder.set_class("Fighter", level)
    builder.set_subclass(subclass)
    return builder.to_character()


class TestChampionFeatures:
    """Test Champion subclass features at each progression level."""

    def test_level_3_improved_critical(self):
        character = build_fighter(3, "Champion")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Improved Critical" in names

    def test_level_3_remarkable_athlete(self):
        character = build_fighter(3, "Champion")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Remarkable Athlete" in names

    def test_level_3_improved_critical_description(self):
        character = build_fighter(3, "Champion")
        subclass_features = character["features"]["subclass"]
        feature = next(f for f in subclass_features if f["name"] == "Improved Critical")
        assert "19 or 20" in feature["description"]

    def test_level_7_additional_fighting_style(self):
        character = build_fighter(7, "Champion")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Additional Fighting Style" in names

    def test_level_7_additional_fighting_style_description(self):
        character = build_fighter(7, "Champion")
        subclass_features = character["features"]["subclass"]
        feature = next(f for f in subclass_features if f["name"] == "Additional Fighting Style")
        assert "Fighting Style" in feature["description"]

    def test_level_10_heroic_warrior(self):
        """Verify the feature is named 'Heroic Warrior' (not 'Heroic Champion')."""
        character = build_fighter(10, "Champion")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Heroic Warrior" in names
        assert "Heroic Champion" not in names

    def test_level_15_superior_critical(self):
        character = build_fighter(15, "Champion")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Superior Critical" in names

    def test_level_15_superior_critical_description(self):
        character = build_fighter(15, "Champion")
        subclass_features = character["features"]["subclass"]
        feature = next(f for f in subclass_features if f["name"] == "Superior Critical")
        assert "18-20" in feature["description"]

    def test_level_18_survivor(self):
        character = build_fighter(18, "Champion")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Survivor" in names

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Improved Critical", "Remarkable Athlete"]),
            (7, ["Additional Fighting Style"]),
            (10, ["Heroic Warrior"]),
            (15, ["Superior Critical"]),
            (18, ["Survivor"]),
        ],
    )
    def test_champion_feature_progression(self, level, expected_features):
        character = build_fighter(level, "Champion")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        for feature_name in expected_features:
            assert feature_name in names, f"Expected '{feature_name}' at level {level}"


class TestEldritchKnightFeatures:
    """Test Eldritch Knight subclass features and spellcasting."""

    def test_level_3_spellcasting_feature(self):
        character = build_fighter(3, "Eldritch Knight")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Spellcasting" in names

    def test_level_3_war_bond_feature(self):
        """Verify the feature is named 'War Bond' (not 'Weapon Bond')."""
        character = build_fighter(3, "Eldritch Knight")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "War Bond" in names
        assert "Weapon Bond" not in names

    def test_level_3_has_spellcasting(self):
        character = build_fighter(3, "Eldritch Knight")
        stats = character["spellcasting_stats"]
        assert stats["has_spellcasting"] is True

    def test_level_3_spellcasting_ability(self):
        character = build_fighter(3, "Eldritch Knight")
        stats = character["spellcasting_stats"]
        assert stats["spellcasting_ability"] == "Intelligence"

    def test_level_3_spell_slots(self):
        character = build_fighter(3, "Eldritch Knight")
        spell_slots = character["spell_slots"]
        assert spell_slots.get("1st") == 2

    def test_level_3_max_cantrips_prepared(self):
        character = build_fighter(3, "Eldritch Knight")
        stats = character["spellcasting_stats"]
        assert stats["max_cantrips_prepared"] == 2

    def test_level_7_war_magic(self):
        character = build_fighter(7, "Eldritch Knight")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "War Magic" in names

    def test_level_7_war_magic_description_2024(self):
        """Verify War Magic has 2024 wording (replace attack with cantrip)."""
        character = build_fighter(7, "Eldritch Knight")
        subclass_features = character["features"]["subclass"]
        feature = next(f for f in subclass_features if f["name"] == "War Magic")
        assert "cantrip" in feature["description"].lower()

    def test_level_7_spell_slots(self):
        character = build_fighter(7, "Eldritch Knight")
        spell_slots = character["spell_slots"]
        assert spell_slots.get("1st") == 4
        assert spell_slots.get("2nd") == 2

    def test_level_10_eldritch_strike(self):
        character = build_fighter(10, "Eldritch Knight")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Eldritch Strike" in names

    def test_level_10_max_cantrips_prepared(self):
        character = build_fighter(10, "Eldritch Knight")
        stats = character["spellcasting_stats"]
        assert stats["max_cantrips_prepared"] == 3

    def test_level_15_arcane_charge(self):
        character = build_fighter(15, "Eldritch Knight")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Arcane Charge" in names

    def test_level_18_improved_war_magic(self):
        character = build_fighter(18, "Eldritch Knight")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Improved War Magic" in names

    def test_level_18_improved_war_magic_description_2024(self):
        """Verify Improved War Magic has 2024 wording (level 1 or level 2 spells)."""
        character = build_fighter(18, "Eldritch Knight")
        subclass_features = character["features"]["subclass"]
        feature = next(f for f in subclass_features if f["name"] == "Improved War Magic")
        assert "level 1" in feature["description"].lower() or "level 2" in feature["description"].lower()

    def test_level_19_spell_slots_include_4th(self):
        character = build_fighter(19, "Eldritch Knight")
        spell_slots = character["spell_slots"]
        assert spell_slots.get("4th", 0) >= 1

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Spellcasting", "War Bond"]),
            (7, ["War Magic"]),
            (10, ["Eldritch Strike"]),
            (15, ["Arcane Charge"]),
            (18, ["Improved War Magic"]),
        ],
    )
    def test_ek_feature_progression(self, level, expected_features):
        character = build_fighter(level, "Eldritch Knight")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        for feature_name in expected_features:
            assert feature_name in names, f"Expected '{feature_name}' at level {level}"

    def test_spellcasting_uses_wizard_spell_list(self):
        """Regression: Eldritch Knight available spells must come from Wizard list, not Fighter."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_background("Soldier")
        builder.set_class("Fighter", 3)
        builder.set_subclass("Eldritch Knight")
        stats = builder.calculate_spellcasting_stats()
        assert stats["has_spellcasting"] is True
        # Must have Wizard cantrips (e.g., Fire Bolt) and spells available
        assert len(stats.get("available_cantrips", [])) > 0, (
            "Eldritch Knight should have Wizard cantrips available"
        )
        assert len(stats.get("available_spells", {})) > 0, (
            "Eldritch Knight should have Wizard spells available"
        )
    """Test Psi Warrior subclass features and effects."""

    def test_level_3_psionic_power(self):
        character = build_fighter(3, "Psi Warrior")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Psionic Power" in names

    def test_level_3_psionic_power_description_mentions_abilities(self):
        character = build_fighter(3, "Psi Warrior")
        subclass_features = character["features"]["subclass"]
        feature = next(f for f in subclass_features if f["name"] == "Psionic Power")
        desc = feature["description"]
        assert "Protective Field" in desc
        assert "Psionic Strike" in desc
        assert "Telekinetic Movement" in desc

    def test_level_7_telekinetic_adept(self):
        """Verify the feature is named 'Telekinetic Adept' (not 'Psi-Powered Leap')."""
        character = build_fighter(7, "Psi Warrior")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Telekinetic Adept" in names

    def test_level_10_guarded_mind(self):
        character = build_fighter(10, "Psi Warrior")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Guarded Mind" in names

    def test_level_10_guarded_mind_psychic_resistance_effect(self):
        character = build_fighter(10, "Psi Warrior")
        effects = character.get("effects", [])
        resistance_effects = [
            e for e in effects
            if e["type"] == "grant_damage_resistance" and e["damage_type"] == "Psychic"
        ]
        assert len(resistance_effects) >= 1, "Expected Psychic damage resistance from Guarded Mind"

    def test_level_15_bulwark_of_force(self):
        character = build_fighter(15, "Psi Warrior")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Bulwark of Force" in names

    def test_level_15_bulwark_of_force_description(self):
        character = build_fighter(15, "Psi Warrior")
        subclass_features = character["features"]["subclass"]
        feature = next(f for f in subclass_features if f["name"] == "Bulwark of Force")
        assert "Half Cover" in feature["description"]

    def test_level_18_telekinetic_master(self):
        character = build_fighter(18, "Psi Warrior")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Telekinetic Master" in names

    def test_level_18_telekinetic_master_grant_spell_effect(self):
        character = build_fighter(18, "Psi Warrior")
        effects = character.get("effects", [])
        spell_effects = [
            e for e in effects
            if e["type"] == "grant_spell" and e["spell"] == "Telekinesis"
        ]
        assert len(spell_effects) >= 1, "Expected grant_spell Telekinesis from Telekinetic Master"

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Psionic Power"]),
            (7, ["Telekinetic Adept"]),
            (10, ["Guarded Mind"]),
            (15, ["Bulwark of Force"]),
            (18, ["Telekinetic Master"]),
        ],
    )
    def test_psi_warrior_feature_progression(self, level, expected_features):
        character = build_fighter(level, "Psi Warrior")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        for feature_name in expected_features:
            assert feature_name in names, f"Expected '{feature_name}' at level {level}"


class TestBattleMasterProgression:
    """Test Battle Master subclass feature progression (levels 7+, not covered by existing tests)."""

    def test_level_7_know_your_enemy(self):
        character = build_fighter(7, "Battle Master")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Know Your Enemy" in names

    def test_level_10_improved_combat_superiority(self):
        character = build_fighter(10, "Battle Master")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Improved Combat Superiority" in names

    def test_level_10_improved_combat_superiority_description(self):
        character = build_fighter(10, "Battle Master")
        subclass_features = character["features"]["subclass"]
        feature = next(f for f in subclass_features if f["name"] == "Improved Combat Superiority")
        assert "d10" in feature["description"]

    def test_level_15_relentless(self):
        character = build_fighter(15, "Battle Master")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Relentless" in names

    def test_level_18_ultimate_combat_superiority(self):
        character = build_fighter(18, "Battle Master")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        assert "Ultimate Combat Superiority" in names

    def test_level_18_ultimate_combat_superiority_description(self):
        character = build_fighter(18, "Battle Master")
        subclass_features = character["features"]["subclass"]
        feature = next(f for f in subclass_features if f["name"] == "Ultimate Combat Superiority")
        assert "d12" in feature["description"]

    def test_student_of_war_selected_tool_and_skill_are_granted(self):
        builder = CharacterBuilder()
        builder.apply_choices(
            {
                "character_name": "Student of War Test",
                "level": 3,
                "species": "Human",
                "class": "Fighter",
                "subclass": "Battle Master",
                "background": "Soldier",
                "ability_scores": {
                    "Strength": 14,
                    "Dexterity": 14,
                    "Constitution": 14,
                    "Intelligence": 10,
                    "Wisdom": 10,
                    "Charisma": 10,
                },
                "subclass_Student of War_artisan_tool": "Smith's Tools",
                "subclass_Student of War_fighter_skill": "Perception",
            }
        )

        character = builder.to_character()
        assert "Smith's Tools" in character["proficiencies"]["tools"]
        assert "Perception" in character["proficiencies"]["skills"]

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (7, ["Know Your Enemy"]),
            (10, ["Improved Combat Superiority"]),
            (15, ["Relentless"]),
            (18, ["Ultimate Combat Superiority"]),
        ],
    )
    def test_battle_master_feature_progression(self, level, expected_features):
        character = build_fighter(level, "Battle Master")
        subclass_features = character["features"]["subclass"]
        names = [f["name"] for f in subclass_features]
        for feature_name in expected_features:
            assert feature_name in names, f"Expected '{feature_name}' at level {level}"
