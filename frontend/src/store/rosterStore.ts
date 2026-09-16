/**
 * Roster store — manages the list of saved character snapshots.
 *
 * Reads/writes go through `getPersistence()` so the storage backend
 * (localStorage today, Postgres later) is swappable.
 */

import { create } from "zustand";
import {
  getPersistence,
  newEntryId,
  summarizeChoices,
  type RosterEntry,
} from "@/lib/persistence";
import type { ChoicesMade } from "@/lib/api";

interface RosterState {
  entries: RosterEntry[];
  loaded: boolean;
  loading: boolean;
  error: string | null;

  load: () => Promise<void>;
  saveCurrent: (
    choices: ChoicesMade,
    name: string,
    existingId?: string,
  ) => Promise<RosterEntry>;
  delete: (id: string) => Promise<void>;
}

export const useRosterStore = create<RosterState>((set, get) => ({
  entries: [],
  loaded: false,
  loading: false,
  error: null,

  load: async () => {
    if (get().loading) return;
    set({ loading: true, error: null });
    try {
      const entries = await getPersistence().loadRoster();
      set({ entries, loaded: true, loading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Failed to load roster",
        loading: false,
      });
    }
  },

  saveCurrent: async (choices, name, existingId) => {
    const trimmed = name.trim() || "Unnamed character";
    const now = new Date().toISOString();
    const entry: RosterEntry = {
      id: existingId ?? newEntryId(),
      name: trimmed,
      summary: summarizeChoices(choices),
      savedAt: Date.now(),
      created: now,
      modified: now,
      choices,
    };
    await getPersistence().saveSnapshot(entry);
    const entries = await getPersistence().loadRoster();
    set({ entries, loaded: true });
    return entry;
  },

  delete: async (id) => {
    await getPersistence().deleteSnapshot(id);
    const entries = await getPersistence().loadRoster();
    set({ entries });
  },
}));
