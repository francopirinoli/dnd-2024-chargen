"""Unit tests for the Level Up Preview feature."""

import pytest
from app import app
from modules.derived_stats import build_level_up_preview


class TestLevelUpPreview:
    """Tests for build_level_up_preview pure function."""

    def test_fighter_1_to_2(self):
        choices = {
            "class": "Fighter",
            "level": 1,
            "ability_scores": {"Constitution": 14},
        }
        preview = build_level_up_preview(choices)

        assert preview["can_level_up"] is True
        assert preview["class_name"] == "Fighter"
        assert preview["current_class_level"] == 1
        assert preview["next_class_level"] == 2
        assert preview["current_total_level"] == 1
        assert preview["next_total_level"] == 2

        # Fighter hit die is d10. Average roll is 6. CON mod 14 -> +2. Total +8
        hp = preview["hp_increase"]
        assert hp["hit_die"] == 10
        assert hp["average_roll"] == 6
        assert hp["con_modifier"] == 2
        assert hp["total_increase"] == 8
        assert hp["next_max_hp"] == hp["current_max_hp"] + 8

        # Proficiency bonus stays +2 at level 2
        assert preview["proficiency_bonus"]["current"] == 2
        assert preview["proficiency_bonus"]["next"] == 2
        assert preview["proficiency_bonus"]["increased"] is False

        # Features gained at level 2 (Action Surge, Tactical Mind)
        feature_names = [f["name"] for f in preview["features_gained"]]
        assert "Action Surge" in feature_names

        # Does not need subclass or feat at level 2
        assert preview["subclass"]["needs_subclass"] is False
        assert preview["feat"]["needs_feat"] is False

    def test_wizard_2_to_3_subclass_and_slots(self):
        choices = {
            "class": "Wizard",
            "level": 2,
            "ability_scores": {"Intelligence": 16, "Constitution": 12},
        }
        preview = build_level_up_preview(choices)

        assert preview["can_level_up"] is True
        assert preview["current_class_level"] == 2
        assert preview["next_class_level"] == 3

        # Subclass required at level 3 in D&D 2024
        assert preview["subclass"]["needs_subclass"] is True
        assert len(preview["subclass"]["available_subclasses"]) > 0
        sub_names = [s["name"] for s in preview["subclass"]["available_subclasses"]]
        assert "Evoker" in sub_names or "Evocation" in sub_names or "Abjurer" in sub_names

        # Spellcasting: 2nd level slots unlocked
        spell_changes = preview["spellcasting_changes"]
        assert spell_changes["has_spellcasting"] is True
        assert 2 in spell_changes["unlocked_slot_levels"]
        assert spell_changes["next_prepared_limit"] > spell_changes["current_prepared_limit"]

        # Wizard spellbook expansion
        sb = spell_changes["wizard_spellbook"]
        assert sb is not None
        assert sb["spells_added"] == 2
        assert sb["next_limit"] == sb["current_limit"] + 2

    def test_rogue_3_to_4_feat(self):
        choices = {
            "class": "Rogue",
            "level": 3,
            "subclass": "Assassin",
            "ability_scores": {"Dexterity": 16, "Constitution": 12},
        }
        preview = build_level_up_preview(choices)

        assert preview["can_level_up"] is True
        assert preview["current_class_level"] == 3
        assert preview["next_class_level"] == 4

        # Feat / ASI required at level 4
        assert preview["feat"]["needs_feat"] is True
        assert preview["feat"]["choice_key"] == "class_feat_4"
        assert preview["feat"]["slot_level"] == 4

        # Subclass already selected, should not prompt again
        assert preview["subclass"]["needs_subclass"] is False

    def test_level_4_to_5_proficiency_bonus_increase(self):
        choices = {
            "class": "Barbarian",
            "level": 4,
            "subclass": "Path of the Berserker",
            "ability_scores": {"Strength": 16, "Constitution": 14},
        }
        preview = build_level_up_preview(choices)

        assert preview["can_level_up"] is True
        assert preview["proficiency_bonus"]["current"] == 2
        assert preview["proficiency_bonus"]["next"] == 3
        assert preview["proficiency_bonus"]["increased"] is True

    def test_level_20_cap(self):
        choices = {
            "class": "Cleric",
            "level": 20,
            "subclass": "Life Domain",
        }
        preview = build_level_up_preview(choices)
        assert preview["can_level_up"] is False
        assert "maximum level" in preview["reason"].lower()

    def test_multiclass_level_up_selection(self):
        choices = {
            "classes": [
                {"class_name": "Fighter", "level": 3, "subclass": "Battle Master"},
                {"class_name": "Wizard", "level": 1},
            ],
            "level": 4,
            "ability_scores": {"Strength": 14, "Intelligence": 14, "Constitution": 12},
        }

        # Level up Wizard specifically
        preview_wiz = build_level_up_preview(choices, class_to_level="Wizard")
        assert preview_wiz["class_name"] == "Wizard"
        assert preview_wiz["current_class_level"] == 1
        assert preview_wiz["next_class_level"] == 2
        assert preview_wiz["current_total_level"] == 4
        assert preview_wiz["next_total_level"] == 5
        wiz_features = [f["name"] for f in preview_wiz["features_gained"]]
        assert "Scholar" in wiz_features
        assert "Action Surge" not in wiz_features

        # Level up Fighter specifically
        preview_fighter = build_level_up_preview(choices, class_to_level="Fighter")
        assert preview_fighter["class_name"] == "Fighter"
        assert preview_fighter["current_class_level"] == 3
        assert preview_fighter["next_class_level"] == 4
        assert preview_fighter["feat"]["needs_feat"] is True

    def test_fighter_2_to_3_with_subclass_choice(self):
        choices = {
            "class": "Fighter",
            "level": 2,
            "classes": [{"class_name": "Fighter", "level": 2}],
            "ability_scores": {"Strength": 16, "Constitution": 14},
        }
        # Without subclass selected yet: needs_subclass is True, no subclass choices yet
        preview_no_sub = build_level_up_preview(choices)
        assert preview_no_sub["subclass"]["needs_subclass"] is True
        assert len(preview_no_sub["choices_needed"]) == 0

        # With Battle Master selected: needs_subclass stays True so UI card is selected,
        # and choices_needed contains maneuvers and student of war choices!
        preview_sub = build_level_up_preview(choices, subclass_to_level="Battle Master")
        assert preview_sub["subclass"]["needs_subclass"] is True
        assert preview_sub["subclass"]["selected_subclass"] == "Battle Master"

        feat_names = [f["name"] for f in preview_sub["features_gained"]]
        assert "Combat Superiority" in feat_names
        assert "Student of War" in feat_names

        choice_keys = [c.get("choices_made_key") or c.get("choice_key") for c in preview_sub["choices_needed"]]
        assert "maneuvers" in choice_keys
        assert "subclass_Student of War_artisan_tool" in choice_keys
        assert "subclass_Student of War_fighter_skill" in choice_keys


