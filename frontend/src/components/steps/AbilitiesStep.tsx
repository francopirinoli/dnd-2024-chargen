import { useEffect, useState } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { AlertCircle, Check, ChevronDown, ChevronUp, Dice6, Info, Loader2 } from "lucide-react";
import { api, type AbilityRoll } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useCharacterStore } from "@/store/characterStore";

const ABILITIES = [
  "Strength",
  "Dexterity",
  "Constitution",
  "Intelligence",
  "Wisdom",
  "Charisma",
] as const;
type Ability = (typeof ABILITIES)[number];

const MANUAL_MIN = 3;
const MANUAL_MAX = 18;
const EXTRA_MOD_MIN = -5;
const EXTRA_MOD_MAX = 5;

type Method = "standard_array" | "point_buy" | "manual" | "recommended";
type RollAssignments = Record<Ability, number | null>;

const EMPTY_ROLL_ASSIGNMENTS: RollAssignments = {
  Strength: null,
  Dexterity: null,
  Constitution: null,
  Intelligence: null,
  Wisdom: null,
  Charisma: null,
};

function defaultScores(
  method: Method,
  recommended?: Record<string, number>,
  pointBuyMin = 8,
): Partial<Record<Ability, number>> {
  if (method === "standard_array") {
    return {};
  }
  if (method === "recommended" && recommended) {
    return Object.fromEntries(
      ABILITIES.map((a) => [a, Number(recommended[a] ?? 10)]),
    ) as Record<Ability, number>;
  }
  return Object.fromEntries(ABILITIES.map((a) => [a, pointBuyMin])) as Record<
    Ability,
    number
  >;
}

function normalizeMethod(method: unknown): Method {
  if (method === "roll" || method === "manual") return "manual";
  if (
    method === "standard_array" ||
    method === "point_buy" ||
    method === "recommended"
  ) {
    return method;
  }
  return "standard_array";
}

function modifierToneClass(tone: unknown): string {
  if (tone === "positive") return "text-green-600 dark:text-green-400";
  if (tone === "negative") return "text-destructive/80";
  return "text-muted-foreground";
}

interface BackgroundAsi {
  total_points?: number;
  suggested?: Record<string, number>;
  ability_options?: string[];
}

interface AbilityGenerationState {
  abilities?: Record<string, {
    score?: number;
    modifier_display?: string;
    modifier_tone?: string;
  }>;
  standard_array?: {
    values?: number[];
    assigned_count?: number;
    complete?: boolean;
    valid?: boolean;
    available_values_by_ability?: Record<string, number[]>;
  };
  point_buy?: {
    total?: number;
    min?: number;
    max?: number;
    spent?: number;
    remaining?: number;
    controls?: Record<string, {
      current_cost?: number;
      can_increment?: boolean;
      can_decrement?: boolean;
      increment_score?: number | null;
      decrement_score?: number | null;
    }>;
  };
  manual?: { min?: number; max?: number };
  background_asi?: {
    spent?: number;
    remaining?: number;
    values_by_ability?: Record<string, number[]>;
  };
}

const STANDARD_ARRAY_DEFAULT = [15, 14, 13, 12, 10, 8];

