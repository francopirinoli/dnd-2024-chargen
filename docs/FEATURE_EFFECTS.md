# Feature Effects System

## Overview
Features can grant various mechanical benefits through a structured "effects" array. This allows for consistent parsing and application of feature benefits without string searching.

## Effect Types

### Spellcasting Effects

#### grant_cantrip ✅
Grants a specific cantrip to the character.

```json
{
  "type": "grant_cantrip",
  "spell": "Light",
  "spell_list": "Cleric"
}
```

#### grant_spell ✅
Grants a specific spell that's always prepared.

```json
{
  "type": "grant_spell",
  "spell": "Shield",
  "level": 1,
  "spell_list": "Wizard"
}
```

#### grant_spell_slots ✅
Grants additional spell slots. Slots are additive — multiple effects stack. Supports two shapes:

Single-level form:
```json
{
  "type": "grant_spell_slots",
  "slot_level": 1,
  "count": 2
}
```

Multi-level form:
```json
{
  "type": "grant_spell_slots",
  "slots": {"1": 2, "3": 1}
}
```

Handler: adds each specified count to `character_data["spells"]["slots"][level]`.

#### grant_weapon_mastery ✅
Grants mastery in a specific weapon. Appends the weapon name to `character_data["weapon_masteries"]["selected"]` (idempotent).

```json
{
  "type": "grant_weapon_mastery",
  "weapon": "Longsword"
}
```

### Proficiency Effects

#### grant_weapon_proficiency ✅
Grants weapon proficiencies.

```json
{
  "type": "grant_weapon_proficiency",
  "proficiencies": ["Martial weapons"]
}
```

#### grant_armor_proficiency ✅
Grants armor proficiencies.

```json
{
  "type": "grant_armor_proficiency",
  "proficiencies": ["Heavy armor"]
}
```

#### grant_skill_proficiency ✅
Grants skill proficiencies.

```json
{
  "type": "grant_skill_proficiency",
  "skills": ["Perception", "Insight"]
}
```

#### grant_skill_expertise ✅
Grants expertise in skills.

```json
{
  "type": "grant_skill_expertise",
  "skills": ["Stealth"]
}
```

#### grant_tool_proficiency ✅
Grants tool proficiencies.

```json
{
  "type": "grant_tool_proficiency",
  "tools": ["Thieves' Tools", "Disguise Kit"]
}
```

### Saving Throw Effects

#### grant_save_advantage ✅
Grants advantage on saving throws.

```json
{
  "type": "grant_save_advantage",
  "abilities": ["Constitution"],
  "condition": "Poisoned",
  "display": "Advantage vs Poisoned condition"
}
```

**Properties:**
- `abilities`: Array of ability scores this applies to (e.g., ["Constitution", "Wisdom"])
- `condition`: (Optional) Specific condition this applies against (e.g., "Poisoned", "Charmed")
- `display`: Text to display in character sheet

**Example:** Dwarven Resilience
```json
{
  "type": "grant_save_advantage",
  "abilities": ["Constitution"],
  "condition": "Poisoned",
  "display": "Advantage vs Poisoned condition"
}
```

#### grant_save_proficiency ✅
Grants proficiency in saving throws.

```json
{
  "type": "grant_save_proficiency",
  "abilities": ["Wisdom", "Charisma"]
}
```

#### grant_origin_feat ✅
Grants an Origin Feat by name. Loads the feat data, adds it to the character's feats list, and applies any direct effects the feat has (e.g., Tough's `bonus_hp`). Used by the Human Versatile trait.

**Properties:**
- `feat`: Name of the origin feat (must exist in `data/origin_feats.json`)

**Example**: Human Versatile trait choice
```json
{
  "type": "grant_origin_feat",
  "feat": "Tough"
}
```

### Resistance and Immunity Effects

#### grant_damage_resistance ✅
Grants resistance to one or more damage types. Accepts both singular and plural forms; both are valid in data files.

Singular form (back-compat):
```json
{
  "type": "grant_damage_resistance",
  "damage_type": "Poison"
}
```

Plural form (preferred):
```json
{
  "type": "grant_damage_resistance",
  "damage_types": ["Poison", "Cold"]
}
```

Dynamic form (damage type resolved from a species/trait choice):
```json
{
  "type": "grant_damage_resistance",
  "damage_type_from_choice": "Draconic Ancestry"
}
```

> **grant_damage_immunity — Removed 2026-05-21:** immunity is runtime/DM-adjudicated in 2024 rules and not a sheet field. Use `grant_damage_resistance` for resistance.

#### grant_condition_immunity ✅
Grants immunity to a condition.

