---
name: implement-feature
description: "Implement any D&D feature end-to-end via the effects system: class/subclass features, species traits, lineage choices, background benefits, feats, weapon masteries, fighting styles, eldritch invocations, or spells. Verifies wiki source, updates JSON with effects, adds effect handlers if needed, writes tests."
---

# Implement Feature

End-to-end workflow for implementing **any feature-bearing D&D entity** with full effects system integration. The procedure is the same regardless of where the feature lives — only the data file changes.

## When to Use

- Adding or completing a class or subclass feature
- Adding or completing a species trait or lineage choice
- Adding or completing a background's mechanical benefits
- Adding a feat (general or origin)
- Adding a weapon mastery, fighting style, or eldritch invocation
- Adding a spell with mechanical effects
- Introducing a brand-new effect type to support any of the above

## Where Each Feature Type Lives

Pick the right data file (and matching schema) before you start.

| Entity                | Data path                                        | Schema                              | Wiki fetcher                         |
|-----------------------|--------------------------------------------------|-------------------------------------|--------------------------------------|
| Class feature         | `data/classes/<class>.json`                      | `models/class_schema.json`          | `python update_classes.py --class <name>` |
| Subclass feature      | `data/subclasses/<class>/<subclass>.json`        | `models/subclass_schema.json`       | `python update_classes.py --class <name>` (subclasses bundled with parent class) |
| Species trait         | `data/species/<species>.json`                    | (see `models/`)                     | `python update_species.py --species <name>` |
| Lineage / variant     | `data/species_variants/<species>.json`           | (see `models/`)                     | `python update_species.py --species <name>` |
| Background            | `data/backgrounds/<background>.json`             | (see `models/`)                     | hand-authored from wiki              |
| General feat          | `data/general_feats.json`                        | (see `models/`)                     | hand-authored from wiki              |
| Origin feat           | `data/origin_feats.json`                         | (see `models/`)                     | hand-authored from wiki              |
| Weapon mastery        | `data/equipment/weapon_masteries.json`           | (see `models/`)                     | hand-authored from wiki              |
| Fighting style        | `data/fighting_styles.json`                      | (see `models/`)                     | hand-authored from wiki              |
| Eldritch invocation   | `data/eldritch_invocations.json`                 | (see `models/`)                     | hand-authored from wiki              |
| Spell (definition)    | `data/spells/definitions/<spell>.json`           | (see `models/`)                     | hand-authored from wiki              |
| Spell (class list)    | `data/spells/class_lists/<class>.json`           | (see `models/`)                     | `python update_spells.py --class <name>` (writes directly to `data/`) |

If your feature is a **player choice**, also see `.github/instructions/choice-reference.instructions.md` — choices are encoded with the Choice Reference System rather than as raw effect arrays.

## Procedure

### 1. Verify Source Material

Check the wiki cache first:

```bash
ls wiki_data/<area>/<name>.json
```

If missing, fetch (where a fetcher exists — see table above):

```bash
python update_classes.py --class <name>
python update_species.py --species <name>
python update_spells.py --class <name>
```

For backgrounds, feats, weapon masteries, fighting styles, eldritch invocations, and spell definitions there is no fetcher — read the wiki directly and capture the rules text.

Parse `content.text` from the cached JSON (where applicable) to understand the feature's mechanics.

### 2. Identify Effect Types

Map every mechanical benefit the feature provides to an effect type from the [Effect Type Catalog](./references/effect-type-catalog.md). Common mappings:

