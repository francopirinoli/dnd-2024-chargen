---
description: "Use when writing or modifying pytest tests for the D&D character creator: unit tests, integration tests, character building tests, effects validation, API tests."
applyTo: "tests/**/*.py"
---

# Testing Conventions

## Framework & Config

- **pytest** with `pyproject.toml` config
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration`
- Run: `pytest tests/` or `pytest tests/ -x -q --tb=short` for fast feedback

## Test Directory Structure

```
tests/
├── core/                    # Core module unit tests
│   ├── test_character_builder.py
│   ├── test_spell_management.py
│   ├── test_equipment.py
│   ├── test_serialization.py
│   └── test_flask_integration.py
├── integration/             # Full character recreation tests
│   └── test_character_recreation.py
├── species/                 # Species-specific tests
├── fighter/                 # Class-specific tests
├── cleric/                  # Class-specific tests
└── test_api.py              # API endpoint tests
```

## Building Characters in Tests

Use `CharacterBuilder` directly — never construct character dicts manually:

```python
from modules.character_builder import CharacterBuilder

def test_dwarf_cleric_hp():
    builder = CharacterBuilder()
    builder.apply_choices({
        "character_name": "Test",
        "level": 3,
        "species": "Dwarf",
        "class": "Cleric",
        "subclass": "Light Domain",
        "background": "Acolyte",
        "ability_scores": {
            "Strength": 10, "Dexterity": 12, "Constitution": 14,
            "Intelligence": 8, "Wisdom": 16, "Charisma": 10
        },
        "background_bonuses": {"Wisdom": 2, "Constitution": 1}
    })
    character = builder.to_character()
    
    # Assert on calculated values
    assert character['combat']['hit_points']['maximum'] == 27
```

## Stateless API Testing

Use `POST /api/v1/character/build` for integration tests (no session needed). It is the same endpoint the React SPA consumes:

```python
import pytest
from app import create_app  # or however app is created

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_rebuild_character_api(client):
    response = client.post('/api/v1/character/build',
        json={"choices_made": {
            "character_name": "Test",
            "level": 3,
            "species": "Dwarf",
            "class": "Cleric",
            "subclass": "Light Domain",
            "background": "Acolyte",
            "ability_scores": {...},
            "background_bonuses": {...}
        }})
    assert response.status_code == 200
    data = response.get_json()
    character = data['character']
    assert character['combat']['hit_points']['maximum'] == 27
```

See `tests/test_api_v1.py` for further examples (catalog, validate, derived views).

## Assertion Patterns

### Effects
```python
effects = character.get('effects', [])
resistance_types = [e['damage_type'] for e in effects if e['type'] == 'grant_damage_resistance']
assert 'Poison' in resistance_types
```

### Proficiencies
```python
assert 'Perception' in character['proficiencies']['skills']
assert 'Light armor' in character['proficiencies']['armor']
```

### Spells
```python
cantrips = character['spells']['prepared']['cantrips']
assert 'Light' in cantrips
```

### Combat Stats
```python
assert character['combat']['hit_points']['maximum'] == expected_hp
assert character['combat']['armor_class'] >= 10
```

## Test Naming

- `test_<class>_<feature>_<assertion>` for specific features
- `test_<species>_<trait>_effect` for species traits
- `test_api_<endpoint>_<scenario>` for API tests
- Keep test functions focused on testing ONE thing

## Common Fixtures

```python
@pytest.fixture
def dwarf_cleric_choices():
    return {
        "character_name": "Thorin",
        "level": 7,
        "species": "Dwarf",
        "class": "Cleric",
        "subclass": "Light Domain",
        "background": "Acolyte",
        "ability_scores": {
            "Strength": 14, "Dexterity": 8, "Constitution": 15,
            "Intelligence": 10, "Wisdom": 16, "Charisma": 12
        },
        "background_bonuses": {"Wisdom": 2, "Constitution": 1}
    }

@pytest.fixture
def built_character(dwarf_cleric_choices):
    builder = CharacterBuilder()
    builder.apply_choices(dwarf_cleric_choices)
    return builder.to_character()
```

## Running Tests

```bash
pytest tests/                        # All tests
pytest tests/core/ -x               # Core tests, stop on first failure
pytest tests/ -k "dwarf"            # Tests matching "dwarf"
pytest tests/ -m integration        # Only integration tests
pytest tests/ --tb=short -q         # Compact output
```

## Round-Trip Equality Safety Net

`tests/integration/test_rebuild_equality.py` is the parametrized safety net
for the "wizard = rebuild" architectural guarantee (audit item P0-2). It
builds every saved sample character, exports `choices_made`, rebuilds a
fresh `CharacterBuilder` from that export, and asserts both
`to_character()` dicts are byte-equal under
`json.dumps(..., sort_keys=True)` after stripping volatile fields.

**Rules for new archetypes:**

- Discovery is by glob (`test_characters/*.json` plus
  `data/example_complete_character.json`). **Every new character archetype
  added to `test_characters/` is picked up automatically — do not
  enumerate fixtures by name.** Drop the JSON in and the parametrized
  suite will cover it on the next run.
- If a fixture fails round-trip equality, that is a real defect. Do not
  weaken the assertion, do not edit the fixture to make it pass, and do
  not add fields to the volatile-field stripper to silence the failure.
  Report the defect; let the architect route the fix.
- The volatile-field stripper (`strip_volatile` in the test module) is
  intentionally conservative. Only add a key to `_VOLATILE_TOP_LEVEL_KEYS`
  if you can demonstrate the field is non-deterministic across two builds
  from the same `choices_made`.
