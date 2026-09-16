import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useCharacterStore } from "@/store/characterStore";
import { Button } from "@/components/ui/button";
import { Printer, ArrowLeft, Sparkles } from "lucide-react";
import { PrintablePageLayout } from "@/components/print/PrintablePageLayout";
import { PrintableCombatPage } from "@/components/print/PrintableCombatPage";
import { PrintableFeaturesPage } from "@/components/print/PrintableFeaturesPage";
import { PrintableSpellsPage } from "@/components/print/PrintableSpellsPage";
import { PrintableEquipmentPage } from "@/components/print/PrintableEquipmentPage";

type Char = Record<string, unknown>;

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}
function num(v: unknown): number | undefined {
  return typeof v === "number" ? v : undefined;
}
function rec(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : {};
}
function arr<T = unknown>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}

const PRINT_CSS = `
@media print {
  @page {
    size: letter portrait;
    margin: 0.35in;
  }
  *, *::before, *::after {
    box-sizing: border-box !important;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
    scrollbar-width: none !important;
    -ms-overflow-style: none !important;
  }
  *::-webkit-scrollbar {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
  }
  html, body, #root, #root > div, .min-h-screen, main {
    background: #ffffff !important;
    background-color: #ffffff !important;
    color: #000000 !important;
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
  }
  .no-print {
    display: none !important;
  }
  .printable-page {
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    box-shadow: none !important;
    width: 100% !important;
    max-width: none !important;
    min-height: 0 !important;
    background: #ffffff !important;
    background-color: #ffffff !important;
    break-after: page !important;
    page-break-after: always !important;
    break-before: page !important;
    page-break-before: always !important;
  }
  .printable-page:first-of-type {
    break-before: auto !important;
    page-break-before: auto !important;
  }
  .printable-page:last-of-type {
    break-after: auto !important;
    page-break-after: auto !important;
  }
  .avoid-break {
    break-inside: avoid !important;
    page-break-inside: avoid !important;
  }
  /* Remove scrollbars and overflows in print */
  .overflow-x-auto, .overflow-y-auto, .overflow-auto, .overflow-hidden {
    overflow: visible !important;
  }
}
`;

