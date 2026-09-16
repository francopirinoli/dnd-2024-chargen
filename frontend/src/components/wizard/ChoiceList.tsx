import { Check, CircleDashed, Info, ListChecks } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCharacterStore } from "@/store/characterStore";

/**
 * Generic single- or multi-select renderer for a {choice_key, options, count}
 * shape. Used for class/subclass skill picks, fighting style choices,
 * species trait choices, etc.
 *
 * Stores selection in `choices_made[choiceKey]` by default:
 *   - count === 1 → single string
 *   - count > 1   → array of strings (length capped at `count`)
 *
 * When `parentKey` is provided, the selection is instead stored at
 * `choices_made[parentKey][choiceKey]` (canonical nested shape — e.g.
 * `species_trait_choices`). Multi-select is not supported with a parentKey.
 */
interface Option {
  id?: string;
  name?: string;
  label?: string;
  description?: string;
}

interface Props {
  choiceKey: string;
  /** If set, write/read at `choices_made[parentKey][choiceKey]` instead of
   * the top level. Single-select only. */
  parentKey?: string;
  title?: string;
  description?: string;
  options: Array<string | Option>;
  /** Optional map of option value → description, merged with per-option `description`. */
  optionDescriptions?: Record<string, string>;
  count?: number;
  /** Option values that are already granted by another source (class, background, etc.).
   * Items that are currently selected in this choice are automatically excluded
   * so a player's own picks here are never incorrectly marked as "already granted". */
  disabledOptions?: string[];
  /** Short label shown beneath disabled options. Defaults to "Already granted". */
  disabledReason?: string;
  /** Optional compact badge shown below each option name (e.g. prerequisites). */
  optionBadges?: Record<string, string | undefined>;
  /** Optional info callback to inspect an option in a sidebar panel. */
  onInspectOption?: (optionValue: string) => void;
  /** Current option being inspected for aria-pressed state on info buttons. */
  inspectedOption?: string;
  /** When true, suppresses the default option description body. */
  hideOptionDescriptions?: boolean;
}

const ARRAY_BACKED_SINGLE_SELECT_KEYS = new Set(["skill_choices", "tool_choices"]);

function counterTone(selectedCount: number, requiredCount: number) {
  if (selectedCount === requiredCount) {
    return "border-primary/40 bg-muted/60 text-primary";
  }

  if (selectedCount > 0) {
    return "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300";
  }

  return "border-border bg-muted/40 text-muted-foreground";
}

function normalize(opt: string | Option): { value: string; label: string; description?: string } {
  if (typeof opt === "string") return { value: opt, label: opt };
  const value = opt.id ?? opt.name ?? opt.label ?? "";
  const label = opt.label ?? opt.name ?? opt.id ?? value;
  return { value, label, description: opt.description };
}

function normalizeSingleSelectValue(value: unknown): string {
  if (Array.isArray(value)) {
    return typeof value[0] === "string" ? value[0] : "";
  }
  return typeof value === "string" ? value : "";
}

