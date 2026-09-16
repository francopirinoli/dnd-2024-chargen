---
name: file-issue
description: "Create a GitHub Issue from a casual bug report or feature request. Gathers context from the codebase, identifies affected files, and writes a structured issue. Use when the user describes a bug, missing feature, or inaccuracy conversationally."
---

# File Issue

Create a structured GitHub Issue from a casual user description. The agent enriches the report with codebase context before filing.

## When to Use

- User describes a bug they found while testing (e.g., "monk speed bonus seems wrong at level 10")
- User reports a missing feature (e.g., "Evasion doesn't show up on the character sheet")
- User notes a D&D rules inaccuracy (e.g., "Stunning Strike DC should use Wisdom, not Charisma")
- User says "file an issue", "log this bug", "track this", etc.

## Procedure

### 1. Parse the User's Description

Extract from the conversational input:
- **What's wrong or missing** — the core problem
- **Class/subclass/species/feature involved** — if mentioned
- **Level** — if mentioned
- **Expected vs actual behavior** — if described

If details are ambiguous, ask ONE clarifying question at most. Prefer inferring from context over asking.

### 2. Gather Codebase Context

Based on what's affected, inspect the relevant files:

```bash
# For class features
cat data/classes/{class_name}.json | python -m json.tool

# For subclass features
cat data/subclasses/{class_name}/{subclass_slug}.json | python -m json.tool

# For species
cat data/species/{species_name}.json | python -m json.tool

# Check effect handlers if relevant
grep -n "effect_type_name" modules/character_builder.py
```

Identify:
- Which data file(s) are affected
- Whether the feature has effects or is plain text
- What the current behavior produces (build a test character if needed)
- What level(s) are affected

### 3. Check for Duplicates

Search existing issues to avoid duplicates:

```
mcp_github_search_issues(query="repo:QuickNS/dnd-character-creator is:open {feature_name_or_keyword}")
```

If a matching issue exists, tell the user and optionally add a comment to the existing issue instead.

### 4. Determine Labels

- `bug` — Something that exists but is wrong (incorrect values, broken logic)
- `enhancement` — Something missing that should be added (missing effects, missing features)
- `copilot` — **Always added** so the Copilot coding agent picks up the issue automatically

### 5. Create the Issue

Use the standard title format: `[ClassName] Short description`
For subclasses: `[ClassName/SubclassName] Short description`
For species: `[SpeciesName] Short description`
For non-class issues: `Short description` (no prefix)

```
mcp_github_issue_write(
  owner="QuickNS",
  repo="dnd-character-creator",
  method="create",
  title="[Monk] Martial Arts die not scaling at level 5",
  labels=["bug", "copilot"],
  body=<structured body>
)
```

Then assign Copilot to the issue so the coding agent starts working on it:

```
mcp_github_assign_copilot_to_issue(
  owner="QuickNS",
  repo="dnd-character-creator",
  issueNumber=<created issue number>
)
```

### 6. Issue Body Template

```markdown
## Issue Type
Bug | Missing Feature | Inaccuracy

## Severity
High | Medium | Low

## Class / Feature
**Class:** {ClassName}
**Subclass:** {SubclassName} (if applicable)
**Feature:** {FeatureName} (Level {N})
**Affected Levels:** {comma-separated}

## Description
{Clear explanation of the problem, written from the codebase context gathered in step 2}

## Current Behavior
{What actually happens — include JSON snippets or calculated values if relevant}

## Expected Behavior
{What should happen according to D&D 2024 rules}

## Files
- `data/classes/{class}.json` — {what needs to change}
- `modules/character_builder.py` — {if effect handler changes needed}

## Reproduction
{If a bug: steps or character choices to reproduce}
```

### Severity Guidelines

- **High**: Character sheet shows wrong numbers (HP, AC, attack rolls, save DCs), or a core feature is completely missing
- **Medium**: A feature exists but lacks structured effects, or a secondary calculation is wrong
- **Low**: Cosmetic issues, missing flavor text, or features that don't have mechanical impact on the sheet

### 7. Confirm to User

After creating, report back:
```
Filed #{number}: [ClassName] Title
https://github.com/QuickNS/dnd-character-creator/issues/{number}
Copilot has been assigned and will start working on it.
```

## Examples

**User says:** "the monk's speed at level 10 should be +20 but I'm seeing +15"

**Agent does:**
1. Reads `data/classes/monk.json` → finds Unarmored Movement effects at levels 2/6/10
2. Checks level 10 effect: `increase_speed` value is 5 (incremental), level 6 is 5, level 2 is 10 → total +20
3. Builds a test character at level 10, checks calculated speed
4. Identifies the actual discrepancy
5. Files: `[Monk] Unarmored Movement speed incorrect at level 10` with full context

**User says:** "Warrior of Shadow should get Shadow Arts spells but I don't see them"

**Agent does:**
1. Reads `data/subclasses/monk/warrior_of_shadow.json`
2. Checks if Shadow Arts feature has `grant_spell` effects
3. Cross-references with wiki data
4. Files: `[Monk/Warrior of Shadow] Shadow Arts spells not granted` with expected spell list
