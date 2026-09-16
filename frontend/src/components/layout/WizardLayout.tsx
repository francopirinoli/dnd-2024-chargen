import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Outlet, Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bug, ChevronLeft, ChevronRight, Home as HomeIcon, Package, RotateCcw } from "lucide-react";
import { api } from "@/lib/api";
import { useCharacterStore } from "@/store/characterStore";
import { useSupplementStore } from "@/store/supplementStore";
import { StepSidebar } from "@/components/wizard/StepSidebar";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { SupplementManagerDialog } from "@/components/supplements/SupplementManagerDialog";
import { useBugReportUrl } from "@/hooks/useBugReportUrl";

export function WizardLayout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { stepId } = useParams();
  const setDependencies = useCharacterStore((s) => s.setDependencies);
  const setCurrentStep = useCharacterStore((s) => s.setCurrentStep);
  const reset = useCharacterStore((s) => s.reset);
  const bugReportUrl = useBugReportUrl();
  const activeSources = useSupplementStore((s) => s.activeSources);
  const supplementDialogOpen = useSupplementStore((s) => s.dialogOpen);
  const setSupplementDialogOpen = useSupplementStore((s) => s.setDialogOpen);
  const [sidebarPanel, setSidebarPanel] = useState<ReactNode | null>(null);
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const outletContext = useMemo(
    () => ({ setSidebarPanel }),
    [setSidebarPanel],
  );

  const stepsQuery = useQuery({
    queryKey: ["wizard", "steps"],
    queryFn: api.wizard.steps,
  });

  const depsQuery = useQuery({
    queryKey: ["wizard", "dependencies"],
    queryFn: api.wizard.dependencies,
  });

  useEffect(() => {
    if (depsQuery.data) setDependencies(depsQuery.data);
  }, [depsQuery.data, setDependencies]);

  useEffect(() => {
    setCurrentStep(stepId ?? null);
  }, [stepId, setCurrentStep]);

  // Redirect /wizard → first step once steps load.
  useEffect(() => {
    if (!stepId && stepsQuery.data && stepsQuery.data.length > 0) {
      navigate(`/wizard/${stepsQuery.data[0].id}`, { replace: true });
    }
  }, [stepId, stepsQuery.data, navigate]);

  if (stepsQuery.isLoading || depsQuery.isLoading) {
    return (
      <div className="min-h-dvh grid place-items-center bg-background text-muted-foreground">
        Loading wizard…
      </div>
    );
  }

  if (stepsQuery.error || depsQuery.error) {
    return (
      <div className="min-h-dvh grid place-items-center bg-background text-destructive">
        Failed to load wizard.{" "}
        {String(stepsQuery.error ?? depsQuery.error ?? "")}
      </div>
    );
  }

  const steps = stepsQuery.data ?? [];

  function handleConfirmStartOver() {
    reset();
    // Drop any cached /character/* and /wizard/* responses so the new
    // wizard session doesn't render stale build/preview data.
    queryClient.removeQueries({ queryKey: ["character"] });
    queryClient.removeQueries({ queryKey: ["wizard"] });
    if (steps.length > 0) {
      navigate(`/wizard/${steps[0].id}`, { replace: true });
    }
    setIsResetDialogOpen(false);
  }

  function handleStartOver() {
    setIsResetDialogOpen(true);
  }

  return (
    <div className="min-h-dvh bg-background text-foreground font-sans">
      <div className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur-sm md:hidden">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <Link
              to="/"
              className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            >
              <HomeIcon className="h-4 w-4" aria-hidden="true" />
              Home
            </Link>
            <a
              href={bugReportUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-md px-2 py-2 text-xs text-muted-foreground hover:bg-secondary/60 hover:text-foreground transition-colors"
            >
              <Bug className="h-4 w-4" aria-hidden="true" />
              Report bug
            </a>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSupplementDialogOpen(true)}
              aria-label="Manage supplements"
              title={`Manage supplements (${activeSources.length} active)`}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-foreground hover:bg-secondary transition-colors"
            >
              <Package className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">Supplements</span>
            </button>
            <button
              type="button"
              onClick={handleStartOver}
              aria-label="Reset wizard"
              title="Discard all choices and restart the wizard"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-foreground hover:bg-secondary transition-colors"
            >
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">Reset</span>
            </button>
            <ThemeToggle />
          </div>
        </div>
      </div>
      <div
        className={`grid grid-cols-1 gap-0 min-h-dvh relative z-10 ${sidebarCollapsed ? 'md:grid-cols-[3rem_minmax(0,1fr)_24rem]' : 'md:grid-cols-[16rem_minmax(0,1fr)_24rem]'}`}
      >
        <aside className="hidden md:flex md:flex-col border-r border-border bg-card/50 overflow-hidden sticky top-0 h-dvh">
          {sidebarCollapsed ? (
            <div className="flex flex-col items-center gap-2 py-3 px-2 border-b border-border">
              <button
                type="button"
                onClick={() => setSidebarCollapsed((c) => !c)}
                aria-label="Expand sidebar"
                title="Expand sidebar"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-foreground hover:bg-secondary transition-colors"
              >
                <ChevronRight className="h-4 w-4" aria-hidden="true" />
                <span className="sr-only">Expand</span>
              </button>
              <Link
                to="/"
                aria-label="Return to home page"
                title="Return to home page"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-foreground hover:bg-secondary transition-colors"
              >
                <HomeIcon className="h-4 w-4" aria-hidden="true" />
              </Link>
              <button
                type="button"
                onClick={() => setSupplementDialogOpen(true)}
                aria-label="Manage supplements"
                title={`Manage supplements (${activeSources.length} active)`}
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-foreground hover:bg-secondary transition-colors"
              >
                <Package className="h-4 w-4 text-primary" aria-hidden="true" />
                <span className="sr-only">Supplements</span>
              </button>
              <button
                type="button"
                onClick={handleStartOver}
                aria-label="Reset wizard"
                title="Discard all choices and restart the wizard"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-foreground hover:bg-secondary transition-colors"
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                <span className="sr-only">Reset</span>
              </button>
              <ThemeToggle />
              <a
                href={bugReportUrl}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Report a bug"
                title="Report a bug"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary/60 hover:text-foreground transition-colors"
              >
                <Bug className="h-4 w-4" aria-hidden="true" />
              </a>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 px-3 py-3 border-b border-border">
                <Link
                  to="/"
                  aria-label="Return to home page"
                  title="Return to home page"
                  className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-foreground hover:bg-secondary transition-colors"
                >
                  <HomeIcon className="h-4 w-4" aria-hidden="true" />
                </Link>
                <button
                  type="button"
                  onClick={() => setSupplementDialogOpen(true)}
                  aria-label="Manage supplements"
                  title={`Manage supplements (${activeSources.length} active)`}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-foreground hover:bg-secondary transition-colors"
                >
                  <Package className="h-4 w-4 text-primary" aria-hidden="true" />
                  <span className="sr-only">Supplements</span>
                </button>
                <button
                  type="button"
                  onClick={handleStartOver}
                  aria-label="Reset wizard"
                  title="Discard all choices and restart the wizard"
                  className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-foreground hover:bg-secondary transition-colors"
                >
                  <RotateCcw className="h-4 w-4" aria-hidden="true" />
                  <span className="sr-only">Reset</span>
                </button>
                <ThemeToggle />
                <a
                  href={bugReportUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Report a bug"
                  title="Report a bug"
                  className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary/60 hover:text-foreground transition-colors"
                >
                  <Bug className="h-4 w-4" aria-hidden="true" />
                </a>
                <div className="flex-1" />
                <button
                  type="button"
                  onClick={() => setSidebarCollapsed((c) => !c)}
                  aria-label="Collapse sidebar"
                  title="Collapse sidebar"
                  className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-foreground hover:bg-secondary transition-colors"
                >
                  <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                  <span className="sr-only">Collapse</span>
                </button>
              </div>
              <div className="flex-1 overflow-y-auto min-h-0">
                <StepSidebar steps={steps} currentStepId={stepId ?? null} />
              </div>
            </>
          )}
        </aside>
        <main className="px-4 md:px-10 py-6 md:py-8 w-full min-w-0">
          <Outlet context={outletContext} />
        </main>
        {sidebarPanel && (
          <aside className="lg:hidden border-t border-border bg-card/30 px-4 py-6">
            {sidebarPanel}
          </aside>
        )}
        <aside className={`hidden lg:block border-l border-border bg-card/30 ${stepId === 'complete' ? 'invisible' : ''}`}>
          <div className="sticky top-0 p-6 min-h-[100dvh]">
            {sidebarPanel}
          </div>
        </aside>
      </div>

      <SupplementManagerDialog
        open={supplementDialogOpen}
        onClose={() => setSupplementDialogOpen(false)}
      />

      <ConfirmDialog
        open={isResetDialogOpen}
        title="Start over?"
        description="This will discard all your current choices and return you to the first wizard step."
        confirmLabel="Reset"
        onConfirm={handleConfirmStartOver}
        onCancel={() => setIsResetDialogOpen(false)}
      />
    </div>
  );
}
