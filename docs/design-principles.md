# Design Principles for D&D 2024 Character Creator Wizard

## Purpose

This document defines the UI and UX patterns, interaction design, and layout rules for the character creation wizard. It complements [DesignSystem.md](./DesignSystem.md), which defines visual design tokens, by specifying how those tokens should be applied to create a consistent, intuitive, and aesthetically pleasing experience.

Scope boundary:
- [DesignSystem.md](./DesignSystem.md) is the cross-app source of truth for tokens, typography, spacing, radius, and reusable component conventions.
- This document is the wizard-specific source of truth for page composition, information hierarchy, navigation, validation behavior, and progressive disclosure patterns.

These should remain separate unless the application collapses to a single surface with no meaningful distinction between token rules and wizard interaction rules.

Target audience: frontend developers, UX designers, and contributors implementing or modifying wizard step components.

Related documentation:
- [DesignSystem.md](./DesignSystem.md) - Visual design tokens, colors, typography, spacing
- [WizardFlow.md](./WizardFlow.md) - Step structure, data dependencies, API contract
- [Architecture.md](./Architecture.md) - React/Flask separation, calculation boundaries

## Core Design Goals

Every design decision in the wizard must serve these three principles.

### 1. Aesthetically Pleasing and Modern

- Clean, uncluttered interface with purposeful use of whitespace.
- D&D Beyond-inspired visual language with serif headings and warm red accents.
- Smooth transitions and microinteractions that provide feedback.
- Support both light and dark themes with equal attention to quality.

### 2. Clear Information Architecture

- Visual hierarchy that guides the eye to the most important elements.
- Logical grouping of related choices.
- Progressive disclosure: show complexity only when needed.
- Consistent labeling and terminology throughout.

### 3. Obvious Flow and Operation

- The user always knows where they are, what they need to do, and how to proceed.
- Primary actions are prominent; secondary actions are accessible but not distracting.
- Validation feedback is immediate and helpful.
- Navigation is sticky, persistent, and predictable.

## 1. Layout Structure

### 1.1 Wizard Shell

Implementation anchor: `frontend/src/components/layout/WizardLayout.tsx`

```text
┌─────────────────┬──────────────────────────┬──────────────┐
│ Left Sidebar    │ Main Content Area        │ Right Sidebar│
│ Step Nav        │ Step Component           │ Character    │
│                 │                          │ Preview      │
│ - Step 1        │ [Step Header]            │ [Stats]      │
│ - Step 2 ✓      │ [Instructions]           │ [HP / AC]    │
│ → Step 3        │ [Selection UI]           │ [Abilities]  │
│ - Step 4        │ [Choices]                │              │
│                 │                          │              │
│ [Theme Toggle]  │ [Sticky Footer Nav]      │              │
└─────────────────┴──────────────────────────┴──────────────┘
```

Rules:
- Left sidebar is fixed-width navigation for steps, progress indicators, and theme toggle.
- Left sidebar is always visible on `md+` screens and collapses on mobile.
- Main content is the active step surface and should use comfortable reading width and spacing.
- Right sidebar is reserved for live character preview and should be sticky on larger screens.
- Main content should scroll independently from sticky navigation where practical.

### 1.2 Step Header

Every step should start with the same structure.

```tsx
<header className="mb-8">
  <p className="text-sm text-muted-foreground uppercase tracking-widest mb-2">
    Step {stepNumber} of {totalSteps}
  </p>
  <h1 className="font-display text-3xl md:text-4xl text-primary mb-2">
    {stepTitle}
  </h1>
  {stepDescription && (
 
  Distinct informational-panel styling rule:
  - Detail panels must visually read as informational surfaces, not selectable cards.
  - Use the shared `info-panel` pattern from `frontend/src/styles/theme.css`:
    - `info-panel`
    - `info-panel-header`
    - `info-panel-kicker`
    - `info-panel-title`
    - `info-panel-body`
    - `info-panel-block`
  - Do not reuse choice-card hover or selected-fill treatments inside informational panels.
  - Keep panel chrome stable: no hover lift, no click affordance on container.
    <p className="text-base text-muted-foreground max-w-3xl">
      {stepDescription}
    </p>
  )}
</header>
```

Rules:
- Step counter uses small uppercase tracking.
- Step title uses the display font and primary color.
- Description stays readable with a max width.
- The header separates the step context from the task area.

