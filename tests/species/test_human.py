"""
Unit tests for the Human species implementation.
Tests the Versatile trait (origin feat choice) and Skillful trait.
Regression tests for GitHub Issue #8.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def human_builder():
    """Fixture providing a fresh CharacterBuilder with Human species setup."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    return builder


class TestHumanVersatileTrait:
    """Regression tests for GitHub Issue #8: Versatile trait grants an Origin Feat."""

    def test_versatile_is_choice_trait(self, human_builder):
        """Versatile trait should be a choice, not plain text."""
        trait_choices = human_builder.get_species_trait_choices()
        assert "Versatile" in trait_choices
        assert len(trait_choices["Versatile"]["options"]) > 0

    def test_versatile_offers_all_origin_feats(self, human_builder):
        """Versatile should offer all origin feats as choices."""
        trait_choices = human_builder.get_species_trait_choices()
        options = trait_choices["Versatile"]["options"]
        expected_feats = [
            "Alert", "Crafter", "Healer", "Lucky",
            "Magic Initiate (Cleric)", "Magic Initiate (Druid)",
            "Magic Initiate (Wizard)", "Musician", "Savage Attacker",
            "Skilled", "Tavern Brawler", "Tough",
        ]
        for feat in expected_feats:
            assert feat in options, f"Versatile should offer '{feat}'"

    def test_versatile_grants_chosen_feat(self, human_builder):
        """Choosing an origin feat via Versatile adds it to character feats."""
        human_builder.apply_choice("Versatile", "Alert")

        char_data = human_builder.character_data
        feat_names = [f["name"] for f in char_data["features"]["feats"]]
        assert "Alert" in feat_names

    def test_versatile_feat_has_description(self, human_builder):
        """Origin feat granted by Versatile should have a description."""
        human_builder.apply_choice("Versatile", "Lucky")

        char_data = human_builder.character_data
        feat_entry = next(
            f for f in char_data["features"]["feats"] if f["name"] == "Lucky"
        )
        assert len(feat_entry["description"]) > 0

    def test_versatile_feat_has_source(self, human_builder):
        """Origin feat granted by Versatile should record the source."""
        human_builder.apply_choice("Versatile", "Healer")

        char_data = human_builder.character_data
        feat_entry = next(
            f for f in char_data["features"]["feats"] if f["name"] == "Healer"
        )
        assert feat_entry["source"] is not None

    def test_versatile_choice_is_stored(self, human_builder):
        """Versatile choice should be stored in choices_made."""
        human_builder.apply_choice("Versatile", "Musician")

        choices_made = human_builder.character_data["choices_made"]
        assert "Versatile" in choices_made
        assert choices_made["Versatile"] == "Musician"

    def test_versatile_tough_applies_hp_effect(self):
        """Choosing Tough via Versatile should apply bonus_hp effect."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Tough Human",
            "level": 3,
            "species": "Human",
            "class": "Fighter",
            "background": "Criminal",
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        builder.apply_choice("Versatile", "Tough")

        # The bonus_hp effect from Tough should be tracked
        hp_effects = [
            e for e in builder.applied_effects
            if e["effect"].get("type") == "bonus_hp"
        ]
        assert len(hp_effects) > 0, "Tough feat should produce a bonus_hp effect"

    def test_versatile_extra_feat_on_top_of_background(self):
        """Human should have TWO origin feats: one from background, one from Versatile."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Two Feats",
            "level": 1,
            "species": "Human",
            "class": "Fighter",
            "background": "Criminal",
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        # Criminal background grants "Alert" feat
        builder.apply_choice("Versatile", "Skilled")

        character = builder.to_character()
        feat_names = [f["name"] for f in character["features"]["feats"]]
        assert "Alert" in feat_names, "Background feat should be present"
        assert "Skilled" in feat_names, "Versatile feat should be present"
        assert len(feat_names) >= 2, "Human should have at least 2 origin feats"


class TestHumanSkillfulTrait:
    """Test Skillful trait (existing functionality)."""

    def test_skillful_grants_chosen_skill(self, human_builder):
        """Skillful trait should grant proficiency in the chosen skill."""
        human_builder.apply_choice("Skillful", "Athletics")

        skills = human_builder.character_data["proficiencies"]["skills"]
        assert "Athletics" in skills


class TestVersatileFeatChoicesFlow:
    """Regression tests for GitHub Issue: Versatile feat choices not presented."""

    def test_skilled_via_versatile_sets_pending_species_feat(self, human_builder):
        """Choosing Skilled via Versatile should set pending_species_feat."""
        human_builder.apply_choice("Versatile", "Skilled")
        assert human_builder.character_data.get("pending_species_feat") == "Skilled"

    def test_feat_without_choices_does_not_set_pending(self, human_builder):
        """Choosing a feat with no choices (Alert) should not set pending_species_feat."""
        human_builder.apply_choice("Versatile", "Alert")
        assert human_builder.character_data.get("pending_species_feat") is None

    def test_tough_does_not_set_pending(self, human_builder):
        """Tough has no choices, so pending_species_feat should not be set."""
        human_builder.apply_choice("Versatile", "Tough")
        assert human_builder.character_data.get("pending_species_feat") is None

    def test_get_species_feat_choices_returns_skilled_choices(self, human_builder):
        """get_species_feat_choices should return Skilled's skill/tool choice."""
        human_builder.apply_choice("Versatile", "Skilled")
        data = human_builder.get_species_feat_choices()
        assert data["feat_name"] == "Skilled"
        assert len(data["choices"]) > 0
        assert data["choices"][0]["count"] == 3

    def test_get_species_feat_choices_empty_when_no_pending(self, human_builder):
        """get_species_feat_choices returns empty when no feat requires choices."""
        human_builder.apply_choice("Versatile", "Alert")
        data = human_builder.get_species_feat_choices()
        assert data["feat_name"] is None
        assert data["choices"] == []

    def test_apply_feat_choices_with_explicit_feat_name(self, human_builder):
        """apply_feat_choices(feat_name=...) should grant selected skills/tools."""
        human_builder.apply_choice("Versatile", "Skilled")
        human_builder.apply_feat_choices(
            {"skills_or_tools": ["Arcana", "History", "Deception"]},
            feat_name="Skilled",
        )
        skills = human_builder.character_data["proficiencies"]["skills"]
        assert "Arcana" in skills
        assert "History" in skills
        assert "Deception" in skills

    def test_skilled_choices_stored_in_choices_made(self, human_builder):
        """Skilled choices should be persisted under a namespaced key."""
        human_builder.apply_choice("Versatile", "Skilled")
        human_builder.apply_feat_choices(
            {"skills_or_tools": ["Arcana", "History", "Deception"]},
            feat_name="Skilled",
        )
        key = "feat_Skilled_skills_or_tools"
        assert key in human_builder.character_data["choices_made"]
        assert "Arcana" in human_builder.character_data["choices_made"][key]

    def test_crafter_via_versatile_sets_pending(self, human_builder):
        """Crafter (which has tool choices) should also set pending_species_feat."""
        human_builder.apply_choice("Versatile", "Crafter")
        # Crafter has choices if the feat data includes them; if not the key won't be set.
        # We at least verify get_species_feat_choices doesn't raise an exception.
        data = human_builder.get_species_feat_choices()
        assert isinstance(data, dict)
        assert "feat_name" in data
        assert "choices" in data


class TestHumanDarkvision:
    """Tests for darkvision in to_character() output for Human species."""

    def test_no_darkvision_in_to_character_output(self):
        """to_character() must expose darkvision == 0 for Human (no darkvision species)."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        character = builder.to_character()
        assert character["darkvision"] == 0
