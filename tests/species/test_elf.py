#!/usr/bin/env python3
"""
Unit tests for the Elf species implementation.
Tests all features, effects, lineages, and mechanics specific to the Elf species.
"""

import pytest
from modules.character_builder import CharacterBuilder
from modules.variant_manager import VariantManager


@pytest.fixture
def elf_builder():
    """Fixture providing a fresh CharacterBuilder with Elf species setup"""
    builder = CharacterBuilder()
    builder.set_species("Elf")
    return builder


@pytest.fixture
def variant_manager():
    """Fixture providing a VariantManager instance"""
    return VariantManager()


class TestElfSpecies:
    """Test base Elf species implementation"""

    def test_elf_basic_traits(self, elf_builder):
        """Test basic elf species setup"""
        char_data = elf_builder.character_data

        # Check basic species properties
        assert char_data["species"] == "Elf"
        assert char_data["speed"] == 30
        assert char_data["darkvision"] == 60

        # Check languages
        languages = char_data["proficiencies"]["languages"]
        assert "Common" in languages
        assert "Elvish" not in languages

    def test_elf_features_present(self, elf_builder):
        """Test that all elf features are present"""
        char_data = elf_builder.character_data
        species_features = char_data["features"]["species"]
        feature_names = [f["name"] for f in species_features]

        # All elf features should be present
        assert "Darkvision" in feature_names
        assert "Elven Lineage" in feature_names
        assert "Fey Ancestry" in feature_names
        assert "Keen Senses" in feature_names
        assert "Trance" in feature_names

    def test_darkvision_feature(self, elf_builder):
        """Test Darkvision feature implementation"""
        char_data = elf_builder.character_data

        # Check darkvision range is set correctly
        assert char_data["darkvision"] == 60

        # Check feature description
        species_features = char_data["features"]["species"]
        darkvision_feature = None
        for feature in species_features:
            if feature["name"] == "Darkvision":
                darkvision_feature = feature
                break

        assert darkvision_feature is not None
        description = darkvision_feature["description"]
        assert "Darkvision" in description
        assert "60 feet" in description

    def test_fey_ancestry_effects(self, elf_builder):
        """Test Fey Ancestry effects application"""

        # Check applied effects
        applied_effects = getattr(elf_builder, "applied_effects", [])

        # Should have save advantage effect
        save_advantage_effect = None
        for effect_data in applied_effects:
            effect = effect_data["effect"]
            if effect.get("type") == "grant_save_advantage":
                save_advantage_effect = effect
                break

        assert save_advantage_effect is not None
        assert save_advantage_effect["condition"] == "Charmed"
        assert save_advantage_effect["display"] == "Advantage vs Charmed condition"

    def test_keen_senses_choice(self, elf_builder):
        """Test Keen Senses choice structure"""
        char_data = elf_builder.character_data
        species_features = char_data["features"]["species"]

        keen_senses_feature = None
        for feature in species_features:
            if feature["name"] == "Keen Senses":
                keen_senses_feature = feature
                break

        assert keen_senses_feature is not None
        # Should have choice structure (handled by front-end)
        description = keen_senses_feature["description"]
        assert "Insight" in description
        assert "Perception" in description
        assert "Survival" in description

    def test_keen_senses_skill_proficiency_choice(self):
        """Test that Keen Senses grants proficiency in the chosen skill"""
        # Test each possible skill choice
        skill_choices = ["Insight", "Perception", "Survival"]

        for chosen_skill in skill_choices:
            builder = CharacterBuilder()
            builder.set_species("Elf")

            # Get initial proficiencies
            builder.character_data["proficiencies"]["skills"].copy()

            # Apply the Keen Senses choice using the existing choice system
            result = builder.apply_choice("Keen Senses", chosen_skill)

            # Check if the choice was stored
            char_data = builder.character_data
            choices_made = char_data.get("choices_made", {})

            # The choice should be recorded
            assert "Keen Senses" in choices_made
            assert choices_made["Keen Senses"] == chosen_skill

            # The skill proficiency should be granted
            skill_proficiencies = char_data["proficiencies"]["skills"]
            assert chosen_skill in skill_proficiencies, (
                f"Should have proficiency in {chosen_skill}"
            )

            # Verify the choice was successful
            assert result is True

    def test_keen_senses_proficiency_source_tracking(self):
        """Test that Keen Senses skill proficiency source is tracked correctly"""
        builder = CharacterBuilder()
        builder.set_species("Elf")

        # Apply the Keen Senses choice
        result = builder.apply_choice("Keen Senses", "Insight")
        assert result is True

        # Check that the proficiency source is tracked
        char_data = builder.character_data
        proficiency_sources = char_data.get("proficiency_sources", {}).get("skills", {})

        assert "Insight" in proficiency_sources
        assert proficiency_sources["Insight"] == "Elf"

    def test_keen_senses_choice_display_update(self):
        """Test that Keen Senses feature display is updated when choice is made"""
        builder = CharacterBuilder()
        builder.set_species("Elf")

        # Apply a choice
        result = builder.apply_choice("Keen Senses", "Perception")
        assert result is True

        # Check that the feature display name is updated
        char_data = builder.character_data
        species_features = char_data["features"]["species"]

        keen_senses_feature = None
        for feature in species_features:
            if "Keen Senses" in feature["name"]:
                keen_senses_feature = feature
                break

        assert keen_senses_feature is not None
        # The feature name should include the choice made
        assert "Perception" in keen_senses_feature["name"]

    def test_elven_lineage_choice(self, elf_builder):
        """Test Elven Lineage choice structure"""
        char_data = elf_builder.character_data
        species_features = char_data["features"]["species"]

        lineage_feature = None
        for feature in species_features:
            if feature["name"] == "Elven Lineage":
                lineage_feature = feature
                break

        assert lineage_feature is not None
        description = lineage_feature["description"]
        assert "Intelligence" in description
        assert "Wisdom" in description
        assert "Charisma" in description

    def test_trance_feature(self, elf_builder):
        """Test Trance feature details"""
        char_data = elf_builder.character_data
        species_features = char_data["features"]["species"]

        trance_feature = None
        for feature in species_features:
            if feature["name"] == "Trance":
                trance_feature = feature
                break

        assert trance_feature is not None
        description = trance_feature["description"]

        # Check key elements of Trance
        assert "don't need to sleep" in description
        assert "4 hours" in description
        assert "Long Rest" in description
        assert "trancelike meditation" in description
        assert "retain consciousness" in description


