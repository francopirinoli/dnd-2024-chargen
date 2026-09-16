import { useEffect } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { Check, ChevronRight, Leaf, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type { SpeciesSummary } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useCharacterStore } from "@/store/characterStore";
import { useSupplementStore } from "@/store/supplementStore";
import { ChoiceList } from "@/components/wizard/ChoiceList";
import { FeatChoicesPicker } from "@/components/wizard/FeatChoicesPicker";
import { useWizardSidebarPanel } from "@/components/layout/useWizardSidebarPanel";

interface TraitChoice {
  description?: string;
  options?: Array<string | { name?: string }>;
  option_descriptions?: Record<string, string>;
  count?: number;
}

interface LineageEntry {
  id: string;
  name: string;
  description?: string;
  traits?: Record<string, unknown>;
}

/**
 * The backend returns `lineages` enriched with variant data
 * (`{id, name, description, traits}`). For older payloads we still
 * accept arrays of strings or dict maps and fall back gracefully.
 */
function normalizeLineages(raw: unknown): LineageEntry[] {
  if (!raw) return [];
  if (Array.isArray(raw)) {
    return raw.map((item, i) => {
      if (typeof item === "string") {
        return { id: item, name: item };
      }
      if (item && typeof item === "object") {
        const o = item as Record<string, unknown>;
        const id =
          (typeof o.id === "string" && o.id) ||
          (typeof o.name === "string" && o.name) ||
          String(i);
        return {
          id,
          name: typeof o.name === "string" ? o.name : id,
          description:
            typeof o.description === "string" ? o.description : undefined,
          traits:
            o.traits && typeof o.traits === "object"
              ? (o.traits as Record<string, unknown>)
              : undefined,
        };
      }
      return { id: String(i), name: String(i) };
    });
  }
  if (typeof raw === "object") {
    return Object.entries(raw as Record<string, unknown>).map(([id, v]) => {
      const o = v && typeof v === "object" ? (v as Record<string, unknown>) : {};
      return {
        id,
        name: typeof o.name === "string" ? o.name : id,
        description:
          typeof o.description === "string" ? o.description : undefined,
        traits:
          o.traits && typeof o.traits === "object"
            ? (o.traits as Record<string, unknown>)
            : undefined,
      };
    });
  }
  return [];
}

interface GrantedSpell {
  spell: string;
  level: "cantrip" | number;
}

function extractGrantedSpells(traits: Record<string, unknown>): GrantedSpell[] {
  const spells: GrantedSpell[] = [];
  for (const traitValue of Object.values(traits)) {
    if (!traitValue || typeof traitValue !== "object" || Array.isArray(traitValue)) continue;
    const effects = (traitValue as Record<string, unknown>).effects;
    if (!Array.isArray(effects)) continue;
    for (const effect of effects) {
      if (!effect || typeof effect !== "object") continue;
      const e = effect as Record<string, unknown>;
      if (e.type === "grant_cantrip" && typeof e.spell === "string") {
        spells.push({ spell: e.spell, level: "cantrip" });
      } else if (e.type === "grant_spell" && typeof e.spell === "string") {
        spells.push({ spell: e.spell, level: typeof e.min_level === "number" ? e.min_level : 1 });
      }
    }
  }
  return spells;
}

function traitDescription(value: unknown): string | undefined {
  if (typeof value === "string") return value;
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const d = (value as Record<string, unknown>).description;
    if (typeof d === "string") return d;
  }
  return undefined;
}

