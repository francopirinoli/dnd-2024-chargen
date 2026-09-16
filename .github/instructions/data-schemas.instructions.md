---
description: "Use when creating or editing D&D game data JSON files: classes, subclasses, species, backgrounds, spells, feats. Covers required fields, data types, and the critical features_by_level object format."
applyTo: "data/**/*.json"
---

# Data File Schemas

All data files MUST comply with schemas in `models/`. Run `python validate_data.py` to check.

## Class Data (`data/classes/*.json`)

**Schema**: `models/class_schema.json`

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | Capitalized: "Wizard" |
| `description` | string | ✅ | |
| `hit_die` | integer | ✅ | One of: 6, 8, 10, 12 |
| `primary_ability` | string | ✅ | |
| `saving_throw_proficiencies` | array[2] | ✅ | Exactly 2 ability names |
| `subclass_selection_level` | integer | ✅ | 1, 2, or 3 |
| `proficiency_bonus_by_level` | object | ✅ | `"1"` → 2 through `"20"` → 6 |
| `features_by_level` | object | ✅ | **See critical format below** |
| `armor_proficiencies` | array | ❌ | |
| `weapon_proficiencies` | array | ❌ | |
| `spellcasting_ability` | string | ❌ | For casters only |
| `cantrips_by_level` | object | ❌ | `"1"` → count |
| `prepared_spells_by_level` | object | ❌ | `"1"` → count |
| `spell_slots_by_level` | object | ❌ | `"1"` → [9 integers] |

## Subclass Data (`data/subclasses/{class}/*.json`)

**Schema**: `models/subclass_schema.json`

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | "Light Domain" |
| `class` | string | ✅ | Parent class name |
| `description` | string | ✅ | |
| `source` | string | ✅ | "Player's Handbook 2024" |
| `features_by_level` | object | ✅ | **See critical format below** |

## Critical Format: `features_by_level`

Maps level (as **string**) → **OBJECT** of feature_name → description-or-object.

```json
// ❌ NEVER arrays
"features_by_level": {
  "1": ["Spellcasting", "Ritual Adept"]
}

// ✅ ALWAYS objects
"features_by_level": {
  "1": {
    "Spellcasting": "Cast spells using Intelligence.",
    "Ritual Adept": "Cast Ritual spells without preparing."
  }
}
```

### Feature Values

A feature value can be:
- **String**: Simple description (display-only)
- **Object**: Description + effects (mechanical benefit)

```json
"3": {
  "Bonus Cantrip": {
    "description": "You know the Light cantrip.",
    "effects": [
      {"type": "grant_cantrip", "spell": "Light"}
    ]
  },
  "Warding Flare": "React to impose disadvantage on an attack roll."
}
```

### `feature_kind`, `hidden`, `pdf_summary` (Phase 8)

Class and subclass features may carry three additional first-class fields:

| Field | Type | Notes |
|---|---|---|
| `feature_kind` | enum | `"normal"` (default) \| `"asi"` \| `"subclass_pick"` \| `"spellcasting_setup"` \| `"subclass_feature_slot"` |
| `hidden` | boolean | When `true`, suppress this feature from the rendered class-features list. |
| `pdf_summary` | string | Short PDF-style summary that replaces the verbose `description` when the feature is rendered on the sheet. |

The enum is **closed**. Do not invent new values — propose them in the audit-fix planning loop and extend `models/class_schema.json` + `models/subclass_schema.json` + the dispatch in `CharacterBuilder._apply_trait_effects` in lockstep.

Builder semantics:

- `feature_kind: "asi"` → always suppressed from the class-features list. The ASI slot is handled by the feat / ability-score pipeline.
- `feature_kind: "subclass_pick"` → always suppressed. The subclass selector handles this.
- `feature_kind: "subclass_feature_slot"` → rendered as a class-level header; the actual subclass feature lands alongside it via the subclass walk.
- `feature_kind: "spellcasting_setup"` → rendered normally, and triggers the legacy `choices_made["Spellcasting"]` cantrip-list append used by older saved characters.
- `hidden: true` → always suppressed, regardless of `feature_kind`. Use sparingly — `feature_kind` covers the structural cases.
- `pdf_summary` → if present, the rendered feature's `description` is replaced by this summary string.

### Forbidden: name-based branching for these categories

Do **not** add code that branches on a feature's display name to decide whether it is an ASI slot, a subclass-pick placeholder, a spellcasting-setup feature, or a subclass-feature slot. Examples that are no longer permitted (all removed in Phase 8):

```python
if normalized_trait_name == "ability score improvement": ...     # ❌
if normalized_trait_name == f"{class_name.lower()} subclass": ...  # ❌
if trait_name == "Spellcasting": ...                              # ❌
if trait_name == "Pact Magic": ...                                # ❌
```

