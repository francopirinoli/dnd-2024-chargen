import { AlertTriangle, Check, CircleDashed, ListChecks } from "lucide-react";
import { cn } from "@/lib/utils";
import { type FeatDefinition, type SpellDefinition } from "@/lib/api";
import { useCharacterStore } from "@/store/characterStore";
import { ChoiceList } from "./ChoiceList";
import { SpellChoiceList } from "./FeatChoicesPicker";

const ASI_PLUS_TWO_OPTION = "+2 to one ability";
const ASI_PLUS_ONE_TWO_OPTION = "+1 to two abilities";
const ASI_ABILITIES = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"];

interface AsiChoiceGroup {
  asiOptionChoice?: { choice_key?: string; description?: string };
  plusTwoChoice?: { choice_key?: string };
  plusOneChoice?: { choice_key?: string };
}

interface FeatSubChoiceItem {
  choice_key?: string;
  name?: string;
  feature_name?: string;
  title?: string;
  description?: string;
  options?: Array<unknown>;
  option_descriptions?: Record<string, string>;
  count?: number;
  choice_category?: string;
}

interface FeatDropdownPickerProps {
  choiceKey: string;
  slotLevel: number;
  title: string;
  description?: string;
  generalFeats: Record<string, FeatDefinition>;
  originFeats: Record<string, FeatDefinition>;
  featSubChoices: Array<FeatSubChoiceItem>;
  choicesMade: Record<string, unknown>;
  prerequisiteWarning?: string[];
  grantedProficiencies?: string[];
  asiChoiceGroup?: AsiChoiceGroup;
  onInspectSpell?: (spell: SpellDefinition) => void;
  inspectedSpellName?: string;
}

interface AbilitySelectListProps {
  choiceKey: string;
  title: string;
  description?: string;
  options: string[];
  count?: number;
}

function isProficiencySubChoice(subChoice: FeatSubChoiceItem): boolean {
  const key = (subChoice.choice_key ?? "").toLowerCase();
  const title = (subChoice.title ?? "").toLowerCase();
  const featName = (subChoice.feature_name ?? "").toLowerCase();
  const cat = (subChoice.choice_category ?? "").toLowerCase();
  if (
    key.includes("expertise") ||
    title.includes("expertise") ||
    featName.includes("expertise") ||
    cat === "expertise"
  ) {
    return false;
  }
  if (cat === "skills" || cat === "tools") return true;
  const keywords = `${subChoice.title ?? ""} ${subChoice.feature_name ?? ""}`.toLowerCase();
  return keywords.includes("skill") || keywords.includes("tool");
}

function normalizeAbilityOptions(options: Array<unknown>): string[] {
  return options
    .map((option) => {
      if (typeof option === "string") return option;
      if (option && typeof option === "object") {
        const record = option as { name?: string; label?: string; id?: string };
        return record.name ?? record.label ?? record.id ?? "";
      }
      return "";
    })
    .filter((option): option is string => ASI_ABILITIES.includes(option));
}

function isAbilityScoreSubChoice(subChoice: FeatSubChoiceItem): boolean {
  const normalizedOptions = normalizeAbilityOptions(subChoice.options ?? []);
  if (!normalizedOptions.length) return false;
  return normalizedOptions.length === (subChoice.options ?? []).length;
}

export function getFeatRequiredLevel(feat: FeatDefinition): number {
  if (feat.category?.toLowerCase() === "epic boon") {
    return 19;
  }
  const prereq = feat.prerequisite;
  if (!prereq) return 1;
  const match = prereq.match(/(?:(\d+)(?:st|nd|rd|th)\s+level|level\s+(\d+)\+?)/i);
  if (match) {
    return parseInt(match[1] || match[2], 10);
  }
  return 1;
}

export function isEpicBoonFeat(feat: FeatDefinition): boolean {
  return feat.category?.toLowerCase() === "epic boon" || getFeatRequiredLevel(feat) >= 19;
}

