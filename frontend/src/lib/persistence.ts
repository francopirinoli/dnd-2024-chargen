/**
 * Character roster persistence layer.
 * 
 * Currently uses localStorage. Future versions may use IndexedDB or
 * a server-side database.
 */

import type { ChoicesMade } from "./api";

export interface RosterEntry {
  id: string;
  name: string;
  summary: string;
  choices: ChoicesMade;
  created: string;
  modified: string;
  savedAt: number;
}

const ROSTER_KEY = "dnd-character-roster";

// ========== Helper Functions ==========

export function newEntryId(): string {
  return `char-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function summarizeChoices(choices: ChoicesMade): string {
  const parts: string[] = [];
  
  const level = choices.level as number | undefined;
  if (level) {
    parts.push(`Level ${level}`);
  }
  
  const cls = choices.class as string | undefined;
  if (cls) {
    parts.push(cls);
    const sub = choices.subclass as string | undefined;
    if (sub) {
      parts.push(`(${sub})`);
    }
  }
  
  if (choices.species) {
    parts.push(choices.species);
    if (choices.lineage) {
      parts.push(`(${choices.lineage})`);
    }
  }
  
  if (choices.background) {
    parts.push(choices.background);
  }
  
  return parts.join(" ") || "New Character";
}

// ========== Persistence Interface ==========

export interface Persistence {
  loadRoster(): Promise<RosterEntry[]>;
  saveEntry(entry: RosterEntry): Promise<void>;
  deleteEntry(id: string): Promise<void>;
  saveSnapshot(entry: RosterEntry): Promise<void>;
  deleteSnapshot(id: string): Promise<void>;
}

class LocalStoragePersistence implements Persistence {
  async loadRoster(): Promise<RosterEntry[]> {
    try {
      const raw = localStorage.getItem(ROSTER_KEY);
      if (!raw) return [];
      const data = JSON.parse(raw);
      return Array.isArray(data) ? data : [];
    } catch (err) {
      console.error("Failed to load roster from localStorage:", err);
      return [];
    }
  }

  async saveEntry(entry: RosterEntry): Promise<void> {
    const roster = await this.loadRoster();
    const existingIndex = roster.findIndex((e) => e.id === entry.id);
    
    if (existingIndex >= 0) {
      roster[existingIndex] = entry;
    } else {
      roster.push(entry);
    }
    
    // Sort by modified date (most recent first)
    roster.sort((a, b) => 
      new Date(b.modified).getTime() - new Date(a.modified).getTime()
    );
    
    localStorage.setItem(ROSTER_KEY, JSON.stringify(roster));
  }

  async deleteEntry(id: string): Promise<void> {
    const roster = await this.loadRoster();
    const filtered = roster.filter((e) => e.id !== id);
    localStorage.setItem(ROSTER_KEY, JSON.stringify(filtered));
  }

  async saveSnapshot(entry: RosterEntry): Promise<void> {
    return this.saveEntry(entry);
  }

  async deleteSnapshot(id: string): Promise<void> {
    return this.deleteEntry(id);
  }
}

let _persistence: Persistence | null = null;

export function getPersistence(): Persistence {
  if (!_persistence) {
    _persistence = new LocalStoragePersistence();
  }
  return _persistence;
}

export function setPersistence(impl: Persistence): void {
  _persistence = impl;
}
