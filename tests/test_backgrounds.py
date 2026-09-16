"""Tests for all D&D 2024 backgrounds - data loading and character building."""

import json
import pytest
from pathlib import Path
from jsonschema import Draft7Validator

from modules.data_loader import DataLoader
from modules.character_builder import CharacterBuilder


DATA_DIR = Path(__file__).parent.parent / "data" / "backgrounds"
REPO_ROOT = Path(__file__).parent.parent
BACKGROUND_SCHEMA = REPO_ROOT / "models" / "background_schema.json"

# Every D&D 2024 background that should exist
ACTIVE_2024_BACKGROUNDS = [
    "Acolyte", "Artisan", "Charlatan", "Criminal", "Entertainer",
    "Farmer", "Guard", "Guide", "Hermit", "Merchant", "Noble",
    "Sage", "Sailor", "Scribe", "Soldier", "Wayfarer",
]
LEGACY_BACKGROUNDS = ["Folk Hero", "Guild Artisan"]
ALL_BACKGROUNDS = ACTIVE_2024_BACKGROUNDS + LEGACY_BACKGROUNDS


@pytest.fixture(scope="module")
def data_loader():
    return DataLoader()


class TestBackgroundDataFiles:
    """Verify every background JSON file loads and has required fields."""

    @pytest.mark.parametrize("bg_name", ALL_BACKGROUNDS)
    def test_background_exists(self, data_loader, bg_name):
        """Each background should be loadable from data files."""
        assert bg_name in data_loader.backgrounds, f"Missing background: {bg_name}"

    @pytest.mark.parametrize("bg_name", ALL_BACKGROUNDS)
    def test_background_required_fields(self, data_loader, bg_name):
        """Each background must have the required schema fields."""
        bg = data_loader.backgrounds.get(bg_name)
        if bg is None:
            pytest.skip(f"{bg_name} not loaded")

        assert bg.get("name") == bg_name
        assert isinstance(bg.get("description"), str)
        assert bg.get("edition") in {"2024", "2014"}
        assert bg.get("status") in {"active", "legacy"}
        # Phase 9 (D1-1): backgrounds expose all mechanical grants via the
        # canonical ``effects`` array — the origin feat as
        # ``grant_origin_feat`` with a ``feat`` field, skill proficiencies as
        # ``grant_skill_proficiency``, tool proficiencies as
        # ``grant_tool_proficiency``. The flat top-level ``feat`` and
        # ``skill_proficiencies`` keys are no longer permitted.
        assert "feat" not in bg, (
            "Background must not carry a flat top-level ``feat`` key "
            "(Phase 9: encode as grant_origin_feat effect instead)."
        )
        assert "skill_proficiencies" not in bg, (
            "Background must not carry a flat top-level "
            "``skill_proficiencies`` key (Phase 9: encode as "
            "grant_skill_proficiency effect instead)."
        )
        assert isinstance(bg.get("effects"), list)
        origin_feat_effects = [
            e for e in bg["effects"] if e.get("type") == "grant_origin_feat"
        ]
        assert len(origin_feat_effects) == 1
        assert isinstance(origin_feat_effects[0].get("feat"), str)
        skill_effects = [
            e for e in bg["effects"] if e.get("type") == "grant_skill_proficiency"
        ]
        assert len(skill_effects) == 1
        assert len(skill_effects[0].get("skills", [])) == 2
        tool_effects = [
            e for e in bg["effects"] if e.get("type") == "grant_tool_proficiency"
        ]
        assert len(tool_effects) >= 1
        tools_granted = [t for e in tool_effects for t in e.get("tools", [])]
        assert len(tools_granted) >= 1

    def test_background_catalog_status_sets(self, data_loader):
        """Only 2024 active backgrounds are in the default catalog set."""
        active = {
            name for name, bg in data_loader.backgrounds.items()
            if bg.get("edition") == "2024" and bg.get("status") == "active"
        }
        legacy = {
            name for name, bg in data_loader.backgrounds.items()
            if bg.get("edition") == "2014" and bg.get("status") == "legacy"
        }

        assert active == set(ACTIVE_2024_BACKGROUNDS)
        assert legacy == set(LEGACY_BACKGROUNDS)

    def test_background_schema_rejects_unsupported_catalog_metadata(self):
        """Schema validation must reject unsupported edition/status values."""
        schema = json.loads(BACKGROUND_SCHEMA.read_text())
        sample = json.loads((DATA_DIR / "artisan.json").read_text())
        sample["edition"] = "2023"
        sample["status"] = "deprecated"
        sample["effects"] = []

        validator = Draft7Validator(schema)

        errors = list(validator.iter_errors(sample))
        assert errors

    @pytest.mark.parametrize("bg_name", ALL_BACKGROUNDS)
    def test_background_ability_scores(self, data_loader, bg_name):
        """Ability score increase must have total=3, 3 options, and valid suggested split."""
        bg = data_loader.backgrounds.get(bg_name)
        if bg is None:
            pytest.skip(f"{bg_name} not loaded")

        asi = bg["ability_score_increase"]
        assert asi["total"] == 3
        assert len(asi["options"]) == 3
        suggested = asi["suggested"]
        assert sum(suggested.values()) == 3
        # All suggested abilities must be in options
        for ability in suggested:
            assert ability in asi["options"]

    @pytest.mark.parametrize("bg_name", ALL_BACKGROUNDS)
    def test_background_equipment(self, data_loader, bg_name):
        """Starting equipment must have option_a (with items + gold) and option_b (gold only)."""
        bg = data_loader.backgrounds.get(bg_name)
        if bg is None:
            pytest.skip(f"{bg_name} not loaded")

        equip = bg["starting_equipment"]
        assert "option_a" in equip
        assert "option_b" in equip
        assert "items" in equip["option_a"]
        assert "gold" in equip["option_b"]
        assert equip["option_b"]["gold"] == 50


