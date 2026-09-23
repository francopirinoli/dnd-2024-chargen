/**
 * API client for the D&D Character Creator REST API.
 * 
 * All endpoints are stateless — the frontend holds `choices_made`,
 * the backend calculates character stats.
 */

import { z } from "zod";

// ========== Types ==========

export interface ClassAllocation {
  class_name: string;
  level: number;
  subclass?: string;
}

export type AbilityName =
  | "Strength"
  | "Dexterity"
  | "Constitution"
  | "Intelligence"
  | "Wisdom"
  | "Charisma";

/** All six ability scores must be present; unset abilities should be 0. */
export type AbilityModifierMap = Record<AbilityName, number>;

/** Loose spell selection storage. Keys are spell-list buckets the wizard
 * tracks (`cantrips`, `spells`, `background_cantrips`, `background_spells`,
 * etc.); the backend resolves the canonical shape. */
export interface SpellSelections {
  cantrips?: string[];
  spells?: string[];
  spellbook?: string[];
  background_cantrips?: string[];
  background_spells?: string[];
  [bucket: string]: string[] | undefined;
}

export interface ChoicesMade {
  character_name?: string;
  classes?: ClassAllocation[];
  background?: string;
  species?: string;
  lineage?: string;
  ability_scores_method?: "standard_array" | "point_buy" | "manual" | "roll" | "recommended";
  ability_scores?: Record<string, number>;
  additional_ability_modifiers?: AbilityModifierMap;
  background_bonuses?: Record<string, number>;
  skill_choices?: string[];
  tool_choices?: string[];
  languages?: string[];
  fighting_style?: string;
  maneuvers?: string[];
  arcane_shots?: string[];
  equipment_selections?: Record<string, string>;
  background_skill_replacement?: string[];
  species_skill_replacement?: string[];
  /** Nested species trait picks, keyed by trait name (e.g. `"Draconic Ancestry": "Red"`). */
  species_trait_choices?: Record<string, string>;
  /** Class spell / cantrip selections (see `SpellSelections`). */
  spell_selections?: SpellSelections;
  /**
   * Catch-all for dynamic per-feat / per-choice keys (e.g.
   * `feat_Skilled_skills_or_tools`, `class_choice_*`, ad-hoc trait picks
   * the wizard hasn't yet promoted to a nested home). Treated as opaque
   * by the frontend; the backend resolves and normalizes them.
   */
  [key: string]: unknown;
}

export interface WizardStep {
  id: string;
  label: string;
  description: string;
  required_keys: string[];
  nested_choices?: string[];
}

export interface WizardDependencies {
  [key: string]: string[];
}

export interface Character {
  name: string;
  level: number;
  class: string;
  subclass?: string;
  background: string;
  species: string;
  lineage?: string;
  ability_scores: Record<string, number>;
  ability_modifiers: Record<string, number>;
  saving_throws: Record<string, { modifier: number; proficient: boolean }>;
  skills: Record<string, { modifier: number; proficient: boolean }>;
  hp: { max: number; current: number };
  ac: number;
  proficiency_bonus: number;
  speed: number;
  features: string[];
  proficiencies: {
    armor: string[];
    weapons: string[];
    tools: string[];
    languages: string[];
    saving_throws: string[];
    skills: string[];
  };
  spells?: {
    cantrips: string[];
    known: string[];
    prepared?: string[];
    slots?: Record<string, number>;
  };
  equipment?: unknown[];
  maneuvers_known?: string[];
  arcane_shots_known?: string[];
  arcane_shot_die?: string;
  choices_made: ChoicesMade;
  [key: string]: unknown;
}

export interface ValidationStatus {
  step: string;
  complete: boolean;
  missing: string[];
}

export interface ValidationResponse {
  valid: boolean;
  steps: ValidationStatus[];
  missing_top_level: string[];
}

export interface PreviewStepRowContext {
  row_index: number;
  is_primary: boolean;
  total_class_rows: number;
}

export interface PreviewStepResponse {
  step: string;
  row_context?: PreviewStepRowContext;
  [key: string]: unknown;
}

export interface AbilityRoll {
  value: number;
  dice?: number[];
  modifier: number;
  modifier_display: string;
  modifier_tone: "positive" | "negative" | "neutral";
}

