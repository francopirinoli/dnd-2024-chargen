import { NavLink } from "react-router-dom";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { api, type WizardStep } from "@/lib/api";
import { useCharacterStore } from "@/store/characterStore";
import { cn } from "@/lib/utils";

interface Props {
  steps: WizardStep[];
  currentStepId: string | null;
}

export function StepSidebar({ steps, currentStepId: _ }: Props) {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const setChoice = useCharacterStore((s) => s.setChoice);
  const name = (choicesMade.character_name as string | undefined) ?? "";

  const validateQuery = useQuery({
    queryKey: ["character", "validate", choicesMade],
    queryFn: () => api.character.validate(choicesMade),
    placeholderData: keepPreviousData,
  });

  const statusByStep = new Map(
    (validateQuery.data?.steps ?? []).map((s) => [s.step, s]),
  );

  return (
    <nav className="py-3">
      <div className="px-5 pb-4 border-b border-border/70">
        <label
          htmlFor="sidebar_character_name"
          className="block text-[11px] uppercase tracking-[0.2em] text-muted-foreground"
        >
          Character name
        </label>
        <input
          id="sidebar_character_name"
          type="text"
          value={name}
          onChange={(e) => setChoice("character_name", e.target.value)}
          className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="Enter a name"
        />
      </div>
      <ol className="flex flex-col">
        {steps.map((step, idx) => {
          const status = statusByStep.get(step.id);
          const complete = status?.complete ?? false;
          return (
            <li key={step.id}>
              <NavLink
                to={`/wizard/${step.id}`}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-5 py-3 border-l-2 text-sm transition-colors",
                    isActive
                      ? "border-l-primary bg-secondary text-foreground"
                      : "border-l-transparent text-muted-foreground hover:text-foreground hover:bg-secondary/50",
                  )
                }
              >
                <span
                  className={cn(
                    "inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold",
                    complete
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground",
                  )}
                  aria-label={complete ? "complete" : "pending"}
                >
                  {complete ? "✓" : idx + 1}
                </span>
                <span className="font-medium">{step.label}</span>
              </NavLink>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