class TestNewBackgroundsIntegration:
    """Integration tests building characters with newly added backgrounds."""

    def test_artisan_character(self, built_character):
        """Build a character with Artisan background."""
        character = built_character({
            "character_name": "Artisan Test",
            "level": 1,
            "species": "Human",
            "class": "Fighter",
            "background": "Artisan",
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 1, "Intelligence": 2},
        })
        assert character["background"] == "Artisan"
        assert "Investigation" in character.get("skill_proficiencies", [])
        assert "Persuasion" in character.get("skill_proficiencies", [])

    def test_farmer_character(self, built_character):
        """Build a character with Farmer background."""
        character = built_character({
            "character_name": "Farmer Test",
            "level": 1,
            "species": "Human",
            "class": "Barbarian",
            "background": "Farmer",
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 12, "Charisma": 10
            },
            "background_bonuses": {"Strength": 1, "Constitution": 2},
        })
        assert character["background"] == "Farmer"
        assert "Animal Handling" in character.get("skill_proficiencies", [])
        assert "Nature" in character.get("skill_proficiencies", [])

    def test_guard_character(self, built_character):
        """Build a character with Guard background."""
        character = built_character({
            "character_name": "Guard Test",
            "level": 1,
            "species": "Human",
            "class": "Fighter",
            "background": "Guard",
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Wisdom": 1},
        })
        assert character["background"] == "Guard"
        assert "Athletics" in character.get("skill_proficiencies", [])
        assert "Perception" in character.get("skill_proficiencies", [])

    def test_guide_character(self, built_character):
        """Build a character with Guide background."""
        character = built_character({
            "character_name": "Guide Test",
            "level": 1,
            "species": "Human",
            "class": "Ranger",
            "background": "Guide",
            "ability_scores": {
                "Strength": 10, "Dexterity": 15, "Constitution": 14,
                "Intelligence": 8, "Wisdom": 13, "Charisma": 12
            },
            "background_bonuses": {"Dexterity": 1, "Wisdom": 2},
        })
        assert character["background"] == "Guide"
        assert "Stealth" in character.get("skill_proficiencies", [])
        assert "Survival" in character.get("skill_proficiencies", [])

    def test_merchant_character(self, built_character):
        """Build a character with Merchant background."""
        character = built_character({
            "character_name": "Merchant Test",
            "level": 1,
            "species": "Human",
            "class": "Rogue",
            "background": "Merchant",
            "ability_scores": {
                "Strength": 8, "Dexterity": 15, "Constitution": 14,
                "Intelligence": 13, "Wisdom": 10, "Charisma": 12
            },
            "background_bonuses": {"Intelligence": 1, "Charisma": 2},
        })
        assert character["background"] == "Merchant"
        assert "Animal Handling" in character.get("skill_proficiencies", [])
        assert "Persuasion" in character.get("skill_proficiencies", [])

    def test_sailor_character(self, built_character):
        """Build a character with Sailor background."""
        character = built_character({
            "character_name": "Sailor Test",
            "level": 1,
            "species": "Human",
            "class": "Fighter",
            "background": "Sailor",
            "ability_scores": {
                "Strength": 14, "Dexterity": 15, "Constitution": 13,
                "Intelligence": 8, "Wisdom": 12, "Charisma": 10
            },
            "background_bonuses": {"Strength": 1, "Dexterity": 2},
        })
        assert character["background"] == "Sailor"
        assert "Acrobatics" in character.get("skill_proficiencies", [])
        assert "Perception" in character.get("skill_proficiencies", [])

    def test_scribe_character(self, built_character):
        """Build a character with Scribe background."""
        character = built_character({
            "character_name": "Scribe Test",
            "level": 1,
            "species": "Human",
            "class": "Wizard",
            "background": "Scribe",
            "ability_scores": {
                "Strength": 8, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 15, "Wisdom": 12, "Charisma": 10
            },
            "background_bonuses": {"Dexterity": 1, "Intelligence": 2},
        })
        assert character["background"] == "Scribe"
        assert "Investigation" in character.get("skill_proficiencies", [])
        assert "Perception" in character.get("skill_proficiencies", [])

    def test_wayfarer_character(self, built_character):
        """Build a character with Wayfarer background."""
        character = built_character({
            "character_name": "Wayfarer Test",
            "level": 1,
            "species": "Human",
            "class": "Rogue",
            "background": "Wayfarer",
            "ability_scores": {
                "Strength": 8, "Dexterity": 15, "Constitution": 14,
                "Intelligence": 12, "Wisdom": 13, "Charisma": 10
            },
            "background_bonuses": {"Dexterity": 2, "Wisdom": 1},
        })
        assert character["background"] == "Wayfarer"
        assert "Insight" in character.get("skill_proficiencies", [])
        assert "Stealth" in character.get("skill_proficiencies", [])