export interface MulticlassingSkillProficiencies {
  count: number;
  /** Either a closed list of skills, or the literal string "any". */
  options: string[] | "any";
}

export interface Multiclassing {
  hit_die_granted: number;
  armor_training: string[];
  weapon_training: string[];
  tool_training: string[];
  skill_proficiencies: MulticlassingSkillProficiencies | null;
  saving_throw_proficiencies: string[];
  other_proficiencies: string[];
  notes: string | null;
  source_text: string;
}

export interface ClassSummary {
  id: string;
  name: string;
  description?: string;
  hit_die: number;
  primary_ability: string;
  subclass_selection_level: number;
  multiclassing?: Multiclassing;
  source?: string;
  source_id?: string;
  source_title?: string;
}

/**
 * Full class payload from /catalog/classes/{name}. Includes everything in
 * `ClassSummary` plus the proficiency tables, feature progression, and
 * spellcasting tables consumed by the class info panel.
 */
export interface ClassDetail extends ClassSummary {
  saving_throw_proficiencies: string[];
  armor_proficiencies: string[];
  weapon_proficiencies: string[];
  tool_proficiencies?: string[] | null;
  skill_proficiencies_count: number;
  skill_options: string[];
  features_by_level?: Record<string, Record<string, unknown> | string[]>;
  spellcasting_ability?: string;
  spellcasting_focus?: string[];
  spell_slots_by_level?: Record<string, Record<string, number>>;
  spells_known_by_level?: Record<string, number>;
  prepared_spells_by_level?: Record<string, number>;
  cantrips_known_by_level?: Record<string, number>;
  proficiency_bonus_by_level?: Record<string, number>;
  starting_equipment?: unknown;
  standard_array_assignment?: Record<string, string | number>;
}

export interface SubclassSummary {
  id: string;
  name: string;
  description?: string;
  source?: string;
  source_id?: string;
  source_title?: string;
}

export interface LevelUpFeatureGained {
  name: string;
  description: string;
  type: string;
  source: string;
  level: number;
}

export interface LevelUpSubclassInfo {
  needs_subclass: boolean;
  current_subclass?: string | null;
  selected_subclass?: string | null;
  selection_level: number;
  available_subclasses: Array<{
    id: string;
    name: string;
    description: string;
    level_3_features?: Array<{ name: string; description: string }>;
    source?: string;
  }>;
}

export interface LevelUpFeatInfo {
  needs_feat: boolean;
  choice_key: string | null;
  slot_level: number | null;
  sub_choices?: Array<Record<string, unknown>>;
}

