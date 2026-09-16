# Architecture

The D&D 2024 Character Creator is a **two-tier application** with a hard boundary between presentation and calculation. The React SPA is a pure consumer of game data and computed character stats; the Flask backend is the single source of truth for every derived value.

## Top-Level Layout

```
┌────────────────────────────┐         HTTP/JSON          ┌─────────────────────────────┐
│  React SPA (frontend/)     │  ───  /api/v1/*  ───►      │  Flask API (routes/api/)    │
│  - Vite + TS               │                            │  Stateless, JSON only       │
│  - shadcn/ui + Tailwind    │  ◄── calculated character ─│                             │
│  - Zustand (UI state only) │                            │  ─► CharacterBuilder        │
│  - LocalStorage now,       │                            │     (modules/) — ALL        │
│    Postgres+auth later     │                            │     calculations live here  │
│  NO calculation logic      │                            │  ─► JSON data files (data/) │
└────────────────────────────┘                            └─────────────────────────────┘
```

## The Calculation Boundary

The boundary between TypeScript and Python is the **API contract**, defined in [docs/APIContract.md](APIContract.md).

| Side | Responsibility |
|------|----------------|
| React | Render game data; collect raw player choices; render calculated character returned by the API. |
| Flask | Load JSON data; apply choices through `CharacterBuilder`; return a fully-calculated `Character`. |

TypeScript never:
- computes an ability modifier;
- computes AC, HP, initiative, passive perception, proficiency bonus;
- computes spell save DC, spell attack, slot counts, prepared count;
- evaluates multiclass or feat prerequisites;
- ranks attacks or composes hit-dice display values;
- decides which features grant which proficiencies, languages, or spells.

If the UI needs to display any of those, it goes in Python and reaches the UI through the API.

## Request / Response Flow

The wizard is an interactive loop over three endpoint families:

```
                      ┌──────────────────────────────┐
                      │  Zustand: choicesMade        │
                      │  (raw player picks only)     │
                      └──────────┬───────────────────┘
                                 │ on every change
                                 ▼
        ┌──────────────────────────────────────────────────┐
        │  POST /api/v1/character/preview-step             │
        │   → nested choice options for the active step    │
        │  POST /api/v1/character/validate                 │
        │   → per-step completion status                   │
        │  POST /api/v1/character/build                    │
        │   → full Character (to_character() output)       │
        └──────────────────────────────────────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │  React renders the response   │
                  │  via @tanstack/react-query    │
                  └───────────────────────────────┘
```

Catalog lookups (`/api/v1/catalog/*`) and wizard metadata (`/api/v1/wizard/*`) are cached aggressively by react-query because they only change when data files or wizard config change.

## The Calculation Core — `CharacterBuilder`

`modules/character_builder.py` is the **single source of truth**. Surrounding helpers split the work:

| Module | Role |
|--------|------|
| `character_builder.py` | Applies `choices_made`, runs effects, produces `to_character()`. |
| `ability_scores.py` | Ability score arithmetic and ASI bookkeeping. |
| `hp_calculator.py` | HP-by-level rules and bonus HP from effects. |
| `equipment_manager.py` | Weapon/armor selection, AC options. |
| `feature_manager.py` | Feature collection from class/subclass/species/background/feats. |
| `variant_manager.py` | Lineage / species variant handling. |
| `derived_stats.py` | View-models for derived endpoints (damage cantrips, spell management, mastery, invocations). |
| `data_loader.py` | JSON loading and lookup helpers for `data/`. |