class TestBackgroundReselection:
    """Regression tests for GitHub Issue: origin feats accumulate when changing background."""

    def _base_choices(self, background):
        return {
            "character_name": "Test Hero",
            "level": 1,
            "species": "Human",
            "class": "Fighter",
            "background": background,
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        }

    def test_changing_background_replaces_feat(self):
        """Switching background replaces the origin feat, not accumulates it."""
        builder = CharacterBuilder()
        # First pick Soldier (Savage Attacker)
        builder.apply_choices(self._base_choices("Soldier"))
        # Then switch to Guard (Alert)
        builder.set_background("Guard")
        character = builder.to_character()

        feat_names = [f["name"] for f in character["features"]["feats"]]
        assert "Alert" in feat_names, "New background feat should be present"
        assert "Savage Attacker" not in feat_names, "Old background feat should be removed"
        assert feat_names.count("Alert") == 1, "Feat should appear exactly once"

    def test_changing_background_removes_old_skills(self):
        """Switching background removes the old background's skill proficiencies."""
        builder = CharacterBuilder()
        builder.apply_choices(self._base_choices("Soldier"))  # Athletics, Intimidation
        builder.set_background("Guard")   # Athletics, Perception
        character = builder.to_character()

        # Guard skills present
        assert "Athletics" in character.get("skill_proficiencies", [])
        assert "Perception" in character.get("skill_proficiencies", [])
        # Soldier-only skill gone
        assert "Intimidation" not in character.get("skill_proficiencies", [])

    def test_tough_hp_bonus_not_multiplied(self):
        """Switching to a background with Tough does not multiply the bonus_hp effect."""
        builder = CharacterBuilder()
        # Start with Sage (Magic Initiate Wizard)
        builder.apply_choices(self._base_choices("Sage"))
        # Switch to Folk Hero (Tough)
        builder.set_background("Folk Hero")

        # Count bonus_hp effects from Tough to confirm it's applied exactly once
        tough_hp_effects = [
            e for e in builder.applied_effects
            if e.get("source") == "Tough" and e["effect"].get("type") == "bonus_hp"
        ]
        assert len(tough_hp_effects) == 1, (
            f"Tough's bonus_hp should appear exactly once, got {len(tough_hp_effects)}"
        )

    def test_multiple_background_changes_no_accumulation(self):
        """Multiple background changes result in exactly one feat from the final background."""
        builder = CharacterBuilder()
        builder.apply_choices(self._base_choices("Sage"))
        builder.set_background("Soldier")
        builder.set_background("Guard")
        builder.set_background("Folk Hero")
        character = builder.to_character()

        feat_names = [f["name"] for f in character["features"]["feats"]]
        # Only Tough (from Folk Hero) should remain
        assert "Tough" in feat_names
        assert "Alert" not in feat_names
        assert "Savage Attacker" not in feat_names
        assert feat_names.count("Tough") == 1


