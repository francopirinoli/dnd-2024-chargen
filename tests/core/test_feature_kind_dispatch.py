#!/usr/bin/env python3
"""Phase 8: feature_kind dispatch + first-class hidden / pdf_summary fields.

Replaces the legacy contract that lived in data/feature_override.json: the
escape hatch was retired, and the same behaviours are now driven by the
``feature_kind``, ``hidden``, and ``pdf_summary`` fields authored directly
on class/subclass features.
"""

import json
import shutil
from pathlib import Path

from modules.character_builder import CharacterBuilder


REPO_DATA = Path(__file__).resolve().parents[2] / "data"


def _class_feature_names(builder: CharacterBuilder) -> list[str]:
    return [f.get("name") for f in builder.character_data["features"]["class"]]


def _class_feature(builder: CharacterBuilder, name: str):
    for feature in builder.character_data["features"]["class"]:
        if feature.get("name") == name:
            return feature
    return None


def _subclass_feature(builder: CharacterBuilder, name: str):
    for feature in builder.character_data["features"]["subclass"]:
        if feature.get("name") == name:
            return feature
    return None


def _subclass_feature_names(builder: CharacterBuilder) -> list[str]:
    return [f.get("name") for f in builder.character_data["features"]["subclass"]]


def test_wizard_subclass_placeholder_not_in_class_features():
    """feature_kind: 'subclass_pick' suppresses the class-features entry."""
    builder = CharacterBuilder()
    assert builder.set_class("Wizard", 3) is True
    assert "Wizard Subclass" not in _class_feature_names(builder)


def test_ability_score_improvement_not_in_class_features():
    """feature_kind: 'asi' suppresses the class-features entry."""
    builder = CharacterBuilder()
    assert builder.set_class("Fighter", 4) is True
    assert "Ability Score Improvement" not in _class_feature_names(builder)


def test_cleric_subclass_placeholder_not_in_class_features():
    """feature_kind: 'subclass_pick' suppression is uniform across classes."""
    builder = CharacterBuilder()
    assert builder.set_class("Cleric", 3) is True
    assert "Cleric Subclass" not in _class_feature_names(builder)


def test_druid_ability_score_improvement_not_in_class_features():
    """feature_kind: 'asi' suppression is uniform across classes."""
    builder = CharacterBuilder()
    assert builder.set_class("Druid", 4) is True
    assert "Ability Score Improvement" not in _class_feature_names(builder)


def test_pdf_summary_replaces_description():
    """A feature with a pdf_summary field renders that string as its description."""
    builder = CharacterBuilder()
    assert builder.set_class("Fighter", 1) is True

    second_wind = _class_feature(builder, "Second Wind")
    assert second_wind is not None
    # Backfilled in data/classes/fighter.json from the retired feature_override.json
    assert second_wind["description"] == (
        "Bonus Action: Regain 1d10+Fighter level HP "
        "(2/Short Rest, 3/Short Rest at level 4)"
    )


def test_hidden_field_suppresses_feature(tmp_path):
    """An explicit hidden: true boolean on a feature suppresses it from the list."""
    tmp_data = tmp_path / "data"
    shutil.copytree(REPO_DATA, tmp_data)

    fighter_path = tmp_data / "classes" / "fighter.json"
    doc = json.loads(fighter_path.read_text())
    weapon_mastery = doc["features_by_level"]["1"]["Weapon Mastery"]
    if isinstance(weapon_mastery, str):
        doc["features_by_level"]["1"]["Weapon Mastery"] = {
            "description": weapon_mastery,
            "hidden": True,
        }
    else:
        weapon_mastery["hidden"] = True
    fighter_path.write_text(json.dumps(doc))

    builder = CharacterBuilder(data_dir=str(tmp_data))
    assert builder.set_class("Fighter", 1) is True
    assert "Weapon Mastery" not in _class_feature_names(builder)


def test_pdf_summary_action_surge():
    """A second pdf_summary case to lock in the contract end-to-end."""
    builder = CharacterBuilder()
    assert builder.set_class("Fighter", 2) is True

    action_surge = _class_feature(builder, "Action Surge")
    assert action_surge is not None
    # pdf_summary in data/classes/fighter.json must win over the verbose description.
    assert (
        action_surge["description"]
        == "Once per Short Rest, take one additional Action on your turn"
    )


def test_subclass_feature_slot_renders_as_header():
    """feature_kind: 'subclass_feature_slot' is kept visible as a level header.

    Per .github/instructions/data-schemas.instructions.md and the dispatch in
    CharacterBuilder._apply_trait_effects, the slot stays in the class-features
    list so the level callout still shows even before / alongside the subclass
    walk that fills it.
    """
    builder = CharacterBuilder()
    assert builder.set_class("Fighter", 7) is True
    # Fighter "Subclass Feature" at level 7 is feature_kind: subclass_feature_slot.
    assert "Subclass Feature" in _class_feature_names(builder)


def test_spellcasting_setup_renders_normally_class_level():
    """feature_kind: 'spellcasting_setup' is NOT suppressed (it renders normally)."""
    builder = CharacterBuilder()
    assert builder.set_class("Wizard", 1) is True
    assert "Spellcasting" in _class_feature_names(builder)


def test_spellcasting_setup_appends_cantrips_class_level():
    """Legacy choices_made['Spellcasting'] cantrips are appended to the rendered description.

    Dispatch is on feature_kind == 'spellcasting_setup', not on the literal
    feature name — proving the same path works for any class with that kind.
    """
    builder = CharacterBuilder()
    builder.character_data["choices_made"]["Spellcasting"] = [
        "Fire Bolt",
        "Mage Hand",
        "Light",
    ]
    assert builder.set_class("Wizard", 1) is True

    spellcasting = _class_feature(builder, "Spellcasting")
    assert spellcasting is not None
    assert "Cantrips Known: Fire Bolt, Mage Hand, Light" in spellcasting["description"]


def test_spellcasting_setup_appends_cantrips_subclass_level():
    """Eldritch Knight's subclass-level Spellcasting (also feature_kind:
    'spellcasting_setup') receives the same cantrip append treatment."""
    builder = CharacterBuilder()
    builder.character_data["choices_made"]["Spellcasting"] = [
        "Booming Blade",
        "Green-Flame Blade",
    ]
    assert builder.set_class("Fighter", 3) is True
    assert builder.set_subclass("Eldritch Knight") is True

    spellcasting = _subclass_feature(builder, "Spellcasting")
    assert spellcasting is not None, (
        f"Eldritch Knight Spellcasting missing from subclass features: "
        f"{_subclass_feature_names(builder)}"
    )
    assert (
        "Cantrips Known: Booming Blade, Green-Flame Blade"
        in spellcasting["description"]
    )
