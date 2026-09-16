import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useCharacterStore } from "@/store/characterStore";

interface ComputedCombat {
  hp?: number;
  hit_points?: number;
  armor_class?: number;
  ac?: number;
  speed?: number;
  initiative?: number;
  proficiency_bonus?: number;
}

interface ComputedCharacter {
  name?: string;
  character_name?: string;
  class?: string;
  subclass?: string;
  species?: string;
  lineage?: string;
  background?: string;
  level?: number;
  combat?: ComputedCombat;
  ability_scores?: Record<string, number>;
  abilities?: Record<string, { score?: number; modifier?: number }>;
  features?: Record<string, Array<{ name: string; description?: string }>>;
}

function readNumber(...vals: Array<unknown>): number | undefined {
  for (const v of vals) {
    if (typeof v === "number") return v;
  }
  return undefined;
}

/**
 * Live computed-effects panel. Posts the current `choices_made` to
 * `/api/v1/character/build` and surfaces the headline calculated values.
 *
 * Failures are expected mid-wizard (e.g. before a class is picked) and
 * are rendered as a friendly hint, not an error.
 */
export function EffectsPanel() {
  const choicesMade = useCharacterStore((s) => s.choicesMade);

  const buildQuery = useQuery({
    queryKey: ["character", "build", choicesMade],
    queryFn: () => api.character.build(choicesMade),
    retry: false,
    placeholderData: keepPreviousData,
  });

  if (buildQuery.isLoading && !buildQuery.data) {
    return (
      <div className="rounded-md border border-border bg-card/50 p-4 text-sm text-muted-foreground">
        Computing…
      </div>
    );
  }

  if (buildQuery.error && !buildQuery.data) {
    return (
      <div className="rounded-md border border-border bg-card/50 p-4 text-sm text-muted-foreground">
        <p className="font-semibold text-foreground mb-1">Effects</p>
        <p className="text-xs">
          Pick a class, species, and background to see computed stats.
        </p>
      </div>
    );
  }

  const c = ((buildQuery.data as { character?: ComputedCharacter } | undefined)?.character ??
    (buildQuery.data as ComputedCharacter | undefined) ??
    {}) as ComputedCharacter;
  const combat = c.combat ?? {};
  const hp = readNumber(combat.hp, combat.hit_points);
  const ac = readNumber(combat.armor_class, combat.ac);
  const pb = readNumber(combat.proficiency_bonus);
  const speed = readNumber(combat.speed);
  const init = readNumber(combat.initiative);

  const features = c.features ?? {};
  const featureRows: Array<{ category: string; name: string }> = [];
  for (const [category, list] of Object.entries(features)) {
    for (const f of list) {
      if (f && typeof f.name === "string") {
        featureRows.push({ category, name: f.name });
      }
    }
  }

  return (
    <div className="rounded-md border border-border bg-card/50 p-4">
      <h3 className="font-display text-lg font-semibold text-primary mb-3">
        {c.name || c.character_name || "Unnamed"}
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        {c.species ?? "—"}
        {c.lineage ? ` (${c.lineage})` : ""} ·{" "}
        {c.class ?? "—"}
        {c.subclass ? ` (${c.subclass})` : ""} · Lv {c.level ?? "—"}
        {c.background ? ` · ${c.background}` : ""}
      </p>

      <dl className="grid grid-cols-2 gap-y-2 gap-x-4 text-sm">
        <Stat label="HP" value={hp} />
        <Stat label="AC" value={ac} />
        <Stat label="Prof" value={pb !== undefined ? `+${pb}` : undefined} />
        <Stat label="Speed" value={speed !== undefined ? `${speed} ft` : undefined} />
        <Stat label="Init" value={init !== undefined ? (init >= 0 ? `+${init}` : String(init)) : undefined} />
      </dl>

      {c.abilities && (
        <div className="mt-4">
          <p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">
            Abilities
          </p>
          <div className="grid grid-cols-3 gap-1 text-xs">
            {Object.entries(c.abilities).map(([name, data]) => {
              const score = readNumber(data?.score);
              const mod = readNumber(data?.modifier);
              return (
                <div
                  key={name}
                  className="rounded border border-border bg-background/40 px-2 py-1"
                >
                  <div className="font-semibold uppercase">
                    {name.slice(0, 3)}
                  </div>
                  <div>
                    {score ?? "—"}
                    {mod !== undefined && (
                      <span className="ml-1 text-muted-foreground">
                        ({mod >= 0 ? "+" : ""}
                        {mod})
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {featureRows.length > 0 && (
        <details className="mt-4">
          <summary className="cursor-pointer text-xs uppercase tracking-widest text-muted-foreground">
            Features ({featureRows.length})
          </summary>
          <ul className="mt-2 space-y-1 text-xs max-h-64 overflow-auto">
            {featureRows.slice(0, 60).map((f, i) => (
              <li key={`${f.category}-${f.name}-${i}`}>
                <span className="text-primary">{f.name}</span>
                <span className="text-muted-foreground"> · {f.category}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
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
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-semibold">{value ?? "—"}</dd>
    </>
  );
}
