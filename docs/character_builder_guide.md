# CharacterBuilder - Testing & Development Guide

## Overview

The `CharacterBuilder` class is a **Flask-independent**, **stateful** character creation system that can be used for:
- ✅ Unit testing without web interface
- ✅ Automated testing scripts
- ✅ API endpoints
- ✅ CLI tools
- ✅ Debugging specific character states

## Why CharacterBuilder?

### Before (Problems)
- Had to click through entire web wizard to test features
- Couldn't easily test specific character states
- Hard to reproduce bugs
- No automated testing possible
- Tightly coupled to Flask request state

### After (Solutions)
- Create any character state in seconds with code
- Automated, repeatable tests
- Easy debugging of specific scenarios
- Reusable in multiple contexts
- Clear separation of business logic from web layer

## Quick Start

### Basic Usage

```python
from modules.character_builder import CharacterBuilder

# Create a builder
builder = CharacterBuilder()

# Set species and lineage
builder.set_species("Elf")
builder.set_lineage("Wood Elf", spellcasting_ability="Wisdom")

# Set class and level
builder.set_class("Ranger", level=3)

# Set background
builder.set_background("Sage")

# Set ability scores
builder.set_abilities({
    "STR": 10,
    "DEX": 16,
    "CON": 14,
    "INT": 12,
    "WIS": 15,
    "CHA": 8
})

# Check results
print(builder.get_cantrips())  # ['Druidcraft']
print(builder.get_spells())     # ['Longstrider']
print(builder.character_data['speed'])  # 35
```

### Quick Create (For Testing)

```python
# One-liner character creation
builder = CharacterBuilder.quick_create(
    species="Elf",
    lineage="Wood Elf",
    char_class="Ranger",
    background="Sage",
    abilities={"STR": 10, "DEX": 16, "CON": 14, "INT": 12, "WIS": 15, "CHA": 8},
    level=3,
    spellcasting_ability="Wisdom"
)

# Character is fully built and ready
assert builder.is_complete()
```

## Testing Examples

### Test a Specific Feature

```python
def test_wood_elf_gets_druidcraft():
    """Test that Wood Elf receives Druidcraft cantrip"""
    builder = CharacterBuilder()
    builder.set_species("Elf")
    builder.set_lineage("Wood Elf", spellcasting_ability="Wisdom")
    
    cantrips = builder.get_cantrips()
    assert "Druidcraft" in cantrips
    assert builder.character_data['speed'] == 35
```

### Test Level-Based Features

```python
def test_level_3_spell_grant():
    """Test spells granted at specific levels"""
    # Level 1 - shouldn't have Longstrider
    builder_l1 = CharacterBuilder.quick_create(
        species="Elf",
        lineage="Wood Elf",
        char_class="Ranger",
        background="Sage",
        abilities={"STR": 10, "DEX": 16, "CON": 14, "INT": 12, "WIS": 15, "CHA": 8},
        level=1
    )
    assert "Longstrider" not in builder_l1.get_spells()
    
    # Level 3 - should have Longstrider
    builder_l3 = CharacterBuilder.quick_create(
        species="Elf",
        lineage="Wood Elf",
        char_class="Ranger",
        background="Sage",
        abilities={"STR": 10, "DEX": 16, "CON": 14, "INT": 12, "WIS": 15, "CHA": 8},
        level=3
    )
    assert "Longstrider" in builder_l3.get_spells()
```

### Test Character Export

```python
def test_character_export():
    """Test exporting to different formats"""
    builder = CharacterBuilder.quick_create(
        species="Elf",
        lineage="Wood Elf",
        char_class="Ranger",
        background="Sage",
        abilities={"STR": 10, "DEX": 16, "CON": 14, "INT": 12, "WIS": 15, "CHA": 8}
    )
    
    # Export to JSON
    json_data = builder.to_json()
    
    # Export to Character object
    char_obj = builder.to_character()
    
    # Round-trip test
    builder2 = CharacterBuilder()
    builder2.from_json(json_data)
    assert builder2.character_data['species'] == builder.character_data['species']
```

## Available Methods

### Setup Methods

| Method | Description |
|--------|-------------|
| `set_species(name)` | Set character species |
| `set_lineage(name, spellcasting_ability)` | Set lineage/variant |
| `set_class(name, level)` | Set class and level |
| `set_subclass(name)` | Set subclass |
| `set_background(name)` | Set background |
| `set_abilities(scores)` | Set ability scores |

### Query Methods

| Method | Description |
|--------|-------------|
| `get_cantrips()` | Get list of cantrips |
| `get_spells()` | Get list of known spells |
| `get_proficiencies(type)` | Get proficiencies by type |
| `get_current_step()` | Get current creation step |
| `is_complete()` | Check if character is complete |
| `validate()` | Validate character data |