class TestElfLineages:
    """Test Elf lineage/variant implementations"""

    def test_elf_has_lineages(self, variant_manager):
        """Test that elf has available lineages"""
        assert variant_manager.has_variants("Elf")
        lineages = variant_manager.get_available_variants("Elf")

        # Check expected lineages
        assert "High Elf" in lineages
        assert "Wood Elf" in lineages
        assert "Drow" in lineages
        assert len(lineages) >= 3

    def test_high_elf_lineage(self):
        """Test High Elf lineage implementation"""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        result = builder.set_lineage("High Elf", "Intelligence")
        builder.apply_choice("High Elf Cantrip", "Prestidigitation")

        assert result is True
        char_data = builder.character_data

        # Basic properties
        assert char_data["species"] == "Elf"
        assert char_data["lineage"] == "High Elf"
        assert char_data["darkvision"] == 60  # Base elf darkvision
        assert char_data["speed"] == 30  # Base elf speed

        # Check applied effects (Fey Ancestry + High Elf Spells)
        applied_effects = getattr(builder, "applied_effects", [])
        effect_types = [e["effect"]["type"] for e in applied_effects]

        assert "grant_save_advantage" in effect_types  # Fey Ancestry
        assert "grant_cantrip" in effect_types  # Prestidigitation
        assert "grant_spell" in effect_types  # Detect Magic, Misty Step

        # Phase 9: Darkvision now contributes a grant_darkvision effect
        # (Fey Ancestry + Darkvision + cantrip + 2 spells = 5).
        assert len(applied_effects) == 5

    def test_wood_elf_lineage(self):
        """Test Wood Elf lineage implementation"""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        result = builder.set_lineage("Wood Elf", "Wisdom")

        assert result is True
        char_data = builder.character_data

        # Basic properties
        assert char_data["species"] == "Elf"
        assert char_data["lineage"] == "Wood Elf"
        assert char_data["darkvision"] == 60  # Base elf darkvision
        assert char_data["speed"] == 35  # Increased speed

        # Check applied effects (Fey Ancestry + Wood Elf Spells)
        applied_effects = getattr(builder, "applied_effects", [])
        effect_types = [e["effect"]["type"] for e in applied_effects]

        assert "grant_save_advantage" in effect_types  # Fey Ancestry
        assert "grant_cantrip" in effect_types  # Druidcraft
        assert "grant_spell" in effect_types  # Longstrider, Pass without Trace
        assert "increase_speed" in effect_types  # Wood Elf Increased Speed

        # Phase 9: Wood Elf's Increased Speed contributes an ``increase_speed``
        # effect; the base elf darkvision contributes a ``grant_darkvision``
        # effect. Total: Fey Ancestry + base Darkvision + Increased Speed +
        # cantrip + 2 spells = 6.
        assert len(applied_effects) == 6

    def test_drow_lineage(self):
        """Test Drow lineage implementation"""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        result = builder.set_lineage("Drow", "Charisma")

        assert result is True
        char_data = builder.character_data

        # Basic properties
        assert char_data["species"] == "Elf"
        assert char_data["lineage"] == "Drow"
        assert char_data["darkvision"] == 120  # Extended darkvision
        assert char_data["speed"] == 30  # Base elf speed

        # Check applied effects (Fey Ancestry + Drow Spells)
        applied_effects = getattr(builder, "applied_effects", [])
        effect_types = [e["effect"]["type"] for e in applied_effects]

        assert "grant_save_advantage" in effect_types  # Fey Ancestry
        assert "grant_cantrip" in effect_types  # Dancing Lights
        assert "grant_spell" in effect_types  # Faerie Fire, Darkness

        # Phase 9: Drow's Extended Darkvision contributes its own
        # ``grant_darkvision`` (range 120) on top of the base elf
        # ``grant_darkvision`` (range 60). Total: Fey Ancestry + base
        # Darkvision + Extended Darkvision + cantrip + 2 spells = 6.
        assert len(applied_effects) == 6
        darkvision_effects = [
            e for e in applied_effects
            if e["effect"].get("type") == "grant_darkvision"
        ]
        assert len(darkvision_effects) == 2

    def test_lineage_spells_by_level(self):
        """Test lineage spells are available at correct levels"""
        # Test High Elf spells
        builder = CharacterBuilder()
        builder.set_species("Elf")
        builder.set_lineage("High Elf", "Intelligence")
        builder.apply_choice("High Elf Cantrip", "Prestidigitation")

        applied_effects = getattr(builder, "applied_effects", [])
        spell_effects = [
            e
            for e in applied_effects
            if e["effect"]["type"] in ["grant_cantrip", "grant_spell"]
        ]

        # Check spell availability by level
        cantrips = [e for e in spell_effects if e["effect"]["type"] == "grant_cantrip"]
        spells = [e for e in spell_effects if e["effect"]["type"] == "grant_spell"]

        assert len(cantrips) == 1  # Prestidigitation
        assert len(spells) == 2  # Detect Magic (3rd), Misty Step (5th)

        # Check specific spells
        cantrip_names = [e["effect"]["spell"] for e in cantrips]
        spell_names = [e["effect"]["spell"] for e in spells]

        assert "Prestidigitation" in cantrip_names
        assert "Detect Magic" in spell_names
        assert "Misty Step" in spell_names

    def test_high_elf_cantrip_choice_is_available(self):
        """High Elf exposes a selectable lineage cantrip choice."""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        builder.set_lineage("High Elf", "Intelligence")

        trait_choices = builder.get_species_trait_choices()
        assert "High Elf Cantrip" in trait_choices
        options = trait_choices["High Elf Cantrip"]["options"]
        assert "Prestidigitation" in options
        assert "Mage Hand" in options


