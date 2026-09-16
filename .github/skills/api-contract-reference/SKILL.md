---
name: api-contract-reference
description: "Reference skill. REST API v1 endpoint catalogue and request/response shapes. Use before adding/changing endpoints or wiring a new frontend call."
---

# API Contract Reference (`/api/v1`)

> Authoritative source: [docs/APIContract.md](../../../docs/APIContract.md). This skill is a quick lookup. Defer to the doc for full request/response shapes, error payloads and the `Character` field catalogue.

All endpoints are **stateless JSON**. The frontend holds `choices_made`; the backend computes everything else via `CharacterBuilder`.

## Health

| Method | Path             | Purpose         |
|--------|------------------|-----------------|
| GET    | `/api/v1/health` | Liveness probe  |

## Catalog (`routes/api/catalog.py`, mounted at `/api/v1/catalog`)

| Method | Path                                                        | Purpose                                  |
|--------|-------------------------------------------------------------|------------------------------------------|
| GET    | `/catalog/classes`                                          | List all classes                         |
| GET    | `/catalog/classes/<class_name>`                             | Single class detail                      |
| GET    | `/catalog/classes/<class_name>/subclasses`                  | List subclasses for a class              |
| GET    | `/catalog/classes/<class_name>/subclasses/<subclass_name>`  | Subclass detail                          |
| GET    | `/catalog/species`                                          | List species                             |
| GET    | `/catalog/species/<species_name>`                           | Species detail (with lineages, traits)   |
| GET    | `/catalog/backgrounds`                                      | List backgrounds                         |
| GET    | `/catalog/backgrounds/<background_name>`                    | Background detail                        |
| GET    | `/catalog/feats?type=origin\|general`                       | List feats (optional category filter)    |
| GET    | `/catalog/feats/<feat_name>`                                | Feat detail                              |
| GET    | `/catalog/spells/<class_name>?level=N`                      | Class spell list (level=0 = cantrips)    |
| GET    | `/catalog/spells/definitions/<spell_name>`                  | Single spell definition                  |
| GET    | `/catalog/equipment/<kind>`                                 | `kind ∈ { weapons, armor, adventuring_gear, weapon_masteries }` |
| GET    | `/catalog/reference/<name>`                                 | `name ∈ { fighting_styles, eldritch_invocations, origin_feats, general_feats, trait_patterns }` |

## Wizard (`routes/api/wizard.py`, mounted at `/api/v1/wizard`)

| Method | Path                       | Purpose                                  |
|--------|----------------------------|------------------------------------------|
| GET    | `/wizard/steps`            | Ordered wizard steps + required keys     |
| GET    | `/wizard/dependencies`     | Map of which choices invalidate which    |

## Character (`routes/api/character.py`, mounted at `/api/v1/character`)

| Method | Path                          | Purpose                                                 |
|--------|-------------------------------|---------------------------------------------------------|
| POST   | `/character/build`            | Build a fully calculated character from `choices_made`  |
| POST   | `/character/validate`         | Per-step completion status                              |
| POST   | `/character/preview-step`     | Step-specific dynamic option payload                    |
| POST   | `/character/derived`          | Derived view-models (see allowed `view` values below)   |

`/character/build` and `/character/validate` accept both legacy single-class keys (`class`, `level`, optional `subclass`) and multiclass rows via `choices_made.classes`.

Multiclass behavior snapshot:
- total character level = sum of `classes[].level`
- proficiency bonus follows total level
- additional class-row features are applied
- validation requires `classes[i].subclass` when that row meets subclass threshold
- spellcasting progression is currently conservative/primary-row based

### `POST /character/derived` — allowed `view` values

| `view`                  | Prerequisite (else 400)        |
|-------------------------|--------------------------------|
| `damage_cantrips`       | None                           |
| `spell_management`      | Character has spellcasting     |
| `mastery_management`    | Character has weapon mastery   |
| `invocation_management` | Character is a Warlock         |

Unknown `view` returns `400` with `{ "error": "Unknown view '<x>'", "allowed": [...] }`.

## Canonical Request Shape — `choices_made`

```ts
interface ChoicesMade {
  character_name?: string;
  level?: number;
  class?: string;
  classes?: Array<{
    class_name: string;
    level: number;
    subclass?: string;
  }>;
  subclass?: string;
  background?: string;
  species?: string;
  lineage?: string;
  ability_scores?: Record<string, number>;
  background_bonuses?: Record<string, number>;
  skill_choices?: string[];
  tool_choices?: string[];
  spells?: string[];
  cantrips?: string[];
  fighting_style?: string;
  maneuvers?: string[];
  equipment_selections?: Record<string, string>;
  languages_chosen?: string[];
  background_skill_replacement?: string[];
  species_skill_replacement?: string[];
  species_trait_choices?: Record<string, string>;
  species_feat_choices?: Record<string, string>;
  origin_feat?: string;
  [key: string]: unknown;
}
```

`POST /character/build` body: `{ "choices_made": ChoicesMade }`.

## Canonical Response — `Character`

The `to_character()` output. **Full field catalogue in [docs/APIContract.md](../../../docs/APIContract.md#canonical-response--character-shape)**, including `combat`, `abilities`, `skills`, `spells_by_level`, `spell_slots`, `spellcasting_stats`, `weapon_mastery_stats`, `eldritch_invocation_stats`, `effects`, flattened proficiencies, and the `choices_made` echo with `spell_selections` / `weapon_mastery_selections` / `eldritch_invocation_selections`.

## Rules for Changing the Contract

1. **Backward compatibility**: never silently rename a field. Add new, deprecate old, then remove.
2. **Calculations belong server-side.** New derived values → new field on `Character`, not a TS helper.
3. **Update in lockstep**:
   - `routes/api/<file>.py` (handler)
   - `modules/character_builder.py` if needed
   - `docs/APIContract.md`
   - `frontend/src/lib/api.ts` (types + client)
   - Tests in `tests/test_api_v1.py`
4. **No statefulness**: do not introduce server-side session state; the request must carry everything.
