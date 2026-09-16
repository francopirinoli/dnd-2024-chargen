---
name: review-wizard-design
description: "Workflow skill. Review an existing wizard page against docs/design-principles.md and docs/DesignSystem.md, with findings focused on layout, hierarchy, interaction clarity, and progressive disclosure."
---

# Review Wizard Design

Read-only workflow for evaluating a wizard page against the repo's design rules.

## When to Use

- When asked to critique a wizard page before implementation work begins
- When reviewing a redesign or refactor of a step in `frontend/`
- When checking whether a page is ready to use as the template for the rest of the wizard
- When comparing two page variants against the documented design principles

## Sources of Truth

Review against:

- `docs/design-principles.md` — wizard-specific layout and interaction rules
- `docs/DesignSystem.md` — tokens, typography, spacing, reusable component conventions
- `docs/WizardFlow.md` — step structure and nesting expectations
- the actual target component and any shared components it depends on

## Review Mindset

Findings come first. Focus on:

- user confusion
- weak visual hierarchy
- overloaded selection surfaces
- unclear navigation or validation
- inconsistent use of shared patterns
- accessibility gaps

Do not lead with a summary. Lead with concrete findings ordered by severity.

## Review Checklist

### 1. Primary Decision Clarity

Check whether the page makes the main decision obvious.

Questions:
- Can a user tell the single most important thing they are deciding on this page?
- Are dependent choices visually secondary until they become relevant?
- Is the page trying to solve too many decisions at once?

### 2. Information Hierarchy

Check:
- step header consistency
- H1/H2/H3 structure
- spacing rhythm between sections
- required, optional, and conditional labeling
- readability of supporting text

Flag pages where all content has the same visual weight.

### 3. Selection-State Clarity

Check:
- selected state visibility
- use of icon plus color for selection state
- counter visibility for multi-select groups
- disabled state clarity when limits are reached
- consistency across cards, buttons, and grouped choices

Flag pages where selection relies on a faint border change alone.

### 4. Navigation and Validation

Check:
- whether next and back actions are easy to find
- whether navigation remains accessible during long scrolls
- whether validation messaging is specific and actionable
- whether the continue action is correctly gated by required choices

Flag pages where the user can miss the navigation controls or cannot tell what remains incomplete.

### 5. Progressive Disclosure

Check whether dense information is handled correctly.

Use this rule of thumb:
- brief choices can stay inline
- dense, high-impact choices should use summary + detail drill-down

Flag pages where long feature text, spell text, or level progressions are dumped directly into cards or dense lists.

### 6. Responsive and Accessibility Quality

Check:
- mobile stacking behavior
- tap target comfort
- keyboard focus visibility
- semantic control usage
- contrast in both themes
- use of hover-only interactions

Flag pages that are effectively desktop-only or mouse-only.

## Output Format

Use this structure:

```
Findings:
1. [Severity] <problem> — <file or component>
2. [Severity] <problem> — <file or component>

Open questions:
- <if any>

Recommendation:
- <short next-step guidance>
```

## Severity Guide

- High: likely to confuse or block users, or meaningfully break the step flow
- Medium: weakens clarity or consistency, but the page remains usable
- Low: polish, consistency, or maintainability issue

## Guardrails

- Keep the review grounded in the documented principles, not personal preference.
- Prefer findings that can directly inform an implementation pass.
- If no findings are present, state that explicitly and note any residual testing gaps.
