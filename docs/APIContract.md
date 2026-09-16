# API Contract — `/api/v1`

The REST API is **stateless JSON**. No server-side request state, no cookies. The frontend is the source of truth for in-progress `choices_made`; the backend (`CharacterBuilder`) is the source of truth for every calculated value.

Source layout:

| Blueprint          | Mount        | File                     |
|--------------------|--------------|--------------------------|
| `api_v1_bp`        | `/api/v1`    | [routes/api/__init__.py](../routes/api/__init__.py) |
| `catalog_bp`       | `/catalog`   | [routes/api/catalog.py](../routes/api/catalog.py) |
| `character_bp`     | `/character` | [routes/api/character.py](../routes/api/character.py) |
| `wizard_bp`        | `/wizard`    | [routes/api/wizard.py](../routes/api/wizard.py) |

All paths below are prefixed with `/api/v1`.

## Health

| Method | Path      | Response                              |
|--------|-----------|---------------------------------------|
| GET    | `/health` | `{ "status": "ok", "version": "v1" }` |

## Catalog

Read-only access to game data. Cached aggressively on the client.

| Method | Path                                                         | Response (success)                                  |
|--------|--------------------------------------------------------------|-----------------------------------------------------|
| GET    | `/catalog/classes`                                           | `{ "classes": ClassSummary[] }`                     |
| GET    | `/catalog/classes/<class_name>`                              | Full class JSON (raw `data/classes/<n>.json`)       |
| GET    | `/catalog/classes/<class_name>/subclasses`                   | `{ "class": str, "subclasses": Summary[] }`         |
| GET    | `/catalog/classes/<class_name>/subclasses/<subclass_name>`   | Full subclass JSON                                  |
| GET    | `/catalog/species`                                           | `{ "species": SpeciesSummary[] }`                   |
| GET    | `/catalog/species/<species_name>`                            | Full species JSON (with `lineages`, `traits`)       |
| GET    | `/catalog/backgrounds`                                       | `{ "backgrounds": BackgroundSummary[] }` (active D&D 2024 only by default; `?include_legacy=true` includes retained legacy entries) |
| GET    | `/catalog/backgrounds/<background_name>`                     | Full background JSON                                |
| GET    | `/catalog/feats?type=origin\|general`                        | `{ "feats": FeatSummary[] }` (optional filter)      |
| GET    | `/catalog/feats/<feat_name>`                                 | Full feat JSON                                      |
| GET    | `/catalog/spells/<class_name>?level=N`                       | Class spell list. `level=0` returns cantrips. Omit `level` for the full list. |
| GET    | `/catalog/spells/definitions/<spell_name>`                   | Single spell definition (`data/spells/definitions/<slug>.json`) |
| GET    | `/catalog/equipment/<kind>`                                  | Raw equipment JSON. `kind ∈ { weapons, armor, adventuring_gear, weapon_masteries }` |
| GET    | `/catalog/reference/<name>`                                  | Top-level reference JSON. `name ∈ { fighting_styles, eldritch_invocations, origin_feats, general_feats, trait_patterns }` |

### Summary shapes

```ts
interface ClassSummary {
  id: string; name: string; description?: string;
  hit_die?: number; primary_ability?: string;
  subclass_selection_level?: number;
}

interface SpeciesSummary {
  id: string; name: string; description?: string;
  creature_type?: string; size?: string; speed?: number; darkvision?: number;
  has_lineages: boolean;     // true if `lineages` is non-empty
  has_trait_choices: boolean;// true if any trait has type === "choice"
}

interface BackgroundSummary {
  id: string; name: string; description?: string;
  skill_proficiencies?: string[]; ability_scores?: string[]; feat?: string;
  edition: "2024" | "2014"; status: "active" | "legacy";
}

interface FeatSummary {
  id: string; name: string; description?: string;
  category?: "origin" | "general"; prerequisites?: unknown;
}
```