```json
{
  "type": "grant_condition_immunity",
  "condition": "Charmed"
}
```

### Combat Effects

#### alternative_ac ✅
Provides an alternative AC calculation formula (e.g., Monk or Barbarian Unarmored Defense). Added as an additional AC option in `calculate_ac_options()`.

**Properties:**
- `base`: Base AC value (typically 10)
- `modifiers`: Array of ability score names to add as modifiers (e.g., `["dexterity", "wisdom"]`)
- `condition`: (Optional) Condition string. `"no_armor_no_shield"` means no armor and no shield allowed.

**Example**: Monk Unarmored Defense
```json
{
  "type": "alternative_ac",
  "base": 10,
  "modifiers": ["dexterity", "wisdom"],
  "condition": "no_armor_no_shield"
}
```

**Example**: Barbarian Unarmored Defense
```json
{
  "type": "alternative_ac",
  "base": 10,
  "modifiers": ["dexterity", "constitution"],
  "condition": "no_armor"
}
```

#### bonus_ac ✅
Grants a bonus to AC.

**Implementation**: Applied in `calculate_ac_options()`. Only applies to armored AC options (checks if `equipped_armor` is not None).

**Example**: Defense fighting style
```json
{
  "type": "bonus_ac",
  "value": 1,
  "condition": "wearing armor"
}
```

#### bonus_damage ✅
Grants a bonus to damage rolls.

**Implementation**: Applied in `calculate_weapon_attacks()`. Checks conditions against weapon properties:
- `"one handed melee weapon"`: Melee weapon without Two-Handed property, only one weapon equipped (Dueling)
- `"thrown weapon ranged attack"`: Weapon with Thrown property used for ranged attack (Thrown Weapon Fighting)
- No condition: Applies to all attacks

**Example**: Dueling fighting style
```json
{
  "type": "bonus_damage",
  "value": 2,
  "condition": "one handed melee weapon"
}
```

**Example**: Thrown Weapon Fighting
```json
{
  "type": "bonus_damage",
  "value": 2,
  "condition": "thrown weapon ranged attack"
}
```

#### bonus_attack ✅
Grants a bonus to attack rolls.

**Implementation**: Applied in `calculate_weapon_attacks()`. Checks conditions against weapon category or properties:
- `weapon_property: "Ranged"`: Applies if weapon category contains "Ranged" (Archery)
- `weapon_property: "<property>"`: Applies if weapon has that property in its properties list
- No condition: Applies to all attacks

**Example**: Archery fighting style
```json
{
  "type": "bonus_attack",
  "value": 2,
  "weapon_property": "Ranged"
}
```

#### great_weapon_fighting ✅
Allows rerolling 1s and 2s on damage dice for melee weapons wielded with two hands.

**Implementation**: Applied in `calculate_weapon_attacks()`. Affects average damage calculations for qualifying weapons. Applies to weapons that are:
- Melee weapons (not Ranged category)
- Have Two-Handed property OR Versatile property

**Example**: Great Weapon Fighting style
```json
{
  "type": "great_weapon_fighting"
}
```

**Calculation**: When calculating average damage, the expected value per die changes from `(1 + die_size) / 2` to account for rerolling 1s and 2s:
- Expected value = `(2 * avg_all + sum(3 to N)) / N`
- Where `avg_all` is the normal die average `(1 + die_size) / 2`

#### two_weapon_fighting_modifier ✅
Adds ability modifier to offhand attack damage when dual-wielding.

**Implementation**: Applied in `_create_dual_wield_combo()`. When creating combination cards for two light weapons:
- Without this effect: Offhand damage = dice only (e.g., "1d4")
- With this effect: Offhand damage = dice + ability modifier (e.g., "1d4 + 3")

**Example**: Two-Weapon Fighting style
```json
{
  "type": "two_weapon_fighting_modifier"
}
```

#### unarmed_fighting ✅
Enhances unarmed strikes with improved damage dice and grapple damage.

**Implementation**: Applied in `calculate_weapon_attacks()`. Modifies the Unarmed Strike attack that's always added to all characters:
- **Base Unarmed Strike** (without style): 1 + STR modifier
- **With Unarmed Fighting**:
  - 1d6 + STR modifier (when wielding weapons or shield)
  - 1d8 + STR modifier (when not wielding any weapons or shield)
  - Adds note: "1d4 damage to grappled creature (start of turn)"

**Example**: Unarmed Fighting style
```json
{
  "type": "unarmed_fighting"
}
```

**Grapple Damage**: At the start of your turn, you can deal 1d4 bludgeoning damage to one creature grappled by you (displayed as a damage note).

