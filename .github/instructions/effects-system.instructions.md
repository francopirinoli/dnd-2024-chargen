---
description: "Use when working with D&D feature effects, grant_spell, grant_cantrip, grant_proficiency, bonus_hp, bonus_ac, bonus_damage, damage resistance, save advantage, or any mechanical benefit in JSON data files or CharacterBuilder effect processing code."
applyTo: ["data/**/*.json", "modules/character_builder.py", "modules/feature_manager.py", "docs/FEATURE_EFFECTS.md"]
---

# Effects System

## Cardinal Rule

**NEVER hardcode feature names or species names in application logic.**
All mechanical benefits MUST be defined as structured `effects` arrays in JSON data files and processed generically by `CharacterBuilder._apply_effect()`.

```python
# ❌ WRONG — hardcoded feature check
if feature_name == 'Dwarven Resilience':
    hp_bonus += level

# ✅ CORRECT — generic effect processing
if effect['type'] == 'bonus_hp' and effect.get('scaling') == 'per_level':
    hp_bonus += level * effect['value']
```

## One Dispatcher Rule (audit Phase 6)

The effects subsystem has **one** mutation chokepoint and **one** lookup helper for choice-driven effects. Contributors MUST respect both.

1. **`_apply_effect()` is the only mutator.** Every effect — regardless of where it was authored — reaches `character_data` exclusively through `CharacterBuilder._apply_effect()` in [modules/character_builder.py](../../modules/character_builder.py). No other method may mutate character state based on an effect dict.
2. **Choice-driven effects route through `resolve_effects_for_choice()` first.** Fighting styles, maneuvers, eldritch invocations, future metamagic, and any other player-picked option are resolved by [`resolve_effects_for_choice`](../../modules/character_builder.py) into `(effect, source_label, source_type)` triples. The caller then hands each triple to `_apply_effect`. The resolver performs **lookup only**; it never mutates.
3. **`applied_effects` is an audit log only.** Calculation methods (`calculate_weapon_attacks`, `calculate_ac_options`, `_extract_hp_bonuses`, etc.) MUST read from the structured bonus fields populated by `_apply_effect` on `character_data` — `damage_bonuses`, `attack_bonuses`, `ac_bonuses`, `hp_bonuses`, `alternative_ac_options`, `fighting_style_flags`. They MUST NOT re-walk `applied_effects` to derive behaviour. The log exists for tests, diffing, and debugging; it is not a calculation input.
4. **No name-based branching.** Branch on `effect['type']`. Never on feature names, option names, fighting-style names, or species names — those belong in JSON, not in Python.
5. **New effect types ship in one PR**, with all five pieces together:
   - enum entry in [models/_shared/effect.json](../../models/_shared/effect.json),
   - matching string in `KNOWN_EFFECT_TYPES` in [modules/strict_mode.py](../../modules/strict_mode.py),
   - handler branch in `_apply_effect`,
   - entry in [docs/FEATURE_EFFECTS.md](../../docs/FEATURE_EFFECTS.md),
   - at least one test exercising the handler.

The five legitimate JSON authoring locations that feed this dispatcher are catalogued in [.github/instructions/data-schemas.instructions.md](./data-schemas.instructions.md) under **"The 5 valid `effects`-array authoring locations"**.

## Strict Mode & The Closed Enum (audit Phase 5)

The set of valid `effect.type` values is a **closed enum**, duplicated in two
places that MUST stay in sync:

1. [models/_shared/effect.json](models/_shared/effect.json) — `properties.type.enum`. Gates JSON authoring via `validate_data.py`.
2. [modules/strict_mode.py](modules/strict_mode.py) — `KNOWN_EFFECT_TYPES` frozenset. Gates runtime dispatch in `_apply_effect`.

The test [tests/core/test_strict_mode.py](tests/core/test_strict_mode.py)::`test_effect_enum_matches_schema` enforces parity — drift fails CI.

### Adding a new effect type (single PR)

1. Add the new type string to the enum in [models/_shared/effect.json](models/_shared/effect.json).
2. Add the same string to `KNOWN_EFFECT_TYPES` in [modules/strict_mode.py](modules/strict_mode.py).
3. Implement the handler branch in `CharacterBuilder._apply_effect` ([modules/character_builder.py](modules/character_builder.py)).
4. Document the type in the table below and in [docs/FEATURE_EFFECTS.md](docs/FEATURE_EFFECTS.md).
5. Add a test that exercises the handler.

### Strict mode toggle

- Environment variable `DND_STRICT_EFFECTS=1` → strict (raise on unknown effect
  type, unknown top-level `choices_made` key, non-canonical fallback choice
  resolution, malformed `features_by_level`).
