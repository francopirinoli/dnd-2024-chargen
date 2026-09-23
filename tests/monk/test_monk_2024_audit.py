"""
Comprehensive unit tests for 2024 RAW Monk audit:
- 2024 RAW progression tables & feature definitions
- calculate_monk_stats() engine calculations
- Subclass mechanics (Mercy, Shadow, Elements, Open Hand, Venom, Mystic Arts)
- Attack calculations and damage notes
- Level-up preview monk_changes
- to_character() monk_stats export
"""

import json
from pathlib import Path
import pytest
from modules.character_builder import CharacterBuilder
from modules.derived_stats import build_level_up_preview

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _build_monk(level=1, subclass=None, ability_scores=None, background_bonuses=None):
    builder = CharacterBuilder()
    choices = {
        "character_name": "Test Monk",
        "level": level,
        "species": "Human",
        "class": "Monk",
        "background": "Acolyte",
        "ability_scores": ability_scores or {
            "Strength": 10,
            "Dexterity": 16,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 16,
            "Charisma": 8,
        },
        "background_bonuses": background_bonuses or {
            "Dexterity": 2,
            "Wisdom": 1,
        },
    }
    if subclass and level >= 3:
        choices["subclass"] = subclass
    builder.apply_choices(choices)
    return builder


# ==============================================================================
# 1. Progression Tables & Data Validation
# ==============================================================================

class TestMonkProgressionTables:
    @pytest.fixture(autouse=True)
    def load_data(self):
        monk_path = PROJECT_ROOT / "data" / "classes" / "monk.json"
        self.data = json.loads(monk_path.read_text(encoding="utf-8"))

    def test_martial_arts_die_table(self):
        table = self.data.get("martial_arts_die_by_level")
        assert table is not None
        assert table["1"] == "1d6"
        assert table["4"] == "1d6"
        assert table["5"] == "1d8"
        assert table["10"] == "1d8"
        assert table["11"] == "1d10"
        assert table["16"] == "1d10"
        assert table["17"] == "1d12"
        assert table["20"] == "1d12"

    def test_focus_points_table(self):
        table = self.data.get("focus_points_by_level")
        assert table is not None
        assert table["1"] == 0
        assert table["2"] == 2
        assert table["10"] == 10
        assert table["20"] == 20

    def test_unarmored_movement_bonus_table(self):
        table = self.data.get("unarmored_movement_bonus_by_level")
        assert table is not None
        assert table["1"] == 0
        assert table["2"] == 10
        assert table["5"] == 10
        assert table["6"] == 15
        assert table["9"] == 15
        assert table["10"] == 20
        assert table["13"] == 20
        assert table["14"] == 25
        assert table["17"] == 25
        assert table["18"] == 30
        assert table["20"] == 30

    def test_attacks_per_action_table(self):
        table = self.data.get("attacks_per_action_by_level")
        assert table is not None
        assert table["1"] == 1
        assert table["4"] == 1
        assert table["5"] == 2
        assert table["20"] == 2

    def test_epic_boon_level_19_slot(self):
        feat_19 = self.data["features_by_level"]["19"]["Epic Boon"]
        assert isinstance(feat_19, dict)
        assert feat_19.get("feature_kind") == "asi"
        assert feat_19.get("choices", {}).get("name") == "class_feat_19"
        assert feat_19.get("choices", {}).get("source", {}).get("file") == "general_feats.json"


# ==============================================================================
# 2. calculate_monk_stats() Engine Tests
# ==============================================================================

