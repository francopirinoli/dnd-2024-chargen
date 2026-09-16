# Code Quality, Consistency & Reconstruction Parity Audit

**Date:** 2026-05-21
**Scope:** Backend (`modules/`, `routes/api/`), frontend choice controls (`frontend/src/`), rebuild-from-choices parity, and the data layer (`data/`, `models/`).
**Method:** Four parallel read-only deep dives (backend, frontend, parity, data layer). Findings consolidated, deduplicated, and prioritized below.

> This document is the source of truth for the upcoming fix plan. Detailed file/line references are inline. Do not re-run the analysis; extend this report instead.

---

## Executive Summary

The architecture is fundamentally sound: a single Python `CharacterBuilder` is the source of truth, and **the wizard and the rebuild-from-choices path share the same entry point** (`POST /api/v1/character/build` → `apply_choices()`). Each step's preview also re-runs `apply_choices()` over the full accumulated state, so there is no separate "incremental" engine — that property eliminates a whole class of divergence bugs.

However, the audits surfaced a consistent pattern: **the same logical decision is represented in two or three different shapes/locations**. Where this happens, defensive code accumulates, naming-based fallbacks creep in, and silent data loss becomes possible. The recently-fixed Fighting Style bug is one instance of this pattern, and several more remain.

The three highest-impact problems are:

1. **Frontend↔backend choice schema is informal.** Several declared `ChoicesMade` fields are never populated (the frontend writes the same data under different keys, or at the top level). Most dangerous: **species trait choices are stored as flat top-level keys** instead of under `species_trait_choices`, which can cause silent loss of trait bonuses.
2. **Effects are applied via multiple competing paths** (`_apply_effect`, `_apply_choice_effects`, `_apply_trait_effects`, and ad-hoc reads of `applied_effects` inside `calculate_weapon_attacks`). This was the root cause of the Fighting Style double/missed application; analogous risk exists for other choice-driven effects.
3. **No round-trip equality test.** The architecture guarantees parity *in principle*, but there is no test that asserts "rebuild from exported `choices_made` == original character." Multiclass and combined species+background skill replacements are the most likely places this would break.

The data-layer audit (added 2026-05-21) confirmed the same pattern at the JSON level and surfaced two more silent player-data-loss bugs of the same class as the pre-fix Fighting Style. Both are restricted to the **sheet-affecting subset** of each category — in-play-only mechanics (reactions, GM-adjudicated effects, narrative abilities) are intentionally out of scope, see the box at the top of "Data Layer Issues":

- **Eldritch invocations whose RAW benefit changes a sheet field carry zero machine-readable effects** — e.g. `Beguiling Influence` (skill proficiencies), `Agonizing Blast` (damage), `Devil's Sight`. The non-mechanical invocations (`Mask of Many Faces` description, etc.) are fine as prose.
- **Battle Master maneuver *selection* is not recorded on the sheet.** Individual maneuver mechanics (push/trip/parry) are play-time and don't need effects; the *list of chosen maneuvers* does need to be recorded.

The data-layer audit also found that **roughly two-thirds of `data/` has no schema at all** — `validate_data.py` only covers classes and subclasses. Species, lineages, backgrounds, feats, spells, equipment, and all external reference files are unvalidated, which is the root cause of most of the shape-drift findings in this report.

---

## P0 — Blocking Correctness Risks

### P0-1. Species trait choices are stored under the wrong key