- `DND_STRICT_EFFECTS=0` → lenient (warn-only).
- Default OFF when `FLASK_ENV=production`, ON everywhere else.
- The pytest suite forces it ON via [conftest.py](conftest.py).

## Effect JSON Shape

Every effect is an object inside a feature's `effects` array:

```json
{
  "Feature Name": {
    "description": "Human-readable description.",
    "effects": [
      {"type": "<effect_type>", ...type-specific fields}
    ]
  }
}
```

## Quick Reference Table

| Effect Type | Required Fields | Optional Fields | Example Use |
|---|---|---|---|
| `grant_cantrip` | `spell` | `spell_list` | Light Domain bonus cantrip |
| `grant_spell` | `spell` | `level`, `min_level`, `spell_list`, `counts_against_limit` | Domain spells, lineage spells |
| `grant_spell_slots` | `level`, `count` | — | Bonus spell slots |
| `grant_weapon_proficiency` | `proficiencies` (array) | — | Protector martial weapons |
| `grant_armor_proficiency` | `proficiencies` (array) | — | Protector heavy armor |
| `grant_tool_proficiency` | `tools` (array) | — | Rogue Thieves' Tools, class features |
| `grant_skill_proficiency` | `skills` (array) | — | Background skill grants |
| `grant_skill_expertise` | `skills` (array) | — | Rogue/Bard expertise |
| `grant_save_advantage` | `abilities` (array) | `condition`, `display` | Dwarven Resilience |
| `grant_save_proficiency` | `abilities` (array) | — | Class saving throws |
| `grant_damage_resistance` | `damage_type` | — | Poison, Fire, Necrotic |
| `grant_damage_immunity` | `damage_type` | — | Full immunity |
| `grant_condition_immunity` | `condition` | — | Charmed immunity |
| `bonus_ac` | `value` | `condition` | Defense fighting style |
| `bonus_damage` | `value` | `condition` | Dueling, Thrown Weapon |
| `bonus_attack` | `value` | `weapon_property` | Archery (+2 ranged) |
| `bonus_hp` | `value` | `scaling` (`per_level`) | Dwarven Toughness |
| `ability_bonus` | `ability`, `value` | `skills`, `minimum` | Thaumaturge WIS→INT |
| `grant_language` | `languages` (array) | — | Species languages |
| `grant_darkvision` | `range` | — | 60ft or 120ft |
| `increase_speed` | `value` | — | Wood Elf +5ft |
| `great_weapon_fighting` | — | — | Reroll 1s/2s on damage |
| `two_weapon_fighting_modifier` | — | — | Add ability mod to offhand |
| `unarmed_fighting` | — | — | Enhanced unarmed strikes |

## Spell Granting — Critical Format

**ALL spell granting MUST use effects arrays. NEVER use separate `spells` dicts.**

```json
// ❌ WRONG
{"Light Domain Spells": {"spells": {"3": ["Burning Hands"]}}}

// ✅ CORRECT
{
  "Light Domain Spells": {
    "description": "You always have certain spells prepared.",
    "effects": [
      {"type": "grant_spell", "spell": "Burning Hands", "min_level": 3},
      {"type": "grant_spell", "spell": "Faerie Fire", "min_level": 3}
    ]
  }
}
```

### Spell Storage Destinations
- Domain/subclass spells → `character['spells']['prepared']` (always prepared, use slots)
- Species/lineage spells → `character['spells']['prepared']` + `spell_metadata` (always prepared, 1/day free)

## Condition Strings for bonus_damage

| Condition Value | Meaning |
|---|---|
| `"one handed melee weapon"` | Melee, no Two-Handed, one weapon equipped (Dueling) |
| `"thrown weapon ranged attack"` | Thrown property, ranged attack roll (Thrown Weapon Fighting) |
| *(omitted)* | Applies to all attacks |

## Condition Strings for bonus_attack

| Field | Meaning |
|---|---|
| `weapon_property: "Ranged"` | Weapon category contains "Ranged" (Archery) |
| `weapon_property: "<name>"` | Weapon has that property in its properties list |

## Adding a New Effect Type

See the **One Dispatcher Rule** above for the full PR checklist. In short: enum + `KNOWN_EFFECT_TYPES` + `_apply_effect` handler (populating the appropriate structured bonus field on `character_data`) + [docs/FEATURE_EFFECTS.md](../../docs/FEATURE_EFFECTS.md) entry + test. Calculation methods read the structured bonus field; they do not re-walk `applied_effects`.
