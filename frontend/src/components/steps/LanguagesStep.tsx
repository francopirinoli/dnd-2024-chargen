import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { Check, Loader2, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useCharacterStore } from "@/store/characterStore";

interface LanguageOptions {
  base_languages?: string[];
  rare_base_languages?: string[];
  available_languages?: string[];
  standard_available_languages?: string[];
  rare_available_languages?: string[];
  selection_count?: number;
  selected_languages?: string[];
  all_rare_languages?: string[];
  selected_rare_languages?: string[];
}

const LANGUAGES_KEY = "languages";
const RARE_LANGUAGES_KEY = "rare_languages";

export function LanguagesStep() {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const setChoice = useCharacterStore((s) => s.setChoice);

  const previewQuery = useQuery({
    queryKey: ["character", "preview-step", "languages", choicesMade],
    queryFn: () => api.character.previewStep(choicesMade, "languages"),
    placeholderData: keepPreviousData,
  });

  const data =
    (previewQuery.data?.language_options as LanguageOptions | undefined) ?? {};
  const base = data.base_languages ?? ["Common"];
  const rareBase = data.rare_base_languages ?? [];
  const available = data.available_languages ?? [];
  const selectionCount = data.selection_count ?? 2;
  const allRare = data.all_rare_languages ?? [];

  // Reconcile selected from both current key and any legacy rare_languages
  const rawStandard = Array.isArray(choicesMade[LANGUAGES_KEY])
    ? (choicesMade[LANGUAGES_KEY] as string[])
    : [];
  const rawRare = Array.isArray(choicesMade[RARE_LANGUAGES_KEY])
    ? (choicesMade[RARE_LANGUAGES_KEY] as string[])
    : [];

  const combinedRaw = Array.from(new Set([...rawStandard, ...rawRare]));
  const selected = combinedRaw
    .filter((lang) => available.includes(lang))
    .slice(0, selectionCount);

  // Group available languages
  const standardAvailable = data.standard_available_languages ??
    available.filter((l) => !allRare.includes(l));
  const rareAvailable = data.rare_available_languages ??
    available.filter((l) => allRare.includes(l));

  const suggestLanguages = useMutation({
    mutationFn: () => api.character.suggestRandomLanguages(choicesMade),
    onSuccess: (languages) => {
      setChoice(LANGUAGES_KEY, languages);
    },
  });

  function toggle(lang: string) {
    const set = new Set(selected);
    if (set.has(lang)) {
      set.delete(lang);
    } else if (set.size < selectionCount) {
      set.add(lang);
    }
    const nextChoices = Array.from(set);
    setChoice(LANGUAGES_KEY, nextChoices);
    // If there were legacy rare_languages, clear them so they don't conflict
    if (choicesMade[RARE_LANGUAGES_KEY]) {
      setChoice(RARE_LANGUAGES_KEY, []);
    }
  }

  function handleClear() {
    setChoice(LANGUAGES_KEY, []);
    if (choicesMade[RARE_LANGUAGES_KEY]) {
      setChoice(RARE_LANGUAGES_KEY, []);
    }
  }

  const isLoadingInitial =
    (previewQuery.isLoading || previewQuery.isFetching) && available.length === 0;
  const hasNoChoices = !isLoadingInitial && selectionCount === 0;
  const counterAtMax = selected.length >= selectionCount;

  return (
    <div className="space-y-8">
      {/* ── Already Known Section ── */}
      <section>
        <h3 className="font-semibold text-lg">Already known</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Granted automatically by your background, species, or features.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {base.map((lang) => (
            <span
              key={`base-${lang}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-secondary px-3 py-1 text-xs text-muted-foreground"
            >
              <Check className="h-3 w-3" aria-hidden="true" />
              <span>{lang}</span>
            </span>
          ))}
          {rareBase.map((lang) => (
            <span
              key={`rare-base-${lang}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-700 dark:text-amber-400"
            >
              <Check className="h-3 w-3" aria-hidden="true" />
              <span>{lang}</span>
              <span className="ml-0.5 rounded px-1 py-0.2 text-[9px] font-semibold uppercase bg-amber-500/20 text-amber-600 dark:text-amber-300">
                Rare
              </span>
            </span>
          ))}
        </div>
      </section>

      {/* ── Additional Languages Section ── */}
      <section className="space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h3 className="font-semibold text-lg">Additional languages</h3>
            <p className="mt-0.5 text-sm text-muted-foreground">
              Choose exactly {selectionCount} language
              {selectionCount === 1 ? "" : "s"} from the standard or rare options below.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "rounded-full px-3 py-1 text-xs font-semibold border transition-colors",
                counterAtMax
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-muted/50 text-muted-foreground",
              )}
            >
              {selected.length} of {selectionCount} selected
            </span>
            <button
              type="button"
              onClick={() => suggestLanguages.mutate()}
              disabled={previewQuery.isLoading || suggestLanguages.isPending}
              className={cn(
                "inline-flex h-8 items-center justify-center rounded-md border border-border bg-background px-2.5 text-xs font-medium",
                "hover:bg-secondary hover:text-foreground transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                "disabled:opacity-50 disabled:pointer-events-none",
              )}
            >
              {suggestLanguages.isPending ? "Rolling…" : `Roll ${selectionCount}`}
            </button>
            <button
              type="button"
              onClick={handleClear}
              disabled={selected.length === 0}
              className={cn(
                "inline-flex h-8 items-center justify-center rounded-md px-2.5 text-xs font-medium text-muted-foreground",
                "hover:bg-secondary hover:text-foreground transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                "disabled:opacity-50 disabled:pointer-events-none",
              )}
            >
              Clear
            </button>
          </div>
        </div>

        {isLoadingInitial ? (
          <div className="flex flex-col items-center justify-center gap-2 py-12">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Loading languages…</p>
          </div>
        ) : hasNoChoices ? (
          <p className="text-sm text-muted-foreground">
            No additional languages are offered by your current selections.
          </p>
        ) : (
          <div className="space-y-6">
            {/* Standard Languages Group */}
            {standardAvailable.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Standard Languages
                  </h4>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                  {standardAvailable.map((lang) => {
                    const isSelected = selected.includes(lang);
                    const isDisabled = !isSelected && counterAtMax;
                    return (
                      <button
                        key={`std-${lang}`}
                        type="button"
                        onClick={() => toggle(lang)}
                        disabled={isDisabled}
                        aria-pressed={isSelected}
                        className={cn(
                          "rounded-md border px-3 py-2 text-sm transition-all duration-150 text-left",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                          isSelected
                            ? "border-primary bg-secondary ring-2 ring-primary/20 text-foreground font-medium"
                            : "border-border hover:bg-secondary/40 hover:border-primary/40",
                          isDisabled && "opacity-40 cursor-not-allowed",
                        )}
                      >
                        <span className="flex items-center justify-between gap-2">
                          <span className="truncate">{lang}</span>
                          {isSelected && (
                            <span
                              className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-primary bg-background text-primary"
                              aria-hidden="true"
                            >
                              <Check className="h-3 w-3" />
                            </span>
                          )}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Rare Languages Group */}
            {rareAvailable.length > 0 && (
              <div className="space-y-2.5 pt-2 border-t border-border/50">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-3.5 w-3.5 text-amber-500" />
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-400">
                    Rare Languages
                  </h4>
                  <span className="text-[11px] text-muted-foreground">
                    (may be selected as any of your {selectionCount} picks)
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                  {rareAvailable.map((lang) => {
                    const isSelected = selected.includes(lang);
                    const isDisabled = !isSelected && counterAtMax;
                    return (
                      <button
                        key={`rare-${lang}`}
                        type="button"
                        onClick={() => toggle(lang)}
                        disabled={isDisabled}
                        aria-pressed={isSelected}
                        className={cn(
                          "rounded-md border px-3 py-2 text-sm transition-all duration-150 text-left",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                          isSelected
                            ? "border-amber-500 bg-amber-500/10 ring-2 ring-amber-500/20 text-amber-700 dark:text-amber-400 font-medium"
                            : "border-border hover:bg-amber-500/5 hover:border-amber-500/40",
                          isDisabled && "opacity-40 cursor-not-allowed",
                        )}
                      >
                        <span className="flex items-center justify-between gap-2">
                          <span className="truncate">{lang}</span>
                          {isSelected && (
                            <span
                              className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-amber-500 bg-background text-amber-600 dark:text-amber-400"
                              aria-hidden="true"
                            >
                              <Check className="h-3 w-3" />
                            </span>
                          )}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
