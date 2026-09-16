import { cn } from "@/lib/utils";

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

function formatDesc(text: string): string {
  return text.replace(/\*\*(.*?)\*\*/g, '<strong class="text-slate-950 font-semibold">$1</strong>');
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
    <div className="flex flex-col gap-2.5 text-slate-900 leading-tight">
      <div className="border-b-2 border-slate-900 pb-1 mb-0.5">
        <h2 className="font-display text-base font-black text-slate-950 uppercase tracking-wide">
          {title}
        </h2>
        <p className="text-[10px] text-slate-600">{subtitle}</p>
      </div>

      {/* Structured Sections with Multi-Column Masonry Packing */}
      <div className="space-y-2.5">
        {sections.map((section) => (
          <div key={section.title} className="avoid-break break-inside-avoid-page">
            {/* Compact Section Banner */}
            <div className="bg-slate-900 text-white px-2 py-0.5 rounded-t font-display font-bold text-[11px] uppercase tracking-wider mb-1 flex items-center justify-between">
              <span>{section.title}</span>
              <span className="text-[8.5px] font-normal text-slate-300">
                {section.list.length} {section.list.length === 1 ? "entry" : "entries"}
              </span>
            </div>

            {/* List of Feature Cards in Multi-Column Masonry for Optimal Space Usage */}
            <div className="columns-1 sm:columns-2 gap-1.5 [column-fill:balance]">
              {section.list.map((feat, idx) => {
                const name = str(feat.name) ?? "Feature";
                const desc = str(feat.description) ?? "";
                const level = num(feat.level);
                const source = str(feat.source) ?? section.defaultBadge;
                const category = str(feat.category);
                const prereq = str(feat.prerequisite);
                const benefits = arr<string>(feat.benefits);

                // Check for rest/use patterns (e.g. "1/Long Rest", "2/Short Rest")
                const matchUses = desc.match(/(\d+)\s*\/\s*(Short|Long)\s*Rest/i);
                const useCount = matchUses ? parseInt(matchUses[1], 10) : 0;

                return (
                  <div
                    key={idx}
                    className="break-inside-avoid mb-1.5 bg-white border border-slate-300 rounded p-1.5 shadow-2xs flex flex-col justify-between text-[9px] hover:border-slate-400 transition-colors"
                    style={{ breakInside: "avoid", pageBreakInside: "avoid" }}
                  >
                    <div>
                      {/* Card Header */}
                      <div className="flex items-start justify-between gap-1 border-b border-slate-200 pb-0.5 mb-1">
                        <div className="min-w-0">
                          <span className="font-display font-bold text-[10.5px] text-slate-950 block leading-tight">
                            {name}
                          </span>
                          {prereq && prereq.toLowerCase() !== "none" && (
                            <span className="text-[7.5px] font-medium text-slate-500 italic block">
                              Prereq: {prereq}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-1 shrink-0">
                          {useCount > 0 && useCount <= 6 && (
                            <span className="font-mono text-[8px] font-bold text-slate-700 bg-slate-100 border border-slate-200 px-1 py-0.2 rounded">
                              {Array.from({ length: useCount }).map(() => "[ ]").join(" ")}
                            </span>
                          )}
                          <span
                            className={cn(
                              "text-[8px] font-semibold uppercase tracking-tight px-1 py-0.2 rounded",
                              category
                                ? "bg-amber-100 text-amber-900 border border-amber-200"
                                : "bg-slate-100 text-slate-700 border border-slate-200"
                            )}
                          >
                            {category ? `${category} Feat` : level ? `Lvl ${level}` : source}
                          </span>
                        </div>
                      </div>

                      {/* Card Description */}
                      {desc && (
                        <div
                          className="text-slate-800 leading-[1.35] whitespace-pre-line"
                          dangerouslySetInnerHTML={{ __html: formatDesc(desc) }}
                        />
                      )}

                      {/* Benefits Bullets if structured */}
                      {benefits.length > 0 && (
                        <ul className="mt-1 space-y-0.5 text-slate-800 leading-[1.3] list-disc list-inside">
                          {benefits.map((b, bIdx) => (
                            <li
                              key={bIdx}
                              dangerouslySetInnerHTML={{ __html: formatDesc(b) }}
                            />
                          ))}
                        </ul>
                      )}
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