class TestElfLineageCantrips:
    """Test that elf lineages properly grant cantrips"""

    def test_high_elf_grants_prestidigitation_cantrip(self):
        """Test that High Elf lineage grants Prestidigitation cantrip"""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        result = builder.set_lineage("High Elf", "Intelligence")
        builder.apply_choice("High Elf Cantrip", "Prestidigitation")

        assert result is True
        char_data = builder.character_data

        # Check that Prestidigitation is in cantrips
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Prestidigitation" in always_prepared
        # Verify it came from the correct effect
        applied_effects = getattr(builder, "applied_effects", [])
        cantrip_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_cantrip"
        ]

        prestidigitation_effect = None
        for effect in cantrip_effects:
            if effect["effect"]["spell"] == "Prestidigitation":
                prestidigitation_effect = effect
                break

        assert prestidigitation_effect is not None
        assert prestidigitation_effect["source_type"] == "species_choice"
        assert prestidigitation_effect["source"] == "High Elf Cantrip: Prestidigitation"

    def test_high_elf_cantrip_can_be_swapped(self):
        """Regression for #193: High Elf cantrip choice can replace Prestidigitation."""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        builder.set_lineage("High Elf", "Intelligence")
        builder.apply_choice("High Elf Cantrip", "Mage Hand")

        always_prepared = builder.character_data["spells"]["always_prepared"]
        assert "Mage Hand" in always_prepared
        assert "Prestidigitation" not in always_prepared

    def test_wood_elf_grants_druidcraft_cantrip(self):
        """Test that Wood Elf lineage grants Druidcraft cantrip"""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        result = builder.set_lineage("Wood Elf", "Wisdom")

        assert result is True
        char_data = builder.character_data

        # Check that Druidcraft is in cantrips
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Druidcraft" in always_prepared
        # Verify it came from the correct effect
        applied_effects = getattr(builder, "applied_effects", [])
        cantrip_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_cantrip"
        ]

        druidcraft_effect = None
        for effect in cantrip_effects:
            if effect["effect"]["spell"] == "Druidcraft":
                druidcraft_effect = effect
                break

        assert druidcraft_effect is not None
        assert druidcraft_effect["source_type"] == "lineage"
        assert druidcraft_effect["source"] == "Wood Elf Spells"

    def test_drow_grants_dancing_lights_cantrip(self):
        """Test that Drow lineage grants Dancing Lights cantrip"""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        result = builder.set_lineage("Drow", "Charisma")

        assert result is True
        char_data = builder.character_data

        # Check that Dancing Lights is in cantrips
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Dancing Lights" in always_prepared
        # Verify it came from the correct effect
        applied_effects = getattr(builder, "applied_effects", [])
        cantrip_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_cantrip"
        ]

        dancing_lights_effect = None
        for effect in cantrip_effects:
            if effect["effect"]["spell"] == "Dancing Lights":
                dancing_lights_effect = effect
                break

        assert dancing_lights_effect is not None
        assert dancing_lights_effect["source_type"] == "lineage"
        assert dancing_lights_effect["source"] == "Drow Spells"

    def test_elf_lineage_cantrip_with_class_cantrips(self):
        """Test that elf lineage cantrips work alongside class cantrips"""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        builder.set_lineage("High Elf", "Intelligence")
        builder.apply_choice("High Elf Cantrip", "Prestidigitation")

        # Set a class that also grants cantrips
        builder.set_class("Wizard", 1)

        # Make cantrip choices for the class (Wizard needs cantrips chosen)
        # Manually add to prepared.cantrips since we're not using the wizard flow
        cantrip_choices = ["Mage Hand", "Minor Illusion", "Firebolt"]
        for cantrip in cantrip_choices:
            builder.character_data["spells"]["prepared"]["cantrips"][cantrip] = {}

        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        # Should have the High Elf cantrip
        assert "Prestidigitation" in always_prepared

        # Check class cantrips in prepared.cantrips
        prepared_cantrips = char_data["spells"]["prepared"]["cantrips"]
        for cantrip in cantrip_choices:
            assert cantrip in prepared_cantrips

        # Verify the character has both species and class cantrips
        applied_effects = getattr(builder, "applied_effects", [])
        cantrip_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_cantrip"
        ]

        # Should have at least the lineage cantrip effect
        assert len(cantrip_effects) >= 1

        # Check that at least one cantrip comes from lineage choice
        lineage_cantrip_found = False
        for effect in cantrip_effects:
            if effect["source_type"] == "species_choice":
                lineage_cantrip_found = True
                break

        assert lineage_cantrip_found

    def test_lineage_cantrip_persists_with_level_up(self):
        """Test that lineage cantrips persist when character levels up"""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        builder.set_lineage("Drow", "Charisma")
        builder.set_class("Sorcerer", 1)

        # Check cantrips at level 1
        char_data = builder.character_data
        always_prepared_l1 = char_data["spells"]["always_prepared"].copy()
        assert "Dancing Lights" in always_prepared_l1

        # Level up to 2
        builder.set_class("Sorcerer", 2)
        char_data = builder.character_data
        always_prepared_l2 = char_data["spells"]["always_prepared"]

        # Dancing Lights should still be present
        assert "Dancing Lights" in always_prepared_l2

        # Verify it's still tracked as coming from lineage
        applied_effects = getattr(builder, "applied_effects", [])
        cantrip_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_cantrip"
        ]

        dancing_lights_effect = None
        for effect in cantrip_effects:
            if effect["effect"]["spell"] == "Dancing Lights":
                dancing_lights_effect = effect
                break

        assert dancing_lights_effect is not None
        assert dancing_lights_effect["source_type"] == "lineage"