#### set_martial_arts_die ✅
Sets the Monk's Martial Arts die for unarmed strikes and monk weapons, scaling with level. Also enables using DEX instead of STR for unarmed strike attack and damage rolls (Dexterous Attacks).

**Implementation**: Handler in `_apply_effect()` resolves the correct die for the current character level and stores it in `character_data["martial_arts_die"]`. Applied in `calculate_weapon_attacks()` to override unarmed strike damage with the Martial Arts die, using `max(STR, DEX)` as the modifier.

**Die Progression**:
- Level 1–4: 1d6
- Level 5–10: 1d8
- Level 11–16: 1d10
- Level 17–20: 1d12

**Example**: Monk Martial Arts feature
```json
{
  "type": "set_martial_arts_die",
  "die_by_level": {
    "1": "1d6",
    "5": "1d8",
    "11": "1d10",
    "17": "1d12"
  }
}
```

#### monk_dexterous_attacks ✅
Enables using `max(STR, DEX)` for attack and damage rolls of monk weapons (Simple Melee, or Martial Melee with the Light property). Implements the "Dexterous Attacks" part of the Monk's Martial Arts feature.

**Implementation**: Handler in `_apply_effect()` sets `character_data["monk_dexterous_attacks"] = True`. In `calculate_weapon_attacks()`, when this flag is set and the weapon qualifies as a monk weapon, `max(str_mod, dex_mod)` is used instead of `str_mod`.

**Monk weapon criteria**:
- Category is `"Simple Melee"`, OR
- Category is `"Martial Melee"` AND weapon has the `"Light"` property

**Example**: Monk Martial Arts feature
```json
{
  "type": "monk_dexterous_attacks"
}
```

### Ability Score Effects

#### ability_bonus ✅
Grants a bonus to ability checks.

```json
{
  "type": "ability_bonus",
  "ability": "Intelligence",
  "skills": ["Arcana", "Religion"],
  "value": "wisdom_modifier",
  "minimum": 1
}
```

### Miscellaneous Effects

#### grant_language ✅
Grants language proficiencies.

```json
{
  "type": "grant_language",
  "languages": ["Elvish", "Dwarvish"]
}
```

#### increase_speed ✅
Increases movement speed.

```json
{
  "type": "increase_speed",
  "value": 10
}
```

#### grant_darkvision ✅
Grants or improves darkvision.

```json
{
  "type": "grant_darkvision",
  "range": 60
}
```

#### bonus_hp ✅
Grants a bonus to hit points.

```json
{
  "type": "bonus_hp",
  "value": 1,
  "scaling": "per_level"
}
```

**Properties:**
- `value`: The amount of HP bonus to grant
- `scaling`: (Optional) How the bonus scales. Use "per_level" for bonuses that apply at each level (like Dwarven Toughness)

**Example:** Dwarven Toughness
```json
{
  "type": "bonus_hp",
  "value": 1,
  "scaling": "per_level"
}
```

**Multiclass scoping for `per_level`**: when a `bonus_hp` effect with `scaling: "per_level"` originates from a **class or subclass feature**, it scales on the **source class's level**, not on total character level. Non-class sources (species, background, feats) continue to scale on total character level.

Example: a Sorcerer 5 / Paladin 5 with Draconic Resilience (Draconic Sorcery, `value: 1`, `per_level`, source = Sorcerer) gains `+5` HP from that effect, not `+10`. Dwarven Toughness on the same character still grants `+10`.

#### bonus_initiative ✅
Grants a bonus to initiative.

**Implementation**: Applied in `calculate_combat_stats()`. Numeric values add directly; `"proficiency"` adds the character's current proficiency bonus.

**Example:** Alert feat
```json
{
  "type": "bonus_initiative",
  "value": "proficiency"
}
```

## Feature Structure

Features can include an `effects` array alongside their description:

```json
"Bonus Cantrip": {
  "description": "You know the Light cantrip.",
  "effects": [
    {
      "type": "grant_cantrip",
      "spell": "Light",
      "spell_list": "Cleric"
    }
  ]
}
```

## Multiple Effects

A single feature can grant multiple effects:

```json
"Divine Order - Protector": {
  "description": "You gain proficiency with Martial weapons and training with Heavy armor.",
  "effects": [
    {
      "type": "grant_weapon_proficiency",
      "proficiencies": ["Martial weapons"]
    },
    {
      "type": "grant_armor_proficiency",
      "proficiencies": ["Heavy armor"]
    }
  ]
}
```

## Phase 7+ Effect Types

These effect types were added after the initial documentation pass. All are ✅ implemented in `_apply_effect()`.

#### grant_cantrip_choice ✅