class TestBackgroundSkillReplacement:
    """Regression tests for GitHub Issue: overlapping class/background skill proficiencies
    should offer a replacement choice instead of silently dropping the duplicate."""

    def _monk_choices(self, background: str):
        """Monk choosing Acrobatics as their class skill, then a given background."""
        return {
            "character_name": "Test Monk",
            "level": 1,
            "species": "Human",
            "class": "Monk",
            "background": background,
            "skill_choices": ["Acrobatics", "History"],
            "ability_scores": {
                "Strength": 12, "Dexterity": 16, "Constitution": 13,
                "Intelligence": 10, "Wisdom": 14, "Charisma": 8,
            },
            "background_bonuses": {"Dexterity": 2, "Wisdom": 1},
        }

    # ---- overlap detection --------------------------------------------------

    def test_overlap_detection_sets_replacements_needed(self):
        """When background skill overlaps with class skill, replacements_needed is stored."""
        builder = CharacterBuilder()
        # Monk picks Acrobatics; Sailor also grants Acrobatics
        builder.apply_choices(self._monk_choices("Sailor"))
        needed = builder.character_data["choices_made"].get(
            "background_skill_replacements_needed", 0
        )
        assert needed == 1, f"Expected 1 replacement needed, got {needed}"

    def test_no_overlap_no_replacements_needed(self):
        """When there is no overlap, replacements_needed is not set."""
        builder = CharacterBuilder()
        # Monk picks History and Insight; Sailor grants Acrobatics + Perception — no overlap
        builder.apply_choices({
            **self._monk_choices("Sailor"),
            "skill_choices": ["History", "Insight"],
        })
        needed = builder.character_data["choices_made"].get(
            "background_skill_replacements_needed", 0
        )
        assert needed == 0, f"Expected 0 replacements needed, got {needed}"

    # ---- replacement info ---------------------------------------------------

    def test_get_replacement_info_returns_options(self):
        """get_background_skill_replacement_info() lists valid replacement options."""
        builder = CharacterBuilder()
        builder.apply_choices(self._monk_choices("Sailor"))

        info = builder.get_background_skill_replacement_info()
        assert info["needed"] == 1
        assert len(info["options"]) > 0
        # Options should not include already-proficient skills
        current_profs = set(builder.character_data["proficiencies"]["skills"])
        for skill in info["options"]:
            assert skill not in current_profs, f"Option '{skill}' is already proficient — should be excluded"

    def test_get_replacement_info_returns_zero_when_no_overlap(self):
        """get_background_skill_replacement_info() returns needed=0 when no overlap."""
        builder = CharacterBuilder()
        builder.apply_choices({
            **self._monk_choices("Sailor"),
            "skill_choices": ["History", "Insight"],
        })
        info = builder.get_background_skill_replacement_info()
        assert info["needed"] == 0

    # ---- applying replacements ----------------------------------------------

    def test_apply_replacement_adds_skill(self):
        """apply_background_skill_replacement() grants the chosen skill proficiency."""
        builder = CharacterBuilder()
        builder.apply_choices(self._monk_choices("Sailor"))

        info = builder.get_background_skill_replacement_info()
        replacement_skill = info["options"][0]

        builder.apply_background_skill_replacement([replacement_skill])

        skills = builder.character_data["proficiencies"]["skills"]
        assert replacement_skill in skills, f"Replacement skill '{replacement_skill}' should now be proficient"

    def test_apply_replacement_correct_total_proficiencies(self):
        """After replacement, character should have the expected total skill count."""
        builder = CharacterBuilder()
        # Monk picks 2 class skills; Sailor grants 2 background skills with 1 overlap
        # → should end up with 2 + 2 = 4 distinct skill proficiencies (1 bg replaced)
        builder.apply_choices(self._monk_choices("Sailor"))

        info = builder.get_background_skill_replacement_info()
        builder.apply_background_skill_replacement([info["options"][0]])

        skills = builder.character_data["proficiencies"]["skills"]
        assert len(skills) == 4, f"Expected 4 distinct skill proficiencies, got {len(skills)}: {skills}"

    def test_apply_replacement_idempotent(self):
        """Calling apply_background_skill_replacement twice replaces the first choice."""
        builder = CharacterBuilder()
        builder.apply_choices(self._monk_choices("Sailor"))

        info = builder.get_background_skill_replacement_info()
        skill_a = info["options"][0]
        skill_b = info["options"][1] if len(info["options"]) > 1 else info["options"][0]

        builder.apply_background_skill_replacement([skill_a])
        builder.apply_background_skill_replacement([skill_b])

        skills = builder.character_data["proficiencies"]["skills"]
        # Only one replacement should survive
        assert skills.count(skill_a) <= 1
        assert skills.count(skill_b) == 1

    # ---- clearing on background change --------------------------------------

    def test_changing_background_clears_replacement_data(self):
        """Switching background removes replacement tracking and replacement skills."""
        builder = CharacterBuilder()
        builder.apply_choices(self._monk_choices("Sailor"))

        info = builder.get_background_skill_replacement_info()
        replacement_skill = info["options"][0]
        builder.apply_background_skill_replacement([replacement_skill])

        # Switch to a background that does NOT overlap with remaining class skills
        builder.set_background("Hermit")  # Grants Medicine + Religion

        choices_made = builder.character_data["choices_made"]
        assert "background_skill_replacements_needed" not in choices_made
        assert "background_skill_replacements" not in choices_made
        # Replacement skill from old background should be removed
        assert replacement_skill not in builder.character_data["proficiencies"]["skills"]

    # ---- restore from choices_made ------------------------------------------

    def test_apply_choices_restores_replacement_skills(self):
        """apply_choices() with background_skill_replacements restores proficiencies."""
        builder = CharacterBuilder()
        builder.apply_choices({
            **self._monk_choices("Sailor"),
            "background_skill_replacements": ["Athletics"],
        })
        skills = builder.character_data["proficiencies"]["skills"]
        assert "Athletics" in skills, (
            "Replacement skill should be restored from choices_made"
        )
        assert len(set(skills)) == len(skills), "No duplicate proficiencies"


