# Copilot Instructions for D&D 2024 Character Creator

## Architecture in One Picture

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

**Hard boundary**: the React SPA sends raw player choices and renders calculated results.
The Python `CharacterBuilder` is the **single source of truth** for every derived stat.
TypeScript never computes a modifier, AC, slot count, save DC, or proficiency bonus.

## Core Principles

### 1. Single Source of Truth — `CharacterBuilder`
`modules/character_builder.py` is the ONLY place where character calculations happen.
- `/api/v1/character/build` calls `builder.to_character()` and returns the resulting dict.
- The React SPA is a pure consumer of that dict.
- JSON export, PDF sheet, and any future surface (Discord bot, mobile, etc.) use the same dict.
- If a calculation is needed in the UI, it goes in Python and is exposed through the API.

### 2. Effects System — NEVER Hardcode
**NEVER hardcode specific feature, species, class, or feat names in application logic.**
All mechanical benefits are structured `effects` arrays in JSON data files, applied generically through `CharacterBuilder._apply_effect()`. Branch on `effect['type']`, never on `feature_name == '...'`.
See `.github/instructions/effects-system.instructions.md` and `docs/FEATURE_EFFECTS.md`.

### 3. D&D 2024 Edition Compliance
- Verify rules come from D&D 2024 (One D&D), not 2014.
- Species no longer have ability score increases (moved to backgrounds).
- Dwarf variants (Hill/Mountain) don't exist in 2024.
- When in doubt, check `wiki_data/` cache or fetch from http://dnd2024.wikidot.com/.

### 4. Data-Driven Design
**NEVER hardcode lists of game content.** Check against data files instead.
- Weapon detection checks `data/equipment/weapons.json`, not keyword lists.
- All game content (classes, species, spells, feats, backgrounds) lives in `data/` as JSON.
- Adding content means updating data files, not code.

### 5. Schema Compliance
All data files MUST comply with schemas in `models/`.
- `features_by_level` maps level (string) → **OBJECT** of feature_name → description.
- ❌ NEVER arrays: `"1": ["Feature1"]` — ✅ ALWAYS objects: `"1": {"Feature1": "Description"}`.
See `.github/instructions/data-schemas.instructions.md`.

### 6. Frontend ≠ Calculation Surface
- React components, hooks, and Zustand stores must not derive D&D stats.
- Zustand holds **UI state and the player's raw choices only** — never derived values.
- Anything beyond trivial display formatting belongs in `CharacterBuilder` and reaches the UI through the API.
- See `.github/instructions/frontend-architecture.instructions.md`.

## Tech Stack

| Layer        | Choice                                                           |
|--------------|------------------------------------------------------------------|
| Frontend     | Vite + React 18 + TypeScript                                     |
| UI kit       | shadcn/ui (Radix primitives) + Tailwind CSS + lucide-react       |
| State (UI)   | Zustand 5 (raw choices + UI flags only)                          |
| Data fetch   | @tanstack/react-query → typed client in `frontend/src/lib/api.ts`|
| Routing      | react-router-dom v6                                              |
| PWA          | vite-plugin-pwa                                                  |
| Persistence  | LocalStorage now → Flask + PostgreSQL + auth later               |
| Backend      | Flask (calculation + persistence API only)                       |
| Calculations | Python `CharacterBuilder` + effects system (authoritative)       |
| Data         | JSON files in `data/`, validated against `models/` schemas       |
| CI/Tracking  | GitHub Issues + PRs                                              |

See `docs/Stack.md` for rationale.

## Repository Layout

```
modules/                       # Python — all calculation logic
  character_builder.py         #   single source of truth
  ability_scores.py / hp_calculator.py / equipment_manager.py
  feature_manager.py / variant_manager.py / derived_stats.py
  data_loader.py

routes/api/                    # REST API v1 (/api/v1/*) — stateless JSON
routes/                        # DEPRECATED legacy Jinja routes — DO NOT MODIFY
templates/                     # DEPRECATED legacy templates — DO NOT MODIFY

frontend/                      # React + Vite + TS SPA (the UI)
  src/lib/api.ts               #   typed client for /api/v1
  src/store/                   #   Zustand stores — UI state + raw choices ONLY
  src/components/              #   shadcn/ui components and primitives
  src/pages/ src/app/          #   route-level views
  src/styles/                  #   Tailwind + design tokens

data/                          # Game content JSON
models/                        # JSON Schema definitions
wiki_data/                     # Cached D&D 2024 wiki source material

docs/                          # Living documentation (see list below)
.github/                       # Agents, skills, instructions, workflows
```

## Legacy Surface — Quarantined

The Jinja UI under `routes/` (non-`api/`) and `templates/` is **deprecated**.
- Do not modify it.
- Do not extend it.
- Do not use it as a reference for new behaviour — `CharacterBuilder` and the API contract are authoritative.
- It will be deleted in a future cleanup pass.

## Documentation