`GET /catalog/backgrounds` is the wizard/frontend default catalog and filters to backgrounds with `edition: "2024"` and `status: "active"`. Retained 2014 legacy backgrounds remain available by direct detail lookup and through `?include_legacy=true` for explicit opt-in tools.

### Errors

- `404` with `{ "description": "..." }` for unknown class, subclass, species, background, feat, spell or equipment kind.
- `400` with `{ "description": "level must be an integer" }` from `/catalog/spells/<class>` when `level` is not numeric.

## Wizard

| Method | Path                  | Response                                                |
|--------|-----------------------|---------------------------------------------------------|
| GET    | `/wizard/steps`       | `{ "steps": WizardStep[] }`                             |
| GET    | `/wizard/dependencies`| `{ "dependencies": Record<string, string[]> }`          |

```ts
interface WizardStep {
  id: string;
  label: string;
  description: string;
  required_keys: string[];
  nested_choices?: string[];
}
```

Current step order (as returned by `/wizard/steps`):

```json
[
  "class",
  "background",
  "species",
  "languages",
  "abilities",
  "equipment",
  "complete"
]
```

Current required keys for the class step (as returned by `/wizard/steps`):

```json
{
  "id": "class",
  "required_keys": ["class"]
}
```

Dependency excerpt (from `/wizard/dependencies`):

```json
{
  "classes": [
    "subclass",
    "fighting_style",
    "maneuvers",
    "spells",
    "cantrips",
    "class_features"
  ],
  "class": [
    "subclass",
    "fighting_style",
    "maneuvers",
    "spells",
    "cantrips",
    "class_features"
  ]
}
```

See [docs/WizardFlow.md](WizardFlow.md) for the full step list, dependency map, and cascade semantics.

## Character

All character endpoints are `POST` with `Content-Type: application/json` and a body containing `choices_made` (and, where required, `step` or `view`).

### Shared request validation

All character endpoints validate their outer request envelope before processing. Envelopes are closed: unknown top-level fields return `400`. The permitted fields are:

| Endpoint | Permitted request fields |
|----------|--------------------------|
| `/character/build`, `/character/validate`, `/character/random-languages` | `choices_made` |
| `/character/preview-step` | `choices_made`, `step` |
| `/character/derived` | `choices_made`, `view` |

`choices_made` must be a JSON object. Its keys must be recognized static choices, data-driven choices, or supported dynamic choice keys; unknown choices are rejected. JSON arrays and objects are limited to 100 items, strings and object keys to 512 characters, and nesting to 8 levels. Class allocations have a separate maximum of 12 rows.

Class levels must be JSON integers (not booleans) from `1` through `20`; the sum of all `classes[].level` values cannot exceed `20`. Each class row is a closed object with only `class_name`, `level`, and optional `subclass`.

When supplied, `ability_scores` (or the legacy `abilities` alias) must be exactly:

```json
{
  "Strength": 8,
  "Dexterity": 8,
  "Constitution": 8,
  "Intelligence": 8,
  "Wisdom": 8,
  "Charisma": 8
}
```

All six values must be integer (not boolean) scores from `1` through `20`.

Class, subclass, species, background, and lineage identifiers are trimmed, matched case-insensitively against the catalog, and normalized to their canonical catalog spelling. Unknown identifiers are rejected.

