import { act } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WizardStep } from "./WizardStep";
import { api, type WizardStep as WizardStepType } from "@/lib/api";

vi.mock("@/components/wizard/StepRenderer", () => ({
  StepRenderer: ({ step }: { step: WizardStepType }) => (
    <div>Rendered {step.id}</div>
  ),
}));

vi.mock("@/lib/api", () => ({
  api: {
    wizard: {
      steps: vi.fn(),
    },
  },
}));

function renderWizardStep(stepId = "basics", retry = false) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry,
        retryDelay: 0,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/wizard/${stepId}`]}>
        <Routes>
          <Route path="/wizard/:stepId" element={<WizardStep />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("WizardStep", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("supports loading-to-success transition without hook-order errors", async () => {
    const steps = [{ id: "basics", label: "Basics", description: "", required_keys: [] }];
    let resolveSteps: ((value: WizardStepType[]) => void) | undefined;

    vi.mocked(api.wizard.steps).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSteps = resolve;
        }),
    );

    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    renderWizardStep();
    expect(screen.getByText("Loading…")).toBeTruthy();

    await act(async () => {
      resolveSteps?.(steps);
    });

    await screen.findByText("Rendered basics");
    expect(
      consoleErrorSpy.mock.calls.some((call) =>
        call.some((value) =>
          String(value).includes("Rendered more hooks than during the previous render"),
        ),
      ),
    ).toBe(false);
  });

  it("supports retry-to-success transition without hook-order errors", async () => {
    const steps = [{ id: "basics", label: "Basics", description: "", required_keys: [] }];

    vi.mocked(api.wizard.steps)
      .mockRejectedValueOnce(new Error("temporary failure"))
      .mockResolvedValueOnce(steps);

    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    renderWizardStep("basics", true);

    await screen.findByText("Rendered basics");
    await waitFor(() => {
      expect(vi.mocked(api.wizard.steps)).toHaveBeenCalledTimes(2);
    });

    expect(
      consoleErrorSpy.mock.calls.some((call) =>
        call.some((value) =>
          String(value).includes("Rendered more hooks than during the previous render"),
        ),
      ),
    ).toBe(false);
  });
});