class TestBackgroundSkillReplacementKeyNormalization:
    """Regression tests for singular/plural key mismatch bug.

    The frontend sends 'background_skill_replacement' (singular);
    CharacterBuilder expects 'background_skill_replacements' (plural).
    The API layer normalises the key before calling apply_choices().
    """

    def _barbarian_farmer_choices(self):
        """Barbarian picking Animal Handling + Intimidation, background Farmer."""
        return {
            "character_name": "Test Barbarian",
            "level": 1,
            "species": "Human",
            "class": "Barbarian",
            "background": "Farmer",
            "skill_choices": ["Animal Handling", "Intimidation"],
            "ability_scores": {
                "Strength": 16, "Dexterity": 13, "Constitution": 15,
                "Intelligence": 8, "Wisdom": 12, "Charisma": 10,
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        }

    def test_normalization_coerces_singular_string_to_plural_list(self):
        """_normalize_choices_for_builder wraps singular string replacement in a plural list."""
        from routes.api.character import _normalize_choices_for_builder

        choices = {
            "class": "Barbarian",
            "level": 1,
            "background_skill_replacement": "Survival",
        }
        normalized = _normalize_choices_for_builder(choices)
        assert "background_skill_replacements" in normalized
        assert normalized["background_skill_replacements"] == ["Survival"]
        assert "background_skill_replacement" not in normalized

    def test_normalization_coerces_empty_singular_to_empty_plural_list(self):
        """Empty singular replacement value should normalize to an empty plural list."""
        from routes.api.character import _normalize_choices_for_builder

        choices = {
            "class": "Barbarian",
            "level": 1,
            "background_skill_replacement": "",
        }
        normalized = _normalize_choices_for_builder(choices)
        assert "background_skill_replacements" in normalized
        assert normalized["background_skill_replacements"] == []
        assert "background_skill_replacement" not in normalized

    def test_substitution_applied_via_plural_key(self):
        """Barbarian + Farmer: substitution via plural key yields 4 distinct skills."""
        builder = CharacterBuilder()
        builder.apply_choices({
            **self._barbarian_farmer_choices(),
            "background_skill_replacements": ["Survival"],
        })
        skills = builder.character_data["proficiencies"]["skills"]
        # Animal Handling (class) + Intimidation (class) + Nature (bg) + Survival (sub)
        assert "Animal Handling" in skills
        assert "Intimidation" in skills
        assert "Nature" in skills
        assert "Survival" in skills
        assert len(set(skills)) == len(skills), "No duplicate proficiencies"

    def test_substitution_applied_via_normalized_singular_key(self):
        """Repro: singular key from frontend, normalised through API layer, applied correctly."""
        from routes.api.character import _normalize_choices_for_builder

        raw_choices = {
            **self._barbarian_farmer_choices(),
            "background_skill_replacement": ["Survival"],   # singular — as sent by frontend
        }
        normalized = _normalize_choices_for_builder(raw_choices)

        builder = CharacterBuilder()
        builder.apply_choices(normalized)
        skills = builder.character_data["proficiencies"]["skills"]
        # Animal Handling (class) + Intimidation (class) + Nature (bg) + Survival (sub)
        assert "Animal Handling" in skills
        assert "Intimidation" in skills
        assert "Nature" in skills
        assert "Survival" in skills, (
            "Survival substitution was lost — singular→plural normalization likely missing"
        )
        assert len(set(skills)) == len(skills), "No duplicate proficiencies"

    def test_apply_choice_background_skill_replacements_accepts_string(self):
        """apply_choice() should accept a singular string for plural replacement key."""
        builder = CharacterBuilder()
        builder.apply_choices(self._barbarian_farmer_choices())

        # Farmer overlaps Animal Handling; replacement should accept a bare string.
        builder.apply_choice("background_skill_replacements", "Survival")

        skills = builder.character_data["proficiencies"]["skills"]
        chosen = builder.character_data["choices_made"]["background_skill_replacements"]
        assert "Survival" in skills
        assert chosen == ["Survival"]

    def test_replacement_info_coerces_legacy_string_to_list(self):
        """get_background_skill_replacement_info() should expose already_chosen as a list."""
        builder = CharacterBuilder()
        builder.apply_choices(self._barbarian_farmer_choices())

        # Simulate legacy persisted shape.
        builder.character_data["choices_made"]["background_skill_replacements"] = "Survival"

        info = builder.get_background_skill_replacement_info()
        assert isinstance(info["already_chosen"], list)
        assert info["already_chosen"] == ["Survival"]


class TestSpeciesSkillReplacementKeyNormalization:
    """Targeted regressions for species replacement singular/string coercion."""

    def _ranger_elf_choices(self, keen_senses_pick="Perception"):
        """Ranger who picks Perception as a class skill, then Elf Keen Senses."""
        return {
            "character_name": "Test Ranger",
            "level": 1,
            "class": "Ranger",
            "background": "Acolyte",
            "skill_choices": ["Perception", "Stealth", "Survival"],
            "Keen Senses": keen_senses_pick,
            "species": "Elf",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 15,
                "Constitution": 14,
                "Intelligence": 8,
                "Wisdom": 13,
                "Charisma": 12,
            },
            "background_bonuses": {"Intelligence": 1, "Wisdom": 2},
        }

    def test_normalization_coerces_species_singular_string_to_plural_list(self):
        """_normalize_choices_for_builder wraps species singular string in plural list."""
        from routes.api.character import _normalize_choices_for_builder

        choices = {
            "class": "Ranger",
            "level": 1,
            "species_skill_replacement": "Athletics",
        }
        normalized = _normalize_choices_for_builder(choices)
        assert "species_skill_replacements" in normalized
        assert normalized["species_skill_replacements"] == ["Athletics"]
        assert "species_skill_replacement" not in normalized

    def test_normalization_coerces_empty_species_singular_to_empty_plural_list(self):
        """Empty species singular replacement value should normalize to empty plural list."""
        from routes.api.character import _normalize_choices_for_builder

        choices = {
            "class": "Ranger",
            "level": 1,
            "species_skill_replacement": "",
        }
        normalized = _normalize_choices_for_builder(choices)
        assert "species_skill_replacements" in normalized
        assert normalized["species_skill_replacements"] == []
        assert "species_skill_replacement" not in normalized

    def test_apply_choice_species_skill_replacements_accepts_string(self):
        """apply_choice() should accept bare string for species_skill_replacements."""
        builder = CharacterBuilder()
        builder.apply_choices(self._ranger_elf_choices("Perception"))

        # Keen Senses overlaps Ranger Perception; replacement should accept a bare string.
        builder.apply_choice("species_skill_replacements", "Athletics")

        skills = builder.character_data["proficiencies"]["skills"]
        chosen = builder.character_data["choices_made"]["species_skill_replacements"]
        assert "Athletics" in skills
        assert chosen == ["Athletics"]

    def test_species_replacement_info_coerces_legacy_string_to_list(self):
        """get_species_skill_replacement_info() should expose already_chosen as a list."""
        builder = CharacterBuilder()
        builder.apply_choices(self._ranger_elf_choices("Perception"))

        # Simulate legacy persisted shape.
        builder.character_data["choices_made"]["species_skill_replacements"] = "Athletics"

        info = builder.get_species_skill_replacement_info()
        assert isinstance(info["already_chosen"], list)
        assert info["already_chosen"] == ["Athletics"]