All request-validation failures use HTTP `400` and this envelope:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Human-readable validation message",
    "field": "choices_made.classes[0].level"
  }
}
```

`field` is omitted when the failure is not attributable to one field. Codes include `invalid_request`, `missing_field`, `unknown_field`, `unknown_identifier`, `out_of_bounds`, and `choice_error`.

### `POST /character/build`

Build the complete calculated character.

Request:
```json
{ "choices_made": { /* ChoicesMade */ } }
```

Request notes:
- Supports single-class compatibility inputs (`class`, `level`, optional `subclass`).
- Also supports `choices_made.classes` in this shape:

```json
{
  "choices_made": {
    "classes": [
      {
        "class_name": "Wizard",
        "level": 3,
        "subclass": "Evoker"
      }
    ]
  }
}
```

- `classes` may contain multiple rows. The builder applies each row's class/subclass features and computes total character level as the sum of row levels.
- The **first row is the primary class** (used for level-1 max-hit-die HP and starting proficiencies); subsequent rows are secondary classes (proficiencies are limited to each class's `multiclassing` block — see [DataFiles.md](DataFiles.md#multiclassing-block) and [character_builder_guide.md](character_builder_guide.md#multiclassing)).
- `proficiency_bonus` is computed from total character level.
- Multiclass spellcasting progression now uses effective caster level aggregation for standard slots:
  - Full caster row contributes `class_level`.
  - Half caster row contributes `ceil(class_level / 2)` (RAW, "round up").
  - Third caster row contributes `floor(class_level / 3)`.
  - Non-caster row contributes `0`.
- Standard spell slots use the canonical full-caster slot table keyed by `effective_caster_level`.
- Pact Magic slots are tracked separately and are not merged into standard multiclass slots in this phase.
- Single-class spell slot behavior remains compatible with previous responses.

Response (200):
```json
{ "character": { /* Character — see "Character Shape" below */ } }
```

Errors:
- `400` request-validation errors use the [shared error envelope](#shared-request-validation).
- `400` for invalid submitted managed selections (spell selections, weapon masteries, eldritch invocations):

```json
{
  "error": "Submitted spell selections are not valid for this character",
  "selection_family": "spell_selections",
  "code": "invalid_selection",
  "violations": [
    {
      "field": "spell_selections.spells",
      "reason": "unavailable_selection",
      "selections": ["Cure Wounds"]
    }
  ]
}
```

- `500` `{ "error": "Internal server error", "correlation_id": "<id>" }`

### `POST /character/validate`

Per-step completion status.

Request:
```json
{ "choices_made": { /* ChoicesMade */ } }
```

Request notes are identical to `/character/build` for `choices_made.classes` and single-class `class`/`level` compatibility.

Validation behavior for class rows:
- For `choices_made.classes`, validation checks each row independently.
- If a row's level meets that class's `subclass_selection_level`, `classes[i].subclass` is required.
- Single-class `class`/`level` payloads still use `subclass` for this check.

Response (200):
```json
{
  "complete": true,
  "steps": [
    { "step": "class",      "complete": false, "missing": ["subclass"] },
    { "step": "background", "complete": true,  "missing": [] },
    { "step": "species",    "complete": true,  "missing": [] },
    { "step": "languages",  "complete": true,  "missing": [] },
    { "step": "abilities",  "complete": true,  "missing": [] },
    { "step": "equipment",  "complete": true,  "missing": [] }
  ]
}
```

`complete` is `all(s.complete for s in steps)`. Conditional checks: subclass when level qualifies, species/background skill-replacement when there is overlap, species trait choices, lineage when species has lineages, background ASI when offered, class feature `nested_choices`.

Errors:
- `400` request-validation errors use the [shared error envelope](#shared-request-validation).
- `500` `{ "error": "Internal server error", "correlation_id": "<id>" }`

> **Type drift to fix on the frontend:** `frontend/src/lib/api.ts` declares `ValidationResponse` as `{ valid, steps, missing_top_level }`, but the server returns `{ complete, steps }`. The frontend types must be updated to match.

### `POST /character/preview-step`

Return the dynamic, data-driven options for a given wizard step. This is the data feed for nested-choice rendering.

Request:
```json
{ "choices_made": { /* ChoicesMade */ }, "step": "class" }
```

Response (200) — **always includes `step`**, plus a step-specific payload. Examples:

```jsonc
// step: "class"
{
  "step": "class",
  "needs_subclass": true,
  "available_subclasses": [{
    "id": "...",
    "name": "...",
    "description": "...",
    "level_3_feature_names": ["Feature A", "Feature B", "Feature C"]
  }],
  "features_by_level": { "1": { "Feature": "Description" } },
  "nested_choices": [ /* choice descriptors */ ],
  "multiclass_prerequisites": {
    "classes": {
      "Wizard": { "ok": false, "missing": ["Intelligence"], "messages": ["Requires Intelligence 13+ (have 10)"], "abilities_unknown": false }
    }
  },
  "class_feat_prerequisite_warnings": [
    { "choice_key": "class_feat_4", "feat_name": "Great Weapon Master", "messages": ["Requires Strength 13+. Current Strength: 10."] }
  ],
  "row_context": {
    "row_index": 0,        // index into choices_made.classes
    "is_primary": true,    // row_index == 0
    "total_class_rows": 1
  }
}
```

#### `step: "class"` — row context and multiclass filtering

Every `class` preview response carries a `row_context` object describing which row of `choices_made.classes` the payload corresponds to:

| Field              | Type    | Meaning                                                          |
|--------------------|---------|------------------------------------------------------------------|
| `row_index`        | int     | Index of the resolved row in `choices_made.classes`.             |
| `is_primary`       | bool    | `true` when `row_index == 0` (the primary class).                |
| `total_class_rows` | int     | Length of `choices_made.classes`.                                |

Resolution: the server matches the request's previewed class (case-insensitive) against `choices_made.classes` and returns the first matching row. Single-class payloads (`class` / `level` without a `classes` array) always receive `{"row_index": 0, "is_primary": true, "total_class_rows": 1}` with `nested_choices` unfiltered.

When `is_primary` is `false`, `nested_choices` is filtered **server-side** only for multiclass proficiency narrowing. The filter consults the class's `multiclassing` block (see [DataFiles.md](DataFiles.md#multiclassing-block)) and:

| Category in `nested_choices`                | Kept on secondary rows? | Conditions                                                                                              |
|---------------------------------------------|-------------------------|---------------------------------------------------------------------------------------------------------|
| Skill picker                                | Only when allowed       | `multiclassing.skill_proficiencies` is non-null (Bard, Rogue, Ranger). `count` and `options` are narrowed to the multiclass entry — Bard = any skill, Rogue / Ranger = their constrained lists. |
| Tool picker                                 | Only when allowed       | `multiclassing.tool_training` contains a wildcard "(N of your choice)" entry (e.g. Bard musical instrument). `count` and `options` reflect the wildcard. |
| Feature picker / non-core-trait choices | Always preserved        | Feature-driven choices are returned unchanged on secondary rows, including features unlocked above level 1. |
| Subclass selection (`needs_subclass` / `available_subclasses`) | Always              | Reported via top-level fields, independent of `nested_choices` filtering. Always allowed at the subclass-unlock level for every row. |
| Fighting style, expertise, bonus cantrip, weapon mastery, eldritch invocations, other non-core-trait categories | Always preserved | Class features continue to apply on secondary rows according to the selected class level. |

Example secondary-row payload (`choices_made.classes = [{Wizard, 5}, {Rogue, 1}]`, previewing Rogue):

```jsonc
{
  "step": "class",
  "needs_subclass": false,
  "features_by_level": { "1": { "Expertise": "...", "Sneak Attack": "..." } },
  "nested_choices": [
    {
      "type": "skills",
      "choice_key": "skill_choices",
      "count": 1,
      "description": "Choose 1 skill proficiency (multiclass).",
      "options": ["Acrobatics", "Athletics", "Insight", "Investigation", "Perception", "Persuasion", "Sleight of Hand", "Stealth"]
    }
  ],
  "row_context": { "row_index": 1, "is_primary": false, "total_class_rows": 2 }
}

