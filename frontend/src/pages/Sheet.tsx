import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { api, type ChoicesMade } from "@/lib/api";
import { useCharacterStore } from "@/store/characterStore";
import { useRosterStore } from "@/store/rosterStore";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { useBugReportUrl } from "@/hooks/useBugReportUrl";
import { cn } from "@/lib/utils";
import {
  BookmarkCheck,
  Download,
  Save,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Swords,
  Shield,
  Scroll,
  BookOpen,
  Backpack,
  ChevronsUpDown,
  Printer,
  Flame,
  Music,
  PawPrint,
  Zap,
} from "lucide-react";
import { PrepareSpellsDialog } from "@/components/sheet/PrepareSpellsDialog";
import { ChooseMasteriesDialog } from "@/components/sheet/ChooseMasteriesDialog";
import { InvocationsDialog } from "@/components/sheet/InvocationsDialog";
import { ReplicateMagicItemDialog } from "@/components/sheet/ReplicateMagicItemDialog";
import { LevelUpDialog } from "@/components/sheet/LevelUpDialog";
import { AspectOfTheWildsDialog } from "@/components/sheet/AspectOfTheWildsDialog";
import { InventorySection } from "@/components/sheet/InventorySection";

// `to_character()` is too sprawling to fully type at the boundary.
// We treat it as a loose record and narrow only where we read.
type Char = Record<string, unknown>;

function num(v: unknown): number | undefined {
  return typeof v === "number" ? v : undefined;
}
function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}
function arr<T = unknown>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}
function rec(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : {};
}
function signed(v: number | undefined): string {
  if (v === undefined) return "—";
  return v >= 0 ? `+${v}` : String(v);
}
const SLOT_LEVEL_ORDINALS = [
  "Cantrip",
  "1st",
  "2nd",
  "3rd",
  "4th",
  "5th",
  "6th",
  "7th",
  "8th",
  "9th",
];

function slotLevelOrdinal(level: string): string {
  const numeric = Number(level.match(/\d+/)?.[0]);
  if (!Number.isFinite(numeric)) return level;
  return SLOT_LEVEL_ORDINALS[numeric] ?? `${numeric}th`;
}

function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function safeFilename(name: string): string {
  return (
    name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9._-]+/g, "-")
      .replace(/^-+|-+$/g, "") || "character"
  );
}