export interface LevelUpPreviewResponse {
  can_level_up: boolean;
  reason?: string;
  class_name: string;
  current_class_level: number;
  next_class_level: number;
  current_total_level: number;
  next_total_level: number;
  all_classes: Array<{ class_name: string; level: number; subclass?: string }>;
  hp_increase: {
    hit_die: number;
    average_roll: number;
    con_modifier: number;
    feature_bonus: number;
    total_increase: number;
    current_max_hp: number;
    next_max_hp: number;
  };
  proficiency_bonus: {
    current: number;
    next: number;
    increased: boolean;
  };
  hit_dice: {
    current: string;
    next: string;
    gained: string;
  };
  features_gained: LevelUpFeatureGained[];
  subclass: LevelUpSubclassInfo;
  feat: LevelUpFeatInfo;
  choices_needed: Array<Record<string, unknown>>;
  spellcasting_changes: {
    has_spellcasting: boolean;
    current_slots?: Record<string, number>;
    next_slots?: Record<string, number>;
    current_pact_slots?: Record<string, number>;
    next_pact_slots?: Record<string, number>;
    unlocked_slot_levels: number[];
    current_prepared_limit: number;
    next_prepared_limit: number;
    is_wizard: boolean;
    wizard_spellbook?: {
      current_limit: number;
      next_limit: number;
      spells_added: number;
      savant_school?: string | null;
      savant_bonus: number;
    } | null;
  };
  mastery_changes: {
    has_mastery: boolean;
    current_max: number;
    next_max: number;
    increased: boolean;
  };
  invocation_changes?: {
    has_invocations: boolean;
    invocations_gained?: boolean;
    allows_swap?: boolean;
    max_invocations?: number;
    current_invocations?: string[];
    available_invocations?: Array<Record<string, unknown>>;
    invocation_choice_descriptors?: Array<Record<string, unknown>>;
    cantrip_choice_descriptors?: Array<Record<string, unknown>>;
    dependency_map?: Record<string, string[]>;
  };
  barbarian_changes?: {
    has_rage: boolean;
    is_barbarian: boolean;
    current_rage_uses: number | string;
    next_rage_uses: number | string;
    current_rage_damage: number;
    next_rage_damage: number;
    rage_damage_increased: boolean;
    current_brutal_strike?: string | null;
    next_brutal_strike?: string | null;
    brutal_strike_unlocked: boolean;
    brutal_strike_effects: string[];
  };
  bard_changes?: {
    has_bardic_inspiration: boolean;
    is_bard: boolean;
    current_inspiration_die?: string | null;
    next_inspiration_die?: string | null;
    die_increased: boolean;
    current_inspiration_uses: number;
    next_inspiration_uses: number;
    current_recharge?: string;
    next_recharge?: string;
    recharge_improved: boolean;
  };
  cleric_changes?: {
    has_channel_divinity: boolean;
    is_cleric: boolean;
    current_cd_uses: number;
    next_cd_uses: number;
    cd_uses_increased: boolean;
    current_spark_dice?: string | null;
    next_spark_dice?: string | null;
    spark_dice_increased: boolean;
    sear_undead_unlocked: boolean;
    divine_intervention_unlocked: boolean;
    greater_divine_intervention_unlocked: boolean;
  };
  druid_changes?: {
    has_wild_shape: boolean;
    is_druid: boolean;
    current_ws_uses: number;
    next_ws_uses: number;
    ws_uses_increased: boolean;
    current_max_cr?: string | null;
    next_max_cr?: string | null;
    max_cr_increased: boolean;
    current_known_forms: number;
    next_known_forms: number;
    known_forms_increased: boolean;
    fly_speed_unlocked: boolean;
    wild_resurgence_unlocked: boolean;
    elemental_fury_unlocked: boolean;
    improved_elemental_fury_unlocked: boolean;
    beast_spells_unlocked: boolean;
    archdruid_unlocked: boolean;
  };
  fighter_changes?: {
    is_fighter: boolean;
    current_second_wind_uses: number;
    next_second_wind_uses: number;
    second_wind_increased: boolean;
    tactical_mind_unlocked: boolean;
    tactical_shift_unlocked: boolean;
    action_surge_unlocked: boolean;
    action_surge_increased: boolean;
    current_action_surge_uses: number;
    next_action_surge_uses: number;
    indomitable_unlocked: boolean;
    indomitable_increased: boolean;
    current_indomitable_uses: number;
    next_indomitable_uses: number;
    attacks_per_action_increased: boolean;
    current_attacks_per_action: number;
    next_attacks_per_action: number;
    tactical_master_unlocked: boolean;
    studied_attacks_unlocked: boolean;
    masteries_increased: boolean;
    current_masteries: number;
    next_masteries: number;
  };
  monk_changes?: {
    is_monk: boolean;
    current_martial_arts_die: string;
    next_martial_arts_die: string;
    martial_arts_die_increased: boolean;
    current_focus_points: number;
    next_focus_points: number;
    focus_points_increased: boolean;
    current_unarmored_movement: number;
    next_unarmored_movement: number;
    unarmored_movement_increased: boolean;
    uncanny_metabolism_unlocked: boolean;
    deflect_attacks_unlocked: boolean;
    deflect_energy_unlocked: boolean;
    stunning_strike_unlocked: boolean;
    empowered_strikes_unlocked: boolean;
    heightened_focus_unlocked: boolean;
    self_restoration_unlocked: boolean;
    disciplined_survivor_unlocked: boolean;
    perfect_focus_unlocked: boolean;
    superior_defense_unlocked: boolean;
    body_and_mind_unlocked: boolean;
    attacks_per_action_increased: boolean;
    current_attacks_per_action: number;
    next_attacks_per_action: number;
  };
}

export interface BackgroundSummary {
  id: string;
  name: string;
  description?: string;
  feat?: string;
  edition: "2024" | "2014";
  status: "active" | "legacy";
  source?: string;
  source_id?: string;
  source_title?: string;
  starting_equipment?: unknown;
}

