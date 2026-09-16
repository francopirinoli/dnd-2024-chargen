"""
Tests for wizard back/forward navigation — ensuring proper cleanup
when users revisit steps and make different choices.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def builder():
    return CharacterBuilder()


# ── Bug 1: Class skill/tool proficiency leak on re-selection ─────────


class TestClassSkillToolCleanup:
    """Changing class should remove old class-granted skills and tools."""

    def test_class_skills_cleared_on_class_change(self, builder):
        builder.set_species("Human")
        builder.set_class("Fighter", 1)
        builder.apply_choice("skill_choices", ["Athletics", "Intimidation"])

        assert "Athletics" in builder.character_data["proficiencies"]["skills"]
        assert "Intimidation" in builder.character_data["proficiencies"]["skills"]

        # Switch to Rogue
        builder.set_class("Rogue", 1)
        builder.apply_choice("skill_choices", ["Stealth", "Deception"])

        skills = builder.character_data["proficiencies"]["skills"]
        assert "Stealth" in skills
        assert "Deception" in skills
        # Old Fighter skills must be gone
        assert "Athletics" not in skills
        assert "Intimidation" not in skills

    def test_class_tools_cleared_on_class_change(self, builder):
        builder.set_species("Human")
        builder.set_class("Rogue", 1)
        builder.apply_choice("tool_choices", ["Thieves' Tools"])

        assert "Thieves' Tools" in builder.character_data["proficiencies"]["tools"]

        # Switch to Bard
        builder.set_class("Bard", 1)
        builder.apply_choice("tool_choices", ["Lute"])

        tools = builder.character_data["proficiencies"]["tools"]
        assert "Lute" in tools
        assert "Thieves' Tools" not in tools

    def test_class_skills_not_leaked_on_relevel(self, builder):
        """Re-setting the same class at a different level should not duplicate skills."""
        builder.set_species("Human")
        builder.set_class("Fighter", 1)
        builder.apply_choice("skill_choices", ["Athletics", "Intimidation"])

        builder.set_class("Fighter", 3)
        builder.apply_choice("skill_choices", ["Athletics", "Intimidation"])

        skills = builder.character_data["proficiencies"]["skills"]
        assert skills.count("Athletics") == 1
        assert skills.count("Intimidation") == 1

    def test_skill_sources_updated_on_class_change(self, builder):
        builder.set_species("Human")
        builder.set_class("Fighter", 1)
        builder.apply_choice("skill_choices", ["Athletics"])

        sources = builder.character_data["proficiency_sources"]["skills"]
        assert sources.get("Athletics") == "Fighter"

        builder.set_class("Rogue", 1)
        builder.apply_choice("skill_choices", ["Athletics"])

        sources = builder.character_data["proficiency_sources"]["skills"]
        assert sources.get("Athletics") == "Rogue"


# ── Bug 2: Stale class feature choices in choices_made ───────────────


class TestStaleClassChoicesCleared:
    """Class feature choices should be cleared when changing class."""

    def test_class_choices_cleared_on_class_change(self, builder):
        builder.set_species("Human")
        builder.set_class("Fighter", 1)
        builder.apply_choice("skill_choices", ["Athletics", "Intimidation"])

        assert "skill_choices" in builder.character_data["choices_made"]

        # Switch class — skill_choices should be cleared
        builder.set_class("Rogue", 1)
        assert "skill_choices" not in builder.character_data["choices_made"]

    def test_subclass_choice_cleared_on_class_change(self, builder):
        builder.set_species("Human")
        builder.set_class("Cleric", 3)
        builder.apply_choice("subclass", "Light Domain")

        assert builder.character_data["choices_made"].get("subclass") == "Light Domain"
        assert builder.character_data.get("subclass") == "Light Domain"

        # Switch class — subclass choice should be cleared
        builder.set_class("Fighter", 3)
        assert "subclass" not in builder.character_data["choices_made"]
        assert builder.character_data.get("subclass") is None or builder.character_data.get("subclass") != "Light Domain"


# ── Bug 3: Subclass always_prepared spells not cleared ───────────────


class TestSubclassSpellCleanup:
    """Changing subclass should clear always_prepared spells from old subclass."""

    def test_subclass_always_prepared_cleared_on_change(self, builder):
        builder.set_species("Human")
        builder.set_class("Cleric", 3)
        builder.set_subclass("Light Domain")

        always_prepared = builder.character_data["spells"]["always_prepared"]
        # Light Domain grants Burning Hands, Faerie Fire at level 3
        assert "Burning Hands" in always_prepared
        assert "Faerie Fire" in always_prepared

        # Switch to Life Domain
        builder.set_subclass("Life Domain")

        always_prepared = builder.character_data["spells"]["always_prepared"]
        # Old Light Domain spells should be gone
        assert "Burning Hands" not in always_prepared
        assert "Faerie Fire" not in always_prepared
        # New Life Domain spells should be present
        assert "Bless" in always_prepared
        assert "Cure Wounds" in always_prepared

    def test_subclass_spell_metadata_cleared(self, builder):
        builder.set_species("Human")
        builder.set_class("Cleric", 3)
        builder.set_subclass("Light Domain")

        metadata = builder.character_data["spell_metadata"]
        assert "Burning Hands" in metadata

        builder.set_subclass("Life Domain")

        metadata = builder.character_data["spell_metadata"]
        assert "Burning Hands" not in metadata
        assert "Bless" in metadata

    def test_subclass_features_cleared_on_change(self, builder):
        builder.set_species("Human")
        builder.set_class("Cleric", 3)
        builder.set_subclass("Light Domain")

        feature_names = [f["name"] for f in builder.character_data["features"]["subclass"]]
        assert any("Light" in n for n in feature_names)

        builder.set_subclass("Life Domain")

        feature_names = [f["name"] for f in builder.character_data["features"]["subclass"]]
        # Old features should be replaced
        assert not any("Bonus Cantrip" in n for n in feature_names)


# ── Bug 4: Language selection leak on re-visit ───────────────────────


class TestLanguageSelectionCleanup:
    """Re-selecting languages should replace old user selections, not accumulate."""

    def test_language_reselection_replaces_old(self, builder):
        builder.set_species("Human")
        builder.set_class("Fighter", 1)

        builder.apply_choice("languages", ["Elvish", "Dwarvish"])

        langs = builder.character_data["proficiencies"]["languages"]
        assert "Elvish" in langs
        assert "Dwarvish" in langs

        # Re-select different languages
        builder.apply_choice("languages", ["Draconic", "Goblin"])

        langs = builder.character_data["proficiencies"]["languages"]
        assert "Draconic" in langs
        assert "Goblin" in langs
        assert "Elvish" not in langs
        assert "Dwarvish" not in langs
        assert "Common" in langs

    def test_species_no_longer_grants_default_languages(self, builder):
        """Species should not implicitly grant spoken languages in 2024 flow."""
        builder.set_species("Elf")
        builder.set_class("Fighter", 1)

        species_langs = builder.character_data["proficiencies"]["languages"]
        assert "Common" in species_langs
        assert "Elvish" not in species_langs

        builder.apply_choice("languages", ["Dwarvish", "Elvish"])

        langs = builder.character_data["proficiencies"]["languages"]
        assert "Common" in langs
        assert "Elvish" in langs
        assert "Dwarvish" in langs

        # Re-select
        builder.apply_choice("languages", ["Draconic", "Goblin"])

        langs = builder.character_data["proficiencies"]["languages"]
        assert "Common" in langs
        assert "Draconic" in langs
        assert "Goblin" in langs
        assert "Dwarvish" not in langs
        assert "Elvish" not in langs

    def test_language_sources_tracked(self, builder):
        builder.set_species("Human")
        builder.set_class("Fighter", 1)

        builder.apply_choice("languages", ["Elvish", "Dwarvish"])

        sources = builder.character_data["proficiency_sources"]["languages"]
        assert sources.get("Elvish") == "user_choice"
        assert sources.get("Common") == "base"

    def test_language_selection_ignores_invalid_or_duplicate_choices(self, builder):
        builder.set_species("Human")
        builder.set_class("Fighter", 1)

        builder.apply_choice("languages", ["Elvish", "Elvish", "Infernal", "Dwarvish"])

        selected = builder.character_data["choices_made"]["languages"]
        assert selected == ["Elvish", "Dwarvish"]


# ── Bug 5: Feat choices accumulate on re-submission ──────────────────


class TestFeatChoicesCleanup:
    """Re-submitting feat choices should replace old selections."""

    def test_feat_skill_choices_replaced_on_resubmit(self, builder):
        builder.set_species("Human")
        builder.set_class("Fighter", 1)
        builder.set_background("Charlatan")  # Grants Skilled feat

        # First submission: pick 3 skills
        builder.apply_feat_choices(
            {"skills_or_tools": ["Arcana", "History", "Medicine"]},
            feat_name="Skilled"
        )

        skills = builder.character_data["proficiencies"]["skills"]
        assert "Arcana" in skills
        assert "History" in skills
        assert "Medicine" in skills

        # Re-submit with different choices
        builder.apply_feat_choices(
            {"skills_or_tools": ["Nature", "Religion", "Perception"]},
            feat_name="Skilled"
        )

        skills = builder.character_data["proficiencies"]["skills"]
        assert "Nature" in skills
        assert "Religion" in skills
        assert "Perception" in skills
        # Old choices must be gone
        assert "Arcana" not in skills
        assert "History" not in skills
        assert "Medicine" not in skills

    def test_feat_cantrip_choices_replaced_on_resubmit(self, builder):
        builder.set_species("Human")
        builder.set_class("Cleric", 1)
        builder.set_background("Acolyte")  # Magic Initiate (Cleric)

        feat_name = "Magic Initiate (Cleric)"

        builder.apply_feat_choices(
            {"cantrips": ["Sacred Flame", "Guidance"]},
            feat_name=feat_name
        )

        cantrips = builder.character_data["spells"]["always_prepared"]
        assert "Sacred Flame" in cantrips
        assert "Guidance" in cantrips

        # Re-submit with different cantrips
        builder.apply_feat_choices(
            {"cantrips": ["Thaumaturgy", "Light"]},
            feat_name=feat_name
        )

        cantrips = builder.character_data["spells"]["always_prepared"]
        assert "Thaumaturgy" in cantrips
        assert "Light" in cantrips
        assert "Sacred Flame" not in cantrips
        assert "Guidance" not in cantrips

    def test_feat_spell_choices_replaced_on_resubmit(self, builder):
        builder.set_species("Human")
        builder.set_class("Cleric", 1)
        builder.set_background("Acolyte")

        feat_name = "Magic Initiate (Cleric)"

        builder.apply_feat_choices(
            {"1st_level_spell": "Bless"},
            feat_name=feat_name
        )

        spells = builder.character_data["spells"]["always_prepared"]
        assert "Bless" in spells

        builder.apply_feat_choices(
            {"1st_level_spell": "Healing Word"},
            feat_name=feat_name
        )

        spells = builder.character_data["spells"]["always_prepared"]
        assert "Healing Word" in spells
        assert "Bless" not in spells

    def test_feat_choices_made_updated(self, builder):
        builder.set_species("Human")
        builder.set_class("Fighter", 1)
        builder.set_background("Charlatan")

        builder.apply_feat_choices(
            {"skills_or_tools": ["Arcana"]},
            feat_name="Skilled"
        )

        key = "feat_Skilled_skills_or_tools"
        assert builder.character_data["choices_made"][key] == ["Arcana"]

        builder.apply_feat_choices(
            {"skills_or_tools": ["Nature"]},
            feat_name="Skilled"
        )

        assert builder.character_data["choices_made"][key] == ["Nature"]


# ── Bug 6: Species trait choice effects accumulate ───────────────────


class TestSpeciesTraitChoiceCleanup:
    """Re-selecting a species trait option should replace old effects."""

    def test_elf_keen_senses_replaced_on_reselect(self, builder):
        builder.set_species("Elf")
        builder.set_class("Fighter", 1)

        # Choose Insight for Keen Senses
        builder.apply_choice("Keen Senses", "Insight")

        skills = builder.character_data["proficiencies"]["skills"]
        assert "Insight" in skills

        # Change to Perception
        builder.apply_choice("Keen Senses", "Perception")

        skills = builder.character_data["proficiencies"]["skills"]
        assert "Perception" in skills
        assert "Insight" not in skills

    def test_elf_keen_senses_no_duplicate(self, builder):
        builder.set_species("Elf")
        builder.set_class("Fighter", 1)

        builder.apply_choice("Keen Senses", "Survival")
        builder.apply_choice("Keen Senses", "Survival")

        skills = builder.character_data["proficiencies"]["skills"]
        assert skills.count("Survival") == 1

    def test_species_choice_effects_cleaned_in_applied_effects(self, builder):
        builder.set_species("Elf")
        builder.set_class("Fighter", 1)

        builder.apply_choice("Keen Senses", "Insight")

        # Check applied_effects has species_choice for Keen Senses
        keen_effects = [
            e for e in builder.applied_effects
            if e.get("source_type") == "species_choice"
            and "Keen Senses" in e.get("source", "")
        ]
        assert len(keen_effects) == 1

        # Change choice
        builder.apply_choice("Keen Senses", "Perception")

        keen_effects = [
            e for e in builder.applied_effects
            if e.get("source_type") == "species_choice"
            and "Keen Senses" in e.get("source", "")
        ]
        assert len(keen_effects) == 1
        assert "Perception" in keen_effects[0]["source"]


# ── Integration: full wizard back-and-forth ──────────────────────────


class TestWizardBackAndForth:
    """End-to-end tests simulating a user going back and forth in the wizard."""

    def test_full_class_change_roundtrip(self, builder):
        """Simulate: create → class → skills → go back → new class → new skills."""
        builder.set_species("Elf")
        builder.apply_choice("Keen Senses", "Insight")
        builder.set_class("Fighter", 3)
        builder.apply_choice("skill_choices", ["Athletics", "Acrobatics"])
        builder.set_subclass("Champion")
        builder.set_background("Soldier")

        character = builder.to_character()
        assert "Athletics" in character["proficiencies"]["skills"]
        assert "Acrobatics" in character["proficiencies"]["skills"]

        # Go back and change class
        builder.set_class("Rogue", 3)
        builder.apply_choice("skill_choices", ["Stealth", "Deception", "Sleight of Hand", "Investigation"])
        builder.set_subclass("Thief")

        character = builder.to_character()
        skills = character["proficiencies"]["skills"]

        # New Rogue skills present
        assert "Stealth" in skills
        assert "Deception" in skills
        # Old Fighter skills gone
        assert "Athletics" not in skills
        assert "Acrobatics" not in skills
        # Species skill still there
        assert "Insight" in skills

    def test_full_background_change_preserves_class_skills(self, builder):
        """Changing background should not affect class-granted skills."""
        builder.set_species("Human")
        builder.set_class("Fighter", 1)
        builder.apply_choice("skill_choices", ["Athletics", "Intimidation"])
        builder.set_background("Soldier")

        character = builder.to_character()
        assert "Athletics" in character["proficiencies"]["skills"]

        # Change background
        builder.set_background("Acolyte")

        character = builder.to_character()
        # Class skills still there
        assert "Athletics" in character["proficiencies"]["skills"]
        assert "Intimidation" in character["proficiencies"]["skills"]

    def test_multiple_language_reselections(self, builder):
        """Repeatedly changing language selections should work cleanly."""
        builder.set_species("Human")
        builder.set_class("Fighter", 1)

        builder.apply_choice("languages", ["Elvish"])
        builder.apply_choice("languages", ["Dwarvish"])
        builder.apply_choice("languages", ["Draconic"])

        langs = builder.character_data["proficiencies"]["languages"]
        assert "Draconic" in langs
        assert "Common" in langs
        assert "Elvish" not in langs
        assert "Dwarvish" not in langs