export function SheetPdf() {
  const choicesMade = useCharacterStore((s) => s.choicesMade);

  const buildQuery = useQuery({
    queryKey: ["character", "build", choicesMade],
    queryFn: () => api.character.build(choicesMade),
    retry: false,
    placeholderData: keepPreviousData,
  });

  const [includeCombat, setIncludeCombat] = useState(true);
  const [includeFeatures, setIncludeFeatures] = useState(true);
  const [includeSpells, setIncludeSpells] = useState(true);
  const [includeEquipment, setIncludeEquipment] = useState(true);

  if (buildQuery.isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 dark:bg-slate-900 text-slate-700 dark:text-slate-300">
        <div className="text-center p-8 bg-white dark:bg-slate-800 rounded-xl shadow-md border border-slate-200 dark:border-slate-700 max-w-sm">
          <Sparkles className="h-8 w-8 animate-spin mx-auto text-primary mb-3" />
          <p className="font-display font-semibold text-lg">Building Character Sheet…</p>
          <p className="text-xs text-muted-foreground mt-1">Preparing high-resolution printable layout</p>
        </div>
      </div>
    );
  }

  if (buildQuery.error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 dark:bg-slate-900 p-4">
        <div className="max-w-md w-full p-6 text-center bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-destructive/40">
          <h2 className="font-display text-xl text-destructive font-bold mb-2">Unable to Build Sheet</h2>
          <p className="text-xs text-muted-foreground mb-4">{String(buildQuery.error)}</p>
          <Button asChild variant="default">
            <Link to="/wizard">Return to Wizard</Link>
          </Button>
        </div>
      </div>
    );
  }

  const c = (buildQuery.data ?? {}) as Char;
  const name = str(c.name) ?? str(c.character_name) ?? "Character";
  const cls = str(c.class) ?? "Adventurer";
  const lvl = num(c.level) ?? 1;
  const subclass = str(c.subclass);
  const subhead = `${cls} ${lvl}${subclass ? ` (${subclass})` : ""}`;

  // Check if character has spellcasting
  const stats = rec(c.spellcasting_stats);
  const spellsByLevel = rec(c.spells_by_level);
  const spellSlots = rec(c.spell_slots);
  const hasSpells =
    stats.has_spellcasting === true ||
    Object.keys(spellsByLevel).length > 0 ||
    Object.keys(spellSlots).length > 0;

  // Compute active pages
  const activePages: Array<{ id: string; title: string; component: React.ReactNode }> = [];

  if (includeCombat) {
    activePages.push({
      id: "combat",
      title: "Combat & Vitals",
      component: <PrintableCombatPage c={c} />,
    });
  }

  if (includeFeatures) {
    const features = rec(c.features);
    const classFeatures = arr<Record<string, unknown>>(features.class);
    const subclassFeatures = arr<Record<string, unknown>>(features.subclass);
    const speciesTraits = arr<Record<string, unknown>>(features.species);
    const lineageTraits = arr<Record<string, unknown>>(features.lineage);
    const feats = arr<Record<string, unknown>>(features.feats);
    const backgroundTraits = arr<Record<string, unknown>>(features.background);

    const classSections = [
      { title: "Class Features", list: classFeatures, defaultBadge: "Class" },
      { title: "Subclass Features", list: subclassFeatures, defaultBadge: "Subclass" },
    ].filter((s) => s.list.length > 0);

    const charSections = [
      { title: "Species & Lineage Traits", list: [...speciesTraits, ...lineageTraits], defaultBadge: "Species" },
      { title: "Feats & Abilities", list: feats, defaultBadge: "Feat" },
      { title: "Background & Origin", list: backgroundTraits, defaultBadge: "Background" },
    ].filter((s) => s.list.length > 0);

    const totalFeaturesCount =
      classFeatures.length +
      subclassFeatures.length +
      speciesTraits.length +
      lineageTraits.length +
      feats.length +
      backgroundTraits.length;

    if (totalFeaturesCount > 8 && classSections.length > 0 && charSections.length > 0) {
      activePages.push({
        id: "features_class",
        title: "Class Features & Powers",
        component: (
          <PrintableFeaturesPage
            title="Class & Subclass Features"
            subtitle="Core class progression, tactical abilities, and subclass powers."
            sections={classSections}
          />
        ),
      });
      activePages.push({
        id: "features_character",
        title: "Species Traits & Feats",
        component: (
          <PrintableFeaturesPage
            title="Species Traits & Feats"
            subtitle="Racial lineage traits, origin feats, and general abilities."
            sections={charSections}
          />
        ),
      });
    } else {
      activePages.push({
        id: "features",
        title: "Features & Traits",
        component: (
          <PrintableFeaturesPage
            c={c}
            title="Features, Traits & Feats Reference"
            subtitle="Complete descriptions of all abilities, racial traits, subclass powers, and feats."
          />
        ),
      });
    }
  }

  if (hasSpells && includeSpells) {
    activePages.push({
      id: "spells",
      title: "Spells & Magic",
      component: <PrintableSpellsPage c={c} />,
    });
  }

  if (includeEquipment) {
    activePages.push({
      id: "equipment",
      title: "Equipment & Roleplay Details",
      component: <PrintableEquipmentPage c={c} choicesMade={choicesMade} />,
    });
  }

  const totalPages = activePages.length;

  return (
    <div className="min-h-screen bg-slate-200/80 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col items-center print:bg-white print:text-black">
      <style>{PRINT_CSS}</style>

      {/* ── Sticky Print Controls Bar (No Print) ── */}
      <header className="no-print sticky top-0 z-40 w-full bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-300 dark:border-slate-800 px-4 py-3 shadow-xs">
        <div className="max-w-5xl mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <Button asChild variant="ghost" size="sm" className="h-8 gap-1.5 text-xs font-semibold">
              <Link to="/sheet">
                <ArrowLeft className="h-3.5 w-3.5" />
                Back to Sheet
              </Link>
            </Button>
            <div className="h-4 w-px bg-slate-300 dark:bg-slate-700 hidden sm:block" />
            <div>
              <h1 className="font-display text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100">
                {name} <span className="font-normal text-xs text-slate-500">— Printable Sheet</span>
              </h1>
            </div>
          </div>

          {/* Page Checkboxes & Print Trigger */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="hidden lg:flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 mr-2 bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded-md border border-slate-200 dark:border-slate-700">
              <span className="font-semibold text-slate-700 dark:text-slate-200">Include:</span>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeCombat}
                  onChange={(e) => setIncludeCombat(e.target.checked)}
                  className="rounded text-primary focus:ring-0"
                />
                Combat
              </label>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeFeatures}
                  onChange={(e) => setIncludeFeatures(e.target.checked)}
                  className="rounded text-primary focus:ring-0"
                />
                Features
              </label>
              {hasSpells && (
                <label className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeSpells}
                    onChange={(e) => setIncludeSpells(e.target.checked)}
                    className="rounded text-primary focus:ring-0"
                  />
                  Spells
                </label>
              )}
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeEquipment}
                  onChange={(e) => setIncludeEquipment(e.target.checked)}
                  className="rounded text-primary focus:ring-0"
                />
                Equipment
              </label>
            </div>

            <Button
              onClick={() => window.print()}
              size="sm"
              className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold shadow-sm gap-2 h-9 px-4"
            >
              <Printer className="h-4 w-4" />
              <span>Print to PDF</span>
            </Button>
          </div>
        </div>

        {/* Helpful Print Tip Banner */}
        <div className="max-w-5xl mx-auto mt-2 pt-2 border-t border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
          <span>
            💡 <strong>Print Tip:</strong> In your browser print dialog, select <strong>Save as PDF</strong>, set Margins to <strong>Default</strong> or <strong>None</strong>. No background images required.
          </span>
          <span className="font-mono text-slate-600 dark:text-slate-300 font-semibold">
            {totalPages} {totalPages === 1 ? "Page" : "Pages"} Generated
          </span>
        </div>
      </header>

      {/* ── Document Container ── */}
      <main className="w-full flex-1 py-4 sm:py-6 px-2 sm:px-4 flex flex-col items-center print:p-0 print:m-0 print:w-full print:bg-white">
        {activePages.map((page, idx) => (
          <PrintablePageLayout
            key={page.id}
            pageNumber={idx + 1}
            totalPages={totalPages}
            characterName={name}
            characterSubhead={subhead}
            pageTitle={page.title}
            isFirstPage={idx === 0}
          >
            {page.component}
          </PrintablePageLayout>
        ))}
      </main>
    </div>
  );
}