// step: "species"
{
  "step": "species",
  "traits": { /* species traits */ },
  "lineages": [{ "id": "...", "name": "...", "description": "...", "traits": {} }],
  "trait_choices": { /* per-trait option lists */ },
  "species_feat_choices": { /* */ },
  "skill_replacement": { "needed": false }
}

// step: "background"
{
  "step": "background",
  "skill_replacement": { "needed": 0 },
  "origin_feat_choices": [/* */]
}

// step: "languages"
{
  "step": "languages",
  "language_options": {
    "base_languages": ["Common"],
    "available_languages": [
      "Common Sign Language",
      "Draconic",
      "Dwarvish",
      "Elvish",
      "Giant",
      "Gnomish",
      "Goblin",
      "Halfling",
      "Orc"
    ],
    "selection_count": 2,
    "selected_languages": ["Elvish", "Dwarvish"]
  }
}

// step: "abilities"
{
  "step": "abilities",
  "background_asi": { "total_points": 3, "options": [/* */] },
  "ability_generation": {
    "abilities": {
      "Strength": { "score": 10, "modifier": 0, "modifier_display": "+0", "modifier_tone": "neutral" }
    },
    "standard_array": { "values": [15, 14, 13, 12, 10, 8], "assigned_count": 6, "complete": true, "valid": true },
    "point_buy": { "total": 27, "min": 8, "max": 15, "spent": 27, "remaining": 0, "valid": true, "controls": {} },
    "manual": { "min": 3, "max": 18 },
    "background_asi": { "spent": 3, "remaining": 0, "values_by_ability": {} }
  },
  "recommended_array": { "STR": 8, "DEX": 14, /* … */ }
}