class TestBackgroundSkillReplacementValidationRegression:
    """Regression tests for the validation bug where the background step was
    incorrectly reported as incomplete even after the player supplied a valid
    background_skill_replacement.

    Root cause: the validator was checking
      ``choices.get("background_skill_replacement")`` (wrong key, never set)
    instead of
      ``info.get("already_chosen")`` from get_background_skill_replacement_info().

    Scenario: Cleric picks History + Religion as class skills, then takes Sage
    background which grants Arcana + History.  History overlaps → 1 replacement
    needed.  Player picks Athletics.
    """

    def _cleric_sage_choices(self):
        """Cleric with History + Religion class skills and Sage background."""
        return {
            "character_name": "Regdar the Scholar",
            "level": 1,
            "species": "Human",
            "class": "Cleric",
            "background": "Sage",
            "skill_choices": ["History", "Religion"],
            "ability_scores": {
                "Strength": 10, "Dexterity": 12, "Constitution": 13,
                "Intelligence": 12, "Wisdom": 16, "Charisma": 10,
            },
            "background_bonuses": {"Constitution": 1, "Intelligence": 2},
        }

    # ---- overlap detection -------------------------------------------------

    def test_cleric_sage_overlap_detected(self):
        """Cleric(History+Religion) + Sage(Arcana+History): History overlap triggers needed=1."""
        builder = CharacterBuilder()
        builder.apply_choices(self._cleric_sage_choices())

        info = builder.get_background_skill_replacement_info()
        assert info["needed"] > 0, (
            f"Expected needed > 0 for History overlap, got {info['needed']}"
        )

    # ---- replacement resolves the choice -----------------------------------

    def test_already_chosen_populated_after_replacement(self):
        """After apply_choices with replacement, already_chosen is non-empty.

        This directly covers the fixed bug: the old code checked the wrong key
        and always saw an empty value, so it incorrectly kept reporting the
        background step as incomplete.
        """
        builder = CharacterBuilder()
        builder.apply_choices({
            **self._cleric_sage_choices(),
            "background_skill_replacements": ["Athletics"],
        })

        info = builder.get_background_skill_replacement_info()
        assert info["already_chosen"], (
            "already_chosen should be non-empty after providing the replacement — "
            "empty means the validator would (incorrectly) flag the background step "
            "as incomplete, which is the regression being guarded here"
        )
        assert "Athletics" in info["already_chosen"]

    def test_replacement_skill_in_final_character(self):
        """After replacement, Athletics appears in the character's skill proficiencies."""
        builder = CharacterBuilder()
        builder.apply_choices({
            **self._cleric_sage_choices(),
            "background_skill_replacements": ["Athletics"],
        })
        character = builder.to_character()

        skills = character.get("skill_proficiencies", [])
        assert "Athletics" in skills, (
            f"Replacement skill Athletics should be in skill_proficiencies, got: {skills}"
        )
        # The duplicate History should not appear twice
        assert skills.count("History") == 1, (
            f"History should appear exactly once, got: {skills}"
        )
        # Arcana from Sage should be present (non-overlapping background skill)
        assert "Arcana" in skills, (
            f"Arcana (non-overlapping Sage skill) should be present, got: {skills}"
        )

    def test_total_distinct_skills_after_replacement(self):
        """Cleric(2 class skills) + Sage(2 background skills, 1 overlap) → 4 distinct skills."""
        builder = CharacterBuilder()
        builder.apply_choices({
            **self._cleric_sage_choices(),
            "background_skill_replacements": ["Athletics"],
        })
        character = builder.to_character()

        skills = character.get("skill_proficiencies", [])
        assert len(set(skills)) == len(skills), f"Duplicate skills found: {skills}"
        # History (class), Religion (class), Arcana (bg), Athletics (bg replacement)
        for expected in ("History", "Religion", "Arcana", "Athletics"):
            assert expected in skills, f"Expected '{expected}' in {skills}"

    # ---- API validation regression -----------------------------------------

    def test_api_background_step_complete_after_replacement(self, client):
        """POST /api/v1/character/validate must report background step complete
        once background_skill_replacements has been supplied.

        This is the exact API-level regression: before the fix the validator
        used the wrong key and always reported background as incomplete even
        when the player had already made the replacement choice.
        """
        choices_made = {
            **self._cleric_sage_choices(),
            "background_skill_replacements": ["Athletics"],
        }
        response = client.post(
            "/api/v1/character/validate",
            json={"choices_made": choices_made},
        )
        assert response.status_code == 200
        data = response.get_json()

        steps_by_name = {s["step"]: s for s in data["steps"]}
        background_status = steps_by_name.get("background", {})
        assert background_status.get("complete"), (
            "background step should be complete after providing background_skill_replacements; "
            f"missing keys: {background_status.get('missing', [])}"
        )
        assert "background_skill_replacement" not in background_status.get("missing", []), (
            "background_skill_replacement should not appear in missing keys "
            "when already_chosen is populated — this is the fixed regression"
        )

    def test_api_background_step_incomplete_without_replacement(self, client):
        """POST /api/v1/character/validate must report background step incomplete
        when a replacement is needed but has not been provided.
        """
        choices_made = self._cleric_sage_choices()  # no replacement key
        response = client.post(
            "/api/v1/character/validate",
            json={"choices_made": choices_made},
        )
        assert response.status_code == 200
        data = response.get_json()

        steps_by_name = {s["step"]: s for s in data["steps"]}
        background_status = steps_by_name.get("background", {})
        assert not background_status.get("complete"), (
            "background step should be incomplete when replacement not yet chosen"
        )
        assert "background_skill_replacement" in background_status.get("missing", []), (
            "background_skill_replacement should be listed in missing keys "
            f"when the overlap is unresolved; status={background_status}"
        )



