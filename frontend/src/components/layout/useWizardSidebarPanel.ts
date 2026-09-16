import type { ReactNode } from "react";
import { useOutletContext } from "react-router-dom";

interface WizardSidebarOutletContext {
  setSidebarPanel: (panel: ReactNode | null) => void;
}

export function useWizardSidebarPanel() {
  return useOutletContext<WizardSidebarOutletContext>();
}
