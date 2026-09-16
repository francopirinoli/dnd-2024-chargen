# Data Files

All game content lives as **plain JSON** under `data/`. Schemas are in `models/`. There is no code generation: adding a class, subclass, species, background, feat or spell means editing JSON.

## Top-Level Layout

```
data/
├── classes/                   # 12 class files
├── subclasses/                # one folder per class
│   └── <class>/
├── species/                   # 10 species files
├── species_variants/          # 8 lineage / variant files
├── backgrounds/               # 16 active D&D 2024 backgrounds + retained tagged legacy files
├── equipment/                 # weapons, armor, gear, masteries
├── spells/
│   ├── class_lists/           # 8 spellcasting-class lists
│   └── definitions/           # ~383 individual spell definitions
├── completeness/
│   └── backlog.json           # tracked content gaps
├── fighting_styles.json       # reference: all fighting styles
├── eldritch_invocations.json  # reference: all warlock invocations
├── origin_feats.json          # reference: origin feats catalogue
├── general_feats.json         # reference: general feats catalogue
├── trait_patterns.json        # reference: shared trait shapes
├── character_sheet_model.json # reference: character export model
└── example_complete_character.json
```

## Categories

### Classes (`data/classes/`)

12 files, one per class:

```
barbarian.json   bard.json     cleric.json     druid.json
fighter.json     monk.json     paladin.json    ranger.json
rogue.json       sorcerer.json warlock.json    wizard.json
```

Validated against [models/class_schema.json](../models/class_schema.json). Required fields include `name`, `hit_die`, `primary_ability`, `saving_throw_proficiencies`, `armor_proficiencies`, `weapon_proficiencies`, `subclass_selection_level`, `features_by_level`, and (where applicable) `spell_slots_by_level`.

`features_by_level` is **always an object of `{ feature_name: description }`**, never an array. See [.github/instructions/data-schemas.instructions.md](../.github/instructions/data-schemas.instructions.md).

#### Multiclassing block

Every class file carries a `multiclassing` object describing what the class grants **when taken as a secondary class** via multiclassing. It is **not** applied for the primary (first) class — that path uses the full class block. The shape is defined in [models/class_schema.json](../models/class_schema.json):

```json
"multiclassing": {
  "hit_die_granted": 8,
  "armor_training": ["Light", "Shields"],
  "weapon_training": [],
  "tool_training": [],
  "skill_proficiencies": null,
  "saving_throw_proficiencies": [],
  "other_proficiencies": [],
  "notes": null,
  "source_text": "exact wiki quote"
}
```

| Field                         | Notes                                                                                  |
|-------------------------------|----------------------------------------------------------------------------------------|
| `hit_die_granted`             | Hit die size added to the HP pool for each level of this class beyond level 1 of the primary class. |
| `armor_training`              | Armor groups granted (e.g. `"Light"`, `"Medium"`, `"Heavy"`, `"Shields"`).             |
| `weapon_training`             | Weapon proficiencies granted (e.g. `"Martial"`, named simple weapons).                 |
| `tool_training`               | Tool proficiencies granted.                                                            |
| `skill_proficiencies`         | `null`, or `{ "count": n, "options": ["Skill", ...] }`. `options` may be `"any"`.      |
| `saving_throw_proficiencies`  | Always `[]` per D&D 2024 RAW — multiclass never grants save proficiencies. Field is present for schema uniformity. |
| `other_proficiencies`         | Anything that doesn't fit the buckets above (rare).                                    |
| `notes`                       | Free-text rules notes (optional).                                                      |
| `source_text`                 | The exact wiki quote the block was authored from. Preserved for auditability so a reviewer can diff the structured grants against the original prose. |

