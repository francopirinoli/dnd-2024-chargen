"""
Strict-mode contract tests (audit Phase 5 — P2-6, D6-4).

These tests assert that the strict validators in :mod:`modules.strict_mode`
raise on three specific kinds of silent-failure inputs and that the closed
``effect.type`` enum in :mod:`modules.strict_mode` stays in sync with the
schema in ``models/_shared/effect.json``.

Strict mode is forced on by ``conftest.py`` (``DND_STRICT_EFFECTS=1``); the
toggle is also exercised here so the off-path stays warning-only.
"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

import pytest

from modules import strict_mode
from modules.character_builder import CharacterBuilder


REPO_ROOT = Path(__file__).resolve().parents[2]
EFFECT_SCHEMA = REPO_ROOT / "models" / "_shared" / "effect.json"


# ---------------------------------------------------------------------------
# Closed enum parity
# ---------------------------------------------------------------------------


def test_effect_enum_matches_schema():
    """``KNOWN_EFFECT_TYPES`` MUST equal the closed enum in effect.json.

    The two are intentionally duplicated — the schema gates JSON authoring at
    ``validate_data.py`` time, the constant gates runtime ``_apply_effect``
    dispatch. They must never drift.
    """
    schema = json.loads(EFFECT_SCHEMA.read_text())
    schema_enum = set(schema["properties"]["type"]["enum"])
    assert schema_enum == set(strict_mode.KNOWN_EFFECT_TYPES), (
        "models/_shared/effect.json enum and modules.strict_mode."
        "KNOWN_EFFECT_TYPES have drifted. Update both in lockstep — see "
        ".github/instructions/effects-system.instructions.md."
    )


def test_effect_enum_has_expected_size():
    """Sanity check: 40 effect types. Phase 7 (D0-1/D0-2/D4-3) added
    grant_spell_at_will, bonus_spell_damage_ability_mod, bonus_spell_range,
    grant_magical_darkness_sight, grant_maneuver, grant_superiority_dice
    (+6 over the Phase 6 baseline of 28). Phase 10 (D2-3) added
    grant_spell_slots and grant_weapon_mastery (+2). attack_ability_override (+1).
    Arcana Unleashed added grant_arcane_shot and grant_arcane_shot_dice (+2)."""
    assert len(strict_mode.KNOWN_EFFECT_TYPES) == 40


# ---------------------------------------------------------------------------
# Toggle
# ---------------------------------------------------------------------------


def test_strict_mode_default_on_in_tests():
    """``conftest.py`` sets ``DND_STRICT_EFFECTS=1`` for the whole suite."""
    assert strict_mode.is_strict() is True


def test_strict_mode_explicit_off(monkeypatch):
    """``DND_STRICT_EFFECTS=0`` disables strict mode even outside production."""
    monkeypatch.setenv("DND_STRICT_EFFECTS", "0")
    assert strict_mode.is_strict() is False


def test_strict_mode_off_in_production(monkeypatch):
    """Production must default to lenient so a bad payload never raises mid-build."""
    monkeypatch.delenv("DND_STRICT_EFFECTS", raising=False)
    monkeypatch.setenv("FLASK_ENV", "production")
    assert strict_mode.is_strict() is False


# ---------------------------------------------------------------------------
# Unknown effect type
# ---------------------------------------------------------------------------


def test_unknown_effect_type_raises_in_strict():
    """An effect with a type not in the closed enum must raise."""
    builder = CharacterBuilder()
    with pytest.raises(ValueError, match="unknown effect type"):
        builder._apply_effect(
            {"type": "grant_typo"},
            source_name="Test Source",
            source_type="class",
        )


def test_unknown_effect_type_warns_in_lenient(monkeypatch):
    """In lenient mode, the same input warns and continues."""
    monkeypatch.setenv("DND_STRICT_EFFECTS", "0")
    builder = CharacterBuilder()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        builder._apply_effect(
            {"type": "grant_typo"},
            source_name="Test Source",
            source_type="class",
        )
    assert any("unknown effect type" in str(w.message) for w in caught)


def test_known_effect_type_does_not_raise():
    """Spot-check: every type in the enum is accepted by ``check_effect_type``."""
    for effect_type in strict_mode.KNOWN_EFFECT_TYPES:
        strict_mode.check_effect_type(effect_type, source_label="enum-parity")


# ---------------------------------------------------------------------------
# Unknown choices_made top-level keys
# ---------------------------------------------------------------------------


def test_unknown_choice_key_raises_in_strict():
    """An unknown top-level key in ``choices_made`` must raise via apply_choices."""
    builder = CharacterBuilder()
    with pytest.raises(ValueError, match="unknown top-level keys"):
        builder.apply_choices({
            "class": "Fighter",
            "level": 1,
            "totally_made_up_key": "value",
        })


def test_unknown_choice_key_warns_in_lenient(monkeypatch):
    monkeypatch.setenv("DND_STRICT_EFFECTS", "0")
    builder = CharacterBuilder()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        builder.apply_choices({
            "class": "Fighter",
            "level": 1,
            "totally_made_up_key": "value",
        })
    assert any("unknown top-level keys" in str(w.message) for w in caught)


def test_known_static_choice_keys_do_not_raise():
    """A payload composed entirely of static allowlist keys is accepted."""
    builder = CharacterBuilder()
    builder.apply_choices({
        "class": "Fighter",
        "level": 1,
        "ability_scores": {
            "Strength": 16, "Dexterity": 14, "Constitution": 14,
            "Intelligence": 10, "Wisdom": 12, "Charisma": 8,
        },
        "skill_choices": ["Athletics", "Intimidation"],
    })


def test_dynamic_choice_keys_accepted():
    """Dynamic regex patterns (feat_*, class_feat_*, *_bonus_cantrip, …) pass."""
    for key in (
        "class_feat_4",
        "class_feat_4_ability",
        "feat_Skilled_skills_or_tools",
        "subclass_Spellcasting_cantrips",
        "species_trait_Elven Lineage",
        "Thaumaturge_bonus_cantrip",
    ):
        assert strict_mode.is_dynamic_choice_key(key), key


# ---------------------------------------------------------------------------
# features_by_level shape (data_loader)
# ---------------------------------------------------------------------------


def test_data_loader_rejects_array_features_by_level(tmp_path):
    """A class file with ``features_by_level: {"1": ["Foo"]}`` must fail at load."""
    from modules.data_loader import _validate_features_by_level

    bad_fbl = {"1": ["Spellcasting"]}  # array, not object
    with pytest.raises(ValueError, match="features_by_level"):
        _validate_features_by_level(bad_fbl, "test/path/Bad.json")


def test_data_loader_accepts_canonical_features_by_level():
    from modules.data_loader import _validate_features_by_level

    good_fbl = {"1": {"Spellcasting": "You can cast spells."}}
    _validate_features_by_level(good_fbl, "test/path/Good.json")  # no raise


# ---------------------------------------------------------------------------
# Non-canonical choice fallback resolution
# ---------------------------------------------------------------------------


def test_resolve_choice_value_fallback_raises_in_strict():
    """``_resolve_choice_value`` must raise when only a legacy flat key matches.

    Strict mode locks the contract that species trait picks live nested under
    ``choices_made['species_trait_choices']``. Any hit on the legacy flat /
    prefixed variants signals a non-canonical writer.
    """
    builder = CharacterBuilder()
    builder.character_data["choices_made"] = {
        "species_trait_Some Trait": "Option A",
    }
    with pytest.raises(ValueError, match="non-canonical fallback"):
        builder._resolve_choice_value("Some Trait")


def test_resolve_choice_value_nested_form_does_not_warn():
    """Canonical nested form resolves silently."""
    builder = CharacterBuilder()
    builder.character_data["choices_made"] = {
        "species_trait_choices": {"Some Trait": "Option A"},
    }
    assert builder._resolve_choice_value("Some Trait") == "Option A"