`to_character()` is the canonical export. JSON export, the React sheet, the printable PDF view and any future surface (Discord bot, mobile shell) consume the same dict. See [docs/APIContract.md](APIContract.md#character-shape) for the field-level shape and [docs/character_builder_guide.md](character_builder_guide.md) for the internal walkthrough.

### `apply_choices()` Pass Ordering

`CharacterBuilder.apply_choices()` processes the `choices_made` dict in six ordered stages so that each stage can rely on the state established by the previous one:

1. **Pass 1 — ordered dependency keys.** A static `order` list defines the canonical processing sequence: `character_name` → `name` → `level` → `species` → `lineage` → `lineage_spellcasting_ability` → `class` → `subclass` → `skill_choices` / `skills` → `background` → `background_skill_replacements` → ability-score keys (`ability_scores_method`, `ability_scores`, `abilities`, `background_ability_score_assignment`, `background_bonuses_method`, `background_bonuses`, `additional_ability_modifiers`) → `tool_choices` / `tools` → `spellcasting` → `spell_selections` → `weapon mastery` / `weapon_mastery_selections` → `eldritch_invocation_selections` → `alignment`. Keys absent from `choices_made` are skipped silently. If both `ability_scores_method` and `ability_scores` (or `abilities`) are present, the method key is preserved for UI round-tripping but its score-assignment side-effect is suppressed.
2. **Normalize — species trait choices.** After species (and optionally lineage) are loaded, any legacy flat species-trait keys are lifted into the nested `species_trait_choices` object by `_normalize_species_trait_choices()`. This must run before Pass 2 so the trait-choice dispatcher sees a consistent key shape.
3. **Pass 2 — remaining keys.** All keys not in the ordered list and not in `{"species_skill_replacements", "classes"}` are applied. Within this pass, parent feat-slot keys (`class_feat_N`) are sorted before their sub-keys (`class_feat_N_*`) so sub-choice handlers can look up their parent.
4. **Multiclass block.** If a `classes` array is present, each row beyond the first is applied as a secondary class track via `_apply_additional_multiclass_tracks()`. Total level and proficiency bonus are recalculated from the sum of all row levels.
5. **Pass 3 — `species_skill_replacements`.** Runs after all trait effects have been applied so that overlap detection (a species trying to grant a skill the character already has from class or background) sees the full proficiency picture.
6. **Finalize.** `_apply_pending_dynamic_effects()` resolves deferred dynamic effects (e.g. `damage_type_from_choice` resolutions that need `choices_made` fully populated). A final `_normalize_species_trait_choices()` canonicalizes any stray flat keys written as side-effects of Pass 2 dispatch. Strict-mode validation (`strict_mode.check_choices_made_keys()`) runs last.

### Rebuild-Equality Invariant

Given the same `choices_made` dict, `CharacterBuilder.to_character()` must always produce byte-equal output (after stripping volatile fields such as timestamps). This determinism guarantee is essential for export/import round-trips, character versioning, and diffing. The mechanical enforcement is `tests/integration/test_rebuild_equality.py`: the test serialises a reference build, reconstructs the character from the echoed `choices_made`, and asserts the two serialised dicts are identical. Any non-determinism in pass ordering or effect application will surface as a failure there.

## Data Layer

All game content lives as JSON under `data/` and is validated against schemas in `models/`. Adding a class, subclass, species, background, feat, or spell means **editing JSON, not code**. See [docs/DataFiles.md](DataFiles.md).

Mechanical benefits are expressed as structured `effects` arrays applied generically by `CharacterBuilder._apply_effect()`. Application code never branches on `feature_name == "..."`. See [docs/FEATURE_EFFECTS.md](FEATURE_EFFECTS.md).

## Persistence

Today everything player-facing is **client-side only**:

| Concern | Storage | Key | Owner |
|---------|---------|-----|-------|
| Saved character roster | `localStorage` | `dnd-character-roster` | `frontend/src/lib/persistence.ts` (`LocalStoragePersistence`) |
| In-progress wizard draft | `localStorage` (Zustand `persist`) | `dnd-creator-character-v1` | `frontend/src/store/characterStore.ts` |

Both are deliberately funnelled through narrow interfaces:

- `Persistence` (interface in `frontend/src/lib/persistence.ts`) abstracts roster CRUD. The concrete `LocalStoragePersistence` is swappable via `setPersistence()`.
- The Zustand store uses Zustand's `persist` middleware with a `version` field and `migrate` shim, so the same blob can later sync to a server.

The planned next step is a **Flask + PostgreSQL** persistence service behind the same `Persistence` interface, with user accounts and authentication. The SPA boundary does not change: roster sync becomes a different `Persistence` implementation; in-progress drafts continue to live in the Zustand store but mirror to the server. The API contract for character calculation is untouched.

## UI Surface

The product surface is now React SPA + `/api/v1` only. Documentation and implementation guidance assume the SPA consumes stateless JSON endpoints backed by `CharacterBuilder`.

## See Also

- [docs/Stack.md](Stack.md) — tech choices per layer
- [docs/APIContract.md](APIContract.md) — endpoint catalogue and shapes
- [docs/WizardFlow.md](WizardFlow.md) — wizard step structure and cascades
- [docs/DataFiles.md](DataFiles.md) — `data/` layout and generation pipeline
- [docs/DesignSystem.md](DesignSystem.md) — tokens, typography, conventions
- [docs/FEATURE_EFFECTS.md](FEATURE_EFFECTS.md) — effect catalogue
- [docs/character_builder_guide.md](character_builder_guide.md) — internal walkthrough
