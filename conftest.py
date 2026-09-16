"""Pytest configuration and shared fixtures."""

import sys
import os
import json
import pytest
from pathlib import Path

# Phase 5 (audit P2-6): strict mode is default-on in tests so silent typos
# in JSON data or unknown choice keys fail the suite immediately. Production
# (FLASK_ENV=production) keeps strict OFF to avoid raising mid-build.
os.environ.setdefault("DND_STRICT_EFFECTS", "1")

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.character_builder import CharacterBuilder


# ==================== App Fixtures ====================


@pytest.fixture
def app():
    """Create a Flask test app with TESTING enabled."""
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    flask_app.config["SESSION_TYPE"] = "filesystem"
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client for API testing."""
    with app.test_client() as client:
        yield client


# ==================== Builder Fixtures ====================


@pytest.fixture
def character_builder():
    """Factory fixture that returns a fresh CharacterBuilder."""
    def _make_builder():
        return CharacterBuilder()
    return _make_builder


@pytest.fixture
def built_character():
    """Factory fixture that builds a character from choices and returns to_character() output."""
    def _build(choices):
        builder = CharacterBuilder()
        builder.apply_choices(choices)
        return builder.to_character()
    return _build


# ==================== Sample Choices Fixtures ====================


@pytest.fixture
def dwarf_cleric_choices():
    """Level 7 Dwarf Cleric (Light Domain) - standard test build."""
    return {
        "character_name": "Thorin",
        "level": 7,
        "species": "Dwarf",
        "class": "Cleric",
        "subclass": "Light Domain",
        "background": "Acolyte",
        "languages": ["Draconic", "Dwarvish"],
        "ability_scores": {
            "Strength": 14, "Dexterity": 8, "Constitution": 15,
            "Intelligence": 10, "Wisdom": 16, "Charisma": 12
        },
        "background_bonuses": {"Wisdom": 2, "Constitution": 1}
    }


@pytest.fixture
def elf_fighter_choices():
    """Level 3 Wood Elf Fighter (Champion) - standard test build."""
    return {
        "character_name": "Elenian",
        "level": 3,
        "species": "Elf",
        "lineage": "Wood Elf",
        "class": "Fighter",
        "subclass": "Champion",
        "background": "Soldier",
        "languages": ["Goblin", "Halfling"],
        "ability_scores": {
            "Strength": 14, "Dexterity": 15, "Constitution": 13,
            "Intelligence": 8, "Wisdom": 12, "Charisma": 10
        },
        "background_bonuses": {"Dexterity": 2, "Constitution": 1},
        "Elven Lineage": "Wisdom",
        "Fighting Style": "Dueling",
        "Keen Senses": "Survival",
        "skill_choices": ["Acrobatics", "Perception"]
    }


@pytest.fixture
def human_wizard_choices():
    """Level 5 Human Wizard (Evoker) - standard test build."""
    return {
        "character_name": "Elara",
        "level": 5,
        "species": "Human",
        "class": "Wizard",
        "subclass": "Evoker",
        "background": "Sage",
        "languages": ["Gnomish", "Orc"],
        "ability_scores": {
            "Strength": 8, "Dexterity": 14, "Constitution": 13,
            "Intelligence": 16, "Wisdom": 12, "Charisma": 10
        },
        "background_bonuses": {"Intelligence": 2, "Wisdom": 1}
    }


# ==================== Test Character File Fixtures ====================


@pytest.fixture
def test_character_files():
    """Return paths to test character JSON files."""
    test_dir = project_root / "test_characters"
    return {
        "dwarf_cleric": test_dir / "test_cleric_dwarf.json",
        "elf_fighter": test_dir / "test_figher_wood_elf.json",
    }


def load_test_character(filepath):
    """Load a test character JSON file and return choices_made."""
    with open(filepath) as f:
        data = json.load(f)
    return data.get("choices_made", data)
