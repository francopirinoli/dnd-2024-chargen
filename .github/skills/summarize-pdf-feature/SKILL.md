---
name: summarize-pdf-feature
description: "Create or update one class feature entry in data/feature_override.json with a concise PDF summary or hidden flag."
---

# Summarize PDF Feature

Use this skill to add a single class feature override for the PDF character sheet.

## Inputs

- Class name (for top-level key in `data/feature_override.json`)
- Feature name

## Procedure

1. Find the feature text in:
   - `data/classes/<class>.json`, or
   - `data/subclasses/<class>/*.json` when needed for context.
2. Optionally verify wording/mechanics with:
   - `wiki_data/` cache, then
   - <http://dnd2024.wikidot.com/> if cache is missing.
3. Draft a concise `pdf_summary` (target 1–3 lines) focused on:
   - action economy (Action / Bonus Action / Reaction),
   - numeric values (dice, ranges, durations),
   - recharge cadence (SR / LR / per day),
   - hard usage conditions.
   Exclude lore/flavor text.
4. Update `data/feature_override.json` under:
   - `<ClassName> -> <FeatureName> -> { "pdf_summary": "..." }`, or
   - `<ClassName> -> <FeatureName> -> { "hidden": true }` when the feature should not appear on the PDF.
5. Create `data/feature_override.json` if it does not exist, preserving existing entries when present.

## Output

- Updated `data/feature_override.json` with the requested class + feature override only.
