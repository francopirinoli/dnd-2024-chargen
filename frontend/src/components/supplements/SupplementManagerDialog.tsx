import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  CheckCircle2,
  FileUp,
  Package,
  Sparkles,
  Trash2,
  X,
  AlertCircle,
} from "lucide-react";
import { api, type SupplementManifest, type SupplementValidationResult } from "@/lib/api";
import { useSupplementStore } from "@/store/supplementStore";
import { Button } from "@/components/ui/button";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function SupplementManagerDialog({ open, onClose }: Props) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeSources = useSupplementStore((s) => s.activeSources);
  const toggleSource = useSupplementStore((s) => s.toggleSource);
  const enableSource = useSupplementStore((s) => s.enableSource);
  const setSupplementsInStore = useSupplementStore((s) => s.setSupplements);

  const [importFile, setImportFile] = useState<File | null>(null);
  const [validationResult, setValidationResult] = useState<SupplementValidationResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Fetch supplements list
  const { data: supplements = [], isLoading } = useQuery({
    queryKey: ["supplements"],
    queryFn: () => api.supplements.list(),
    enabled: open,
  });

  useEffect(() => {
    if (supplements.length > 0) {
      setSupplementsInStore(supplements);
    }
  }, [supplements, setSupplementsInStore]);

  // Install mutation
  const installMutation = useMutation({
    mutationFn: (pkg: unknown) => api.supplements.install(pkg),
    onSuccess: (data) => {
      setSuccessMessage(data.message || "Supplement installed successfully.");
      setValidationResult(null);
      setImportFile(null);
      if (data.manifest?.id) {
        enableSource(data.manifest.id);
      }
      void queryClient.invalidateQueries({ queryKey: ["supplements"] });
      void queryClient.invalidateQueries({ queryKey: ["catalog"] });
      void queryClient.invalidateQueries({ queryKey: ["character"] });
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Failed to install supplement.");
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.supplements.delete(id),
    onSuccess: () => {
      setSuccessMessage("Supplement removed.");
      void queryClient.invalidateQueries({ queryKey: ["supplements"] });
      void queryClient.invalidateQueries({ queryKey: ["catalog"] });
      void queryClient.invalidateQueries({ queryKey: ["character"] });
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Failed to remove supplement.");
    },
  });

  // Handle file select & validate
  async function handleFileSelected(file: File) {
    setErrorMessage(null);
    setSuccessMessage(null);
    setValidationResult(null);
    setImportFile(file);

    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      const res = await api.supplements.validate(parsed);
      if (!res.valid) {
        setErrorMessage("Validation failed: " + res.errors.slice(0, 3).join("; "));
      } else {
        setValidationResult(res);
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Invalid JSON file.");
    }
  }

  async function handleConfirmInstall() {
    if (!importFile) return;
    try {
      const text = await importFile.text();
      const parsed = JSON.parse(text);
      installMutation.mutate(parsed);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to read file.");
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog card */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="supplement-dialog-title"
        className="relative w-full max-w-2xl rounded-xl border border-border bg-card p-6 text-foreground shadow-2xl flex flex-col max-h-[90vh] overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-border">
          <div className="flex items-center gap-2.5">
            <span className="p-2 rounded-lg bg-primary/10 text-primary">
              <Package className="w-5 h-5" />
            </span>
            <div>
              <h2 id="supplement-dialog-title" className="font-display text-xl font-bold">
                Sources &amp; Supplements
              </h2>
              <p className="text-xs text-muted-foreground">
                Manage rulebooks, third-party content, and homebrew options.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status messages */}
        {errorMessage && (
          <div className="mt-4 p-3 rounded-lg border border-destructive/30 bg-destructive/10 text-destructive text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}
        {successMessage && (
          <div className="mt-4 p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-500 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
          {/* Active / Available list */}
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Installed Rulebooks &amp; Supplements
            </p>

            {isLoading ? (
              <div className="p-8 text-center text-sm text-muted-foreground">
                Loading available modules…
              </div>
            ) : (
              <div className="space-y-2.5">
                {supplements.map((s: SupplementManifest) => {
                  const isActive = activeSources.includes(s.id);
                  const isCore = s.is_core || s.id === "core-phb-2024";

                  return (
                    <div
                      key={s.id}
                      className={`p-4 rounded-lg border transition-all ${
                        isActive
                          ? "border-primary/40 bg-secondary/20 shadow-sm"
                          : "border-border/60 bg-card/40 opacity-70"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1 min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-sm text-foreground">
                              {s.title}
                            </span>
                            {isCore && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary/20 text-primary uppercase tracking-wide">
                                Core 2024
                              </span>
                            )}
                            <span className="text-xs text-muted-foreground font-mono">
                              v{s.version}
                            </span>
                            {s.publisher && (
                              <span className="text-xs text-muted-foreground">
                                · {s.publisher}
                              </span>
                            )}
                          </div>
                          {s.description && (
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {s.description}
                            </p>
                          )}

                          {/* Content counts */}
                          {s.counts && (
                            <div className="flex flex-wrap gap-1.5 pt-1.5 text-[11px]">
                              {s.counts.classes > 0 && (
                                <span className="px-2 py-0.5 rounded bg-secondary text-secondary-foreground">
                                  {s.counts.classes} Classes
                                </span>
                              )}
                              {s.counts.subclasses > 0 && (
                                <span className="px-2 py-0.5 rounded bg-secondary text-secondary-foreground">
                                  {s.counts.subclasses} Subclasses
                                </span>
                              )}
                              {s.counts.species > 0 && (
                                <span className="px-2 py-0.5 rounded bg-secondary text-secondary-foreground">
                                  {s.counts.species} Species
                                </span>
                              )}
                              {s.counts.backgrounds > 0 && (
                                <span className="px-2 py-0.5 rounded bg-secondary text-secondary-foreground">
                                  {s.counts.backgrounds} Backgrounds
                                </span>
                              )}
                              {s.counts.feats !== undefined && s.counts.feats > 0 && (
                                <span className="px-2 py-0.5 rounded bg-secondary text-secondary-foreground">
                                  {s.counts.feats} Feats
                                </span>
                              )}
                              {s.counts.spells > 0 && (
                                <span className="px-2 py-0.5 rounded bg-secondary text-secondary-foreground">
                                  {s.counts.spells} Spells
                                </span>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Controls */}
                        <div className="flex items-center gap-2 shrink-0">
                          {!isCore && (
                            <button
                              type="button"
                              onClick={() => deleteMutation.mutate(s.id)}
                              className="p-1.5 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                              title="Delete supplement"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            type="button"
                            disabled={isCore}
                            onClick={() => toggleSource(s.id)}
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                              isCore
                                ? "bg-primary/20 text-primary cursor-default"
                                : isActive
                                ? "bg-primary text-primary-foreground shadow hover:opacity-90"
                                : "border border-border text-muted-foreground hover:bg-secondary hover:text-foreground"
                            }`}
                          >
                            {isActive ? (
                              <>
                                <Check className="w-3.5 h-3.5" />
                                Enabled
                              </>
                            ) : (
                              "Disabled"
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Validation preview card if a file was selected */}
          {validationResult && importFile && (
            <div className="p-4 rounded-lg border border-primary/40 bg-primary/5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <span className="font-semibold text-sm text-foreground">
                    Ready to Install: {validationResult.manifest.title}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground font-mono">
                  {importFile.name}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {validationResult.manifest.description || "No description provided."}
              </p>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="px-2 py-0.5 rounded bg-background border border-border">
                  +{validationResult.counts.subclasses} Subclasses
                </span>
                <span className="px-2 py-0.5 rounded bg-background border border-border">
                  +{validationResult.counts.species} Species
                </span>
                <span className="px-2 py-0.5 rounded bg-background border border-border">
                  +{validationResult.counts.backgrounds} Backgrounds
                </span>
                {validationResult.counts.feats !== undefined && validationResult.counts.feats > 0 && (
                  <span className="px-2 py-0.5 rounded bg-background border border-border">
                    +{validationResult.counts.feats} Feats
                  </span>
                )}
                <span className="px-2 py-0.5 rounded bg-background border border-border">
                  +{validationResult.counts.spells} Spells
                </span>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setValidationResult(null);
                    setImportFile(null);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleConfirmInstall}
                  disabled={installMutation.isPending}
                >
                  {installMutation.isPending ? "Installing…" : "Install & Activate"}
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Footer / Import section */}
        <div className="pt-4 border-t border-border flex items-center justify-between gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleFileSelected(file);
              e.target.value = "";
            }}
          />

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-dashed border-border text-xs font-semibold text-foreground hover:bg-secondary hover:border-primary/50 transition-colors"
          >
            <FileUp className="w-4 h-4 text-primary" />
            Import Supplement (.json)
          </button>

          <Button variant="outline" size="sm" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </div>
  );
}