class TestElfIntegration:
    """Test Elf species integration with other systems"""

    def test_elf_with_class_integration(self):
        """Test elf integration with different classes"""
        # Test with Wizard
        builder = CharacterBuilder()
        builder.set_species("Elf")
        builder.set_lineage("High Elf", "Intelligence")
        builder.apply_choice("High Elf Cantrip", "Prestidigitation")
        builder.set_class("Wizard", 1)

        char_data = builder.character_data

        assert char_data["class"] == "Wizard"
        assert char_data["species"] == "Elf"
        assert char_data["lineage"] == "High Elf"
        assert char_data["level"] == 1

        # Elf traits should still be present
        assert char_data["darkvision"] == 60
        applied_effects = getattr(builder, "applied_effects", [])
        assert len(applied_effects) >= 4  # At least Fey Ancestry + High Elf spells

    def test_elf_feature_descriptions(self):
        """Test that all elf features have proper descriptions"""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        char_data = builder.character_data
        species_features = char_data["features"]["species"]

        for feature in species_features:
            assert "description" in feature
            assert len(feature["description"]) > 0
            assert isinstance(feature["description"], str)

    def test_darkvision_in_to_character_output(self):
        """to_character() must expose darkvision == 60 for Elf."""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        character = builder.to_character()
        assert character["darkvision"] == 60

    def test_elf_effects_system_integration(self):
        """Test elf features work with the effects system"""
        builder = CharacterBuilder()
        builder.set_species("Elf")
        builder.set_lineage("High Elf", "Intelligence")
        builder.apply_choice("High Elf Cantrip", "Prestidigitation")

        applied_effects = getattr(builder, "applied_effects", [])

        # Should have effects from base elf and lineage
        assert len(applied_effects) >= 1  # At least Fey Ancestry

        # Check effect sources are correct
        for effect_data in applied_effects:
            assert effect_data["source_type"] in ["species", "lineage", "species_choice"]
            assert effect_data["source"] in [
                "Darkvision",
                "Fey Ancestry",
                "High Elf Cantrip: Prestidigitation",
                "High Elf Spells",
            ]

    def test_invalid_lineage_handling(self):
        """Test error handling for invalid lineages"""
        builder = CharacterBuilder()
        builder.set_species("Elf")

        # Test with invalid lineage
        result = builder.set_lineage("Invalid Elf", "Intelligence")
        assert result is False

        # Character should still have base elf traits
        char_data = builder.character_data
        assert char_data["species"] == "Elf"
        assert char_data.get("lineage") is None

    def test_spellcasting_ability_choices(self):
        """Test that lineages support different spellcasting abilities"""
        # Test all three abilities work for High Elf
        for ability in ["Intelligence", "Wisdom", "Charisma"]:
            builder = CharacterBuilder()
            builder.set_species("Elf")
            result = builder.set_lineage("High Elf", ability)
            assert result is True

            char_data = builder.character_data
            assert char_data.get("spellcasting_ability") == ability


