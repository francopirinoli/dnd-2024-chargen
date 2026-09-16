# Wizard Flow

The character-creation wizard is **data-driven**: step ordering, required keys and cascade rules come from `/api/v1/wizard/*`, and the choice surface for every step is computed by `/api/v1/character/preview-step`. Adding a class, species, feat or spell in `data/` automatically surfaces in the wizard with no frontend change.

## Steps

The canonical step list is served by `GET /api/v1/wizard/steps` (source: [routes/api/wizard.py](../routes/api/wizard.py)).

| # | `id`         | Label           | Required keys                | Nested choices (conditional)                                                  |
|---|--------------|-----------------|------------------------------|-------------------------------------------------------------------------------|
| 1 | `class`      | Class           | `character_name`, `class`    | `subclass`, `fighting_style`, `maneuvers`, `spells`, `cantrips`               |
| 2 | `background` | Background      | `background`                 | `background_skill_replacement`, `origin_feat`                                 |
| 3 | `species`    | Species         | `species`                    | `lineage`, `species_trait_choices`, `species_feat_choices`, `species_skill_replacement` |
| 4 | `languages`  | Languages       | —                            | —                                                                             |
| 5 | `abilities`  | Ability Scores  | `ability_scores`             | `background_bonuses`                                                          |
| 6 | `equipment`  | Equipment       | —                            | —                                                                             |
| 7 | `complete`   | Summary         | —                            | —                                                                             |

The breadcrumb in the SPA renders one entry per step in this order. The current step is held in the Zustand store as `currentStepId`.

The wizard now starts at Class. The old Basics step is no longer in the active flow. Character name is captured globally in the sidebar and validated as part of class-step completeness, rather than through a dedicated step.

The Class step accepts per-class allocations via `choices_made.classes` rows (`class_name`, `level`, optional `subclass`). Multiple rows are accepted and built: total character level is the sum of row levels, and additional rows apply their class/subclass features.

Class-step row interaction is active-row driven in the SPA:
- The user can mark any class row as active.
- Class details, subclass picker, and class advanced-choice sections target the active row.
- Subclass validation remains per row at build/validate time (`classes[i].subclass` when that row qualifies).
- Multiclass standard spell slots now use effective caster level aggregation (full = 1x level, half = ceil(level / 2), third = floor(level / 3), non-caster = 0) and the canonical full-caster slot table.
- Pact Magic slots are tracked separately from standard slots in this phase (not merged).
- Single-class spellcasting behavior remains compatible.

### Multiclass class step UX

The class step adapts its rendering and validation to the active row's `row_context` (see [APIContract.md](APIContract.md#step-class--row-context-and-multiclass-filtering)). The `is_primary` flag returned by `/api/v1/character/preview-step` drives the following frontend behaviour:

- **Core Traits vs Multiclass Traits panel.** The class info panel renders above the feature progression and switches on `row_context.is_primary`:
  - **Primary row (`is_primary: true`)** — a **Core Traits** block lists the full level-1 grants (HP die, primary ability, saving throws, armour / weapon / tool proficiencies, full skill list, starting equipment) from the class's top-level fields.
  - **Secondary row (`is_primary: false`)** — a **Multiclass Traits** block sourced from the class's `multiclassing` JSON block lists only what multiclass entry actually grants (armour / weapon / tool training, the narrowed skill picker, and the note that saves are never granted).
- **Multiclass prerequisite gating on the class picker.** On secondary rows, every candidate class is checked against D&D 2024 multiclassing prerequisites — every class in the build (the candidate plus all already-selected classes) must have ≥13 in its primary ability. Candidates that fail get a `disabled` `<option>` with an inline reason (e.g. "Requires STR 13 (Fighter) and CHA 13 (Bard)"). The primary class row is never gated.
- **Advisory state when ability scores are unset.** If `choices_made.ability_scores` has not been entered yet, the prerequisite check is skipped: all classes remain selectable and an advisory notice renders beside the picker ("Set ability scores to confirm multiclass eligibility"). The build endpoint enforces the rule at submission time regardless.
- **Per-row pending indicator.** Each class row in the list shows an amber dot when that row has unresolved choices. A row is "pending" when:
  - `row_context.is_primary == true` (or there is only one row) and any of the row's required `nested_choices` are unsatisfied; or
  - `needs_subclass == true` for the row and `classes[i].subclass` is empty; or
  - `is_primary == false` and the filtered secondary-row `nested_choices` (core-trait skill / tool picks narrowed by multiclass rules, plus preserved class-feature choices at all unlocked levels) are unsatisfied.

> **Known limitation — shared choice keys across rows.** Player choices like `skill_choices` and `tool_choices` are stored under a single key in `choices_made`, not partitioned per class row. In multi-row builds where both the primary row and a secondary row prompt for skill picks, the two pickers currently write to the same storage slot and can overwrite each other. Per-row choice partitioning (e.g. `skill_choices_by_row`) is tracked as a future improvement.