The replacement is always `feature_kind`-based dispatch. If you need a new structural category, propose a new enum value rather than smuggling it back in as a name match.

## Species Data (`data/species/*.json`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | |
| `creature_type` | string | ✅ | Usually "Humanoid" |
| `size` | string | ✅ | "Small" or "Medium" |
| `speed` | integer | ✅ | Base walking speed |
| `darkvision` | integer | ❌ | Range in feet |
| `traits` | object | ✅ | Trait name → {description, effects?} |
| `languages` | array | ✅ | ["Common", ...] |

**Species do NOT have ability score increases** (those come from backgrounds in D&D 2024).

## Background Data (`data/backgrounds/*.json`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | |
| `ability_score_increase` | object | ✅ | `total`, `options`, `suggested` |
| `feat` | string | ✅ | Origin feat name |
| `skill_proficiencies` | array | ✅ | Exactly 2 skills |
| `starting_equipment` | object | ❌ | |

```json
"ability_score_increase": {
  "total": 3,
  "options": ["Strength", "Constitution", "Wisdom"],
  "suggested": {"Strength": 2, "Constitution": 1}
}
```

## Spell Definition (`data/spells/definitions/*.json`)

| Field | Type | Required |
|---|---|---|
| `name` | string | ✅ |
| `level` | integer | ✅ |
| `school` | string | ✅ |
| `casting_time` | string | ✅ |
| `range` | string | ✅ |
| `components` | string | ✅ |
| `duration` | string | ✅ |
| `description` | string | ✅ |
| `classes` | array | ✅ |
| `source` | string | ✅ |

## The 5 valid `effects`-array authoring locations

Every `effects` array in `data/` must appear in one of exactly **five** locations. This catalogue is the authoring contract; the runtime dispatcher counterpart is the **One Dispatcher Rule** in [.github/instructions/effects-system.instructions.md](./effects-system.instructions.md). Canonical wording lives in the `resolve_effects_for_choice` docstring in [modules/character_builder.py](../../modules/character_builder.py).

Every effect — regardless of which location below — is applied exclusively through `CharacterBuilder._apply_effect()`. The columns below name the **entry point** that hands the effect to the dispatcher so a contributor can trace JSON → handler.

### Location 1 — Top-level of a feat

Files: [data/general_feats.json](../../data/general_feats.json), [data/origin_feats.json](../../data/origin_feats.json). Entry point: feat loaders in [modules/feature_manager.py](../../modules/feature_manager.py).

```json
{
  "Tough": {
    "effects": [
      {"type": "bonus_hp", "value": 2, "scaling": "per_level"}
    ]
  }
}
```

### Location 2 — Inside a class / subclass / species feature

Path: `features_by_level.<lvl>.<feature_name>.effects` (or, for species, `traits.<name>.effects`). Entry point: `_apply_trait_effects` during the feature walk.

```json
"features_by_level": {
  "1": {
    "Unarmored Defense": {
      "description": "AC = 10 + DEX + CON.",
      "effects": [
        {"type": "alternative_ac", "formula": "10 + DEX + CON"}
      ]
    }
  }
}
```

### Location 3 — Inside `choice_effects` keyed by chosen option

The chosen option value is the key; its value is an effects array (or a list of them). Entry point: `_apply_species_choice_effects` (and the equivalent feat path).

```json
"choice_effects": {
  "Fire": [{"type": "grant_damage_resistance", "damage_type": "Fire"}],
  "Cold": [{"type": "grant_damage_resistance", "damage_type": "Cold"}]
}
```

### Location 4 — Inside a `choices` object on a feature

Effects attached to a sub-choice option, resolved at character-build time. Entry point: `resolve_effects_for_choice` → `_apply_effect`.

```json
"choices": {
  "type": "skill",
  "count": 1,
  "options": {
    "Stealth": {"effects": [{"type": "grant_skill_expertise", "skills": ["Stealth"]}]}
  }
}
```

### Location 5 — Inside a `source: "external"` file

The feature declares `choices.source` pointing at an external catalogue file; the chosen option's effects live in that file. [data/fighting_styles.json](../../data/fighting_styles.json) is the canonical example; future maneuvers and metamagic catalogues follow the same pattern. Entry point: `resolve_effects_for_choice` (external branch) → `_apply_effect`.

```json
// feature in a class file:
"Fighting Style": {
  "choices": {
    "source": {"type": "external", "file": "fighting_styles.json", "list": "fighting_styles"}
  }
}

// data/fighting_styles.json:
{
  "fighting_styles": {
    "Defense": {
      "effects": [{"type": "bonus_ac", "value": 1, "condition": "wearing armor"}]
    }
  }
}
```

