import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useCharacterStore } from "@/store/characterStore";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { BookOpen, ChevronDown, ChevronUp, Wand2 } from "lucide-react";

type Loose = Record<string, unknown>;

interface SpellReference {
  name: string;
  level?: number;
  source?: string;
  school?: string;
  description?: string;
  casting_time?: string;
  range?: string;
  duration?: string;
  components?: string[];
  counts_against_limit?: boolean;
  is_always_prepared?: boolean;
  ritual?: boolean;
  concentration?: boolean;
}

interface CurrentSpellSelections {
  cantrips: string[];
  spells: string[];
  spellbook: string[];
  background_cantrips: string[];
  background_spells: string[];
}

interface SpellEntry extends SpellReference {
  isAlwaysPrepared: boolean;
  levelKey: string;
}

interface PactMagicSlot {
  class_name?: string;
  slot_level?: number;
  slots?: number;
}

function arr<T = unknown>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}
function rec(v: unknown): Loose {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Loose) : {};
}
function num(v: unknown): number | undefined {
  return typeof v === "number" ? v : undefined;
}
function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

function normalizeSpellRef(raw: Loose): SpellReference | null {
  const name = str(raw.name);
  if (!name) return null;
  const rawComponents = raw.components;
  const components =
    typeof rawComponents === "string"
      ? [rawComponents]
      : arr<string>(rawComponents).filter(
          (e): e is string => typeof e === "string" && e.length > 0,
        );
  return {
    name,
    level: num(raw.level),
    source: str(raw.source),
    school: str(raw.school),
    description: str(raw.description),
    casting_time: str(raw.casting_time),
    range: str(raw.range),
    duration: str(raw.duration),
    components: components.length > 0 ? components : undefined,
    counts_against_limit:
      typeof raw.counts_against_limit === "boolean" ? raw.counts_against_limit : undefined,
    ritual: typeof raw.ritual === "boolean" ? raw.ritual : undefined,
    concentration:
      typeof raw.concentration === "boolean" ? raw.concentration : undefined,
  };
}

function normalizeCurrent(raw: Loose): CurrentSpellSelections {
  const spells = arr<string>(raw.spells);
  let spellbook = arr<string>(raw.spellbook);
  if (spellbook.length === 0 && spells.length > 0) {
    spellbook = [...spells];
  }
  return {
    cantrips: arr<string>(raw.cantrips),
    spells,
    spellbook,
    background_cantrips: arr<string>(raw.background_cantrips),
    background_spells: arr<string>(raw.background_spells),
  };
}

const ORDINAL_TO_NUM: Record<string, number> = {
  first: 1, second: 2, third: 3, fourth: 4, fifth: 5,
  sixth: 6, seventh: 7, eighth: 8, ninth: 9,
};

const LEVEL_ORDINALS = [
  "Cantrip", "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th",
];

function levelOrdinal(level: number | undefined): string {
  if (level === undefined) return "";
  return LEVEL_ORDINALS[level] ?? `${level}th`;
}

const PREPARE_RULE_NOTES: Record<string, string> = {
  long_rest: "You can change your prepared spells after a Long Rest.",
  level_up: "You can swap one spell each time you gain a level.",
  short_rest: "You can change your known spells after a Short Rest.",
  fixed: "Your spells are fixed and cannot be changed.",
};

interface PrepareSpellsDialogProps {
  open: boolean;
  onClose: () => void;
}

