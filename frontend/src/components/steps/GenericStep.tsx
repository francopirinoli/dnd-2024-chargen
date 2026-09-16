import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { api, type ChoicesMade, type WizardStep } from "@/lib/api";

interface Props {
  step: WizardStep;
  choicesMade: ChoicesMade;
}

/**
 * Placeholder for not-yet-implemented steps. Renders the server-side
 * preview-step payload as inspectable JSON. Phase 4 replaces this with
 * rich pickers per step.
 */
export function GenericStep({ step, choicesMade }: Props) {
  const previewQuery = useQuery({
    queryKey: ["character", "preview-step", step.id, choicesMade],
    queryFn: () => api.character.previewStep(choicesMade, step.id),
    placeholderData: keepPreviousData,
  });

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Rich UI for this step lands in Phase 4. Server-provided context below.
      </p>

      {step.required_keys.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-1">Required keys</h3>
          <ul className="text-sm text-muted-foreground list-disc pl-5">
            {step.required_keys.map((k) => (
              <li key={k}>
                <code className="text-primary">{k}</code>
              </li>
            ))}
          </ul>
        </div>
      )}

      {step.nested_choices && step.nested_choices.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-1">Nested choices</h3>
          <ul className="text-sm text-muted-foreground list-disc pl-5">
            {step.nested_choices.map((k) => (
              <li key={k}>
                <code className="text-primary">{k}</code>
              </li>
            ))}
          </ul>
        </div>
      )}

      <details className="rounded-md border border-border bg-card/40 p-4">
        <summary className="cursor-pointer text-sm font-medium">
          Preview payload
        </summary>
        {previewQuery.isLoading && (
          <p className="mt-3 text-xs text-muted-foreground">Loading…</p>
        )}
        {previewQuery.error && (
          <p className="mt-3 text-xs text-destructive">
            {String(previewQuery.error)}
          </p>
        )}
        {previewQuery.data && (
          <pre className="mt-3 max-h-96 overflow-auto text-xs text-muted-foreground">
            {JSON.stringify(previewQuery.data, null, 2)}
          </pre>
        )}
      </details>
    </div>
  );
}