class TestLevelUpApiEndpoint:
    """Tests for POST /api/v1/character/level-up-preview route."""

    @pytest.fixture
    def client(self):
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_endpoint_level_up_preview_success(self, client):
        payload = {
            "choices_made": {
                "class": "Paladin",
                "level": 1,
                "ability_scores": {"Strength": 16, "Charisma": 14, "Constitution": 14},
            }
        }
        resp = client.post("/api/v1/character/level-up-preview", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "preview" in data
        preview = data["preview"]
        assert preview["class_name"] == "Paladin"
        assert preview["current_class_level"] == 1
        assert preview["next_class_level"] == 2
        assert preview["hp_increase"]["hit_die"] == 10

        # Paladin level 2 choices should include fighting_style
        choice_keys = [c.get("choice_key") or c.get("choices_made_key") for c in preview["choices_needed"]]
        assert "fighting_style" in choice_keys

    def test_endpoint_missing_choices_made(self, client):
        resp = client.post("/api/v1/character/level-up-preview", json={})
        assert resp.status_code == 400

    def test_endpoint_level_up_preview_with_class_to_level(self, client):
        payload = {
            "choices_made": {
                "classes": [
                    {"class_name": "Fighter", "level": 1},
                    {"class_name": "Rogue", "level": 1},
                ],
                "level": 2,
            },
            "class_to_level": "Rogue",
        }
        resp = client.post("/api/v1/character/level-up-preview", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["preview"]["class_name"] == "Rogue"
        feat_names = [f["name"] for f in data["preview"]["features_gained"]]
        assert "Cunning Action" in feat_names

    def test_endpoint_level_up_preview_with_subclass_to_level(self, client):
        payload = {
            "choices_made": {
                "class": "Fighter",
                "level": 2,
            },
            "subclass_to_level": "Battle Master",
        }
        resp = client.post("/api/v1/character/level-up-preview", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "preview" in data
        preview = data["preview"]
        assert preview["subclass"]["needs_subclass"] is True
        assert preview["subclass"]["selected_subclass"] == "Battle Master"

        choice_keys = [c.get("choices_made_key") or c.get("choice_key") for c in preview["choices_needed"]]
        assert "maneuvers" in choice_keys


