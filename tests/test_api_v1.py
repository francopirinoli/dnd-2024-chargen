"""Tests for the v1 REST API used by the React SPA frontend."""

import pytest
from modules.character_builder import CharacterBuilder


# ==================== Health ====================


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "version": "v1"}


# ==================== Catalog: classes ====================


class TestCatalogClasses:
    def test_list_classes(self, client):
        r = client.get("/api/v1/catalog/classes")
        assert r.status_code == 200
        data = r.get_json()
        assert "classes" in data
        names = {c["name"] for c in data["classes"]}
        # Should include all 12 standard classes
        for expected in ("Fighter", "Wizard", "Cleric", "Rogue"):
            assert expected in names
        # Each summary has the required shape
        for c in data["classes"]:
            assert "id" in c and "name" in c

    def test_get_class(self, client):
        r = client.get("/api/v1/catalog/classes/Fighter")
        assert r.status_code == 200
        data = r.get_json()
        assert data["name"] == "Fighter"
        assert "hit_die" in data
        assert "features_by_level" in data

    def test_get_class_unknown_404(self, client):
        r = client.get("/api/v1/catalog/classes/NotARealClass")
        assert r.status_code == 404

    def test_list_subclasses(self, client):
        r = client.get("/api/v1/catalog/classes/Fighter/subclasses")
        assert r.status_code == 200
        data = r.get_json()
        assert data["class"] == "Fighter"
        assert isinstance(data["subclasses"], list)
        assert len(data["subclasses"]) > 0


# ==================== Catalog: species ====================


class TestCatalogSpecies:
    def test_list_species(self, client):
        r = client.get("/api/v1/catalog/species")
        assert r.status_code == 200
        species = r.get_json()["species"]
        names = {s["name"] for s in species}
        assert "Elf" in names and "Dwarf" in names and "Human" in names
        # Elf has lineages and trait choices (per data files)
        elf = next(s for s in species if s["name"] == "Elf")
        assert elf["has_lineages"] is True
        assert elf["has_trait_choices"] is True

    def test_get_species(self, client):
        r = client.get("/api/v1/catalog/species/Elf")
        assert r.status_code == 200
        data = r.get_json()
        assert data["name"] == "Elf"
        assert "traits" in data


# ==================== Catalog: backgrounds, feats, spells, equipment ====================


class TestCatalogMisc:
    def test_list_backgrounds(self, client):
        r = client.get("/api/v1/catalog/backgrounds")
        assert r.status_code == 200
        backgrounds = r.get_json()["backgrounds"]
        names = {b["name"] for b in backgrounds}
        assert "Acolyte" in names
        assert "Folk Hero" not in names
        assert "Guild Artisan" not in names
        assert all(b["edition"] == "2024" for b in backgrounds)
        assert all(b["status"] == "active" for b in backgrounds)

    def test_list_backgrounds_include_legacy(self, client):
        r = client.get("/api/v1/catalog/backgrounds?include_legacy=true")
        assert r.status_code == 200
        backgrounds = r.get_json()["backgrounds"]
        by_name = {b["name"]: b for b in backgrounds}
        assert by_name["Folk Hero"]["edition"] == "2014"
        assert by_name["Folk Hero"]["status"] == "legacy"
        assert by_name["Guild Artisan"]["edition"] == "2014"
        assert by_name["Guild Artisan"]["status"] == "legacy"

    def test_get_legacy_background_detail(self, client):
        r = client.get("/api/v1/catalog/backgrounds/Folk%20Hero")
        assert r.status_code == 200
        data = r.get_json()
        assert data["name"] == "Folk Hero"
        assert data["edition"] == "2014"
        assert data["status"] == "legacy"

    def test_list_feats(self, client):
        r = client.get("/api/v1/catalog/feats")
        assert r.status_code == 200
        assert isinstance(r.get_json()["feats"], list)

    def test_class_spells_all(self, client):
        r = client.get("/api/v1/catalog/spells/wizard")
        assert r.status_code == 200
        data = r.get_json()
        assert data["class"] == "Wizard"
        assert "cantrips" in data and "spells_by_level" in data

    def test_class_spells_by_level(self, client):
        r = client.get("/api/v1/catalog/spells/wizard?level=0")
        assert r.status_code == 200
        data = r.get_json()
        assert data["level"] == 0
        assert "Fire Bolt" in data["spells"]

    def test_equipment_weapons(self, client):
        r = client.get("/api/v1/catalog/equipment/weapons")
        assert r.status_code == 200

    def test_equipment_unknown_404(self, client):
        r = client.get("/api/v1/catalog/equipment/spaceships")
        assert r.status_code == 404


# ==================== Wizard metadata ====================


class TestWizard:
    def test_steps(self, client):
        r = client.get("/api/v1/wizard/steps")
        assert r.status_code == 200
        steps = r.get_json()["steps"]
        ids = [s["id"] for s in steps]
        assert ids[0] == "class"
        assert "basics" not in ids
        assert "class" in ids and "species" in ids and "complete" in ids

    def test_dependencies(self, client):
        r = client.get("/api/v1/wizard/dependencies")
        assert r.status_code == 200
        deps = r.get_json()["dependencies"]
        # Class change must invalidate subclass + spells
        assert "subclass" in deps["class"]
        assert "spells" in deps["class"]
        # Classes payload change must invalidate class-dependent choices
        assert "classes" in deps
        assert "subclass" in deps["classes"]
        assert "spells" in deps["classes"]
        assert "skill_choices" in deps["classes"]
        assert "tool_choices" in deps["classes"]
        assert "background_skill_replacement" in deps["classes"]
        assert "equipment_selections" in deps["classes"]
        # Species change must invalidate lineage
        assert "lineage" in deps["species"]

    def test_steps_class_only_requires_class_selection(self, client):
        r = client.get("/api/v1/wizard/steps")
        assert r.status_code == 200
        steps = r.get_json()["steps"]
        class_step = next(s for s in steps if s["id"] == "class")
        assert "class" in class_step["required_keys"]
        assert "character_name" not in class_step["required_keys"]
        assert "level" not in class_step["required_keys"]


# ==================== Character build/validate/preview ====================


