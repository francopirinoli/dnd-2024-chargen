import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  BookOpen,
  Check,
  ChevronRight,
  Layers3,
  Plus,
  Shield,
  Sparkles,
  Sword,
  Trash2,
  User,
} from "lucide-react";
import {
  api,
  type ChoicesMade,
  type ClassAllocation,
  type ClassDetail,
  type ClassSummary,
  type FeatDefinition,
  type GeneralFeatsReference,
  type Multiclassing,
  type OriginFeatsReference,
  type SpellDefinition,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { useCharacterStore } from "@/store/characterStore";
import { useSupplementStore } from "@/store/supplementStore";
import { ChoiceList } from "@/components/wizard/ChoiceList";
import { FeatDropdownPicker } from "@/components/wizard/FeatDropdownPicker";
import { SpellChoiceList } from "@/components/wizard/FeatChoicesPicker";
import { ClassAdvancedChoices, type SpellReference } from "@/components/wizard/ClassAdvancedChoices";
import { useWizardSidebarPanel } from "@/components/layout/useWizardSidebarPanel";

interface PreviewChoice {
  choice_key?: string;
  choices_made_key?: string;
  name?: string;
  feature_name?: string;
  title?: string;
  description?: string;
  options?: Array<unknown>;
  option_descriptions?: Record<string, string>;
  count?: number;
  depends_on?: string;
  depends_on_value?: string;
  choice_category?: string;
}

interface ClassFeatPrerequisiteWarning {
  choice_key?: string;
  feat_name?: string;
  messages: string[];
}

interface PrerequisiteResult {
  ok?: boolean;
  missing?: string[];
  messages?: string[];
  abilities_unknown?: boolean;
}

const DND_SKILLS = new Set([
  "Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception",
  "History", "Insight", "Intimidation", "Investigation", "Medicine",
  "Nature", "Perception", "Performance", "Persuasion", "Religion",
  "Sleight of Hand", "Stealth", "Survival"
]);

function isSpellLikeChoice(
  choice: PreviewChoice,
  options: Array<unknown>,
): options is string[] {
  if (
    !options.every((option) => typeof option === "string" && option.length > 0)
  ) {
    return false;
  }
  if (choice.choice_category === "spells") {
    return true;
  }

  // If any option is a standard skill name, this is a skill choice, not a spell choice!
  if (options.some((opt) => typeof opt === "string" && DND_SKILLS.has(opt))) {
    return false;
  }

  const keyOrTitle = [
    choice.choice_key,
    choice.choices_made_key,
    choice.feature_name,
    choice.title,
    choice.name,
  ]
    .filter((value): value is string => typeof value === "string" && value.length > 0)
    .join(" ")
    .toLowerCase();

  if (
    keyOrTitle.includes("skill") ||
    keyOrTitle.includes("proficiency") ||
    keyOrTitle.includes("expertise") ||
    keyOrTitle.includes("tool") ||
    keyOrTitle.includes("weapon") ||
    keyOrTitle.includes("language") ||
    keyOrTitle.includes("shot") ||
    keyOrTitle.includes("maneuver")
  ) {
    return false;
  }

  // Only check title, name, and choice_key — NOT feature description, which can describe
  // a multi-benefit feature like Arcane Archer Lore mentioning both cantrips and skills.
  return keyOrTitle.includes("spell") || keyOrTitle.includes("cantrip");
}

interface SubclassSummary {
  id: string;
  name: string;
  description?: string;
  level_3_feature_names?: string[];
  source?: string;
  source_id?: string;
  source_title?: string;
}

interface SubclassDetail {
  name?: string;
  description?: string;
  features_by_level?: Record<string, Record<string, unknown> | string[]>;
}

interface SubclassFeatureEntry {
  name: string;
  description?: string;
  options?: string[];
}

type ClassInfoTarget = { kind: "class" } | { kind: "subclass"; id: string };

function clampLevel(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value)) return 1;
  return Math.max(1, Math.min(20, Math.floor(value)));
}

function normalizeAllocations(value: unknown): ClassAllocation[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => {
      if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
        return null;
      }
      const row = entry as Record<string, unknown>;
      const className =
        typeof row.class_name === "string" ? row.class_name : "";
      const level = clampLevel(row.level);
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

/** Generate the variants of a depends_on key the parent choice might be stored under. */
function parentKeyVariants(key: string): string[] {
  const snake = key.toLowerCase().replace(/[\s_-]+/g, "_");
  const titleSpaces = snake
    .split("_")
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
  // de-dup while keeping order
  return Array.from(new Set([key, snake, titleSpaces]));
}

const CLASS_FEAT_ASI_OPTION_KEY_RE =
  /^(class_feat_\d+)_(asi_option|ability_plus_2|abilities_plus_1)$/;

/**
 * Collapses list-based backend feature choices into a shared feature header.
 * Example: `feature_name="Deft Explorer_deft_explorer_expertise"` with
 * `choice_key="deft_explorer_expertise"` groups under `"Deft Explorer"`.
 */
function groupedFeatureName(choice: PreviewChoice): string | null {
  if (!choice.feature_name || !choice.choice_key) return null;
  const suffix = `_${choice.choice_key}`;
  if (choice.feature_name.endsWith(suffix)) {
    const rawGroup = choice.feature_name.slice(0, -suffix.length);
    return rawGroup.replace(/^subclass_/, "");
  }
  return null;
}

function groupedChoiceTitle(choice: PreviewChoice, groupName: string): string {
  const rawTitle =
    choice.title ?? choice.name ?? choice.choice_key ?? groupName;
  const withoutMeta = rawTitle.replace(/\s+\([^)]*\)\s*$/, "");
  const cleanGroupName = groupName.replace(/^subclass_/, "");
  const prefix = `${cleanGroupName} - `;
  let title = withoutMeta.startsWith(prefix)
    ? withoutMeta.slice(prefix.length)
    : withoutMeta;
  // Format numbered choices like "Skill1" -> "Skill 1"
  title = title.replace(/^([A-Za-z]+)(\d+)$/, "$1 $2");
  return title;
}

function featureLevelEntries(
  featuresByLevel: SubclassDetail["features_by_level"],
  classData?: Record<string, unknown>,
): Array<{ level: string; features: SubclassFeatureEntry[] }> {
  if (!featuresByLevel) return [];

  function featureText(raw: unknown): string | undefined {
    if (typeof raw === "string" && raw.trim().length > 0) {
      return raw;
    }
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
      return undefined;
    }

    const node = raw as Record<string, unknown>;
    const baseDescription =
      typeof node.description === "string" && node.description.trim().length > 0
        ? node.description
        : "";

    const effects = Array.isArray(node.effects)
      ? (node.effects as Array<Record<string, unknown>>)
      : [];

    const grantedSpells = effects
      .filter(
        (effect) =>
          effect?.type === "grant_spell" && typeof effect.spell === "string",
      )
      .map((effect) => {
        const spell = String(effect.spell);
        const minLevel =
          typeof effect.min_level === "number"
            ? ` (level ${effect.min_level})`
            : "";
        return `${spell}${minLevel}`;
      });

    const extra =
      grantedSpells.length > 0
        ? `Always prepared spells: ${grantedSpells.join(", ")}.`
        : "";

    const combined = [baseDescription, extra].filter(Boolean).join(" ").trim();
    return combined.length > 0 ? combined : undefined;
  }

  function extractOptions(raw: unknown): string[] | undefined {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) return undefined;
    const node = raw as Record<string, unknown>;
    const choices = node.choices as Record<string, unknown> | undefined;
    if (!choices) return undefined;
    const source = choices.source as Record<string, unknown> | undefined;
    if (!source || source.type !== "internal") return undefined;
    const listName = source.list as string | undefined;
    if (!listName || !classData) return undefined;
    const list = classData[listName];
    if (!list || typeof list !== "object" || Array.isArray(list))
      return undefined;
    return Object.keys(list as Record<string, unknown>);
  }

  return Object.entries(featuresByLevel)
    .map(([level, value]) => {
      const features: SubclassFeatureEntry[] = Array.isArray(value)
        ? value
            .filter((entry): entry is string => typeof entry === "string")
            .map((name) => ({ name }))
        : Object.entries(value ?? {})
            .filter(([name]) => Boolean(name))
            .map(([name, description]) => ({
              name,
              description: featureText(description),
              options: extractOptions(description),
            }));

      return { level, features };
    })
    .filter((entry) => entry.features.length > 0)
    .sort((a, b) => Number(a.level) - Number(b.level));
}

