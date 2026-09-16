---
description: "Reference for CharacterBuilder API, to_character() output shape, test assertion paths, and internal quirks. Read this before writing data files, effect handlers, or tests."
applyTo: ["modules/character_builder.py", "tests/**/*.py", "data/**/*.json"]
---

# CharacterBuilder API Reference

## Builder Methods

```python
builder = CharacterBuilder(data_dir=None)
builder.set_species("Human") -> bool
builder.set_lineage("Wood Elf", spellcasting_ability="Wisdom") -> bool
builder.set_class("Rogue", level=5) -> bool
builder.set_subclass("Thief") -> bool
builder.set_background("Criminal") -> bool
character = builder.to_character() -> Dict
```

## to_character() Output Keys

### Identity
| Key | Type | Notes |
|---|---|---|
| `name` | str | |
| `class` | str | "Rogue" |
| `subclass` | str | "Thief" |
| `species` | str | "Human" |
| `lineage` | str or None | "Wood Elf" |
| `background` | str | "Criminal" |
| `level` | int | 1–20 |
| `class_data` | dict | Raw class JSON |
| `subclass_data` | dict | Raw subclass JSON |
| `proficiency_bonus` | int | Calculated from level |

### Features
```python
character["features"]["class"]      # List[{name, description, source, level}]
character["features"]["subclass"]   # List[{name, description, source, level}]
character["features"]["species"]    # List[{name, description, source}]
character["features"]["lineage"]    # List[{name, description, source}]
character["features"]["feats"]      # List[{name, description, source}]
```

### Proficiencies
```python
character["proficiencies"]["saving_throws"]  # List[str]: ["Dexterity", "Intelligence"]
character["proficiencies"]["armor"]          # List[str]: ["Light armor"]
character["proficiencies"]["weapons"]        # List[str]: ["Simple weapons"]
character["proficiencies"]["tools"]          # List[str]: ["Thieves' Tools"]
character["proficiencies"]["skills"]         # List[str]: ["Stealth", "Perception"]
character["proficiencies"]["languages"]      # List[str]: ["Common", "Thieves' Cant"]

# Convenience aliases (flattened at top level):
character["languages"]              # same as proficiencies.languages
character["skill_proficiencies"]    # same as proficiencies.skills
character["weapon_proficiencies"]   # same as proficiencies.weapons
character["armor_proficiencies"]    # same as proficiencies.armor
character["tool_proficiencies"]     # same as proficiencies.tools
```

### Spellcasting Stats
```python
stats = character["spellcasting_stats"]
stats["has_spellcasting"]       # bool
stats["spellcasting_ability"]   # "Intelligence", "Wisdom", etc.
stats["spellcasting_modifier"]  # int
stats["spell_save_dc"]          # 8 + prof + mod
stats["spell_attack_bonus"]     # prof + mod
stats["max_cantrips_prepared"]  # int (total cantrip slots)
stats["max_spells_prepared"]    # int (total prepared spell slots)
```

### Spell Slots
```python
character["spell_slots"]  # {"1st": 2, "2nd": 0, ...} — only non-zero keys present
```

### Combat
```python
character["combat"]["hit_points"]["maximum"]  # int
character["combat"]["armor_class"]            # int (best option)
character["combat"]["initiative"]             # int (Dex mod)
character["combat"]["speed"]                  # int
character["combat"]["passive_perception"]     # int
```

### AC Options
```python
character["ac_options"]  # List[{ac, armor, shield, formula, notes, equipped_armor}]
```

### Attacks
```python
character["attacks"]  # List[{weapon_name, attack_bonus, damage, damage_type, ...}]
```

### Skills
```python
character["skills"]["stealth"]  # {ability, ability_modifier, proficient, expert, bonus}
```

### Effects (exported)
```python
character["effects"]  # List[{type, source, source_type, ...effect fields}]
```

### Other
```python
character["resistances"]           # List[str]
character["condition_immunities"]  # List[str]
character["save_advantages"]       # List[{abilities, display, condition}]
character["skill_expertise"]       # List[str]
character["speed"]                 # int
character["darkvision"]            # int (0 if none)
```

## Internal Quirks

### Feature Deduplication
Features are deduped by `startswith(trait_name)`. If the same feature name appears at multiple levels (e.g., Rogue "Expertise" at L1 and L6), only the first is added to the feature list. **Effects are still applied for both.**

### "Choose" Skip Logic
Features whose description starts with `"Choose"` are **skipped** (not displayed). Effects are still applied if present. This means features like "Rogue Subclass: Choose your archetype" won't appear in `character["features"]["class"]`.

### Subclass Spellcasting
For subclass casters (Eldritch Knight, Arcane Trickster), the subclass JSON must include:
```json
{
  "spellcasting_ability": "Intelligence",
  "spell_list": "Wizard",
  "cantrips_by_level": {"3": 2, "10": 3, ...},
  "prepared_spells_by_level": {"3": 3, "4": 4, ...},
  "spell_slots_by_level": {"3": [2,0,0,0,0,0,0,0,0], ...}
}
```
The builder checks `subclass_data.get("spellcasting_ability")` when the class itself has none.

## Test Assertion Patterns

```python
from modules.character_builder import CharacterBuilder

def build_rogue(level, subclass=None):
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_background("Criminal")
    builder.set_class("Rogue", level)
    if subclass and level >= 3:
        builder.set_subclass(subclass)
    return builder.to_character()

# Feature presence
names = [f["name"] for f in character["features"]["class"]]
assert "Sneak Attack" in names

# Proficiencies
assert "Dexterity" in character["proficiencies"]["saving_throws"]
assert "Light armor" in character["proficiencies"]["armor"]
assert "Thieves' Tools" in character["proficiencies"]["tools"]
assert "Thieves' Cant" in character["proficiencies"]["languages"]

# Spellcasting (subclass casters)
stats = character["spellcasting_stats"]
assert stats["has_spellcasting"] is True
assert stats["spellcasting_ability"] == "Intelligence"
assert stats["max_cantrips_prepared"] == 2
assert character["spell_slots"]["1st"] == 2

# Effects
effects = character.get("effects", [])
tool_grants = [e for e in effects if e["type"] == "grant_tool_proficiency"]
assert any("Disguise Kit" in e["effect"]["tools"] for e in tool_grants)
```
