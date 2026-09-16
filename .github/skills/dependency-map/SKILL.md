---
name: dependency-map
description: "Reference skill. Cheatsheet of how layers depend on each other across the stack. Use when planning a change to gauge blast radius."
---

# Dependency Map

Read direction: **A → B** means "A depends on B; changes to B may break A."

## Top-Level Flow

```
frontend/src/components ──► frontend/src/store ──► frontend/src/lib/api.ts
                                                          │
                                                          ▼  HTTP /api/v1/*
                                                  routes/api/*.py
                                                          │
                                                          ▼
                                                  modules/character_builder.py
                                                          │
                                          ┌───────────────┼─────────────────┐
                                          ▼               ▼                 ▼
                              modules/feature_manager  modules/...      data/*.json
                                          │
                                          ▼
                              effects system (data-driven)
```

## Backend Internals (`modules/`)

```
character_builder.py
  ├─► ability_scores.py
  ├─► hp_calculator.py
  ├─► equipment_manager.py
  ├─► feature_manager.py ──► (parses `effects` arrays from data/*.json)
  ├─► variant_manager.py
  ├─► derived_stats.py     (stateless view helpers, also used by API directly)
  ├─► level_manager.py
  └─► data_loader.py       ──► data/*.json
```

`character_builder.py` is the only module that orchestrates effect application. Other modules are leaves and should not import it.

## API → Builder

```
routes/api/character.py   ──► modules.character_builder.CharacterBuilder
routes/api/catalog.py     ──► modules.data_loader
routes/api/wizard.py      ──► (wizard step config; ideally driven from data + builder choice metadata)
```

API handlers must remain thin: parse JSON → call builder/loader → serialize response.

## Frontend Internals (`frontend/src/`)

```
components/steps/*       ──► store/characterStore   (write raw choices)
components/wizard/*      ──► lib/api.ts             (read /wizard/steps)
pages/* (sheet, preview) ──► lib/api.ts             (read /character/build via react-query)
store/rosterStore        ──► localStorage           (now) → lib/api.ts (future)
components/ui/*          ──► (Radix + tailwindcss-animate)
all components           ──► lib/utils.ts (cn)
```

The **only HTTP boundary** is `lib/api.ts`. Nothing else may call `fetch`.

## Data → Schema → Validator

```
data/**/*.json ──► validated by ──► models/*.json (JSON Schema)
                                        ▲
                                        │
                              validate_data.py (CI / manual)
```

Adding new data fields requires updating both the data file and the matching schema in `models/`.

## Wiki Pipeline

```
http://dnd2024.wikidot.com/  ──► update_classes.py / update_species.py / update_spells.py
                                            │
                                            ▼
                                       wiki_data/*.json
                                            │
                                            ▼ (manual authoring)
                                       data/**/*.json
```

`update_*.py` never writes to `data/`. JSON authoring is a separate, human-reviewed step.

## Tests

```
tests/test_api_v1.py        ──► routes/api/* + modules/character_builder
tests/test_<feature>.py     ──► modules/character_builder + data/
conftest.py                 ──► shared fixtures (sample characters, builders)
```

A change to `_apply_effect` or `to_character` typically requires updates to `tests/test_api_v1.py` and feature-specific tests.

## Blast-Radius Heuristics

| Change                                      | Likely also touched                                                    |
|---------------------------------------------|-------------------------------------------------------------------------|
| Add new effect type                         | `character_builder.py`, `docs/FEATURE_EFFECTS.md`, relevant data file, tests |
| Add field to `to_character()` output        | `docs/APIContract.md`, `frontend/src/lib/api.ts`, components consuming the field, `tests/test_api_v1.py` |
| Add new API endpoint                        | `routes/api/<file>.py`, `docs/APIContract.md`, `lib/api.ts`, react-query hook, tests |
| Add new data file                           | matching schema in `models/`, `validate_data.py` run, possibly catalog endpoint |
| Add new wizard step                         | `routes/api/wizard.py`, `components/steps/`, `characterStore` shape, `docs/WizardFlow.md` |
| Change Tailwind tokens                      | `tailwind.config.ts`, `styles/theme.css`, visual regression of all pages, `docs/DesignSystem.md` |
| Rename a `ChoicesMade` key                  | `lib/api.ts`, every step component, builder choice processing, tests, docs — **avoid; deprecate instead** |

## Forbidden Edges

- `frontend/**` → any Python file: never. Cross via HTTP only.
- `modules/**` → `routes/**`: never. Modules must not know about the web layer.
- `routes/api/**` → `routes/` (legacy): never. Legacy is quarantined.
- `components/**` → raw `fetch`: always go through `lib/api.ts`.
- TS code → hardcoded D&D constants: always fetch from the catalog API or receive from `/character/build`.