class TestGrantOriginFeatEffect:
    """Phase 9 (D1-1): the ``grant_origin_feat`` effect handler must work in
    both shapes:

      * ``{type: grant_origin_feat, feat: "<feat name>"}`` — names the feat
        explicitly. Used by every background (e.g. Acolyte → Magic Initiate
        (Cleric)) and by Human's species feat choice cells.
      * ``{type: grant_origin_feat}`` — no feat name. Used by the warlock
        invocation *Lessons of the First Ones* and by other "pick an Origin
        feat" prompts where the player chooses the feat downstream. The
        handler must apply the entry as a no-op direct grant so the
        downstream choice flow can resolve it.
    """

    def test_grant_origin_feat_with_feat_field_grants_named_feat(self):
        builder = CharacterBuilder()
        # Apply the effect directly with source_type="background" — mirrors
        # what _apply_background_features does with the canonical effects
        # array.
        builder._apply_effect(
            {"type": "grant_origin_feat", "feat": "Alert"},
            "TestBackground",
            "background",
        )
        feat_names = [f["name"] for f in builder.character_data["features"]["feats"]]
        assert "Alert" in feat_names

    def test_grant_origin_feat_without_feat_field_is_safe_noop(self):
        builder = CharacterBuilder()
        before = len(builder.character_data["features"]["feats"])
        # The Lessons of the First Ones case: no ``feat`` key. The handler
        # must not crash and must not add a phantom entry — the player will
        # pick the feat through the downstream choice flow.
        builder._apply_effect(
            {"type": "grant_origin_feat"},
            "Lessons of the First Ones",
            "invocation",
        )
        after = len(builder.character_data["features"]["feats"])
        assert after == before