### 1.3 Responsive Breakpoints

Use Tailwind defaults consistently.

- Mobile-first base styles apply below `sm`.
- `sm`: single-column layouts can expand to two columns.
- `md`: left sidebar becomes visible and card grids can open further.
- `lg`: right sidebar may appear and the full desktop composition can be used.
- `xl`: respect the maximum reading width and avoid stretching content excessively.

Recommended grids:
- Selection cards: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4`
- Form sections: `grid grid-cols-1 md:grid-cols-2 gap-6`
- Dense summaries: stack on mobile and split only when readability improves.

## 2. Selection UI Patterns

### 2.1 Button-Based Selection

Primary anchor: `frontend/src/components/wizard/ChoiceList.tsx`

The current wizard uses button-based selection for classes, species, backgrounds, skills, feats, and similar choices. This remains the preferred baseline pattern.

Visual states:
- Unselected: light border, neutral surface, subtle hover highlight.
- Selected: red border, tinted background, stronger visual emphasis.
- Disabled: reduced opacity and blocked interaction.
- Focused: visible ring using semantic focus token.

Recommended selected-state enhancement:

```tsx
{isSelected && (
  <Check className="absolute top-2 right-2 h-5 w-5 text-primary" />
)}
```

Rules:
- Selection must be visible without relying on color alone.
- The selected state should include both border and icon feedback.
- Hover and focus states must remain visible in both themes.

### 2.2 Card-Based Selection

For more complex choices such as classes, subclasses, species, and backgrounds, use cards rather than minimal buttons.

```tsx
<button
  className={cn(
    "relative text-left rounded-lg border p-5 transition-all duration-200",
    "hover:shadow-md hover:-translate-y-0.5",
    isSelected
      ? "border-primary bg-secondary ring-2 ring-primary/20"
      : "border-border hover:bg-secondary/40"
  )}
>
  {isSelected && (
    <Check className="absolute top-4 right-4 h-5 w-5 text-primary" />
  )}
  <h3 className="font-display text-xl mb-2 font-semibold">{title}</h3>
  <p className="text-sm text-muted-foreground mb-3">{summary}</p>
  <ul className="text-xs space-y-1">
    {keyFeatures.map((feature) => (
      <li key={feature}>• {feature}</li>
    ))}
  </ul>
</button>
```

Rules:
- Cards need a clear primary action and a clear selected state.
- Hover motion should be subtle.
- Keep summaries short enough for scanning.
- Use consistent spacing and radius across all card groups.

### 2.3 Single-Choice and Multi-Choice Rules

- Single-choice groups should behave like radio groups even when visually presented as cards or buttons.
- Multi-choice groups should show a visible counter and selection limit.
- When a multi-select limit is reached, unselected options should be disabled rather than silently ignored.

### 2.4 Selection Counters

Multi-choice interfaces should always show progress.

```tsx
<div className="flex items-center justify-between mb-3">
  <h3 className="font-semibold">{title}</h3>
  <span className={cn(
    "text-sm font-medium",
    selected.length === required ? "text-primary" : "text-muted-foreground"
  )}>
    {selected.length} of {required} selected
  </span>
</div>
```

Rules:
- Counters should be visible before the options, not hidden after interaction.
- Completed counters should be visually distinct.
- Validation should explain what is still required.

## 3. Navigation and Flow

### 3.1 Sticky Footer Navigation

Navigation must remain visible while the user scrolls.

```tsx
<footer className="sticky bottom-0 left-0 right-0 bg-background/95 backdrop-blur-sm border-t border-border p-4 mt-8">
  <div className="container flex items-center justify-between">
    <Button variant="ghost" onClick={handleBack} disabled={isFirstStep}>
      <ChevronLeft className="h-4 w-4 mr-1" />
      {prevStepLabel || "Back"}
    </Button>

    <span className="text-sm text-muted-foreground">
      Step {currentStep} of {totalSteps}
    </span>

    <Button onClick={handleNext} disabled={!isStepValid}>
      {nextStepLabel || "Continue"}
      <ChevronRight className="h-4 w-4 ml-1" />
    </Button>
  </div>
