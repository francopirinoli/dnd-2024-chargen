# Design System

The visual language is **D&D Beyond–inspired**: dense, content-first, dark-friendly, with a serif display face for character identity and a single warm-red brand accent. Everything is driven by CSS variables in `frontend/src/styles/theme.css` and surfaced as Tailwind tokens in `frontend/tailwind.config.ts`.

## Scope

This document is the cross-app source of truth for:

- design tokens
- typography
- spacing and radius
- component primitives and theming conventions
- global layout conventions shared across multiple surfaces

Wizard-specific page composition, interaction flow, progressive disclosure, validation messaging, and selection behavior live in [docs/design-principles.md](design-principles.md).

Keep these documents separate:

- Use this file when changing tokens, theme variables, typography, or reusable component conventions.
- Use [docs/design-principles.md](design-principles.md) when redesigning or reviewing wizard step layouts and interactions.

## Token Source

- CSS variables live in [frontend/src/styles/theme.css](../frontend/src/styles/theme.css).
- They are mapped to Tailwind theme keys in [frontend/tailwind.config.ts](../frontend/tailwind.config.ts) via `hsl(var(--…))`.
- Both light and dark themes are defined; dark mode is **class-based** (`darkMode: ["class"]`) and toggled by `frontend/src/components/ThemeToggle.tsx`.

Token values are **HSL triplets** (no `hsl(...)` wrapper) so Tailwind can compose opacity utilities (`bg-primary/10`).

## Colour Tokens

### Light theme

| Token                       | HSL triplet         | Notes                              |
|-----------------------------|---------------------|------------------------------------|
| `background`                | `0 0% 100%`         | Page surface                       |
| `foreground`                | `240 10% 4%`        | Default text                       |
| `card` / `card-foreground`  | `0 0% 100%` / `240 10% 4%` | Cards, panels                |
| `popover` / `popover-foreground` | `0 0% 100%` / `240 10% 4%` | Floating surfaces       |
| `primary`                   | `351 85% 41%`       | **D&D Beyond red** (`#C8102E`)     |
| `primary-foreground`        | `0 0% 100%`         | Text on `primary`                  |
| `secondary` / `secondary-foreground` | `240 5% 96%` / `240 6% 10%` | Subtle accent       |
| `muted` / `muted-foreground`| `240 5% 96%` / `240 4% 40%` | Low-emphasis              |
| `accent` / `accent-foreground` | `351 85% 41%` / `0 0% 100%` | Hover/highlight (red)  |
| `destructive` / `destructive-foreground` | `0 72% 45%` / `0 0% 100%` | Errors, danger |
| `border`                    | `240 6% 90%`        | Outlines                           |
| `input`                     | `240 6% 90%`        | Form field borders                 |
| `ring`                      | `351 85% 41%`       | Focus ring (red)                   |

### Dark theme

| Token                       | HSL triplet         |
|-----------------------------|---------------------|
| `background`                | `240 9% 6%`         |
| `foreground`                | `40 30% 92%`        |
| `card` / `card-foreground`  | `240 8% 10%` / `40 30% 92%` |
| `popover` / `popover-foreground` | `240 8% 10%` / `40 30% 92%` |
| `primary`                   | `351 85% 41%`       |
| `primary-foreground`        | `40 30% 96%`        |
| `secondary` / `secondary-foreground` | `240 6% 18%` / `40 30% 92%` |
| `muted` / `muted-foreground`| `240 6% 14%` / `40 12% 65%` |
| `accent` / `accent-foreground` | `351 85% 41%` / `40 30% 96%` |
| `destructive` / `destructive-foreground` | `0 72% 45%` / `40 30% 96%` |
| `border` / `input`          | `240 6% 20%`        |
| `ring`                      | `351 85% 41%`       |

### Aliases

- `brand` is exposed in `tailwind.config.ts` as an alias for `primary`. Use `brand` when the intent is brand identity (logos, hero accents); use `primary` for primary actions.

Always reference colours via Tailwind classes (`bg-card`, `text-muted-foreground`, `border-border`, `bg-primary/10`). **Never hardcode hex/HSL** in components.

## Typography