export function AbilitiesStep() {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const setChoice = useCharacterStore((s) => s.setChoice);

  const method = normalizeMethod(choicesMade["ability_scores_method"]);

  const previewQuery = useQuery({
    queryKey: ["character", "preview-step", "abilities", choicesMade],
    queryFn: () => api.character.previewStep(choicesMade, "abilities"),
    placeholderData: keepPreviousData,
  });
  const recommended = previewQuery.data?.recommended_array as
    | Record<string, number>
    | undefined;
  const asi = (previewQuery.data?.background_asi as BackgroundAsi | undefined) ??
    { total_points: 3, suggested: {}, ability_options: [...ABILITIES] };
  const abilityGeneration = (previewQuery.data?.ability_generation as
    | AbilityGenerationState
    | undefined) ?? {};
  const pointBuyMin = abilityGeneration.point_buy?.min ?? 8;
  const standardValues =
    abilityGeneration.standard_array?.values &&
    abilityGeneration.standard_array.values.length > 0
      ? abilityGeneration.standard_array.values
      : STANDARD_ARRAY_DEFAULT;

  const storedScores = (choicesMade["ability_scores"] as
    | Record<string, unknown>
    | undefined) ??
    {};
  const fallbackScores = defaultScores(method, recommended, pointBuyMin);

  const scores = ABILITIES.reduce(
    (acc, a) => {
      const stored = Number(storedScores[a]);
      if (Number.isFinite(stored)) {
        acc[a] = stored;
      } else if (typeof fallbackScores[a] === "number") {
        acc[a] = Number(fallbackScores[a]);
      } else {
        acc[a] = 8;
      }
      return acc;
    },
    {} as Record<Ability, number>,
  );

  const standardArrayAssignments = ABILITIES.reduce(
    (acc, a) => {
      const value = Number(storedScores[a]);
      acc[a] = standardValues.includes(value)
        ? value
        : "";
      return acc;
    },
    {} as Record<Ability, number | "">,
  );

  const [rolledValues, setRolledValues] = useState<AbilityRoll[]>([]);
  const [rollAssignments, setRollAssignments] =
    useState<RollAssignments>(EMPTY_ROLL_ASSIGNMENTS);

  function setMethod(next: Method) {
    setChoice("ability_scores_method", next);
    setChoice("ability_scores", defaultScores(next, recommended, pointBuyMin));
  }

  // Keep `recommended` mode in sync with whatever the class-recommended
  // array currently is (e.g. after switching class).
  useEffect(() => {
    if (method !== "recommended" || !recommended) return;
    const current = (choicesMade["ability_scores"] as
      | Record<string, number>
      | undefined) ??
      {};
    const matches = ABILITIES.every(
      (a) => Number(current[a]) === Number(recommended[a]),
    );
    if (!matches) {
      setChoice("ability_scores", defaultScores("recommended", recommended, pointBuyMin));
    }
  }, [method, recommended, choicesMade, pointBuyMin, setChoice]);

  function setScore(ability: Ability, value: number) {
    const next = { ...scores, [ability]: value };
    setChoice("ability_scores", next);
  }

  function setStandardArrayScore(ability: Ability, value: number | "") {
    const next = { ...standardArrayAssignments, [ability]: value };
    const normalized = ABILITIES.reduce(
      (acc, a) => {
        const picked = next[a];
        if (typeof picked === "number") acc[a] = picked;
        return acc;
      },
      {} as Partial<Record<Ability, number>>,
    );
    setChoice("ability_scores", normalized);
  }

  function decrementPointBuy(ability: Ability) {
    const next = abilityGeneration.point_buy?.controls?.[ability]?.decrement_score;
    if (typeof next === "number") setScore(ability, next);
  }

  function incrementPointBuy(ability: Ability) {
    const next = abilityGeneration.point_buy?.controls?.[ability]?.increment_score;
    if (typeof next === "number") setScore(ability, next);
  }

  async function rollAllAbilityScores() {
    setRolledValues(await api.character.rollAbilities());
    setRollAssignments(EMPTY_ROLL_ASSIGNMENTS);
  }

  function assignRolledValue(ability: Ability, index: number | null) {
    setRollAssignments((prev) => ({ ...prev, [ability]: index }));
  }

  function applyRollAssignments() {
    const complete = ABILITIES.every((a) => rollAssignments[a] !== null);
    if (!complete || rolledValues.length !== 6) return;

    const assigned = ABILITIES.reduce(
      (acc, ability) => {
        const index = rollAssignments[ability];
        if (index !== null) acc[ability] = rolledValues[index]?.value ?? pointBuyMin;
        return acc;
      },
      {} as Record<Ability, number>,
    );

    setChoice("ability_scores_method", "manual");
    setChoice("ability_scores", assigned);
  }

  const assignedStandardValues = ABILITIES.map(
    (a) => standardArrayAssignments[a],
  ).filter((v): v is number => typeof v === "number");
  const arraySelections = assignedStandardValues;
  const localArrayComplete = assignedStandardValues.length === ABILITIES.length;
  const localArrayValid =
    localArrayComplete &&
    [...assignedStandardValues].sort((a, b) => b - a).join(",") ===
      [...standardValues].sort((a, b) => b - a).join(",");

  const arrayComplete =
    abilityGeneration.standard_array?.complete ?? localArrayComplete;
  const arrayValid =
    method !== "standard_array" ||
    (abilityGeneration.standard_array?.valid ?? localArrayValid);

  const getAvailableStandardValues = (ability: Ability): number[] => {
    const backendAvailable =
      abilityGeneration.standard_array?.available_values_by_ability?.[ability];
    if (Array.isArray(backendAvailable) && backendAvailable.length > 0) {
      return backendAvailable;
    }
    const current = standardArrayAssignments[ability];
    const usedByOthers = new Set(
      ABILITIES.filter((a) => a !== ability)
        .map((a) => standardArrayAssignments[a])
        .filter((v): v is number => typeof v === "number"),
    );
    return standardValues.filter(
      (v) => v === current || !usedByOthers.has(v),
    );
  };

  const additionalStored = (choicesMade["additional_ability_modifiers"] as
    | Record<string, number>
    | undefined) ??
    {};
  const additionalModifiers = ABILITIES.reduce(
    (acc, ability) => {
      acc[ability] = Number(additionalStored[ability] ?? 0);
      return acc;
    },
    {} as Record<Ability, number>,
  );

  function setAdditionalModifier(ability: Ability, value: number) {
    const clamped = Math.max(EXTRA_MOD_MIN, Math.min(EXTRA_MOD_MAX, value));
    // Always send the full 6-ability map (with explicit zeros for unset
    // abilities). The backend expects a complete `AbilityModifierMap` shape.
    const next = ABILITIES.reduce(
      (acc, a) => {
        acc[a] = a === ability ? clamped : additionalModifiers[a];
        return acc;
      },
      {} as Record<Ability, number>,
    );
    setChoice("additional_ability_modifiers", next);
  }

  const methodButtons = [
    ["standard_array", "Standard array"],
    ["point_buy", "Point buy"],
    ["manual", "Manual / Roll"],
    ["recommended", "Recommended"],
  ] as Array<[Method, string]>;

  const rollAssignmentsComplete =
    rolledValues.length === 6 && ABILITIES.every((a) => rollAssignments[a] !== null);
  const pointTotal = abilityGeneration.point_buy?.total ?? 0;
  const pointRemaining = abilityGeneration.point_buy?.remaining ?? 0;
  const manualMin = abilityGeneration.manual?.min ?? MANUAL_MIN;
  const manualMax = abilityGeneration.manual?.max ?? MANUAL_MAX;

  return (
    <div className="space-y-8">

      {/* ── Generation method ─────────────────────────────────────────── */}
      <section className="overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card to-secondary/40 shadow-sm">
        <div className="border-b border-border/70 px-5 py-5 sm:px-6">
          <div className="flex items-start gap-3">
            <div className="rounded-full bg-primary/10 p-2 text-primary">
              <Dice6 className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Step 1 of 2
              </p>
              <h3 className="mt-1 font-display text-2xl text-primary font-bold">
                Generation method
              </h3>
              <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
                Choose how to determine your six ability scores. Standard array and Point Buy are the balanced options; roll or enter values manually for a more adventurous approach.
              </p>
            </div>
          </div>
        </div>

        <div className="px-5 py-5 sm:px-6 space-y-4">
          <div className="flex flex-wrap gap-2">
            {methodButtons.map(([id, label]) => {
              const disabled = id === "recommended" && !recommended;
              const isSelected = method === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => !disabled && setMethod(id)}
                  disabled={disabled}
                  aria-pressed={isSelected}
                  title={disabled ? "Pick a class to see its recommended array." : undefined}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm font-medium transition-all duration-200",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                    isSelected
                      ? "border-primary bg-muted/60 text-foreground shadow-sm ring-1 ring-primary/20"
                      : "border-border/80 bg-background/75 text-muted-foreground hover:bg-secondary/50 hover:border-primary/40 hover:text-foreground",
                    disabled && "cursor-not-allowed opacity-40",
                  )}
                >
                  {isSelected && <Check className="h-3.5 w-3.5 text-primary" />}
                  {label}
                </button>
              );
            })}
          </div>

          {method === "recommended" && recommended && (
            <div className="flex items-start gap-2 rounded-lg border border-border/60 bg-secondary/30 px-4 py-3">
              <Info className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
              <p className="text-sm text-muted-foreground">
                Uses the suggested array for your class. Switch to{" "}
                <strong className="text-foreground">Standard array</strong>,{" "}
                <strong className="text-foreground">Point buy</strong>, or{" "}
                <strong className="text-foreground">Manual / Roll</strong> to customize.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* ── Roll helper (manual mode only) ────────────────────────────── */}
      {method === "manual" && (
        <section className="overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card to-secondary/40 shadow-sm">
          <div className="border-b border-border/70 px-5 py-4 sm:px-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h3 className="font-semibold text-lg">Roll helper</h3>
                <p className="text-sm text-muted-foreground">
                  4d6 drop lowest × 6 — then assign each result to an ability.
                </p>
              </div>
              <button
                type="button"
                onClick={rollAllAbilityScores}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-lg border border-primary bg-primary px-4 py-2 text-sm font-medium text-primary-foreground",
                  "transition-all duration-200 hover:-translate-y-0.5 hover:opacity-95",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                )}
              >
                <Dice6 className="h-4 w-4" />
                Roll now
              </button>
            </div>
          </div>

          {rolledValues.length > 0 && (
            <div className="px-5 py-5 sm:px-6 space-y-5">
              {/* Dice chips — one per rolled value */}
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-3">Rolled values</p>
                <div className="flex flex-wrap gap-2">
                  {rolledValues.map((roll, idx) => {
                    const assignedTo = ABILITIES.find((a) => rollAssignments[a] === idx);
                    return (
                      <div
                        key={idx}
                        className={cn(
                          "flex flex-col items-center rounded-xl border px-3 py-2 min-w-[54px] transition-all duration-200",
                          assignedTo
                            ? "border-border/50 bg-muted/30 opacity-50"
                            : "border-border/80 bg-background/80 shadow-sm",
                        )}
                      >
                        <span className="text-xl font-bold text-foreground leading-tight">{roll.value}</span>
                        <span className={cn("text-xs font-medium", modifierToneClass(roll.modifier_tone))}>
                          {roll.modifier_display}
                        </span>
                        {assignedTo && (
                          <span className="text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5">
                            {assignedTo.slice(0, 3)}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {ABILITIES.map((ability) => {
                  const current = rollAssignments[ability];
                  const usedByOthers = new Set<number>(
                    ABILITIES.filter((a) => a !== ability)
                      .map((a) => rollAssignments[a])
                      .filter((i): i is number => i !== null),
                  );
                  const options = rolledValues
                    .map((roll, idx) => ({ roll, idx }))
                    .filter(({ idx }) => idx === current || !usedByOthers.has(idx));

                  return (
                    <div key={`roll-${ability}`} className="rounded-xl border border-border/80 bg-background/75 px-3 py-3">
                      <label
                        htmlFor={`roll-assignment-${ability}`}
                        className="text-xs uppercase tracking-[0.2em] text-muted-foreground"
                      >
                        {ability}
                      </label>
                      <select
                        id={`roll-assignment-${ability}`}
                        value={current === null ? "" : String(current)}
                        onChange={(e) =>
                          assignRolledValue(
                            ability,
                            e.target.value === "" ? null : Number(e.target.value),
                          )
                        }
                        className={cn(
                          "mt-2 w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm",
                          "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
                        )}
                      >
                        <option value="">— assign —</option>
                        {options.map(({ roll, idx }) => (
                          <option key={`${ability}-${idx}-${roll.value}`} value={idx}>
                            {roll.value}
                          </option>
                        ))}
                      </select>
                    </div>
                  );
                })}
              </div>

              <button
                type="button"
                onClick={applyRollAssignments}
                disabled={!rollAssignmentsComplete}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm font-medium transition-all duration-200",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  rollAssignmentsComplete
                    ? "border-primary bg-primary text-primary-foreground shadow-sm hover:-translate-y-0.5 hover:opacity-95"
                    : "cursor-not-allowed border-border bg-muted text-muted-foreground opacity-60",
                )}
              >
                {rollAssignmentsComplete && <Check className="h-3.5 w-3.5" />}
                Apply assignments
              </button>
            </div>
          )}
        </section>
      )}

      {/* ── Assign scores ─────────────────────────────────────────────── */}
      <section className="overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card to-secondary/40 shadow-sm">
        <div className="border-b border-border/70 px-5 py-4 sm:px-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="font-semibold text-lg">Assign scores</h3>
              {method === "standard_array" && (
                <p className="text-sm text-muted-foreground">
                  Assign each of {standardValues.join(", ")} to exactly one ability.
                </p>
              )}
              {method === "point_buy" && (
                <p className="text-sm text-muted-foreground">
                  Spend up to {pointTotal} points. Higher scores cost more.
                </p>
              )}
              {method === "recommended" && (
                <p className="text-sm text-muted-foreground">
                  Class-recommended allocation — read-only.
                </p>
              )}
              {method === "manual" && (
                <p className="text-sm text-muted-foreground">
                  Enter scores between {manualMin} and {manualMax} for each ability.
                </p>
              )}
            </div>

            {method === "point_buy" && (
              <div className={cn(
                "flex-shrink-0 rounded-lg border px-3 py-2 text-center min-w-[108px]",
                pointRemaining < 0
                  ? "border-destructive/40 bg-destructive/10 text-destructive"
                  : pointRemaining === 0
                    ? "border-green-500/40 bg-green-500/10 text-green-700 dark:text-green-400"
                    : "border-border bg-secondary/30 text-muted-foreground",
              )}>
                {pointRemaining < 0 ? (
                  <>
                    <p className="text-xs uppercase tracking-widest mb-0.5">Over budget</p>
                    <p className="text-lg font-bold">+{Math.abs(pointRemaining)}</p>
                  </>
                ) : pointRemaining === 0 ? (
                  <>
                    <p className="text-xs uppercase tracking-widest mb-0.5">Complete</p>
                    <p className="text-lg font-bold flex items-center justify-center gap-1">
                      <Check className="h-5 w-5" />
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-xs uppercase tracking-widest mb-0.5">Remaining</p>
                    <p className="text-lg font-bold">{pointRemaining}</p>
                  </>
                )}
              </div>
            )}

            {method === "standard_array" && (
              <div className={cn(
                "flex-shrink-0 rounded-lg border px-3 py-2 text-center min-w-[100px]",
                arrayComplete
                  ? "border-green-500/40 bg-green-500/10 text-green-700 dark:text-green-400"
                  : "border-border bg-secondary/30 text-muted-foreground",
              )}>
                <p className="text-xs uppercase tracking-widest mb-0.5">Assigned</p>
                <p className="text-lg font-bold">
                  {arraySelections.length}
                  <span className="text-sm font-normal">/{ABILITIES.length}</span>
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="px-5 py-5 sm:px-6 space-y-4">
          {previewQuery.isLoading && method === "recommended" && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading recommended scores…
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {ABILITIES.map((ability) => {
              const currentScore = scores[ability];
              const abilityView = abilityGeneration.abilities?.[ability];
              const pointControl = abilityGeneration.point_buy?.controls?.[ability];
              const canPointBuyDecrement = pointControl?.can_decrement === true;
              const canPointBuyIncrement = pointControl?.can_increment === true;

              const displayScore =
                method === "standard_array"
                  ? standardArrayAssignments[ability] || null
                  : currentScore;

              return (
                <div
                  key={ability}
                  className="rounded-xl border border-border/80 bg-background/75 p-4"
                >
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-3">
                    {ability}
                  </p>

                  {/* Score + modifier display */}
                  {method !== "standard_array" && (
                    <div className="flex items-baseline gap-2 mb-3">
                      <span className="text-2xl font-bold text-foreground">
                        {displayScore ?? "—"}
                      </span>
                      {displayScore !== null && (
                        <span className={cn("text-sm font-medium", modifierToneClass(abilityView?.modifier_tone))}>
                          {abilityView?.modifier_display ?? "—"}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Controls */}
                  {method === "standard_array" ? (
                    <div>
                      <div className="flex items-baseline gap-2 mb-2">
                        <span className="text-2xl font-bold text-foreground">
                          {standardArrayAssignments[ability] || "—"}
                        </span>
                        {standardArrayAssignments[ability] && (
                          <span className={cn("text-sm font-medium", modifierToneClass(abilityView?.modifier_tone))}>
                            {abilityView?.modifier_display ?? "—"}
                          </span>
                        )}
                      </div>
                      <select
                        id={`score-${ability}`}
                        value={String(standardArrayAssignments[ability] || "")}
                        onChange={(e) =>
                          setStandardArrayScore(
                            ability,
                            e.target.value === "" ? "" : Number(e.target.value),
                          )
                        }
                        className={cn(
                          "w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm",
                          "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
                        )}
                      >
                        <option value="">— choose —</option>
                        {getAvailableStandardValues(ability).map((value) => (
                          <option key={`${ability}-${value}`} value={value}>
                            {value}
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : method === "point_buy" ? (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => decrementPointBuy(ability)}
                        disabled={!canPointBuyDecrement}
                        aria-label={`Decrease ${ability}`}
                        className={cn(
                          "h-8 w-8 rounded-md border text-sm font-bold transition-colors",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
                          canPointBuyDecrement
                            ? "border-border hover:bg-secondary/60 hover:border-primary/40"
                            : "cursor-not-allowed border-border opacity-40",
                        )}
                      >
                        <ChevronDown className="h-4 w-4 mx-auto" />
                      </button>
                      <button
                        type="button"
                        onClick={() => incrementPointBuy(ability)}
                        disabled={!canPointBuyIncrement}
                        aria-label={`Increase ${ability}`}
                        className={cn(
                          "h-8 w-8 rounded-md border text-sm font-bold transition-colors",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
                          canPointBuyIncrement
                            ? "border-border hover:bg-secondary/60 hover:border-primary/40"
                            : "cursor-not-allowed border-border opacity-40",
                        )}
                      >
                        <ChevronUp className="h-4 w-4 mx-auto" />
                      </button>
                      {method === "point_buy" && (
                        <span className="text-xs text-muted-foreground">
                        costs {pointControl?.current_cost ?? 0} pts
                        </span>
                      )}
                    </div>
                  ) : method === "recommended" ? null : (
                    <div className="flex items-center gap-2">
                      <input
                        id={`score-${ability}`}
                        type="number"
                        min={manualMin}
                        max={manualMax}
                        value={currentScore}
                        onChange={(e) =>
                          setScore(
                            ability,
                            Math.max(
                              manualMin,
                              Math.min(manualMax, Number(e.target.value) || manualMin),
                            ),
                          )
                        }
                        className={cn(
                          "w-20 rounded-md border border-input bg-background px-3 py-1.5 text-sm",
                          "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
                        )}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {!arrayValid && method === "standard_array" && (
            <div className="rounded-md border border-destructive/30 bg-destructive/10 p-4">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-destructive text-sm mb-1">
                    Incomplete assignment
                  </h4>
                  <p className="text-sm text-destructive/80">
                    Each value in the standard array must be used exactly once before continuing.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      <BackgroundAsiPicker
        asi={asi}
        state={abilityGeneration.background_asi}
        hasBackground={!!choicesMade["background"]}
      />

      {/* ── Additional modifiers (optional) ───────────────────────────── */}
      <section className="overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card to-secondary/40 shadow-sm">
        <div className="border-b border-border/70 px-5 py-4 sm:px-6">
          <h3 className="font-semibold text-lg">
            Additional modifiers
            <span className="text-sm font-normal text-muted-foreground ml-2">(Optional)</span>
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Applied on top of base scores and background bonuses — for magic items, feats, or DM rulings.
          </p>
        </div>

        <div className="px-5 py-5 sm:px-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {ABILITIES.map((ability) => {
              const value = additionalModifiers[ability];
              const canDown = value > EXTRA_MOD_MIN;
              const canUp = value < EXTRA_MOD_MAX;
              return (
                <div
                  key={`additional-${ability}`}
                  className="rounded-xl border border-border/80 bg-background/75 px-3 py-3"
                >
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">
                    {ability.slice(0, 3)}
                  </p>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => setAdditionalModifier(ability, value - 1)}
                      disabled={!canDown}
                      aria-label={`Decrease ${ability} modifier`}
                      className={cn(
                        "h-7 w-7 rounded-md border text-xs font-bold transition-colors",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
                        canDown
                          ? "border-border hover:bg-secondary/60 hover:border-primary/40"
                          : "cursor-not-allowed border-border opacity-40",
                      )}
                    >
                      −
                    </button>
                    <div className={cn(
                      "h-7 min-w-[44px] rounded-md border border-input bg-background px-2 text-center text-sm leading-7 font-medium",
                      value > 0 && "text-green-600 dark:text-green-400",
                      value < 0 && "text-destructive/80",
                    )}>
                      {value >= 0 ? `+${value}` : value}
                    </div>
                    <button
                      type="button"
                      onClick={() => setAdditionalModifier(ability, value + 1)}
                      disabled={!canUp}
                      aria-label={`Increase ${ability} modifier`}
                      className={cn(
                        "h-7 w-7 rounded-md border text-xs font-bold transition-colors",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
                        canUp
                          ? "border-border hover:bg-secondary/60 hover:border-primary/40"
                          : "cursor-not-allowed border-border opacity-40",
                      )}
                    >
                      +
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

    </div>
  );
}

function BackgroundAsiPicker({
  asi,
  state,
  hasBackground,
}: {
  asi: BackgroundAsi;
  state?: AbilityGenerationState["background_asi"];
  hasBackground: boolean;
}) {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const setChoice = useCharacterStore((s) => s.setChoice);
  const total = asi.total_points ?? 3;
  const options = (asi.ability_options ?? ABILITIES) as string[];
  const stored =
    (choicesMade["background_bonuses"] as Record<string, number> | undefined) ??
    {};

  const remaining = state?.remaining ?? total;

  function setBonus(ability: string, value: number) {
    const next = { ...stored, [ability]: value };
    // Drop zeros so the payload stays tidy.
    if (value <= 0) delete next[ability];
    setChoice("background_bonuses", next);
  }

  function applySuggested() {
    if (asi.suggested) setChoice("background_bonuses", asi.suggested);
  }

  if (total <= 0) return null;

  if (!hasBackground) {
    return (
      <section className="overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card to-secondary/40 shadow-sm">
        <div className="px-5 py-5 sm:px-6">
          <h3 className="font-semibold text-lg mb-1">Background ability bonuses</h3>
          <p className="text-sm text-muted-foreground">
            No background selected yet — pick a background first to distribute its ability bonuses here.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card to-secondary/40 shadow-sm">
      <div className="border-b border-border/70 px-5 py-4 sm:px-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="font-semibold text-lg">Background ability bonuses</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Distribute {total} point{total === 1 ? "" : "s"} across abilities (max +2 per ability).{" "}
              <span className={cn(
                "font-medium",
                remaining === 0 ? "text-green-600 dark:text-green-400" : "text-muted-foreground",
              )}>
                {remaining} remaining.
              </span>
            </p>
          </div>
          {asi.suggested && Object.keys(asi.suggested).length > 0 && (
            <button
              type="button"
              onClick={applySuggested}
              className={cn(
                "flex-shrink-0 inline-flex items-center gap-1.5 rounded-lg border border-border/80 px-3 py-2 text-sm font-medium",
                "bg-background/75 text-muted-foreground hover:bg-secondary/50 hover:border-primary/40 hover:text-foreground",
                "transition-all duration-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              )}
            >
              Use suggested
            </button>
          )}
        </div>
      </div>

      <div className="px-5 py-5 sm:px-6">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {options.map((ability) => {
            const v = Number(stored[ability] ?? 0);
            return (
              <div
                key={ability}
                className="rounded-xl border border-border/80 bg-background/75 px-3 py-3"
              >
                <label
                  htmlFor={`bonus-${ability}`}
                  className="text-xs uppercase tracking-[0.2em] text-muted-foreground"
                >
                  {ability.slice(0, 3)}
                </label>
                <div className="flex items-baseline gap-2 mt-1 mb-2">
                  <span className={cn(
                    "text-xl font-bold",
                    v > 0 ? "text-green-600 dark:text-green-400" : "text-muted-foreground",
                  )}>
                    +{v}
                  </span>
                </div>
                <select
                  id={`bonus-${ability}`}
                  value={v}
                  onChange={(e) => setBonus(ability, Number(e.target.value))}
                  className={cn(
                    "w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm",
                    "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
                  )}
                >
                  {(state?.values_by_ability?.[ability] ?? [v]).map((opt) => {
                    return (
                      <option key={opt} value={opt}>
                        +{opt}
                      </option>
                    );
                  })}
                </select>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