function matchesPreviewContext(
  previewData: Record<string, unknown> | undefined,
  selectedClass: string,
  level: number,
): boolean {
  if (!previewData) return false;
  const previewChoices = previewData["choices_made"];
  if (
    !previewChoices ||
    typeof previewChoices !== "object" ||
    Array.isArray(previewChoices)
  ) {
    return false;
  }

  const choices = previewChoices as Record<string, unknown>;
  const previewClass = typeof choices.class === "string" ? choices.class : "";
  const previewLevel = clampLevel(choices.level);

  // Only validate class + level. Subclass changes within the same class
  // use keepPreviousData so the UI stays mounted during the refetch;
  // the subclass-specific choices update smoothly when the new response arrives.
  return previewClass === selectedClass && previewLevel === clampLevel(level);
}

function formatProfList(values: string[] | null | undefined): string {
  if (!values || values.length === 0) return "—";
  return values.join(", ");
}

function formatMulticlassSkillProfs(
  block: Multiclassing["skill_proficiencies"],
): string {
  if (!block) return "None";
  const opts = block.options;
  if (opts === "any") return `Choose ${block.count} from any skill`;
  if (Array.isArray(opts) && opts.length > 0) {
    return `Choose ${block.count} from ${opts.join(", ")}`;
  }
  return `Choose ${block.count}`;
}

function isClassFeatChoiceKey(value: string): boolean {
  return /^class_feat_\d+$/.test(value);
}

function getEffectiveChoiceKey(choice: PreviewChoice): string {
  if (isClassFeatChoiceKey(choice.choice_key ?? "")) return choice.choice_key!;
  if (isClassFeatChoiceKey(choice.choices_made_key ?? "")) return choice.choices_made_key!;
  return choice.choices_made_key ?? choice.choice_key ?? choice.feature_name ?? choice.name ?? "";
}