</footer>
```

Rules:
- Back is secondary; continue is primary.
- Continue remains disabled until required choices are complete.
- Progress context stays visible in the footer.
- The footer should feel attached to the current step, not the entire app shell.

### 3.2 Validation Feedback

Validation must be specific and immediate.

```tsx
{!isStepValid && (
  <div className="rounded-md bg-destructive/10 border border-destructive/20 p-4 mb-6">
    <div className="flex items-start gap-2">
      <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
      <div>
        <h4 className="font-semibold text-destructive mb-1">
          Incomplete selections
        </h4>
        <ul className="text-sm space-y-1">
          {missingRequirements.map((req) => (
            <li key={req}>• {req}</li>
          ))}
        </ul>
      </div>
    </div>
  </div>
)}
```

Rules:
- Name the missing requirements explicitly.
- Put validation near the primary action.
- Remove the message as soon as the requirement is satisfied.

### 3.3 Step Completion Indicators

The step list should communicate current, complete, and pending states clearly.

Rules:
- Current step gets the strongest emphasis.
- Completed steps show a clear completion icon.
- Future steps remain available but visually quieter.
- Users should be able to revisit previous steps without friction.

## 4. Information Hierarchy

### 4.1 Type Scale

Use this hierarchy consistently.

- H1: step title, `font-display text-3xl md:text-4xl text-primary`
- H2: major section, `font-display text-2xl text-foreground`
- H3: subsection, `font-semibold text-lg`
- H4: feature or option title, `font-medium text-base`
- Body: `text-sm text-muted-foreground`
- Label or metadata: `text-xs uppercase tracking-widest text-muted-foreground`

Rules:
- Do not skip levels.
- Each step should have one H1.
- Major sections should be visually obvious before the user reads body copy.

### 4.2 Spacing Rhythm

Use consistent vertical spacing:
- Between major sections: `space-y-8`
- Between subsections: `space-y-6`
- Between related choice groups: `space-y-4`
- Between closely related lines: `space-y-2`

Rules:
- Use spacing to show structure before borders are needed.
- Avoid stacking multiple dense panels without extra separation.

### 4.3 Required, Optional, and Conditional Labels

Patterns:
- Required sections do not need a label saying they are required.
- Optional sections should explicitly say `(Optional)`.
- Conditional sections should explain when or why they appear.

Example:

```tsx
<h3 className="font-semibold text-lg mb-4">
  Subclass
  <span className="text-xs font-normal text-muted-foreground ml-2">
    Available at level 3
  </span>
</h3>
```

## 5. Progressive Disclosure Patterns

### 5.1 Problem Statement

Some D&D choices carry implications across many levels. Subclasses are the clearest example. A subclass card cannot reasonably display every feature from level 3 through max level, but hiding that information completely leads to uninformed decisions.

The design goal is to support three user behaviors:

### 5.1a Class & Subclass Selection — Detail Panel Pattern (2026)

Class selection now mirrors the subclass pattern for consistency and clarity. Both use a summary card grid and a detail panel (info-panel style) for progressive disclosure and comparison.

**Pattern:**

- **Summary Card Grid:**
  - Grid of cards for each class or subclass (name, tagline, icon)
  - Cards are clickable and hoverable
- **Detail Panel (Info-Panel):**
  - Selecting or hovering a card opens the detail panel
  - Panel displays:
    - Full description
    - Features by level (with robust extraction of both string and object features)
    - Hit dice, proficiencies, and other class-specific info (for classes)
    - Any special rules or notes

**Interaction:**

- Selecting or hovering a class or subclass card updates the detail panel
- The detail panel remains visible for comparison until another card is selected/hovered
- Users can compare options without committing to a choice

**Visual Style:**

- The detail panel uses the `info-panel` style:
  - Elevated card appearance
  - Clear section headers
  - Scrollable if content is long
- Consistent styling across class and subclass selection for a unified experience

**Rationale:**

- Consistency: Both class and subclass selection use the same interaction and visual pattern, reducing cognitive load
- Clarity: Players can see all relevant details before making a choice
- Progressive Disclosure: Only the selected/hovered option reveals full details, preventing information overload
- Robust Feature Extraction: The frontend logic extracts and displays all features, handling both string and object feature formats

**Feature Extraction Logic:**

- The detail panel leverages robust feature extraction logic:
  - Handles both string and object features in the `features_by_level` data
  - Ensures all class and subclass features are displayed accurately, regardless of data shape
  - Supports future-proofing as new feature types are added

**Implementation Note:**

- The feature extraction logic is shared between class and subclass panels, ensuring consistency and maintainability.

See also:
- [DesignSystem.md](DesignSystem.md) for visual tokens and info-panel styling
- [WizardFlow.md](WizardFlow.md) for step order and dependencies

### 5.2 Recommended Pattern: Summary Card + Detail Panel + Confirmation

This is the default pattern for complex choices such as subclasses, advanced feats, and other options with long-term progression.

#### Summary Card

The card should show only the information needed for scanning and shortlisting.

Recommended card content:
- Subclass name
- One-line fantasy or role summary
- Mechanical focus label, such as Combat, Healing, Control, or Utility
- A short list of signature early features or themes
- Secondary action: `View full details`
- Primary action: `Select`

Example structure:

```tsx
<div className="rounded-lg border p-5">
  <h4 className="font-display text-lg mb-1">War Domain</h4>
  <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2">
    Combat • Divine frontliner
  </p>
  <p className="text-sm mb-3">
    A battle-focused cleric domain built around martial pressure and divine offense.
  </p>
  <ul className="text-xs space-y-1 mb-4">
    <li>• Martial emphasis</li>
    <li>• Early offensive features</li>
    <li>• Strong frontline identity</li>
  </ul>
  <div className="flex gap-2">
    <Button variant="outline" size="sm">View full details</Button>
    <Button size="sm">Select</Button>
  </div>