// step: "equipment"
{
  "step": "equipment",
  "class_equipment": { /* class starting_equipment */ },
  "background_equipment": { /* background starting_equipment */ }
}
```

Errors:
- `400` request-validation errors use the [shared error envelope](#shared-request-validation).
- `500` `{ "error": "Internal server error", "correlation_id": "<id>" }`

### `POST /character/derived`

Return a derived view-model for the SPA. Used for screens that need a tailored shape rather than the full `Character`.

Request:
```json
{ "choices_made": { /* ChoicesMade */ }, "view": "damage_cantrips" }
```

Allowed `view` values:

| `view`                  | Built by                                    | Prerequisite (else `applicable:false`) |
|-------------------------|---------------------------------------------|-----------------------------------------|
| `damage_cantrips`       | `derived_stats.build_damage_cantrip_rows`   | None                                    |
| `spell_management`      | `derived_stats.build_spell_management_view` | Character has spellcasting              |
| `mastery_management`    | `derived_stats.build_mastery_management_view` | Character has weapon mastery          |
| `invocation_management` | `derived_stats.build_invocation_management_view` | Character is a Warlock             |

For `invocation_management`, `data.cantrip_choice_descriptors` contains the
server-validated pickers produced by selected invocation effects. Each
descriptor has `{ id, invocation, count, spell_list, options, selected }`.
Submit selections in the canonical nested shape
`eldritch_invocation_selections: { selected: string[], cantrip_choices: { [id]: string[] } }`.
Legacy `eldritch_invocation_selections: string[]` payloads remain accepted.

Response (200):
```json
{
  "view": "<name>",
  "applicable": true,
  "choices_made": { /* echoed request choices */ },
  "data": { /* view-specific shape */ }
}
```

Response (200, valid view but not applicable):
```json
{
  "view": "<name>",
  "applicable": false,
  "choices_made": { /* echoed request choices */ },
  "reason": "<message>",
  "data": null
}
```

Errors:
- `400` request-validation errors use the [shared error envelope](#shared-request-validation). For an unknown `view`, the response also includes `allowed` with the accepted values.
- `500` `{ "error": "Internal server error", "correlation_id": "<id>" }`

### `POST /character/random-languages`

Return a backend-validated random selection for the language step.

Request:
```json
{ "choices_made": { /* ChoicesMade */ } }
```

Response (200):
```json
{ "languages": ["Elvish", "Gnomish"] }
```

Errors:
- `400` request-validation errors use the [shared error envelope](#shared-request-validation).
- `500` `{ "error": "Internal server error", "correlation_id": "<id>" }`

### `POST /character/roll-abilities`

Return backend-rolled 4d6-drop-lowest candidates for the ability step. The frontend displays and assigns these raw roll values; modifier labels are supplied by the backend.

Response (200):
```json
{
  "rolls": [
    { "value": 14, "dice": [6, 5, 3, 1], "modifier": 2, "modifier_display": "+2", "modifier_tone": "positive" }
  ]
}
```

Errors:
- `500` `{ "error": "Internal server error", "correlation_id": "<id>" }`

## Canonical Request — `ChoicesMade`

The canonical `ChoicesMade` shape is defined in `frontend/src/lib/api.ts` and validated by `ChoicesMadeSchema` (Zod). All character endpoints accept this body.

### Content identifiers

`species`, `lineage`, `background`, `subclass` and `classes[].class_name` name
game-content JSON files under `data/`. Only canonical content identifiers are
accepted — the display name of an existing catalog entry (e.g. `"Wood Elf"`,
`"Fighter"`). Unknown names, path separators, traversal segments and absolute
paths are rejected by every `/character/*` endpoint with the `400` envelope
above, using code `unknown_identifier` and a generic message that never echoes
the submitted value:

```json
{
  "error": {
    "code": "unknown_identifier",
    "message": "Invalid character request",
    "field": "choices_made.species"
  }
}
```

`CharacterBuilder` enforces the same rule independently: every content load
resolves through a canonical slug and is verified to stay inside its expected
`data/` subdirectory, so a malformed identifier can never reach the filesystem.

### Primary class carrier: `classes`

`classes` is the authoritative way to specify class allocation. The client (post-Phase 11) always writes `classes` and never writes flat `class` / `level` / `subclass` keys. The server normalises legacy flat keys inbound (see `_normalize_multiclass_rows()`) for backward compatibility, but the client must not rely on that path for new builds.

```ts
interface ClassAllocation {
  class_name: string;
  level: number;
  subclass?: string;
}

interface AbilityScores {
  Strength: number; Dexterity: number; Constitution: number;
  Intelligence: number; Wisdom: number; Charisma: number;
}
```

The `classes` array may contain multiple rows for multiclass characters. The **first row is the primary class** (full starting proficiencies and level-1 max-hit-die HP); subsequent rows are secondary classes (proficiencies limited to each class's `multiclassing` block). `proficiency_bonus` is computed from total character level (`sum(classes[].level)`).

### Full interface

```ts
interface ChoicesMade {
  character_name?: string;
  /** Primary class carrier. Always use this; never write flat `class`/`level`/`subclass`. */
  classes?: ClassAllocation[];
  background?: string;
  species?: string;
  lineage?: string;
  ability_scores_method?: "standard_array" | "point_buy" | "manual" | "roll" | "recommended";
  ability_scores?: AbilityScores; // each value is an integer from 1 through 20
  additional_ability_modifiers?: Record<string, number>;
  background_bonuses?: Record<string, number>;
  skill_choices?: string[];
  tool_choices?: string[];
  fighting_style?: string;
  maneuvers?: string[];
  equipment_selections?: Record<string, string>;
  languages_chosen?: string[];
  background_skill_replacement?: string[];
  species_skill_replacement?: string[];
  species_trait_choices?: Record<string, string>;
  species_feat_choices?: Record<string, string>;
  origin_feat?: string;
  // Multiclass: player's resolution of pending skill picks per secondary class
  multiclass_skill_choices?: Record<string, string[]>;
  // Dynamic keys: feat sub-choices, ASI variants, per-feature picks, etc.
  // Only supported dynamic keys are accepted; the backend resolves and
  // normalises them via apply_choices() Pass 2.
  [key: string]: unknown;
}
```

> **Legacy compatibility**: the server's inbound normaliser still accepts flat `class`, `level`, and `subclass` at the top level of `choices_made`. These are treated as equivalent to a single-row `classes` array. The client must not write them; they exist only so that older saved characters and tests can be replayed without a migration.

## Canonical Response — `Character` Shape

The `Character` object is the literal output of `CharacterBuilder.to_character()` ([modules/character_builder.py](../modules/character_builder.py), starting around line 4221). `to_character()` is the **source of truth** for the shape; this section catalogues the fields it adds on top of the stored `character_data` so consumers know what to expect.

### Identity / inputs (echoed)

| Field        | Type                                | Notes                                  |
|--------------|-------------------------------------|----------------------------------------|
| `name`       | `string`                            | From `choices_made.character_name`.    |
| `level`      | `number`                            |                                        |
| `class`      | `string`                            |                                        |
| `subclass`   | `string \| undefined`               |                                        |
| `background` | `string`                            |                                        |
| `species`    | `string`                            |                                        |
| `lineage`    | `string \| undefined`               |                                        |

### Calculated stats added by `to_character()`

| Field                       | Source                                              | Notes                                                                 |
|-----------------------------|-----------------------------------------------------|-----------------------------------------------------------------------|
| `ability_scores`            | `self.ability_scores.final_scores`                  | Map of ability → final score.                                         |
| `abilities`                 | `calculate_processed_ability_scores()`              | Map of ability → `{ score, modifier, save_modifier, save_proficient, ... }`. |
| `skills`                    | `calculate_skills()`                                | Map of skill → `{ modifier, proficient, expertise?, ... }`.           |
| `combat`                    | `calculate_combat_stats()`                          | `{ armor_class, initiative, initiative_bonus, speed, hit_point_maximum, hit_points: { current, maximum, temporary }, hp_breakdown, hit_dice: { total, spent }, passive_perception }`. `hit_dice.total` and `passive_perception` are display-ready server-calculated values. |
| `darkvision`                | Applied via effects system                          | Range of darkvision in feet. `0` means no darkvision. Examples: `0` (Human), `60` (Elf), `120` (Orc). |
| `attacks`                   | `calculate_weapon_attacks().attacks`                | List of attack rows.                                                  |
| `attack_combinations`       | `calculate_weapon_attacks().combinations`           | List of multi-weapon combinations, sorted by backend recommendation with `rank` and `recommended` fields. |
| `best_attack_combination`   | `calculate_weapon_attacks().combinations[0]`        | Recommended attack combination for sheets.                            |
| `ac_options`                | `calculate_ac_options()`                            | List of AC formulas with their components.                            |
| `spells_by_level`           | Computed inline                                     | `{ [level: number]: SpellDefinition[] }` — flattens `always_prepared`, `prepared`, `known`, `background_spells` and merges with definitions from `data/spells/definitions/`. |
| `spell_slots`               | Inline (override if supplied; otherwise computed)    | `{ "1st": n, "2nd": n, ... }` (English ordinals). For multiclass rows, standard slots come from the canonical full-caster table keyed by `effective_caster_level`; single-class fallback remains class/subclass-by-level. |
| `pact_magic_slots`          | Inline (multiclass spellcasting calc)               | Optional list of Pact Magic slot tracks, one entry per pact-contributing row. |
| `spell_slot_notes`          | Inline (multiclass spellcasting calc)               | Optional explanatory notes for slot handling (for example, pact slots tracked separately). |
| `proficiency_bonus`         | `calculate_proficiency_bonus(level)`                | Uses total character level (`sum(classes[].level)` when `classes` is present). |
| `spellcasting_stats`        | `calculate_spellcasting_stats()`                    | Save DC, attack bonus, ability, prepared count, plus multiclass metadata: `effective_caster_level`, `pact_magic_slots`, `multiclass_notes`. |
| `weapon_mastery_stats`      | `calculate_weapon_mastery_stats()`                  | Mastery slots, selected weapons, available masteries.                 |
| `eldritch_invocation_stats` | `calculate_eldritch_invocation_stats()`             | Warlock only; populated otherwise as an empty/zero shape.             |
| `effects`                   | `self.applied_effects` (copied)                     | Each entry is the original effect dict augmented with `source` and `source_type`. |

Multiclass spellcasting additive fields now available in build responses:

- `character.pact_magic_slots`
- `character.spell_slot_notes`
- `character.spellcasting_stats.effective_caster_level`
- `character.spellcasting_stats.pact_magic_slots`
- `character.spellcasting_stats.multiclass_notes`

### Multiclass pending choices

When a secondary class's `multiclassing` block requires the player to pick skills or tools (Bard, Rogue, Ranger), the build response surfaces them as optional top-level arrays. Both default to `[]` (or are omitted) when nothing is pending. They are **backward-compatible additive fields** — existing single-class responses are unchanged.

| Field                              | Type                                                                | Notes                                                       |
|------------------------------------|---------------------------------------------------------------------|-------------------------------------------------------------|
| `pending_multiclass_skill_choices` | `Array<{ class_name: string; count: number; options: string[] \| "any" }>` | One entry per secondary class awaiting a skill pick.        |
| `pending_multiclass_tool_choices`  | `Array<{ class_name: string; label: string }>`                      | One entry per secondary class awaiting a tool pick (e.g. Bard musical instrument). |

The player resolves skill picks by including `multiclass_skill_choices` in the next request:

```json
{
  "choices_made": {
    "classes": [
      { "class_name": "Fighter", "level": 5 },
      { "class_name": "Bard",    "level": 1 }
    ],
    "multiclass_skill_choices": {
      "Bard": ["Persuasion"]
    }
  }
}
```

Once resolved, the corresponding entry disappears from `pending_multiclass_skill_choices` on the next build.

### Flattened proficiencies

| Field                  | Source                              |
|------------------------|-------------------------------------|
| `languages`            | `proficiencies.languages`           |
| `skill_proficiencies`  | `proficiencies.skills`              |
| `weapon_proficiencies` | `proficiencies.weapons`             |
| `armor_proficiencies`  | `proficiencies.armor`               |
| `tool_proficiencies`   | `proficiencies.tools`               |

The original nested `proficiencies` object is also preserved.

### `choices_made` echo

`to_character()` re-injects three derived selection lists into `choices_made` so the dict round-trips cleanly through export/import:

| Key                              | When present                                  |
|----------------------------------|-----------------------------------------------|
| `spell_selections`               | Any cantrip/spell/background spell selected. Shape: `{ cantrips, spells, background_cantrips, background_spells }` (lists of names). |
| `weapon_mastery_selections`      | Any weapon masteries selected.                |
| `eldritch_invocation_selections` | Warlock with at least one invocation chosen. Shape: `{ selected, cantrip_choices }`, where `cantrip_choices` maps invocation effect descriptor IDs to selected cantrip names. |

### Other fields

`features`, `proficiencies`, `equipment`, `spells` (raw store), `class_data`, `subclass_data`, `species_data`, `background_data` and any other keys placed on `character_data` during the build are passed through unchanged. Treat any field not listed above as **read-through from the underlying `character_data`** and verify against `to_character()` if you need a guarantee.

## Type Drift Follow-Ups for the Frontend

These are gaps between `frontend/src/lib/api.ts` and the server. Filed as follow-ups for the `frontend` agent:

1. **`ValidationResponse`** — frontend declares `{ valid, steps, missing_top_level }`; server returns `{ complete, steps }`. Update the type and any consumer.
2. **`PreviewStepResponse`** — frontend declares `{ choices_made, [key]: unknown }`; server returns `{ step, ... }` with no `choices_made`. Update the type.
3. **Catalog client coverage** — `api.catalog` is missing typed methods for `feats`, `feat`, `spells/<class>`, `spells/definitions/<spell>`, `equipment/<kind>`, and `reference/<name>`. Add wrappers consistent with the existing `classes` / `species` / `backgrounds` helpers.

## See Also

- [docs/Architecture.md](Architecture.md)
- [docs/WizardFlow.md](WizardFlow.md)
- [docs/character_builder_guide.md](character_builder_guide.md)
- [docs/FEATURE_EFFECTS.md](FEATURE_EFFECTS.md)
- [.github/instructions/character-builder-api.instructions.md](../.github/instructions/character-builder-api.instructions.md)
