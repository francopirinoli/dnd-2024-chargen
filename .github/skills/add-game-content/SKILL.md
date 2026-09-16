---
name: add-game-content
description: "Add a batch of D&D game content: multiple subclasses, backgrounds, feats, or spells. Use when populating missing data for an entire category or class."
---

# Add Game Content

Workflow for adding a batch of game content (e.g., all subclasses for a class, missing backgrounds, feat categories).

## When to Use

- Populating all subclasses for a class
- Adding missing backgrounds (Artisan, Farmer, Guard, etc.)
- Creating spell definition files
- Adding general feat data

## Procedure

### 1. Fetch Wiki Data

Ensure wiki cache has the needed content:

```bash
python update_classes.py --class ranger
# Subclasses auto-fetched if class is fetched
```

For spell lists:
```bash
python update_spells.py --class sorcerer
# Generates {class}_cantrips.json, {class}_spells.json, and class_lists/{class}.json
```

### 2. Create Data Files from Templates

Use these templates as starting points:

#### Class Template
See [data file templates](./references/data-file-templates.md).

### 3. Add Effects

For each feature with mechanical benefits, add an `effects` array. Reference the effect type catalog in `.github/skills/implement-feature/references/effect-type-catalog.md`.

### 4. Validate

```bash
python validate_data.py
```

### 5. Write Tests

Create at least one integration test per class/species added:

```python
def test_new_subclass_features():
    builder = CharacterBuilder()
    builder.apply_choices({...})
    character = builder.to_character()
    # Assert key features are present
```

### 6. Run Full Suite

```bash
pytest tests/ -x -q --tb=short
```

## Reference Files

- [Data File Templates](./references/data-file-templates.md)
- `models/class_schema.json`, `models/subclass_schema.json` — Schemas
