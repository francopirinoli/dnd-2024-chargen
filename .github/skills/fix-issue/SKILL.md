---
name: fix-issue
description: "Pick up and resolve bugs, missing features, or inaccuracies tracked as GitHub Issues. Use when fixing known problems for classes, subclasses, species, feats, backgrounds, or application logic."
---

# Fix Issue

Workflow for resolving issues (bugs, missing features, inaccuracies) tracked as GitHub Issues in `QuickNS/dnd-character-creator`.

## When to Use

- When asked to fix bugs or missing features for any game content or application logic
- When asked "what issues are open?" and then to resolve them
- When assigned a specific GitHub Issue number

## Issue Conventions

Title formats by category:
- Classes: `[ClassName] Short description`
- Subclasses: `[ClassName/SubclassName] Short description`
- Species: `[SpeciesName] Short description`
- Feats / App / Other: `Short description` (no prefix)

Labels used:
- `bug` — Something is broken or incorrect
- `enhancement` — Missing feature or improvement needed

The issue body contains structured sections: Issue Type, Severity, Class/Feature, Affected Levels, Description, Current Behavior, Expected Behavior, and Files.

## Procedure

### 1. Find Open Issues

Use the GitHub MCP tools to list or search issues:

```
mcp_github_list_issues(owner="QuickNS", repo="dnd-character-creator", state="OPEN")
```

Or search for a specific category:
```
mcp_github_search_issues(query="repo:QuickNS/dnd-character-creator is:open [Monk]")
mcp_github_search_issues(query="repo:QuickNS/dnd-character-creator is:open [Elf]")
mcp_github_search_issues(query="repo:QuickNS/dnd-character-creator is:open feat")
```

Pick the highest-severity open issue to fix first (severity is noted in the issue body).

### 2. Read the Issue

```
mcp_github_issue_read(owner="QuickNS", repo="dnd-character-creator", issueNumber=N)
```

Parse the issue body to understand: affected area, current vs expected behavior, and which files to change.

### 3. Determine Issue Category

Classify the issue to know which files and validation steps apply:

| Category | Data files | Wiki source | Validate with |
|----------|-----------|-------------|---------------|
| **Class** | `data/classes/{name}.json` | `wiki_data/classes/{name}.json` | `validate_data.py` + `pytest` |
| **Subclass** | `data/subclasses/{class}/{name}.json` | `wiki_data/subclasses/{class}/{name}.json` | `validate_data.py` + `pytest` |
| **Species** | `data/species/{name}.json` | `wiki_data/species/{name}.json` | `validate_data.py` + `pytest` |
| **Species variant** | `data/species_variants/{species}/{name}.json` | `wiki_data/species/{parent}.json` | `validate_data.py` + `pytest` |
| **Background** | `data/backgrounds/{name}.json` | `wiki_data/backgrounds/{name}.json` | `validate_data.py` + `pytest` |
| **Feat** | `data/general_feats.json` or `data/origin_feats.json` | `wiki_data/feats/{name}.json` | `validate_data.py` + `pytest` |
| **Spell** | `data/spells/{level}/` | `wiki_data/spells/{name}.json` | `validate_data.py` + `pytest` |
| **Application (backend)** | `modules/`, `routes/api/`, `routes/` (legacy), `templates/` (legacy) | N/A | `pytest` |
| **Application (SPA)** | `frontend/src/` (React + TypeScript) | N/A | `cd frontend && npm run typecheck && npm run build` |
| **Equipment** | `data/equipment/` | N/A | `validate_data.py` + `pytest` |

### 4. Create a Feature Branch

Create a branch from `main` for this fix. Use the naming convention `fix/issue-N-short-description`:

```bash
git checkout main && git pull
git checkout -b fix/issue-N-short-description
```

### 5. Verify Against Source of Truth

**For game content issues** — check wiki data to confirm correct D&D 2024 rules:

```bash
# Check cache for the relevant category
cat wiki_data/{category}/{name}.json | python -m json.tool | head -100

# If missing, fetch it
python update_classes.py --class {class_name}      # classes/subclasses
python update_species.py --species {species_name}   # species
python update_spells.py --class {class_name}        # spell lists
```

