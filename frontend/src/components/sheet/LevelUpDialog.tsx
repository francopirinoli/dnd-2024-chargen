import { useState, useMemo, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  api,
  type ChoicesMade,
  type ClassAllocation,
  type GeneralFeatsReference,
  type OriginFeatsReference,
  type LevelUpPreviewResponse,
  type FeatDefinition,
} from "@/lib/api";
import { useCharacterStore } from "@/store/characterStore";
import { useRosterStore } from "@/store/rosterStore";
import { useSupplementStore } from "@/store/supplementStore";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ChoiceList } from "@/components/wizard/ChoiceList";
import { FeatDropdownPicker } from "@/components/wizard/FeatDropdownPicker";
import { InvocationPicker } from "@/components/wizard/ClassAdvancedChoices";
import {
  Sparkles,
  Heart,
  Shield,
  BookOpen,
  Sword,
  Check,
  AlertCircle,
  TrendingUp,
  Layers,
  ChevronDown,
  ChevronUp,
  Wand2,
  Music,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface LevelUpDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: (newLevel: number, hasSpellcasting: boolean) => void;
}

export function LevelUpDialog({ open, onClose, onSuccess }: LevelUpDialogProps) {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const setChoices = useCharacterStore((s) => s.setChoices);
  const saveCurrent = useRosterStore((s) => s.saveCurrent);
  const activeSources = useSupplementStore((s) => s.activeSources);

  // Snapshot choices upon opening so cancelling restores original choices
  const initialChoicesRef = useRef<ChoicesMade>(choicesMade);
  const isCommittedRef = useRef(false);

  useEffect(() => {
    if (open) {
      initialChoicesRef.current = JSON.parse(JSON.stringify(choicesMade));
      isCommittedRef.current = false;
      setSelectedSubclass(null);
    }
  }, [open]);

  const [selectedClass, setSelectedClass] = useState<string | undefined>(undefined);
  const [selectedSubclass, setSelectedSubclass] = useState<string | null>(null);
  const [expandedSubclasses, setExpandedSubclasses] = useState<Record<string, boolean>>({});

  // Fetch Level Up Preview
  const previewQuery = useQuery<LevelUpPreviewResponse>({
    queryKey: ["character", "level-up-preview", choicesMade, selectedClass, selectedSubclass],
    queryFn: () =>
      api.character.levelUpPreview(choicesMade, selectedClass, selectedSubclass || undefined),
    enabled: open,
    retry: false,
  });

  // Fetch Feats reference for FeatDropdownPicker
  const generalFeatsQuery = useQuery({
    queryKey: ["catalog", "reference", "general_feats", activeSources],
    queryFn: () =>
      api.catalog.getReference<GeneralFeatsReference>("general_feats", activeSources),
    enabled: open,
  });
  const originFeatsQuery = useQuery({
    queryKey: ["catalog", "reference", "origin_feats", activeSources],
    queryFn: () =>
      api.catalog.getReference<OriginFeatsReference>("origin_feats", activeSources),
    enabled: open,
  });

  const generalFeats = useMemo<Record<string, FeatDefinition>>(
    () => generalFeatsQuery.data?.general_feats ?? {},
    [generalFeatsQuery.data],
  );
  const originFeats = useMemo<Record<string, FeatDefinition>>(
    () => originFeatsQuery.data?.origin_feats ?? {},
    [originFeatsQuery.data],
  );

  const preview = previewQuery.data;

  // Sync selectedSubclass if character already has an established subclass
  useEffect(() => {
    if (preview?.subclass) {
      if (!preview.subclass.needs_subclass && preview.subclass.current_subclass) {
        setSelectedSubclass(preview.subclass.current_subclass);
      }
    }
  }, [preview?.subclass?.needs_subclass, preview?.subclass?.current_subclass]);

  function handleSubclassSelect(subName: string) {
    if (subName === selectedSubclass) return;

    // Clean up any choices that belonged to previous preview.choices_needed
    const keysToClean: string[] = [];
    if (preview?.choices_needed) {
      for (const ch of preview.choices_needed) {
        const k = (ch.choices_made_key || ch.choice_key) as string;
        if (k) keysToClean.push(k);
      }
    }

    const nextChoices: ChoicesMade = { ...choicesMade };
    for (const k of keysToClean) {
      delete nextChoices[k];
    }

    const targetClassName = preview?.class_name || "";
    const isPrimary =
      !choicesMade.class ||
      String(choicesMade.class).toLowerCase() === targetClassName.toLowerCase();
    if (isPrimary) {
      nextChoices.subclass = subName;
    }

    if (Array.isArray(nextChoices.classes)) {
      nextChoices.classes = nextChoices.classes.map((c) =>
        c.class_name.toLowerCase() === targetClassName.toLowerCase()
          ? { ...c, subclass: subName }
          : c
      );
    }

    setChoices(nextChoices);
    setSelectedSubclass(subName);
  }

  function handleClose() {
    if (!isCommittedRef.current) {
      // Revert any changes made during this unconfirmed level-up session
      setChoices(initialChoicesRef.current);
    }
    setSelectedSubclass(null);
    onClose();
  }

  // Determine validation readiness
  const validationError = useMemo<string | null>(() => {
    if (!preview) return "Loading preview…";
    if (!preview.can_level_up) {
      return preview.reason || "Cannot level up.";
    }

    // Subclass requirement
    if (preview.subclass.needs_subclass && !selectedSubclass) {
      return "Please select a subclass.";
    }

    // Feat requirement
    if (preview.feat.needs_feat && preview.feat.choice_key) {
      const featVal = choicesMade[preview.feat.choice_key];
      if (!featVal || typeof featVal !== "string") {
        return "Please choose a feat or Ability Score Improvement.";
      }
      if (featVal === "Ability Score Improvement") {
        const asiOptKey = `${preview.feat.choice_key}_asi_option`;
        const asiOpt = choicesMade[asiOptKey];
        if (!asiOpt) {
          return "Please choose +2 to one ability or +1 to two abilities.";
        }
        if (asiOpt === "+2 to one ability") {
          const plus2Key = `${preview.feat.choice_key}_ability_plus_2`;
          if (!choicesMade[plus2Key]) {
            return "Please select an ability score to increase by 2.";
          }
        } else if (asiOpt === "+1 to two abilities") {
          const plus1Key = `${preview.feat.choice_key}_abilities_plus_1`;
          const arrVal = choicesMade[plus1Key];
          if (!Array.isArray(arrVal) || arrVal.length < 2) {
            return "Please select two different ability scores to increase by 1.";
          }
        }
      }
    }

    // Required feature choices
    if (preview.choices_needed && preview.choices_needed.length > 0) {
      for (const choice of preview.choices_needed) {
        const key = (choice.choices_made_key || choice.choice_key) as string;
        if (!key) continue;
        const requiredCount = typeof choice.count === "number" ? choice.count : 1;
        const currentVal = choicesMade[key];
        if (requiredCount > 1) {
          if (!Array.isArray(currentVal) || currentVal.length < requiredCount) {
            return `Please select ${requiredCount} option(s) for "${choice.title || choice.name || key}".`;
          }
        } else {
          if (currentVal === undefined || currentVal === null || currentVal === "") {
            return `Please make a selection for "${choice.title || choice.name || key}".`;
          }
          if (Array.isArray(currentVal) && currentVal.length < 1) {
            return `Please make a selection for "${choice.title || choice.name || key}".`;
          }
        }
      }
    }

    return null;
  }, [preview, selectedSubclass, choicesMade]);

  async function handleConfirmLevelUp() {
    if (validationError || !preview) return;

    const targetClassName = preview.class_name;
    const nextClassLevel = preview.next_class_level;
    const nextTotalLevel = preview.next_total_level;

    // Build updated classes array
    const rawClasses: ClassAllocation[] =
      Array.isArray(choicesMade.classes) && choicesMade.classes.length > 0
        ? choicesMade.classes
        : [{ class_name: targetClassName, level: preview.current_class_level }];

    const updatedClasses: ClassAllocation[] = rawClasses.map((cls) => {
      if (cls.class_name.toLowerCase() === targetClassName.toLowerCase()) {
        return {
          ...cls,
          level: nextClassLevel,
          ...(selectedSubclass
            ? { subclass: selectedSubclass }
            : cls.subclass
              ? { subclass: cls.subclass }
              : {}),
        };
      }
      return cls;
    });

    const isPrimary =
      !choicesMade.class ||
      String(choicesMade.class).toLowerCase() === targetClassName.toLowerCase();

    const finalChoices: ChoicesMade = {
      ...choicesMade,
      classes: updatedClasses,
      level: nextTotalLevel,
    };

    if (isPrimary) {
      finalChoices.class = targetClassName;
      if (selectedSubclass) {
        finalChoices.subclass = selectedSubclass;
      }
    }

    isCommittedRef.current = true;
    setChoices(finalChoices);

    const charName =
      typeof choicesMade.character_name === "string" && choicesMade.character_name.trim().length > 0
        ? choicesMade.character_name
        : "Unnamed Character";

    try {
      await saveCurrent(finalChoices, charName);
    } catch {
      // Non-fatal, local storage store already has it
    }

    if (onSuccess) {
      onSuccess(nextTotalLevel, Boolean(preview.spellcasting_changes?.has_spellcasting));
    }
    onClose();
  }

  function toggleSubclassExpand(id: string) {
    setExpandedSubclasses((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        if (!isOpen) handleClose();
      }}
    >
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto p-6">
        <DialogHeader>
          <div className="flex items-center gap-2 text-primary font-display text-2xl">
            <Sparkles className="h-6 w-6 text-amber-500 animate-pulse" />
            <DialogTitle className="text-2xl">Level Up Character</DialogTitle>
          </div>
          <DialogDescription className="text-sm text-muted-foreground">
            {preview
              ? `Advancing ${preview.class_name} to Level ${preview.next_class_level} (Total Level ${preview.next_total_level})`
              : "Preparing level advancement preview…"}
          </DialogDescription>
        </DialogHeader>

        {previewQuery.isLoading ? (
          <div className="py-12 flex flex-col items-center justify-center gap-3 text-muted-foreground">
            <Sparkles className="h-8 w-8 text-primary animate-spin" />
            <p className="text-sm">Calculating progression & feature choices…</p>
          </div>
        ) : previewQuery.isError ? (
          <div className="p-4 rounded-lg border border-destructive/50 bg-destructive/10 text-destructive text-sm">
            Failed to load level up preview: {String(previewQuery.error)}
          </div>
        ) : preview && !preview.can_level_up ? (
          <div className="p-4 rounded-lg border border-amber-500/40 bg-amber-500/10 text-amber-900 dark:text-amber-200 text-sm flex items-start gap-3">
            <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
            <div>
              <p className="font-semibold">Cannot Level Up</p>
              <p className="mt-1">{preview.reason ?? "This character has reached the maximum level."}</p>
            </div>
          </div>
        ) : preview ? (
          <div className="space-y-6 mt-2">
            {/* Multiclass class selector */}
            {preview.all_classes && preview.all_classes.length > 1 && (
              <div className="rounded-lg border border-border bg-card/60 p-4 space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Select Class to Advance
                </p>
                <div className="flex flex-wrap gap-2">
                  {preview.all_classes.map((cls) => {
                    const isSelected =
                      (selectedClass ?? preview.class_name).toLowerCase() ===
                      cls.class_name.toLowerCase();
                    return (
                      <Button
                        key={cls.class_name}
                        type="button"
                        size="sm"
                        variant={isSelected ? "default" : "outline"}
                        onClick={() => {
                          setSelectedClass(cls.class_name);
                          setSelectedSubclass(null);
                        }}
                        className={cn(
                          "transition-all",
                          isSelected && "shadow-sm font-semibold",
                        )}
                      >
                        <Layers className="h-3.5 w-3.5 mr-1.5" />
                        {cls.class_name} {cls.level} → {cls.level + 1}
                      </Button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Core Gains Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {/* HP Increase Card */}
              <div className="rounded-xl border border-border bg-card/70 p-4 flex flex-col justify-between shadow-xs">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium uppercase tracking-wider">Hit Points</span>
                  <Heart className="h-4 w-4 text-rose-500" />
                </div>
                <div className="mt-2">
                  <div className="text-2xl font-bold text-primary">
                    +{preview.hp_increase.total_increase} HP
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    d{preview.hp_increase.hit_die} avg ({preview.hp_increase.average_roll})
                    {preview.hp_increase.con_modifier >= 0 ? ` + CON (+${preview.hp_increase.con_modifier})` : ` - CON (${preview.hp_increase.con_modifier})`}
                    {preview.hp_increase.feature_bonus > 0 ? ` + bonus (+${preview.hp_increase.feature_bonus})` : ""}
                  </p>
                  <p className="text-[11px] text-muted-foreground/80 mt-0.5">
                    Max HP: {preview.hp_increase.current_max_hp} → <span className="font-semibold text-foreground">{preview.hp_increase.next_max_hp}</span>
                  </p>
                </div>
              </div>

              {/* Hit Dice Card */}
              <div className="rounded-xl border border-border bg-card/70 p-4 flex flex-col justify-between shadow-xs">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium uppercase tracking-wider">Hit Dice</span>
                  <Shield className="h-4 w-4 text-blue-500" />
                </div>
                <div className="mt-2">
                  <div className="text-2xl font-bold text-primary">
                    +{preview.hit_dice.gained}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Total: {preview.hit_dice.next}
                  </p>
                </div>
              </div>

              {/* Proficiency Bonus Card */}
              <div className="rounded-xl border border-border bg-card/70 p-4 flex flex-col justify-between shadow-xs">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium uppercase tracking-wider">Proficiency Bonus</span>
                  <TrendingUp className="h-4 w-4 text-emerald-500" />
                </div>
                <div className="mt-2">
                  <div className="text-2xl font-bold text-primary">
                    +{preview.proficiency_bonus.next}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {preview.proficiency_bonus.increased
                      ? `Increased from +${preview.proficiency_bonus.current}!`
                      : `Unchanged (+${preview.proficiency_bonus.current})`}
                  </p>
                </div>
              </div>
            </div>

            {/* Spellcasting, Weapon Mastery, Bardic Inspiration & Channel Divinity callouts */}
            {(preview.spellcasting_changes?.has_spellcasting || preview.mastery_changes?.increased || (preview.bard_changes?.has_bardic_inspiration && (preview.bard_changes.die_increased || preview.bard_changes.recharge_improved)) || (preview.cleric_changes?.has_channel_divinity && (preview.cleric_changes.cd_uses_increased || preview.cleric_changes.spark_dice_increased || preview.cleric_changes.divine_intervention_unlocked))) && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {preview.spellcasting_changes?.has_spellcasting && (
                  <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm space-y-1.5">
                    <div className="flex items-center gap-2 font-semibold text-primary">
                      <BookOpen className="h-4 w-4 text-primary" />
                      Spellcasting Progression
                    </div>
                    {preview.spellcasting_changes.unlocked_slot_levels.length > 0 && (
                      <p className="text-xs font-medium text-amber-700 dark:text-amber-300">
                        Unlocked Level {preview.spellcasting_changes.unlocked_slot_levels.join(", ")} Spell Slots!
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Prepared Spells Limit: {preview.spellcasting_changes.current_prepared_limit} →{" "}
                      <span className="font-semibold text-foreground">{preview.spellcasting_changes.next_prepared_limit}</span>
                    </p>
                    {preview.spellcasting_changes.is_wizard && preview.spellcasting_changes.wizard_spellbook && (
                      <div className="pt-1 text-xs text-indigo-700 dark:text-indigo-300 font-medium">
                        Wizard Spellbook: +{preview.spellcasting_changes.wizard_spellbook.spells_added} free spells added!
                        (Capacity: {preview.spellcasting_changes.wizard_spellbook.next_limit})
                      </div>
                    )}
                  </div>
                )}

                {preview.mastery_changes?.increased && (
                  <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-sm space-y-1.5">
                    <div className="flex items-center gap-2 font-semibold text-amber-700 dark:text-amber-300">
                      <Sword className="h-4 w-4" />
                      Weapon Mastery Increased
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Masteries Known: {preview.mastery_changes.current_max} →{" "}
                      <span className="font-semibold text-foreground">{preview.mastery_changes.next_max}</span>
                    </p>
                  </div>
                )}

                {preview.bard_changes?.has_bardic_inspiration && (preview.bard_changes.die_increased || preview.bard_changes.recharge_improved) && (
                  <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-sm space-y-1.5">
                    <div className="flex items-center gap-2 font-semibold text-amber-700 dark:text-amber-300">
                      <Music className="h-4 w-4" />
                      Bardic Inspiration Enhanced
                    </div>
                    {preview.bard_changes.die_increased && (
                      <p className="text-xs text-muted-foreground">
                        Inspiration Die: {preview.bard_changes.current_inspiration_die} →{" "}
                        <span className="font-semibold text-foreground">{preview.bard_changes.next_inspiration_die}</span>
                      </p>
                    )}
                    {preview.bard_changes.recharge_improved && (
                      <p className="text-xs text-muted-foreground">
                        Font of Inspiration: Regain uses on <span className="font-semibold text-foreground">Short or Long Rest</span> (plus spell slot recovery)!
                      </p>
                    )}
                  </div>
                )}

                {preview.cleric_changes?.has_channel_divinity && (preview.cleric_changes.cd_uses_increased || preview.cleric_changes.spark_dice_increased || preview.cleric_changes.divine_intervention_unlocked) && (
                  <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 p-4 text-sm space-y-1.5">
                    <div className="flex items-center gap-2 font-semibold text-sky-700 dark:text-sky-300">
                      <Sparkles className="h-4 w-4" />
                      Channel Divinity Enhanced
                    </div>
                    {preview.cleric_changes.cd_uses_increased && (
                      <p className="text-xs text-muted-foreground">
                        Uses: {preview.cleric_changes.current_cd_uses} →{" "}
                        <span className="font-semibold text-foreground">{preview.cleric_changes.next_cd_uses} per Short/Long Rest</span>
                      </p>
                    )}
                    {preview.cleric_changes.spark_dice_increased && (
                      <p className="text-xs text-muted-foreground">
                        Divine Spark: {preview.cleric_changes.current_spark_dice} →{" "}
                        <span className="font-semibold text-foreground">{preview.cleric_changes.next_spark_dice}</span>
                      </p>
                    )}
                    {preview.cleric_changes.divine_intervention_unlocked && (
                      <p className="text-xs text-muted-foreground">
                        Divine Intervention: <span className="font-semibold text-foreground">Unlocked (Level 5 or lower Cleric spell without slot)</span>
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Features Unlocked */}
            {preview.features_gained && preview.features_gained.length > 0 && (
              <div className="rounded-xl border border-border bg-card/40 p-4 space-y-3">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-amber-500" />
                  New Features Unlocked (Level {preview.next_class_level})
                </h4>
                <div className="space-y-2">
                  {preview.features_gained.map((feat, idx) => (
                    <div
                      key={`${feat.name}-${idx}`}
                      className="rounded-lg border border-border/70 bg-background/80 p-3 text-sm space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-foreground">{feat.name}</span>
                        <span className="text-[11px] text-muted-foreground font-mono bg-muted/60 px-2 py-0.5 rounded">
                          {feat.source}
                        </span>
                      </div>
                      {feat.description && (
                        <p className="text-xs text-muted-foreground whitespace-pre-line leading-relaxed">
                          {feat.description}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Subclass Selection Required */}
            {preview.subclass.needs_subclass && (
              <div className="rounded-xl border-2 border-primary/40 bg-primary/5 p-4 space-y-4">
                <div>
                  <h4 className="text-base font-bold text-primary flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-amber-500" />
                    Choose Your Subclass
                  </h4>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Under the 2024 ruleset, all classes choose their subclass at Level 3. Select a specialization below:
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-3">
                  {preview.subclass.available_subclasses.map((sub) => {
                    const isSelected = selectedSubclass === sub.name || selectedSubclass === sub.id;
                    const isExpanded = Boolean(expandedSubclasses[sub.id]);

                    return (
                      <div
                        key={sub.id}
                        className={cn(
                          "rounded-xl border p-4 transition-all duration-200 cursor-pointer",
                          isSelected
                            ? "border-primary bg-primary/10 shadow-sm ring-1 ring-primary/40"
                            : "border-border bg-background/80 hover:border-primary/40 hover:bg-secondary/40",
                        )}
                        onClick={() => handleSubclassSelect(sub.name)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-3">
                            <div
                              className={cn(
                                "h-5 w-5 rounded-full border flex items-center justify-center transition-colors",
                                isSelected
                                  ? "border-primary bg-primary text-primary-foreground"
                                  : "border-muted-foreground/40 bg-background",
                              )}
                            >
                              {isSelected && <Check className="h-3 w-3" />}
                            </div>
                            <div>
                              <span className="font-semibold text-foreground text-sm">
                                {sub.name}
                              </span>
                              {sub.source && (
                                <span className="ml-2 text-[10px] text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded">
                                  {sub.source}
                                </span>
                              )}
                            </div>
                          </div>

                          {sub.level_3_features && sub.level_3_features.length > 0 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-7 text-xs px-2 text-muted-foreground hover:text-foreground"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleSubclassExpand(sub.id);
                              }}
                            >
                              {sub.level_3_features.length} features
                              {isExpanded ? (
                                <ChevronUp className="h-3.5 w-3.5 ml-1" />
                              ) : (
                                <ChevronDown className="h-3.5 w-3.5 ml-1" />
                              )}
                            </Button>
                          )}
                        </div>

                        {sub.description && (
                          <p className="text-xs text-muted-foreground mt-2 pl-8">
                            {sub.description}
                          </p>
                        )}

                        {/* Expandable Level 3 Features */}
                        {isExpanded && sub.level_3_features && sub.level_3_features.length > 0 && (
                          <div className="mt-3 pl-8 space-y-2 border-t border-border/40 pt-3">
                            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                              Level 3 Features Granted:
                            </p>
                            {sub.level_3_features.map((f, fi) => (
                              <div key={fi} className="text-xs bg-muted/30 p-2.5 rounded-md border border-border/50">
                                <span className="font-semibold text-foreground">{f.name}: </span>
                                <span className="text-muted-foreground">{f.description}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Feat Selection Required */}
            {preview.feat.needs_feat && preview.feat.choice_key && (
              <div className="rounded-xl border border-border bg-card/60 p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-amber-500" />
                  <h4 className="text-sm font-semibold uppercase tracking-wider text-foreground">
                    Feat / Ability Score Improvement (Level {preview.feat.slot_level ?? preview.next_class_level})
                  </h4>
                </div>
                <FeatDropdownPicker
                  choiceKey={preview.feat.choice_key}
                  slotLevel={preview.feat.slot_level ?? preview.next_class_level}
                  title="Choose Feat or ASI"
                  description="Select a general feat, origin feat, or Ability Score Improvement."
                  generalFeats={generalFeats}
                  originFeats={originFeats}
                  featSubChoices={preview.feat.sub_choices ?? []}
                  choicesMade={choicesMade}
                  asiChoiceGroup={{
                    asiOptionChoice: { choice_key: `${preview.feat.choice_key}_asi_option` },
                    plusTwoChoice: { choice_key: `${preview.feat.choice_key}_ability_plus_2` },
                    plusOneChoice: { choice_key: `${preview.feat.choice_key}_abilities_plus_1` },
                  }}
                />
              </div>
            )}

            {/* Feature Choices Needed */}
            {preview.choices_needed && preview.choices_needed.length > 0 && (
              <div className="rounded-xl border border-border bg-card/60 p-4 space-y-4">
                <h4 className="text-sm font-semibold uppercase tracking-wider text-foreground flex items-center gap-2">
                  <Sword className="h-4 w-4 text-primary" />
                  Feature Choices
                </h4>
                <div className="space-y-4">
                  {preview.choices_needed.map((choice, idx) => {
                    const effKey =
                      (choice.choices_made_key as string) ||
                      (choice.choice_key as string) ||
                      `level_choice_${idx}`;
                    const rawOpts = (choice.options ?? []) as Array<string | { id?: string; name?: string; label?: string; description?: string }>;
                    const optDescs = choice.option_descriptions as Record<string, string> | undefined;

                    return (
                      <ChoiceList
                        key={effKey}
                        choiceKey={effKey}
                        title={String(choice.title || choice.name || effKey)}
                        description={choice.description ? String(choice.description) : undefined}
                        options={rawOpts}
                        optionDescriptions={optDescs}
                        count={typeof choice.count === "number" ? choice.count : 1}
                      />
                    );
                  })}
                </div>
              </div>
            )}

            {/* Eldritch Invocations Management */}
            {preview.invocation_changes?.has_invocations && (
              <div className="rounded-xl border border-border bg-card/60 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Wand2 className="h-4 w-4 text-purple-500" />
                    <h4 className="text-sm font-semibold uppercase tracking-wider text-foreground">
                      Eldritch Invocations
                    </h4>
                  </div>
                  {preview.invocation_changes.allows_swap && (
                    <span className="text-[11px] font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded-full">
                      Swap 1 invocation allowed
                    </span>
                  )}
                </div>
                <InvocationPicker data={preview.invocation_changes as Record<string, unknown>} />
              </div>
            )}
          </div>
        ) : null}

        {/* Footer actions */}
        <DialogFooter className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-border pt-4">
          <div className="text-xs text-muted-foreground w-full sm:w-auto">
            {validationError ? (
              <span className="text-amber-600 dark:text-amber-400 font-medium flex items-center gap-1.5">
                <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
                {validationError}
              </span>
            ) : (
              <span className="text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1.5">
                <Check className="h-3.5 w-3.5 flex-shrink-0" />
                Ready to level up!
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <Button variant="outline" size="sm" onClick={handleClose}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={Boolean(validationError)}
              onClick={handleConfirmLevelUp}
              className="bg-primary text-primary-foreground font-semibold shadow-xs hover:bg-primary/90"
            >
              <Sparkles className="h-4 w-4 mr-1.5 text-amber-300" />
              Confirm Level Up
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
