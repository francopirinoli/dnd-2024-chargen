import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useCharacterStore } from "@/store/characterStore";
import { Check, Eye, Mountain, Waves } from "lucide-react";
import { cn } from "@/lib/utils";

interface AspectOfTheWildsDialogProps {
  open: boolean;
  onClose: () => void;
  currentAspect?: string;
}

const ASPECTS = [
  {
    id: "Owl",
    name: "Owl",
    icon: Eye,
    benefit: "Darkvision +60 ft.",
    description:
      "You have Darkvision with a range of 60 feet. If you already have Darkvision, its range increases by 60 feet.",
  },
  {
    id: "Panther",
    name: "Panther",
    icon: Mountain,
    benefit: "Climb Speed equal to your Speed",
    description: "You have a Climb Speed equal to your Speed.",
  },
  {
    id: "Salmon",
    name: "Salmon",
    icon: Waves,
    benefit: "Swim Speed equal to your Speed",
    description: "You have a Swim Speed equal to your Speed.",
  },
];

export function AspectOfTheWildsDialog({
  open,
  onClose,
  currentAspect,
}: AspectOfTheWildsDialogProps) {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const setChoice = useCharacterStore((s) => s.setChoice);

  const selectedAspect =
    currentAspect ??
    (typeof choicesMade.aspect_of_the_wilds === "string"
      ? choicesMade.aspect_of_the_wilds
      : typeof choicesMade.subclass_aspect_of_the_wilds === "string"
        ? choicesMade.subclass_aspect_of_the_wilds
        : "Owl");

  function handleSelect(aspectId: string) {
    setChoice("aspect_of_the_wilds", aspectId);
    setChoice("subclass_aspect_of_the_wilds", aspectId);
    onClose();
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        if (!isOpen) onClose();
      }}
    >
      <DialogContent className="w-[calc(100vw-1.5rem)] sm:w-full max-w-lg p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle>Aspect of the Wilds</DialogTitle>
          <DialogDescription className="text-xs sm:text-sm text-muted-foreground">
            You gain one of the following aspects of your choice. Whenever you
            finish a Long Rest, you can change your choice.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 space-y-3">
          {ASPECTS.map((aspect) => {
            const Icon = aspect.icon;
            const isSelected = selectedAspect === aspect.id;
            return (
              <button
                key={aspect.id}
                type="button"
                onClick={() => handleSelect(aspect.id)}
                className={cn(
                  "w-full text-left rounded-lg border p-3.5 transition-all flex items-start gap-3.5 cursor-pointer",
                  isSelected
                    ? "border-primary bg-primary/10 shadow-xs ring-1 ring-primary"
                    : "border-border/70 bg-card/40 hover:bg-secondary/40 hover:border-border",
                )}
              >
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-md border",
                    isSelected
                      ? "border-primary/50 bg-primary/20 text-primary"
                      : "border-border/70 bg-background text-muted-foreground",
                  )}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-sm text-foreground">
                      {aspect.name}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                        {aspect.benefit}
                      </span>
                      {isSelected && (
                        <span className="flex items-center gap-1 rounded bg-primary/20 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                          <Check className="h-3 w-3" />
                          Active
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                    {aspect.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
