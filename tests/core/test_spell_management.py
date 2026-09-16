#!/usr/bin/env python3
"""
Unit tests for spell management system.

Tests spell selection, preparation, spell level organization,
and the effects-based spell granting system (grant_spell, grant_cantrip).
"""

import pytest
from modules.character_builder import CharacterBuilder, SelectionValidationError
from modules.derived_stats import ORDINAL_TO_INT


class TestSpellManagement:
    """Test spell selection, preparation, and organization."""

    @pytest.fixture
    def cleric_builder(self):
        """Create a Cleric for testing spell management."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Test Cleric",
            "species": "Human",
            "class": "Cleric",
            "level": 3,
            "subclass": "Light Domain",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 12,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 16,
                "Charisma": 12,
            },
            "skill_choices": ["Insight", "Religion"],
            "Divine Order": "Thaumaturge",
            "Thaumaturge_bonus_cantrip": "Guidance",
        }
        builder.apply_choices(choices)
        return builder

    @pytest.fixture
    def wizard_builder(self):
        """Create a Wizard for testing spell preparation."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Test Wizard",
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
        }
        builder.apply_choices(choices)
        return builder

    def test_domain_spells_always_prepared(self, cleric_builder):
        """Test Light Domain spells are always prepared."""
        char_data = cleric_builder.to_character()
        spells_by_level = char_data.get("spells_by_level", {})

        # Check for Light Domain level 1 spells
        level_1_spells = spells_by_level.get(1, [])
        level_1_names = [spell["name"] for spell in level_1_spells]

        assert "Burning Hands" in level_1_names
        assert "Faerie Fire" in level_1_names

        # Verify they're marked as always prepared
        for spell in level_1_spells:
            if spell["name"] in ["Burning Hands", "Faerie Fire"]:
                assert spell.get("always_prepared") is True
                assert spell.get("source") == "Light Domain"

    def test_spell_level_organization(self, cleric_builder):
        """Test spells are organized by their correct spell level."""
        # Advance to level 7 to get higher level spells
        builder = CharacterBuilder()
        choices = {
            "character_name": "Test Cleric",
            "species": "Human",
            "class": "Cleric",
            "level": 7,
            "subclass": "Light Domain",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 12,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 16,
                "Charisma": 12,
            },
            "skill_choices": ["Insight", "Religion"],
            "Divine Order": "Thaumaturge",
            "Thaumaturge_bonus_cantrip": "Guidance",
        }
        builder.apply_choices(choices)

        char_data = builder.to_character()
        spells_by_level = char_data.get("spells_by_level", {})

        # Check cantrips (level 0)
        cantrips = spells_by_level.get(0, [])
        assert len(cantrips) > 0
        for spell in cantrips:
            assert spell.get("level") == 0

        # Check level 1 spells
        level_1 = spells_by_level.get(1, [])
        level_1_names = [s["name"] for s in level_1]
        assert "Burning Hands" in level_1_names
        assert "Faerie Fire" in level_1_names
        for spell in level_1:
            assert spell.get("level") == 1

        # Check level 2 spells (should include Scorching Ray, See Invisibility)
        level_2 = spells_by_level.get(2, [])
        level_2_names = [s["name"] for s in level_2]
        assert "Scorching Ray" in level_2_names
        assert "See Invisibility" in level_2_names
        for spell in level_2:
            assert spell.get("level") == 2

        # Check level 3 spells (should include Daylight, Fireball at level 5+)
        level_3 = spells_by_level.get(3, [])
        level_3_names = [s["name"] for s in level_3]
        assert "Daylight" in level_3_names
        assert "Fireball" in level_3_names
        for spell in level_3:
            assert spell.get("level") == 3

        # Check level 4 spells (should include Arcane Eye, Wall of Fire at level 7+)
        level_4 = spells_by_level.get(4, [])
        level_4_names = [s["name"] for s in level_4]
        assert "Arcane Eye" in level_4_names
        assert "Wall of Fire" in level_4_names
        for spell in level_4:
            assert spell.get("level") == 4

    def test_grant_spell_effect_with_min_level(self):
        """Test grant_spell effects only apply at min_level."""
        # Level 2 Cleric shouldn't have Light Domain spells yet (requires level 3)
        builder = CharacterBuilder()
        choices = {
            "character_name": "Low Level Cleric",
            "species": "Human",
            "class": "Cleric",
            "level": 2,
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 12,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 16,
                "Charisma": 12,
            },
            "skill_choices": ["Insight", "Religion"],
            "Divine Order": "Thaumaturge",
            "Thaumaturge_bonus_cantrip": "Guidance",
        }
        builder.apply_choices(choices)

        char_data = builder.to_character()
        spells = char_data.get("spells", {})

        # Shouldn't have Light Domain spells yet (requires subclass at level 3)
        always_prepared = spells.get("always_prepared", {})
        assert "Burning Hands" not in always_prepared

    def test_spell_selection_storage(self, wizard_builder):
        """Test spell selections are stored correctly."""
        # Add prepared spells
        wizard_builder.character_data["spells"]["prepared"]["spells"][
            "Detect Magic"
        ] = {}
        wizard_builder.character_data["spells"]["prepared"]["spells"][
            "Magic Missile"
        ] = {}

        char_data = wizard_builder.to_character()
        spells_by_level = char_data.get("spells_by_level", {})

        level_1_spells = spells_by_level.get(1, [])
        level_1_names = [s["name"] for s in level_1_spells]

        assert "Detect Magic" in level_1_names
        assert "Magic Missile" in level_1_names

    def test_spell_export_import(self):
        """Test spell selections survive export/import."""
        # Create character with spell selections
        builder = CharacterBuilder()
        choices = {
            "character_name": "Test Wizard",
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
                "spells": ["Detect Magic", "Magic Missile"],
                "background_cantrips": [],
                "background_spells": [],
            },
        }
        builder.apply_choices(choices)

        # Export
        exported = builder.to_json()
        assert "spell_selections" in exported["choices_made"]

        # Reimport
        builder2 = CharacterBuilder()
        builder2.apply_choices(exported["choices_made"])

        char_data = builder2.to_character()
        spells_by_level = char_data.get("spells_by_level", {})
        level_1_spells = spells_by_level.get(1, [])
        level_1_names = [s["name"] for s in level_1_spells]

        assert "Detect Magic" in level_1_names
        assert "Magic Missile" in level_1_names

    def test_spellcasting_stats_calculation(self, cleric_builder):
        """Test spellcasting statistics are calculated correctly."""
        stats = cleric_builder.calculate_spellcasting_stats()

        assert stats["has_spellcasting"] is True
        assert stats["spellcasting_ability"] == "Wisdom"
        assert stats["spellcasting_modifier"] == 3  # +3 from WIS 16
        assert stats["spell_save_dc"] == 13  # 8 + prof(2) + mod(3)
        assert stats["spell_attack_bonus"] == 5  # prof(2) + mod(3)

    def test_cantrip_count_progression(self):
        """Test cantrip slots increase with level."""
        test_levels = [
            (1, 3),  # Level 1 Cleric: 3 cantrips
            (4, 4),  # Level 4 Cleric: 4 cantrips
            (10, 5),  # Level 10 Cleric: 5 cantrips
        ]

        for level, expected_cantrips in test_levels:
            builder = CharacterBuilder()
            choices = {
                "character_name": "Test Cleric",
                "species": "Human",
                "class": "Cleric",
                "level": level,
                "background": "Acolyte",
                "ability_scores": {
                    "Strength": 10,
                    "Dexterity": 12,
                    "Constitution": 14,
                    "Intelligence": 10,
                    "Wisdom": 16,
                    "Charisma": 12,
                },
                "skill_choices": ["Insight", "Religion"],
                "Divine Order": "Thaumaturge",
                "Thaumaturge_bonus_cantrip": "Guidance",
            }
            builder.apply_choices(choices)

            stats = builder.calculate_spellcasting_stats()
            assert stats["max_cantrips"] >= expected_cantrips, (
                f"Level {level} should have at least {expected_cantrips} cantrips"
            )

    def test_bard_cantrip_count_progression(self):
        """Test Bard cantrip count reads cantrips_by_level (not cantrip_progression)."""
        test_levels = [
            (1, 2),   # Level 1 Bard: 2 cantrips
            (4, 3),   # Level 4 Bard: 3 cantrips
            (10, 4),  # Level 10 Bard: 4 cantrips
        ]

        for level, expected_cantrips in test_levels:
            builder = CharacterBuilder()
            choices = {
                "character_name": "Test Bard",
                "species": "Human",
                "class": "Bard",
                "level": level,
                "background": "Entertainer",
                "ability_scores": {
                    "Strength": 8,
                    "Dexterity": 14,
                    "Constitution": 12,
                    "Intelligence": 10,
                    "Wisdom": 10,
                    "Charisma": 16,
                },
                "skill_choices": ["Perception", "Persuasion", "Performance"],
            }
            builder.apply_choices(choices)

            stats = builder.calculate_spellcasting_stats()
            assert stats["max_cantrips_prepared"] == expected_cantrips, (
                f"Level {level} Bard should have {expected_cantrips} cantrips, "
                f"got {stats['max_cantrips_prepared']}"
            )

    def test_spell_selections_reject_unavailable_spell(self, wizard_builder):
        with pytest.raises(SelectionValidationError) as exc:
            wizard_builder.apply_choice(
                "spell_selections",
                {
                    "cantrips": [],
                    "spells": ["Cure Wounds"],
                    "background_cantrips": [],
                    "background_spells": [],
                },
            )
        assert exc.value.family == "spell_selections"
        assert exc.value.code == "invalid_selection"

    def test_spell_selections_reject_exceeding_limit(self, wizard_builder):
        with pytest.raises(SelectionValidationError) as exc:
            wizard_builder.apply_choice(
                "spell_selections",
                {
                    "cantrips": ["Fire Bolt", "Light", "Mage Hand", "Ray of Frost"],
                    "spells": [],
                    "background_cantrips": [],
                    "background_spells": [],
                },
            )
        assert any(v.get("reason") == "max_exceeded" for v in exc.value.violations)

    def test_spell_selections_reject_background_spells_without_requirement(self, wizard_builder):
        with pytest.raises(SelectionValidationError) as exc:
            wizard_builder.apply_choice(
                "spell_selections",
                {
                    "cantrips": [],
                    "spells": [],
                    "background_cantrips": [],
                    "background_spells": ["Magic Missile"],
                },
            )
        assert exc.value.family == "spell_selections"
        assert any(
            v.get("field") == "spell_selections.background_spells"
            for v in exc.value.violations
        )

    def test_prepared_spell_limit(self, cleric_builder):
        """Test prepared spell limit calculation."""
        stats = cleric_builder.calculate_spellcasting_stats()

        # Cleric: Level + WIS modifier (includes always_prepared spells)
        # At level 3 with Light Domain, has several always prepared spells
        assert stats["max_prepared_spells"] > 0
        assert isinstance(stats["max_prepared_spells"], int)

    def test_spell_slots_by_level(self, cleric_builder):
        """Test spell slots is defined in class data."""
        # Check that class data has spell slots defined
        class_data = cleric_builder.character_data.get("class_data", {})
        spell_slots_by_level = class_data.get("spell_slots_by_level", {})

        # Level 3 Cleric should have spell slot definition
        level_3_slots = spell_slots_by_level.get("3")
        assert level_3_slots is not None, "Level 3 should have spell slots defined"
        assert isinstance(level_3_slots, list), "Spell slots should be a list"
        assert len(level_3_slots) == 9, "Should have 9 spell levels (1-9)"

    def test_non_caster_no_spellcasting(self):
        """Test non-caster classes don't have spellcasting stats."""
        builder = CharacterBuilder()
        choices = {
            "character_name": "Test Fighter",
            "species": "Human",
            "class": "Fighter",
            "level": 3,
            "background": "Soldier",
            "ability_scores": {
                "Strength": 16,
                "Dexterity": 14,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 12,
                "Charisma": 10,
            },
            "skill_choices": ["Athletics", "Intimidation"],
            "Fighting Style": "Dueling",
        }
        builder.apply_choices(choices)

        stats = builder.calculate_spellcasting_stats()
        assert stats["has_spellcasting"] is False

    def test_grant_cantrip_effect(self, cleric_builder):
        """Test grant_cantrip effects add cantrips to character."""
        char_data = cleric_builder.to_character()
        spells_by_level = char_data.get("spells_by_level", {})

        cantrips = spells_by_level.get(0, [])
        cantrip_names = [s["name"] for s in cantrips]

        # Should have Guidance from Thaumaturge Divine Order
        # Note: Light Domain does not grant a bonus cantrip in D&D 2024
        assert "Guidance" in cantrip_names

    def test_spell_management_data_loads_definitions(self, wizard_builder):
        """Regression test: spell management data returns actual spell definitions, not 'Unknown'.

        Simulates what api_spell_management_data does after the fix so that the
        spell preparation modal shows real school, casting_time, range, etc.
        """
        stats = wizard_builder.calculate_spellcasting_stats()
        assert stats["has_spellcasting"] is True

        # Simulate what the route now does for available cantrips
        available_cantrips = [
            wizard_builder._load_spell_definition(name)
            for name in stats.get("available_cantrips", [])
        ]
        assert len(available_cantrips) > 0, "Wizard should have available cantrips"

        for spell_def in available_cantrips:
            assert "name" in spell_def
            assert "school" in spell_def, (
                f"Spell '{spell_def['name']}' should have 'school' field"
            )
            assert spell_def["school"] != "Unknown", (
                f"Spell '{spell_def['name']}' should have actual school, not 'Unknown'"
            )

        # Simulate what the route does for available leveled spells
        available_spells = {}
        for level, spell_names in stats.get("available_spells", {}).items():
            available_spells[str(level)] = [
                wizard_builder._load_spell_definition(name)
                for name in spell_names
            ]

        level_1 = available_spells.get("1", [])
        assert len(level_1) > 0, "Wizard should have level 1 spells available"

        for spell_def in level_1:
            assert "school" in spell_def, (
                f"Spell '{spell_def['name']}' should have 'school' field"
            )
            assert spell_def["school"] != "Unknown", (
                f"Spell '{spell_def['name']}' should have actual school, not 'Unknown'"
            )

    # -----------------------------------------------------------------------
    # Tests for spell slot level filtering (issue: modal allowed spells above
    # the character's available slot levels)
    # -----------------------------------------------------------------------

    def test_level1_wizard_only_has_1st_level_slots(self):
        """A level 1 Wizard should only have 1st-level spell slots."""
        builder = CharacterBuilder()
        builder.apply_choices(
            {
                "character_name": "Baby Wizard",
                "species": "Human",
                "class": "Wizard",
                "level": 1,
                "background": "Sage",
                "ability_scores": {
                    "Strength": 8,
                    "Dexterity": 14,
                    "Constitution": 13,
                    "Intelligence": 16,
                    "Wisdom": 12,
                    "Charisma": 10,
                },
                "background_bonuses": {"Intelligence": 2, "Wisdom": 1},
            }
        )
        character = builder.to_character()
        spell_slots = character.get("spell_slots", {})

        # Only 1st-level slots should be present (non-zero)
        assert "1st" in spell_slots and spell_slots["1st"] > 0
        # No higher-level slots for a level 1 Wizard
        for high_level in ["2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"]:
            assert high_level not in spell_slots or spell_slots[high_level] == 0

    def test_available_spells_is_capped_to_accessible_levels(self):
        """calculate_spellcasting_stats() should only expose spell levels the character can cast."""
        builder = CharacterBuilder()
        builder.apply_choices(
            {
                "character_name": "Baby Wizard",
                "species": "Human",
                "class": "Wizard",
                "level": 3,
                "background": "Sage",
                "ability_scores": {
                    "Strength": 8,
                    "Dexterity": 14,
                    "Constitution": 13,
                    "Intelligence": 16,
                    "Wisdom": 12,
                    "Charisma": 10,
                },
                "background_bonuses": {"Intelligence": 2, "Wisdom": 1},
            }
        )
        stats = builder.calculate_spellcasting_stats()

        available_spells = stats.get("available_spells", {})
        levels_in_list = {int(k) for k in available_spells}
        assert levels_in_list == {1, 2}

    def test_slot_filtering_removes_unavailable_levels(self):
        """Verify the filtering logic used in the route correctly narrows down
        available_spells to only levels the character has slots for."""
        builder = CharacterBuilder()
        builder.apply_choices(
            {
                "character_name": "Baby Wizard",
                "species": "Human",
                "class": "Wizard",
                "level": 1,
                "background": "Sage",
                "ability_scores": {
                    "Strength": 8,
                    "Dexterity": 14,
                    "Constitution": 13,
                    "Intelligence": 16,
                    "Wisdom": 12,
                    "Charisma": 10,
                },
                "background_bonuses": {"Intelligence": 2, "Wisdom": 1},
            }
        )
        character = builder.to_character()
        spell_slots = character.get("spell_slots", {})
        stats = builder.calculate_spellcasting_stats()

        # Replicate the route filtering logic
        available_slot_levels = {
            ORDINAL_TO_INT[name]
            for name in spell_slots
            if name in ORDINAL_TO_INT and spell_slots[name] > 0
        }

        # Build available_spells as the route does (string keys)
        raw_available = {
            str(level): spells
            for level, spells in stats.get("available_spells", {}).items()
        }

        # Apply filtering
        filtered = {
            level: spells
            for level, spells in raw_available.items()
            if int(level) in available_slot_levels
        }

        # Level 1 Wizard only has 1st-level slots → only "1" should survive
        assert set(filtered.keys()) == {"1"}, (
            f"Expected only '1' but got {set(filtered.keys())}"
        )

    def test_level3_wizard_has_1st_and_2nd_level_spells_after_filtering(self):
        """A level 3 Wizard with 1st and 2nd-level slots should see spells up to level 2."""
        builder = CharacterBuilder()
        builder.apply_choices(
            {
                "character_name": "Apprentice Wizard",
                "species": "Human",
                "class": "Wizard",
                "level": 3,
                "background": "Sage",
                "ability_scores": {
                    "Strength": 8,
                    "Dexterity": 14,
                    "Constitution": 13,
                    "Intelligence": 16,
                    "Wisdom": 12,
                    "Charisma": 10,
                },
                "background_bonuses": {"Intelligence": 2, "Wisdom": 1},
            }
        )
        character = builder.to_character()
        spell_slots = character.get("spell_slots", {})

        # Level 3 Wizard has both 1st and 2nd-level slots
        assert "1st" in spell_slots and spell_slots["1st"] > 0
        assert "2nd" in spell_slots and spell_slots["2nd"] > 0

        # Apply filtering
        available_slot_levels = {
            ORDINAL_TO_INT[name]
            for name in spell_slots
            if name in ORDINAL_TO_INT and spell_slots[name] > 0
        }
        stats = builder.calculate_spellcasting_stats()
        raw_available = {
            str(level): spells
            for level, spells in stats.get("available_spells", {}).items()
        }
        filtered = {
            level: spells
            for level, spells in raw_available.items()
            if int(level) in available_slot_levels
        }

        # Should include levels 1 and 2, but NOT 3+
        assert "1" in filtered
        assert "2" in filtered
        assert "3" not in filtered


