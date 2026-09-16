---
description: "Use when working in the React SPA: components, hooks, Zustand stores, shadcn/ui, Tailwind, react-query, react-router, PWA. Enforces the calculation-free frontend boundary."
applyTo: "frontend/**"
---

# Frontend Architecture Rules

The React SPA is a **view + raw-choice capture surface**. It must never derive D&D stats.

## The Hard Boundary

| Frontend MAY                                | Frontend MUST NOT                                       |
|---------------------------------------------|---------------------------------------------------------|
| Capture player choices (class, ASI, spells) | Compute modifiers, AC, HP, save DCs, slot counts, PB    |
| Display values from `/api/v1/character/build` | Roll/total dice, calculate spell slots                |
| Format numbers, pluralise text              | Apply effects from `data/`                              |
| Validate raw input shape (Zod)              | Decide whether a feature applies, or at what level      |
| Cache server responses (react-query)        | Re-implement any logic that lives in `CharacterBuilder` |

**If the UI needs a value, the backend computes it and the API returns it.** Add a field to `to_character()` (or a new `/api/v1/*` endpoint) before reaching for a TS helper.

## State Layers

| Layer            | Holds                                       | Library            |
|------------------|---------------------------------------------|--------------------|
| Server cache     | API responses (catalog, built character)    | `@tanstack/react-query` |
| Player choices   | Raw `ChoicesMade` from the wizard           | Zustand (`characterStore`) |
| Roster / saved   | LocalStorage-backed character list          | Zustand (`rosterStore`) |
| UI flags         | Open dialogs, current step, theme           | Zustand or local component state |

Zustand stores hold **raw choices and UI flags only**. Derived character data lives in the react-query cache from `/api/v1/character/build`. Do not duplicate calculated fields into Zustand.

## API Access

- All HTTP goes through `frontend/src/lib/api.ts`. Do not call `fetch` from components.
- Types in `api.ts` mirror the backend response shape; keep them in sync with `docs/APIContract.md`.
- Use react-query hooks (`useQuery`, `useMutation`) — no manual `useEffect` + `fetch`.

## UI Kit & Styling

- Use **shadcn/ui** primitives (already in `src/components/ui/` once added). Compose, do not fork.
- New shadcn components go in `src/components/ui/` via the shadcn CLI pattern.
- Use Tailwind utility classes. Theme tokens live as CSS variables in `src/styles/theme.css` and are mapped in `tailwind.config.ts`.
- Use the `cn()` helper from `src/lib/utils.ts` for conditional class merging.
- Icons: `lucide-react` only.
- Fonts: `var(--font-display)` (Cinzel) for headings, `var(--font-body)` (Inter) for body.
- See `docs/DesignSystem.md` for tokens, spacing, and D&D Beyond–inspired conventions.

## Routing

- `react-router-dom` v6. Routes are declared in `src/app/` (or `src/main.tsx`).
- Wizard step routing lives under a single parent route; step ids match `WizardStep.id` from the API.

## PWA

- `vite-plugin-pwa` is configured in `vite.config.ts`.
- New static assets must be added to the precache glob if they should work offline.
- `OfflineIndicator` and `UpdatePrompt` components handle the runtime UX.

## Persistence (current → future)

- **Now**: Zustand `rosterStore` persists to LocalStorage.
- **Future**: same store will sync to Flask + Postgres behind auth. Keep the store API stable so the swap is local to one file.

## File Layout

```
frontend/src/
  app/             # Route tree, providers (QueryClient, Theme, Router)
  pages/           # Route-level views
  components/
    ui/            # shadcn primitives (Button, Dialog, Tabs, ...)
    layout/        # Shell, header, nav
    wizard/        # Wizard shell, step navigation
    steps/         # Individual wizard step components
  store/           # Zustand stores (UI state + raw choices ONLY)
  lib/
    api.ts         # Typed REST client — single HTTP boundary
    utils.ts       # cn() and tiny helpers (no D&D logic)
  styles/          # Tailwind entry + theme tokens
  main.tsx
```

## Forbidden Patterns

- Computing ability modifiers in TS (`Math.floor((score - 10) / 2)`).
- Hardcoding spell-slot tables, proficiency bonus tables, or class feature lists.
- Duplicating `data/*.json` content into TS constants — fetch from the catalog API.
- Branching component logic on hardcoded class/species/feature names. Drive UI from API metadata where possible.
- Calling `fetch` outside `lib/api.ts`.
- Storing computed character fields in Zustand.

## Adding a New Wizard Step

1. Confirm the step exists in `/api/v1/wizard/steps` (backend owns the flow).
2. Add the step component under `src/components/steps/`.
3. Read raw choices from / write to `characterStore`.
4. Render values for the live preview by reading the react-query result of `/api/v1/character/build`.
5. Update `docs/WizardFlow.md` if step ordering, nesting, or dependencies change.

## Anti-Patterns (forbidden)

- **Dual-writing class allocation**: never write flat `class`/`level`/`subclass` keys. Use `classes[]` only.
- **Synthesizing choice keys**: never construct `feat_{name}_{index}` or similar. Use `choices_made_key` / `choice_key` from the server response only. If the key is absent, warn and skip.
- **Filtering server-provided lists client-side**: never remove items from `always_prepared`, `spell_management`, or any server-derived list. Display the server output as-is.
- **Unvalidated payloads**: all outbound `ChoicesMade` objects must pass `ChoicesMadeSchema` before dispatch. Zod is the enforcement layer.
- **Calculating D&D stats in TypeScript**: modifiers, AC, HP, proficiency bonus, save DCs are never computed in the frontend.
