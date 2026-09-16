"""
Regression tests for audit P0-1 (backend half): species trait picks must be
read from the canonical nested ``choices_made["species_trait_choices"]``
object, and any legacy flat top-level trait keys present on saved characters
must be lifted into that nested object on rebuild.

Phase 4 will retire the flat-key write path on the frontend. Until then both
shapes must produce identical results.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from modules.character_builder import CharacterBuilder


_BASE_DRAGONBORN_CHOICES: Dict[str, Any] = {
    "classes": [{"class_name": "Fighter", "level": 1, "subclass": None}],
    "class": "Fighter",
    "level": 1,
    "species": "Dragonborn",
    "background": "Soldier",
    "ability_scores_method": "standard_array",
    "ability_scores": {
        "Strength": 15,
        "Dexterity": 14,
        "Constitution": 13,
        "Intelligence": 8,
        "Wisdom": 12,
        "Charisma": 10,
    },
    "background_bonuses": {"Strength": 2, "Constitution": 1},
    "skill_choices": ["Athletics", "Intimidation"],
    "languages": ["Dwarvish", "Elvish"],
}


def _build(choices: Dict[str, Any]) -> Dict[str, Any]:
    builder = CharacterBuilder()
    ok = builder.apply_choices(choices)
    assert ok, "apply_choices returned False"
    return builder.to_character()


def test_legacy_flat_trait_key_is_lifted_into_nested_object() -> None:
    """A flat 'Draconic Ancestry' key must be lifted into species_trait_choices."""
    flat_choices = {**_BASE_DRAGONBORN_CHOICES, "Draconic Ancestry": "Red (Fire)"}
    char = _build(flat_choices)

    nested = char["choices_made"].get("species_trait_choices")
    assert isinstance(nested, dict), (
        "species_trait_choices must be present as a nested dict after normalization"
    )
    assert nested.get("Draconic Ancestry") == "Red (Fire)"

    # The flat duplicate must be cleaned up — nested is canonical.
    assert "Draconic Ancestry" not in char["choices_made"], (
        "Flat top-level trait key must be removed after lift (audit P0-1)"
    )


def test_nested_species_trait_choices_input_is_honored() -> None:
    """The canonical nested input shape must work end-to-end."""
    nested_choices = {
        **_BASE_DRAGONBORN_CHOICES,
        "species_trait_choices": {"Draconic Ancestry": "Red (Fire)"},
    }
    char = _build(nested_choices)

    nested = char["choices_made"].get("species_trait_choices")
    assert isinstance(nested, dict)
    assert nested.get("Draconic Ancestry") == "Red (Fire)"


def test_flat_and_nested_inputs_produce_equivalent_characters() -> None:
    """Flat and nested input shapes must build identical characters."""
    flat = _build({**_BASE_DRAGONBORN_CHOICES, "Draconic Ancestry": "Red (Fire)"})
    nested = _build(
        {
            **_BASE_DRAGONBORN_CHOICES,
            "species_trait_choices": {"Draconic Ancestry": "Red (Fire)"},
        }
    )

    # Both should resolve the damage_type substitution identically. Inspect the
    # Damage Resistance feature description as a proxy for the substitution
    # having fired.
    def _damage_resistance_desc(character: Dict[str, Any]) -> str:
        for feat in character["features"]["species"]:
            if feat["name"].startswith("Damage Resistance"):
                return feat["description"]
        return ""

    flat_desc = _damage_resistance_desc(flat)
    nested_desc = _damage_resistance_desc(nested)
    assert flat_desc and "Fire" in flat_desc, (
        f"Flat-key build did not resolve damage type into description: {flat_desc!r}"
    )
    assert flat_desc == nested_desc, (
        "Flat and nested inputs must produce identical feature descriptions"
    )


def test_trait_side_effects_fire_from_nested_input_elven_lineage() -> None:
    """Elven Lineage selection via nested input must set spellcasting_ability."""
    choices = {
        "classes": [{"class_name": "Fighter", "level": 1, "subclass": None}],
        "class": "Fighter",
        "level": 1,
        "species": "Elf",
        "background": "Sage",
        "species_trait_choices": {"Elven Lineage": "Wisdom"},
        "ability_scores_method": "standard_array",
        "ability_scores": {
            "Strength": 15,
            "Dexterity": 14,
            "Constitution": 13,
            "Intelligence": 8,
            "Wisdom": 12,
            "Charisma": 10,
        },
        "background_bonuses": {"Intelligence": 2, "Constitution": 1},
        "skill_choices": ["Athletics", "Intimidation"],
        "languages": ["Dwarvish", "Draconic"],
    }
    builder = CharacterBuilder()
    assert builder.apply_choices(choices)
    assert builder.character_data.get("spellcasting_ability") == "Wisdom"


def test_normalization_is_idempotent() -> None:
    """Running the normalizer twice on the same input must be a no-op."""
    choices = {**_BASE_DRAGONBORN_CHOICES, "Draconic Ancestry": "Red (Fire)"}
    builder = CharacterBuilder()
    # First normalization (species needs to be loaded for trait name discovery).
    builder.set_species("Dragonborn")
    builder._normalize_species_trait_choices(choices)
    snapshot = {
        "flat_present": "Draconic Ancestry" in choices,
        "nested_value": choices.get("species_trait_choices", {}).get(
            "Draconic Ancestry"
        ),
    }
    builder._normalize_species_trait_choices(choices)
    assert snapshot == {
        "flat_present": "Draconic Ancestry" in choices,
        "nested_value": choices.get("species_trait_choices", {}).get(
            "Draconic Ancestry"
        ),
    }
    assert snapshot["flat_present"] is False
    assert snapshot["nested_value"] == "Red (Fire)"


def test_unrelated_top_level_keys_are_not_lifted() -> None:
    """Only keys matching a known trait choice name are lifted."""
    choices = {
        **_BASE_DRAGONBORN_CHOICES,
        "Draconic Ancestry": "Red (Fire)",
        "some_unrelated_key": "leave me alone",
    }
    builder = CharacterBuilder()
    builder.set_species("Dragonborn")
    builder._normalize_species_trait_choices(choices)
    assert choices["some_unrelated_key"] == "leave me alone"
    assert "some_unrelated_key" not in choices.get("species_trait_choices", {})


@pytest.mark.integration
def test_dragonborn_legacy_fixture_rebuild_equality_is_covered() -> None:
    """The new legacy fixture is discovered by the round-trip equality suite."""
    from pathlib import Path

    fixture = (
        Path(__file__).resolve().parents[2]
        / "test_characters"
        / "dragonborn_fighter_legacy_flat_traits.json"
    )
    assert fixture.exists(), "Legacy flat-trait-keys fixture must exist"
