import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useCharacterStore } from "@/store/characterStore";
import { MasteryPicker } from "@/components/wizard/ClassAdvancedChoices";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

type Loose = Record<string, unknown>;

interface ChooseMasteriesDialogProps {
  open: boolean;
  onClose: () => void;
}

export function ChooseMasteriesDialog({ open, onClose }: ChooseMasteriesDialogProps) {
  const choicesMade = useCharacterStore((s) => s.choicesMade);

  const query = useQuery({
    queryKey: [
      "character", "derived", "mastery_management",
      choicesMade.class,
      choicesMade.level,
      choicesMade.subclass,
      choicesMade.classes,
    ],
    queryFn: () => api.character.derived(choicesMade as Loose, "mastery_management"),
    enabled: open && Array.isArray(choicesMade["classes"]) && (choicesMade["classes"] as unknown[]).length > 0,
    retry: false,
  });

  const payload = query.data;
  const applicable =
    payload &&
    payload.applicable === true &&
    payload.data &&
    typeof payload.data === "object" &&
    !Array.isArray(payload.data);
  const data = applicable ? (payload!.data as Loose) : null;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogContent className="w-[calc(100vw-1.5rem)] sm:w-full max-w-2xl max-h-[90vh] overflow-y-auto p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle>Choose Weapon Masteries</DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            Select your weapon masteries according to your class features.
          </DialogDescription>
        </DialogHeader>

        {query.fetchStatus === "fetching" && !data ? (
          <div className="rounded-xl border border-dashed border-border/70 bg-background/60 px-4 py-5 text-sm text-muted-foreground">
            Loading weapon masteries…
          </div>
        ) : data ? (
          <MasteryPicker data={data} />
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
