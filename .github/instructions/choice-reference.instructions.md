---
description: "Use when implementing or modifying character choices: spell selection, feat options, fighting style picks, maneuver selections, skill choices, or any player decision in JSON data or CharacterBuilder choice processing."
applyTo: ["data/**/*.json", "modules/character_builder.py"]
---

# Choice Reference System

All player choices are defined declaratively in JSON and resolved generically at runtime. **Never hardcode choice logic.**

## Choice Object Schema

```json
{
  "Feature Name": {
    "description": "...",
    "choices": {
      "type": "select_multiple | select_single | select_or_replace",
      "count": 3,
      "name": "choice_identifier",
      "source": {
        "type": "internal | external | external_dynamic | fixed_list",
        "list": "list_name",
        "file": "path/to/file.json",
        "file_pattern": "spells/{class}_spells.json",
        "depends_on": "previous_choice_name",
        "options": ["Option1", "Option2"]
      },
      "restrictions": ["Abjuration", "Evocation"],
      "optional": true,
      "additional_choices_by_level": {
        "7": {"count": 2, "replace_allowed": true}
      }
    }
  }
}
```

## Source Types

| Type | When to Use | Key Fields |
|---|---|---|
| `internal` | Options in the same JSON file | `list` — key name in same file |
| `external` | Options in a specific file | `file`, `list` |
| `external_dynamic` | File depends on prior choice | `file_pattern`, `depends_on`, `list` |
| `fixed_list` | Small inline list | `options` (array) |

## Examples

### Internal Source — Battle Master Maneuvers
```json
{
  "Combat Superiority": {
    "description": "You learn three maneuvers.",
    "choices": {
      "type": "select_multiple",
      "count": 3,
      "name": "maneuvers",
      "source": {"type": "internal", "list": "maneuvers"},
      "additional_choices_by_level": {
        "7": {"count": 2, "replace_allowed": true},
        "10": {"count": 2, "replace_allowed": true}
      }
    }
  },
  "maneuvers": {
    "Disarming Attack": "When you hit a creature...",
    "Feinting Attack": "As a Bonus Action..."
  }
}
```

### External Source — Fighting Styles
```json
{
  "Fighting Style": {
    "description": "You adopt a particular style.",
    "choices": {
      "type": "select_single",
      "count": 1,
      "name": "fighting_style",
      "source": {
        "type": "external",
        "file": "fighting_styles.json",
        "list": "fighting_styles"
      }
    }
  }
}
```

### External Dynamic — Magic Initiate
```json
{
  "choices": [
    {
      "type": "select_single",
      "name": "spell_list_class",
      "source": {"type": "fixed_list", "options": ["Wizard", "Cleric", "Druid"]}
    },
    {
      "type": "select_multiple",
      "count": 2,
      "name": "cantrips",
      "source": {
        "type": "external_dynamic",
        "file_pattern": "spells/{spell_list_class}_cantrips.json",
        "list": "cantrips",
        "depends_on": "spell_list_class"
      }
    }
  ]
}
```

## Level Progression

Use `additional_choices_by_level` for features that grant more options at higher levels:

```json
"additional_choices_by_level": {
  "7": {"count": 2, "replace_allowed": true},
  "10": {"count": 2, "replace_allowed": true},
  "15": {"count": 2, "replace_allowed": true}
}
```

- `count`: Additional selections at that level
- `replace_allowed`: Whether existing choices can be swapped

## Rules

1. All choice behavior defined in JSON — no hardcoded logic
2. External spell/maneuver lists in separate files for reuse across classes
3. Dynamic resolution based on `depends_on` previous choice
4. Restrictions filter available options (e.g., spell school restrictions)
5. `select_or_replace` allows swapping existing choices at level-up

## Storage shape: grouped choices MUST be nested

Grouped choice payloads in `choices_made` are **nested objects keyed by group name**, never flat top-level keys (audit P0-1). The canonical nested keys are:

- `species_trait_choices` — `{ "<Trait Name>": "<picked value>", ... }`
- `spell_selections` — `{ "cantrips": [...], "spells": [...], ... }`
- `weapon_mastery_selections`, `eldritch_invocation_selections`, etc.

Do **not** write trait, spell, or other grouped picks as flat top-level keys (e.g. `choices_made["Draconic Ancestry"] = "Red (Fire)"`). Flat shapes silently collide with other top-level keys, drift from the typed `ChoicesMade` interface, and bypass the canonical reader.

```jsonc
// ❌ Forbidden — flat top-level trait keys
{ "species": "Dragonborn", "Draconic Ancestry": "Red (Fire)" }

// ✅ Canonical — nested under species_trait_choices
{
  "species": "Dragonborn",
  "species_trait_choices": { "Draconic Ancestry": "Red (Fire)" }
}
```

For backwards compatibility with saved characters, `CharacterBuilder.apply_choices` lifts legacy flat trait keys into `species_trait_choices` via `_normalize_species_trait_choices`. New writers (frontend, tests, exporters) MUST emit the nested shape directly.