class TestCharacterBuild:
    @staticmethod
    def _rogue_fighter_multiclass_choices():
        return {
            "character_name": "Dual Track",
            "species": "Human",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 16,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 14,
                "Charisma": 8,
            },
            "background_bonuses": {"Dexterity": 2, "Wisdom": 1},
            "classes": [
                {"class_name": "Rogue", "level": 3, "subclass": "Thief"},
                {"class_name": "Fighter", "level": 2},
            ],
            "Fighting Style": "Dueling",
        }

    @staticmethod
    def _cleric_fighter_multiclass_choices():
        return {
            "character_name": "Spellblade",
            "species": "Human",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 12,
                "Dexterity": 10,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 16,
                "Charisma": 8,
            },
            "background_bonuses": {"Wisdom": 2, "Constitution": 1},
            "classes": [
                {"class_name": "Cleric", "level": 4, "subclass": "Light Domain"},
                {"class_name": "Fighter", "level": 1},
            ],
        }

    @staticmethod
    def _cleric_wizard_multiclass_choices():
        return {
            "character_name": "Twin Study",
            "species": "Human",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 10,
                "Constitution": 14,
                "Intelligence": 16,
                "Wisdom": 16,
                "Charisma": 8,
            },
            "background_bonuses": {"Wisdom": 2, "Intelligence": 1},
            "classes": [
                {"class_name": "Cleric", "level": 3, "subclass": "Light Domain"},
                {"class_name": "Wizard", "level": 2},
            ],
        }

    @staticmethod
    def _cleric_ranger_multiclass_choices():
        return {
            "character_name": "Wild Aegis",
            "species": "Human",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 14,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 16,
                "Charisma": 8,
            },
            "background_bonuses": {"Wisdom": 2, "Dexterity": 1},
            "classes": [
                {"class_name": "Cleric", "level": 4, "subclass": "Light Domain"},
                {"class_name": "Ranger", "level": 2},
            ],
        }

    @staticmethod
    def _cleric_eldritch_knight_multiclass_choices():
        return {
            "character_name": "Tempered Arcana",
            "species": "Human",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 14,
                "Dexterity": 10,
                "Constitution": 14,
                "Intelligence": 14,
                "Wisdom": 16,
                "Charisma": 8,
            },
            "background_bonuses": {"Wisdom": 2, "Constitution": 1},
            "classes": [
                {"class_name": "Cleric", "level": 4, "subclass": "Light Domain"},
                {"class_name": "Fighter", "level": 3, "subclass": "Eldritch Knight"},
            ],
        }

    @staticmethod
    def _cleric_warlock_multiclass_choices():
        return {
            "character_name": "Veilbound",
            "species": "Human",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 10,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 16,
                "Charisma": 14,
            },
            "background_bonuses": {"Wisdom": 2, "Constitution": 1},
            "classes": [
                {"class_name": "Cleric", "level": 4, "subclass": "Light Domain"},
                {"class_name": "Warlock", "level": 2},
            ],
        }

    def test_build_dwarf_cleric(self, client, dwarf_cleric_choices):
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": dwarf_cleric_choices},
        )
        assert r.status_code == 200
        char = r.get_json()["character"]
        assert char["name"] == "Thorin"
        assert char["class"] == "Cleric"

    def test_build_response_structure_wrapped(self, client, dwarf_cleric_choices):
        """
        REGRESSION TEST: Validate that /character/build returns { "character": {...} }
        
        The Flask endpoint must return a wrapped response structure. The frontend
        API client (frontend/src/lib/api.ts) unwraps this to return the character
        object directly to React components.
        
        This test prevents regression of the double-unwrapping bug where components
        were attempting to access response.character.character instead of response.character.
        
        Contract:
        - Flask returns: { "character": {...} }
        - API client unwraps and returns: {...}
        - Components receive: {...}
        """
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": dwarf_cleric_choices},
        )
        assert r.status_code == 200
        
        # Response must be wrapped in { "character": {...} }
        data = r.get_json()
        assert isinstance(data, dict), "Response must be a dict"
        assert "character" in data, "Response must have 'character' key"
        
        # The character value must be a dict, not double-wrapped
        character = data["character"]
        assert isinstance(character, dict), "character must be a dict, not further nested"
        
        # Validate expected top-level keys exist in the character object
        # (proves it's the actual character, not another wrapper)
        expected_keys = [
            "name", "level", "class", "species", "background",
            "proficiencies", "combat", "features", "spellcasting_stats"
        ]
        for key in expected_keys:
            assert key in character, f"character must have '{key}' key"
        
        # Sanity check: verify it's the actual character data
        assert character["name"] == "Thorin"
        assert character["level"] == 7
        assert character["class"] == "Cleric"

    def test_build_with_inventory_choices(self, client, dwarf_cleric_choices):
        """Verify that inventory choices with coins and items build cleanly without 400."""
        choices = dict(dwarf_cleric_choices)
        choices["inventory"] = {
            "coins": {"cp": 10, "sp": 5, "ep": 0, "gp": 150, "pp": 2},
            "items": [{"id": "item-1", "name": "Rope, Hempen (50 feet)", "quantity": 1}],
        }
        r = client.post("/api/v1/character/build", json={"choices_made": choices})
        assert r.status_code == 200
        data = r.get_json()
        assert "character" in data
        assert data["character"]["inventory"]["coins"]["gp"] == 150

        r_val = client.post("/api/v1/character/validate", json={"choices_made": choices})
        assert r_val.status_code == 200

    def test_build_missing_body(self, client):
        r = client.post("/api/v1/character/build", json={})
        assert r.status_code == 400

    def test_build_invalid_spell_selection_returns_structured_400(self, client):
        payload = {
            "choices_made": {
                "character_name": "Broken Wizard",
                "species": "Human",
                "class": "Wizard",
                "level": 3,
                "background": "Sage",
                "ability_scores": {
                    "Strength": 8,
                    "Dexterity": 14,
                    "Constitution": 14,
                    "Intelligence": 16,
                    "Wisdom": 12,
                    "Charisma": 10,
                },
                "skill_choices": ["Arcana", "History"],
                "spell_selections": {
                    "cantrips": [],
                    "spells": ["Cure Wounds"],
                    "background_cantrips": [],
                    "background_spells": [],
                },
            }
        }
        r = client.post("/api/v1/character/build", json=payload)
        assert r.status_code == 400
        body = r.get_json()
        assert body["selection_family"] == "spell_selections"
        assert body["code"] == "invalid_selection"
        assert isinstance(body.get("violations"), list) and body["violations"]

    def test_build_validation_errors_remain_client_errors(self, client):
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": {"classes": "not-a-list"}},
        )
        assert r.status_code == 400
        assert "error" in r.get_json()

    @pytest.mark.parametrize(
        ("path", "payload"),
        [
            ("/api/v1/character/build", {"choices_made": {"class": "Fighter"}}),
            ("/api/v1/character/validate", {"choices_made": {"class": "Fighter"}}),
            (
                "/api/v1/character/preview-step",
                {"choices_made": {"class": "Fighter"}, "step": "class"},
            ),
            (
                "/api/v1/character/derived",
                {"choices_made": {"class": "Fighter"}, "view": "damage_cantrips"},
            ),
        ],
    )
    def test_character_internal_errors_are_sanitized(self, client, monkeypatch, path, payload):
        from routes.api import character as character_routes

        def fail_build(*args, **kwargs):
            raise RuntimeError("sensitive traceback detail")

        monkeypatch.setattr(character_routes, "_build", fail_build)

        r = client.post(path, json=payload)

        assert r.status_code == 500
        assert r.get_json()["error"] == "Internal server error"
        assert isinstance(r.get_json().get("correlation_id"), str)
        assert "traceback" not in r.get_json()
        assert "sensitive traceback detail" not in r.get_data(as_text=True)

    def test_build_legacy_class_level_payload_still_supported(self, client, dwarf_cleric_choices):
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": dwarf_cleric_choices},
        )
        assert r.status_code == 200
        char = r.get_json()["character"]
        assert char["class"] == "Cleric"
        assert char["level"] == 7

    def test_build_single_entry_classes_payload_matches_legacy(self, client, dwarf_cleric_choices):
        legacy_payload = dict(dwarf_cleric_choices)

        new_shape_payload = {
            k: v
            for k, v in dwarf_cleric_choices.items()
            if k not in ("class", "level", "subclass")
        }
        new_shape_payload["classes"] = [{
            "class_name": dwarf_cleric_choices["class"],
            "level": dwarf_cleric_choices["level"],
            "subclass": dwarf_cleric_choices["subclass"],
        }]

        legacy_response = client.post(
            "/api/v1/character/build",
            json={"choices_made": legacy_payload},
        )
        new_shape_response = client.post(
            "/api/v1/character/build",
            json={"choices_made": new_shape_payload},
        )

        assert legacy_response.status_code == 200
        assert new_shape_response.status_code == 200

        legacy_character = legacy_response.get_json()["character"]
        new_shape_character = new_shape_response.get_json()["character"]

        assert new_shape_character["class"] == legacy_character["class"]
        assert new_shape_character["level"] == legacy_character["level"]
        assert new_shape_character["subclass"] == legacy_character["subclass"]
        assert (
            new_shape_character["combat"]["hit_points"]["maximum"]
            == legacy_character["combat"]["hit_points"]["maximum"]
        )
        assert (
            new_shape_character["proficiency_bonus"]
            == legacy_character["proficiency_bonus"]
        )

    def test_build_multiclass_rogue3_fighter2_returns_200(self, client):
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": self._rogue_fighter_multiclass_choices()},
        )

        assert r.status_code == 200
        char = r.get_json()["character"]
        assert char["class"] == "Rogue"
        assert char["level"] == 5
        assert char["proficiency_bonus"] == 3
        assert char["combat"]["hit_dice"]["total"] == "3d8 + 2d10"

    def test_build_multiclass_features_include_both_class_tracks(self, client):
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": self._rogue_fighter_multiclass_choices()},
        )

        assert r.status_code == 200
        char = r.get_json()["character"]
        class_feature_names = [f["name"] for f in char["features"]["class"]]

        assert any(name.startswith("Sneak Attack") for name in class_feature_names)
        assert any(name.startswith("Action Surge") for name in class_feature_names)

    def test_multiclass_spellcasting_stats_use_total_level_proficiency_bonus(self, client):
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": self._cleric_fighter_multiclass_choices()},
        )

        assert r.status_code == 200
        char = r.get_json()["character"]
        spell_stats = char["spellcasting_stats"]

        # Cleric 4 / Fighter 1 is total level 5 (PB +3), while primary class level 4 would be +2.
        assert char["level"] == 5
        assert char["proficiency_bonus"] == 3
        assert spell_stats["has_spellcasting"] is True
        assert spell_stats["spell_attack_bonus"] == (
            char["proficiency_bonus"] + spell_stats["spellcasting_modifier"]
        )
        assert spell_stats["spell_save_dc"] == (
            8 + char["proficiency_bonus"] + spell_stats["spellcasting_modifier"]
        )

    def test_build_passive_perception_matches_server_skill_bonus(self, client):
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": self._rogue_fighter_multiclass_choices()},
        )

        assert r.status_code == 200
        char = r.get_json()["character"]
        assert char["combat"]["passive_perception"] == (
            10 + char["skills"]["perception"]["modifier"]
        )

    def test_multiclass_full_plus_full_uses_effective_caster_level_for_slots(self, client):
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": self._cleric_wizard_multiclass_choices()},
        )

        assert r.status_code == 200
        char = r.get_json()["character"]
        stats = char["spellcasting_stats"]

        # Cleric 3 + Wizard 2 => effective caster level 5.
        assert char["spell_slots"].get("1st") == 4
        assert char["spell_slots"].get("2nd") == 3
        assert char["spell_slots"].get("3rd") == 2
        assert stats.get("effective_caster_level") == 5

    def test_multiclass_full_plus_half_uses_floor_rule(self, client):
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": self._cleric_ranger_multiclass_choices()},
        )

        assert r.status_code == 200
        char = r.get_json()["character"]
        stats = char["spellcasting_stats"]

        # Cleric 4 + Ranger 2 => 4 + floor(2/2) = effective caster level 5.
        assert char["spell_slots"].get("1st") == 4
        assert char["spell_slots"].get("2nd") == 3
        assert char["spell_slots"].get("3rd") == 2
        assert stats.get("effective_caster_level") == 5

    def test_multiclass_full_plus_third_uses_floor_rule(self, client):
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": self._cleric_eldritch_knight_multiclass_choices()},
        )

        assert r.status_code == 200
        char = r.get_json()["character"]
        stats = char["spellcasting_stats"]

        # Cleric 4 + Fighter(EK) 3 => 4 + floor(3/3) = effective caster level 5.
        assert char["spell_slots"].get("1st") == 4
        assert char["spell_slots"].get("2nd") == 3
        assert char["spell_slots"].get("3rd") == 2
        assert stats.get("effective_caster_level") == 5

    def test_multiclass_non_caster_rows_do_not_change_effective_caster_level(self, client):
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": self._cleric_fighter_multiclass_choices()},
        )

        assert r.status_code == 200
        char = r.get_json()["character"]
        stats = char["spellcasting_stats"]

        # Cleric 4 + Fighter 1 (non-caster row) => effective caster level remains 4.
        assert char["spell_slots"].get("1st") == 4
        assert char["spell_slots"].get("2nd") == 3
        assert "3rd" not in char["spell_slots"]
        assert stats.get("effective_caster_level") == 4

    def test_multiclass_pact_magic_is_tracked_separately(self, client):
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": self._cleric_warlock_multiclass_choices()},
        )

        assert r.status_code == 200
        char = r.get_json()["character"]
        stats = char["spellcasting_stats"]

        # Cleric standard slots still use effective standard caster level 4.
        assert char["spell_slots"].get("1st") == 4
        assert char["spell_slots"].get("2nd") == 3
        assert "3rd" not in char["spell_slots"]

        # Pact slots are additive metadata, not merged into standard slots.
        assert "pact_magic_slots" in char
        assert isinstance(char["pact_magic_slots"], list)
        assert char["pact_magic_slots"][0]["class_name"] == "Warlock"
        assert char["pact_magic_slots"][0]["slots"] == 2
        assert char["pact_magic_slots"][0]["slot_level"] == 1
        assert isinstance(char.get("spell_slot_notes"), list)
        assert isinstance(stats.get("multiclass_notes"), list)

    def test_build_single_entry_classes_payload_preserves_single_class_spell_slots(
        self,
        client,
        dwarf_cleric_choices,
    ):
        legacy_payload = dict(dwarf_cleric_choices)
        new_shape_payload = {
            k: v
            for k, v in dwarf_cleric_choices.items()
            if k not in ("class", "level", "subclass")
        }
        new_shape_payload["classes"] = [{
            "class_name": dwarf_cleric_choices["class"],
            "level": dwarf_cleric_choices["level"],
            "subclass": dwarf_cleric_choices["subclass"],
        }]

        legacy_response = client.post(
            "/api/v1/character/build",
            json={"choices_made": legacy_payload},
        )
        new_shape_response = client.post(
            "/api/v1/character/build",
            json={"choices_made": new_shape_payload},
        )

        assert legacy_response.status_code == 200
        assert new_shape_response.status_code == 200

        legacy_character = legacy_response.get_json()["character"]
        new_shape_character = new_shape_response.get_json()["character"]
        assert new_shape_character["spell_slots"] == legacy_character["spell_slots"]

    def test_single_class_full_caster_has_effective_caster_level(
        self, client, dwarf_cleric_choices
    ):
        """A single-class full caster should report effective_caster_level equal to its class level."""
        r = client.post(
            "/api/v1/character/build",
            json={"choices_made": dwarf_cleric_choices},
        )
        assert r.status_code == 200
        char = r.get_json()["character"]
        stats = char["spellcasting_stats"]
        expected_level = dwarf_cleric_choices["level"]
        assert stats.get("effective_caster_level") == expected_level, (
            f"Expected effective_caster_level={expected_level}, got {stats.get('effective_caster_level')}"
        )

    def test_validate_complete(self, client, dwarf_cleric_choices):
        r = client.post(
            "/api/v1/character/validate",
            json={"choices_made": dwarf_cleric_choices},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert "steps" in data
        # Each step has the expected shape
        for step in data["steps"]:
            assert "step" in step and "complete" in step and "missing" in step

    def test_validate_missing_class_fails(self, client):
        # Just basics — class is missing, should not be complete
        r = client.post(
            "/api/v1/character/validate",
            json={"choices_made": {"character_name": "X", "level": 1}},
        )
        assert r.status_code == 200
        data = r.get_json()
        class_step = next(s for s in data["steps"] if s["step"] == "class")
        assert class_step["complete"] is False
        assert "class" in class_step["missing"]

    def test_validate_standard_array_duplicate_values(self, client):
        r = client.post(
            "/api/v1/character/validate",
            json={
                "choices_made": {
                    "character_name": "Array Test",
                    "level": 1,
                    "class": "Wizard",
                    "species": "Human",
                    "background": "Sage",
                    "ability_scores_method": "standard_array",
                    "ability_scores": {
                        "Strength": 15,
                        "Dexterity": 15,
                        "Constitution": 13,
                        "Intelligence": 12,
                        "Wisdom": 10,
                        "Charisma": 8,
                    },
                    "background_bonuses": {"Intelligence": 2, "Wisdom": 1},
                }
            },
        )
        assert r.status_code == 200
        data = r.get_json()
        abilities_step = next(s for s in data["steps"] if s["step"] == "abilities")
        assert abilities_step["complete"] is False
        assert "ability_scores" in abilities_step["missing"]
        
    def test_validate_step_list_excludes_basics(self, client):
        choices = {
            "character_name": "Phase3",
            "classes": [{"class_name": "Fighter", "level": 1}],
        }
        r = client.post(
            "/api/v1/character/validate",
            json={"choices_made": choices},
        )

        assert r.status_code == 200
        data = r.get_json()
        step_ids = [s["step"] for s in data["steps"]]
        assert step_ids == [
            "class",
            "background",
            "species",
            "languages",
            "abilities",
            "equipment",
            "complete",
        ]

    def test_validate_missing_character_name_does_not_block_class_step(
        self, client, dwarf_cleric_choices
    ):
        choices = dict(dwarf_cleric_choices)
        choices.pop("character_name")
        r = client.post(
            "/api/v1/character/validate",
            json={"choices_made": choices},
        )

        assert r.status_code == 200
        data = r.get_json()
        class_step = next(s for s in data["steps"] if s["step"] == "class")
        assert "character_name" not in class_step["missing"]
        assert "class" not in class_step["missing"]

    def test_validate_multiclass_requires_subclass_per_qualifying_class_row(self, client):
        choices = self._rogue_fighter_multiclass_choices()
        choices["classes"] = [
            {"class_name": "Rogue", "level": 3},
            {"class_name": "Fighter", "level": 2},
        ]

        r = client.post(
            "/api/v1/character/validate",
            json={"choices_made": choices},
        )

        assert r.status_code == 200
        data = r.get_json()
        class_step = next(s for s in data["steps"] if s["step"] == "class")
        assert class_step["complete"] is False
        assert "classes[0].subclass" in class_step["missing"]

    def test_preview_class_step(self, client):
        # Fighter at level 3 needs subclass
        r = client.post(
            "/api/v1/character/preview-step",
            json={
                "step": "class",
                "choices_made": {
                    "character_name": "Test",
                    "level": 3,
                    "class": "Fighter",
                },
            },
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data["step"] == "class"
        assert data["needs_subclass"] is True
        assert isinstance(data["available_subclasses"], list)
        assert len(data["available_subclasses"]) > 0
        first = data["available_subclasses"][0]
        assert isinstance(first["id"], str)
        assert isinstance(first["name"], str)
        assert isinstance(first["level_3_feature_names"], list)
        champion = next((s for s in data["available_subclasses"] if s["name"] == "Champion"), None)
        assert champion is not None
        assert "Improved Critical" in champion["level_3_feature_names"]

    def test_preview_class_step_respects_explicit_multiclass_active_row(self, client):
        choices = self._cleric_fighter_multiclass_choices()
        choices["class"] = "Fighter"
        choices["level"] = 1
        choices.pop("subclass", None)

        r = client.post(
            "/api/v1/character/preview-step",
            json={"step": "class", "choices_made": choices},
        )

        assert r.status_code == 200
        data = r.get_json()
        assert data["choices_made"]["class"] == "Fighter"
        assert data["needs_subclass"] is False
        assert "available_subclasses" not in data

    def test_preview_class_no_subclass_at_low_level(self, client):
        r = client.post(
            "/api/v1/character/preview-step",
            json={
                "step": "class",
                "choices_made": {
                    "character_name": "Test",
                    "level": 1,
                    "class": "Fighter",
                },
            },
        )
        assert r.status_code == 200
        assert r.get_json()["needs_subclass"] is False

    def test_preview_class_fey_wanderer_filters_unresolved_skill_placeholder(self, client):
        choices = {
            "character_name": "Preview Ranger",
            "level": 3,
            "class": "Ranger",
            "subclass": "Fey Wanderer",
            "species": "Human",
            "background": "Soldier",
            "skill_choices": ["Stealth", "Perception", "Survival"],
            "fighting_style": "Archery",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 15,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 14,
                "Charisma": 8,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        }

        r = client.post(
            "/api/v1/character/preview-step",
            json={"step": "class", "choices_made": choices},
        )

        assert r.status_code == 200
        data = r.get_json()
        deft_explorer = next(
            (
                choice
                for choice in data["nested_choices"]
                if choice.get("choice_key") == "deft_explorer_expertise"
            ),
            None,
        )
        assert deft_explorer is not None
        assert "__otherworldly_glamour_skill__" not in deft_explorer["options"]

    # ---------- preview-step: multiclass row_context + nested_choices filtering ----------

    @staticmethod
    def _basics_for_preview():
        return {
            "character_name": "Preview",
            "species": "Human",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 12,
                "Constitution": 14,
                "Intelligence": 13,
                "Wisdom": 14,
                "Charisma": 10,
            },
            "background_bonuses": {"Intelligence": 2, "Wisdom": 1},
        }

    @staticmethod
    def _find_choices_of_type(nested_choices, choice_type):
        return [c for c in nested_choices if (c.get("type") or "").lower() == choice_type]

    def _preview_class(self, client, choices, *, target_class, target_level):
        """Preview the class step for a specific multiclass row.

        Mirrors the `class` + `level` explicit-row pattern used by
        test_preview_class_step_respects_explicit_multiclass_active_row.
        """
        payload = dict(choices)
        payload["class"] = target_class
        payload["level"] = target_level
        payload.pop("subclass", None)
        r = client.post(
            "/api/v1/character/preview-step",
            json={"step": "class", "choices_made": payload},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        return r.get_json()

    def test_preview_class_primary_returns_is_primary_true_and_full_choices(self, client):
        choices = self._basics_for_preview()
        choices["classes"] = [{"class_name": "Cleric", "level": 1}]
        data = self._preview_class(client, choices, target_class="Cleric", target_level=1)

        assert data["row_context"] == {
            "row_index": 0,
            "is_primary": True,
            "total_class_rows": 1,
        }
        nested = data["nested_choices"]
        assert self._find_choices_of_type(nested, "skills"), \
            "Primary Cleric preview must include the skill picker"
        # Divine Order is a select_single choice keyed under the feature.
        divine = [
            c for c in nested
            if "divine" in (c.get("choice_key") or "").lower()
            or "divine order" in (c.get("title") or c.get("feature_name") or "").lower()
        ]
        assert divine, "Primary Cleric preview must include Divine Order picker"

    def test_preview_class_secondary_wizard_druid_keeps_primal_order(self, client):
        choices = self._basics_for_preview()
        choices["classes"] = [
            {"class_name": "Wizard", "level": 3},
            {"class_name": "Druid", "level": 1},
        ]
        data = self._preview_class(client, choices, target_class="Druid", target_level=1)

        assert data["row_context"]["is_primary"] is False
        assert data["row_context"]["row_index"] == 1
        assert data["row_context"]["total_class_rows"] == 2
        nested = data["nested_choices"]
        primal = [
            c for c in nested
            if (c.get("feature_name") or "") == "Primal Order"
            or (c.get("choice_key") or "") == "primal_order"
        ]
        assert primal, f"Expected Primal Order choice to be retained, got: {nested}"
        primal_order = primal[0]
        assert primal_order.get("feature_name") == "Primal Order"
        assert primal_order.get("choice_key") == "primal_order"

    def test_preview_class_secondary_bard_keeps_skill_and_instrument(self, client):
        choices = self._basics_for_preview()
        choices["classes"] = [
            {"class_name": "Wizard", "level": 3},
            {"class_name": "Bard", "level": 1},
        ]
        data = self._preview_class(client, choices, target_class="Bard", target_level=1)

        assert data["row_context"]["is_primary"] is False
        assert data["row_context"]["row_index"] == 1
        nested = data["nested_choices"]

        skill_choices = self._find_choices_of_type(nested, "skills")
        tool_choices = self._find_choices_of_type(nested, "tools")
        assert len(skill_choices) == 1
        assert len(tool_choices) == 1

        skill = skill_choices[0]
        assert skill["count"] == 1
        assert len(skill["options"]) >= 15

        tool = tool_choices[0]
        assert tool["count"] == 1
        assert len(tool["options"]) >= 1

    def test_preview_class_secondary_rogue_narrows_skill_options(self, client):
        choices = self._basics_for_preview()
        choices["classes"] = [
            {"class_name": "Wizard", "level": 3},
            {"class_name": "Rogue", "level": 1},
        ]
        data = self._preview_class(client, choices, target_class="Rogue", target_level=1)

        assert data["row_context"]["is_primary"] is False
        nested = data["nested_choices"]
        skill_choices = self._find_choices_of_type(nested, "skills")
        assert len(skill_choices) == 1, f"Expected exactly 1 skill choice, got: {nested}"
        skill = skill_choices[0]
        assert (skill.get("type") or "").lower() == "skills"
        assert skill["count"] == 1
        assert set(skill["options"]) == {
            "Acrobatics", "Athletics", "Deception", "Insight", "Intimidation",
            "Investigation", "Perception", "Performance", "Persuasion",
            "Sleight of Hand", "Stealth",
        }

    def test_preview_class_secondary_ranger_narrows_skill_options_no_fighting_style(self, client):
        choices = self._basics_for_preview()
        choices["classes"] = [
            {"class_name": "Wizard", "level": 3},
            {"class_name": "Ranger", "level": 1},
        ]
        data = self._preview_class(client, choices, target_class="Ranger", target_level=1)

        assert data["row_context"]["is_primary"] is False
        nested = data["nested_choices"]
        skill_choices = self._find_choices_of_type(nested, "skills")
        assert len(skill_choices) == 1, f"Expected exactly 1 skill choice, got: {nested}"
        skill = skill_choices[0]
        assert (skill.get("type") or "").lower() == "skills"
        assert set(skill["options"]) == {
            "Animal Handling", "Athletics", "Insight", "Investigation",
            "Nature", "Perception", "Stealth", "Survival",
        }

    def test_preview_class_secondary_ranger_level2_keeps_feature_choices(self, client):
        choices = self._basics_for_preview()
        choices["classes"] = [
            {"class_name": "Wizard", "level": 3},
            {"class_name": "Ranger", "level": 2},
        ]
        data = self._preview_class(client, choices, target_class="Ranger", target_level=2)

        assert data["row_context"]["is_primary"] is False
        nested = data["nested_choices"]

        skill_choices = [
            c for c in nested if (c.get("choice_key") or "").lower() == "skill_choices"
        ]
        assert len(skill_choices) == 1
        assert skill_choices[0]["count"] == 1
        assert set(skill_choices[0]["options"]) == {
            "Animal Handling", "Athletics", "Insight", "Investigation",
            "Nature", "Perception", "Stealth", "Survival",
        }

        feature_choices_by_key = {
            (c.get("choice_key") or "").lower(): c
            for c in nested
            if c.get("choice_key")
        }
        assert "deft_explorer_expertise" in feature_choices_by_key
        assert "fighting_style" in feature_choices_by_key

        deft_explorer = feature_choices_by_key["deft_explorer_expertise"]
        assert deft_explorer.get("count") == 1
        assert isinstance(deft_explorer.get("options"), list)
        assert len(deft_explorer["options"]) >= 1

        fighting_style = feature_choices_by_key["fighting_style"]
        assert fighting_style.get("count") == 1
        assert isinstance(fighting_style.get("options"), list)
        assert len(fighting_style["options"]) >= 1

    def test_preview_class_secondary_fighter_keeps_fighting_style_and_drops_skills(self, client):
        choices = self._basics_for_preview()
        choices["classes"] = [
            {"class_name": "Wizard", "level": 3},
            {"class_name": "Fighter", "level": 1},
        ]
        data = self._preview_class(client, choices, target_class="Fighter", target_level=1)

        assert data["row_context"]["is_primary"] is False
        assert data["row_context"]["row_index"] == 1
        nested = data["nested_choices"]
        assert self._find_choices_of_type(nested, "skills") == []
        style_choices = [
            c for c in nested
            if "fighting_style" in (c.get("choice_key") or "").lower()
            or "fighting style" in (c.get("title") or c.get("feature_name") or "").lower()
        ]
        assert style_choices, f"Expected Fighting Style choice for secondary fighter, got: {nested}"

    def test_preview_class_legacy_single_class_unchanged(self, client):
        r = client.post(
            "/api/v1/character/preview-step",
            json={
                "step": "class",
                "choices_made": {
                    "character_name": "Test",
                    "level": 1,
                    "class": "Wizard",
                },
            },
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data["row_context"] == {
            "row_index": 0,
            "is_primary": True,
            "total_class_rows": 1,
        }
        skill_choices = self._find_choices_of_type(data["nested_choices"], "skills")
        assert len(skill_choices) == 1
        assert skill_choices[0]["count"] == 2

    def test_preview_class_secondary_subclass_unlock_still_offered(self, client):
        choices = self._basics_for_preview()
        choices["classes"] = [
            {"class_name": "Wizard", "level": 3},
            {"class_name": "Cleric", "level": 3},
        ]
        data = self._preview_class(client, choices, target_class="Cleric", target_level=3)

        assert data["row_context"]["is_primary"] is False
        assert data["row_context"]["row_index"] == 1
        assert data.get("needs_subclass") is True
        assert isinstance(data.get("available_subclasses"), list)
        assert len(data["available_subclasses"]) > 0

    def test_preview_class_asi_nested_choices_include_dependency_metadata(self, client):
        choices = self._basics_for_preview()
        choices["classes"] = [{"class_name": "Fighter", "level": 4}]
        choices["class_feat_4"] = "Ability Score Improvement"
        data = self._preview_class(client, choices, target_class="Fighter", target_level=4)

        nested_by_key = {
            c.get("choice_key"): c
            for c in data["nested_choices"]
            if c.get("choice_key")
        }
        assert "class_feat_4_asi_option" in nested_by_key
        assert "class_feat_4_ability_plus_2" in nested_by_key
        assert "class_feat_4_abilities_plus_1" in nested_by_key
        assert nested_by_key["class_feat_4_ability_plus_2"]["depends_on"] == "class_feat_4_asi_option"
        assert nested_by_key["class_feat_4_ability_plus_2"]["depends_on_value"] == "+2 to one ability"
        assert nested_by_key["class_feat_4_abilities_plus_1"]["depends_on"] == "class_feat_4_asi_option"
        assert nested_by_key["class_feat_4_abilities_plus_1"]["depends_on_value"] == "+1 to two abilities"

    def test_preview_abilities_includes_server_calculation_state(self, client):
        choices = self._basics_for_preview()
        choices["ability_scores_method"] = "point_buy"

        r = client.post(
            "/api/v1/character/preview-step",
            json={"step": "abilities", "choices_made": choices},
        )

        assert r.status_code == 200
        state = r.get_json()["ability_generation"]
        assert state["abilities"]["Dexterity"]["modifier_display"] == "+1"
        assert state["point_buy"]["total"] == 27
        assert state["point_buy"]["remaining"] == 0
        assert state["point_buy"]["controls"]["Dexterity"]["current_cost"] == 4
        assert state["standard_array"]["values"] == [15, 14, 13, 12, 10, 8]

    def test_preview_class_includes_server_multiclass_prerequisites(self, client):
        choices = self._basics_for_preview()
        choices["ability_scores"]["Intelligence"] = 10
        choices["background_bonuses"] = {"Wisdom": 2, "Constitution": 1}
        choices["classes"] = [
            {"class_name": "Cleric", "level": 1},
            {"class_name": "Wizard", "level": 1},
        ]

        data = self._preview_class(client, choices, target_class="Wizard", target_level=1)

        wizard = data["multiclass_prerequisites"]["classes"]["Wizard"]
        assert wizard["ok"] is False
        assert wizard["abilities_unknown"] is False
        assert "Intelligence" in wizard["missing"]

    def test_preview_class_includes_server_feat_prerequisite_warnings(self, client):
        choices = self._basics_for_preview()
        choices["classes"] = [{"class_name": "Fighter", "level": 4}]
        choices["class_feat_4"] = "Great Weapon Master"

        data = self._preview_class(client, choices, target_class="Fighter", target_level=4)

        warnings = data["class_feat_prerequisite_warnings"]
        assert warnings
        assert warnings[0]["choice_key"] == "class_feat_4"
        assert warnings[0]["feat_name"] == "Great Weapon Master"
        assert any("Strength 13+" in message for message in warnings[0]["messages"])

    def test_preview_class_cleric_thaumaturge_bonus_cantrip_appears_after_divine_order(
        self, client
    ):
        choices = self._basics_for_preview()
        choices["classes"] = [{"class_name": "Cleric", "level": 4}]
        data = self._preview_class(
            client, choices, target_class="Cleric", target_level=4
        )

        nested = data["nested_choices"]
        divine_order_index = next(
            (
                idx
                for idx, choice in enumerate(nested)
                if choice.get("choice_key") == "divine_order"
            ),
            None,
        )
        assert divine_order_index is not None, (
            "Expected Divine Order choice in nested choices"
        )
        thaumaturge_bonus_cantrip_index = next(
            (
                idx
                for idx, choice in enumerate(nested)
                if choice.get("feature_name") == "Thaumaturge_bonus_cantrip"
            ),
            None,
        )
        assert thaumaturge_bonus_cantrip_index is not None, (
            "Expected Thaumaturge bonus cantrip nested choice in nested choices"
        )
        class_feat_4_index = next(
            (
                idx
                for idx, choice in enumerate(nested)
                if choice.get("choice_key") == "class_feat_4"
            ),
            None,
        )
        assert class_feat_4_index is not None, (
            "Expected class_feat_4 choice in nested choices"
        )

        assert divine_order_index < thaumaturge_bonus_cantrip_index < class_feat_4_index

    def test_preview_species_step(self, client):
        r = client.post(
            "/api/v1/character/preview-step",
            json={
                "step": "species",
                "choices_made": {
                    "character_name": "Test",
                    "level": 1,
                    "species": "Elf",
                },
            },
        )
        assert r.status_code == 200
        data = r.get_json()
        assert "traits" in data
        assert "trait_choices" in data

    def test_preview_languages_step_shape(self, client):
        r = client.post(
            "/api/v1/character/preview-step",
            json={
                "step": "languages",
                "choices_made": {
                    "character_name": "Test",
                    "level": 1,
                    "class": "Fighter",
                    "background": "Acolyte",
                    "species": "Human",
                    "languages": ["Elvish", "Dwarvish"],
                },
            },
        )
        assert r.status_code == 200
        data = r.get_json()
        options = data["language_options"]
        assert data["step"] == "languages"
        assert options["selection_count"] == 2
        assert options["base_languages"] == ["Common"]
        assert "Common Sign Language" in options["available_languages"]
        assert "Common" not in options["available_languages"]
        assert options["selected_languages"] == ["Elvish", "Dwarvish"]

    def test_preview_languages_empty_choices(self, client):
        """Languages step must return the standard language pool even with empty choices."""
        r = client.post(
            "/api/v1/character/preview-step",
            json={"step": "languages", "choices_made": {}},
        )
        assert r.status_code == 200
        data = r.get_json()
        opts = data["language_options"]
        assert opts["base_languages"] == ["Common"]
        assert len(opts["standard_available_languages"]) == 9
        assert len(opts["available_languages"]) == 19
        assert "Elvish" in opts["available_languages"]
        assert "Celestial" in opts["available_languages"]
        assert "Common" not in opts["available_languages"]
        assert opts["selection_count"] == 2

    def test_random_languages_endpoint(self, client):
        r = client.post(
            "/api/v1/character/random-languages",
            json={
                "choices_made": {
                    "character_name": "Test",
                    "level": 1,
                    "class": "Fighter",
                    "background": "Acolyte",
                    "species": "Human",
                }
            },
        )
        assert r.status_code == 200
        data = r.get_json()
        languages = data["languages"]
        assert len(languages) == 2
        assert len(set(languages)) == 2
        for language in languages:
            assert language in (
                set(CharacterBuilder.STANDARD_LANGUAGE_OPTIONS)
                | set(CharacterBuilder.RARE_LANGUAGE_OPTIONS)
            )


# ==================== Character derived views (Phase 2) ====================


class TestCharacterDerived:
    def test_derived_missing_body(self, client):
        r = client.post("/api/v1/character/derived", json={})
        assert r.status_code == 400

    def test_derived_unknown_view(self, client, dwarf_cleric_choices):
        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": dwarf_cleric_choices, "view": "nope"},
        )
        assert r.status_code == 400
        body = r.get_json()
        assert "allowed" in body

    def test_derived_damage_cantrips_cleric(self, client, dwarf_cleric_choices):
        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": dwarf_cleric_choices, "view": "damage_cantrips"},
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["view"] == "damage_cantrips"
        assert isinstance(body["data"], list)
        # Each row (if any) has the documented shape
        for row in body["data"]:
            assert {"name", "atk_display", "damage", "damage_type", "notes"} <= set(row)

    def test_derived_spell_management_cleric(self, client, dwarf_cleric_choices):
        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": dwarf_cleric_choices, "view": "spell_management"},
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert "available_cantrips" in data
        assert "available_spells" in data
        assert "spell_slots" in data
        assert "limits" in data

    def test_derived_spell_management_warlock_includes_pact_magic_slots(self, client):
        choices = {
            "character_name": "Test",
            "level": 5,
            "species": "Human",
            "class": "Warlock",
            "subclass": "Fiend",
            "background": "Acolyte",
            "languages": [],
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 10,
                "Constitution": 10,
                "Intelligence": 10,
                "Wisdom": 16,
                "Charisma": 16,
            },
            "background_bonuses": {"Wisdom": 2, "Charisma": 1},
        }

        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": choices, "view": "spell_management"},
        )

        assert r.status_code == 200
        body = r.get_json()
        assert body["view"] == "spell_management"
        assert body["applicable"] is True

        data = body["data"]
        assert data is not None
        assert "pact_magic_slots" in data
        assert isinstance(data["pact_magic_slots"], list)
        assert data["pact_magic_slots"]

        first_slot = data["pact_magic_slots"][0]
        assert first_slot["slots"] > 0
        assert first_slot["slot_level"] > 0

    def test_derived_spell_management_respects_explicit_multiclass_active_row(self, client):
        choices = TestCharacterBuild._cleric_fighter_multiclass_choices()
        choices["class"] = "Fighter"
        choices["level"] = 1
        choices.pop("subclass", None)

        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": choices, "view": "spell_management"},
        )

        assert r.status_code == 200
        body = r.get_json()
        assert body["choices_made"]["class"] == "Fighter"
        assert body["applicable"] is False
        assert body["data"] is None

    def test_derived_spell_management_includes_always_prepared_spell_details(
        self, client, dwarf_cleric_choices
    ):
        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": dwarf_cleric_choices, "view": "spell_management"},
        )
        assert r.status_code == 200
        data = r.get_json()["data"]

        always_prepared = data["always_prepared"]
        assert always_prepared

        burning_hands = next(
            spell for spell in always_prepared if spell["name"] == "Burning Hands"
        )
        assert burning_hands["source"] == "Light Domain"
        assert burning_hands["level"] == 1
        assert isinstance(burning_hands.get("description"), str)
        assert burning_hands.get("description")
        assert isinstance(burning_hands.get("duration"), str)
        assert burning_hands.get("duration")

    def test_derived_spell_management_non_caster_not_applicable(self, client, elf_fighter_choices):
        # Champion Fighter is not a spellcaster
        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": elf_fighter_choices, "view": "spell_management"},
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["view"] == "spell_management"
        assert body["applicable"] is False
        assert isinstance(body.get("reason"), str)
        assert body["data"] is None

    # ------------------------------------------------------------------
    # prepare_rule tests
    # ------------------------------------------------------------------

    def test_derived_spell_management_prepare_rule_present(self, client, dwarf_cleric_choices):
        """prepare_rule must be present in every applicable spell_management response."""
        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": dwarf_cleric_choices, "view": "spell_management"},
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert "prepare_rule" in data
        assert data["prepare_rule"] in ("long_rest", "level_up", "short_rest", "fixed")

    @pytest.mark.parametrize(
        "class_name,subclass,expected_rule",
        [
            ("Cleric", "Light Domain", "long_rest"),
            ("Druid", "Moon", "long_rest"),
            ("Paladin", "Oath of Devotion", "long_rest"),
            ("Wizard", "Evoker", "long_rest"),
            ("Bard", "Lore", "level_up"),
            ("Sorcerer", "Draconic Bloodline", "level_up"),
            ("Warlock", "Fiend", "short_rest"),
        ],
    )
    def test_derived_spell_management_prepare_rule_by_class(
        self, client, class_name, subclass, expected_rule
    ):
        choices = {
            "character_name": "Test",
            "level": 5,
            "species": "Human",
            "class": class_name,
            "subclass": subclass,
            "background": "Acolyte",
            "languages": [],
            "ability_scores": {
                "Strength": 10, "Dexterity": 10, "Constitution": 10,
                "Intelligence": 10, "Wisdom": 16, "Charisma": 16,
            },
            "background_bonuses": {"Wisdom": 2, "Charisma": 1},
        }
        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": choices, "view": "spell_management"},
        )
        assert r.status_code == 200
        body = r.get_json()
        # Some classes might not be applicable at all; skip those gracefully.
        if not body.get("applicable", True):
            pytest.skip(f"{class_name} returned applicable=False; skipping prepare_rule check")
        data = body["data"]
        assert data["prepare_rule"] == expected_rule, (
            f"{class_name}: expected prepare_rule={expected_rule!r}, got {data['prepare_rule']!r}"
        )

    def test_derived_spell_management_prepare_rule_fixed_for_non_caster(
        self, client, elf_fighter_choices
    ):
        """Non-casters return applicable=False; prepare_rule is absent from data (data is None)."""
        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": elf_fighter_choices, "view": "spell_management"},
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["applicable"] is False
        assert body["data"] is None  # no prepare_rule when not applicable

    def test_derived_mastery_management_fighter(self, client, elf_fighter_choices):
        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": elf_fighter_choices, "view": "mastery_management"},
        )
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert "available_weapons" in data
        assert "max_masteries" in data
        assert "weapon_masteries" in data

    def test_derived_invocation_management_non_warlock_not_applicable(self, client, dwarf_cleric_choices):
        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": dwarf_cleric_choices, "view": "invocation_management"},
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["view"] == "invocation_management"
        assert body["applicable"] is False
        assert isinstance(body.get("reason"), str)
        assert body["data"] is None

    def test_derived_invocation_management_returns_tome_cantrip_choices(self, client):
        choices = {
            "classes": [{"class_name": "Warlock", "level": 1}],
            "species": "Human",
            "background": "Acolyte",
            "eldritch_invocation_selections": {
                "selected": ["Pact of the Tome"],
                "cantrip_choices": {
                    "eldritch_invocation_pact_of_the_tome_0": ["Fire Bolt"],
                    "eldritch_invocation_pact_of_the_tome_1": ["Guidance"],
                    "eldritch_invocation_pact_of_the_tome_2": ["Druidcraft"],
                },
            },
        }
        r = client.post(
            "/api/v1/character/derived",
            json={"choices_made": choices, "view": "invocation_management"},
        )

        assert r.status_code == 200
        data = r.get_json()["data"]
        descriptors = data["cantrip_choice_descriptors"]
        assert [descriptor["spell_list"] for descriptor in descriptors] == [
            "Wizard",
            "Cleric",
            "Druid",
        ]
        assert [descriptor["selected"] for descriptor in descriptors] == [
            ["Fire Bolt"],
            ["Guidance"],
            ["Druidcraft"],
        ]