| Family token   | CSS variable         | Font (fontsource)      | Used for                                    |
|----------------|----------------------|------------------------|---------------------------------------------|
| `font-display` | `--font-display`     | `@fontsource/cinzel`   | Headings, hero text, character sheet titles |
| `font-sans`    | `--font-body`        | `@fontsource/inter`    | Body, UI controls, dense data               |

Both faces are self-hosted via fontsource so the PWA can cache them and there is no third-party request.

Recommended scale (Tailwind defaults; lean on `tracking-tight` for display sizes):

| Use                     | Classes                                              |
|-------------------------|------------------------------------------------------|
| Page title              | `font-display text-3xl md:text-4xl text-primary`     |
| Section header          | `font-display text-xl`                               |
| Body                    | `text-base font-sans`                                |
| Meta / helper text      | `text-sm font-sans text-muted-foreground`            |
| Caption / micro-label   | `text-xs uppercase tracking-widest text-muted-foreground` |

## Radius and Spacing

- `--radius: 0.5rem`. Tailwind exposes:
  - `rounded-lg` → `var(--radius)`
  - `rounded-md` → `calc(var(--radius) - 2px)`
  - `rounded-sm` → `calc(var(--radius) - 4px)`
- Spacing uses the default Tailwind scale.
- `container`: centred, `1rem` padding, max width `1400px` at the `2xl` breakpoint.

## shadcn / Radix Customisations

- Primitives compose Radix (`@radix-ui/react-dialog`, `react-label`, `react-slot`, `react-tabs`, `react-tooltip`).
- Local primitives live in `frontend/src/components/ui/`. **Compose, do not fork.**
- Class composition uses `cn()` from `frontend/src/lib/utils.ts` (`clsx` + `tailwind-merge`).
- Variant-rich components use `class-variance-authority` (`cva`), mirroring shadcn conventions.
- Animations come from `tailwindcss-animate` (already configured) and Radix data-state attributes.
- Dialogs/popovers always use the Radix primitives — never roll a custom portal.

## Iconography

- `lucide-react` only.
- Default size: `h-4 w-4`. Primary actions: `h-5 w-5`.
- Pair every actionable icon with a label or `aria-label`.

## Component Tables (`feature-description`)

The `feature-description` class scope in `theme.css` styles HTML tables embedded in feature descriptions (e.g. class-feature charts):

- `w-full mt-2 border-collapse text-xs`
- Header cells use `bg-muted` + `font-semibold`.
- `tr.table-success` highlights with `bg-primary/10`.
- `tr.table-secondary` deemphasises with `bg-muted/60 text-muted-foreground`.

## Layout Conventions

- **Wizard**: left rail (steps) + main panel + right `<aside>` sticky preview. Implemented by `WizardLayout` and `StepRenderer`. The right `<aside>` currently shows a class portrait; the `EffectsPanel` live preview is wired up but intentionally hidden — see [docs/WizardFlow.md](WizardFlow.md#open-follow-ups).
- Cards stack vertically on mobile, switch to two columns at `md`, three at `lg`.
- Provide both compact and roomy variants for data-dense screens (the character sheet).

## Dark Mode

- All new components must be readable in both themes.
- Never use raw `gray-*` / `zinc-*` — always semantic tokens.
- Test focus rings against both backgrounds (`ring` is `351 85% 41%` in both themes).
- Theme toggle persists via `ThemeToggle.tsx`.

## D&D Beyond Inspiration — Do / Don't

| Do                                                       | Don't                                              |
|----------------------------------------------------------|----------------------------------------------------|
| Use the brand red sparingly for primary actions and identity | Flood the UI with red — the accent loses meaning  |
| Lean on the serif display face for character identity     | Use Cinzel for body text or long lists             |
| Show calculated values prominently (large modifiers, AC)  | Surface raw choices where calculated numbers belong |
| Treat the character sheet as the canonical visualisation  | Re-style the same data inconsistently across views |
| Reference colours through semantic tokens                 | Hardcode hex / HSL values in components            |

## See Also

- [docs/Architecture.md](Architecture.md)
- [docs/Stack.md](Stack.md)
- [docs/WizardFlow.md](WizardFlow.md)
- [docs/design-principles.md](design-principles.md)
