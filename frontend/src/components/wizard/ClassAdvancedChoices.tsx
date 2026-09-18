import { useMemo, useState } from "react";
import { AlertCircle, BookOpen, Check, ChevronDown, ChevronUp, Info, Package, Search, Sparkles, Wand2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useCharacterStore } from "@/store/characterStore";
import { ChoiceList } from "./ChoiceList";

type Loose = Record<string, unknown>;

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

interface CurrentSpellSelections {
  cantrips: string[];
  spells: string[];
  spellbook: string[];
  background_cantrips: string[];
  background_spells: string[];
}

export interface SpellReference {
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

function normalizeSpellReference(raw: Loose): SpellReference | null {
  const name = str(raw.name);
  if (!name) return null;

  const rawComponents = raw.components;
  const components =
    typeof rawComponents === "string"
      ? [rawComponents]
      : arr<string>(rawComponents).filter(
          (entry): entry is string =>
            typeof entry === "string" && entry.length > 0,
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
      typeof raw.counts_against_limit === "boolean"
        ? raw.counts_against_limit
        : undefined,
    ritual: typeof raw.ritual === "boolean" ? raw.ritual : undefined,
    concentration:
      typeof raw.concentration === "boolean" ? raw.concentration : undefined,
  };
}

function spellLevelLabel(level?: number): string {
  if (level === 0) return "Cantrip";
  if (typeof level === "number" && Number.isFinite(level)) {
    return `Level ${level}`;
  }
  return "Spell";
}

function matchesChoiceContext(
  responseChoices: unknown,
  sourceChoices: Loose,
): boolean {
  if (!responseChoices || typeof responseChoices !== "object" || Array.isArray(responseChoices)) {
    return false;
  }

  const response = responseChoices as Loose;
  const responseClass = str(response.class) ?? "";
  const responseSubclass = str(response.subclass) ?? "";
  const responseLevel = num(response.level) ?? 1;
  const sourceClass = str(sourceChoices.class) ?? "";
  const sourceSubclass = str(sourceChoices.subclass) ?? "";
  const sourceLevel = num(sourceChoices.level) ?? 1;

  return (
    responseClass === sourceClass &&
    responseSubclass === sourceSubclass &&
    responseLevel === sourceLevel
  );
}

/**
 * Renders the spell, weapon-mastery, and eldritch-invocation pickers
 * inside the class step. Each picker silently hides itself when the
 * underlying derived view reports `applicable: false`.
 */
export function ClassAdvancedChoices({
  choicesForDerived,
  inspectedSpellName,
  onInspectSpell,
  hideSpells = false,
  onlySpells = false,
}: {
  choicesForDerived?: Loose;
  inspectedSpellName?: string;
  onInspectSpell?: (spell: SpellReference) => void;
  hideSpells?: boolean;
  onlySpells?: boolean;
} = {}) {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const sourceChoices = choicesForDerived ?? choicesMade;

  const spellsQ = useDerived(sourceChoices, "spell_management");
  const masteryQ = useDerived(sourceChoices, "mastery_management");
  const invocationsQ = useDerived(sourceChoices, "invocation_management");
  const replicationsQ = useDerived(sourceChoices, "replicate_magic_item_management");
  const spellsData = hideSpells ? null : getApplicableData(spellsQ, sourceChoices);
  const masteryData = onlySpells ? null : getApplicableData(masteryQ, sourceChoices);
  const invocationsData = onlySpells ? null : getApplicableData(invocationsQ, sourceChoices);
  const replicationsData = onlySpells ? null : getApplicableData(replicationsQ, sourceChoices);

  const anyVisible = Boolean(spellsData || masteryData || invocationsData || replicationsData);
  const isLoading =
    (!spellsQ.error &&
      !spellsData &&
      !hideSpells &&
      spellsQ.fetchStatus === "fetching") ||
    (!masteryQ.error &&
      !masteryData &&
      !onlySpells &&
      masteryQ.fetchStatus === "fetching") ||
    (!invocationsQ.error &&
      !invocationsData &&
      !onlySpells &&
      invocationsQ.fetchStatus === "fetching") ||
    (!replicationsQ.error &&
      !replicationsData &&
      !onlySpells &&
      replicationsQ.fetchStatus === "fetching");
  if (!anyVisible && !isLoading) return null;

  return (
    <section className="rounded-xl border border-border/70 bg-card/50 p-5 shadow-sm sm:p-6">
      <div className="mb-5 flex items-start gap-3">
        <div className="rounded-full bg-primary/10 p-2 text-primary">
          {onlySpells ? <BookOpen className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
            {onlySpells ? "Magic & Spells" : "Class refinement"}
          </p>
          <h3 className="mt-1 font-display text-xl text-primary font-semibold">
            {onlySpells ? "Spell Preparation & Spellbook" : "Class loadout"}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {onlySpells
              ? "Select your prepared spells, cantrips, and manage your spellbook for your adventure."
              : "Finish the class-specific picks that shape how this character plays."}
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {!anyVisible && isLoading ? (
          <div className="rounded-xl border border-dashed border-border/70 bg-background/60 px-4 py-5 text-sm text-muted-foreground">
            Loading {onlySpells ? "spells" : "class loadout"}…
          </div>
        ) : (
          <>
            {spellsData && (
              <SpellPicker
                data={spellsData}
                inspectedSpellName={inspectedSpellName}
                onInspectSpell={onInspectSpell}
              />
            )}
            {masteryData && (
              <MasteryPicker data={masteryData} />
            )}
            {invocationsData && (
              <InvocationPicker data={invocationsData} />
            )}
            {replicationsData && (
              <ReplicateMagicItemPicker data={replicationsData} />
            )}
          </>
        )}
      </div>
    </section>
  );
}

function useDerived(choicesMade: Loose, view: string) {
  // Key on only the fields that change which options are available.
  // Selecting a spell or mastery does not change the available-options list.
  // Invocation cantrip choices do, so keep invocation selections in the key.
  return useQuery({
    queryKey: [
      "character", "derived", view,
      choicesMade.class,
      choicesMade.level,
      choicesMade.subclass,
      choicesMade.classes,
      choicesMade.eldritch_invocation_selections,
      choicesMade.artificer_replicate_plans,
      choicesMade.artificer_active_replications,
    ],
    queryFn: () => api.character.derived(choicesMade, view),
    enabled: Array.isArray(choicesMade["classes"]) && (choicesMade["classes"] as unknown[]).length > 0,
    retry: false,
  });
}

function getApplicableData(
  q: { data?: unknown },
  sourceChoices: Loose,
): Loose | null {
  if (!q.data || typeof q.data !== "object") return null;
  const payload = q.data as Loose;
  if (!matchesChoiceContext(payload.choices_made, sourceChoices)) {
    return null;
  }
  if (payload.applicable !== true) return null;
  const data = payload.data;
  if (data && typeof data === "object" && !Array.isArray(data)) {
    return data as Loose;
  }
  return null;
}

// ---------- Spells ----------

export function SpellPicker({
  data,
  inspectedSpellName,
  onInspectSpell,
}: {
  data: Loose;
  inspectedSpellName?: string;
  onInspectSpell?: (spell: SpellReference) => void;
}) {
  const setChoice = useCharacterStore((s) => s.setChoice);
  const choicesMade = useCharacterStore((s) => s.choicesMade);

  const hasSpellbook = Boolean(data.has_spellbook);
  const spellbookLimits = rec(data.spellbook_limits);
  const totalSpellbook = num(spellbookLimits.total_spells) ?? 6;
  const savantSchool = str(spellbookLimits.savant_school);
  const savantSpells = num(spellbookLimits.savant_spells) ?? 0;

  const limits = rec(data.limits);
  const maxCantrips = num(limits.cantrips) ?? 0;
  const maxSpells = num(limits.spells) ?? 0;

  const availableCantrips = arr<Loose>(data.available_cantrips);
  const availableSpellsByLevel = rec(data.available_spells);
  const alwaysPrepared = useMemo(
    () =>
      arr<Loose>(data.always_prepared)
        .map(normalizeSpellReference)
        .filter((spell): spell is SpellReference => Boolean(spell))
        .map((spell) => ({ ...spell, is_always_prepared: true as const })),
    [data.always_prepared],
  );
  const alwaysPreparedNames = useMemo(
    () => new Set(alwaysPrepared.map((spell) => spell.name)),
    [alwaysPrepared],
  );

  const current =
    (choicesMade["spell_selections"] as CurrentSpellSelections | undefined) ??
    normalizeCurrent(rec(data.current_selections));

  function update(patch: Partial<CurrentSpellSelections>) {
    const next: CurrentSpellSelections = {
      cantrips: current.cantrips,
      spells: current.spells,
      spellbook: current.spellbook,
      background_cantrips: current.background_cantrips,
      background_spells: current.background_spells,
      ...patch,
    };
    setChoice("spell_selections", next);
  }

  function toggle(
    list: string[],
    name: string,
    cap: number,
  ): string[] | null {
    if (list.includes(name)) {
      return list.filter((n) => n !== name);
    }
    if (list.length >= cap) return null;
    return [...list, name];
  }

  // Lookup map for spell definitions
  const spellMap = useMemo(() => {
    const map = new Map<string, SpellReference>();
    Object.values(availableSpellsByLevel).forEach((rawList) => {
      arr<Loose>(rawList).forEach((raw) => {
        const ref = normalizeSpellReference(raw);
        if (ref) map.set(ref.name, ref);
      });
    });
    arr<Loose>(data.spellbook).forEach((raw) => {
      const ref = normalizeSpellReference(raw);
      if (ref) map.set(ref.name, ref);
    });
    return map;
  }, [availableSpellsByLevel, data.spellbook]);

  // Spells in spellbook grouped by level for the prepared picker
  const spellbookSpellsByLevel = useMemo(() => {
    const grouped: Record<number, SpellReference[]> = {};
    for (const name of current.spellbook) {
      const ref = spellMap.get(name) || { name, level: 1 };
      const lvl = ref.level ?? 1;
      if (!grouped[lvl]) grouped[lvl] = [];
      grouped[lvl].push(ref);
    }
    return grouped;
  }, [current.spellbook, spellMap]);

  function toggleSpellbook(name: string) {
    if (current.spellbook.includes(name)) {
      const nextBook = current.spellbook.filter((n) => n !== name);
      const nextSpells = current.spells.filter((n) => n !== name);
      update({ spellbook: nextBook, spells: nextSpells });
    } else {
      if (current.spellbook.length < totalSpellbook) {
        update({ spellbook: [...current.spellbook, name] });
      }
    }
  }

  function togglePrepared(name: string) {
    const next = toggle(current.spells, name, maxSpells);
    if (next) update({ spells: next });
  }

  return (
    <div className="rounded-xl border border-border/70 bg-background/70 p-4 shadow-sm space-y-5 sm:p-5">
      <header>
        <div className="flex items-center gap-2">
          {hasSpellbook && <BookOpen className="h-4 w-4 text-primary" />}
          <h4 className="font-display text-base text-primary font-semibold">
            {hasSpellbook ? "Wizard Spells & Spellbook" : "Spells"}
          </h4>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          Cantrips {current.cantrips.length}/{maxCantrips} ·{" "}
          {hasSpellbook && `Spellbook ${current.spellbook.length}/${totalSpellbook} · `}
          Prepared spells {current.spells.length}/{maxSpells}
        </p>
        {hasSpellbook && savantSchool && (
          <p className="text-xs text-primary/90 mt-1">
            ✦ {savantSchool} Savant: includes bonus {savantSchool} spells (+{savantSpells})
          </p>
        )}
      </header>

      {alwaysPrepared.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs uppercase text-muted-foreground">
            Always prepared
          </div>
          <ul className="space-y-2">
            {alwaysPrepared.map((spell) => {
              const isInspected = inspectedSpellName === spell.name;
              return (
                <li key={`${spell.name}-${spell.source ?? "always-prepared"}`}>
                  <button
                    type="button"
                    onClick={() => onInspectSpell?.(spell)}
                    aria-pressed={isInspected}
                    className={cn(
                      "w-full rounded-lg border px-3 py-3 text-left transition-all duration-200",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                      isInspected
                        ? "border-primary bg-muted/60 shadow-sm ring-1 ring-primary/20"
                        : "border-border/80 bg-background/80 hover:border-primary/30 hover:bg-secondary/60",
                    )}
                  >
                    <div className="flex flex-wrap items-center text-sm gap-1.5">
                      <span className="font-medium text-foreground">{spell.name}</span>
                      {spell.concentration === true && (
                        <span className="shrink-0 rounded bg-amber-600/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                          C
                        </span>
                      )}
                      {spell.ritual === true && (
                        <span className="shrink-0 rounded bg-sky-600/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                          R
                        </span>
                      )}
                      <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[11px] uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
                        Always prepared
                      </span>
                      <span className="rounded-full border border-primary/70 bg-background px-2 py-0.5 text-[11px] uppercase tracking-wide text-foreground">
                        {spellLevelLabel(spell.level)}
                      </span>
                      {spell.source && (
                        <span className="rounded-full border border-border/70 bg-primary px-2 py-0.5 text-[11px] uppercase tracking-wide text-background">
                          {spell.source}
                        </span>
                      )}

                    </div>
                    {(spell.school || spell.description) && (
                      <div className="mt-2 text-sm text-muted-foreground">
                        {spell.description && (
                          <div className="line-clamp-2">{spell.description}</div>
                        )}
                        {spell.school && (
                          <span className="text-primary text-xs">{spell.school}</span>
                        )}
                      </div>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {availableCantrips.length > 0 && maxCantrips > 0 && (
        <SpellGroup
          title="Cantrips"
          spells={normalizeSpellList(availableCantrips)}
          selected={current.cantrips}
          disabledNames={alwaysPreparedNames}
          inspectedSpellName={inspectedSpellName}
          onInspect={onInspectSpell}
          onToggle={(name) => {
            const next = toggle(current.cantrips, name, maxCantrips);
            if (next) update({ cantrips: next });
          }}
        />
      )}

      {hasSpellbook ? (
        <>
          {/* Section 1: Spellbook (Known Spells) */}
          <div className="border-t border-border/70 pt-4 space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <h5 className="font-display text-sm text-primary font-semibold flex items-center gap-1.5">
                  <BookOpen className="h-3.5 w-3.5" />
                  <span>Spellbook (Known Spells)</span>
                </h5>
                <span className="text-xs font-mono font-medium text-muted-foreground">
                  {current.spellbook.length} / {totalSpellbook}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Choose spells to record in your spellbook. Ritual spells in your spellbook can be cast without preparing them.
              </p>
            </div>

            {Object.keys(availableSpellsByLevel)
              .sort((a, b) => Number(a) - Number(b))
              .map((lvl) => {
                if (lvl === "0") return null;
                const list = arr<Loose>(availableSpellsByLevel[lvl]);
                if (list.length === 0) return null;
                return (
                  <SpellGroup
                    key={`book-lvl-${lvl}`}
                    title={`Level ${lvl} Spells`}
                    spells={normalizeSpellList(list)}
                    selected={current.spellbook}
                    disabledNames={alwaysPreparedNames}
                    inspectedSpellName={inspectedSpellName}
                    onInspect={onInspectSpell}
                    highlightSchool={savantSchool}
                    highlightBadge={`${savantSchool} Savant`}
                    onToggle={toggleSpellbook}
                  />
                );
              })}
          </div>

          {/* Section 2: Prepared Spells (from Spellbook) */}
          <div className="border-t border-border/70 pt-4 space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <h5 className="font-display text-sm text-primary font-semibold flex items-center gap-1.5">
                  <Wand2 className="h-3.5 w-3.5" />
                  <span>Prepared Spells</span>
                </h5>
                <span className="text-xs font-mono font-medium text-muted-foreground">
                  {current.spells.length} / {maxSpells}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Choose which spells from your spellbook you have prepared to cast today.
              </p>
            </div>

            {current.spellbook.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border/70 p-4 text-center text-xs text-muted-foreground">
                Select spells for your spellbook above to prepare them here.
              </div>
            ) : (
              Object.keys(spellbookSpellsByLevel)
                .sort((a, b) => Number(a) - Number(b))
                .map((lvlStr) => {
                  const lvl = Number(lvlStr);
                  const list = spellbookSpellsByLevel[lvl] || [];
                  if (list.length === 0) return null;
                  return (
                    <SpellGroup
                      key={`prep-lvl-${lvl}`}
                      title={`Level ${lvl} in Spellbook`}
                      spells={list}
                      selected={current.spells}
                      disabledNames={alwaysPreparedNames}
                      inspectedSpellName={inspectedSpellName}
                      onInspect={onInspectSpell}
                      onToggle={togglePrepared}
                    />
                  );
                })
            )}
          </div>
        </>
      ) : (
        /* Regular caster (non-wizard) */
        Object.keys(availableSpellsByLevel)
          .sort((a, b) => Number(a) - Number(b))
          .map((lvl) => {
            if (lvl === "0") return null;
            const list = arr<Loose>(availableSpellsByLevel[lvl]);
            if (list.length === 0) return null;
            return (
              <SpellGroup
                key={lvl}
                title={`Level ${lvl}`}
                spells={normalizeSpellList(list)}
                selected={current.spells}
                disabledNames={alwaysPreparedNames}
                inspectedSpellName={inspectedSpellName}
                onInspect={onInspectSpell}
                onToggle={(name) => {
                  const next = toggle(current.spells, name, maxSpells);
                  if (next) update({ spells: next });
                }}
              />
            );
          })
      )}

      <BackgroundSpells
        requirements={rec(data.background_requirements)}
        current={current}
        update={update}
        disabledNames={alwaysPreparedNames}
        inspectedSpellName={inspectedSpellName}
        onInspect={onInspectSpell}
      />
    </div>
  );
}

function normalizeSpellList(raw: Loose[]): SpellReference[] {
  return raw
    .map(normalizeSpellReference)
    .filter((spell): spell is SpellReference => Boolean(spell));
}

function SpellGroup({
  title,
  spells,
  selected,
  disabledNames,
  onToggle,
  onInspect,
  inspectedSpellName,
  highlightSchool,
  highlightBadge,
}: {
  title: string;
  spells: SpellReference[];
  selected: string[];
  disabledNames?: Set<string>;
  onToggle: (name: string) => void;
  onInspect?: (spell: SpellReference) => void;
  inspectedSpellName?: string;
  highlightSchool?: string;
  highlightBadge?: string;
}) {
  return (
    <div>
      <div className="text-xs uppercase text-muted-foreground mb-1">
        {title}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
        {spells.map((spell, i) => {
          const name = spell.name;
          const school = spell.school;
          const isSelected = selected.includes(name);
          const isDisabled = disabledNames?.has(name) ?? false;
          const isInspected = inspectedSpellName === name;
          const isHighlight =
            Boolean(highlightSchool) &&
            school?.toLowerCase() === highlightSchool?.toLowerCase();
          return (
            <div
              key={`${name}-${i}`}
              className={cn(
                "flex items-stretch gap-1 rounded-lg border text-left text-sm transition-all duration-200",
                isDisabled
                  ? "border-border/70 bg-muted/30 text-muted-foreground opacity-80"
                  : isSelected
                  ? "border-primary bg-muted/60 shadow-sm ring-1 ring-primary/20"
                  : isInspected
                  ? "border-muted-foreground/40 bg-secondary/60 ring-1 ring-muted-foreground/20"
                  : "border-border bg-background/70 hover:border-primary/30 hover:bg-secondary/60",
              )}
            >
              <button
                type="button"
                onClick={() => {
                  if (!isDisabled) onToggle(name);
                }}
                aria-pressed={isSelected}
                aria-disabled={isDisabled}
                disabled={isDisabled}
                className={cn(
                  "flex flex-1 items-center justify-between gap-3 rounded-l-lg px-3 py-2 text-left",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  isDisabled ? "cursor-not-allowed" : "cursor-pointer",
                )}
              >
                <span className="min-w-0">
                  <span className="flex flex-wrap items-center gap-1.5">
                    <span>{name}</span>
                    {spell.concentration === true && (
                      <span
                        title="Concentration"
                        className="shrink-0 rounded bg-amber-600/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
                      >
                        C
                      </span>
                    )}
                    {spell.ritual === true && (
                      <span
                        title="Ritual"
                        className="shrink-0 rounded bg-sky-600/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
                      >
                        R
                      </span>
                    )}
                    {isHighlight && (
                      <span className="shrink-0 rounded border border-primary/40 bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary">
                        {highlightBadge ?? "Savant"}
                      </span>
                    )}
                  </span>
                  {(school || spell.ritual === true || isDisabled) && (
                    <span className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
                      {school && <span>{school}</span>}
                      {spell.ritual === true && (
                        <span className="text-sky-600 dark:text-sky-400 font-medium">Ritual</span>
                      )}
                      {isDisabled && (
                        <span className="rounded-full border border-border/70 bg-background px-2 py-0.5 uppercase tracking-wide">
                          Always prepared
                        </span>
                      )}
                    </span>
                  )}
                </span>
                <span
                  className={cn(
                    "inline-flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border",
                    isDisabled
                      ? "border-border/70 bg-background text-muted-foreground"
                      : isSelected
                      ? "border-primary bg-background text-primary"
                      : "border-border bg-background text-transparent",
                  )}
                >
                  <Check className="h-3 w-3" />
                </span>
              </button>
              {onInspect && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onInspect(spell);
                  }}
                  aria-label="View spell details"
                  aria-pressed={isInspected}
                  className={cn(
                    "flex flex-shrink-0 items-center justify-center rounded-r-lg p-1 px-2 text-muted-foreground transition-colors",
                    "hover:bg-muted hover:text-foreground",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                    isInspected && "text-primary",
                  )}
                >
                  <Info className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BackgroundSpells({
  requirements,
  current,
  update,
  disabledNames,
  inspectedSpellName,
  onInspect,
}: {
  requirements: Loose;
  current: CurrentSpellSelections;
  update: (patch: Partial<CurrentSpellSelections>) => void;
  disabledNames?: Set<string>;
  inspectedSpellName?: string;
  onInspect?: (spell: SpellReference) => void;
}) {
  const cantripReq = rec(requirements.cantrips);
  const spellReq = rec(requirements.spells);
  const cantripsNeeded = num(cantripReq.count);
  const spellsNeeded = num(spellReq.count);
  if (!cantripsNeeded && !spellsNeeded) return null;

  return (
    <div className="border-t border-border pt-3 space-y-3">
      <div className="text-xs uppercase text-muted-foreground">
        Background spells
      </div>
      {cantripsNeeded ? (
        <SpellGroup
          title={`Background cantrips (${current.background_cantrips.length}/${cantripsNeeded})`}
          spells={normalizeSpellList(arr<Loose>(cantripReq.available))}
          selected={current.background_cantrips}
          disabledNames={disabledNames}
          inspectedSpellName={inspectedSpellName}
          onInspect={onInspect}
          onToggle={(name) => {
            const list = current.background_cantrips;
            if (list.includes(name)) {
              update({
                background_cantrips: list.filter((n) => n !== name),
              });
            } else if (list.length < cantripsNeeded) {
              update({ background_cantrips: [...list, name] });
            }
          }}
        />
      ) : null}
      {spellsNeeded ? (
        <SpellGroup
          title={`Background spells (${current.background_spells.length}/${spellsNeeded})`}
          spells={normalizeSpellList(arr<Loose>(spellReq.available))}
          selected={current.background_spells}
          disabledNames={disabledNames}
          inspectedSpellName={inspectedSpellName}
          onInspect={onInspect}
          onToggle={(name) => {
            const list = current.background_spells;
            if (list.includes(name)) {
              update({
                background_spells: list.filter((n) => n !== name),
              });
            } else if (list.length < spellsNeeded) {
              update({ background_spells: [...list, name] });
            }
          }}
        />
      ) : null}
    </div>
  );
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

// ---------- Weapon Masteries ----------

interface MasteryProperty {
  name: string;
  description: string;
  weapons: string[];
}

export function MasteryPicker({ data }: { data: Loose }) {
  const setChoice = useCharacterStore((s) => s.setChoice);
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const max = num(data.max_masteries) ?? 0;
  const available = arr<string>(data.available_weapons);
  const masteries = rec(data.weapon_masteries);
  const masteryProperties = rec(data.mastery_properties);
  const current =
    (choicesMade["weapon_mastery_selections"] as string[] | undefined) ??
    arr<string>(data.current_masteries);

  const [expandedProp, setExpandedProp] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<"weapons" | "properties">("weapons");

  const propertyList = useMemo<MasteryProperty[]>(
    () =>
      Object.values(masteryProperties)
        .map((v) => {
          const p = rec(v as Loose);
          const name = str(p.name);
          const description = str(p.description);
          if (!name || !description) return null;
          return { name, description, weapons: arr<string>(p.weapons) };
        })
        .filter((p): p is MasteryProperty => p !== null)
        .sort((a, b) => a.name.localeCompare(b.name)),
    [masteryProperties],
  );

  function toggle(name: string) {
    const list = current;
    if (list.includes(name)) {
      setChoice(
        "weapon_mastery_selections",
        list.filter((n) => n !== name),
      );
    } else if (list.length < max) {
      setChoice("weapon_mastery_selections", [...list, name]);
    }
  }

  if (max === 0) return null;
  return (
    <div className="rounded-xl border border-border/70 bg-background/70 p-3.5 shadow-xs sm:p-5">
      <header className="mb-3 flex items-center justify-between">
        <div>
          <h4 className="font-display text-base text-primary font-semibold">Weapon Masteries</h4>
          <p className="text-xs text-muted-foreground">
            Select {max} weapon{max === 1 ? "" : "s"} you have mastered
          </p>
        </div>
        <div className="rounded-full bg-secondary px-2.5 py-1 text-xs font-semibold text-foreground border border-border">
          {current.length}/{max} chosen
        </div>
      </header>

      {/* Mobile Tab Switcher */}
      {propertyList.length > 0 && (
        <div className="flex md:hidden mb-3 rounded-lg bg-muted p-1 text-sm font-medium">
          <button
            type="button"
            onClick={() => setMobileTab("weapons")}
            className={cn(
              "flex-1 rounded-md py-1.5 text-xs font-medium transition-colors text-center",
              mobileTab === "weapons"
                ? "bg-background text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            Weapons ({current.length}/{max})
          </button>
          <button
            type="button"
            onClick={() => setMobileTab("properties")}
            className={cn(
              "flex-1 rounded-md py-1.5 text-xs font-medium transition-colors text-center",
              mobileTab === "properties"
                ? "bg-background text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            Properties Guide ({propertyList.length})
          </button>
        </div>
      )}

      <div className="flex flex-col md:flex-row gap-4">
        {/* Weapon grid */}
        <div className={cn("flex-1 min-w-0", mobileTab === "weapons" ? "block" : "hidden md:block")}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
            {available.map((weapon) => {
              const isSelected = current.includes(weapon);
              const mastery = str(masteries[weapon]);
              return (
                <button
                  key={weapon}
                  type="button"
                  onClick={() => toggle(weapon)}
                  aria-pressed={isSelected}
                  className={cn(
                    "flex items-center justify-between gap-2.5 rounded-lg border px-3 py-2.5 text-left text-sm transition-all duration-200 min-w-0",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                    isSelected
                      ? "border-primary bg-muted/60 shadow-xs ring-1 ring-primary/20"
                      : "border-border bg-background/70 hover:border-primary/30 hover:bg-secondary/60",
                  )}
                >
                  <div className="flex flex-col min-w-0 flex-1 pr-1">
                    <span className="font-semibold text-sm text-foreground truncate">{weapon}</span>
                    {mastery && (
                      <span className="text-[11px] font-medium text-amber-600 dark:text-amber-400 mt-0.5">
                        {mastery}
                      </span>
                    )}
                  </div>
                  <span
                    className={cn(
                      "inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border",
                      isSelected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-muted-foreground/30 bg-background text-transparent",
                    )}
                  >
                    <Check className="h-3 w-3" />
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Mastery properties accordion */}
        {propertyList.length > 0 && (
          <div className={cn("w-full md:w-56 shrink-0", mobileTab === "properties" ? "block" : "hidden md:block")}>
            <p className="hidden md:block mb-1.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
              Mastery Properties
            </p>
            <div className="flex flex-col gap-1.5">
              {propertyList.map((prop) => {
                const isOpen = expandedProp === prop.name;
                return (
                  <div key={prop.name} className="rounded-lg border border-border/60 bg-background/50 overflow-hidden">
                    <button
                      type="button"
                      onClick={() => setExpandedProp(isOpen ? null : prop.name)}
                      className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left hover:bg-muted/30 transition-colors"
                    >
                      <span className="text-xs font-semibold text-foreground">{prop.name}</span>
                      {isOpen ? (
                        <ChevronUp className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      )}
                    </button>
                    {isOpen && (
                      <div className="px-3 pb-2.5 pt-0.5 space-y-1.5 border-t border-border/30 bg-muted/10">
                        <p className="text-xs text-foreground/90 leading-relaxed">{prop.description}</p>
                        {prop.weapons.length > 0 && (
                          <p className="text-[10px] text-muted-foreground pt-1 border-t border-border/20">
                            <span className="font-semibold text-foreground/70">Used by: </span>
                            {prop.weapons.sort().join(", ")}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------- Eldritch Invocations ----------

interface InvocationSelections {
  selected: string[];
  cantrip_choices: Record<string, string[]>;
  choices?: Record<string, Record<string, any>>;
}

interface InvocationCantripChoice {
  id: string;
  invocation: string;
  count: number;
  spell_list: string;
  options: string[];
  selected: string[];
}

function readInvocationSelections(
  value: unknown,
  fallbackSelected: string[],
): InvocationSelections {
  if (Array.isArray(value)) {
    return { selected: value as string[], cantrip_choices: {}, choices: {} };
  }

  if (!value || typeof value !== "object") {
    return { selected: fallbackSelected, cantrip_choices: {}, choices: {} };
  }

  const stored = rec(value);
  const choicesRaw = rec(stored.choices);
  const choices: Record<string, Record<string, any>> = {};
  for (const [invName, invChoices] of Object.entries(choicesRaw)) {
    choices[invName] = rec(invChoices);
  }

  return {
    selected: arr<string>(stored.selected),
    cantrip_choices: Object.entries(rec(stored.cantrip_choices)).reduce<
      Record<string, string[]>
    >((acc, [id, spells]) => {
      acc[id] = arr<string>(spells);
      return acc;
    }, {}),
    choices,
  };
}

export function InvocationPicker({ data }: { data: Loose }) {
  const setChoice = useCharacterStore((s) => s.setChoice);
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const max = num(data.max_invocations) ?? 0;
  const available = arr<Loose>(data.available_invocations);
  const cantripDescriptors = arr<InvocationCantripChoice>(
    data.cantrip_choice_descriptors,
  );
  const invocationChoiceDescriptors = arr<Loose>(
    data.invocation_choice_descriptors,
  );
  const dependencyMap = (data.dependency_map as Record<string, string[]>) || {};
  const [dependencyWarning, setDependencyWarning] = useState<string | null>(null);

  const selections = readInvocationSelections(
    choicesMade["eldritch_invocation_selections"],
    arr<string>(data.current_invocations),
  );
  const current = selections.selected;

  const classes = choicesMade.classes;
  const warlockLevel = useMemo(() => {
    if (Array.isArray(classes)) {
      const match = classes.find(
        (c) => c && typeof c === "object" && (c as unknown as Loose).class_name === "Warlock",
      );
      if (match && typeof (match as unknown as Loose).level === "number") {
        return (match as unknown as Loose).level as number;
      }
    }
    if (choicesMade.class === "Warlock") {
      return typeof choicesMade.level === "number" ? choicesMade.level : 1;
    }
    return 0;
  }, [classes, choicesMade.class, choicesMade.level]);

  function resolvedCantripChoices(
    selectedInvocations: string[] = current,
  ): Record<string, string[]> {
    const resolved = { ...selections.cantrip_choices };
    for (const descriptor of cantripDescriptors) {
      if (!selectedInvocations.includes(descriptor.invocation)) {
        delete resolved[descriptor.id];
      } else if (!(descriptor.id in resolved)) {
        resolved[descriptor.id] = descriptor.selected;
      }
    }
    return resolved;
  }

  function toggle(name: string, isGated = false) {
    if (isGated) return;
    setDependencyWarning(null);
    const isSelected = current.includes(name);
    if (isSelected) {
      const dependents = dependencyMap[name] || [];
      if (dependents.length > 0) {
        setDependencyWarning(
          `Cannot remove "${name}" because the following active invocation(s) depend on it: ${dependents.join(", ")}.`
        );
        return;
      }
    } else {
      if (current.length >= max) return;
    }

    const selected = isSelected
      ? current.filter((invocation) => invocation !== name)
      : [...current, name];
    const cantrip_choices = resolvedCantripChoices(selected);

    const nextChoices = { ...selections.choices };
    if (isSelected) {
      delete nextChoices[name];
    }

    setChoice("eldritch_invocation_selections", {
      selected,
      cantrip_choices,
      choices: nextChoices,
    } satisfies InvocationSelections);
  }

  function toggleCantrip(descriptor: InvocationCantripChoice, spell: string) {
    const cantrip_choices = resolvedCantripChoices();
    const selected = cantrip_choices[descriptor.id] ?? descriptor.selected;
    const isSelected = selected.includes(spell);
    if (!isSelected && selected.length >= descriptor.count) return;

    cantrip_choices[descriptor.id] = isSelected
      ? selected.filter((choice) => choice !== spell)
      : [...selected, spell];

    setChoice("eldritch_invocation_selections", {
      selected: current,
      cantrip_choices,
      choices: selections.choices,
    } satisfies InvocationSelections);
  }

  function setInvocationChoice(invocationName: string, choiceKey: string, value: string) {
    const nextChoices = { ...selections.choices };
    if (!nextChoices[invocationName]) {
      nextChoices[invocationName] = {};
    }
    if (value) {
      nextChoices[invocationName] = {
        ...nextChoices[invocationName],
        [choiceKey]: value,
      };
    } else {
      const copy = { ...nextChoices[invocationName] };
      delete copy[choiceKey];
      nextChoices[invocationName] = copy;
    }

    setChoice("eldritch_invocation_selections", {
      selected: current,
      cantrip_choices: selections.cantrip_choices,
      choices: nextChoices,
    } satisfies InvocationSelections);
  }

  const [expandedInv, setExpandedInv] = useState<string | null>(null);

  if (max === 0) return null;
  return (
    <div className="rounded-xl border border-border/70 bg-background/70 p-4 shadow-sm sm:p-5">
      <header className="mb-3">
        <h4 className="flex items-center gap-2 font-display text-base text-primary font-semibold">
          <Wand2 className="h-4 w-4" />
          Eldritch Invocations
        </h4>
        <p className="text-xs text-muted-foreground">
          {current.length}/{max} chosen
        </p>
      </header>

      {dependencyWarning && (
        <div className="mb-3 flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-2.5 text-xs text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{dependencyWarning}</span>
        </div>
      )}

      <div className="flex flex-col gap-1">
        {available.map((inv, i) => {
          const name = str(inv.name) ?? `Invocation ${i}`;
          const description = str(inv.description);
          const min_level = num(inv.prerequisite_level) ?? 1;
          const isLevelGated = warlockLevel < min_level;
          const isSelected = current.includes(name);
          const isOpen = expandedInv === name;
          const invocationCantripChoices = cantripDescriptors.filter(
            (descriptor) => descriptor.invocation === name,
          );
          const invocationChoices = invocationChoiceDescriptors.filter(
            (descriptor) => descriptor.invocation === name,
          );

          return (
            <div
              key={`${name}-${i}`}
              className={cn(
                "rounded-lg border transition-colors",
                isLevelGated
                  ? "border-border/40 bg-muted/20 opacity-60"
                  : isSelected
                    ? "border-primary bg-muted/60 ring-1 ring-primary/20"
                    : "border-border bg-background/70",
              )}
            >
              {/* Row: select checkbox + name + badge + expand toggle */}
              <div className="flex items-center gap-2 px-3 py-2">
                <button
                  type="button"
                  onClick={() => toggle(name, isLevelGated)}
                  disabled={isLevelGated}
                  title={isLevelGated ? `Requires Warlock level ${min_level}` : undefined}
                  aria-pressed={isSelected}
                  className={cn(
                    "inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
                    isLevelGated && "cursor-not-allowed opacity-40 hover:border-border",
                    isSelected
                      ? "border-primary bg-background text-primary"
                      : "border-border bg-background text-transparent hover:border-primary/50",
                  )}
                  aria-label={
                    isLevelGated
                      ? `${name} (Requires Warlock level ${min_level})`
                      : isSelected
                        ? `Deselect ${name}`
                        : `Select ${name}`
                  }
                >
                  <Check className="h-3 w-3" />
                </button>
                <span className="flex-1 text-sm font-medium text-foreground">{name}</span>
                {min_level > 1 && (
                  <span
                    className={cn(
                      "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide border",
                      isLevelGated
                        ? "border-destructive/30 bg-destructive/10 text-destructive"
                        : "border-primary/30 bg-primary/10 text-primary",
                    )}
                  >
                    Level {min_level}+
                  </span>
                )}
                {description && (
                  <button
                    type="button"
                    onClick={() => setExpandedInv(isOpen ? null : name)}
                    className="shrink-0 text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 rounded"
                    aria-label={isOpen ? "Hide description" : "Show description"}
                  >
                    {isOpen ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </button>
                )}
              </div>
              {/* Accordion body */}
              {isOpen && description && (
                <div className="px-3 pb-3 pt-0">
                  <p className="text-xs text-foreground/90 whitespace-pre-line">{description}</p>
                </div>
              )}

              {/* Sub-choice selectors for invocations (e.g. Origin Feat for Lessons of the First Ones) */}
              {isSelected && invocationChoices.map((descriptor) => {
                const choiceKey = str(descriptor.choice_key) ?? "choice";
                const currentVal = str(selections.choices?.[name]?.[choiceKey]) ?? "";
                const options = arr<string>(descriptor.options);
                const featSubChoices = arr<Loose>(descriptor.feat_sub_choices);

                return (
                  <div
                    key={str(descriptor.id) ?? choiceKey}
                    className="border-t border-border/60 px-3 py-3 space-y-2 bg-muted/15"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <label className="text-xs font-semibold text-foreground">
                        {str(descriptor.title) ?? "Choose Origin Feat"}
                      </label>
                      <span className="text-[10px] text-muted-foreground uppercase font-medium">Origin Feat</span>
                    </div>
                    {str(descriptor.description) && (
                      <p className="text-xs text-muted-foreground">{str(descriptor.description)}</p>
                    )}
                    <select
                      value={currentVal}
                      onChange={(e) => setInvocationChoice(name, choiceKey, e.target.value)}
                      className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                    >
                      <option value="">Select an Origin Feat...</option>
                      {options.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>

                    {featSubChoices.length > 0 && (
                      <div className="mt-3 space-y-3 pt-2 border-t border-border/40">
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                          {currentVal} Options
                        </p>
                        {featSubChoices.map((subChoice) => {
                          const subKey = str(subChoice.choice_key) ?? "";
                          const subTitle = str(subChoice.title) ?? subKey;
                          const subDesc = str(subChoice.description);
                          const subOpts = arr<string | { name?: string }>(subChoice.options);
                          const subCount = num(subChoice.count) ?? 1;
                          return (
                            <ChoiceList
                              key={subKey}
                              choiceKey={subKey}
                              title={subTitle}
                              description={subDesc}
                              options={subOpts}
                              count={subCount}
                            />
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Cantrip pickers for invocations */}
              {isSelected && invocationCantripChoices.map((descriptor) => {
                const selectedCantrips =
                  selections.cantrip_choices[descriptor.id] ?? descriptor.selected;
                return (
                  <div
                    key={descriptor.id}
                    className="border-t border-border/60 px-3 py-3"
                  >
                    <div className="mb-2 flex items-baseline justify-between gap-2">
                      <h5 className="text-xs font-semibold text-foreground">
                        {descriptor.spell_list}
                      </h5>
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {selectedCantrips.length}/{descriptor.count} chosen
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {descriptor.options.map((spell) => {
                        const isCantripSelected = selectedCantrips.includes(spell);
                        return (
                          <button
                            key={spell}
                            type="button"
                            onClick={() => toggleCantrip(descriptor, spell)}
                            aria-pressed={isCantripSelected}
                            className={cn(
                              "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors",
                              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
                              isCantripSelected
                                ? "border-primary bg-primary text-primary-foreground"
                                : "border-border bg-background text-foreground hover:border-primary/50",
                            )}
                          >
                            <Check
                              className={cn(
                                "h-3 w-3",
                                isCantripSelected ? "opacity-100" : "opacity-0",
                              )}
                            />
                            {spell}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function ReplicateMagicItemPicker({
  data,
  onlyActive = false,
}: {
  data: Loose;
  onlyActive?: boolean;
}) {
  const setChoice = useCharacterStore((s) => s.setChoice);
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const maxPlans = num(data.max_plans) ?? 0;
  const maxActive = num(data.max_active) ?? 0;
  const available = arr<Loose>(data.available_plans);

  const currentKnown: string[] = Array.isArray(choicesMade.artificer_replicate_plans)
    ? (choicesMade.artificer_replicate_plans as string[])
    : arr<string>(data.known_plans);

  const currentActive: string[] = Array.isArray(choicesMade.artificer_active_replications)
    ? (choicesMade.artificer_active_replications as string[])
    : arr<string>(data.active_items);

  const [activeTab, setActiveTab] = useState<"active" | "plans">(onlyActive ? "active" : "plans");
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState<number | "all">("all");
  const [expandedPlan, setExpandedPlan] = useState<string | null>(null);

  if (maxPlans === 0) return null;

  function toggleKnownPlan(name: string) {
    const isSelected = currentKnown.includes(name);
    if (!isSelected && currentKnown.length >= maxPlans) return;

    const nextKnown = isSelected
      ? currentKnown.filter((p) => p !== name)
      : [...currentKnown, name];

    // If removing a plan that is active, deactivate it
    const nextActive = currentActive.filter((p) => nextKnown.includes(p));

    setChoice("artificer_replicate_plans", nextKnown);
    if (nextActive.length !== currentActive.length) {
      setChoice("artificer_active_replications", nextActive);
    }
  }

  function toggleActiveItem(name: string) {
    const isActive = currentActive.includes(name);
    if (!isActive && currentActive.length >= maxActive) return;

    const nextActive = isActive
      ? currentActive.filter((p) => p !== name)
      : [...currentActive, name];

    setChoice("artificer_active_replications", nextActive);
  }

  // Filter available plans for the Plans tab
  const filteredPlans = available.filter((p) => {
    const name = str(p.name) ?? "";
    const type = str(p.type) ?? "";
    const matchesSearch =
      search === "" ||
      name.toLowerCase().includes(search.toLowerCase()) ||
      type.toLowerCase().includes(search.toLowerCase());
    const matchesTier = tierFilter === "all" || num(p.level) === tierFilter;
    return matchesSearch && matchesTier;
  });

  return (
    <div className="rounded-xl border border-border/70 bg-background/70 p-4 shadow-sm sm:p-5">
      <header className="mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h4 className="flex items-center gap-2 font-display text-base text-primary font-semibold">
            <Package className="h-4 w-4" />
            Replicate Magic Item
          </h4>
          <p className="text-xs text-muted-foreground">
            {currentKnown.length}/{maxPlans} Plans Known • {currentActive.length}/{maxActive} Infusions Active
          </p>
        </div>

        {/* Tab switcher */}
        <div className="inline-flex rounded-lg border border-border/80 bg-muted/40 p-0.5 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("plans")}
            className={cn(
              "px-3 py-1 rounded-md font-medium transition-colors",
              activeTab === "plans"
                ? "bg-background text-primary shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            Known Plans ({currentKnown.length}/{maxPlans})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("active")}
            className={cn(
              "px-3 py-1 rounded-md font-medium transition-colors",
              activeTab === "active"
                ? "bg-background text-primary shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            Active Loadout ({currentActive.length}/{maxActive})
          </button>
        </div>
      </header>

      {activeTab === "active" ? (
        <div className="space-y-3">
          <div className="rounded-lg bg-muted/30 border border-border/60 p-3 text-xs text-muted-foreground flex items-center justify-between">
            <span>
              Choose up to <strong>{maxActive}</strong> active items to infuse from your known plans on each Long Rest.
            </span>
            <span className="font-semibold text-primary">
              {currentActive.length} / {maxActive}
            </span>
          </div>

          {currentKnown.length === 0 ? (
            <div className="p-6 text-center text-xs text-muted-foreground border border-dashed rounded-lg">
              No known plans selected yet. Switch to the <strong>Known Plans</strong> tab to select up to {maxPlans} plans.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {currentKnown.map((name) => {
                const plan = available.find((p) => str(p.name) === name) || {};
                const isActive = currentActive.includes(name);
                const rarity = str(plan.rarity);
                const attunement = Boolean(plan.attunement);
                const desc = str(plan.description);
                const itemType = str(plan.type);
                const isExpanded = expandedPlan === name;

                return (
                  <div
                    key={name}
                    className={cn(
                      "rounded-lg border p-3 transition-colors flex flex-col justify-between gap-2",
                      isActive
                        ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                        : "border-border bg-background/50"
                    )}
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-sm font-medium text-foreground">{name}</span>
                        <div className="flex items-center gap-1 shrink-0">
                          {rarity && (
                            <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-secondary/80 text-muted-foreground">
                              {rarity}
                            </span>
                          )}
                          {attunement && (
                            <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 border border-amber-500/20">
                              Attune
                            </span>
                          )}
                        </div>
                      </div>
                      {itemType && (
                        <p className="text-[11px] text-muted-foreground mt-0.5">{itemType}</p>
                      )}
                      {desc && isExpanded && (
                        <p className="mt-2 text-xs text-foreground/90 whitespace-pre-line leading-relaxed border-t pt-2 border-border/50">
                          {desc}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center justify-between gap-2 pt-1 border-t border-border/40 mt-1">
                      {desc ? (
                        <button
                          type="button"
                          onClick={() => setExpandedPlan(isExpanded ? null : name)}
                          className="text-[11px] text-muted-foreground hover:text-primary inline-flex items-center gap-0.5"
                        >
                          {isExpanded ? "Hide Details" : "Details"}
                          {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                        </button>
                      ) : <span />}

                      <button
                        type="button"
                        onClick={() => toggleActiveItem(name)}
                        disabled={!isActive && currentActive.length >= maxActive}
                        className={cn(
                          "px-2.5 py-1 text-xs rounded font-medium transition-colors inline-flex items-center gap-1",
                          isActive
                            ? "bg-primary text-primary-foreground hover:bg-primary/90"
                            : currentActive.length >= maxActive
                              ? "bg-muted text-muted-foreground cursor-not-allowed opacity-50"
                              : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                        )}
                      >
                        {isActive ? (
                          <>
                            <Check className="h-3 w-3" />
                            Infused
                          </>
                        ) : (
                          "Infuse Item"
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {/* Controls: Search and Tier Filter */}
          <div className="flex flex-col sm:flex-row gap-2 items-center justify-between">
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search magic items..."
                className="w-full rounded-md border border-input bg-background/80 pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="flex items-center gap-1 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
              {(["all", 2, 6, 10, 14] as const).map((lvl) => (
                <button
                  key={String(lvl)}
                  type="button"
                  onClick={() => setTierFilter(lvl)}
                  className={cn(
                    "px-2.5 py-1 rounded text-xs font-medium shrink-0 transition-colors",
                    tierFilter === lvl
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted/60 text-muted-foreground hover:text-foreground"
                  )}
                >
                  {lvl === "all" ? "All Tiers" : `Lvl ${lvl}+`}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1 max-h-[480px] overflow-y-auto pr-1">
            {filteredPlans.map((plan, i) => {
              const name = str(plan.name) ?? `Plan ${i}`;
              const desc = str(plan.description);
              const lvl = num(plan.level) ?? 2;
              const rarity = str(plan.rarity);
              const attunement = Boolean(plan.attunement);
              const itemType = str(plan.type);
              const isSelected = currentKnown.includes(name);
              const isExpanded = expandedPlan === name;

              return (
                <div
                  key={`${name}-${i}`}
                  className={cn(
                    "rounded-lg border transition-colors",
                    isSelected
                      ? "border-primary bg-muted/60 ring-1 ring-primary/20"
                      : "border-border bg-background/70 hover:bg-muted/30"
                  )}
                >
                  <div className="flex items-center gap-2 px-3 py-2">
                    <button
                      type="button"
                      onClick={() => toggleKnownPlan(name)}
                      disabled={!isSelected && currentKnown.length >= maxPlans}
                      aria-pressed={isSelected}
                      className={cn(
                        "inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors",
                        !isSelected && currentKnown.length >= maxPlans && "cursor-not-allowed opacity-40",
                        isSelected
                          ? "border-primary bg-background text-primary"
                          : "border-border bg-background text-transparent hover:border-primary/50"
                      )}
                    >
                      <Check className="h-3 w-3" />
                    </button>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-foreground">{name}</span>
                        {itemType && (
                          <span className="text-xs text-muted-foreground">({itemType})</span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="text-[10px] rounded px-1.5 py-0.5 bg-secondary/70 text-muted-foreground font-mono">
                        Lv {lvl}+
                      </span>
                      {rarity && (
                        <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-secondary/80 text-muted-foreground">
                          {rarity}
                        </span>
                      )}
                      {attunement && (
                        <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 border border-amber-500/20">
                          Attune
                        </span>
                      )}
                      {desc && (
                        <button
                          type="button"
                          onClick={() => setExpandedPlan(isExpanded ? null : name)}
                          className="p-1 rounded text-muted-foreground hover:text-foreground"
                          title="Toggle description"
                        >
                          {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                        </button>
                      )}
                    </div>
                  </div>

                  {desc && isExpanded && (
                    <div className="px-3 pb-3 pt-1 border-t border-border/40 text-xs text-foreground/90 whitespace-pre-line leading-relaxed bg-background/40">
                      {desc}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