- **Where:** [frontend/src/components/steps/SpeciesStep.tsx](frontend/src/components/steps/SpeciesStep.tsx#L543) writes each trait choice as a flat top-level key (`setChoice(traitName, value)` → `choicesMade["Draconic Resilience"] = "Red"`).
- **Contract says:** [frontend/src/lib/api.ts](frontend/src/lib/api.ts#L25-L44) declares `species_trait_choices?: Record<string, string>` for exactly this purpose.
- **Backend reads:** `apply_choices()` resolves trait choices either via the catch-all dynamic key handler **or** via `species_trait_choices`, depending on which path is hit first. The dynamic-key path works only because backend lookups happen to tolerate the flat shape — it is not contractually guaranteed.
- **Problem this creates:**
  - Round-trip loss: exported characters whose trait values were stored at the top level can collide with future top-level keys (e.g., a future `"Telepathy"` choice key clashing with a top-level `Telepathy` boolean).
  - Frontend ↔ backend interface drift: anyone reading the TS interface assumes traits are nested and writes consumers (typed clients, tests) that don't see the data.
  - Silent failure: a typo in a trait name produces no error; the value just vanishes.
- **Complexity:** Small. One side picks the canonical shape (recommend nested `species_trait_choices`), the other migrates. Add a backend normalizer that lifts legacy flat keys into the nested object for backwards compatibility with existing saved characters.

### P0-2. No incremental-vs-batch / round-trip equality test exists

- **Where:** `tests/integration/` has per-archetype recreation tests (Dwarf Cleric, Wood Elf Fighter, Tiefling Warlock) but none compares two builds for full equality.
- **Problem this creates:** The architectural guarantee that "wizard = rebuild" is *unverified*. The Fighting Style bug existed undetected because tests asserted feature presence, not effect application. Future regressions in `apply_choices()` ordering, in `to_character()` re-injection of derived fields, or in normalization will not be caught.
- **Complexity:** Small (one parametrized test using the sample characters under `test_characters/` + `data/example_complete_character.json`). Assert `json.dumps(c1, sort_keys=True) == json.dumps(c2, sort_keys=True)` after stripping volatile fields (timestamps, IDs).

### P0-3. `calculate_weapon_attacks()` re-derives effects from `applied_effects`

- **Where:** [modules/character_builder.py](modules/character_builder.py) lines ~4822–4905. The method walks `applied_effects` looking for `bonus_attack`, `bonus_damage`, `great_weapon_fighting`, `two_weapon_fighting_modifier`, and Dueling-by-name.
- **Problem this creates:** Two parallel mental models of effects: (a) effects mutate stat fields directly via `_apply_effect`, (b) effects are *re-read* at calculation time. If an effect is applied via path (a) and also present in `applied_effects`, weapon math double-counts. The Fighting Style fix added a short-circuit in `_apply_choice_effects` precisely to keep this from doubling — but the underlying duality is still there.
- **Complexity:** Medium. Decide one model: either effects are applied imperatively and `applied_effects` is *audit only* (current intent), or all derived calculations consume `applied_effects` declaratively (cleaner, but bigger refactor). Recommend the first; remove the reads from `calculate_weapon_attacks()` and store the relevant deltas on the weapon entries when the effect is applied.

---

## P1 — High Impact: Choice-Layer Divergence

### P1-1. Dual-write of class identity (multiclass array + legacy flat fields)

- **Where:** [frontend/src/components/steps/ClassStep.tsx](frontend/src/components/steps/ClassStep.tsx#L461-L469) writes `classes`, `class`, `level`, and `subclass` simultaneously. The backend normalizer ([routes/api/character.py](routes/api/character.py#L288-L402)) accepts either.
- **Problem this creates:** Ghost data. If the user reduces a multiclass build, the flat fields are not cleared and resurface on reload through fallback paths. The frontend store also has class-change cascade logic ([characterStore.ts L79-L88](frontend/src/store/characterStore.ts#L79)) that only handles part of this state.
- **Complexity:** Medium. Pick `classes[]` as canonical, remove all writes to the flat keys in the frontend, keep the backend normalizer **read-only** (accept both for inbound legacy data, never emit both).

### P1-2. `ChoicesMade` interface declares fields that are never populated

- **Where:** [frontend/src/lib/api.ts](frontend/src/lib/api.ts#L25-L44). Declared but unused: `spells`, `cantrips`, `languages_chosen`, `species_trait_choices` (see P0-1), `species_feat_choices`, `origin_feat`. The actual storage uses `spell_selections` (nested), `languages`, dynamic per-feat keys.
- **Problem this creates:** False contract. Anyone reading the TS interface and writing a consumer (export tooling, future Discord bot) will get an empty result. Encourages duplicate naming when new features land.
- **Complexity:** Small (delete unused fields, document the dynamic-key catch-all).

### P1-3. Dynamic choice keys generated independently on both sides

- **Where:** Frontend generates feat sub-choice keys ([FeatDropdownPicker.tsx L394](frontend/src/components/wizard/FeatDropdownPicker.tsx#L394), [FeatChoicesPicker.tsx L331](frontend/src/components/wizard/FeatChoicesPicker.tsx#L331)) — usually using the server-provided `choices_made_key`, but with a fallback that synthesizes a name. Backend resolves choices via `_resolve_choice_value()` which tries **4 key variants** ([modules/character_builder.py](modules/character_builder.py) ~line 4122).
- **Problem this creates:** A 4-variant lookup is a code smell. Each variant exists because some control somewhere generates a slightly different key. New choices added in JSON can quietly fail if their generated key matches none of the variants.
- **Complexity:** Medium. The server's `preview-step` already returns the canonical `choices_made_key` for each sub-choice; make that the **only** source. Treat absence of `choices_made_key` as a JSON-data bug, fail loud in dev.

### P1-4. `additional_ability_modifiers` is compacted asymmetrically

- **Where:** [AbilitiesStep.tsx L274](frontend/src/components/steps/AbilitiesStep.tsx#L274) strips zero entries before sending. Backend then iterates declared abilities and reads with `.get(ability, 0)` in most places, but not all.
- **Problem this creates:** `undefined + 0 = NaN` on any code path that doesn't default. Bug surfaces only for characters with partial modifier maps.
- **Complexity:** Trivial. Either always send the full 6-ability map, or audit backend reads to ensure `.get(..., 0)` is used everywhere.

### P1-5. `LanguagesStep` mutates state from a server-suggestion endpoint

- **Where:** [LanguagesStep.tsx L54](frontend/src/components/steps/LanguagesStep.tsx#L54) calls `api.character.randomLanguages(choicesMade)` and writes the result into `choicesMade`. This is the only "ad-hoc choice mutation" endpoint in the frontend.
- **Problem this creates:** Breaks the "frontend sends raw choices, backend calculates" contract from the *other* direction — the backend is now suggesting choices. Acceptable, but should be named/documented as such (it's a *suggestion* endpoint, not a *mutation* endpoint) so future contributors don't add similar one-offs.
- **Complexity:** Trivial (rename + doc).

---

## P2 — Effects System & Backend Code Quality

### P2-1. Effects applied through three competing dispatchers

- **Where:** `modules/character_builder.py`:
  - `_apply_effect()` (line ~1215) — generic dispatcher on `effect['type']`.
  - `_apply_trait_effects()` — wraps `_apply_effect` for class/subclass features parsed from `features_by_level`.
  - `_apply_choice_effects()` (line ~3249) — three-way lookup: external file → feat data → internal class data.
  - Plus inline reads of `applied_effects` in `calculate_weapon_attacks()` (see P0-3) and `calculate_ac_options()`.
- **Problem this creates:** Each new effect-bearing concept must be wired into the right dispatcher, and the wiring is not obvious. The Fighting Style bug was a wiring miss between `_apply_choice_effects` (external file) and the calculation reading `applied_effects`. Other choice types that resolve to external files (e.g., maneuvers, eldritch invocations) follow the same pattern and are at similar risk.
- **Complexity:** Medium. Collapse to one dispatcher that takes `(effect, source_label)` and one *resolver* that turns "this choice in this slot" into a list of effects regardless of source (inline JSON, external file, feat data). Document the rule: *features and choices both emit effects; only `_apply_effect` applies them*.

### P2-2. Hardcoded feature/class names in branching logic

- **Where (representative):**
  - `if normalized_trait_name == "ability score improvement": return` ([character_builder.py](modules/character_builder.py) ~L1047) — silently skips ASI feature.
  - `if trait_name == "Spellcasting":` (~L1164) — name-based.
  - `subclass_placeholder = f"{class_name.strip().lower()} subclass"` — format-coupled.
  - Dueling fighting-style special-cased by name in weapon-attack math (~L4851).
  - `routes/api/character.py` L65–70 branches on `ctype in ("skills", "tools")` to filter multiclass choices.
- **Problem this creates:** Direct violation of the project rule "branch on `effect['type']`, never on `feature_name == '...'`". Renaming or translating these strings silently breaks behavior. Each is a future maintenance trap.
- **Complexity:** Medium. Replace with explicit schema markers: `feature_kind: "asi" | "subclass_pick" | "spellcasting_setup"` on the JSON feature entry, dispatched by kind.

### P2-3. `feature_override.json` is used as a runtime escape hatch

- **Where:** [modules/character_builder.py](modules/character_builder.py) ~L974 (`_get_class_feature_override`). Supports `hidden: true` (skip application) and `pdf_summary` (replace description).
- **Problem this creates:** A side-channel that bypasses the class/subclass JSON. Two places to look when a feature behaves unexpectedly. Easy to "fix" a bug by adding an override instead of correcting the underlying data.
- **Complexity:** Small. Migrate existing overrides into the corresponding class/subclass JSON files as `hidden` and `pdf_summary` fields on the feature entry, then delete the file and its loader.

### P2-4. Three places store spell metadata

- **Where:** `character_data["spells"]["always_prepared"]`, `character_data["spells"]["prepared"]`, and `character_data["spell_metadata"]`. Each mutation must update all three; clear operations iterate all three.
- **Problem this creates:** Classic desync risk. Already requires defensive multi-dict update on grant ([~L1328](modules/character_builder.py#L1328)) and on subclass-spell clear (~L1749).
- **Complexity:** Medium. One owning dict (`spell_metadata` keyed by spell name with all attributes), and the others become *views* derived in `to_character()`.

### P2-5. Missing handlers for documented effect types

- **Where:** `docs/FEATURE_EFFECTS.md` documents `bonus_hp`, `bonus_ac`, `grant_weapon_mastery` as first-class effects. The `_apply_effect()` dispatcher does not handle them generically:
  - `bonus_ac` is only consumed in `calculate_ac_options()` (~L2392) — fine but not symmetric with other effects.
  - `bonus_hp` is only handled in the multiclass HP breakdown path (~L4005+) — not as a generic feature effect.
  - `grant_weapon_mastery` does not appear in the dispatcher at all (frontend ships selections via `weapon_mastery_selections`; the *grant* effect type is undefined).
- **Problem this creates:** Authors adding new features per the FEATURE_EFFECTS docs cannot rely on the documented types working. Silent no-ops.
- **Complexity:** Small to Medium per type. Implement each handler or strike the type from the docs.

### P2-6. Validation gaps allow silent typos

- `_apply_effect()` does not error on unknown `effect['type']`.
- `apply_choice()` does not error on unknown keys (it stores them in `choices_made` and they are simply never read).
- `features_by_level` shape is validated defensively at runtime instead of at load.
- **Complexity:** Small. Add a strict mode (default-on in tests/dev) that raises on unknown effect type and unknown top-level choice key. Validate `features_by_level` shape in `data_loader.py` once.

### P2-7. Dead and overlapping code in `modules/`

- **Unused modules:** `EquipmentManager`, `FeatureManager` (registry never populated), most of `VariantManager`.
- **Duplicated logic:** `_clear_species_features` vs `_clear_lineage_features` (~80% overlap); `_clear_background_features` has three near-identical loops (skills/tools/languages) that should be one `_remove_proficiencies_by_source(category, source)`.
- **No-op handlers:** Legacy `spellcasting` and `weapon mastery` choice handlers that return `True` without doing anything; `grant_cantrip_choice` and `alternative_ac` cases that `pass`.
- **Problem:** New contributors can't tell what's load-bearing. Effort is wasted maintaining mental models of code that doesn't run.
- **Complexity:** Small. Delete what's unused; extract the proficiency-by-source helper.

### P2-8. Build pipeline is four passes deep

- **Where:** `apply_choices()` ([~L4069–L4160](modules/character_builder.py#L4069-L4160)) — ordered first pass, regex-sorted second pass, third pass for species skill replacements, fourth for multiclass rows.
- **Problem this creates:** Implicit ordering. Works today but is fragile and undocumented. The third-pass placement of species skill replacements exists specifically because earlier passes would resolve them incorrectly — that constraint should be encoded, not implicit.
- **Complexity:** Small. Add a docstring/diagram, plus asserts that earlier passes have completed required state before later ones run.

---

## P3 — Frontend Architecture Smells

### P3-1. Client-side filtering of always-prepared spells

- [ClassAdvancedChoices.tsx L312](frontend/src/components/wizard/ClassAdvancedChoices.tsx#L312) removes always-prepared spells from the player's selection client-side. This is a derived calculation creeping into the UI.
- **Problem:** Server is the authority on what's always-prepared. If they diverge (different list versions, future subclass overrides), UI silently drops the wrong items.
- **Complexity:** Small. Move filter to backend `derived` endpoint output; UI just renders.

### P3-2. No Zod (or equivalent) validation on `choicesMade` before send

- **Problem:** All schema mismatches surface as silent server-side ignore or as opaque 500s. Combined with P1-2 (false interface fields), it's easy to ship a control that silently does nothing.
- **Complexity:** Medium. Define a Zod schema mirroring the canonical `ChoicesMade` (post P1-2 cleanup), validate at the api-client boundary.

### P3-3. No post-build round-trip assertion in the client

- After `POST /character/build`, the frontend never checks that submitted choices show up in the returned character.
- **Complexity:** Small. In dev mode, log a warning when a key in `choicesMade` does not appear in `character.choices_made` after build.

---

## Data Layer Issues

Findings from a dedicated audit of `data/` and `models/`. Each item carries its own priority (P0–P3) by impact — they are grouped here for locality, not because they share a single severity. IDs are prefixed `D` to avoid colliding with P0/P1/P2/P3 IDs above.

> **Scope of "missing effects"**
>
> This is a **character builder**, not an interactive play tool. A structured `effects` array is required only when a feature **changes the rendered character sheet** — stats, AC, HP, attack rolls, damage, proficiencies, expertise, saves, resistances, speed, darkvision, known/prepared spells, slot counts, etc. Features that only matter *during play* (spending a reaction, optional triggers, narrative abilities, GM-adjudicated effects) do not need an `effects` array; appearing in the feature list with a clear description is sufficient.
>
> **Example (no effect needed):** Lucky (Origin Feat) grants advantage on an attack/save/check when you spend a luck die. The sheet shows the feature and the description; no roll or stat changes when the character is built.
>
> **Example (effect needed):** Beguiling Influence grants proficiency in Deception and Persuasion. Proficiencies appear on the sheet and change skill modifiers — this requires `grant_skill_proficiency` effects.
>
> A finding labelled "missing effects" in this section is only a defect if the underlying RAW change would alter a visible field on the sheet. Triage each prose-only entry against this rule before assuming it needs migration.

### D0-1. Eldritch invocations with sheet-affecting mechanics have zero machine-readable effects — P0

- **Where:** [data/eldritch_invocations.json](../data/eldritch_invocations.json). 32 entries total; the P0 subset is the ones whose RAW benefit changes a sheet field.
- **Sheet-affecting invocations (require `effects`):**
  - `Beguiling Influence` — `grant_skill_proficiency` (Deception, Persuasion).
  - `Eldritch Mind` — `grant_save_advantage` on Constitution saves to maintain concentration.
  - `Devil's Sight` — darkvision-equivalent in magical darkness (sheet annotation on the Senses line).
  - `Armor of Shadows`, `Fiendish Vigor`, `Mask of Many Faces`, `Misty Visions`, `Whispers of the Grave`, etc. — grant at-will spells (`grant_spell_at_will`).
  - `Agonizing Blast` — `bonus_spell_damage_ability_mod` on Eldritch Blast (adds Cha to damage).
  - `Eldritch Spear` — `bonus_spell_range` on Eldritch Blast.
  - `Repelling Blast` — sheet annotation on Eldritch Blast (forced movement on hit).
  - Pact-specific invocations granting proficiency in additional weapons / armor.
- **Out-of-scope invocations (description-only is fine):** invocations whose benefit is purely in-play (free use of a reaction, GM-adjudicated narrative effects, ritual-cast-without-prep behavior that doesn't change the prepared list).
- **Problem this creates:** Identical shape to fighting styles before they were fixed. When a Warlock selects a sheet-affecting invocation, nothing is granted — the choice resolves to a name but the dispatcher has no effects to apply.
- **Complexity:** Medium. Adopt the fighting-style external-source pattern; add `effects` to the sheet-affecting subset; route through the same resolver. Several invocations need new effect types (`grant_spell_at_will`, `bonus_spell_damage_ability_mod`, `bonus_spell_range`).

### D0-2. Battle Master maneuver *selection* is not recorded on the sheet — P0

- **Where:** [data/subclasses/fighter/battle_master.json](../data/subclasses/fighter/battle_master.json) — 21 maneuvers under `maneuvers: {…}`, each a bare description.
- **Sheet impact:** Most individual maneuver effects (push, trip, disarm, parry damage reduction) are spent-resource reactions/bonus actions resolved at play — those do **not** need per-maneuver `effects` arrays under the scope rule. **What the sheet does need** is the *list of chosen maneuvers* and the superiority-die metadata (count, die size) so the player can read what they have access to.
- **Problem this creates:** The class chooses 3 maneuvers via `source.type: "internal"`, but no handler records the chosen names anywhere. The sheet shows "Combat Superiority" but no list of maneuvers known.
- **Complexity:** Small. Either (a) add a `grant_maneuver` effect type that pushes the chosen maneuver into a `maneuvers_known` array on the character (no per-maneuver mechanical effects needed), or (b) extract maneuvers to a top-level `data/maneuvers.json` and use the external-source pattern; the maneuver entries can stay description-only.

### D0-3. Two-thirds of `data/` has no schema — P0

- **Where:** `validate_data.py` validates classes (12) and subclasses (48). Unvalidated: all 10 species, 8 lineages, 18 backgrounds, 268 spell definitions, 8 spell class lists, both feat files, fighting styles, invocations, all 4 equipment files, languages, `feature_override.json`, `trait_patterns.json`.
- **Problem this creates:** Every shape inconsistency below could have been caught at load but wasn't. Contributors get no signal when they add malformed JSON. Root cause for D1/D3.
- **Complexity:** Medium. Author one schema per unvalidated category, extend `validate_data.py` to discover and apply them.

### D0-4. `grant_spell` effects reference undefined or typo'd spells — P0 (typos) / P1 (genuinely missing)

- **Where (typos — P0, trivial fix):** [data/subclasses/cleric/life_domain.json](../data/subclasses/cleric/life_domain.json) and others reference `Power Word: Heal` / `Power Word: Kill` with a colon; definitions store the names without the colon and the files are `power_word_heal.json` / `power_word_kill.json`. The lookup silently falls back to level=1 metadata.
- **Where (missing definitions — P1, small effort):** `Fount of Moonlight` (Circle of the Moon), `Summon Dragon` (Draconic Sorcery), `Yolande's Regal Presence` (Oath of Glory), `Summon Construct` (Aberrant / Clockwork Sorcery).
- **Problem this creates:** Spell appears on the sheet but with no metadata. UI cannot look up casting time / range / components. Combined with no schema for `data/spells/`, no test catches this today.
- **Complexity:** Trivial for typos; Medium to author the 5 missing definitions.

### D1-1. Three competing shapes for "mechanical benefit" — P1

- **Where:** Same logical concept written three ways:
  - **Structured `effects` array** — classes, subclasses, species, lineages, feats.
  - **Flat top-level keys** (`skill_proficiencies`, `tool_proficiencies`, `feat`, `languages`) — backgrounds.
  - **Pure prose** — invocations, ~half of class features, all flavor traits.
- **Problem this creates:** Three import paths in `CharacterBuilder`, three mental models for contributors, undefined boundary between when to use which. A new background contributor copies `acolyte.json`'s flat keys; a new feat contributor copies `Tough`'s `effects` array; nothing tells them which is canonical.
- **Complexity:** Medium. Pick the `effects` array as canonical and migrate, or keep flat keys for backgrounds but mark that as deliberate and forbid new ad-hoc keys elsewhere.

### D1-2. Species `darkvision` vs `darkvision_range` drift — P1

- **Where:** [data/species/dwarf.json](../data/species/dwarf.json), [elf.json](../data/species/elf.json), [gnome.json](../data/species/gnome.json), [aasimar.json](../data/species/aasimar.json), [dragonborn.json](../data/species/dragonborn.json) use `darkvision`; [orc.json](../data/species/orc.json), [tiefling.json](../data/species/tiefling.json) use `darkvision_range`; [human.json](../data/species/human.json), [goliath.json](../data/species/goliath.json), [halfling.json](../data/species/halfling.json) use neither.
- **Problem this creates:** Either both keys are read silently, or only one is — in which case the orc/tiefling top-level value is ignored in favor of the `grant_darkvision` effect inside `traits.Darkvision`. The field's mere existence implies it's authoritative.
- **Complexity:** Trivial. Delete the redundant key; rely on `grant_darkvision` everywhere.

### D1-3. Species variants have no required shape — P1

- **Where:** [data/species_variants/rock_gnome.json](../data/species_variants/rock_gnome.json) and [forest_gnome.json](../data/species_variants/forest_gnome.json) lack `description` (sheet renders blank). High Elf / Wood Elf / Drow / Tiefling lineages each define a different mix of top-level keys (`spells_by_level`, `spellcasting_ability_choice`, `cantrip_replacement`, `darkvision`).
- **Problem this creates:** No required shape → missing fields go unnoticed; per-lineage rendering must defensively check every key.
- **Complexity:** Small. Author `species_variant_schema.json`; backfill the missing fields.

### D1-4. Backgrounds carry vestigial `languages: 2` — P2

- **Where:** all 18 files in [data/backgrounds/](../data/backgrounds/).
- **Problem this creates:** D&D 2024 backgrounds do not grant additional languages — that's a 2014-ism. The field is ignored by `LanguagesStep` but its presence misleads anyone reading the data.
- **Complexity:** Trivial. Delete the field.

### D1-7. Singular/plural inconsistency in effect properties — P2

- **Where:** `effect.skills: [...]`, `effect.tools: [...]`, `effect.proficiencies: [...]` (weapon/armor), `effect.languages: [...]` — different singular property names per category. `effect.damage_type` is singular even when granting multiple types (see [data/subclasses/druid/circle_of_the_stars.json](../data/subclasses/druid/circle_of_the_stars.json), 3 separate `grant_damage_resistance` entries for Bludgeoning/Piercing/Slashing).
- **Problem this creates:** Authoring friction; copy-paste of nearly identical effect blocks; no obvious target field name when adding a new grant.
- **Complexity:** Small. Allow `damage_types: [...]` array form; normalize in the dispatcher.

### D1-8. `effects` arrays live at 5 different nesting depths — P1 (root cause of P2-1)

- **Where:** Authoring locations: (1) top-level of a feat, (2) inside a class feature, (3) inside `choice_effects` keyed by chosen option, (4) inside a `choices` object, (5) inside a `source: "external"` file. All five are valid, all resolved by different code paths.
- **Problem this creates:** This is the data-layer counterpart of P2-1. Each location pairs with a different dispatcher entry point.
- **Complexity:** Folded into the P2-1 dispatcher consolidation. The fix here is to **document the 5 locations** in `data-schemas.instructions.md` so the dispatcher consolidation has a clear specification to satisfy.

### D2-1. Seven effect types are consumed out-of-band — P1 (subset of P0-3 / P2-1)

- **Where:** `bonus_damage`, `bonus_attack`, `bonus_ac`, `bonus_hp`, `great_weapon_fighting`, `two_weapon_fighting_modifier`, `unarmed_fighting` are present in JSON but `_apply_effect` does not handle them — they are re-read by `calculate_weapon_attacks()`, `calculate_ac_options()`, and `hp_calculator.py`.
- **Problem this creates:** Confirms the architectural risk in P0-3 with a precise count: **7 of the 28 used effect types** rely on out-of-band consumers. Each is a candidate for double application or for being missed entirely.
- **Complexity:** Resolved by the same dispatcher consolidation in P0-3 / P2-1.

### D2-2. No-op effect handlers — P2

- **Where:** `grant_cantrip_choice` ([modules/character_builder.py L1251](../modules/character_builder.py#L1251)) and `alternative_ac` ([L1492](../modules/character_builder.py#L1492)) handlers both `pass`. Used in data 4× for `alternative_ac`.
- **Problem this creates:** Looks handled but isn't; actual application happens in `calculate_ac_options()`. A reader can't tell from the dispatcher what the effect does.
- **Complexity:** Small. Either consolidate the logic into the dispatcher or document the deferred-handling pattern explicitly.

### D2-3. Documented effect types without handlers — P2 (data-side confirmation of P2-5)

- **Where:** `grant_spell_slots`, `grant_damage_immunity`, `grant_weapon_mastery` are in [docs/FEATURE_EFFECTS.md](FEATURE_EFFECTS.md) but have no handler and no data usage.
- **Complexity:** Small. Delete from docs or add handlers + usage.

### D3-4. Subclass-pick markers are stringly-typed — P2

- **Where:** Every class JSON has a feature like `"Wizard Subclass"` in `features_by_level` whose only job is to mark the level at which the player picks a subclass. The system hard-codes the convention `"<classname> subclass"` in code (see P2-2).
- **Problem this creates:** Renaming the placeholder string in JSON breaks the picker silently.
- **Complexity:** Small. Add `feature_kind: "subclass_pick"` to the feature entry; dispatch on the field, not the name.

### D3-5. ASI feature hidden inconsistently across classes — P2

- **Where:** [data/feature_override.json](../data/feature_override.json) hides `Ability Score Improvement` only for Fighter and Wizard. All 10 other classes display ASI as a regular feature.
- **Problem this creates:** Visible UI inconsistency — the same RAW feature appears on some class sheets and not others. No test catches it.
- **Complexity:** Small. Migrate to `feature_kind: "asi"` and let the wizard handle uniformly.

### D4-1. Lineage spell lists duplicated in both `effects` and `spells_by_level` — P1

- **Where:** [data/species_variants/high_elf.json](../data/species_variants/high_elf.json), [wood_elf.json](../data/species_variants/wood_elf.json), [drow.json](../data/species_variants/drow.json) declare the same spell grants twice — inside `traits["X Spells"].effects` and in a top-level `spells_by_level` block.
- **Problem this creates:** Whichever is read first wins; whichever is read second is a no-op duplicate today, but on edit the two will silently diverge — the exact pre-fix Fighting Style failure mode.
- **Complexity:** Small. Delete `spells_by_level`; the `effects` array is authoritative.

### D4-3. Maneuvers / metamagic / masteries lack the external-file pattern — P1

- **Where:** Fighting styles → external file ✅. Eldritch invocations → external file ✅ (but no effects, see D0-1). **Maneuvers → inline** in [data/subclasses/fighter/battle_master.json](../data/subclasses/fighter/battle_master.json). Metamagic doesn't exist yet but will land in the same shape. [data/equipment/weapon_masteries.json](../data/equipment/weapon_masteries.json) is external ✅ but mastery properties are pure prose with no `effects`.
- **Problem this creates:** Three concept types follow the external-source pattern, one doesn't — contributors copying battle_master will inline future choice menus too. Same anti-pattern surface as the original Fighting Style bug.
- **Complexity:** Small. Extract maneuvers to a top-level `data/maneuvers.json` with the same shape as `fighting_styles.json`; add `effects` to weapon masteries.

### D5. `feature_override.json` full inventory — P2 (refines P2-3)

- **Where:** Six entries in [data/feature_override.json](../data/feature_override.json) — Fighter (Second Wind `pdf_summary`, Action Surge `pdf_summary`, subclass placeholder `hidden`, ASI `hidden`), Wizard (subclass placeholder `hidden`, ASI `hidden`).
- **Problem this creates:** Two patterns conflated in one file: `hidden` markers for structural features (which should be `feature_kind` per D3-4/D3-5) and `pdf_summary` strings (which should be a sibling field on the feature). The asymmetric ASI hiding (D3-5) is the visible bug.
- **Complexity:** Small. Migrate all six entries to fields on the source JSON; delete the file and its loader.

### D6. Schema improvement proposals — various priorities

Concrete additions to `models/` that would prevent the patterns above from recurring. Detailed list in the data-axis raw audit; the headline changes are:

- **D6-1 (P0, Medium):** Author the missing schemas (species, lineage, background, feat, spell definition, spell class list, weapon, armor, weapon mastery, fighting style, eldritch invocation, languages, feature override).
- **D6-2 (P1, Small):** Add `feature_kind` enum (`normal | asi | subclass_pick | spellcasting_setup | subclass_feature_slot`) to feature entries in `class_schema.json` and `subclass_schema.json`. Resolves D3-4, D3-5, and the name-based branching in P2-2.
- **D6-3 (P2, Trivial):** Promote `hidden` and `pdf_summary` to first-class fields on the feature entry (replaces `feature_override.json`).
- **D6-4 (P1, Small):** Tight closed enum on `effect.type` (28 known types), referenced via `$ref` from feature/trait schemas. Catches typos at load; pairs with the dispatcher's strict-mode flag from P2-6.
- **D6-5 (P2, Small):** Stricter `background_schema.json`: require `feat` to reference an entry in `origin_feats.json`; require `skill_proficiencies` to be exactly 2; require `ability_score_increase.total == 3`; forbid `languages: 2`.
- **D6-6 (P3, Small):** Typed `$choice_ref` form to replace `"${1st_level_spell}"` string placeholders.
- **D6-7 (P3, Trivial):** Allow plural array forms (`damage_types: [...]`) where today multiple effects are emitted to grant a set.

### D7. Wiki drift — No systematic drift found

Spot checks of Dwarf, Elf, Battle Master, Warlock invocations, and Wizard `Arcane Recovery` against `wiki_data/` found that **where mechanics are present in `data/`, they match the D&D 2024 source.** The drift that exists is *absence* of structured mechanics for sheet-affecting features (D0-1, D0-2, D1-1), not incorrect ones. Description-only entries for play-time-only mechanics (e.g. Wizard `Arcane Recovery` short-rest slot recovery, Lucky-style spendable dice) are **intentional under the scope rule** and not findings. No P-level item.

---

## Resolution Complexity — Summary Table

| ID    | Issue                                                       | Priority | Complexity |
|-------|-------------------------------------------------------------|----------|------------|
| P0-1  | Species trait keys stored flat instead of nested            | P0       | Small      |
| P0-2  | No rebuild-equality / round-trip test                       | P0       | Small      |
| P0-3  | `calculate_weapon_attacks` re-reads `applied_effects`       | P0       | Medium     |
| P1-1  | Class dual-write (`classes` + `class`/`level`/`subclass`)   | P1       | Medium     |
| P1-2  | `ChoicesMade` interface declares unused fields              | P1       | Small      |
| P1-3  | Dynamic choice key generation diverges client/server        | P1       | Medium     |
| P1-4  | `additional_ability_modifiers` compaction asymmetry         | P1       | Trivial    |
| P1-5  | `randomLanguages` endpoint mutates choices from server      | P1       | Trivial    |
| P2-1  | Three competing effect dispatchers                          | P2       | Medium     |
| P2-2  | Hardcoded feature/class names in branching                  | P2       | Medium     |
| P2-3  | `feature_override.json` as runtime escape hatch             | P2       | Small      |
| P2-4  | Spell metadata stored in three places                       | P2       | Medium     |
| P2-5  | Documented effect types without handlers                    | P2       | Small/Med  |
| P2-6  | No strict validation for effect types & choice keys         | P2       | Small      |
| P2-7  | Dead modules / overlapping clear functions / no-op handlers | P2       | Small      |
| P2-8  | Four-pass undocumented `apply_choices()` ordering           | P2       | Small      |
| P3-1  | Client-side filtering of always-prepared spells             | P3       | Small      |
| P3-2  | No Zod validation on `choicesMade`                          | P3       | Medium     |
| P3-3  | No client-side post-build round-trip check                  | P3       | Small      |
| D0-1  | Eldritch invocations have zero `effects`                    | P0       | Medium     |
| D0-2  | Battle Master maneuvers have zero `effects`                 | P0       | Small/Med  |
| D0-3  | Two-thirds of `data/` has no schema                         | P0       | Medium     |
| D0-4a | `grant_spell` typo'd spell names (colon mismatch)           | P0       | Trivial    |
| D0-4b | `grant_spell` references missing spell definitions          | P1       | Medium     |
| D1-1  | Three competing shapes for mechanical benefits              | P1       | Medium     |
| D1-2  | Species `darkvision` vs `darkvision_range` drift            | P1       | Trivial    |
| D1-3  | Species variants have no required shape                     | P1       | Small      |
| D1-4  | Backgrounds carry vestigial `languages: 2`                  | P2       | Trivial    |
| D1-7  | Singular/plural inconsistency in effect properties          | P2       | Small      |
| D1-8  | `effects` arrays at 5 different nesting depths              | P1       | (in P2-1)  |
| D2-1  | 7 effect types consumed out-of-band                         | P1       | (in P0-3)  |
| D2-2  | No-op `grant_cantrip_choice` / `alternative_ac` handlers    | P2       | Small      |
| D2-3  | Documented effect types without handlers (data confirmation)| P2       | Small      |
| D3-4  | Subclass-pick markers are stringly-typed                    | P2       | Small      |
| D3-5  | ASI feature hidden inconsistently across classes            | P2       | Small      |
| D4-1  | Lineage spell lists duplicated in `effects` + `spells_by_level` | P1   | Small      |
| D4-3  | Maneuvers / weapon-mastery effects lack external-source pattern | P1   | Small      |
| D5    | `feature_override.json` to migrate (6 entries)              | P2       | Small      |
| D6-1  | Author 13+ missing schemas in `models/`                     | P0       | Medium     |
| D6-2  | Add `feature_kind` enum                                     | P1       | Small      |
| D6-3  | Promote `hidden` / `pdf_summary` to first-class fields      | P2       | Trivial    |
| D6-4  | Closed enum on `effect.type` (+ strict mode)                | P1       | Small      |
| D6-5  | Stricter background schema                                  | P2       | Small      |
| D6-6  | Typed `$choice_ref` placeholders                            | P3       | Small      |
| D6-7  | Allow plural array forms in effects                         | P3       | Trivial    |

Complexity legend: **Trivial** (single file, < 1h) · **Small** (few files, well-scoped) · **Medium** (cross-layer or refactor) · **Large** (architectural).

---

## What Should Change in HVE Assets

These are the documents/skills/agents that should be updated so the patterns above are enforced going forward. Each item names the file and the specific addition.

### Instructions (`.github/instructions/`)

1. **`effects-system.instructions.md`** — add a "**One Dispatcher Rule**" section:
   - All effects flow through `_apply_effect`. Never branch on feature/option names.
   - Choice-driven effects (fighting styles, maneuvers, invocations, metamagic) resolve their effect list via a single resolver and then call `_apply_effect`. No reading `applied_effects` from calculation methods.
   - Add a checklist for new effect types: schema entry, dispatcher handler, FEATURE_EFFECTS.md doc, test.

2. **`choice-reference.instructions.md`** — make the choice-key contract explicit:
   - Canonical key shape is whatever the server's `/preview-step` returns as `choices_made_key`. The frontend must use that exact string. No client-side key synthesis as primary path.
   - Forbid storing structured choices as flat top-level keys (the P0-1 case). All grouped choices live under a nested object (`species_trait_choices`, `spell_selections`, etc.).

3. **`data-schemas.instructions.md`** — expand significantly. Add:
   - The `feature_kind` enum (D6-2) and a rule that name-based branching for ASI / subclass-pick / spellcasting-setup features is forbidden.
   - `hidden` and `pdf_summary` as first-class feature properties (D6-3), replacing `feature_override.json`.
   - The closed `effect.type` enum (D6-4) and a list of the **5 valid `effects`-array authoring locations** (D1-8) with the matching dispatcher entry point for each.
   - Forbid `darkvision_range` as an alias for `darkvision` on species (D1-2).
   - Forbid `languages: <int>` on backgrounds (D1-4) and the asymmetric ASI override pattern (D3-5).
   - A rule: any new "pick one from a list" mechanic (maneuvers, metamagic, future class options) MUST use the external-source pattern from day one, not inline maps (D4-3).

4. **`character-builder-api.instructions.md`** — document the `apply_choices()` four-pass ordering, the rationale for each pass, and the invariant that wizard preview and `/character/build` use the same code path. Include the rebuild-equality test as part of the API contract.

5. **`frontend-architecture.instructions.md`** — strengthen the "no calculation in the frontend" rule with concrete anti-patterns surfaced here:
   - Do not filter server-derived lists client-side (always-prepared spells).
   - Do not synthesize choice keys; use server-provided `choices_made_key`.
   - Do not dual-write the same logical decision under multiple keys.
   - Validate `choicesMade` with Zod before sending.

6. **`testing.instructions.md`** — require a round-trip equality test for every new character archetype added to `test_characters/`, plus an "incremental vs batch" parity test as a standing fixture.

### Skills (`.github/skills/`)

7. **`implement-feature/SKILL.md`** — add a "Wiring Checklist" step:
   - Does this feature emit effects? They go in JSON under `effects`.
   - Is this a choice with its own effect file (like fighting styles)? Use the external-source pattern; verify the dispatcher resolves it through `_apply_choice_effects` only.
   - Did you add a name-based branch anywhere? Stop and use `feature_kind` / `effect['type']` instead.
   - Did you add a frontend key? It must come from the server's `choices_made_key`.

8. **`validate-character/SKILL.md`** — extend to run the round-trip test: rebuild from the character's exported `choices_made`, assert equality with the original `character` dict.

9. **`add-game-content/SKILL.md`** — add a verification step that any external choice file (like `fighting_styles.json`) declares its source explicitly in the referencing class JSON (`source_config.type = "external"`), and that the dispatcher path is exercised by at least one test. Also: every new content entry that grants a **sheet-affecting** mechanical benefit MUST include a structured `effects` array. Play-time-only features (reactions, spendable dice, GM-adjudicated narrative) may remain description-only. The reviewer's first question is *"does selecting this change any field on the rendered character sheet?"* — if yes, `effects` is required; if no, prose is sufficient.

10. **`validate-data` workflow / `validate_data.py`** — not currently a skill, but should be. Extend `validate_data.py` to apply the new schemas (D0-3, D6-1) to *all* file categories, and add a CI gate so unschema'd categories fail the build.

11. **New skill: `audit-choice-paths`** — a workflow skill that, given a choice type, traces the full path: UI control → store key → API payload → backend resolver → effect dispatcher → returned character field. Used whenever a "my choice doesn't take effect" bug appears. (This is exactly the workflow that surfaced the Fighting Style bug; codifying it makes the next one faster.)

### Agents (`.github/agents/`)

12. **`architect.md`** — add to the routing rules: any feature that introduces a new *choice type* or a new *effect type* triggers a mandatory consultation with the `data-completeness` agent before merge, to confirm the dispatcher, schema, and test all exist.

13. **`frontend.md`** — explicitly forbid synthesizing choice keys or filtering server-provided lists; require Zod validation at the api-client boundary (mirrors the instruction change in item 5).

14. **`backend.md`** — explicitly forbid `if feature_name ==` / `if choice_value ==` style branching; require new effect types to land with a handler in `_apply_effect`, a test, and a `FEATURE_EFFECTS.md` entry in the same PR.

15. **`data-completeness.md`** — promote from an auditing-only role to also gating new content: every PR adding to `data/` runs `validate_data.py` (post D0-3 expansion) and is rejected if any new entry grants a mechanical benefit in prose without an `effects` array.

### Docs (`docs/`)

16. **`Architecture.md`** — add the build pipeline diagram (four passes) and the rebuild-equality invariant.
17. **`APIContract.md`** — replace the current `ChoicesMade` documentation with the canonical post-P1-2 shape; list every key, who writes it, what nesting it uses. Mark dynamic keys explicitly.
18. **`FEATURE_EFFECTS.md`** — remove the effect types without handlers or usage (`grant_spell_slots`, `grant_damage_immunity`, `grant_weapon_mastery` per D2-3), or tag them "Status: not yet implemented" so authors don't rely on them. Document the 5 authoring locations (D1-8) and the new effect-type enum (D6-4).
19. **`DataFiles.md`** — add a per-category table: which files are validated, which schema, which dispatcher consumes the `effects`, which external-source pattern applies (or doesn't). Currently no such overview exists.

---

## Suggested Fix Sequencing (for the upcoming plan)

A reasonable order, keeping each phase small and verifiable:

1. **Land P0-2** (rebuild equality test) first — gives every subsequent change a safety net.
2. **Land P0-1** (species trait nesting) and **D0-4a** (spell-name colon typos) — unblock real silent data-loss bugs; tiny surface.
3. **Land D0-3 + D6-1** (schema coverage for the unvalidated two-thirds of `data/`) — surfaces all the shape drift below as enforceable rules before larger changes start moving JSON around.
4. **Land P1-4, P1-5, P1-2, D1-4** — trivial cleanups that simplify the contract before the bigger work.
5. **Land P2-6 + D6-4** — strict mode on `effect.type` plus closed enum; surfaces hidden mismatches early.
6. **Land P0-3 + P2-1 + D1-8 + D2-1** together — the effects-dispatcher consolidation; this is the structural fix that retires the Fighting Style class of bugs, the 7 out-of-band consumer types, and the 5-location authoring confusion in one cut.
7. **Land D0-1 + D0-2 + D4-3** — add `effects` to all eldritch invocations and battle-master maneuvers; extract maneuvers to an external file. Best done immediately after step 6 because they all ride on the consolidated dispatcher.
8. **Land P1-1, P1-3, D1-1, D1-2, D1-3, D4-1** — contract canonicalization across frontend and data shapes.
9. **Land P2-2 + D3-4 + D3-5 + D6-2 + D6-3 + P2-3 + D5** — the `feature_kind` migration plus retirement of `feature_override.json`; replaces all remaining name-based branching.
10. **Land P2-4, P2-5, P2-7, P2-8, D0-4b, D1-7, D2-2, D2-3, D6-5, D6-6, D6-7** — backend hygiene and data-schema polish; can be parallelized.
11. **Land P3-1, P3-2, P3-3** — frontend guardrails on the now-stable contract.
12. **Land the HVE-asset updates** alongside their corresponding code changes (not all at the end) so the rules are written down when the patterns are fresh.

---

## Appendix — Source Audits

The three underlying audits (backend, frontend, parity) are preserved in the chat session resources. Key code references used in this consolidation:

- Backend: `modules/character_builder.py` (lines ~974, 1047, 1164, 1215–1495, 1749, 2392, 3249–3340, 4005, 4069–4160, 4122, 4822–4905), `modules/{equipment,feature,variant}_manager.py` (largely unused), `routes/api/character.py` (lines 65–70, 288–402, 334–346, 403–418, 649–820).
- Frontend: `frontend/src/components/steps/{ClassStep,BackgroundStep,SpeciesStep,AbilitiesStep,LanguagesStep,EquipmentStep}.tsx`, `frontend/src/components/wizard/{ClassAdvancedChoices,ChoiceList,SpellChoiceList,FeatDropdownPicker,FeatChoicesPicker,AbilitySelectList}.tsx`, `frontend/src/store/characterStore.ts`, `frontend/src/lib/api.ts`.
- Parity: `tests/integration/test_character_recreation.py`, `tests/core/test_character_builder.py`, `tests/core/test_spell_management.py`, `tests/core/test_weapon_mastery.py`, `test_characters/*.json`, `data/example_complete_character.json`.
- Data layer: `data/eldritch_invocations.json` (all 32 entries, prose-only), `data/subclasses/fighter/battle_master.json` (`maneuvers` block, prose-only), `data/feature_override.json` (6 entries), `data/species/*.json` (10 files, `darkvision` shape drift), `data/species_variants/*.json` (8 files, gnome variants missing `description`, elf/drow with duplicate spell lists), `data/backgrounds/*.json` (18 files, vestigial `languages: 2`), `data/subclasses/{druid,cleric,sorcerer,paladin}/...` (`grant_spell` references with colon typos or missing definitions); `models/` contains schemas only for `class` and `subclass` — 13+ categories unvalidated.