export function ClassStep() {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const setChoice = useCharacterStore((s) => s.setChoice);
  const activeClassRowIndex = useCharacterStore((s) => s.activeClassRowIndex);
  const setActiveClassRowIndex = useCharacterStore(
    (s) => s.setActiveClassRowIndex,
  );

  const storedRows = useMemo(
    () => normalizeAllocations(choicesMade.classes),
    [choicesMade.classes],
  );
  const classAllocations = useMemo(() => {
    return storedRows;
  }, [storedRows]);

  const { setSidebarPanel } = useWizardSidebarPanel();
  const [infoTarget, setInfoTarget] = useState<ClassInfoTarget>({
    kind: "class",
  });
  const [inspectedSpell, setInspectedSpell] = useState<SpellReference | null>(
    null,
  );

  function writeAllocations(nextRows: ClassAllocation[]) {
    const normalized =
      nextRows.length > 0
        ? normalizeAllocations(nextRows)
        : [{ class_name: "", level: 1 }];

    setChoice("classes", normalized);
  }

  useEffect(() => {
    if (classAllocations.length === 0) {
      writeAllocations([{ class_name: "", level: 1 }]);
    }
  }, [classAllocations.length]);

  useEffect(() => {
    if (classAllocations.length === 0) {
      if (activeClassRowIndex !== 0) {
        setActiveClassRowIndex(0);
      }
      return;
    }

    const maxIndex = classAllocations.length - 1;
    const clampedIndex = Math.min(activeClassRowIndex, maxIndex);
    if (clampedIndex !== activeClassRowIndex) {
      setActiveClassRowIndex(clampedIndex);
    }
  }, [activeClassRowIndex, classAllocations.length, setActiveClassRowIndex]);

  const activeRowIndex =
    classAllocations.length > 0
      ? Math.min(activeClassRowIndex, classAllocations.length - 1)
      : 0;

  const activeRow = classAllocations[activeRowIndex] ??
    classAllocations[0] ?? { class_name: "", level: 1 };
  const selectedClass = activeRow.class_name ?? "";
  const selectedSubclass = activeRow.subclass ?? "";
  const multiclassPending = classAllocations.length > 1;
  const activeRowLabel = activeRowIndex + 1;
  const activeSources = useSupplementStore((s) => s.activeSources);

  const previewChoices: ChoicesMade = useMemo(() => {
    if (!selectedClass) return choicesMade;
    return {
      ...choicesMade,
      active_sources: activeSources,
      class: selectedClass,
      level: clampLevel(activeRow.level),
      ...(selectedSubclass ? { subclass: selectedSubclass } : {}),
    };
  }, [activeRow.level, choicesMade, selectedClass, selectedSubclass, activeSources]);

  const classesQuery = useQuery({
    queryKey: ["catalog", "classes", activeSources],
    queryFn: () => api.catalog.classes(activeSources),
  });

  const allClassSummaries = useMemo(
    () => classesQuery.data ?? [],
    [classesQuery.data],
  );
  const abilitiesUnknown =
    !choicesMade.ability_scores || Object.keys(choicesMade.ability_scores).length === 0;

  // Fetch full class data (with features_by_level) for the detail panel
  const fullClassQuery = useQuery({
    queryKey: ["catalog", "classes", selectedClass, activeSources],
    queryFn: () => api.catalog.getClass(selectedClass, activeSources),
    enabled: !!selectedClass,
  });
  const generalFeatsQuery = useQuery({
    queryKey: ["catalog", "reference", "general_feats", activeSources],
    queryFn: () =>
      api.catalog.getReference<GeneralFeatsReference>("general_feats", activeSources),
  });

  // Stable key fragment for skill_choices: sorted join so that order changes
  // don't cause spurious re-fetches, but adding/removing a skill does.
  // skill_choices must be included so expertise pickers (whose options are
  // filtered to the character's current proficiencies) refresh when the user
  // changes their skill selection.
  const skillChoicesKey =
    (choicesMade.skill_choices as string[] | undefined)
      ?.slice()
      .sort()
      .join(",") ?? "";
  const classFeatChoicesKey = Object.entries(choicesMade)
    .filter(([k]) => k.startsWith("class_feat_"))
    .sort(([a], [b]) => a.localeCompare(b))
    .map(
      ([k, v]) =>
        `${k}:${Array.isArray(v) ? v.slice().sort().join("|") : String(v)}`,
    )
    .join(";");
  const nestedClassChoicesKey = Object.entries(choicesMade)
    .filter(
      ([key]) =>
        !["class", "subclass", "level", "classes", "skill_choices"].includes(
          key,
        ),
    )
    .filter(([key]) => !key.startsWith("class_feat_"))
    .filter(
      ([, value]) =>
        typeof value === "string" ||
        typeof value === "number" ||
        (Array.isArray(value) &&
          value.every(
            (item) => typeof item === "string" || typeof item === "number",
          )),
    )
    .sort(([a], [b]) => a.localeCompare(b))
    .map(
      ([key, value]) =>
        `${key}:${Array.isArray(value) ? value.slice().sort().join("|") : String(value)}`,
    )
    .join(";");

  const previewQuery = useQuery({
    // Key on the four fields that actually change what class features are
    // shown. Deliberately excludes spell_selections, mastery_selections, etc.
    // so picking a spell/mastery/invocation doesn't force a reload of the
    // class preview. skill_choices IS included because expertise-picker options
    // depend on the character's skill proficiencies.
    queryKey: [
      "character",
      "preview-step",
      "class",
      selectedClass,
      clampLevel(activeRow.level),
      selectedSubclass,
      skillChoicesKey,
      classFeatChoicesKey,
      nestedClassChoicesKey,
    ],
    queryFn: () => api.character.previewStep(previewChoices, "class"),
    enabled: !!selectedClass,
    placeholderData: keepPreviousData,
  });

  // For detail panel: use full class data (which has the complete features_by_level from JSON).
  // When the selected class changes, react-query serves the previous response as placeholder
  // data until the new fetch resolves. Treat that placeholder as "no data yet" so the panel
  // doesn't momentarily render the prior class's features under the new class's name.
  const classSummary = (classesQuery.data ?? []).find(
    (cls) => cls.id === selectedClass,
  );
  const classSummaryById = useMemo(() => {
    return new Map((classesQuery.data ?? []).map((entry) => [entry.id, entry]));
  }, [classesQuery.data]);
  const fullClassData = fullClassQuery.isPlaceholderData
    ? undefined
    : (fullClassQuery.data as ClassDetail | undefined);
  const detailClass =
    selectedClass && classSummary
      ? ({
          ...classSummary,
          features_by_level:
            (fullClassData?.features_by_level as
              | Record<string, Record<string, unknown> | string[]>
              | undefined) ?? {},
        } as any)
      : undefined;

  const previewDataRaw = previewQuery.data as
    | Record<string, unknown>
    | undefined;
  const previewData = matchesPreviewContext(
    previewDataRaw,
    selectedClass,
    activeRow.level,
  )
    ? previewDataRaw
    : undefined;
  const needsSubclass = previewData?.["needs_subclass"] === true;
  const multiclassPrereqByClass =
    ((previewData?.["multiclass_prerequisites"] as
      | { classes?: Record<string, PrerequisiteResult> }
      | undefined)?.classes) ?? {};
  const serverFeatPrerequisiteWarnings =
    (previewData?.["class_feat_prerequisite_warnings"] as
      | ClassFeatPrerequisiteWarning[]
      | undefined) ?? [];
  const availableSubclasses =
    (previewData?.["available_subclasses"] as SubclassSummary[] | undefined) ??
    [];
  const activeSubclassId =
    infoTarget.kind === "subclass"
      ? infoTarget.id
      : selectedSubclass || availableSubclasses[0]?.id || "";
  const subclassDetailQuery = useQuery({
    queryKey: ["catalog", "subclass", selectedClass, activeSubclassId],
    queryFn: () => api.catalog.getSubclass(selectedClass, activeSubclassId),
    enabled: !!selectedClass && needsSubclass && !!activeSubclassId,
  });
  const activeSubclassDetail = subclassDetailQuery.isPlaceholderData
    ? undefined
    : (subclassDetailQuery.data as SubclassDetail | undefined);
  const activeFeatureLevels = featureLevelEntries(
    activeSubclassDetail?.features_by_level,
  );
  const shouldRenderInfoPanel =
    infoTarget.kind === "subclass"
      ? Boolean(activeSubclassId)
      : Boolean(detailClass);
  const generalFeatDefinitions = useMemo<Record<string, FeatDefinition>>(
    () => generalFeatsQuery.data?.general_feats ?? {},
    [generalFeatsQuery.data],
  );
  const originFeatsQuery = useQuery({
    queryKey: ["catalog", "reference", "origin_feats", activeSources],
    queryFn: () =>
      api.catalog.getReference<OriginFeatsReference>("origin_feats", activeSources),
  });
  const originFeatDefinitions = useMemo<Record<string, FeatDefinition>>(
    () => originFeatsQuery.data?.origin_feats ?? {},
    [originFeatsQuery.data],
  );

  // Only show the overlay for previewQuery when the *structural* parts of its
  // key change (class, subclass, level) — not when only choice keys (skills,
  // feats, nested choices) change. Those background re-fetches are silent: the
  // nav-bar validation indicator covers their status.
  const structuralKey = `${selectedClass}:${clampLevel(activeRow.level)}:${selectedSubclass ?? ""}`;
  const prevStructuralKeyRef = useRef(structuralKey);
  const structuralChangePendingRef = useRef(false);
  if (prevStructuralKeyRef.current !== structuralKey) {
    prevStructuralKeyRef.current = structuralKey;
    structuralChangePendingRef.current = true;
  }
  if (!previewQuery.isFetching) {
    structuralChangePendingRef.current = false;
  }

  const isStepFetching =
    (structuralChangePendingRef.current && previewQuery.isFetching) ||
    fullClassQuery.isFetching ||
    subclassDetailQuery.isFetching;

  useEffect(() => {
    setInspectedSpell(null);
    setInfoTarget({ kind: "class" });
  }, [activeRowIndex, selectedClass]);

  useEffect(() => {
    setSidebarPanel(
      inspectedSpell ? (
        <SpellInfoPanel
          spell={inspectedSpell}
          onBack={() => setInspectedSpell(null)}
        />
      ) : shouldRenderInfoPanel ? (
        <ClassInfoPanel
          infoTarget={infoTarget}
          detailClass={detailClass}
          fullClassData={fullClassData}
          isPrimaryRow={activeRowIndex === 0}
          selectedClass={selectedClass}
          classLoading={
            (fullClassQuery.isLoading || fullClassQuery.isPlaceholderData) &&
            !fullClassData
          }
          showClassFeatureFallback={
            !!selectedClass &&
            !!fullClassData &&
            !detailClass?.features_by_level
          }
          needsSubclass={needsSubclass}
          selectedSubclass={selectedSubclass}
          activeSubclassName={
            availableSubclasses.find((sub) => sub.id === activeSubclassId)?.name
          }
          activeSubclassDetail={activeSubclassDetail}
          activeFeatureLevels={activeFeatureLevels}
          subclassLoading={
            (subclassDetailQuery.isLoading ||
              subclassDetailQuery.isPlaceholderData) &&
            !activeSubclassDetail
          }
        />
      ) : null,
    );
    return () => setSidebarPanel(null);
  }, [
    activeFeatureLevels,
    activeRowIndex,
    activeSubclassDetail,
    activeSubclassId,
    availableSubclasses,
    detailClass,
    fullClassData,
    fullClassQuery.isLoading,
    fullClassQuery.isPlaceholderData,
    inspectedSpell,
    infoTarget,
    needsSubclass,
    selectedClass,
    selectedSubclass,
    setSidebarPanel,
    shouldRenderInfoPanel,
    subclassDetailQuery.isLoading,
    subclassDetailQuery.isPlaceholderData,
  ]);

  return (
    <div className="relative space-y-8">
      {isStepFetching && (
        <div
          aria-live="polite"
          aria-busy="true"
          className="absolute inset-0 z-20 flex items-center justify-center rounded-2xl bg-background/60 backdrop-blur-[2px]"
        >
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary/30 border-t-primary" />
            <p className="text-sm text-muted-foreground">Loading…</p>
          </div>
        </div>
      )}
      {/* ── Character Name / Identity Card ──────────────────────── */}
      <section className="overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card to-secondary/40 shadow-sm">
        <div className="border-b border-border/70 px-5 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-primary/10 p-2 text-primary">
              <User className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Identity
              </p>
              <h3 className="mt-0.5 font-display text-xl text-primary font-bold">
                Character Name
              </h3>
            </div>
          </div>
        </div>
        <div className="px-5 py-4 sm:px-6">
          <label htmlFor="character_name_step_input" className="sr-only">
            Character Name
          </label>
          <input
            id="character_name_step_input"
            type="text"
            value={(choicesMade.character_name as string | undefined) ?? ""}
            onChange={(e) => setChoice("character_name", e.target.value)}
            placeholder="Enter your character's name (e.g. Valeros, Lyra, Torvin)..."
            className="w-full rounded-lg border border-border/80 bg-background/90 px-4 py-2.5 text-base text-foreground placeholder:text-muted-foreground/60 shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card to-secondary/40 shadow-sm">
        <div className="border-b border-border/70 px-5 py-5 sm:px-6">
          <div className="flex items-start gap-3">
            <div className="rounded-full bg-primary/10 p-2 text-primary">
              <Sword className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Primary choice
              </p>
              <h3 className="mt-1 font-display text-2xl text-primary font-bold">
                Choose your class first
              </h3>
              <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
                Your class defines the core fantasy, early play pattern, and
                which follow-up choices appear below.
              </p>
            </div>
          </div>
        </div>

        <div
          className={cn(
            "grid grid-cols-1 gap-6 lg:items-start",
            "px-5 py-5 sm:px-6",
          )}
        >
          <div className="space-y-3">
            {classAllocations.map((row, idx) => {
              const isPrimary = idx === 0;
              const isActiveRow = idx === activeRowIndex;
              const rowClassSummary = classSummaryById.get(row.class_name);
              const rowSubclassThreshold =
                rowClassSummary?.subclass_selection_level;
              const rowNeedsSubclass =
                isActiveRow && row.class_name
                  ? needsSubclass
                  : Boolean(
                      row.class_name &&
                      typeof rowSubclassThreshold === "number" &&
                      clampLevel(row.level) >= rowSubclassThreshold,
                    );
              const rowSubclassLabel = row.subclass
                ? `Subclass: ${row.subclass}`
                : rowNeedsSubclass
                  ? "Subclass required"
                  : typeof rowSubclassThreshold === "number" &&
                      clampLevel(row.level) < rowSubclassThreshold
                    ? `Subclass at level ${rowSubclassThreshold}`
                    : "Subclass optional";
              return (
                <div
                  key={`class-row-${idx}`}
                  className={cn(
                    "rounded-xl border border-border/70 bg-background/75 p-4",
                    isPrimary && "ring-1 ring-primary/20",
                    isActiveRow &&
                      "border-primary/40 bg-background ring-2 ring-primary/20",
                  )}
                >
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    {isActiveRow && (
                      <span className="inline-flex items-center rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] uppercase tracking-wide text-primary">
                        Active row
                      </span>
                    )}
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] uppercase tracking-wide",
                        row.subclass
                          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                          : rowNeedsSubclass
                            ? "border-amber-400/50 bg-amber-500/10 text-amber-800 dark:text-amber-300"
                            : "border-border/70 bg-background/70 text-muted-foreground",
                      )}
                    >
                      {rowSubclassLabel}
                    </span>
                    <RowPendingIndicator
                      row={row}
                      rowSummary={rowClassSummary}
                      choicesMade={choicesMade}
                      isPrimary={isPrimary}
                    />
                  </div>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-[minmax(0,1fr)_8rem_auto] md:items-end">
                    <div>
                      <label
                        htmlFor={`class_name_${idx}`}
                        className="text-xs uppercase tracking-wide text-muted-foreground"
                      >
                        {isPrimary ? "Primary class" : `Class ${idx + 1}`}
                      </label>
                      <select
                        id={`class_name_${idx}`}
                        value={row.class_name}
                        onChange={(e) => {
                          const next = classAllocations.map((entry, i) =>
                            i === idx
                              ? {
                                  class_name: e.target.value,
                                  level: clampLevel(entry.level),
                                }
                              : entry,
                          );
                          writeAllocations(next);
                          setActiveClassRowIndex(idx);
                          setInspectedSpell(null);
                          setInfoTarget({ kind: "class" });
                        }}
                        className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      >
                        <option value="">Select class</option>
                        {allClassSummaries.map((cls) => {
                          // Dedupe: hide any class already used by ANOTHER
                          // row. The current row's own selection always
                          // remains available so the player can keep it.
                          const usedByOtherRow = classAllocations.some(
                            (entry, entryIdx) =>
                              entryIdx !== idx && entry.class_name === cls.id,
                          );
                          if (usedByOtherRow && cls.id !== row.class_name) {
                            return null;
                          }
                          // Primary row (idx 0) is never restricted by
                          // multiclass prereqs.
                          // For multiclass rows, disable any candidate whose
                          // prereqs the character doesn't meet — but never
                          // disable the option that is already selected for
                          // this row (you can't un-pick something via the
                          // disabled attribute).
                          if (isPrimary || cls.id === row.class_name) {
                            return (
                              <option key={cls.id} value={cls.id}>
                                {cls.name}{cls.source && cls.source !== "core-phb-2024" ? ` (${cls.source_title || cls.source})` : ""}
                              </option>
                            );
                          }
                          const check = multiclassPrereqByClass[cls.id];
                          if (!check || check.ok || check.abilities_unknown) {
                            return (
                              <option key={cls.id} value={cls.id}>
                                {cls.name}{cls.source && cls.source !== "core-phb-2024" ? ` (${cls.source_title || cls.source})` : ""}
                              </option>
                            );
                          }
                          const reasonParts = check.messages ?? check.missing ?? [];
                          return (
                            <option key={cls.id} value={cls.id} disabled>
                              {cls.name} — requires {reasonParts.join(", ")}
                            </option>
                          );
                        })}
                      </select>
                      {!isPrimary && abilitiesUnknown && (
                        <p className="mt-2 text-[11px] text-muted-foreground">
                          Ability scores not yet set — multiclass prerequisites
                          will be checked once you complete the Abilities step.
                        </p>
                      )}
                    </div>

                    <div>
                      <label
                        htmlFor={`class_level_${idx}`}
                        className="text-xs uppercase tracking-wide text-muted-foreground"
                      >
                        Level
                      </label>
                      <select
                        id={`class_level_${idx}`}
                        value={clampLevel(row.level)}
                        onChange={(e) => {
                          const next = classAllocations.map((entry, i) =>
                            i === idx
                              ? {
                                  ...entry,
                                  level: clampLevel(Number(e.target.value)),
                                }
                              : entry,
                          );
                          writeAllocations(next);
                        }}
                        className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      >
                        {Array.from({ length: 20 }, (_, i) => i + 1).map(
                          (lvl) => (
                            <option key={lvl} value={lvl}>
                              {lvl}
                            </option>
                          ),
                        )}
                      </select>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setActiveClassRowIndex(idx);
                          setInspectedSpell(null);
                          setInfoTarget({ kind: "class" });
                        }}
                        className={cn(
                          "inline-flex h-9 items-center rounded-md border px-3 text-xs font-medium transition-colors",
                          isActiveRow
                            ? "border-primary/40 bg-primary/10 text-primary"
                            : "border-border bg-background text-foreground hover:bg-secondary",
                        )}
                        aria-pressed={isActiveRow}
                      >
                        {isActiveRow ? "Active" : "Set active"}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const next = classAllocations.filter(
                            (_, i) => i !== idx,
                          );
                          writeAllocations(next);
                          const current = activeClassRowIndex;
                          if (current > idx) {
                            setActiveClassRowIndex(current - 1);
                          } else if (current === idx) {
                            setActiveClassRowIndex(Math.max(0, current - 1));
                          }
                          setInspectedSpell(null);
                          setInfoTarget({ kind: "class" });
                        }}
                        disabled={classAllocations.length <= 1}
                        className={cn(
                          "inline-flex h-9 w-9 items-center justify-center rounded-md border transition-colors",
                          classAllocations.length <= 1
                            ? "cursor-not-allowed border-border/60 text-muted-foreground"
                            : "border-border bg-background text-foreground hover:bg-secondary",
                        )}
                        aria-label={`Remove class row ${idx + 1}`}
                        title="Remove class"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() =>
                  writeAllocations([
                    ...classAllocations,
                    { class_name: "", level: 1 },
                  ])
                }
                disabled={abilitiesUnknown}
                title={
                  abilitiesUnknown
                    ? "Set your ability scores first — multiclassing requires a score of 13 in the primary ability of each class involved."
                    : undefined
                }
                className={cn(
                  "inline-flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground transition-colors hover:bg-secondary",
                  abilitiesUnknown &&
                    "cursor-not-allowed opacity-50 hover:bg-background",
                )}
              >
                <Plus className="h-4 w-4" />
                Add class
              </button>
              {abilitiesUnknown ? (
                <p className="text-xs text-muted-foreground">
                  Set your ability scores first — multiclassing requires a score
                  of 13 in the primary ability of each class involved.
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Select an active row to drive class details, subclass
                  selection, and class loadout picks.
                </p>
              )}
            </div>

            {multiclassPending && (
              <div className="rounded-lg border border-amber-400/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-300">
                Multiclass rows are saved independently. The detail panel and
                class refinement sections below always reflect the active row.
              </div>
            )}
          </div>
        </div>
      </section>

      {selectedClass && (previewQuery.isLoading || !previewData) && (
        <p className="text-xs text-muted-foreground">Loading class details…</p>
      )}

      {selectedClass && previewData && (
        <ClassDetail
          previewData={previewData}
          choicesMade={choicesMade}
          featPrerequisiteWarnings={serverFeatPrerequisiteWarnings}
          featDefinitions={generalFeatDefinitions}
          originFeatDefinitions={originFeatDefinitions}
          selectedClassSummary={detailClass}
          selectedSubclass={selectedSubclass}
          activeRowLabel={activeRowLabel}
          needsSubclass={needsSubclass}
          availableSubclasses={availableSubclasses}
          onInspectSpell={(spell) => {
            setInspectedSpell({
              ...spell,
              components: Array.isArray(spell.components)
                ? spell.components
                : spell.components
                  ? [spell.components]
                  : undefined,
            });
          }}
          inspectedSpellName={inspectedSpell?.name}
          onSelectSubclassInfo={(id) => {
            setInspectedSpell(null);
            setInfoTarget({ kind: "subclass", id });
          }}
          onSubclass={(v) => {
            if (classAllocations.length === 0) return;
            const next = classAllocations.map((row, idx) =>
              idx === activeRowIndex
                ? { ...row, ...(v ? { subclass: v } : {}) }
                : row,
            );
            if (!v) {
              const activeRow = next[activeRowIndex];
              if (activeRow) {
                next[activeRowIndex] = {
                  class_name: activeRow.class_name,
                  level: activeRow.level,
                };
              }
            }
            setInspectedSpell(null);
            writeAllocations(next);
          }}
        />
      )}

    </div>
  );
}

