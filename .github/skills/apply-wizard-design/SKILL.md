---
name: apply-wizard-design
description: "Workflow skill. Apply the wizard design principles to an existing or new wizard page in frontend/, using docs/design-principles.md and docs/DesignSystem.md as the source of truth."
---

# Apply Wizard Design

Workflow for implementing or refactoring a wizard page so it follows the repo's design rules.

## When to Use

- When redesigning an existing wizard step in `frontend/src/components/steps/`
- When building a new wizard page or replacing a generic step with a specialized one
- When normalizing layout, hierarchy, selection states, navigation, or validation UI
- When applying the subclass-style progressive disclosure pattern to complex choices

## Sources of Truth

Read these before editing:

- `docs/design-principles.md` — wizard-specific layout and interaction rules
- `docs/DesignSystem.md` — tokens, typography, spacing, reusable component conventions
- `docs/WizardFlow.md` — step order, nested choices, validation expectations
- `.github/instructions/frontend-architecture.instructions.md` — frontend lane and architectural constraints

## Expected Outcomes

A compliant page should:

- make the primary decision of the step obvious
- show clear selection states without relying on color alone
- keep navigation visible and understandable
- use progressive disclosure instead of overloading cards with dense rules text
- preserve the boundary that the frontend does not calculate D&D mechanics

## Procedure

### 1. Identify the Page's Primary Decision

Read the target step and name:

- the primary choice the user is making
- the secondary or dependent choices
- the overload points where too much information is currently shown at once

Examples:
- `ClassStep`: primary = class, dependent = subclass and class-specific choices
- `SpeciesStep`: primary = species, dependent = lineage and trait choices

Do not redesign until you can state the page's primary decision in one sentence.

### 2. Audit Against the Design Principles

Check the current page for:

- step header consistency
- section hierarchy and spacing
- clarity of selected vs unselected states
- visibility of required vs optional choices
- sticky navigation behavior
- validation messaging quality
- use of progressive disclosure for dense content
- mobile layout behavior

Use the smallest set of changes that fixes the page at the right level.

### 3. Pick the Right Interaction Pattern

Choose one of these patterns based on the choice complexity:

- simple buttons or compact cards for short, low-context choices
- card selection for medium-complexity choices
- summary card + detail panel + confirmation for long-term or high-impact choices such as subclasses

For complex choice groups, keep the summary card scannable:

- name
- short fantasy or mechanical identity
- 2-4 high-signal bullets
- `View full details` secondary action
- `Select` primary action

### 4. Implement the Layout and Hierarchy

Normalize the page to the wizard conventions:

- standard step header
- clear H2/H3 section grouping
- consistent spacing rhythm
- sticky footer navigation
- visible selection counters for multi-select groups

Prefer reusing or extending shared components such as:

- `frontend/src/components/wizard/ChoiceList.tsx`
- `frontend/src/components/wizard/StepNav.tsx`
- `frontend/src/components/wizard/ClassAdvancedChoices.tsx`
- primitives in `frontend/src/components/ui/`

Do not fork or restyle the same pattern differently on each step without a good reason.

### 5. Apply Progressive Disclosure Where Needed

When the page includes a complex option such as a subclass or advanced feature package:

- keep the card summary compact
- move full progression details into a detail panel or modal
- keep a clear selection action in the detail view
- show a compact confirmation or selection summary after the choice is made when the decision is high-impact

Do not place long level-by-level feature lists directly in a comparison grid.

### 6. Validate the Step Flow

After the first substantive edit, validate with the narrowest useful check:

- `npm run typecheck`
- `npm run lint` if available and relevant
- manual step walkthrough path if the page is highly interactive

Manual checks should confirm:

- current step can be completed
- required choices gate the continue action correctly
- selected state remains visible after interaction
- mobile and desktop layouts remain usable
- light and dark mode both work

### 7. Report Remaining Gaps

If the page still falls short because of a shared component limitation, missing API data, or an unresolved design conflict, report that clearly instead of papering over it locally.

## Guardrails

- Never calculate D&D stats in the frontend.
- Never hardcode D&D content lists that should come from the API.
- Never hardcode raw colors or spacing values in components.
- Never use hover as the only way to access critical information.
- Never leave the user without a visible path to continue or go back.

## Output Format

```
Page: <target page>
Primary decision: <one sentence>
Patterns applied:
- <pattern>
- <pattern>

Files changed:
- frontend/src/...

Validation:
- <typecheck/lint/manual result>

Remaining gaps:
- <if any>
```
