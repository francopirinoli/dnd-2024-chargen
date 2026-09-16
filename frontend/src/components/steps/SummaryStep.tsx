import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { AlertCircle, BookmarkCheck, CheckCircle2, ChevronRight, Circle, Download, Loader2, Save } from "lucide-react";
import { api, type WizardStep } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useCharacterStore } from "@/store/characterStore";
import { useRosterStore } from "@/store/rosterStore";
import { Button } from "@/components/ui/button";

interface Props {
  steps: WizardStep[];
}

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

export function SummaryStep({ steps }: Props) {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const saveCurrent = useRosterStore((s) => s.saveCurrent);
  const [savedFlash, setSavedFlash] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const validateQuery = useQuery({
    queryKey: ["character", "validate", choicesMade],
    queryFn: () => api.character.validate(choicesMade),
    placeholderData: keepPreviousData,
  });

  const buildQuery = useQuery({
    queryKey: ["character", "build", choicesMade],
    queryFn: () => api.character.build(choicesMade),
    retry: false,
    placeholderData: keepPreviousData,
  });

  const stepLabel = new Map(steps.map((s) => [s.id, s.label]));
  const statuses = validateQuery.data?.steps ?? [];
  const incomplete = statuses.filter((s) => !s.complete);
  const allComplete = statuses.length > 0 && incomplete.length === 0;

  const character = (buildQuery.data ?? {}) as Char;
  const buildError = buildQuery.error ? String(buildQuery.error) : null;

  const name = str(character.name) || str(character.character_name) || "Unnamed";
  const cls = str(character.class);
  const sub = str(character.subclass);
  const species = str(character.species);
  const lineage = str(character.lineage);
  const bg = str(character.background);
  const level = num(character.level);
  const alignment = str(character.alignment);

  const combat = rec(character.combat);
  const hp = rec(combat.hit_points);
  const hpMax = num(hp.maximum) ?? num(combat.hp);
  const acOptions = arr<Record<string, unknown>>(character.ac_options);
  const topAc = acOptions[0] ? num(rec(acOptions[0]).ac) : undefined;
  const speed = num(character.speed) ?? num(combat.speed);
  const init = num(combat.initiative_bonus) ?? num(combat.initiative);
  const pb = num(character.proficiency_bonus);
  const passive = num(combat.passive_perception);

  const abilityOrder = [
    "Strength",
    "Dexterity",
    "Constitution",
    "Intelligence",
    "Wisdom",
    "Charisma",
  ];
  const abilities = rec(character.abilities);
  const abilityScores = rec(character.ability_scores);
  function abilityRow(a: string) {
    const direct = rec(abilities[a.toLowerCase()]);
    const score =
      num(direct.score) ??
      num(abilityScores[a]) ??
      num(abilityScores[a.toLowerCase()]);
    const mod = num(direct.modifier) ?? num(direct.mod);
    return { score, mod };
  }

  const languages = arr<string>(character.languages);
  const features = arr<Record<string, unknown>>(character.features);

  function handleSave() {
    setSaveError(null);
    const characterName =
      typeof choicesMade.character_name === "string"
        ? choicesMade.character_name
        : name;
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

  function handleExport() {
    const baseName = safeFilename(name);
    downloadJson(`${baseName}-choices.json`, {
      version: 1,
      exported_at: new Date().toISOString(),
      choices_made: choicesMade,
    });
  }

  return (
    <div className="space-y-8">
      {/* Validation */}
      <section className="info-panel">
        <div className="info-panel-header">
          <p className="info-panel-kicker">Completion checklist</p>
        </div>
        <div className="info-panel-body">
          {validateQuery.isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-xs">Checking…</span>
            </div>
          )}
          {validateQuery.error && (
            <p className="text-xs text-destructive">
              {String(validateQuery.error)}
            </p>
          )}
          {!validateQuery.isLoading && !validateQuery.error && (
            <>
              {allComplete ? (
                <div className="flex items-center gap-2 rounded-md bg-green-500/10 border border-green-500/30 p-3 mb-4">
                  <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
                  <p className="text-sm font-semibold text-green-700 dark:text-green-400">All required choices made. Ready to play.</p>
                </div>
              ) : (
                <>
                  {incomplete.length > 0 && (
                    <div className="rounded-md bg-destructive/10 border border-destructive/20 p-4 mb-4">
                      <div className="flex items-start gap-2">
                        <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                        <div>
                          <h4 className="font-semibold text-destructive mb-1">
                            Incomplete selections
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {incomplete.length} step{incomplete.length === 1 ? "" : "s"} still need attention.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
              <ul className="mt-3 space-y-1.5 text-sm">
                {statuses.map((s) => {
                  const label = stepLabel.get(s.step) ?? s.step;
                  return (
                    <li key={s.step} className="flex items-start gap-2">
                      {s.complete ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                      ) : (
                        <Circle className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <Link
                          to={`/wizard/${s.step}`}
                          className={
                            s.complete
                              ? "text-foreground hover:text-primary"
                              : "text-foreground hover:text-primary underline"
                          }
                        >
                          {label}
                        </Link>
                        {!s.complete && s.missing.length > 0 && (
                          <ul className="mt-0.5 space-y-0.5">
                            {s.missing.map((m) => (
                              <li key={m} className="text-xs text-muted-foreground ml-1">• {m}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </div>
      </section>

      {/* Build error */}
      {buildError && (
        <section className="rounded-md border border-destructive/40 bg-destructive/10 p-4">
          <h2 className="font-display text-2xl text-destructive mb-1">
            Build failed
          </h2>
          <p className="text-sm text-destructive">{buildError}</p>
          <p className="text-xs text-muted-foreground mt-2">
            Resolve the items above and the character will rebuild
            automatically.
          </p>
        </section>
      )}

      {/* Character preview */}
      {!buildError && (
        <section className="info-panel">
          <div className="info-panel-header">
            <p className="info-panel-kicker">Character preview</p>
            <div className="mt-2">
              <div className={cn("font-display text-2xl", name === "Unnamed" ? "text-muted-foreground italic" : "text-primary")}>{name}</div>
              <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 mt-1 text-sm text-muted-foreground">
                {level !== undefined && <span>Level {level}</span>}
                {cls && <><span aria-hidden>·</span><span>{cls}</span></>}
                {sub && <span className="text-muted-foreground/70">({sub})</span>}
                {species && <><span aria-hidden>·</span><span>{species}</span></>}
                {lineage && <span className="text-muted-foreground/70">({lineage})</span>}
                {bg && <><span aria-hidden>·</span><span>{bg}</span></>}
                {alignment && <><span aria-hidden>·</span><span>{alignment}</span></>}
              </div>
            </div>
          </div>
          <div className="info-panel-body space-y-5">
            {buildQuery.isLoading && !buildQuery.data ? (
              <div className="flex items-center justify-center gap-2 text-muted-foreground py-6">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-sm">Building character…</span>
              </div>
            ) : (
              <>
                <dl className="grid grid-cols-2 sm:grid-cols-3 gap-y-4 gap-x-6 text-sm">
                  <Stat label="HP" value={hpMax} />
                  <Stat label="AC" value={topAc} />
                  <Stat
                    label="Speed"
                    value={speed !== undefined ? `${speed} ft` : undefined}
                  />
                  <Stat label="Initiative" value={signed(init)} />
                  <Stat label="Prof. Bonus" value={signed(pb)} />
                  <Stat label="Passive Perc." value={passive} />
                </dl>

                <div className="grid grid-cols-6 gap-2">
                  {abilityOrder.map((a) => {
                    const v = abilityRow(a);
                    return (
                      <div key={a} className="info-panel-block text-center">
                        <div className="text-[10px] uppercase text-muted-foreground">
                          {a.slice(0, 3)}
                        </div>
                        <div className="text-lg font-semibold mt-0.5">
                          {v.score ?? "—"}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {signed(v.mod)}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {languages.length > 0 && (
                  <div className="text-sm">
                    <span className="text-xs uppercase tracking-widest text-muted-foreground mr-2">
                      Languages
                    </span>
                    {languages.join(", ")}
                  </div>
                )}

                {features.length > 0 && (
                  <details className="info-panel-block">
                    <summary className="cursor-pointer select-none text-xs uppercase tracking-widest text-muted-foreground">
                      Features ({features.length})
                    </summary>
                    <ul className="mt-3 space-y-1 text-sm">
                      {features.slice(0, 30).map((f, i) => {
                        const fname = str(f.name) ?? str(f.feature) ?? "Feature";
                        const source = str(f.source);
                        return (
                          <li key={i} className="flex justify-between gap-3">
                            <span>{fname}</span>
                            {source && (
                              <span className="text-xs text-muted-foreground">
                                {source}
                              </span>
                            )}
                          </li>
                        );
                      })}
                      {features.length > 30 && (
                        <li className="text-xs text-muted-foreground">
                          + {features.length - 30} more…
                        </li>
                      )}
                    </ul>
                  </details>
                )}
              </>
            )}
          </div>
        </section>
      )}

      {/* Actions */}
      <section className="space-y-4">
        <div className="rounded-xl border border-primary/30 bg-primary/5 p-6 text-center">
          <h2 className="font-display text-2xl text-foreground mb-1">Ready to play?</h2>
          <p className="text-sm text-muted-foreground mb-5">
            {allComplete
              ? "Your character is complete and ready to play."
              : "You can view your sheet and finish filling in details there."}
          </p>
          <Button size="lg" asChild>
            <Link to="/sheet">
              View character sheet <ChevronRight className="h-4 w-4 ml-1" />
            </Link>
          </Button>
        </div>
        <div className="info-panel">
          <div className="info-panel-header">
            <p className="info-panel-kicker">Save &amp; Export</p>
          </div>
          <div className="info-panel-body space-y-4">
            <div className="flex items-start gap-3">
              <Button variant="outline" size="sm" className="shrink-0 w-44 justify-start" onClick={handleSave}>
                {savedFlash ? (
                  <><BookmarkCheck className="h-4 w-4 mr-1.5 text-green-600" />Saved!</>
                ) : (
                  <><Save className="h-4 w-4 mr-1.5" />Save to roster</>
                )}
              </Button>
              <p className="text-xs text-muted-foreground pt-1.5">
                Saves this character to your local browser roster so you can load it again from the home page.
              </p>
            </div>
            {saveError && (
              <p className="text-xs text-destructive">{saveError}</p>
            )}
            <div className="flex items-start gap-3">
              <Button variant="outline" size="sm" className="shrink-0 w-44 justify-start" onClick={handleExport}>
                <Download className="h-4 w-4 mr-1.5" />Download character
              </Button>
              <p className="text-xs text-muted-foreground pt-1.5">
                Downloads your choices as a JSON file. You can re-import it later from the home page to restore this character.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
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
