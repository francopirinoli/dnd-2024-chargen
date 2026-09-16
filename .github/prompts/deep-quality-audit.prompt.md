---
description: "Run a deep cross-layer code-quality, consistency, and reconstruction-parity audit and produce a prioritized written report. Use when the codebase feels patchy, divergent paths are suspected, or before planning a major refactor."
argument-hint: "optional: extra focus areas (e.g. 'spell management', 'multiclass')"
agent: "architect"
---

# Deep Quality, Consistency & Parity Audit

Run a thorough read-only audit of the codebase along three axes, then consolidate findings into a single prioritized report that a fix plan can be built from without re-running the analysis.

## Inputs

- Optional extra focus areas from the user prompt (e.g. specific subsystems they're worried about). Treat these as **additional** scope, not a replacement for the three default axes below.

## Axes (run in parallel as read-only `Explore` subagents)

### Axis 1 — Backend code quality (`modules/`, `routes/api/`, calculation core)

For each finding capture file + line range, a concrete snippet, the underlying risk, and a complexity estimate. Cover at minimum:

- Divergent code paths that compute the same thing differently (two routes, two dispatchers, two storage shapes).
- Dead code: unused methods, parameters, imports, modules, no-op handlers that still return success.
- Hardcoded feature / class / option **names** in branching logic (violates the effects-system rule in [.github/instructions/effects-system.instructions.md](../instructions/effects-system.instructions.md)).
- Separation-of-concerns violations: god objects, calculation logic leaking into loaders/routes, modules that mirror state held elsewhere.
- State stored in multiple places that must be kept in sync manually.
- The build pipeline / order of operations — is it documented, deterministic, and asserted?
- Effects-system audit: list every effect type the dispatcher handles, every type referenced in JSON, every type documented in [docs/FEATURE_EFFECTS.md](../../docs/FEATURE_EFFECTS.md). Flag mismatches in either direction.
- Escape hatches like `feature_override.json` used in place of fixing the underlying data.
- Inconsistent error handling and silent failure paths.
- API endpoints that bypass `CharacterBuilder` or duplicate its work.

### Axis 2 — Frontend choice-control consistency (`frontend/src/`)

Verify that swapping one UI control for another for the same logical decision produces the same character. Capture:

- Inventory of every choice control (skill / spell / cantrip / feat / fighting style / maneuver / mastery / invocation / ASI / language / tool / equipment / subclass / species / lineage / background pickers).
- For each control: file, choice type, owning step/page, Zustand key it writes, shape it writes, and the API endpoint it ultimately drives.
- Divergent storage shapes for similar choices (nested vs flat, ID vs name, snake_case vs camelCase).
- Dual-writes of the same logical decision under multiple keys.
- Client-side calculation or filtering of server-derived data (forbidden by [.github/instructions/frontend-architecture.instructions.md](../instructions/frontend-architecture.instructions.md)).
- Dynamic choice-key generation diverging from the server-provided canonical key.
- Fields declared in the `ChoicesMade` (or equivalent) interface that are never populated, and dynamic keys written that are not declared.
- Endpoints called only from one control ("ad-hoc choice mutation" endpoints) — flag these.

### Axis 3 — Reconstruction-from-choices parity

Verify that rebuilding a character from a saved `choices_made` object yields the same character as the wizard produces incrementally. Capture:

- The exact entry points for "rebuild" and "wizard incremental" — are they actually the same code path?
- The ordering inside `apply_choices()` (or equivalent) and the dependencies between passes.
- Whether each declared choice type is handled symmetrically by both paths.
- Existing tests that exercise this property (parametrized across [test_characters/](../../test_characters/) and [data/example_complete_character.json](../../data/example_complete_character.json)). If no full-equality test exists, **flag it as critical**.
- Choices that may produce divergent results: multiclass rows, combined species + background skill replacements, late-restored selections (spells, masteries, invocations), order-sensitive ability modifiers.

### Axis 4 — Data layer (`data/`, `models/`, `wiki_data/`)

Dispatch the `data-completeness` agent for this axis. Audit the JSON content that drives the calculation engine and capture:

- **Schema compliance**: every file in `data/` validated against its schema in `models/`. Flag files missing required fields, using wrong types, or violating the `features_by_level: {level: {feature_name: description}}` object shape.
- **Effects-description consistency**: for every feature/feat/species-trait/background that grants a mechanical benefit, check whether the benefit is expressed as a structured `effects` array (correct) or only in prose (incorrect). Group offenders by category so they can be fixed in batches. **Apply the sheet-affecting scope rule:** this project is a *character builder*, not an interactive play tool. A structured `effects` array is required only when the feature changes a rendered sheet field (stats, AC, HP, attacks, damage, proficiencies, expertise, saves, resistances, speed, senses, known/prepared spells, slot counts, etc.). Features whose RAW benefit is purely in-play (reactions, spendable dice, GM-adjudicated narrative, optional triggers) may remain prose-only and are NOT findings. Estimate roughly how many *sheet-affecting* entries are missing structured effects.
- **Effect-type usage**: cross-reference every `effect.type` value used in JSON against the dispatcher in `modules/character_builder.py` and the catalogue in [docs/FEATURE_EFFECTS.md](../../docs/FEATURE_EFFECTS.md). Flag (a) types used in data but unhandled in code, (b) types handled in code but undocumented, (c) types documented but never used.
- **Field-shape consistency**: same conceptual data shaped differently across files (e.g. `proficiencies: ["Athletics"]` vs `proficiencies: {skills: ["Athletics"]}`, ID vs name references, snake_case vs camelCase keys, singular vs plural). Pick a canonical shape per concept and list the deviations.
- **Missing data**: classes/subclasses/species/backgrounds/feats/spells that exist on the D&D 2024 wiki (consult `wiki_data/`) but are absent from `data/`, and features listed in `features_by_level` without descriptions or effects.
- **Repeated / duplicate data**: identical effect blocks copy-pasted across files (candidates for shared definitions), duplicate spell/feat/feature entries, content that appears both in a class JSON and in an external reference file (e.g. `fighting_styles.json`) with the risk of double-application.
- **Escape-hatch usage**: entries in `data/feature_override.json` (or similar side-channel files) that should be migrated into the primary data file.
- **Schema improvement suggestions**: where the current schema makes correct authoring hard or invites the inconsistencies above, propose concrete schema changes (new fields, tightened enums, stricter required-field rules) and identify which `models/*.json` files would change.
- **Wiki drift**: spot-check a sample of entries against `wiki_data/` cached content; flag descriptions or mechanical benefits that have diverged from the D&D 2024 source.

## Output

Write the consolidated report to `docs/CODE_QUALITY_AUDIT_<YYYY-MM>.md` with the following sections, in this order:

1. **Executive summary** — 3–5 sentences naming the top structural problems.
2. **P0 — Blocking correctness risks** — issues that can silently produce wrong characters or lose data.
3. **P1 — High impact** — divergence and contract issues that don't yet corrupt data but invite future bugs.
4. **P2 — Backend code quality** — dispatcher consolidation, dead code, validation gaps, schema enforcement.
5. **P3 — Frontend architecture smells** — guardrails, validation, post-build verification.
6. **Data layer issues** — schema violations, inconsistent effect descriptions, duplicate/missing/repeated entries, schema improvement suggestions. Each item carries its own priority (P0–P3) by impact (e.g. a missing effect on a published feature is P0; a stylistic inconsistency is P2).
7. **Resolution complexity summary table** — one row per issue with priority and complexity (Trivial / Small / Medium / Large).
8. **HVE asset changes** — for each `.github/instructions/*.md`, `.github/skills/*/SKILL.md`, `.github/agents/*.md`, and `docs/*.md` file, the specific change that would prevent this class of problem from recurring. Changes may be **additions, edits, merges, or deletions** — recommend retiring or consolidating assets when they overlap, contradict each other, or are no longer load-bearing. Propose new skills/instructions only when an existing one cannot reasonably absorb the rule.
9. **Suggested fix sequencing** — a numbered phase plan ordered so each phase is verifiable and lands on top of the previous one. The first phase is almost always "add the missing parity / equality test."
10. **Appendix — source audits** — the key file/line references each finding rests on, so the report can be re-checked without re-running the audit.

For every issue, include:

- A short title.
- **Where**: file + approximate line range, plus a minimal code excerpt when it clarifies the issue.
- **Problem this creates**: the concrete failure mode (correctness, maintainability, data loss, UX) — not a generic "this is bad."
- **Complexity**: Trivial · Small · Medium · Large.

## Rules

- Read-only. Do not modify code while auditing.
- Do not duplicate findings across axes; consolidate.
- Do not propose specific patches in the report — only the problem, the impact, and the complexity. Patches belong in the follow-up plan.
- Reference real files with workspace-relative markdown links. Never invent line numbers.
- Use the existing agent boundaries: `backend` for `modules/` and `routes/api/`, `frontend` for `frontend/`, `data-completeness` for `data/` and `models/`. Dispatch read-only subagents in parallel for the four axes (`Explore` for axes 1–3, `data-completeness` for axis 4).
- Respect the project's anchor rules while auditing: `CharacterBuilder` is the single source of truth; effects branch on `type`, never on names; the frontend never calculates D&D stats; data files follow the schemas in `models/`.

## When done

Print a brief summary in chat naming:

- The top three structural problems.
- The number of issues at each priority level.
- The recommended first phase to land (usually the missing parity/equality test).
- The path to the written report.
