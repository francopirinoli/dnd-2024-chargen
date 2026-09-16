---
description: "Consume a code-quality audit report and emit a phase-by-phase implementation plan with agent assignments, ordering, dependencies, and verification steps. Use after /deep-quality-audit has produced a report and the user is ready to schedule the fixes."
argument-hint: "path to audit report (defaults to the newest docs/CODE_QUALITY_AUDIT_*.md)"
agent: "architect"
---

# Audit Fix Plan

Read an existing audit report and produce an actionable, phased implementation plan. **Do not implement anything.** This prompt only plans — execution happens later through specialist agents.

## Inputs

- Path to the audit report. If the user did not provide one, default to the newest `docs/CODE_QUALITY_AUDIT_*.md` in the workspace.
- Optional user constraints in the prompt body (e.g. "skip P3", "frontend only", "deliver in 3 phases max"). Honor these in the output.

## Process

1. Read the entire audit report. Build an internal index of every issue ID (P0-N, P1-N, P2-N, P3-N, D0-N, …), its priority, complexity, and the files/areas it touches.
2. Re-read the report's own **Suggested Fix Sequencing** section. Treat it as a starting hypothesis, not a constraint. You may merge, split, or reorder phases if the dependencies justify it — explain why in each case.
3. Cluster issues by:
   - **Shared blast radius** (same files / same subsystem touched).
   - **Hard dependencies** (issue B can't land safely without issue A).
   - **Owning agent** (`frontend`, `backend`, `data-completeness`, `test`, `docs`).
   - **Risk** (irreversible refactors vs. additive cleanups).
4. Detect cross-cutting work that needs **split phases** because it crosses agent lanes (e.g. effect-dispatcher consolidation needs `backend` for the engine and `test` for the parity suite). Never put both lanes in a single phase.
5. Build the phase plan according to the rules below.

## Phasing Rules

- **Phase 1 is always a safety net.** Identify the parity / equality / regression test the report calls out (almost always present); if it exists, land that first. If the report does *not* call one out, propose one and flag the gap.
- **Each phase must be independently shippable and verifiable.** No phase depends on a future phase being merged.
- **No phase mixes agent lanes.** If a logical chunk crosses lanes, split it: the planning phase notes the split and orders the lane-phases so the upstream lane lands first.
- **Group trivial cleanups** into a single phase per lane when they're risk-free and additive (e.g. all P1 trivial frontend cleanups).
- **Heavy refactors get their own phase** with a single owner and an explicit list of files in scope.
- **HVE-asset updates ride alongside their code change**, not at the end. Each phase that lands behavior also lands the matching instruction/skill/agent/doc edits.
- **Cap phase count at ~12** unless the report is unusually large. Prefer fewer, well-scoped phases over many tiny ones.

## Output

Write the plan to `docs/AUDIT_FIX_PLAN_<YYYY-MM>.md` (next to the audit, same month tag if applicable). Use this structure:

### 1. Header
- Audit source file (linked).
- Date.
- Total issues by priority (P0 / P1 / P2 / P3 / D-band rollup).
- Any user-imposed constraints honored.

### 2. Executive Strategy (3–6 bullets)
- What the overall trajectory looks like (e.g. "lock the contract, then refactor under it").
- The single biggest structural fix and which phase delivers it.
- Anything explicitly out of scope and why.

### 3. Dependency Graph
A concise list (or mermaid `graph TD`) showing which issues must precede which. Only include real dependencies — don't draw lines for "would be nice".

### 4. Phase Plan
One subsection per phase. For each phase:

- **Title** — short, descriptive.
- **Owner agent** — exactly one of `backend`, `frontend`, `data-completeness`, `test`, `docs`, or `architect` for cross-cutting coordination phases that only produce design artifacts.
- **Issue IDs delivered** — list from the audit (e.g. `P0-2`, `D0-3`).
- **Scope** — concrete files / directories touched. Bullet list.
- **Out of scope** — adjacent issues NOT addressed here and why (forward-references to a later phase).
- **Deliverables** — code + HVE-asset edits + docs in this phase.
- **Verification** — exactly how we know the phase landed correctly. Cite specific tests, commands, or assertions. Every phase has at least one mechanical verification step.
- **Estimated complexity** — Trivial · Small · Medium · Large (carried from the audit, possibly upgraded if combined).
- **Dependencies** — phase numbers this one builds on.

### 5. Agent Workload Summary
A small table:

| Agent             | Phases owned | Issues delivered |
|-------------------|--------------|------------------|
| `backend`         | …            | …                |
| `frontend`        | …            | …                |
| `data-completeness` | …          | …                |
| `test`            | …            | …                |
| `docs`            | …            | …                |

Used to spot lanes that are under- or over-loaded.

### 6. Risk Register
For each phase carrying real risk (irreversible refactor, schema migration, public-contract change), one bullet:
- **Risk** — what could go wrong.
- **Mitigation** — concrete (additional tests, feature flag, staged rollout, backup migration).
- **Rollback** — what makes this reversible if it goes bad.

### 7. Open Questions
Anything the audit left ambiguous that must be resolved before a phase can start. Each item names the phase that blocks on it.

### 8. Out-of-Scope / Deferred
Issues in the audit that the plan deliberately does not address (with reason — e.g. "P3-2 Zod validation deferred until P1-2 cleanup ships").

## Rules

- Do not implement. This is a planning artifact only.
- Do not re-do the audit. Trust the report; if the report is wrong, flag it in **Open Questions**, don't silently override.
- Every issue ID in the audit either appears in a phase, in **Out-of-Scope**, or in **Open Questions**. No issue is silently dropped.
- Every phase has a single owner agent. Cross-lane work is split, not merged.
- Use workspace-relative markdown links for every file reference. Never invent line numbers.
- Respect the architectural anchors while planning: `CharacterBuilder` is the single source of truth, frontend never calculates, effects branch on `type` not names, data files comply with `models/` schemas.

## When done

Print a brief summary in chat naming:

- Total phase count.
- The owner of phase 1 and what it delivers.
- The phase that absorbs the single biggest structural fix.
- Any blockers raised in **Open Questions**.
- The path to the written plan.

After printing the summary, stop. Do not start executing phases — that requires the user's explicit approval and goes through the normal architect → specialist delegation flow.