</div>
```

Rules:
- Do not dump full level-by-level text into the card.
- Do not rely on level 3 features alone to define the entire subclass.
- Make the summary useful for comparison, not exhaustive.

#### Detail Panel

On desktop, `View full details` should open a right-side slide panel or a dialog aligned to the reading flow. On mobile, this should become a full-screen modal or dialog.

Recommended panel content:
- Full subclass title and summary
- Flavor overview or short design intent
- Feature progression grouped by level
- Expandable sections for each feature tier
- Primary action in the panel footer: `Select this subclass`

Suggested structure:

```tsx
<Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
  <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
    <DialogHeader>
      <DialogTitle className="font-display text-2xl">{option.name}</DialogTitle>
      <DialogDescription className="text-base">
        {option.fullDescription}
      </DialogDescription>
    </DialogHeader>

    <div className="space-y-4">
      {option.featuresByLevel.map(({ level, features }) => (
        <Accordion key={level} type="single" collapsible>
          <AccordionItem value={`level-${level}`}>
            <AccordionTrigger>Level {level}</AccordionTrigger>
            <AccordionContent>
              {features.map((feature) => (
                <div key={feature.name} className="space-y-1">
                  <h5 className="font-semibold text-sm">{feature.name}</h5>
                  <div className="text-sm">{feature.description}</div>
                </div>
              ))}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      ))}
    </div>

    <DialogFooter>
      <Button variant="ghost">Close</Button>
      <Button>Select this subclass</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

Rules:
- The detail view is for understanding, not for replacing the main selection surface.
- Keep the selection call to action available in the panel.
- On desktop, ensure this does not permanently conflict with the live character preview.

#### Confirmation Surface

After a user selects a complex option, show a compact confirmation area summarizing what that choice means.

Purpose:
- Reinforce confidence
- Give the user one more chance to switch
- Surface the long-term implications without forcing them to re-open the panel

Rules:
- The confirmation surface should summarize feature progression at a high level.
- It should include `Change selection` and `Confirm` or simply fold into step completion.
- Do not require a second confirmation for every trivial choice. Reserve this for high-impact decisions.

### 5.3 When to Use This Pattern

Use summary card + detail panel + confirmation for:
- Subclasses
- Advanced class feature packages
- Feats with dense rule text
- Species choices with multiple long-term effects

Do not use this full pattern for:
- Simple skill choices
- Language selection
- Basic binary options with minimal implications

### 5.4 Alternate Patterns and Tradeoffs

Possible alternatives:
- Expandable cards: good for in-place exploration, but can create very tall pages and unstable scanning.
- Full modal only: good for focus, but worse for comparison and step continuity.
- Compare view: useful as a secondary enhancement, but not a substitute for the main selection pattern.

Preferred default:
- Use summary cards in the main surface.
- Use a detail panel or modal for full information.
- Add compare mode only if the content genuinely benefits from side-by-side analysis.

## 6. Visual Feedback and Interaction States

### 6.1 Interaction States

Every interactive element must support:
- Default
- Hover
- Focus
- Selected or active
- Disabled