### Export Methods

| Method | Description |
|--------|-------------|
| `to_json()` | Export as JSON dictionary |
| `to_character()` | Convert to Character object |
| `from_json(data)` | Import from JSON |

### Factory Methods

| Method | Description |
|--------|-------------|
| `quick_create(...)` | Create complete character in one call |

## Running Tests

### Run All Tests
```bash
python test_character_builder.py
```

### Run Specific Test
```python
python -c "from test_character_builder import test_wood_elf_cantrip; test_wood_elf_cantrip()"
```

## Integration with the REST API and the React SPA

The CharacterBuilder is the single source of truth for character calculations.
It is exposed to the React SPA (and any other client) through the stateless
REST API v1 under `/api/v1/*`. The SPA never recomputes anything — it sends
the user's choices and renders the dict that comes back from
`builder.to_character()`.

### Primary endpoint: `POST /api/v1/character/build`

```python
# routes/api/character.py
from flask import Blueprint, jsonify, request
from modules.character_builder import CharacterBuilder

character_bp = Blueprint("character", __name__, url_prefix="/character")
# Mounted under /api/v1 by routes/api/__init__.py

@character_bp.post("/build")
def build_character():
    body = request.get_json(silent=True) or {}
    if "choices_made" not in body:
        return jsonify({"error": "Body must be JSON with 'choices_made'"}), 400

    builder = CharacterBuilder()
    builder.apply_choices(body["choices_made"])
    return jsonify({"character": builder.to_character()})
```

Other API v1 endpoints follow the same pattern:

- `POST /api/v1/character/validate` — per-step validation
- `POST /api/v1/character/preview-step` — preview a single step
- `POST /api/v1/character/derived` — stateless view projections (e.g. `view=damage_cantrips`)
- `GET /api/v1/{classes,species,backgrounds,feats,spells,equipment,reference}` — read-only catalog
- `GET /api/v1/wizard/{steps,dependencies}` — declarative wizard metadata

All of them are stateless — no server-side request state, no cookies, no in-memory state.

## Character Data Structure

The `character_data` dictionary contains:

```python
{
    'name': str,
    'species': str,
    'species_data': dict,
    'lineage': str,
    'lineage_data': dict,
    'class': str,
    'class_data': dict,
    'subclass': str,
    'subclass_data': dict,
    'background': str,
    'background_data': dict,
    'level': int,
    'abilities': {
        'base': dict,
        'species_bonuses': dict,
        'background_bonuses': dict,
        'final': dict
    },
    'features': list,
    'choices_made': dict,
    'spells': {
        'cantrips': list,
        'known': list,
        'prepared': list,
        'slots': dict
    },
    'proficiencies': {
        'armor': list,
        'weapons': list,
        'tools': list,
        'skills': list,
        'languages': list,
        'saving_throws': list
    },
    'speed': int,
    'darkvision': int,
    'resistances': list,
    'immunities': list,
    'step': str  # Current creation step
}
```

## Multiclassing

The builder supports multiclass characters via `choices_made.classes` (an ordered list of `{ class_name, level, subclass? }` rows). The first row is the **primary class**; subsequent rows are **secondary classes**. The rules below match D&D 2024 RAW.

### Hit points

- **Level 1 of the primary class** uses the class's maximum hit die value.
- **Every other level (any class, primary or secondary)** uses that class's hit-die average (`die/2 + 1`).
- The Constitution modifier is added at every level (including level 1).

Worked example — **Fighter 3 / Druid 2**, Constitution 14 (`+2`):

```
Fighter L1 (primary):           10 + 2 = 12   (max d10 + CON)
Fighter L2, L3:           2 × (  6 + 2) = 16   (avg d10 + CON, twice)
Druid   L1, L2:           2 × (  5 + 2) = 14   (avg d8 + CON, twice)
                                        ────
                                          42
```

Worked example — **Paladin 5 / Sorcerer 5**, Constitution 14 (`+2`), with Draconic Resilience (`bonus_hp +1 per_level`, source = Sorcerer):

```
Paladin L1 (primary):           10 + 2 = 12   (max d10 + CON)
Paladin L2–L5:            4 × (  6 + 2) = 32   (avg d10 + CON, four times)
Sorcerer L1–L5:           5 × (  4 + 2) = 30   (avg d6 + CON, five times)
Draconic Resilience:    +1 × (sorcerer level) =  5
                                        ────
                                          79
```

