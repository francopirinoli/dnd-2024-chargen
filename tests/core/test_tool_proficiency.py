"""Tests for grant_tool_proficiency effect type — GitHub Issue: Tool proficiencies not fully tracked or displayed."""

import pytest
from modules.character_builder import CharacterBuilder


class TestGrantToolProficiencyEffect:
    """Test the grant_tool_proficiency effect type in _apply_effect()."""

    def _builder_with_effect(self, tools):
        """Return a builder that has had grant_tool_proficiency applied directly."""
        builder = CharacterBuilder()
        effect = {"type": "grant_tool_proficiency", "tools": tools}
        builder._apply_effect(effect, source_name="Test Feature", source_type="class")
        return builder

    def test_single_tool_added(self):
        """A single tool in the effect should appear in proficiencies['tools']."""
        builder = self._builder_with_effect(["Thieves' Tools"])
        character = builder.to_character()
        assert "Thieves' Tools" in character["proficiencies"]["tools"]

    def test_multiple_tools_added(self):
        """Multiple tools should all be added to proficiencies['tools']."""
        builder = self._builder_with_effect(["Thieves' Tools", "Disguise Kit"])
        character = builder.to_character()
        assert "Thieves' Tools" in character["proficiencies"]["tools"]
        assert "Disguise Kit" in character["proficiencies"]["tools"]

    def test_no_duplicate_tools(self):
        """Applying the same tool twice should not create duplicates."""
        builder = CharacterBuilder()
        effect = {"type": "grant_tool_proficiency", "tools": ["Thieves' Tools"]}
        builder._apply_effect(effect, "Feature A", "class")
        builder._apply_effect(effect, "Feature B", "class")
        character = builder.to_character()
        assert character["proficiencies"]["tools"].count("Thieves' Tools") == 1

    def test_source_tracked(self):
        """The source of the tool proficiency should be stored in proficiency_sources."""
        builder = self._builder_with_effect(["Thieves' Tools"])
        sources = builder.character_data["proficiency_sources"]["tools"]
        assert sources.get("Thieves' Tools") == "Test Feature"

    def test_species_source_uses_species_name(self):
        """For species/lineage source_type, the source should resolve to the species name."""
        builder = CharacterBuilder()
        builder.character_data["species"] = "Elf"
        effect = {"type": "grant_tool_proficiency", "tools": ["Herbalism Kit"]}
        builder._apply_effect(effect, "Elf Trait", "species")
        sources = builder.character_data["proficiency_sources"]["tools"]
        assert sources.get("Herbalism Kit") == "Elf"


class TestBackgroundToolProficiencies:
    """Tool proficiencies from backgrounds (existing path) should still work."""

    def test_wayfarer_background_tools(self):
        """Wayfarer background grants Thieves' Tools proficiency."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", 1)
        builder.set_background("Wayfarer")
        character = builder.to_character()
        assert "Thieves' Tools" in character["proficiencies"]["tools"]

    def test_tool_proficiencies_in_character_dict(self):
        """tool_proficiencies should appear in the top-level character dict."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Fighter", 1)
        builder.set_background("Wayfarer")
        character = builder.to_character()
        # Should be accessible as character['proficiencies']['tools']
        assert isinstance(character["proficiencies"]["tools"], list)
        assert len(character["proficiencies"]["tools"]) > 0