Recommended classes:
- Hover: `hover:bg-secondary hover:border-primary/40 transition-colors duration-200`
- Focus: `focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2`
- Active: `border-primary bg-secondary ring-2 ring-primary/20`
- Disabled: `opacity-40 cursor-not-allowed pointer-events-none`

### 6.2 Loading States

Whenever the wizard is rebuilding preview data or saving selections, show a loading state.

```tsx
<div className="flex items-center justify-center py-12">
  <div className="flex flex-col items-center gap-3">
    <Loader2 className="h-8 w-8 animate-spin text-primary" />
    <p className="text-sm text-muted-foreground">Loading options...</p>
  </div>
</div>
```

Rules:
- Never leave the user wondering whether a click registered.
- Inline button spinners are preferred for short operations.

### 6.3 Success and Error Feedback

Success feedback should be brief and low-drama.
Error feedback should be actionable and specific.

Rules:
- Success messages should confirm the result, not celebrate excessively.
- Error messages should explain the problem and offer recovery.
- Retry actions should be local to the failed operation.

### 6.4 Motion

Use motion sparingly and purposefully.

Rules:
- Keep transitions under 300ms.
- Prefer fade, slight scale, and small slide transitions.
- Respect reduced-motion preferences.
- Do not use decorative animations that distract from selection tasks.

## 7. Content Guidelines

### 7.1 Writing Style

- Be concise.
- Use active voice.
- Prefer instructions that tell the player exactly what to do.
- Add context when a rule depends on level or prerequisite state.

### 7.2 Instruction Pattern

Recommended structure:

```tsx
<h3 className="font-semibold text-lg mb-2">{featureName}</h3>
<p className="text-sm text-muted-foreground mb-4">
  Choose {count} option{count === 1 ? "" : "s"} from the following.
</p>
```

### 7.3 Feature Text

When rendering feature text from game data:
- Preserve meaningful structure such as lists and tables.
- Use readable body text size.
- Avoid dumping dense prose without grouping or headings.

## 8. Responsive Design

### 8.1 Mobile-First Rules

- Start with stacked layouts.
- Expand only when width improves comprehension.
- Keep primary actions visible.
- Touch targets must remain comfortably tappable.

### 8.2 Sidebar Behavior

- On mobile, the left sidebar collapses and the right sidebar should not compete with the main task.
- On tablet, prioritize the step nav over the live preview.
- On desktop, use the full three-area composition only when it improves clarity.

## 9. Accessibility

### 9.1 Keyboard and Focus

- All controls must be keyboard accessible.
- Focus order must follow the visual order.
- Focus states must be clearly visible in both themes.

### 9.2 Semantic Structure

- Use real buttons for actions.
- Use semantic headings.
- Add `aria-label` to icon-only actions.
- Use `aria-live` for dynamic validation or save feedback where appropriate.

### 9.3 Contrast and Motion

- Meet WCAG 2.1 AA contrast standards.
- Respect reduced-motion preferences.
- Do not communicate state with color alone.

## 10. Implementation Checklist

Before shipping a wizard step update, verify:

Layout:
- Step header follows the standard pattern.
- Main content uses consistent spacing.
- Navigation remains visible while scrolling.
- The layout behaves well across mobile, tablet, and desktop.

Selection UI:
- Selected state is obvious.
- Counters are visible for multi-select groups.
- Hover, focus, and disabled states are implemented.
- Complex choices use progressive disclosure instead of dense cards.

Information hierarchy:
- Headings follow the correct scale.
- Sections are clearly separated.
- Optional and conditional content is labeled clearly.

Feedback:
- Validation is specific.
- Loading states exist.
- Error states offer recovery.

Accessibility:
- Keyboard navigation works.
- Contrast is acceptable.
- Focus indicators are visible.

## 11. Anti-Patterns

Do not:
- Hardcode colors instead of using design tokens.
- Hide navigation controls at the bottom of long forms without sticky access.
- Put complete long-form subclass progression directly in a card grid.
- Use vague validation copy such as `Please fill in all fields`.
- Skip mobile design and retrofit later.
- Depend on hover alone for critical information.
- Use color alone to indicate selection or completion.

## 12. Next Use

This document is the baseline for redesigning the wizard.

Recommended rollout:
1. Apply these principles to the class step first.
2. Validate the patterns in a real step with subclass selection, advanced choices, and sticky navigation.
3. Reuse the validated patterns across the remaining wizard steps.
