import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { StepRenderer } from "@/components/wizard/StepRenderer";

export function WizardStep() {
  const { stepId } = useParams<{ stepId: string }>();
  const navigate = useNavigate();

  const stepsQuery = useQuery({
    queryKey: ["wizard", "steps"],
    queryFn: api.wizard.steps,
  });

  const steps = stepsQuery.data ?? [];
  const step = steps.find((s) => s.id === stepId);

  useEffect(() => {
    if (steps.length > 0 && !step) {
      navigate(`/wizard/${steps[0].id}`, { replace: true });
    }
  }, [navigate, step, steps]);

  if (stepsQuery.isLoading) {
    return <p className="text-muted-foreground">Loading…</p>;
  }
  if (stepsQuery.error || !stepsQuery.data) {
    return (
      <p className="text-destructive">
        Failed to load wizard steps.
      </p>
    );
  }

  if (!step) {
    return <p className="text-muted-foreground">Loading wizard step…</p>;
  }

  return <StepRenderer step={step} steps={steps} />;
}
