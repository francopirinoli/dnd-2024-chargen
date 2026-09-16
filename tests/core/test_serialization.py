#!/usr/bin/env python3
"""
Pytest tests for CharacterBuilder serialization (to_json/from_json)

These tests ensure that character data, especially effects, are preserved
through save/restore cycles, preventing data loss during the wizard flow.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def character_builder():
    """Fixture providing a fresh CharacterBuilder for each test"""
    return CharacterBuilder()


@pytest.fixture
def tiefling_paladin():
    """Fixture providing a Chthonic Tiefling Paladin with effects"""
    builder = CharacterBuilder()
    builder.character_data["level"] = 2
    builder.character_data["name"] = "Test Paladin"
    builder.set_class("Paladin", 2)
    builder.set_species("Tiefling")
    builder.set_lineage("Chthonic Tiefling", spellcasting_ability="Charisma")
    return builder


class TestBasicSerialization:
    """Test basic to_json and from_json functionality"""

    def test_to_json_creates_valid_dict(self, character_builder):
        """Test that to_json produces a valid dictionary"""
        character_builder.set_species("Human")
        character_builder.set_class("Fighter", 1)

        json_data = character_builder.to_json()

        assert isinstance(json_data, dict)
        assert "species" in json_data
        assert "class" in json_data
        assert "level" in json_data
        assert json_data["species"] == "Human"
        assert json_data["class"] == "Fighter"

    def test_from_json_restores_basic_data(self, character_builder):
        """Test that from_json restores basic character data"""
        # Create a character
        character_builder.set_species("Elf")
        character_builder.set_class("Wizard", 3)
        character_builder.character_data["name"] = "Test Wizard"

        # Export and restore
        json_data = character_builder.to_json()
        new_builder = CharacterBuilder()
        new_builder.from_json(json_data)

        # Verify restoration
        assert new_builder.character_data["species"] == "Elf"
        assert new_builder.character_data["class"] == "Wizard"
        assert new_builder.character_data["level"] == 3
        assert new_builder.character_data["name"] == "Test Wizard"


class TestEffectsSerialization:
    """Test that effects are properly preserved through serialization"""

    def test_effects_exported_to_json(self, tiefling_paladin):
        """Test that applied_effects are exported to effects array"""
        json_data = tiefling_paladin.to_json()

        assert "effects" in json_data
        assert isinstance(json_data["effects"], list)
        assert len(json_data["effects"]) > 0

        # Check for grant_cantrip effects specifically
        cantrip_effects = [
            e for e in json_data["effects"] if e.get("type") == "grant_cantrip"
        ]
        assert len(cantrip_effects) >= 2  # Thaumaturgy + Chill Touch

        cantrip_names = [e.get("spell") for e in cantrip_effects]
        assert "Thaumaturgy" in cantrip_names
        assert "Chill Touch" in cantrip_names

    def test_effects_restored_from_json(self, tiefling_paladin):
        """Test that effects are restored to applied_effects"""
        # Export
        json_data = tiefling_paladin.to_json()
        original_effects_count = len(json_data["effects"])

        # Restore
        new_builder = CharacterBuilder()
        new_builder.from_json(json_data)

        # Verify applied_effects was restored
        assert hasattr(new_builder, "applied_effects")
        assert len(new_builder.applied_effects) == original_effects_count

        # Verify structure of restored effects
        for applied_effect in new_builder.applied_effects:
            assert "effect" in applied_effect
            assert "source" in applied_effect
            assert "source_type" in applied_effect

    def test_effects_survive_multiple_cycles(self, tiefling_paladin):
        """Test that effects survive multiple save/restore cycles"""
        # Cycle 1: Save and restore
        json1 = tiefling_paladin.to_json()
        builder2 = CharacterBuilder()
        builder2.from_json(json1)

        # Cycle 2: Save and restore again
        json2 = builder2.to_json()
        builder3 = CharacterBuilder()
        builder3.from_json(json2)

        # Cycle 3: One more time
        json3 = builder3.to_json()

        # All should have same effects
        assert len(json1["effects"]) == len(json2["effects"])
        assert len(json2["effects"]) == len(json3["effects"])

        # Verify the actual effects match
        assert json1["effects"] == json2["effects"]
        assert json2["effects"] == json3["effects"]


class TestCantripsPreservation:
    """Test that cantrips specifically are preserved"""

    def test_cantrips_in_both_locations(self, tiefling_paladin):
        """Test that cantrips exist in spells.always_prepared and effects"""
        json_data = tiefling_paladin.to_json()

        # Check spells.always_prepared dict (cantrips from effects)
        always_prepared = json_data.get("spells", {}).get("always_prepared", {})
        assert "Thaumaturgy" in always_prepared
        assert "Chill Touch" in always_prepared

        # Check effects array
        cantrip_effects = [
            e for e in json_data["effects"] if e.get("type") == "grant_cantrip"
        ]
        effect_cantrips = [e.get("spell") for e in cantrip_effects]
        assert "Thaumaturgy" in effect_cantrips
        assert "Chill Touch" in effect_cantrips

    def test_cantrips_preserved_after_restore(self, tiefling_paladin):
        """Test that cantrips are available after restore"""
        # Save and restore
        json_data = tiefling_paladin.to_json()
        new_builder = CharacterBuilder()
        new_builder.from_json(json_data)

        # Re-export
        json_data2 = new_builder.to_json()

        # Cantrips should still be in always_prepared
        always_prepared = json_data2.get("spells", {}).get("always_prepared", {})
        assert "Thaumaturgy" in always_prepared
        assert "Chill Touch" in always_prepared

        # Effects should still be there
        cantrip_effects = [
            e for e in json_data2["effects"] if e.get("type") == "grant_cantrip"
        ]
        assert len(cantrip_effects) >= 2


class TestWizardFlowSimulation:
    """Test realistic wizard flow scenarios"""

    def test_full_wizard_flow(self, character_builder):
        """Simulate a full wizard flow with multiple steps"""
        # Step 1: Class selection
        character_builder.character_data["level"] = 2
        character_builder.set_class("Paladin", 2)
        session1 = character_builder.to_json()

        # Step 2: Species selection
        builder2 = CharacterBuilder()
        builder2.from_json(session1)
        builder2.set_species("Tiefling")
        session2 = builder2.to_json()

        # Step 3: Lineage selection (adds cantrips)
        builder3 = CharacterBuilder()
        builder3.from_json(session2)
        builder3.set_lineage("Chthonic Tiefling", spellcasting_ability="Charisma")
        session3 = builder3.to_json()

        # Step 4: Language selection
        builder4 = CharacterBuilder()
        builder4.from_json(session3)
        builder4.apply_choice("languages", ["Infernal", "Abyssal"])
        session4 = builder4.to_json()

        # Step 5: Ability scores
        builder5 = CharacterBuilder()
        builder5.from_json(session4)
        builder5.set_abilities(
            {
                "Strength": 15,
                "Dexterity": 10,
                "Constitution": 14,
                "Intelligence": 8,
                "Wisdom": 12,
                "Charisma": 13,
            }
        )
        final_session = builder5.to_json()

        # Verify effects survived the entire flow
        assert "effects" in final_session
        assert len(final_session["effects"]) > 0

        cantrip_effects = [
            e for e in final_session["effects"] if e.get("type") == "grant_cantrip"
        ]
        assert len(cantrip_effects) >= 2

        # Verify cantrips are accessible in always_prepared
        always_prepared = final_session.get("spells", {}).get("always_prepared", {})
        assert "Chill Touch" in always_prepared
        assert "Thaumaturgy" in always_prepared

    def test_effects_not_duplicated_on_restore(self, tiefling_paladin):
        """Test that restoring doesn't duplicate effects"""
        json1 = tiefling_paladin.to_json()
        effects_count1 = len(json1["effects"])

        # Restore and immediately export (no changes)
        builder2 = CharacterBuilder()
        builder2.from_json(json1)
        json2 = builder2.to_json()
        effects_count2 = len(json2["effects"])

        # Should have exact same number of effects
        assert effects_count1 == effects_count2

        # And they should be identical
        assert json1["effects"] == json2["effects"]


