import { useQueries } from "@tanstack/react-query";
import { Check, Info } from "lucide-react";
import { api, type SpellDefinition } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useCharacterStore } from "@/store/characterStore";
import { ChoiceList } from "./ChoiceList";

/**
 * Renders the `{feat_name, feat_description, feat_benefits, choices: [...]}`
 * shape returned by `builder.get_feat_choices()` /
 * `builder.get_species_feat_choices()` (surfaced via /character/preview-step).
 */
interface FeatChoice {
  title?: string;
  description?: string;
  /** Structured type from the backend: "skills" | "tools" | "languages" | etc. */
  type?: string;
  options?: Array<unknown>;
  count?: number;
  choices_made_key?: string;
  feature_name?: string;
  choice_category?: string;
}

interface FeatChoicesData {
  feat_name?: string | null;
  feat_description?: string;
  feat_benefits?: string[];
  choices?: FeatChoice[];
}

interface Props {
  data: FeatChoicesData | undefined;
  heading: string;
  /**
   * Skill and tool proficiencies already granted by other sources (class,
   * background direct grants, etc.). For skill/tool-type choices these are
   * shown grayed out and disabled so the player can see duplicates at a glance.
   */
  grantedProficiencies?: string[];
  onInspectSpell?: (spell: SpellDefinition) => void;
  inspectedSpellName?: string;
}

/** Returns true for choice types that deal in skill or tool proficiencies. */
function isProficiencyChoice(choice: FeatChoice): boolean {
  const key = (choice.choices_made_key ?? "").toLowerCase();
  const title = (choice.title ?? "").toLowerCase();
  const featName = (choice.feature_name ?? "").toLowerCase();
  const t = (choice.type ?? "").toLowerCase();
  const cat = (choice.choice_category ?? "").toLowerCase();
  if (
    key.includes("expertise") ||
    title.includes("expertise") ||
    featName.includes("expertise") ||
    cat === "expertise" ||
    t === "expertise"
  ) {
    return false;
  }
  if (t === "skills" || t === "tools") return true;
  // Fallback: keyword scan on title/feature_name for choices that lack a type.
  const keywords = `${choice.title ?? ""} ${choice.feature_name ?? ""}`.toLowerCase();
  return keywords.includes("skill") || keywords.includes("tool");
}

function isSpellChoice(choice: FeatChoice): boolean {
  return choice.choice_category === "spells";
}

function normalizeSpellOptions(options: Array<unknown>): string[] {
  return options
    .filter((option): option is string => typeof option === "string")
    .filter((option) => option.length > 0);
}

function spellHasConcentration(spell: SpellDefinition): boolean {
  const duration = (spell.duration ?? "").toLowerCase();
  return duration.includes("concentration");
}