class TestElfDataValidation:
    """Test elf species data validation and edge cases"""

    def test_elf_data_file_structure(self):
        """Test that elf data file has correct structure"""
        from pathlib import Path
        import json

        elf_file = Path("data/species/elf.json")
        assert elf_file.exists(), "Elf data file should exist"

        with open(elf_file, "r") as f:
            elf_data = json.load(f)

        # Check required fields
        assert "name" in elf_data
        assert elf_data["name"] == "Elf"
        assert "description" in elf_data
        assert "creature_type" in elf_data
        assert elf_data["creature_type"] == "Humanoid"
        assert "size" in elf_data
        assert elf_data["size"] == "Medium"
        assert "speed" in elf_data
        assert elf_data["speed"] == 30
        # Phase 9: elf no longer carries a top-level ``darkvision`` field;
        # the canonical source is the grant_darkvision effect on the
        # ``Darkvision`` trait.
        darkvision_trait = elf_data["traits"]["Darkvision"]
        assert isinstance(darkvision_trait, dict)
        dv_effects = [
            e for e in darkvision_trait.get("effects", [])
            if e.get("type") == "grant_darkvision"
        ]
        assert len(dv_effects) == 1
        assert dv_effects[0].get("range") == 60
        assert "traits" in elf_data
        assert "languages" in elf_data
        assert "lineages" in elf_data

        # Check lineages reference
        lineages = elf_data["lineages"]
        assert "Drow" in lineages
        assert "High Elf" in lineages
        assert "Wood Elf" in lineages

        # Check traits structure
        traits = elf_data["traits"]
        assert "Darkvision" in traits
        assert "Elven Lineage" in traits
        assert "Fey Ancestry" in traits
        assert "Keen Senses" in traits
        assert "Trance" in traits

        # Check Fey Ancestry has effects
        fey_ancestry = traits["Fey Ancestry"]
        assert "effects" in fey_ancestry
        assert len(fey_ancestry["effects"]) == 1
        assert fey_ancestry["effects"][0]["type"] == "grant_save_advantage"

    def test_elf_lineage_data_files(self):
        """Test that all elf lineage data files exist and are valid"""
        from pathlib import Path
        import json

        lineages = ["high_elf", "wood_elf", "drow"]

        for lineage_file in lineages:
            lineage_path = Path(f"data/species_variants/{lineage_file}.json")
            assert lineage_path.exists(), f"{lineage_file} data file should exist"

            with open(lineage_path, "r") as f:
                lineage_data = json.load(f)

            # Check required fields
            assert "name" in lineage_data
            assert "parent_species" in lineage_data
            assert lineage_data["parent_species"] == "Elf"
            assert "description" in lineage_data
            assert "traits" in lineage_data

            # Each lineage should have spell-granting traits with effects
            traits = lineage_data["traits"]
            spell_traits = [
                trait
                for trait in traits.values()
                if isinstance(trait, dict) and "effects" in trait
            ]
            assert len(spell_traits) >= 1, (
                f"{lineage_file} should have spell-granting traits"
            )

    def test_elf_species_loading_error_handling(self):
        """Test error handling when loading elf species"""
        builder = CharacterBuilder()

        # Test that valid elf loading works
        result = builder.set_species("Elf")
        assert result is True

        # Test lineage loading without setting species first
        builder_no_species = CharacterBuilder()
        result = builder_no_species.set_lineage("High Elf", "Intelligence")
        assert result is False

    def test_drow_cleric_integration(self):
        """Integration test: Drow Elf Cleric should have both lineage and class cantrips"""
        builder = CharacterBuilder()

        # Create a Drow Elf Cleric like the test character file
        builder.set_species("Elf")
        builder.set_lineage("Drow", "Charisma")
        builder.set_class("Cleric", 1)

        # Make Cleric spellcasting choices
        cleric_cantrips = ["Guidance", "Sacred Flame", "Thaumaturgy"]
        for cantrip in cleric_cantrips:
            builder.character_data["spells"]["prepared"]["cantrips"][cantrip] = {}

        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]

        # Should have Drow lineage cantrip
        assert "Dancing Lights" in always_prepared, (
            f"Dancing Lights missing from {always_prepared}"
        )

        # Should have chosen Cleric cantrips in prepared.cantrips
        prepared_cantrips = char_data["spells"]["prepared"]["cantrips"]
        for cantrip in cleric_cantrips:
            assert cantrip in prepared_cantrips, (
                f"{cantrip} missing from {prepared_cantrips}"
            )

        # Should have total cantrips (1 from Drow in always_prepared + 3 from Cleric in prepared)
        total_cantrips = len(always_prepared) + len(prepared_cantrips)
        assert total_cantrips == 4, f"Expected 4 cantrips, got {total_cantrips}"

        # Verify effects tracking
        applied_effects = getattr(builder, "applied_effects", [])
        cantrip_effects = [
            e for e in applied_effects if e["effect"]["type"] == "grant_cantrip"
        ]

        # Should have lineage cantrip effect
        lineage_effects = [e for e in cantrip_effects if e["source_type"] == "lineage"]
        assert len(lineage_effects) >= 1, "No lineage cantrip effects found"

        # Verify Dancing Lights comes from lineage
        dancing_lights_from_lineage = False
        for effect in lineage_effects:
            if effect["effect"]["spell"] == "Dancing Lights":
                dancing_lights_from_lineage = True
                break

        assert dancing_lights_from_lineage, (
            "Dancing Lights not found from lineage effects"
        )