export function PrepareSpellsDialog({ open, onClose }: PrepareSpellsDialogProps) {
  const setChoice = useCharacterStore((s) => s.setChoice);
  const choicesMade = useCharacterStore((s) => s.choicesMade);

  const [wizardMode, setWizardMode] = useState<"prepare" | "spellbook">("prepare");
  // Multi-select level filter (empty = show all)
  const [activeLevels, setActiveLevels] = useState<Set<string>>(new Set());
  const [filterText, setFilterText] = useState("");
  // Accordion: set of spell names whose details are expanded (right panel)
  const [expandedSpells, setExpandedSpells] = useState<Set<string>>(new Set());
  // Mobile tab toggle: "available" vs "prepared" (< md screens)
  const [mobileViewTab, setMobileViewTab] = useState<"available" | "prepared">("available");

  const query = useQuery({
    queryKey: [
      "character", "derived", "spell_management",
      choicesMade.class,
      choicesMade.level,
      choicesMade.subclass,
      choicesMade.classes,
    ],
    queryFn: () => api.character.derived(choicesMade as Loose, "spell_management"),
    enabled:
      open &&
      Array.isArray(choicesMade["classes"]) &&
      (choicesMade["classes"] as unknown[]).length > 0,
    retry: false,
  });

  const payload = query.data;
  const applicable =
    payload &&
    payload.applicable === true &&
    payload.data &&
    typeof payload.data === "object" &&
    !Array.isArray(payload.data);
  const data = applicable ? (payload!.data as Loose) : null;

  const hasSpellbook = Boolean(data?.has_spellbook);
  const spellbookLimits = rec(data?.spellbook_limits);
  const totalSpellbook = num(spellbookLimits.total_spells) ?? 6;
  const savantSchool = str(spellbookLimits.savant_school);
  const savantSpells = num(spellbookLimits.savant_spells) ?? 0;

  const limits = rec(data?.limits);
  const maxCantrips = num(limits.cantrips) ?? 0;
  const maxSpells = num(limits.spells) ?? 0;

  const availableCantrips = useMemo(
    () =>
      arr<Loose>(data?.available_cantrips ?? [])
        .map(normalizeSpellRef)
        .filter((s): s is SpellReference => s !== null),
    [data?.available_cantrips],
  );

  const availableSpellsByLevel = useMemo(
    () => rec(data?.available_spells ?? {}),
    [data?.available_spells],
  );

  const alwaysPrepared = useMemo(
    () =>
      arr<Loose>(data?.always_prepared ?? [])
        .map(normalizeSpellRef)
        .filter((s): s is SpellReference => s !== null)
        .map((s) => ({ ...s, is_always_prepared: true as const })),
    [data?.always_prepared],
  );

  const alwaysPreparedNames = useMemo(
    () => new Set(alwaysPrepared.map((s) => s.name)),
    [alwaysPrepared],
  );

  const spellSlots = rec(data?.spell_slots ?? {});

  const current: CurrentSpellSelections =
    (choicesMade["spell_selections"] as CurrentSpellSelections | undefined) ??
    normalizeCurrent(rec(data?.current_selections ?? {}));

  const spellLevels = useMemo(
    () =>
      Object.keys(availableSpellsByLevel)
        .filter((lvl) => lvl !== "0" && arr(availableSpellsByLevel[lvl]).length > 0)
        .sort((a, b) => Number(a) - Number(b)),
    [availableSpellsByLevel],
  );

  const tabs = useMemo(
    () => {
      const showCantrips = (!hasSpellbook || wizardMode !== "spellbook") && (availableCantrips.length > 0 || maxCantrips > 0);
      return [
        ...(showCantrips ? [{ key: "cantrips", label: "0" }] : []),
        ...spellLevels.map((lvl) => ({
          key: `level_${lvl}`,
          label: levelOrdinal(Number(lvl)),
        })),
      ];
    },
    [availableCantrips.length, maxCantrips, spellLevels, hasSpellbook, wizardMode],
  );

  const slotDisplay = useMemo(
    () =>
      Object.entries(spellSlots)
        .map(([key, count]) => ({
          kind: "regular" as const,
          level: ORDINAL_TO_NUM[key] ?? parseInt(key, 10),
          count: num(count) ?? 0,
        }))
        .filter((s) => s.count > 0 && !Number.isNaN(s.level))
        .sort((a, b) => a.level - b.level),
    [spellSlots],
  );

  const pactSlotDisplay = useMemo(
    () => {
      const slots = arr<PactMagicSlot>(data?.pact_magic_slots ?? []).reduce<
        Array<{
          kind: "pact";
          level: number;
          count: number;
          className?: string;
        }>
      >((acc, slot) => {
        const level = num(slot.slot_level);
        const count = num(slot.slots) ?? 0;
        if (level === undefined || count <= 0) return acc;
        acc.push({
          kind: "pact",
          level,
          count,
          className: str(slot.class_name),
        });
        return acc;
      }, []);

      return slots.sort((a, b) => a.level - b.level);
    },
    [data?.pact_magic_slots],
  );

  const allSlotDisplay = useMemo(
    () => [...slotDisplay, ...pactSlotDisplay],
    [slotDisplay, pactSlotDisplay],
  );

  // Flat list of all spells available to pick (cantrips + leveled + always-prepared extras)
  const availableFlat = useMemo<SpellEntry[]>(() => {
    const result: SpellEntry[] = [];
    const seen = new Set<string>();

    for (const s of availableCantrips) {
      if (seen.has(s.name)) continue;
      seen.add(s.name);
      result.push({ ...s, isAlwaysPrepared: alwaysPreparedNames.has(s.name), levelKey: "cantrips" });
    }

    for (const lvl of spellLevels) {
      for (const raw of arr<Loose>(availableSpellsByLevel[lvl])) {
        const s = normalizeSpellRef(raw);
        if (!s || seen.has(s.name)) continue;
        seen.add(s.name);
        result.push({
          ...s,
          isAlwaysPrepared: alwaysPreparedNames.has(s.name),
          levelKey: `level_${lvl}`,
        });
      }
    }

    // Always-prepared spells not already covered above
    for (const s of alwaysPrepared) {
      if (seen.has(s.name)) continue;
      seen.add(s.name);
      const lk = (s.level ?? 0) === 0 ? "cantrips" : `level_${s.level ?? 1}`;
      result.push({ ...s, isAlwaysPrepared: true, levelKey: lk });
    }

    return result;
  }, [availableCantrips, availableSpellsByLevel, alwaysPrepared, alwaysPreparedNames, spellLevels]);

  const allSpellsByName = useMemo(
    () => new Map(availableFlat.map((s) => [s.name, s])),
    [availableFlat],
  );

  // Left-panel flat list depends on mode
  const displayAvailableFlat = useMemo(() => {
    if (!hasSpellbook) return availableFlat;
    if (wizardMode === "spellbook") {
      // In spellbook mode, show all leveled spells to add/remove
      return availableFlat.filter((s) => (s.level ?? 0) > 0);
    }
    // In prepare mode for wizards, show cantrips, always-prepared, and spells currently in spellbook
    const bookSet = new Set(current.spellbook);
    return availableFlat.filter(
      (s) => (s.level ?? 0) === 0 || s.isAlwaysPrepared || bookSet.has(s.name),
    );
  }, [availableFlat, hasSpellbook, wizardMode, current.spellbook]);

  // Left-panel filtered list
  const filteredAvailable = useMemo(() => {
    let list = displayAvailableFlat;
    if (activeLevels.size > 0) list = list.filter((s) => activeLevels.has(s.levelKey));
    if (filterText.trim()) {
      const lower = filterText.toLowerCase();
      list = list.filter((s) => s.name.toLowerCase().includes(lower));
    }
    return list;
  }, [displayAvailableFlat, activeLevels, filterText]);

  // Right-panel flat prepared list, sorted by level
  const preparedFlat = useMemo<SpellEntry[]>(() => {
    const byName = allSpellsByName;
    const result: SpellEntry[] = [];
    const seen = new Set<string>();

    const add = (name: string, isAlways: boolean, fallbackLevel: number) => {
      if (seen.has(name)) return;
      seen.add(name);
      const known = byName.get(name);
      if (known) {
        result.push({ ...known, isAlwaysPrepared: isAlways || known.isAlwaysPrepared });
      } else {
        const lk = fallbackLevel === 0 ? "cantrips" : `level_${fallbackLevel}`;
        result.push({ name, isAlwaysPrepared: isAlways, levelKey: lk, level: fallbackLevel });
      }
    };

    for (const s of alwaysPrepared) add(s.name, true, s.level ?? 0);
    for (const n of current.cantrips) add(n, false, 0);
    for (const n of current.spells) add(n, false, 1);

    result.sort((a, b) => (a.level ?? 0) - (b.level ?? 0));
    return result;
  }, [allSpellsByName, alwaysPrepared, current]);

  // Right-panel: prepared spells grouped by level for section rendering
  const preparedGroups = useMemo<Array<{ level: number; label: string; spells: SpellEntry[] }>>(() => {
    const groups = new Map<number, SpellEntry[]>();
    for (const s of preparedFlat) {
      const lvl = s.level ?? 0;
      if (!groups.has(lvl)) groups.set(lvl, []);
      groups.get(lvl)!.push(s);
    }
    return Array.from(groups.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([level, spells]) => ({
        level,
        label: level === 0 ? "Cantrips" : `Level ${level}`,
        spells,
      }));
  }, [preparedFlat]);

  // Right-panel (Spellbook mode): spells currently in spellbook grouped by level
  const spellbookGroups = useMemo(() => {
    const groups = new Map<number, SpellEntry[]>();
    for (const name of current.spellbook) {
      const s = allSpellsByName.get(name) || {
        name,
        level: 1,
        isAlwaysPrepared: false,
        levelKey: "level_1",
      };
      const lvl = s.level ?? 1;
      if (!groups.has(lvl)) groups.set(lvl, []);
      groups.get(lvl)!.push(s);
    }
    return Array.from(groups.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([level, spells]) => ({
        level,
        label: `Level ${level}`,
        spells: spells.sort((a, b) => a.name.localeCompare(b.name)),
      }));
  }, [current.spellbook, allSpellsByName]);

  // --- Handlers ---

  function update(patch: Partial<CurrentSpellSelections>) {
    setChoice("spell_selections", {
      cantrips: current.cantrips,
      spells: current.spells,
      spellbook: current.spellbook,
      background_cantrips: current.background_cantrips,
      background_spells: current.background_spells,
      ...patch,
    });
  }

  function toggleList(list: string[], name: string, cap: number): string[] | null {
    if (list.includes(name)) return list.filter((n) => n !== name);
    if (list.length >= cap) return null;
    return [...list, name];
  }

  function toggleSpell(spell: SpellEntry) {
    if (spell.isAlwaysPrepared) return;
    if ((spell.level ?? 0) === 0) {
      const next = toggleList(current.cantrips, spell.name, maxCantrips);
      if (next) update({ cantrips: next });
    } else {
      const next = toggleList(current.spells, spell.name, maxSpells);
      if (next) update({ spells: next });
    }
  }

  function toggleSpellbook(spell: SpellEntry) {
    if (current.spellbook.includes(spell.name)) {
      const nextBook = current.spellbook.filter((n) => n !== spell.name);
      const nextSpells = current.spells.filter((n) => n !== spell.name);
      update({ spellbook: nextBook, spells: nextSpells });
    } else {
      if (current.spellbook.length < totalSpellbook) {
        update({ spellbook: [...current.spellbook, spell.name] });
      }
    }
  }

  function removeSpellFromSpellbook(name: string) {
    const nextBook = current.spellbook.filter((n) => n !== name);
    const nextSpells = current.spells.filter((n) => n !== name);
    update({ spellbook: nextBook, spells: nextSpells });
  }

  function unprepareSpell(spell: SpellEntry) {
    if (spell.isAlwaysPrepared) return;
    if ((spell.level ?? 0) === 0) {
      update({ cantrips: current.cantrips.filter((n) => n !== spell.name) });
    } else {
      update({ spells: current.spells.filter((n) => n !== spell.name) });
    }
  }

  function toggleExpand(name: string) {
    setExpandedSpells((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  function toggleLevelFilter(key: string) {
    setActiveLevels((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  const prepareRule = data ? str(data.prepare_rule as unknown) : undefined;
  const ruleNote = prepareRule ? PREPARE_RULE_NOTES[prepareRule] : undefined;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col gap-0 p-0 overflow-hidden">
        <DialogHeader className="px-6 pt-5 pb-3 shrink-0 border-b border-border">
          <DialogTitle>
            {hasSpellbook ? "Wizard Spells & Spellbook" : "Prepare Spells"}
          </DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground mt-1">
            {hasSpellbook
              ? "Manage your spellbook and prepared spells according to the D&D 2024 ruleset."
              : ruleNote || "Manage your prepared spells and cantrips."}
          </DialogDescription>
        </DialogHeader>

        {hasSpellbook && (
          <div className="flex border-b border-border bg-muted/20 px-6 py-2 gap-2">
            <button
              type="button"
              onClick={() => setWizardMode("prepare")}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all",
                wizardMode === "prepare"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Wand2 className="h-3.5 w-3.5" />
              <span>Prepared Spells ({current.spells.length}/{maxSpells})</span>
            </button>
            <button
              type="button"
              onClick={() => setWizardMode("spellbook")}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all",
                wizardMode === "spellbook"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>Manage Spellbook ({current.spellbook.length}/{totalSpellbook})</span>
            </button>
          </div>
        )}

        {query.fetchStatus === "fetching" && !data ? (
          <div className="px-6 py-5 text-sm text-muted-foreground">Loading spells…</div>
        ) : data ? (
          <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
            {/* ── Mobile view tab toggle (< md) ── */}
            <div className="flex md:hidden border-b border-border bg-muted/40 p-2 gap-2 shrink-0">
              <button
                type="button"
                onClick={() => setMobileViewTab("available")}
                className={cn(
                  "flex-1 py-1.5 px-3 rounded-md text-xs font-semibold transition-all text-center",
                  mobileViewTab === "available"
                    ? "bg-background text-foreground shadow-xs border border-border"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                Available Spells
              </button>
              <button
                type="button"
                onClick={() => setMobileViewTab("prepared")}
                className={cn(
                  "flex-1 py-1.5 px-3 rounded-md text-xs font-semibold transition-all text-center flex items-center justify-center gap-1.5",
                  mobileViewTab === "prepared"
                    ? "bg-background text-foreground shadow-xs border border-border"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <span>
                  {hasSpellbook && wizardMode === "spellbook"
                    ? `Spellbook (${current.spellbook.length}/${totalSpellbook})`
                    : `Prepared (${current.spells.length}/${maxSpells})`}
                </span>
              </button>
            </div>

            <div className="flex flex-1 min-h-0 overflow-hidden">

              {/* ── Left: Available Spells / Spellbook List ──────────────────────── */}
              <div
                className={cn(
                  "flex-col min-w-0 overflow-hidden md:flex md:basis-3/5 md:border-r md:border-border",
                  mobileViewTab === "available" ? "flex flex-1 w-full" : "hidden",
                )}
              >
                <div className="px-5 pt-4 pb-2 shrink-0">
                  <h3 className="font-display text-lg text-primary font-semibold flex items-center gap-2">
                    {hasSpellbook && wizardMode === "spellbook" ? (
                      <>
                        <BookOpen className="h-4 w-4" />
                        <span>Learn Spells (Wizard List)</span>
                      </>
                    ) : hasSpellbook ? (
                      <>
                        <BookOpen className="h-4 w-4" />
                        <span>Spells in Spellbook</span>
                      </>
                    ) : (
                      <span>Available Spells</span>
                    )}
                  </h3>
                  {hasSpellbook && wizardMode === "prepare" && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Select spells to prepare today. Rituals (R) can be cast without preparing.
                    </p>
                  )}
                  {hasSpellbook && wizardMode === "spellbook" && savantSchool && (
                    <p className="text-xs text-primary/90 mt-0.5">
                      ✦ {savantSchool} Savant: bonus {savantSchool} spells included
                    </p>
                  )}
                </div>

                {/* Filter input */}
                <div className="px-5 pb-2 shrink-0">
                  <label className="text-xs text-muted-foreground">Filter</label>
                  <input
                    type="text"
                    value={filterText}
                    onChange={(e) => setFilterText(e.target.value)}
                    placeholder="Search spells…"
                    className="mt-1 w-full rounded border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>

                {/* Level tabs — multi-select */}
                {tabs.length > 1 && (
                  <div className="px-5 pb-3 shrink-0">
                    <label className="text-xs text-muted-foreground">
                      Filter by spell level
                    </label>
                    <div className="themed-scrollbar mt-1 flex flex-wrap gap-1.5 overflow-x-auto">
                      {tabs.map((tab) => (
                        <button
                          key={tab.key}
                          type="button"
                          onClick={() => toggleLevelFilter(tab.key)}
                          className={cn(
                            "shrink-0 rounded border px-2 py-0.5 text-xs font-medium transition-colors min-w-[2rem] text-center",
                            activeLevels.has(tab.key)
                              ? "border-primary bg-primary text-primary-foreground"
                              : "border-border bg-background hover:border-primary/50 text-foreground",
                          )}
                        >
                          {tab.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Spell rows */}
                <div className="themed-scrollbar flex-1 overflow-y-auto px-5 pb-4">
                  {hasSpellbook && wizardMode === "prepare" && current.spellbook.length === 0 ? (
                    <div className="py-8 text-center space-y-3">
                      <p className="text-sm text-muted-foreground">Your spellbook has no spells yet.</p>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setWizardMode("spellbook")}
                        className="text-xs"
                      >
                        <BookOpen className="h-3.5 w-3.5 mr-1.5" />
                        Add Spells to Spellbook
                      </Button>
                    </div>
                  ) : filteredAvailable.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No spells match.</p>
                  ) : (
                    <ul className="space-y-0.5">
                      {filteredAvailable.map((spell) => {
                        const inSpellbook = current.spellbook.includes(spell.name);
                        const isPrepared =
                          (spell.level ?? 0) === 0
                            ? current.cantrips.includes(spell.name)
                            : current.spells.includes(spell.name);
                        const isSelected =
                          hasSpellbook && wizardMode === "spellbook"
                            ? inSpellbook
                            : isPrepared;
                        const isSavant =
                          Boolean(savantSchool) &&
                          spell.school?.toLowerCase() === savantSchool?.toLowerCase();
                        const expandKey = `available:${spell.name}`;
                        const isExpanded = expandedSpells.has(expandKey);
                        return (
                          <li key={spell.name}>
                            <div className="flex items-center gap-1.5 py-1">
                              <span className="flex flex-1 items-center gap-1.5 text-sm min-w-0">
                                <span className="truncate text-foreground">{spell.name}</span>
                                {spell.concentration && (
                                  <span title="Concentration" className="shrink-0 rounded bg-amber-600/80 px-1 py-0.5 text-[10px] font-semibold uppercase text-white">
                                    C
                                  </span>
                                )}
                                {spell.ritual && (
                                  <span title="Ritual" className="shrink-0 rounded bg-sky-600/80 px-1 py-0.5 text-[10px] font-semibold uppercase text-white">
                                    R
                                  </span>
                                )}
                                {hasSpellbook && wizardMode === "spellbook" && isSavant && (
                                  <span className="shrink-0 rounded border border-primary/40 bg-primary/10 px-1 py-0.5 text-[10px] font-semibold uppercase text-primary">
                                    {savantSchool}
                                  </span>
                                )}
                                <span className="shrink-0 text-xs text-muted-foreground">
                                  ({levelOrdinal(spell.level)})
                                </span>
                              </span>
                              <button
                                type="button"
                                onClick={() => {
                                  if (hasSpellbook && wizardMode === "spellbook") {
                                    toggleSpellbook(spell);
                                  } else {
                                    toggleSpell(spell);
                                  }
                                }}
                                disabled={spell.isAlwaysPrepared}
                                className={cn(
                                  "shrink-0 rounded border px-2 w-16 py-0.5 font-mono text-[11px] transition-colors",
                                  spell.isAlwaysPrepared
                                    ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 cursor-not-allowed"
                                    : isSelected
                                      ? "border-primary bg-primary/10 text-primary hover:bg-primary/20"
                                      : "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground",
                                )}
                              >
                                {spell.isAlwaysPrepared
                                  ? "ALWAYS"
                                  : hasSpellbook && wizardMode === "spellbook"
                                    ? isSelected ? "IN BOOK" : "LEARN"
                                    : (spell.level ?? 0) === 0
                                      ? isSelected ? "UNLEARN" : "LEARN"
                                      : isSelected ? "UNSELECT" : "SELECT"}
                              </button>
                              {/* Accordion toggle */}
                              <button
                                type="button"
                                onClick={() => toggleExpand(expandKey)}
                                className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
                                aria-label={isExpanded ? "Hide spell details" : "Show spell details"}
                              >
                                {isExpanded ? (
                                  <ChevronUp className="h-4 w-4" />
                                ) : (
                                  <ChevronDown className="h-4 w-4" />
                                )}
                              </button>
                            </div>

                            {/* Accordion body */}
                            {isExpanded && (
                              <div className="mb-1.5 rounded border border-border bg-background/50 px-3 py-2 text-xs space-y-2">
                                {(() => {
                                  const meta: Array<[string, string | undefined]> = [
                                    ["Level", levelOrdinal(spell.level) || undefined],
                                    ["School", spell.school],
                                    ["Casting Time", spell.casting_time],
                                    ["Range", spell.range],
                                    [
                                      "Components",
                                      spell.components && spell.components.length > 0
                                        ? spell.components.join(", ")
                                        : undefined,
                                    ],
                                    ["Duration", spell.duration],
                                  ].filter(([, v]) => v) as Array<[string, string]>;
                                  return meta.length > 0 ? (
                                    <div className="text-muted-foreground">
                                      {meta.map(([k, v], j) => (
                                        <span key={k}>
                                          <span className="font-semibold text-foreground/80">{k}:</span>{" "}
                                          {v}
                                          {j < meta.length - 1 ? " | " : ""}
                                        </span>
                                      ))}
                                    </div>
                                  ) : null;
                                })()}
                                {spell.concentration && (
                                  <div className="text-[10px] font-semibold uppercase tracking-wide text-primary">
                                    * Concentration
                                  </div>
                                )}
                                {spell.description && (
                                  <p className="whitespace-pre-line text-foreground/90">
                                    {spell.description}
                                  </p>
                                )}
                              </div>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              </div>

              {/* ── Right: Prepared Spells OR Spellbook Contents ──────────────────────── */}
              <div
                className={cn(
                  "shrink-0 flex-col overflow-hidden md:flex md:basis-2/5",
                  mobileViewTab === "prepared" ? "flex flex-1 w-full" : "hidden",
                )}
              >
                {hasSpellbook && wizardMode === "spellbook" ? (
                  <>
                    <div className="px-4 pt-4 pb-2 shrink-0">
                      <h3 className="font-display text-lg text-primary font-semibold flex items-center gap-2">
                        <BookOpen className="h-4 w-4" />
                        <span>Spellbook</span>
                      </h3>
                    </div>

                    {/* Spellbook summary card */}
                    <div className="mx-4 mb-2 shrink-0 rounded border border-border bg-background/50 p-2.5 space-y-1 text-center">
                      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
                        Spellbook Capacity
                      </div>
                      <div className="text-base font-semibold tabular-nums text-foreground">
                        {current.spellbook.length}
                        <span className="text-muted-foreground font-normal"> / {totalSpellbook}</span>
                      </div>
                      {savantSchool && (
                        <p className="text-[11px] text-primary">
                          ✦ {savantSchool} Savant (+{savantSpells} bonus spells included)
                        </p>
                      )}
                      <p className="text-[10px] text-muted-foreground italic">
                        Ritual Adept: Cast ritual spells directly from your spellbook.
                      </p>
                    </div>

                    {/* Spellbook spells grouped by level */}
                    <div className="themed-scrollbar flex-1 overflow-y-auto px-4 pb-4">
                      {current.spellbook.length === 0 ? (
                        <p className="text-sm text-muted-foreground">Your spellbook is empty.</p>
                      ) : (
                        <div className="space-y-3">
                          {spellbookGroups.map((group) => (
                            <div key={group.level}>
                              <div className="mb-1 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
                                {group.label}
                              </div>
                              <ul className="space-y-0.5">
                                {group.spells.map((spell) => {
                                  const isPrepared = current.spells.includes(spell.name);
                                  const expandKey = `spellbook:${spell.name}`;
                                  const isExpanded = expandedSpells.has(expandKey);
                                  return (
                                    <li key={spell.name}>
                                      <div className="flex items-center gap-1.5 py-1">
                                        <span className="flex flex-1 items-center gap-1.5 text-sm min-w-0">
                                          <span className="truncate text-foreground">{spell.name}</span>
                                          {spell.concentration && (
                                            <span title="Concentration" className="shrink-0 rounded bg-amber-600/80 px-1 py-0.5 text-[10px] font-semibold uppercase text-white">
                                              C
                                            </span>
                                          )}
                                          {spell.ritual && (
                                            <span title="Ritual" className="shrink-0 rounded bg-sky-600/80 px-1 py-0.5 text-[10px] font-semibold uppercase text-white">
                                              R
                                            </span>
                                          )}
                                          {isPrepared && (
                                            <span className="shrink-0 rounded border border-emerald-500/40 bg-emerald-500/10 px-1 py-0.5 text-[9px] font-semibold uppercase text-emerald-600 dark:text-emerald-400">
                                              PREP
                                            </span>
                                          )}
                                        </span>
                                        <button
                                          type="button"
                                          onClick={() => removeSpellFromSpellbook(spell.name)}
                                          className="shrink-0 rounded border border-border px-1.5 py-0.5 w-16 font-mono text-[10px] text-muted-foreground hover:border-destructive/60 hover:text-destructive transition-colors"
                                        >
                                          REMOVE
                                        </button>
                                        <button
                                          type="button"
                                          onClick={() => toggleExpand(expandKey)}
                                          className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
                                          aria-label={isExpanded ? "Hide spell details" : "Show spell details"}
                                        >
                                          {isExpanded ? (
                                            <ChevronUp className="h-4 w-4" />
                                          ) : (
                                            <ChevronDown className="h-4 w-4" />
                                          )}
                                        </button>
                                      </div>

                                      {isExpanded && (
                                        <div className="mb-1.5 rounded border border-border bg-background/50 px-3 py-2 text-xs space-y-2">
                                          {(() => {
                                            const meta: Array<[string, string | undefined]> = [
                                              ["Level", levelOrdinal(spell.level) || undefined],
                                              ["School", spell.school],
                                              ["Casting Time", spell.casting_time],
                                              ["Range", spell.range],
                                              [
                                                "Components",
                                                spell.components && spell.components.length > 0
                                                  ? spell.components.join(", ")
                                                  : undefined,
                                              ],
                                              ["Duration", spell.duration],
                                            ].filter(([, v]) => v) as Array<[string, string]>;
                                            return meta.length > 0 ? (
                                              <div className="text-muted-foreground">
                                                {meta.map(([k, v], j) => (
                                                  <span key={k}>
                                                    <span className="font-semibold text-foreground/80">{k}:</span>{" "}
                                                    {v}
                                                    {j < meta.length - 1 ? " | " : ""}
                                                  </span>
                                                ))}
                                              </div>
                                            ) : null;
                                          })()}
                                          {spell.concentration && (
                                            <div className="text-[10px] font-semibold uppercase tracking-wide text-primary">
                                              * Concentration
                                            </div>
                                          )}
                                          {spell.description && (
                                            <p className="whitespace-pre-line text-foreground/90">
                                              {spell.description}
                                            </p>
                                          )}
                                        </div>
                                      )}
                                    </li>
                                  );
                                })}
                              </ul>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="px-4 pt-4 pb-2 shrink-0">
                      <h3 className="font-display text-lg text-primary font-semibold">
                        Prepared Spells
                      </h3>
                    </div>

                    {/* Spell slots box */}
                    {allSlotDisplay.length > 0 && (
                      <div className="mx-4 mb-2 shrink-0 rounded border border-border bg-background/50 p-2">
                        <div className="flex flex-1 justify-center items-center gap-6">
                          <div className="flex shrink-0 text-[10px] uppercase tracking-widest text-muted-foreground leading-tight">
                            Slots
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {allSlotDisplay.map((slot) => (
                              <div
                                key={slot.kind === "pact" ? `pact-${slot.className ?? "slot"}-${slot.level}` : `regular-${slot.level}`}
                                className="flex flex-col items-center gap-0.5"
                              >
                                <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                                  {slot.kind === "pact"
                                    ? `Pact ${LEVEL_ORDINALS[slot.level] ?? `${slot.level}th`}`
                                    : LEVEL_ORDINALS[slot.level] ?? `${slot.level}th`}
                                </span>
                                <span className="text-sm font-semibold text-foreground">{slot.count}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Count line */}
                    <div className="px-4 pb-3 shrink-0">
                      <div className="grid grid-cols-2 gap-2">
                        {(() => {
                          const items: Array<{ label: string; used: number; max: number }> = [
                            { label: "Cantrips", used: current.cantrips.length, max: maxCantrips },
                            { label: "Spells", used: current.spells.length, max: maxSpells },
                          ];
                          return items.map(({ label, used, max }) => {
                            const atCap = max > 0 && used >= max;
                            return (
                              <div
                                key={label}
                                className={cn(
                                  "flex flex-col items-center justify-center rounded border px-2 py-1.5 transition-colors",
                                  atCap
                                    ? "border-emerald-600/50 bg-emerald-600/10"
                                    : "border-border bg-background/50",
                                )}
                              >
                                <span className="text-[10px] uppercase tracking-widest text-muted-foreground">
                                  {label}
                                </span>
                                <span
                                  className={cn(
                                    "text-base font-semibold tabular-nums",
                                    atCap ? "text-emerald-600" : "text-foreground",
                                  )}
                                >
                                  {used}
                                  <span className="text-muted-foreground">/{max}</span>
                                </span>
                              </div>
                            );
                          });
                        })()}
                      </div>
                    </div>

                    {/* Flat prepared list with accordion */}
                    <div className="themed-scrollbar flex-1 overflow-y-auto px-4 pb-4">
                      {preparedFlat.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                          {hasSpellbook && current.spellbook.length > 0
                            ? "None prepared yet. Select spells from your spellbook on the left to prepare them."
                            : "None prepared yet."}
                        </p>
                      ) : (
                        <div className="space-y-3">
                          {preparedGroups.map((group) => (
                            <div key={group.level}>
                              <div className="mb-1 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
                                {group.label}
                              </div>
                              <ul className="space-y-0.5">
                                {group.spells.map((spell) => {
                                  const expandKey = `prepared:${spell.name}`;
                                  const isExpanded = expandedSpells.has(expandKey);
                                  return (
                                    <li key={spell.name}>
                                      {/* Row */}
                                      <div className="flex items-center gap-1.5 py-1">
                                        <span className="flex flex-1 items-center gap-1.5 text-sm min-w-0">
                                          <span className="truncate text-foreground">{spell.name}</span>
                                          {spell.concentration && (
                                            <span className="shrink-0 rounded bg-amber-600/80 px-1 py-0.5 text-[10px] font-semibold uppercase text-white">
                                              C
                                            </span>
                                          )}
                                          {spell.ritual && (
                                            <span className="shrink-0 rounded bg-sky-600/80 px-1 py-0.5 text-[10px] font-semibold uppercase text-white">
                                              R
                                            </span>
                                          )}
                                        </span>
                                        <button
                                          type="button"
                                          onClick={() => unprepareSpell(spell)}
                                          disabled={spell.isAlwaysPrepared}
                                          className={cn(
                                            "shrink-0 rounded border px-1.5 py-0.5 w-16 font-mono text-[10px] transition-colors",
                                            spell.isAlwaysPrepared
                                              ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 cursor-not-allowed"
                                              : "border-border text-muted-foreground hover:border-destructive/60 hover:text-destructive",
                                          )}
                                        >
                                          {spell.isAlwaysPrepared
                                            ? "ALWAYS"
                                            : (spell.level ?? 0) === 0
                                              ? "UNLEARN"
                                              : "UNSELECT"}
                                        </button>
                                        {/* Accordion toggle */}
                                        <button
                                          type="button"
                                          onClick={() => toggleExpand(expandKey)}
                                          className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
                                          aria-label={isExpanded ? "Hide spell details" : "Show spell details"}
                                        >
                                          {isExpanded ? (
                                            <ChevronUp className="h-4 w-4" />
                                          ) : (
                                            <ChevronDown className="h-4 w-4" />
                                          )}
                                        </button>
                                      </div>

                                      {/* Accordion body */}
                                      {isExpanded && (
                                        <div className="mb-1.5 rounded border border-border bg-background/50 px-3 py-2 text-xs space-y-2">
                                          {(() => {
                                            const meta: Array<[string, string | undefined]> = [
                                              ["Level", levelOrdinal(spell.level) || undefined],
                                              ["School", spell.school],
                                              ["Casting Time", spell.casting_time],
                                              ["Range", spell.range],
                                              [
                                                "Components",
                                                spell.components && spell.components.length > 0
                                                  ? spell.components.join(", ")
                                                  : undefined,
                                              ],
                                              ["Duration", spell.duration],
                                            ].filter(([, v]) => v) as Array<[string, string]>;
                                            return meta.length > 0 ? (
                                              <div className="text-muted-foreground">
                                                {meta.map(([k, v], j) => (
                                                  <span key={k}>
                                                    <span className="font-semibold text-foreground/80">{k}:</span>{" "}
                                                    {v}
                                                    {j < meta.length - 1 ? " | " : ""}
                                                  </span>
                                                ))}
                                              </div>
                                            ) : null;
                                          })()}
                                          {spell.concentration && (
                                            <div className="text-[10px] font-semibold uppercase tracking-wide text-primary">
                                              * Concentration
                                            </div>
                                          )}
                                          {spell.description && (
                                            <p className="whitespace-pre-line text-foreground/90">
                                              {spell.description}
                                            </p>
                                          )}
                                        </div>
                                      )}
                                    </li>
                                  );
                                })}
                              </ul>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="shrink-0 border-t border-border px-5 py-3 flex justify-end">
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}