Note that Draconic Resilience scales on the **Sorcerer level (5)**, not on total character level (10) — see [FEATURE_EFFECTS.md](FEATURE_EFFECTS.md#bonus_hp).

### Proficiencies for secondary classes

Only the grants declared in each secondary class's `multiclassing` block (see [DataFiles.md](DataFiles.md#multiclassing-block)) are added, de-duplicated against proficiencies the character already has. **Saving throw proficiencies are never granted by multiclassing.**

Skill and tool grants that require a player choice surface on the build response as `pending_multiclass_skill_choices` and `pending_multiclass_tool_choices`. The player resolves them by posting `choices_made.multiclass_skill_choices = { "<ClassName>": ["<Skill>"] }`. See [APIContract.md](APIContract.md#multiclass-pending-choices).

### Spell slots

Standard (non-Pact) spell slots use the canonical **Multiclass Spellcaster** table. The builder encodes this as `_get_canonical_full_caster_slots_table()`, derived from the full-caster slot progression in the class data files (Wizard / Cleric / Druid / Bard / Sorcerer share the same column).

The effective caster level is:

```
effective_caster_level
    = sum(full-caster levels)
    + ceil(half-caster levels / 2)
    + floor(third-caster levels / 3)
```

> ⚠️ **Half-caster fix**: half-caster contribution now uses `ceil` ("round up") per RAW. A previous implementation used `floor`, which under-counted slots for characters with an odd number of half-caster levels (e.g. Paladin 3 → 2, not 1).

**Pact Magic** is tracked separately from standard slots and is not merged into the multiclass slot table. It is surfaced on the response as `character.pact_magic_slots` with explanatory `character.spell_slot_notes`.

### `per_level` bonus_hp scoping

`bonus_hp` effects with `scaling: "per_level"` are scoped by source:

| Source              | Scales on               |
|---------------------|-------------------------|
| Class feature       | Source class's level    |
| Subclass feature    | Source class's level    |
| Species / lineage   | Total character level   |
| Background / feat   | Total character level   |

This matches the Paladin/Sorcerer example above.

## Effects System

The CharacterBuilder automatically applies effects from species, lineages, classes, and backgrounds:

### Supported Effect Types

- `grant_cantrip` - Grants a cantrip
- `grant_spell` - Grants a spell (with level requirements)
- `grant_weapon_proficiency` - Grants weapon proficiencies
- `grant_armor_proficiency` - Grants armor proficiencies
- `grant_skill_proficiency` - Grants skill proficiencies
- `grant_damage_resistance` - Grants damage resistance
- `grant_darkvision` - Grants or improves darkvision
- `increase_speed` - Increases movement speed

### Effect Application Example

Wood Elf lineage data:
```json
{
  "traits": {
    "Druidcraft": {
      "description": "You know the Druidcraft cantrip.",
      "effects": [
        {
          "type": "grant_cantrip",
          "spell": "Druidcraft"
        }
      ]
    }
  }
}
```

Automatically applied when lineage is set:
```python
builder.set_lineage("Wood Elf")
# Druidcraft is now in builder.get_cantrips()
```

## Best Practices

### ✅ Do This
- Use `quick_create()` for simple test scenarios
- Test specific features in isolation
- Use meaningful test names that describe what's being tested
- Validate character data after building
- Test edge cases (level 1 vs level 3, etc.)

### ❌ Don't Do This
- Don't test through Flask routes if you can test the CharacterBuilder directly
- Don't create incomplete characters without validation
- Don't assume effects are applied - verify them
- Don't test multiple unrelated features in one test

## Troubleshooting

### Issue: Species/lineage not found
**Solution**: Verify JSON files exist in `data/species/` or `data/species_variants/`

### Issue: Effects not applying
**Solution**: Check that the effect type is supported in `_apply_effect()` method

### Issue: Level-based features not working
**Solution**: Ensure effects have `min_level` property and level is set correctly

### Issue: Validation failing
**Solution**: Check required fields are set and ability scores are valid (1-20)

## Next Steps

1. **Add more tests** for other species, classes, and features
2. **Extend the REST API v1** with new stateless endpoints under `routes/api/`
3. **Add CLI tool** for command-line character creation
4. **Build new UI features in the React SPA** (`frontend/src/`) on top of `/api/v1`
5. **Add CI/CD tests** to run automatically on commits

## Resources

- **Test Script**: `test_character_builder.py`
- **Module**: `modules/character_builder.py`
- **Data Files**: `data/species/`, `data/classes/`, `data/backgrounds/`, etc.
- **Effects Documentation**: `docs/FEATURE_EFFECTS.md`

---

**Need help?** Check the test scripts for examples or refer to the CharacterBuilder source code documentation.