### Rule

Anything outside these five locations is invalid authoring. If a new mechanical surface (e.g. metamagic, maneuvers) needs effects, model it on Location 5 — a `source: "external"` catalogue file — rather than inventing a sixth location.

## Validation

```bash
python validate_data.py          # Validate every file under data/
```

The validator walks `data/`, dispatches each file to the schema named in the `CATEGORIES` manifest at the top of [validate_data.py](../../validate_data.py), and exits non-zero on the first failure. It also **refuses to run** if any JSON file under `data/` is not covered by the manifest (and is not in `EXCLUDED_FILES`) — this is the gate that keeps new categories from landing without a schema.

## Schema coverage

Every category under `data/` has a schema in [models/](../../models/). Shared subschemas live in [models/_shared/](../../models/_shared/) and are referenced from entity schemas via relative `$ref` (e.g. `"$ref": "_shared/effect.json"`).

| Category               | Schema                                                                                      | applyTo glob                              |
|------------------------|---------------------------------------------------------------------------------------------|-------------------------------------------|
| classes                | [models/class_schema.json](../../models/class_schema.json)                                   | `data/classes/*.json`                     |
| subclasses             | [models/subclass_schema.json](../../models/subclass_schema.json)                             | `data/subclasses/*/*.json`                |
| species                | [models/species_schema.json](../../models/species_schema.json)                               | `data/species/*.json`                     |
| species_variants       | [models/species_variant_schema.json](../../models/species_variant_schema.json)               | `data/species_variants/*.json`            |
| backgrounds            | [models/background_schema.json](../../models/background_schema.json)                         | `data/backgrounds/*.json`                 |
| origin_feats           | [models/feat_schema.json](../../models/feat_schema.json)                                     | `data/origin_feats.json`                  |
| general_feats          | [models/feat_schema.json](../../models/feat_schema.json)                                     | `data/general_feats.json`                 |
| spell definitions      | [models/spell_schema.json](../../models/spell_schema.json)                                   | `data/spells/definitions/*.json`          |
| spell class lists      | [models/spell_class_list_schema.json](../../models/spell_class_list_schema.json)             | `data/spells/class_lists/*.json`          |
| weapons                | [models/weapon_schema.json](../../models/weapon_schema.json)                                 | `data/equipment/weapons.json`             |
| armor                  | [models/armor_schema.json](../../models/armor_schema.json)                                   | `data/equipment/armor.json`               |
| weapon masteries       | [models/weapon_mastery_schema.json](../../models/weapon_mastery_schema.json)                 | `data/equipment/weapon_masteries.json`    |
| adventuring gear       | [models/adventuring_gear_schema.json](../../models/adventuring_gear_schema.json)             | `data/equipment/adventuring_gear.json`    |
| fighting styles        | [models/fighting_style_schema.json](../../models/fighting_style_schema.json)                 | `data/fighting_styles.json`               |
| eldritch invocations   | [models/eldritch_invocation_schema.json](../../models/eldritch_invocation_schema.json)       | `data/eldritch_invocations.json`          |
| languages              | [models/languages_schema.json](../../models/languages_schema.json)                           | `data/languages.json`                     |
| feature override       | [models/feature_override_schema.json](../../models/feature_override_schema.json)             | `data/feature_override.json`              |
| trait patterns         | [models/trait_patterns_schema.json](../../models/trait_patterns_schema.json)                 | `data/trait_patterns.json`                |

### Shared subschemas

| Subschema                                              | Used by                                                                                  |
|--------------------------------------------------------|------------------------------------------------------------------------------------------|
| [models/_shared/effect.json](../../models/_shared/effect.json)               | species, species_variants, backgrounds, feat (general/origin), fighting_styles, eldritch_invocations, trait_entry, choice_effects |
| [models/_shared/choice.json](../../models/_shared/choice.json)               | species (via trait_entry), feat, eldritch_invocations                                    |
| [models/_shared/choice_effects.json](../../models/_shared/choice_effects.json) | species (via trait_entry), feat, eldritch_invocations                                  |
| [models/_shared/trait_entry.json](../../models/_shared/trait_entry.json)     | species, species_variants                                                                |

Phase 3 deliberately leaves `effect.type` open (any string). Phase 5 (audit item `D6-4`) ratchets it to a closed enum — when that happens, only `models/_shared/effect.json` needs editing.

### Rule

**Every new category under `data/` requires a schema in `models/` and an entry in the `CATEGORIES` manifest in [validate_data.py](../../validate_data.py) before the first data file lands.** `validate_data.py` will refuse to run otherwise.
