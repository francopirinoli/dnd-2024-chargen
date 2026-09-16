---
name: dnd-rules-reference
description: "Reference skill. Where to find authoritative D&D 2024 rules and how the project models them. Use when verifying a rule, classifying a feature, or deciding whether a behaviour is RAW."
---

# D&D 2024 Rules Reference

This project implements **D&D 2024 (One D&D)**, not 2014. When rules conflict, 2024 wins.

## Source Hierarchy (always check in this order)

1. **`data/`** — application-ready JSON. If a rule is encoded here as effects/choices, this is the operative interpretation for the codebase.
2. **`wiki_data/`** — cached scrapes of http://dnd2024.wikidot.com/. Each cache file has `content.text` (clean) and `content.html` (raw).
3. **http://dnd2024.wikidot.com/** — live wiki. Only fetch when the cache is missing; then cache it via the `update_*.py` scripts.

If a rule is not in any of these, ask the user — never invent.

## Key 2024 vs 2014 Differences

| Topic                          | 2024 (correct)                                          |
|--------------------------------|---------------------------------------------------------|
| Ability score increases        | Granted by **backgrounds**, not species                 |
| Dwarf subraces                 | **Removed** — single Dwarf species, no Hill/Mountain    |
| Backgrounds                    | Provide ASIs, an Origin Feat, two skills, one tool, one language |
| Origin Feats                   | New category, granted at level 1 by background          |
| Weapon Mastery                 | New mechanic; weapons have a `mastery` property         |
| Cunning Strike (Rogue)         | Replaces several 2014 Rogue features                    |
| Spellcasting prep              | Most prepared casters now prepare from a known list     |
| Class features                 | Many shifted levels; verify with wiki cache             |

## Where Each Rule Type Lives in the Project

| Rule type                | Data file(s)                                  | Schema                       |
|--------------------------|-----------------------------------------------|------------------------------|
| Class features           | `data/classes/<class>.json`                   | `models/class_schema.json`   |
| Subclass features        | `data/subclasses/<class>/<subclass>.json`     | `models/subclass_schema.json`|
| Species traits           | `data/species/<species>.json`                 | (see `models/`)              |
| Species variants/lineages| `data/species_variants/<species>.json`        | (see `models/`)              |
| Backgrounds              | `data/backgrounds/<background>.json`          | (see `models/`)              |
| Spells                   | `data/spells/<class>.json` and definitions    | (see `models/`)              |
| Feats (general/origin)   | `data/general_feats.json`, `data/origin_feats.json` |                        |
| Equipment                | `data/equipment/*.json`                       |                              |
| Eldritch invocations     | `data/eldritch_invocations.json`              |                              |
| Fighting styles          | `data/fighting_styles.json`                   |                              |

## How Rules Become Mechanics

Mechanical effects are **never hardcoded** in Python. Each feature/trait/feat carries an `effects` array that the `CharacterBuilder._apply_effect()` dispatcher reads.

- New mechanic? Add or extend an effect type. See `.github/instructions/effects-system.instructions.md` and `docs/FEATURE_EFFECTS.md`.
- Player choice required? Use the Choice Reference System. See `.github/instructions/choice-reference.instructions.md`.

## Fetching Cache

```bash
python update_classes.py --class <name>
python update_species.py --species <name>
python update_spells.py --class <name>
```

These populate `wiki_data/`. They never write to `data/` — JSON authoring is a separate manual step.

## Quick Sanity Checks

- "Does this species give an ASI?" → No (2024). ASIs come from backgrounds.
- "Does Hill Dwarf get +1 Wis?" → Hill Dwarf does not exist in 2024.
- "Can a Fighter pick a Fighting Style at level 1?" → Yes, via class feature; encode as a choice with `effect_type: "grant_fighting_style"`.
- "Is this calculation in the API response?" → It must be, before the UI displays it.
