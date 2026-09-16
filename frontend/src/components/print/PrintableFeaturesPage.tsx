type Char = Record<string, unknown>;

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}
function num(v: unknown): number | undefined {
  return typeof v === "number" ? v : undefined;
}
function arr<T = unknown>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}
function rec(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : {};
}

export interface FeatureSection {
  title: string;
  list: Array<Record<string, unknown>>;
  defaultBadge: string;
}

interface PrintableFeaturesPageProps {
  c?: Char;
  title?: string;
  subtitle?: string;
  sections?: FeatureSection[];
}

export function PrintableFeaturesPage({
  c,
  title = "Features, Traits & Feats Reference",
  subtitle = "Complete descriptions of all abilities, racial traits, subclass powers, and feats.",
  sections: propSections,
}: PrintableFeaturesPageProps) {
  let sections: FeatureSection[] = [];

  if (propSections) {
    sections = propSections;
  } else if (c) {
    const features = rec(c.features);
    const classFeatures = arr<Record<string, unknown>>(features.class);
    const subclassFeatures = arr<Record<string, unknown>>(features.subclass);
    const speciesTraits = arr<Record<string, unknown>>(features.species);
    const lineageTraits = arr<Record<string, unknown>>(features.lineage);
    const feats = arr<Record<string, unknown>>(features.feats);
    const backgroundTraits = arr<Record<string, unknown>>(features.background);

    sections = [
      { title: "Class Features", list: classFeatures, defaultBadge: "Class" },
      { title: "Subclass Features", list: subclassFeatures, defaultBadge: "Subclass" },
      {
        title: "Species & Lineage Traits",
        list: [...speciesTraits, ...lineageTraits],
        defaultBadge: "Species",
      },
      { title: "Feats & Abilities", list: feats, defaultBadge: "Feat" },
      { title: "Background & Origin", list: backgroundTraits, defaultBadge: "Background" },
    ].filter((sec) => sec.list.length > 0);
  }

  return (
    <div className="flex flex-col gap-3 text-slate-900 leading-tight">
      <div className="border-b-2 border-slate-900 pb-1 mb-1">
        <h2 className="font-display text-base font-bold text-slate-950 uppercase tracking-wide">
          {title}
        </h2>
        <p className="text-[10.5px] text-slate-600">{subtitle}</p>
      </div>

      {/* Structured Sections with 2-Column Grid */}
      <div className="space-y-3">
        {sections.map((section) => (
          <div key={section.title} className="mb-2">
            {/* Section Banner */}
            <div className="bg-slate-800 text-white px-2.5 py-1 rounded-t-md font-display font-bold text-xs uppercase tracking-wider mb-1.5 flex items-center justify-between">
              <span>{section.title}</span>
              <span className="text-[9.5px] font-normal text-slate-300">
                {section.list.length} {section.list.length === 1 ? "entry" : "entries"}
              </span>
            </div>

            {/* List of Feature Cards in a 2-Column Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {section.list.map((feat, idx) => {
                const name = str(feat.name) ?? "Feature";
                const desc = str(feat.description) ?? "";
                const level = num(feat.level);
                const source = str(feat.source) ?? section.defaultBadge;

                // Check for rest/use patterns (e.g. "1/Long Rest", "2/Short Rest")
                const matchUses = desc.match(/(\d+)\s*\/\s*(Short|Long)\s*Rest/i);
                const useCount = matchUses ? parseInt(matchUses[1], 10) : 0;

                return (
                  <div
                    key={idx}
                    className="avoid-break break-inside-avoid bg-white border border-slate-300 rounded-sm p-2 shadow-2xs flex flex-col justify-between"
                    style={{ breakInside: "avoid", pageBreakInside: "avoid" }}
                  >
                    <div>
                      <div className="flex items-start justify-between gap-1 border-b border-slate-200 pb-1 mb-1">
                        <span className="font-display font-bold text-xs text-slate-950">
                          {name}
                        </span>
                        <div className="flex items-center gap-1 shrink-0">
                          {useCount > 0 && useCount <= 6 && (
                            <span className="font-mono text-[9px] text-slate-600 bg-slate-100 px-1 rounded">
                              {Array.from({ length: useCount }).map(() => "[ ]").join(" ")}
                            </span>
                          )}
                          <span className="text-[8.5px] font-semibold text-slate-500 uppercase tracking-tighter bg-slate-100 px-1 py-0.5 rounded">
                            {level ? `Lvl ${level}` : source}
                          </span>
                        </div>
                      </div>
                      <p className="text-[10px] text-slate-750 whitespace-pre-line leading-relaxed">
                        {desc}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