function SpellInfoPanel({
  spell,
  onBack,
}: {
  spell: SpellReference;
  onBack: () => void;
}) {
  const meta: Array<[string, string | undefined]> = [
    ["School", spell.school],
    ["Casting Time", spell.casting_time],
    ["Range", spell.range],
    [
      "Components",
      Array.isArray(spell.components) && spell.components.length > 0
        ? spell.components.join(", ")
        : undefined,
    ],
    ["Duration", spell.duration],
    ["Source", spell.source],
  ];

  return (
    <aside className="info-panel" aria-label="Spell details panel">
      <div className="info-panel-header">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="info-panel-kicker">Spell details</p>
            <h4 className="info-panel-title">{spell.name}</h4>
          </div>
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center rounded-md border border-border/70 bg-background px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            Back
          </button>
        </div>
      </div>
      <div className="info-panel-body">
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-border/70 bg-background px-2.5 py-1 text-[11px] uppercase tracking-wide text-muted-foreground">
            {spell.level === 0 ? "Cantrip" : `Level ${spell.level ?? "—"}`}
          </span>
          {spell.ritual === true && (
            <span className="rounded-full border border-blue-500/40 bg-blue-500/10 px-2.5 py-1 text-[11px] uppercase tracking-wide text-blue-700 dark:text-blue-300">
              Ritual
            </span>
          )}
        </div>

        {spell.concentration === true && (
          <div className="mt-3 rounded bg-amber-600/20 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-400 border border-amber-600/40">
            ✦ Concentration
          </div>
        )}

        {spell.description && (
          <p className="mt-4 text-sm text-muted-foreground">
            {spell.description}
          </p>
        )}

        <dl className="mt-4 space-y-3">
          {meta
            .filter(([, value]) => Boolean(value))
            .map(([label, value]) => (
              <div
                key={label}
                className="rounded-lg border border-border/70 bg-background/80 px-3 py-2"
              >
                <dt className="text-xs uppercase tracking-wide text-muted-foreground">
                  {label}
                </dt>
                <dd className="mt-1 text-sm font-medium text-foreground">
                  {value}
                </dd>
              </div>
            ))}
        </dl>
      </div>
    </aside>
  );
}