Parse `content.text` to understand the feature's intended mechanics. Never guess — the wiki is the source of truth.

**For application issues** — read the affected modules/routes and understand the current logic before changing it.

### 6. Fix the Issue

Depending on issue type and category:

**Game content — `enhancement` (missing feature)**: Add or update effects in the relevant JSON:
```json
"Feature Name": {
  "description": "...",
  "effects": [
    {"type": "...", ...}
  ]
}
```

**Game content — `bug`**: Fix the incorrect data or effect in the JSON. May also require fixing effect handlers in `modules/character_builder.py` → `_apply_effect()`.

**Application — `bug`**: Fix the logic where it lives:
- Calculation/data bugs → `modules/character_builder.py` (and friends). All math must stay here.
- REST API shape bugs → `routes/api/`. Keep these stateless and JSON-only.
- New SPA UI is the primary surface — fix it under `frontend/src/`. Remember the SPA only consumes `/api/v1/*`; it never recalculates.

**Application — `enhancement`**: Implement the feature following existing patterns. If a new effect type is needed, add a handler in `_apply_effect()` and document it in `docs/FEATURE_EFFECTS.md`. New UI features go into `frontend/src/`, not the legacy templates.

### 7. Validate

```bash
python validate_data.py          # skip for pure application issues
pytest tests/ -x -q --tb=short
```

### 8. Write or Update Tests

Every fix should have a test proving it works. Follow the patterns in `tests/`:

```python
from modules.character_builder import CharacterBuilder

def test_feature_name_effect():
    """Regression test for GitHub Issue #N: title"""
    builder = CharacterBuilder()
    builder.apply_choices({
        "character_name": "Test",
        "level": ...,
        "class": "...",
        ...
    })
    character = builder.to_character()
    # Assert the fix is correct
    assert ...
```

For application issues, write tests appropriate to the fix (route tests, unit tests, etc.).

### 9. Commit, Push, and Create a Pull Request

Commit the changes and push the branch:

```bash
git add -A
git commit -m "Fix #N: short description"
git push -u origin fix/issue-N-short-description
```

Create a pull request linking the issue:

```
mcp_github_create_pull_request(
    owner="QuickNS",
    repo="dnd-character-creator",
    head="fix/issue-N-short-description",
    base="main",
    title="Fix #N: short description",
    body="## Summary\n\n{what was changed and why}\n\nCloses #N\n\n## Changes\n- {file}: {what changed}\n\n## Testing\n- All existing tests pass\n- Added: {new test file or function}"
)
```

### 10. Present Summary and Ask for Confirmation

Report what was fixed and **ask the user to confirm before merging**:

```
PR #{pr_number} created for issue #N — {title}
  - Branch: fix/issue-N-short-description
  - Changed: {files changed}
  - Added: {new test file or function}
  - Tests: all passing

Please review the PR. Ready to merge and close issue #N?
```

**Do NOT merge or close until the user explicitly confirms.** Wait for approval.

### 11. Merge and Close

Only after user confirmation:

1. Merge the PR:
```
mcp_github_merge_pull_request(owner="QuickNS", repo="dnd-character-creator", pullNumber=PR_NUMBER)
```

2. Close the issue with a comment:
```
mcp_github_add_issue_comment(owner="QuickNS", repo="dnd-character-creator", issue_number=N,
    body="Fixed in PR #PR_NUMBER.")
mcp_github_issue_write(owner="QuickNS", repo="dnd-character-creator", issue_number=N,
    method="update", state="closed", state_reason="completed")
```

3. Switch back to main locally:
```bash
git checkout main && git pull
```

## Tips

- Fix one issue at a time. Run tests between each fix.
- For missing feature issues, use the implement-feature skill's effect mapping table to choose the right effect types.
- When an issue requires a new effect type, also update `docs/FEATURE_EFFECTS.md` and `_apply_effect()`.
- Subclass issues will have titles like `[Monk/Warrior of Shadow] ...`.
- For species issues, check `data/species_variants/` if the species has lineage variants.
- For feat issues, determine whether it's a general feat or origin feat before editing.