export function SpellChoiceList({
  choiceKey,
  title,
  description,
  options,
  count = 1,
  onInspectSpell,
  inspectedSpellName,
}: {
  choiceKey: string;
  title: string;
  description?: string;
  options: string[];
  count?: number;
  onInspectSpell?: (spell: SpellDefinition) => void;
  inspectedSpellName?: string;
}) {
  const value = useCharacterStore((s) => s.choicesMade[choiceKey]);
  const setChoice = useCharacterStore((s) => s.setChoice);
  const isMulti = count > 1;

  const selected = new Set<string>(
    isMulti
      ? Array.isArray(value)
        ? (value as string[])
        : []
      : typeof value === "string" && value
        ? [value]
        : [],
  );

  const spellDefinitionQueries = useQueries({
    queries: options.map((name) => ({
      queryKey: ["catalog", "spell-definition", name],
      queryFn: () => api.catalog.getSpellDefinition(name),
    })),
  });

  const spellByName = new Map(
    options.map((name, index) => [name, spellDefinitionQueries[index]?.data]),
  );
  const selectedName = !isMulti && typeof value === "string" ? value : "";
  const selectedSpell = selectedName ? spellByName.get(selectedName) : undefined;

  function toggle(name: string) {
    if (!isMulti) {
      setChoice(choiceKey, name);
      return;
    }

    const next = new Set(selected);
    if (next.has(name)) {
      next.delete(name);
    } else {
      if (next.size >= count) return;
      next.add(name);
    }
    setChoice(choiceKey, Array.from(next));
  }

  return (
    <fieldset className="rounded-xl border border-border/70 bg-card/70 p-4 shadow-sm sm:p-5">
      <legend className="px-0 text-base font-semibold text-foreground">{title}</legend>
      {description && (
        <p className="mt-1 mb-4 max-w-3xl text-sm text-muted-foreground">
          {description}
        </p>
      )}
      {isMulti ? (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {options.map((name) => {
            const isSelected = selected.has(name);
            const spell = spellByName.get(name);
            const isInspected = inspectedSpellName === name;
            const atLimit = !isSelected && selected.size >= count;

            return (
              <div
                key={name}
                className={cn(
                  "flex items-stretch gap-1 rounded-lg border text-left text-sm transition-all duration-200",
                  isSelected
                    ? "border-primary bg-muted/60 shadow-sm ring-1 ring-primary/20"
                    : isInspected
                      ? "border-muted-foreground/40 bg-secondary/60 ring-1 ring-muted-foreground/20"
                      : "border-border bg-background/70 hover:border-primary/30 hover:bg-secondary/60",
                  atLimit && "cursor-not-allowed opacity-50",
                )}
              >
                <button
                  type="button"
                  onClick={() => {
                    if (!atLimit) toggle(name);
                  }}
                  disabled={atLimit}
                  aria-pressed={isSelected}
                  className={cn(
                    "flex flex-1 items-center justify-between gap-3 rounded-l-lg px-3 py-2 text-left",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  )}
                >
                  <span className="min-w-0">
                    <span className="flex flex-wrap items-center gap-3">
                      <span>{name}</span>
                      {spell && spellHasConcentration(spell) && (
                        <span className="shrink-0 rounded bg-amber-600/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                          C
                        </span>
                      )}
                    </span>
                    {spell?.school && (
                      <span className="mt-1 text-xs text-muted-foreground">
                        {spell.school}
                      </span>
                    )}
                  </span>
                  <span
                    className={cn(
                      "inline-flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border",
                      isSelected
                        ? "border-primary bg-background text-primary"
                        : "border-border bg-background text-transparent",
                    )}
                  >
                    <Check className="h-3 w-3" />
                  </span>
                </button>
                {onInspectSpell && spell && (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onInspectSpell(spell);
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
      ) : (
        <div className="space-y-3">
          <select
            value={selectedName}
            onChange={(event) => setChoice(choiceKey, event.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label={title}
          >
            <option value="">Select a spell</option>
            {options.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          {selectedSpell && (
            <div className="rounded-lg border border-border/70 bg-background/50 p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-foreground">{selectedSpell.name}</span>
                <span className="rounded-full border border-border/70 bg-background px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted-foreground">
                  {selectedSpell.level === 0 ? "Cantrip" : `Level ${selectedSpell.level ?? "-"}`}
                </span>
                {selectedSpell.school && (
                  <span className="rounded-full border border-border/70 bg-background px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted-foreground">
                    {selectedSpell.school}
                  </span>
                )}
                {spellHasConcentration(selectedSpell) && (
                  <span className="rounded bg-amber-600/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                    C
                  </span>
                )}
              </div>
              {selectedSpell.description && (
                <p className="mt-2 text-xs text-muted-foreground">{selectedSpell.description}</p>
              )}
              <dl className="mt-3 grid grid-cols-1 gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                {selectedSpell.casting_time && (
                  <div>
                    <dt className="font-medium text-foreground">Casting Time</dt>
                    <dd>{selectedSpell.casting_time}</dd>
                  </div>
                )}
                {selectedSpell.range && (
                  <div>
                    <dt className="font-medium text-foreground">Range</dt>
                    <dd>{selectedSpell.range}</dd>
                  </div>
                )}
                {selectedSpell.duration && (
                  <div>
                    <dt className="font-medium text-foreground">Duration</dt>
                    <dd>{selectedSpell.duration}</dd>
                  </div>
                )}
                {selectedSpell.components && (
                  <div>
                    <dt className="font-medium text-foreground">Components</dt>
                    <dd>{Array.isArray(selectedSpell.components) ? selectedSpell.components.join(", ") : selectedSpell.components}</dd>
                  </div>
                )}
              </dl>
            </div>
          )}
        </div>
      )}
    </fieldset>
  );
}

export function FeatChoicesPicker({
  data,
  heading,
  grantedProficiencies,
  onInspectSpell,
  inspectedSpellName,
}: Props) {
  if (!data || !data.feat_name) return null;
  const choices = data.choices ?? [];

  return (
    <section className="rounded-md border border-border bg-card/40 p-4 space-y-3">
      <header>
        <h3 className="text-lg font-semibold">
          {heading}: <span className="text-primary">{data.feat_name}</span>
        </h3>
        {data.feat_description && (
          <p className="mt-1 text-sm text-muted-foreground">
            {data.feat_description}
          </p>
        )}
        {data.feat_benefits && data.feat_benefits.length > 0 && (
          <div className="mt-2 space-y-2 text-sm text-muted-foreground">
            <ul className="space-y-1.5 list-disc pl-5">
              {(() => {
                type BenefitGroup =
                  | { type: "text"; text: string }
                  | { type: "table"; rows: Array<{ level: string; spells: string }> };

                const groups: BenefitGroup[] = [];
                let currentTable: Array<{ level: string; spells: string }> | null = null;

                for (const b of data.feat_benefits) {
                  const tableMatch = b.match(/^(?:•\s*)?Level\s+(\d+):\s*(.+)$/i);
                  if (tableMatch) {
                    if (!currentTable) {
                      currentTable = [];
                      groups.push({ type: "table", rows: currentTable });
                    }
                    currentTable.push({ level: tableMatch[1], spells: tableMatch[2] });
                  } else {
                    currentTable = null;
                    groups.push({ type: "text", text: b });
                  }
                }

                return groups.map((group, i) => {
                  if (group.type === "table") {
                    return (
                      <li key={i} className="list-none -ml-5 my-2">
                        <div className="max-w-md overflow-hidden rounded-md border border-border/70 bg-muted/20 text-xs">
                          <table className="w-full border-collapse">
                            <thead className="bg-muted/60 text-muted-foreground border-b border-border/60">
                              <tr>
                                <th className="px-3 py-1.5 text-left font-medium w-24">Spell Level</th>
                                <th className="px-3 py-1.5 text-left font-medium">Spells</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border/30">
                              {group.rows.map((row) => (
                                <tr key={row.level} className="hover:bg-muted/30">
                                  <td className="px-3 py-1.5 font-semibold text-foreground">Level {row.level}</td>
                                  <td className="px-3 py-1.5 text-muted-foreground">{row.spells}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </li>
                    );
                  }

                  const match = group.text.match(/^([^.]+?\.)\s+(.+)$/);
                  return (
                    <li key={i} className="leading-relaxed">
                      {match ? (
                        <>
                          <strong className="text-foreground font-semibold">{match[1]}</strong>{" "}
                          {match[2]}
                        </>
                      ) : (
                        group.text
                      )}
                    </li>
                  );
                });
              })()}
            </ul>
          </div>
        )}
      </header>

      {choices.map((choice) => {
        if (!choice.choices_made_key) {
          if (import.meta.env.DEV) {
            console.warn('[FeatChoicesPicker] missing choices_made_key for choice', choice);
          }
          return null;
        }
        const key = choice.choices_made_key;
        const opts = (choice.options ?? []) as Array<unknown>;
        if (opts.length === 0) return null;

        const spellOptions = normalizeSpellOptions(opts);
        if (isSpellChoice(choice) && spellOptions.length === opts.length) {
          return (
            <SpellChoiceList
              key={key}
              choiceKey={key}
              title={choice.title ?? key}
              description={choice.description}
              options={spellOptions}
              count={choice.count ?? 1}
              onInspectSpell={onInspectSpell}
              inspectedSpellName={inspectedSpellName}
            />
          );
        }

        const disabledOptions =
          grantedProficiencies && isProficiencyChoice(choice)
            ? grantedProficiencies
            : undefined;
        return (
          <ChoiceList
            key={key}
            choiceKey={key}
            title={choice.title ?? key}
            description={choice.description}
            options={opts as Array<string | { name?: string }>}
            count={choice.count ?? 1}
            disabledOptions={disabledOptions}
            disabledReason="Already granted"
          />
        );
      })}
    </section>
  );
}
