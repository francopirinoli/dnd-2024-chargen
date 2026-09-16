import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Dice6, Package, ScrollText, Sword, Trash2 } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { SupplementManagerDialog } from "@/components/supplements/SupplementManagerDialog";
import { useCharacterStore } from "@/store/characterStore";
import { useRosterStore } from "@/store/rosterStore";
import { useSupplementStore } from "@/store/supplementStore";
import { summarizeChoices } from "@/lib/persistence";
import { SAMPLE_CHARACTERS } from "@/data/sampleCharacters";
import { useBugReportUrl } from "@/hooks/useBugReportUrl";

export function Home() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const reset = useCharacterStore((s) => s.reset);
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const rosterEntries = useRosterStore((s) => s.entries);
  const rosterLoaded = useRosterStore((s) => s.loaded);
  const loadRoster = useRosterStore((s) => s.load);
  const saveCurrent = useRosterStore((s) => s.saveCurrent);
  const deleteEntry = useRosterStore((s) => s.delete);
  const bugReportUrl = useBugReportUrl();
  const activeSources = useSupplementStore((s) => s.activeSources);
  const supplementDialogOpen = useSupplementStore((s) => s.dialogOpen);
  const setSupplementDialogOpen = useSupplementStore((s) => s.setDialogOpen);

  const [importError, setImportError] = useState<string | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [saveName, setSaveName] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedFlash, setSavedFlash] = useState<string | null>(null);
  const [deleteDialogEntry, setDeleteDialogEntry] = useState<{
    id: string;
    name: string;
  } | null>(null);

  useEffect(() => {
    if (!rosterLoaded) {
      void loadRoster();
    }
  }, [rosterLoaded, loadRoster]);

  const hasInProgress = Object.keys(choicesMade).length > 0;
  const inProgressSummary = hasInProgress
    ? summarizeChoices(choicesMade)
    : "";

  function applyChoices(choices: Record<string, unknown>, navigateToSheet = false) {
    // Replace persisted store state directly so the import lands atomically
    // without firing per-key cascade invalidation.
    useCharacterStore.setState({ choicesMade: choices, currentStepId: null });
    queryClient.removeQueries({ queryKey: ["character"] });
    queryClient.removeQueries({ queryKey: ["wizard"] });
    if (navigateToSheet) navigate("/sheet");
  }

  function extractChoices(parsed: unknown): Record<string, unknown> {
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("File does not contain a valid choices object.");
    }
    const obj = parsed as Record<string, unknown>;
    let choices: unknown = obj;
    if (
      obj.choices_made &&
      typeof obj.choices_made === "object" &&
      !Array.isArray(obj.choices_made)
    ) {
      choices = obj.choices_made;
    } else if (
      obj.choices &&
      typeof obj.choices === "object" &&
      !Array.isArray(obj.choices)
    ) {
      choices = obj.choices;
    }
    if (!choices || typeof choices !== "object" || Array.isArray(choices)) {
      throw new Error("File does not contain a valid choices object.");
    }
    return choices as Record<string, unknown>;
  }

  function importFromText(text: string) {
    const trimmed = text.trim();
    if (!trimmed) {
      throw new Error("Paste some JSON first.");
    }
    const parsed: unknown = JSON.parse(trimmed);
    const choices = extractChoices(parsed);
    applyChoices(choices);
  }

  async function handleFile(file: File) {
    setImportError(null);
    try {
      importFromText(await file.text());
      setImportOpen(false);
      setPasteText("");
      navigate("/wizard");
    } catch (err) {
      setImportError(
        err instanceof Error ? err.message : "Failed to read character file.",
      );
    }
  }

  function handlePasteImport() {
    setImportError(null);
    try {
      importFromText(pasteText);
      setImportOpen(false);
      setPasteText("");
      navigate("/wizard");
    } catch (err) {
      setImportError(
        err instanceof Error ? err.message : "Invalid JSON.",
      );
    }
  }

  function handleSaveCurrent() {
    setSaveError(null);
    if (!hasInProgress) {
      setSaveError("Nothing to save yet — start the wizard first.");
      return;
    }
    const name =
      saveName.trim() ||
      (typeof choicesMade.character_name === "string"
        ? (choicesMade.character_name as string)
        : "Unnamed character");
    saveCurrent(choicesMade, name)
      .then((entry) => {
        setSaveName("");
        setSavedFlash(`Saved “${entry.name}” to your roster.`);
        window.setTimeout(() => setSavedFlash(null), 3000);
      })
      .catch((err: unknown) => {
        setSaveError(
          err instanceof Error ? err.message : "Failed to save character.",
        );
      });
  }

  function handleLoadEntry(id: string, target: "sheet" | "wizard" = "sheet") {
    const entry = rosterEntries.find((e) => e.id === id);
    if (!entry) return;
    applyChoices(entry.choices as Record<string, unknown>);
    navigate(target === "sheet" ? "/sheet" : "/wizard");
  }

  function handleDeleteEntry(id: string, name: string) {
    setDeleteDialogEntry({ id, name });
  }

  function handleConfirmDeleteEntry() {
    if (!deleteDialogEntry) return;
    void deleteEntry(deleteDialogEntry.id);
    setDeleteDialogEntry(null);
  }

  function handleStartFresh(e: React.MouseEvent) {
    e.preventDefault();
    reset();
    queryClient.removeQueries({ queryKey: ["character"] });
    queryClient.removeQueries({ queryKey: ["wizard"] });
    navigate("/wizard");
  }

  // Pick 3 random characters once on mount
  const [featured] = useState(() => {
    const shuffled = [...SAMPLE_CHARACTERS].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, 3);
  });

  return (
    <main className="min-h-dvh bg-background text-foreground font-sans overflow-x-hidden">
      {/* ── Header Toolbar ─────────────────────────────────────────── */}
      <div className="fixed top-4 right-4 z-20 flex items-center gap-2">
        <button
          type="button"
          onClick={() => setSupplementDialogOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-2 text-sm font-medium text-muted-foreground shadow-sm hover:bg-secondary hover:text-foreground transition-colors"
        >
          <Package className="w-4 h-4 text-primary" />
          <span>Supplements ({activeSources.length})</span>
        </button>
        <a
          href={bugReportUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center rounded-md border border-border bg-background px-3 py-2 text-sm font-medium text-muted-foreground shadow-sm hover:bg-secondary hover:text-foreground transition-colors"
        >
          Bug Report
        </a>
        <ThemeToggle />
      </div>

      {/* ── Content ────────────────────────────────────────────── */}
      <div className="relative z-10">

        {/* ── Hero ───────────────────────────────────────────────── */}
        <section className="min-h-[28rem] border-border flex flex-col items-center justify-center text-center px-6 py-14 gap-6">
          <img
            src="/images/logos/logo.png"
            alt="D&D Character Creator"
            className="w-40 h-40 md:w-52 md:h-52 drop-shadow-2xl"
          />
          <div className="space-y-3 max-w-2xl">
            <h1 className="font-display text-4xl md:text-5xl text-primary tracking-wide leading-tight">
              D&amp;D 2024 Character Builder
            </h1>
            <p className="text-base md:text-lg text-muted-foreground leading-relaxed">
              A fast, rule-compliant character builder for D&amp;D 2024 (One D&amp;D).
              Configure species, class, background, ability scores, feats, spells, and equipment
              with automated calculations, sheet export, and modular supplement support.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 justify-center">
            <button
              type="button"
              onClick={handleStartFresh}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground shadow hover:opacity-90"
            >
              <Sword className="w-4 h-4" />
              {hasInProgress ? "Start New Character" : "Create Character"}
            </button>
            {hasInProgress && (
              <Link
                to="/wizard"
                className="inline-flex items-center rounded-md border border-border px-6 py-2.5 text-sm font-semibold text-foreground hover:bg-secondary"
              >
                Continue Draft
              </Link>
            )}
            <button
              type="button"
              onClick={() => setSupplementDialogOpen(true)}
              className="inline-flex items-center gap-2 rounded-md border border-border px-5 py-2.5 text-sm font-semibold text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            >
              <Package className="w-4 h-4 text-primary" />
              Sources &amp; Supplements ({activeSources.length})
            </button>
          </div>
        </section>

        {/* ── Three Sections ─────────────────────────────────────── */}
        <div className="container py-12 max-w-6xl">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">

          {/* ── 1. Create a Character ─────────────────────────────── */}
          <section className="rounded-lg border border-border bg-card flex flex-col">
            <div className="flex items-center gap-3 px-6 pt-6 pb-4 border-b border-border">
              <span className="rounded-md bg-primary/10 p-2">
                <Sword className="w-5 h-5 text-primary" />
              </span>
              <h2 className="font-display text-xl text-foreground">Create a Character</h2>
            </div>
            <div className="p-6 flex flex-col gap-5 flex-1">
              <p className="text-sm text-muted-foreground leading-relaxed">
                Step-by-step wizard adhering to D&amp;D 2024 rules.
                Choose species, assign background ability bonuses, customize classes,
                configure spells, and select starting gear.
              </p>

              {hasInProgress && (
                <div className="rounded-md border border-primary/30 bg-primary/5 px-4 py-3">
                  <p className="text-sm font-semibold text-foreground">Draft in progress</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{inProgressSummary}</p>
                </div>
              )}

              <div className="mt-auto flex flex-col gap-2 pt-2">
                {hasInProgress && (
                  <Link
                    to="/wizard"
                    className="inline-flex items-center justify-center rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow hover:opacity-90"
                  >
                    Continue Draft
                  </Link>
                )}
                <button
                  type="button"
                  onClick={handleStartFresh}
                  className={
                    hasInProgress
                      ? "inline-flex items-center justify-center rounded-md border border-border px-5 py-2.5 text-sm font-semibold text-foreground hover:bg-secondary"
                      : "inline-flex items-center justify-center rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow hover:opacity-90"
                  }
                >
                  {hasInProgress ? "Start New Character" : "Create Character"}
                </button>
                <Link
                  to="/sheet"
                  className="inline-flex items-center justify-center rounded-md border border-border px-5 py-2 text-sm text-muted-foreground hover:bg-secondary hover:text-foreground"
                >
                  View Character Sheet
                </Link>
              </div>
            </div>
          </section>

          {/* ── 2. Load a Character ───────────────────────────────── */}
          <section className="rounded-lg border border-border bg-card flex flex-col">
            <div className="flex items-center gap-3 px-6 pt-6 pb-4 border-b border-border">
              <span className="rounded-md bg-primary/10 p-2">
                <ScrollText className="w-5 h-5 text-primary" />
              </span>
              <h2 className="font-display text-xl text-foreground">Load a Character</h2>
            </div>
            <div className="p-6 flex flex-col gap-5 flex-1">
              <p className="text-sm text-muted-foreground leading-relaxed">
                Access saved characters in your local browser storage or import an exported character JSON file.
              </p>

              {/* Import from file or JSON */}
              <div className="flex flex-col gap-2">
                <p className="text-xs uppercase tracking-widest text-muted-foreground">
                  Import from file or JSON
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex-1 inline-flex items-center justify-center rounded-md border border-border px-3 py-2 text-xs hover:bg-secondary"
                  >
                    Choose file…
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setImportError(null);
                      setImportOpen((v) => !v);
                    }}
                    className="flex-1 inline-flex items-center justify-center rounded-md border border-border px-3 py-2 text-xs hover:bg-secondary"
                    aria-expanded={importOpen}
                  >
                    {importOpen ? "Cancel paste" : "Paste JSON"}
                  </button>
                </div>

                {importOpen && (
                  <div className="flex flex-col gap-2">
                    <textarea
                      id="paste-json"
                      value={pasteText}
                      onChange={(e) => setPasteText(e.target.value)}
                      placeholder='{ "choices_made": { "character_name": "Aria", ... } }'
                      spellCheck={false}
                      rows={6}
                      className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                    />
                    <button
                      type="button"
                      onClick={handlePasteImport}
                      disabled={!pasteText.trim()}
                      className="self-end inline-flex items-center rounded-md bg-primary px-4 py-1.5 text-xs font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      Import pasted JSON
                    </button>
                  </div>
                )}

                {importError && (
                  <p className="text-xs text-destructive">Import failed: {importError}</p>
                )}
              </div>

              {/* Saved Roster */}
              <div className="flex flex-col gap-3">
                <div className="flex items-baseline justify-between">
                  <p className="text-xs uppercase tracking-widest text-muted-foreground">
                    Saved Roster
                  </p>
                  <span className="text-xs text-muted-foreground">Local browser</span>
                </div>

                {/* Save current progress */}
                <div className="flex gap-2">
                  <input
                    id="save-name"
                    type="text"
                    value={saveName}
                    onChange={(e) => setSaveName(e.target.value)}
                    placeholder={
                      hasInProgress
                        ? typeof choicesMade.character_name === "string"
                          ? (choicesMade.character_name as string)
                          : "Character name"
                        : "Start the wizard first"
                    }
                    disabled={!hasInProgress}
                    className="flex-1 min-w-0 rounded-md border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-40"
                  />
                  <button
                    type="button"
                    onClick={handleSaveCurrent}
                    disabled={!hasInProgress}
                    className="shrink-0 inline-flex items-center rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Save
                  </button>
                </div>
                {saveError && (
                  <p className="text-xs text-destructive">{saveError}</p>
                )}
                {savedFlash && (
                  <p className="text-xs text-emerald-500">{savedFlash}</p>
                )}

                {/* Roster list */}
                {rosterEntries.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">
                    No saved characters yet.
                  </p>
                ) : (
                  <ul className="flex flex-col gap-2 max-h-52 overflow-y-auto pr-1">
                    {rosterEntries.map((entry) => (
                      <li
                        key={entry.id}
                        className="rounded-md border border-border bg-secondary/30 px-3 py-2.5 flex items-center justify-between gap-2"
                      >
                        <div
                          className="min-w-0 flex-1 cursor-pointer"
                          onClick={() => handleLoadEntry(entry.id, "sheet")}
                        >
                          <p className="text-sm font-semibold text-foreground truncate hover:text-primary transition-colors">
                            {entry.name}
                          </p>
                          <p className="text-xs text-muted-foreground truncate">
                            {entry.summary ?? summarizeChoices(entry.choices)}
                            {" · "}
                            {new Date(entry.savedAt).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="flex gap-1.5 shrink-0">
                          <button
                            type="button"
                            onClick={() => handleLoadEntry(entry.id, "sheet")}
                            className="rounded-md border border-primary px-2.5 py-1 text-xs font-semibold text-primary hover:bg-primary/10"
                          >
                            View Sheet
                          </button>
                          <button
                            type="button"
                            onClick={() => handleLoadEntry(entry.id, "wizard")}
                            className="rounded-md border border-border px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-secondary hover:text-foreground"
                            title="Edit in wizard"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteEntry(entry.id, entry.name)}
                            className="rounded-md border border-border p-1 text-muted-foreground hover:text-destructive hover:border-destructive"
                            aria-label={`Delete ${entry.name}`}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </section>

          {/* ── 3. Sample Characters ──────────────────────────────── */}
          <section className="rounded-lg border border-border bg-card flex flex-col">
            <div className="flex items-center gap-3 px-6 pt-6 pb-4 border-b border-border">
              <span className="rounded-md bg-primary/10 p-2">
                <Dice6 className="w-5 h-5 text-primary" />
              </span>
              <h2 className="font-display text-xl text-foreground">Sample Characters</h2>
            </div>
            <div className="p-6 flex flex-col gap-5 flex-1">
              <p className="text-sm text-muted-foreground leading-relaxed">
                Explore pre-built Level 3 archetype characters demonstrating 2024 class mechanics, origin feats, and spell selections.
              </p>

              <ul className="flex flex-col gap-3">
                {featured.map((c) => (
                  <li
                    key={c.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => applyChoices(c.choices, true)}
                    onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && applyChoices(c.choices, true)}
                    className="rounded-md border border-dashed border-border bg-secondary/20 px-3 py-2.5 flex items-center gap-3 cursor-pointer hover:border-primary/50 hover:bg-secondary/40 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50"
                  >
                    <img
                      src={`/images/classes/${c.classKey}-card.png`}
                      alt={c.characterClass}
                      className="h-10 w-10 rounded object-cover object-top shrink-0"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-foreground truncate">{c.name}</p>
                      <p className="text-xs text-primary/80 font-medium">{c.species} {c.characterClass}</p>
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">{c.subclass}</p>
                    </div>
                  </li>
                ))}
              </ul>

              <Link
                to="/characters"
                className="mt-auto inline-flex items-center justify-center rounded-md border border-border px-5 py-2 text-sm text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
              >
                View All 12 Characters →
              </Link>
            </div>
          </section>

        </div>

        </div>

      </div>{/* end content wrapper */}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="application/json,.json"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            void handleFile(file);
          }
          e.target.value = "";
        }}
      />

      <SupplementManagerDialog
        open={supplementDialogOpen}
        onClose={() => setSupplementDialogOpen(false)}
      />

      <ConfirmDialog
        open={Boolean(deleteDialogEntry)}
        title="Delete saved character?"
        description={
          deleteDialogEntry
            ? `Delete "${deleteDialogEntry.name}" from your roster? This cannot be undone.`
            : ""
        }
        confirmLabel="Delete"
        onConfirm={handleConfirmDeleteEntry}
        onCancel={() => setDeleteDialogEntry(null)}
      />
    </main>
  );
}
