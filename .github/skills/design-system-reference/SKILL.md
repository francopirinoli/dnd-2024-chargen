---
name: design-system-reference
description: "Reference skill. Tailwind tokens, typography, shadcn/ui customisations, and the D&D Beyond–inspired visual language. Use when styling components or extending the theme."
---

# Design System Reference

> Authoritative sources: [docs/DesignSystem.md](../../../docs/DesignSystem.md) for tokens and reusable component conventions, and [docs/design-principles.md](../../../docs/design-principles.md) for wizard-specific layout and interaction rules. This skill is a quick lookup, not the source of truth.

The visual aesthetic is inspired by **D&D Beyond**: dense, content-first, dark-friendly, with parchment-like warmth in light mode and a warm-red brand accent.

## Token Source

- CSS variables live in `frontend/src/styles/theme.css` (or `globals.css`).
- They are mapped to Tailwind theme keys in `frontend/tailwind.config.ts` via `hsl(var(--…))`.
- Both light and dark themes are defined; dark mode is class-based (`darkMode: ["class"]`) and toggled by `ThemeToggle.tsx`.

## Semantic Colour Tokens (shadcn convention)

| Token                  | Use                                              |
|------------------------|--------------------------------------------------|
| `background`/`foreground` | Page surface and default text                 |
| `card` / `card-foreground` | Cards, panels                                |
| `popover` / `popover-foreground` | Floating surfaces (dropdowns, dialogs)  |
| `primary` / `primary-foreground` | Brand accent (D&D Beyond red)           |
| `secondary` / `secondary-foreground` | Subtle accent                       |
| `muted` / `muted-foreground` | Low-emphasis backgrounds and text          |
| `accent` / `accent-foreground` | Hover states, soft highlights            |
| `destructive` / `destructive-foreground` | Errors, destructive actions    |
| `border` / `input` / `ring` | Outlines and focus rings                    |
| `brand`                | Alias for `primary` — use when intent is brand identity rather than action emphasis |

Always reference via Tailwind classes (`bg-card`, `text-muted-foreground`, `border-border`, …). Do not hardcode hex/HSL in components.

## Typography

| Family token   | CSS variable        | Used for          |
|----------------|---------------------|-------------------|
| `font-display` | `--font-display` (Cinzel)  | Headings, hero text, sheet titles |
| `font-sans`    | `--font-body` (Inter)      | Body, UI controls |

Recommended scale (Tailwind defaults are fine; lean on `tracking-tight` for display sizes):
- `text-3xl`/`text-4xl` `font-display` — page titles
- `text-xl` `font-display` — section headers
- `text-base` `font-sans` — body
- `text-sm` `font-sans text-muted-foreground` — meta / helper text

## Spacing & Radius

- Default Tailwind spacing scale.
- Radius is variable-driven: `lg = var(--radius)`, `md = calc(var(--radius) - 2px)`, `sm = calc(var(--radius) - 4px)`. Tune `--radius` once, everything follows.
- Container: centred, `1rem` padding, max `1400px` at `2xl`.

## Iconography

- `lucide-react` only. Default size `h-4 w-4`; `h-5 w-5` for primary actions.
- Pair icon + label for any actionable control.

## Component Patterns

- Primitives live in `frontend/src/components/ui/`. Compose, do not fork.
- Use `cn()` from `lib/utils.ts` to merge classes (`clsx` + `tailwind-merge`).
- Use `class-variance-authority` (`cva`) for variant-rich components, mirroring shadcn conventions.
- Animations via `tailwindcss-animate` (already configured) and Radix data attributes.
- Dialogs/popovers: Radix primitives wrapped by shadcn — never roll your own portals.

## Layout Conventions

- Wizard: left rail (steps) + main panel + right preview (sheet snapshot from `/api/v1/character/build`).
- Cards stack vertically on mobile; switch to two-column at `md`, three-column at `lg`.
- Always provide both compact and roomy variants for data-dense screens (character sheet).

For wizard step redesigns, also consult `docs/design-principles.md` for:
- sticky footer navigation
- selection-state clarity
- progressive disclosure for complex choices
- section hierarchy and validation messaging

## Dark Mode

- All new components must be readable in both themes.
- Never use raw `gray-*` / `zinc-*`; always semantic tokens.
- Test focus rings against both backgrounds.

## D&D Beyond Inspiration — Do / Don't

| Do                                                 | Don't                                          |
|----------------------------------------------------|------------------------------------------------|
| Use the brand red sparingly for primary actions    | Flood UI with red — it loses meaning           |
| Lean on serif display type for character identity  | Use Cinzel for body text — it harms readability|
| Show calculated values prominently (big modifiers) | Surface raw choices where calc'd numbers belong|
| Treat the sheet as the source of truth visualisation | Re-style the same data inconsistently across views |
