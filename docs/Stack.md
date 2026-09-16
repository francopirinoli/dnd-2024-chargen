# Stack

Per-layer technology choices and the reasoning behind them. Reflects what is in `frontend/package.json`, `requirements.txt`, and the runtime configuration today.

## Summary

| Layer        | Choice                                                              |
|--------------|---------------------------------------------------------------------|
| Frontend     | Vite + React 18 + TypeScript                                        |
| UI kit       | shadcn/ui (Radix primitives) + Tailwind CSS + lucide-react          |
| Client state | Zustand 5 (raw choices + UI flags only)                             |
| Data fetch   | `@tanstack/react-query` 5 → typed client in `frontend/src/lib/api.ts` |
| Schema/parse | `zod`                                                               |
| Routing      | `react-router-dom` 6                                                |
| PWA          | `vite-plugin-pwa`                                                   |
| Persistence  | `localStorage` now → Flask + PostgreSQL + auth later                |
| Backend      | Flask (REST API only, stateless)                                    |
| Calculations | Python `CharacterBuilder` + effects system                          |
| Data         | JSON files in `data/`, validated against `models/` JSON Schemas     |
| CI/Tracking  | GitHub Issues + PRs                                                 |

## Frontend

### Vite + React 18 + TypeScript
A small, opinionated SPA toolchain with first-class TypeScript support and instant HMR. Vite's dev server is configured for devcontainer/Codespaces use (`host: true`, `clientPort: 443`, `wss` HMR) and proxies `/api` to Flask on `localhost:5000`. React 18's concurrent features back the wizard's optimistic flows; TypeScript enforces the API contract at the client boundary.

### shadcn/ui + Tailwind CSS
Headless Radix primitives composed by shadcn give us accessible dialogs, tabs, tooltips, labels and slots without a heavyweight component library. Tailwind keeps styling colocated with markup and lets the design tokens in `frontend/src/styles/theme.css` (HSL triplets, CSS variables) drive both light and dark themes uniformly. See [docs/DesignSystem.md](DesignSystem.md).

Specific Radix packages in use: `react-dialog`, `react-label`, `react-slot`, `react-tabs`, `react-tooltip`. Helpers: `class-variance-authority` for variant-rich components, `clsx` + `tailwind-merge` (`cn()` in `lib/utils.ts`) for class composition, `tailwindcss-animate` for transitions, `lucide-react` for iconography.

### Zustand 5 (UI state only)
Zustand is intentionally narrow: it holds the player's raw `choices_made`, the wizard's current step, and the cascade dependency map fetched from `/api/v1/wizard/dependencies`. It never derives D&D values. The `persist` middleware writes the draft to `localStorage` under `dnd-creator-character-v1` with a `version` field and a `migrate` shim, so the same blob can later sync to a server without changing the consuming components.

### `@tanstack/react-query` 5
All network access goes through the typed client in `frontend/src/lib/api.ts`, wrapped by react-query for caching, revalidation, and request deduplication. Query keys mirror the URL family (`["wizard", "steps"]`, `["character", "build", choicesMade]`), so invalidating a class change wipes derived caches in one call (see `WizardLayout.handleStartOver`).

### `zod`
Available for runtime validation of payloads at the boundary. Used sparingly today; intended for stricter parsing as the API surface grows.

### `react-router-dom` 6
Standard routing: `/`, `/wizard`, `/wizard/:stepId`, `/sheet/:id`, `/sheet/:id/pdf`. Layout routes own the sidebar/outlet split.

### `vite-plugin-pwa`
Auto-update service worker so the wizard works offline once visited. Workbox precaches JS/CSS/HTML/SVG/PNG/WOFF2 but **excludes `pdf_template/**`** because the printable sheet backgrounds are >2 MB each and only needed by the PDF view. Theme/background colours match the dark theme.

### Typography — `@fontsource/cinzel`, `@fontsource/inter`
Self-hosted via fontsource so there is no third-party font request and the PWA can cache them. Cinzel (display) carries the D&D Beyond–inspired serif identity; Inter (body) keeps long lists and tables readable.

## Backend

### Flask
Small, dependency-light HTTP framework. The REST API lives entirely under `routes/api/` (blueprints `catalog_bp`, `character_bp`, `wizard_bp`) and is stateless — no server-side request state, no cookies.

### `CharacterBuilder` + effects system
The single source of truth for every derived value. Choices in, calculated character out via `to_character()`. All mechanical benefits are structured `effects` arrays in JSON, applied by a generic dispatcher — application code never branches on feature names. See [docs/FEATURE_EFFECTS.md](FEATURE_EFFECTS.md) and [docs/character_builder_guide.md](character_builder_guide.md).

## Data

### JSON in `data/`, schemas in `models/`
Game content (classes, subclasses, species, lineages, backgrounds, feats, spells, equipment) is plain JSON, version-controlled with the rest of the source. JSON Schemas in `models/` (`class_schema.json`, `subclass_schema.json`, `character_sheet_v2_schema.json`) define required fields and shapes. `validate_data.py` enforces them in CI.

Wiki ingestion (`update_classes.py`, `update_species.py`, `update_spells.py`) caches D&D 2024 wiki HTML/JSON under `wiki_data/`. See [docs/DataFiles.md](DataFiles.md) for the layout and the spell-fetcher asymmetry.

## Tooling

### GitHub Issues + PRs
Bugs and feature gaps are tracked as Issues on `QuickNS/dnd-character-creator` with `[Category]` titles and `bug` / `enhancement` labels. The `issue-tracker` agent and the `file-issue` / `fix-issue` skills wrap the workflow.

## See Also

- [docs/Architecture.md](Architecture.md)
- [docs/APIContract.md](APIContract.md)
- [docs/DesignSystem.md](DesignSystem.md)
- [docs/DataFiles.md](DataFiles.md)
