import { useLocation } from "react-router-dom";
import { useCharacterStore } from "@/store/characterStore";

const BASE_URL =
  "https://github.com/QuickNS/dnd-character-creator/issues/new";

export function useBugReportUrl(): string {
  const location = useLocation();
  const choicesMade = useCharacterStore((s) => s.choicesMade);

  const body = [
    "## Bug Report",
    "",
    `**Page:** \`${location.pathname}\``,
    "",
    "**Description:**",
    "<!-- Describe what happened -->",
    "",
    "**Steps to Reproduce:**",
    "<!-- Optional -->",
    "",
    "**Character Choices:**",
    "```json",
    JSON.stringify(choicesMade, null, 2),
    "```",
  ].join("\n");

  const params = new URLSearchParams({ labels: "bug", body });
  return `${BASE_URL}?${params.toString()}`;
}
