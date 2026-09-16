/**
 * Character wizard store.
 *
 * The frontend is the source of truth for in-progress `choices_made`.
 * The backend `CharacterBuilder` is the source of truth for calculated
 * stats — we POST `choices_made` to `/api/v1/character/*` to derive
 * everything else.
 *
 * Cascade invalidation: when a key listed in `/wizard/dependencies`
 * changes, all dependent keys are removed from `choices_made` so stale
 * subclass/spell/feat picks don't survive a class change.
 *
 * Persisted to localStorage so a refresh during character creation
 * doesn't lose progress.
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { ChoicesMade, WizardDependencies, ClassAllocation } from "@/lib/api";

interface CharacterState {
  choicesMade: ChoicesMade;
  dependencies: WizardDependencies;
  currentStepId: string | null;
  activeClassRowIndex: number;

  setDependencies: (deps: WizardDependencies) => void;
  setCurrentStep: (stepId: string | null) => void;
  setActiveClassRowIndex: (index: number) => void;
  setChoice: (key: string, value: unknown) => void;
  setChoices: (choices: ChoicesMade) => void;
  /**
   * Write a value into a nested object stored under `parentKey`.
   * Used for canonical nested-shape choices like `species_trait_choices`
   * and (in the same spirit as) `spell_selections`.
   */
  setNestedChoice: (parentKey: string, childKey: string, value: unknown) => void;
  clearChoice: (key: string) => void;
  reset: () => void;
}

const STORAGE_KEY = "dnd-creator-character-v1";

function normalizeClassAllocations(value: unknown): ClassAllocation[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => {
      if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
        return null;
      }
      const row = entry as Record<string, unknown>;
      const className =
        typeof row.class_name === "string" ? row.class_name : "";
      const rawLevel =
        typeof row.level === "number" && Number.isFinite(row.level)
          ? row.level
          : 1;
      const level = Math.max(1, Math.min(20, Math.floor(rawLevel)));
      const subclass =
        typeof row.subclass === "string" && row.subclass.length > 0
          ? row.subclass
          : undefined;

      return {
        class_name: className,
        level,
        ...(subclass ? { subclass } : {}),
      };
    })
    .filter((entry): entry is ClassAllocation => Boolean(entry));
}

function cascade(
  choices: ChoicesMade,
  deps: WizardDependencies,
  changedKey: string,
): ChoicesMade {
  const dependents = deps[changedKey];
  const next = { ...choices };
  if (dependents) {
    for (const k of dependents) {
      delete next[k];
    }
  }
  // Special-case class: also wipe any positional `class_choice_*` keys
  // that older builds stored before nested choices got stable keys.
  if (changedKey === "class") {
    for (const k of Object.keys(next)) {
      if (k.startsWith("class_choice_")) delete next[k];
    }
  }
  return next;
}

export const useCharacterStore = create<CharacterState>()(
  persist(
    (set) => ({
      choicesMade: {},
      dependencies: {},
      currentStepId: null,
      activeClassRowIndex: 0,

      setDependencies: (dependencies) => set({ dependencies }),
      setCurrentStep: (currentStepId) => set({ currentStepId }),
      setActiveClassRowIndex: (index) =>
        set({ activeClassRowIndex: Math.max(0, Math.floor(index)) }),

      setChoice: (key, value) =>
        set((state) => {
          const prevValue = state.choicesMade[key];
          const valueChanged =
            JSON.stringify(prevValue) !== JSON.stringify(value);
          let nextChoices: ChoicesMade = { ...state.choicesMade, [key]: value };
          if (valueChanged) {
            nextChoices = cascade(nextChoices, state.dependencies, key);
          }
          // Re-set the changed key in case cascade dropped it (it
          // shouldn't, but guard against accidental self-reference).
          nextChoices[key] = value;
          return { choicesMade: nextChoices };
        }),

      setChoices: (choices) => set({ choicesMade: choices }),

      setNestedChoice: (parentKey, childKey, value) =>
        set((state) => {
          const prevParent = state.choicesMade[parentKey];
          const parentObj: Record<string, unknown> =
            prevParent && typeof prevParent === "object" && !Array.isArray(prevParent)
              ? { ...(prevParent as Record<string, unknown>) }
              : {};
          if (value === undefined || value === null || value === "") {
            delete parentObj[childKey];
          } else {
            parentObj[childKey] = value;
          }
          return {
            choicesMade: { ...state.choicesMade, [parentKey]: parentObj },
          };
        }),

      clearChoice: (key) =>
        set((state) => {
          const next = { ...state.choicesMade };
          delete next[key];
          return {
            choicesMade: cascade(next, state.dependencies, key),
          };
        }),

      reset: () =>
        set({ choicesMade: {}, currentStepId: null, activeClassRowIndex: 0 }),
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      version: 3,
      migrate: (persisted, version) => {
        if (
          !persisted ||
          typeof persisted !== "object" ||
          version > 3
        ) {
          return {
            choicesMade: {},
            currentStepId: null,
            activeClassRowIndex: 0,
          } as Partial<
            CharacterState
          >;
        }

        const next = persisted as Partial<CharacterState>;
        const choices =
          next.choicesMade && typeof next.choicesMade === "object"
            ? { ...next.choicesMade }
            : ({} as ChoicesMade);

        if (version < 2) {
          const className =
            typeof choices.class === "string" ? choices.class : "";
          const level =
            typeof choices.level === "number" && Number.isFinite(choices.level)
              ? Math.max(1, Math.min(20, Math.floor(choices.level)))
              : 1;
          const subclass =
            typeof choices.subclass === "string" && choices.subclass.length > 0
              ? choices.subclass
              : undefined;
          const existing = normalizeClassAllocations(choices.classes);

          if (existing.length === 0 && className) {
            choices.classes = [
              {
                class_name: className,
                level,
                ...(subclass ? { subclass } : {}),
              },
            ];
          } else if (existing.length > 0) {
            choices.classes = existing;
          }
        } else {
          const existing = normalizeClassAllocations(choices.classes);
          if (existing.length > 0) {
            choices.classes = existing;
          }
        }

        next.activeClassRowIndex =
          typeof next.activeClassRowIndex === "number" &&
          Number.isFinite(next.activeClassRowIndex)
            ? Math.max(0, Math.floor(next.activeClassRowIndex))
            : 0;

        next.choicesMade = choices;
        return next;
      },
      partialize: (state) => ({
        choicesMade: state.choicesMade,
        currentStepId: state.currentStepId,
        activeClassRowIndex: state.activeClassRowIndex,
      }),
    },
  ),
);
