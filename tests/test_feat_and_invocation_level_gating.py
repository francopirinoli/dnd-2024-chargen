"""Tests for level requirement enforcement on Feats (including Epic Boons) and Eldritch Invocations."""

import pytest
from modules.character_builder import CharacterBuilder, SelectionValidationError
from routes.api.character import _normalize_choices_for_builder


class TestFeatLevelGating:
    """Test level requirement validation on class_feat_* slots."""

    def test_class_feat_4_rejects_epic_boon(self):
        """At level 4, selecting Boon of Bloodshed (requires Level 19+) must be rejected."""
        builder = CharacterBuilder()
        builder.set_class("Fighter", 4)
        with pytest.raises(SelectionValidationError) as exc_info:
            builder.apply_choice("class_feat_4", "Boon of Bloodshed")
        assert exc_info.value.code == "prerequisite_level_not_met"
        assert exc_info.value.family == "class_feat"
        assert any("Boon of Bloodshed" in v.get("selection", "") for v in exc_info.value.violations)

    def test_class_feat_19_allows_epic_boon(self):
        """At level 19, selecting Boon of Bloodshed (requires Level 19+) must be allowed."""
        builder = CharacterBuilder()
        builder.set_class("Fighter", 19)
        applied = builder.apply_choice("class_feat_19", "Boon of Bloodshed")
        assert applied is True
        feats = builder.character_data["features"]["feats"]
        feat_names = [f["name"] for f in feats]
        assert "Boon of Bloodshed" in feat_names

    def test_class_feat_4_allows_level_4_general_feat(self):
        """At level 4, selecting Ability Score Improvement or Charger (requires level 4) must be allowed."""
        builder = CharacterBuilder()
        builder.set_class("Fighter", 4)
        applied = builder.apply_choice("class_feat_4", "Ability Score Improvement")
        assert applied is True

    def test_class_feat_4_allows_origin_feat(self):
        """At level 4, origin feats (no level requirement) must be allowed."""
        builder = CharacterBuilder()
        builder.set_class("Fighter", 4)
        applied = builder.apply_choice("class_feat_4", "Alert")
        assert applied is True

    def test_api_build_rejects_epic_boon_at_level_4(self, client):
        """POST /api/v1/character/build returns 400 when an Epic Boon is selected at level 4."""
        payload = {
            "choices_made": {
                "name": "Test Fighter",
                "species": "Human",
                "background": "Soldier",
                "class": "Fighter",
                "level": 4,
                "ability_scores": {
                    "Strength": 16,
                    "Dexterity": 14,
                    "Constitution": 14,
                    "Intelligence": 10,
                    "Wisdom": 12,
                    "Charisma": 8,
                },
                "class_feat_4": "Boon of Bloodshed",
            }
        }
        res = client.post("/api/v1/character/build", json=payload)
        assert res.status_code == 400
        data = res.get_json()
        assert data["code"] == "prerequisite_level_not_met" or data.get("error")


