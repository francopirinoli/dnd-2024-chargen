# Skill: audit-choice-paths

## Purpose
Trace a specific choice (e.g., "Warlock feat at level 4") from UI interaction all the way to the rendered character sheet, verifying each layer hands off the correct key and value.

## When to Use
- A choice is not persisting or is being silently dropped.
- A server-provided `choices_made_key` appears wrong or mismatched.
- A feat sub-choice causes incorrect character output.
- After adding a new choice type, to verify end-to-end wiring.

## Trace Path

```
UI Component (e.g., FeatDropdownPicker)
  ↓  setChoice(choices_made_key, value)         ← Zustand store
  ↓  choicesMade validated by ChoicesMadeSchema ← api.ts (Zod)
  ↓  POST /api/v1/character/build               ← api.ts
  ↓  CharacterBuilder.apply_choices()           ← modules/character_builder.py
  ↓  _apply_effect() dispatcher                 ← modules/character_builder.py
  ↓  to_character() field populated             ← modules/character_builder.py
  ↓  Response JSON                              ← routes/api/character.py
  ↓  Rendered field in character sheet
```

## Steps

1. **Identify the key**: Inspect `choicesMade` in the browser's localStorage or React DevTools Zustand store. Note the exact key used.
2. **Verify server echo**: Call `api.character.build(choicesMade)` and inspect `response.choices_made`. Does the key appear?
3. **If key is missing from echo**: The backend `apply_choices()` did not consume it. Search `modules/character_builder.py` for the key pattern or its `choices_made_key` definition in the data JSON.
4. **Trace the choice resolver**: In `character_builder.py`, locate where `self.choices_made.get(key)` is called. Follow the value into the effect dispatcher.
5. **Trace the effect**: Find the handler for the relevant `effect['type']` in `_apply_effect()`. Verify the value is stored on the correct character attribute.
6. **Verify `to_character()` output**: Check that the attribute set in step 5 is included in the dict returned by `to_character()`.
7. **Verify rendered field**: Confirm the React component consuming the response renders the expected field.

## Common Failure Modes

| Symptom | Likely Cause |
|---------|-------------|
| Key in `choicesMade` not in server echo | Backend `apply_choices()` doesn't handle that key |
| Server echo has key but field empty | Effect handler set the wrong attribute |
| Field set but not in `to_character()` | `to_character()` doesn't include that attribute |
| Zod validation error in dev console | `ChoicesMadeSchema` is stale — update with the new key shape |
| `console.warn('[round-trip] key ... not echoed'` | Stale key in store from a previous schema version |

## Files: What to read for each layer

| Layer | File |
|-------|------|
| UI component | `frontend/src/components/steps/` or `frontend/src/components/wizard/` |
| Zustand store | `frontend/src/store/characterStore.ts` |
| API client | `frontend/src/lib/api.ts` |
| Choice resolver | `modules/character_builder.py` — `apply_choices()` |
| Effect dispatcher | `modules/character_builder.py` — `_apply_effect()` |
| Character output | `modules/character_builder.py` — `to_character()` |
| Route | `routes/api/character.py` |