The builder consumes this block when assembling a multiclass character (see [character_builder_guide.md](character_builder_guide.md#multiclassing)). Skill / tool grants that require a player choice surface as `pending_multiclass_skill_choices` and `pending_multiclass_tool_choices` on the build response — see [APIContract.md](APIContract.md#multiclass-pending-choices).

### Subclasses (`data/subclasses/<class>/`)

One folder per class, one file per subclass within. Validated against [models/subclass_schema.json](../models/subclass_schema.json). Same `features_by_level` rule applies.

### Species (`data/species/`)

10 files:

```
aasimar.json   dragonborn.json  dwarf.json   elf.json    gnome.json
goliath.json   halfling.json    human.json   orc.json    tiefling.json
```

Each species defines `traits`, `creature_type`, `size`, `speed`, optional `darkvision`, and either a list or map of `lineages`.

### Species variants / lineages (`data/species_variants/`)

8 files for lineage detail (description, traits, etc.) referenced by parent species:

```
abyssal_tiefling.json   chthonic_tiefling.json   drow.json
forest_gnome.json       high_elf.json            infernal_tiefling.json
rock_gnome.json         wood_elf.json
```

The catalog endpoint normalises these into a uniform `{ id, name, description, traits }` shape via `_enrich_lineages` in [routes/api/character.py](../routes/api/character.py).

### Backgrounds (`data/backgrounds/`)

18 files: 16 active D&D 2024 backgrounds plus retained 2014 legacy entries that are tagged but excluded from the default wizard catalog. In D&D 2024 every active background grants an origin feat and ASI options — both are encoded here.

Each background carries catalog metadata validated by [models/background_schema.json](../models/background_schema.json):

| Field | Values | Meaning |
|-------|--------|---------|
| `edition` | `"2024"` or `"2014"` | Rules edition the entry came from |
| `status` | `"active"` or `"legacy"` | Whether the entry belongs in the default catalog |

The default API/frontend catalog (`GET /api/v1/catalog/backgrounds`) returns only `edition: "2024"` + `status: "active"`. Retained legacy files such as `Folk Hero` and `Guild Artisan` remain loadable by direct name and through `?include_legacy=true` for explicit opt-in tooling.

### Equipment (`data/equipment/`)

| File                    | Contents                                       |
|-------------------------|------------------------------------------------|
| `weapons.json`          | All weapons. Authoritative source for "is X a weapon?" — never hardcode lists in Python. |
| `armor.json`            | All armor (light, medium, heavy, shields).     |
| `adventuring_gear.json` | Gear, packs, tools, kits.                      |
| `weapon_masteries.json` | Mastery property definitions.                  |

### Spells (`data/spells/`)

```
data/spells/
├── class_lists/   # 8 files: bard, cleric, druid, paladin, ranger, sorcerer, warlock, wizard
└── definitions/   # ~383 individual spell JSON files (slug-named)
```

Class lists hold `{ class, cantrips: [...], spells_by_level: { "1": [...], "2": [...] } }`. Definitions hold the full mechanical text for each spell.

### Reference files (top level)

| File                          | Contents                                                              |
|-------------------------------|-----------------------------------------------------------------------|
| `fighting_styles.json`        | All fighting styles, their effects.                                   |
| `eldritch_invocations.json`   | All warlock invocations, prerequisites, effects.                      |
| `origin_feats.json`           | Origin feats granted by 2024 backgrounds.                             |
| `general_feats.json`          | General feats available at level 4+.                                  |
| `trait_patterns.json`         | Shared trait shape patterns referenced by species traits.             |
| `character_sheet_model.json`  | Reference model used when exporting a complete character.             |
| `example_complete_character.json` | A worked example — handy for tests and inspection.                |

Served by `GET /api/v1/catalog/reference/<name>` (allowed names: `fighting_styles`, `eldritch_invocations`, `origin_feats`, `general_feats`, `trait_patterns`).

### Completeness tracking (`data/completeness/`)

| File             | Contents                                         |
|------------------|--------------------------------------------------|
| `backlog.json`   | Known content gaps tracked outside GitHub Issues |

## Schemas (`models/`)

Every category under `data/` is validated by [validate_data.py](../validate_data.py) against a schema in [models/](../models/). Shared subschemas live in [models/_shared/](../models/_shared/) and are referenced by entity schemas via relative `$ref`.

| File glob                                      | Schema                                                                                  | Dispatcher entry point                                               | External-source pattern        | Notes                                                                                              |
|------------------------------------------------|-----------------------------------------------------------------------------------------|----------------------------------------------------------------------|--------------------------------|----------------------------------------------------------------------------------------------------|
| `data/classes/*.json`                          | [models/class_schema.json](../models/class_schema.json)                                 | `apply_choice("class")` → `feature_manager` → `_apply_effect()`     | `update_classes.py`             | `feature_kind` migration arrives in Phase 8 (`D6-2`).                                              |
| `data/subclasses/*/*.json`                     | [models/subclass_schema.json](../models/subclass_schema.json)                           | `apply_choice("subclass")` → `feature_manager` → `_apply_effect()`  | `update_classes.py`             | Same `features_by_level` rules as classes.                                                         |
| `data/species/*.json`                          | [models/species_schema.json](../models/species_schema.json)                             | `apply_choice("species")` → `_apply_effect()`                        | `update_species.py`             | No ability score increases per D&D 2024.                                                           |
| `data/species_variants/*.json`                 | [models/species_variant_schema.json](../models/species_variant_schema.json)             | `apply_choice("lineage")` → `_apply_effect()`                        | `update_species.py`             | `parent_species` field resolves to a file in `data/species/`.                                      |
| `data/backgrounds/*.json`                      | [models/background_schema.json](../models/background_schema.json)                       | `apply_choice("background")` → `_apply_effect()`                     | hand-authored                   | Stricter background constraints (skill count, ASI total, origin-feat existence) land in Phase 10 (`D6-5`). |
| `data/origin_feats.json`                       | [models/feat_schema.json](../models/feat_schema.json)                                   | `grant_origin_feat` effect → `_apply_effect()`                       | hand-authored                   | Single schema covers both feat files; outer wrapper key distinguishes them.                        |
| `data/general_feats.json`                      | [models/feat_schema.json](../models/feat_schema.json)                                   | class feat slot choice → `_apply_effect()`                           | hand-authored                   |                                                                                                    |
| `data/spells/definitions/*.json`               | [models/spell_schema.json](../models/spell_schema.json)                                 | `_load_spell_definition()` (on-demand lookup)                        | hand-authored                   | 383 spell files; no fetcher.                                                                       |
| `data/spells/class_lists/*.json`               | [models/spell_class_list_schema.json](../models/spell_class_list_schema.json)           | `apply_choice("spells")` / `calculate_spellcasting_stats()`          | `update_spells.py`              | `update_spells.py` writes straight into `data/`. See the asymmetry section below.                  |
| `data/equipment/weapons.json`                  | [models/weapon_schema.json](../models/weapon_schema.json)                               | `apply_choice("equipment_selections")` → `equipment_manager.py`      | hand-authored                   | `damage_type` admits `"Special"` only for Net; see schema TODO.                                    |
| `data/equipment/armor.json`                    | [models/armor_schema.json](../models/armor_schema.json)                                 | `apply_choice("equipment_selections")` → `equipment_manager.py`      | hand-authored                   | Single schema covers body armor (ac_base/ac_formula) and shields (ac_bonus).                       |
| `data/equipment/weapon_masteries.json`         | [models/weapon_mastery_schema.json](../models/weapon_mastery_schema.json)               | `calculate_weapon_mastery_stats()`                                   | hand-authored                   |                                                                                                    |
| `data/equipment/adventuring_gear.json`         | [models/adventuring_gear_schema.json](../models/adventuring_gear_schema.json)           | `apply_choice("equipment_selections")` → `equipment_manager.py`      | hand-authored                   | `weight` admits the literal `"Variable"` only for catch-alls like `Musical Instrument`; see schema TODO. |
| `data/fighting_styles.json`                    | [models/fighting_style_schema.json](../models/fighting_style_schema.json)               | `apply_choice("fighting_style")` → `_apply_effect()`                 | hand-authored                   | Some styles have `notes` instead of `effects` (reaction-based).                                    |
| `data/eldritch_invocations.json`               | [models/eldritch_invocation_schema.json](../models/eldritch_invocation_schema.json)     | `apply_choice("eldritch_invocation_selections")` → `_apply_effect()` | hand-authored                   | `effects` are added in Phase 7 (`D0-1`) without re-authoring the schema.                           |
| `data/maneuvers.json`                          | [models/maneuver_schema.json](../models/maneuver_schema.json)                           | `apply_choice("maneuvers")` (name recorded); `grant_maneuver` effect → `_apply_effect()` (from Battle Master features) | hand-authored | Description-only per schema; individual maneuver mechanics are runtime interactions. Sheet recording is via `grant_maneuver` + `grant_superiority_dice` effects on the Battle Master subclass. |
| `data/languages.json`                          | [models/languages_schema.json](../models/languages_schema.json)                         | `_apply_effect("grant_language")` (species/bg/feat path); `apply_choice("languages_chosen")` (wizard step) | hand-authored |                                                                                                    |
| `data/feature_override.json`                   | [models/feature_override_schema.json](../models/feature_override_schema.json)           | `feature_manager` (summary lookup)                                   | hand-authored                   | **Scheduled for deletion in Phase 8 (`D5`/`D6-2`)**; schema authored for its remaining lifetime.   |
| `data/trait_patterns.json`                     | [models/trait_patterns_schema.json](../models/trait_patterns_schema.json)               | `feature_manager` (heuristic fallback)                               | hand-authored                   | Heuristic fallback patterns; prefer explicit `effects` on new content.                             |

### Shared subschemas

| Subschema                                                                | Used by                                                                                                       |
|--------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| [models/_shared/effect.json](../models/_shared/effect.json)              | species, species_variants, backgrounds, feat (general/origin), fighting_styles, eldritch_invocations          |
| [models/_shared/choice.json](../models/_shared/choice.json)              | species (via `trait_entry`), feat, eldritch_invocations                                                       |
| [models/_shared/choice_effects.json](../models/_shared/choice_effects.json) | species (via `trait_entry`), feat, eldritch_invocations                                                    |
| [models/_shared/trait_entry.json](../models/_shared/trait_entry.json)    | species, species_variants                                                                                     |

### Legacy / non-active schemas

| File                              | Status        | Used by                               |
|-----------------------------------|---------------|---------------------------------------|
| `character_sheet_v2_schema.json`  | **Aspirational** — no producer or consumer was found in the codebase. Document the intended shape but do not assume any code reads or emits it today. |
| `example_character_v2.json`       | Reference     | Companion example for the v2 schema   |
| `README.md`                       | Schema notes  | Reference                             |

Run `python validate_data.py` to validate `data/` against the active schemas. It exits non-zero on any failure **and** refuses to run if any JSON file under `data/` is not covered by the `CATEGORIES` manifest in [validate_data.py](../validate_data.py) (or explicitly listed in `EXCLUDED_FILES`).

## Wiki Generation Pipeline

Three updater scripts pull from `http://dnd2024.wikidot.com/` and cache results locally. **They are not symmetrical.**

| Script              | Reads                                  | Writes to                                                | Notes |
|---------------------|----------------------------------------|----------------------------------------------------------|-------|
| `update_classes.py` | Wiki class + subclass pages            | **`wiki_data/classes/`** and **`wiki_data/subclasses/<class>/`** | Cache only. Prints: *"Create a separate script to transform `wiki_data → data/`"*. The application-ready `data/classes/<n>.json` and `data/subclasses/<class>/<sub>.json` are **hand-authored** from the cache. |
| `update_species.py` | Wiki species pages                     | **`wiki_data/species/`**                                  | Cache only. Same pattern as classes. Application-ready `data/species/<n>.json` and `data/species_variants/<v>.json` are hand-authored. |
| `update_spells.py`  | Wiki class spell-list pages            | **`data/spells/class_lists/<class>.json` directly**       | **Asymmetry — writes straight into `data/`.** Three `write_text` calls in the script bypass `wiki_data/` entirely. There is no transform step for spell lists. |

### The spell-fetcher asymmetry — what it means in practice

- Re-running `update_spells.py --class wizard` will **overwrite `data/spells/class_lists/wizard.json` in place** (only with `--overwrite`, but still in the production data tree). Diff before committing.
- There is no parallel cache, so any manual edits to a class spell list are lost on re-fetch.
- `data/spells/definitions/*.json` (~383 files) has **no fetcher at all** — every individual spell is hand-authored.
- A future cleanup should either (a) align `update_spells.py` with the `update_classes.py` / `update_species.py` pattern (write to `wiki_data/spells/` and add a transform), or (b) decide explicitly that spell lists are wiki-mirrored and document that the application-ready file *is* the cache.

## Loading Data at Runtime

`modules/data_loader.py` provides `DataLoader(data_dir=...)` which lazily loads:

- `classes`, `subclasses` (per class), `species`, `backgrounds`, `feats`
- Equipment files via direct path access (`data/equipment/<kind>.json`)
- Spell lists / definitions via direct path access

The catalog and character endpoints share a single `DataLoader` instance; previewers re-instantiate it with the absolute `data/` path because they need to read fresh data without polluting the app-level cache.

## Adding Content

Generic procedure:

1. Verify the rule against D&D 2024 (use `wiki_data/` cache or fetch from `http://dnd2024.wikidot.com/`).
2. Add or update the JSON file in the relevant `data/` subfolder.
3. Encode mechanical benefits as `effects` arrays — never hardcode in Python. See [docs/FEATURE_EFFECTS.md](FEATURE_EFFECTS.md) and [.github/instructions/effects-system.instructions.md](../.github/instructions/effects-system.instructions.md).
4. Run `python validate_data.py`.
5. Add or update tests under `tests/`.

For batch additions, the `add-game-content` and `implement-class-feature` skills automate steps 1–5.

## See Also

- [docs/Architecture.md](Architecture.md)
- [docs/APIContract.md](APIContract.md)
- [docs/FEATURE_EFFECTS.md](FEATURE_EFFECTS.md)
- [.github/instructions/data-schemas.instructions.md](../.github/instructions/data-schemas.instructions.md)
- [.github/instructions/effects-system.instructions.md](../.github/instructions/effects-system.instructions.md)
