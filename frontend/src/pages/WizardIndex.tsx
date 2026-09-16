import { useNavigate } from "react-router-dom";

export function WizardIndex() {
  const navigate = useNavigate();
  return (
    <div className="text-muted-foreground">
      <p>Loading first step…</p>
      <button
        type="button"
        className="mt-4 underline"
        onClick={() => navigate("/")}
      >
        Back to home
      </button>
    </div>
  );
}
