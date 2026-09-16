# HVE — Highly Valuable Experience

This document is the **operating manual** for the GitHub Copilot customization system in the D&D 2024 Character Creator. It describes every artifact under `.github/`, how the pieces fit together, and — most importantly — **how to use the system day to day**.

If you only read one section, read [How to Use This System](#how-to-use-this-system).

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Repository Layout (`.github/`)](#repository-layout-github)
3. [How to Use This System](#how-to-use-this-system)
4. [Agents](#agents)
5. [Skills](#skills)
6. [Instructions](#instructions)
7. [Prompts](#prompts)
8. [Hooks](#hooks)
9. [Setup Steps](#setup-steps)
10. [Interaction Map](#interaction-map)
11. [Common Tasks — Recipes](#common-tasks--recipes)

---

## System Overview

The Copilot configuration is built around three ideas:

1. **A single gatekeeper.** The **Architect Agent** (Opus) plans and routes any non-trivial change. Specialist agents stay in their lane.
2. **Hard architectural boundaries.** React SPA captures choices and renders results; Python `CharacterBuilder` is the single source of truth for every calculation. The frontend never derives D&D stats.
3. **Data-driven content.** Mechanical effects live in JSON `effects` arrays, applied generically by `_apply_effect`. No hardcoded class/species/feature names anywhere in code.

Everything in `.github/` exists to enforce those three ideas while keeping AI-assisted work fast.

```
┌──────────────┐  request  ┌──────────────┐  delegate  ┌─────────────────┐
│     User     ├──────────►│  Architect   ├───────────►│  Specialist(s)  │
└──────────────┘           │  (gatekeeper)│            │  frontend /     │
                           │              │            │  backend /      │
                           │  plans only  │            │  test / docs /  │
                           │              │            │  data-complete  │
                           └──────┬───────┘            │  / issue-tracker│
                                  │                    └─────────────────┘
                              instructions
                              + skills
                              + reference docs
                              loaded automatically
                              by topic / file path
```

Tier-2 stack reminder (also in `copilot-instructions.md`): React 18 + Vite + TS + shadcn/ui + Tailwind + Zustand 5 (UI state only) + react-query + react-router + vite-plugin-pwa over a stateless Flask `/api/v1/*` API backed by `CharacterBuilder` and JSON `data/`. Persistence is LocalStorage today and Flask + Postgres + auth in the future.

---

## Repository Layout (`.github/`)

```
.github/
├── copilot-instructions.md          # Always-loaded global rules
├── copilot-setup-steps.yml          # Cloud coding-agent bootstrap
├── dependabot.yml                   # Dependency PRs (stock)
├── workflows/
│   └── copilot-autofix.yml          # Auto-assign Copilot to issues with the "copilot" label
├── hooks/
│   ├── post-edit-data.json          # Auto-run validate_data.py after data edits
│   └── post-edit-python.json        # Auto-run pytest after Python edits
├── agents/                          # 7 role-based agents
│   ├── architect.agent.md           #   Opus    — gatekeeper / planner
│   ├── frontend.agent.md            #   Sonnet  — React SPA only
│   ├── backend.agent.md             #   Sonnet  — Python + data + wiki tooling
│   ├── data-completeness.agent.md   #   Opus    — data/ auditor
│   ├── test.agent.md                #   Sonnet  — owns tests/
│   ├── docs.agent.md                #   Sonnet  — owns docs/
│   └── issue-tracker.agent.md       #   Sonnet  — GitHub issues / PRs
├── instructions/                    # applyTo-scoped rules; auto-loaded by file path
│   ├── character-builder-api.instructions.md
│   ├── choice-reference.instructions.md
│   ├── data-schemas.instructions.md          # applyTo: data/**/*.json
│   ├── effects-system.instructions.md
│   ├── flask-routes.instructions.md          # applyTo: routes/**/*.py
│   ├── frontend-architecture.instructions.md # applyTo: frontend/**
│   └── testing.instructions.md               # applyTo: tests/**/*.py
├── skills/                          # Reusable knowledge + procedures
│   ├── api-contract-reference/      #   reference
│   ├── codebase-navigator/          #   reference
│   ├── dependency-map/              #   reference
│   ├── design-system-reference/     #   reference
│   ├── dnd-rules-reference/         #   reference
│   ├── add-game-content/            #   workflow
│   ├── implement-feature/           #   workflow (any entity, not just classes)
│   ├── validate-character/          #   workflow
│   ├── file-issue/                  #   workflow
│   └── fix-issue/                   #   workflow
└── prompts/
    ├── add-data-files.prompt.md     # → backend agent
    └── check-data-files.prompt.md   # → data-completeness agent
```

---

## How to Use This System

You almost never invoke a specific file directly. Instead, you state the goal and the gatekeeper routes it. Three tracks cover ~all daily work:

### Track A — "I want to do something" (work)

1. **Tell the user-facing chat what you want**, in a sentence (e.g. *"add the Bladesinger subclass"*, *"make the wizard preview update after subclass changes"*, *"audit the backgrounds folder"*).
2. The conversation will route to the **Architect Agent** for anything multi-file or cross-layer. Architect will:
   - Read the relevant code via the read-only `Explore` subagent.
   - Produce a numbered plan with files, owning specialist per phase, and tests.
   - **Stop and wait for your approval.**
3. Approve. Architect dispatches each phase to the appropriate specialist (`frontend`, `backend`, `test`, `docs`).
4. After each phase the specialist reports files changed and validation results. Architect summarises and moves on.

For a single-file edit clearly inside one lane (e.g. *"fix this typo in `frontend/src/pages/Home.tsx`"*), the lane's specialist agent can be addressed directly without going through Architect.

### Track B — "I found a bug / I want to track an idea" (issues)

1. Describe the bug or feature in chat (e.g. *"Stunning Strike DC seems wrong"*).
2. The **`issue-tracker` agent** (or the `file-issue` skill) will:
   - Search for duplicates.
   - Gather code context (file paths, line numbers).
   - File a structured GitHub Issue with the right labels and `[Category]` title prefix.
3. Later, to fix it: *"fix issue #42"* → the **`fix-issue` skill** handles it (read issue → branch → fix via Architect → test → PR).

### Track C — "I just want to know something" (read-only)

For "where does X live", "what's the API shape", "what tokens are in the design system":

- The reference skills (`codebase-navigator`, `api-contract-reference`, `dependency-map`, `design-system-reference`, `dnd-rules-reference`) auto-surface in context.
- For deeper exploration, the **`Explore` subagent** can be invoked by any agent to do parallel reads without polluting the main thread.
- The authoritative documents live under `docs/` (`Architecture.md`, `Stack.md`, `DesignSystem.md`, `WizardFlow.md`, `APIContract.md`, `DataFiles.md`, `FEATURE_EFFECTS.md`, `character_builder_guide.md`). The reference skills are abridged pointers to those.

### Rules of Engagement

- **Never ask the AI to invent rules.** D&D content always traces back to `wiki_data/` or http://dnd2024.wikidot.com/.
- **Never accept a calculation in TypeScript.** If the UI needs a number, the backend computes it and exposes it via `/api/v1/*`.
- **Always validate.** Hooks fire `validate_data.py` and `pytest` automatically after edits — read their output.
- **Cross-layer work goes through Architect.** Avoid tasking specialists with anything that crosses the React/Flask boundary directly.

---

## Agents

Each agent carries a `model` in its YAML frontmatter and a strict lane. The full table mirrors `copilot-instructions.md`.

| Agent              | Model  | Lane                                                                  |
|--------------------|--------|-----------------------------------------------------------------------|
| `architect`        | Opus   | Gatekeeper. Plans, analyses impact, sequences phases, delegates.      |
| `frontend`         | Sonnet | `frontend/**` only. React, shadcn, Tailwind, Zustand, react-query.    |
| `backend`          | Sonnet | `modules/`, `routes/api/`, `data/`, `models/`, `update_*.py`, `validate_data.py`. |
| `data-completeness`| Opus   | Audits `data/` for schema, effects coverage, D&D 2024 accuracy.       |
| `test`             | Sonnet | Owns `tests/`. Pytest now; frontend tests when introduced.            |
| `docs`             | Sonnet | Owns `docs/`. Keeps Architecture/Stack/DesignSystem/etc. current.     |
| `issue-tracker`    | Sonnet | GitHub Issues / PRs via the GitHub MCP tools.                         |

Specialists report to Architect using the format documented in their `.agent.md`. They **never cross lanes**: `frontend` will refuse to edit Python; `backend` will refuse to edit `frontend/`. If a phase needs both, Architect splits it.

The read-only `Explore` subagent is available to every agent for parallel codebase Q&A.

---

## Skills

Skills are split into **reference** (knowledge lookup; auto-surfaces by relevance) and **workflow** (multi-step procedures any agent can run).

### Reference skills

| Skill                       | What you get                                                            |
|-----------------------------|-------------------------------------------------------------------------|
| `dnd-rules-reference`       | D&D 2024 rule lookup; where each rule type lives in `data/`             |
| `codebase-navigator`        | Repo map; "where does X live?"; layer and ownership boundaries          |
| `design-system-reference`   | Tailwind tokens, typography, shadcn customisations (abridged)           |
| `api-contract-reference`    | `/api/v1/*` endpoint catalogue (abridged)                               |
| `dependency-map`            | How layers depend on each other; blast-radius cheatsheet                |

The full versions of the design system and API contract live in `docs/DesignSystem.md` and `docs/APIContract.md` respectively; the skills are deliberately thin pointers so they stay in sync.

### Workflow skills

| Skill                       | When to invoke                                                                     |
|-----------------------------|------------------------------------------------------------------------------------|
| `add-game-content`          | Batch-add subclasses, backgrounds, feats, or spells.                               |
| `implement-feature`         | Implement **any** feature-bearing entity end-to-end (class/subclass/species/lineage/background/feat/weapon mastery/fighting style/eldritch invocation/spell). |
| `validate-character`        | Spot-check a built character end-to-end.                                           |
| `file-issue`                | Turn a casual report into a structured GitHub Issue.                               |
| `fix-issue`                 | Resolve a known GitHub Issue start-to-finish (branch → fix → test → PR).           |

`implement-feature` is intentionally entity-agnostic — the procedure is the same whether you're adding a Monk subclass, a new feat, a weapon mastery, or an eldritch invocation. Only the data file changes. See its routing table.

---

## Instructions

Instruction files apply automatically when the file paths in their `applyTo` glob (or topic in their description) match the current task.

| File                                              | Triggers on                                       |
|---------------------------------------------------|---------------------------------------------------|
| `effects-system.instructions.md`                  | Effects work in any data or builder file          |
| `data-schemas.instructions.md`                    | `data/**/*.json`                                  |
| `choice-reference.instructions.md`                | Player-choice authoring                           |
| `character-builder-api.instructions.md`           | `to_character()` shape & test assertion paths     |
| `flask-routes.instructions.md`                    | `routes/**/*.py` (REST API v1)                    |
| `frontend-architecture.instructions.md`           | `frontend/**` — enforces the no-calc boundary     |
| `testing.instructions.md`                         | `tests/**/*.py`                                   |

These are **rules, not procedures**. They tell the agent what to do at a fine-grained level when editing the matching files.

---

## Prompts

Prompts are explicit launchers (slash-commands) that take input variables and target a specific agent.

| Prompt                          | Variable             | Target agent        | Purpose                                  |
|---------------------------------|----------------------|---------------------|------------------------------------------|
| `add-data-files.prompt.md`      | `{{ content_type }}` | `backend`           | Generate data files for a content type.  |
| `check-data-files.prompt.md`    | (none)               | `data-completeness` | Read-only audit of `data/` against schemas. |

The older `implement-class` / `implement-species` prompts have been removed — the `implement-feature` skill (invoked by name or auto-detected) covers both, plus every other entity type.

---

## Hooks

Hooks execute automatically after Copilot tool use. Read their output; do not silence them.

| Hook                          | Fires after          | Command                                                                                |
|-------------------------------|----------------------|----------------------------------------------------------------------------------------|
| `hooks/post-edit-data.json`   | data file edits      | `python validate_data.py 2>&1 \| grep -c '❌' \| xargs -I{} test {} -eq 0` (15s)        |
| `hooks/post-edit-python.json` | Python file edits    | `python -m pytest tests/ -x -q --tb=line 2>&1 \| tail -5` (60s)                        |

Frontend has no hook today. The `frontend` agent runs `npm run typecheck` itself before reporting.

---

## Setup Steps

`.github/copilot-setup-steps.yml` runs when the **GitHub Copilot Coding Agent** (cloud runs triggered by labelling an issue with `copilot`) bootstraps:

```yaml
- pip install -r requirements.txt
- pip install pytest
- npm install                 # frontend deps
- python validate_data.py
- pytest tests/ -x -q --tb=short
- npm run typecheck           # frontend SPA
```

This guarantees both backends and frontend are healthy before the agent edits anything.

---

## Interaction Map

```
User Request
   │
   ├─[always]──► copilot-instructions.md (core rules + agent table)
   │
   ├─[editing data/*.json]──► data-schemas.instr.
   │                          effects-system.instr.
   │                          choice-reference.instr.
   │
   ├─[editing modules/character_builder.py
   │   or tests/**]──────────► character-builder-api.instr.
   │
   ├─[editing tests/**]──────► testing.instr.
   │
   ├─[editing routes/api/**]─► flask-routes.instr.
   │
   ├─[editing frontend/**]───► frontend-architecture.instr.
   │
   ├─[multi-file / cross-layer]
   │       └──► Architect Agent
   │              ├─► Explore (read-only discovery)
   │              ├─► frontend
   │              ├─► backend
   │              ├─► data-completeness
   │              ├─► test
   │              └─► docs
   │
   ├─[bug report / feature ask]
   │       └──► issue-tracker / file-issue skill
   │              └──► GitHub Issue ──► (later) fix-issue skill ──► Architect
   │
   ├─[implement any feature]
   │       └──► implement-feature skill
   │              └──► routing table picks data file ──► backend ──► test
   │
   ├─[batch content drop]
   │       └──► add-game-content skill ──► backend
   │
   ├─[audit data/]
   │       └──► data-completeness agent (or check-data-files prompt)
   │
   ├─[validate a build]
   │       └──► validate-character skill
   │
   └─[after every tool edit]
          ├─► post-edit-python.json  → pytest
          └─► post-edit-data.json    → validate_data.py
```

---

## Common Tasks — Recipes

### 1. "Implement the Bladesinger subclass"

→ `implement-feature` skill (auto-detected). Architect approves a plan if it will touch tests + docs + API. Otherwise `backend` does it directly: routing table picks `data/subclasses/wizard/bladesinger.json` and `models/subclass_schema.json`; effects mapped from the catalog; `validate_data.py` and pytest run via hooks.

### 2. "Add the Sailor background"

→ `implement-feature` skill, entity `background`. Same flow, different data path: `data/backgrounds/sailor.json`. No wiki fetcher exists for backgrounds — author from the wiki text by hand.

### 3. "Add Cleave weapon mastery"

→ `implement-feature` skill, entity `weapon mastery`. Edits `data/equipment/weapon_masteries.json`; if the mechanic needs a new effect type, `backend` extends `_apply_effect` and `docs/FEATURE_EFFECTS.md`.

### 4. "Fix issue #42"

→ `fix-issue` skill. Reads the issue, classifies it, branches, hands the implementation to Architect, runs tests, opens a PR. You merge.

### 5. "I think Stunning Strike DC is wrong" (casual)

→ `issue-tracker` agent (or `file-issue` skill). Searches for duplicates, gathers code context, files a structured `[Monk]` issue with `bug` label.

### 6. "Audit the backgrounds folder for completeness"

→ `data-completeness` agent (or `check-data-files` prompt). Walks every file across the seven audit dimensions, writes `data/completeness/backgrounds-<date>.md`, hands findings to `backend`.

### 7. "Make the wizard preview update after a subclass change"

→ Cross-layer ⇒ Architect. Likely phases: confirm `/api/v1/wizard/dependencies` already lists `subclass`; verify `/character/preview-step` returns updated data; have `frontend` rewire the react-query invalidation in the relevant step component; `test` adds a regression assertion; `docs` updates `WizardFlow.md` if the cascade behaviour changed.

### 8. "Add a new field `passive_perception` to the character response"

→ Cross-layer ⇒ Architect. Phases: `backend` adds the field in `to_character()`; `docs` updates `APIContract.md`; `frontend` extends the `Character` type in `lib/api.ts` and surfaces it in the sheet; `test` covers the new path.

### 9. "Validate that my Dwarf Cleric build is correct"

→ `validate-character` skill. Builds via `POST /api/v1/character/build` (or `CharacterBuilder` directly), walks the output against the areas-to-check checklist, reports.

### 10. "Where does X live?" / "What endpoints exist?" / "What tokens are in the theme?"

→ Reference skills (`codebase-navigator`, `api-contract-reference`, `design-system-reference`) auto-surface. For full detail, follow their pointers into `docs/`.

---

## See also

- `.github/copilot-instructions.md` — the always-loaded ground rules
- `docs/Architecture.md` — React/Flask split and API boundary
- `docs/Stack.md` — tech choices and rationale
- `docs/APIContract.md` — endpoint and response shapes
- `docs/DataFiles.md` — `data/` layout and the wiki pipeline
- `docs/FEATURE_EFFECTS.md` — canonical effect catalogue
