import type { WizardStep } from "@/lib/api";
import { useCharacterStore } from "@/store/characterStore";
import { StepNav } from "./StepNav";
import { BasicsStep } from "@/components/steps/BasicsStep";
import { ClassStep } from "@/components/steps/ClassStep";
import { SpeciesStep } from "@/components/steps/SpeciesStep";
import { BackgroundStep } from "@/components/steps/BackgroundStep";
import { LanguagesStep } from "@/components/steps/LanguagesStep";
import { AbilitiesStep } from "@/components/steps/AbilitiesStep";
import { EquipmentStep } from "@/components/steps/EquipmentStep";
import { SummaryStep } from "@/components/steps/SummaryStep";
import { GenericStep } from "@/components/steps/GenericStep";

interface Props {
  step: WizardStep;
  steps: WizardStep[];
}

function renderStepBody(
  step: WizardStep,
  steps: WizardStep[],
  choicesMade: Record<string, unknown>,
) {
  switch (step.id) {
    case "basics":
      return <BasicsStep />;
    case "class":
      return <ClassStep />;
    case "species":
      return <SpeciesStep />;
    case "background":
      return <BackgroundStep />;
    case "languages":
      return <LanguagesStep />;
    case "abilities":
      return <AbilitiesStep />;
    case "equipment":
      return <EquipmentStep />;
    case "complete":
      return <SummaryStep steps={steps} />;
    default:
      return <GenericStep step={step} choicesMade={choicesMade} />;
  }
}


export function StepRenderer({ step, steps }: Props) {
  const choicesMade = useCharacterStore((s) => s.choicesMade);

  return (
    <>
      <article className="relative z-10">
        <header className="mb-6">
          <p className="text-xs uppercase tracking-widest text-muted-foreground">
            Step {steps.findIndex((s) => s.id === step.id) + 1} of{" "}
            {steps.length}
          </p>
          <h1 className="font-display text-3xl font-semibold text-primary mt-1">
            {step.label}
          </h1>
          <p className="mt-2 text-muted-foreground">{step.description}</p>
        </header>

        <section>{renderStepBody(step, steps, choicesMade)}</section>

        <StepNav steps={steps} currentStepId={step.id} />
      </article>
    </>
  );
}