export function SpeciesStep() {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const setChoice = useCharacterStore((s) => s.setChoice);
  const selectedSpecies = (choicesMade["species"] as string | undefined) ?? "";
  const { setSidebarPanel } = useWizardSidebarPanel();

  const activeSources = useSupplementStore((s) => s.activeSources);

  const speciesQuery = useQuery({
    queryKey: ["catalog", "species", activeSources],
    queryFn: () => api.catalog.species(activeSources),
  });

  const previewQuery = useQuery({
    queryKey: ["character", "preview-step", "species", choicesMade, activeSources],
    queryFn: () =>
      api.character.previewStep(
        { ...choicesMade, active_sources: activeSources },
        "species",
      ),
    enabled: !!selectedSpecies,
    placeholderData: keepPreviousData,
  });

  const fullSpeciesQuery = useQuery({
    queryKey: ["catalog", "species", selectedSpecies],
    queryFn: () => api.catalog.getSpecies(selectedSpecies),
    enabled: !!selectedSpecies,
    placeholderData: keepPreviousData,
  });

  const selectedSpeciesSummary = (speciesQuery.data ?? []).find(
    (sp) => sp.id === selectedSpecies,
  );

  const fullSpeciesData = fullSpeciesQuery.isPlaceholderData
    ? undefined
    : (fullSpeciesQuery.data as Record<string, unknown> | undefined);

  useEffect(() => {
    setSidebarPanel(
      selectedSpeciesSummary
        ? (
            <SpeciesInfoPanel
              selectedSpeciesSummary={selectedSpeciesSummary}
              fullSpeciesData={fullSpeciesData}
              speciesLoading={(fullSpeciesQuery.isLoading || fullSpeciesQuery.isPlaceholderData) && !fullSpeciesData}
            />
          )
        : null,
    );
    return () => setSidebarPanel(null);
  }, [selectedSpeciesSummary, fullSpeciesData, fullSpeciesQuery.isLoading, fullSpeciesQuery.isPlaceholderData, setSidebarPanel]);

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card to-secondary/40 shadow-sm">
        <div className="border-b border-border/70 px-5 py-5 sm:px-6">
          <div className="flex items-start gap-3">
            <div className="rounded-full bg-primary/10 p-2 text-primary">
              <Leaf className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Primary choice
              </p>
              <h3 className="mt-1 font-display text-2xl text-primary font-bold">
                Choose your species
              </h3>
              <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
                Your species determines what lineage and species-specific follow-up
                options appear below.
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                You can continue without selecting one, but species details and
                related choices will remain hidden for now.
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
          <div>
            {speciesQuery.isLoading && (
              <p className="text-xs text-muted-foreground">Loading species…</p>
            )}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 items-start">
              {(speciesQuery.data ?? []).map((sp) => {
                const isSelected = selectedSpecies === sp.id;
                return (
                  <button
                    key={sp.id}
                    type="button"
                    onClick={() => setChoice("species", sp.id)}
                    aria-pressed={isSelected}
                    className={cn(
                      "group rounded-xl border p-4 text-left transition-all duration-200",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                      isSelected
                        ? "border-primary bg-muted/60 shadow-md ring-1 ring-primary/20"
                        : "border-border/80 bg-background/75 hover:-translate-y-1 hover:border-primary/40 hover:bg-secondary/50 hover:shadow-md",
                    )}
                  >
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div>
                        <div className="font-display text-xl text-primary font-semibold">
                          {sp.name}
                        </div>
                        {sp.source && sp.source !== "core-phb-2024" && (
                          <div className="mt-1">
                            <span className="inline-block text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full border border-primary/40 bg-primary/10 text-primary">
                              {sp.source_title || sp.source}
                            </span>
                          </div>
                        )}
                      </div>
                      <span
                        className={cn(
                          "inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border transition-colors",
                          isSelected
                            ? "border-primary bg-background text-primary"
                            : "border-border bg-background text-transparent group-hover:border-primary/40",
                        )}
                      >
                        <Check className="h-4 w-4" />
                      </span>
                    </div>

                    <dl className="text-xs text-muted-foreground/80 space-y-1">
                      {sp.size !== undefined && (
                        <div>
                          <span className="font-semibold">Size:</span>{" "}
                          {String(sp.size)}
                        </div>
                      )}
                      {sp.speed !== undefined && (
                        <div>
                          <span className="font-semibold">Speed:</span>{" "}
                          {typeof sp.speed === "number"
                            ? `${sp.speed} ft`
                            : Object.entries(sp.speed)
                                .map(([k, v]) => `${k} ${v} ft`)
                                .join(" · ")}
                        </div>
                      )}
                      {sp.darkvision !== undefined && sp.darkvision > 0 && (
                        <div>
                          <span className="font-semibold">Darkvision:</span>{" "}
                          {sp.darkvision} ft
                        </div>
                      )}
                    </dl>

                    {sp.description && (
                      <div className="mt-2 text-sm text-muted-foreground line-clamp-3">
                        {sp.description}
                      </div>
                    )}

                    <div className="mt-4 flex items-center justify-between text-xs font-medium text-muted-foreground">
                      <span>
                        {isSelected ? "Selected species" : "Click to select"}
                      </span>
                      <span className="inline-flex items-center gap-1 text-primary/80">
                        {isSelected ? "Details on panel" : "Select to view details"}
                        <ChevronRight className="h-3.5 w-3.5" />
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

        </div>
      </section>

      {selectedSpecies && previewQuery.data && (
        <SpeciesDetail previewData={previewQuery.data} />
      )}
    </div>
  );
}

function SpeciesTraits({ traits }: { traits: Record<string, unknown> }) {
  const entries = Object.entries(traits);
  if (entries.length === 0) return null;
  return (
    <div className="mt-6">
      <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-background px-3 py-1 text-xs font-medium text-primary">
        <Sparkles className="h-3.5 w-3.5" />
        Species traits
      </div>
      <ul className="mt-2 space-y-3">
        {entries.map(([name, value]) => {
          const desc = traitDescription(value);
          return (
            <li key={name} className="info-panel-block">
              <p className="font-semibold text-sm">{name}</p>
              {desc && (
                <div className="mt-1 rounded-md border border-border/60 bg-background px-3 py-2">
                  <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    Trait details
                  </p>
                  <p className="mt-1 text-sm text-foreground/85">{desc}</p>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function SpeciesInfoPanel({
  selectedSpeciesSummary,
  fullSpeciesData,
  speciesLoading,
}: {
  selectedSpeciesSummary?: SpeciesSummary;
  fullSpeciesData?: Record<string, unknown>;
  speciesLoading?: boolean;
}) {
  const traits = fullSpeciesData?.traits as Record<string, unknown> | undefined;

  return (
    <aside className="info-panel" aria-label="Species details panel">
      <div className="info-panel-header">
        <p className="info-panel-kicker">Informational panel</p>
        <h4 className="info-panel-title">
          {selectedSpeciesSummary?.name ?? "Select a species"}
        </h4>
      </div>
      <div className="info-panel-body">
        {!selectedSpeciesSummary && (
          <p className="mt-2 text-xs text-muted-foreground">
            Previewing species details. Select a species card to view full
            information.
          </p>
        )}
        {selectedSpeciesSummary?.description && (
          <p className="mt-3 text-sm text-muted-foreground">
            {selectedSpeciesSummary.description}
          </p>
        )}
        {selectedSpeciesSummary && (
          <div className="mt-4 grid grid-cols-1 gap-2">
            {selectedSpeciesSummary.size !== undefined && (
              <div className="rounded-lg border border-border/70 bg-background/80 px-3 py-2">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Size
                </div>
                <div className="mt-1 font-medium text-foreground">
                  {String(selectedSpeciesSummary.size)}
                </div>
              </div>
            )}
            {selectedSpeciesSummary.speed !== undefined && (
              <div className="rounded-lg border border-border/70 bg-background/80 px-3 py-2">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Speed
                </div>
                <div className="mt-1 font-medium text-foreground">
                  {typeof selectedSpeciesSummary.speed === "number"
                    ? `${selectedSpeciesSummary.speed} ft`
                    : Object.entries(selectedSpeciesSummary.speed)
                        .map(([k, v]) => `${k} ${v} ft`)
                        .join(" · ")}
                </div>
              </div>
            )}
            {selectedSpeciesSummary.darkvision !== undefined &&
              selectedSpeciesSummary.darkvision > 0 && (
                <div className="rounded-lg border border-border/70 bg-background/80 px-3 py-2">
                  <div className="text-xs uppercase tracking-wide text-muted-foreground">
                    Darkvision
                  </div>
                  <div className="mt-1 font-medium text-foreground">
                    {selectedSpeciesSummary.darkvision} ft
                  </div>
                </div>
              )}
          </div>
        )}
        {selectedSpeciesSummary && speciesLoading && (
          <div className="mt-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-background px-3 py-1 text-xs font-medium text-primary">
              <Sparkles className="h-3.5 w-3.5 animate-pulse" />
              Loading species traits…
            </div>
          </div>
        )}
        {traits && <SpeciesTraits traits={traits} />}
      </div>
    </aside>
  );
}

function SpeciesDetail({
  previewData,
}: {
  previewData: Record<string, unknown>;
}) {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const setChoice = useCharacterStore((s) => s.setChoice);

  const lineageEntries = normalizeLineages(previewData["lineages"]);
  const selectedLineage = (choicesMade["lineage"] as string | undefined) ?? "";

  const traitChoices = (previewData["trait_choices"] as
    | Record<string, TraitChoice>
    | undefined) ?? {};

  const speciesFeat = previewData["species_feat_choices"] as
    | Parameters<typeof FeatChoicesPicker>[0]["data"]
    | undefined;

  // The background grants one origin feat; disable that option in the species
  // feat picker so the player can't double-pick it (e.g. Human "Versatile").
  const backgroundFeat = (previewData["background_feat"] as string | undefined) ?? undefined;

  const grantedProficiencies = (() => {
    const gp = previewData["granted_proficiencies"] as
      | { skills?: string[]; tools?: string[] }
      | undefined;
    return [
      ...(gp?.skills ?? []),
      ...(gp?.tools ?? []),
    ];
  })();

  return (
    <div className="space-y-6">
      {lineageEntries.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold mb-3">Choose a lineage</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 items-start">
            {lineageEntries.map((entry) => {
              const isSelected = selectedLineage === entry.id;
              const traitEntries = Object.entries(entry.traits ?? {});
              return (
                <button
                  key={entry.id}
                  type="button"
                  onClick={() => setChoice("lineage", entry.id)}
                  aria-pressed={isSelected}
                  className={cn(
                    "group flex h-full w-full flex-col items-stretch rounded-xl border p-4 text-left transition-all duration-200",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                    isSelected
                      ? "border-primary bg-muted/60 shadow-md ring-1 ring-primary/20"
                      : "border-border/80 bg-background/75 hover:-translate-y-1 hover:border-primary/40 hover:bg-secondary/50 hover:shadow-md",
                  )}
                >
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div className="font-display text-lg text-primary font-semibold">
                      {entry.name}
                    </div>
                    <span
                      className={cn(
                        "inline-flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border transition-colors",
                        isSelected
                          ? "border-primary bg-background text-primary"
                          : "border-border bg-background text-transparent group-hover:border-primary/40",
                      )}
                    >
                      <Check className="h-3.5 w-3.5" />
                    </span>
                  </div>
                  {entry.description && (
                    <p className="text-xs text-muted-foreground">
                      {entry.description}
                    </p>
                  )}
                  {traitEntries.length > 0 && (
                    <div className="mt-3 border-t border-border pt-3">
                      <dl className="space-y-2 text-xs">
                        {traitEntries.map(([traitName, traitValue]) => {
                          const desc = traitDescription(traitValue);
                          return (
                            <div key={traitName}>
                              <dt className="inline font-semibold text-foreground">
                                {traitName}:
                              </dt>{" "}
                              {desc && (
                                <dd className="inline text-muted-foreground">
                                  {desc}
                                </dd>
                              )}
                            </div>
                          );
                        })}
                      </dl>
                    </div>
                  )}
                  {(() => {
                    const spells = extractGrantedSpells(entry.traits ?? {});
                    if (spells.length === 0) return null;
                    return (
                      <div className="mt-3 border-t border-border pt-3">
                        <div className="mb-1.5 flex items-center gap-1 text-xs font-semibold text-primary">
                          <Sparkles className="h-3 w-3" />
                          Granted spells
                        </div>
                        <ul className="space-y-1">
                          {spells.map((s) => (
                            <li key={s.spell} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                              <span className="inline-flex items-center rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                                {s.level === "cantrip" ? "Cantrip" : `Lvl ${s.level}+`}
                              </span>
                              {s.spell}
                            </li>
                          ))}
                        </ul>
                      </div>
                    );
                  })()}
                  <div className="mt-4 flex items-center justify-between text-xs font-medium text-muted-foreground">
                    <span>
                      {isSelected
                        ? "Selected lineage"
                        : "Click to select lineage"}
                    </span>
                    <span className="inline-flex items-center gap-1 text-primary/80">
                      {isSelected ? "Lineage selected" : "Select lineage"}
                      <ChevronRight className="h-3.5 w-3.5" />
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </section>
      )}

      {Object.keys(traitChoices).length > 0 && (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold">Species trait choices</h3>
          {Object.entries(traitChoices).map(([traitName, choice]) => (
            <ChoiceList
              key={traitName}
              choiceKey={traitName}
              parentKey="species_trait_choices"
              title={traitName}
              description={choice.description}
              options={choice.options ?? []}
              optionDescriptions={choice.option_descriptions}
              count={choice.count ?? 1}
              disabledOptions={[
                ...(backgroundFeat ? [backgroundFeat] : []),
                ...grantedProficiencies,
              ]}
            />
          ))}
        </section>
      )}

      {speciesFeat && speciesFeat.feat_name && (
        <FeatChoicesPicker
          data={speciesFeat}
          heading="Species feat"
          grantedProficiencies={grantedProficiencies}
        />
      )}
    </div>
  );
}
