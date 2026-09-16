import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { Backpack, BookOpen, Check, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useCharacterStore } from "@/store/characterStore";

interface EquipmentOption {
  gold?: number;
  items?: unknown[];
  [key: string]: unknown;
}

type EquipmentBlock = Record<string, EquipmentOption>;

const EQUIPMENT_KEY = "equipment_selections";

const SLOT_META: Record<
  string,
  { kicker: string; title: string; icon: React.ReactNode }
> = {
  class_equipment: {
    kicker: "From your class",
    title: "Class Starting Equipment",
    icon: <Backpack className="h-4 w-4" />,
  },
  background_equipment: {
    kicker: "From your background",
    title: "Background Starting Equipment",
    icon: <BookOpen className="h-4 w-4" />,
  },
};

export function EquipmentStep() {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const setChoice = useCharacterStore((s) => s.setChoice);

  const previewQuery = useQuery({
    queryKey: ["character", "preview-step", "equipment", choicesMade],
    queryFn: () => api.character.previewStep(choicesMade, "equipment"),
    placeholderData: keepPreviousData,
  });

  const stored =
    (choicesMade[EQUIPMENT_KEY] as Record<string, string> | undefined) ?? {};

  function setSelection(slot: string, value: string | null) {
    const next = { ...stored };
    if (value === null) delete next[slot];
    else next[slot] = value;
    setChoice(EQUIPMENT_KEY, next);
  }

  if (previewQuery.isLoading && !previewQuery.data) {
    return (
      <div className="overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card to-secondary/40 shadow-sm">
        <div className="flex items-center gap-3 px-5 py-8 sm:px-6">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading equipment…</p>
        </div>
      </div>
    );
  }

  const slots: Array<{ key: string; block: EquipmentBlock }> = [
    {
      key: "class_equipment",
      block:
        (previewQuery.data?.class_equipment as EquipmentBlock | undefined) ??
        {},
    },
    {
      key: "background_equipment",
      block:
        (previewQuery.data?.background_equipment as
          | EquipmentBlock
          | undefined) ?? {},
    },
  ];

  return (
    <div className="space-y-8">
      {slots.map(({ key, block }) => (
        <EquipmentSlot
          key={key}
          slotKey={key}
          block={block}
          selected={stored[key] ?? null}
          onSelect={(option) => setSelection(key, option)}
        />
      ))}
    </div>
  );
}

function EquipmentSlot({
  slotKey,
  block,
  selected,
  onSelect,
}: {
  slotKey: string;
  block: EquipmentBlock;
  selected: string | null;
  onSelect: (option: string | null) => void;
}) {
  const options = Object.entries(block ?? {});
  const meta = SLOT_META[slotKey] ?? {
    kicker: slotKey,
    title: humanizeOption(slotKey),
    icon: <Backpack className="h-4 w-4" />,
  };

  return (
    <section className="overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card to-secondary/40 shadow-sm">
      {/* Section header */}
      <div className="border-b border-border/70 px-5 py-5 sm:px-6">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-primary/10 p-2 text-primary">
            {meta.icon}
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
              {meta.kicker}
            </p>
            <h3 className="mt-1 font-display text-xl text-primary font-bold">
              {meta.title}
            </h3>
          </div>
        </div>
      </div>

      {/* Section body */}
      <div className="px-5 py-5 sm:px-6">
        {options.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No starting equipment data available for this source.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {options.map(([optKey, opt]) => {
              const isSelected = selected === optKey;
              const items = Array.isArray(opt?.items)
                ? (opt.items as unknown[])
                : [];
              const gold =
                typeof opt?.gold === "number" ? opt.gold : undefined;
              const label = humanizeOption(optKey);

              return (
                <button
                  key={`${slotKey}-${optKey}`}
                  type="button"
                  onClick={() => onSelect(isSelected ? null : optKey)}
                  aria-pressed={isSelected}
                  className={cn(
                    "group relative flex h-full w-full flex-col items-stretch text-left rounded-xl border p-4 transition-all duration-200",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                    isSelected
                      ? "border-primary bg-muted/60 shadow-md ring-1 ring-primary/20"
                      : "border-border/80 bg-background/75 hover:-translate-y-1 hover:border-primary/40 hover:bg-secondary/50 hover:shadow-md",
                  )}
                >
                  {/* Card header row: label + check circle */}
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div className="font-display text-xl text-primary font-semibold">
                      {label}
                    </div>
                    <span
                      className={cn(
                        "inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border transition-colors",
                        isSelected
                          ? "border-primary bg-background text-primary"
                          : "border-border bg-background text-transparent group-hover:border-primary/40",
                      )}
                    >
                      <Check className="h-4 w-4" />
                    </span>
                  </div>

                  {/* Gold */}
                  {gold !== undefined && (
                    <div className={cn("text-sm", items.length > 0 && "mb-3 pb-3 border-b border-border/60")}>
                      <span className="text-xs uppercase tracking-wide text-muted-foreground">Gold</span>
                      <p className="mt-0.5 font-medium text-foreground">{gold} gp</p>
                    </div>
                  )}

                  {/* Items list */}
                  {items.length > 0 && (
                    <ul className="space-y-1 text-sm text-muted-foreground">
                      {items.map((it, i) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <span className="mt-0.5 select-none text-muted-foreground/60">
                            •
                          </span>
                          <span>
                            {typeof it === "string" ? it : JSON.stringify(it)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

function humanizeOption(key: string): string {
  // "option_a" → "Option A", "option_b" → "Option B", fallback title-case.
  const m = /^option_([a-z])$/i.exec(key);
  if (m) return `Option ${m[1].toUpperCase()}`;
  return key
    .split("_")
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}
