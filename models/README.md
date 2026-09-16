# Data Models for D&D 2024 Character Creator

This directory contains JSON Schema definitions that enforce consistent data structure across all game data files.

## Purpose

Data models ensure:
1. **Consistency**: All class/subclass files follow the same structure
2. **Validation**: Data can be validated before use
3. **Documentation**: Clear reference for data file format
4. **AI Guidance**: Copilot follows these schemas when generating data

## Schema Files

### [class_schema.json](class_schema.json)
Defines the structure for base class files in `data/classes/`

**Required Fields:**
- `name`: Class name (string)
- `description`: Class description (string)
- `hit_die`: Hit die size (6, 8, 10, or 12)
- `primary_ability`: Primary ability score
- `saving_throw_proficiencies`: Array of 2 abilities
- `subclass_selection_level`: Level when subclass is chosen (1-3)
- `proficiency_bonus_by_level`: Object with levels 1-20
- `features_by_level`: Object mapping levels to feature objects (same format as subclasses)

**Optional Fields (for spellcasters):**
- `spellcasting_ability`: Casting ability score
- `cantrips_by_level`: Cantrip progression
- `prepared_spells_by_level`: Prepared spell progression
- `spell_slots_by_level`: Spell slot progression (9-element arrays)

**Example:**
```json
{
  "name": "Wizard",
  "description": "Masters of arcane magic...",
  "hit_die": 6,
  "primary_ability": "Intelligence",
  "saving_throw_proficiencies": ["Intelligence", "Wisdom"],
  "subclass_selection_level": 3,
  "features_by_level": {
    "1": {
      "Spellcasting": "Cast spells using Intelligence as your spellcasting ability.",
      "Ritual Adept": "Cast any Ritual spell from your spellbook without preparing it.",
      "Arcane Recovery": "Regain spell slots equal to half your Wizard level on Short Rest."
    },
    "2": {
      "Scholar": "Gain Expertise in one skill: Arcana, History, Investigation, Medicine, Nature, or Religion."
    }
  },
  "spell_slots_by_level": {
    "1": [2, 0, 0, 0, 0, 0, 0, 0, 0],
    "2": [3, 0, 0, 0, 0, 0, 0, 0, 0]
  }
}
```

### [subclass_schema.json](subclass_schema.json)
Defines the structure for subclass files in `data/subclasses/{class}/`

**Required Fields:**
- `name`: Subclass name (string)
- `class`: Parent class name (string)
- `description`: Subclass description (string)
- `source`: Source book (string)
- `features_by_level`: Object mapping levels to feature objects

**Critical Structure Rule:**
`features_by_level` must use this structure:
```json
{
  "features_by_level": {
    "3": {
      "Feature Name 1": "Description text",
      "Feature Name 2": "Description text"
    }
  }
}
```

❌ **WRONG** (arrays not allowed):
```json
{
  "features_by_level": {
    "3": ["Feature Name 1", "Feature Name 2"]
  }
}
```

**Example:**
```json
{
  "name": "Oath of Devotion",
  "class": "Paladin",
  "description": "Paladins devoted to justice and order",
  "source": "Player's Handbook 2024",
  "features_by_level": {
    "3": {
      "Sacred Weapon": "Use Channel Divinity to make weapon radiant.",
      "Oath Spells": {
        "description": "Always have certain spells prepared",
        "spells": {
          "3": ["Protection from Evil and Good", "Shield of Faith"]
        }
      }
    },
    "7": {
      "Aura of Devotion": "You and allies within 10 feet are immune to Charmed."
    }
  }
}
```

## Validation

To validate a data file against its schema:

```bash
# Install jsonschema validator
pip install jsonschema

# Validate a class file
python -c "
import json
import jsonschema

with open('models/class_schema.json') as f:
    schema = json.load(f)

with open('data/classes/wizard.json') as f:
    data = json.load(f)

jsonschema.validate(data, schema)
print('✅ Valid!')
"
```

## Usage Guidelines

### When Creating New Data Files

1. **Check the schema first**: Review the appropriate schema file
2. **Follow required fields**: Ensure all required fields are present
3. **Match data types**: Use correct types (string, integer, array, object)
4. **Validate after creation**: Run validation to catch errors early

### When Updating Schemas

1. **Update the schema file**: Modify `class_schema.json` or `subclass_schema.json`
2. **Update this README**: Document any breaking changes
3. **Update Copilot instructions**: Ensure `.github/copilot-instructions.md` references the new schema
4. **Migrate existing files**: Update any data files that don't match the new schema

## Common Pitfalls

### ❌ Class Features as Arrays (OLD FORMAT - DO NOT USE)
```json
{
  "features_by_level": {
    "1": ["Feature 1", "Feature 2"]  // WRONG! This is deprecated
  }
}
```

### ✅ Class Features as Objects (CORRECT FORMAT)
```json
{
  "features_by_level": {
    "1": {
      "Feature 1": "Description of feature 1",
      "Feature 2": "Description of feature 2"
    }
  }
}
```

### ✅ Both Classes and Subclasses Use Same Format
```json
// Classes and subclasses both use this format:
{
  "features_by_level": {
    "3": {
      "Feature Name": "Description"
    }
  }
}
```

### ❌ Missing Required Fields
```json
{
  "name": "Wizard"
  // Missing: description, hit_die, primary_ability, etc.
}
```

### ✅ All Required Fields Present
```json
{
  "name": "Wizard",
  "description": "Masters of arcane magic",
  "hit_die": 6,
  "primary_ability": "Intelligence",
  "saving_throw_proficiencies": ["Intelligence", "Wisdom"],
  "subclass_selection_level": 3,
  "proficiency_bonus_by_level": { "1": 2, "2": 2, ... },
  "features_by_level": { 
    "1": {
      "Spellcasting": "Cast spells using Intelligence.",
      "Arcane Recovery": "Regain spell slots on Short Rest."
    }
  }
}
```

## Integration with Development Workflow

1. **AI Code Generation**: Copilot uses these schemas to generate consistent data
2. **Data Transformation**: Scripts transforming wiki data should output to these schemas
3. **Application Code**: Character creator expects data in these formats
4. **Testing**: Validation tests ensure data integrity

## See Also

- [.github/copilot-instructions.md](../.github/copilot-instructions.md) - AI coding guidelines
- [DATA_PIPELINE.md](../DATA_PIPELINE.md) - Data transformation workflow
- [wiki_data/README.md](../wiki_data/README.md) - Wiki data caching