function ClassTraitsSection({
  fullClassData,
  isPrimaryRow,
}: {
  fullClassData: ClassDetail;
  isPrimaryRow: boolean;
}) {
  const rows: Array<{ label: string; value: ReactNode }> = [];
  let title: string;
  let notes: string | null = null;
  let sourceText: string | undefined;

  if (isPrimaryRow) {
    title = "Core Traits";
    rows.push({
      label: "Saving throws",
      value: formatProfList(fullClassData.saving_throw_proficiencies),
    });
    rows.push({
      label: "Armor training",
      value: formatProfList(fullClassData.armor_proficiencies),
    });
    rows.push({
      label: "Weapon training",
      value: formatProfList(fullClassData.weapon_proficiencies),
    });
    rows.push({
      label: "Tool training",
      value: formatProfList(fullClassData.tool_proficiencies ?? null),
    });
    const skillCount = fullClassData.skill_proficiencies_count;
    const skillOptions = fullClassData.skill_options ?? [];
    const skillValue =
      skillCount && skillCount > 0 && skillOptions.length > 0
        ? skillOptions.length === 1 && skillOptions[0].toLowerCase() === "any"
          ? `Choose ${skillCount} from any skill`
          : `Choose ${skillCount} from ${skillOptions.join(", ")}`
        : "—";
    rows.push({ label: "Skill proficiencies", value: skillValue });
  } else {
    title = "Multiclass Traits";
    const mc = fullClassData.multiclassing;
    if (!mc) {
      return (
        <div className="mt-6 rounded-lg border border-border/60 bg-background px-4 py-3">
          <p className="text-sm text-muted-foreground">
            Multiclass information is not available for this class.
          </p>
        </div>
      );
    }
    rows.push({ label: "Hit Die", value: `d${mc.hit_die_granted}` });
    rows.push({
      label: "Armor training",
      value: formatProfList(mc.armor_training),
    });
    rows.push({
      label: "Weapon training",
      value: formatProfList(mc.weapon_training),
    });
    rows.push({
      label: "Tool training",
      value: formatProfList(mc.tool_training),
    });
    rows.push({
      label: "Skill proficiencies",
      value: formatMulticlassSkillProfs(mc.skill_proficiencies),
    });
    rows.push({
      label: "Saving throws",
      value:
        mc.saving_throw_proficiencies.length > 0
          ? mc.saving_throw_proficiencies.join(", ")
          : "None",
    });
    notes = mc.notes;
    sourceText = mc.source_text;
  }

  return (
    <div className="mt-6">
      <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-background px-3 py-1 text-xs font-medium text-primary">
        <Shield className="h-3.5 w-3.5" />
        {title}
      </div>
      <div className="mt-2 grid grid-cols-1 gap-2">
        {rows.map((row) => (
          <div
            key={row.label}
            className="rounded-lg border border-border/70 bg-background/80 px-3 py-2"
          >
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              {row.label}
            </div>
            <div className="mt-1 text-sm font-medium text-foreground">
              {row.value}
            </div>
          </div>
        ))}
      </div>
      {notes && (
        <p className="mt-3 text-sm italic text-muted-foreground">{notes}</p>
      )}
      {sourceText && (
        <p className="mt-3 border-t border-border/60 pt-2 text-[11px] leading-relaxed text-muted-foreground">
          {sourceText}
        </p>
      )}
    </div>
  );
}

