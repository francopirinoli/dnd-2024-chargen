import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useCharacterStore } from "@/store/characterStore";
import { ReplicateMagicItemPicker } from "@/components/wizard/ClassAdvancedChoices";
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

interface ReplicateMagicItemDialogProps {
  open: boolean;
  onClose: () => void;
}

export function ReplicateMagicItemDialog({ open, onClose }: ReplicateMagicItemDialogProps) {
  const choicesMade = useCharacterStore((s) => s.choicesMade);

  const query = useQuery({
    queryKey: [
      "character", "derived", "replicate_magic_item_management",
      choicesMade.class,
      choicesMade.level,
      choicesMade.subclass,
      choicesMade.classes,
      choicesMade.artificer_replicate_plans,
      choicesMade.artificer_active_replications,
    ],
    queryFn: () => api.character.derived(choicesMade as Loose, "replicate_magic_item_management"),
    enabled:
      open &&
      Boolean(
        choicesMade.class === "Artificer" ||
          (Array.isArray(choicesMade["classes"]) &&
            (choicesMade["classes"] as Array<{ class_name?: string }>).some(
              (c) => c?.class_name === "Artificer",
            )),
      ),
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
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Replicate Magic Item (Infusions)</DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            Manage your known plans and change your active infused items loadout.
          </DialogDescription>
        </DialogHeader>

        {query.fetchStatus === "fetching" && !data ? (
          <div className="rounded-xl border border-dashed border-border/70 bg-background/60 px-4 py-5 text-sm text-muted-foreground">
            Loading replications…
          </div>
        ) : data ? (
          <ReplicateMagicItemPicker data={data} onlyActive={true} />
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