Deferred cantrip selection — a no-op in `_apply_effect()` itself. The actual `grant_cantrip` is applied when the player's selection is resolved through the choice system. Present so `strict_mode.check_effect_type()` does not raise an unknown-type warning on data files that carry this type.

```json
{ "type": "grant_cantrip_choice" }
```

#### grant_skill_proficiency_or_expertise ✅

D&D 2024 pattern: if the character lacks the skill proficiency, it is granted; if the character already has proficiency, expertise is granted instead.

```json
{
  "type": "grant_skill_proficiency_or_expertise",
  "skills": ["Perception"]
}
```

#### grant_spell_at_will ✅

Grants a spell that can be cast at will (no spell slot required). Typical Warlock invocation pattern (e.g. Armor of Shadows → Mage Armor). Recorded in `always_prepared` with `at_will: true`; renderers annotate it "(at will)".

```json
{
  "type": "grant_spell_at_will",
  "spell": "Mage Armor"
}
```

#### bonus_spell_damage_ability_mod ✅

Adds a chosen ability's modifier to the damage rolls of a specific spell. Written into `spell_metadata[spell]["damage_bonus"]`. Used by the Agonizing Blast invocation.

```json
{
  "type": "bonus_spell_damage_ability_mod",
  "spell": "Eldritch Blast",
  "ability": "Charisma"
}
```

#### bonus_spell_range ✅

Overrides the displayed range of a specific spell. Written into `spell_metadata[spell]["range_override"]`. Used by the Eldritch Spear invocation.

```json
{
  "type": "bonus_spell_range",
  "spell": "Eldritch Blast",
  "range": "300 feet"
}
```

#### grant_magical_darkness_sight ✅

Grants the ability to see normally in magical darkness up to a given range. Kept distinct from `grant_darkvision` because the rule is specifically about magical darkness. Takes the maximum range if applied multiple times.

```json
{
  "type": "grant_magical_darkness_sight",
  "range": 120
}
```

#### grant_maneuver ✅

Records a Battle Master maneuver by name on the character sheet. Idempotent.

```json
{
  "type": "grant_maneuver",
  "maneuver": "Riposte"
}
```

#### grant_superiority_dice ✅

Sets the Battle Master's Combat Superiority dice count and die size, resolving per-level scaling from `count_by_level` and `die_by_level` maps against the current character level. Writes `character_data["superiority_dice"]`.

```json
{
  "type": "grant_superiority_dice",
  "count_by_level": { "3": 4, "7": 5, "10": 6, "15": 7, "18": 8 },
  "die_by_level":   { "3": "d8", "10": "d10", "18": "d12" }
}
```

## Effect Authoring Locations

An `effects` array may appear in exactly **five** places in the data files. Each has a distinct dispatcher entry point in `CharacterBuilder`:

| Location | File pattern | Dispatcher entry point |
|---|---|---|
| Class feature | `data/classes/<class>.json` → `features_by_level.<level>.<feature_name>.effects` | `apply_choice("class")` → `feature_manager` → `_apply_effect()` |
| Subclass feature | `data/subclasses/<class>/<subclass>.json` → `features_by_level.<level>.<feature_name>.effects` | `apply_choice("subclass")` → `feature_manager` → `_apply_effect()` |
| Species trait | `data/species/<species>.json` or `data/species_variants/<variant>.json` → `traits.<trait_name>.effects` | `apply_choice("species")` / `apply_choice("lineage")` → `_apply_effect()` |
| Background benefit | `data/backgrounds/<bg>.json` → `benefits[].effects` | `apply_choice("background")` → `_apply_effect()` |
| Feat | `data/origin_feats.json` or `data/general_feats.json` → `feats.<feat_name>.effects` | class feat slot / `grant_origin_feat` effect → `_apply_effect()` |

Fighting styles (`data/fighting_styles.json`) and eldritch invocations (`data/eldritch_invocations.json`) also carry `effects` arrays and follow the same dispatcher path via `apply_choice("fighting_style")` and `apply_choice("eldritch_invocation_selections")` respectively.

## Closed Effect Type Enum

Every valid `effect.type` string accepted by `_apply_effect()`. Using a value not in this list will trigger a `strict_mode` warning (or error in strict mode). To add a new type, implement a handler in `_apply_effect()` and register it with `strict_mode.check_effect_type()` **in the same PR**.