class TestEffectTypes:
    """Test preservation of different effect types"""

    def test_damage_resistance_effect(self, tiefling_paladin):
        """Test that damage resistance effects are preserved"""
        json_data = tiefling_paladin.to_json()

        # Chthonic Tiefling should have necrotic resistance
        resistance_effects = [
            e
            for e in json_data["effects"]
            if e.get("type") == "grant_damage_resistance"
        ]
        assert len(resistance_effects) > 0

        damage_types = [e.get("damage_type") for e in resistance_effects]
        assert "Necrotic" in damage_types

        # Restore and verify it's still there
        new_builder = CharacterBuilder()
        new_builder.from_json(json_data)
        new_json = new_builder.to_json()

        new_resistance_effects = [
            e for e in new_json["effects"] if e.get("type") == "grant_damage_resistance"
        ]
        assert len(new_resistance_effects) == len(resistance_effects)

    def test_grant_spell_effects(self, tiefling_paladin):
        """Test that grant_spell effects (leveled spells) are preserved"""
        json_data = tiefling_paladin.to_json()

        # Chthonic Tiefling gets False Life and Ray of Enfeeblement
        spell_effects = [
            e for e in json_data["effects"] if e.get("type") == "grant_spell"
        ]
        assert len(spell_effects) >= 2

        spell_names = [e.get("spell") for e in spell_effects]
        assert "False Life" in spell_names
        assert "Ray of Enfeeblement" in spell_names

        # Restore and verify
        new_builder = CharacterBuilder()
        new_builder.from_json(json_data)
        new_json = new_builder.to_json()

        new_spell_effects = [
            e for e in new_json["effects"] if e.get("type") == "grant_spell"
        ]
        new_spell_names = [e.get("spell") for e in new_spell_effects]
        assert "False Life" in new_spell_names
        assert "Ray of Enfeeblement" in new_spell_names


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_effects_array(self, character_builder):
        """Test handling of character with no effects"""
        character_builder.set_species("Human")
        character_builder.set_class("Fighter", 1)

        json_data = character_builder.to_json()

        # Even with no effects, should have empty array
        assert "effects" in json_data
        assert isinstance(json_data["effects"], list)

        # Should be able to restore
        new_builder = CharacterBuilder()
        new_builder.from_json(json_data)

        assert hasattr(new_builder, "applied_effects")
        assert isinstance(new_builder.applied_effects, list)

    def test_malformed_effects_in_json(self, character_builder):
        """Test handling of malformed effects data"""
        character_builder.set_species("Human")
        json_data = character_builder.to_json()

        # Add malformed effect
        json_data["effects"] = [
            {"type": "grant_cantrip", "spell": "Test"},  # Valid
            "not a dict",  # Invalid
            {"type": "grant_spell"},  # Missing spell name
        ]

        # Should not crash on restore
        new_builder = CharacterBuilder()
        new_builder.from_json(json_data)

        # Should have restored what it could
        assert hasattr(new_builder, "applied_effects")