class TestCalculateMonkStats:
    def test_non_monk_returns_inactive(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Fighter",
            "level": 3,
            "species": "Human",
            "class": "Fighter",
            "background": "Soldier",
            "ability_scores": {"Strength": 16, "Dexterity": 14, "Constitution": 14, "Intelligence": 10, "Wisdom": 12, "Charisma": 8},
        })
        stats = builder.calculate_monk_stats()
        assert stats["is_monk"] is False
        assert stats["monk_level"] == 0
        assert stats["focus_points_max"] == 0

    def test_level_1_monk(self):
        builder = _build_monk(level=1)
        stats = builder.calculate_monk_stats()
        assert stats["is_monk"] is True
        assert stats["monk_level"] == 1
        assert stats["focus_points"] == 0
        assert stats["focus_points_max"] == 0
        assert stats["martial_arts_die"] == "1d6"
        assert stats["unarmored_movement_bonus"] == 0
        assert stats["attacks_per_action"] == 1
        act_names = [a["name"] for a in stats["actions"]]
        assert "Bonus Unarmed Strike" in act_names

    def test_level_2_monk_focus_features(self):
        builder = _build_monk(level=2)
        stats = builder.calculate_monk_stats()
        assert stats["focus_points"] == 2
        assert stats["focus_points_max"] == 2
        assert stats["unarmored_movement_bonus"] == 10
        assert stats["has_uncanny_metabolism"] is True
        act_names = [a["name"] for a in stats["actions"]]
        assert "Flurry of Blows" in act_names
        assert "Patient Defense" in act_names
        assert "Step of the Wind" in act_names
        assert "Uncanny Metabolism" in act_names

    def test_level_3_deflect_attacks(self):
        builder = _build_monk(level=3)
        stats = builder.calculate_monk_stats()
        assert stats["focus_points_max"] == 3
        assert stats["has_deflect_attacks"] is True
        assert stats["has_deflect_energy"] is False
        act_names = [a["name"] for a in stats["actions"]]
        assert "Deflect Attacks" in act_names

    def test_level_5_extra_attack_and_stunning_strike(self):
        builder = _build_monk(level=5)
        stats = builder.calculate_monk_stats()
        assert stats["attacks_per_action"] == 2
        assert stats["martial_arts_die"] == "1d8"
        assert stats["has_stunning_strike"] is True
        act_names = [a["name"] for a in stats["actions"]]
        assert "Stunning Strike" in act_names

    def test_level_6_empowered_strikes(self):
        builder = _build_monk(level=6)
        stats = builder.calculate_monk_stats()
        assert stats["unarmored_movement_bonus"] == 15
        assert stats["has_empowered_strikes"] is True
        assert any("Empowered Strikes" in p for p in stats["active_perks"])

    def test_level_7_evasion(self):
        builder = _build_monk(level=7)
        stats = builder.calculate_monk_stats()
        assert stats["has_evasion"] is True

    def test_level_10_heightened_focus_and_self_restoration(self):
        builder = _build_monk(level=10)
        stats = builder.calculate_monk_stats()
        assert stats["unarmored_movement_bonus"] == 20
        assert stats["has_heightened_focus"] is True
        assert stats["has_self_restoration"] is True
        flurry = next(a for a in stats["actions"] if a["name"] == "Flurry of Blows")
        assert "three" in flurry["effect"]

    def test_level_13_deflect_energy(self):
        builder = _build_monk(level=13)
        stats = builder.calculate_monk_stats()
        assert stats["has_deflect_energy"] is True
        act_names = [a["name"] for a in stats["actions"]]
        assert "Deflect Energy" in act_names

    def test_level_14_disciplined_survivor(self):
        builder = _build_monk(level=14)
        stats = builder.calculate_monk_stats()
        assert stats["has_disciplined_survivor"] is True
        assert stats["unarmored_movement_bonus"] == 25
        act_names = [a["name"] for a in stats["actions"]]
        assert "Disciplined Survivor Reroll" in act_names

    def test_level_15_perfect_focus(self):
        builder = _build_monk(level=15)
        stats = builder.calculate_monk_stats()
        assert stats["has_perfect_focus"] is True

    def test_level_18_superior_defense(self):
        builder = _build_monk(level=18)
        stats = builder.calculate_monk_stats()
        assert stats["has_superior_defense"] is True
        assert stats["unarmored_movement_bonus"] == 30
        assert stats["martial_arts_die"] == "1d12"
        act_names = [a["name"] for a in stats["actions"]]
        assert "Superior Defense" in act_names

    def test_level_20_body_and_mind(self):
        builder = _build_monk(level=20)
        stats = builder.calculate_monk_stats()
        assert stats["has_body_and_mind"] is True
        assert stats["focus_points_max"] == 20