| Effect type | Category | Notes |
|---|---|---|
| `grant_cantrip` | Spellcasting | Adds cantrip to `always_prepared` |
| `grant_cantrip_choice` | Spellcasting | No-op; deferred to choice resolver |
| `grant_spell` | Spellcasting | Adds always-prepared spell |
| `grant_spell_at_will` | Spellcasting | Adds at-will spell (no slot) |
| `grant_spell_slots` | Spellcasting | Adds extra spell slots additively |
| `grant_weapon_mastery` | Proficiency | Appends to `weapon_masteries.selected` |
| `grant_weapon_proficiency` | Proficiency | Weapon proficiency list |
| `grant_armor_proficiency` | Proficiency | Armor proficiency list |
| `grant_skill_proficiency` | Proficiency | Skill proficiency list |
| `grant_skill_expertise` | Proficiency | Skill expertise list |
| `grant_skill_proficiency_or_expertise` | Proficiency | Proficiency or expertise (D&D 2024 pattern) |
| `grant_tool_proficiency` | Proficiency | Tool proficiency list |
| `grant_save_proficiency` | Proficiency | Saving throw proficiency list |
| `grant_language` | Proficiency | Language list |
| `grant_save_advantage` | Saves | Adds entry to `save_advantages` |
| `grant_damage_resistance` | Defense | Adds to `resistances` |
| `grant_condition_immunity` | Defense | Adds to `condition_immunities` |
| `grant_darkvision` | Senses | Sets `darkvision` to max of current and new |
| `grant_magical_darkness_sight` | Senses | Distinct from darkvision; magical darkness only |
| `grant_origin_feat` | Feats | Loads feat data and recursively applies its effects |
| `grant_maneuver` | Combat | Appends to `maneuvers_known` |
| `grant_superiority_dice` | Combat | Sets `superiority_dice` with per-level scaling |
| `alternative_ac` | Combat | Adds formula to `alternative_ac_options` |
| `bonus_ac` | Combat | Adds entry to `ac_bonuses` |
| `bonus_damage` | Combat | Adds entry to `damage_bonuses` |
| `bonus_attack` | Combat | Adds entry to `attack_bonuses` |
| `attack_ability_override` | Combat | Uses an ability for the weapon named by `choices_made[weapon_tag]` when it is better |
| `bonus_hp` | Combat | Adds entry to `hp_bonuses` |
| `bonus_initiative` | Combat | Adds entry to `initiative_bonuses` |
| `bonus_spell_damage_ability_mod` | Combat | Writes `spell_metadata[spell]["damage_bonus"]` |
| `bonus_spell_range` | Combat | Writes `spell_metadata[spell]["range_override"]` |
| `great_weapon_fighting` | Fighting style | Flag in `fighting_style_flags` |
| `two_weapon_fighting_modifier` | Fighting style | Flag in `fighting_style_flags` |
| `unarmed_fighting` | Fighting style | Flag in `fighting_style_flags` |
| `set_martial_arts_die` | Monk | Sets `martial_arts_die` per level |
| `monk_dexterous_attacks` | Monk | Sets `monk_dexterous_attacks: true` |
| `ability_bonus` | Ability scores | Adds entry to `ability_bonuses` |
| `increase_speed` | Movement | Increments `speed`; `feature_group` prevents double-counting |

## External Effect References

Features that are shared across multiple classes (like Fighting Styles) should be stored in separate data files and referenced using the choice reference system:

### Example: Fighting Styles

**In class data (e.g., fighter.json):**
```json
"Fighting Style": {
  "description": "You adopt a particular style of fighting as your specialty.",
  "choices": {
    "type": "select_single",
    "count": 1,
    "name": "fighting_style",
    "source": {
      "type": "external",
      "file": "fighting_styles.json",
      "list": "fighting_styles"
    },
    "optional": false
  }
}
```

**In external data file (data/fighting_styles.json):**
```json
{
  "fighting_styles": {
    "Archery": {
      "description": "You gain a +2 bonus to attack rolls you make with ranged weapons.",
      "effects": [
        {
          "type": "bonus_attack",
          "value": 2,
          "weapon_property": "Ranged"
        }
      ]
    },
    "Defense": {
      "description": "While you are wearing armor, you gain a +1 bonus to AC.",
      "effects": [
        {
          "type": "bonus_ac",
          "value": 1,
          "condition": "wearing armor"
        }
      ]
    }
  }
}
```

This approach allows:
- Reuse across Fighter, Paladin, Ranger, and feats
- Single source of truth for fighting style mechanics
- Easy updates to all classes when fighting styles change
- Consistent behavior across all sources

## Implementation Notes

1. Effects are optional - features without effects are display-only
2. Effects should be processed when the feature is gained
3. Effects should be reversible (for changing choices)
4. The system should gracefully handle unknown effect types
5. Complex features may still require custom code, but common patterns should use this system
6. External references are loaded automatically when applying choices