# ---------------------------------------------------------------------------
# Concentration flag tests
# ---------------------------------------------------------------------------


class TestConcentrationFlag:
    """Tests for the `concentration` boolean field on spell objects.

    _load_spell_definition() derives this flag by checking whether the
    spell's `duration` string starts with "Concentration".  The field
    must flow through to every spell object in spells_by_level.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _builder() -> CharacterBuilder:
        return CharacterBuilder()

    # ------------------------------------------------------------------
    # Unit-level: _load_spell_definition() sets the flag correctly
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "spell_name,expected_concentration",
        [
            # Concentration spells (duration starts with "Concentration")
            ("Bless", True),           # "Concentration, up to 1 minute"
            ("Hold Person", True),     # "Concentration, up to 1 minute"
            ("Faerie Fire", True),     # "Concentration, up to 1 minute"
            # Non-concentration spells
            ("Alarm", False),          # "8 hours"
            ("Acid Splash", False),    # "Instantaneous"
        ],
    )
    def test_concentration_flag_from_load_spell_definition(
        self, spell_name: str, expected_concentration: bool
    ):
        """_load_spell_definition() derives `concentration` correctly from the duration field."""
        builder = self._builder()
        spell = builder._load_spell_definition(spell_name)

        assert "concentration" in spell, (
            f"'concentration' key missing from spell object for '{spell_name}'"
        )
        assert spell["concentration"] is expected_concentration, (
            f"Expected concentration={expected_concentration} for '{spell_name}' "
            f"(duration={spell.get('duration')!r}), got {spell['concentration']}"
        )

    def test_concentration_flag_true(self):
        """Positive test: a known concentration spell has concentration=True."""
        builder = self._builder()
        # Bless: "Concentration, up to 1 minute"
        spell = builder._load_spell_definition("Bless")
        assert spell["concentration"] is True

    def test_concentration_flag_false(self):
        """Negative test: a known non-concentration spell has concentration=False."""
        builder = self._builder()
        # Alarm: "8 hours"
        spell = builder._load_spell_definition("Alarm")
        assert spell["concentration"] is False

    def test_concentration_absent_source_returns_false(self):
        """A spell with no matching file gets a fallback object with concentration=False."""
        builder = self._builder()
        result = builder._load_spell_definition("__nonexistent_spell_xyz__")
        # The fallback dict must still carry the key and default to False
        assert "concentration" in result
        assert result["concentration"] is False

    # ------------------------------------------------------------------
    # Stacking / caching: loading the same spell twice is idempotent
    # ------------------------------------------------------------------

    def test_concentration_flag_cached_result_is_consistent(self):
        """Repeated calls for the same spell return the same concentration value."""
        builder = self._builder()
        first = builder._load_spell_definition("Bless")
        second = builder._load_spell_definition("Bless")
        assert first["concentration"] is True
        assert second["concentration"] is True
        assert first["concentration"] == second["concentration"]

    # ------------------------------------------------------------------
    # Integration: flag flows into to_character() → spells_by_level
    # ------------------------------------------------------------------

    @pytest.fixture
    def light_domain_cleric_character(self):
        """Level-3 Light Domain Cleric whose domain spells include Faerie Fire (concentration)."""
        builder = CharacterBuilder()
        builder.apply_choices(
            {
                "character_name": "Test Cleric",
                "species": "Human",
                "class": "Cleric",
                "level": 3,
                "subclass": "Light Domain",
                "background": "Acolyte",
                "ability_scores": {
                    "Strength": 10,
                    "Dexterity": 12,
                    "Constitution": 14,
                    "Intelligence": 10,
                    "Wisdom": 16,
                    "Charisma": 12,
                },
                "background_bonuses": {"Wisdom": 2, "Constitution": 1},
                "skill_choices": ["Insight", "Religion"],
                "Divine Order": "Thaumaturge",
                "Thaumaturge_bonus_cantrip": "Guidance",
            }
        )
        return builder.to_character()

    def test_concentration_in_to_character(self, light_domain_cleric_character):
        """A concentration domain spell in spells_by_level has concentration=True."""
        spells_by_level = light_domain_cleric_character.get("spells_by_level", {})

        # Light Domain grants Faerie Fire (level-1, concentration) always-prepared
        level_1_spells = spells_by_level.get(1, [])
        faerie_fire = next(
            (s for s in level_1_spells if s.get("name") == "Faerie Fire"), None
        )
        assert faerie_fire is not None, (
            "Faerie Fire not found in spells_by_level[1] for Light Domain Cleric; "
            f"found: {[s.get('name') for s in level_1_spells]}"
        )
        assert "concentration" in faerie_fire, (
            "Faerie Fire spell object is missing the 'concentration' key in spells_by_level"
        )
        assert faerie_fire["concentration"] is True, (
            f"Expected Faerie Fire to have concentration=True, got {faerie_fire['concentration']!r}"
        )

    def test_non_concentration_spell_in_to_character(self, light_domain_cleric_character):
        """A non-concentration domain spell in spells_by_level has concentration=False."""
        spells_by_level = light_domain_cleric_character.get("spells_by_level", {})

        # Light Domain grants Burning Hands (level-1, instantaneous) always-prepared
        level_1_spells = spells_by_level.get(1, [])
        burning_hands = next(
            (s for s in level_1_spells if s.get("name") == "Burning Hands"), None
        )
        assert burning_hands is not None, (
            "Burning Hands not found in spells_by_level[1] for Light Domain Cleric; "
            f"found: {[s.get('name') for s in level_1_spells]}"
        )
        assert "concentration" in burning_hands, (
            "Burning Hands spell object is missing the 'concentration' key in spells_by_level"
        )
        assert burning_hands["concentration"] is False, (
            f"Expected Burning Hands to have concentration=False, got {burning_hands['concentration']!r}"
        )

    def test_all_spells_in_spells_by_level_have_concentration_key(
        self, light_domain_cleric_character
    ):
        """Every spell in every level of spells_by_level carries the `concentration` key."""
        spells_by_level = light_domain_cleric_character.get("spells_by_level", {})
        missing = []
        for level, spells in spells_by_level.items():
            for spell in spells:
                if "concentration" not in spell:
                    missing.append((level, spell.get("name")))
        assert missing == [], (
            f"The following spells are missing the 'concentration' key: {missing}"
        )