Living docs in `docs/`:
- `Architecture.md` — React/Flask split, API contract boundary
- `Stack.md` — tech choices and rationale
- `DesignSystem.md` — D&D Beyond–inspired tokens, typography, shadcn customisations
- `WizardFlow.md` — wizard step structure, nesting rules, choice cascades
- `APIContract.md` — Flask endpoints, request/response shapes
- `DataFiles.md` — data file locations, generation process, Python fetch tooling
- `FEATURE_EFFECTS.md` — full effect catalog (existing, authoritative)
- `character_builder_guide.md` — internal `CharacterBuilder` walkthrough

## Scoped Instructions

Loaded automatically when their `applyTo` matches:
- `instructions/effects-system.instructions.md` — Effect types, JSON shapes, rules
- `instructions/data-schemas.instructions.md` — Class, subclass, species, background schemas
- `instructions/choice-reference.instructions.md` — Choice Reference System
- `instructions/character-builder-api.instructions.md` — `to_character()` output shape
- `instructions/testing.instructions.md` — Pytest conventions
- `instructions/flask-routes.instructions.md` — REST API v1 patterns
- `instructions/frontend-architecture.instructions.md` — React/shadcn/Zustand rules

## Agent System

The agent system is **role-based with a single gatekeeper**. The **Architect Agent** plans and routes all non-trivial work; specialised agents execute within their lane.

| Agent              | Model   | Lane                                                                  |
|--------------------|---------|-----------------------------------------------------------------------|
| `architect`        | Opus    | Gatekeeper. Planning, impact analysis, phasing, codebase reasoning.   |
| `frontend`         | Sonnet  | `frontend/**` only. React, shadcn, Tailwind, Zustand, responsive UI.  |
| `backend`          | Sonnet  | Flask API, `CharacterBuilder`, effects, `data/`, `wiki_data/` tooling.|
| `data-completeness`| Opus    | Audits `data/` for schema, effects coverage, D&D 2024 accuracy.       |
| `test`             | Sonnet  | Pytest (and future frontend tests). Owns `tests/`.                    |
| `docs`             | Sonnet  | Owns `docs/`. Keeps documentation current after changes.              |
| `issue-tracker`    | Sonnet  | GitHub Issues / PRs via the GitHub MCP tools.                         |

Routing rules:
- Any **multi-file or cross-layer change** must be planned by `architect` first.
- `architect` invokes the specialist agents (and read-only `Explore`) as subagents.
- Agents stay in their lane: `frontend` never edits Python; `backend` never edits `frontend/`.
- Bug reports and feature requests are **fixed locally by default** — plan and delegate directly.
- Only route to `issue-tracker` when the user explicitly says `File Issue: <description>`.
- Fixing a known issue uses the `fix-issue` skill, orchestrated by `architect`.

Model assignment is declared in each agent file's YAML frontmatter (`model:` field) and mirrored in this table.

## Shared Skills (reference)

Knowledge lookups any agent can pull in:
- `dnd-rules-reference` — D&D 2024 rules summary and where to find source material.
- `codebase-navigator` — directory map and "where does X live".
- `design-system-reference` — Tailwind tokens, typography, shadcn customisations.
- `api-contract-reference` — `/api/v1/*` endpoints, request/response shapes.
- `dependency-map` — module/file dependency cheatsheet across layers.

## Workflow Skills (procedures)

Multi-step procedures any agent can run:
- `add-game-content` — batch-add subclasses, backgrounds, feats, spells.
- `implement-feature` — end-to-end implementation of any feature (class, subclass, species, lineage, background, feat, weapon mastery, fighting style, eldritch invocation, spell).
- `validate-character` — rebuild a character and verify all calculated values.
- `file-issue` — turn a casual bug report into a structured GitHub Issue.
- `fix-issue` — full workflow for resolving a known GitHub Issue.

## Data Sources Priority

1. `data/` — application-ready structured JSON (primary)
2. `wiki_data/` — cached wiki content with `content.text` and `content.html` fields
3. http://dnd2024.wikidot.com/ — live wiki (only when cache is missing)

Use `update_classes.py --class <name>`, `update_species.py --species <name>`, or `update_spells.py --class <name>` to fetch/cache wiki data.

## Development Checklist

When implementing any feature:
1. Verify it exists in D&D 2024 (not 2014).
2. Define effects in JSON data files (never hardcode).
3. Implement a generic handler if a new effect type is needed.
4. Validate data against schema (`python validate_data.py`).
5. Write tests (`pytest tests/`).
6. If the change crosses the React/Flask boundary, update `docs/APIContract.md`.

## Issue Tracking

Known bugs and missing features are tracked as GitHub Issues on `QuickNS/dnd-character-creator`.
Issue titles follow `[Category] Short description` (e.g., `[Monk]`, `[Elf]`, `[Monk/Warrior of Shadow]`) with `bug` or `enhancement` labels.
Use GitHub MCP tools (`mcp_github_list_issues`, `mcp_github_search_issues`) to find open issues.
The `issue-tracker` agent and the `file-issue` / `fix-issue` skills wrap this workflow.