class TestEldritchInvocationLevelGating:
    """Test level requirement validation on Eldritch Invocations."""

    @pytest.mark.parametrize(
        "warlock_level,expected_max,should_contain,should_not_contain",
        [
            (1, 1, ["Armor of Shadows"], ["Devil's Sight", "Ascendant Step", "Witch Sight"]),
            (2, 3, ["Devil's Sight"], ["Ascendant Step", "Witch Sight"]),
            (4, 3, ["Devil's Sight", "Agonizing Blast"], ["Ascendant Step", "Witch Sight"]),
            (5, 5, ["Ascendant Step"], ["Witch Sight"]),
            (9, 7, ["Ascendant Step", "Whispers of the Grave"], ["Witch Sight"]),
            (15, 9, ["Witch Sight", "Ascendant Step"], []),
        ],
    )
    def test_calculate_eldritch_invocation_stats_by_level(
        self, warlock_level, expected_max, should_contain, should_not_contain
    ):
        """Verify available invocations and max count for Warlocks across various levels."""
        builder = CharacterBuilder()
        builder.set_class("Warlock", warlock_level)
        stats = builder.calculate_eldritch_invocation_stats()

        assert stats["has_invocations"] is True
        assert stats["max_invocations"] == expected_max
        available_names = {inv["name"] for inv in stats["available_invocations"]}

        for name in should_contain:
            assert name in available_names, f"Expected {name} to be available at level {warlock_level}"

        for name in should_not_contain:
            assert name not in available_names, f"Expected {name} to NOT be available at level {warlock_level}"

        # Ensure all returned invocations have prerequisite_level <= warlock_level
        for inv in stats["available_invocations"]:
            assert inv["prerequisite_level"] <= warlock_level

    def test_multiclass_warlock_invocation_stats(self):
        """Multiclass Fighter 10 / Warlock 2 has Warlock level 2 (max 3 invocations, max prereq level 2)."""
        builder = CharacterBuilder()
        builder.character_data["class"] = "Fighter"
        builder.character_data["level"] = 12
        builder.character_data["class_breakdown"] = [
            {"class_name": "Fighter", "level": 10},
            {"class_name": "Warlock", "level": 2},
        ]
        stats = builder.calculate_eldritch_invocation_stats()

        assert stats["has_invocations"] is True
        assert stats["max_invocations"] == 3
        available_names = {inv["name"] for inv in stats["available_invocations"]}
        assert "Devil's Sight" in available_names
        assert "Ascendant Step" not in available_names
        assert "Witch Sight" not in available_names

    def test_validate_eldritch_invocation_selections_rejects_ineligible_invocation(self):
        """Selecting Ascendant Step (requires level 5) on a Level 2 Warlock must be rejected."""
        builder = CharacterBuilder()
        builder.set_class("Warlock", 2)
        with pytest.raises(SelectionValidationError) as exc_info:
            builder._validate_eldritch_invocation_selections(["Ascendant Step"])
        assert exc_info.value.code == "invalid_selection"
        assert any(
            v.get("reason") == "prerequisite_level_not_met" for v in exc_info.value.violations
        )

    def test_validate_eldritch_invocation_selections_allows_eligible_invocation(self):
        """Selecting Devil's Sight (requires level 2) on a Level 2 Warlock must be accepted."""
        builder = CharacterBuilder()
        builder.set_class("Warlock", 2)
        validated = builder._validate_eldritch_invocation_selections(["Devil's Sight"])
        assert validated == ["Devil's Sight"]


class TestMulticlassNormalizationAndDerivedViews:
    """Test _normalize_choices_for_builder and derived view invocation_management."""

    def test_normalize_choices_preserves_explicit_class_level(self):
        """_normalize_choices_for_builder must resolve the explicit class level from class entries."""
        choices_made = {
            "classes": [
                {"class_name": "Fighter", "level": 10},
                {"class_name": "Warlock", "level": 2},
            ],
            "class": "Warlock",
            "level": 12,
        }
        normalized = _normalize_choices_for_builder(
            choices_made, preserve_explicit_class_context=True
        )
        assert normalized["class"] == "Warlock"
        assert normalized["level"] == 2
        assert len(normalized["classes"]) == 1
        assert normalized["classes"][0]["class_name"] == "Warlock"
        assert normalized["classes"][0]["level"] == 2

    def test_derived_invocation_management_multiclass(self, client):
        """Derived endpoint with invocation_management on Fighter 10 / Warlock 2 resolves Warlock level 2."""
        choices_made = {
            "name": "Multiclass Hero",
            "species": "Human",
            "background": "Soldier",
            "classes": [
                {"class_name": "Fighter", "level": 10},
                {"class_name": "Warlock", "level": 2},
            ],
            "class": "Warlock",
            "level": 12,
            "ability_scores": {
                "Strength": 16,
                "Dexterity": 14,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 12,
                "Charisma": 14,
            },
        }
        res = client.post(
            "/api/v1/character/derived",
            json={"view": "invocation_management", "choices_made": choices_made},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["applicable"] is True
        inv_data = data["data"]
        assert inv_data["max_invocations"] == 3
        avail = {inv["name"] for inv in inv_data["available_invocations"]}
        assert "Devil's Sight" in avail
        assert "Ascendant Step" not in avail