function AbilitySelectList({
  choiceKey,
  title,
  description,
  options,
  count = 1,
}: AbilitySelectListProps) {
  const value = useCharacterStore((s) => s.choicesMade[choiceKey]);
  const setChoice = useCharacterStore((s) => s.setChoice);

  const selections = count > 1
    ? Array.isArray(value)
      ? (value as string[]).filter((entry): entry is string => typeof entry === "string")
      : []
    : typeof value === "string" && value
      ? [value]
      : [];
  const selectedCount = selections.filter(Boolean).length;
  const remainingCount = Math.max(count - selectedCount, 0);
  const displayTitle = title === "" ? null : title;
  const counter = count > 1 ? (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold sm:ml-auto",
        selectedCount === count
          ? "border-primary/40 bg-muted/60 text-primary"
          : selectedCount > 0
            ? "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300"
            : "border-border bg-muted/40 text-muted-foreground",
      )}
    >
      <ListChecks className="h-3.5 w-3.5" />
      <span>
        {selectedCount} of {count} selected
      </span>
      <span className="text-current/80">
        {remainingCount === 0 ? "Complete" : `${remainingCount} remaining`}
      </span>
    </div>
  ) : (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium sm:ml-auto",
        selectedCount === 1
          ? "border-primary/40 bg-muted/60 text-primary"
          : "border-border bg-muted/40 text-muted-foreground",
      )}
    >
      {selectedCount === 1 ? (
        <Check className="h-3.5 w-3.5" />
      ) : (
        <CircleDashed className="h-3.5 w-3.5" />
      )}
      {selectedCount === 1 ? "Complete" : "Choose 1 option"}
    </div>
  );

  function updateSelection(index: number, nextValue: string) {
    if (count === 1) {
      setChoice(choiceKey, nextValue);
      return;
    }

    const nextSelections = Array.from({ length: count }, (_, currentIndex) => selections[currentIndex] ?? "");
    nextSelections[index] = nextValue;

    const compact = nextSelections.filter((entry) => entry.length > 0);
    setChoice(choiceKey, compact);
  }

  return (
    <fieldset className="rounded-xl border border-border/70 bg-card/70 p-4 shadow-sm sm:p-5">
      {displayTitle && (
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <legend className="px-0 text-base font-semibold text-foreground">{displayTitle}</legend>
          {counter}
        </div>
      )}
      {description ? (
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <p className="max-w-3xl text-sm text-muted-foreground">{description}</p>
          {!displayTitle && counter}
        </div>
      ) : !displayTitle ? (
        <div className="mb-4 flex justify-start sm:justify-end">
          {counter}
        </div>
      ) : null}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {Array.from({ length: count }, (_, index) => {
          const selectedValue = selections[index] ?? "";
          const otherSelections = new Set(
            selections.filter((entry, entryIndex) => entryIndex !== index && entry.length > 0),
          );
          return (
            <label key={`${choiceKey}-${index}`} className="space-y-1.5 text-sm text-foreground">
              <span className="block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {count > 1 ? `Ability ${index + 1}` : "Ability"}
              </span>
              <select
                value={selectedValue}
                onChange={(event) => updateSelection(index, event.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                aria-label={count > 1 ? `${title} ${index + 1}` : title}
              >
                <option value="">Select an ability</option>
                {options.map((option) => (
                  <option
                    key={option}
                    value={option}
                    disabled={otherSelections.has(option)}
                  >
                    {option}
                  </option>
                ))}
              </select>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export function FeatDropdownPicker({
  choiceKey,
  slotLevel,
  title,
  description,
  generalFeats,
  originFeats,
  featSubChoices,
  prerequisiteWarning,
  grantedProficiencies,
  asiChoiceGroup,
  onInspectSpell,
  inspectedSpellName,
}: FeatDropdownPickerProps) {
  const currentSelection = useCharacterStore((s) => s.choicesMade[choiceKey]);
  const selectedFeat = typeof currentSelection === "string" ? currentSelection : "";
  const setChoice = useCharacterStore((s) => s.setChoice);
  const clearChoice = useCharacterStore((s) => s.clearChoice);
  const allChoicesMade = useCharacterStore((s) => s.choicesMade);

  // ASI state — keys are always derived from choiceKey; reads are unconditional
  const asiOptionKey = `${choiceKey}_asi_option`;
  const plusTwoKey = `${choiceKey}_ability_plus_2`;
  const plusOneKey = `${choiceKey}_abilities_plus_1`;
  const selectedAsiOption =
    typeof allChoicesMade[asiOptionKey] === "string" ? (allChoicesMade[asiOptionKey] as string) : "";

  function setAsiOption(option: string) {
    setChoice(asiOptionKey, option);
    if (option === ASI_PLUS_TWO_OPTION) {
      clearChoice(plusOneKey);
    } else if (option === ASI_PLUS_ONE_TWO_OPTION) {
      clearChoice(plusTwoKey);
    }
  }

  function handleChange(newFeat: string) {
    const slotPrefix = `${choiceKey}_`;
    const staleFeatPrefix = selectedFeat ? `feat_${selectedFeat}_` : null;

    useCharacterStore.setState((state) => {
      const nextChoices = Object.fromEntries(
        Object.entries(state.choicesMade).filter(([key]) => {
          if (key === choiceKey) return false;
          if (key.startsWith(slotPrefix)) return false;
          if (staleFeatPrefix && key.startsWith(staleFeatPrefix)) return false;
          return true;
        }),
      );

      return {
        choicesMade: {
          ...nextChoices,
          [choiceKey]: newFeat,
        },
      };
    });
  }

  const classes = useCharacterStore((s) => s.choicesMade.classes);
  const rawLevel = useCharacterStore((s) => s.choicesMade.level);
  const fallbackLevel = typeof rawLevel === "number" ? rawLevel : 1;
  const totalCharacterLevel = Array.isArray(classes) && classes.length > 0
    ? classes.reduce(
        (acc, c) =>
          acc +
          (c && typeof c === "object" && typeof (c as unknown as Record<string, unknown>).level === "number"
            ? ((c as unknown as Record<string, unknown>).level as number)
            : 1),
        0,
      )
    : fallbackLevel;
  const effectiveLevel = Math.max(slotLevel, totalCharacterLevel || 1);

  const eligibleGeneralFeats = Object.entries(generalFeats)
    .filter(([_, feat]) => !isEpicBoonFeat(feat) && getFeatRequiredLevel(feat) <= effectiveLevel)
    .map(([name]) => name)
    .sort();

  const eligibleEpicBoons = effectiveLevel >= 19
    ? Object.entries(generalFeats)
        .filter(([_, feat]) => isEpicBoonFeat(feat) && getFeatRequiredLevel(feat) <= effectiveLevel)
        .map(([name]) => name)
        .sort()
    : [];

  const sortedOriginFeats = Object.keys(originFeats).sort();

  const selectedFeatDef = selectedFeat
    ? (generalFeats[selectedFeat] ?? originFeats[selectedFeat])
    : undefined;

  const selectedFeatRequiredLevel = selectedFeatDef ? getFeatRequiredLevel(selectedFeatDef) : 1;
  const isSelectedFeatIneligible = selectedFeatDef ? selectedFeatRequiredLevel > effectiveLevel : false;

  return (
    <fieldset className="overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card to-secondary/30 shadow-sm">
      <div className="border-b border-border/70 px-5 py-4 sm:px-6">
        <legend className="font-semibold text-lg text-foreground">{title}</legend>
        {description && (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        )}
        <div className="mt-3">
          <select
            value={selectedFeat}
            onChange={(e) => handleChange(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label={`Choose feat for level ${slotLevel}`}
          >
            <option value="">— Choose a feat —</option>
            {selectedFeat && isSelectedFeatIneligible && (
              <option value={selectedFeat} disabled>
                {selectedFeat} (Ineligible: Level {selectedFeatRequiredLevel}+ required)
              </option>
            )}
            {eligibleGeneralFeats.length > 0 && (
              <optgroup label="General Feats">
                {eligibleGeneralFeats.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </optgroup>
            )}
            {eligibleEpicBoons.length > 0 && (
              <optgroup label="Epic Boons">
                {eligibleEpicBoons.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </optgroup>
            )}
            {sortedOriginFeats.length > 0 && (
              <optgroup label="Origin Feats">
                {sortedOriginFeats.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </optgroup>
            )}
          </select>
        </div>
        {isSelectedFeatIneligible && (
          <div className="mt-3 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-xs text-destructive flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Level Requirement Not Met</p>
              <p className="mt-0.5">
                <strong>{selectedFeat}</strong> requires Level {selectedFeatRequiredLevel}+, but the current effective level is {effectiveLevel}. Please select a different feat.
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="space-y-4 px-5 py-5 sm:px-6">
        {!selectedFeat ? (
          <p className="text-sm text-muted-foreground">Select a feat to see its details.</p>
        ) : (
          <>
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-base font-semibold text-foreground">{selectedFeat}</h4>
              {selectedFeatDef?.source && (
                <span className="inline-flex rounded-full border border-primary/40 bg-primary/10 px-2.5 py-0.5 text-[11px] font-medium text-primary">
                  {selectedFeatDef.source}
                </span>
              )}
            </div>

            {selectedFeatDef?.prerequisite && (
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase tracking-wide text-muted-foreground">Prerequisite</span>
                <span className="inline-flex rounded-full border border-border/70 bg-background/70 px-2.5 py-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                  {selectedFeatDef.prerequisite}
                </span>
              </div>
            )}

            {prerequisiteWarning && prerequisiteWarning.length > 0 && (
              <div className="rounded-lg border border-amber-400/40 bg-amber-500/10 px-4 py-3">
                <div className="flex items-start gap-2 text-amber-800 dark:text-amber-300">
                  <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <div className="text-sm">
                    <p className="font-semibold">Prerequisite warning</p>
                    <ul className="mt-1 list-disc space-y-1 pl-4">
                      {prerequisiteWarning.map((msg) => (
                        <li key={msg}>{msg}</li>
                      ))}
                    </ul>
                    <p className="mt-2 text-xs">
                      You can still proceed, but verify your final scores before play.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {selectedFeatDef?.description && (
              <p className="mt-2 text-sm text-muted-foreground whitespace-pre-line">
                {selectedFeatDef.description}
              </p>
            )}

            {Array.isArray(selectedFeatDef?.benefits) && selectedFeatDef.benefits.length > 0 && (
              <div className="mt-2 space-y-2 text-sm text-muted-foreground">
                <ul className="space-y-1.5 list-disc pl-5">
                  {(() => {
                    type BenefitGroup =
                      | { type: "text"; text: string }
                      | { type: "table"; rows: Array<{ level: string; spells: string }> };

                    const groups: BenefitGroup[] = [];
                    let currentTable: Array<{ level: string; spells: string }> | null = null;

                    for (const b of selectedFeatDef.benefits) {
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

                      const match = group.text.match(/^([^.:]+?[.:])\s+(.+)$/s);
                      return (
                        <li key={i} className="leading-relaxed text-foreground/90">
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

            {selectedFeat === "Ability Score Improvement" && asiChoiceGroup && (
              <div className="border-t border-border/50 pt-4">
                <div className="mb-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {[ASI_PLUS_TWO_OPTION, ASI_PLUS_ONE_TWO_OPTION].map((option) => {
                    const isSelected = selectedAsiOption === option;
                    return (
                      <button
                        key={option}
                        type="button"
                        onClick={() => setAsiOption(option)}
                        aria-pressed={isSelected}
                        className={cn(
                          "rounded-lg border px-4 py-3 text-left text-sm transition-all duration-200",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                          isSelected
                            ? "border-primary bg-muted/60 text-foreground shadow-sm ring-1 ring-primary/20"
                            : "border-border bg-background/70 hover:border-primary/40 hover:bg-secondary/50",
                        )}
                      >
                        {option}
                      </button>
                    );
                  })}
                </div>
                {selectedAsiOption && (
                  <div className="mt-3">
                    <AbilitySelectList
                      choiceKey={selectedAsiOption === ASI_PLUS_TWO_OPTION ? plusTwoKey : plusOneKey}
                      title=""
                      description={selectedAsiOption === ASI_PLUS_TWO_OPTION ? "Choose one ability to increase by 2." : "Choose two different abilities to increase by 1."}
                      options={ASI_ABILITIES}
                      count={selectedAsiOption === ASI_PLUS_TWO_OPTION ? 1 : 2}
                    />
                  </div>
                )}
              </div>
            )}

            {featSubChoices.map((subChoice) => {
              if (!subChoice.choice_key) {
                if (import.meta.env.DEV) {
                  console.warn('[FeatDropdownPicker] missing choice_key for sub-choice', subChoice);
                }
                return null;
              }
              const subKey = subChoice.choice_key;
              const opts = (subChoice.options ?? []) as Array<unknown>;
              if (opts.length === 0) return null;

              if (subChoice.choice_category === "spells") {
                const spellOptions = opts.filter(
                  (o): o is string => typeof o === "string" && o.length > 0,
                );
                return (
                  <SpellChoiceList
                    key={subKey}
                    choiceKey={subKey}
                    title={subChoice.title ?? subKey}
                    description={`Choose ${subChoice.count ?? 1} spell${(subChoice.count ?? 1) > 1 ? "s" : ""}.`}
                    options={spellOptions}
                    count={subChoice.count ?? 1}
                    onInspectSpell={onInspectSpell}
                    inspectedSpellName={inspectedSpellName}
                  />
                );
              }

              const count = subChoice.count ?? 1;
              if (isAbilityScoreSubChoice(subChoice)) {
                return (
                  <AbilitySelectList
                    key={subKey}
                    choiceKey={subKey}
                    title=""
                    description="Choose ability score(s) to increase."
                    options={normalizeAbilityOptions(opts)}
                    count={count}
                  />
                );
              }

              const disabledOptions =
                grantedProficiencies && isProficiencySubChoice(subChoice)
                  ? grantedProficiencies
                  : undefined;

              return (
                <ChoiceList
                  key={subKey}
                  choiceKey={subKey}
                  title={subChoice.title ?? subKey}
                  description={subChoice.description ? `${subChoice.description}` : ""}
                  options={opts as Array<string | { name?: string }>}
                  optionDescriptions={subChoice.option_descriptions}
                  count={count}
                  disabledOptions={disabledOptions}
                  disabledReason="Already granted"
                />
              );
            })}
          </>
        )}
      </div>
    </fieldset>
  );
}