| Mechanic                          | Effect type                                                |
|-----------------------------------|------------------------------------------------------------|
| Grants a cantrip                  | `grant_cantrip`                                            |
| Always-prepared spell             | `grant_spell` with `min_level`                             |
| Weapon / armor / tool proficiency | `grant_weapon_proficiency` / `grant_armor_proficiency` / `grant_tool_proficiency` |
| Skill proficiency / expertise     | `grant_skill_proficiency` / `grant_skill_expertise`        |
| Save proficiency / advantage      | `grant_save_proficiency` / `grant_save_advantage`          |
| Damage resistance / immunity      | `grant_damage_resistance` / `grant_damage_immunity`        |
| Condition immunity                | `grant_condition_immunity`                                 |
| AC bonus / alternative AC         | `bonus_ac` / `alternative_ac`                              |
| Damage / attack bonus             | `bonus_damage` / `bonus_attack`                            |
| HP bonus                          | `bonus_hp`                                                 |
| Speed change                      | `increase_speed`                                           |
| Fighting-style mechanics          | `great_weapon_fighting`, `two_weapon_fighting_modifier`, `unarmed_fighting` |

If no existing effect type fits, **stop and add a new one** (see step 5) before authoring the data.

### 3. Update the Data File

Find the right file from the routing table above and add the feature with its `effects` array.

For **class / subclass / species / background** features, the canonical shape is:

```json
"features_by_level": {
  "3": {
    "Feature Name": {
      "description": "Description from wiki.",
      "effects": [
        {"type": "effect_type", "...": "..."}
      ]
    }
  }
}
```

For **flat catalogues** (feats, weapon masteries, fighting styles, eldritch invocations, spells), the shape varies per file but the `effects` array follows the same conventions. Mirror existing entries in the same file.

**Critical**: `features_by_level` values are always **objects keyed by feature name**, never arrays. See `.github/instructions/data-schemas.instructions.md`.

If the feature requires a player choice (pick a skill, pick a spell, pick a fighting style), encode it via the Choice Reference System rather than baking the result into effects.

### 4. Validate Schema

```bash
python validate_data.py
```

Fix every violation before moving on.

### 5. Implement an Effect Handler (only if needed)

If step 2 surfaced a new effect type:

1. Add a `case` in `modules/character_builder.py` → `_apply_effect()`.
2. Wire it into the relevant calculation method (skills, AC, attacks, spell slots, …).
3. Document it in `docs/FEATURE_EFFECTS.md`.
4. Add a positive, negative, and (if relevant) stacking test in `tests/`.

See `.github/instructions/effects-system.instructions.md` for the full rules.

### 6. Write Tests

Add or extend a test file under `tests/` matching the feature's home (`test_classes.py`, `test_species.py`, `test_backgrounds.py`, `test_feats.py`, etc.). Assert on paths into `to_character()`:

```python
from modules.character_builder import CharacterBuilder

def test_feature_name_effect():
    builder = CharacterBuilder()
    builder.apply_choices({
        "character_name": "Test",
        "level": 3,
        "species": "...",
        "class": "...",
        "subclass": "...",
        "background": "...",
        "ability_scores": {...},
        "background_bonuses": {...},
        # any choice that triggers the feature, e.g.
        # "origin_feat": "...", "fighting_style": "...", etc.
    })
    character = builder.to_character()
    assert ...
```

Prefer parameterised tests (`@pytest.mark.parametrize`) when verifying the same shape across many entries (every fighting style, every weapon mastery, every spell in a list). See `.github/instructions/testing.instructions.md`.

### 7. Run the Full Test Suite

```bash
pytest tests/ -x -q --tb=short
```

All tests must pass before the feature is considered complete.

### 8. Cross-Layer Follow-Ups

If the change exposes a **new field** on the `Character` response (e.g., a new derived stat, a new selection echo), also:

- Update `docs/APIContract.md`.
- Hand off to the `frontend` agent to add the field to `frontend/src/lib/api.ts` and surface it in the UI.

## Reference Files

- [Effect Type Catalog](./references/effect-type-catalog.md) — All supported effect types
- `docs/FEATURE_EFFECTS.md` — Canonical effect documentation
- `.github/instructions/effects-system.instructions.md` — Rules for adding effect types
- `.github/instructions/data-schemas.instructions.md` — Data file shapes
- `.github/instructions/choice-reference.instructions.md` — When the feature requires a player choice
- `.github/instructions/character-builder-api.instructions.md` — `to_character()` assertion paths
- `models/class_schema.json`, `models/subclass_schema.json` — Class/subclass schemas