## Nesting Rules

- A step's "required keys" are the unconditional ones — they must be present in `choices_made` for the step to validate.
- Nested choices are surfaced **only when the prerequisite is met**. Examples:
  - `subclass` only when `level >= class.subclass_selection_level` (default 3).
  - `fighting_style` / `maneuvers` only when the class grants them.
  - `lineage` only when the chosen species has lineages.
  - `species_trait_choices` only when traits expose `type: "choice"`.
  - `background_skill_replacement` only when the background's granted skills overlap with class skills.
  - `origin_feat` always (every background grants one in 2024).
  - `background_bonuses` only when the background offers ASI options.
- The `preview-step` endpoint computes these on the fly from current `choices_made` and returns the structured options the UI should render.
- The `validate` endpoint checks the same conditions and returns `missing` keys per step.

## Choice Dependencies (Cascade Behaviour)

Source: `_DEPENDENCIES` in `routes/api/wizard.py`, served by `GET /api/v1/wizard/dependencies`. When a key on the left changes, all keys on the right are **deleted from `choices_made`** before the rebuild request — preventing stale subclass / spell / feat picks from surviving an upstream change.

| Changed key  | Invalidates                                                                                     |
|--------------|-------------------------------------------------------------------------------------------------|
| `classes`    | `subclass`, `fighting_style`, `maneuvers`, `spells`, `cantrips`, `class_features`, `skill_choices`, `tool_choices`, `background_skill_replacement`, `equipment_selections` |
| `level`      | `subclass`, `spells`, `cantrips`, `fighting_style`, `maneuvers`, `class_features`               |
| `class`      | `subclass`, `fighting_style`, `maneuvers`, `spells`, `cantrips`, `class_features`, `skill_choices`, `tool_choices`, `background_skill_replacement`, `equipment_selections` |
| `subclass`   | `subclass_features`, `spells`, `cantrips`                                                       |
| `background` | `background_bonuses`, `background_skill_replacement`, `origin_feat`, `feat_choices`, `equipment_selections` |
| `species`    | `lineage`, `species_trait_choices`, `species_feat_choices`, `species_skill_replacement`, `languages` |
| `lineage`    | `lineage_features`, `lineage_spells`, `languages`                                               |

The cascade is implemented in `frontend/src/store/characterStore.ts` (`cascade()`). Setting a key always re-asserts that key after pruning dependents, in case of accidental self-reference. Changing `class` additionally wipes any positional `class_choice_*` compatibility keys.

## Frontend Layout

```
WizardLayout (frontend/src/components/layout/WizardLayout.tsx)
├── <aside>  StepSidebar (steps + Start over + ThemeToggle)
└── <main>   <Outlet>
              └── StepRenderer (frontend/src/components/wizard/StepRenderer.tsx)
                  ├── <article>
                  │     header (step number, label, description)
                  │     section → renderStepBody(step)
                  │       ├── ClassStep / SpeciesStep / …
                  │       └── GenericStep (fallback, data-driven)
                  │     StepNav (Prev / Next)
                  └── <aside>  class portrait  (placeholder for EffectsPanel)
```

Per-step components in `frontend/src/components/steps/` own the rendering of choice options returned by `preview-step`. The `GenericStep` fallback exists so a brand-new step added to `_STEPS` will render a usable form even before a bespoke component is written.

## Persistence Keys

| Concern                  | Storage        | Key                          | Owner                                          |
|--------------------------|----------------|------------------------------|------------------------------------------------|
| In-progress wizard draft | `localStorage` | `dnd-creator-character-v1`   | Zustand `persist` in `characterStore.ts` (`version: 2`, `migrate` shim) |
| Saved character roster   | `localStorage` | `dnd-character-roster`       | `LocalStoragePersistence` in `lib/persistence.ts` |

The Zustand `partialize` config persists `choicesMade` and `currentStepId` only; the dependency map and other transient state are not written to disk.

## "Start Over"

`WizardLayout.handleStartOver`:
1. Confirms with the user.
2. Calls `useCharacterStore.reset()`.
3. Removes `["character"]` and `["wizard"]` query caches from react-query so the new run does not render stale build/preview data.
4. Navigates to the first step.

## Open Follow-Ups

- **`EffectsPanel` is wired up but intentionally hidden.** `frontend/src/components/wizard/EffectsPanel.tsx` posts the current `choices_made` to `/api/v1/character/build` and renders the headline calculated values (HP, AC, speed, initiative, prof bonus, ability modifiers). `StepRenderer` notes the placeholder explicitly: the right `<aside>` currently shows a class portrait, with a comment indicating how to restore the live preview. Re-enabling the panel is a UI polish task — verify performance with the rapid `choicesMade`-keyed query and confirm the placeholder no longer carries design value before swapping it in.

## See Also

- [docs/APIContract.md](APIContract.md)
- [docs/Architecture.md](Architecture.md)
- [docs/DesignSystem.md](DesignSystem.md)