export function ChoiceList({
  choiceKey,
  parentKey,
  title,
  description,
  options,
  optionDescriptions,
  count = 1,
  disabledOptions,
  disabledReason = "Already granted",
  optionBadges,
  onInspectOption,
  inspectedOption,
  hideOptionDescriptions = false,
}: Props) {
  const shouldStoreAsArray =
    !parentKey && ARRAY_BACKED_SINGLE_SELECT_KEYS.has(choiceKey);
  const value = useCharacterStore((s) => {
    if (parentKey) {
      const parent = s.choicesMade[parentKey];
      if (parent && typeof parent === "object" && !Array.isArray(parent)) {
        return (parent as Record<string, unknown>)[choiceKey];
      }
      return undefined;
    }
    return s.choicesMade[choiceKey];
  });
  const setChoice = useCharacterStore((s) => s.setChoice);
  const setNestedChoice = useCharacterStore((s) => s.setNestedChoice);

  function writeValue(next: unknown) {
    let normalizedNext = next;
    if (shouldStoreAsArray && !Array.isArray(next)) {
      normalizedNext = typeof next === "string" && next ? [next] : [];
    }
    if (parentKey) {
      setNestedChoice(parentKey, choiceKey, normalizedNext);
    } else {
      setChoice(choiceKey, normalizedNext);
    }
  }

  const normalized = options.map((opt) => {
    const n = normalize(opt);
    if (!n.description && optionDescriptions) {
      const fromMap =
        optionDescriptions[n.value] ?? optionDescriptions[n.label];
      if (fromMap) n.description = fromMap;
    }
    return n;
  });
  const isMulti = count > 1;
  const singleSelectValue = normalizeSingleSelectValue(value);

  const selected = new Set<string>(
    isMulti
      ? Array.isArray(value)
        ? (value as string[])
        : []
      : singleSelectValue
        ? [singleSelectValue]
        : [],
  );

  // Items the user has already selected in THIS choice are excluded from the
  // disabled set — they shouldn't be marked "already granted" when they were
  // chosen here, not from another source.
  const alreadyGranted = new Set<string>(
    (disabledOptions ?? []).filter((opt) => !selected.has(opt)),
  );

  function toggle(v: string) {
    if (!isMulti) {
      writeValue(v);
      return;
    }
    const next = new Set(selected);
    if (next.has(v)) {
      next.delete(v);
    } else {
      if (next.size >= count) return;
      next.add(v);
    }
    writeValue(Array.from(next));
  }

  const selectedCount = selected.size;
  const remainingCount = Math.max(count - selectedCount, 0);
  const selectedValue = !isMulti ? singleSelectValue : "";
  const selectedOption = !isMulti
    ? normalized.find((opt) => opt.value === selectedValue)
    : undefined;
  const displayTitle = title === "" ? null : (title ?? choiceKey);
  const counter = isMulti ? (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold sm:ml-auto",
        counterTone(selectedCount, count),
      )}
    >
      <ListChecks className="h-3.5 w-3.5" />
      <span>
        {selectedCount} of {count} selected
      </span>
      <span className="text-current/80">
        {remainingCount === 0
          ? "Complete"
          : `${remainingCount} remaining`}
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

  return (
    <fieldset className="rounded-xl border border-border/70 bg-card/70 p-4 shadow-sm sm:p-5">
      {displayTitle && (
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <legend className="px-0 text-base font-semibold text-foreground">
            {displayTitle}
          </legend>
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
      {isMulti ? (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {normalized.map((opt) => {
            const isSelected = selected.has(opt.value);
            const isAlreadyGranted = alreadyGranted.has(opt.value);
            const disabled =
              isAlreadyGranted ||
              (isMulti && !isSelected && selected.size >= count);
            return (
              <div
                key={opt.value}
                className={cn(
                  "group relative overflow-hidden rounded-lg border text-left text-sm transition-all duration-200",
                  isSelected && !isAlreadyGranted &&
                    "border-primary bg-muted/60 text-foreground shadow-sm ring-1 ring-primary/20",
                  !isSelected && !disabled &&
                    "border-border bg-background/70 hover:-translate-y-0.5 hover:border-primary/40 hover:bg-secondary/60 hover:shadow-sm",
                  isAlreadyGranted &&
                    "border-border/40 bg-muted/10 opacity-50",
                  !isAlreadyGranted && disabled &&
                    "border-border/60 bg-muted/20 opacity-45",
                )}
              >
                <div className="flex items-stretch">
                  <button
                    type="button"
                    onClick={() => !isAlreadyGranted && toggle(opt.value)}
                    disabled={disabled}
                    aria-pressed={isSelected}
                    aria-label={
                      isAlreadyGranted
                        ? `${opt.label} — ${disabledReason.toLowerCase()}`
                        : opt.label
                    }
                    className={cn(
                      "min-w-0 flex-1 px-4 py-3 text-left",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                      (isAlreadyGranted || (!isAlreadyGranted && disabled)) &&
                        "cursor-not-allowed",
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-medium">{opt.label}</div>
                        {optionBadges?.[opt.value] && (
                          <span
                            className="mt-1 inline-flex rounded-full border border-border/70 bg-background/70 px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
                            role="status"
                            aria-label={`Prerequisite: ${optionBadges[opt.value]}`}
                          >
                            {optionBadges[opt.value]}
                          </span>
                        )}
                        {isAlreadyGranted && (
                          <div className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                            {disabledReason}
                          </div>
                        )}
                        {!isAlreadyGranted && !hideOptionDescriptions && opt.description && (
                          <div className="mt-1 text-xs text-muted-foreground">
                            {opt.description}
                          </div>
                        )}
                      </div>
                      <span
                        className={cn(
                          "mt-0.5 inline-flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border transition-colors",
                          isSelected
                            ? "border-primary bg-background text-primary"
                            : "border-border bg-background text-transparent group-hover:border-primary/40",
                        )}
                      >
                        <Check className="h-3.5 w-3.5" />
                      </span>
                    </div>
                  </button>
                  {onInspectOption && (
                    <button
                      type="button"
                      onClick={() => onInspectOption(opt.value)}
                      aria-label={`View details for ${opt.label}`}
                      aria-pressed={inspectedOption === opt.value}
                      className={cn(
                        "flex flex-shrink-0 items-center justify-center border-l border-border/70 px-3 text-muted-foreground transition-colors",
                        "hover:bg-muted hover:text-foreground",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                        inspectedOption === opt.value && "text-primary",
                      )}
                    >
                      <Info className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="space-y-3">
          <select
            value={selectedValue}
            onChange={(event) => writeValue(event.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label={title ?? choiceKey}
          >
            <option value="">Select an option</option>
            {normalized.map((opt) => (
              <option
                key={opt.value}
                value={opt.value}
                disabled={alreadyGranted.has(opt.value)}
              >
                {opt.label}
              </option>
            ))}
          </select>
          {selectedOption && !hideOptionDescriptions && selectedOption.description && (
            <div className="text-sm text-muted-foreground">
              {selectedOption.description}
            </div>
          )}
          {selectedOption && optionBadges?.[selectedOption.value] && (
            <span
              className="inline-flex rounded-full border border-border/70 bg-background/70 px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
              role="status"
              aria-label={`Prerequisite: ${optionBadges[selectedOption.value]}`}
            >
              {optionBadges[selectedOption.value]}
            </span>
          )}
          {alreadyGranted.size > 0 && (
            <div className="text-xs text-muted-foreground">
              Disabled options are marked as unavailable because they are already granted.
            </div>
          )}
        </div>
      )}
    </fieldset>
  );
}