export interface SpeciesSummary {
  id: string;
  name: string;
  description?: string;
  creature_type: string;
  size: string;
  speed: number;
  darkvision?: number;
  has_lineages: boolean;
  has_trait_choices: boolean;
  source?: string;
  source_id?: string;
  source_title?: string;
}

export interface EquipmentCatalogItem {
  id: string;
  name: string;
  category: "Weapon" | "Armor" | "Shield" | "Gear" | "Tool" | "Consumable" | "Treasure" | "Other";
  subcategory?: string;
  cost?: string;
  weight?: number | string;
  damage?: string;
  damage_type?: string;
  properties?: string[];
  mastery?: string | null;
  ac_base?: number;
  ac_formula?: string;
  ac_bonus?: number;
  stealth_disadvantage?: boolean;
  strength_requirement?: number;
}

export interface DerivedResponse {
  view: string;
  applicable: boolean;
  choices_made?: ChoicesMade;
  reason?: string;
  data: unknown | null;
}

export interface SpellDefinition {
  name: string;
  level?: number;
  school?: string;
  description?: string;
  casting_time?: string;
  range?: string;
  duration?: string;
  components?: string | string[];
  source?: string;
  ritual?: boolean;
}

export interface FeatDefinition {
  name?: string;
  description?: string;
  benefits?: string[];
  prerequisite?: string;
  category?: string;
  source?: string;
  source_id?: string;
  source_title?: string;
  choices?: Array<Record<string, unknown>>;
}

export interface GeneralFeatsReference {
  general_feats: Record<string, FeatDefinition>;
}

export interface OriginFeatsReference {
  origin_feats: Record<string, FeatDefinition>;
}

export interface SupplementCounts {
  classes: number;
  subclasses: number;
  species: number;
  species_variants?: number;
  backgrounds: number;
  spells: number;
  feats?: number;
}

export interface SupplementManifest {
  id: string;
  title: string;
  publisher?: string;
  version: string;
  compatibility?: string;
  description?: string;
  is_core?: boolean;
  is_builtin?: boolean;
  is_user_uploaded?: boolean;
  enabled?: boolean;
  dependencies?: string[];
  counts?: SupplementCounts;
}

export interface SupplementValidationResult {
  valid: boolean;
  errors: string[];
  manifest: SupplementManifest;
  counts: SupplementCounts;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown,
  ) {
    super(`API Error ${status}: ${statusText}`);
    this.name = "ApiError";
  }
}

// ========== Zod Schema ==========

const ClassAllocationSchema = z.object({
  class_name: z.string(),
  level: z.number().int().min(1).max(20),
  subclass: z.string().optional(),
});

const SpellSelectionsSchema = z.object({
  cantrips: z.array(z.string()).optional(),
  spells: z.array(z.string()).optional(),
  spellbook: z.array(z.string()).optional(),
  background_cantrips: z.array(z.string()).optional(),
  background_spells: z.array(z.string()).optional(),
}).catchall(z.array(z.string()).optional());

const CoercedStringArraySchema = z.preprocess(
  (value) => (typeof value === "string" ? (value ? [value] : []) : value),
  z.array(z.string()).optional(),
);

export const ChoicesMadeSchema = z.object({
  character_name: z.string().optional(),
  classes: z.array(ClassAllocationSchema).optional(),
  background: z.string().optional(),
  species: z.string().optional(),
  lineage: z.string().optional(),
  ability_scores_method: z.enum(["standard_array", "point_buy", "manual", "roll", "recommended"]).optional(),
  ability_scores: z.record(z.number()).optional(),
  additional_ability_modifiers: z.record(z.number()).optional(),
  background_bonuses: z.record(z.number()).optional(),
  skill_choices: CoercedStringArraySchema,
  tool_choices: CoercedStringArraySchema,
  languages: z.array(z.string()).optional(),
  fighting_style: z.string().optional(),
  maneuvers: z.array(z.string()).optional(),
  arcane_shots: z.array(z.string()).optional(),
  equipment_selections: z.record(z.string()).optional(),
  background_skill_replacement: z.preprocess(
    (v) => (typeof v === "string" ? (v ? [v] : []) : v),
    z.array(z.string()).optional(),
  ),
  background_skill_replacements: z.preprocess(
    (v) => (typeof v === "string" ? (v ? [v] : []) : v),
    z.array(z.string()).optional(),
  ),
  species_skill_replacement: z.preprocess(
    (v) => (typeof v === "string" ? (v ? [v] : []) : v),
    z.array(z.string()).optional(),
  ),
  species_skill_replacements: z.preprocess(
    (v) => (typeof v === "string" ? (v ? [v] : []) : v),
    z.array(z.string()).optional(),
  ),
  species_trait_choices: z.record(z.string()).optional(),
  spell_selections: SpellSelectionsSchema.optional(),
  inventory: z.record(z.unknown()).optional(),
}).catchall(z.unknown());

