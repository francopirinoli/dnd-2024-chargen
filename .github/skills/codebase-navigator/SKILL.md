---
name: codebase-navigator
description: "Reference skill. Map of the repository: where each layer lives, where to add new code, and which surfaces are quarantined. Use when you need to find or place a file."
---

# Codebase Navigator

## Top-Level Map

```
/                          # repo root
├── app.py                 # Flask entrypoint
├── conftest.py            # pytest fixtures
├── modules/               # Python — calculation core (single source of truth)
├── routes/                # Flask routes
│   ├── api/               # REST API v1 — ACTIVE surface
│   └── *.py               # Legacy Jinja routes — DEPRECATED, do not modify
├── templates/             # Legacy Jinja templates — DEPRECATED, do not modify
├── data/                  # Game content JSON (classes, species, spells, …)
├── models/                # JSON Schema definitions for data/
├── wiki_data/             # Cached D&D 2024 wiki content
├── frontend/              # React + Vite + TS SPA
├── tests/                 # Pytest suite (Python)
├── docs/                  # Living documentation
├── update_classes.py      # Wiki fetcher (classes)
├── update_species.py      # Wiki fetcher (species)
├── update_spells.py       # Wiki fetcher (spells)
└── validate_data.py       # JSON ↔ schema validator
```

## Calculation Core — `modules/`

| File                       | Responsibility                                                |
|----------------------------|---------------------------------------------------------------|
| `character_builder.py`     | **Single source of truth.** `_apply_effect`, `to_character`.  |
| `ability_scores.py`        | Ability score management                                      |
| `hp_calculator.py`         | HP per level                                                  |
| `feature_manager.py`       | Feature collection and effect parsing                         |
| `variant_manager.py`       | Species variants / lineages                                   |
| `equipment_manager.py`     | Equipment, weapons, armor                                     |
| `derived_stats.py`         | Stateless view helpers (skills, saves, attacks)               |
| `data_loader.py`           | JSON file loading & caching                                   |
| `level_manager.py`         | Level-up bookkeeping                                          |
| `character.py`             | Lightweight character object                                  |

## REST API — `routes/api/`

| Module           | Endpoints (under `/api/v1`)                                                |
|------------------|-----------------------------------------------------------------------------|
| `__init__.py`    | `GET /health`                                                              |
| `catalog.py`     | `GET /classes`, `/classes/<n>`, `/classes/<n>/subclasses[…]`, `/species[…]`, `/backgrounds[…]`, `/feats[…]`, `/spells/<class>`, `/spells/definitions/<spell>`, `/equipment/<kind>`, `/reference/<name>` |
| `wizard.py`      | `GET /wizard/steps`, `/wizard/dependencies`                                |
| `character.py`   | `POST /character/build`, `/character/validate`, `/character/preview-step`, `/character/derived` |

Every endpoint is **stateless** — request carries `choices_made`, response carries calculated character data. See `docs/APIContract.md`.

## Frontend — `frontend/src/`

```
app/         # Providers + route tree
pages/       # Route-level views
components/
  ui/        # shadcn/ui primitives
  layout/    # Shell, header, nav
  wizard/    # Wizard shell + navigation
  steps/     # Individual wizard step UIs
store/       # Zustand stores — UI state + raw choices ONLY
  characterStore.ts   # current character draft (raw choices)
  rosterStore.ts      # saved characters list (LocalStorage)
lib/
  api.ts     # Typed REST client — single HTTP boundary
  utils.ts   # cn() and tiny non-D&D helpers
styles/      # Tailwind entry + theme tokens
main.tsx     # Vite entry
```

See `.github/instructions/frontend-architecture.instructions.md` for boundary rules.

## Game Data — `data/`

| Path                         | Contents                                  |
|------------------------------|-------------------------------------------|
| `classes/`                   | One JSON per class                        |
| `subclasses/<class>/`        | Subclasses grouped by parent class        |
| `species/`                   | Species definitions                       |
| `species_variants/`          | Lineages / variant choices                |
| `backgrounds/`               | Backgrounds (ASIs, origin feat, skills)   |
| `spells/`                    | Class spell lists + per-spell definitions |
| `equipment/`                 | Weapons, armor, packs, gear               |
| `general_feats.json`         | General feats catalogue                   |
| `origin_feats.json`          | Origin feats catalogue                    |
| `fighting_styles.json`       | Fighting styles                           |
| `eldritch_invocations.json`  | Warlock invocations                       |
| `completeness/`              | Completeness audit reports                |
| `character_sheet_model.json` | Sheet/output model                        |
| `example_complete_character.json` | Reference output                     |

## Where to Put New Code

| Need                                          | Place it in                                         |
|-----------------------------------------------|-----------------------------------------------------|
| New class/subclass/species/feat               | `data/<area>/...json` (see `data-schemas` instr.)   |
| New effect type                               | `modules/character_builder.py` `_apply_effect`      |
| New API endpoint                              | New file or function under `routes/api/`            |
| New wizard step UI                            | `frontend/src/components/steps/`                    |
| New shadcn primitive                          | `frontend/src/components/ui/`                       |
| New Zustand state                             | `frontend/src/store/` (UI/raw-choice ONLY)          |
| New test                                      | `tests/test_<area>.py` (see `testing` instructions) |
| New cross-cutting doc                         | `docs/`                                             |

## Quarantined / Do Not Modify

- `routes/*.py` (everything except `routes/api/`)
- `templates/`
- `static/` Jinja-related assets

These are the deprecated Jinja UI; they will be removed in a cleanup pass. Do not extend them and do not use them as a behavioural reference — `CharacterBuilder` and the API contract are authoritative.
