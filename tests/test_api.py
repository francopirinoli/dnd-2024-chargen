"""Tests for the REST API v1 endpoints and character builder functionality."""

import pytest
import json
from modules.character_builder import CharacterBuilder


class TestBuildCharacterAPI:
    """Tests for /api/v1/character/build."""

    def test_valid_build(self, client, dwarf_cleric_choices):
        response = client.post(
            "/api/v1/character/build",
            json={"choices_made": dwarf_cleric_choices},
            content_type="application/json"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "character" in data
        character = data["character"]
        assert character.get("name") == "Thorin"

    def test_elf_fighter_build(self, client, elf_fighter_choices):
        response = client.post(
            "/api/v1/character/build",
            json={"choices_made": elf_fighter_choices},
            content_type="application/json"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "character" in data

    def test_missing_choices(self, client):
        response = client.post(
            "/api/v1/character/build",
            json={},
            content_type="application/json"
        )
        assert response.status_code == 400


class TestValidateEffects:
    """Tests for species/class effect validation using CharacterBuilder directly."""

    def test_dwarf_effects(self, built_character):
        choices = {
            "species": "Dwarf",
            "class": "Cleric",
            "level": 3,
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 10, "Dexterity": 10, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 14, "Charisma": 10
            }
        }
        character = built_character(choices)
        effects = character.get("effects", [])
        resistance_types = [e.get("damage_type") for e in effects if e.get("type") == "grant_damage_resistance"]
        assert "Poison" in resistance_types

    def test_human_fighter_builds(self, built_character):
        choices = {
            "species": "Human",
            "class": "Fighter",
            "level": 1,
            "background": "Soldier",
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            }
        }
        character = built_character(choices)
        assert character.get("class") == "Fighter"
        assert character.get("species") == "Human"


class TestDirectBuilder:
    """Tests using CharacterBuilder directly (no HTTP)."""

    def test_dwarf_cleric_build(self, built_character, dwarf_cleric_choices):
        character = built_character(dwarf_cleric_choices)
        assert character.get("name") == "Thorin"
        assert character.get("class") == "Cleric"
        assert character.get("species") == "Dwarf"

    def test_elf_fighter_build(self, built_character, elf_fighter_choices):
        character = built_character(elf_fighter_choices)
        assert character.get("name") == "Elenian"
        assert character.get("class") == "Fighter"