export function Sheet() {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const saveCurrent = useRosterStore((s) => s.saveCurrent);
  const buildQuery = useQuery({
    queryKey: ["character", "build", choicesMade],
    queryFn: () => api.character.build(choicesMade),
    retry: false,
    placeholderData: keepPreviousData,
  });

  const [spellDialogOpen, setSpellDialogOpen] = useState(false);
  const [masteryDialogOpen, setMasteryDialogOpen] = useState(false);
  const [invocationDialogOpen, setInvocationDialogOpen] = useState(false);
  const [replicateDialogOpen, setReplicateDialogOpen] = useState(false);
  const [aspectDialogOpen, setAspectDialogOpen] = useState(false);
  const [levelUpOpen, setLevelUpOpen] = useState(false);
  const [levelUpFlash, setLevelUpFlash] = useState<string | null>(null);
  const [showSpellPrompt, setShowSpellPrompt] = useState(false);
  const [savedFlash, setSavedFlash] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [exportFlash, setExportFlash] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  // Section collapse state:
  // On mobile (< 768px), default to having only combat open to eliminate endless scrolling.
  // On desktop (>= 768px), default to having all sections open.
  const [openSections, setOpenSections] = useState<Record<string, boolean>>(() => {
    const isMobile = typeof window !== "undefined" && window.innerWidth < 768;
    return {
      combat: true,
      abilities: !isMobile,
      proficiencies: !isMobile,
      magic: !isMobile,
      features: !isMobile,
      inventory: !isMobile,
    };
  });

  function toggleSection(sec: string) {
    setOpenSections((prev) => ({ ...prev, [sec]: !prev[sec] }));
  }

  const allOpen = Object.values(openSections).every(Boolean);

  function toggleAllSections() {
    const next = !allOpen;
    setOpenSections({
      combat: next,
      abilities: next,
      proficiencies: next,
      magic: next,
      features: next,
      inventory: next,
    });
  }

  function scrollToSection(sec: string) {
    setOpenSections((prev) => ({ ...prev, [sec]: true }));
    setTimeout(() => {
      const el = document.getElementById(`section-${sec}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 50);
  }

  const spellDerived = useQuery({
    queryKey: [
      "character",
      "derived",
      "spell_management",
      choicesMade.class,
      choicesMade.level,
      choicesMade.subclass,
      choicesMade.classes,
    ],
    queryFn: () => api.character.derived(choicesMade, "spell_management"),
    enabled:
      Array.isArray(choicesMade["classes"]) &&
      (choicesMade["classes"] as unknown[]).length > 0,
    retry: false,
  });
  const masteryDerived = useQuery({
    queryKey: [
      "character",
      "derived",
      "mastery_management",
      choicesMade.class,
      choicesMade.level,
      choicesMade.subclass,
      choicesMade.classes,
    ],
    queryFn: () => api.character.derived(choicesMade, "mastery_management"),
    enabled:
      Array.isArray(choicesMade["classes"]) &&
      (choicesMade["classes"] as unknown[]).length > 0,
    retry: false,
  });
  const invocationDerived = useQuery({
    queryKey: [
      "character",
      "derived",
      "invocation_management",
      choicesMade.class,
      choicesMade.level,
      choicesMade.subclass,
      choicesMade.classes,
      choicesMade.eldritch_invocation_selections,
    ],
    queryFn: () => api.character.derived(choicesMade, "invocation_management"),
    enabled: Boolean(
      choicesMade.class === "Warlock" ||
        (Array.isArray(choicesMade["classes"]) &&
          (choicesMade["classes"] as Array<{ class_name?: string }>).some(
            (c) => c?.class_name === "Warlock",
          )),
    ),
    retry: false,
  });

  const replicateDerived = useQuery({
    queryKey: [
      "character", "derived", "replicate_magic_item_management",
      choicesMade.class,
      choicesMade.level,
      choicesMade.subclass,
      choicesMade.classes,
      choicesMade.artificer_replicate_plans,
      choicesMade.artificer_active_replications,
    ],
    queryFn: () => api.character.derived(choicesMade, "replicate_magic_item_management"),
    enabled: Boolean(
      choicesMade.class === "Artificer" ||
        (Array.isArray(choicesMade["classes"]) &&
          (choicesMade["classes"] as Array<{ class_name?: string }>).some(
            (c) => c?.class_name === "Artificer",
          )),
    ),
    retry: false,
  });

  const spellApplicable = spellDerived.data?.applicable === true;
  const masteryApplicable = masteryDerived.data?.applicable === true;
  const invocationApplicable = invocationDerived.data?.applicable === true;
  const replicateApplicable = replicateDerived.data?.applicable === true;
  const repData =
    replicateDerived.data?.data != null &&
    typeof replicateDerived.data.data === "object"
      ? (replicateDerived.data.data as Record<string, unknown>)
      : null;
  const activeReplicationsList: Array<{
    name: string;
    level?: number;
    rarity?: string;
    attunement?: boolean;
    description?: string;
    type?: string;
  }> = Array.isArray(repData?.active_items_details)
    ? (repData!.active_items_details as Array<{
        name: string;
        level?: number;
        rarity?: string;
        attunement?: boolean;
        description?: string;
        type?: string;
      }>)
    : [];
  const maxActiveReplications = typeof repData?.max_active === "number" ? repData.max_active : 0;
  const knownPlansCount = Array.isArray(repData?.known_plans) ? repData.known_plans.length : 0;
  const invData =
    invocationDerived.data?.data != null &&
    typeof invocationDerived.data.data === "object"
      ? (invocationDerived.data.data as Record<string, unknown>)
      : null;
  const currentInvocations: string[] = Array.isArray(
    invData?.current_invocations,
  )
    ? (invData!.current_invocations as string[])
    : [];
  // Build a lookup map from name → description using available_invocations
  const invocationDescMap = new Map<string, string>(
    (Array.isArray(invData?.available_invocations)
      ? (invData!.available_invocations as Record<string, unknown>[])
      : []
    )
      .filter((v) => typeof v === "object" && v !== null)
      .flatMap((v) => {
        const name = String(v.name ?? "");
        const desc = String(v.description ?? "");
        return name.length > 0 ? [[name, desc] as [string, string]] : [];
      }),
  );
  const invocationsList: Array<{ name: string; description?: string }> =
    Array.isArray(invData?.invocations) && (invData!.invocations as unknown[]).length > 0
      ? (invData!.invocations as Array<{ name: string; description?: string }>)
      : currentInvocations.map((inv) => ({
          name: inv,
          description: invocationDescMap.get(inv),
        }));

  if (buildQuery.isLoading) {
    return (
      <Shell>
        <p className="text-muted-foreground">Building character…</p>
      </Shell>
    );
  }
  if (buildQuery.error) {
    return (
      <Shell>
        <p className="text-destructive">
          Cannot build character yet: {String(buildQuery.error)}
        </p>
        <p className="mt-3 text-sm text-muted-foreground">
          Finish the wizard first.{" "}
          <Link to="/wizard" className="text-primary underline">
            Go to wizard →
          </Link>
        </p>
      </Shell>
    );
  }

  const c = (buildQuery.data ?? {}) as Char;
  const hasSpells =
    spellApplicable ||
    Object.keys(rec(c.spells_by_level)).length > 0 ||
    Object.keys(rec(c.spell_slots)).length > 0;
  const currentLevel =
    num(c.level) ??
    (typeof choicesMade.level === "number" ? choicesMade.level : 1);
  const canLevelUp = currentLevel < 20;

  const barbarianStats = rec(c.barbarian_stats);
  const isWildHeartBarbarian =
    barbarianStats.has_rage === true &&
    str(barbarianStats.subclass) === "Path of the Wild Heart" &&
    (num(barbarianStats.barbarian_level) ?? 0) >= 6;
  const currentAspect =
    str(rec(rec(barbarianStats.subclass_resources).aspect_of_the_wilds).choice) ??
    (typeof choicesMade.aspect_of_the_wilds === "string"
      ? choicesMade.aspect_of_the_wilds
      : typeof choicesMade.subclass_aspect_of_the_wilds === "string"
        ? choicesMade.subclass_aspect_of_the_wilds
        : undefined);

  const defaultName =
    (typeof choicesMade.character_name === "string" &&
    choicesMade.character_name.trim().length > 0
      ? choicesMade.character_name
      : undefined) ??
    str(c.name) ??
    str(c.character_name) ??
    "Unnamed";

  function handleSaveToRoster() {
    setSaveError(null);
    setExportFlash(null);
    const characterName =
      typeof choicesMade.character_name === "string"
        ? choicesMade.character_name
        : defaultName;
    saveCurrent(choicesMade, characterName)
      .then((entry) => {
        setSavedFlash(`Saved "${entry.name}" to your roster.`);
        window.setTimeout(() => setSavedFlash(null), 3000);
      })
      .catch((err: unknown) => {
        setSaveError(
          err instanceof Error ? err.message : "Failed to save character.",
        );
      });
  }

  function handleDownloadChoices() {
    setExportError(null);
    setSaveError(null);
    try {
      downloadJson(`${safeFilename(defaultName)}-choices.json`, {
        version: 1,
        exported_at: new Date().toISOString(),
        choices_made: choicesMade,
      });
      setExportFlash("Downloaded character choices JSON.");
      window.setTimeout(() => setExportFlash(null), 3000);
    } catch (err: unknown) {
      setExportError(
        err instanceof Error ? err.message : "Failed to download character.",
      );
    }
  }

  return (
    <Shell
      debugData={c}
      headerActions={
        <>
          <Button
            size="sm"
            onClick={() => setLevelUpOpen(true)}
            disabled={!canLevelUp}
            className="bg-amber-600 hover:bg-amber-700 text-white font-semibold shadow-xs"
          >
            <Sparkles className="w-3.5 h-3.5 mr-1.5" />
            Level Up
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/sheet/pdf">
              <Printer className="w-3.5 h-3.5 mr-1.5" />
              Print Sheet
            </Link>
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownloadChoices}>
            <Download className="w-3 h-3 mr-1" />
            Download Choices
          </Button>
          <Button variant="outline" size="sm" onClick={handleSaveToRoster}>
            {savedFlash ? (
              <>
                <BookmarkCheck className="w-3 h-3 mr-1 text-green-600" />
                Saved!
              </>
            ) : (
              <>
                <Save className="w-3 h-3 mr-1" />
                Save to Roster
              </>
            )}
          </Button>
        </>
      }
      actionFeedback={
        <>
          {levelUpFlash && (
            <div className="flex items-center gap-2 text-xs text-amber-700 dark:text-amber-300 font-medium bg-amber-500/10 px-3 py-1.5 rounded-md border border-amber-500/30 animate-in fade-in">
              <Sparkles className="w-3.5 h-3.5 shrink-0" />
              <span>{levelUpFlash}</span>
              {showSpellPrompt && (
                <Button
                  variant="link"
                  size="sm"
                  className="h-auto p-0 text-xs text-primary underline font-semibold ml-1"
                  onClick={() => {
                    setShowSpellPrompt(false);
                    setSpellDialogOpen(true);
                  }}
                >
                  Prepare Spells →
                </Button>
              )}
            </div>
          )}
          {saveError && <p className="text-xs text-destructive">{saveError}</p>}
          {savedFlash && <p className="text-xs text-emerald-500">{savedFlash}</p>}
          {exportError && (
            <p className="text-xs text-destructive">{exportError}</p>
          )}
          {exportFlash && (
            <p className="text-xs text-emerald-500">{exportFlash}</p>
          )}
        </>
      }
    >
      <Header
        c={c}
        onLevelUp={() => setLevelUpOpen(true)}
        canLevelUp={canLevelUp}
      />
      <CoreStats c={c} />
      {/* ── Section Jump & Expand Controls ── */}
      <div className="mt-6 mb-4 flex flex-wrap items-center justify-between gap-2 p-2 rounded-lg border border-border/60 bg-card/40">
        <div className="flex flex-wrap items-center gap-1.5">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleAllSections}
            className="h-8 px-2.5 text-xs font-medium gap-1.5"
          >
            <ChevronsUpDown className="h-3.5 w-3.5" />
            <span>{allOpen ? "Collapse All" : "Expand All"}</span>
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-1 text-xs">
          <button
            type="button"
            onClick={() => scrollToSection("combat")}
            className={cn(
              "rounded-md px-2 py-1 transition-colors border text-[11px] font-medium flex items-center gap-1",
              openSections.combat
                ? "bg-secondary border-primary/40 text-foreground"
                : "bg-background/60 border-border text-muted-foreground hover:text-foreground",
            )}
          >
            <Swords className="h-3 w-3 text-primary" />
            <span>Combat</span>
          </button>
          <button
            type="button"
            onClick={() => scrollToSection("abilities")}
            className={cn(
              "rounded-md px-2 py-1 transition-colors border text-[11px] font-medium flex items-center gap-1",
              openSections.abilities
                ? "bg-secondary border-primary/40 text-foreground"
                : "bg-background/60 border-border text-muted-foreground hover:text-foreground",
            )}
          >
            <Shield className="h-3 w-3 text-primary" />
            <span>Abilities</span>
          </button>
          <button
            type="button"
            onClick={() => scrollToSection("proficiencies")}
            className={cn(
              "rounded-md px-2 py-1 transition-colors border text-[11px] font-medium flex items-center gap-1",
              openSections.proficiencies
                ? "bg-secondary border-primary/40 text-foreground"
                : "bg-background/60 border-border text-muted-foreground hover:text-foreground",
            )}
          >
            <Scroll className="h-3 w-3 text-primary" />
            <span>Proficiencies</span>
          </button>
          {(hasSpells || invocationApplicable || replicateApplicable) && (
            <button
              type="button"
              onClick={() => scrollToSection("magic")}
              className={cn(
                "rounded-md px-2 py-1 transition-colors border text-[11px] font-medium flex items-center gap-1",
                openSections.magic
                  ? "bg-secondary border-primary/40 text-foreground"
                  : "bg-background/60 border-border text-muted-foreground hover:text-foreground",
              )}
            >
              <Sparkles className="h-3 w-3 text-primary" />
              <span>Magic</span>
            </button>
          )}
          <button
            type="button"
            onClick={() => scrollToSection("features")}
            className={cn(
              "rounded-md px-2 py-1 transition-colors border text-[11px] font-medium flex items-center gap-1",
              openSections.features
                ? "bg-secondary border-primary/40 text-foreground"
                : "bg-background/60 border-border text-muted-foreground hover:text-foreground",
            )}
          >
            <BookOpen className="h-3 w-3 text-primary" />
            <span>Features</span>
          </button>
          <button
            type="button"
            onClick={() => scrollToSection("inventory")}
            className={cn(
              "rounded-md px-2 py-1 transition-colors border text-[11px] font-medium flex items-center gap-1",
              openSections.inventory
                ? "bg-secondary border-primary/40 text-foreground"
                : "bg-background/60 border-border text-muted-foreground hover:text-foreground",
            )}
          >
            <Backpack className="h-3 w-3 text-primary" />
            <span>Inventory</span>
          </button>
        </div>
      </div>

      <div className="space-y-6">
        {/* 1. Combat & Attacks */}
        <CollapsibleCard
          id="section-combat"
          title="Combat & Attacks"
          icon={<Swords className="h-5 w-5" />}
          isOpen={openSections.combat}
          onToggle={() => toggleSection("combat")}
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
            <div className="space-y-6">
              <ACOptions c={c} />
              <SpecialFeatures c={c} />
            </div>
            <Attacks
              c={c}
              masteryApplicable={masteryApplicable}
              choicesMade={choicesMade}
              onChooseMasteries={() => setMasteryDialogOpen(true)}
            />
          </div>
        </CollapsibleCard>

        {/* 2. Abilities & Skills */}
        <CollapsibleCard
          id="section-abilities"
          title="Abilities & Skills"
          icon={<Shield className="h-5 w-5" />}
          isOpen={openSections.abilities}
          onToggle={() => toggleSection("abilities")}
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:items-stretch">
            <div className="flex flex-col gap-6 lg:h-full">
              <Abilities c={c} className="flex-1" />
              <SavingThrows c={c} />
            </div>
            <Skills c={c} />
          </div>
        </CollapsibleCard>

        {/* 3. Proficiencies & Languages */}
        <CollapsibleCard
          id="section-proficiencies"
          title="Proficiencies & Languages"
          icon={<Scroll className="h-5 w-5" />}
          isOpen={openSections.proficiencies}
          onToggle={() => toggleSection("proficiencies")}
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Proficiencies c={c} />
            <Languages c={c} />
          </div>
        </CollapsibleCard>

        {/* 4. Magic & Spells */}
        {(hasSpells || invocationApplicable || replicateApplicable) && (
          <CollapsibleCard
            id="section-magic"
            title="Spells & Magic"
            icon={<Sparkles className="h-5 w-5" />}
            isOpen={openSections.magic}
            onToggle={() => toggleSection("magic")}
          >
            <div className="space-y-6">
              {replicateApplicable && (
                <Section
                  title="Replicate Magic Item (Infusions)"
                  titleRight={
                    <Button size="sm" onClick={() => setReplicateDialogOpen(true)}>
                      Change Loadout (Long Rest)
                    </Button>
                  }
                >
                  {activeReplicationsList.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No replicated magic items currently active ({activeReplicationsList.length}/{maxActiveReplications} infused).
                    </p>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-xs text-muted-foreground">
                        Active Infused Items: <span className="font-semibold text-foreground">{activeReplicationsList.length} / {maxActiveReplications}</span> (from {knownPlansCount} known plans)
                      </p>
                      <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {activeReplicationsList.map((item, idx) => (
                          <li
                            key={`${item.name}-${idx}`}
                            className="rounded border border-border bg-background/50 p-3 shadow-sm flex flex-col justify-between"
                          >
                            <div>
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-sm font-semibold text-primary">{item.name}</span>
                                <div className="flex items-center gap-1.5">
                                  {item.rarity && (
                                    <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-secondary/80 text-muted-foreground">
                                      {item.rarity}
                                    </span>
                                  )}
                                  {item.attunement && (
                                    <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 border border-amber-500/20">
                                      Attunement
                                    </span>
                                  )}
                                </div>
                              </div>
                              {item.type && (
                                <p className="text-[11px] text-muted-foreground mt-0.5">{item.type}</p>
                              )}
                              {item.description && (
                                <p className="mt-1.5 text-xs text-foreground/90 whitespace-pre-line leading-relaxed">
                                  {item.description}
                                </p>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </Section>
              )}
              {invocationApplicable && (
                <Section
                  title="Eldritch Invocations"
                  titleRight={
                    <Button size="sm" onClick={() => setInvocationDialogOpen(true)}>
                      Manage Invocations
                    </Button>
                  }
                >
                  {invocationsList.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No invocations selected.
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {invocationsList.map((inv, idx) => (
                        <li
                          key={`${inv.name}-${idx}`}
                          className="rounded border border-border bg-background/40 p-3"
                        >
                          <div className="text-sm font-semibold text-foreground">{inv.name}</div>
                          {inv.description && (
                            <p className="mt-1 text-xs text-foreground/90 whitespace-pre-line leading-relaxed">
                              {inv.description}
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </Section>
              )}
              {hasSpells && (
                <Spells
                  c={c}
                  spellApplicable={spellApplicable}
                  onPrepareSpells={() => setSpellDialogOpen(true)}
                />
              )}
            </div>
          </CollapsibleCard>
        )}

        {/* 5. Features & Traits */}
        <CollapsibleCard
          id="section-features"
          title="Features & Traits"
          icon={<BookOpen className="h-5 w-5" />}
          isOpen={openSections.features}
          onToggle={() => toggleSection("features")}
        >
          <Features
            c={c}
            isWildHeartBarbarian={isWildHeartBarbarian}
            currentAspect={currentAspect}
            onOpenAspectDialog={() => setAspectDialogOpen(true)}
          />
        </CollapsibleCard>

        {/* 6. Inventory & Equipment */}
        <CollapsibleCard
          id="section-inventory"
          title="Inventory & Equipment"
          icon={<Backpack className="h-5 w-5" />}
          isOpen={openSections.inventory}
          onToggle={() => toggleSection("inventory")}
        >
          <InventorySection c={c} />
        </CollapsibleCard>
      </div>
      <PrepareSpellsDialog
        open={spellDialogOpen}
        onClose={() => setSpellDialogOpen(false)}
      />
      <ChooseMasteriesDialog
        open={masteryDialogOpen}
        onClose={() => setMasteryDialogOpen(false)}
      />
      <InvocationsDialog
        open={invocationDialogOpen}
        onClose={() => setInvocationDialogOpen(false)}
      />
      <ReplicateMagicItemDialog
        open={replicateDialogOpen}
        onClose={() => setReplicateDialogOpen(false)}
      />
      <AspectOfTheWildsDialog
        open={aspectDialogOpen}
        onClose={() => setAspectDialogOpen(false)}
        currentAspect={currentAspect}
      />
      <LevelUpDialog
        open={levelUpOpen}
        onClose={() => setLevelUpOpen(false)}
        onSuccess={(newLevel, isSpellcaster) => {
          setLevelUpFlash(`Leveled up to Level ${newLevel}!`);
          setShowSpellPrompt(isSpellcaster);
          window.setTimeout(() => setLevelUpFlash(null), 8000);
        }}
      />
    </Shell>
  );
}

function Shell({
  children,
  debugData,
  headerActions,
  actionFeedback,
}: {
  children: React.ReactNode;
  debugData?: unknown;
  headerActions?: React.ReactNode;
  actionFeedback?: React.ReactNode;
}) {
  const bugReportUrl = useBugReportUrl();
  return (
    <div className="min-h-dvh bg-background text-foreground">
      {/* ── Content ─────────────────────────────────────────── */}
      <div className="relative z-10">
        <div className="container py-10 max-w-5xl">
          <div className="mb-6 space-y-2">
            <div className="flex items-center justify-between gap-4">
            <Button asChild variant="ghost" size="sm">
              <Link to="/">← Home</Link>
            </Button>
              <div className="flex flex-wrap items-center justify-end gap-3">
              <Button asChild variant="outline" size="sm">
                <a
                  href={bugReportUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Bug Report
                </a>
              </Button>
              {headerActions}
              {import.meta.env.DEV && debugData != null && (
                <Button
                  variant="outline"
                  size="sm"
                  className="border-amber-500 text-amber-700 hover:bg-amber-50 print:hidden"
                  onClick={() => {
                    const name =
                      typeof (debugData as Record<string, unknown>).name ===
                      "string"
                        ? ((debugData as Record<string, unknown>)
                            .name as string)
                        : "character";
                    const filename = `${
                      name
                        .trim()
                        .toLowerCase()
                        .replace(/[^a-z0-9._-]+/g, "-")
                        .replace(/^-+|-+$/g, "") || "character"
                    }-debug.json`;
                    downloadJson(filename, debugData);
                  }}
                >
                  <Download className="w-3 h-3 mr-1" />
                  Debug JSON
                </Button>
              )}
              <Button asChild variant="outline" size="sm">
                <Link to="/sheet/pdf">Printable Sheet</Link>
              </Button>
              <Button asChild size="sm">
                <Link to="/wizard">Edit in Wizard</Link>
              </Button>
              <ThemeToggle />
            </div>
            </div>
            {actionFeedback ? (
              <div className="flex flex-wrap items-center justify-end gap-x-4 gap-y-1">
                {actionFeedback}
              </div>
            ) : null}
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}

function CollapsibleCard({
  id,
  title,
  icon,
  isOpen,
  onToggle,
  children,
  headerActions,
  className,
}: {
  id: string;
  title: string;
  icon?: React.ReactNode;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  headerActions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      id={id}
      className={cn(
        "rounded-xl border border-border bg-card/60 transition-all duration-200 overflow-hidden shadow-2xs",
        className,
      )}
    >
      <div
        role="button"
        tabIndex={0}
        onClick={onToggle}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onToggle();
          }
        }}
        aria-expanded={isOpen}
        className="flex items-center justify-between p-3.5 sm:p-4 cursor-pointer select-none hover:bg-muted/40 transition-colors gap-3"
      >
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          {icon && <span className="text-primary shrink-0">{icon}</span>}
          <h2 className="font-display text-base sm:text-lg text-foreground font-semibold">
            {title}
          </h2>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {headerActions && (
            <div onClick={(e) => e.stopPropagation()}>{headerActions}</div>
          )}
          <span
            className="p-1 text-muted-foreground hover:text-foreground rounded transition-colors"
            aria-hidden="true"
          >
            {isOpen ? (
              <ChevronUp className="h-5 w-5" />
            ) : (
              <ChevronDown className="h-5 w-5" />
            )}
          </span>
        </div>
      </div>
      {isOpen && (
        <div className="p-4 pt-0 border-t border-border/40">
          <div className="pt-4">{children}</div>
        </div>
      )}
    </div>
  );
}

function Section({
  title,
  children,
  className,
  titleRight,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
  titleRight?: React.ReactNode;
}) {
  return (
    <section
      className={
        "rounded-md border border-border bg-card/50 p-4 flex flex-col" +
        (className ? " " + className : "")
      }
    >
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-display text-lg text-primary">{title}</h2>
        {titleRight}
      </div>
      {children}
    </section>
  );
}

function Header({
  c,
  onLevelUp,
  canLevelUp,
}: {
  c: Char;
  onLevelUp?: () => void;
  canLevelUp?: boolean;
}) {
  const name = str(c.name) ?? str(c.character_name) ?? "Unnamed";
  const cls = str(c.class) ?? "—";
  const sub = str(c.subclass);
  const species = str(c.species) ?? "—";
  const lineage = str(c.lineage);
  const bg = str(c.background);
  const level = num(c.level) ?? "—";
  const alignment = str(c.alignment) ?? "Unspecified";
  return (
    <header className="rounded-md border border-border bg-card/50 p-5 mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 className="font-display text-3xl text-primary">{name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Level {level} {cls}
          {sub ? ` (${sub})` : ""} · {species}
          {lineage ? ` (${lineage})` : ""}
          {bg ? ` · ${bg}` : ""} · {alignment}
        </p>
      </div>
      {onLevelUp && (
        <Button
          size="sm"
          onClick={onLevelUp}
          disabled={!canLevelUp}
          className="bg-amber-600 hover:bg-amber-700 text-white font-semibold shadow-xs shrink-0 self-start sm:self-auto"
        >
          <Sparkles className="w-3.5 h-3.5 mr-1.5" />
          Level Up {canLevelUp && typeof level === "number" ? `(${level} → ${level + 1})` : ""}
        </Button>
      )}
    </header>
  );
}

function CoreStats({ c }: { c: Char }) {
  const combat = rec(c.combat);
  const hp = rec(combat.hit_points);
  const speed = num(c.speed) ?? num(combat.speed);
  const climbSpeed = num(c.climb_speed) ?? num(combat.climb_speed);
  const swimSpeed = num(c.swim_speed) ?? num(combat.swim_speed);
  const speedDisplay =
    speed !== undefined
      ? climbSpeed
        ? `${speed} ft (Climb: ${climbSpeed} ft)`
        : swimSpeed
          ? `${speed} ft (Swim: ${swimSpeed} ft)`
          : `${speed} ft`
      : "—";
  const init = num(combat.initiative_bonus) ?? num(combat.initiative);
  const passive = num(combat.passive_perception);
  const pb = num(c.proficiency_bonus);
  const hpMax = num(hp.maximum) ?? num(combat.hp);
  const hitDice = rec(combat.hit_dice);
  const hitDiceTotal = str(hitDice.total) ?? num(hitDice.total);
  return (
    <Section title="Combat">
      <dl className="grid grid-cols-2 sm:grid-cols-3 gap-y-3 gap-x-6 text-sm">
        <Stat label="Hit Points" value={hpMax} />
        <Stat label="Initiative" value={signed(init)} />
        <Stat label="Speed" value={speedDisplay} />
        <Stat label="Passive Perception" value={passive} />
        <Stat label="Proficiency Bonus" value={signed(pb)} />
        <Stat
          label="Hit Dice"
          value={hitDiceTotal}
        />
      </dl>
    </Section>
  );
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: string | number | undefined;
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-widest text-muted-foreground">
        {label}
      </dt>
      <dd className="text-lg font-semibold">{value ?? "—"}</dd>
    </div>
  );
}

function Abilities({ c, className }: { c: Char; className?: string }) {
  const abilities = rec(c.abilities);
  const order = [
    "Strength",
    "Dexterity",
    "Constitution",
    "Intelligence",
    "Wisdom",
    "Charisma",
  ];
  type AbilityView = {
    score?: number;
    modifier?: number;
    base?: number;
    speciesBonus?: number;
    backgroundBonus?: number;
  };
  function pick(name: string): AbilityView {
    const direct = rec(
      abilities[name] ??
        abilities[name.toLowerCase()] ??
        abilities[name.slice(0, 3).toLowerCase()],
    );
    if (Object.keys(direct).length) {
      return {
        score: num(direct.score),
        modifier: num(direct.modifier) ?? num(direct.mod),
        base: num(direct.base_score),
        speciesBonus: num(direct.species_bonus),
        backgroundBonus: num(direct.background_bonus),
      };
    }
    const rawScores = rec(c.ability_scores);
    const raw =
      rawScores[name] ??
      rawScores[name.toLowerCase()] ??
      rawScores[name.slice(0, 3).toLowerCase()];
    return { score: num(raw) };
  }

  const views = order.map((a) => ({ name: a, v: pick(a) }));

  const abbr = (name: string) => name.slice(0, 3).toUpperCase();
  const fmtBonus = (n: number) => (n > 0 ? `+${n}` : String(n));

  // Collect contribution rows grouped by source
  type Contribution = { ability: string; value: number };
  const groups: Array<{ source: string; contribs: Contribution[] }> = [];

  // Background bonuses (from per-ability breakdown)
  const backgroundContribs: Contribution[] = views
    .filter(({ v }) => (v.backgroundBonus ?? 0) !== 0)
    .map(({ name, v }) => ({ ability: name, value: v.backgroundBonus ?? 0 }));
  if (backgroundContribs.length > 0) {
    const bgName = str(c.background);
    groups.push({
      source: bgName ? `${bgName} (Background)` : "Background",
      contribs: backgroundContribs,
    });
  }

  // Feat / ASI contributions from ability_bonuses[]
  const featBonuses = arr<Record<string, unknown>>(c.ability_bonuses);
  const bySource = new Map<string, Contribution[]>();
  for (const b of featBonuses) {
    const ability = str(b.ability);
    const value = num(b.value);
    const source = str(b.source) ?? "Feat";
    if (!ability || value === undefined || value === 0) continue;
    if (!bySource.has(source)) bySource.set(source, []);
    bySource.get(source)!.push({ ability, value });
  }
  for (const [source, contribs] of bySource) {
    groups.push({ source, contribs });
  }

  return (
    <Section title="Abilities" className={className}>
      <div className="grid grid-cols-3 gap-2 flex-1 content-start">
        {views.map(({ name, v }) => (
          <div
            key={name}
            className="rounded border border-border bg-background/40 p-2 text-center flex flex-col"
          >
            <div className="text-xs uppercase text-muted-foreground">
              {abbr(name)}
            </div>
            <div className="text-2xl font-semibold">{v.score ?? "—"}</div>
            <div className="text-sm text-muted-foreground">
              {signed(v.modifier)}
            </div>
          </div>
        ))}
      </div>
      {groups.length > 0 && (
        <div className="mt-3 border-t border-border/60 pt-2 text-[11px] text-muted-foreground/90">
          <div className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground/70">
            Contributions
          </div>
          <ul className="space-y-0.5">
            {groups.map(({ source, contribs }, i) => (
              <li key={i} className="flex flex-wrap gap-x-2">
                <span className="font-semibold text-foreground/90">
                  {source}:
                </span>
                <span>
                  {contribs
                    .map((cn) => `${abbr(cn.ability)} ${fmtBonus(cn.value)}`)
                    .join(", ")}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Section>
  );
}

const SAVE_ORDER = [
  "Strength",
  "Dexterity",
  "Constitution",
  "Intelligence",
  "Wisdom",
  "Charisma",
];

function SavingThrows({ c }: { c: Char }) {
  const abilities = rec(c.abilities);
  const advantages = arr<Record<string, unknown>>(c.save_advantages);
  const hasAnyAdvantage = advantages.length > 0;

  const advantageFor = (name: string) => {
    for (const sa of advantages) {
      const list = arr<string>(sa.abilities);
      if (list.includes(name)) {
        return str(sa.display) ?? "Advantage on save";
      }
    }
    return undefined;
  };

  return (
    <Section title="Saving Throws">
      <ul className="space-y-1 text-sm">
        {SAVE_ORDER.map((name) => {
          const data = rec(abilities[name.toLowerCase()]);
          const bonus = num(data.saving_throw);
          const proficient = data.saving_throw_proficient === true;
          const advLabel = advantageFor(name);
          return (
            <li
              key={name}
              className="flex items-center justify-between gap-2 py-0.5"
            >
              <span className="flex min-w-0 items-center gap-1.5">
                <span
                  className={
                    proficient
                      ? "font-semibold text-foreground"
                      : "text-muted-foreground"
                  }
                >
                  {name}
                </span>
                {proficient && <span className="shrink-0 text-primary">★</span>}
                {advLabel && (
                  <span
                    title={advLabel}
                    className="shrink-0 rounded bg-emerald-600/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
                  >
                    Adv
                  </span>
                )}
              </span>
              <span
                className={
                  "shrink-0 tabular-nums " +
                  (proficient
                    ? "text-foreground font-semibold"
                    : "text-muted-foreground")
                }
              >
                {signed(bonus)}
              </span>
            </li>
          );
        })}
      </ul>
      <div className="mt-3 border-t border-border/60 pt-2 text-[10px] uppercase tracking-wide text-muted-foreground/80">
        <span className="text-primary">★</span> Proficient
        {hasAnyAdvantage && (
          <>
            {" · "}
            <span className="rounded bg-emerald-600/80 px-1 py-0.5 text-white">
              Adv
            </span>{" "}
            Advantage on save
          </>
        )}
      </div>
    </Section>
  );
}

function Skills({ c }: { c: Char }) {
  const skills = rec(c.skills);
  const entries = Object.entries(skills);
  const formatName = (key: string) =>
    key
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  return (
    <Section title="Skills">
      {entries.length === 0 ? (
        <p className="text-xs text-muted-foreground">No skill data.</p>
      ) : (
        <>
          <ul className="grid grid-cols-1 gap-y-1 text-sm">
            {entries
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([name, data]) => {
                const d = rec(data);
                const bonus = num(d.bonus) ?? num(d.modifier);
                const ability = str(d.ability);
                const proficient = d.proficient === true;
                const expertise = d.expertise === true;
                const jackOfAllTrades = d.jack_of_all_trades === true;
                const marked = proficient || expertise;
                const source = str(d.source);
                const showSource = marked && source && source !== "None";
                const marker = expertise ? "★" : proficient ? "★" : jackOfAllTrades ? "◑" : "○";
                const markerClass = expertise
                  ? "text-blue-400"
                  : proficient
                    ? "text-primary"
                    : jackOfAllTrades
                      ? "text-amber-400"
                      : "text-muted-foreground/60";
                return (
                  <li
                    key={name}
                    className="flex items-center justify-between gap-2 py-0.5"
                  >
                    <span className="flex min-w-0 items-center gap-1.5">
                      <span className={"shrink-0 " + markerClass}>
                        {marker}
                      </span>
                      <span
                        className={
                          "truncate " +
                          (marked
                            ? "font-semibold text-foreground"
                            : jackOfAllTrades
                              ? "font-medium text-foreground"
                              : "text-muted-foreground")
                        }
                      >
                        {formatName(name)}
                      </span>
                      {ability && (
                        <span className="shrink-0 text-xs uppercase text-muted-foreground/70">
                          ({ability.slice(0, 3)})
                        </span>
                      )}
                      {showSource && (
                        <span className="shrink-0 rounded border border-border bg-secondary/60 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                          {source}
                        </span>
                      )}
                      {jackOfAllTrades && (
                        <span className="shrink-0 rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber-400">
                          JoAT
                        </span>
                      )}
                    </span>
                    <span
                      className={
                        "shrink-0 tabular-nums " +
                        (marked || jackOfAllTrades ? "text-foreground" : "text-muted-foreground")
                      }
                    >
                      {signed(bonus)}
                    </span>
                  </li>
                );
              })}
          </ul>
          <div className="mt-3 border-t border-border/60 pt-2 text-[10px] uppercase tracking-wide text-muted-foreground/80">
            <span className="text-primary">★</span> Proficient ·{" "}
            <span className="text-blue-400">★</span> Expertise ·{" "}
            <span className="text-amber-400">◑</span> Jack of All Trades
          </div>
        </>
      )}
    </Section>
  );
}

function ACOptions({ c }: { c: Char }) {
  const options = arr<Record<string, unknown>>(c.ac_options);
  return (
    <Section title="Armor Class">
      {options.length === 0 ? (
        <p className="text-xs text-muted-foreground">No AC options computed.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {options.slice(0, 4).map((opt, i) => {
            const ac = num(opt.ac);
            const armor = str(opt.armor);
            const shield = opt.shield;
            const formula = str(opt.formula);
            return (
              <li
                key={i}
                className={
                  "rounded border p-2 " +
                  (i === 0
                    ? "border-primary bg-secondary"
                    : "border-border bg-background/40")
                }
              >
                <div className="flex justify-between">
                  <span className="font-semibold">
                    {i === 0 ? "★ " : ""}AC {ac ?? "—"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {armor ?? "Unarmored"}
                    {shield ? " + Shield" : ""}
                  </span>
                </div>
                {formula && (
                  <div className="text-xs text-muted-foreground mt-1">
                    {formula}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Section>
  );
}

function SpecialFeatures({ c }: { c: Char }) {
  const barbarianStats = rec(c.barbarian_stats);
  const hasRage = Boolean(barbarianStats.has_rage);
  const bardStats = rec(c.bard_stats);
  const hasBardicInspiration = Boolean(bardStats.has_bardic_inspiration);
  const clericStats = rec(c.cleric_stats);
  const hasChannelDivinity = Boolean(clericStats.has_channel_divinity);
  const druidStats = rec(c.druid_stats);
  const hasWildShape = Boolean(druidStats.has_wild_shape);
  const fighterStats = rec(c.fighter_stats);
  const isFighter = Boolean(fighterStats.is_fighter);
  const monkStats = rec(c.monk_stats);
  const isMonk = Boolean(monkStats.is_monk);
  const superiorityDice = rec(c.superiority_dice);
  const hasSuperiorityDice = num(superiorityDice.count) !== undefined;
  const hasArcaneShot = num(c.arcane_shot_dc) !== undefined;

  const hasAnySpecial =
    (hasRage && num(barbarianStats.rage_damage) !== undefined) ||
    (hasBardicInspiration && bardStats.inspiration_die !== undefined) ||
    (hasChannelDivinity && clericStats.channel_divinity_max !== undefined) ||
    (hasWildShape && druidStats.wild_shape_max !== undefined) ||
    (isFighter && fighterStats.fighter_level !== undefined) ||
    (isMonk && monkStats.monk_level !== undefined) ||
    hasSuperiorityDice ||
    hasArcaneShot;

  if (!hasAnySpecial) {
    return null;
  }

  return (
    <Section title="Special Features">
      <div className="space-y-3">
        {hasSuperiorityDice && (
          <div className="rounded border border-border/80 bg-background/40 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide text-primary">
                Superiority Dice
              </span>
              {num(superiorityDice.save_dc) !== undefined && (
                <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                  DC {num(superiorityDice.save_dc)}
                </span>
              )}
            </div>
            <div className="mt-1 text-sm text-foreground">
              {num(superiorityDice.count)} dice ({str(superiorityDice.die) ?? "d8"}) · Regain on Short or Long Rest
            </div>
            {arr<Record<string, unknown>>(c.maneuvers).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {arr<Record<string, unknown>>(c.maneuvers).map((m, idx) => (
                  <span
                    key={idx}
                    className="rounded border border-border bg-secondary/60 px-2 py-0.5 text-xs text-foreground"
                    title={str(m.description)}
                  >
                    {str(m.name)}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {hasArcaneShot && (
          <div className="rounded border border-border/80 bg-background/40 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide text-primary">
                Arcane Shot
              </span>
              <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                DC {num(c.arcane_shot_dc)}
              </span>
            </div>
            <div className="mt-1 text-sm text-foreground">
              {str(c.arcane_shot_die) ?? "d6"} Arcane Shot Die · {num(c.arcane_shot_uses) ?? "—"} uses per Short or Long Rest
            </div>
            {arr<Record<string, unknown>>(c.arcane_shots).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {arr<Record<string, unknown>>(c.arcane_shots).map((s, idx) => (
                  <span
                    key={idx}
                    className="rounded border border-border bg-secondary/60 px-2 py-0.5 text-xs text-foreground"
                    title={str(s.description)}
                  >
                    {str(s.name)}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {hasRage && num(barbarianStats.rage_damage) !== undefined && (
          <div className="flex items-center justify-between rounded border border-border/80 bg-background/40 p-3 text-xs">
            <div className="flex items-center gap-2">
              <Flame className="h-4 w-4 text-red-400" />
              <span className="font-semibold uppercase tracking-wide text-red-400">
                Rage Damage
              </span>
              <span className="rounded bg-red-500/20 px-2 py-0.5 text-xs font-semibold text-red-300">
                +{num(barbarianStats.rage_damage)}
              </span>
              <span className="text-muted-foreground hidden sm:inline">
                (Strength melee attacks while Raging)
              </span>
            </div>
            <span className="rounded border border-border/60 bg-background/60 px-2 py-0.5 text-xs font-medium text-foreground">
              {typeof barbarianStats.rage_uses === "string"
                ? barbarianStats.rage_uses
                : `${num(barbarianStats.rage_uses)} uses / Long Rest`}
            </span>
          </div>
        )}

        {hasBardicInspiration && bardStats.inspiration_die !== undefined && (
          <div className="flex items-center justify-between rounded border border-border/80 bg-background/40 p-3 text-xs">
            <div className="flex items-center gap-2">
              <Music className="h-4 w-4 text-amber-400" />
              <span className="font-semibold uppercase tracking-wide text-amber-400">
                Bardic Inspiration
              </span>
              <span className="rounded bg-amber-500/20 px-2 py-0.5 text-xs font-semibold text-amber-300">
                {str(bardStats.inspiration_die)}
              </span>
              <span className="text-muted-foreground hidden sm:inline">
                (Bonus Action to inspire creature within 60 ft)
              </span>
            </div>
            <span className="rounded border border-border/60 bg-background/60 px-2 py-0.5 text-xs font-medium text-foreground">
              {num(bardStats.inspiration_uses)} uses / {str(bardStats.recharge) ?? "Long Rest"}
            </span>
          </div>
        )}

        {hasChannelDivinity && clericStats.channel_divinity_max !== undefined && (
          <div className="flex flex-col gap-2 rounded border border-border/80 bg-background/40 p-3 text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-sky-400" />
                <span className="font-semibold uppercase tracking-wide text-sky-400">
                  Channel Divinity
                </span>
                {clericStats.divine_spark_dice !== undefined && (
                  <span className="rounded bg-sky-500/20 px-2 py-0.5 text-xs font-semibold text-sky-300">
                    Spark {str(clericStats.divine_spark_dice)}
                  </span>
                )}
                {clericStats.save_dc !== undefined && (
                  <span className="text-muted-foreground hidden sm:inline">
                    (Save DC {num(clericStats.save_dc)})
                  </span>
                )}
              </div>
              <span className="rounded border border-border/60 bg-background/60 px-2 py-0.5 text-xs font-medium text-foreground">
                {num(clericStats.channel_divinity_max)} uses / Short or Long Rest
              </span>
            </div>

            {arr<Record<string, unknown>>(clericStats.channel_divinity_options).length > 0 && (
              <div className="mt-1 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                {arr<Record<string, unknown>>(clericStats.channel_divinity_options).map((opt, idx) => (
                  <div
                    key={idx}
                    className="rounded border border-border/50 bg-background/50 px-2 py-1.5"
                  >
                    <div className="font-medium text-foreground">
                      {str(opt.name)} <span className="text-[10px] text-muted-foreground">({str(opt.action)})</span>
                    </div>
                    <div className="text-[11px] text-muted-foreground line-clamp-2">
                      {str(opt.effect)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {hasWildShape && druidStats.wild_shape_max !== undefined && (
          <div className="flex flex-col gap-2 rounded border border-border/80 bg-background/40 p-3 text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <PawPrint className="h-4 w-4 text-emerald-400" />
                <span className="font-semibold uppercase tracking-wide text-emerald-400">
                  Wild Shape
                </span>
                {druidStats.wild_shape_max_cr !== undefined && (
                  <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-semibold text-emerald-300">
                    Max CR {str(druidStats.wild_shape_max_cr)}
                  </span>
                )}
                {druidStats.wild_shape_temp_hp !== undefined && (
                  <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-200">
                    +{num(druidStats.wild_shape_temp_hp)} Temp HP
                  </span>
                )}
                {druidStats.save_dc !== undefined && (
                  <span className="text-muted-foreground hidden sm:inline">
                    (Save DC {num(druidStats.save_dc)})
                  </span>
                )}
              </div>
              <span className="rounded border border-border/60 bg-background/60 px-2 py-0.5 text-xs font-medium text-foreground">
                {num(druidStats.wild_shape_max)} uses / Short or Long Rest
              </span>
            </div>

            <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground">
              <span>Known Forms: <strong className="text-foreground">{num(druidStats.wild_shape_known_forms)}</strong></span>
              <span>·</span>
              <span>Duration: <strong className="text-foreground">{num(druidStats.wild_shape_duration_hours)} hrs</strong></span>
              <span>·</span>
              <span>Fly Speed: <strong className="text-foreground">{druidStats.fly_speed_allowed ? "Yes" : "No (Lv 8+)"}</strong></span>
              <span>·</span>
              <span>Swim Speed: <strong className="text-foreground">Yes</strong></span>
            </div>

            {arr<Record<string, unknown>>(druidStats.wild_shape_options).length > 0 && (
              <div className="mt-1 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                {arr<Record<string, unknown>>(druidStats.wild_shape_options).map((opt, idx) => (
                  <div
                    key={idx}
                    className="rounded border border-border/50 bg-background/50 px-2 py-1.5"
                  >
                    <div className="font-medium text-foreground">
                      {str(opt.name)} <span className="text-[10px] text-muted-foreground">({str(opt.action)})</span>
                    </div>
                    <div className="text-[11px] text-muted-foreground line-clamp-2">
                      {str(opt.effect)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {isFighter && fighterStats.fighter_level !== undefined && (
          <div className="flex flex-col gap-2 rounded border border-border/80 bg-background/40 p-3 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Swords className="h-4 w-4 text-orange-400" />
                <span className="font-semibold uppercase tracking-wide text-orange-400">
                  Tactical Martial Exploits
                </span>
                <span className="rounded bg-orange-500/20 px-2 py-0.5 text-xs font-semibold text-orange-300">
                  {str(fighterStats.extra_attacks_label) ?? `${num(fighterStats.attacks_per_action)} attack/action`}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="rounded border border-border/60 bg-background/60 px-2 py-0.5 text-xs font-medium text-foreground">
                  Second Wind: {num(fighterStats.second_wind_uses)} / {num(fighterStats.second_wind_max)}
                </span>
                {Boolean(fighterStats.has_action_surge) && (
                  <span className="rounded border border-border/60 bg-background/60 px-2 py-0.5 text-xs font-medium text-foreground">
                    Action Surge: {num(fighterStats.action_surge_uses)} / {num(fighterStats.action_surge_max)}
                  </span>
                )}
                {Boolean(fighterStats.has_indomitable) && (
                  <span className="rounded border border-border/60 bg-background/60 px-2 py-0.5 text-xs font-medium text-foreground">
                    Indomitable: {num(fighterStats.indomitable_uses)} / {num(fighterStats.indomitable_max)} (+{num(fighterStats.indomitable_bonus)})
                  </span>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground border-t border-border/40 pt-1.5">
              <span>Second Wind: <strong className="text-foreground">{str(fighterStats.second_wind_healing)} HP</strong></span>
              {Boolean(fighterStats.tactical_mind) && (
                <>
                  <span>·</span>
                  <span className="text-emerald-400 font-medium">Tactical Mind: +1d10 to failed check</span>
                </>
              )}
              {Boolean(fighterStats.tactical_shift) && (
                <>
                  <span>·</span>
                  <span className="text-sky-400 font-medium">Tactical Shift: Half Speed move w/o OA</span>
                </>
              )}
              {Boolean(fighterStats.has_tactical_master) && (
                <>
                  <span>·</span>
                  <span className="text-amber-400 font-medium">Tactical Master (Push, Sap, Slow)</span>
                </>
              )}
              {Boolean(fighterStats.has_studied_attacks) && (
                <>
                  <span>·</span>
                  <span className="text-purple-400 font-medium">Studied Attacks (Advantage on miss)</span>
                </>
              )}
            </div>

            {arr<Record<string, unknown>>(fighterStats.actions).length > 0 && (
              <div className="mt-1 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                {arr<Record<string, unknown>>(fighterStats.actions).map((act, idx) => (
                  <div
                    key={idx}
                    className="rounded border border-border/50 bg-background/50 px-2 py-1.5"
                  >
                    <div className="font-medium text-foreground">
                      {str(act.name)} <span className="text-[10px] text-muted-foreground">({str(act.action)})</span>
                      {act.recharge !== undefined && (
                        <span className="ml-1 text-[10px] text-muted-foreground">· {str(act.recharge)}</span>
                      )}
                    </div>
                    <div className="text-[11px] text-muted-foreground line-clamp-2">
                      {str(act.effect)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {isMonk && monkStats.monk_level !== undefined && (
          <div className="flex flex-col gap-2 rounded border border-border/80 bg-background/40 p-3 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Zap className="h-4 w-4 text-amber-400" />
                <span className="font-semibold uppercase tracking-wide text-amber-400">
                  Focus & Martial Arts
                </span>
                <span className="rounded bg-amber-500/20 px-2 py-0.5 text-xs font-semibold text-amber-300">
                  {str(monkStats.extra_attacks_label) ?? `${num(monkStats.attacks_per_action)} attack/action`}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="rounded border border-border/60 bg-background/60 px-2 py-0.5 text-xs font-medium text-foreground">
                  Focus Points: {num(monkStats.focus_points)} / {num(monkStats.focus_points_max)} FP
                </span>
                <span className="rounded border border-border/60 bg-background/60 px-2 py-0.5 text-xs font-medium text-foreground">
                  Save DC: {num(monkStats.focus_save_dc)}
                </span>
                <span className="rounded border border-border/60 bg-background/60 px-2 py-0.5 text-xs font-medium text-foreground">
                  Die: {str(monkStats.martial_arts_die)}
                </span>
                {(num(monkStats.unarmored_movement_bonus) ?? 0) > 0 && (
                  <span className="rounded border border-border/60 bg-background/60 px-2 py-0.5 text-xs font-medium text-foreground">
                    Speed: +{num(monkStats.unarmored_movement_bonus)} ft
                  </span>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground border-t border-border/40 pt-1.5">
              <span>Recharge: <strong className="text-foreground">{str(monkStats.focus_recharge)}</strong></span>
              {Boolean(monkStats.has_uncanny_metabolism) && (
                <>
                  <span>·</span>
                  <span className="text-emerald-400 font-medium">Uncanny Metabolism (Init: Regain FP + Heal)</span>
                </>
              )}
              {Boolean(monkStats.has_deflect_attacks) && (
                <>
                  <span>·</span>
                  <span className="text-sky-400 font-medium">
                    {Boolean(monkStats.has_deflect_energy) ? "Deflect Energy (Any damage)" : "Deflect Attacks (B/P/S)"}
                  </span>
                </>
              )}
              {Boolean(monkStats.has_stunning_strike) && (
                <>
                  <span>·</span>
                  <span className="text-amber-400 font-medium">Stunning Strike (CON save)</span>
                </>
              )}
              {Boolean(monkStats.has_empowered_strikes) && (
                <>
                  <span>·</span>
                  <span className="text-purple-400 font-medium">Empowered Strikes (Force)</span>
                </>
              )}
              {Boolean(monkStats.has_heightened_focus) && (
                <>
                  <span>·</span>
                  <span className="text-rose-400 font-medium">Heightened Focus</span>
                </>
              )}
              {Boolean(monkStats.has_self_restoration) && (
                <>
                  <span>·</span>
                  <span className="text-teal-400 font-medium">Self-Restoration</span>
                </>
              )}
              {Boolean(monkStats.has_disciplined_survivor) && (
                <>
                  <span>·</span>
                  <span className="text-indigo-400 font-medium">Disciplined Survivor (All Saves)</span>
                </>
              )}
              {Boolean(monkStats.has_perfect_focus) && (
                <>
                  <span>·</span>
                  <span className="text-cyan-400 font-medium">Perfect Focus (Init: Regain to 4 FP)</span>
                </>
              )}
              {Boolean(monkStats.has_superior_defense) && (
                <>
                  <span>·</span>
                  <span className="text-yellow-400 font-medium">Superior Defense (3 FP Resistance)</span>
                </>
              )}
              {Boolean(monkStats.has_body_and_mind) && (
                <>
                  <span>·</span>
                  <span className="text-fuchsia-400 font-medium">Body and Mind (+4 DEX/WIS)</span>
                </>
              )}
            </div>

            {arr<Record<string, unknown>>(monkStats.actions).length > 0 && (
              <div className="mt-1 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                {arr<Record<string, unknown>>(monkStats.actions).map((act, idx) => (
                  <div
                    key={idx}
                    className="rounded border border-border/50 bg-background/50 px-2 py-1.5"
                  >
                    <div className="flex items-center justify-between gap-1 font-semibold text-foreground">
                      <span className="text-amber-300">{str(act.name)}</span>
                      <div className="flex items-center gap-1">
                        {act.cost !== undefined && (
                          <span className="rounded bg-muted/60 px-1 text-[10px] text-muted-foreground font-normal">
                            {str(act.cost)}
                          </span>
                        )}
                        <span className="rounded bg-primary/20 px-1 text-[10px] text-primary">
                          {str(act.action)}
                        </span>
                      </div>
                    </div>
                    <div className="mt-0.5 text-[11px] text-muted-foreground">
                      {str(act.effect)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Section>
  );
}

function Attacks({
  c,
  masteryApplicable,
  choicesMade,
  onChooseMasteries,
}: {
  c: Char;
  masteryApplicable?: boolean;
  choicesMade?: ChoicesMade;
  onChooseMasteries?: () => void;
}) {
  const attacks = arr<Record<string, unknown>>(c.attacks);
  const combinations = arr<Record<string, unknown>>(c.attack_combinations);

  const serverBestCombination = rec(c.best_attack_combination);
  const bestCombination =
    Object.keys(serverBestCombination).length > 0
      ? serverBestCombination
      : combinations.find((combo) => combo.recommended === true) ?? combinations[0];

  const bestMainhand = rec(bestCombination?.mainhand);
  const bestOffhand = rec(bestCombination?.offhand);
  const bestCombinationName = str(bestCombination?.name) ?? "Combination";
  const comboNotes = arr<string>(bestCombination?.notes);

  function renderCombinationWeaponLine(
    label: string,
    weapon: Record<string, unknown>,
  ) {
    const weaponName = str(weapon.name) ?? label;
    const attackBonusDisplay =
      str(weapon.attack_bonus_display) ?? signed(num(weapon.attack_bonus));
    const damage = str(weapon.damage) ?? str(weapon.damage_string);
    const damageType = str(weapon.damage_type);
    const avgDamage = num(weapon.avg_damage);

    return (
      <div className="rounded border border-border/60 bg-background/30 p-2">
        <div className="text-xs font-semibold text-foreground">
          {label}: {weaponName}
        </div>
        <div className="mt-1 text-xs text-foreground">{attackBonusDisplay} to hit</div>
        {damage && (
          <div className="text-xs text-foreground/90">
            {damage}
            {damageType ? ` ${damageType}` : ""}
            {avgDamage !== undefined ? ` (Avg: ${avgDamage})` : ""}
          </div>
        )}
      </div>
    );
  }

  return (
    <Section
      title="Attacks"
      titleRight={
        masteryApplicable &&
        onChooseMasteries && (
          <Button size="sm" onClick={onChooseMasteries}>
            Choose Masteries
          </Button>
        )
      }
    >
      {attacks.length === 0 ? (
        <p className="text-xs text-muted-foreground">No weapon attacks.</p>
      ) : (
        <>
          <ul className="space-y-3 text-sm">
            {attacks.map((a, i) => {
              const name = str(a.name) ?? str(a.weapon) ?? "Attack";
              const bonus = num(a.attack_bonus) ?? num(a.bonus);
              const bonusDisplay = str(a.attack_bonus_display) ?? signed(bonus);
              const damage = str(a.damage) ?? str(a.damage_string);
              const damageType = str(a.damage_type);
              const avgDamage = num(a.avg_damage);
              const avgCrit = num(a.avg_crit);
              const range = str(a.range);
              const ability = str(a.ability);
              const properties = arr<string>(a.properties);
              const damageNotes = arr<string>(a.damage_notes);
              const mastery = str(a.mastery);
              const weaponName = str(a.weapon ?? a.name) ?? "";
              const masteryIsSelected =
                masteryApplicable === true &&
                Array.isArray(choicesMade?.weapon_mastery_selections) &&
                (choicesMade!.weapon_mastery_selections as string[]).includes(
                  weaponName,
                );
              const proficient = a.proficient !== false;
              const throwDamage = str(a.throw_damage);
              const avgThrow = num(a.avg_throw_damage);
              const oneHanded = str(a.damage_one_handed);
              const twoHanded = str(a.damage_two_handed);
              const avgOne = num(a.avg_one_handed);
              const avgTwo = num(a.avg_two_handed);

              return (
                <li
                  key={i}
                  className="rounded border border-border bg-background/40 p-3"
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-semibold text-foreground">{name}</span>
                    {ability && (
                      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                        {str(a.effective_ability) || (ability.match(/\(([A-Z]{3})\)/)?.[1] ?? ability.slice(0, 3))}
                      </span>
                    )}
                  </div>

                  <dl className="mt-2 space-y-1 text-xs">
                    <div className="flex flex-wrap gap-x-2">
                      <dt className="font-semibold text-muted-foreground">
                        Attack:
                      </dt>
                      <dd className="text-foreground">{bonusDisplay} to hit</dd>
                      {range && (
                        <dd className="text-muted-foreground">
                          (Range: {range})
                        </dd>
                      )}
                    </div>

                    {damage && (
                      <div className="flex flex-wrap gap-x-2">
                        <dt className="font-semibold text-muted-foreground">
                          Damage:
                        </dt>
                        <dd className="text-foreground">
                          {damage}
                          {damageType ? ` ${damageType}` : ""}
                        </dd>
                        {(avgDamage !== undefined || avgCrit !== undefined) && (
                          <dd className="text-muted-foreground">
                            (Avg: {avgDamage ?? "—"}
                            {avgCrit !== undefined ? `, Crit: ${avgCrit}` : ""})
                          </dd>
                        )}
                      </div>
                    )}

                    {throwDamage && (
                      <div className="flex flex-wrap gap-x-2">
                        <dt className="font-semibold text-muted-foreground">
                          Throw:
                        </dt>
                        <dd className="text-foreground">
                          {throwDamage}
                          {damageType ? ` ${damageType}` : ""}
                        </dd>
                        {avgThrow !== undefined && (
                          <dd className="text-muted-foreground">
                            (Avg: {avgThrow})
                          </dd>
                        )}
                      </div>
                    )}

                    {oneHanded && twoHanded && (
                      <>
                        <div className="flex flex-wrap gap-x-2">
                          <dt className="font-semibold text-muted-foreground">
                            One-Handed:
                          </dt>
                          <dd className="text-foreground">
                            {oneHanded}
                            {damageType ? ` ${damageType}` : ""}
                          </dd>
                          {avgOne !== undefined && (
                            <dd className="text-muted-foreground">
                              (Avg: {avgOne})
                            </dd>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-x-2">
                          <dt className="font-semibold text-muted-foreground">
                            Two-Handed:
                          </dt>
                          <dd className="text-foreground">
                            {twoHanded}
                            {damageType ? ` ${damageType}` : ""}
                          </dd>
                          {avgTwo !== undefined && (
                            <dd className="text-muted-foreground">
                              (Avg: {avgTwo})
                            </dd>
                          )}
                        </div>
                      </>
                    )}

                    {properties.length > 0 && (
                      <div className="flex flex-wrap gap-x-2">
                        <dt className="font-semibold text-muted-foreground">
                          Properties:
                        </dt>
                        <dd className="text-muted-foreground">
                          {properties.join(", ")}
                        </dd>
                      </div>
                    )}

                    {masteryApplicable && mastery && (
                      <div className="flex flex-wrap items-center gap-x-2">
                        <dt className="font-semibold text-muted-foreground">
                          Mastery:
                        </dt>
                        <dd>
                          <span
                            className={cn(
                              "rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wide",
                              masteryIsSelected
                                ? "border-primary bg-primary/15 text-primary font-semibold"
                                : "border-border bg-secondary/60 text-muted-foreground",
                            )}
                          >
                            {mastery}
                          </span>
                        </dd>
                      </div>
                    )}
                  </dl>

                  {damageNotes.length > 0 && (
                    <ul className="mt-2 space-y-0.5 text-[11px] text-emerald-400/90">
                      {damageNotes.map((n, j) => (
                        <li key={j}>+ {n}</li>
                      ))}
                    </ul>
                  )}

                  {!proficient && (
                    <div className="mt-2 text-[11px] text-amber-400">
                      ⚠ Not proficient — no proficiency bonus applied
                    </div>
                  )}
                </li>
              );
            })}
          </ul>

          {bestCombination && (
            <div className="mt-3 rounded border border-border bg-background/40 p-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Two-Weapon Combination
              </div>
              <div className="mt-1 text-sm font-semibold text-foreground">
                {bestCombinationName}
              </div>
              <div className="mt-2 grid gap-2">
                {renderCombinationWeaponLine("Mainhand", bestMainhand)}
                {renderCombinationWeaponLine("Offhand (Bonus Action)", bestOffhand)}
              </div>
              {comboNotes.length > 0 && (
                <ul className="mt-2 space-y-0.5 text-[11px] text-emerald-400/90">
                  {comboNotes.map((note, idx) => (
                    <li key={idx}>+ {note}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
    </Section>
  );
}

function Proficiencies({ c }: { c: Char }) {
  const groups: Array<[string, string[]]> = [
    ["Armor", arr<string>(c.armor_proficiencies)],
    ["Weapons", arr<string>(c.weapon_proficiencies)],
    ["Tools", arr<string>(c.tool_proficiencies)],
  ];
  return (
    <Section title="Proficiencies">
      <div className="space-y-2 text-sm">
        {groups.map(([label, list]) => (
          <div key={label}>
            <div className="text-xs uppercase text-muted-foreground">
              {label}
            </div>
            <div>{list.length > 0 ? list.join(", ") : "—"}</div>
          </div>
        ))}
      </div>
    </Section>
  );
}

function Languages({ c }: { c: Char }) {
  const langs = arr<string>(c.languages);
  const darkvision = c.darkvision as number | undefined;
  return (
    <Section title="Languages & Senses">
      <div className="space-y-3">
        <div>
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-1">
            Languages
          </p>
          <p className="text-sm">{langs.length > 0 ? langs.join(", ") : "—"}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-1">
            Darkvision
          </p>
          <p className="text-sm">
            {darkvision && darkvision > 0 ? `${darkvision} feet` : "None"}
          </p>
        </div>
      </div>
    </Section>
  );
}

function Spells({
  c,
  spellApplicable,
  onPrepareSpells,
}: {
  c: Char;
  spellApplicable?: boolean;
  onPrepareSpells?: () => void;
}) {
  const byLevel = rec(c.spells_by_level);
  const slots = rec(c.spell_slots);
  const stats = rec(c.spellcasting_stats);
  const hasSpellcasting = stats.has_spellcasting === true;
  const effectiveCasterLevelFromStats = num(stats.effective_caster_level);
  const effectiveCasterLevel =
    effectiveCasterLevelFromStats && effectiveCasterLevelFromStats > 0
      ? effectiveCasterLevelFromStats
      : (num(c.level) ?? effectiveCasterLevelFromStats);
  const statsPactMagicSlots = arr<Record<string, unknown>>(
    stats.pact_magic_slots,
  );
  const topLevelPactMagicSlots = arr<Record<string, unknown>>(
    c.pact_magic_slots,
  );
  const pactMagicSlots =
    statsPactMagicSlots.length > 0
      ? statsPactMagicSlots
      : topLevelPactMagicSlots;
  const statsMulticlassNotes = arr<string>(stats.multiclass_notes);
  const topLevelSpellSlotNotes = arr<string>(c.spell_slot_notes);
  const multiclassNotes =
    statsMulticlassNotes.length > 0
      ? statsMulticlassNotes
      : topLevelSpellSlotNotes;
  const levels = Object.keys(byLevel).sort((a, b) => Number(a) - Number(b));

  if (
    !hasSpellcasting &&
    levels.length === 0 &&
    Object.keys(slots).length === 0
  ) {
    return null;
  }

  const ability = str(stats.spellcasting_ability);
  const saveDC = num(stats.spell_save_dc);
  const attackBonus = num(stats.spell_attack_bonus);
  const castingMod = num(stats.spellcasting_modifier);
  const cantripsAlwaysPrepared = num(stats.cantrips_always_prepared) ?? 0;
  const cantripsToChoose = num(stats.cantrips_to_prepare);
  const cantripsPrepared =
    num(stats.cantrips_always_prepared) !== undefined ||
    cantripsToChoose !== undefined
      ? cantripsAlwaysPrepared + (cantripsToChoose ?? 0)
      : undefined;
  const maxCantrips = num(stats.max_cantrips_prepared);
  const spellsPreparedTotal = num(stats.spells_prepared);
  const maxSpells =
    num(stats.max_spells_to_prepare) ?? num(stats.max_spells_prepared);
  const ritual = stats.ritual_casting === true;

  return (
    <div className="mt-6">
      <Section
        title="Spellcasting"
        titleRight={
          spellApplicable &&
          onPrepareSpells && (
            <Button size="sm" onClick={onPrepareSpells}>
              Prepare Spells
            </Button>
          )
        }
      >
        {hasSpellcasting && (
          <>
            <dl className="grid grid-cols-2 sm:grid-cols-4 gap-y-3 gap-x-6 text-sm">
              <Stat label="Spellcasting Ability" value={ability ?? "—"} />
              <Stat label="Spell Save DC" value={saveDC ?? "—"} />
              <Stat label="Spell Attack Bonus" value={signed(attackBonus)} />
              <Stat label="Spellcasting Modifier" value={signed(castingMod)} />
              {effectiveCasterLevel !== undefined && (
                <Stat
                  label="Effective Caster Level"
                  value={effectiveCasterLevel}
                />
              )}
              {maxCantrips !== undefined &&
                (() => {
                  const cantripsDisplay =
                    cantripsAlwaysPrepared > 0
                      ? `${cantripsToChoose ?? 0} / ${maxCantrips} (+${cantripsAlwaysPrepared})`
                      : `${cantripsPrepared ?? 0} / ${maxCantrips}`;
                  return (
                    <Stat label="Cantrips Known" value={cantripsDisplay} />
                  );
                })()}
              {maxSpells !== undefined &&
                (() => {
                  const alwaysPreparedCount =
                    num(stats.spells_always_prepared) ?? 0;
                  const userPrepared =
                    (spellsPreparedTotal ?? 0) - alwaysPreparedCount;
                  const preparedDisplay =
                    alwaysPreparedCount > 0
                      ? `${userPrepared} / ${maxSpells} (+${alwaysPreparedCount})`
                      : `${spellsPreparedTotal ?? 0} / ${maxSpells}`;
                  return (
                    <Stat label="Prepared Spells" value={preparedDisplay} />
                  );
                })()}
              {ritual && <Stat label="Ritual Casting" value="Yes" />}
            </dl>

            {Object.keys(slots).length > 0 && (
              <div className="mt-4 rounded border border-primary/60 bg-primary/5 p-3">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary">
                  Spell Slots
                </div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(slots).map(([lvl, n]) => (
                    <div
                      key={lvl}
                      className="flex flex-col items-center gap-0.5"
                    >
                      <span className="text-xs uppercase tracking-wide text-muted-foreground">
                        {slotLevelOrdinal(lvl)}
                      </span>
                      <span className="text-xs font-semibold text-foreground">
                        {String(n)}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="mt-2 text-[11px] text-muted-foreground">
                  You regain all expended slots when you finish a Long Rest.
                </div>
              </div>
            )}

            {pactMagicSlots.length > 0 && (
              <div className="mt-4 rounded border border-primary/60 bg-primary/5 p-3">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary">
                  Pact Magic Slots
                </div>
                <div className="flex flex-wrap gap-2">
                  {pactMagicSlots.map((entry, i) => {
                    const slotLevel = num(entry.slot_level);
                    const slotCount = num(entry.slots);
                    return (
                      <div
                        key={`pact-${slotLevel ?? "x"}-${i}`}
                        className="flex flex-col items-center gap-0.5"
                      >
                        <span className="text-xs uppercase tracking-wide text-muted-foreground">
                          {slotLevelOrdinal(String(slotLevel ?? 0))}
                        </span>
                        <span className="text-xs font-semibold text-foreground">
                          {String(slotCount ?? 0)}
                        </span>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-2 text-[11px] text-muted-foreground">
                  You regain all expended slots when you finish a Short Rest.
                </div>
              </div>
            )}

            {multiclassNotes.length > 0 && (
              <div className="mt-3 rounded border border-border/70 bg-background/30 p-3">
                <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Multiclass Notes
                </div>
                <ul className="space-y-1 text-xs text-muted-foreground">
                  {multiclassNotes.map((note, i) => (
                    <li key={`${note}-${i}`}>• {note}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}

        {!hasSpellcasting && levels.length > 0 && (
          <div className="mb-4 rounded-lg border border-border/70 bg-muted/20 p-3 text-xs text-muted-foreground">
            <span className="font-semibold text-foreground">Innate & Feat Spells:</span>{" "}
            This character does not have spell slots from a spellcasting class. Spells granted by feats, species traits, or class features are cast without expending spell slots (cantrips at will, 1st-level feat spells once per Long Rest for free). Each spell displays its specific ability, save DC, and attack bonus below.
          </div>
        )}

        {levels.length > 0 && (
          <div className="mt-4 space-y-5 text-sm">
            {levels.map((lvl) => {
              const ABILITY_NAMES = new Set([
                "Strength",
                "Dexterity",
                "Constitution",
                "Intelligence",
                "Wisdom",
                "Charisma",
              ]);
              const list = arr<Record<string, unknown>>(byLevel[lvl]).filter(
                (sp) => !ABILITY_NAMES.has(str(sp.name) ?? ""),
              );
              if (list.length === 0) return null;
              return (
                <div key={lvl}>
                  <div className="mb-2 text-sm font-semibold uppercase tracking-wide text-primary">
                    {lvl === "0" ? "Cantrips" : `Level ${lvl}`}
                  </div>
                  <ul className="space-y-3">
                    {list.map((sp, i) => {
                      const name = str(sp.name) ?? "Spell";
                      const school = str(sp.school);
                      const castingTime = str(sp.casting_time);
                      const range = str(sp.range);
                      const components = arr<string>(sp.components).join(", ");
                      const duration = str(sp.duration);
                      const description = str(sp.description);
                      const source = str(sp.source);
                      const showSource = source && source !== "Selected";
                      const spAbility = str(sp.spellcasting_ability);
                      const spDC = num(sp.spell_save_dc);
                      const spAttack = num(sp.spell_attack_bonus);
                      const isFreePerLongRest = sp.once_per_long_rest === true || sp.once_per_day === true;
                      const isAtWill = lvl === "0" || sp.at_will === true;
                      const meta: Array<[string, string | undefined]> = [
                        ["School", school],
                        ["Casting Time", castingTime],
                        ["Range", range],
                        ["Components", components || undefined],
                        ["Duration", duration],
                      ];
                      if (spAbility) meta.push(["Ability", spAbility]);
                      if (spDC !== undefined && spDC > 0) meta.push(["Save DC", String(spDC)]);
                      if (spAttack !== undefined) meta.push(["Attack", signed(spAttack)]);
                      return (
                        <li
                          key={`${name}-${i}`}
                          className="rounded border border-border bg-background/40 p-3"
                        >
                          <div className="flex flex-wrap items-center gap-2 font-semibold text-foreground">
                            <span>{name}</span>
                            {sp.concentration === true && (
                              <span className="shrink-0 rounded bg-amber-600/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white" title="Concentration">
                                C
                              </span>
                            )}
                            {sp.always_prepared === true && (
                              <span className="shrink-0 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[11px] uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
                                Always Prepared
                              </span>
                            )}
                            {isFreePerLongRest && (
                              <span className="shrink-0 rounded-full border border-sky-500/40 bg-sky-500/10 px-2 py-0.5 text-[11px] uppercase tracking-wide text-sky-700 dark:text-sky-300">
                                1 / Long Rest (Free)
                              </span>
                            )}
                            {isAtWill && (
                              <span className="shrink-0 rounded-full border border-purple-500/40 bg-purple-500/10 px-2 py-0.5 text-[11px] uppercase tracking-wide text-purple-700 dark:text-purple-300">
                                At-Will
                              </span>
                            )}
                          </div>
                          <div className="mt-1 text-xs text-muted-foreground">
                            {meta
                              .filter(([, v]) => v)
                              .map(([k, v], j, all) => (
                                <span key={k}>
                                  <span className="font-semibold">{k}:</span>{" "}
                                  {v}
                                  {j < all.length - 1 ? " | " : ""}
                                </span>
                              ))}
                          </div>
                          {isFreePerLongRest && (
                            <p className="mt-1.5 text-xs text-sky-600 dark:text-sky-400 font-medium">
                              Can be cast once per Long Rest without expending a spell slot.
                            </p>
                          )}
                          {description && (
                            <p className="mt-2 text-xs text-foreground/90">
                              {description}
                            </p>
                          )}
                          {showSource && (
                            <p className="mt-1 text-[11px] italic text-muted-foreground">
                              Source: {source}
                            </p>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
          </div>
        )}
      </Section>
    </div>
  );
}

function formatFeatureDescription(desc: string): string {
  return desc.replace(/\*\*(.*?)\*\*/g, '<strong class="text-foreground font-semibold">$1</strong>');
}

function Features({
  c,
  isWildHeartBarbarian,
  currentAspect,
  onOpenAspectDialog,
}: {
  c: Char;
  isWildHeartBarbarian?: boolean;
  currentAspect?: string;
  onOpenAspectDialog?: () => void;
}) {
  const features = rec(c.features);
  const entries = Object.entries(features);
  if (entries.length === 0) return null;
  return (
    <div className="mt-6">
      <Section title="Features">
        <div className="space-y-4 text-sm">
          {entries.map(([category, list]) => {
            const items = arr<Record<string, unknown>>(list);
            if (items.length === 0) return null;
            return (
              <div key={category}>
                <div className="text-xs uppercase text-muted-foreground mb-1">
                  {category}
                </div>
                <ul className="space-y-2">
                  {items.map((f, i) => {
                    const featName = str(f.name) ?? "Feature";
                    const isAspect =
                      featName === "Aspect of the Wilds" && isWildHeartBarbarian;

                    return (
                      <li
                        key={i}
                        className="rounded border border-border bg-background/40 p-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium text-primary">
                            {featName}
                          </span>
                          <div className="flex items-center gap-1.5">
                            {isAspect && currentAspect && (
                              <span className="rounded border border-primary/40 bg-primary/15 px-2 py-0.5 text-[10px] font-semibold text-primary">
                                Active: {currentAspect}
                              </span>
                            )}
                            {num(f.level) !== undefined && (
                              <span className="shrink-0 rounded bg-secondary/80 px-1.5 py-0.5 text-[10px] text-muted-foreground uppercase tracking-wide">
                                Level {num(f.level)}
                              </span>
                            )}
                          </div>
                        </div>
                        {str(f.description) && (
                          <div
                            className="feature-description text-xs text-muted-foreground mt-2 whitespace-pre-line leading-relaxed"
                            dangerouslySetInnerHTML={{
                              __html: formatFeatureDescription(
                                str(f.description) as string,
                              ),
                            }}
                          />
                        )}
                        {isAspect && onOpenAspectDialog && (
                          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-border/50 pt-2.5">
                            <span className="text-xs text-muted-foreground">
                              Change your aspect whenever you finish a Long Rest:
                            </span>
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs"
                              onClick={onOpenAspectDialog}
                            >
                              Change Aspect (Long Rest)
                            </Button>
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>
      </Section>
    </div>
  );
}
