"""Tests for species/lineage skill proficiency overlap replacement (Phase 3).

Mirrors the TestBackgroundSkillReplacement pattern from test_backgrounds.py.
"""

import pytest
from modules.character_builder import CharacterBuilder


class TestSpeciesSkillReplacement:
    """When a species/lineage grants a skill the character already has,
    the player should be offered a replacement choice."""

    def _ranger_elf_choices(self, keen_senses_pick="Perception"):
        """Ranger who picks Perception as class skill, then Elf with Keen Senses."""
        return {
            "character_name": "Test Ranger",
            "level": 1,
            "class": "Ranger",
            "background": "Acolyte",
            "skill_choices": ["Perception", "Stealth", "Survival"],
            "Keen Senses": keen_senses_pick,
            "species": "Elf",
            "ability_scores": {
                "Strength": 10, "Dexterity": 15, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 13, "Charisma": 12,
            },
            "background_bonuses": {"Intelligence": 1, "Wisdom": 2},
        }

    # ---- overlap detection --------------------------------------------------

    def test_overlap_detected_when_species_grants_existing_skill(self):
        """Elf Keen Senses picking Perception when Ranger already has it."""
        builder = CharacterBuilder()
        builder.apply_choices(self._ranger_elf_choices("Perception"))
        needed = builder.character_data["choices_made"].get(
            "species_skill_replacements_needed", 0
        )
        assert needed == 1, f"Expected 1 replacement needed, got {needed}"

    def test_no_overlap_when_species_skill_is_unique(self):
        """Elf Keen Senses picking Survival — no overlap when Ranger doesn't pick it."""
        # Ranger picks Perception+Stealth+Insight so Survival is free
        builder = CharacterBuilder()
        builder.apply_choices({
            **self._ranger_elf_choices("Survival"),
            "skill_choices": ["Perception", "Stealth", "Insight"],
        })
        needed = builder.character_data["choices_made"].get(
            "species_skill_replacements_needed", 0
        )
        assert needed == 0, f"Expected 0 replacements needed, got {needed}"

    # ---- replacement info ---------------------------------------------------

    def test_get_replacement_info_returns_options(self):
        """get_species_skill_replacement_info() lists valid replacement options."""
        builder = CharacterBuilder()
        builder.apply_choices(self._ranger_elf_choices("Perception"))

        info = builder.get_species_skill_replacement_info()
        assert info["needed"] == 1
        assert len(info["options"]) > 0
        # Options must not include skills the character already has
        current_profs = set(builder.character_data["proficiencies"]["skills"])
        for skill in info["options"]:
            assert skill not in current_profs

    def test_get_replacement_info_zero_when_no_overlap(self):
        """get_species_skill_replacement_info() returns needed=0 when no overlap."""
        builder = CharacterBuilder()
        builder.apply_choices({
            **self._ranger_elf_choices("Survival"),
            "skill_choices": ["Perception", "Stealth", "Insight"],
        })
        info = builder.get_species_skill_replacement_info()
        assert info["needed"] == 0

    # ---- applying replacements ----------------------------------------------

    def test_apply_replacement_adds_skill(self):
        """apply_species_skill_replacement() grants the chosen skill proficiency."""
        builder = CharacterBuilder()
        builder.apply_choices(self._ranger_elf_choices("Perception"))

        info = builder.get_species_skill_replacement_info()
        replacement_skill = info["options"][0]

        builder.apply_species_skill_replacement([replacement_skill])

        skills = builder.character_data["proficiencies"]["skills"]
        assert replacement_skill in skills

    def test_apply_replacement_correct_total_proficiencies(self):
        """After replacement, character should have expected total skill count."""
        builder = CharacterBuilder()
        # Ranger picks 3 class skills; Acolyte grants 2 background skills
        # Elf Keen Senses grants 1 species skill (overlapping) → replacement
        # Total: 3 (class) + 2 (background) + 1 (species replacement) = 6
        builder.apply_choices(self._ranger_elf_choices("Perception"))

        info = builder.get_species_skill_replacement_info()
        builder.apply_species_skill_replacement([info["options"][0]])

        skills = builder.character_data["proficiencies"]["skills"]
        assert len(skills) == 6, f"Expected 6 skill proficiencies, got {len(skills)}: {skills}"

    def test_apply_replacement_idempotent(self):
        """Calling apply_species_skill_replacement twice replaces the first choice."""
        builder = CharacterBuilder()
        builder.apply_choices(self._ranger_elf_choices("Perception"))

        info = builder.get_species_skill_replacement_info()
        skill_a = info["options"][0]
        skill_b = info["options"][1] if len(info["options"]) > 1 else skill_a

        builder.apply_species_skill_replacement([skill_a])
        builder.apply_species_skill_replacement([skill_b])

        skills = builder.character_data["proficiencies"]["skills"]
        assert skills.count(skill_a) <= 1
        assert skills.count(skill_b) == 1

    # ---- clearing on species change -----------------------------------------

    def test_changing_species_clears_replacement_data(self):
        """Switching species removes replacement tracking and replacement skills."""
        builder = CharacterBuilder()
        builder.apply_choices(self._ranger_elf_choices("Perception"))

        info = builder.get_species_skill_replacement_info()
        replacement_skill = info["options"][0]
        builder.apply_species_skill_replacement([replacement_skill])

        # Switch to Dwarf (no skill proficiency grants)
        builder.apply_choice("species", "Dwarf")

        choices_made = builder.character_data["choices_made"]
        assert "species_skill_replacements_needed" not in choices_made
        assert "species_skill_replacements" not in choices_made
        # Replacement skill should be removed
        assert replacement_skill not in builder.character_data["proficiencies"]["skills"]

    # ---- restore from choices_made ------------------------------------------

    def test_apply_choices_restores_replacement_skills(self):
        """apply_choices() with species_skill_replacements restores proficiencies."""
        builder = CharacterBuilder()
        builder.apply_choices({
            **self._ranger_elf_choices("Perception"),
            "species_skill_replacements": ["Athletics"],
        })
        skills = builder.character_data["proficiencies"]["skills"]
        assert "Athletics" in skills, (
            "Replacement skill should be restored from choices_made"
        )
        assert len(set(skills)) == len(skills), "No duplicate proficiencies"