/** Dev-mode only: warn about keys in choicesMade that the server did not echo back. */
function warnStaleChoiceKeys(choicesMade: ChoicesMade, serverChoicesMade: ChoicesMade): void {
  if (!import.meta.env.DEV) return;
  const KEY_ALIASES: Record<string, string[]> = {
    background_skill_replacement: ["background_skill_replacements"],
    background_skill_replacements: ["background_skill_replacement"],
    species_skill_replacement: ["species_skill_replacements"],
    species_skill_replacements: ["species_skill_replacement"],
  };
  for (const key of Object.keys(choicesMade)) {
    if (key in serverChoicesMade) continue;
    const aliases = KEY_ALIASES[key] || [];
    if (aliases.some((alias) => alias in serverChoicesMade)) continue;
    console.warn('[round-trip] key in choicesMade not echoed by server:', key);
  }
}

// ========== Configuration ==========

const API_BASE_URL = import.meta.env.DEV
  ? "http://localhost:5000/api/v1"
  : "/api/v1";

// ========== Fetch wrapper ==========

async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, response.statusText, data);
  }

  return response.json();
}

// ========== API Client ==========

export const api = {
  // Wizard metadata
  wizard: {
    steps: (): Promise<WizardStep[]> =>
      apiFetch<{ steps: WizardStep[] }>("/wizard/steps").then((r) => r.steps),

    dependencies: (): Promise<WizardDependencies> =>
      apiFetch<{ dependencies: WizardDependencies }>("/wizard/dependencies").then(
        (r) => r.dependencies,
      ),
  },

  // Catalog (read-only game data)
  catalog: {
    classes: (sources?: string[]): Promise<ClassSummary[]> => {
      const q = sources && sources.length ? `?sources=${encodeURIComponent(sources.join(","))}` : "";
      return apiFetch<{ classes: ClassSummary[] }>(`/catalog/classes${q}`).then((r) => r.classes);
    },

    getClass: (className: string, sources?: string[]): Promise<ClassDetail> => {
      const q = sources && sources.length ? `?sources=${encodeURIComponent(sources.join(","))}` : "";
      return apiFetch<ClassDetail>(`/catalog/classes/${encodeURIComponent(className)}${q}`);
    },

    subclasses: (className: string, sources?: string[]) => {
      const q = sources && sources.length ? `?sources=${encodeURIComponent(sources.join(","))}` : "";
      return apiFetch<{ class: string; subclasses: SubclassSummary[] }>(
        `/catalog/classes/${encodeURIComponent(className)}/subclasses${q}`,
      );
    },

    getSubclass: (className: string, subclassName: string, sources?: string[]) => {
      const q = sources && sources.length ? `?sources=${encodeURIComponent(sources.join(","))}` : "";
      return apiFetch(
        `/catalog/classes/${encodeURIComponent(className)}/subclasses/${encodeURIComponent(subclassName)}${q}`,
      );
    },

    species: (sources?: string[]): Promise<SpeciesSummary[]> => {
      const q = sources && sources.length ? `?sources=${encodeURIComponent(sources.join(","))}` : "";
      return apiFetch<{ species: SpeciesSummary[] }>(`/catalog/species${q}`).then((r) => r.species);
    },

    getSpecies: (speciesName: string) =>
      apiFetch(`/catalog/species/${encodeURIComponent(speciesName)}`),

    backgrounds: (sources?: string[]): Promise<BackgroundSummary[]> => {
      const q = sources && sources.length ? `?sources=${encodeURIComponent(sources.join(","))}` : "";
      return apiFetch<{ backgrounds: BackgroundSummary[] }>(`/catalog/backgrounds${q}`).then((r) => r.backgrounds);
    },

    getBackground: (backgroundName: string) =>
      apiFetch(`/catalog/backgrounds/${encodeURIComponent(backgroundName)}`),

    getReference: <T>(name: string, sources?: string[]): Promise<T> => {
      const q = sources && sources.length ? `?sources=${encodeURIComponent(sources.join(","))}` : "";
      return apiFetch<T>(`/catalog/reference/${encodeURIComponent(name)}${q}`);
    },

    getSpellDefinition: (spellName: string): Promise<SpellDefinition> =>
      apiFetch(
        `/catalog/spells/definitions/${encodeURIComponent(spellName)}`,
      ),

    getEquipment: (): Promise<EquipmentCatalogItem[]> =>
      apiFetch<{ items: EquipmentCatalogItem[] }>("/catalog/equipment").then((r) => r.items),
  },

  // Supplements management
  supplements: {
    list: (): Promise<SupplementManifest[]> =>
      apiFetch<{ supplements: SupplementManifest[] }>("/supplements").then((r) => r.supplements),

    validate: (pkg: unknown): Promise<SupplementValidationResult> =>
      apiFetch<SupplementValidationResult>("/supplements/validate", {
        method: "POST",
        body: JSON.stringify(pkg),
      }),

    install: (pkg: unknown): Promise<{ success: boolean; message: string; manifest?: SupplementManifest }> =>
      apiFetch<{ success: boolean; message: string; manifest?: SupplementManifest }>("/supplements/install", {
        method: "POST",
        body: JSON.stringify(pkg),
      }),

    delete: (id: string): Promise<{ success: boolean; message: string }> =>
      apiFetch<{ success: boolean; message: string }>(`/supplements/${encodeURIComponent(id)}`, {
        method: "DELETE",
      }),
  },

  // Character building
  character: {
    build: (choices: ChoicesMade): Promise<Character> => {
      const validated = ChoicesMadeSchema.parse(choices);
      return apiFetch<{ character: Character }>("/character/build", {
        method: "POST",
        body: JSON.stringify({ choices_made: validated }),
      }).then((r) => {
        warnStaleChoiceKeys(choices, r.character.choices_made ?? {});
        return r.character;
      });
    },

    validate: (choices: ChoicesMade): Promise<ValidationResponse> =>
      apiFetch<ValidationResponse>("/character/validate", {
        method: "POST",
        body: JSON.stringify({ choices_made: choices }),
      }),

    previewStep: (
      choices: ChoicesMade,
      step: string,
    ): Promise<PreviewStepResponse> => {
      const validated = ChoicesMadeSchema.parse(choices);
      return apiFetch<PreviewStepResponse>("/character/preview-step", {
        method: "POST",
        body: JSON.stringify({ choices_made: validated, step }),
      });
    },

    rollAbilities: (): Promise<AbilityRoll[]> =>
      apiFetch<{ rolls: AbilityRoll[] }>("/character/roll-abilities", {
        method: "POST",
        body: JSON.stringify({}),
      }).then((r) => r.rolls),

    derived: (choices: ChoicesMade, view: string): Promise<DerivedResponse> =>
      apiFetch<DerivedResponse>("/character/derived", {
        method: "POST",
        body: JSON.stringify({ choices_made: choices, view }),
      }),

    /**
     * Ask the backend for a SUGGESTED random language set for the current
     * choices. This is a read-only suggestion — the server does NOT persist
     * the result. Callers should render it as a default the user can accept
     * or override; commit happens only when the user writes back through
     * `setChoice("languages", ...)`.
     */
    suggestRandomLanguages: (choices: ChoicesMade): Promise<string[]> =>
      apiFetch<{ languages: string[] }>("/character/random-languages", {
        method: "POST",
        body: JSON.stringify({ choices_made: choices }),
      }).then((r) => r.languages),

    /**
     * Compute actionable preview data for leveling up the character.
     */
    levelUpPreview: (
      choices: ChoicesMade,
      classToLevel?: string,
      subclassToLevel?: string,
    ): Promise<LevelUpPreviewResponse> =>
      apiFetch<{ preview: LevelUpPreviewResponse }>("/character/level-up-preview", {
        method: "POST",
        body: JSON.stringify({
          choices_made: choices,
          class_to_level: classToLevel,
          subclass_to_level: subclassToLevel,
        }),
      }).then((r) => r.preview),
  },
};