# ==============================================================================
# 3. Subclass Mechanics Tests
# ==============================================================================

class TestMonkSubclasses:
    def test_warrior_of_mercy(self):
        builder = _build_monk(level=3, subclass="Warrior of Mercy")
        stats = builder.calculate_monk_stats()
        sub = stats["subclass_details"].get("warrior_of_mercy", {})
        assert "1d6" in sub.get("hand_of_healing_formula", "")
        act_names = [a["name"] for a in stats["actions"]]
        assert "Hand of Healing" in act_names
        assert "Hand of Harm" in act_names

    def test_warrior_of_mercy_high_level(self):
        builder = _build_monk(level=17, subclass="Warrior of Mercy")
        stats = builder.calculate_monk_stats()
        act_names = [a["name"] for a in stats["actions"]]
        assert "Flurry of Healing & Harm" in act_names
        assert "Hand of Ultimate Mercy" in act_names

    def test_warrior_of_shadow(self):
        builder = _build_monk(level=6, subclass="Warrior of Shadow")
        stats = builder.calculate_monk_stats()
        act_names = [a["name"] for a in stats["actions"]]
        assert "Shadow Arts: Darkness" in act_names
        assert "Shadow Step" in act_names

    def test_warrior_of_shadow_high_level(self):
        builder = _build_monk(level=17, subclass="Warrior of Shadow")
        stats = builder.calculate_monk_stats()
        act_names = [a["name"] for a in stats["actions"]]
        assert "Improved Shadow Step" in act_names
        assert "Cloak of Shadows" in act_names

    def test_warrior_of_the_elements(self):
        builder = _build_monk(level=6, subclass="Warrior of the Elements")
        stats = builder.calculate_monk_stats()
        act_names = [a["name"] for a in stats["actions"]]
        assert "Elemental Attunement" in act_names
        assert "Elemental Burst" in act_names

    def test_warrior_of_the_open_hand(self):
        builder = _build_monk(level=6, subclass="Warrior of the Open Hand")
        stats = builder.calculate_monk_stats()
        act_names = [a["name"] for a in stats["actions"]]
        assert "Open Hand Technique" in act_names
        assert "Wholeness of Body" in act_names

    def test_warrior_of_the_open_hand_quivering_palm(self):
        builder = _build_monk(level=17, subclass="Warrior of the Open Hand")
        stats = builder.calculate_monk_stats()
        act_names = [a["name"] for a in stats["actions"]]
        assert "Quivering Palm" in act_names

    def test_warrior_of_venom_supplement(self):
        # Warrior of Venom from UA supplement
        builder = _build_monk(level=11, subclass="Warrior of Venom")
        stats = builder.calculate_monk_stats()
        act_names = [a["name"] for a in stats["actions"]]
        assert "Envenom Weapon" in act_names
        assert "Toxic Touch" in act_names
        assert any("Toxin Refiner" in p for p in stats["active_perks"])
        # Check poison damage immunity granted
        assert "Poison" in builder.character_data.get("immunities", [])
        # Check poisoner's kit granted
        assert "Poisoner's Kit" in builder.character_data["proficiencies"]["tools"]

    def test_warrior_of_the_mystic_arts_supplement(self):
        # Warrior of the Mystic Arts from Arcana Unleashed supplement
        builder = _build_monk(level=6, subclass="Warrior of the Mystic Arts")
        stats = builder.calculate_monk_stats()
        act_names = [a["name"] for a in stats["actions"]]
        assert "Mystic Fighting Style" in act_names
        assert "Mystic Focus" in act_names


