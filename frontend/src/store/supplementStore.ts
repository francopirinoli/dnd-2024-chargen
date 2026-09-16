import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { SupplementManifest } from "@/lib/api";

interface SupplementState {
  activeSources: string[];
  supplements: SupplementManifest[];
  dialogOpen: boolean;
  
  setDialogOpen: (open: boolean) => void;
  setSupplements: (list: SupplementManifest[]) => void;
  toggleSource: (id: string) => void;
  enableSource: (id: string) => void;
  disableSource: (id: string) => void;
  isSourceActive: (id: string) => boolean;
}

export const useSupplementStore = create<SupplementState>()(
  persist(
    (set, get) => ({
      activeSources: ["core-phb-2024"],
      supplements: [],
      dialogOpen: false,

      setDialogOpen: (open) => set({ dialogOpen: open }),

      setSupplements: (list) => {
        set({ supplements: list });
        // Sanitize activeSources so stale or removed supplements (e.g. samples) are stripped
        const validIds = new Set(["core-phb-2024", ...list.map((s) => s.id)]);
        const currentActive = get().activeSources.filter((id) => validIds.has(id));

        if (currentActive.length === 0) {
          set({
            activeSources: [
              "core-phb-2024",
              ...list.filter((s) => s.enabled !== false).map((s) => s.id),
            ],
          });
        } else {
          // Auto-enable any newly discovered supplements that are enabled on the server
          const newSources = list
            .filter((s) => s.enabled !== false && !currentActive.includes(s.id))
            .map((s) => s.id);
          set({ activeSources: [...currentActive, ...newSources] });
        }
      },

      toggleSource: (id) => {
        if (id === "core-phb-2024") return; // Core PHB cannot be toggled off
        const current = get().activeSources;
        if (current.includes(id)) {
          set({ activeSources: current.filter((s) => s !== id) });
        } else {
          set({ activeSources: [...current, id] });
        }
      },

      enableSource: (id) => {
        const current = get().activeSources;
        if (!current.includes(id)) {
          set({ activeSources: [...current, id] });
        }
      },

      disableSource: (id) => {
        if (id === "core-phb-2024") return;
        set({ activeSources: get().activeSources.filter((s) => s !== id) });
      },

      isSourceActive: (id) => {
        return get().activeSources.includes(id);
      },
    }),
    {
      name: "dnd-2024-active-supplements",
      partialize: (state) => ({ activeSources: state.activeSources }),
    },
  ),
);
