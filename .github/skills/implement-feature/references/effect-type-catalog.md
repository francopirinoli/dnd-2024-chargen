# Effect Type Catalog

Quick reference for all supported effect types in the D&D character creator effects system.

## Spellcasting

| Type | Required | Optional | Example |
|---|---|---|---|
| `grant_cantrip` | `spell` | `spell_list` | `{"type": "grant_cantrip", "spell": "Light"}` |
| `grant_spell` | `spell` | `level`, `min_level`, `spell_list`, `counts_against_limit` | `{"type": "grant_spell", "spell": "Shield", "min_level": 3}` |
| `grant_spell_slots` | `level`, `count` | — | `{"type": "grant_spell_slots", "level": 1, "count": 2}` |

## Proficiencies

| Type | Required | Optional | Example |
|---|---|---|---|
| `grant_weapon_proficiency` | `proficiencies` (array) | — | `{"type": "grant_weapon_proficiency", "proficiencies": ["Martial weapons"]}` |
| `grant_armor_proficiency` | `proficiencies` (array) | — | `{"type": "grant_armor_proficiency", "proficiencies": ["Heavy armor"]}` |
| `grant_skill_proficiency` | `skills` (array) | — | `{"type": "grant_skill_proficiency", "skills": ["Perception"]}` |
| `grant_skill_expertise` | `skills` (array) | — | `{"type": "grant_skill_expertise", "skills": ["Stealth"]}` |

## Saving Throws

| Type | Required | Optional | Example |
|---|---|---|---|
| `grant_save_advantage` | `abilities` (array) | `condition`, `display` | `{"type": "grant_save_advantage", "abilities": ["Constitution"], "condition": "Poisoned"}` |
| `grant_save_proficiency` | `abilities` (array) | — | `{"type": "grant_save_proficiency", "abilities": ["Wisdom"]}` |

## Resistances & Immunities

| Type | Required | Optional | Example |
|---|---|---|---|
| `grant_damage_resistance` | `damage_type` | — | `{"type": "grant_damage_resistance", "damage_type": "Poison"}` |
| `grant_damage_immunity` | `damage_type` | — | `{"type": "grant_damage_immunity", "damage_type": "Fire"}` |
| `grant_condition_immunity` | `condition` | — | `{"type": "grant_condition_immunity", "condition": "Charmed"}` |

## Combat

| Type | Required | Optional | Notes |
|---|---|---|---|
| `alternative_ac` | `base`, `modifiers` | `condition` | `{"type": "alternative_ac", "base": 10, "modifiers": ["dexterity", "wisdom"], "condition": "no_armor_no_shield"}` |
| `bonus_ac` | `value` | `condition` | Only applies to armored AC |
| `bonus_damage` | `value` | `condition` | See condition strings below |
| `bonus_attack` | `value` | `weapon_property` | Filters by weapon category/property |
| `great_weapon_fighting` | — | — | Reroll 1s/2s on two-handed damage |
| `two_weapon_fighting_modifier` | — | — | Add ability mod to offhand |
| `unarmed_fighting` | — | — | Enhanced unarmed strikes |

### bonus_damage conditions
- `"one handed melee weapon"` — Dueling
- `"thrown weapon ranged attack"` — Thrown Weapon Fighting
- *(omitted)* — All attacks

### bonus_attack weapon_property
- `"Ranged"` — Archery
- Any weapon property name

## Ability & Misc

| Type | Required | Optional | Example |
|---|---|---|---|
| `ability_bonus` | `ability`, `value` | `skills`, `minimum` | Thaumaturge WIS→INT |
| `bonus_hp` | `value` | `scaling` | `{"type": "bonus_hp", "value": 1, "scaling": "per_level"}` |
| `grant_language` | `languages` (array) | — | `{"type": "grant_language", "languages": ["Elvish"]}` |
| `grant_darkvision` | `range` | — | `{"type": "grant_darkvision", "range": 60}` |
| `increase_speed` | `value` | — | `{"type": "increase_speed", "value": 10}` |