function ClassFeatureProgression({
  featuresByLevel,
  classData,
}: {
  featuresByLevel: Record<string, Record<string, unknown> | string[]>;
  classData?: Record<string, unknown>;
}) {
  // Reuse featureLevelEntries logic for robust feature extraction
  const levels = featureLevelEntries(featuresByLevel, classData);
  if (levels.length === 0) return null;
  return (
    <div className="mt-6">
      <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-background px-3 py-1 text-xs font-medium text-primary">
        <Sparkles className="h-3.5 w-3.5" />
        Feature progression
      </div>
      <div className="space-y-3 mt-2">
        {levels.map((entry) => (
          <div key={entry.level} className="info-panel-block">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
              <Shield className="h-3.5 w-3.5 text-primary" />
              Level {entry.level}
              <span className="text-[11px] normal-case tracking-normal text-muted-foreground">
                ({entry.features.length} feature
                {entry.features.length === 1 ? "" : "s"})
              </span>
            </div>
            <ul className="mt-2 space-y-3 text-sm text-foreground/90">
              {entry.features.map((feature) => (
                <li key={feature.name}>
                  <p className="font-semibold">{feature.name}</p>
                  {feature.description && (
                    <div className="mt-1 rounded-md border border-border/60 bg-background px-3 py-2">
                      <p className="mt-1 text-sm text-foreground/85">
                        {feature.description}
                      </p>
                      {feature.options && feature.options.length > 0 && (
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          Options: {feature.options.join(", ")}
                        </p>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Per-row indicator that surfaces "this class row has unsatisfied required
 * choices". Re-uses the same `/character/preview-step` endpoint the active
 * row uses, scoped to this row's class/level/subclass; react-query caches
 * the response by that triple to avoid hammering the API.
 *
 * A choice is considered satisfied when `choicesMade[choice_key]` is
 * non-empty. Subclass requirement is checked against the row's own
 * `subclass` (per-allocation) and the class's `subclass_selection_level`.
 *
 * Known limitation: nested-choice keys (skill_choices, tool_choices,
 * fighting_style, ...) live in a single shared `choicesMade` map, so in a
 * multiclass build both rows read the same value for those keys. This
 * mirrors the existing storage model and matches what the backend sees.
 */
function RowPendingIndicator({
  row,
  rowSummary,
  choicesMade,
  isPrimary,
}: {
  row: ClassAllocation;
  rowSummary: ClassSummary | undefined;
  choicesMade: ChoicesMade;
  isPrimary: boolean;
}) {
  const level = clampLevel(row.level);
  const subclass = row.subclass ?? "";
  const enabled = Boolean(row.class_name);

  const rowChoices: ChoicesMade = useMemo(
    () => ({
      ...choicesMade,
      class: row.class_name,
      level,
      ...(subclass ? { subclass } : {}),
    }),
    [choicesMade, row.class_name, level, subclass],
  );

  const previewQuery = useQuery({
    queryKey: [
      "character",
      "preview-step",
      "class-pending",
      row.class_name,
      level,
      subclass,
    ],
    queryFn: () => api.character.previewStep(rowChoices, "class"),
    enabled,
    staleTime: 60_000,
  });

  if (!enabled) return null;

  const data = previewQuery.data as Record<string, unknown> | undefined;
  const missing: string[] = [];

  // Subclass requirement applies to all rows.
  const subclassThreshold = rowSummary?.subclass_selection_level;
  if (
    !subclass &&
    typeof subclassThreshold === "number" &&
    level >= subclassThreshold
  ) {
    missing.push("subclass");
  }

  if (data) {
    const nested =
      (data["nested_choices"] as PreviewChoice[] | undefined) ?? [];
    for (const choice of nested) {
      // Skip conditional choices whose parent condition is not met
      if (choice.depends_on) {
        const variants = parentKeyVariants(choice.depends_on);
        const parent = variants.reduce<string | string[] | undefined>(
          (acc, v) => acc ?? (choicesMade[v] as string | string[] | undefined),
          undefined,
        );
        const met =
          choice.depends_on_value === undefined
            ? Boolean(parent)
            : Array.isArray(parent)
              ? parent.includes(choice.depends_on_value)
              : parent === choice.depends_on_value;
        if (!met) continue;
      }

      const key = getEffectiveChoiceKey(choice);
      if (!key) continue;
      const value = choicesMade[key] ?? (choice.choice_key ? choicesMade[choice.choice_key] : undefined);
      const satisfied = Array.isArray(value)
        ? value.length > 0
        : typeof value === "string"
          ? value.length > 0
          : value !== undefined && value !== null && value !== "";
      if (!satisfied) missing.push(key);
    }
  }

  if (missing.length === 0) return null;

  const labels = missing.map((m) => m.replace(/_/g, " "));
  const title = `${missing.length} choice${missing.length === 1 ? "" : "s"} missing: ${labels.join(", ")}`;

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border border-amber-400/50 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:text-amber-300"
      title={title}
      aria-label={title}
      data-row-primary={isPrimary || undefined}
    >
      <span className="h-2 w-2 rounded-full bg-amber-500" aria-hidden />
      {missing.length} pending
    </span>
  );
}

function ClassInfoPanel({
  infoTarget,
  detailClass,
  fullClassData,
  isPrimaryRow,
  selectedClass,
  classLoading,
  showClassFeatureFallback,
  needsSubclass,
  selectedSubclass,
  activeSubclassName,
  activeSubclassDetail,
  activeFeatureLevels,
  subclassLoading,
}: {
  infoTarget: ClassInfoTarget;
  detailClass?: any;
  fullClassData?: ClassDetail;
  isPrimaryRow: boolean;
  selectedClass: string;
  classLoading: boolean;
  showClassFeatureFallback: boolean;
  needsSubclass: boolean;
  selectedSubclass: string;
  activeSubclassName?: string;
  activeSubclassDetail?: SubclassDetail;
  activeFeatureLevels: Array<{
    level: string;
    features: SubclassFeatureEntry[];
  }>;
  subclassLoading: boolean;
}) {
  const showSubclassPanel = infoTarget.kind === "subclass" && needsSubclass;

  return (
    <aside
      className="info-panel"
      aria-label={
        showSubclassPanel ? "Subclass details panel" : "Class details panel"
      }
    >
      {showSubclassPanel ? (
        <>
          <div className="info-panel-header">
            <p className="info-panel-kicker">Informational panel</p>
            <h4 className="info-panel-title">
              {activeSubclassName ?? "Select a subclass"}
            </h4>
          </div>
          <div className="info-panel-body">
            {!selectedSubclass && (
              <p className="mt-2 text-xs text-muted-foreground">
                Previewing subclass details. Select a subclass card to lock your
                choice.
              </p>
            )}
            {subclassLoading && (
              <p className="mt-3 text-sm text-muted-foreground">
                Loading subclass details…
              </p>
            )}
            {activeSubclassDetail?.description && (
              <p className="mt-3 text-sm text-muted-foreground">
                {activeSubclassDetail.description}
              </p>
            )}
            {activeFeatureLevels.length > 0 ? (
              <div className="mt-4 space-y-3">
                <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-background px-3 py-1 text-xs font-medium text-primary">
                  <Sparkles className="h-3.5 w-3.5" />
                  Feature progression
                </div>
                <div className="space-y-3">
                  {activeFeatureLevels.map((entry) => (
                    <div key={entry.level} className="info-panel-block">
                      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
                        <Shield className="h-3.5 w-3.5 text-primary" />
                        Level {entry.level}
                        <span className="text-[11px] normal-case tracking-normal text-muted-foreground">
                          ({entry.features.length} feature
                          {entry.features.length === 1 ? "" : "s"})
                        </span>
                      </div>
                      <ul className="mt-2 space-y-3 text-sm text-foreground/90">
                        {entry.features.map((feature) => (
                          <li key={feature.name}>
                            <p className="font-semibold">{feature.name}</p>
                            {feature.description && (
                              <div className="mt-1 rounded-md border border-border/60 bg-background px-3 py-2">
                                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                                  Feature details
                                </p>
                                <p className="mt-1 text-sm text-foreground/85">
                                  {feature.description}
                                </p>
                              </div>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              !subclassLoading && (
                <p className="mt-4 text-sm text-muted-foreground">
                  No additional subclass detail is available from the current
                  catalog payload.
                </p>
              )
            )}
          </div>
        </>
      ) : (
        <>
          <div className="info-panel-header">
            <p className="info-panel-kicker">Informational panel</p>
            <h4 className="info-panel-title">
              {detailClass?.name ?? "Select a class"}
            </h4>
          </div>
          <div className="info-panel-body">
            {!detailClass && (
              <p className="mt-2 text-xs text-muted-foreground">
                Previewing class details. Select a class card to view its full
                feature progression.
              </p>
            )}
            {detailClass?.description && (
              <p className="mt-3 text-sm text-muted-foreground">
                {detailClass.description}
              </p>
            )}
            <div className="mt-4 grid grid-cols-1 gap-2">
              {detailClass && (
                <>
                  <div className="rounded-lg border border-border/70 bg-background/80 px-3 py-2">
                    <div className="text-xs uppercase tracking-wide text-muted-foreground">
                      Primary ability
                    </div>
                    <div className="mt-1 font-medium text-foreground">
                      {Array.isArray(detailClass.primary_ability)
                        ? detailClass.primary_ability.join(" / ")
                        : detailClass.primary_ability}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/70 bg-background/80 px-3 py-2">
                    <div className="text-xs uppercase tracking-wide text-muted-foreground">
                      Hit Die
                    </div>
                    <div className="mt-1 font-medium text-foreground">
                      d{detailClass.hit_die}
                    </div>
                  </div>
                </>
              )}
            </div>
            {detailClass && fullClassData && (
              <ClassTraitsSection
                fullClassData={fullClassData}
                isPrimaryRow={isPrimaryRow}
              />
            )}
            {selectedClass && classLoading && (
              <div className="mt-6">
                <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-background px-3 py-1 text-xs font-medium text-primary">
                  <Sparkles className="h-3.5 w-3.5 animate-pulse" />
                  Loading feature progression…
                </div>
              </div>
            )}
            {detailClass?.features_by_level && (
              <ClassFeatureProgression
                featuresByLevel={
                  detailClass.features_by_level as Record<
                    string,
                    Record<string, unknown> | string[]
                  >
                }
                classData={fullClassData as unknown as Record<string, unknown>}
              />
            )}
            {showClassFeatureFallback && (
              <div className="mt-6 rounded-lg border border-border/60 bg-background px-4 py-3">
                <p className="text-sm text-muted-foreground">
                  Feature progression details are being prepared…
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </aside>
  );
}

function ClassDetail({
  previewData,
  choicesMade,
  featPrerequisiteWarnings,
  featDefinitions,
  originFeatDefinitions,
  selectedClassSummary,
  selectedSubclass,
  activeRowLabel,
  needsSubclass,
  availableSubclasses,
  onSelectSubclassInfo,
  onSubclass,
  onInspectSpell,
  inspectedSpellName,
}: {
  previewData: Record<string, unknown>;
  choicesMade: Record<string, unknown>;
  featPrerequisiteWarnings: ClassFeatPrerequisiteWarning[];
  featDefinitions: Record<string, FeatDefinition>;
  originFeatDefinitions: Record<string, FeatDefinition>;
  selectedClassSummary?: {
    name: string;
    subclass_selection_level: number;
  };
  selectedSubclass: string;
  activeRowLabel: number;
  needsSubclass: boolean;
  availableSubclasses: SubclassSummary[];
  onSelectSubclassInfo: (id: string) => void;
  onSubclass: (v: string) => void;
  onInspectSpell: (spell: SpellDefinition) => void;
  inspectedSpellName?: string;
}) {
  const nestedChoices =
    (previewData["nested_choices"] as PreviewChoice[] | undefined) ?? [];
  const asiChoiceGroups = useMemo(() => {
    const grouped = new Map<
      string,
      {
        slotKey: string;
        slotLevel: number;
        asiOptionChoice?: PreviewChoice;
        plusTwoChoice?: PreviewChoice;
        plusOneChoice?: PreviewChoice;
      }
    >();
    for (const choice of nestedChoices) {
      const key = getEffectiveChoiceKey(choice);
      const match = key.match(CLASS_FEAT_ASI_OPTION_KEY_RE);
      if (!match) continue;
      const slotKey = match[1];
      const kind = match[2];
      const slotLevel = Number(slotKey.replace("class_feat_", "")) || 0;
      const current = grouped.get(slotKey) ?? { slotKey, slotLevel };
      if (kind === "asi_option") current.asiOptionChoice = choice;
      if (kind === "ability_plus_2") current.plusTwoChoice = choice;
      if (kind === "abilities_plus_1") current.plusOneChoice = choice;
      grouped.set(slotKey, current);
    }
    return Array.from(grouped.values())
      .filter((group) => Boolean(group.asiOptionChoice))
      .sort((a, b) => a.slotLevel - b.slotLevel);
  }, [nestedChoices]);
  const asiChoiceKeys = useMemo(() => {
    const keys = new Set<string>();
    for (const group of asiChoiceGroups) {
      keys.add(`${group.slotKey}_asi_option`);
      keys.add(`${group.slotKey}_ability_plus_2`);
      keys.add(`${group.slotKey}_abilities_plus_1`);
    }
    return keys;
  }, [asiChoiceGroups]);
  const displayNestedChoices = nestedChoices.filter((choice) => {
    const key = getEffectiveChoiceKey(choice);
    return !asiChoiceKeys.has(key);
  });
  const visibleNestedChoices = useMemo(() => {
    return displayNestedChoices.filter((choice) => {
      const key = getEffectiveChoiceKey(choice);

      // Feat sub-choices are rendered inside FeatDropdownPicker — skip here
      if (key.startsWith("feat_") && !isClassFeatChoiceKey(key)) return false;

      // ASI sub-choices (class_feat_N_asi_option etc.) are rendered inside
      // ClassFeatAsiPicker which is inlined after FeatDropdownPicker — skip here
      if (asiChoiceKeys.has(key)) return false;

      // Feat sub-choices keyed as class_feat_N_<name> (e.g. class_feat_4_ability)
      // are rendered inside FeatDropdownPicker — skip them at the top level
      if (!isClassFeatChoiceKey(key) && /^class_feat_\d+_/.test(key)) return false;

      if (!choice.depends_on) return true;

      const variants = parentKeyVariants(choice.depends_on);
      const parent = variants.map((k) => choicesMade[k]).find((v) => v !== undefined);
      return choice.depends_on_value == null
        ? Boolean(parent)
        : Array.isArray(parent)
          ? parent.includes(choice.depends_on_value)
          : parent === choice.depends_on_value;
    });
  }, [asiChoiceKeys, choicesMade, displayNestedChoices]);
  const groupedChoiceCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const choice of visibleNestedChoices) {
      const groupName = groupedFeatureName(choice);
      if (!groupName) continue;
      counts.set(groupName, (counts.get(groupName) ?? 0) + 1);
    }
    return counts;
  }, [visibleNestedChoices]);
  const groupedChoiceBlocks = useMemo(() => {
    const blocks: Array<{ groupName?: string; choices: PreviewChoice[] }> = [];
    const groupedNames = new Set<string>();

    for (const choice of visibleNestedChoices) {
      const groupName = groupedFeatureName(choice);
      const shouldGroup =
        Boolean(groupName) && (groupedChoiceCounts.get(groupName ?? "") ?? 0) > 1;

      if (groupName && shouldGroup) {
        if (groupedNames.has(groupName)) continue;
        groupedNames.add(groupName);
        blocks.push({
          groupName,
          choices: visibleNestedChoices.filter(
            (candidate) => groupedFeatureName(candidate) === groupName,
          ),
        });
        continue;
      }

      blocks.push({ choices: [choice] });
    }

    return blocks;
  }, [groupedChoiceCounts, visibleNestedChoices]);
  const renderChoiceControl = (
    choice: PreviewChoice,
    idx: number,
    overrides?: { title?: string; description?: string },
  ): ReactNode => {
    const key = getEffectiveChoiceKey(choice) || `class_choice_${idx}`;

    if (isClassFeatChoiceKey(key)) {
      const slotLevel = Number(key.replace("class_feat_", "")) || 0;
      const selectedFeat =
        typeof choicesMade[key] === "string" ? String(choicesMade[key]) : "";
      const subChoicesForSlot = selectedFeat
        ? displayNestedChoices.filter((sc) => {
            const scKey =
              sc.choice_key ?? sc.feature_name ?? sc.name ?? "";
            return scKey.startsWith(`${key}_`) && !asiChoiceKeys.has(scKey);
          })
        : [];
      const warningsForFeat = featPrerequisiteWarnings
        .filter((w) => w.feat_name === selectedFeat || w.choice_key === key)
        .flatMap((w) => w.messages);
      const asiGroup = asiChoiceGroups.find((g) => g.slotKey === key);
      return (
        <FeatDropdownPicker
          key={key}
          choiceKey={key}
          slotLevel={slotLevel}
          title={overrides?.title ?? choice.title ?? `Feat (Level ${slotLevel})`}
          description={overrides?.description ?? choice.description}
          generalFeats={featDefinitions}
          originFeats={originFeatDefinitions}
          featSubChoices={subChoicesForSlot}
          choicesMade={choicesMade}
          prerequisiteWarning={warningsForFeat}
          asiChoiceGroup={asiGroup}
          onInspectSpell={onInspectSpell}
          inspectedSpellName={inspectedSpellName}
        />
      );
    }

    const opts = (choice.options ?? []) as Array<unknown>;
    if (opts.length === 0) return null;
    if (isSpellLikeChoice(choice, opts)) {
      return (
        <SpellChoiceList
          key={key}
          choiceKey={key}
          title={overrides?.title ?? choice.title ?? choice.name ?? key}
          description={overrides?.description ?? choice.description}
          options={opts}
          count={choice.count ?? 1}
          onInspectSpell={onInspectSpell}
          inspectedSpellName={inspectedSpellName}
        />
      );
    }
    const grantedLanguages =
      choice.choice_category === "languages"
        ? ((previewData["granted_languages"] as string[] | undefined) ?? [])
        : undefined;
    return (
      <ChoiceList
        key={key}
        choiceKey={key}
        title={overrides?.title ?? choice.title ?? choice.name ?? key}
        description={overrides?.description ?? choice.description}
        options={opts as Array<string | { name?: string }>}
        optionDescriptions={choice.option_descriptions}
        count={choice.count ?? 1}
        disabledOptions={grantedLanguages}
        disabledReason="Already known"
      />
    );
  };

  return (
    <div className="space-y-6">
      {needsSubclass && (
        <section className="rounded-xl border border-border/70 bg-card/60 p-5 shadow-sm sm:p-6">
          <div className="mb-5 flex items-start gap-3">
            <div className="rounded-full bg-primary/10 p-2 text-primary">
              <Layers3 className="h-4 w-4" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-display text-xl text-primary font-bold">
                  Choose a subclass
                </h3>
                <span className="rounded-full border border-border/70 bg-background/70 px-2.5 py-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                  Row {activeRowLabel}
                </span>
                {selectedClassSummary && (
                  <span className="rounded-full border border-border/70 bg-background/70 px-2.5 py-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                    Available at level{" "}
                    {selectedClassSummary.subclass_selection_level}
                  </span>
                )}
              </div>
              <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
                Scan the themes first, then open the detail panel for a quick
                look at the feature progression before you lock one in.
              </p>
            </div>
          </div>

          <div className={cn("grid grid-cols-1 gap-3 lg:items-start")}>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 items-start">
              {availableSubclasses.map((sub) => {
                const isSelected = selectedSubclass === sub.id;
                return (
                  <button
                    key={sub.id}
                    type="button"
                    onClick={() => {
                      onSubclass(sub.id);
                      onSelectSubclassInfo(sub.id);
                    }}
                    aria-pressed={isSelected}
                    className={cn(
                      "rounded-xl border p-4 text-left transition-all duration-200",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                      isSelected
                        ? "border-primary bg-muted/60 shadow-sm ring-1 ring-primary/20"
                        : "border-border/80 bg-background/80 hover:border-primary/40 hover:bg-secondary/50",
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-display text-lg text-primary font-semibold">
                          {sub.name}
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px] uppercase tracking-wide text-muted-foreground">
                          {sub.source && sub.source !== "core-phb-2024" && (
                            <span className="rounded-full border border-primary/40 bg-primary/10 text-primary font-medium px-2 py-1">
                              {sub.source_title || sub.source}
                            </span>
                          )}
                          <span className="rounded-full border border-border/70 bg-background/70 px-2 py-1">
                            Subclass path
                          </span>
                          {(sub.level_3_feature_names ?? []).length > 0 && (
                            <span className="rounded-full border border-border/70 bg-background/70 px-2 py-1">
                              {(sub.level_3_feature_names ?? []).length} early
                              features
                            </span>
                          )}
                        </div>
                      </div>
                      <span
                        className={cn(
                          "inline-flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border",
                          isSelected
                            ? "border-primary bg-background text-primary"
                            : "border-border bg-background text-transparent",
                        )}
                      >
                        <Check className="h-3.5 w-3.5" />
                      </span>
                    </div>
                    {sub.description && (
                      <div className="mt-3 text-sm text-muted-foreground line-clamp-4">
                        {sub.description}
                      </div>
                    )}
                    {(sub.level_3_feature_names ?? []).length > 0 && (
                      <div className="mt-4 border-t border-border/70 pt-3">
                        <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                          Signature features
                        </div>
                        <ul className="mt-2 space-y-1 text-sm text-foreground/90">
                          {sub.level_3_feature_names?.map((featureName) => (
                            <li key={featureName}>• {featureName}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="mt-4 flex items-center justify-between text-xs font-medium text-muted-foreground">
                      <span>
                        {isSelected
                          ? "Selected subclass"
                          : "Click card to select"}
                      </span>
                      <span className="inline-flex items-center gap-1 text-primary/80">
                        {isSelected
                          ? "Details on panel"
                          : "Select to view details"}
                        <ChevronRight className="h-3.5 w-3.5" />
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {nestedChoices.length > 0 && (
        <section className="rounded-xl border border-border/70 bg-card/50 p-5 shadow-sm sm:p-6">
          <div className="mb-5 flex items-start gap-3">
            <div className="rounded-full bg-primary/10 p-2 text-primary">
              <BookOpen className="h-4 w-4" />
            </div>
            <div>
              <h3 className="font-display text-xl text-primary font-bold">
                Class choices
              </h3>
              <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
                These selections refine the class you picked above, such as
                spell lists, fighting styles, or other feature-specific choices.
              </p>
            </div>
          </div>

          {featPrerequisiteWarnings.length > 0 && (
            <div className="mb-4 rounded-lg border border-amber-400/40 bg-amber-500/10 px-4 py-3">
              <div className="flex items-start gap-2 text-amber-800 dark:text-amber-300">
                <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <div className="text-sm">
                  <p className="font-semibold">Prerequisite warning</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4">
                    {featPrerequisiteWarnings.map((warning) =>
                      warning.messages.map((message) => (
                        <li key={`${warning.feat_name ?? warning.choice_key}-${message}`}>
                          <strong>{warning.feat_name ?? "Selected feat"}</strong>: {message}
                        </li>
                      )),
                    )}
                  </ul>
                  <p className="mt-2 text-xs">
                    You can still proceed, but verify your final scores before
                    play.
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            {groupedChoiceBlocks.map((block, idx) => {
              if (block.groupName) {
                const groupName = block.groupName;
                return (
                  <section
                    key={groupName}
                    className="rounded-xl border border-border/70 bg-card/70 p-4 shadow-sm sm:p-5"
                  >
                    <div className="mb-4 space-y-2">
                      <h4 className="text-base font-semibold text-foreground">
                        {groupName.replace(/^subclass_/, "")}
                      </h4>
                      {block.choices[0]?.description && (
                        <p className="text-sm text-muted-foreground whitespace-pre-line">
                          {block.choices[0].description}
                        </p>
                      )}
                    </div>
                    <div className="space-y-3">
                      {block.choices.map((groupedChoice, groupedIdx) =>
                        renderChoiceControl(groupedChoice, idx + groupedIdx, {
                          title: groupedChoiceTitle(groupedChoice, groupName),
                          description: undefined,
                        }),
                      )}
                    </div>
                  </section>
                );
              }

              return renderChoiceControl(block.choices[0], idx);
            })}
          </div>
        </section>
      )}

      <ClassAdvancedChoices
        choicesForDerived={choicesMade}
        inspectedSpellName={inspectedSpellName}
        onInspectSpell={(spell) => {
          onInspectSpell({
            name: spell.name,
            level: spell.level ?? 0,
            school: spell.school ?? "",
            casting_time: spell.casting_time ?? "",
            range: spell.range ?? "",
            duration: spell.duration ?? "",
            components: spell.components ?? [],
            description: spell.description ?? "",
            source: spell.source,
          });
        }}
      />
    </div>
  );
}
