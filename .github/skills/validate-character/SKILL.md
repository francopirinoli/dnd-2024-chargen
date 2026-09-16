---
name: validate-character
description: "Validate a complete character build by rebuilding from choices and checking all calculated values: HP, AC, skills, proficiencies, spells, effects. Use when verifying character correctness or testing after changes."
---

# Validate Character

Manual end-to-end sanity check: build a character from raw choices and confirm the computed output is correct. Use this when an automated test would be heavy-handed (exploratory check after a refactor, verifying a bug fix in context, eyeballing a new build).

For canonical assertion paths into the response, see `.github/instructions/character-builder-api.instructions.md` and `docs/APIContract.md`. Do not duplicate those shapes here — they drift.

## When to Use

- After implementing a feature, to verify it lights up in a full build.
- Confirming a bug fix resolved the user-visible calculation.
- Spot-checking a new class/species/background combo end-to-end.
- Validating that a `test_characters/*.json` reference is still correct.

For repeatable regression coverage, write a pytest test instead (delegate to the `test` agent).

## Procedure

### 1. Define or load choices

Either reuse a reference build or compose a minimal `choices_made` dict:

- `test_characters/test_cleric_dwarf.json`
- `test_characters/test_figher_wood_elf.json`

Required keys mirror the wizard: `character_name`, `level`, `species`, `class`, `subclass` (when relevant), `background`, `ability_scores`, `background_bonuses`. Add choice keys (`origin_feat`, `fighting_style`, `spells`, `cantrips`, `equipment_selections`, …) as the build demands.

### 2. Build via the API or in Python

API (matches what the React SPA does):

```bash
curl -X POST http://localhost:5000/api/v1/character/build \
  -H 'Content-Type: application/json' \
  -d '{"choices_made": {...}}'
```

Python:

```python
from modules.character_builder import CharacterBuilder

builder = CharacterBuilder()
builder.apply_choices(choices)
character = builder.to_character()
```

### 3. Walk the output

Read the character dict and confirm each area looks right. Use `.github/instructions/character-builder-api.instructions.md` to find the field paths. Areas to scan:

- Identity & level (`name`, `level`, `class`, `subclass`, `species`, `background`)
- Ability scores and modifiers
- Combat block (HP, AC options, initiative, speed)
- Saving throws and skills (proficient/expertise flags)
- Proficiencies (armor, weapons, tools, languages)
- Attacks and attack combinations
- Spellcasting (slots, prepared/known, cantrips, DC, attack mod)
- Effects array (resistances, immunities, save advantages, …)
- Selection echoes (`spell_selections`, `weapon_mastery_selections`, `eldritch_invocation_selections` inside `choices_made`)

### 4. Compare against a reference (optional)

If a baseline file exists (e.g. in `test_characters/`), diff the two dicts with `json.dumps(..., sort_keys=True, indent=2)` and a text diff tool, or assert section-by-section in a REPL.

### 5. Report

Summarise:
- Areas checked.
- Discrepancies: expected vs actual, with the field path.
- Suggested next step (file an issue via `issue-tracker`, hand off to `backend` for a fix, or write a regression test via `test`).

## Related

- `.github/instructions/character-builder-api.instructions.md` — authoritative output paths
- `docs/APIContract.md` — `Character` response shape
- `.github/skills/implement-feature/SKILL.md` — when validation surfaces a missing/incorrect feature

## Round-trip equality check

After validating the character, run:

```bash
pytest tests/integration/test_rebuild_equality.py -v
```

A passing run confirms that re-building from the same `choices_made` produces byte-equal output. If the test fails, the character's `choices_made` dict contains keys or values that produce non-deterministic output — investigate `apply_choices()` pass ordering.