# ==============================================================================
# 4. Attack Notes & Weapon Calculations
# ==============================================================================

class TestMonkAttackNotes:
    def test_empowered_strikes_on_unarmed(self):
        builder = _build_monk(level=6)
        weapons = builder.calculate_weapon_attacks()
        unarmed = next(a for a in weapons["attacks"] if a["name"] == "Unarmed Strike")
        assert any("Empowered Strikes" in note for note in unarmed["damage_notes"])

    def test_warrior_of_mercy_hand_of_harm_note(self):
        builder = _build_monk(level=3, subclass="Warrior of Mercy")
        weapons = builder.calculate_weapon_attacks()
        unarmed = next(a for a in weapons["attacks"] if a["name"] == "Unarmed Strike")
        assert any("Hand of Harm" in note for note in unarmed["damage_notes"])

    def test_warrior_of_the_elements_attunement_note(self):
        builder = _build_monk(level=3, subclass="Warrior of the Elements")
        weapons = builder.calculate_weapon_attacks()
        unarmed = next(a for a in weapons["attacks"] if a["name"] == "Unarmed Strike")
        assert any("Elemental Attunement" in note for note in unarmed["damage_notes"])

    def test_warrior_of_venom_weapon_note(self):
        builder = _build_monk(level=3, subclass="Warrior of Venom")
        dagger = {
            "name": "Dagger",
            "quantity": 1,
            "properties": {
                "category": "Simple Melee",
                "damage": "1d4",
                "damage_type": "Piercing",
                "properties": ["Finesse", "Light", "Thrown"],
            },
        }
        if builder.character_data.get("equipment") is None:
            builder.character_data["equipment"] = {"weapons": [], "armor": [], "items": [], "gold": 0}
        builder.character_data["equipment"].setdefault("weapons", []).append(dagger)
        weapons = builder.calculate_weapon_attacks()
        dagger_atk = next((a for a in weapons["attacks"] if a["name"] == "Dagger"), None)
        assert dagger_atk is not None
        assert any("Envenom Weapon" in note for note in dagger_atk["damage_notes"])


# ==============================================================================
# 5. to_character() Export & Level Up Preview
# ==============================================================================

class TestMonkCharacterExportAndPreview:
    def test_to_character_exports_monk_stats(self):
        builder = _build_monk(level=3)
        char = builder.to_character()
        assert "monk_stats" in char
        assert char["monk_stats"]["is_monk"] is True
        assert char["monk_stats"]["monk_level"] == 3
        assert char["monk_stats"]["focus_points_max"] == 3

    def test_level_up_preview_monk_changes(self):
        choices = {
            "character_name": "Test Monk",
            "classes": [{"class_name": "Monk", "level": 4}],
            "level": 4,
            "species": "Human",
            "background": "Acolyte",
            "ability_scores": {"Strength": 10, "Dexterity": 16, "Constitution": 14, "Intelligence": 10, "Wisdom": 16, "Charisma": 8},
            "background_bonuses": {"Dexterity": 2, "Wisdom": 1},
        }
        preview = build_level_up_preview(choices, class_to_level="Monk")
        monk_changes = preview.get("monk_changes")
        assert monk_changes is not None
        assert monk_changes["is_monk"] is True
        assert monk_changes["current_focus_points"] == 4
        assert monk_changes["next_focus_points"] == 5
        assert monk_changes["focus_points_increased"] is True
        assert monk_changes["current_martial_arts_die"] == "1d6"
        assert monk_changes["next_martial_arts_die"] == "1d8"
        assert monk_changes["martial_arts_die_increased"] is True
        assert monk_changes["stunning_strike_unlocked"] is True
        assert monk_changes["attacks_per_action_increased"] is True
