#!/usr/bin/env python3
"""
Character Builder Module

Stateful character builder that manages the step-by-step character creation process.
This class is independent of Flask/web framework and can be used in:
- Unit tests
- CLI tools
- API endpoints
- Scripts

Usage:
    builder = CharacterBuilder()
    builder.set_species("Elf")
    builder.set_lineage("Wood Elf", spellcasting_ability="Wisdom")
    builder.set_class("Ranger", level=1)
    builder.set_background("Sage")
    builder.set_abilities({"STR": 10, "DEX": 16, "CON": 14, "INT": 12, "WIS": 15, "CHA": 8})

    # Export to various formats
    character_json = builder.to_json()
    character_obj = builder.to_character()
"""

import json
import os
import re
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from copy import deepcopy

from .ability_scores import (
    ABILITIES,
    POINT_BUY_COSTS,
    POINT_BUY_MAX,
    POINT_BUY_MIN,
    POINT_BUY_TOTAL,
    AbilityScores,
    validate_point_buy,
)
from .feature_manager import FeatureManager
from .hp_calculator import HPCalculator
from .variant_manager import VariantManager
from .derived_stats import build_spell_management_view
from .data_loader import DataLoader
from . import strict_mode

# Import choice resolver for feature processing
import sys
import math

if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.choice_resolver import (
    resolve_choice_options,
    get_option_descriptions,
    is_unresolved_placeholder,
)


def _humanize(snake: str) -> str:
    """Title-case a snake_case identifier for display.

    Unlike :py:meth:`str.title`, this does not capitalize the letter that
    follows a digit, so ``"1st_level_spell"`` becomes ``"1st Level Spell"``
    rather than ``"1St Level Spell"``.
    """
    return " ".join(
        (w[0].upper() + w[1:]) if w and w[0].isalpha() else w
        for w in snake.split("_")
    )


# Regex patterns for class-level feat slot keys (e.g. "class_feat_4") and
# their sub-choice keys (e.g. "class_feat_4_ability_plus_2").  Defined once
# here so all callers share the same compiled pattern.
_CLASS_FEAT_SLOT_RE = re.compile(r"^class_feat_\d+$")
_CLASS_FEAT_SUB_RE = re.compile(r"^(class_feat_\d+)_(.+)$")


# ==================== Canonical content identifiers ====================
#
# Every game-content file in ``data/`` is named with a canonical slug made of
# lowercase letters, digits, underscores and hyphens. Player selections that
# arrive from the API are converted to such a slug before they may touch the
# filesystem; anything else (path separators, traversal segments, absolute
# paths, NUL bytes, encoded traversal) fails the pattern and is rejected.
_CONTENT_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

# Substitutions applied before validation. Content names are title-cased
# display strings ("Wood Elf", "Fighter: Champion"), so a small, fixed set of
# separators maps onto the canonical filename form.
CONTENT_SLUG_SUBSTITUTIONS = ((" ", "_"), (":", "-"), ("'", ""))
SPELL_SLUG_SUBSTITUTIONS = ((" ", "_"), ("'", ""), ("/", "_"))


def content_slug(
    identifier: Any,
    substitutions: Tuple[Tuple[str, str], ...] = CONTENT_SLUG_SUBSTITUTIONS,
) -> Optional[str]:
    """Return the canonical file slug for *identifier*, or None if malformed.

    A malformed identifier is one that cannot possibly name a content file:
    a non-string, an empty string, or anything containing characters outside
    the canonical slug alphabet once the display-name substitutions above have
    been applied.
    """
    if not isinstance(identifier, str):
        return None
    slug = identifier.strip().lower()
    for old, new in substitutions:
        slug = slug.replace(old, new)
    if not _CONTENT_SLUG_RE.match(slug):
        return None
    return slug


class SelectionValidationError(ValueError):
    """Raised when submitted post-creation selections are not valid."""

    def __init__(
        self,
        *,
        family: str,
        code: str,
        message: str,
        violations: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.family = family
        self.code = code
        self.message = message
        self.violations = violations or []

    def to_error_payload(self) -> Dict[str, Any]:
        return {
            "error": self.message,
            "selection_family": self.family,
            "code": self.code,
            "violations": self.violations,
        }


class CharacterBuilder:
    """
    Stateful builder for D&D 2024 character creation.

    This class manages the step-by-step process of creating a character,
    loading data from JSON files, applying effects, and tracking choices.
    """

    # Character creation steps in order
    CREATION_STEPS = [
        "create",           # Name + alignment
        "class",            # Class + level selection
        "class_choices",    # Subclass (if applicable) + class feature choices
        "background",       # Background selection
        "background_skill_replacement",  # Optional - overlap resolution
        "feat_choices",     # Optional - origin feat choices
        "species",          # Species selection
        "species_traits",   # Optional - species trait choices
        "species_feat_choices",  # Optional - species feat choices
        "lineage",          # Optional - subspecies/lineage
        "species_skill_replacement",  # Optional - species skill overlap resolution
        "languages",        # Language selection
        "ability_scores",   # Ability scores + background bonuses
        "equipment",        # Equipment selection
        "complete",         # Character summary
    ]
    SPELL_LEVEL_NAMES = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"]

    BASE_LANGUAGE = "Common"
    STANDARD_LANGUAGE_OPTIONS = [
        "Common Sign Language",
        "Draconic",
        "Dwarvish",
        "Elvish",
        "Giant",
        "Gnomish",
        "Goblin",
        "Halfling",
        "Orc",
    ]
    # Rare languages used for in-memory classification in get_language_options().
    # This list mirrors the "rare" array in data/languages.json, which is the
    # authoritative source for the choice-picker UI. Keep both in sync when adding
    # new rare languages.
    RARE_LANGUAGE_OPTIONS = [
        "Abyssal",
        "Celestial",
        "Deep Speech",
        "Druidic",
        "Giant Owl",
        "Gnoll",
        "Primordial",
        "Sylvan",
        "Thieves' Cant",
        "Undercommon",
    ]
    REQUIRED_LANGUAGE_SELECTION_COUNT = 2

    # Content kind → directory under ``data/`` holding one JSON file per
    # canonical identifier. Used by :py:meth:`content_selection_exists`.
    CONTENT_DIRECTORIES = {
        "species": "species",
        "lineage": "species_variants",
        "class": "classes",
        "background": "backgrounds",
    }

    def __init__(self, data_dir: str = None):
        """
        Initialize the character builder.

        Args:
            data_dir: Path to data directory. If None, uses default location.
        """
        # Set up data directory
        if data_dir is None:
            current_dir = Path(__file__).parent
            self.data_dir = current_dir.parent / "data"
        else:
            self.data_dir = Path(data_dir)

        # Initialize modular components
        self.ability_scores = AbilityScores()
        self.feature_manager = FeatureManager()
        self.hp_calculator = HPCalculator()
        self.variant_manager = VariantManager()
        self.data_loader = DataLoader(str(self.data_dir))

        # Load weapon and armor data for equipment processing
        self._weapon_data = self._load_weapon_data()
        self._weapon_data_lowercase = {
            weapon_key.lower(): weapon_key for weapon_key in self._weapon_data.keys()
        }
        self._armor_data = self._load_armor_data()

        # Spell definitions cache
        self._spell_definitions_cache = {}

        # D&D 2024 skill to ability mappings for calculations
        self.skill_abilities = {
            "acrobatics": "dexterity",
            "animal_handling": "wisdom",
            "arcana": "intelligence",
            "athletics": "strength",
            "deception": "charisma",
            "history": "intelligence",
            "insight": "wisdom",
            "intimidation": "charisma",
            "investigation": "intelligence",
            "medicine": "wisdom",
            "nature": "intelligence",
            "perception": "wisdom",
            "performance": "charisma",
            "persuasion": "charisma",
            "religion": "intelligence",
            "sleight_of_hand": "dexterity",
            "stealth": "dexterity",
            "survival": "wisdom",
        }

        # Character data storage
        self.character_data = {
            "name": "",
            "alignment": "",
            "species": None,
            "species_data": None,
            "lineage": None,
            "lineage_data": None,
            "class": None,
            "class_data": None,
            "subclass": None,
            "subclass_data": None,
            "background": None,
            "background_data": None,
            "level": 1,
            "abilities": {},
            "features": {
                "class": [],
                "subclass": [],
                "species": [],
                "lineage": [],
                "background": [],
                "feats": [],
            },
            "choices_made": {},
            "spells": {
                "always_prepared": {},  # Fixed spells (subclass, lineage, features) - dict of spell_name -> metadata
                "prepared": {
                    "cantrips": {},
                    "spells": {},
                },  # User-selected prepared spells (can change on long rest)
                "known": {},  # Permanently known spells (for known casters)
                "background_spells": {},  # Special background spells (Magic Initiate, etc.)
                "slots": {},
            },
            "spell_metadata": {},  # Track spell sources and special properties
            "spell_selections_needed": {  # Track what spells need to be selected
                "cantrips": 0,
                "prepared_spells": 0,
                "background_cantrips": {"count": 0, "spell_list": None},
                "background_spells": {"count": 0, "spell_list": None, "level": 1},
            },
            "weapon_masteries": {
                "selected": [],  # User-selected weapon masteries
                "available": [],  # Weapons available for mastery
                "max_count": 0,  # Maximum masteries allowed
            },
            "proficiencies": {
                "armor": [],
                "weapons": [],
                "tools": [],
                "skills": [],
                "languages": [self.BASE_LANGUAGE],
                "saving_throws": [],
            },
            "proficiency_sources": {
                "armor": {},
                "weapons": {},
                "tools": {},
                "skills": {},
                "languages": {self.BASE_LANGUAGE: "base"},
                "saving_throws": {},
            },
            "speed": 30,
            "darkvision": 0,
            "speed_bonuses": {},
            "resistances": [],
            "immunities": [],
            "condition_immunities": [],
            "save_advantages": [],  # [{"abilities": [...], "display": "...", "condition": "..."}]
            # ===== Phase 6 structured bonus fields =====
            # These are the *sole* inputs to calculation methods for the
            # corresponding effect types. The dispatcher ``_apply_effect``
            # populates them; calculation methods (``calculate_weapon_attacks``,
            # ``calculate_ac_options``, ``_extract_hp_bonuses``, etc.) read only
            # from these structured fields and never re-walk ``applied_effects``.
            "damage_bonuses": [],            # bonus_damage  (Dueling, Thrown Weapon Fighting, ...)
            "attack_bonuses": [],            # bonus_attack  (Archery fighting style, ...)
            "ac_bonuses": [],                # bonus_ac      (Defense fighting style, ...)
            "hp_bonuses": [],                # bonus_hp      (Tough feat, Hill Dwarf, ...)
            "initiative_bonuses": [],        # bonus_initiative (Alert feat, ...)
            "alternative_ac_options": [],    # alternative_ac (Monk/Barbarian Unarmored Defense)
            "attack_ability_overrides": [],  # attack_ability_override (Pact of the Blade)
            "fighting_style_flags": {
                "great_weapon_fighting": [],         # list of source names
                "two_weapon_fighting_modifier": [],  # list of source names
                "unarmed_fighting": [],              # list of source names
            },
            # ===== Phase 7 (D0-1 / D0-2 / D4-3) structured fields =====
            "maneuvers_known": [],           # grant_maneuver — Battle Master picks
            "superiority_dice": {},          # grant_superiority_dice — {"count": N, "die": "dX"}
            "arcane_shots_known": [],        # grant_arcane_shot — Arcane Archer picks
            "arcane_shot_die": None,         # grant_arcane_shot_dice — e.g. "d6", "d8", "d10", "d12"
            "magical_darkness_sight": {},    # grant_magical_darkness_sight — {"range": N, "source": ...}
            # NOTE: bonus_spell_damage_ability_mod and bonus_spell_range now write
            # into spell_metadata[spell_name]["damage_bonus"] and ["range_override"]
            # respectively (P2-4 consolidation). The separate spell_damage_bonuses /
            # spell_range_overrides top-level keys are no longer initialised here.
            "equipment": None,  # Will be initialized when equipment_selections are processed
            "step": "species",  # Track current step
        }

        # ``applied_effects`` is the AUDIT LOG of every effect application.
        # It is **append-only inside ``_apply_effect``** and **read-only outside**
        # of ``_apply_effect`` / ``to_character()``'s export path. Calculation
        # methods must read structured bonus fields above instead — never this
        # list. See Phase 6 of docs/AUDIT_FIX_PLAN_2026-05.md.
        self.applied_effects = []
        self._ensure_base_language()

    def _ensure_base_language(self):
        """Ensure Common is always present and tracked as a baseline language."""
        languages = self.character_data["proficiencies"]["languages"]
        if self.BASE_LANGUAGE not in languages:
            languages.insert(0, self.BASE_LANGUAGE)
        self.character_data["proficiency_sources"]["languages"][self.BASE_LANGUAGE] = "base"

    # ==================== Data Loading Methods ====================

    def _load_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load a JSON file and return its contents."""
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {file_path}: {e}")
            return None

    def _content_file_path(
        self,
        subdir: str,
        *identifiers: str,
        substitutions: Tuple[Tuple[str, str], ...] = CONTENT_SLUG_SUBSTITUTIONS,
    ) -> Optional[Path]:
        """Resolve a content JSON path from canonical identifiers.

        ``subdir`` is a trusted literal (e.g. ``"species"`` or
        ``"spells/definitions"``). ``identifiers`` are player-supplied names;
        every one of them must slugify to a canonical content id. The last
        identifier names the JSON file, any preceding ones name nested content
        directories.

        Returns None when an identifier is malformed or when the resolved path
        escapes the expected content directory (defense in depth against
        traversal), so callers behave exactly as they do for missing files.
        """
        slugs = [content_slug(identifier, substitutions) for identifier in identifiers]
        if not slugs or any(slug is None for slug in slugs):
            return None

        base_dir = os.path.realpath(str(self.data_dir / subdir))
        candidate = os.path.realpath(
            os.path.join(base_dir, *slugs[:-1], f"{slugs[-1]}.json")
        )

        if not candidate.startswith(base_dir + os.sep):
            return None
        return Path(candidate)

    def _external_data_path(self, file_name: str) -> Optional[Path]:
        """Resolve a data-relative file reference, rejecting escapes from ``data/``.

        ``file_name`` normally comes from an authored ``source.file`` entry in a
        JSON data file, but some references are assembled from player choices,
        so containment is verified before the file is opened.
        """
        if not isinstance(file_name, str) or not file_name:
            return None
        base_dir = os.path.realpath(str(self.data_dir))
        candidate = os.path.realpath(os.path.join(base_dir, file_name))
        if not candidate.startswith(base_dir + os.sep):
            return None
        return Path(candidate)

    def _load_species_data(self, species_name: str) -> Optional[Dict[str, Any]]:
        """Load species data from JSON file."""
        file_path = self._content_file_path("species", species_name)
        if file_path is not None and file_path.exists():
            return self._load_json_file(file_path)
        from .supplement_manager import get_supplement_manager
        data = get_supplement_manager(data_dir=str(self.data_dir)).get_species_detail(species_name)
        return deepcopy(data) if data else None

    def _load_lineage_data(
        self, species_name: str, lineage_name: str
    ) -> Optional[Dict[str, Any]]:
        """Load lineage/variant data from JSON file."""
        file_path = self._content_file_path("species_variants", lineage_name)
        if file_path is not None and file_path.exists():
            return self._load_json_file(file_path)
        from .supplement_manager import get_supplement_manager
        data = get_supplement_manager(data_dir=str(self.data_dir)).get_lineage(lineage_name)
        return deepcopy(data) if data else None

    def _load_class_data(self, class_name: str) -> Optional[Dict[str, Any]]:
        """Load class data from JSON file."""
        file_path = self._content_file_path("classes", class_name)
        if file_path is not None and file_path.exists():
            return self._load_json_file(file_path)
        from .supplement_manager import get_supplement_manager
        data = get_supplement_manager(data_dir=str(self.data_dir)).get_classes().get(class_name)
        return deepcopy(data) if data else None

    def _load_subclass_data(
        self, class_name: str, subclass_name: str
    ) -> Optional[Dict[str, Any]]:
        """Load subclass data from JSON file.

        First tries the canonical filename derived from the subclass name.
        If that file doesn't exist, scans every JSON in the class folder and
        returns the first whose "name" field matches (case-insensitive).
        Finally falls back to installed modular supplements.
        """
        file_path = self._content_file_path("subclasses", class_name, subclass_name)
        if file_path is not None and file_path.exists():
            return self._load_json_file(file_path)
        # Fallback: scan folder and match by the "name" field or file stem
        if file_path is not None and file_path.parent.exists():
            try:
                for json_file in sorted(file_path.parent.glob("*.json")):
                    data = self._load_json_file(json_file)
                    if not data:
                        continue
                    name_lower = data.get("name", "").lower()
                    sub_lower = subclass_name.lower()
                    stem_lower = json_file.stem.lower()
                    if name_lower == sub_lower or stem_lower == sub_lower:
                        return data
                    if (name_lower.startswith(sub_lower) or sub_lower.startswith(name_lower) or
                            stem_lower.startswith(sub_lower) or sub_lower.startswith(stem_lower)) and len(sub_lower) >= 4:
                        return data
            except (OSError, ValueError):
                pass
        # Fallback to supplement manager
        from .supplement_manager import get_supplement_manager
        data = get_supplement_manager(data_dir=str(self.data_dir)).get_subclass(class_name, subclass_name)
        return deepcopy(data) if data else None

    def _load_background_data(self, background_name: str) -> Optional[Dict[str, Any]]:
        """Load background data from JSON file."""
        file_path = self._content_file_path("backgrounds", background_name)
        if file_path is not None and file_path.exists():
            return self._load_json_file(file_path)
        from .supplement_manager import get_supplement_manager
        data = get_supplement_manager(data_dir=str(self.data_dir)).get_background(background_name)
        return deepcopy(data) if data else None

    def content_selection_exists(self, kind: str, identifier: Any) -> bool:
        """True when *identifier* names an existing content file of *kind*.

        Supported kinds match the directories under ``data/``:
        "classes", "subclasses", "species", "backgrounds", "species_variants".
        Accepts both singular and plural forms of the kind name.
        """
        subdir = self.CONTENT_DIRECTORIES.get(kind)
        if subdir is None:
            raise ValueError(f"Unknown content kind: {kind}")
        file_path = self._content_file_path(subdir, identifier)
        if file_path is not None and file_path.is_file():
            return True
        from .supplement_manager import get_supplement_manager
        mgr = get_supplement_manager(data_dir=str(self.data_dir))
        ident_str = str(identifier)
        if kind in ("species", "species_variants"):
            return mgr.get_species_detail(ident_str) is not None or mgr.get_lineage(ident_str) is not None
        elif kind in ("background", "backgrounds"):
            return mgr.get_background(ident_str) is not None
        elif kind in ("class", "classes"):
            return ident_str in mgr.get_classes()
        return False

    @staticmethod
    def _background_feat_name(background_data: Optional[Dict[str, Any]]) -> Optional[str]:
        """Return the origin feat granted by *background_data*, or None.

        Phase 9 (D1-1) canonicalized background mechanical grants onto the
        ``effects`` array. The feat is encoded as a ``grant_origin_feat``
        entry with an explicit ``feat`` field. This helper is the single
        chokepoint every consumer (clearing, prereq lookup, Magic Initiate
        detection, feat-choices UI) uses to discover the granted feat name
        without re-reading the deprecated flat ``feat`` top-level key.
        """
        if not isinstance(background_data, dict):
            return None
        for effect in background_data.get("effects", []) or []:
            if (
                isinstance(effect, dict)
                and effect.get("type") == "grant_origin_feat"
            ):
                feat = effect.get("feat")
                if isinstance(feat, str) and feat:
                    return feat
        return None

    @staticmethod
    def _background_skill_proficiencies(
        background_data: Optional[Dict[str, Any]],
    ) -> List[str]:
        """Return the skill proficiencies granted by *background_data*.

        Phase 9 (D1-1): backgrounds expose skill grants exclusively through
        ``effects: [{type: grant_skill_proficiency, skills: [...]}, ...]``.
        Multiple entries are concatenated in declaration order.
        """
        if not isinstance(background_data, dict):
            return []
        skills: List[str] = []
        for effect in background_data.get("effects", []) or []:
            if (
                isinstance(effect, dict)
                and effect.get("type") == "grant_skill_proficiency"
            ):
                for skill in effect.get("skills", []) or []:
                    if isinstance(skill, str) and skill:
                        skills.append(skill)
        return skills

    @staticmethod
    def _format_benefits(benefits: list) -> str:
        """Format a list of benefits as markdown paragraphs with bold titles.

        Each benefit string is expected to be in the form "Title: Description".
        Returns formatted text compatible with the nl2br template filter so that
        sub-feature titles render in bold (matching class feature formatting).
        """
        parts = []
        for benefit in benefits:
            colon_idx = benefit.find(": ")
            if colon_idx > 0:
                title = benefit[:colon_idx]
                rest = benefit[colon_idx + 2:]
                parts.append(f"**{title}.** {rest}")
            else:
                parts.append(benefit)
        return "\n\n" + "\n\n".join(parts)

    @staticmethod
    def _synthesize_feat_asi(feat_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Synthesize ASI choices and effects if feat defines an ASI benefit but lacks schema."""
        if not isinstance(feat_data, dict):
            return feat_data

        choices = feat_data.get("choices", [])
        effects = feat_data.get("effects", [])
        has_asi_choice = any(
            isinstance(c, dict)
            and c.get("name") in ("ability", "ability_score", "ability_plus_2", "abilities_plus_1")
            for c in choices
        )
        has_asi_fixed = any(
            isinstance(e, dict) and e.get("type") == "ability_bonus"
            for e in effects
        )
        if has_asi_choice or has_asi_fixed:
            return feat_data

        benefits = feat_data.get("benefits", [])
        if isinstance(benefits, str):
            benefits = [benefits]
        all_abs = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]

        for b in benefits:
            if not isinstance(b, str):
                continue
            if re.search(r"Increase one ability score of your choice by 1", b, re.IGNORECASE):
                abs_list, is_choice = all_abs, True
            elif re.search(r"Increase the spellcasting ability score used by your Dragonmark feat by 1", b, re.IGNORECASE):
                abs_list, is_choice = ["Intelligence", "Wisdom", "Charisma"], True
            else:
                m = re.search(r"Increase (?:your )?([A-Za-z, ]+?) (?:ability )?score by 1", b, re.IGNORECASE)
                if m:
                    raw = re.sub(r"\bor\b", ",", m.group(1), flags=re.IGNORECASE)
                    abs_list = [a.strip() for a in raw.split(",") if a.strip() in all_abs]
                    is_choice = len(abs_list) > 1
                else:
                    m2 = re.search(r"Increase your ([A-Za-z]+) score by 1", b, re.IGNORECASE)
                    if m2 and m2.group(1).strip() in all_abs:
                        abs_list, is_choice = [m2.group(1).strip()], False
                    else:
                        continue

            if not abs_list:
                continue

            feat_copy = deepcopy(feat_data)
            if is_choice:
                feat_copy.setdefault("choices", []).append({
                    "type": "select_single",
                    "description": "Choose which ability score to increase.",
                    "name": "ability",
                    "source": {
                        "type": "fixed_list",
                        "options": abs_list,
                    },
                })
                choice_effects = feat_copy.setdefault("choice_effects", {})
                choice_effects.setdefault("ability", {})
                for ab in abs_list:
                    choice_effects["ability"][ab] = [
                        {"type": "ability_bonus", "ability": ab, "value": 1}
                    ]
            else:
                feat_copy.setdefault("effects", []).append({
                    "type": "ability_bonus",
                    "ability": abs_list[0],
                    "value": 1,
                })
            return feat_copy

        return feat_data

    def _load_feat_data(self, feat_name: str) -> Optional[Dict[str, Any]]:
        """Load feat data from grouped feat files."""
        feat_name_lower = feat_name.strip().lower()

        # Load origin feats
        origin_feats_file = self.data_dir / "origin_feats.json"
        origin_data = self._load_json_file(origin_feats_file)
        if origin_data and "origin_feats" in origin_data:
            if feat_name in origin_data["origin_feats"]:
                return self._synthesize_feat_asi(origin_data["origin_feats"][feat_name])
            for k, v in origin_data["origin_feats"].items():
                if k.lower() == feat_name_lower:
                    return self._synthesize_feat_asi(v)

        # Load general feats
        general_feats_file = self.data_dir / "general_feats.json"
        general_data = self._load_json_file(general_feats_file)
        if general_data and "general_feats" in general_data:
            if feat_name in general_data["general_feats"]:
                return self._synthesize_feat_asi(general_data["general_feats"][feat_name])
            for k, v in general_data["general_feats"].items():
                if k.lower() == feat_name_lower:
                    return self._synthesize_feat_asi(v)

        from .supplement_manager import get_supplement_manager
        supp_feats = get_supplement_manager(data_dir=str(self.data_dir)).get_feats()
        if feat_name in supp_feats:
            return self._synthesize_feat_asi(supp_feats[feat_name])
        for k, v in supp_feats.items():
            if k.lower() == feat_name_lower:
                return self._synthesize_feat_asi(v)

        return None

    @staticmethod
    def _class_feat_slot_level(slot_key: str) -> int:
        """Extract the numeric level from a class-level feat slot key.

        For example, ``"class_feat_4"`` → ``4``.  Returns ``0`` if the key
        does not match the expected pattern.
        """
        m = re.search(r"class_feat_(\d+)", slot_key)
        return int(m.group(1)) if m else 0

    @staticmethod
    def _get_feat_required_level(feat_data: Optional[Dict[str, Any]]) -> int:
        """Parse the required character or slot level for a feat definition."""
        if not isinstance(feat_data, dict):
            return 1
        category = feat_data.get("category")
        if isinstance(category, str) and category.lower() == "epic boon":
            return 19
        prereq = feat_data.get("prerequisite")
        if not isinstance(prereq, str) or not prereq.strip():
            return 1
        m = re.search(r"(?:(\d+)(?:st|nd|rd|th)?\s+level|level\s+(\d+)\+?)", prereq, re.IGNORECASE)
        if m:
            val = m.group(1) or m.group(2)
            if val:
                return int(val)
        return 1

    def _resolve_feat_choice_context(
        self, choice_key: str
    ) -> Optional[Tuple[str, str, Optional[Dict[str, Any]], Optional[Dict[str, Any]], str]]:
        """Resolve a persisted feat sub-choice key to its feat metadata.

        Supports both class-level feat slot keys (for example,
        ``class_feat_4_cantrips``) and namespaced feat keys used by feat choice
        pages (for example, ``feat_Magic Initiate (Wizard)_cantrips``).
        """
        match = _CLASS_FEAT_SUB_RE.match(choice_key)
        if match:
            parent_key = match.group(1)
            choice_name = match.group(2)
            feat_name = self.character_data["choices_made"].get(parent_key)
            if not isinstance(feat_name, str) or not feat_name:
                return None
            feat_data = self._load_feat_data(feat_name)
            if not isinstance(feat_data, dict):
                return None
            choice_def = next(
                (
                    item
                    for item in feat_data.get("choices", [])
                    if isinstance(item, dict) and item.get("name") == choice_name
                ),
                None,
            )
            return feat_name, choice_name, feat_data, choice_def, parent_key

        if not choice_key.startswith("feat_"):
            return None

        candidate_feat_names: List[str] = []
        background_data = self.character_data.get("background_data") or {}
        background_feat = self._background_feat_name(background_data)
        if isinstance(background_feat, str) and background_feat:
            candidate_feat_names.append(background_feat)

        pending_species_feat = self.character_data.get("pending_species_feat")
        if isinstance(pending_species_feat, str) and pending_species_feat:
            candidate_feat_names.append(pending_species_feat)

        for feat_entry in self.character_data["features"].get("feats", []):
            feat_name = feat_entry.get("name")
            if isinstance(feat_name, str) and feat_name:
                candidate_feat_names.append(feat_name)

        seen_feat_names = set()
        for feat_name in candidate_feat_names:
            if feat_name in seen_feat_names:
                continue
            seen_feat_names.add(feat_name)
            feat_data = self._load_feat_data(feat_name)
            if not isinstance(feat_data, dict):
                continue
            for choice_def in feat_data.get("choices", []):
                if not isinstance(choice_def, dict):
                    continue
                choice_name = choice_def.get("name")
                if not isinstance(choice_name, str) or not choice_name:
                    continue
                if choice_key == f"feat_{feat_name}_{choice_name}":
                    return feat_name, choice_name, feat_data, choice_def, f"feat_{feat_name}"

        return None

    def _feat_choice_dependencies_met(
        self,
        choice_namespace: str,
        choice_def: Optional[Dict[str, Any]],
        choice_key: Optional[str] = None,
    ) -> bool:
        """Check whether a feat sub-choice should be active for the current state."""
        if not isinstance(choice_def, dict):
            return True

        depends_on = choice_def.get("depends_on")
        depends_on_value = choice_def.get("depends_on_value")
        if not depends_on or depends_on_value is None:
            return True

        dependency_key = f"{choice_namespace}_{depends_on}"
        dependency_value = self.character_data["choices_made"].get(dependency_key)
        if dependency_value is None:
            # Backward compatibility: allow legacy ASI payloads that persist only
            # the branch key (ability_plus_2 / abilities_plus_1) without
            # explicitly persisting asi_option.
            if (
                depends_on == "asi_option"
                and isinstance(choice_key, str)
                and (
                    choice_key.endswith("_ability_plus_2")
                    or choice_key.endswith("_abilities_plus_1")
                )
            ):
                return True
            return False
        if isinstance(dependency_value, list):
            return depends_on_value in dependency_value
        return dependency_value == depends_on_value

    def _apply_feat_choice_selection(
        self,
        feat_name: str,
        choice_name: str,
        choice_value: Any,
        feat_data: Optional[Dict[str, Any]] = None,
        persist_choice_key: Optional[str] = None,
    ) -> None:
        """Apply one feat sub-choice to character state.

        This is shared by the live feat choice flow and rebuild-time replay from
        ``choices_made`` so both paths hydrate spells, proficiencies, and
        data-driven ``choice_effects`` the same way.
        """
        if isinstance(choice_value, str):
            values = [choice_value]
        elif isinstance(choice_value, list):
            values = choice_value
        else:
            values = []

        if persist_choice_key:
            self.character_data["choices_made"][persist_choice_key] = values

        if choice_name in ("skills_or_tools", "skills", "skill"):
            for item in values:
                if item in self._ALL_SKILLS:
                    if item not in self.character_data["proficiencies"]["skills"]:
                        self.character_data["proficiencies"]["skills"].append(item)
                        self.character_data["proficiency_sources"]["skills"][item] = feat_name
                else:
                    if item not in self.character_data["proficiencies"]["tools"]:
                        self.character_data["proficiencies"]["tools"].append(item)
                        self.character_data["proficiency_sources"]["tools"][item] = feat_name

        elif choice_name in ("expertise", "skill_expertise"):
            if "skill_expertise" not in self.character_data:
                self.character_data["skill_expertise"] = []
            for item in values:
                if item not in self.character_data["skill_expertise"]:
                    self.character_data["skill_expertise"].append(item)
                self.character_data.setdefault("proficiency_sources", {}).setdefault("expertise", {})[item] = feat_name

        elif choice_name in ("language", "languages"):
            for item in values:
                if item not in self.character_data["proficiencies"]["languages"]:
                    self.character_data["proficiencies"]["languages"].append(item)
                    self.character_data["proficiency_sources"]["languages"][item] = feat_name

        elif choice_name in ("tools", "tool", "artisan_tools", "musical_instruments"):
            for item in values:
                if item not in self.character_data["proficiencies"]["tools"]:
                    self.character_data["proficiencies"]["tools"].append(item)
                    self.character_data["proficiency_sources"]["tools"][item] = feat_name

        elif choice_name == "spellcasting_ability":
            ability = values[0] if values else None
            if ability:
                self.character_data.setdefault("feat_spellcasting_abilities", {})[feat_name] = ability
                for spell_name, info in self.character_data["spells"]["always_prepared"].items():
                    if info.get("source") == feat_name:
                        info["spellcasting_ability"] = ability
                for spell_name, info in self.character_data["spell_metadata"].items():
                    if info.get("source") == feat_name:
                        info["spellcasting_ability"] = ability

        elif choice_name == "cantrips":
            ability = self.character_data.get("feat_spellcasting_abilities", {}).get(feat_name)
            if not ability:
                ab_choice = self.character_data.get("choices_made", {}).get(f"feat_{feat_name}_spellcasting_ability")
                if isinstance(ab_choice, list) and ab_choice:
                    ability = ab_choice[0]
                elif isinstance(ab_choice, str):
                    ability = ab_choice
            for cantrip in values:
                if not cantrip or not isinstance(cantrip, str):
                    continue
                if cantrip.strip() in ("Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"):
                    continue
                # Store in always_prepared so stats count these correctly as "+X" bonus
                prepared_info = {
                    "level": 0,
                    "source": feat_name,
                    "always_prepared": True,
                    "counts_against_limit": False,
                }
                if ability:
                    prepared_info["spellcasting_ability"] = ability
                self.character_data["spells"]["always_prepared"][cantrip] = prepared_info

                meta_info = {
                    "source": feat_name,
                    "always_prepared": True,
                    "once_per_day": False,
                    "counts_against_limit": False,
                }
                if ability:
                    meta_info["spellcasting_ability"] = ability
                self.character_data["spell_metadata"][cantrip] = meta_info

        elif "spell" in choice_name and choice_name != "spellcasting_ability":
            ability = self.character_data.get("feat_spellcasting_abilities", {}).get(feat_name)
            if not ability:
                ab_choice = self.character_data.get("choices_made", {}).get(f"feat_{feat_name}_spellcasting_ability")
                if isinstance(ab_choice, list) and ab_choice:
                    ability = ab_choice[0]
                elif isinstance(ab_choice, str):
                    ability = ab_choice
            for spell in values:
                if not spell or not isinstance(spell, str):
                    continue
                if spell.strip() in ("Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"):
                    continue
                spell_def = self._load_spell_definition(spell) or {}
                spell_level = spell_def.get("level", 1)
                # Store in always_prepared so stats count these correctly as "+X" bonus
                prepared_info = {
                    "level": spell_level,
                    "source": feat_name,
                    "always_prepared": True,
                    "once_per_day": True,
                    "counts_against_limit": False,
                }
                if ability:
                    prepared_info["spellcasting_ability"] = ability
                self.character_data["spells"]["always_prepared"][spell] = prepared_info

                meta_info = {
                    "source": feat_name,
                    "always_prepared": True,
                    "once_per_day": True,
                    "counts_against_limit": False,
                }
                if ability:
                    meta_info["spellcasting_ability"] = ability
                self.character_data["spell_metadata"][spell] = meta_info

        feat_data = feat_data if isinstance(feat_data, dict) else self._load_feat_data(feat_name)
        if not isinstance(feat_data, dict) or "choice_effects" not in feat_data:
            return

        choice_effect_map = feat_data["choice_effects"].get(choice_name, {})
        for value in values:
            if value in choice_effect_map:
                for effect in choice_effect_map[value]:
                    self._apply_effect(effect, feat_name, "feat")

    # ==================== Species/Lineage Methods ====================

    def _clear_species_features(self):
        """Clear all species-related features and effects before re-applying."""
        # Clear species skill replacement data
        prev_species_name = self.character_data.get("species", "") or ""
        prev_replacements = self.character_data["choices_made"].pop(
            "species_skill_replacements", []
        )
        self._remove_skills_sourced_from(prev_replacements, prev_species_name)
        self.character_data["choices_made"].pop(
            "species_skill_replacements_needed", None
        )

        # Clear species and lineage features
        self.character_data["features"]["species"] = []
        self.character_data["features"]["lineage"] = []

        # Reset species-specific attributes to defaults
        self.character_data["speed"] = 30  # Default speed
        self.character_data["darkvision"] = 0  # No darkvision
        self.character_data["speed_bonuses"] = {}  # Clear tracked speed bonuses

        # Clear species/lineage language grants while preserving baseline/user/other sources
        old_species_name = self.character_data.get("species")
        old_lineage_name = self.character_data.get("lineage")
        blocked_sources = {"species", "lineage", old_species_name, old_lineage_name}
        lang_sources = self.character_data["proficiency_sources"]["languages"]
        current_languages = self.character_data["proficiencies"]["languages"]
        self.character_data["proficiencies"]["languages"] = [
            lang
            for lang in current_languages
            if lang == self.BASE_LANGUAGE or lang_sources.get(lang) not in blocked_sources
        ]
        self.character_data["proficiency_sources"]["languages"] = {
            lang: source
            for lang, source in lang_sources.items()
            if lang in self.character_data["proficiencies"]["languages"]
        }

        # Clear applied effects from species and lineage source
        if hasattr(self, "applied_effects"):
            self._filter_applied_effects(
                lambda e: e.get("source_type") in ["species", "species_choice", "lineage", "lineage_choice"]
            )

        # Clear species/lineage spells from always_prepared
        always_prepared = self.character_data["spells"]["always_prepared"]
        spell_metadata = self.character_data.get("spell_metadata", {})
        
        spells_to_remove = []
        for spell_name, spell_info in always_prepared.items():
            if isinstance(spell_info, dict):
                source = spell_info.get("source", "")
                if "species" in source.lower() or "lineage" in source.lower():
                    spells_to_remove.append(spell_name)
        
        for spell_name in spells_to_remove:
            always_prepared.pop(spell_name, None)
            spell_metadata.pop(spell_name, None)

        # Clear species and lineage names/data
        self.character_data["species"] = None
        self.character_data["species_data"] = None
        self.character_data["lineage"] = None
        self.character_data["lineage_data"] = None

    def _clear_lineage_features(self):
        """Clear all lineage-related features and effects before re-applying."""
        # Clear species skill replacement data (lineage change may affect overlap count)
        species_name = self.character_data.get("species", "") or ""
        prev_replacements = self.character_data["choices_made"].pop(
            "species_skill_replacements", []
        )
        self._remove_skills_sourced_from(prev_replacements, species_name)
        self.character_data["choices_made"].pop(
            "species_skill_replacements_needed", None
        )

        # Clear lineage features
        self.character_data["features"]["lineage"] = []

        # Reset lineage-specific attributes (preserve species attributes)
        species_data = self.character_data.get("species_data")
        if species_data:
            # Reset to species defaults
            if "speed" in species_data:
                self.character_data["speed"] = species_data["speed"]
            if "darkvision" in species_data:
                self.character_data["darkvision"] = species_data.get("darkvision", 0)
            else:
                # Phase 9: dwarf/elf no longer carry a top-level ``darkvision``
                # convenience key — the species's grant_darkvision effect is the
                # canonical source. Reset to 0 here and let the surviving
                # species-sourced grant_darkvision effects re-establish the
                # baseline below.
                self.character_data["darkvision"] = 0

        # Clear lineage language grants while preserving baseline/user/other sources
        old_lineage_name = self.character_data.get("lineage")
        lang_sources = self.character_data["proficiency_sources"]["languages"]
        current_languages = self.character_data["proficiencies"]["languages"]
        self.character_data["proficiencies"]["languages"] = [
            lang
            for lang in current_languages
            if lang == self.BASE_LANGUAGE
            or lang_sources.get(lang) not in {"lineage", old_lineage_name}
        ]
        self.character_data["proficiency_sources"]["languages"] = {
            lang: source
            for lang, source in lang_sources.items()
            if lang in self.character_data["proficiencies"]["languages"]
        }

        # Clear applied effects from lineage source
        if hasattr(self, "applied_effects"):
            self._filter_applied_effects(
                lambda e: e.get("source_type") in ["lineage", "lineage_choice"]
            )

        # Phase 9: re-derive darkvision from surviving (species-sourced)
        # grant_darkvision effects. Required because dwarf/elf no longer have a
        # top-level convenience key; their species grant_darkvision effect is
        # the only source of truth and the lineage clear above zeroed the
        # field before pruning lineage entries from applied_effects.
        if hasattr(self, "applied_effects"):
            for tracked in self.applied_effects:
                eff = tracked.get("effect", {})
                if eff.get("type") == "grant_darkvision":
                    r = int(eff.get("range", 60) or 0)
                    if r > self.character_data.get("darkvision", 0):
                        self.character_data["darkvision"] = r

        # Clear lineage spells from always_prepared
        always_prepared = self.character_data["spells"]["always_prepared"]
        spell_metadata = self.character_data.get("spell_metadata", {})
        
        spells_to_remove = []
        for spell_name, spell_info in always_prepared.items():
            if isinstance(spell_info, dict):
                source = spell_info.get("source", "")
                if "lineage" in source.lower():
                    spells_to_remove.append(spell_name)
        
        for spell_name in spells_to_remove:
            always_prepared.pop(spell_name, None)
            spell_metadata.pop(spell_name, None)

        # Clear lineage name/data
        self.character_data["lineage"] = None
        self.character_data["lineage_data"] = None

    def set_species(self, species_name: str) -> bool:
        """
        Set the character's species.

        Args:
            species_name: Name of the species (e.g., "Elf", "Dwarf")

        Returns:
            True if successful, False otherwise
        """
        # Clear any existing species/lineage data first
        self._clear_species_features()
        
        species_data = self._load_species_data(species_name)
        if not species_data:
            return False

        self.character_data["species"] = species_name
        self.character_data["species_data"] = species_data

        # Apply species base traits
        self._apply_species_traits(species_data)

        # Check if species has variants
        has_variants = species_name in self.variant_manager.species_variants
        if has_variants:
            self.character_data["step"] = "lineage"
        else:
            self.character_data["step"] = "class"

        return True

    def set_lineage(
        self, lineage_name: str, spellcasting_ability: Optional[str] = None
    ) -> bool:
        """
        Set the character's lineage/variant.

        Args:
            lineage_name: Name of the lineage (e.g., "Wood Elf", "High Elf")
            spellcasting_ability: For lineages with spell choices (e.g., "Wisdom")

        Returns:
            True if successful, False otherwise
        """
        if not self.character_data["species"]:
            return False

        # Clear any existing lineage data first
        self._clear_lineage_features()
        
        lineage_data = self._load_lineage_data(
            self.character_data["species"], lineage_name
        )
        if not lineage_data:
            return False

        self.character_data["lineage"] = lineage_name
        self.character_data["lineage_data"] = lineage_data

        # Store spellcasting ability if provided
        if spellcasting_ability:
            self.character_data["spellcasting_ability"] = spellcasting_ability

        # Apply lineage traits and effects
        self._apply_lineage_traits(lineage_data)

        self.character_data["step"] = "class"
        return True

    def _apply_species_traits(self, species_data: Dict[str, Any]):
        """Apply base species traits."""
        # Speed
        if "speed" in species_data:
            self.character_data["speed"] = species_data["speed"]

        # Darkvision
        if "darkvision" in species_data:
            self.character_data["darkvision"] = species_data["darkvision"]

        # Traits with effects
        traits = species_data.get("traits", {})
        for trait_name, trait_data in traits.items():
            self._apply_trait_effects(trait_name, trait_data, "species")

    def _apply_lineage_traits(self, lineage_data: Dict[str, Any]):
        """Apply lineage/variant traits."""
        # Override speed if lineage specifies it
        if "speed" in lineage_data:
            self.character_data["speed"] = lineage_data["speed"]

        # Override darkvision if lineage specifies it
        if "darkvision" in lineage_data:
            self.character_data["darkvision"] = lineage_data["darkvision"]

        # Store lineage data for later re-application when level changes
        self.character_data["_lineage_traits"] = lineage_data.get("traits", {})

        # Traits with effects
        traits = lineage_data.get("traits", {})
        for trait_name, trait_data in traits.items():
            self._apply_trait_effects(trait_name, trait_data, "lineage")

    def _apply_trait_effects(
        self, trait_name: str, trait_data: Any, source: str, level: int = None
    ):
        """Apply effects from a single trait/feature (Locations 1 + 2).

        This method covers two of the five effect-authoring locations
        documented in ``.github/instructions/data-schemas.instructions.md``:

          * **Location 1** — top-level feat ``effects`` array (when invoked
            via the feat-walk path).
          * **Location 2** — class/subclass/species feature ``effects`` array
            (the common case).

        After Phase 6 this is a **thin wrapper around ``_apply_effect``**:
        it resolves description/scaling/choice substitutions, builds the
        feature entry, then funnels every effect through the single
        ``_apply_effect`` dispatcher. Choice-driven effects (Locations 4 + 5)
        are *not* handled here — they flow through
        ``resolve_effects_for_choice`` → ``_apply_effect`` via
        ``_apply_choice_effects``. Species ``choice_effects`` (Location 3)
        flow through ``_apply_species_choice_effects`` → ``_apply_effect``.
        The One Dispatcher Rule: every effect, regardless of authoring
        location, lands in ``character_data`` exclusively through
        ``_apply_effect``.

        Args:
            trait_name: Name of the trait
            trait_data: Trait data (string or dict with effects)
            source: Source of the trait ('species', 'lineage', 'class', etc.)
        """
        # Get description and apply any template substitutions
        description = (
            trait_data
            if isinstance(trait_data, str)
            else trait_data.get("description", "")
            if isinstance(trait_data, dict)
            else ""
        )

        # Apply scaling/template substitutions for class features
        if (
            source == "class"
            and isinstance(trait_data, dict)
            and "scaling" in trait_data
        ):
            description = self._apply_feature_scaling(
                description, trait_data["scaling"]
            )

        # Apply choice-based template substitutions (e.g., {damage_type} from Draconic Ancestry)
        if isinstance(trait_data, dict) and "choice_substitutions" in trait_data:
            for var_name, choice_name in trait_data["choice_substitutions"].items():
                choice_value = self._resolve_choice_value(choice_name)
                if choice_value:
                    resolved = self._extract_parenthetical(choice_value)
                    description = description.replace(f"{{{var_name}}}", resolved)

        # Phase 8 (D6-2): dispatch on feature_kind / first-class hidden + pdf_summary
        # fields instead of name-matching or feature_override.json lookups. The kind
        # is authored in data/classes/*.json and data/subclasses/**/*.json.
        if source in ("class", "subclass", "class_choice"):
            trait_dict = trait_data if isinstance(trait_data, dict) else {}
            feature_kind = trait_dict.get("feature_kind", "normal")

            # Explicit suppression
            if trait_dict.get("hidden") is True:
                return

            # ASI slots and subclass-selection placeholders never render as
            # standalone features — they're system plumbing handled elsewhere
            # (ASI by the feat / ability-score pipeline; subclass_pick by the
            # subclass selector). subclass_feature_slot is the class-level
            # header for "Gain a subclass feature at this level" — keep it
            # visible so the level callout still shows in the rendered list.
            if feature_kind in ("asi", "subclass_pick"):
                return

            # First-class pdf_summary replaces the verbose description.
            pdf_summary = trait_dict.get("pdf_summary")
            if isinstance(pdf_summary, str) and pdf_summary.strip():
                description = pdf_summary.strip()

        # Skip features that are just choice placeholders
        # (e.g. "Choose a subclass") and should be skipped. Use a length threshold to
        # avoid skipping meaningful feature descriptions that happen to start with "Choose"
        # (e.g. Fiendish Resilience: "Choose one damage type when you finish a Short Rest...").
        CHOICE_PLACEHOLDER_MAX_LENGTH = 100
        if (
            isinstance(description, str)
            and description.lower().startswith("choose")
            and len(description) < CHOICE_PLACEHOLDER_MAX_LENGTH
        ):
            return

        # Map source to feature category and get descriptive source name
        category_map = {
            "species": "species",
            "lineage": "lineage",
            "class": "class",
            "subclass": "subclass",
            "class_choice": "class",
        }
        category = category_map.get(source, "class")

        # Get descriptive source name
        if source == "class":
            source_display = self.character_data.get("class", "Class")
        elif source == "subclass":
            source_display = f"{self.character_data.get('subclass', 'Subclass')}"
        elif source == "species":
            source_display = self.character_data.get("species", "Species")
        elif source == "lineage":
            source_display = self.character_data.get("lineage", "Lineage")
        else:
            source_display = source

        # Check if this feature has a choice and if a choice was made
        display_name = trait_name
        if isinstance(trait_data, dict) and "choices" in trait_data:
            # Look up the choice from choices_made
            choice_config = trait_data["choices"]
            # When choices is a list (multiple independent choice pickers per feature,
            # e.g. Deft Explorer which has both an expertise picker and a language picker),
            # use the first item for the display-name lookup. Each choice in the list
            # carries its own `name` key (choice_key) and is processed separately by
            # get_class_features_and_choices / _process_level_features. Using the first
            # item here prevents an AttributeError while still showing the primary
            # (first) selection in the feature's display name.
            if isinstance(choice_config, list):
                choice_config = choice_config[0] if choice_config else {}
            choice_key = choice_config.get("name", trait_name.lower().replace(" ", "_"))

            # Check various possible choice keys (including species_trait_ prefix).
            # Canonical: nested ``choices_made["species_trait_choices"]`` (P0-1).
            choice_value = None
            nested_traits = self.character_data["choices_made"].get(
                "species_trait_choices"
            )
            if isinstance(nested_traits, dict):
                for nested_key in [
                    choice_key,
                    trait_name,
                    trait_name.lower().replace(" ", "_"),
                ]:
                    if nested_key in nested_traits:
                        choice_value = nested_traits[nested_key]
                        break
            if choice_value is None:
                for possible_key in [
                    choice_key,
                    trait_name,
                    trait_name.lower().replace(" ", "_"),
                    f"species_trait_{trait_name}",
                    f"species_trait_{trait_name.replace(' ', '_')}",
                ]:
                    if possible_key in self.character_data["choices_made"]:
                        choice_value = self.character_data["choices_made"][possible_key]
                        break

            # Append choice to display name
            if choice_value:
                if isinstance(choice_value, list):
                    display_name = f"{trait_name}: {', '.join(choice_value)}"
                else:
                    display_name = f"{trait_name}: {choice_value}"

                # Replace base description with specific choice description
                choice_source = choice_config.get("source", {})
                source_type_str = choice_source.get("type", "")

                if source_type_str == "external":
                    # Load description from external file
                    external_file = choice_source.get("file", "")
                    choice_list_name = choice_source.get("list", "")

                    if external_file and choice_list_name:
                        try:
                            external_path = self._external_data_path(external_file)
                            if external_path is not None and external_path.exists():
                                with open(external_path, "r") as f:
                                    external_data = json.load(f)
                                    choice_list = external_data.get(
                                        choice_list_name, {}
                                    )

                                    # Handle both single choice and list of choices
                                    if isinstance(choice_value, list):
                                        # For multiple choices, combine descriptions
                                        descriptions = []
                                        for cv in choice_value:
                                            if isinstance(choice_list.get(cv), dict):
                                                descriptions.append(
                                                    choice_list[cv].get(
                                                        "description", ""
                                                    )
                                                )
                                            elif isinstance(choice_list.get(cv), str):
                                                descriptions.append(choice_list[cv])
                                        if descriptions:
                                            description = "\n\n".join(descriptions)
                                    else:
                                        # Single choice
                                        if isinstance(
                                            choice_list.get(choice_value), dict
                                        ):
                                            choice_desc = choice_list[choice_value].get(
                                                "description", ""
                                            )
                                            if choice_desc:
                                                description = choice_desc
                                        elif isinstance(
                                            choice_list.get(choice_value), str
                                        ):
                                            description = choice_list[choice_value]
                        except (json.JSONDecodeError, IOError) as e:
                            print(
                                f"Warning: Could not load choice description from {external_file}: {e}"
                            )

                elif source_type_str == "internal":
                    # Load description from internal list
                    internal_list_name = choice_source.get("list", "")

                    if internal_list_name and isinstance(trait_data, dict):
                        internal_list = trait_data.get(internal_list_name, {})

                        # Handle both single choice and list of choices
                        if isinstance(choice_value, list):
                            descriptions = []
                            for cv in choice_value:
                                if isinstance(internal_list.get(cv), dict):
                                    descriptions.append(
                                        internal_list[cv].get("description", "")
                                    )
                                elif isinstance(internal_list.get(cv), str):
                                    descriptions.append(internal_list[cv])
                            if descriptions:
                                description = "\n\n".join(descriptions)
                        else:
                            # Single choice
                            if isinstance(internal_list.get(choice_value), dict):
                                choice_desc = internal_list[choice_value].get(
                                    "description", ""
                                )
                                if choice_desc:
                                    description = choice_desc
                            elif isinstance(internal_list.get(choice_value), str):
                                description = internal_list[choice_value]

        # Phase 8: legacy cantrip-selection rendering for spellcasting_setup features
        # (Spellcasting / Pact Magic). Old saved characters stored their chosen
        # cantrips under choices_made["Spellcasting"]; new characters manage spells
        # post-creation. Dispatch on feature_kind, not feature name.
        if (
            isinstance(trait_data, dict)
            and trait_data.get("feature_kind") == "spellcasting_setup"
        ):
            spellcasting_choices = self.character_data["choices_made"].get(
                "Spellcasting", []
            )
            if isinstance(spellcasting_choices, list) and spellcasting_choices:
                description += f"\n\nCantrips Known: {', '.join(spellcasting_choices)}"

        # Check for grant_spell effects and append spell list to description
        if isinstance(trait_data, dict) and "effects" in trait_data:
            spells_by_level = {}  # Group spells by their min_level
            current_level = self.character_data.get("level", 1)

            for effect in trait_data.get("effects", []):
                if effect.get("type") == "grant_spell":
                    spell_name = effect.get("spell")
                    min_level = effect.get("min_level", 1)
                    if spell_name:
                        if min_level not in spells_by_level:
                            spells_by_level[min_level] = []
                        spells_by_level[min_level].append(spell_name)

            if spells_by_level:
                # Check if spells are granted at multiple levels
                if len(spells_by_level) > 1:
                    # Create an HTML table format for multiple levels
                    description += "\n\n"
                    description += (
                        '<table class="table table-sm table-bordered mt-2">\n'
                    )
                    description += "<thead><tr><th>Character Level</th><th>Spells</th></tr></thead>\n"
                    description += "<tbody>\n"
                    for level in sorted(spells_by_level.keys()):
                        spells = ", ".join(spells_by_level[level])
                        if current_level >= level:
                            row_class = "table-success"
                            marker = "✓ "
                        else:
                            row_class = "table-secondary"
                            marker = "🔒 "
                        description += f'<tr class="{row_class}"><td>{level}</td><td>{marker}{spells}</td></tr>\n'
                    description += "</tbody>\n</table>"
                else:
                    # Single level, use simple format
                    all_spells = []
                    for spells in spells_by_level.values():
                        all_spells.extend(spells)
                    description += (
                        f"\n\nSpells Always Prepared: {', '.join(all_spells)}"
                    )

        # Render structured options (e.g. Celestial Revelation transformations)
        if isinstance(trait_data, dict) and "options" in trait_data:
            options = trait_data["options"]
            if isinstance(options, dict) and options:
                options_html = '<div class="mt-2">'
                for opt_name, opt_desc in options.items():
                    options_html += (
                        f'<div class="mt-1"><strong class="text-secondary">{opt_name}:</strong> '
                        f'<span>{opt_desc}</span></div>'
                    )
                options_html += "</div>"
                description += options_html

        # Add to features dict
        feature_entry = {
            "name": display_name,
            "description": description,
            "source": source_display,
        }

        # Preserve choice_substitutions on the entry so to_character() can resolve
        # placeholders that weren't available yet when the trait was first applied
        if isinstance(trait_data, dict) and "choice_substitutions" in trait_data:
            feature_entry["choice_substitutions"] = trait_data["choice_substitutions"]

        # Add level information if provided (for class/subclass features)
        if level is not None:
            feature_entry["level"] = level

        # Check if feature already exists (avoid duplicates)
        if not any(
            f["name"].startswith(trait_name)
            for f in self.character_data["features"][category]
        ):
            self.character_data["features"][category].append(feature_entry)

        # If trait_data is just a string, no effects to apply
        if isinstance(trait_data, str):
            return

        # If trait_data is a dict, check for effects
        if isinstance(trait_data, dict):
            effects = list(trait_data.get("effects", []))
            if "spells" in trait_data and isinstance(trait_data["spells"], dict):
                for min_lvl_str, spell_list in trait_data["spells"].items():
                    try:
                        min_lvl = int(min_lvl_str)
                    except (ValueError, TypeError):
                        min_lvl = 1
                    if isinstance(spell_list, list):
                        for sp in spell_list:
                            if isinstance(sp, str) and not any(isinstance(e, dict) and e.get("type") == "grant_spell" and e.get("spell") == sp for e in effects):
                                effects.append({
                                    "type": "grant_spell",
                                    "spell": sp,
                                    "min_level": min_lvl,
                                    "counts_against_limit": False
                                })
            # For class/subclass effects, capture which class the effect came from
            # so per-level scaling (e.g., Draconic Resilience) can be scoped to that
            # class's level in multiclass builds rather than total character level.
            source_class_name = None
            if source in ("class", "subclass"):
                source_class_name = self.character_data.get("class")
            for effect in effects:
                self._apply_effect(effect, trait_name, source, source_class_name=source_class_name)

    def _extract_parenthetical(self, value: str) -> str:
        """
        Extract the content inside parentheses from a string.
        E.g., 'Black (Acid)' -> 'Acid'. Returns the original string if no match.
        """
        import re
        match = re.search(r'\(([^)]+)\)', value)
        return match.group(1) if match else value

    def _resolve_choice_value(self, choice_name: str) -> Optional[str]:
        """
        Look up a choice value from choices_made.

        Canonical storage for species trait picks is the nested
        ``choices_made["species_trait_choices"]`` object (audit P0-1). That
        nested map is consulted first. The remaining flat / prefixed key
        variants are kept as a backwards-compat fallback for saved characters
        and for in-flight callers that still write flat top-level keys; the
        ``apply_choices()`` normalizer lifts those into the nested object.
        """
        choices_made = self.character_data.get("choices_made", {})
        nested_traits = choices_made.get("species_trait_choices")
        if isinstance(nested_traits, dict):
            if choice_name in nested_traits:
                return nested_traits[choice_name]
            snake = choice_name.lower().replace(" ", "_")
            if snake in nested_traits:
                return nested_traits[snake]
        for key in [
            choice_name,
            f"species_trait_{choice_name}",
            choice_name.lower().replace(" ", "_"),
            f"species_trait_{choice_name.lower().replace(' ', '_')}",
        ]:
            if key in choices_made:
                strict_mode.warn_choice_fallback(choice_name, key)
                return choices_made[key]
        return None

    def _apply_feature_scaling(self, description: str, scaling: Dict[str, Any]) -> str:
        """
        Apply scaling substitutions to feature description.

        Args:
            description: Feature description with template variables
            scaling: Scaling configuration

        Returns:
            Description with substituted values
        """
        level = self.character_data.get("level", 1)

        for var_name, scale_list in scaling.items():
            # Find the appropriate value for current level
            value = None
            for scale_entry in scale_list:
                min_level = scale_entry.get("min_level", 1)
                if level >= min_level:
                    value = scale_entry.get("value")

            # Replace template variable
            if value is not None:
                description = description.replace(f"{{{var_name}}}", str(value))

        return description

    def _apply_effect(self, effect: Dict[str, Any], source_name: str, source_type: str, source_class_name: Optional[str] = None):
        """
        Apply a single effect from the effects system.

        Args:
            effect: Effect dictionary with 'type' and other parameters
            source_name: Name of the feature/trait providing the effect
            source_type: Type of source ('species', 'lineage', 'class', etc.)
            source_class_name: For class/subclass effects, the originating class name
                (used so per-level scaling is scoped to that class's level in multiclass).
        """

        effect_type = effect.get("type")
        strict_mode.check_effect_type(effect_type, source_name)

        def _resolve_choice_reference(ref: str):
            # Only handles ${cantrips[0]}, ${cantrips[1]}, ${1st_level_spell}, etc.
            import re
            m = re.match(r"^\$\{(.+?)\}$", ref)
            if not m:
                return ref
            key = m.group(1)
            # Handle cantrips[0], cantrips[1], 1st_level_spell, etc.
            if key.startswith("cantrips["):
                idx = int(key[len("cantrips["):-1])
                cantrips = []
                # Try to find the feat name from the effect context
                # This is only used for feat effects (e.g. Magic Initiate)
                for feat_key, value in self.character_data.get("choices_made", {}).items():
                    if feat_key.endswith("cantrips") and isinstance(value, list):
                        cantrips = value
                        break
                if idx < len(cantrips):
                    return cantrips[idx]
                return None
            elif key == "1st_level_spell":
                # Find the spell choice for 1st_level_spell
                for feat_key, value in self.character_data.get("choices_made", {}).items():
                    if feat_key.endswith("1st_level_spell") and value:
                        if isinstance(value, list):
                            return value[0]
                        return value
                # Some feats use 'spell' as the key
                for feat_key, value in self.character_data.get("choices_made", {}).items():
                    if feat_key.endswith("spell") and value:
                        if isinstance(value, list):
                            return value[0]
                        return value
            elif key == "spellcasting_ability":
                for feat_key, value in self.character_data.get("choices_made", {}).items():
                    if feat_key.endswith("spellcasting_ability") and value:
                        if isinstance(value, list):
                            return value[0]
                        return value
                return None
            return None

        if effect_type == "grant_cantrip":
            if "from_choice" in effect:
                choice_key = effect["from_choice"]
                clean_key = choice_key[9:] if choice_key.startswith("subclass_") else choice_key
                short_key = choice_key.split("_")[-1]
                spell_name = (
                    self.character_data.get("choices_made", {}).get(choice_key)
                    or self.character_data.get("choices_made", {}).get(clean_key)
                    or self.character_data.get("choices_made", {}).get(short_key)
                    or self._resolve_choice_value(choice_key)
                )
            else:
                spell_name = effect.get("spell") or effect.get("cantrip")
            counts_against_limit = effect.get("counts_against_limit", False)

            # Resolve choice reference if present
            resolved_spell = None
            if isinstance(spell_name, str) and spell_name.startswith("${"):
                resolved_spell = _resolve_choice_reference(spell_name)
            else:
                resolved_spell = spell_name

            ability_ref = effect.get("spellcasting_ability") or effect.get("ability")
            resolved_ability = None
            if isinstance(ability_ref, str) and ability_ref.startswith("${"):
                resolved_ability = _resolve_choice_reference(ability_ref)
            elif isinstance(ability_ref, str):
                resolved_ability = ability_ref

            if resolved_spell:
                # Map source_type to actual display name
                if source_type == "species":
                    display_source = self.character_data.get("species", source_name)
                elif source_type == "lineage":
                    display_source = self.character_data.get("lineage", source_name)
                elif source_type == "class":
                    display_source = self.character_data.get("class", source_name)
                elif source_type == "subclass":
                    display_source = self.character_data.get("subclass", source_name)
                else:
                    display_source = source_name

                # Add to always_prepared dict with metadata
                prepared_info = {
                    "level": 0,
                    "source": display_source,
                    "always_prepared": True,
                    "counts_against_limit": counts_against_limit,
                }
                if resolved_ability:
                    prepared_info["spellcasting_ability"] = resolved_ability
                self.character_data["spells"]["always_prepared"][resolved_spell] = prepared_info

                # Also track in spell_metadata for compatibility
                meta_info = {
                    "source": display_source,
                    "source_type": source_type,
                    "always_prepared": True,
                    "once_per_day": False,
                    "counts_against_limit": counts_against_limit,
                }
                if resolved_ability:
                    meta_info["spellcasting_ability"] = resolved_ability
                self.character_data["spell_metadata"][resolved_spell] = meta_info

        elif effect_type == "grant_cantrip_choice":
            # This branch intentionally does nothing here.  The cantrip choice
            # is deferred to the choice resolver: when the player selects a
            # cantrip (via a feat or feature choice), apply_choice() resolves
            # the name and calls _apply_effect(grant_cantrip).  This branch
            # must remain so strict_mode.check_effect_type() does not raise an
            # "unknown effect type" warning for data files that carry this type.
            pass

        elif effect_type == "grant_spell":
            if "from_choice" in effect:
                choice_key = effect["from_choice"]
                clean_key = choice_key[9:] if choice_key.startswith("subclass_") else choice_key
                short_key = choice_key.split("_")[-1]
                spell_name = (
                    self.character_data.get("choices_made", {}).get(choice_key)
                    or self.character_data.get("choices_made", {}).get(clean_key)
                    or self.character_data.get("choices_made", {}).get(short_key)
                    or self._resolve_choice_value(choice_key)
                )
            else:
                spell_name = effect.get("spell")
            min_level = effect.get("min_level", 1)
            counts_against_limit = effect.get("counts_against_limit", False)

            # Resolve choice reference if present
            resolved_spell = None
            if isinstance(spell_name, str) and spell_name.startswith("${"):
                resolved_spell = _resolve_choice_reference(spell_name)
            else:
                resolved_spell = spell_name

            ability_ref = effect.get("spellcasting_ability") or effect.get("ability")
            resolved_ability = None
            if isinstance(ability_ref, str) and ability_ref.startswith("${"):
                resolved_ability = _resolve_choice_reference(ability_ref)
            elif isinstance(ability_ref, str):
                resolved_ability = ability_ref

            effective_level = self.character_data["level"]
            if source_class_name and source_type in ("class", "subclass"):
                class_levels = self.character_data.get("class_levels", {})
                if source_class_name in class_levels:
                    effective_level = class_levels[source_class_name]

            if resolved_spell and effective_level >= min_level:
                # Load spell definition to get actual spell level
                spell_def = self._load_spell_definition(resolved_spell)
                spell_level = spell_def.get("level", 1)

                # Map source_type to actual name for display
                if source_type == "species":
                    display_source = self.character_data.get("species", source_name)
                elif source_type == "lineage":
                    display_source = self.character_data.get("lineage", source_name)
                elif source_type == "class":
                    display_source = self.character_data.get("class", source_name)
                elif source_type == "subclass":
                    display_source = self.character_data.get("subclass", source_name)
                elif source_type == "background":
                    display_source = self.character_data.get("background", source_name)
                else:
                    display_source = source_name

                # Species/lineage grants retain the legacy once-per-day flag.
                # Explicit long-rest grants carry their independent metadata.
                once_per_long_rest = bool(effect.get("once_per_long_rest", False))
                once_per_day = source_type in ["species", "lineage"]

                # Add to always_prepared dict with metadata
                prepared_info = {
                    "level": spell_level,
                    "source": display_source,
                    "always_prepared": True,
                    "once_per_day": once_per_day,
                    "once_per_long_rest": once_per_long_rest,
                    "counts_against_limit": counts_against_limit,
                }
                if resolved_ability:
                    prepared_info["spellcasting_ability"] = resolved_ability
                self.character_data["spells"]["always_prepared"][resolved_spell] = prepared_info

                # Also track in spell_metadata for compatibility
                meta_info = {
                    "source": display_source,
                    "source_type": source_type,
                    "once_per_day": once_per_day,
                    "once_per_long_rest": once_per_long_rest,
                    "always_prepared": True,
                    "counts_against_limit": counts_against_limit,
                }
                if resolved_ability:
                    meta_info["spellcasting_ability"] = resolved_ability
                self.character_data["spell_metadata"][resolved_spell] = meta_info

        elif effect_type == "grant_weapon_proficiency":
            proficiencies = effect.get("proficiencies", [])
            for prof in proficiencies:
                if prof not in self.character_data["proficiencies"]["weapons"]:
                    self.character_data["proficiencies"]["weapons"].append(prof)
                    # Track the source of this weapon proficiency
                    if source_type == "species_choice":
                        source_display = self.character_data.get("species", source_name)
                    elif source_type in ["species", "lineage"]:
                        source_display = self.character_data.get("species", source_name)
                    else:
                        source_display = source_name
                    self.character_data["proficiency_sources"]["weapons"][prof] = (
                        source_display
                    )

        elif effect_type == "grant_armor_proficiency":
            proficiencies = effect.get("proficiencies", [])
            for prof in proficiencies:
                if prof not in self.character_data["proficiencies"]["armor"]:
                    self.character_data["proficiencies"]["armor"].append(prof)
                    # Track the source of this armor proficiency
                    if source_type == "species_choice":
                        source_display = self.character_data.get("species", source_name)
                    elif source_type in ["species", "lineage"]:
                        source_display = self.character_data.get("species", source_name)
                    else:
                        source_display = source_name
                    self.character_data["proficiency_sources"]["armor"][prof] = (
                        source_display
                    )

        elif effect_type == "grant_tool_proficiency":
            if "from_choice" in effect:
                choice_key = effect["from_choice"]
                clean_key = choice_key[9:] if choice_key.startswith("subclass_") else choice_key
                short_key = choice_key.split("_")[-1]
                chosen = (
                    self.character_data.get("choices_made", {}).get(choice_key)
                    or self.character_data.get("choices_made", {}).get(clean_key)
                    or self.character_data.get("choices_made", {}).get(short_key)
                    or self._resolve_choice_value(choice_key)
                )
                tools = chosen if isinstance(chosen, list) else [chosen] if chosen else []
            elif "tools" in effect:
                tools = effect.get("tools", [])
            elif "tool" in effect:
                tools = [effect["tool"]] if effect["tool"] else []
            else:
                tools = []
            for tool in tools:
                if not isinstance(tool, str) or not tool:
                    continue
                if tool not in self.character_data["proficiencies"]["tools"]:
                    self.character_data["proficiencies"]["tools"].append(tool)
                    # Track the source of this tool proficiency
                    if source_type == "species_choice":
                        source_display = self.character_data.get("species", source_name)
                    elif source_type in ["species", "lineage"]:
                        source_display = self.character_data.get("species", source_name)
                    else:
                        source_display = source_name
                    self.character_data["proficiency_sources"]["tools"][tool] = (
                        source_display
                    )

        elif effect_type == "grant_skill_proficiency":
            if "from_choice" in effect:
                choice_key = effect["from_choice"]
                clean_key = choice_key[9:] if choice_key.startswith("subclass_") else choice_key
                short_key = choice_key.split("_")[-1]
                chosen = (
                    self.character_data.get("choices_made", {}).get(choice_key)
                    or self.character_data.get("choices_made", {}).get(clean_key)
                    or self.character_data.get("choices_made", {}).get(short_key)
                    or self._resolve_choice_value(choice_key)
                )
                skills = chosen if isinstance(chosen, list) else [chosen] if chosen else []
            elif isinstance(effect.get("skills"), str) and effect["skills"].startswith("$"):
                choice_key = effect["skills"][1:]
                clean_key = choice_key[9:] if choice_key.startswith("subclass_") else choice_key
                short_key = choice_key.split("_")[-1]
                chosen = (
                    self.character_data.get("choices_made", {}).get(choice_key)
                    or self.character_data.get("choices_made", {}).get(clean_key)
                    or self.character_data.get("choices_made", {}).get(short_key)
                    or self._resolve_choice_value(choice_key)
                )
                skills = chosen if isinstance(chosen, list) else [chosen] if chosen else []
            else:
                raw_skills = effect.get("skills", [])
                skills = [raw_skills] if isinstance(raw_skills, str) else (raw_skills if isinstance(raw_skills, list) else [])
            for skill in skills:
                if (
                    not isinstance(skill, str)
                    or not skill
                    or is_unresolved_placeholder(skill)
                    or skill.startswith("$")
                    or len(skill) <= 1
                ):
                    continue
                if skill not in self.character_data["proficiencies"]["skills"]:
                    self.character_data["proficiencies"]["skills"].append(skill)
                    # Track the source of this skill proficiency
                    if source_type == "species_choice":
                        # For species choices, use just the species name
                        source_display = self.character_data.get("species", source_name)
                    elif source_type in ["species", "lineage"]:
                        source_display = self.character_data.get("species", source_name)
                    else:
                        source_display = source_name
                    self.character_data["proficiency_sources"]["skills"][skill] = (
                        source_display
                    )
                elif source_type in (
                    "species", "species_choice", "lineage", "lineage_choice"
                ):
                    # Skill overlap — species/lineage tried to grant a skill
                    # the character already has. Track for replacement choice.
                    needed = self.character_data["choices_made"].get(
                        "species_skill_replacements_needed", 0
                    )
                    self.character_data["choices_made"][
                        "species_skill_replacements_needed"
                    ] = needed + 1
                elif source_type == "background":
                    # Phase 9 (D1-1): background skill overlap. D&D 2024:
                    # overlapping background skill proficiencies are replaced
                    # by player's choice. Track count for the wizard prompt.
                    needed = self.character_data["choices_made"].get(
                        "background_skill_replacements_needed", 0
                    )
                    self.character_data["choices_made"][
                        "background_skill_replacements_needed"
                    ] = needed + 1

        elif effect_type == "grant_skill_expertise":
            # Resolve skills from a choice key if specified, otherwise use direct list
            if "from_choice" in effect:
                choice_key = effect["from_choice"]
                clean_key = choice_key[9:] if choice_key.startswith("subclass_") else choice_key
                short_key = choice_key.split("_")[-1]
                chosen = (
                    self.character_data.get("choices_made", {}).get(choice_key)
                    or self.character_data.get("choices_made", {}).get(clean_key)
                    or self.character_data.get("choices_made", {}).get(short_key)
                    or self._resolve_choice_value(choice_key)
                )
                if isinstance(chosen, list):
                    skills = chosen
                elif isinstance(chosen, str) and chosen:
                    skills = [chosen]
                else:
                    skills = []
            else:
                skills = effect.get("skills", [])
            if "skill_expertise" not in self.character_data:
                self.character_data["skill_expertise"] = []
            for skill in skills:
                # Skip unresolved choice placeholders (e.g. Ranger still uses
                # "__deft_explorer_expertise__" / "__expertise_skills__" until
                # those classes are migrated to the from_choice pattern).
                if skill.startswith("__"):
                    continue
                if skill not in self.character_data["skill_expertise"]:
                    self.character_data["skill_expertise"].append(skill)

        elif effect_type == "grant_skill_proficiency_or_expertise":
            # D&D 2024 pattern: "If you lack proficiency, gain proficiency;
            # if you already have proficiency, gain Expertise."
            skills = effect.get("skills", [])
            if "skill_expertise" not in self.character_data:
                self.character_data["skill_expertise"] = []
            for skill in skills:
                if skill in self.character_data["proficiencies"]["skills"]:
                    # Already proficient → grant expertise
                    if skill not in self.character_data["skill_expertise"]:
                        self.character_data["skill_expertise"].append(skill)
                else:
                    # Not proficient → grant proficiency
                    self.character_data["proficiencies"]["skills"].append(skill)
                    self.character_data["proficiency_sources"]["skills"][skill] = (
                        source_name
                    )

        elif effect_type == "grant_save_advantage":
            abilities = effect.get("abilities") or ([effect["ability"]] if "ability" in effect else [])
            display = effect.get("display") or source_name or ""
            condition = effect.get("condition", "")
            # Avoid duplicate entries
            if (abilities or condition) and not any(
                e.get("abilities") == abilities and e.get("condition") == condition
                for e in self.character_data["save_advantages"]
            ):
                self.character_data["save_advantages"].append({
                    "abilities": abilities,
                    "display": display,
                    "condition": condition,
                })

        elif effect_type == "grant_damage_resistance":
            # Accept both singular and plural damage type forms:
            #   {"type": "grant_damage_resistance", "damage_type": "Poison"}
            #   {"type": "grant_damage_resistance", "damage_types": ["Poison", "Cold"]}
            # The plural form is the preferred shape; singular is kept for
            # back-compat with existing data files.
            damage_types = effect.get("damage_types") or (
                [effect["damage_type"]] if "damage_type" in effect else []
            )
            # Support dynamic damage type resolved from a species/trait choice
            if not damage_types and "damage_type_from_choice" in effect:
                choice_value = self._resolve_choice_value(effect["damage_type_from_choice"])
                if choice_value:
                    damage_types = [self._extract_parenthetical(choice_value)]
            for damage_type in damage_types:
                if damage_type and damage_type not in self.character_data["resistances"]:
                    self.character_data["resistances"].append(damage_type)

        elif effect_type == "grant_damage_immunity":
            damage_types = effect.get("damage_types") or (
                [effect["damage_type"]] if "damage_type" in effect else []
            )
            for damage_type in damage_types:
                if damage_type and damage_type not in self.character_data["immunities"]:
                    self.character_data["immunities"].append(damage_type)

        elif effect_type == "grant_condition_immunity":
            condition = effect.get("condition")
            if condition and condition not in self.character_data["condition_immunities"]:
                self.character_data["condition_immunities"].append(condition)

        elif effect_type == "grant_darkvision":
            darkvision_range = effect.get("range", 60)
            if darkvision_range > self.character_data["darkvision"]:
                self.character_data["darkvision"] = darkvision_range

        elif effect_type == "increase_speed":
            speed_increase = effect.get("value", 0)
            feature_group = effect.get("feature_group")
            if feature_group:
                previous = self.character_data["speed_bonuses"].get(feature_group, 0)
                self.character_data["speed"] = self.character_data["speed"] - previous + speed_increase
                self.character_data["speed_bonuses"][feature_group] = speed_increase
            else:
                self.character_data["speed"] += speed_increase

        elif effect_type == "ability_bonus":
            # Store ability bonuses for later calculation (like Thaumaturge)
            if "ability_bonuses" not in self.character_data:
                self.character_data["ability_bonuses"] = []

            bonus_info = {
                "ability": effect.get("ability"),
                "skills": effect.get("skills", []),
                "value": effect.get("value"),
                "minimum": effect.get("minimum", 0),
                "maximum": effect.get("maximum", 20),
                "source": source_name,
            }
            self.character_data["ability_bonuses"].append(bonus_info)

        elif effect_type == "grant_save_proficiency":
            abilities = effect.get("abilities", [])
            for ability in abilities:
                if ability not in self.character_data["proficiencies"]["saving_throws"]:
                    self.character_data["proficiencies"]["saving_throws"].append(ability)
                    self.character_data["proficiency_sources"]["saving_throws"][ability] = source_name

        elif effect_type == "alternative_ac":
            # Monk/Barbarian Unarmored Defense and similar formulas.
            # Stored on a structured field that ``calculate_ac_options``
            # consumes directly. (Audit log still receives the entry via the
            # tail of ``_apply_effect``.)
            entry = {
                "base": effect.get("base", 10),
                "modifiers": list(effect.get("modifiers", [])),
                "condition": effect.get("condition", ""),
                "source": source_name,
                "source_type": source_type,
            }
            # Idempotent: do not double-store an identical entry from the
            # same source.
            existing = self.character_data["alternative_ac_options"]
            if not any(
                e["source"] == entry["source"]
                and e["base"] == entry["base"]
                and e["modifiers"] == entry["modifiers"]
                and e.get("condition", "") == entry["condition"]
                for e in existing
            ):
                existing.append(entry)

        elif effect_type == "bonus_damage":
            # Fighting styles (Dueling, Thrown Weapon Fighting), feats, etc.
            entry = {
                "value": effect.get("value", 0),
                "condition": effect.get("condition", ""),
                "weapon_property": effect.get("weapon_property"),
                "damage_type": effect.get("damage_type"),
                "source": source_name,
                "source_type": source_type,
                "source_class_name": source_class_name,
            }
            self.character_data["damage_bonuses"].append(entry)

        elif effect_type == "bonus_attack":
            entry = {
                "value": effect.get("value", 0),
                "weapon_property": effect.get("weapon_property"),
                "condition": effect.get("condition", ""),
                "source": source_name,
                "source_type": source_type,
                "source_class_name": source_class_name,
            }
            self.character_data["attack_bonuses"].append(entry)

        elif effect_type == "bonus_ac":
            entry = {
                "value": effect.get("value", 0),
                "condition": effect.get("condition", ""),
                "source": source_name,
                "source_type": source_type,
                "source_class_name": source_class_name,
            }
            self.character_data["ac_bonuses"].append(entry)

        elif effect_type == "bonus_hp":
            entry = {
                "value": effect.get("value", 0),
                "scaling": effect.get("scaling"),
                "source": source_name,
                "source_type": source_type,
                "source_class_name": source_class_name,
            }
            self.character_data["hp_bonuses"].append(entry)

        elif effect_type == "bonus_initiative":
            self.character_data["initiative_bonuses"].append(
                self._build_initiative_bonus_entry(
                    effect,
                    source_name,
                    source_type,
                    source_class_name,
                )
            )

        elif effect_type == "great_weapon_fighting":
            flags = self.character_data["fighting_style_flags"]["great_weapon_fighting"]
            if source_name not in flags:
                flags.append(source_name)

        elif effect_type == "two_weapon_fighting_modifier":
            flags = self.character_data["fighting_style_flags"]["two_weapon_fighting_modifier"]
            if source_name not in flags:
                flags.append(source_name)

        elif effect_type == "unarmed_fighting":
            flags = self.character_data["fighting_style_flags"]["unarmed_fighting"]
            if source_name not in flags:
                flags.append(source_name)

        elif effect_type == "set_martial_arts_die":
            # Monk: resolve the correct Martial Arts die for the current level
            die_by_level = effect.get("die_by_level", {})
            level = self.character_data.get("level", 1)
            resolved_die = "1d6"  # fallback
            for level_threshold, die in sorted(
                die_by_level.items(), key=lambda x: int(x[0])
            ):
                if level >= int(level_threshold):
                    resolved_die = die
            self.character_data["martial_arts_die"] = resolved_die

        elif effect_type == "monk_dexterous_attacks":
            # Monk: Dexterous Attacks allows using DEX instead of STR for
            # attack and damage rolls of monk weapons (Simple Melee, or
            # Martial Melee with Light property)
            self.character_data["monk_dexterous_attacks"] = True

        elif effect_type == "attack_ability_override":
            ability = effect.get("ability")
            weapon_tag = effect.get("weapon_tag")
            if isinstance(ability, str) and isinstance(weapon_tag, str):
                self.character_data["attack_ability_overrides"].append({
                    "ability": ability,
                    "weapon_tag": weapon_tag,
                    "source": source_name,
                    "source_type": source_type,
                })

        elif effect_type == "grant_language":
            # Resolve languages from a choice key if specified, otherwise use direct list
            if "from_choice" in effect:
                choice_key = effect["from_choice"]
                chosen = self.character_data.get("choices_made", {}).get(choice_key)
                if isinstance(chosen, list):
                    languages = chosen
                elif isinstance(chosen, str) and chosen:
                    languages = [chosen]
                else:
                    languages = []
            elif "languages" in effect:
                languages = effect.get("languages", [])
            elif "language" in effect:
                languages = [effect["language"]] if effect["language"] else []
            else:
                languages = []
            for lang in languages:
                if lang not in self.character_data["proficiencies"]["languages"]:
                    self.character_data["proficiencies"]["languages"].append(lang)
                    if source_type == "species":
                        source_display = "species"
                    elif source_type == "lineage":
                        source_display = "lineage"
                    else:
                        source_display = source_name
                    self.character_data["proficiency_sources"]["languages"][lang] = source_display

        elif effect_type == "grant_origin_feat":
            feat_name = effect.get("feat")
            if feat_name:
                feat_data = self._load_feat_data(feat_name)
                if feat_data:
                    description = feat_data.get("description", "")
                    benefits = feat_data.get("benefits", [])
                    if benefits:
                        description += self._format_benefits(benefits)
                else:
                    description = f"Origin feat: {feat_name}"

                feat_entry = {
                    "name": feat_name,
                    "description": description,
                    "source": source_name,
                }
                if not any(
                    f["name"] == feat_name
                    for f in self.character_data["features"]["feats"]
                ):
                    self.character_data["features"]["feats"].append(feat_entry)

                # Apply any direct effects from the feat (e.g., Tough's bonus_hp)
                if feat_data:
                    for feat_effect in feat_data.get("effects", []):
                        self._apply_effect(feat_effect, feat_name, "feat")

                # If granted via a species/lineage choice and the feat has
                # follow-up choices (e.g., Skilled needs 3 skill/tool picks),
                # record the feat name so the species route can present them.
                # Feats with no choices (e.g., Alert, Tough) need no follow-up.
                if source_type in ("species_choice", "lineage_choice") and feat_data:
                    if feat_data.get("choices") or feat_data.get("choice_options"):
                        self.character_data["pending_species_feat"] = feat_name
                    else:
                        self.character_data.pop("pending_species_feat", None)

        # ------------------------------------------------------------------
        # Phase 7 (D0-1 / D0-2 / D4-3) handlers — invocations, maneuvers,
        # weapon masteries, and the spell-modifier effects they need.
        # ------------------------------------------------------------------

        elif effect_type == "grant_spell_at_will":
            # Sheet-affecting: spell becomes part of the character's
            # always-available list (typical Warlock invocation pattern,
            # e.g. Armor of Shadows -> Mage Armor). Recorded in the same
            # `always_prepared` dict that `grant_spell` writes to, with an
            # `at_will: True` flag so renderers can annotate "(at will)".
            if "from_choice" in effect:
                chosen = self.character_data.get("choices_made", {}).get(
                    effect["from_choice"]
                )
                spell_names = chosen if isinstance(chosen, list) else [chosen] if chosen else []
            else:
                spell_names = [effect.get("spell")]

            eligible_from = effect.get("eligible_from")
            if eligible_from == "spellbook":
                spellbook = self.character_data["spells"].get("spellbook", {})
                if isinstance(spellbook, dict):
                    eligible_names = set(spellbook)
                elif isinstance(spellbook, list):
                    eligible_names = {
                        item if isinstance(item, str) else item.get("name")
                        for item in spellbook
                        if isinstance(item, (str, dict))
                    }
                else:
                    eligible_names = set()
                spell_names = [name for name in spell_names if name in eligible_names]

            required_casting_time = effect.get("casting_time")
            if required_casting_time:
                req_norm = str(required_casting_time).lower().replace("1 ", "").strip()
                if any(
                    not isinstance(name, str)
                    or str(self._load_spell_definition(name).get("casting_time", "")).lower().replace("1 ", "").strip()
                    != req_norm
                    for name in spell_names
                ):
                    spell_names = []

            required_levels = effect.get("spell_levels")
            if isinstance(required_levels, list):
                selected_levels = [
                    self._load_spell_definition(name).get("level")
                    for name in spell_names
                    if isinstance(name, str)
                ]
                if sorted(selected_levels) != sorted(required_levels):
                    spell_names = []

            for spell_name in spell_names:
                if not isinstance(spell_name, str) or not spell_name:
                    continue
                spell_def = self._load_spell_definition(spell_name) or {}
                spell_level = spell_def.get("level", 0)
                if source_type == "subclass":
                    display_source = self.character_data.get("subclass", source_name)
                elif source_type == "class":
                    display_source = self.character_data.get("class", source_name)
                else:
                    display_source = source_name

                # Idempotent: write/refresh the same record on re-apply.
                self.character_data["spells"]["always_prepared"][spell_name] = {
                    "level": spell_level,
                    "source": display_source,
                    "always_prepared": True,
                    "at_will": True,
                    "once_per_day": False,
                    "counts_against_limit": False,
                }
                self.character_data["spell_metadata"][spell_name] = {
                    "source": display_source,
                    "source_type": source_type,
                    "always_prepared": True,
                    "at_will": True,
                    "once_per_day": False,
                    "counts_against_limit": False,
                }

        elif effect_type == "bonus_spell_damage_ability_mod":
            # Agonizing Blast: add a chosen ability's modifier to the damage
            # rolls of a specific spell. Written into spell_metadata[spell]["damage_bonus"]
            # (P2-4 consolidation) so the renderer / `calculate_spellcasting_stats`
            # can annotate the spell via a single metadata dict.
            spell_name = effect.get("spell")
            ability = effect.get("ability")
            if isinstance(spell_name, str) and isinstance(ability, str):
                self.character_data["spell_metadata"].setdefault(spell_name, {})["damage_bonus"] = {
                    "ability": ability,
                    "source": source_name,
                    "source_type": source_type,
                }

        elif effect_type == "bonus_spell_range":
            # Eldritch Spear: overrides the displayed range of a specific
            # spell. Written into spell_metadata[spell]["range_override"]
            # (P2-4 consolidation). `to_character()` reads from there when
            # emitting `spells_by_level` so the override is visible on the sheet.
            spell_name = effect.get("spell")
            new_range = effect.get("range")
            if isinstance(spell_name, str) and new_range:
                self.character_data["spell_metadata"].setdefault(spell_name, {})["range_override"] = {
                    "range": new_range,
                    "source": source_name,
                    "source_type": source_type,
                }

        elif effect_type == "grant_magical_darkness_sight":
            # Devil's Sight: see normally in magical darkness up to N feet.
            # Kept distinct from `grant_darkvision` because the underlying
            # rule is genuinely different (magical darkness specifically).
            range_ft = int(effect.get("range", 120) or 0)
            current = self.character_data.get("magical_darkness_sight") or {}
            if range_ft > int(current.get("range", 0) or 0):
                self.character_data["magical_darkness_sight"] = {
                    "range": range_ft,
                    "source": source_name,
                    "source_type": source_type,
                }

        elif effect_type == "grant_maneuver":
            # Battle Master maneuver pick. Idempotent: do not duplicate names.
            maneuver_name = effect.get("maneuver")
            if isinstance(maneuver_name, str) and maneuver_name:
                if maneuver_name not in self.character_data["maneuvers_known"]:
                    self.character_data["maneuvers_known"].append(maneuver_name)

        elif effect_type == "grant_superiority_dice":
            # Battle Master Combat Superiority. Resolves per-level scaling
            # (count_by_level / die_by_level) against the current class
            # level; idempotent rewrite of the structured field.
            level = self.character_data.get("level", 1)
            count_by_level = effect.get("count_by_level") or {}
            die_by_level = effect.get("die_by_level") or {}
            count = int(effect.get("count", 0) or 0)
            die = effect.get("die", "d8") or "d8"
            for threshold, value in sorted(
                count_by_level.items(), key=lambda kv: int(kv[0])
            ):
                if level >= int(threshold):
                    count = int(value)
            for threshold, value in sorted(
                die_by_level.items(), key=lambda kv: int(kv[0])
            ):
                if level >= int(threshold):
                    die = str(value)
            if count > 0:
                self.character_data["superiority_dice"] = {
                    "count": count,
                    "die": die,
                    "source": source_name,
                }

        elif effect_type == "grant_arcane_shot":
            shot_name = effect.get("shot") or effect.get("arcane_shot")
            if isinstance(shot_name, str) and shot_name:
                known = self.character_data.setdefault("arcane_shots_known", [])
                if shot_name not in known:
                    known.append(shot_name)

        elif effect_type == "grant_arcane_shot_dice":
            level = self.character_data.get("level", 1)
            die_by_level = effect.get("die_by_level") or {}
            die = effect.get("die", "d6") or "d6"
            for threshold, value in sorted(
                die_by_level.items(), key=lambda kv: int(kv[0])
            ):
                if level >= int(threshold):
                    die = str(value)
            self.character_data["arcane_shot_die"] = die

        elif effect_type == "grant_spell_slots":
            # Grant additional spell slots.  Supports two shapes:
            #   {"type": "grant_spell_slots", "slots": {"1": 2, "3": 1}}
            #   {"type": "grant_spell_slots", "slot_level": 1, "count": 2}
            # Slots are additive — multiple effects of this type stack.
            slots_map = effect.get("slots") or {}
            if not slots_map and "slot_level" in effect:
                slots_map = {str(effect["slot_level"]): effect.get("count", 1)}
            for lvl, cnt in slots_map.items():
                key = str(lvl)
                self.character_data["spells"]["slots"][key] = (
                    self.character_data["spells"]["slots"].get(key, 0) + int(cnt)
                )

        elif effect_type == "grant_weapon_mastery":
            # Grant a specific weapon mastery.
            # effect shape: {"type": "grant_weapon_mastery", "weapon": "Longsword"}
            weapon = effect.get("weapon", "")
            if weapon:
                selected = self.character_data["weapon_masteries"].setdefault("selected", [])
                if weapon not in selected:
                    selected.append(weapon)

        # Track applied effect — AUDIT LOG ONLY. See class-level docstring on
        # ``applied_effects`` for the contract.
        tracked: Dict[str, Any] = {
            "type": effect_type,
            "source": source_name,
            "source_type": source_type,
            "effect": effect,
        }
        if source_class_name:
            tracked["source_class_name"] = source_class_name
        self.applied_effects.append(tracked)

    # ------------------------------------------------------------------
    # Phase 6: applied_effects pruning + structured-bonus invariance
    # ------------------------------------------------------------------

    def _rebuild_structured_bonuses(self) -> None:
        """Rebuild structured bonus fields from the current ``applied_effects``.

        Called by ``_filter_applied_effects`` after the audit log has been
        pruned (e.g. on class/subclass/lineage change, or after replacing a
        feat in a class slot). This is the *only* path by which structured
        bonus fields are derived from ``applied_effects``; calculation
        methods never re-derive them and never read ``applied_effects``
        directly.
        """
        self.character_data["damage_bonuses"] = []
        self.character_data["attack_bonuses"] = []
        self.character_data["ac_bonuses"] = []
        self.character_data["hp_bonuses"] = []
        self.character_data["initiative_bonuses"] = []
        self.character_data["alternative_ac_options"] = []
        self.character_data["fighting_style_flags"] = {
            "great_weapon_fighting": [],
            "two_weapon_fighting_modifier": [],
            "unarmed_fighting": [],
        }
        # Phase 7: rebuildable structured fields owned by new effect types.
        self.character_data["maneuvers_known"] = []
        self.character_data["superiority_dice"] = {}
        self.character_data["arcane_shots_known"] = []
        self.character_data["arcane_shot_die"] = None
        self.character_data["magical_darkness_sight"] = {}
        # P2-4: damage/range overrides live inside spell_metadata sub-keys;
        # clear only those sub-keys rather than a separate top-level dict.
        for meta in self.character_data.get("spell_metadata", {}).values():
            meta.pop("damage_bonus", None)
            meta.pop("range_override", None)

        for tracked in self.applied_effects:
            effect = tracked.get("effect", {})
            etype = effect.get("type") or tracked.get("type")
            source = tracked.get("source", "Unknown")
            stype = tracked.get("source_type", "")
            sclass = tracked.get("source_class_name")

            if etype == "bonus_damage":
                self.character_data["damage_bonuses"].append({
                    "value": effect.get("value", 0),
                    "condition": effect.get("condition", ""),
                    "weapon_property": effect.get("weapon_property"),
                    "damage_type": effect.get("damage_type"),
                    "source": source,
                    "source_type": stype,
                    "source_class_name": sclass,
                })
            elif etype == "bonus_attack":
                self.character_data["attack_bonuses"].append({
                    "value": effect.get("value", 0),
                    "weapon_property": effect.get("weapon_property"),
                    "condition": effect.get("condition", ""),
                    "source": source,
                    "source_type": stype,
                    "source_class_name": sclass,
                })
            elif etype == "bonus_ac":
                self.character_data["ac_bonuses"].append({
                    "value": effect.get("value", 0),
                    "condition": effect.get("condition", ""),
                    "source": source,
                    "source_type": stype,
                    "source_class_name": sclass,
                })
            elif etype == "bonus_hp":
                self.character_data["hp_bonuses"].append({
                    "value": effect.get("value", 0),
                    "scaling": effect.get("scaling"),
                    "source": source,
                    "source_type": stype,
                    "source_class_name": sclass,
                })
            elif etype == "bonus_initiative":
                self.character_data["initiative_bonuses"].append(
                    self._build_initiative_bonus_entry(
                        effect,
                        source,
                        stype,
                        sclass,
                    )
                )
            elif etype == "alternative_ac":
                self.character_data["alternative_ac_options"].append({
                    "base": effect.get("base", 10),
                    "modifiers": list(effect.get("modifiers", [])),
                    "condition": effect.get("condition", ""),
                    "source": source,
                    "source_type": stype,
                })
            elif etype == "great_weapon_fighting":
                flags = self.character_data["fighting_style_flags"]["great_weapon_fighting"]
                if source not in flags:
                    flags.append(source)
            elif etype == "two_weapon_fighting_modifier":
                flags = self.character_data["fighting_style_flags"]["two_weapon_fighting_modifier"]
                if source not in flags:
                    flags.append(source)
            elif etype == "unarmed_fighting":
                flags = self.character_data["fighting_style_flags"]["unarmed_fighting"]
                if source not in flags:
                    flags.append(source)
            # Phase 7 rebuildable types
            elif etype == "grant_maneuver":
                name = effect.get("maneuver")
                if isinstance(name, str) and name and name not in self.character_data["maneuvers_known"]:
                    self.character_data["maneuvers_known"].append(name)
            elif etype == "grant_superiority_dice":
                level = self.character_data.get("level", 1)
                count_by_level = effect.get("count_by_level") or {}
                die_by_level = effect.get("die_by_level") or {}
                count = int(effect.get("count", 0) or 0)
                die = effect.get("die", "d8") or "d8"
                for threshold, value in sorted(count_by_level.items(), key=lambda kv: int(kv[0])):
                    if level >= int(threshold):
                        count = int(value)
                for threshold, value in sorted(die_by_level.items(), key=lambda kv: int(kv[0])):
                    if level >= int(threshold):
                        die = str(value)
                if count > 0:
                    self.character_data["superiority_dice"] = {
                        "count": count,
                        "die": die,
                        "source": source,
                    }
            elif etype == "grant_arcane_shot":
                name = effect.get("shot") or effect.get("arcane_shot")
                if isinstance(name, str) and name and name not in self.character_data["arcane_shots_known"]:
                    self.character_data["arcane_shots_known"].append(name)
            elif etype == "grant_arcane_shot_dice":
                level = self.character_data.get("level", 1)
                die_by_level = effect.get("die_by_level") or {}
                die = effect.get("die", "d6") or "d6"
                for threshold, value in sorted(die_by_level.items(), key=lambda kv: int(kv[0])):
                    if level >= int(threshold):
                        die = str(value)
                self.character_data["arcane_shot_die"] = die
            elif etype == "grant_magical_darkness_sight":
                range_ft = int(effect.get("range", 120) or 0)
                current = self.character_data.get("magical_darkness_sight") or {}
                if range_ft > int(current.get("range", 0) or 0):
                    self.character_data["magical_darkness_sight"] = {
                        "range": range_ft,
                        "source": source,
                        "source_type": stype,
                    }
            elif etype == "bonus_spell_damage_ability_mod":
                spell_name = effect.get("spell")
                ability = effect.get("ability")
                if isinstance(spell_name, str) and isinstance(ability, str):
                    self.character_data["spell_metadata"].setdefault(spell_name, {})["damage_bonus"] = {
                        "ability": ability,
                        "source": source,
                        "source_type": stype,
                    }
            elif etype == "bonus_spell_range":
                spell_name = effect.get("spell")
                new_range = effect.get("range")
                if isinstance(spell_name, str) and new_range:
                    self.character_data["spell_metadata"].setdefault(spell_name, {})["range_override"] = {
                        "range": new_range,
                        "source": source,
                        "source_type": stype,
                    }

    def _filter_applied_effects(self, predicate) -> None:
        """Drop applied effects matching *predicate* and rebuild structured fields.

        *predicate* is called with each ``applied_effects`` entry; entries for
        which it returns ``True`` are removed. After pruning, structured bonus
        fields are rebuilt from the surviving audit-log entries. This is the
        single chokepoint through which ``applied_effects`` is mutated outside
        of ``_apply_effect``.
        """
        self.applied_effects = [
            e for e in self.applied_effects if not predicate(e)
        ]
        self._rebuild_structured_bonuses()

    # ==================== Class/Subclass Methods ====================

    def set_class(self, class_name: str, level: int = 1) -> bool:
        """
        Set the character's class and level.

        Args:
            class_name: Name of the class (e.g., "Wizard", "Fighter")
            level: Character level (default: 1)

        Returns:
            True if successful, False otherwise
        """
        class_data = self._load_class_data(class_name)
        if not class_data:
            return False

        # If class is changing or level is changing, clear existing class features
        class_is_changing = self.character_data.get("class") != class_name
        if (
            class_is_changing
            or self.character_data.get("level") != level
        ):
            self._clear_class_features()
            # If the class itself is changing, subclass is no longer valid
            if class_is_changing and self.character_data.get("subclass"):
                self._clear_subclass_features()
                self.character_data["subclass"] = None
                self.character_data["subclass_data"] = None

        self.character_data["class"] = class_name
        self.character_data["class_data"] = class_data
        self.character_data["level"] = level

        # Re-apply lineage traits if they exist (for level-based spells)
        if "_lineage_traits" in self.character_data:
            # Clear existing level-based spells first
            self.character_data["spells"]["known"] = {}
            # Re-apply with new level
            for trait_name, trait_data in self.character_data[
                "_lineage_traits"
            ].items():
                self._apply_trait_effects(trait_name, trait_data, "lineage")

        # Apply class features
        self._apply_class_features(class_data, level)

        # Re-apply subclass features if subclass exists (same class, level change)
        if self.character_data.get("subclass"):
            subclass_data = self.character_data.get("subclass_data")
            if subclass_data:
                self._clear_subclass_features()
                self._apply_subclass_features(subclass_data, level)

        # Determine next step
        subclass_level = class_data.get("subclass_selection_level", 3)
        if level >= subclass_level:
            self.character_data["step"] = "subclass"
        else:
            self.character_data["step"] = "background"

        return True

    def _clear_class_features(self):
        """Clear all class-related features and effects before re-applying."""
        old_class_name = self.character_data.get("class", "")

        # Clear class features
        self.character_data["features"]["class"] = []

        # Reset proficiencies to base level (before class was added)
        self.character_data["proficiencies"]["saving_throws"] = []
        self.character_data["proficiencies"]["weapons"] = []
        self.character_data["proficiencies"]["armor"] = []

        # Remove skill proficiencies sourced from the old class
        skill_sources = self.character_data["proficiency_sources"]["skills"]
        old_class_skills = [
            s for s, src in skill_sources.items() if src == old_class_name
        ]
        for skill in old_class_skills:
            self.character_data["proficiencies"]["skills"] = [
                s for s in self.character_data["proficiencies"]["skills"] if s != skill
            ]
            skill_sources.pop(skill, None)

        # Remove tool proficiencies sourced from the old class
        tool_sources = self.character_data["proficiency_sources"]["tools"]
        old_class_tools = [
            t for t, src in tool_sources.items() if src == old_class_name
        ]
        for tool in old_class_tools:
            self.character_data["proficiencies"]["tools"] = [
                t for t in self.character_data["proficiencies"]["tools"] if t != tool
            ]
            tool_sources.pop(tool, None)

        # Clear class-related entries from choices_made
        class_choice_keys = [
            "skill_choices", "skills", "tool_choices", "tools", "subclass",
        ]
        for key in class_choice_keys:
            self.character_data["choices_made"].pop(key, None)
        # Also remove dynamic class feature choices (e.g. "Divine Order", "Fighting Style")
        if self.character_data.get("class_data"):
            features_by_level = self.character_data["class_data"].get("features_by_level", {})
            for level_features in features_by_level.values():
                if isinstance(level_features, dict):
                    for feature_name in level_features:
                        self.character_data["choices_made"].pop(feature_name, None)

        # Clear applied effects from class source
        if hasattr(self, "applied_effects"):
            self._filter_applied_effects(
                lambda e: e.get("source_type") in ["class", "class_choice"]
            )

    def _clear_subclass_features(self):
        """Clear all subclass-related features and effects before re-applying."""
        # Clear subclass features
        self.character_data["features"]["subclass"] = []

        # Clear applied effects from subclass source
        if hasattr(self, "applied_effects"):
            self._filter_applied_effects(
                lambda e: e.get("source_type") == "subclass"
            )

        # Clear subclass spells from prepared cantrips and spells
        spell_metadata = self.character_data.get("spell_metadata", {})
        prepared = self.character_data["spells"]["prepared"]

        for collection in (prepared.get("cantrips", {}), prepared.get("spells", {})):
            for spell_name in list(collection):
                if (
                    spell_name in spell_metadata
                    and spell_metadata[spell_name].get("source_type") == "subclass"
                ):
                    del collection[spell_name]
                    del spell_metadata[spell_name]

        # Clear subclass spells from always_prepared
        subclass_name = self.character_data.get("subclass", "")
        always_prepared = self.character_data["spells"]["always_prepared"]
        for spell_name in list(always_prepared):
            meta = spell_metadata.get(spell_name, {})
            ap_info = always_prepared[spell_name]
            source_type = meta.get("source_type", "")
            # Also check the always_prepared entry itself for source info
            if isinstance(ap_info, dict):
                source_type = source_type or ap_info.get("source_type", "")
            # Check source_type directly, or fall back to matching source name
            source_name = meta.get("source", "")
            if not source_name and isinstance(ap_info, dict):
                source_name = ap_info.get("source", "")
            if source_type == "subclass" or (subclass_name and source_name == subclass_name):
                del always_prepared[spell_name]
                spell_metadata.pop(spell_name, None)

        # Clear subclass-related entries from choices_made
        if self.character_data.get("subclass_data"):
            features_by_level = self.character_data["subclass_data"].get("features_by_level", {})
            for level_features in features_by_level.values():
                if isinstance(level_features, dict):
                    for feature_name in level_features:
                        self.character_data["choices_made"].pop(feature_name, None)

    def set_subclass(self, subclass_name: str) -> bool:
        """
        Set the character's subclass.

        Args:
            subclass_name: Name of the subclass

        Returns:
            True if successful, False otherwise
        """
        if not self.character_data["class"]:
            return False

        subclass_data = self._load_subclass_data(
            self.character_data["class"], subclass_name
        )
        if not subclass_data:
            return False

        # If subclass is changing, clear existing subclass features first
        if (
            self.character_data.get("subclass")
            and self.character_data.get("subclass") != subclass_name
        ):
            self._clear_subclass_features()

        self.character_data["subclass"] = subclass_name
        self.character_data["subclass_data"] = subclass_data

        # Apply subclass features for current level
        self._apply_subclass_features(subclass_data, self.character_data["level"])

        self.character_data["step"] = "background"
        return True

    def _apply_class_features(self, class_data: Dict[str, Any], level: int):
        """Apply class features up to the specified level."""
        # Saving throw proficiencies
        saving_throws = class_data.get("saving_throw_proficiencies", [])
        self.character_data["proficiencies"]["saving_throws"].extend(saving_throws)

        # Armor proficiencies
        armor_profs = class_data.get("armor_proficiencies", [])
        for prof in armor_profs:
            if prof not in self.character_data["proficiencies"]["armor"]:
                self.character_data["proficiencies"]["armor"].append(prof)

        # Weapon proficiencies
        weapon_profs = class_data.get("weapon_proficiencies", [])
        for prof in weapon_profs:
            if prof not in self.character_data["proficiencies"]["weapons"]:
                self.character_data["proficiencies"]["weapons"].append(prof)

        # Tool proficiencies (e.g. Artificer, Bard, Rogue, Monk)
        tool_profs = class_data.get("tool_proficiencies", [])
        for prof in tool_profs:
            if isinstance(prof, str) and prof and prof not in self.character_data["proficiencies"]["tools"]:
                self.character_data["proficiencies"]["tools"].append(prof)
                self.character_data["proficiency_sources"]["tools"][prof] = class_data.get("name", "Class")

        # Features by level
        features_by_level = class_data.get("features_by_level", {})

        # Shape validated at load time by modules.data_loader.
        for feat_level in range(1, level + 1):
            level_features = features_by_level.get(str(feat_level), {})
            for feature_name, feature_data in level_features.items():
                self._apply_trait_effects(
                    feature_name, feature_data, "class", feat_level
                )

    def _apply_subclass_features(self, subclass_data: Dict[str, Any], level: int):
        """Apply subclass features up to the specified level."""
        features_by_level = subclass_data.get("features_by_level", {})

        # Shape validated at load time by modules.data_loader.
        for feat_level_str, level_features in features_by_level.items():
            feat_level = int(feat_level_str)
            if feat_level <= level:
                for feature_name, feature_data in level_features.items():
                    self._apply_trait_effects(
                        feature_name, feature_data, "subclass", feat_level
                    )

    # ==================== Background Methods ====================

    def _remove_skills_sourced_from(
        self, skills: List[str], source_name: str
    ) -> None:
        """Remove character skill proficiencies that belong to *source_name*.

        Iterates over *skills* and, for each entry whose source in
        ``proficiency_sources['skills']`` equals *source_name*, removes it
        from ``proficiencies['skills']`` and clears the source entry.
        """
        skill_sources = self.character_data["proficiency_sources"]["skills"]
        for skill in skills:
            if skill_sources.get(skill) == source_name:
                self.character_data["proficiencies"]["skills"] = [
                    s for s in self.character_data["proficiencies"]["skills"] if s != skill
                ]
                skill_sources.pop(skill, None)

    def _remove_proficiencies_by_source(self, category: str, source: str) -> None:
        """Remove all proficiencies in *category* that were granted by *source*.

        Generic helper used by ``_clear_background_features`` to handle the
        skills, tools, and languages removal loops uniformly. Iterates
        ``proficiency_sources[category]``, collects every item whose recorded
        source matches *source*, then removes those items from both
        ``proficiencies[category]`` and ``proficiency_sources[category]``.

        Categories supported: 'skills', 'tools', 'languages' (any category that
        shares the same ``proficiencies`` / ``proficiency_sources`` shape).
        """
        sources_map = self.character_data["proficiency_sources"].get(category, {})
        to_remove = [item for item, src in list(sources_map.items()) if src == source]
        if not to_remove:
            return
        self.character_data["proficiencies"][category] = [
            p for p in self.character_data["proficiencies"].get(category, [])
            if p not in to_remove
        ]
        for item in to_remove:
            sources_map.pop(item, None)

    def _clear_background_features(self):
        """Clear all background-related features and effects before re-applying."""
        prev_bg_data = self.character_data.get("background_data") or {}
        prev_bg_name = prev_bg_data.get("name", self.character_data.get("background", ""))

        # Remove skill proficiencies granted by the previous background.
        # Phase 9 (D1-1): skill grants live in the canonical ``effects`` array.
        # The generic helper reads proficiency_sources["skills"] to find items
        # whose source matches the background name, covering both regular grants
        # and any replacement skills the player chose due to overlap.
        self._remove_proficiencies_by_source("skills", prev_bg_name)

        # Also clear any replacement-needed counter
        self.character_data["choices_made"].pop(
            "background_skill_replacements", []
        )
        self.character_data["choices_made"].pop(
            "background_skill_replacements_needed", None
        )

        # Remove tool proficiencies granted by the previous background's
        # canonical ``effects`` array (Phase 9: tool_proficiencies migrated to
        # grant_tool_proficiency effects). The generic helper reads
        # proficiency_sources["tools"] so both effects-encoded and legacy
        # flat-key tools are handled uniformly.
        self._remove_proficiencies_by_source("tools", prev_bg_name)

        # Remove language proficiencies granted by the previous background.
        # Integer ``languages`` values are legacy; clear the choice counter only.
        prev_languages = prev_bg_data.get("languages", [])
        if isinstance(prev_languages, int):
            self.character_data["choices_made"].pop("language_choices_needed", None)
        else:
            self._remove_proficiencies_by_source("languages", prev_bg_name)

        # Clear background features list
        self.character_data["features"]["background"] = []

        # Remove the origin feat granted by the previous background.
        # Phase 9 (D1-1): the feat is encoded as a ``grant_origin_feat``
        # effect in the canonical effects array.
        prev_feat_name = self._background_feat_name(prev_bg_data)
        if prev_feat_name:
            self.character_data["features"]["feats"] = [
                f for f in self.character_data["features"]["feats"]
                if f.get("name") != prev_feat_name
            ]

            # Clear spells granted by the feat (e.g. Magic Initiate cantrips/spells)
            spell_metadata = self.character_data.get("spell_metadata", {})
            spells_to_remove = set()
            for collection in (
                self.character_data["spells"]["prepared"]["cantrips"],
                self.character_data["spells"]["prepared"]["spells"],
                self.character_data["spells"]["always_prepared"],
                self.character_data["spells"]["background_spells"],
            ):
                for spell_name in list(collection):
                    if spell_metadata.get(spell_name, {}).get("source") == prev_feat_name:
                        del collection[spell_name]
                        spells_to_remove.add(spell_name)
            for spell_name in spells_to_remove:
                spell_metadata.pop(spell_name, None)

            # Remove feat-related choices from choices_made
            feat_choice_prefix = f"feat_{prev_feat_name}_"
            for key in [k for k in self.character_data["choices_made"] if k.startswith(feat_choice_prefix)]:
                del self.character_data["choices_made"][key]

            # Clear applied effects that originated from the previous background's feat
            if hasattr(self, "applied_effects"):
                self._filter_applied_effects(
                    lambda e: e.get("source_type") == "feat" and e.get("source") == prev_feat_name
                )

        # Phase 9 (D1-1): clear applied effects sourced directly from the
        # previous background (canonical ``effects`` array entries).
        if hasattr(self, "applied_effects") and prev_bg_name:
            self._filter_applied_effects(
                lambda e: e.get("source_type") == "background"
                and e.get("source") == prev_bg_name
            )

    def set_background(self, background_name: str) -> bool:
        """
        Set the character's background.

        Args:
            background_name: Name of the background (e.g., "Sage", "Soldier")

        Returns:
            True if successful, False otherwise
        """
        background_data = self._load_background_data(background_name)
        if not background_data:
            return False

        # Clear previous background features before applying new ones
        self._clear_background_features()

        self.character_data["background"] = background_name
        self.character_data["background_data"] = background_data

        # Apply background features
        self._apply_background_features(background_data)

        self.character_data["step"] = "abilities"
        return True

    def _apply_background_features(self, background_data: Dict[str, Any]):
        """Apply background features including skill proficiencies."""
        background_name = background_data.get(
            "name", self.character_data.get("background", "Unknown")
        )

        # Skill proficiencies, the origin feat, and tool proficiencies are
        # all applied below through the canonical ``effects`` array
        # (Phase 9 / D1-1). The dispatcher takes care of source tracking,
        # overlap detection (skills), and feat hydration (origin feat).

        # Tool proficiencies — legacy flat-key fallback for saved characters
        # that pre-date the Phase 9 migration. New content MUST use
        # ``effects: [{type: grant_tool_proficiency, tools: [...]}]``.
        legacy_tool_profs = background_data.get("tool_proficiencies", [])
        for tool in legacy_tool_profs:
            if tool not in self.character_data["proficiencies"]["tools"]:
                self.character_data["proficiencies"]["tools"].append(tool)
                # Track source so it can be cleared on background change
                self.character_data["proficiency_sources"]["tools"][tool] = background_name

        # Languages - can be either a list or a number
        languages = background_data.get("languages", [])
        if isinstance(languages, list):
            for lang in languages:
                if lang not in self.character_data["proficiencies"]["languages"]:
                    self.character_data["proficiencies"]["languages"].append(lang)
                    # Track source so it can be cleared on background change
                    self.character_data["proficiency_sources"]["languages"][lang] = background_name
        elif isinstance(languages, int):
            # Language selection is now a universal rule, not background-specific
            self.character_data["choices_made"].pop("language_choices_needed", None)

        # Background features
        features = background_data.get("features", {})

        # Ensure features is a dict
        if not isinstance(features, dict):
            print(
                f"Warning: background features is not a dict for {background_name}: {type(features)}"
            )
            features = {}

        for feature_name, feature_data in features.items():
            description = (
                feature_data
                if isinstance(feature_data, str)
                else feature_data.get("description", "")
            )
            feature_entry = {
                "name": feature_name,
                "description": description,
                "source": background_name,
            }
            if not any(
                f["name"] == feature_name
                for f in self.character_data["features"]["background"]
            ):
                self.character_data["features"]["background"].append(feature_entry)

        # Phase 9 (D1-1): apply background-level effects (canonical surface for
        # skill proficiencies, origin feat, tool proficiencies, etc.). Each
        # entry routes through the shared ``_apply_effect`` dispatcher with
        # source_type="background".
        for bg_effect in background_data.get("effects", []) or []:
            self._apply_effect(bg_effect, background_name, "background")

    def _process_equipment_selections(
        self, equipment_selections: Dict[str, str]
    ) -> bool:
        """
        Process equipment selections to generate actual equipment items.

        Args:
            equipment_selections: Dict with 'class_equipment' and 'background_equipment' choices

        Returns:
            True if equipment was processed successfully
        """
        if not isinstance(equipment_selections, dict):
            return False

        # Initialize equipment if not already present
        if (
            "equipment" not in self.character_data
            or self.character_data["equipment"] is None
        ):
            self.character_data["equipment"] = {
                "weapons": [],
                "armor": [],
                "items": [],
                "gold": 0,
            }

        # Check if equipment has already been processed to avoid duplicates
        equipment = self.character_data["equipment"]
        has_class_equipment = any(
            item.get("source") == "Class"
            for item in equipment["weapons"] + equipment["armor"] + equipment["items"]
        )
        has_background_equipment = any(
            item.get("source") == "Background"
            for item in equipment["weapons"] + equipment["armor"] + equipment["items"]
        )

        # Process class equipment selection
        class_choice = equipment_selections.get("class_equipment")
        if (
            class_choice
            and self.character_data.get("class_data")
            and not has_class_equipment
        ):
            class_equipment = self.character_data["class_data"].get(
                "starting_equipment", {}
            )
            if class_choice in class_equipment:
                option_data = class_equipment[class_choice]
                self._add_equipment_from_option(option_data, "Class")

        # Process background equipment selection
        background_choice = equipment_selections.get("background_equipment")
        if (
            background_choice
            and self.character_data.get("background_data")
            and not has_background_equipment
        ):
            background_equipment = self.character_data["background_data"].get(
                "starting_equipment", {}
            )
            if background_choice in background_equipment:
                option_data = background_equipment[background_choice]
                self._add_equipment_from_option(option_data, "Background")

        return True

    def _add_equipment_from_option(self, option_data: Dict[str, Any], source: str):
        """Add equipment items from a starting equipment option."""
        import re
        
        # Add gold
        gold = option_data.get("gold", 0)
        if gold > 0:
            self.character_data["equipment"]["gold"] += gold

        # Add items with categorization
        items = option_data.get("items", [])
        for item in items:
            item_name_lower = item.lower()

            # Check if item is a weapon by looking it up in weapon data
            weapon_key = self._resolve_weapon_key(item)
            weapon_props = self._weapon_data[weapon_key].copy() if weapon_key else {}
            if weapon_props:
                # Extract quantity from item name (e.g., "2 Daggers" -> 2, "Javelin (5)" -> 5)
                quantity = 1
                leading_quantity_match = re.search(r'^(\d+)\s+', item)
                if leading_quantity_match:
                    quantity = int(leading_quantity_match.group(1))
                else:
                    quantity_match = re.search(r'\((\d+)\)', item)
                    quantity = int(quantity_match.group(1)) if quantity_match else 1
                
                # Item exists in weapons.json, so it's a weapon
                self.character_data["equipment"]["weapons"].append(
                    {
                        "name": weapon_key,
                        "display_name": item,  # Keep original for display
                        "quantity": quantity,
                        "source": source,
                        "properties": weapon_props
                    }
                )
            elif any(
                armor_type in item_name_lower
                for armor_type in [
                    "armor",
                    "mail",
                    "leather",
                    "chain",
                    "scale",
                    "plate",
                    "shield",
                ]
            ):
                self.character_data["equipment"]["armor"].append(
                    {"name": item, "source": source}
                )
            else:
                self.character_data["equipment"]["items"].append(
                    {"name": item, "source": source}
                )

    def _process_inventory_choice(self, inventory_choice: Dict[str, Any]) -> bool:
        """Process user-managed inventory, synchronizing equipment and item effects."""
        if not isinstance(inventory_choice, dict):
            return False

        self.character_data["inventory"] = inventory_choice

        # Initialize or clear equipment so it synchronizes cleanly with inventory
        coins = inventory_choice.get("coins", {})
        gp_from_coins = 0
        if isinstance(coins, dict):
            gp_from_coins = (
                int(coins.get("cp", 0) or 0) / 100
                + int(coins.get("sp", 0) or 0) / 10
                + int(coins.get("ep", 0) or 0) / 2
                + int(coins.get("gp", 0) or 0)
                + int(coins.get("pp", 0) or 0) * 10
            )

        equipment = {
            "weapons": [],
            "armor": [],
            "items": [],
            "gold": int(gp_from_coins),
        }

        raw_items = inventory_choice.get("items", [])
        if not isinstance(raw_items, list):
            self.character_data["equipment"] = equipment
            return True

        # Track any general AC bonus items (e.g. Ring of Protection)
        # First remove any previously applied inventory AC bonuses
        if "ac_bonuses" in self.character_data:
            self.character_data["ac_bonuses"] = [
                b for b in self.character_data["ac_bonuses"]
                if not b.get("is_inventory_bonus")
            ]
        else:
            self.character_data["ac_bonuses"] = []

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            name = (item.get("name") or "").strip()
            if not name:
                continue

            category = item.get("category")
            is_equipped = bool(item.get("equipped", True))
            base_item = (item.get("base_item") or "").strip()
            quantity = max(1, int(item.get("quantity", 1) or 1))
            notes = item.get("notes") or ""
            ac_bonus = int(item.get("ac_bonus", 0) or 0)
            attack_bonus = int(item.get("attack_bonus", 0) or 0)
            damage_bonus = int(item.get("damage_bonus", 0) or 0)
            damage_dice = item.get("damage_dice")
            damage_type = item.get("damage_type")

            # Determine if this item is a weapon
            weapon_lookup_key = self._resolve_weapon_key(base_item or name)
            is_weapon = category == "Weapon" or (weapon_lookup_key is not None)

            # Determine if this item is armor or shield
            is_shield = (
                category == "Shield"
                or name.lower() == "shield"
                or (base_item and base_item.lower() == "shield")
            )
            is_armor = (
                category == "Armor"
                or is_shield
                or (base_item in self._armor_data)
                or (name in self._armor_data)
            )

            if is_weapon:
                # Load base weapon properties if available
                weapon_props = (
                    self._weapon_data[weapon_lookup_key].copy()
                    if weapon_lookup_key
                    else {}
                )
                if not weapon_props:
                    weapon_props = {
                        "category": item.get("subcategory") or "Simple Melee",
                        "damage": damage_dice or "1d6",
                        "damage_type": damage_type or "Slashing",
                        "properties": [],
                        "mastery": None,
                    }
                else:
                    if damage_dice:
                        weapon_props["damage"] = damage_dice
                    if damage_type:
                        weapon_props["damage_type"] = damage_type

                equipment["weapons"].append(
                    {
                        "id": item.get("id"),
                        "name": weapon_lookup_key or name,
                        "display_name": name,
                        "quantity": quantity,
                        "source": item.get("source", "Inventory"),
                        "equipped": is_equipped,
                        "properties": weapon_props,
                        "attack_bonus": attack_bonus,
                        "damage_bonus": damage_bonus,
                        "notes": notes,
                        "is_inventory": True,
                    }
                )

            elif is_armor or is_shield:
                armor_key = (
                    base_item
                    if (base_item in self._armor_data)
                    else name
                    if (name in self._armor_data)
                    else ("Shield" if is_shield else name)
                )
                equipment["armor"].append(
                    {
                        "id": item.get("id"),
                        "name": armor_key,
                        "display_name": name,
                        "quantity": quantity,
                        "source": item.get("source", "Inventory"),
                        "equipped": is_equipped,
                        "category": "Shield" if is_shield else "Armor",
                        "ac_bonus": ac_bonus,
                        "notes": notes,
                    }
                )

            else:
                equipment["items"].append(
                    {
                        "id": item.get("id"),
                        "name": name,
                        "quantity": quantity,
                        "source": item.get("source", "Inventory"),
                        "equipped": is_equipped,
                        "category": category or "Gear",
                        "notes": notes,
                    }
                )

            # If this is an equipped non-armor/non-shield item with an ac_bonus (e.g. Ring of Protection, Cloak of Protection)
            if is_equipped and ac_bonus > 0 and not is_armor and not is_shield:
                self.character_data["ac_bonuses"].append(
                    {
                        "source": name,
                        "value": ac_bonus,
                        "condition": "",
                        "is_inventory_bonus": True,
                    }
                )

        self.character_data["equipment"] = equipment
        return True

    def _load_weapon_data(self) -> Dict[str, Any]:
        """Load weapon data from weapons.json."""
        weapons_file = self.data_dir / "equipment" / "weapons.json"
        try:
            with open(weapons_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Warning: Could not load weapons data from {weapons_file}")
            return {}

    def _load_armor_data(self) -> Dict[str, Any]:
        """Load armor data from armor.json."""
        armor_file = self.data_dir / "equipment" / "armor.json"
        try:
            with open(armor_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Warning: Could not load armor data from {armor_file}")
            return {}

    def _spell_list_contains(self, spell_list: list, spell_name: str) -> bool:
        """
        Check if a spell list contains a spell by name.
        Handles both string and dict spell formats.
        """
        for spell in spell_list:
            if isinstance(spell, dict) and spell.get("name") == spell_name:
                return True
            elif isinstance(spell, str) and spell == spell_name:
                return True
        return False

    def _load_spell_definition(self, spell_name: str) -> Dict[str, Any]:
        """Load spell definition from spell definitions directory."""
        if not spell_name or not isinstance(spell_name, str):
            return {}
        if spell_name.strip() in ("Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"):
            return {}

        # Check cache first
        if spell_name in self._spell_definitions_cache:
            return self._spell_definitions_cache[spell_name]

        # Convert spell name to canonical filename format
        spell_file = self._content_file_path(
            "spells/definitions",
            spell_name,
            substitutions=SPELL_SLUG_SUBSTITUTIONS,
        )
        if spell_file is not None and os.path.exists(spell_file):
            try:
                with open(spell_file, "r") as f:
                    spell_data = json.load(f)
                    # Convert components list to string for template display
                    if "components" in spell_data and isinstance(
                        spell_data["components"], list
                    ):
                        spell_data["components"] = ", ".join(spell_data["components"])
                    # Derive concentration flag from duration string
                    spell_data["concentration"] = str(
                        spell_data.get("duration", "")
                    ).startswith("Concentration")
                    # Cache it
                    self._spell_definitions_cache[spell_name] = spell_data
                    return spell_data
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        # Try DataLoader / SupplementManager fallback for supplement spells
        try:
            active_sources = self.character_data.get("active_sources")
            supp_spell = self.data_loader.get_spell_definition(spell_name, active_sources)
            if supp_spell:
                spell_data = dict(supp_spell)
                if "components" in spell_data and isinstance(
                    spell_data["components"], list
                ):
                    spell_data["components"] = ", ".join(spell_data["components"])
                spell_data["concentration"] = str(
                    spell_data.get("duration", "")
                ).startswith("Concentration")
                self._spell_definitions_cache[spell_name] = spell_data
                return spell_data
        except Exception:
            pass

        # Return minimal spell object if file not found
        if spell_file is not None:
            print(
                f"Warning: Could not load spell definition for '{spell_name}' from {spell_file}"
            )
        return self._minimal_spell_definition(spell_name)

    @staticmethod
    def _minimal_spell_definition(spell_name: str) -> Dict[str, Any]:
        """Placeholder spell definition used when no definition file loads."""
        return {
            "name": spell_name,
            "level": 0,
            "description": "Spell definition not available.",
            "source": "Unknown",
            "concentration": False,
        }

    def _get_weapon_properties(self, weapon_name: str) -> Dict[str, Any]:
        """Get weapon properties from loaded weapon data."""
        weapon_key = self._resolve_weapon_key(weapon_name)
        if weapon_key:
            return self._weapon_data[weapon_key].copy()

        # Return empty dict for non-weapons (will be categorized elsewhere)
        return {}

    def _resolve_weapon_key(self, weapon_name: str) -> Optional[str]:
        """Resolve a starting-equipment weapon string to a key in weapons.json."""
        if not weapon_name:
            return None

        candidates = [weapon_name.strip()]

        # Collect text that appears inside parentheses, e.g. "Arcane Focus (Quarterstaff)"
        search_start = 0
        while True:
            start_idx = weapon_name.find("(", search_start)
            if start_idx == -1:
                break
            end_idx = weapon_name.find(")", start_idx + 1)
            if end_idx == -1:
                break
            parenthetical_value = weapon_name[start_idx + 1 : end_idx].strip()
            if parenthetical_value:
                candidates.append(parenthetical_value)
            search_start = end_idx + 1

        # Remove parenthetical content while preserving spacing between remaining words
        without_parentheses_chars = []
        paren_depth = 0
        for char in weapon_name:
            if char == "(":
                paren_depth += 1
                continue
            if char == ")" and paren_depth > 0:
                paren_depth -= 1
                continue
            if paren_depth == 0:
                without_parentheses_chars.append(char)
        without_parentheses = " ".join("".join(without_parentheses_chars).split())
        if without_parentheses:
            candidates.append(without_parentheses)

        def strip_leading_number(candidate: str) -> str:
            parts = candidate.split(maxsplit=1)
            if len(parts) == 2 and parts[0].isdigit():
                return parts[1].strip()
            return candidate.strip()

        expanded_candidates = []
        for candidate in candidates:
            expanded_candidates.append(candidate)

            without_leading_number = strip_leading_number(candidate)
            if without_leading_number and without_leading_number != candidate:
                expanded_candidates.append(without_leading_number)

            if without_leading_number.endswith("s") and len(without_leading_number) > 1:
                singular_candidate = without_leading_number[:-1]
                # Best-effort plural handling; only keep singular forms that
                # actually exist in the loaded weapon catalog.
                if singular_candidate and (
                    singular_candidate in self._weapon_data
                    or singular_candidate.lower() in self._weapon_data_lowercase
                ):
                    expanded_candidates.append(singular_candidate)

        unique_candidates_by_lowercase = {}
        for candidate in expanded_candidates:
            lowered = candidate.lower()
            if lowered and lowered not in unique_candidates_by_lowercase:
                unique_candidates_by_lowercase[lowered] = candidate
        unique_candidates = list(unique_candidates_by_lowercase.values())

        for candidate in unique_candidates:
            if candidate in self._weapon_data:
                return candidate

        for candidate in unique_candidates:
            if candidate.lower() in self._weapon_data_lowercase:
                return self._weapon_data_lowercase[candidate.lower()]

        return None

    def calculate_ac_options(self) -> List[Dict[str, Any]]:
        """
        Calculate all possible AC combinations based on available equipment.
        Returns AC options sorted from highest to lowest AC.
        """
        ac_options = []

        # Get character data
        abilities = self.calculate_processed_ability_scores()
        dex_mod = abilities.get("dexterity", {}).get("modifier", 0)
        equipment = self.character_data.get("equipment")
        proficiencies = self.character_data.get("proficiencies", {}).get("armor", [])

        def _ac_bonuses_for(armored: bool) -> List[Tuple[str, int]]:
            """Resolve data-authored AC conditions for one equipment option."""
            weapons = (equipment or {}).get("weapons", [])

            def _weapon_data(weapon: Dict[str, Any]) -> Dict[str, Any]:
                """Read direct weapon fields or the legacy catalog-entry wrapper."""
                properties = weapon.get("properties")
                return properties if isinstance(properties, dict) else weapon

            wieldable_weapon_count = sum(
                max(int(weapon.get("quantity", 1) or 1), 1)
                for weapon in weapons
                if isinstance(weapon, dict)
                and "Melee" in _weapon_data(weapon).get("category", "")
                and "Two-Handed" not in _weapon_data(weapon).get("properties", [])
            )
            entries = []
            for entry in self.character_data.get("ac_bonuses", []):
                condition = entry.get("condition", "")
                applies = (
                    not condition
                    or (condition == "wearing armor" and armored)
                    or (
                        condition == "wielding two weapons"
                        and wieldable_weapon_count >= 2
                    )
                )
                if applies:
                    entries.append(
                        (entry.get("source", "Unknown"), entry.get("value", 0))
                    )
            return entries

        def _apply_ac_bonuses(option: Dict[str, Any], armored: bool) -> None:
            for source, value in _ac_bonuses_for(armored):
                if not value:
                    continue
                option["ac"] += value
                sign = "+" if value > 0 else "-"
                option["notes"].append(f"{sign}{abs(value)} from {source}")
                option["formula"] += f" + {source} ({sign}{abs(value)})"

        # Handle case where equipment is None (like in tests)
        if equipment is None:
            # Just return unarmored AC
            unarmored_ac = 10 + dex_mod
            ac_options = [
                {
                    "ac": unarmored_ac,
                    "armor": None,
                    "shield": False,
                    "formula": f"10 + Dex modifier ({dex_mod})",
                    "notes": [],
                    "equipped_armor": None,
                }
            ]
            _apply_ac_bonuses(ac_options[0], armored=False)

            # Check for alternative AC formulas (e.g., Monk/Barbarian Unarmored Defense)
            # Phase 6: read from structured field, not applied_effects.
            for alt_entry in self.character_data.get("alternative_ac_options", []):
                base = alt_entry.get("base", 10)
                modifiers = alt_entry.get("modifiers", [])

                alt_ac = base
                formula_desc = [str(base)]
                for mod_ability in modifiers:
                    mod_val = abilities.get(mod_ability.lower(), {}).get("modifier", 0)
                    alt_ac += mod_val
                    ability_short = mod_ability[:3].capitalize()
                    formula_desc.append(f"{ability_short} modifier ({mod_val})")

                source_name = alt_entry.get("source", "Unarmored Defense")
                alt_option = {
                    "ac": alt_ac,
                    "armor": None,
                    "shield": False,
                    "formula": " + ".join(formula_desc),
                    "notes": [source_name],
                    "equipped_armor": None,
                }
                _apply_ac_bonuses(alt_option, armored=False)
                ac_options.append(alt_option)

            ac_options.sort(key=lambda x: x["ac"], reverse=True)
            return ac_options

        # Available armor pieces
        armor_items = equipment.get("armor", [])

        equipped_shields = [
            item
            for item in armor_items
            if (item.get("name") == "Shield" or item.get("category") == "Shield")
            and item.get("equipped", True)
        ]
        has_shield = len(equipped_shields) > 0
        shield_magic_bonus = sum(
            int(s.get("ac_bonus", 0) or 0) for s in equipped_shields
        )
        base_shield_bonus = 2 if has_shield else 0
        total_shield_bonus = (
            (base_shield_bonus + shield_magic_bonus) if has_shield else 0
        )

        # Get all armor (non-shield) pieces that are equipped
        armor_pieces = [
            item
            for item in armor_items
            if item.get("name") != "Shield"
            and item.get("category") != "Shield"
            and item.get("equipped", True)
        ]

        # Calculate AC for each armor combination
        for armor in armor_pieces:
            armor_name = armor.get("name")
            if armor_name and armor_name in self._armor_data:
                armor_data = self._armor_data[armor_name]
                ac_option = self._calculate_armor_ac(
                    armor_data, dex_mod, has_shield, proficiencies, armor_name
                )
                if shield_magic_bonus and has_shield:
                    ac_option["ac"] += shield_magic_bonus
                    ac_option["formula"] += f" + Shield Magic (+{shield_magic_bonus})"

                armor_bonus = int(armor.get("ac_bonus", 0) or 0)
                if armor_bonus > 0:
                    ac_option["ac"] += armor_bonus
                    ac_option["formula"] += f" + Armor Magic (+{armor_bonus})"
                    ac_option["notes"].append(
                        f"+{armor_bonus} {armor.get('display_name', armor_name)}"
                    )

                ac_option["equipped_armor"] = armor.get("display_name") or armor_name

                _apply_ac_bonuses(ac_option, armored=True)

                ac_options.append(ac_option)

        # Add unarmored AC option
        unarmored_ac = 10 + dex_mod
        shield_bonus = total_shield_bonus
        total_unarmored = unarmored_ac + shield_bonus

        formula_parts = [f"10 + Dex modifier ({dex_mod})"]
        if shield_bonus:
            formula_parts.append(f"Shield ({shield_bonus})")

        unarmored_option = {
            "ac": total_unarmored,
            "armor": None,
            "shield": has_shield,
            "formula": " + ".join(formula_parts),
            "notes": [],
            "equipped_armor": None,
        }
        _apply_ac_bonuses(unarmored_option, armored=False)
        ac_options.append(unarmored_option)

        # Check for alternative AC formulas (e.g., Monk/Barbarian Unarmored Defense)
        # Phase 6: read from structured field, not applied_effects.
        for alt_entry in self.character_data.get("alternative_ac_options", []):
            base = alt_entry.get("base", 10)
            modifiers = alt_entry.get("modifiers", [])
            condition = alt_entry.get("condition", "")

            # Calculate AC from modifiers
            alt_ac = base
            formula_desc = [str(base)]
            for mod_ability in modifiers:
                mod_val = abilities.get(mod_ability.lower(), {}).get("modifier", 0)
                alt_ac += mod_val
                ability_short = mod_ability[:3].capitalize()
                formula_desc.append(f"{ability_short} modifier ({mod_val})")

            # Determine if shield is allowed
            allow_shield = "no_shield" not in condition
            alt_shield_bonus = (
                total_shield_bonus
                if has_shield and allow_shield
                else 0
            )
            alt_total = alt_ac + alt_shield_bonus

            alt_formula_parts = [" + ".join(formula_desc)]
            if alt_shield_bonus:
                alt_formula_parts.append(f"Shield ({alt_shield_bonus})")

            source_name = alt_entry.get("source", "Unarmored Defense")
            alt_option = {
                "ac": alt_total,
                "armor": None,
                "shield": has_shield and allow_shield,
                "formula": " + ".join(alt_formula_parts),
                "notes": [source_name],
                "equipped_armor": None,
            }
            _apply_ac_bonuses(alt_option, armored=False)

            # Replace default unarmored if this is better
            ac_options.append(alt_option)

        # Add notes for unproficient equipment
        for option in ac_options:
            if option["equipped_armor"]:
                armor_data = self._armor_data.get(option["equipped_armor"], {})
                required_prof = armor_data.get("proficiency_required")
                if required_prof and required_prof not in proficiencies:
                    option["notes"].append(f"Not proficient with {required_prof}")

            if has_shield and "Shields" not in proficiencies:
                option["notes"].append("Not proficient with Shields")

        # Sort by AC (highest first)
        ac_options.sort(key=lambda x: x["ac"], reverse=True)

        return ac_options

    def _calculate_armor_ac(
        self,
        armor_data: Dict[str, Any],
        dex_mod: int,
        has_shield: bool,
        proficiencies: List[str],
        armor_name: str = None,
    ) -> Dict[str, Any]:
        """Calculate AC for a specific armor."""
        ac_base = armor_data.get("ac_base", 10)
        category = armor_data.get("category", "")

        # Calculate DEX modifier contribution based on armor type
        if "Light" in category:
            # Light armor: full DEX modifier
            dex_bonus = dex_mod
        elif "Medium" in category:
            # Medium armor: DEX modifier max 2
            dex_bonus = min(dex_mod, 2)
        else:
            # Heavy armor: no DEX modifier
            dex_bonus = 0

        # Base AC calculation
        total_ac = ac_base + dex_bonus

        # Shield bonus
        shield_bonus = 0
        if has_shield:
            shield_bonus = 2
            total_ac += shield_bonus

        # Build formula string
        formula_parts = []
        if ac_base != 10:
            formula_parts.append(f"Armor base ({ac_base})")
        if dex_bonus != 0 or "Light" in category or "Medium" in category:
            formula_parts.append(f"Dex modifier ({dex_bonus})")
        if shield_bonus > 0:
            formula_parts.append(f"Shield ({shield_bonus})")

        formula = " + ".join(formula_parts) if formula_parts else str(total_ac)

        return {
            "ac": total_ac,
            "armor": armor_name,
            "shield": has_shield,
            "formula": formula,
            "notes": [],
        }

    # ==================== Ability Score Methods ====================

    def set_abilities(
        self,
        scores: Dict[str, int],
        species_bonuses: Optional[Dict[str, int]] = None,
        background_bonuses: Optional[Dict[str, int]] = None,
    ) -> bool:
        """
        Set ability scores with optional bonuses.

        Args:
            scores: Base ability scores {"STR": 10, "DEX": 14, ...}
            species_bonuses: Species ability bonuses (usually empty in 2024)
            background_bonuses: Background ability bonuses

        Returns:
            True if successful, False otherwise
        """
        self.ability_scores.set_base_scores(scores)

        if species_bonuses:
            self.ability_scores.apply_species_bonuses(species_bonuses)

        if background_bonuses:
            self.ability_scores.apply_background_bonuses(background_bonuses)

        # Store in character data
        self.character_data["abilities"] = {
            "base": scores,
            "species_bonuses": species_bonuses or {},
            "background_bonuses": background_bonuses or {},
            "final": self.ability_scores.final_scores,
        }

        self.character_data["step"] = "complete"
        return True

    # ==================== Choice Application Methods ====================

    def _validate_selection_list(
        self,
        *,
        family: str,
        field: str,
        value: Any,
    ) -> List[str]:
        """Validate a selection field as a list of unique non-empty strings."""
        if value is None:
            return []
        if not isinstance(value, list):
            raise SelectionValidationError(
                family=family,
                code="invalid_payload_type",
                message=f"'{field}' must be a list of strings",
                violations=[{"field": field, "reason": "must_be_list"}],
            )
        normalized: List[str] = []
        seen = set()
        duplicates = set()
        for idx, raw in enumerate(value):
            if not isinstance(raw, str) or not raw.strip():
                raise SelectionValidationError(
                    family=family,
                    code="invalid_selection_type",
                    message=f"'{field}[{idx}]' must be a non-empty string",
                    violations=[{"field": f"{field}[{idx}]", "reason": "must_be_non_empty_string"}],
                )
            name = raw.strip()
            if name in seen:
                duplicates.add(name)
                continue
            seen.add(name)
            normalized.append(name)
        if duplicates:
            raise SelectionValidationError(
                family=family,
                code="duplicate_selection",
                message=f"'{field}' contains duplicate selections",
                violations=[
                    {
                        "field": field,
                        "reason": "duplicate_values",
                        "duplicates": sorted(duplicates),
                    }
                ],
            )
        return normalized

    def _load_eldritch_invocations_catalog(self) -> Dict[str, Any]:
        try:
            from modules.supplement_manager import get_supplement_manager
            mgr = get_supplement_manager()
            return mgr.get_eldritch_invocations(getattr(self, "active_sources", None))
        except Exception:
            invocations_file = self.data_dir / "eldritch_invocations.json"
            if not invocations_file.exists():
                return {}
            try:
                with open(invocations_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, IOError):
                return {}

    def _validate_spell_selections(self, choice_value: Any, *, strict: Optional[bool] = None) -> Dict[str, List[str]]:
        if strict is None:
            strict = getattr(self, "_fail_on_error", True)
            if strict is None:
                strict = True

        family = "spell_selections"
        if not isinstance(choice_value, dict):
            if strict:
                raise SelectionValidationError(
                    family=family,
                    code="invalid_payload_type",
                    message="'spell_selections' must be an object",
                    violations=[{"field": "spell_selections", "reason": "must_be_object"}],
                )
            return {
                "cantrips": [],
                "spells": [],
                "spellbook": [],
                "background_cantrips": [],
                "background_spells": [],
            }

        def _get_list(field_name: str) -> List[str]:
            val = choice_value.get(field_name, [])
            try:
                return self._validate_selection_list(
                    family=family, field=f"spell_selections.{field_name}", value=val
                )
            except SelectionValidationError:
                if strict:
                    raise
                if isinstance(val, list):
                    return [str(item) for item in val if isinstance(item, str) and item.strip()]
                return []

        cantrips = _get_list("cantrips")
        spells = _get_list("spells")
        spellbook = _get_list("spellbook")
        background_cantrips = _get_list("background_cantrips")
        background_spells = _get_list("background_spells")

        try:
            spell_view = build_spell_management_view(self)
        except ValueError as exc:
            if isinstance(exc, SelectionValidationError):
                if strict:
                    raise
            if cantrips or spells or background_cantrips or background_spells:
                if strict:
                    raise SelectionValidationError(
                        family=family,
                        code="character_not_spellcaster",
                        message="Character cannot select prepared spells",
                        violations=[
                            {
                                "field": "spell_selections",
                                "reason": "not_available_for_character",
                            }
                        ],
                    )
                else:
                    self.character_data.setdefault("warnings", []).append(
                        "Character cannot select prepared spells"
                    )
            return {
                "cantrips": cantrips if not strict else [],
                "spells": spells if not strict else [],
                "spellbook": spellbook if not strict else [],
                "background_cantrips": background_cantrips if not strict else [],
                "background_spells": background_spells if not strict else [],
            }

        violations: List[Dict[str, Any]] = []

        available_cantrips = {
            str(entry.get("name"))
            for entry in spell_view.get("available_cantrips", [])
            if isinstance(entry, dict) and entry.get("name")
        }
        available_spells = {
            str(entry.get("name"))
            for level_entries in (spell_view.get("available_spells", {}) or {}).values()
            for entry in (level_entries or [])
            if isinstance(entry, dict) and entry.get("name")
        }
        limits = spell_view.get("limits", {}) or {}
        max_cantrips = int(limits.get("cantrips", 0) or 0)
        max_spells = int(limits.get("spells", 0) or 0)

        if len(cantrips) > max_cantrips:
            violations.append(
                {
                    "field": "spell_selections.cantrips",
                    "reason": "max_exceeded",
                    "submitted_count": len(cantrips),
                    "max_allowed": max_cantrips,
                }
            )
        if len(spells) > max_spells:
            violations.append(
                {
                    "field": "spell_selections.spells",
                    "reason": "max_exceeded",
                    "submitted_count": len(spells),
                    "max_allowed": max_spells,
                }
            )

        unavailable_cantrips = sorted([name for name in cantrips if name not in available_cantrips])
        if unavailable_cantrips:
            violations.append(
                {
                    "field": "spell_selections.cantrips",
                    "reason": "unavailable_selection",
                    "selections": unavailable_cantrips,
                }
            )

        unavailable_spells = sorted([name for name in spells if name not in available_spells])
        if unavailable_spells:
            violations.append(
                {
                    "field": "spell_selections.spells",
                    "reason": "unavailable_selection",
                    "selections": unavailable_spells,
                }
            )

        has_spellbook = bool(spell_view.get("has_spellbook"))
        if has_spellbook:
            # If spellbook was not provided in choice_value, fallback to auto-populating from spells
            if "spellbook" not in choice_value and spells:
                spellbook = list(spells)

            unavailable_spellbook = sorted([name for name in spellbook if name not in available_spells])
            if unavailable_spellbook:
                violations.append(
                    {
                        "field": "spell_selections.spellbook",
                        "reason": "unavailable_selection",
                        "selections": unavailable_spellbook,
                    }
                )

            # Prepared spells MUST be in the spellbook (or always_prepared)
            always_prepared_names = {
                str(entry.get("name"))
                for entry in spell_view.get("always_prepared", [])
                if isinstance(entry, dict) and entry.get("name")
            }
            not_in_spellbook = sorted([
                name for name in spells
                if name not in spellbook and name not in always_prepared_names
            ])
            if not_in_spellbook:
                violations.append(
                    {
                        "field": "spell_selections.spells",
                        "reason": "not_in_spellbook",
                        "selections": not_in_spellbook,
                    }
                )

        bg_requirements = spell_view.get("background_requirements") or {}
        bg_cantrip_req = bg_requirements.get("cantrips") if isinstance(bg_requirements, dict) else None
        bg_spells_req = bg_requirements.get("spells") if isinstance(bg_requirements, dict) else None

        bg_cantrip_allowed = {
            str(entry.get("name"))
            for entry in (bg_cantrip_req or {}).get("available", [])
            if isinstance(entry, dict) and entry.get("name")
        }
        bg_spell_allowed = {
            str(entry.get("name"))
            for entry in (bg_spells_req or {}).get("available", [])
            if isinstance(entry, dict) and entry.get("name")
        }
        max_bg_cantrips = int((bg_cantrip_req or {}).get("count", 0) or 0)
        max_bg_spells = int((bg_spells_req or {}).get("count", 0) or 0)

        if len(background_cantrips) > max_bg_cantrips:
            violations.append(
                {
                    "field": "spell_selections.background_cantrips",
                    "reason": "max_exceeded",
                    "submitted_count": len(background_cantrips),
                    "max_allowed": max_bg_cantrips,
                }
            )
        if len(background_spells) > max_bg_spells:
            violations.append(
                {
                    "field": "spell_selections.background_spells",
                    "reason": "max_exceeded",
                    "submitted_count": len(background_spells),
                    "max_allowed": max_bg_spells,
                }
            )

        unavailable_bg_cantrips = sorted(
            [name for name in background_cantrips if name not in bg_cantrip_allowed]
        )
        if unavailable_bg_cantrips:
            violations.append(
                {
                    "field": "spell_selections.background_cantrips",
                    "reason": "unavailable_selection",
                    "selections": unavailable_bg_cantrips,
                }
            )

        unavailable_bg_spells = sorted(
            [name for name in background_spells if name not in bg_spell_allowed]
        )
        if unavailable_bg_spells:
            violations.append(
                {
                    "field": "spell_selections.background_spells",
                    "reason": "unavailable_selection",
                    "selections": unavailable_bg_spells,
                }
            )

        if violations:
            if strict:
                raise SelectionValidationError(
                    family=family,
                    code="invalid_selection",
                    message="Submitted spell selections are not valid for this character",
                    violations=violations,
                )
            self.character_data.setdefault("warnings", []).append(
                f"Spell selections had validation issues: {violations}"
            )

        return {
            "cantrips": cantrips,
            "spells": spells,
            "spellbook": spellbook,
            "background_cantrips": background_cantrips,
            "background_spells": background_spells,
        }

    def _validate_weapon_mastery_selections(self, choice_value: Any) -> List[str]:
        family = "weapon_mastery_selections"
        selected = self._validate_selection_list(
            family=family,
            field="weapon_mastery_selections",
            value=choice_value,
        )
        stats = self.calculate_weapon_mastery_stats()
        if not stats.get("has_mastery"):
            if selected:
                raise SelectionValidationError(
                    family=family,
                    code="not_available_for_character",
                    message="Character cannot select weapon masteries",
                    violations=[{"field": "weapon_mastery_selections", "reason": "not_available_for_character"}],
                )
            return []

        available = set(stats.get("available_weapons", []))
        max_masteries = int(stats.get("max_masteries", 0) or 0)
        violations: List[Dict[str, Any]] = []

        if len(selected) > max_masteries:
            violations.append(
                {
                    "field": "weapon_mastery_selections",
                    "reason": "max_exceeded",
                    "submitted_count": len(selected),
                    "max_allowed": max_masteries,
                }
            )
        unavailable = sorted([name for name in selected if name not in available])
        if unavailable:
            violations.append(
                {
                    "field": "weapon_mastery_selections",
                    "reason": "unavailable_selection",
                    "selections": unavailable,
                }
            )

        if violations:
            raise SelectionValidationError(
                family=family,
                code="invalid_selection",
                message="Submitted weapon mastery selections are not valid for this character",
                violations=violations,
            )
        return selected

    def _validate_eldritch_invocation_selections(self, choice_value: Any) -> List[str]:
        family = "eldritch_invocation_selections"
        selected = self._validate_selection_list(
            family=family,
            field="eldritch_invocation_selections",
            value=choice_value,
        )
        stats = self.calculate_eldritch_invocation_stats()
        if not stats.get("has_invocations"):
            if selected:
                raise SelectionValidationError(
                    family=family,
                    code="not_available_for_character",
                    message="Character cannot select Eldritch Invocations",
                    violations=[{"field": "eldritch_invocation_selections", "reason": "not_available_for_character"}],
                )
            return []

        max_invocations = int(stats.get("max_invocations", 0) or 0)
        warlock_level = self._get_class_level("Warlock")
        selected_set = set(selected)
        all_invocations = self._load_eldritch_invocations_catalog()

        violations: List[Dict[str, Any]] = []
        if len(selected) > max_invocations:
            violations.append(
                {
                    "field": "eldritch_invocation_selections",
                    "reason": "max_exceeded",
                    "submitted_count": len(selected),
                    "max_allowed": max_invocations,
                }
            )

        for name in selected:
            inv_data = all_invocations.get(name)
            if not isinstance(inv_data, dict):
                violations.append(
                    {
                        "field": "eldritch_invocation_selections",
                        "reason": "unknown_invocation",
                        "selection": name,
                    }
                )
                continue
            required_level = int(inv_data.get("prerequisite_level", 1) or 1)
            if warlock_level < required_level:
                violations.append(
                    {
                        "field": "eldritch_invocation_selections",
                        "reason": "prerequisite_level_not_met",
                        "selection": name,
                        "required_level": required_level,
                        "current_level": warlock_level,
                    }
                )
            required_invocations = [
                req
                for req in inv_data.get("prerequisite_invocations", [])
                if isinstance(req, str) and req.strip()
            ]
            missing_reqs = [req for req in required_invocations if req not in selected_set]
            if missing_reqs:
                violations.append(
                    {
                        "field": "eldritch_invocation_selections",
                        "reason": "missing_prerequisite_invocations",
                        "selection": name,
                        "missing_prerequisites": missing_reqs,
                    }
                )

        if violations:
            raise SelectionValidationError(
                family=family,
                code="invalid_selection",
                message="Submitted Eldritch Invocation selections are not valid for this character",
                violations=violations,
            )
        return selected

    def _load_replicate_magic_item_plans(self) -> Dict[str, Any]:
        """Load all replicate magic item plans from core data and supplements."""
        try:
            from modules.supplement_manager import get_supplement_manager
            mgr = get_supplement_manager()
            return mgr.get_replicate_magic_item_plans(getattr(self, "active_sources", None))
        except Exception:
            plans_file = self.data_dir / "replicate_magic_item_plans.json"
            if not plans_file.exists():
                return {}
            try:
                with open(plans_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, IOError):
                return {}

    def _validate_artificer_replicate_plans(self, choice_value: Any) -> List[str]:
        family = "artificer_replicate_plans"
        selected = self._validate_selection_list(
            family=family,
            field="artificer_replicate_plans",
            value=choice_value,
        )
        stats = self.calculate_artificer_replications_stats()
        if not stats.get("has_replications"):
            if selected:
                raise SelectionValidationError(
                    family=family,
                    code="not_available_for_character",
                    message="Character cannot select Replicate Magic Item plans",
                    violations=[{"field": "artificer_replicate_plans", "reason": "not_available_for_character"}],
                )
            return []

        max_plans = int(stats.get("max_plans", 0) or 0)
        artificer_level = int(stats.get("artificer_level", 0) or 0)
        all_plans = self._load_replicate_magic_item_plans()

        violations: List[Dict[str, Any]] = []
        if len(selected) > max_plans:
            violations.append(
                {
                    "field": "artificer_replicate_plans",
                    "reason": "max_exceeded",
                    "submitted_count": len(selected),
                    "max_allowed": max_plans,
                }
            )

        for name in selected:
            plan_data = all_plans.get(name)
            if not isinstance(plan_data, dict):
                violations.append(
                    {
                        "field": "artificer_replicate_plans",
                        "reason": "unknown_plan",
                        "selection": name,
                    }
                )
                continue
            required_level = int(plan_data.get("level", 2) or 2)
            if artificer_level < required_level:
                violations.append(
                    {
                        "field": "artificer_replicate_plans",
                        "reason": "prerequisite_level_not_met",
                        "selection": name,
                        "required_level": required_level,
                        "current_level": artificer_level,
                    }
                )

        if violations:
            if getattr(self, "_fail_on_error", True):
                raise SelectionValidationError(
                    family=family,
                    code="invalid_selection",
                    message="Submitted Replicate Magic Item plan selections are not valid for this character",
                    violations=violations,
                )
            valid = []
            for name in selected:
                p = all_plans.get(name)
                if isinstance(p, dict) and int(p.get("level", 2) or 2) <= artificer_level:
                    valid.append(name)
            return valid[:max_plans]

        return selected

    def _validate_artificer_active_replications(self, choice_value: Any) -> List[str]:
        family = "artificer_active_replications"
        selected = self._validate_selection_list(
            family=family,
            field="artificer_active_replications",
            value=choice_value,
        )
        stats = self.calculate_artificer_replications_stats()
        if not stats.get("has_replications"):
            if selected:
                raise SelectionValidationError(
                    family=family,
                    code="not_available_for_character",
                    message="Character cannot replicate magic items",
                    violations=[{"field": "artificer_active_replications", "reason": "not_available_for_character"}],
                )
            return []

        max_active = int(stats.get("max_active", 0) or 0)
        artificer_level = int(stats.get("artificer_level", 0) or 0)
        all_plans = self._load_replicate_magic_item_plans()
        known_plans = set(stats.get("known_plans", []))

        violations: List[Dict[str, Any]] = []
        if len(selected) > max_active:
            violations.append(
                {
                    "field": "artificer_active_replications",
                    "reason": "max_exceeded",
                    "submitted_count": len(selected),
                    "max_allowed": max_active,
                }
            )

        for name in selected:
            plan_data = all_plans.get(name)
            if not isinstance(plan_data, dict):
                violations.append(
                    {
                        "field": "artificer_active_replications",
                        "reason": "unknown_plan",
                        "selection": name,
                    }
                )
                continue
            required_level = int(plan_data.get("level", 2) or 2)
            if artificer_level < required_level:
                violations.append(
                    {
                        "field": "artificer_active_replications",
                        "reason": "prerequisite_level_not_met",
                        "selection": name,
                        "required_level": required_level,
                        "current_level": artificer_level,
                    }
                )
            if known_plans and name not in known_plans:
                violations.append(
                    {
                        "field": "artificer_active_replications",
                        "reason": "plan_not_known",
                        "selection": name,
                    }
                )

        if violations:
            if getattr(self, "_fail_on_error", True):
                raise SelectionValidationError(
                    family=family,
                    code="invalid_selection",
                    message="Submitted active replicated items are not valid for this character",
                    violations=violations,
                )
            valid = []
            for name in selected:
                p = all_plans.get(name)
                if isinstance(p, dict) and int(p.get("level", 2) or 2) <= artificer_level:
                    if not known_plans or name in known_plans:
                        valid.append(name)
            return valid[:max_active]

        return selected

    def apply_choice(self, choice_key: str, choice_value: Any) -> bool:
        """
        Apply a single choice and its effects to the character.

        Args:
            choice_key: The choice identifier (e.g., 'species', 'class', 'Divine Order')
            choice_value: The choice value (can be string, int, list, dict)

        Returns:
            True if choice was applied successfully
        """
        # Store the choice
        self.character_data["choices_made"][choice_key] = choice_value

        # Apply based on choice type
        choice_key_lower = choice_key.lower()

        # Core character selections
        if choice_key_lower == "species":
            return self.set_species(choice_value)
        elif choice_key_lower == "lineage":
            return self.set_lineage(choice_value)
        elif choice_key_lower == "lineage_spellcasting_ability":
            self.character_data["spellcasting_ability"] = choice_value
            return True
        elif choice_key_lower in ["elven lineage", "gnomish lineage"]:
            # Species trait choice for spellcasting ability (INT/WIS/CHA)
            self.character_data["spellcasting_ability"] = choice_value
            return True
        elif choice_key_lower == "species_trait_choices":
            # Canonical nested storage for species (and lineage) trait picks.
            # The dict has already been recorded at choices_made["species_trait_choices"]
            # at the top of this function. Dispatch each trait → value to apply_choice
            # so trait-level side effects (e.g. Elven Lineage → spellcasting_ability,
            # Draconic Ancestry → damage_type substitutions, choice-effect grants)
            # still fire. Per-trait flat keys written during dispatch are normalized
            # back into the nested object at the end of apply_choices().
            if isinstance(choice_value, dict):
                for trait_name, trait_value in choice_value.items():
                    if not self.apply_choice(trait_name, trait_value):
                        return False
            return True
        elif choice_key_lower == "class":
            return self.set_class(choice_value, self.character_data.get("level", 1))
        elif choice_key_lower == "subclass":
            return self.set_subclass(choice_value)
        elif choice_key_lower == "background":
            return self.set_background(choice_value)
        elif choice_key_lower == "level":
            current_class = self.character_data.get("class")
            if current_class:
                return self.set_class(current_class, int(choice_value))
            self.character_data["level"] = int(choice_value)
            return True

        # Ability scores
        elif choice_key_lower in ["ability_scores", "abilities"]:
            if isinstance(choice_value, dict):
                return self.set_abilities(choice_value)
            elif choice_value == "standard_array_recommended":
                # Get the recommended ability scores from class data
                class_data = self.character_data.get("class_data", {})
                standard_array = class_data.get("standard_array_assignment")
                if standard_array:
                    return self.set_abilities(standard_array)
            return True
        elif choice_key_lower == "ability_scores_method":
            # Handle "recommended", "manual", "roll", "standard_array", or "point_buy" methods
            if choice_value == "recommended":
                # Use the predefined standard_array_assignment from class data
                class_data = self.character_data.get("class_data", {})

                if "standard_array_assignment" in class_data:
                    return self.set_abilities(class_data["standard_array_assignment"])
                else:
                    print(
                        f"Warning: Class {class_data.get('name', 'Unknown')} missing standard_array_assignment"
                    )
                    return False
            # "manual", "roll", "standard_array", and "point_buy" all store scores via
            # the "ability_scores" key;
            # nothing extra needed here beyond recording the method choice.
            return True
        elif choice_key_lower == "background_ability_score_assignment":
            # Apply background ability bonuses
            if isinstance(choice_value, dict):
                self.ability_scores.apply_background_bonuses(choice_value)
                # Update character_data so it persists across session save/restore
                if "abilities" not in self.character_data:
                    self.character_data["abilities"] = {}
                self.character_data["abilities"]["background_bonuses"] = choice_value
            return True
        elif choice_key_lower == "background_bonuses":
            # Apply background ability bonuses (alternate key name)
            if isinstance(choice_value, dict):
                self.ability_scores.apply_background_bonuses(choice_value)
                # Update character_data so it persists across session save/restore
                if "abilities" not in self.character_data:
                    self.character_data["abilities"] = {}
                self.character_data["abilities"]["background_bonuses"] = choice_value
            return True
        elif choice_key_lower in ["additional_ability_modifiers", "ability_modifiers"]:
            # Apply user-entered additional ability modifiers
            if isinstance(choice_value, dict):
                self.ability_scores.apply_additional_modifiers(choice_value)
                if "abilities" not in self.character_data:
                    self.character_data["abilities"] = {}
                self.character_data["abilities"]["additional_modifiers"] = choice_value
            return True
        elif choice_key_lower == "background_bonuses_method":
            # Handle "suggested" background bonuses
            if choice_value == "suggested":
                background_data = self.character_data.get("background_data", {})
                if background_data:
                    asi_data = background_data.get("ability_score_increase", {})
                    suggested = asi_data.get("suggested", {})
                    if suggested:
                        self.ability_scores.apply_background_bonuses(suggested)
            return True
        # Standard + Rare language choices (counts towards selection_count)
        elif choice_key_lower == "languages":
            if isinstance(choice_value, list):
                # Clear previously user-selected languages (standard and rare)
                lang_sources = self.character_data["proficiency_sources"]["languages"]
                old_user_langs = [
                    l for l, src in lang_sources.items() if src in ("user_choice", "rare_user_choice")
                ]
                for lang in old_user_langs:
                    self.character_data["proficiencies"]["languages"] = [
                        l for l in self.character_data["proficiencies"]["languages"] if l != lang
                    ]
                    lang_sources.pop(lang, None)

                language_options = self.get_language_options()
                available_languages = set(language_options["available_languages"])
                selection_count = language_options["selection_count"]
                rare_set = set(self.RARE_LANGUAGE_OPTIONS)

                normalized_choices = []
                for lang in choice_value:
                    if (
                        isinstance(lang, str)
                        and lang in available_languages
                        and lang not in normalized_choices
                    ):
                        normalized_choices.append(lang)
                    # Enforce exactly N selected languages by truncating extras.
                    if len(normalized_choices) >= selection_count:
                        break

                # Add new language selections
                for lang in normalized_choices:
                    if lang not in self.character_data["proficiencies"]["languages"]:
                        self.character_data["proficiencies"]["languages"].append(lang)
                        src = "rare_user_choice" if lang in rare_set else "user_choice"
                        self.character_data["proficiency_sources"]["languages"][lang] = src
                self.character_data["choices_made"][choice_key] = normalized_choices
            return True

        # Backward compatibility for legacy rare_languages key
        elif choice_key_lower == "rare_languages":
            if isinstance(choice_value, list):
                language_options = self.get_language_options()
                available_rare = set(language_options["all_rare_languages"])
                rare_set = set(self.RARE_LANGUAGE_OPTIONS)
                standard_existing = [
                    l for l in self.character_data["choices_made"].get("languages", [])
                    if l not in rare_set
                ]
                new_rare = [l for l in choice_value if isinstance(l, str) and l in available_rare]
                combined = (standard_existing + new_rare)[:language_options["selection_count"]]
                self.character_data["choices_made"]["rare_languages"] = new_rare
                self.apply_choice("languages", combined)
            return True

        # Skills
        elif choice_key_lower in ["skill_choices", "skills"]:
            if isinstance(choice_value, list):
                for skill in choice_value:
                    if skill not in self.character_data["proficiencies"]["skills"]:
                        self.character_data["proficiencies"]["skills"].append(skill)
                        # Track that this came from class selection
                        class_name = self.character_data.get("class", "Class")
                        self.character_data["proficiency_sources"]["skills"][skill] = (
                            class_name
                        )
            return True

        # Tool proficiencies
        elif choice_key_lower in ["tool_choices", "tools"]:
            if isinstance(choice_value, list):
                for tool in choice_value:
                    if tool not in self.character_data["proficiencies"]["tools"]:
                        self.character_data["proficiencies"]["tools"].append(tool)
                        # Track that this came from class selection
                        class_name = self.character_data.get("class", "Class")
                        self.character_data["proficiency_sources"]["tools"][tool] = (
                            class_name
                        )
            elif isinstance(choice_value, str) and choice_value:
                if choice_value not in self.character_data["proficiencies"]["tools"]:
                    self.character_data["proficiencies"]["tools"].append(choice_value)
                    class_name = self.character_data.get("class", "Class")
                    self.character_data["proficiency_sources"]["tools"][choice_value] = (
                        class_name
                    )
            return True

        # Background skill replacements — restore from saved choices
        elif choice_key_lower == "background_skill_replacements":
            normalized_replacements: List[str] = []
            if isinstance(choice_value, str):
                normalized_replacements = [choice_value] if choice_value else []
            elif isinstance(choice_value, list):
                normalized_replacements = choice_value
            self.apply_background_skill_replacement(normalized_replacements)
            return True

        # Species skill replacements — restore from saved choices
        elif choice_key_lower == "species_skill_replacements":
            normalized_replacements: List[str] = []
            if isinstance(choice_value, str):
                normalized_replacements = [choice_value] if choice_value else []
            elif isinstance(choice_value, list):
                normalized_replacements = choice_value
            self.apply_species_skill_replacement(normalized_replacements)
            return True

        # Barbarian Primal Knowledge skill choice
        elif choice_key_lower in ("primal_knowledge_skill", "subclass_primal_knowledge_skill"):
            if isinstance(choice_value, str) and choice_value:
                if choice_value not in self.character_data["proficiencies"]["skills"]:
                    self.character_data["proficiencies"]["skills"].append(choice_value)
                    self.character_data["proficiency_sources"]["skills"][choice_value] = (
                        "Barbarian (Primal Knowledge)"
                    )
            return True

        # Bard College of the Moon Primal Lore skill choice
        elif choice_key_lower in ("primal_lore_skill", "subclass_primal_lore_skill"):
            if isinstance(choice_value, str) and choice_value:
                if choice_value not in self.character_data["proficiencies"]["skills"]:
                    self.character_data["proficiencies"]["skills"].append(choice_value)
                    self.character_data["proficiency_sources"]["skills"][choice_value] = (
                        "College of the Moon (Primal Lore)"
                    )
            return True

        # Barbarian Wild Heart Aspect of the Wilds choice
        elif choice_key_lower in ("aspect_of_the_wilds", "subclass_aspect_of_the_wilds"):
            if choice_value == "Owl":
                current_dv = int(self.character_data.get("darkvision", 0) or 0)
                self.character_data["darkvision"] = current_dv + 60 if current_dv > 0 else 60
            elif choice_value == "Panther":
                self.character_data["climb_speed"] = self.character_data.get("speed", 30)
            elif choice_value == "Salmon":
                self.character_data["swim_speed"] = self.character_data.get("speed", 30)
            return True

        # Spells - Legacy handler (cantrip selection removed from creation wizard)
        elif choice_key_lower == "spellcasting":
            # Silently skipped: "spellcasting" is listed in the Pass 1 ordered
            # key list in apply_choices() so it is consumed before the second
            # pass.  Old saved characters may carry this key; new characters
            # never write it.  No action is required here — cantrip selection is
            # handled post-creation via the spell_selections choice.
            return True

        # Spell selections - restore user-selected prepared spells
        elif choice_key_lower == "spell_selections":
            validated = self._validate_spell_selections(choice_value)
            existing_prepared = self.character_data["spells"].get("prepared", {})
            existing_cantrips = existing_prepared.get("cantrips", {})
            existing_spells = existing_prepared.get("spells", {})

            preserved_cantrips = {
                name: data
                for name, data in existing_cantrips.items()
                if isinstance(data, dict) and data
            }
            preserved_spells = {
                name: data
                for name, data in existing_spells.items()
                if isinstance(data, dict) and data
            }

            merged_cantrips = dict(preserved_cantrips)
            merged_cantrips.update({name: {} for name in validated["cantrips"]})
            self.character_data["spells"]["prepared"]["cantrips"] = merged_cantrips

            merged_spells = dict(preserved_spells)
            merged_spells.update({name: {} for name in validated["spells"]})
            self.character_data["spells"]["prepared"]["spells"] = merged_spells
            self.character_data["spells"]["background_spells"] = {}
            for cantrip in validated["background_cantrips"]:
                self.character_data["spells"]["background_spells"][cantrip] = {"level": 0}
            for spell in validated["background_spells"]:
                self.character_data["spells"]["background_spells"][spell] = {"level": 1}

            spellbook_list = validated.get("spellbook", [])
            if isinstance(choice_value, dict) and isinstance(choice_value.get("spellbook"), dict):
                if choice_value["spellbook"]:
                    self.character_data["spells"]["spellbook"] = dict(choice_value["spellbook"])
                else:
                    self.character_data["spells"].pop("spellbook", None)
            elif spellbook_list:
                spellbook_entries = {}
                for spell in spellbook_list:
                    if isinstance(spell, str) and spell:
                        s_def = self._load_spell_definition(spell)
                        spellbook_entries[spell] = {
                            "level": s_def.get("level", 1),
                            "school": s_def.get("school", ""),
                            "ritual": s_def.get("ritual", False),
                        }
                if spellbook_entries:
                    self.character_data["spells"]["spellbook"] = spellbook_entries
            elif isinstance(choice_value, dict) and "spellbook" in choice_value:
                self.character_data["spells"].pop("spellbook", None)
            return True

        # Weapon Mastery - removed from creation wizard, managed post-creation
        elif choice_key_lower == "weapon mastery":
            # Silently skipped: "weapon mastery" is listed in the Pass 1 ordered
            # key list in apply_choices() so it is consumed before the second
            # pass.  Old saved characters may carry this key; new characters
            # never write it.  No action is required here — mastery selection is
            # handled post-creation via the weapon_mastery_selections choice.
            return True

        # Weapon mastery selections - restore user-selected masteries
        elif choice_key_lower == "weapon_mastery_selections":
            self.character_data["weapon_masteries"]["selected"] = self._validate_weapon_mastery_selections(
                choice_value
            )
            return True

        # Eldritch Invocation selections - restore user-selected invocations
        elif choice_key_lower == "eldritch_invocation_selections":
            invocation_selections = self._normalize_eldritch_invocation_selections(
                choice_value
            )
            if invocation_selections is None:
                return False
            selected_invocations = self._validate_eldritch_invocation_selections(
                invocation_selections["selected"]
            )
            invocation_selections["selected"] = selected_invocations
            if not self._validate_eldritch_invocation_cantrip_choices(
                invocation_selections
            ):
                raise SelectionValidationError(
                    family="eldritch_invocation_selections",
                    code="invalid_selection",
                    message=(
                        "Submitted Eldritch Invocation selections are not valid for this character"
                    ),
                    violations=[
                        {
                            "field": "eldritch_invocation_selections.cantrip_choices",
                            "reason": "invalid_cantrip_choices",
                        }
                    ],
                )

            # Store and export one canonical shape.  List input remains accepted
            # for saved characters created before cantrip choices were modeled.
            self.character_data["choices_made"][choice_key] = invocation_selections
            self.character_data["eldritch_invocations"] = invocation_selections

            # Route each chosen invocation through the single dispatcher.  The
            # cantrip-choice effects are materialized as grant_cantrip effects
            # after their selections have been validated.
            self._clear_eldritch_invocation_effects()
            self._apply_eldritch_invocation_effects(
                invocation_selections["selected"],
                invocation_selections["cantrip_choices"],
                invocation_selections["choices"],
            )
            return True

        # Artificer Replicate Magic Item plans
        elif choice_key_lower in ("artificer_replicate_plans", "artificer_plans"):
            plans = self._validate_artificer_replicate_plans(choice_value)
            self.character_data["choices_made"][choice_key] = plans
            self.character_data["artificer_replicate_plans"] = plans
            return True

        # Artificer Active Replicated Items loadout
        elif choice_key_lower in ("artificer_active_replications", "artificer_active_items"):
            active = self._validate_artificer_active_replications(choice_value)
            self.character_data["choices_made"][choice_key] = active
            self.character_data["artificer_active_replications"] = active
            return True

        # Artificer Replications composite (plans + active)
        elif choice_key_lower == "artificer_replications":
            if isinstance(choice_value, dict):
                if "plans" in choice_value:
                    plans = self._validate_artificer_replicate_plans(choice_value["plans"])
                    self.character_data["choices_made"]["artificer_replicate_plans"] = plans
                    self.character_data["artificer_replicate_plans"] = plans
                if "active" in choice_value:
                    active = self._validate_artificer_active_replications(choice_value["active"])
                    self.character_data["choices_made"]["artificer_active_replications"] = active
                    self.character_data["artificer_active_replications"] = active
                self.character_data["choices_made"][choice_key] = choice_value
            return True

        # Nested bonus choices (e.g., Thaumaturge_bonus_cantrip)
        elif "_bonus_cantrip" in choice_key_lower:
            # Extract parent feature name (e.g., "Thaumaturge" from "Thaumaturge_bonus_cantrip")
            parent_name = (
                choice_key.replace("_bonus_cantrip", "").replace("_", " ").title()
            )
            class_name = self.character_data.get("class", "Class")

            # Add cantrip(s) to always_prepared dict (doesn't count against limit)
            cantrips_to_add = (
                choice_value if isinstance(choice_value, list) else [choice_value]
            )
            for cantrip in cantrips_to_add:
                # Add to always_prepared dict
                self.character_data["spells"]["always_prepared"][cantrip] = {
                    "level": 0,
                    "source": f"{parent_name} ({class_name})",
                    "always_prepared": True,
                    "counts_against_limit": False,
                }

                # Also track in spell_metadata for compatibility
                self.character_data["spell_metadata"][cantrip] = {
                    "source": f"{parent_name} ({class_name})",
                    "always_prepared": True,
                    "once_per_day": False,
                    "counts_against_limit": False,
                }

            # Find the parent feature and append the choice
            cantrip_display = (
                ", ".join(cantrips_to_add)
                if isinstance(choice_value, list)
                else choice_value
            )
            for category in ["class", "subclass", "species", "lineage"]:
                for feature in self.character_data["features"][category]:
                    # Look for features that start with "Divine Order: Thaumaturge" or just "Thaumaturge"
                    if parent_name in feature["name"]:
                        # Append the bonus cantrip info
                        bonus_text = f"\n\nBonus Cantrip: {cantrip_display}"
                        if bonus_text not in feature["description"]:
                            feature["description"] += bonus_text
                        return True
            return True

        # Character metadata
        elif choice_key_lower in ["character_name", "name"]:
            self.character_data["name"] = choice_value
            return True
        elif choice_key_lower == "alignment":
            self.character_data["alignment"] = choice_value
            return True

        # Equipment selections
        elif choice_key_lower == "equipment_selections":
            return self._process_equipment_selections(choice_value)
        elif choice_key_lower == "inventory":
            return self._process_inventory_choice(choice_value)

        # Maneuvers
        elif choice_key_lower in ["maneuvers", "subclass_combat superiority"]:
            if isinstance(choice_value, list):
                self.character_data["maneuvers_known"] = [
                    m for m in choice_value if isinstance(m, str) and m
                ]
            elif isinstance(choice_value, str) and choice_value:
                if choice_value not in self.character_data.setdefault("maneuvers_known", []):
                    self.character_data["maneuvers_known"].append(choice_value)
            self._update_feature_choice_display(choice_key, choice_value)
            if self.character_data.get("subclass_data"):
                self._apply_choice_effects(
                    choice_key, choice_value, self.character_data["subclass_data"]
                )
            return True

        # Arcane Shots
        elif choice_key_lower in ["arcane_shots", "arcane_shot", "subclass_arcane shot"]:
            if isinstance(choice_value, list):
                self.character_data["arcane_shots_known"] = [
                    s for s in choice_value if isinstance(s, str) and s
                ]
            elif isinstance(choice_value, str) and choice_value:
                if choice_value not in self.character_data.setdefault("arcane_shots_known", []):
                    self.character_data["arcane_shots_known"].append(choice_value)
            self._update_feature_choice_display(choice_key, choice_value)
            if self.character_data.get("subclass_data"):
                self._apply_choice_effects(
                    choice_key, choice_value, self.character_data["subclass_data"]
                )
            return True

        # Feat sub-choices can come from either class feat slots
        # (for example, class_feat_4_cantrips) or namespaced feat-choice pages
        # (for example, feat_Magic Initiate (Wizard)_cantrips).
        elif (feat_choice_context := self._resolve_feat_choice_context(choice_key)):
            feat_name, sub_choice_name, feat_data, sub_choice_def, choice_namespace = feat_choice_context
            if not self._feat_choice_dependencies_met(choice_namespace, sub_choice_def, choice_key):
                return True
            self._apply_feat_choice_selection(
                feat_name,
                sub_choice_name,
                choice_value,
                feat_data=feat_data,
            )
            return True

        # Class-level feat slot, e.g. class_feat_4, class_feat_8, class_feat_19
        elif _CLASS_FEAT_SLOT_RE.match(choice_key):
            slot_level = self._class_feat_slot_level(choice_key)
            total_level = self._get_total_character_level()
            if isinstance(choice_value, str) and choice_value.strip():
                feat_data_loaded = self._load_feat_data(choice_value)
                if feat_data_loaded:
                    req_level = self._get_feat_required_level(feat_data_loaded)
                    if req_level > slot_level and req_level > total_level:
                        msg = (
                            f"Feat '{choice_value}' requires Level {req_level}+, "
                            f"but slot level is {slot_level} and character level is {total_level}."
                        )
                        self.character_data.setdefault("warnings", []).append(msg)
                        raise SelectionValidationError(
                            family="class_feat",
                            code="prerequisite_level_not_met",
                            message=msg,
                            violations=[
                                {
                                    "field": choice_key,
                                    "reason": "prerequisite_level_not_met",
                                    "selection": choice_value,
                                    "required_level": req_level,
                                    "slot_level": slot_level,
                                    "character_level": total_level,
                                }
                            ],
                        )

                    self._apply_feat_to_slot(choice_key, choice_value, feat_data_loaded, slot_level)

            self._update_feature_choice_display(choice_key, choice_value)
            return True

        # Generic choice - might be class feature choice
        # Try to find and apply effects from class/subclass data
        else:
            # Update feature display name if this is a choice for an existing feature
            self._update_feature_choice_display(choice_key, choice_value)

            # Check if this is a feature choice with effects
            if self.character_data.get("class_data"):
                self._apply_choice_effects(
                    choice_key, choice_value, self.character_data["class_data"]
                )
            if self.character_data.get("subclass_data"):
                self._apply_choice_effects(
                    choice_key, choice_value, self.character_data["subclass_data"]
                )
            if self.character_data.get("species_data"):
                self._apply_species_choice_effects(
                    choice_key, choice_value, self.character_data["species_data"]
                )
            if self.character_data.get("lineage_data"):
                self._apply_species_choice_effects(
                    choice_key, choice_value, self.character_data["lineage_data"]
                )
            # Just store it
            return True

    def _update_feature_choice_display(self, choice_key: str, choice_value: Any):
        """
        Update feature display name and description to include the choice made.

        Args:
            choice_key: The choice identifier (e.g., 'Divine Order', 'divine_order', 'species_trait_Elven Lineage')
            choice_value: The chosen value (e.g., 'Thaumaturge', 'Wisdom')
        """
        if not isinstance(choice_value, (str, list)):
            return

        # Handle species_trait_ and subclass_ prefixes
        feature_base = choice_key
        if choice_key.startswith("species_trait_"):
            feature_base = choice_key.replace("species_trait_", "")
        elif choice_key.startswith("subclass_"):
            feature_base = choice_key.replace("subclass_", "")

        # Normalize choice key to match feature names
        feature_name_variants = [
            feature_base,
            feature_base.replace("_", " ").title(),
            feature_base.replace("_", " "),
            choice_key,  # Also try original
            choice_key.replace("_", " ").title(),
            choice_key.replace("_", " "),
        ]
        target_feature_names = set(feature_name_variants)

        # Try to find the choice-specific description from class/subclass data
        choice_description = None
        choice_scaling = None

        # First check for external sources
        for data_source_key in ["class_data", "subclass_data"]:
            source_data = self.character_data.get(data_source_key, {})
            if source_data and isinstance(source_data, dict):
                # Check features_by_level for external source references
                features_by_level = source_data.get("features_by_level", {})
                for level_features in features_by_level.values():
                    if not isinstance(level_features, dict):
                        continue

                    for feature_name, feature_data in level_features.items():
                        choices_config = feature_data.get("choices", {}) if isinstance(feature_data, dict) else {}
                        choice_names = []
                        if isinstance(choices_config, dict):
                            cn = choices_config.get("name")
                            if cn:
                                choice_names.append(cn)
                        elif isinstance(choices_config, list):
                            for c in choices_config:
                                if isinstance(c, dict) and c.get("name"):
                                    choice_names.append(c["name"])

                        is_match = (
                            feature_name in feature_name_variants
                            or any(cn in feature_name_variants for cn in choice_names)
                            or choice_key in choice_names
                            or any(choice_key == f"subclass_{feature_name}_{cn}" for cn in choice_names)
                            or any(choice_key == f"class_{feature_name}_{cn}" for cn in choice_names)
                            or any(choice_key == f"subclass_{cn}" for cn in choice_names)
                            or any(choice_key == f"class_{cn}" for cn in choice_names)
                        )

                        if is_match and isinstance(feature_data, dict):
                            target_feature_names.add(feature_name)
                            if choices_config:
                                source_config = choices_config.get("source", {}) if isinstance(choices_config, dict) else {}
                                if not source_config and isinstance(choices_config, list):
                                    for c in choices_config:
                                        if isinstance(c, dict) and (c.get("name") == choice_key or choice_key.endswith(str(c.get("name")))):
                                            source_config = c.get("source", {})
                                            break

                                # Handle external source
                                if source_config.get("type") == "external":
                                    external_file = source_config.get("file")
                                    external_list = source_config.get("list")

                                    if external_file and external_list:
                                        try:
                                            external_path = self._external_data_path(
                                                external_file
                                            )
                                            if external_path is not None and external_path.exists():
                                                import json

                                                with open(external_path, "r", encoding="utf-8") as f:
                                                    external_data = json.load(f)
                                                choice_list = external_data.get(
                                                    external_list, {}
                                                )

                                                if isinstance(choice_value, list):
                                                    desc_parts = []
                                                    for item in choice_value:
                                                        opt = choice_list.get(item) if isinstance(choice_list, dict) else None
                                                        if isinstance(opt, dict) and opt.get("description"):
                                                            desc_parts.append(f"**{item}**: {opt['description']}")
                                                        elif isinstance(opt, str):
                                                            desc_parts.append(f"**{item}**: {opt}")
                                                    if desc_parts:
                                                        choice_description = "\n\n".join(desc_parts)
                                                        break
                                                elif isinstance(choice_list, dict) and choice_value in choice_list:
                                                    option_data = choice_list[
                                                        choice_value
                                                    ]
                                                    if isinstance(option_data, dict):
                                                        choice_description = (
                                                            option_data.get(
                                                                "description", ""
                                                            )
                                                        )
                                                        choice_scaling = (
                                                            option_data.get("scaling")
                                                        )
                                                    elif isinstance(option_data, str):
                                                        choice_description = option_data
                                                    break
                                                elif isinstance(choice_list, list) and choice_value in choice_list:
                                                    break
                                        except (json.JSONDecodeError, IOError) as e:
                                            print(
                                                f"Warning: Could not load choice description from {external_file}: {e}"
                                            )

                        if choice_description:
                            break
                    if choice_description:
                        break
                if choice_description:
                    break

        # If not found in external sources, check internal lists
        if not choice_description:
            for data_source_key in ["class_data", "subclass_data"]:
                source_data = self.character_data.get(data_source_key, {})
                if source_data and isinstance(source_data, dict):
                    # Look for internal list (e.g., 'divine_orders', 'fighting_styles')
                    for data_key, data_value in source_data.items():
                        if isinstance(data_value, dict):
                            if isinstance(choice_value, list):
                                desc_parts = []
                                for item in choice_value:
                                    if item in data_value:
                                        opt = data_value[item]
                                        if isinstance(opt, dict) and opt.get("description"):
                                            desc_parts.append(f"**{item}**: {opt['description']}")
                                        elif isinstance(opt, str):
                                            desc_parts.append(f"**{item}**: {opt}")
                                if desc_parts:
                                    choice_description = "\n\n".join(desc_parts)
                                    break
                            elif choice_value in data_value:
                                option_data = data_value[choice_value]
                                if isinstance(option_data, dict):
                                    if "description" in option_data:
                                        choice_description = option_data["description"]
                                        choice_scaling = option_data.get("scaling")
                                        break
                                elif isinstance(option_data, str):
                                    choice_description = option_data
                                    break
                    if choice_description:
                        break

        # Search all feature categories for a matching feature
        for category in [
            "class",
            "subclass",
            "species",
            "lineage",
            "background",
            "feats",
        ]:
            for feature in self.character_data["features"][category]:
                if category == "feats" and feature.get("slot") == choice_key:
                    continue
                # Check if this feature matches the choice
                for variant in target_feature_names:
                    if feature["name"] == variant or feature["name"].startswith(
                        variant + ":"
                    ):
                        # Update the name to include the choice
                        base_name = (
                            variant
                            if feature["name"] == variant
                            else feature["name"].split(":")[0]
                        )
                        if base_name == choice_value:
                            continue
                        if isinstance(choice_value, list):
                            feature["name"] = f"{base_name}: {', '.join(choice_value)}"
                        else:
                            feature["name"] = f"{base_name}: {choice_value}"

                        # Update description if we found a choice-specific one (for single choices)
                        if choice_description and not isinstance(choice_value, list):
                            # Apply scaling if present
                            if choice_scaling:
                                choice_description = self._apply_feature_scaling(
                                    choice_description, choice_scaling
                                )
                            feature["description"] = choice_description
                        return

    # ------------------------------------------------------------------
    # Phase 6: unified choice → effects resolver
    # ------------------------------------------------------------------

    def resolve_effects_for_choice(
        self,
        choice_key: str,
        choice_value: Any,
        source_data: Dict[str, Any],
    ) -> List[Tuple[Dict[str, Any], str, str]]:
        """Resolve a single class/subclass choice to its effects.

        Returns a flat list of ``(effect, source_label, source_type)`` triples
        covering the *choice-driven* effect-authoring locations (see
        ``.github/instructions/data-schemas.instructions.md`` for the catalogue
        of 5 authoring locations):

          * Location 4 — inside a ``choices`` object on a feature.
          * Location 5 — an external file referenced via
            ``choices.source.type == "external"`` (e.g. fighting styles).
          * Internal-list fallback — a sibling dict on ``source_data`` whose
            value contains ``effects`` (e.g. ``divine_orders``).

        Locations 1, 2, 3 are *not* the responsibility of this method:
          * Location 1 (top-level feat ``effects``) — handled by feat loaders.
          * Location 2 (class feature ``effects``) — handled by
            ``_apply_trait_effects`` during the feature walk.
          * Location 3 (``choice_effects``) — handled by
            ``_apply_species_choice_effects``.

        The caller is responsible for invoking ``_apply_effect`` on each
        returned triple; this method performs **lookup only** and never
        mutates character state. That guarantees the "one dispatcher"
        invariant: every effect — regardless of where it was authored —
        reaches ``character_data`` exclusively through ``_apply_effect``.
        """
        if not isinstance(source_data, dict):
            return []

        results: List[Tuple[Dict[str, Any], str, str]] = []

        def _load_external(file_name: str, list_name: str, key: Any):
            """Load and return the option-data dict for ``key`` from an external file."""
            if not file_name or not list_name or not isinstance(key, str):
                return None
            external_path = self._external_data_path(file_name)
            if external_path is None or not external_path.exists():
                return None
            try:
                with open(external_path, "r") as f:
                    external_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"WARNING: Failed to load external file {file_name}: {e}")
                return None
            options_list = external_data.get(list_name, {})
            if not isinstance(options_list, dict):
                return None
            return options_list.get(key)

        def _harvest(option_data: Any, src_label: str) -> bool:
            if not isinstance(option_data, dict):
                return False
            effects = option_data.get("effects")
            if not isinstance(effects, list):
                return False
            for effect in effects:
                if isinstance(effect, dict):
                    results.append((effect, src_label, "class_choice"))
            return True

        # ---------------- Location 5 / 4 : feature.choices.source ----------------
        features_by_level = source_data.get("features_by_level", {})
        for level_features in features_by_level.values():
            if not isinstance(level_features, dict):
                continue
            for feature_name, feature_data in level_features.items():
                if not isinstance(feature_data, dict):
                    continue

                choices_config = feature_data.get("choices")
                # ``choices`` may be a dict OR a list of dicts (some features
                # pose several independent choices). Normalise to a list.
                if isinstance(choices_config, dict):
                    choices_list = [choices_config]
                elif isinstance(choices_config, list):
                    choices_list = [c for c in choices_config if isinstance(c, dict)]
                else:
                    choices_list = []

                clean_choice_key = choice_key[9:] if choice_key.startswith("subclass_") else choice_key
                matches_by_feature_name = (
                    feature_name == choice_key
                    or feature_name == clean_choice_key
                    or clean_choice_key.startswith(f"{feature_name}_")
                )
                matches_by_choice_name = any(
                    c.get("name") in (choice_key, clean_choice_key)
                    or clean_choice_key.endswith(f"_{c.get('name')}")
                    for c in choices_list
                )

                if not (matches_by_feature_name or matches_by_choice_name):
                    continue

                # A feature effect can reference the canonical persisted key
                # for one of its choices (for example, a selected tool or
                # spell). Resolve it here so direct apply_choice() calls and
                # batch rebuilds use the same dispatcher path.
                for effect in feature_data.get("effects", []):
                    if (
                        isinstance(effect, dict)
                        and (
                            effect.get("from_choice") in (choice_key, clean_choice_key)
                        )
                    ):
                        results.append((effect, feature_name, "class_choice"))

                # Data-driven choice_effects on class/subclass features
                feat_choice_effects = feature_data.get("choice_effects", {})
                if isinstance(feat_choice_effects, dict):
                    vals_to_check = choice_value if isinstance(choice_value, (list, tuple, set)) else [choice_value]
                    # Shape 1: choice_name -> choice_value -> effects[]
                    for c_name in [choice_key, clean_choice_key, (clean_choice_key.split('_')[-1] if '_' in clean_choice_key else '')]:
                        if c_name and c_name in feat_choice_effects and isinstance(feat_choice_effects[c_name], dict):
                            val_map = feat_choice_effects[c_name]
                            for val in vals_to_check:
                                if isinstance(val, (str, int, float, bool)) and val in val_map:
                                    for eff in val_map[val]:
                                        results.append((eff, feature_name, "class_choice"))
                    # Shape 2: choice_value -> effects[]
                    for val in vals_to_check:
                        if isinstance(val, (str, int, float, bool)) and val in feat_choice_effects and isinstance(feat_choice_effects[val], list):
                            for eff in feat_choice_effects[val]:
                                results.append((eff, feature_name, "class_choice"))

                if results:
                    return results

                for choice_cfg in choices_list:
                    source_config = choice_cfg.get("source", {})
                    # select_multiple choices (e.g. Battle Master maneuvers)
                    # supply a list value; iterate so each chosen option's
                    # effects flow through the dispatcher independently.
                    if isinstance(choice_value, list):
                        values_iter = [v for v in choice_value if v is not None]
                    else:
                        values_iter = [choice_value]

                    if source_config.get("type") == "external":
                        any_match = False
                        for val in values_iter:
                            option_data = _load_external(
                                source_config.get("file"),
                                source_config.get("list"),
                                val,
                            )
                            if _harvest(option_data, str(val)):
                                any_match = True
                        if any_match:
                            return results
                    elif source_config.get("type") == "internal":
                        # Location 4: ``choices.source.list`` names a sibling
                        # list on the feature or trait.
                        internal_list_name = source_config.get("list", "")
                        if internal_list_name:
                            internal_list = feature_data.get(internal_list_name, {})
                            any_match = False
                            for val in values_iter:
                                option_data = (
                                    internal_list.get(val)
                                    if isinstance(internal_list, dict)
                                    else None
                                )
                                if _harvest(option_data, str(val)):
                                    any_match = True
                            if any_match:
                                return results

        # ---------------- Internal-list sibling fallback ----------------
        # Some class data files keep option dicts at the top level alongside
        # ``features_by_level`` (e.g. ``divine_orders``). Walk those.
        if isinstance(choice_value, str):
            for _, data_value in source_data.items():
                if not isinstance(data_value, dict):
                    continue
                option_data = data_value.get(choice_value)
                if _harvest(option_data, choice_value):
                    return results

        return results

    def _apply_choice_effects(
        self, choice_key: str, choice_value: Any, source_data: Dict[str, Any]
    ):
        """Thin wrapper: resolve effects for a class/subclass choice and apply them.

        After Phase 6 this is the *only* place outside ``_apply_trait_effects``
        that funnels choice-driven effects into ``_apply_effect``. It also
        handles the side-band feat-loading path (when a class feat slot is
        filled by a feat name from ``general_feats.json`` / ``origin_feats.json``)
        because that path also creates a ``features.feats`` entry, not just
        effects.

        The lookup itself lives in ``resolve_effects_for_choice``.
        """
        if not isinstance(source_data, dict):
            print(
                f"WARNING: _apply_choice_effects received non-dict source_data: {type(source_data)}"
            )
            return

        # 1) Primary path: resolve via the unified resolver.
        triples = self.resolve_effects_for_choice(choice_key, choice_value, source_data)
        if triples:
            for effect, src_label, src_type in triples:
                self._apply_effect(effect, src_label, src_type)
            return

        # 2) Feat-slot fallback. Some "fighting_style"-style choice slots are
        # also used to pick FEATS by name (general_feats.json / origin_feats.json);
        # in that case the chosen value is a feat name and we must (a) add a
        # feat entry and (b) apply the feat's direct effects via ``_apply_effect``.
        if not isinstance(choice_value, str):
            return

        features_by_level = source_data.get("features_by_level", {})
        for level_features in features_by_level.values():
            if not isinstance(level_features, dict):
                continue
            for feature_name, feature_data in level_features.items():
                if not isinstance(feature_data, dict):
                    continue
                choices_config = feature_data.get("choices")
                if not isinstance(choices_config, dict):
                    continue
                if choices_config.get("name") != choice_key:
                    continue

                feat_data_loaded = self._load_feat_data(choice_value)
                if feat_data_loaded is None:
                    return
                feat_name = choice_value

                # Extract slot level from choice_key (e.g. "class_feat_4" -> 4)
                slot_level = self._class_feat_slot_level(choice_key)
                total_level = self._get_total_character_level()
                req_level = self._get_feat_required_level(feat_data_loaded)
                if req_level > slot_level and req_level > total_level:
                    msg = (
                        f"Feat '{choice_value}' requires Level {req_level}+, "
                        f"but slot level is {slot_level} and character level is {total_level}."
                    )
                    self.character_data.setdefault("warnings", []).append(msg)
                    raise SelectionValidationError(
                        family="class_feat",
                        code="prerequisite_level_not_met",
                        message=msg,
                        violations=[
                            {
                                "field": choice_key,
                                "reason": "prerequisite_level_not_met",
                                "selection": choice_value,
                                "required_level": req_level,
                                "slot_level": slot_level,
                                "character_level": total_level,
                            }
                        ],
                    )
                self._apply_feat_to_slot(choice_key, feat_name, feat_data_loaded, slot_level)
                return

    def _apply_feat_to_slot(
        self,
        slot_key: str,
        feat_name: str,
        feat_data: Dict[str, Any],
        slot_level: int,
    ):
        """Add a feat to features['feats'] for a specific slot and dispatch its effects."""
        # Clear any previously picked feat for this slot
        old_feat_entry = next(
            (
                f
                for f in self.character_data["features"]["feats"]
                if f.get("slot") == slot_key
            ),
            None,
        )
        if old_feat_entry:
            old_feat_name = old_feat_entry["name"]
            self.character_data["features"]["feats"] = [
                f
                for f in self.character_data["features"]["feats"]
                if f.get("slot") != slot_key
            ]
            self._filter_applied_effects(
                lambda e, _name=old_feat_name, _slot=slot_key: (
                    e.get("source_type") == "feat"
                    and e.get("source") == _name
                    and e.get("slot") == _slot
                )
            )

        # Build feat description
        description = feat_data.get("description", "")
        benefits = feat_data.get("benefits", [])
        if benefits:
            description += self._format_benefits(benefits)

        already_in_slot = any(
            f.get("slot") == slot_key
            for f in self.character_data["features"]["feats"]
        )
        if not already_in_slot:
            self.character_data["features"]["feats"].append(
                {
                    "name": feat_name,
                    "description": description,
                    "source": "class",
                    "level": slot_level,
                    "slot": slot_key,
                }
            )

        # Apply the feat's top-level effects (Location 1) via the dispatcher.
        for feat_effect in feat_data.get("effects", []):
            self._apply_effect(feat_effect, feat_name, "feat")

    def _normalize_multiclass_rows(self, rows: Any) -> List[Dict[str, Any]]:
        """Normalize classes rows into a validated internal list."""
        if not isinstance(rows, list):
            return []

        normalized_rows: List[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            class_name = row.get("class_name")
            if not isinstance(class_name, str) or not class_name.strip():
                continue
            try:
                level = int(row.get("level", 1))
            except (TypeError, ValueError):
                continue
            if level < 1:
                continue

            normalized_row: Dict[str, Any] = {
                "class_name": class_name.strip(),
                "level": level,
            }
            subclass = row.get("subclass")
            if isinstance(subclass, str) and subclass.strip():
                normalized_row["subclass"] = subclass.strip()
            normalized_rows.append(normalized_row)

        return normalized_rows

    def _apply_class_features_only(self, class_data: Dict[str, Any], level: int):
        """Apply only level-based class features (no base proficiencies)."""
        features_by_level = class_data.get("features_by_level", {})
        if not isinstance(features_by_level, dict):
            return

        for feat_level in range(1, level + 1):
            level_features = features_by_level.get(str(feat_level), {})
            if not isinstance(level_features, dict):
                continue
            for feature_name, feature_data in level_features.items():
                self._apply_trait_effects(feature_name, feature_data, "class", feat_level)

    def _apply_multiclass_entry_proficiencies(self, class_data: Dict[str, Any]) -> None:
        """Apply proficiencies granted when this class is taken as a SECONDARY class.

        Reads the ``multiclassing`` block from the class JSON and additively
        merges its armor/weapon/tool/save/other proficiencies into the
        character's proficiency lists. Skill picks and wildcard tool picks
        are surfaced as pending player choices on
        ``character_data["pending_multiclass_skill_choices"]`` and
        ``character_data["pending_multiclass_tool_choices"]``.

        Never branches on class name. Always additive, always de-duped.
        """
        mc = class_data.get("multiclassing")
        class_name = class_data.get("name", "Unknown")
        if not isinstance(mc, dict):
            print(
                f"Warning: class '{class_name}' has no multiclassing block; "
                f"secondary-class proficiencies will not be applied."
            )
            return

        proficiencies = self.character_data["proficiencies"]
        sources = self.character_data["proficiency_sources"]

        # Saving throws (RAW for 2024: no secondary class grants saves, but
        # honor the field if a future class JSON ever populates it).
        for save in mc.get("saving_throw_proficiencies", []) or []:
            if save not in proficiencies["saving_throws"]:
                proficiencies["saving_throws"].append(save)

        # Armor — normalize bare "Light"/"Medium"/"Heavy" to canonical
        # "Light armor"/"Medium armor"/"Heavy armor" used by primary classes.
        _ARMOR_NORMALIZE = {
            "Light": "Light armor",
            "Medium": "Medium armor",
            "Heavy": "Heavy armor",
        }
        for armor in mc.get("armor_training", []) or []:
            canonical = _ARMOR_NORMALIZE.get(armor, armor)
            if canonical not in proficiencies["armor"]:
                proficiencies["armor"].append(canonical)

        # Weapons — normalize bare "Simple"/"Martial" to canonical
        # "Simple weapons"/"Martial weapons".
        _WEAPON_NORMALIZE = {
            "Simple": "Simple weapons",
            "Martial": "Martial weapons",
        }
        for weapon in mc.get("weapon_training", []) or []:
            canonical = _WEAPON_NORMALIZE.get(weapon, weapon)
            if canonical not in proficiencies["weapons"]:
                proficiencies["weapons"].append(canonical)

        # Tools — split fixed grants from wildcard "choose one" entries.
        pending_tool_choices = self.character_data.setdefault(
            "pending_multiclass_tool_choices", []
        )
        for tool in mc.get("tool_training", []) or []:
            if isinstance(tool, str) and "(" in tool and "choice" in tool.lower():
                # Wildcard like "Musical Instrument (1 of your choice)" —
                # surface as a pending choice; do not auto-grant.
                if not any(
                    c.get("class_name") == class_name and c.get("label") == tool
                    for c in pending_tool_choices
                ):
                    pending_tool_choices.append({
                        "class_name": class_name,
                        "label": tool,
                    })
                continue
            if tool not in proficiencies["tools"]:
                proficiencies["tools"].append(tool)
                sources["tools"][tool] = class_name

        # Skill proficiencies — apply player choice if present, else queue.
        skill_block = mc.get("skill_proficiencies")
        if isinstance(skill_block, dict):
            count = int(skill_block.get("count", 0) or 0)
            options = skill_block.get("options")
            if options == "any":
                resolved_options = list(self._ALL_SKILLS)
            elif isinstance(options, list):
                resolved_options = list(options)
            else:
                resolved_options = []

            choices_made = self.character_data["choices_made"]
            multiclass_skill_picks = choices_made.get(
                "multiclass_skill_choices", {}
            )
            picks = multiclass_skill_picks.get(class_name, []) if isinstance(
                multiclass_skill_picks, dict
            ) else []

            applied = 0
            for skill in picks:
                if applied >= count:
                    break
                if resolved_options and skill not in resolved_options:
                    continue
                if skill not in proficiencies["skills"]:
                    proficiencies["skills"].append(skill)
                    sources["skills"][skill] = class_name
                applied += 1

            if applied < count:
                pending_skill_choices = self.character_data.setdefault(
                    "pending_multiclass_skill_choices", []
                )
                # De-dupe by class_name; replace if already present.
                pending_skill_choices[:] = [
                    c for c in pending_skill_choices
                    if c.get("class_name") != class_name
                ]
                pending_skill_choices.append({
                    "class_name": class_name,
                    "count": count - applied,
                    "options": [
                        s for s in resolved_options
                        if s not in proficiencies["skills"]
                    ],
                })

        # Other proficiencies — append to a generic bucket. Create it if needed.
        other_profs = mc.get("other_proficiencies", []) or []
        if other_profs:
            bucket = self.character_data.setdefault("other_proficiencies", [])
            for entry in other_profs:
                if entry not in bucket:
                    bucket.append(entry)

    def _apply_additional_multiclass_tracks(self, class_rows: List[Dict[str, Any]]) -> None:
        """Apply class/subclass features for non-primary multiclass rows."""
        if len(class_rows) <= 1:
            return

        original_level = self.character_data.get("level", 1)
        original_class = self.character_data.get("class")
        original_subclass = self.character_data.get("subclass")

        try:
            for row in class_rows[1:]:
                class_name = row["class_name"]
                class_level = row["level"]
                class_data = self._load_class_data(class_name)
                if not class_data:
                    continue

                # Apply each additional class at its own level threshold.
                self.character_data["level"] = class_level
                self.character_data["class"] = class_name
                self._apply_multiclass_entry_proficiencies(class_data)
                self._apply_class_features_only(class_data, class_level)

                subclass_name = row.get("subclass")
                subclass_level = class_data.get("subclass_selection_level", 3)
                if subclass_name and class_level >= subclass_level:
                    subclass_data = self._load_subclass_data(class_name, subclass_name)
                    if subclass_data:
                        self.character_data["subclass"] = subclass_name
                        self._apply_subclass_features(subclass_data, class_level)
        finally:
            self.character_data["level"] = original_level
            self.character_data["class"] = original_class
            self.character_data["subclass"] = original_subclass

    def _get_primary_class_row(self) -> Optional[Dict[str, Any]]:
        rows = self.character_data.get("class_breakdown")
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            return rows[0]
        return None

    def _get_primary_class_level(self) -> int:
        primary = self._get_primary_class_row()
        if primary:
            try:
                return max(1, int(primary.get("level", 1)))
            except (TypeError, ValueError):
                return 1
        return max(1, int(self.character_data.get("level", 1)))

    def _get_class_level(self, class_name: str) -> int:
        """Look up the level for a specific class across multiclass breakdown or single class."""
        if not class_name:
            return 0
        rows = self.character_data.get("class_breakdown")
        if isinstance(rows, list) and rows:
            for row in rows:
                if isinstance(row, dict) and row.get("class_name") == class_name:
                    try:
                        return max(0, int(row.get("level", 0)))
                    except (TypeError, ValueError):
                        return 0
            return 0
        choices_classes = self.character_data.get("choices_made", {}).get("classes")
        if isinstance(choices_classes, list) and choices_classes:
            for row in choices_classes:
                if isinstance(row, dict) and row.get("class_name") == class_name:
                    try:
                        return max(0, int(row.get("level", 0)))
                    except (TypeError, ValueError):
                        return 0
            return 0
        if self.character_data.get("class") == class_name:
            try:
                return max(0, int(self.character_data.get("level", 1)))
            except (TypeError, ValueError):
                return 1
        return 0

    def _get_class_subclass(self, class_name: str) -> str:
        """Look up the subclass for a specific class across multiclass breakdown or single class."""
        if not class_name:
            return ""
        rows = self.character_data.get("class_breakdown")
        if isinstance(rows, list) and rows:
            for row in rows:
                if isinstance(row, dict) and row.get("class_name") == class_name:
                    sub = row.get("subclass")
                    if sub:
                        return str(sub)
        choices_classes = self.character_data.get("choices_made", {}).get("classes")
        if isinstance(choices_classes, list) and choices_classes:
            for row in choices_classes:
                if isinstance(row, dict) and row.get("class_name") == class_name:
                    sub = row.get("subclass")
                    if sub:
                        return str(sub)
        if self.character_data.get("class") == class_name:
            sub = self.character_data.get("subclass") or self.character_data.get("choices_made", {}).get("subclass")
            if sub:
                return str(sub)
        return ""

    def _get_total_character_level(self) -> int:
        """Return total character level across all classes."""
        rows = self.character_data.get("class_breakdown")
        if isinstance(rows, list) and rows:
            return sum(max(1, int(r.get("level", 1))) for r in rows if isinstance(r, dict))
        choices_classes = self.character_data.get("choices_made", {}).get("classes")
        if isinstance(choices_classes, list) and choices_classes:
            return sum(max(1, int(r.get("level", 1))) for r in choices_classes if isinstance(r, dict))
        try:
            return max(1, int(self.character_data.get("level", 1)))
        except (TypeError, ValueError):
            return 1

    def _get_spellcasting_rows(self) -> List[Dict[str, Any]]:
        """Return normalized class rows used for spellcasting calculations."""
        class_rows = self.character_data.get("class_breakdown")
        if isinstance(class_rows, list) and class_rows:
            return self._normalize_multiclass_rows(class_rows)

        class_name = self.character_data.get("class")
        if not isinstance(class_name, str) or not class_name:
            return []

        row: Dict[str, Any] = {
            "class_name": class_name,
            "level": self._get_primary_class_level(),
        }
        subclass_name = self.character_data.get("subclass")
        if isinstance(subclass_name, str) and subclass_name:
            row["subclass"] = subclass_name
        return [row]

    def _resolve_row_spellcasting_source(
        self,
        row: Dict[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Resolve class/subclass spellcasting metadata source for a row."""
        class_name = row.get("class_name", "")
        class_level = max(1, int(row.get("level", 1)))
        subclass_name = row.get("subclass")

        class_data = self._load_class_data(class_name) or {}
        subclass_data = None
        if isinstance(subclass_name, str) and subclass_name:
            subclass_unlock = class_data.get("subclass_selection_level", 3)
            if class_level >= subclass_unlock:
                subclass_data = self._load_subclass_data(class_name, subclass_name)

        class_has_spellcasting = any(
            key in class_data
            for key in ("spellcasting_ability", "spell_slots_by_level", "pact_magic_slots_by_level")
        )
        if class_has_spellcasting:
            return class_data, class_data, subclass_data

        if isinstance(subclass_data, dict):
            subclass_has_spellcasting = any(
                key in subclass_data
                for key in ("spellcasting_ability", "spell_slots_by_level", "pact_magic_slots_by_level")
            )
            if subclass_has_spellcasting:
                return subclass_data, class_data, subclass_data

        return None, class_data, subclass_data

    def _highest_spell_slot_level(self, level_slots: Any) -> int:
        """Return highest slot level with non-zero slots from a row payload."""
        if isinstance(level_slots, list):
            highest = 0
            for idx, count in enumerate(level_slots):
                try:
                    if int(count) > 0:
                        highest = idx + 1
                except (TypeError, ValueError):
                    continue
            return highest

        if isinstance(level_slots, dict):
            highest = 0
            for key, count in level_slots.items():
                try:
                    if int(count) > 0:
                        if isinstance(key, str) and key.endswith(("st", "nd", "rd", "th")):
                            slot_level = self.SPELL_LEVEL_NAMES.index(key) + 1 if key in self.SPELL_LEVEL_NAMES else 0
                        else:
                            slot_level = int(key)
                        highest = max(highest, slot_level)
                except (TypeError, ValueError):
                    continue
            return highest

        return 0

    def _infer_spellcasting_progression(self, spellcasting_source: Optional[Dict[str, Any]]) -> str:
        """Infer progression type from data metadata without class-name checks."""
        if not isinstance(spellcasting_source, dict):
            return "none"

        spellcasting_type = str(spellcasting_source.get("spellcasting_type", "")).strip().lower()
        if "pact" in spellcasting_type:
            return "pact"
        if "third" in spellcasting_type:
            return "third"
        if "half" in spellcasting_type:
            return "half"
        if "full" in spellcasting_type:
            return "full"

        has_pact_table = isinstance(spellcasting_source.get("pact_magic_slots_by_level"), dict)
        has_standard_table = isinstance(spellcasting_source.get("spell_slots_by_level"), dict)
        if has_pact_table and not has_standard_table:
            return "pact"

        standard_table = spellcasting_source.get("spell_slots_by_level")
        if isinstance(standard_table, dict) and standard_table:
            table_key: Optional[str] = None
            if "20" in standard_table:
                table_key = "20"
            else:
                numeric_keys = []
                for key in standard_table.keys():
                    try:
                        numeric_keys.append(int(key))
                    except (TypeError, ValueError):
                        continue
                if numeric_keys:
                    table_key = str(max(numeric_keys))

            if table_key is not None:
                highest_slot = self._highest_spell_slot_level(standard_table.get(table_key))
                if highest_slot >= 9:
                    return "full"
                if highest_slot >= 5:
                    return "half"
                if highest_slot >= 4:
                    return "third"

        if spellcasting_source.get("spellcasting_ability") and has_standard_table:
            return "full"
        return "none"

    def _slots_payload_to_dict(self, level_slots: Any) -> Dict[str, int]:
        """Normalize class/subclass slot payload into the API spell_slots shape."""
        if isinstance(level_slots, list):
            return {
                self.SPELL_LEVEL_NAMES[i]: int(count)
                for i, count in enumerate(level_slots)
                if i < len(self.SPELL_LEVEL_NAMES) and int(count) > 0
            }

        if isinstance(level_slots, dict):
            normalized: Dict[str, int] = {}
            for key, count in level_slots.items():
                try:
                    parsed_count = int(count)
                except (TypeError, ValueError):
                    continue
                if parsed_count <= 0:
                    continue

                if isinstance(key, str) and key in self.SPELL_LEVEL_NAMES:
                    normalized[key] = parsed_count
                else:
                    try:
                        index = int(key) - 1
                    except (TypeError, ValueError):
                        continue
                    if 0 <= index < len(self.SPELL_LEVEL_NAMES):
                        normalized[self.SPELL_LEVEL_NAMES[index]] = parsed_count
            return normalized

        return {}

    def _get_canonical_full_caster_slots_table(self) -> Dict[str, Any]:
        """Return a deterministic canonical full-caster spell-slot table from data files."""
        cache_key = "_cached_full_caster_slots_table"
        cached = getattr(self, cache_key, None)
        if isinstance(cached, dict) and cached:
            return cached

        classes_dir = self.data_dir / "classes"
        if not classes_dir.exists():
            setattr(self, cache_key, {})
            return {}

        for file_path in sorted(classes_dir.glob("*.json")):
            class_data = self._load_json_file(file_path)
            if not isinstance(class_data, dict):
                continue
            if self._infer_spellcasting_progression(class_data) != "full":
                continue
            slots_table = class_data.get("spell_slots_by_level")
            if isinstance(slots_table, dict) and slots_table:
                setattr(self, cache_key, slots_table)
                return slots_table

        setattr(self, cache_key, {})
        return {}

    def _calculate_multiclass_spell_slot_progression(self) -> Dict[str, Any]:
        """Calculate multiclass standard slots + pact tracks from class rows."""
        rows = self._get_spellcasting_rows()
        is_multiclass = len(rows) > 1
        result: Dict[str, Any] = {
            "is_multiclass": is_multiclass,
            "effective_caster_level": 0,
            "spell_slots": {},
            "pact_magic_slots": [],
            "notes": [],
        }
        if not is_multiclass:
            # For a single-class character, still compute effective_caster_level
            if rows:
                row = rows[0]
                class_level = max(1, int(row.get("level", 1)))
                spellcasting_source, _, _ = self._resolve_row_spellcasting_source(row)
                progression = self._infer_spellcasting_progression(spellcasting_source)
                if progression == "full":
                    result["effective_caster_level"] = class_level
                elif progression == "half":
                    result["effective_caster_level"] = (class_level + 1) // 2
                elif progression == "third":
                    result["effective_caster_level"] = class_level // 3
                elif progression == "pact":
                    pact_table = {}
                    if isinstance(spellcasting_source, dict):
                        pact_table = spellcasting_source.get("pact_magic_slots_by_level") or {}
                    pact_row = pact_table.get(str(class_level), []) if isinstance(pact_table, dict) else []
                    pact_entry: Dict[str, Any] = {
                        "class_name": row.get("class_name", ""),
                        "class_level": class_level,
                        "subclass": row.get("subclass"),
                    }
                    if isinstance(pact_row, list) and len(pact_row) >= 2:
                        try:
                            pact_entry["slots"] = int(pact_row[0])
                            pact_entry["slot_level"] = int(pact_row[1])
                        except (TypeError, ValueError):
                            pact_entry["slots"] = 0
                            pact_entry["slot_level"] = 0
                    else:
                        pact_entry["slots"] = 0
                        pact_entry["slot_level"] = 0
                    result["pact_magic_slots"].append(pact_entry)
                # none leaves effective_caster_level as 0
            return result

        effective_caster_level = 0
        has_standard_contributor = False

        for row in rows:
            class_name = row.get("class_name", "")
            class_level = max(1, int(row.get("level", 1)))
            subclass_name = row.get("subclass")
            spellcasting_source, _, _ = self._resolve_row_spellcasting_source(row)
            progression = self._infer_spellcasting_progression(spellcasting_source)

            if progression == "full":
                effective_caster_level += class_level
                has_standard_contributor = True
            elif progression == "half":
                # D&D 2024: half your levels (round up) in Paladin/Ranger.
                effective_caster_level += (class_level + 1) // 2
                has_standard_contributor = True
            elif progression == "third":
                effective_caster_level += class_level // 3
                has_standard_contributor = True
            elif progression == "pact":
                pact_table = {}
                if isinstance(spellcasting_source, dict):
                    pact_table = spellcasting_source.get("pact_magic_slots_by_level") or {}
                pact_row = pact_table.get(str(class_level), []) if isinstance(pact_table, dict) else []
                pact_entry: Dict[str, Any] = {
                    "class_name": class_name,
                    "class_level": class_level,
                    "subclass": subclass_name,
                }
                if isinstance(pact_row, list) and len(pact_row) >= 2:
                    try:
                        pact_entry["slots"] = int(pact_row[0])
                        pact_entry["slot_level"] = int(pact_row[1])
                    except (TypeError, ValueError):
                        pact_entry["slots"] = 0
                        pact_entry["slot_level"] = 0
                elif isinstance(pact_row, dict):
                    try:
                        pact_entry["slots"] = int(pact_row.get("slots", 0))
                    except (TypeError, ValueError):
                        pact_entry["slots"] = 0
                    try:
                        pact_entry["slot_level"] = int(pact_row.get("slot_level", 0))
                    except (TypeError, ValueError):
                        pact_entry["slot_level"] = 0
                else:
                    pact_entry["slots"] = 0
                    pact_entry["slot_level"] = 0
                result["pact_magic_slots"].append(pact_entry)

        result["effective_caster_level"] = effective_caster_level

        if has_standard_contributor and effective_caster_level > 0:
            canonical_table = self._get_canonical_full_caster_slots_table()
            level_slots = canonical_table.get(str(effective_caster_level), []) if isinstance(canonical_table, dict) else []
            result["spell_slots"] = self._slots_payload_to_dict(level_slots)

        if result["pact_magic_slots"]:
            result["notes"].append(
                "Pact Magic slots are tracked separately from standard multiclass spell slots."
            )

        return result

    def _get_multiclass_hp_breakdown(
        self,
        class_rows: List[Dict[str, Any]],
        constitution_score: int,
        feature_bonuses: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute deterministic HP for multiclass builds.

        Rule for this phase:
        - first class gets max hit die at level 1,
        - all remaining levels use average hit die for each class row,
        - Constitution modifier and per-level hp bonuses use total level.
        """
        if not class_rows:
            return self.hp_calculator.get_hp_breakdown(
                self.character_data.get("class", ""),
                constitution_score,
                feature_bonuses,
                self.character_data.get("level", 1),
            )

        con_modifier = (constitution_score - 10) // 2
        total_level = sum(max(1, int(row.get("level", 1))) for row in class_rows)

        primary_row = class_rows[0]
        primary_hit_die = self.hp_calculator.CLASS_HIT_DICE.get(primary_row["class_name"], 6)
        base_hp = primary_hit_die
        breakdown_parts = [
            f"Level 1 ({primary_row['class_name']}): {primary_hit_die} (max d{primary_hit_die})"
        ]

        for idx, row in enumerate(class_rows):
            class_name = row["class_name"]
            class_level = max(1, int(row.get("level", 1)))
            hit_die = self.hp_calculator.CLASS_HIT_DICE.get(class_name, 6)
            avg_hit_die = (hit_die // 2) + 1

            extra_levels = class_level - 1 if idx == 0 else class_level
            if extra_levels > 0:
                extra_hp = avg_hit_die * extra_levels
                base_hp += extra_hp
                if idx == 0:
                    breakdown_parts.append(
                        f"{class_name} levels 2-{class_level}: {extra_hp} (avg d{hit_die})"
                    )
                else:
                    breakdown_parts.append(
                        f"{class_name} levels 1-{class_level}: {extra_hp} (avg d{hit_die})"
                    )

        constitution_bonus = con_modifier * total_level

        # Compute feature HP bonus. For per-level bonuses originating from a
        # class or subclass feature, scale by THAT class's level (not total
        # character level). Non-class sources (species/background/feat) keep
        # using total level. Branch on data fields only, never on names.
        class_level_by_name = {
            row["class_name"]: max(1, int(row.get("level", 1)))
            for row in class_rows
        }

        feature_bonus = 0
        feature_breakdown = []
        for hp_bonus in feature_bonuses:
            source = hp_bonus.get("source", "Unknown")
            value = hp_bonus.get("value", 0)
            scaling = hp_bonus.get("scaling")
            src_type = hp_bonus.get("source_type")
            src_class = hp_bonus.get("source_class_name")

            if scaling == "per_level":
                if src_type in ("class", "subclass") and src_class in class_level_by_name:
                    scale_level = class_level_by_name[src_class]
                else:
                    scale_level = total_level
                total_bonus = value * scale_level
                feature_bonus += total_bonus
                feature_breakdown.append(
                    f"{source}: +{value} per level (+{total_bonus} total)"
                )
            else:
                feature_bonus += value
                feature_breakdown.append(f"{source}: +{value}")

        total_hp = base_hp + constitution_bonus + feature_bonus

        return {
            "base_hp": base_hp,
            "base_hp_breakdown": " + ".join(breakdown_parts),
            "class_name": primary_row["class_name"],
            "hit_die": primary_hit_die,
            "level": total_level,
            "constitution_score": constitution_score,
            "constitution_modifier": con_modifier,
            "constitution_bonus": constitution_bonus,
            "feature_bonus": feature_bonus,
            "feature_breakdown": feature_breakdown,
            "total_hp": total_hp,
        }

    def _clear_species_choice_effects_for_trait(self, trait_name: str) -> None:
        """Remove effects previously applied for a species/lineage trait choice.

        When a user re-selects a different option for a species trait (e.g.,
        choosing Perception instead of Insight for Keen Senses), this method
        undoes the mechanical impact of the old choice before the new one is
        applied.
        """
        if not hasattr(self, "applied_effects"):
            return

        species_name = self.character_data.get("species", "")
        trait_prefix = f"{trait_name}:"
        old_effects = [
            e for e in self.applied_effects
            if e.get("source_type") == "species_choice"
            and isinstance(e.get("source"), str)
            and e["source"].startswith(trait_prefix)
        ]

        for effect in old_effects:
            etype = effect.get("type", "")
            effect_data = effect.get("effect", {})

            if etype == "grant_skill_proficiency":
                for skill in effect_data.get("skills", []):
                    src = self.character_data["proficiency_sources"]["skills"].get(skill)
                    if src == species_name:
                        self.character_data["proficiencies"]["skills"] = [
                            s for s in self.character_data["proficiencies"]["skills"] if s != skill
                        ]
                        self.character_data["proficiency_sources"]["skills"].pop(skill, None)

            elif etype == "grant_tool_proficiency":
                for tool in effect_data.get("tools", []):
                    src = self.character_data["proficiency_sources"]["tools"].get(tool)
                    if src == species_name:
                        self.character_data["proficiencies"]["tools"] = [
                            t for t in self.character_data["proficiencies"]["tools"] if t != tool
                        ]
                        self.character_data["proficiency_sources"]["tools"].pop(tool, None)

            elif etype == "grant_weapon_proficiency":
                for prof in effect_data.get("proficiencies", []):
                    src = self.character_data["proficiency_sources"]["weapons"].get(prof)
                    if src == species_name:
                        self.character_data["proficiencies"]["weapons"] = [
                            w for w in self.character_data["proficiencies"]["weapons"] if w != prof
                        ]
                        self.character_data["proficiency_sources"]["weapons"].pop(prof, None)

            elif etype == "grant_armor_proficiency":
                for prof in effect_data.get("proficiencies", []):
                    src = self.character_data["proficiency_sources"]["armor"].get(prof)
                    if src == species_name:
                        self.character_data["proficiencies"]["armor"] = [
                            a for a in self.character_data["proficiencies"]["armor"] if a != prof
                        ]
                        self.character_data["proficiency_sources"]["armor"].pop(prof, None)

        # Remove the old effects from applied_effects (and rebuild structured fields)
        self._filter_applied_effects(
            lambda e: (
                e.get("source_type") == "species_choice"
                and isinstance(e.get("source"), str)
                and e["source"].startswith(trait_prefix)
            )
        )

    def _apply_species_choice_effects(
        self, choice_key: str, choice_value: Any, source_data: Dict[str, Any]
    ):
        """
        Look up and apply effects from a choice made in species/lineage traits.

        Args:
            choice_key: The choice identifier (e.g., 'Keen Senses', 'Elven Lineage')
            choice_value: The chosen value (e.g., 'Insight', 'Intelligence')
            source_data: Species or lineage data to search for effects
        """
        if not isinstance(source_data, dict):
            print(
                f"WARNING: _apply_species_choice_effects received non-dict source_data: {type(source_data)}"
            )
            return

        # Clear old effects from a previous choice for this same trait
        self._clear_species_choice_effects_for_trait(choice_key)

        # Look for traits with choice_effects
        traits = source_data.get("traits", {})
        if not isinstance(traits, dict):
            print(f"WARNING: traits is not a dict: {type(traits)}")
            return

        for trait_name, trait_data in traits.items():
            # Check if this trait matches the choice key and has choice_effects or is an origin feat choice
            if (
                trait_name == choice_key
                and isinstance(trait_data, dict)
            ):
                choice_effects = trait_data.get("choice_effects", {})
                if choice_value in choice_effects:
                    effects = choice_effects[choice_value]
                    # Apply each effect
                    for effect in effects:
                        self._apply_effect(
                            effect, f"{trait_name}: {choice_value}", "species_choice"
                        )
                    return
                elif (
                    trait_name == "Versatile"
                    or trait_data.get("choices", {}).get("source", {}).get("list") == "origin_feats"
                ):
                    self._apply_effect(
                        {"type": "grant_origin_feat", "feat": choice_value},
                        f"{trait_name}: {choice_value}",
                        "species_choice",
                    )
                    return

    def _trait_choice_names_for(
        self, species_name: Optional[str], lineage_name: Optional[str] = None
    ) -> set:
        """
        Return the set of trait names that present a player choice for the
        given species (and optionally its lineage). Used by the
        ``species_trait_choices`` normalizer to decide which flat top-level
        keys in ``choices_made`` should be lifted into the nested object.
        """
        names: set = set()
        if not species_name:
            return names
        species_data = self._load_species_data(species_name) or {}
        for trait_name, trait_data in species_data.get("traits", {}).items():
            if isinstance(trait_data, dict) and trait_data.get("type") == "choice":
                names.add(trait_name)
        if lineage_name:
            lineage_data = (
                self._load_lineage_data(species_name, lineage_name) or {}
            )
            for trait_name, trait_data in lineage_data.get("traits", {}).items():
                if isinstance(trait_data, dict) and trait_data.get("type") == "choice":
                    names.add(trait_name)
        return names

    def _normalize_species_trait_choices(
        self,
        choices: Dict[str, Any],
        species_name: Optional[str] = None,
        lineage_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Lift legacy flat top-level trait keys in ``choices`` into the nested
        ``choices["species_trait_choices"]`` object (audit P0-1).

        Idempotent — calling twice has no further effect. Only keys that match
        a known trait choice name on the loaded species/lineage are lifted;
        unrelated top-level keys are left alone.

        When both a flat key and a nested entry exist for the same trait, the
        existing nested entry wins (keep the canonical value, drop the flat
        duplicate).
        """
        if not isinstance(choices, dict):
            return choices

        resolved_species = species_name or choices.get("species") or self.character_data.get("species")
        resolved_lineage = lineage_name or choices.get("lineage") or self.character_data.get("lineage")
        trait_names = self._trait_choice_names_for(resolved_species, resolved_lineage)
        if not trait_names:
            # Nothing to normalize against.
            return choices

        nested = choices.get("species_trait_choices")
        if not isinstance(nested, dict):
            nested = {}

        for trait_name in trait_names:
            # Lift the canonical flat form: choices["Draconic Ancestry"].
            if trait_name in choices:
                if trait_name not in nested:
                    nested[trait_name] = choices[trait_name]
                # Drop the flat duplicate either way — nested is canonical.
                choices.pop(trait_name, None)
            # Lift the legacy prefixed forms that _resolve_choice_value
            # would otherwise hit through its fallback variants. Phase 5
            # makes any such fallback hit fail loud in strict mode; the
            # normalizer lifting them up-front keeps legacy payloads
            # round-tripping cleanly without weakening the strict check.
            for legacy_key in (
                f"species_trait_{trait_name}",
                trait_name.lower().replace(" ", "_"),
                f"species_trait_{trait_name.lower().replace(' ', '_')}",
            ):
                if legacy_key in choices:
                    if trait_name not in nested:
                        nested[trait_name] = choices[legacy_key]
                    choices.pop(legacy_key, None)

        if nested:
            choices["species_trait_choices"] = nested
        return choices

    def apply_choices(self, choices: Dict[str, Any], *, fail_on_error: bool = False) -> bool:
        """
        Apply multiple choices at once from a choices dictionary.
        This is useful for batch operations like rebuilding from saved choices.

        Args:
            choices: Dictionary of choice_key -> choice_value pairs

        Returns:
            True if all choices were applied successfully
        """
        # Ensure choices is a dict
        if not isinstance(choices, dict):
            print(f"Error: apply_choices received non-dict type: {type(choices)}")
            print(f"Choices value: {choices}")
            return False

        prev_fail_on_error = getattr(self, "_fail_on_error", None)
        self._fail_on_error = fail_on_error
        try:
            return self._apply_choices_internal(choices, fail_on_error=fail_on_error)
        finally:
            self._fail_on_error = prev_fail_on_error

    def _apply_choices_internal(self, choices: Dict[str, Any], *, fail_on_error: bool = False) -> bool:
        working_choices = dict(choices)

        # Normalize singular/plural key aliases at builder level so test
        # fixtures and direct API callers that use the singular form work
        # without going through the API normalization layer.
        if "background_skill_replacement" in working_choices and "background_skill_replacements" not in working_choices:
            working_choices["background_skill_replacements"] = working_choices.pop("background_skill_replacement")
        elif "background_skill_replacement" in working_choices:
            working_choices.pop("background_skill_replacement")

        if "species_skill_replacement" in working_choices and "species_skill_replacements" not in working_choices:
            working_choices["species_skill_replacements"] = working_choices.pop("species_skill_replacement")
        elif "species_skill_replacement" in working_choices:
            working_choices.pop("species_skill_replacement")

        class_rows = self._normalize_multiclass_rows(working_choices.get("classes"))
        if class_rows:
            primary = class_rows[0]
            # Keep legacy keys available so existing logic remains compatible.
            working_choices["class"] = primary["class_name"]
            working_choices["level"] = primary["level"]
            if primary.get("subclass"):
                working_choices["subclass"] = primary["subclass"]

        # Apply choices in a specific order for dependencies
        order = [
            "active_sources",
            "character_name",
            "name",
            "level",
            "species",
            "lineage",
            "lineage_spellcasting_ability",  # Must come after lineage is applied
            "class",
            "subclass",
            # Class skill choices must come before background so overlap can be detected
            "skill_choices",
            "skills",
            "background",
            "background_skill_replacements",  # Must come after background is applied
            # Ability scores: only apply method if no explicit scores provided
            "ability_scores_method",  # This might apply standard array
            "ability_scores",
            "abilities",  # This overrides if present
            # Background bonuses must come after base ability scores
            "background_ability_score_assignment",
            "background_bonuses_method",
            "background_bonuses",
            "additional_ability_modifiers",
            "tool_choices",
            "tools",
            "spellcasting",
            "spell_selections",  # Restore spell selections after class/subclass applied
            "weapon mastery",
            "weapon_mastery_selections",  # Restore mastery selections after class applied
            "eldritch_invocation_selections",  # Restore invocation selections after class applied
            "artificer_replicate_plans",  # Restore artificer replicate plans after class applied
            "artificer_active_replications",  # Restore active replications after class applied
            "artificer_replications",  # Composite plans + active if provided
            "primal_knowledge_skill",
            "primal_lore_skill",
            "aspect_of_the_wilds",
            "subclass_aspect_of_the_wilds",
            "alignment",
            "inventory",
        ]

        # Special handling: if both ability_scores and ability_scores_method exist,
        # skip ability_scores_method since ability_scores is the final value
        apply_method = (
            "ability_scores_method" in working_choices
            and "ability_scores" not in working_choices
            and "abilities" not in working_choices
        )

        # ── Pass 1 ──────────────────────────────────────────────────────────
        # Apply ordered dependency keys (species → class → background →
        # abilities → spells) to ensure prerequisite state is set before
        # dependent choices.  The ``order`` list above defines the exact
        # sequence; keys absent from ``working_choices`` are skipped silently.
        for key in order:
            if key in working_choices:
                # Skip ability_scores_method if we have explicit ability_scores
                if key == "ability_scores_method" and not apply_method:
                    # Preserve the user's selected method in choices_made for
                    # UI round-tripping/validation while avoiding method-driven
                    # score reassignment over explicit ability_scores.
                    self.character_data["choices_made"][key] = choices[key]
                    continue
                applied = self.apply_choice(key, working_choices[key])
                if fail_on_error and not applied:
                    return False

        # Invariant: species and class must be loaded before remaining choices.
        assert self.character_data.get("species") or not working_choices.get("species"), \
            "Pass 1 failed to apply species"

        # ── Normalize block ──────────────────────────────────────────────────
        # Lift legacy flat species-trait keys into ``species_trait_choices``
        # now that species (and optionally lineage) are loaded, before the
        # second pass dispatches them.  See ``_normalize_species_trait_choices``
        # (audit P0-1).
        self._normalize_species_trait_choices(working_choices)

        # ── Pass 2 ──────────────────────────────────────────────────────────
        # Apply all remaining keys (feat sub-choices, maneuver picks, etc.).
        # Parent feat-slot keys are processed before sub-keys so the
        # sub-choice handler can look up the parent.
        # Skip species_skill_replacements — it needs a late pass after trait effects.
        remaining_keys = [
            k for k in working_choices
            if k not in order and k not in ("species_skill_replacements", "classes")
        ]
        # Sort so parent feat-slot keys (class_feat_N, key=0) come before their
        # sub-choice keys (class_feat_N_*, key=1).  Python's sort is stable and
        # ascending, so 0 < 1 means parents are processed first.
        remaining_keys.sort(key=lambda k: (1 if _CLASS_FEAT_SUB_RE.match(k) else 0))
        for key in remaining_keys:
            applied = self.apply_choice(key, working_choices[key])
            if fail_on_error and not applied:
                return False

        # ── Multiclass block ─────────────────────────────────────────────────
        # Apply additional class tracks and recalculate totals.  Runs after
        # single-class setup so extra tracks don't break existing flows.
        if class_rows:
            self.character_data["class_breakdown"] = deepcopy(class_rows)
            self.character_data["choices_made"]["classes"] = deepcopy(class_rows)
            self._apply_additional_multiclass_tracks(class_rows)

            total_level = sum(row["level"] for row in class_rows)
            self.character_data["level"] = total_level
            self.character_data["choices_made"]["class"] = class_rows[0]["class_name"]
            self.character_data["choices_made"]["level"] = total_level
            if class_rows[0].get("subclass"):
                self.character_data["choices_made"]["subclass"] = class_rows[0]["subclass"]

        # Invariant: level must be set after class application, which implies
        # calculate_proficiency_bonus() will return > 0.  The full
        # proficiency_bonus key is only materialised in to_character(), so we
        # check the level field as the proxy here.
        if working_choices.get("class") or class_rows:
            assert self.character_data.get("level", 0) > 0, \
                "Level not set after class application (proficiency_bonus will be 0)"

        # ── Pass 3 ──────────────────────────────────────────────────────────
        # Apply species_skill_replacements after trait effects so overlap
        # detection sees the full proficiency picture.
        if "species_skill_replacements" in choices:
            applied = self.apply_choice(
                "species_skill_replacements", choices["species_skill_replacements"]
            )
            if fail_on_error and not applied:
                return False

        # ── Finalize ────────────────────────────────────────────────────────
        # Apply pending dynamic effects (e.g. damage_type_from_choice
        # resolutions that need choices_made to be fully populated), then run
        # strict-mode validation on the final choices_made dict.
        self._apply_pending_dynamic_effects()

        # Final canonicalization: lift any flat species trait keys recorded in
        # ``choices_made`` (e.g. as a side effect of dispatching a nested
        # ``species_trait_choices`` payload through ``apply_choice``) into the
        # nested object. Idempotent. See audit P0-1.
        self._normalize_species_trait_choices(self.character_data["choices_made"])

        # Phase 5 (audit P2-6): in strict mode, raise on unknown top-level
        # choice keys. Allowed keys = the static allowlist + dynamic regex set
        # + feature/choice names enumerated from currently-loaded data
        # (class/subclass/species/lineage/background).
        strict_mode.check_choices_made_keys(
            self.character_data["choices_made"], self.character_data
        )

        return True

    def _apply_pending_dynamic_effects(self):
        """
        Re-scan species/lineage trait effects that use dynamic choice references
        (e.g., damage_type_from_choice) and apply them now that choices_made is
        fully populated. Safe to call multiple times — effects guard against duplicates.
        """
        for data_key in ("species_data", "lineage_data"):
            source_data = self.character_data.get(data_key)
            if not isinstance(source_data, dict):
                continue
            for trait_name, trait_data in source_data.get("traits", {}).items():
                if not isinstance(trait_data, dict):
                    continue
                for effect in trait_data.get("effects", []):
                    if "damage_type_from_choice" in effect:
                        self._apply_effect(effect, trait_name, data_key.replace("_data", ""))

        # Re-apply class and subclass effects whose payload comes from a later
        # feature choice. Class features are initially walked before the second
        # pass of apply_choices, so this is the generic deferred resolution
        # point for all ``from_choice`` effects.
        for data_key, source_type in (
            ("class_data", "class"),
            ("subclass_data", "subclass"),
        ):
            class_data = self.character_data.get(data_key)
            if not isinstance(class_data, dict):
                continue
            level = self.character_data.get("level", 1)
            for level_str, level_features in class_data.get("features_by_level", {}).items():
                if not isinstance(level_features, dict):
                    continue
                if int(level_str) > level:
                    continue
                for feature_name, feature_data in level_features.items():
                    if not isinstance(feature_data, dict):
                        continue
                    for effect in feature_data.get("effects", []):
                        if isinstance(effect, dict) and "from_choice" in effect:
                            self._apply_effect(effect, feature_name, source_type)

    # ==================== Calculation Methods ====================

    def calculate_ability_modifier(self, score: int) -> int:
        """Calculate ability modifier from score."""
        return math.floor((score - 10) / 2)

    def calculate_proficiency_bonus(self, level: int) -> int:
        """Calculate proficiency bonus based on character level."""
        if level >= 17:
            return 6
        elif level >= 13:
            return 5
        elif level >= 9:
            return 4
        elif level >= 5:
            return 3
        else:
            return 2

    def _get_class_spell_list(self, class_name: str) -> Dict[str, Any]:
        """Get the merged spell list for a class, incorporating active supplements."""
        if not class_name:
            return {}
        c_lower = class_name.lower()
        active_sources = (
            self.character_data.get("active_sources")
            or self.character_data.get("choices_made", {}).get("active_sources")
        )
        if hasattr(self, "data_loader") and self.data_loader:
            data = self.data_loader.get_class_spells(c_lower, active_sources)
            if data:
                return data
        spell_file = self._content_file_path("spells/class_lists", c_lower)
        if spell_file is not None and spell_file.exists():
            loaded = self._load_json_file(spell_file)
            if isinstance(loaded, dict):
                return loaded
        return {}

    def calculate_spellcasting_stats(self) -> Dict[str, Any]:
        """
        Calculate spellcasting statistics for spellcasting classes.

        Returns:
            Dictionary with spellcasting ability, save DC, attack bonus, and spell counts
        """
        stats = {
            "has_spellcasting": False,
            "spellcasting_ability": None,
            "spellcasting_modifier": 0,
            "spell_save_dc": 0,
            "spell_attack_bonus": 0,
            "spellcasting_type": None,
            "preparation_formula": None,
            "ritual_casting": False,
            "effective_caster_level": 0,
            "pact_magic_slots": [],
            "multiclass_notes": [],
            # Cantrip tracking
            "cantrips_always_prepared": 0,
            "cantrips_to_prepare": 0,
            "max_cantrips_prepared": 0,
            # Spell tracking
            "spells_always_prepared": 0,
            "spells_prepared": 0,
            "max_spells_prepared": 0,
            # Background spells
            "background_cantrips_needed": 0,
            "background_cantrips_list": None,
            "background_spells_needed": 0,
            "background_spells_list": None,
            "background_spell_level": 1,
            # Available spells
            "available_cantrips": [],
            "available_spells": {},
        }

        # Get class data from character_data (already loaded)
        class_name = self.character_data.get("class")
        if not class_name:
            return stats

        class_data = self.character_data.get("class_data")
        if not class_data:
            # Try to load it if not available
            class_data = self._load_class_data(class_name)
            if not class_data:
                return stats

        multiclass_spellcasting = self._calculate_multiclass_spell_slot_progression()
        stats["effective_caster_level"] = multiclass_spellcasting.get("effective_caster_level", 0)
        stats["pact_magic_slots"] = multiclass_spellcasting.get("pact_magic_slots", [])
        stats["multiclass_notes"] = multiclass_spellcasting.get("notes", [])

        # Check if class has spellcasting
        spellcasting_ability = class_data.get("spellcasting_ability")
        subclass_data = None
        spellcasting_source = class_data  # Track which data source provides spellcasting
        if not spellcasting_ability:
            # Check if subclass grants spellcasting (e.g., Eldritch Knight, Arcane Trickster)
            subclass_data = self.character_data.get("subclass_data")
            if subclass_data:
                spellcasting_ability = subclass_data.get("spellcasting_ability")
                if spellcasting_ability:
                    spellcasting_source = subclass_data
            if not spellcasting_ability and isinstance(multiclass_spellcasting.get("pact_magic_slots"), list):
                if multiclass_spellcasting["pact_magic_slots"]:
                    # Keep deterministic output for pact-only or mixed builds.
                    stats["has_spellcasting"] = True
                    return stats
            if not spellcasting_ability:
                return stats

        stats["has_spellcasting"] = True
        stats["spellcasting_ability"] = spellcasting_ability
        stats["spellcasting_type"] = spellcasting_source.get("spellcasting_type", "prepared")
        stats["preparation_formula"] = spellcasting_source.get("spell_preparation_formula")
        stats["ritual_casting"] = spellcasting_source.get("ritual_casting", False)

        # Get spellcasting modifier from abilities
        ability_key = spellcasting_ability.lower()
        abilities = self.calculate_processed_ability_scores()
        ability_data = abilities.get(ability_key, {})
        spellcasting_modifier = ability_data.get("modifier", 0)
        stats["spellcasting_modifier"] = spellcasting_modifier

        # Calculate spell save DC and attack bonus
        # Proficiency bonus is always based on total character level.
        level = self._get_primary_class_level()
        total_level = max(1, int(self.character_data.get("level", level)))
        proficiency_bonus = self.calculate_proficiency_bonus(total_level)
        stats["spell_save_dc"] = 8 + proficiency_bonus + spellcasting_modifier
        stats["spell_attack_bonus"] = proficiency_bonus + spellcasting_modifier

        # Count always prepared cantrips (from features, lineage, etc)
        always_prepared = self.character_data.get("spells", {}).get(
            "always_prepared", {}
        )
        if isinstance(always_prepared, dict):
            always_prepared_cantrips = [
                spell_name
                for spell_name, spell_data in always_prepared.items()
                if isinstance(spell_data, dict) and spell_data.get("level", 0) == 0
            ]
        else:
            always_prepared_cantrips = []
        stats["cantrips_always_prepared"] = len(always_prepared_cantrips)

        # Get max cantrips from class table (fall back to subclass for EK/AT)
        cantrip_progression = class_data.get("cantrip_progression", {})
        if not cantrip_progression and spellcasting_source is not class_data:
            cantrip_progression = spellcasting_source.get("cantrips_by_level", {})
        if isinstance(cantrip_progression, dict) and cantrip_progression:
            # Direct lookup in cantrip_progression dict
            max_cantrips_total = cantrip_progression.get(str(level), 0)
        else:
            # cantrip_progression is a string like "class_table", or empty/missing — use cantrips_by_level
            cantrips_by_level = class_data.get("cantrips_by_level", {})
            if not cantrips_by_level and spellcasting_source is not class_data:
                cantrips_by_level = spellcasting_source.get("cantrips_by_level", {})
            max_cantrips_total = cantrips_by_level.get(str(level), 0)

        # Calculate how many cantrips can be prepared (not counting always_prepared that don't count)
        always_prepared_that_count = sum(
            1
            for spell_data in always_prepared.values()
            if isinstance(spell_data, dict)
            and spell_data.get("level", 0) == 0
            and spell_data.get("counts_against_limit", True)
        )
        stats["max_cantrips_to_prepare"] = max(
            0, max_cantrips_total - always_prepared_that_count
        )
        stats["max_cantrips_prepared"] = max_cantrips_total

        # Count currently prepared cantrips
        prepared = self.character_data.get("spells", {}).get("prepared", {})
        if isinstance(prepared, dict):
            current_prepared_cantrips = list(prepared.get("cantrips", {}).keys())
        else:
            current_prepared_cantrips = []
        stats["cantrips_to_prepare"] = len(current_prepared_cantrips)

        # Count always prepared spells (from subclass, features)
        if isinstance(always_prepared, dict):
            always_prepared_spells = [
                spell_name
                for spell_name, spell_data in always_prepared.items()
                if isinstance(spell_data, dict) and spell_data.get("level", 0) > 0
            ]
        else:
            always_prepared_spells = []
        stats["spells_always_prepared"] = len(always_prepared_spells)

        # Calculate max prepared spells based on formula (fall back to subclass for EK/AT)
        prepared_by_level = class_data.get("prepared_spells_by_level", {})
        if not prepared_by_level and spellcasting_source is not class_data:
            prepared_by_level = spellcasting_source.get("prepared_spells_by_level", {})
        if prepared_by_level:
            # Use class table
            max_spells_total = prepared_by_level.get(str(level), 0)
        elif stats["preparation_formula"]:
            # Use formula (e.g., "level + wisdom_modifier")
            formula = stats["preparation_formula"]
            if "level" in formula and "modifier" in formula:
                max_spells_total = max(1, level + spellcasting_modifier)
        else:
            max_spells_total = 0

        # Calculate how many spells can be prepared (not counting always_prepared that don't count)
        always_prepared_spells_that_count = sum(
            1
            for spell_data in always_prepared.values()
            if isinstance(spell_data, dict)
            and spell_data.get("level", 0) > 0
            and spell_data.get("counts_against_limit", True)
        )
        stats["max_spells_to_prepare"] = max(
            0, max_spells_total - always_prepared_spells_that_count
        )
        stats["max_spells_prepared"] = max_spells_total

        # Count currently prepared spells
        if isinstance(prepared, dict):
            current_prepared_spells = list(prepared.get("spells", {}).keys())
        else:
            current_prepared_spells = []
        stats["spells_prepared"] = len(current_prepared_spells)

        # Add template-friendly field names for display
        # Total cantrips known = always prepared + user selected
        stats["cantrips_known"] = (
            stats["cantrips_always_prepared"] + stats["cantrips_to_prepare"]
        )
        # Max cantrips = base slots + bonus cantrips that don't count against limit
        bonus_cantrips = stats["cantrips_always_prepared"] - always_prepared_that_count
        stats["max_cantrips"] = stats["max_cantrips_prepared"] + bonus_cantrips
        # Total spells prepared = always prepared + user selected
        total_spells_prepared = (
            stats["spells_always_prepared"] + stats["spells_prepared"]
        )
        stats["spells_prepared"] = total_spells_prepared  # Override with total
        # Max spells = base slots + bonus spells that don't count against limit
        bonus_spells = (
            stats["spells_always_prepared"] - always_prepared_spells_that_count
        )
        stats["max_prepared_spells"] = stats["max_spells_prepared"] + bonus_spells

        # Check for background spell requirements (e.g., Magic Initiate)
        background_data = self.character_data.get("background_data") or {}
        feat = self._background_feat_name(background_data)
        if feat and "Magic Initiate" in feat:
            # Extract spell list from feat name
            import re

            match = re.search(r"Magic Initiate \((\w+)\)", feat)
            if match:
                spell_list_class = match.group(1)
                stats["background_cantrips_needed"] = 2
                stats["background_cantrips_list"] = spell_list_class
                stats["background_spells_needed"] = 1
                stats["background_spells_list"] = spell_list_class
                stats["background_spell_level"] = 1

        # Load available spell lists for this class (or subclass spell_list for EK/AT)
        spell_list_name = class_name.lower()
        if spellcasting_source is not class_data:
            spell_list_override = spellcasting_source.get("spell_list")
            if spell_list_override:
                spell_list_name = spell_list_override.lower()
        spell_list_data = self._get_class_spell_list(spell_list_name)
        if spell_list_data:
            try:
                # Get available cantrips
                available_cantrips = spell_list_data.get("cantrips", [])
                stats["available_cantrips"] = sorted(available_cantrips)

                # Get available spells by level, capped at the character's max accessible level.
                # For pact magic (Warlock), max level = pact slot level from table.
                # For standard casters, max level = highest level with a non-zero slot.
                max_accessible_level = 9  # default: show all
                pact_slots = multiclass_spellcasting.get("pact_magic_slots", [])
                if pact_slots:
                    # Single-class or multiclass Warlock: cap at highest pact slot level
                    max_accessible_level = max(
                        (entry.get("slot_level", 0) for entry in pact_slots), default=0
                    )
                else:
                    slots_table = spellcasting_source.get("spell_slots_by_level", {})
                    if isinstance(slots_table, dict):
                        level_slots = slots_table.get(str(level), [])
                        if isinstance(level_slots, list):
                            # slots list is indexed 0=lvl1, 1=lvl2, ...; find highest non-zero
                            for idx in range(len(level_slots) - 1, -1, -1):
                                try:
                                    if int(level_slots[idx]) > 0:
                                        max_accessible_level = idx + 1
                                        break
                                except (TypeError, ValueError):
                                    pass

                spells_by_level = spell_list_data.get("spells_by_level", {})
                stats["available_spells"] = {
                    int(k): sorted(v)
                    for k, v in spells_by_level.items()
                    if int(k) <= max_accessible_level
                }

            except Exception as e:
                print(f"Warning: Could not process spell list for {class_name}: {e}")

        return stats

    def calculate_weapon_mastery_stats(self) -> Dict[str, Any]:
        """
        Calculate weapon mastery statistics for classes with weapon mastery.

        Returns:
            Dictionary with available weapons, max masteries, and current selections
        """
        stats = {
            "has_mastery": False,
            "available_weapons": [],
            "max_masteries": 0,
            "current_masteries": [],
        }

        # Get class data
        class_name = self.character_data.get("class")
        if not class_name:
            return stats

        class_data = self.character_data.get("class_data")
        if not class_data:
            class_data = self._load_class_data(class_name)
            if not class_data:
                return stats

        # Check if class has masterable_weapons
        masterable_weapons = class_data.get("masterable_weapons", [])
        if not masterable_weapons:
            return stats

        stats["has_mastery"] = True
        stats["available_weapons"] = sorted(masterable_weapons)

        # Get max masteries from masteries_by_level (like cantrips_by_level)
        masteries_by_level = class_data.get("masteries_by_level", {})
        level = self._get_primary_class_level()
        max_masteries = masteries_by_level.get(str(level), 0)

        stats["max_masteries"] = max_masteries

        # Get current selections
        current_masteries = self.character_data.get("weapon_masteries", {}).get(
            "selected", []
        )
        stats["current_masteries"] = current_masteries

        return stats

    @staticmethod
    def _eldritch_invocation_choice_id(
        invocation_name: str, effect_index: int
    ) -> str:
        """Return the stable id for an invocation effect's cantrip picker."""
        invocation_id = re.sub(r"[^a-z0-9]+", "_", invocation_name.lower()).strip("_")
        return f"eldritch_invocation_{invocation_id}_{effect_index}"

    def _load_eldritch_invocations(self) -> Dict[str, Any]:
        """Load the invocation data set, returning an empty map on cache errors."""
        try:
            from modules.supplement_manager import get_supplement_manager
            mgr = get_supplement_manager()
            return mgr.get_eldritch_invocations(getattr(self, "active_sources", None))
        except Exception:
            path = self.data_dir / "eldritch_invocations.json"
            if not path.exists():
                return {}
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, dict) else {}
            except (OSError, json.JSONDecodeError):
                return {}

    def _normalize_eldritch_invocation_selections(
        self, value: Any
    ) -> Optional[Dict[str, Any]]:
        """Accept legacy invocation lists and normalize to the canonical object."""
        if isinstance(value, list):
            selected, cantrip_choices, choices = value, {}, {}
        elif isinstance(value, dict):
            selected = value.get("selected", [])
            cantrip_choices = value.get("cantrip_choices", {})
            choices = value.get("choices", {})
        else:
            return None

        if not isinstance(selected, list) or not all(
            isinstance(name, str) for name in selected
        ):
            return None
        if not isinstance(cantrip_choices, dict) or not isinstance(choices, dict):
            return None

        normalized_choices: Dict[str, List[str]] = {}
        for choice_id, spells in cantrip_choices.items():
            if not isinstance(choice_id, str) or not isinstance(spells, list):
                return None
            if not all(isinstance(spell, str) for spell in spells):
                return None
            normalized_choices[choice_id] = spells
        return {
            "selected": selected,
            "cantrip_choices": normalized_choices,
            "choices": choices,
        }

    def _eldritch_invocation_cantrip_choice_descriptors(
        self,
        invocation_names: List[str],
        cantrip_choices: Dict[str, List[str]],
        all_invocations: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Build data-driven cantrip pickers for selected invocation effects."""
        all_invocations = (
            all_invocations
            if all_invocations is not None
            else self._load_eldritch_invocations()
        )
        descriptors: List[Dict[str, Any]] = []
        for invocation_name in invocation_names:
            invocation = all_invocations.get(invocation_name)
            if not isinstance(invocation, dict):
                continue
            effects = invocation.get("effects", [])
            if not isinstance(effects, list):
                continue
            for effect_index, effect in enumerate(effects):
                if not isinstance(effect, dict) or effect.get("type") != "grant_cantrip_choice":
                    continue
                spell_list = effect.get("spell_list")
                if not isinstance(spell_list, str):
                    continue
                spell_list_data = self._get_class_spell_list(spell_list)
                options = spell_list_data.get("cantrips", [])
                if not isinstance(options, list):
                    options = []
                choice_id = self._eldritch_invocation_choice_id(
                    invocation_name, effect_index
                )
                try:
                    count = int(effect.get("count", 1))
                except (TypeError, ValueError):
                    count = 0
                descriptors.append(
                    {
                        "id": choice_id,
                        "invocation": invocation_name,
                        "count": max(0, count),
                        "spell_list": spell_list,
                        "options": options,
                        "selected": cantrip_choices.get(choice_id, []),
                    }
                )
        return descriptors

    def _validate_eldritch_invocation_cantrip_choices(
        self, invocation_selections: Dict[str, Any]
    ) -> bool:
        """Ensure invocation cantrip picks use their effect's class list and cap."""
        selected = invocation_selections["selected"]
        cantrip_choices = invocation_selections["cantrip_choices"]
        descriptors = self._eldritch_invocation_cantrip_choice_descriptors(
            selected, cantrip_choices
        )
        descriptors_by_id = {descriptor["id"]: descriptor for descriptor in descriptors}
        if any(choice_id not in descriptors_by_id for choice_id in cantrip_choices):
            return False
        for descriptor in descriptors:
            choices = descriptor["selected"]
            if (
                len(choices) > descriptor["count"]
                or len(choices) != len(set(choices))
                or any(choice not in descriptor["options"] for choice in choices)
            ):
                return False
        return True

    def _apply_eldritch_invocation_effects(
        self,
        invocation_names: List[str],
        cantrip_choices: Optional[Dict[str, List[str]]] = None,
        invocation_choices: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """Phase 7 (D0-1): apply sheet-affecting invocation effects.

        Each chosen invocation may carry an ``effects`` array in
        ``data/eldritch_invocations.json``. We funnel each effect through
        the single dispatcher ``_apply_effect`` so the invocation pathway
        joins the One Dispatcher Rule (see
        ``.github/instructions/effects-system.instructions.md``).

        Invocations with no ``effects`` array (play-time-only mechanics
        such as Eldritch Smite's pact-slot damage rider or Pact of the
        Chain's familiar attack) are silently skipped — that
        classification is intentional per the audit's scope rule.
        """
        if not invocation_names:
            return
        cantrip_choices = cantrip_choices or {}
        all_invocations = self._load_eldritch_invocations()
        invocation_choices = invocation_choices or {}
        for name in invocation_names:
            inv = all_invocations.get(name) or {}
            effects = inv.get("effects") or []
            if not isinstance(effects, list):
                continue

            resolved_choices: Dict[str, Any] = {}
            selected_choice_values = invocation_choices.get(name, {})
            if not isinstance(selected_choice_values, dict):
                selected_choice_values = {}
            for choice in inv.get("choices", []):
                if not isinstance(choice, dict):
                    continue
                choice_name = choice.get("name")
                selected_value = selected_choice_values.get(choice_name)
                if not isinstance(choice_name, str) or selected_value is None:
                    continue
                selected_values = (
                    selected_value if isinstance(selected_value, list) else [selected_value]
                )
                options = resolve_choice_options(choice, self.character_data)
                count = choice.get("count", 1)
                if (
                    len(selected_values) == count
                    and all(value in options for value in selected_values)
                ):
                    resolved_choices[choice_name] = selected_value

            for effect_index, effect in enumerate(effects):
                if isinstance(effect, dict):
                    resolved_effect = dict(effect)
                    choice_name = resolved_effect.get("from_choice")
                    choice_field = resolved_effect.get("choice_field")
                    if choice_name and choice_field:
                        selected_value = resolved_choices.get(choice_name)
                        if isinstance(selected_value, list):
                            if len(selected_value) != 1:
                                continue
                            selected_value = selected_value[0]
                        if not isinstance(selected_value, str):
                            continue
                        resolved_effect[choice_field] = selected_value
                    self._apply_effect(resolved_effect, name, "invocation")
                    if effect.get("type") == "grant_cantrip_choice":
                        choice_id = self._eldritch_invocation_choice_id(
                            name, effect_index
                        )
                        for spell_name in cantrip_choices.get(choice_id, []):
                            self._apply_effect(
                                {
                                    "type": "grant_cantrip",
                                    "spell": spell_name,
                                    "counts_against_limit": effect.get(
                                        "counts_against_limit", False
                                    ),
                                },
                                name,
                                "invocation",
                            )

    def _clear_eldritch_invocation_effects(self) -> None:
        """Clear previously applied eldritch invocation effects, cantrips, and granted feats."""
        feats_to_remove = []
        for feat in self.character_data.get("features", {}).get("feats", []):
            if feat.get("source") == "Lessons of the First Ones" or feat.get("source_type") == "invocation":
                feat_name = feat.get("name")
                if feat_name:
                    feats_to_remove.append(feat_name)

        for feat_name in feats_to_remove:
            self._clear_feat_choices(feat_name)

        if "features" in self.character_data and "feats" in self.character_data["features"]:
            self.character_data["features"]["feats"] = [
                f for f in self.character_data["features"]["feats"]
                if f.get("name") not in feats_to_remove
            ]

        # Clear spells/cantrips with source_type == "invocation"
        for spell_name in list(self.character_data.get("spells", {}).get("always_prepared", {}).keys()):
            meta = self.character_data.get("spell_metadata", {}).get(spell_name, {})
            if meta.get("source_type") == "invocation":
                self.character_data["spells"]["always_prepared"].pop(spell_name, None)
                self.character_data["spell_metadata"].pop(spell_name, None)

        if hasattr(self, "applied_effects"):
            self.applied_effects = [
                e for e in self.applied_effects
                if e.get("source_type") != "invocation"
            ]

    def get_dependent_invocations(
        self, invocation_name: str, current_invocations: Optional[List[str]] = None
    ) -> List[str]:
        """Return names of any currently selected invocations that require `invocation_name` as a prerequisite."""
        if current_invocations is None:
            inv_sels = self.character_data.get("eldritch_invocations", {})
            if isinstance(inv_sels, list):
                current_invocations = inv_sels
            elif isinstance(inv_sels, dict):
                current_invocations = inv_sels.get("selected", [])
            else:
                current_invocations = []
        all_invocations = self._load_eldritch_invocations()
        dependents = []
        for name in current_invocations:
            if name == invocation_name:
                continue
            inv_data = all_invocations.get(name) or {}
            prereqs = inv_data.get("prerequisite_invocations", [])
            if invocation_name in prereqs:
                dependents.append(name)
        return dependents

    def calculate_eldritch_invocation_stats(self) -> Dict[str, Any]:
        """
        Calculate Eldritch Invocation statistics for Warlock characters.

        Returns:
            Dictionary with available invocations, max count, and current selections
        """
        stats: Dict[str, Any] = {
            "has_invocations": False,
            "max_invocations": 0,
            "current_invocations": [],
            "available_invocations": [],
        }

        warlock_level = self._get_class_level("Warlock")
        if warlock_level <= 0:
            return stats

        class_data = self.character_data.get("class_data")
        if not class_data or self.character_data.get("class") != "Warlock":
            class_data = self._load_class_data("Warlock")
            if not class_data:
                return stats

        invocations_by_level = class_data.get("invocations_by_level", {})
        max_invocations = invocations_by_level.get(str(warlock_level), 0)

        stats["has_invocations"] = True
        stats["max_invocations"] = max_invocations
        stats["invocations"] = []
        stats["dependency_map"] = {}

        # Load all invocations from data file.
        all_invocations = self._load_eldritch_invocations()

        # Get current invocation selections
        invocation_selections = self._normalize_eldritch_invocation_selections(
            self.character_data.get("eldritch_invocations", {})
        ) or {"selected": [], "cantrip_choices": {}, "choices": {}}
        current_invocations = invocation_selections["selected"]
        stats["current_invocations"] = current_invocations
        invocation_choices = invocation_selections.get("choices", {})
        cantrip_choices = invocation_selections.get("cantrip_choices", {})
        stats["current_choices"] = invocation_choices
        stats["cantrip_choices"] = cantrip_choices

        cantrip_choice_descriptors = self._eldritch_invocation_cantrip_choice_descriptors(
            current_invocations,
            cantrip_choices,
            all_invocations,
        )
        if cantrip_choice_descriptors:
            stats["cantrip_choice_descriptors"] = cantrip_choice_descriptors

        # Build invocation_choice_descriptors for current invocations
        invocation_choice_descriptors: List[Dict[str, Any]] = []
        for name in current_invocations:
            inv_data = all_invocations.get(name) or {}
            for choice in inv_data.get("choices", []):
                if not isinstance(choice, dict):
                    continue
                choice_name = choice.get("name")
                if not choice_name:
                    continue
                options = resolve_choice_options(choice, self.character_data)
                selected_val = invocation_choices.get(name, {}).get(choice_name)

                # Check if the selected option is a feat that itself has choices
                feat_sub_choices = []
                if choice_name == "origin_feat" and isinstance(selected_val, str) and selected_val:
                    feat_data = self._load_feat_data(selected_val)
                    if isinstance(feat_data, dict):
                        for sub_c in feat_data.get("choices", []):
                            if isinstance(sub_c, dict):
                                sub_name = sub_c.get("name")
                                sub_key = f"feat_{selected_val}_{sub_name}"
                                sub_opts = resolve_choice_options(sub_c, self.character_data)
                                feat_sub_choices.append({
                                    "choice_key": sub_key,
                                    "name": sub_name,
                                    "feature_name": sub_name,
                                    "title": f"{selected_val} — {sub_c.get('description') or sub_name.replace('_', ' ').title()}",
                                    "description": sub_c.get("description", ""),
                                    "type": sub_c.get("type", "select_multiple"),
                                    "count": sub_c.get("count", 1),
                                    "options": sub_opts,
                                    "selected": self.character_data.get("choices_made", {}).get(sub_key),
                                })

                descriptor_entry: Dict[str, Any] = {
                    "id": f"invocation_{name}_{choice_name}",
                    "invocation": name,
                    "choice_name": choice_name,
                    "title": choice.get("description") or f"Choose {choice_name.replace('_', ' ').title()}",
                    "type": choice.get("type", "select_single"),
                    "count": choice.get("count", 1),
                    "options": options,
                    "selected": selected_val,
                }
                if feat_sub_choices:
                    descriptor_entry["feat_sub_choices"] = feat_sub_choices
                invocation_choice_descriptors.append(descriptor_entry)
        if invocation_choice_descriptors:
            stats["invocation_choice_descriptors"] = invocation_choice_descriptors

        # Filter available invocations based on character level and prerequisites
        available: list[Dict[str, Any]] = []
        for name, inv_data in all_invocations.items():
            min_level = inv_data.get("prerequisite_level", 1)
            if warlock_level < min_level:
                continue
            required_invocations = inv_data.get("prerequisite_invocations", [])
            if required_invocations and not all(
                req in current_invocations for req in required_invocations
            ):
                continue

            resolved_choices = []
            for choice in inv_data.get("choices", []):
                if isinstance(choice, dict):
                    c_copy = dict(choice)
                    c_copy["options"] = resolve_choice_options(choice, self.character_data)
                    resolved_choices.append(c_copy)

            inv_entry: Dict[str, Any] = {
                "name": name,
                "description": inv_data.get("description", ""),
                "notes": inv_data.get("notes", ""),
                "prerequisite_level": min_level,
                "prerequisite_invocations": required_invocations,
            }
            if resolved_choices:
                inv_entry["choices"] = resolved_choices
            available.append(inv_entry)

        stats["available_invocations"] = sorted(available, key=lambda x: (x["prerequisite_level"], x["name"]))

        # Build invocations list for display/print
        invocations_list: List[Dict[str, Any]] = []
        for name in current_invocations:
            inv_data = all_invocations.get(name) or {}
            desc = inv_data.get("description", "")
            display_name = name
            sub_choices = invocation_choices.get(name, {})
            if sub_choices:
                sub_vals = [str(v) for v in sub_choices.values() if v]
                if sub_vals:
                    display_name = f"{name} ({', '.join(sub_vals)})"
            elif name in cantrip_choices and cantrip_choices[name]:
                display_name = f"{name} ({', '.join(cantrip_choices[name])})"

            invocations_list.append({
                "name": display_name,
                "base_name": name,
                "description": desc,
                "choices": sub_choices,
            })
        stats["invocations"] = invocations_list

        # Dependency map: which current invocations depend on each invocation
        dependency_map: Dict[str, List[str]] = {}
        for name in current_invocations:
            dependents = self.get_dependent_invocations(name, current_invocations)
            if dependents:
                dependency_map[name] = dependents
        stats["dependency_map"] = dependency_map

        return stats

    def calculate_artificer_replications_stats(self) -> Dict[str, Any]:
        """
        Calculate Replicate Magic Item statistics for Artificer characters.

        Returns:
            Dictionary with available plans, max plans known, max active replications,
            known plans, and active items.
        """
        stats: Dict[str, Any] = {
            "has_replications": False,
            "artificer_level": 0,
            "subclass": "",
            "max_plans": 0,
            "max_active": 0,
            "available_plans": [],
            "known_plans": [],
            "known_plans_details": [],
            "active_items": [],
            "active_items_details": [],
        }

        artificer_level = self._get_class_level("Artificer")
        stats["artificer_level"] = artificer_level
        subclass_name = self._get_class_subclass("Artificer")
        stats["subclass"] = subclass_name

        if artificer_level < 2:
            return stats

        # Determine max plans known
        if artificer_level < 6:
            max_plans = 4
        elif artificer_level < 10:
            max_plans = 6
        elif artificer_level < 14:
            max_plans = 8
        elif artificer_level < 18:
            max_plans = 10
        else:
            max_plans = 12

        # Advanced Artifice (14th level) adds +1 known plan
        if artificer_level >= 14:
            max_plans += 1

        # Determine max active infused items
        if artificer_level < 6:
            max_active = 2
        elif artificer_level < 10:
            max_active = 3
        elif artificer_level < 14:
            max_active = 4
        elif artificer_level < 18:
            max_active = 5
        else:
            max_active = 6

        # Improved Armorer (Armorer level 9+) adds +2 active items
        if artificer_level >= 9 and "armorer" in subclass_name.lower():
            max_active += 2

        stats["has_replications"] = True
        stats["max_plans"] = max_plans
        stats["max_active"] = max_active

        # Load catalog
        all_plans = self._load_replicate_magic_item_plans()

        # Available plans for this artificer level
        available = []
        for name, plan in all_plans.items():
            req_level = int(plan.get("level", 2) or 2)
            if req_level <= artificer_level:
                item = dict(plan)
                item["name"] = name
                available.append(item)
        available.sort(key=lambda p: (int(p.get("level", 2) or 2), p["name"]))
        stats["available_plans"] = available

        # Resolve known plans
        known = (
            self.character_data.get("artificer_replicate_plans")
            or self.character_data.get("choices_made", {}).get("artificer_replicate_plans")
        )
        rep_dict = self.character_data.get("choices_made", {}).get("artificer_replications")
        if not known and isinstance(rep_dict, dict) and "plans" in rep_dict:
            known = rep_dict["plans"]

        known_plans: List[str] = []
        if isinstance(known, list):
            for p in known:
                name_str = str(p)
                if name_str in all_plans and int(all_plans[name_str].get("level", 2) or 2) <= artificer_level:
                    if name_str not in known_plans:
                        known_plans.append(name_str)
        stats["known_plans"] = known_plans[:max_plans]
        stats["known_plans_details"] = [dict(all_plans[name], name=name) for name in stats["known_plans"] if name in all_plans]

        # Resolve active items
        active = (
            self.character_data.get("artificer_active_replications")
            or self.character_data.get("choices_made", {}).get("artificer_active_replications")
        )
        if not active and isinstance(rep_dict, dict) and "active" in rep_dict:
            active = rep_dict["active"]

        active_items: List[str] = []
        if isinstance(active, list):
            for p in active:
                name_str = str(p)
                if name_str in all_plans and int(all_plans[name_str].get("level", 2) or 2) <= artificer_level:
                    if not known_plans or name_str in known_plans:
                        if name_str not in active_items:
                            active_items.append(name_str)
        stats["active_items"] = active_items[:max_active]
        stats["active_items_details"] = [dict(all_plans[name], name=name) for name in stats["active_items"] if name in all_plans]

        return stats

    def calculate_barbarian_stats(self) -> Dict[str, Any]:
        """
        Calculate Rage, Brutal Strike, and subclass statistics for Barbarian characters.

        Returns:
            Dictionary with has_rage, barbarian_level, subclass, rage_uses, rage_damage,
            brutal_strike_dice, brutal_strike_effects, subclass_resources, active_perks.
        """
        stats: Dict[str, Any] = {
            "has_rage": False,
            "barbarian_level": 0,
            "subclass": "",
            "rage_uses": 0,
            "rage_damage": 0,
            "brutal_strike_dice": None,
            "brutal_strike_effects": [],
            "subclass_resources": {},
            "active_perks": [],
        }

        barbarian_level = self._get_class_level("Barbarian")
        stats["barbarian_level"] = barbarian_level
        if barbarian_level < 1:
            return stats

        stats["has_rage"] = True
        subclass_name = self._get_class_subclass("Barbarian") or ""
        stats["subclass"] = subclass_name

        # Rage Uses (PHB 2024 Barbarian Table)
        # Level 1-2: 2, Level 3-5: 3, Level 6-11: 4, Level 12-16: 5, Level 17-19: 6, Level 20: Unlimited
        if barbarian_level >= 20:
            stats["rage_uses"] = "Unlimited"
            stats["rage_uses_numeric"] = 999
        elif barbarian_level >= 17:
            stats["rage_uses"] = 6
            stats["rage_uses_numeric"] = 6
        elif barbarian_level >= 12:
            stats["rage_uses"] = 5
            stats["rage_uses_numeric"] = 5
        elif barbarian_level >= 6:
            stats["rage_uses"] = 4
            stats["rage_uses_numeric"] = 4
        elif barbarian_level >= 3:
            stats["rage_uses"] = 3
            stats["rage_uses_numeric"] = 3
        else:
            stats["rage_uses"] = 2
            stats["rage_uses_numeric"] = 2

        # Rage Damage (PHB 2024 Barbarian Table)
        # Level 1-8: +2, Level 9-15: +3, Level 16-20: +4
        if barbarian_level >= 16:
            stats["rage_damage"] = 4
        elif barbarian_level >= 9:
            stats["rage_damage"] = 3
        else:
            stats["rage_damage"] = 2

        # Active Rage Perks / Features
        perks = [
            "Damage Resistance: Bludgeoning, Piercing, and Slashing while Raging",
            "Advantage on Strength checks and Strength saving throws while Raging",
            f"+{stats['rage_damage']} bonus damage on melee attacks using Strength while Raging",
        ]
        if barbarian_level >= 2:
            perks.append("Reckless Attack (Advantage on attack rolls using Strength; attacks against you have Advantage)")
            perks.append("Danger Sense (Advantage on Dexterity saving throws unless Incapacitated)")
        if barbarian_level >= 3:
            perks.append("Primal Knowledge (Make Acrobatics, Intimidation, Perception, Stealth, or Survival as Strength checks while Raging)")
        if barbarian_level >= 5:
            perks.append("Fast Movement (+10 ft Speed while not wearing Heavy armor)")
        if barbarian_level >= 7:
            perks.append("Feral Instinct (Advantage on Initiative rolls)")
            perks.append("Instinctive Pounce (Move up to half Speed when entering Rage)")
        if barbarian_level >= 11:
            perks.append("Relentless Rage (Con save DC 10 + 5/use to drop to 2x level HP instead of 0)")
        if barbarian_level >= 15:
            perks.append("Persistent Rage (Rage lasts 10 minutes without dropping; regain all uses on Initiative 1/Long Rest)")
        if barbarian_level >= 18:
            perks.append("Indomitable Might (Minimum total for Strength check/save equals Strength score)")
        if barbarian_level >= 20:
            perks.append("Primal Champion (+4 Strength, +4 Constitution, max 25)")
        stats["active_perks"] = perks

        # Brutal Strike (PHB 2024 Level 9+)
        if barbarian_level >= 9:
            stats["brutal_strike_dice"] = "2d10" if barbarian_level >= 17 else "1d10"
            effects = [
                "Forceful Blow (Push target 15 ft straight away and move up to half Speed toward it without OA)",
                "Hamstring Blow (Reduce target's Speed by 15 ft until start of your next turn)",
            ]
            if barbarian_level >= 13:
                effects.append("Staggering Blow (Target has Disadvantage on next saving throw and cannot make OA)")
                effects.append("Sundering Blow (Next attack roll by another creature against target gains +5 bonus)")
            if subclass_name == "Path of Unlight" and barbarian_level >= 10:
                effects.append("Radiant Infection (Target takes 1d6 Radiant/turn, sheds 10 ft bright light, DC Con save ends)")
            stats["brutal_strike_effects"] = effects
            stats["brutal_strike_options_count"] = 2 if barbarian_level >= 17 else 1

        # Subclass Resources
        choices_made = self.character_data.get("choices_made", {})
        if subclass_name == "Path of the Zealot" and barbarian_level >= 3:
            zealot_dice_count = 7 if barbarian_level >= 17 else (6 if barbarian_level >= 12 else (5 if barbarian_level >= 6 else 4))
            stats["subclass_resources"]["warrior_of_the_gods"] = {
                "name": "Warrior of the Gods",
                "pool": f"{zealot_dice_count}d12",
                "dice_count": zealot_dice_count,
                "die": "d12",
                "description": "Bonus Action healing pool for yourself. Regain all dice on Long Rest.",
            }
            stats["subclass_resources"]["divine_fury"] = {
                "name": "Divine Fury",
                "damage": f"1d6 + {barbarian_level // 2}",
                "damage_types": ["Necrotic", "Radiant"],
                "description": "First creature hit each turn with weapon/unarmed strike while Raging takes extra damage.",
            }
        elif subclass_name == "Path of the Berserker" and barbarian_level >= 3:
            stats["subclass_resources"]["frenzy"] = {
                "name": "Frenzy",
                "damage": f"{stats['rage_damage']}d6",
                "description": "Extra damage of weapon type to first target hit on turn with Strength attack while Reckless & Raging.",
            }
        elif subclass_name == "Path of the Wild Heart":
            aspect = (
                choices_made.get("aspect_of_the_wilds")
                or choices_made.get("subclass_aspect_of_the_wilds")
            )
            if barbarian_level >= 6 and aspect:
                stats["subclass_resources"]["aspect_of_the_wilds"] = {
                    "name": "Aspect of the Wilds",
                    "choice": aspect,
                    "description": (
                        "Darkvision +60 ft." if aspect == "Owl"
                        else "Climb Speed equal to your Speed." if aspect == "Panther"
                        else "Swim Speed equal to your Speed." if aspect == "Salmon"
                        else ""
                    ),
                }
        elif subclass_name == "Path of the World Tree" and barbarian_level >= 3:
            stats["subclass_resources"]["vitality_surge"] = {
                "name": "Vitality Surge",
                "temp_hp": barbarian_level,
                "description": f"Gain {barbarian_level} Temporary HP when activating Rage.",
            }
            stats["subclass_resources"]["life_giving_force"] = {
                "name": "Life-Giving Force",
                "temp_hp_dice": f"{stats['rage_damage']}d6",
                "description": f"Grant {stats['rage_damage']}d6 Temp HP to another creature within 10 ft at start of each turn while Raging.",
            }
        elif subclass_name == "Path of Lament" and barbarian_level >= 3:
            raw_con = self.ability_scores.final_scores.get("Constitution", 10)
            con_mod = self.calculate_ability_modifier(raw_con)
            stats["subclass_resources"]["banshees_wail"] = {
                "name": "Banshee's Wail",
                "uses": max(1, con_mod),
                "damage": f"{stats['rage_damage']}d12 Psychic",
                "description": "30-ft emanation, Con save DC or Psychic damage & Deafened. Regain on Long Rest or expend 1 Rage.",
            }
        elif subclass_name == "Path of Unlight" and barbarian_level >= 3:
            stats["subclass_resources"]["radiant_rage"] = {
                "name": "Radiant Rage",
                "damage": stats["rage_damage"],
                "description": f"When hit with melee attack while Raging, attacker takes {stats['rage_damage']} Radiant damage. Shed 20 ft bright light.",
            }

        return stats

    def calculate_bard_stats(self) -> Dict[str, Any]:
        """
        Calculate Bardic Inspiration, Font of Inspiration, and subclass statistics for Bard characters.

        Returns:
            Dictionary with has_bardic_inspiration, bard_level, subclass, inspiration_die,
            inspiration_uses, recharge, font_of_inspiration, countercharm, magical_secrets,
            superior_inspiration, words_of_creation, subclass_resources, active_perks.
        """
        stats: Dict[str, Any] = {
            "has_bardic_inspiration": False,
            "bard_level": 0,
            "subclass": "",
            "inspiration_die": None,
            "inspiration_uses": 0,
            "recharge": "Long Rest",
            "font_of_inspiration": False,
            "countercharm": False,
            "magical_secrets": False,
            "superior_inspiration": False,
            "words_of_creation": False,
            "subclass_resources": {},
            "active_perks": [],
        }

        bard_level = self._get_class_level("Bard")
        stats["bard_level"] = bard_level
        if bard_level < 1:
            return stats

        stats["has_bardic_inspiration"] = True
        subclass_name = self._get_class_subclass("Bard") or ""
        stats["subclass"] = subclass_name

        # Inspiration Die (PHB 2024 Bard Table)
        # Levels 1-4: d6, Levels 5-9: d8, Levels 10-14: d10, Levels 15-20: d12
        if bard_level >= 15:
            stats["inspiration_die"] = "d12"
        elif bard_level >= 10:
            stats["inspiration_die"] = "d10"
        elif bard_level >= 5:
            stats["inspiration_die"] = "d8"
        else:
            stats["inspiration_die"] = "d6"

        # Inspiration Uses = Charisma modifier (min 1)
        raw_cha = self.ability_scores.final_scores.get("Charisma", 10)
        cha_mod = self.calculate_ability_modifier(raw_cha)
        stats["inspiration_uses"] = max(1, cha_mod)

        # Recharge: Long Rest (levels 1-4); Short or Long Rest (levels 5+ via Font of Inspiration)
        if bard_level >= 5:
            stats["recharge"] = "Short or Long Rest"
            stats["font_of_inspiration"] = True
        else:
            stats["recharge"] = "Long Rest"

        if bard_level >= 7:
            stats["countercharm"] = True
        if bard_level >= 10:
            stats["magical_secrets"] = True
        if bard_level >= 18:
            stats["superior_inspiration"] = True
        if bard_level >= 20:
            stats["words_of_creation"] = True

        # Active Perks
        die = stats["inspiration_die"]
        perks = [
            f"Bardic Inspiration: Bonus Action, give {die} die to a creature within 60 ft; add to failed D20 Test within 1 hour ({stats['inspiration_uses']} uses/{stats['recharge']})",
        ]
        if bard_level >= 2:
            perks.append("Jack of All Trades: Add half Proficiency Bonus (round down) to ability checks using a skill proficiency you lack")
            perks.append("Expertise: Double Proficiency Bonus for 2 chosen skills")
        if bard_level >= 5:
            perks.append("Font of Inspiration: Regain all Bardic Inspiration uses on Short or Long Rest; can expend any spell slot to regain 1 use")
        if bard_level >= 7:
            perks.append("Countercharm: Reaction when you or a creature within 30 ft fails a save against Charmed or Frightened to reroll with Advantage")
        if bard_level >= 9:
            perks.append("Expertise: Double Proficiency Bonus for 2 additional skills")
        if bard_level >= 10:
            perks.append("Magical Secrets: Choose prepared spells from Bard, Cleric, Druid, and Wizard spell lists")
        if bard_level >= 18:
            perks.append("Superior Inspiration: Regain expended Bardic Inspiration uses until you have at least 2 when rolling Initiative")
        if bard_level >= 20:
            perks.append("Words of Creation: Power Word Heal and Power Word Kill always prepared; can target a second creature within 10 ft")
        stats["active_perks"] = perks

        # Subclass Resources
        if subclass_name == "College of Dance" and bard_level >= 3:
            stats["subclass_resources"]["dazzling_footwork"] = {
                "name": "Dazzling Footwork",
                "unarmored_ac": "10 + DEX + CHA (no armor, no shield)",
                "agile_strikes": "When expending Bardic Inspiration, make 1 Unarmed Strike as part of the action/bonus action/reaction",
                "bardic_damage": f"Unarmed Strikes can use DEX and deal 1{die} + DEX Bludgeoning damage without expending the die",
            }
            if bard_level >= 6:
                stats["subclass_resources"]["inspiring_movement"] = {
                    "name": "Inspiring Movement",
                    "description": "Reaction + 1 Bardic Inspiration use to move half Speed without OA; ally within 30 ft can also move half Speed",
                }
                stats["subclass_resources"]["tandem_footwork"] = {
                    "name": "Tandem Footwork",
                    "description": f"Expend 1 Bardic Inspiration use on Initiative: you and allies within 30 ft gain +1{die} bonus to Initiative",
                }
            if bard_level >= 14:
                stats["subclass_resources"]["leading_evasion"] = {
                    "name": "Leading Evasion",
                    "description": "Dex save half damage -> 0 on success, half on failure. Can share with creatures within 5 ft",
                }
        elif subclass_name == "College of Glamour" and bard_level >= 3:
            stats["subclass_resources"]["beguiling_magic"] = {
                "name": "Beguiling Magic",
                "description": "After casting Enchantment/Illusion spell with spell slot, target within 60 ft makes Wis save or Charmed/Frightened 1 min. 1/Long Rest or expend 1 Bardic Inspiration",
            }
            stats["subclass_resources"]["mantle_of_inspiration"] = {
                "name": "Mantle of Inspiration",
                "description": f"Bonus Action + 1 Bardic Inspiration use: up to {stats['inspiration_uses']} creatures within 60 ft gain 2x 1{die} Temp HP and reaction move Speed without OA",
            }
            if bard_level >= 6:
                stats["subclass_resources"]["mantle_of_majesty"] = {
                    "name": "Mantle of Majesty",
                    "description": "Bonus Action free cast Command, 1 min concentration, repeat BA Command each turn. 1/Long Rest or expend level 3+ slot",
                }
            if bard_level >= 14:
                stats["subclass_resources"]["unbreakable_majesty"] = {
                    "name": "Unbreakable Majesty",
                    "description": "Bonus Action 1 min majesty: first attacker each turn makes Cha save or attack misses. 1/Short or Long Rest",
                }
        elif subclass_name == "College of Lore" and bard_level >= 3:
            stats["subclass_resources"]["cutting_words"] = {
                "name": "Cutting Words",
                "description": f"Reaction + 1 Bardic Inspiration use: subtract 1{die} from creature's damage roll, ability check, or attack roll within 60 ft",
            }
            if bard_level >= 6:
                stats["subclass_resources"]["magical_discoveries"] = {
                    "name": "Magical Discoveries",
                    "description": "Learn 2 spells of choice from Cleric, Druid, or Wizard lists (cantrip or spell slot level), always prepared",
                }
            if bard_level >= 14:
                stats["subclass_resources"]["peerless_skill"] = {
                    "name": "Peerless Skill",
                    "description": f"Add 1{die} to failed ability check or missed attack roll; if still fails, Bardic Inspiration is not expended",
                }
        elif subclass_name == "College of Valor" and bard_level >= 3:
            stats["subclass_resources"]["combat_inspiration"] = {
                "name": "Combat Inspiration",
                "description": f"Creature with your Bardic Inspiration die can add 1{die} to AC as Reaction against an attack, or add 1{die} to damage roll after hitting",
            }
            if bard_level >= 6:
                stats["subclass_resources"]["extra_attack"] = {
                    "name": "Extra Attack",
                    "description": "Attack twice when taking Attack action, and can replace one attack with an action cantrip",
                }
            if bard_level >= 14:
                stats["subclass_resources"]["battle_magic"] = {
                    "name": "Battle Magic",
                    "description": "Make 1 weapon attack as Bonus Action after casting an action spell",
                }
        elif subclass_name == "College of the Moon" and bard_level >= 3:
            stats["subclass_resources"]["moons_inspiration"] = {
                "name": "Moon's Inspiration",
                "description": f"Inspired Eclipse: Invisibility + 30 ft teleport when giving Bardic Inspiration. Lunar Vitality: 1/turn add 1{die} to spell healing and +10 ft speed",
            }
            if bard_level >= 6:
                stats["subclass_resources"]["blessing_of_moonlight"] = {
                    "name": "Blessing of Moonlight",
                    "description": "When casting Moonbeam, shed Dim Light 5 ft; creature fails save -> ally within 60 ft heals 2d4 (1/Long Rest)",
                }
            if bard_level >= 14:
                stats["subclass_resources"]["eventides_splendor"] = {
                    "name": "Eventide's Splendor",
                    "description": "Inspired Eclipse shares invisibility + 30 ft reaction teleport with recipient; Lunar Vitality rolls 1d6 instead of expending Bardic Inspiration die",
                }
        elif subclass_name == "College of Spirits" and bard_level >= 3:
            stats["subclass_resources"]["spirits_from_beyond"] = {
                "name": "Spirits from Beyond",
                "description": f"Channel spirits on Bardic Inspiration die roll (1-{die[1:]}); Controlled Channeling (BA expend BI to choose spirit); Unleash Spirit as Magic action within 30 ft",
            }
            if bard_level >= 6:
                stats["subclass_resources"]["empowered_channeling"] = {
                    "name": "Empowered Channeling",
                    "description": "Power from Beyond: +1d6 to damage or healing of Bard spell with slot 1/turn. Spiritual Manifestation: Spirit Guardians 1/Long Rest free cast; Half Cover for allies in emanation 1/Short or Long Rest",
                }
            if bard_level >= 14:
                stats["subclass_resources"]["mystical_connection"] = {
                    "name": "Mystical Connection",
                    "description": "Roll twice on Spirits from Beyond table and choose; if duplicate rolls, choose any spirit on the table",
                }

        return stats

    def calculate_cleric_stats(self) -> Dict[str, Any]:
        """
        Calculate Channel Divinity, Divine Spark, Divine Order, Blessed Strikes,
        Divine Intervention, and subclass statistics for Cleric characters.

        Returns:
            Dictionary with has_channel_divinity, cleric_level, subclass,
            channel_divinity_uses, channel_divinity_max, recharge,
            divine_spark_dice, save_dc, divine_order, blessed_strikes,
            sear_undead, divine_intervention, greater_divine_intervention,
            channel_divinity_options, subclass_resources, active_perks.
        """
        stats: Dict[str, Any] = {
            "has_channel_divinity": False,
            "cleric_level": 0,
            "subclass": "",
            "channel_divinity_uses": 0,
            "channel_divinity_max": 0,
            "recharge": "Short or Long Rest (regain 1 on Short Rest, all on Long Rest)",
            "divine_spark_dice": None,
            "save_dc": 0,
            "divine_order": None,
            "blessed_strikes": None,
            "sear_undead": False,
            "divine_intervention": False,
            "greater_divine_intervention": False,
            "channel_divinity_options": [],
            "subclass_resources": {},
            "active_perks": [],
        }

        cleric_level = self._get_class_level("Cleric")
        stats["cleric_level"] = cleric_level
        if cleric_level < 1:
            return stats

        subclass_name = self._get_class_subclass("Cleric") or ""
        stats["subclass"] = subclass_name

        ability_scores = getattr(self.ability_scores, "final_scores", {}) if hasattr(self, "ability_scores") else {}
        wis_score = ability_scores.get("Wisdom", 10) if isinstance(ability_scores, dict) else 10
        wis_mod = self.calculate_ability_modifier(wis_score)
        pb = self.calculate_proficiency_bonus(self.character_data.get("level", cleric_level))
        save_dc = 8 + pb + wis_mod
        stats["save_dc"] = save_dc

        # Divine Order (Level 1)
        choices_made = self.character_data.get("choices_made", {})
        divine_order = choices_made.get("divine_order")
        if not divine_order:
            for choice_key, val in choices_made.items():
                if "divine_order" in choice_key.lower() and isinstance(val, str):
                    divine_order = val
                    break
        if divine_order:
            stats["divine_order"] = {
                "name": divine_order,
                "description": (
                    "Martial weapon proficiency & Heavy armor training"
                    if divine_order == "Protector"
                    else f"1 extra Cleric cantrip & +{max(1, wis_mod)} bonus to Arcana and Religion checks"
                ),
            }
            stats["active_perks"].append(f"Divine Order: {divine_order}")

        # Channel Divinity (Level 2+)
        if cleric_level >= 2:
            stats["has_channel_divinity"] = True
            # Uses: 2 at 2-5, 3 at 6-17, 4 at 18-20
            max_uses = 4 if cleric_level >= 18 else (3 if cleric_level >= 6 else 2)
            stats["channel_divinity_uses"] = max_uses
            stats["channel_divinity_max"] = max_uses

            # Divine Spark dice: 1d8 at 2-6, 2d8 at 7-12, 3d8 at 13-17, 4d8 at 18-20
            spark_dice = "4d8" if cleric_level >= 18 else ("3d8" if cleric_level >= 13 else ("2d8" if cleric_level >= 7 else "1d8"))
            stats["divine_spark_dice"] = spark_dice

            # Standard Channel Divinity options
            stats["channel_divinity_options"].append({
                "name": "Divine Spark",
                "action": "Magic Action (Holy Symbol, 30 ft)",
                "effect": f"Roll {spark_dice} + {wis_mod} (Wisdom). Restore HP to a creature, or target makes Con save (DC {save_dc}) taking that much Radiant or Necrotic damage (half on save).",
            })
            turn_undead_desc = f"Undead within 30 ft make Wis save (DC {save_dc}) or be Frightened & Incapacitated for 1 minute (ends on damage)."
            if cleric_level >= 5:
                stats["sear_undead"] = True
                turn_undead_desc += f" Sear Undead: Affected undead also take {spark_dice} Radiant damage on failed save (half on success)."
                stats["active_perks"].append(f"Sear Undead ({spark_dice} Radiant)")
            stats["channel_divinity_options"].append({
                "name": "Turn Undead",
                "action": "Magic Action (Holy Symbol, 30 ft)",
                "effect": turn_undead_desc,
            })

        # Blessed Strikes (Level 7+)
        if cleric_level >= 7:
            blessed_strike = choices_made.get("blessed_strikes")
            if not blessed_strike:
                for k, v in choices_made.items():
                    if "blessed_strikes" in k.lower() and isinstance(v, str):
                        blessed_strike = v
                        break
            strike_dice = "2d8" if cleric_level >= 14 else "1d8"
            if blessed_strike == "Divine Strike":
                desc = f"1/turn when you hit with a weapon, deal extra {strike_dice} Radiant or Necrotic damage."
                stats["blessed_strikes"] = {"name": "Divine Strike", "dice": strike_dice, "description": desc}
                stats["active_perks"].append(f"Divine Strike (+{strike_dice})")
            elif blessed_strike == "Potent Spellcasting":
                desc = f"Add +{max(1, wis_mod)} (Wisdom) to damage dealt with any Cleric cantrip."
                if cleric_level >= 14:
                    desc += f" When dealing cantrip damage, grant {2 * max(1, wis_mod)} Temp HP to self or ally within 60 ft."
                stats["blessed_strikes"] = {"name": "Potent Spellcasting", "bonus": max(1, wis_mod), "description": desc}
                stats["active_perks"].append(f"Potent Spellcasting (+{max(1, wis_mod)})")
            elif not blessed_strike:
                stats["blessed_strikes"] = {"name": "Pending Selection", "description": f"Choose Divine Strike (+{strike_dice}) or Potent Spellcasting (+{max(1, wis_mod)})"}

        # Divine Intervention (Level 10+)
        if cleric_level >= 10:
            stats["divine_intervention"] = True
            if cleric_level >= 20:
                stats["greater_divine_intervention"] = True
                stats["active_perks"].append("Greater Divine Intervention (Wish or Lv 8- spell, 2d4 LR)")
            else:
                stats["active_perks"].append("Divine Intervention (Lv 5- spell, 1/Long Rest)")

        # Subclass Channel Divinity & Features
        if subclass_name == "Life Domain" and cleric_level >= 3:
            stats["subclass_resources"]["disciple_of_life"] = {
                "name": "Disciple of Life",
                "description": "When casting healing spell with slot, creature regains additional 2 + spell slot level HP",
            }
            stats["channel_divinity_options"].append({
                "name": "Preserve Life",
                "action": "Magic Action (Holy Symbol, 30 ft)",
                "effect": f"Restore up to {5 * cleric_level} HP divided among Bloodied creatures within 30 ft (max half max HP).",
            })
            if cleric_level >= 6:
                stats["subclass_resources"]["blessed_healer"] = {
                    "name": "Blessed Healer",
                    "description": "When healing others with spell slot, you regain 2 + spell slot level HP",
                }
            if cleric_level >= 17:
                stats["subclass_resources"]["supreme_healing"] = {
                    "name": "Supreme Healing",
                    "description": "Maximize all dice rolled for healing spells",
                }

        elif subclass_name == "Light Domain" and cleric_level >= 3:
            stats["channel_divinity_options"].append({
                "name": "Radiance of the Dawn",
                "action": "Magic Action (Holy Symbol, 30 ft)",
                "effect": f"Dispel magical darkness; 30-ft emanation, Con save (DC {save_dc}) or 2d10 + {cleric_level} Radiant damage (half on save).",
            })
            flare_uses = max(1, wis_mod)
            recharge_flare = "Short or Long Rest" if cleric_level >= 6 else "Long Rest"
            flare_desc = f"Reaction to impose Disadvantage on attack roll against you/ally within 30 ft ({flare_uses}/LR)."
            if cleric_level >= 6:
                flare_desc += f" Target also gains 2d6 + {wis_mod} Temp HP. Regain on Short or Long Rest."
            stats["subclass_resources"]["warding_flare"] = {
                "name": "Warding Flare",
                "uses": flare_uses,
                "recharge": recharge_flare,
                "description": flare_desc,
            }
            if cleric_level >= 17:
                stats["subclass_resources"]["corona_of_light"] = {
                    "name": "Corona of Light",
                    "uses": max(1, wis_mod),
                    "recharge": "Long Rest",
                    "description": "Aura of sunlight 60 ft bright / 30 ft dim for 1 min. Enemies in bright light have Disadvantage on saves vs Radiance of the Dawn and Fire/Radiant spells.",
                }

        elif subclass_name == "Trickery Domain" and cleric_level >= 3:
            stats["subclass_resources"]["blessing_of_the_trickster"] = {
                "name": "Blessing of the Trickster",
                "description": "Magic Action: Give self or willing creature within 30 ft Advantage on Stealth checks until Long Rest or used again",
            }
            stats["channel_divinity_options"].append({
                "name": "Invoke Duplicity",
                "action": "Bonus Action (30 ft)",
                "effect": "Create visual illusion for 1 min. Cast spells from its space; Advantage on attacks when you and illusion are within 5 ft of target; move 30 ft as Bonus Action (up to 120 ft).",
            })
            if cleric_level >= 6:
                stats["subclass_resources"]["tricksters_transposition"] = {
                    "name": "Trickster's Transposition",
                    "description": "When creating or moving your duplicate, teleport and swap places with it",
                }
            if cleric_level >= 17:
                stats["subclass_resources"]["improved_duplicity"] = {
                    "name": "Improved Duplicity",
                    "description": f"Allies also get Advantage vs creatures within 5 ft of illusion; when duplicate ends, creature within 5 ft heals {cleric_level} HP",
                }

        elif subclass_name == "War Domain" and cleric_level >= 3:
            stats["channel_divinity_options"].append({
                "name": "Guided Strike",
                "action": "No action (Reaction if used for ally within 30 ft)",
                "effect": "Give a missed attack roll a +10 bonus, potentially causing it to hit.",
            })
            war_priest_uses = max(1, wis_mod)
            stats["subclass_resources"]["war_priest"] = {
                "name": "War Priest",
                "uses": war_priest_uses,
                "recharge": "Short or Long Rest",
                "description": f"Bonus Action to make 1 weapon or Unarmed attack ({war_priest_uses}/Short or Long Rest).",
            }
            if cleric_level >= 6:
                stats["subclass_resources"]["war_gods_blessing"] = {
                    "name": "War God's Blessing",
                    "description": "Expend 1 Channel Divinity to cast Shield of Faith or Spiritual Weapon without slot and without Concentration (lasts 1 min)",
                }
            if cleric_level >= 17:
                stats["subclass_resources"]["avatar_of_battle"] = {
                    "name": "Avatar of Battle",
                    "description": "Resistance to Bludgeoning, Piercing, and Slashing damage",
                }

        elif subclass_name == "Knowledge Domain" and cleric_level >= 3:
            stats["channel_divinity_options"].append({
                "name": "Mind Magic",
                "action": "Magic Action",
                "effect": "Expend 1 Channel Divinity to cast any prepared Divination spell from Knowledge Domain Spells table without expending spell slot or material components.",
            })
            if cleric_level >= 6:
                stats["subclass_resources"]["unfettered_mind"] = {
                    "name": "Unfettered Mind",
                    "description": f"Telepathy 60 ft (up to {max(1, wis_mod)} creatures) & Intelligence saving throw proficiency",
                }
            if cleric_level >= 17:
                stats["subclass_resources"]["divine_foreknowledge"] = {
                    "name": "Divine Foreknowledge",
                    "recharge": "Long Rest (or 6+ level spell slot)",
                    "description": "Bonus Action: Gain Advantage on D20 Tests for 1 hour (1/Long Rest or expend level 6+ slot)",
                }

        elif subclass_name == "Grave Domain" and cleric_level >= 3:
            stats["channel_divinity_options"].append({
                "name": "Path to the Grave",
                "action": "Bonus Action (30 ft)",
                "effect": f"Curse creature until start of next turn: Disadvantage on attacks & saves. When hit, end curse to deal extra {cleric_level} Necrotic or Radiant damage.",
            })
            stats["subclass_resources"]["circle_of_mortality"] = {
                "name": "Circle of Mortality",
                "description": "Cast Spare the Dying as Bonus Action; maximize healing dice on creatures with 0 HP; +1d4 Necrotic damage once/turn to wounded creature (+1d6 at lv 11)",
            }
            if cleric_level >= 6:
                stats["subclass_resources"]["sentinel_at_deaths_door"] = {
                    "name": "Sentinel at Death's Door",
                    "uses": max(1, wis_mod),
                    "recharge": "Long Rest",
                    "description": f"Reaction when you or bloodied ally within 60 ft is hit: halve damage and cancel critical hit effects ({max(1, wis_mod)}/LR).",
                }
            if cleric_level >= 17:
                stats["subclass_resources"]["divine_reaper"] = {
                    "name": "Divine Reaper",
                    "description": f"Target 2nd creature with Lv 1-5 necromancy/domain spell with 1 Channel Divinity; when enemy dies within 60 ft, heal ally {2 * cleric_level} HP (1/SR or LR)",
                }

        elif subclass_name == "Pestilence Domain" and cleric_level >= 3:
            stats["subclass_resources"]["blight_weaver"] = {
                "name": "Blight Weaver",
                "description": "Resistance to Necrotic and Poison; ignore enemy resistance with Cleric spells/features; swap Necrotic/Poison damage types",
            }
            stats["channel_divinity_options"].append({
                "name": "Touch of Corruption",
                "action": "Magic Action (Melee spell attack or touch)",
                "effect": f"Channel decay to inflict Poisoned condition and ongoing Necrotic damage (DC {save_dc}).",
            })

        elif subclass_name == "Freedom Domain" and cleric_level >= 3:
            stats["subclass_resources"]["unencumbered_grace"] = {
                "name": "Unencumbered Grace",
                "description": "Unarmored AC = 10 + Dex + Wis; Acrobatics proficiency/expertise",
            }
            stats["channel_divinity_options"].append({
                "name": "Invoke Liberty",
                "action": "Magic Action (30-ft emanation)",
                "effect": "Allies end Frightened, Grappled, Paralyzed, or Restrained (plus Charmed/Petrified at lv 9) and can use Reaction to move speed without OA.",
            })

        elif subclass_name == "Arcana Domain" and cleric_level >= 3:
            stats["channel_divinity_options"].append({
                "name": "Modify Magic",
                "action": "No action (when casting spell)",
                "effect": f"Fortifying: Grant 2d8 + {cleric_level} Temp HP to target; Tenacious: When creature succeeds on save, subtract 1d6 from its first save vs spell.",
            })

        return stats

    def calculate_druid_stats(self) -> Dict[str, Any]:
        """
        Calculate Wild Shape uses, Max CR, known forms, movement capabilities,
        Primal Order, Elemental Fury, and subclass statistics for Druid characters.

        Returns:
            Dictionary with has_wild_shape, druid_level, subclass,
            wild_shape_uses, wild_shape_max, recharge, wild_shape_duration_hours,
            wild_shape_temp_hp, wild_shape_max_cr, wild_shape_known_forms,
            fly_speed_allowed, swim_speed_allowed, save_dc, primal_order,
            elemental_fury, primal_strike_dice, wild_resurgence, beast_spells,
            archdruid, wild_shape_options, subclass_resources, active_perks.
        """
        stats: Dict[str, Any] = {
            "has_wild_shape": False,
            "druid_level": 0,
            "subclass": "",
            "wild_shape_uses": 0,
            "wild_shape_max": 0,
            "recharge": "Short or Long Rest (regain 1 on Short Rest, all on Long Rest)",
            "wild_shape_duration_hours": 0.0,
            "wild_shape_temp_hp": 0,
            "wild_shape_max_cr": "0",
            "wild_shape_known_forms": 0,
            "fly_speed_allowed": False,
            "swim_speed_allowed": False,
            "save_dc": 0,
            "primal_order": None,
            "elemental_fury": None,
            "primal_strike_dice": None,
            "wild_resurgence": False,
            "beast_spells": False,
            "archdruid": False,
            "wild_shape_options": [],
            "subclass_resources": {},
            "active_perks": [],
        }

        druid_level = self._get_class_level("Druid")
        stats["druid_level"] = druid_level
        if druid_level < 1:
            return stats

        subclass_name = self._get_class_subclass("Druid") or ""
        stats["subclass"] = subclass_name

        ability_scores = getattr(self.ability_scores, "final_scores", {}) if hasattr(self, "ability_scores") else {}
        wis_score = ability_scores.get("Wisdom", 10) if isinstance(ability_scores, dict) else 10
        wis_mod = (wis_score - 10) // 2
        prof_bonus = self.calculate_proficiency_bonus(druid_level)
        save_dc = 8 + prof_bonus + wis_mod
        stats["save_dc"] = save_dc

        choices_made = self.character_data.get("choices_made", {})

        # Level 1: Primal Order
        primal_order = choices_made.get("primal_order")
        if not primal_order:
            for choice_key, val in choices_made.items():
                if "primal_order" in choice_key.lower() and isinstance(val, str):
                    primal_order = val
                    break
        if primal_order:
            stats["primal_order"] = {
                "name": primal_order,
                "description": (
                    "Martial weapon proficiency & Medium armor training"
                    if primal_order == "Warden"
                    else "Bonus cantrip & add Wisdom modifier (min +1) to Arcana and Nature checks"
                ),
            }
            stats["active_perks"].append(f"Primal Order: {primal_order}")

        # Level 2+: Wild Shape
        if druid_level >= 2:
            stats["has_wild_shape"] = True
            if druid_level >= 17:
                ws_uses = 4
            elif druid_level >= 6:
                ws_uses = 3
            else:
                ws_uses = 2
            stats["wild_shape_uses"] = ws_uses
            stats["wild_shape_max"] = ws_uses
            stats["wild_shape_duration_hours"] = druid_level / 2.0
            stats["swim_speed_allowed"] = True
            stats["fly_speed_allowed"] = druid_level >= 8

            # Known forms: 4 (lv 2-3), 6 (lv 4-7), 8 (lv 8+)
            if druid_level >= 8:
                stats["wild_shape_known_forms"] = 8
            elif druid_level >= 4:
                stats["wild_shape_known_forms"] = 6
            else:
                stats["wild_shape_known_forms"] = 4

            # Max CR & Temp HP
            if subclass_name == "Circle of the Moon":
                moon_cr = max(1, druid_level // 3)
                stats["wild_shape_max_cr"] = str(moon_cr)
                stats["wild_shape_temp_hp"] = 3 * druid_level
            elif subclass_name in ["Circle of Spores", "Circle of the Titan"]:
                stats["wild_shape_temp_hp"] = 4 * druid_level
                if druid_level >= 8:
                    stats["wild_shape_max_cr"] = "1"
                elif druid_level >= 4:
                    stats["wild_shape_max_cr"] = "1/2"
                else:
                    stats["wild_shape_max_cr"] = "1/4"
            else:
                stats["wild_shape_temp_hp"] = druid_level
                if druid_level >= 8:
                    stats["wild_shape_max_cr"] = "1"
                elif druid_level >= 4:
                    stats["wild_shape_max_cr"] = "1/2"
                else:
                    stats["wild_shape_max_cr"] = "1/4"

            # Base Wild Shape options
            fly_note = " (Fly Speed allowed)" if stats["fly_speed_allowed"] else " (No Fly Speed until Lv 8)"
            stats["wild_shape_options"].append({
                "name": "Beast Shapes",
                "action": "Bonus Action (Known Beast Forms)",
                "effect": f"Assume known Beast form (Max CR {stats['wild_shape_max_cr']}{fly_note}). Gain {stats['wild_shape_temp_hp']} Temp HP. Retain Int/Wis/Cha. Lasts {stats['wild_shape_duration_hours']:.1f} hrs.",
            })
            stats["wild_shape_options"].append({
                "name": "Wild Companion",
                "action": "No action (expend Wild Shape or spell slot)",
                "effect": f"Cast Find Familiar without Material components. Familiar is Fey and disappears after {stats['wild_shape_duration_hours']:.1f} hrs.",
            })

        # Level 5+: Wild Resurgence
        if druid_level >= 5:
            stats["wild_resurgence"] = True
            stats["active_perks"].append("Wild Resurgence (Convert spell slot to Wild Shape; 1/LR convert Wild Shape to Lv 1 slot)")

        # Level 7+: Elemental Fury
        if druid_level >= 7:
            elemental_fury = choices_made.get("elemental_fury")
            if not elemental_fury:
                for choice_key, val in choices_made.items():
                    if "elemental_fury" in choice_key.lower() and isinstance(val, str):
                        elemental_fury = val
                        break
            if elemental_fury == "Potent Spellcasting":
                desc = f"Add Wisdom modifier (+{wis_mod}) to Druid cantrip damage"
                if druid_level >= 15:
                    desc += "; cantrips with 10+ ft range have +300 ft range"
                stats["elemental_fury"] = {
                    "name": "Potent Spellcasting",
                    "description": desc,
                }
                stats["active_perks"].append(f"Elemental Fury: Potent Spellcasting (+{wis_mod} cantrip damage)")
            elif elemental_fury == "Primal Strike":
                strike_dice = "2d8" if druid_level >= 15 else "1d8"
                stats["primal_strike_dice"] = strike_dice
                stats["elemental_fury"] = {
                    "name": "Primal Strike",
                    "description": f"+{strike_dice} Cold, Fire, Lightning, or Thunder damage on 1 weapon or beast attack per turn",
                }
                stats["active_perks"].append(f"Elemental Fury: Primal Strike (+{strike_dice})")

        # Level 18+: Beast Spells
        if druid_level >= 18:
            stats["beast_spells"] = True
            stats["active_perks"].append("Beast Spells (Cast spells in Beast form lacking costly Material components)")

        # Level 20+: Archdruid
        if druid_level >= 20:
            stats["archdruid"] = True
            stats["active_perks"].append("Archdruid (Regain 1 Wild Shape on Initiative; convert Wild Shape to spell slot; 10x slower aging)")

        # Subclass options & resources
        if subclass_name == "Circle of the Moon" and druid_level >= 3:
            stats["wild_shape_options"].append({
                "name": "Circle Forms",
                "action": "Bonus Action",
                "effect": f"Wild Shape Max CR = {stats['wild_shape_max_cr']}; AC = {13 + wis_mod} if higher than beast; Temp HP = {3 * druid_level}; attacks deal normal or Radiant damage.",
            })
            if druid_level >= 6:
                stats["active_perks"].append(f"Increased Toughness (+{wis_mod} Wisdom bonus to Constitution saving throws in Wild Shape)")
            if druid_level >= 10:
                stats["subclass_resources"]["moonlight_step"] = {
                    "name": "Moonlight Step",
                    "uses": max(1, wis_mod),
                    "recharge": "Long Rest (regain 1 by expending Lv 2+ slot)",
                    "description": "Bonus Action: Teleport 30 ft and gain Advantage on next attack roll before turn ends",
                }
            if druid_level >= 14:
                stats["active_perks"].append("Lunar Form (+2d10 Radiant on 1 attack/turn; share Moonlight Step with ally)")

        elif subclass_name == "Circle of the Land" and druid_level >= 3:
            land_type = choices_made.get("land_type") or "Arid"
            aid_dice = "4d6" if druid_level >= 14 else ("3d6" if druid_level >= 10 else "2d6")
            stats["wild_shape_options"].append({
                "name": "Land's Aid",
                "action": "Magic Action (60 ft, 10-ft sphere)",
                "effect": f"Expend 1 Wild Shape use. Con save (DC {save_dc}) for {aid_dice} Necrotic damage (half on save); 1 creature heals {aid_dice} HP.",
            })
            if druid_level >= 6:
                max_rec = (druid_level + 1) // 2
                stats["subclass_resources"]["natural_recovery"] = {
                    "name": "Natural Recovery",
                    "description": f"Free cast 1 Circle spell / Long Rest; recover spell slots on Short Rest up to level {max_rec} (1/Long Rest)",
                }
            if druid_level >= 10:
                res_map = {"Arid": "Fire", "Polar": "Cold", "Temperate": "Lightning", "Tropical": "Poison"}
                res_type = res_map.get(land_type, "Fire")
                stats["active_perks"].append(f"Nature's Ward (Immune to Poisoned condition & {res_type} damage resistance)")
            if druid_level >= 14:
                stats["wild_shape_options"].append({
                    "name": "Nature's Sanctuary",
                    "action": "Magic Action (120 ft, 15-ft cube)",
                    "effect": "Expend 1 Wild Shape use. Spectral grove for 1 min grants allies Half Cover and Nature's Ward resistance; move 60 ft as Bonus Action.",
                })

        elif subclass_name == "Circle of the Sea" and druid_level >= 3:
            emanation_size = 10 if druid_level >= 6 else 5
            stats["wild_shape_options"].append({
                "name": "Wrath of the Sea",
                "action": f"Bonus Action ({emanation_size}-ft emanation, 10 min)",
                "effect": f"Expend 1 Wild Shape use. Con save (DC {save_dc}) or take {max(1, wis_mod)}d6 Cold damage and pushed 15 ft away.",
            })
            if druid_level >= 6:
                stats["active_perks"].append("Aquatic Affinity (Swim speed equal to Speed; 10-ft Wrath emanation)")
            if druid_level >= 10:
                stats["active_perks"].append("Stormborn (Fly speed equal to Speed & Resistance to Cold, Lightning, Thunder while Wrath active)")
            if druid_level >= 14:
                stats["active_perks"].append("Oceanic Gift (Manifest Wrath of the Sea around ally within 60 ft, or both for 2 Wild Shape uses)")

        elif subclass_name == "Circle of the Stars" and druid_level >= 3:
            stats["subclass_resources"]["star_map"] = {
                "name": "Star Map",
                "uses": max(1, wis_mod),
                "recharge": "Long Rest",
                "description": f"Guidance cantrip; cast Guiding Bolt without spell slot {max(1, wis_mod)} times per Long Rest",
            }
            form_dice = "2d8" if druid_level >= 10 else "1d8"
            stats["wild_shape_options"].append({
                "name": "Starry Form",
                "action": "Bonus Action (10 min, 10-ft bright / 10-ft dim light)",
                "effect": f"Archer (BA 60 ft ranged spell attack for {form_dice}+{wis_mod} Radiant), Chalice (healing spell heals extra {form_dice}+{wis_mod} HP within 30 ft), Dragon (treat roll <= 9 as 10 on Int/Wis checks & Con concentration saves; Fly 20 ft hover at Lv 10).",
            })
            if druid_level >= 6:
                stats["subclass_resources"]["cosmic_omen"] = {
                    "name": "Cosmic Omen",
                    "uses": max(1, wis_mod),
                    "recharge": "Long Rest",
                    "description": f"Weal/Woe reaction to add or subtract 1d6 from d20 test within 30 ft ({max(1, wis_mod)}/LR)",
                }
            if druid_level >= 14:
                stats["active_perks"].append("Full of Stars (Resistance to Bludgeoning, Piercing, and Slashing damage in Starry Form)")

        elif subclass_name == "Circle of Spores" and druid_level >= 3:
            halo_die = "1d10" if druid_level >= 14 else ("1d8" if druid_level >= 10 else ("1d6" if druid_level >= 6 else "1d4"))
            stats["subclass_resources"]["halo_of_spores"] = {
                "name": "Halo of Spores",
                "description": f"Reaction when creature enters or starts turn in 10-ft emanation: Con save (DC {save_dc}) or take {halo_die} Necrotic (or disadvantage on next attack on save)",
            }
            stats["wild_shape_options"].append({
                "name": "Symbiotic Entity",
                "action": "Bonus Action (10 min)",
                "effect": f"Expend 1 Wild Shape use. Gain {4 * druid_level} Temp HP; Halo of Spores damage is doubled; deal +1d6 Necrotic on 1 melee attack per turn.",
            })
            if druid_level >= 6:
                stats["subclass_resources"]["fungal_infestation"] = {
                    "name": "Fungal Infestation",
                    "uses": max(1, wis_mod),
                    "recharge": "Long Rest",
                    "description": f"Reaction to animate Small/Medium Beast or Humanoid corpse within 10 ft as Zombie for 1 hour ({max(1, wis_mod)}/LR)",
                }
            if druid_level >= 10:
                stats["active_perks"].append(f"Explosive Burst (Created undead explodes on death: 10 ft Con save DC {save_dc} for 2d8 Necrotic)")
            if druid_level >= 14:
                stats["active_perks"].append("Fungal Body (Immunity to Blinded, Deafened, Frightened, Poisoned; immune to Critical Hits; spores steer body when Unconscious)")

        elif subclass_name == "Circle of the Titan" and druid_level >= 3:
            rend_dice = "3d8" if druid_level >= 12 else ("2d8" if druid_level >= 6 else "1d8")
            stats["wild_shape_options"].append({
                "name": "Titan Form",
                "action": "Bonus Action (10 min)",
                "effect": f"Transform into Large Behemoth, Leviathan, or Insectoid. AC = {13 + wis_mod}; Temp HP = {4 * druid_level}; Speed 40 ft (Climb/Swim/Fly 40 ft); Rend deals {rend_dice}+{wis_mod} damage.",
            })

        return stats

    def calculate_fighter_stats(self) -> Dict[str, Any]:
        """
        Calculate Fighter 2024 RAW statistics including:
        - Second Wind uses and scaling, Tactical Mind (lv 2), Tactical Shift (lv 5)
        - Action Surge uses (lv 2, lv 17) and 2024 restrictions
        - Indomitable uses and bonus scaling (lv 9, lv 13, lv 17)
        - Attacks per Action (1, 2, 3, 4)
        - Tactical Master (lv 9) Push/Sap/Slow
        - Studied Attacks (lv 13)
        - Weapon Mastery count
        - Subclass mechanics for Battle Master, Champion, Eldritch Knight,
          Psi Warrior, Banneret, Hell Knight, Arcane Archer
        """
        stats: Dict[str, Any] = {
            "is_fighter": False,
            "fighter_level": 0,
            "subclass": None,
            "second_wind_uses": 0,
            "second_wind_max": 0,
            "second_wind_die": "1d10",
            "second_wind_healing": "1d10",
            "second_wind_recharge": "Short or Long Rest (regain 1 on Short Rest, all on Long Rest)",
            "tactical_mind": False,
            "tactical_shift": False,
            "has_action_surge": False,
            "action_surge_uses": 0,
            "action_surge_max": 0,
            "action_surge_recharge": "Short or Long Rest",
            "action_surge_restriction": "Take one additional action on your turn (except the Magic action). Only once per turn.",
            "has_indomitable": False,
            "indomitable_uses": 0,
            "indomitable_max": 0,
            "indomitable_bonus": 0,
            "indomitable_recharge": "Long Rest",
            "attacks_per_action": 1,
            "extra_attacks_label": "None",
            "has_tactical_master": False,
            "tactical_master_properties": [],
            "has_studied_attacks": False,
            "weapon_mastery_count": 0,
            "subclass_details": {},
            "active_perks": [],
            "actions": [],
        }

        fighter_level = self._get_class_level("Fighter")
        if fighter_level <= 0:
            return stats

        stats["is_fighter"] = True
        stats["fighter_level"] = fighter_level
        subclass_name = self._get_class_subclass("Fighter")
        stats["subclass"] = subclass_name

        level = self.character_data.get("level", fighter_level)
        pb = self.calculate_proficiency_bonus(level)
        scores = self.calculate_processed_ability_scores()
        str_mod = scores.get("strength", {}).get("modifier", 0)
        dex_mod = scores.get("dexterity", {}).get("modifier", 0)
        con_mod = scores.get("constitution", {}).get("modifier", 0)
        int_mod = scores.get("intelligence", {}).get("modifier", 0)
        wis_mod = scores.get("wisdom", {}).get("modifier", 0)
        cha_mod = scores.get("charisma", {}).get("modifier", 0)

        # Second Wind (Level 1+)
        # 2 uses (lv 1-3), 3 uses (lv 4-9), 4 uses (lv 10-20)
        sw_uses = 4 if fighter_level >= 10 else (3 if fighter_level >= 4 else 2)
        stats["second_wind_uses"] = sw_uses
        stats["second_wind_max"] = sw_uses
        stats["second_wind_healing"] = f"1d10 + {fighter_level}"
        stats["actions"].append({
            "name": "Second Wind",
            "action": "Bonus Action",
            "uses": sw_uses,
            "recharge": "1 on Short Rest, all on Long Rest",
            "effect": f"Regain 1d10+{fighter_level} HP.",
        })

        # Tactical Mind (Level 2+)
        if fighter_level >= 2:
            stats["tactical_mind"] = True
            stats["actions"].append({
                "name": "Tactical Mind",
                "action": "Special",
                "effect": "When you fail an ability check, expend a Second Wind use to add 1d10 to the check. If the check still fails, the use is not expended.",
            })

        # Tactical Shift (Level 5+)
        if fighter_level >= 5:
            stats["tactical_shift"] = True
            stats["active_perks"].append("Tactical Shift (move up to half speed without Opportunity Attacks when using Second Wind)")

        # Action Surge (Level 2+)
        if fighter_level >= 2:
            as_uses = 2 if fighter_level >= 17 else 1
            stats["has_action_surge"] = True
            stats["action_surge_uses"] = as_uses
            stats["action_surge_max"] = as_uses
            stats["actions"].append({
                "name": "Action Surge",
                "action": "Free Action (on your turn)",
                "uses": as_uses,
                "recharge": "Short or Long Rest",
                "effect": "Take one additional action on your turn (except the Magic action). Only once per turn.",
            })

        # Indomitable (Level 9+)
        if fighter_level >= 9:
            indom_uses = 3 if fighter_level >= 17 else (2 if fighter_level >= 13 else 1)
            stats["has_indomitable"] = True
            stats["indomitable_uses"] = indom_uses
            stats["indomitable_max"] = indom_uses
            stats["indomitable_bonus"] = fighter_level
            stats["actions"].append({
                "name": "Indomitable",
                "action": "Reaction",
                "uses": indom_uses,
                "recharge": "Long Rest",
                "effect": f"Reroll a failed saving throw with a +{fighter_level} bonus.",
            })

        # Attacks per Action (Extra Attack)
        if fighter_level >= 20:
            stats["attacks_per_action"] = 4
            stats["extra_attacks_label"] = "Three Extra Attacks (4 attacks/action)"
        elif fighter_level >= 11:
            stats["attacks_per_action"] = 3
            stats["extra_attacks_label"] = "Two Extra Attacks (3 attacks/action)"
        elif fighter_level >= 5:
            stats["attacks_per_action"] = 2
            stats["extra_attacks_label"] = "Extra Attack (2 attacks/action)"
        else:
            stats["attacks_per_action"] = 1
            stats["extra_attacks_label"] = "1 attack/action"

        # Tactical Master (Level 9+)
        if fighter_level >= 9:
            stats["has_tactical_master"] = True
            stats["tactical_master_properties"] = ["Push", "Sap", "Slow"]
            stats["active_perks"].append("Tactical Master (can replace mastery property with Push, Sap, or Slow)")

        # Studied Attacks (Level 13+)
        if fighter_level >= 13:
            stats["has_studied_attacks"] = True
            stats["active_perks"].append("Studied Attacks (Advantage on next attack roll if you miss a creature)")

        # Weapon Masteries count
        if fighter_level >= 16:
            stats["weapon_mastery_count"] = 6
        elif fighter_level >= 10:
            stats["weapon_mastery_count"] = 5
        elif fighter_level >= 4:
            stats["weapon_mastery_count"] = 4
        else:
            stats["weapon_mastery_count"] = 3

        # Subclass Specifics
        subclass_details: Dict[str, Any] = {}

        # 1. Battle Master
        if subclass_name == "Battle Master" and fighter_level >= 3:
            sup_count = 6 if fighter_level >= 15 else (5 if fighter_level >= 7 else 4)
            sup_die = "d12" if fighter_level >= 18 else ("d10" if fighter_level >= 10 else "d8")
            save_dc = 8 + pb + max(str_mod, dex_mod)
            maneuvers_list = self.character_data.get("maneuvers_known", []) or self.character_data.get("maneuvers", [])
            subclass_details["battle_master"] = {
                "superiority_dice_count": sup_count,
                "superiority_die": sup_die,
                "save_dc": save_dc,
                "recharge": "Short or Long Rest",
                "maneuvers": maneuvers_list,
                "know_your_enemy": fighter_level >= 7,
                "relentless": fighter_level >= 15,
            }
            stats["actions"].append({
                "name": "Superiority Dice",
                "action": "Special (Maneuver)",
                "uses": sup_count,
                "recharge": "Short or Long Rest",
                "effect": f"{sup_count}{sup_die} superiority dice. DC {save_dc} (STR/DEX).",
            })
            if fighter_level >= 7:
                stats["actions"].append({
                    "name": "Know Your Enemy",
                    "action": "Bonus Action",
                    "effect": "Discern Immunities, Resistances, and Vulnerabilities of creature within 30 ft (1/LR or 1 Superiority Die).",
                })
            if fighter_level >= 15:
                stats["active_perks"].append("Relentless (1/turn, roll 1d8 instead of expending a Superiority Die)")

        # 2. Champion
        elif subclass_name == "Champion" and fighter_level >= 3:
            crit_threshold = 18 if fighter_level >= 15 else 19
            subclass_details["champion"] = {
                "crit_threshold": crit_threshold,
                "crit_range": f"{crit_threshold}-20",
                "remarkable_athlete": True,
                "additional_fighting_style": fighter_level >= 7,
                "heroic_warrior": fighter_level >= 10,
                "survivor": fighter_level >= 18,
            }
            stats["active_perks"].append(f"Critical Hit on {crit_threshold}-20")
            stats["active_perks"].append("Remarkable Athlete (Advantage on Initiative and Athletics; half speed move on Crit without OA)")
            if fighter_level >= 10:
                stats["active_perks"].append("Heroic Warrior (gain Heroic Inspiration at start of your turn in combat if you lack it)")
            if fighter_level >= 18:
                stats["active_perks"].append(f"Survivor (Advantage on Death Saves, 18-20 counts as 20; regain {5 + con_mod} HP at turn start if Bloodied)")

        # 3. Eldritch Knight
        elif subclass_name == "Eldritch Knight" and fighter_level >= 3:
            ek_dc = 8 + pb + int_mod
            ek_attack = pb + int_mod
            subclass_details["eldritch_knight"] = {
                "spellcasting_ability": "Intelligence",
                "spell_save_dc": ek_dc,
                "spell_attack_bonus": ek_attack,
                "war_bond": True,
                "war_magic": fighter_level >= 7,
                "eldritch_strike": fighter_level >= 10,
                "arcane_charge": fighter_level >= 15,
                "improved_war_magic": fighter_level >= 18,
            }
            stats["actions"].append({
                "name": "War Bond",
                "action": "Bonus Action",
                "effect": "Summon bonded weapon instantly to your hand (up to 2 bonded weapons; cannot be disarmed).",
            })
            if fighter_level >= 7:
                stats["active_perks"].append("War Magic (replace 1 attack in Attack action with an action Wizard cantrip)")
            if fighter_level >= 10:
                stats["active_perks"].append("Eldritch Strike (weapon hit imposes Disadvantage on save vs your spell before end of next turn)")
            if fighter_level >= 15:
                stats["active_perks"].append("Arcane Charge (teleport up to 30 ft when using Action Surge)")
            if fighter_level >= 18:
                stats["active_perks"].append("Improved War Magic (replace 2 attacks in Attack action with a level 1-2 Wizard spell)")

        # 4. Psi Warrior
        elif subclass_name == "Psi Warrior" and fighter_level >= 3:
            psi_count = 2 * pb
            psi_die = "d12" if fighter_level >= 17 else ("d10" if fighter_level >= 11 else ("d8" if fighter_level >= 5 else "d6"))
            psi_dc = 8 + pb + int_mod
            subclass_details["psi_warrior"] = {
                "psionic_dice_count": psi_count,
                "psionic_die": psi_die,
                "save_dc": psi_dc,
                "recharge": "Long Rest (regain 1 as Bonus Action once per Short/Long Rest)",
            }
            stats["actions"].append({
                "name": "Psionic Energy Dice",
                "action": "Special",
                "uses": psi_count,
                "recharge": "Long Rest (1/SR)",
                "effect": f"{psi_count}{psi_die} psionic energy dice. DC {psi_dc} (INT).",
            })
            stats["actions"].append({
                "name": "Protective Field",
                "action": "Reaction",
                "effect": f"Expend 1 Psionic Die to reduce damage to self or ally in 30 ft by 1{psi_die}+{int_mod}.",
            })
            stats["actions"].append({
                "name": "Psionic Strike",
                "action": "Special (1/turn)",
                "effect": f"Deal extra 1{psi_die}+{int_mod} Force damage on weapon hit within 30 ft.",
            })
            stats["actions"].append({
                "name": "Telekinetic Movement",
                "action": "Magic Action",
                "effect": "Move loose object or willing creature within 30 ft up to 30 ft (1/SR or expend 1 Psionic Die).",
            })
            if fighter_level >= 7:
                stats["actions"].append({
                    "name": "Psi-Powered Leap",
                    "action": "Bonus Action",
                    "effect": "Gain Fly Speed equal to 2x Speed until end of turn (1/SR or expend 1 Psionic Die).",
                })
                stats["active_perks"].append(f"Telekinetic Thrust (on Psionic Strike, target makes DC {psi_dc} STR save or is knocked Prone or pushed 10 ft)")
            if fighter_level >= 10:
                stats["active_perks"].append("Guarded Mind (Psychic resistance; expend 1 Psionic Die to end Charmed/Frightened)")
            if fighter_level >= 15:
                stats["actions"].append({
                    "name": "Bulwark of Force",
                    "action": "Bonus Action",
                    "effect": f"Give Half Cover to up to {max(1, int_mod)} creatures in 30 ft for 1 min (1/LR or expend 1 Psionic Die).",
                })
            if fighter_level >= 18:
                stats["actions"].append({
                    "name": "Telekinetic Master",
                    "action": "Magic Action",
                    "effect": "Cast Telekinesis without slot; bonus action weapon attack while concentrating (1/LR or expend 1 Psionic Die).",
                })

        # 5. Banneret (FR Supplement)
        elif subclass_name == "Banneret" and fighter_level >= 3:
            allies_count = max(1, cha_mod)
            subclass_details["banneret"] = {
                "group_recovery_allies": allies_count,
                "group_recovery_heal": f"1d4 + {fighter_level}",
                "team_tactics": fighter_level >= 7,
                "rallying_surge": fighter_level >= 10,
                "shared_resilience": fighter_level >= 15,
                "inspiring_commander": fighter_level >= 18,
            }
            stats["actions"].append({
                "name": "Group Recovery",
                "action": "Special (with Second Wind)",
                "recharge": "Short or Long Rest",
                "effect": f"Heal up to {allies_count} allies within 30 ft for 1d4+{fighter_level} HP when using Second Wind.",
            })
            if fighter_level >= 7:
                stats["active_perks"].append("Team Tactics (Group Recovery grants chosen allies Advantage on D20 Tests until start of next turn)")
            if fighter_level >= 10:
                stats["actions"].append({
                    "name": "Rallying Surge",
                    "action": "Special (with Action Surge)",
                    "effect": f"Up to {allies_count} allies in 30 ft can use Reaction to make 1 attack or move half speed without OA.",
                })
            if fighter_level >= 15:
                stats["actions"].append({
                    "name": "Shared Resilience",
                    "action": "Reaction",
                    "effect": f"Expend Indomitable when ally in 60 ft fails a save to let them reroll with +{fighter_level}.",
                })
            if fighter_level >= 18:
                stats["active_perks"].append("Inspiring Commander (Group Recovery & Rallying Surge range is 60 ft; immune to Charmed & Frightened)")

        # 6. Hell Knight (UA Supplement)
        elif subclass_name == "Hell Knight" and fighter_level >= 3:
            wound_uses = max(1, con_mod)
            subclass_details["hell_knight"] = {
                "infernal_wound_uses": wound_uses,
                "infernal_wound_die": "d6",
                "damage_types": ["Cold", "Fire", "Necrotic"],
                "devils_sight": True,
            }
            stats["actions"].append({
                "name": "Hell-Forged Weapon",
                "action": "Special (on Attack)",
                "effect": "Imbue weapons with Cold, Fire, or Necrotic damage and shed 5 ft Dim Light.",
            })
            stats["actions"].append({
                "name": "Infernal Wound",
                "action": "Special (on hit)",
                "uses": wound_uses,
                "recharge": "Short or Long Rest",
                "effect": "Deal extra 1d6 damage and cause target to bleed 1d6 damage at start of its turns for 1 min.",
            })
            stats["active_perks"].append("Devil's Sight (see in normal and magical darkness up to 120 ft)")
            if fighter_level >= 7:
                stats["active_perks"].append("Advanced Wounds (Purulence of Minauros, Rupture of Cania, Stygian Gangrene + Devil's Luck on 6)")
                stats["active_perks"].append("Infernal Resilience (Resistance to Cold, Fire, or Necrotic while wearing Heavy armor or Shield)")
            if fighter_level >= 10:
                stats["actions"].append({
                    "name": "Hellfire Surge",
                    "action": "Special (with Action Surge)",
                    "effect": "20-ft infernal emanation; wounded creatures take 2d6 instead of 1d6.",
                })
            if fighter_level >= 15:
                stats["actions"].append({
                    "name": "Devil's Misfortune",
                    "action": "Reaction",
                    "effect": "Reduce damage by 1d6 (reroll up to 3x on 6); negate Critical Hits.",
                })

        # 7. Arcane Archer (AU Supplement)
        elif subclass_name == "Arcane Archer" and fighter_level >= 3:
            aa_dc = 8 + pb + int_mod
            subclass_details["arcane_archer"] = {
                "arcane_shot_dice": 2,
                "save_dc": aa_dc,
                "recharge": "Short or Long Rest",
            }
            stats["actions"].append({
                "name": "Arcane Shot",
                "action": "Special (1/turn on attack)",
                "uses": 2,
                "recharge": "Short or Long Rest",
                "effect": f"Apply special magical shot. Save DC {aa_dc} (INT).",
            })

        stats["subclass_details"] = subclass_details
        return stats

    def calculate_monk_stats(self) -> Dict[str, Any]:
        """
        Calculate Monk 2024 RAW statistics including:
        - Martial Arts die scaling (1d6 -> 1d8 -> 1d10 -> 1d12)
        - Focus Points scaling (level 2+, equal to level) and recharge
        - Focus Save DC (8 + PB + WIS mod)
        - Unarmored Defense AC (10 + DEX mod + WIS mod)
        - Unarmored Movement bonus scaling (10 -> 15 -> 20 -> 25 -> 30 ft)
        - Attacks per Action (1, or 2 with Extra Attack at lv 5+)
        - Feature progression:
          - Uncanny Metabolism (lv 2)
          - Deflect Attacks (lv 3) & Deflect Energy (lv 13)
          - Slow Fall (lv 4)
          - Stunning Strike (lv 5)
          - Empowered Strikes (lv 6)
          - Evasion (lv 7)
          - Acrobatic Movement (lv 9)
          - Heightened Focus (lv 10)
          - Self-Restoration (lv 10)
          - Disciplined Survivor (lv 14)
          - Perfect Focus (lv 15)
          - Superior Defense (lv 18)
          - Body and Mind (lv 20)
        - Subclass mechanics for:
          - Warrior of Mercy (Hand of Healing, Hand of Harm, Physician's Touch, Flurry of Healing & Harm, Hand of Ultimate Mercy)
          - Warrior of Shadow (Shadow Arts / Darkness, Darkvision, Shadow Step, Improved Shadow Step, Cloak of Shadows)
          - Warrior of the Elements (Elemental Attunement, Elementalism, Elemental Burst, Stride of the Elements, Elemental Epitome)
          - Warrior of the Open Hand (Open Hand Technique, Wholeness of Body, Fleet Step, Quivering Palm)
          - Warrior of Venom (Potent Arsenal, Envenom Weapon, Toxic Touch, Toxin Refiner, Toxic Blood, Hallucinogenic Breath)
          - Warrior of the Mystic Arts (Sorcerer Spellcasting, Mystic Fighting Style, Mystic Focus, Focused Strike, Improved Mystic Fighting Style)
        """
        stats: Dict[str, Any] = {
            "is_monk": False,
            "monk_level": 0,
            "subclass": None,
            "martial_arts_die": "1d6",
            "focus_points": 0,
            "focus_points_max": 0,
            "focus_save_dc": 10,
            "focus_recharge": "Short or Long Rest",
            "unarmored_movement_bonus": 0,
            "unarmored_defense_ac": 10,
            "attacks_per_action": 1,
            "extra_attacks_label": "None",
            "has_bonus_unarmed_strike": True,
            "has_dexterous_attacks": True,
            "has_uncanny_metabolism": False,
            "has_deflect_attacks": False,
            "has_deflect_energy": False,
            "has_slow_fall": False,
            "has_stunning_strike": False,
            "has_empowered_strikes": False,
            "has_evasion": False,
            "has_acrobatic_movement": False,
            "has_heightened_focus": False,
            "has_self_restoration": False,
            "has_disciplined_survivor": False,
            "has_perfect_focus": False,
            "has_superior_defense": False,
            "has_body_and_mind": False,
            "subclass_details": {},
            "active_perks": [],
            "actions": [],
        }

        monk_level = self._get_class_level("Monk")
        if monk_level <= 0:
            return stats

        stats["is_monk"] = True
        stats["monk_level"] = monk_level
        subclass_name = self._get_class_subclass("Monk")
        stats["subclass"] = subclass_name

        level = self.character_data.get("level", monk_level)
        pb = self.calculate_proficiency_bonus(level)
        scores = self.calculate_processed_ability_scores()
        dex_mod = scores.get("dexterity", {}).get("modifier", 0)
        wis_mod = scores.get("wisdom", {}).get("modifier", 0)
        con_mod = scores.get("constitution", {}).get("modifier", 0)

        # Martial Arts Die
        ma_die = "1d12" if monk_level >= 17 else ("1d10" if monk_level >= 11 else ("1d8" if monk_level >= 5 else "1d6"))
        stats["martial_arts_die"] = ma_die

        # Focus Points (Level 2+)
        fp = monk_level if monk_level >= 2 else 0
        stats["focus_points"] = fp
        stats["focus_points_max"] = fp
        stats["focus_save_dc"] = 8 + pb + wis_mod

        # Unarmored Movement bonus
        um_bonus = 30 if monk_level >= 18 else (25 if monk_level >= 14 else (20 if monk_level >= 10 else (15 if monk_level >= 6 else (10 if monk_level >= 2 else 0))))
        stats["unarmored_movement_bonus"] = um_bonus

        # Unarmored Defense AC
        stats["unarmored_defense_ac"] = 10 + dex_mod + wis_mod

        # Attacks per action
        attacks_count = 2 if monk_level >= 5 else 1
        stats["attacks_per_action"] = attacks_count
        stats["extra_attacks_label"] = "Extra Attack (2 attacks)" if monk_level >= 5 else "1 attack"

        # Base Monk Actions:
        # Bonus Unarmed Strike (Level 1)
        stats["actions"].append({
            "name": "Bonus Unarmed Strike",
            "action": "Bonus Action",
            "cost": "Free",
            "effect": "Make one Unarmed Strike as a Bonus Action.",
        })

        # Level 2 Focus actions
        if monk_level >= 2:
            stats["has_uncanny_metabolism"] = True
            flurry_strikes = "three" if monk_level >= 10 else "two"
            stats["actions"].append({
                "name": "Flurry of Blows",
                "action": "Bonus Action",
                "cost": "1 Focus Point",
                "effect": f"Make {flurry_strikes} Unarmed Strikes.",
            })
            pd_extra = f" Gain 2{ma_die} Temp HP." if monk_level >= 10 else ""
            stats["actions"].append({
                "name": "Patient Defense",
                "action": "Bonus Action",
                "cost": "0 FP (Disengage) or 1 FP (Disengage + Dodge)",
                "effect": f"Take Disengage for free, or spend 1 FP to take both Disengage and Dodge.{pd_extra}",
            })
            sotw_extra = " Move a willing Large or smaller ally with you without OA." if monk_level >= 10 else ""
            stats["actions"].append({
                "name": "Step of the Wind",
                "action": "Bonus Action",
                "cost": "0 FP (Dash) or 1 FP (Dash + Disengage)",
                "effect": f"Take Dash for free, or spend 1 FP to take both Dash and Disengage with doubled jump distance.{sotw_extra}",
            })
            stats["actions"].append({
                "name": "Uncanny Metabolism",
                "action": "Special (on Initiative roll)",
                "uses": 1,
                "recharge": "Long Rest",
                "effect": f"Regain all expended Focus Points, and regain {monk_level}+{ma_die} HP.",
            })

        # Deflect Attacks (Level 3) & Deflect Energy (Level 13)
        if monk_level >= 3:
            stats["has_deflect_attacks"] = True
            if monk_level >= 13:
                stats["has_deflect_energy"] = True
            damage_scope = "any damage type" if monk_level >= 13 else "Bludgeoning, Piercing, or Slashing damage"
            dex_str = f"+{dex_mod}" if dex_mod >= 0 else str(dex_mod)
            stats["actions"].append({
                "name": "Deflect Energy" if monk_level >= 13 else "Deflect Attacks",
                "action": "Reaction",
                "cost": "0 FP to reduce, 1 FP to redirect",
                "effect": f"When hit by an attack dealing {damage_scope}, reduce damage by 1d10{dex_str}+{monk_level}. If reduced to 0, spend 1 FP to counterattack dealing 2{ma_die}{dex_str} damage (DEX save DC {stats['focus_save_dc']}).",
            })

        # Slow Fall (Level 4)
        if monk_level >= 4:
            stats["has_slow_fall"] = True
            stats["actions"].append({
                "name": "Slow Fall",
                "action": "Reaction",
                "cost": "Free",
                "effect": f"Reduce falling damage by {5 * monk_level} HP.",
            })

        # Stunning Strike (Level 5)
        if monk_level >= 5:
            stats["has_stunning_strike"] = True
            stats["actions"].append({
                "name": "Stunning Strike",
                "action": "Special (1/turn on hit)",
                "cost": "1 Focus Point",
                "effect": f"Target makes CON save (DC {stats['focus_save_dc']}). Fail: Stunned until start of next turn. Success: Speed halved & next attack has Advantage.",
            })

        # Empowered Strikes (Level 6)
        if monk_level >= 6:
            stats["has_empowered_strikes"] = True
            stats["active_perks"].append("Empowered Strikes (Unarmed Strikes can deal Force damage)")

        # Evasion (Level 7)
        if monk_level >= 7:
            stats["has_evasion"] = True
            stats["active_perks"].append("Evasion (DEX saves: no damage on success, half on failure)")

        # Acrobatic Movement (Level 9)
        if monk_level >= 9:
            stats["has_acrobatic_movement"] = True
            stats["active_perks"].append("Acrobatic Movement (Run along vertical surfaces & across liquids)")

        # Heightened Focus & Self-Restoration (Level 10)
        if monk_level >= 10:
            stats["has_heightened_focus"] = True
            stats["has_self_restoration"] = True
            stats["active_perks"].append("Heightened Focus (Flurry: 3 strikes; Patient Defense: Temp HP; Step of Wind: Carry ally)")
            stats["active_perks"].append("Self-Restoration (End Charmed, Frightened, or Poisoned at end of turn; immune to food/drink exhaustion)")

        # Disciplined Survivor (Level 14)
        if monk_level >= 14:
            stats["has_disciplined_survivor"] = True
            stats["active_perks"].append("Disciplined Survivor (Proficiency in all saves)")
            stats["actions"].append({
                "name": "Disciplined Survivor Reroll",
                "action": "Special (on failed save)",
                "cost": "1 Focus Point",
                "effect": "Reroll a failed saving throw and take the new result.",
            })

        # Perfect Focus (Level 15)
        if monk_level >= 15:
            stats["has_perfect_focus"] = True
            stats["active_perks"].append("Perfect Focus (Regain Focus Points up to 4 on Initiative roll)")

        # Superior Defense (Level 18)
        if monk_level >= 18:
            stats["has_superior_defense"] = True
            stats["actions"].append({
                "name": "Superior Defense",
                "action": "Special (start of turn)",
                "cost": "3 Focus Points",
                "effect": "Gain Resistance to all damage except Force for 1 minute.",
            })

        # Body and Mind (Level 20)
        if monk_level >= 20:
            stats["has_body_and_mind"] = True
            stats["active_perks"].append("Body and Mind (+4 Dexterity and +4 Wisdom, maximum 25)")

        # Subclass Mechanics
        subclass_details: Dict[str, Any] = {}
        wis_str = f"+{wis_mod}" if wis_mod >= 0 else str(wis_mod)

        # 1. Warrior of Mercy
        if subclass_name == "Warrior of Mercy" and monk_level >= 3:
            subclass_details["warrior_of_mercy"] = {
                "hand_of_healing_formula": f"1{ma_die}{wis_str}",
                "hand_of_harm_formula": f"1{ma_die}{wis_str}",
                "physicians_touch": monk_level >= 6,
                "flurry_of_healing_and_harm": monk_level >= 11,
                "hand_of_ultimate_mercy": monk_level >= 17,
            }
            touch_extra = " Also end Blinded, Deafened, Paralyzed, Poisoned, or Stunned." if monk_level >= 6 else ""
            stats["actions"].append({
                "name": "Hand of Healing",
                "action": "Magic Action (or replace 1 Flurry strike)",
                "cost": "1 FP (or 0 FP with Flurry)",
                "effect": f"Heal creature touched for 1{ma_die}{wis_str} HP.{touch_extra}",
            })
            harm_extra = " Also inflicts Poisoned condition until end of next turn." if monk_level >= 6 else ""
            stats["actions"].append({
                "name": "Hand of Harm",
                "action": "Special (1/turn on Unarmed Strike hit)",
                "cost": "1 Focus Point",
                "effect": f"Deal extra 1{ma_die}{wis_str} Necrotic damage.{harm_extra}",
            })
            if monk_level >= 11:
                stats["actions"].append({
                    "name": "Flurry of Healing & Harm",
                    "action": "Special (with Flurry of Blows)",
                    "uses": max(1, wis_mod),
                    "recharge": "Long Rest",
                    "effect": f"Replace each Flurry strike with Hand of Healing (0 FP) AND apply Hand of Harm without expending FP ({max(1, wis_mod)} uses/LR).",
                })
            if monk_level >= 17:
                stats["actions"].append({
                    "name": "Hand of Ultimate Mercy",
                    "action": "Magic Action",
                    "cost": "5 Focus Points",
                    "uses": 1,
                    "recharge": "Long Rest",
                    "effect": f"Touch a creature dead within 24 hours to revive it with 4d10{wis_str} HP and clear debilitating conditions (1/LR).",
                })

        # 2. Warrior of Shadow
        elif subclass_name == "Warrior of Shadow" and monk_level >= 3:
            subclass_details["warrior_of_shadow"] = {
                "darkness_cost": "1 Focus Point",
                "shadow_step": monk_level >= 6,
                "improved_shadow_step": monk_level >= 11,
                "cloak_of_shadows": monk_level >= 17,
            }
            stats["actions"].append({
                "name": "Shadow Arts: Darkness",
                "action": "Magic Action",
                "cost": "1 Focus Point",
                "effect": "Cast Darkness without components. You can see through it, and move it 60 ft at start of each turn.",
            })
            if monk_level >= 6:
                stats["actions"].append({
                    "name": "Shadow Step",
                    "action": "Bonus Action",
                    "cost": "Free",
                    "effect": "Teleport up to 60 ft between Dim Light or Darkness; gain Advantage on next melee attack.",
                })
            if monk_level >= 11:
                stats["actions"].append({
                    "name": "Improved Shadow Step",
                    "action": "Bonus Action",
                    "cost": "1 Focus Point",
                    "effect": "Teleport up to 60 ft regardless of lighting, and make an Unarmed Strike as part of the bonus action.",
                })
            if monk_level >= 17:
                stats["actions"].append({
                    "name": "Cloak of Shadows",
                    "action": "Magic Action",
                    "cost": "3 Focus Points",
                    "effect": "In Dim Light/Darkness: become Invisible, move through occupied spaces, and Flurry of Blows costs 0 FP for 1 minute.",
                })

        # 3. Warrior of the Elements
        elif subclass_name == "Warrior of the Elements" and monk_level >= 3:
            subclass_details["warrior_of_the_elements"] = {
                "elemental_attunement": True,
                "elemental_burst": monk_level >= 6,
                "stride_of_the_elements": monk_level >= 11,
                "elemental_epitome": monk_level >= 17,
            }
            stats["actions"].append({
                "name": "Elemental Attunement",
                "action": "Special (start of turn)",
                "cost": "1 Focus Point",
                "effect": f"For 10 min: +10 ft reach on Unarmed Strikes, deal Acid/Cold/Fire/Lightning/Thunder, and push or pull target 10 ft on STR save (DC {stats['focus_save_dc']}).",
            })
            if monk_level >= 6:
                stats["actions"].append({
                    "name": "Elemental Burst",
                    "action": "Magic Action",
                    "cost": "2 Focus Points",
                    "effect": f"20-ft radius sphere within 120 ft deals 3{ma_die} elemental damage (Acid, Cold, Fire, Lightning, or Thunder); DEX save DC {stats['focus_save_dc']} for half.",
                })
            if monk_level >= 11:
                stats["active_perks"].append("Stride of the Elements (Fly Speed and Swim Speed equal to Speed while Elemental Attunement active)")
            if monk_level >= 17:
                stats["active_perks"].append(f"Elemental Epitome (Elemental Resistance; Step of the Wind deals 1{ma_die} on passing within 5 ft; +1{ma_die} damage 1/turn)")

        # 4. Warrior of the Open Hand
        elif subclass_name == "Warrior of the Open Hand" and monk_level >= 3:
            subclass_details["warrior_of_the_open_hand"] = {
                "open_hand_technique": True,
                "wholeness_of_body": monk_level >= 6,
                "fleet_step": monk_level >= 11,
                "quivering_palm": monk_level >= 17,
            }
            stats["actions"].append({
                "name": "Open Hand Technique",
                "action": "Special (on Flurry hit)",
                "cost": "Free",
                "effect": f"Addle (no OA until next turn), Push (STR save DC {stats['focus_save_dc']} or 15 ft push), or Topple (DEX save DC {stats['focus_save_dc']} or Prone).",
            })
            if monk_level >= 6:
                stats["actions"].append({
                    "name": "Wholeness of Body",
                    "action": "Bonus Action",
                    "uses": max(1, wis_mod),
                    "recharge": "Long Rest",
                    "effect": f"Regain 1{ma_die}{wis_str} HP ({max(1, wis_mod)} uses/LR).",
                })
            if monk_level >= 11:
                stats["active_perks"].append("Fleet Step (Take Step of the Wind immediately after another Bonus Action)")
            if monk_level >= 17:
                stats["actions"].append({
                    "name": "Quivering Palm",
                    "action": "Special (on hit 4 FP, then Action/Attack to end)",
                    "cost": "4 Focus Points",
                    "effect": f"Set lethal vibrations in target. End vibrations: target makes CON save DC {stats['focus_save_dc']}, taking 10d12 Force damage (or half on save).",
                })

        # 5. Warrior of Venom (UA Supplement)
        elif subclass_name == "Warrior of Venom" and monk_level >= 3:
            subclass_details["warrior_of_venom"] = {
                "envenom_weapon": True,
                "toxic_touch": monk_level >= 6,
                "toxin_refiner": monk_level >= 11,
                "toxic_blood": monk_level >= 11,
                "hallucinogenic_breath": monk_level >= 17,
            }
            stats["actions"].append({
                "name": "Envenom Weapon",
                "action": "Special (start of turn)",
                "cost": "1 Focus Point",
                "effect": f"Coat weapon for 1 min: Slowing Toxin (halved speed, no reactions, action or bonus action only) or Venom (+2{ma_die} Poison or Acid damage).",
            })
            if monk_level >= 6:
                stats["actions"].append({
                    "name": "Toxic Touch",
                    "action": "Magic Action",
                    "cost": "1 Focus Point",
                    "effect": f"Touch creature: CON save DC {stats['focus_save_dc']} or Poisoned for 1 min with Intoxicant (Charmed), Sedative (Unconscious), or Truth Serum (cannot lie).",
                })
            if monk_level >= 11:
                stats["active_perks"].append(f"Toxin Refiner (Immunity to Poison; taking poison adds +1{ma_die} to Envenom; ingesting poison heals 1{ma_die})")
                stats["active_perks"].append(f"Toxic Blood (Melee attacker takes 1d6 Poison damage, or 1{ma_die} if Bloodied)")
            if monk_level >= 17:
                stats["actions"].append({
                    "name": "Hallucinogenic Breath",
                    "action": "Special (replace 1 attack)",
                    "cost": "2 Focus Points",
                    "effect": f"Target within 30 ft: CON save DC {stats['focus_save_dc']} or 3{ma_die} Poison damage & Frightened/fleeing for 1 min (half damage on save).",
                })

        # 6. Warrior of the Mystic Arts (AU Supplement)
        elif subclass_name == "Warrior of the Mystic Arts" and monk_level >= 3:
            mystic_dc = 8 + pb + wis_mod
            mystic_attack = pb + wis_mod
            subclass_details["warrior_of_the_mystic_arts"] = {
                "spellcasting_ability": "Wisdom",
                "spell_save_dc": mystic_dc,
                "spell_attack_bonus": mystic_attack,
                "mystic_fighting_style": monk_level >= 6,
                "mystic_focus": monk_level >= 6,
                "focused_strike": monk_level >= 11,
                "improved_mystic_fighting_style": monk_level >= 17,
            }
            if monk_level >= 6:
                stats["actions"].append({
                    "name": "Mystic Fighting Style",
                    "action": "Special (Attack action)",
                    "effect": "Replace one Unarmed Strike with a casting of an action Sorcerer cantrip.",
                })
                stats["actions"].append({
                    "name": "Mystic Focus",
                    "action": "Special / Bonus Action",
                    "effect": "Expend spell slot to regain slot-level Focus Points (no action), or spend 2 FP for lv 1 slot / 3 FP for lv 2 slot as Bonus Action.",
                })
            if monk_level >= 11:
                stats["active_perks"].append("Focused Strike (Stunning Strike grants target Disadvantage on saves against your spells)")
            if monk_level >= 17:
                stats["actions"].append({
                    "name": "Improved Mystic Fighting Style",
                    "action": "Special (with Flurry of Blows)",
                    "effect": "Replace two Flurry Unarmed Strikes with casting a level 1 or 2 Sorcerer spell as part of the bonus action.",
                })

        stats["subclass_details"] = subclass_details
        return stats

    def calculate_processed_ability_scores(self) -> Dict[str, Dict[str, Any]]:
        """Calculate ability scores with modifiers and saving throws."""
        raw_scores = dict(self.ability_scores.final_scores)
        level = self.character_data.get("level", 1)
        proficiency_bonus = self.calculate_proficiency_bonus(level)

        # Apply feat/feature ability bonuses (e.g., Actor CHA+1, Resilient, ASI)
        for bonus in self.character_data.get("ability_bonuses", []):
            ability = bonus.get("ability")
            try:
                value = int(bonus.get("value", 0))
                minimum = int(bonus.get("minimum", 0))
            except (TypeError, ValueError):
                continue
            if ability in raw_scores:
                if value != 0 or minimum > 0:
                    raw_scores[ability] = max(raw_scores[ability] + value, minimum)
                    # Cap at maximum (20 for normal feats, 30 for epic boons)
                    max_cap = int(bonus.get("maximum", 20))
                    raw_scores[ability] = min(raw_scores[ability], max_cap)

        # Get saving throw proficiencies from class + effects
        class_data = self.character_data.get("class_data")
        if class_data is None:
            class_data = {}
        saving_throw_profs = list(class_data.get("saving_throw_proficiencies", []))
        # Include save proficiencies granted by effects (e.g., Resilient feat)
        for ability in self.character_data.get("proficiencies", {}).get("saving_throws", []):
            if ability not in saving_throw_profs:
                saving_throw_profs.append(ability)

        species_bonuses = getattr(self.ability_scores, "species_bonuses", {}) or {}
        background_bonuses = (
            getattr(self.ability_scores, "background_bonuses", {}) or {}
        )
        additional_modifiers = (
            getattr(self.ability_scores, "additional_modifiers", {}) or {}
        )
        base_scores = getattr(self.ability_scores, "base_scores", {}) or {}

        processed_scores = {}
        for ability_name, score in raw_scores.items():
            ability_lower = ability_name.lower()
            modifier = self.calculate_ability_modifier(score)
            is_proficient = ability_name in saving_throw_profs
            saving_throw_bonus = modifier + (proficiency_bonus if is_proficient else 0)

            processed_scores[ability_lower] = {
                "score": score,
                "modifier": modifier,
                "saving_throw": saving_throw_bonus,
                "saving_throw_proficient": is_proficient,
                "base_score": base_scores.get(ability_name, score),
                "species_bonus": species_bonuses.get(ability_name, 0),
                "background_bonus": background_bonuses.get(ability_name, 0),
                "additional_modifier": additional_modifiers.get(ability_name, 0),
            }

        return processed_scores

    @staticmethod
    def _normalize_skill_name(name: str) -> str:
        """Normalize a skill name to lowercase with spaces for case-insensitive comparison.

        Handles variants stored as "Sleight of Hand", "sleight_of_hand",
        "Sleight Of Hand", etc. by collapsing all forms to "sleight of hand".
        """
        return name.replace("_", " ").lower()

    def calculate_skills(self) -> Dict[str, Dict[str, Any]]:
        """Calculate skill bonuses with proficiency and expertise."""
        ability_scores = self.calculate_processed_ability_scores()
        # Get skill proficiencies from the correct location
        proficiencies = self.character_data.get("proficiencies", {})
        skill_proficiencies = proficiencies.get("skills", [])
        skill_expertise = self.character_data.get("skill_expertise", [])
        proficiency_sources = self.character_data.get("proficiency_sources", {})
        skill_sources = proficiency_sources.get("skills", {})
        proficiency_bonus = self.calculate_proficiency_bonus(
            self.character_data.get("level", 1)
        )
        bard_level = self._get_class_level("Bard")
        has_jack_of_all_trades = bard_level >= 2

        # Build normalized (lowercase, space-separated) lookup sets so that
        # "Sleight of Hand", "Sleight Of Hand", and "sleight_of_hand" all match
        # the skill key "sleight_of_hand" correctly.
        norm = self._normalize_skill_name
        skill_prof_normalized = {norm(s) for s in skill_proficiencies}
        skill_exp_normalized = {norm(s) for s in skill_expertise}
        # Map normalized name → original stored name for source lookups
        skill_sources_normalized = {norm(k): v for k, v in skill_sources.items()}

        skills = {}
        for skill, ability in self.skill_abilities.items():
            skill_norm = norm(skill)

            # Check proficiency and expertise with normalized comparison
            proficient = skill_norm in skill_prof_normalized
            expertise = skill_norm in skill_exp_normalized

            # Determine source of proficiency
            source = "None"
            if proficient:
                source = skill_sources_normalized.get(skill_norm, "Class")

            # Calculate bonus
            ability_modifier = ability_scores[ability]["modifier"]
            prof_bonus = 0
            jack_of_all_trades = False
            if expertise:
                prof_bonus = proficiency_bonus * 2
            elif proficient:
                prof_bonus = proficiency_bonus
            elif has_jack_of_all_trades:
                prof_bonus = proficiency_bonus // 2
                jack_of_all_trades = True

            bonus = ability_modifier + prof_bonus

            skills[skill] = {
                "proficient": proficient,
                "expertise": expertise,
                "bonus": bonus,
                "modifier": bonus,
                "ability": ability,
                "source": source,
            }
            if jack_of_all_trades:
                skills[skill]["jack_of_all_trades"] = True

        return skills

    def calculate_weapon_attacks(self) -> List[Dict[str, Any]]:
        """Calculate attack stats for all weapons in inventory."""
        attacks = []
        equipment = self.character_data.get("equipment") or {
            "weapons": [],
            "armor": [],
            "items": [],
            "gold": 0,
        }
        all_weapons = equipment.get("weapons", [])
        has_explicit_equipped = any("equipped" in w for w in all_weapons)
        active_weapons = [
            w for w in all_weapons if (w.get("equipped", True) if has_explicit_equipped else True)
        ]

        ability_scores = self.calculate_processed_ability_scores()
        proficiencies = self.character_data.get("proficiencies") or {
            "weapons": [],
            "armor": [],
            "skills": [],
        }
        weapon_profs = proficiencies.get("weapons", [])
        level = self.character_data.get("level", 1)
        proficiency_bonus = self.calculate_proficiency_bonus(level)

        barbarian_level = self._get_class_level("Barbarian")
        barbarian_rage_damage = 0
        if barbarian_level >= 16:
            barbarian_rage_damage = 4
        elif barbarian_level >= 9:
            barbarian_rage_damage = 3
        elif barbarian_level >= 1:
            barbarian_rage_damage = 2

        cleric_level = self._get_class_level("Cleric")
        cleric_divine_strike_dice = None
        if cleric_level >= 7:
            choices_made = self.character_data.get("choices_made", {})
            blessed_strike = choices_made.get("blessed_strikes")
            if not blessed_strike:
                for k, v in choices_made.items():
                    if "blessed_strikes" in k.lower() and isinstance(v, str):
                        blessed_strike = v
                        break
            if blessed_strike == "Divine Strike":
                cleric_divine_strike_dice = "2d8" if cleric_level >= 14 else "1d8"

        druid_level = self._get_class_level("Druid")
        druid_primal_strike_dice = None
        if druid_level >= 7:
            choices_made = self.character_data.get("choices_made", {})
            elemental_fury = choices_made.get("elemental_fury")
            if not elemental_fury:
                for k, v in choices_made.items():
                    if "elemental_fury" in k.lower() and isinstance(v, str):
                        elemental_fury = v
                        break
            if elemental_fury == "Primal Strike":
                druid_primal_strike_dice = "2d8" if druid_level >= 15 else "1d8"

        fighter_level = self._get_class_level("Fighter")
        fighter_subclass = self._get_class_subclass("Fighter")
        fighter_crit_threshold = 20
        if fighter_subclass == "Champion" and fighter_level >= 3:
            fighter_crit_threshold = 18 if fighter_level >= 15 else 19

        monk_level = self._get_class_level("Monk")
        monk_subclass = self._get_class_subclass("Monk")

        for weapon in active_weapons:
            weapon_name = (
                weapon.get("display_name")
                if weapon.get("is_inventory")
                else weapon.get("name")
            ) or weapon.get("name")
            weapon_props = weapon.get("properties", {})
            item_attack_bonus = int(weapon.get("attack_bonus", 0) or 0)
            item_damage_bonus = int(weapon.get("damage_bonus", 0) or 0)

            # Determine ability modifier
            category = weapon_props.get("category", "")
            properties = weapon_props.get("properties", [])
            is_monk_weapon = category == "Simple Melee" or (
                category == "Martial Melee" and "Light" in properties
            )

            if "Finesse" in properties:
                str_mod = ability_scores.get("strength", {}).get("modifier", 0)
                dex_mod = ability_scores.get("dexterity", {}).get("modifier", 0)
                ability_mod = max(str_mod, dex_mod)
                ability_name = f"STR/DEX ({'STR' if str_mod >= dex_mod else 'DEX'})"
            elif "Ranged" in category:
                ability_mod = ability_scores.get("dexterity", {}).get("modifier", 0)
                ability_name = "DEX"
            else:
                str_mod = ability_scores.get("strength", {}).get("modifier", 0)
                dex_mod = ability_scores.get("dexterity", {}).get("modifier", 0)
                if self.character_data.get("monk_dexterous_attacks") and is_monk_weapon:
                    ability_mod = max(str_mod, dex_mod)
                    ability_name = f"STR/DEX ({'STR' if str_mod >= dex_mod else 'DEX'})"
                else:
                    ability_mod = str_mod
                    ability_name = "STR"

            for override in self.character_data.get("attack_ability_overrides", []):
                selected_weapon = self.character_data["choices_made"].get(
                    override["weapon_tag"]
                )
                if selected_weapon != weapon_name:
                    continue
                ability = override["ability"].lower()
                override_mod = ability_scores.get(ability, {}).get("modifier", 0)
                if override_mod > ability_mod:
                    ability_mod = override_mod
                    ability_name = override["ability"].upper()[:3]

            # Check proficiency
            is_proficient = self._has_weapon_proficiency(weapon_props, weapon_profs)
            prof_bonus = proficiency_bonus if is_proficient else 0

            # Calculate attack bonus
            attack_bonus = ability_mod + prof_bonus + item_attack_bonus

            # Apply bonus_attack effects from features (e.g., Archery fighting style)
            # Phase 6: read from structured field, not applied_effects.
            for entry in self.character_data.get("attack_bonuses", []):
                weapon_property = entry.get("weapon_property")
                if weapon_property:
                    # Check if weapon matches the property requirement
                    if weapon_property == "Ranged" and "Ranged" in category:
                        attack_bonus += entry.get("value", 0)
                    elif weapon_property in properties:
                        attack_bonus += entry.get("value", 0)
                else:
                    # No condition, applies to all weapons
                    attack_bonus += entry.get("value", 0)

            # Calculate damage
            damage_dice = weapon_props.get("damage", "1d4")
            martial_arts_die = self.character_data.get("martial_arts_die")
            if is_monk_weapon and martial_arts_die:
                base_avg = self._calculate_average_damage(damage_dice, 0)
                ma_avg = self._calculate_average_damage(martial_arts_die, 0)
                if ma_avg > base_avg:
                    damage_dice = martial_arts_die
            damage_bonus = ability_mod + item_damage_bonus
            damage_type = weapon_props.get("damage_type", "Bludgeoning")

            # Phase 6: apply bonus_damage effects from features (e.g. Dueling,
            # Thrown Weapon Fighting). Dispatch is purely by the effect's
            # `condition` string — no feature name is matched. The local
            # `one_handed_melee_bonus` accumulator exists so dual-wielding can
            # exclude that condition's bonus from offhand damage, per RAW.
            damage_notes = []
            if item_damage_bonus > 0:
                damage_notes.append(f"+{item_damage_bonus} weapon bonus")
            if item_attack_bonus > 0:
                damage_notes.append(f"+{item_attack_bonus} to hit")
            one_handed_melee_bonus = 0  # Excluded from dual-wield offhand (RAW: Dueling)

            for entry in self.character_data.get("damage_bonuses", []):
                condition = entry.get("condition", "")

                # Check if condition is met for this weapon
                applies = False
                if condition == "one handed melee weapon":
                    # Effect-driven: any bonus_damage with this condition
                    # qualifies (Dueling is the canonical example). Display
                    # as if used alone (dual-wielding shown separately).
                    is_melee = "Ranged" not in category
                    is_one_handed = "Two-Handed" not in properties

                    if is_melee and is_one_handed:
                        applies = True
                        # Track this condition's bonus to exclude from dual-wield
                        one_handed_melee_bonus = entry.get("value", 0)
                elif condition == "thrown weapon ranged attack":
                    # Thrown Weapon Fighting: Check if weapon has Thrown property
                    # The "Thrown" property means it can be used for ranged attacks
                    # (even if weapon category is "Melee")
                    # Property appears as "Thrown (range X/Y)" in the list
                    #
                    # IMPORTANT: Only apply to pure thrown weapons OR the separate
                    # throw damage calculation. For melee weapons with Thrown property,
                    # we'll show separate "throw_damage" field with this bonus.
                    is_melee = "Melee" in category
                    has_thrown = any("Thrown" in prop for prop in properties)

                    # Only apply to main damage if it's NOT a melee weapon
                    # (pure thrown weapons without melee option get the bonus on main damage)
                    if has_thrown and not is_melee:
                        applies = True
                elif not condition:
                    # No condition, applies to all
                    applies = True

                if applies:
                    bonus_value = entry.get("value", 0)
                    damage_bonus += bonus_value
                    source_name = entry.get("source", "Unknown")
                    damage_notes.append(f"+{bonus_value} from {source_name}")

            # Format damage string with bonus if non-zero
            if damage_bonus > 0:
                damage_str = f"{damage_dice} + {damage_bonus}"
            elif damage_bonus < 0:
                damage_str = f"{damage_dice} - {abs(damage_bonus)}"
            else:
                damage_str = damage_dice

            # Check for Great Weapon Fighting (affects average damage for Two-Handed/Versatile weapons)
            # Phase 6: read from structured fighting-style flags.
            has_gwf = False
            if self.character_data.get("fighting_style_flags", {}).get("great_weapon_fighting"):
                # Check if weapon qualifies (melee with Two-Handed or Versatile)
                is_melee = "Ranged" not in category
                is_two_handed = "Two-Handed" in properties
                is_versatile = any("Versatile" in prop for prop in properties)

                if is_melee and (is_two_handed or is_versatile):
                    has_gwf = True
                    damage_notes.append("Can reroll 1s and 2s (GWF)")

            # Calculate average damage (adjusted for GWF if applicable)
            avg_damage = self._calculate_average_damage(
                damage_dice, damage_bonus, has_gwf=has_gwf
            )
            avg_crit = self._calculate_average_damage(
                damage_dice, damage_bonus, is_crit=True, has_gwf=has_gwf
            )

            # Check for Thrown weapons that can also be used in melee
            # Show separate "Throw Damage" calculation
            throw_damage_str = None
            avg_throw_damage = None
            has_thrown = any("Thrown" in prop for prop in properties)
            is_melee = "Melee" in category

            if has_thrown and is_melee:
                # Calculate throw damage (without Dueling, with Thrown Weapon Fighting if active)
                throw_bonus = ability_mod + item_damage_bonus
                throw_notes = []

                # Check for Thrown Weapon Fighting bonus
                # Phase 6: read from structured damage_bonuses.
                for entry in self.character_data.get("damage_bonuses", []):
                    if entry.get("condition", "") == "thrown weapon ranged attack":
                        bonus_value = entry.get("value", 0)
                        throw_bonus += bonus_value
                        source_name = entry.get("source", "Unknown")
                        throw_notes.append(f"+{bonus_value} from {source_name}")

                # Format throw damage string
                if throw_bonus > 0:
                    throw_damage_str = f"{damage_dice} + {throw_bonus}"
                elif throw_bonus < 0:
                    throw_damage_str = f"{damage_dice} - {abs(throw_bonus)}"
                else:
                    throw_damage_str = damage_dice

                avg_throw_damage = self._calculate_average_damage(
                    damage_dice, throw_bonus
                )

            # Check for Versatile weapons - show one-handed and two-handed damage
            versatile_die = None
            damage_one_handed_str = None
            damage_two_handed_str = None
            avg_one_handed = None
            avg_two_handed = None

            for prop in properties:
                if "Versatile" in prop:
                    # Parse versatile die (e.g., "Versatile (1d8)")
                    import re

                    match = re.search(r"\((\d+d\d+)\)", prop)
                    if match:
                        versatile_die = match.group(1)
                        if is_monk_weapon and martial_arts_die:
                            vers_avg = self._calculate_average_damage(versatile_die, 0)
                            ma_avg = self._calculate_average_damage(martial_arts_die, 0)
                            if ma_avg > vers_avg:
                                versatile_die = martial_arts_die

                        # One-handed damage (use current damage calculation)
                        damage_one_handed_str = damage_str
                        avg_one_handed = avg_damage

                        # Two-handed damage (use versatile die with GWF if active)
                        two_handed_bonus = ability_mod + item_damage_bonus

                        # Dueling doesn't apply when using two hands
                        # But other bonuses might apply
                        # For now, just use ability mod (no Dueling for two-handed)
                        if two_handed_bonus > 0:
                            damage_two_handed_str = (
                                f"{versatile_die} + {two_handed_bonus}"
                            )
                        elif two_handed_bonus < 0:
                            damage_two_handed_str = (
                                f"{versatile_die} - {abs(two_handed_bonus)}"
                            )
                        else:
                            damage_two_handed_str = versatile_die

                        # Apply GWF to two-handed versatile use
                        avg_two_handed = self._calculate_average_damage(
                            versatile_die, two_handed_bonus, has_gwf=has_gwf
                        )
                    break

            # Get weapon mastery if available
            mastery = weapon_props.get("mastery")
            
            # Get quantity from weapon equipment entry
            weapon_quantity = weapon.get("quantity", 1)

            # If Barbarian, Strength-based melee attacks gain Rage Damage bonus while Raging
            is_melee = "Ranged" not in category
            uses_strength = "STR" in ability_name and not ability_name.endswith("(DEX)")
            rage_bonus_value = barbarian_rage_damage if (barbarian_rage_damage > 0 and is_melee and uses_strength) else 0
            if rage_bonus_value > 0:
                damage_notes.append(f"+{rage_bonus_value} while Raging")
            if cleric_divine_strike_dice:
                damage_notes.append(f"+{cleric_divine_strike_dice} Divine Strike (Radiant or Necrotic, 1/turn)")
            if druid_primal_strike_dice:
                damage_notes.append(f"+{druid_primal_strike_dice} Primal Strike (Cold, Fire, Lightning, or Thunder, 1/turn)")
            if self._get_class_subclass("Druid") == "Circle of Spores" and druid_level >= 3:
                damage_notes.append("+1d6 Necrotic (Symbiotic Entity while active, 1/turn)")
            if fighter_crit_threshold < 20:
                damage_notes.append(f"Crit on {fighter_crit_threshold}-20")
            if fighter_subclass == "Psi Warrior" and fighter_level >= 3:
                psi_die = "d12" if fighter_level >= 17 else ("d10" if fighter_level >= 11 else ("d8" if fighter_level >= 5 else "d6"))
                int_mod = ability_scores.get("intelligence", {}).get("modifier", 0)
                int_str = f"+{int_mod}" if int_mod >= 0 else str(int_mod)
                damage_notes.append(f"+1{psi_die}{int_str} Force (Psionic Strike, 1/turn)")
            if fighter_subclass == "Hell Knight" and fighter_level >= 3:
                damage_notes.append("+1d6 Infernal Wound (Cold, Fire, or Necrotic, 1/turn)")
            if monk_subclass == "Warrior of Venom" and monk_level >= 3 and is_monk_weapon:
                ma_d = "1d12" if monk_level >= 17 else ("1d10" if monk_level >= 11 else ("1d8" if monk_level >= 5 else "1d6"))
                damage_notes.append(f"Envenom Weapon (1 FP): Slowing Toxin or +2{ma_d} Poison/Acid")

            attack_info = {
                "name": weapon_name,
                "attack_bonus": attack_bonus,
                "attack_bonus_display": f"+{attack_bonus}"
                if attack_bonus >= 0
                else str(attack_bonus),
                "damage": damage_str,
                "damage_bonus": damage_bonus,
                "damage_type": damage_type,
                "avg_damage": avg_damage,
                "avg_crit": avg_crit,
                "properties": properties,
                "ability": ability_name,
                "effective_ability": "DEX" if (dex_mod > str_mod and ("(DEX)" in ability_name or ability_name == "DEX")) else ("STR" if "(STR)" in ability_name or ability_name == "STR" else ability_name[:3]),
                "proficient": is_proficient,
                "mastery": mastery,
                "icon": self._get_weapon_icon(weapon_name),
                "damage_notes": damage_notes,
                "quantity": weapon_quantity,  # Store quantity for dual wield check
                "_damage_dice": damage_dice,  # Store for offhand calculation
                "_ability_mod": ability_mod,  # Store for offhand calculation
                "_one_handed_melee_bonus": one_handed_melee_bonus,  # Excluded from dual-wield
            }
            if fighter_crit_threshold < 20:
                attack_info["crit_threshold"] = fighter_crit_threshold
            if rage_bonus_value > 0:
                attack_info["rage_damage_bonus"] = rage_bonus_value

            # Add thrown damage if applicable
            if throw_damage_str:
                attack_info["throw_damage"] = throw_damage_str
                attack_info["avg_throw_damage"] = avg_throw_damage

            # Add versatile damage options if applicable
            if versatile_die:
                attack_info["damage_one_handed"] = damage_one_handed_str
                attack_info["damage_two_handed"] = damage_two_handed_str
                attack_info["avg_one_handed"] = avg_one_handed
                attack_info["avg_two_handed"] = avg_two_handed

            attacks.append(attack_info)

        # Add Unarmed Strike
        # Base unarmed strike: 1 + STR modifier
        # With Unarmed Fighting: 1d6 + STR (or 1d8 + STR if no weapons/shield)
        # With Martial Arts (Monk): martial_arts_die + max(STR, DEX)
        # With College of Dance (Bard): 1{inspiration_die} + max(STR, DEX)
        str_mod = ability_scores.get("strength", {}).get("modifier", 0)
        dex_mod = ability_scores.get("dexterity", {}).get("modifier", 0)
        # Phase 6: read from structured fighting-style flags.
        has_unarmed_fighting = bool(
            self.character_data.get("fighting_style_flags", {}).get("unarmed_fighting")
        )
        martial_arts_die = self.character_data.get("martial_arts_die")

        bard_level = self._get_class_level("Bard")
        bard_subclass = self._get_class_subclass("Bard") or ""
        is_dance_bard = bard_subclass == "College of Dance" and bard_level >= 3
        dance_die = None
        if is_dance_bard:
            dance_die = "d12" if bard_level >= 15 else ("d10" if bard_level >= 10 else ("d8" if bard_level >= 5 else "d6"))

        # Determine the damage die and ability modifier for the unarmed strike
        if martial_arts_die:
            # Monk: Martial Arts die + max(STR, DEX) (Dexterous Attacks)
            unarmed_mod = max(str_mod, dex_mod)
            unarmed_damage_dice = martial_arts_die
        elif is_dance_bard and dance_die:
            # College of Dance Bard: Bardic Damage 1{die} + max(STR, DEX)
            unarmed_mod = max(str_mod, dex_mod)
            unarmed_damage_dice = f"1{dance_die}"
        elif has_unarmed_fighting:
            unarmed_mod = str_mod
            has_weapons_or_shield = len(all_weapons) > 0
            armor_list = equipment.get("armor", [])
            has_shield = any("Shield" in armor.get("name", "") for armor in armor_list)
            unarmed_damage_dice = "1d6" if (has_weapons_or_shield or has_shield) else "1d8"
        else:
            unarmed_mod = str_mod
            unarmed_damage_dice = None

        # Format damage string and calculate averages
        if unarmed_damage_dice:
            # Shared formatting for die-based unarmed strikes
            if unarmed_mod > 0:
                unarmed_damage_str = f"{unarmed_damage_dice} + {unarmed_mod}"
            elif unarmed_mod < 0:
                unarmed_damage_str = f"{unarmed_damage_dice} - {abs(unarmed_mod)}"
            else:
                unarmed_damage_str = unarmed_damage_dice
            unarmed_avg = self._calculate_average_damage(unarmed_damage_dice, unarmed_mod)
            unarmed_crit_avg = self._calculate_average_damage(
                unarmed_damage_dice, unarmed_mod, is_crit=True
            )
        else:
            # Base unarmed strike: 1 + STR modifier
            unarmed_damage_base = 1 + str_mod
            if unarmed_damage_base > 0:
                unarmed_damage_str = str(unarmed_damage_base)
            else:
                unarmed_damage_str = "0"  # Minimum 0 damage

            unarmed_avg = float(max(0, 1 + str_mod))
            unarmed_crit_avg = float(
                max(0, 1 + str_mod)
            )  # Unarmed crits don't double the base 1

        unarmed_attack_bonus = unarmed_mod + proficiency_bonus

        unarmed_notes = []
        if is_dance_bard and dance_die:
            unarmed_notes.append("Bardic Damage (roll BI die without expending)")
        if has_unarmed_fighting and not martial_arts_die and not is_dance_bard:
            if has_weapons_or_shield or has_shield:
                unarmed_notes.append("1d8 if no weapons or shield equipped")
            else:
                unarmed_notes.append("1d6 if wielding weapons or shield")
            unarmed_notes.append("1d4 damage to grappled creature (start of turn)")

        unarmed_ability = "DEX" if ((martial_arts_die or is_dance_bard) and dex_mod > str_mod) else "STR"
        unarmed_rage_bonus = barbarian_rage_damage if (barbarian_rage_damage > 0 and unarmed_ability == "STR") else 0
        if unarmed_rage_bonus > 0:
            unarmed_notes.append(f"+{unarmed_rage_bonus} while Raging")
        if fighter_crit_threshold < 20:
            unarmed_notes.append(f"Crit on {fighter_crit_threshold}-20")
        if monk_level >= 6:
            unarmed_notes.append("Empowered Strikes (can deal Force damage)")
        if monk_subclass == "Warrior of the Elements" and monk_level >= 3:
            unarmed_notes.append("Elemental Attunement (+10 ft reach, can deal Acid/Cold/Fire/Lightning/Thunder, push/pull 10 ft)")
        if monk_subclass == "Warrior of Mercy" and monk_level >= 3:
            wis_m = ability_scores.get("wisdom", {}).get("modifier", 0)
            wis_s = f"+{wis_m}" if wis_m >= 0 else str(wis_m)
            poison_s = "; +Poisoned at lv 6+" if monk_level >= 6 else ""
            ma_d = "1d12" if monk_level >= 17 else ("1d10" if monk_level >= 11 else ("1d8" if monk_level >= 5 else "1d6"))
            unarmed_notes.append(f"+1{ma_d}{wis_s} Necrotic (Hand of Harm, 1 FP, 1/turn{poison_s})")

        unarmed_attack = {
            "name": "Unarmed Strike",
            "attack_bonus": unarmed_attack_bonus,
            "attack_bonus_display": f"+{unarmed_attack_bonus}"
            if unarmed_attack_bonus >= 0
            else str(unarmed_attack_bonus),
            "damage": unarmed_damage_str,
            "damage_type": "Bludgeoning",
            "avg_damage": unarmed_avg,
            "avg_crit": unarmed_crit_avg,
            "properties": [],
            "ability": unarmed_ability,
            "effective_ability": unarmed_ability,
            "proficient": True,  # Everyone is proficient with unarmed strikes
            "mastery": None,
            "icon": "/static/images/weapons/strike.svg",
            "damage_notes": unarmed_notes,
        }
        if fighter_crit_threshold < 20:
            unarmed_attack["crit_threshold"] = fighter_crit_threshold
        if unarmed_rage_bonus > 0:
            unarmed_attack["rage_damage_bonus"] = unarmed_rage_bonus

        attacks.append(unarmed_attack)

        # Check if character has 2+ light weapons for dual wielding
        # Create combination cards for each pair
        light_weapons = [atk for atk in attacks if "Light" in atk.get("properties", [])]

        combinations = []
        
        # Check if any single light weapon has quantity >= 2 (e.g., 2 daggers)
        for weapon in light_weapons:
            if weapon.get("quantity", 1) >= 2:
                # Can dual wield with itself
                combo = self._create_dual_wield_combo(
                    weapon, weapon, proficiency_bonus
                )
                combinations.append(combo)
        
        # Create combinations for different light weapons
        if len(light_weapons) >= 2:
            # Create all possible combinations of light weapons
            for i, weapon1 in enumerate(light_weapons):
                for weapon2 in light_weapons[i + 1 :]:
                    # Create combination card
                    combo = self._create_dual_wield_combo(
                        weapon1, weapon2, proficiency_bonus
                    )
                    combinations.append(combo)

        combinations.sort(
            key=lambda combo: (
                (combo.get("mainhand", {}).get("avg_damage") or 0)
                + (combo.get("offhand", {}).get("avg_damage") or 0),
                (combo.get("mainhand", {}).get("attack_bonus") or 0)
                + (combo.get("offhand", {}).get("attack_bonus") or 0),
            ),
            reverse=True,
        )
        for index, combo in enumerate(combinations, start=1):
            combo["rank"] = index
            combo["recommended"] = index == 1

        # Clean up temporary fields for all attacks
        for attack in attacks:
            attack.pop("_damage_dice", None)
            attack.pop("_ability_mod", None)
            attack.pop("_one_handed_melee_bonus", None)
            attack.pop("quantity", None)  # Remove quantity from final attack data

        return {"attacks": attacks, "combinations": combinations}

    def _create_dual_wield_combo(
        self, weapon1: Dict[str, Any], weapon2: Dict[str, Any], proficiency_bonus: int
    ) -> Dict[str, Any]:
        """Create a dual-wield combination card for two light weapons."""
        # Calculate mainhand attack (weapon1)
        mh_damage_dice = weapon1.get("_damage_dice", "1d4")
        mh_ability_mod = weapon1.get("_ability_mod", 0)
        mh_attack_bonus = weapon1.get("attack_bonus")

        # Mainhand damage: ability mod but NO Dueling
        if mh_ability_mod > 0:
            mh_damage = f"{mh_damage_dice} + {mh_ability_mod}"
        elif mh_ability_mod < 0:
            mh_damage = f"{mh_damage_dice} - {abs(mh_ability_mod)}"
        else:
            mh_damage = mh_damage_dice

        # Mainhand average (no GWF adjustment needed here - applied to individual weapons)
        mh_avg_damage = self._calculate_average_damage(mh_damage_dice, mh_ability_mod)

        # Calculate offhand attack (weapon2)
        oh_damage_dice = weapon2.get("_damage_dice", "1d4")
        oh_ability_mod = weapon2.get("_ability_mod", 0)
        oh_attack_bonus = weapon2.get("attack_bonus")

        # Check for Two-Weapon Fighting style (adds ability mod to offhand)
        # Phase 6: read from structured fighting-style flags.
        has_two_weapon_fighting = bool(
            self.character_data.get("fighting_style_flags", {}).get("two_weapon_fighting_modifier")
        )

        # Offhand damage:
        # - With Two-Weapon Fighting: add full ability mod
        # - Without: dice only (but include negative modifier)
        if has_two_weapon_fighting:
            # Add full ability modifier
            if oh_ability_mod > 0:
                oh_damage = f"{oh_damage_dice} + {oh_ability_mod}"
            elif oh_ability_mod < 0:
                oh_damage = f"{oh_damage_dice} - {abs(oh_ability_mod)}"
            else:
                oh_damage = oh_damage_dice
            oh_damage_bonus = oh_ability_mod
        else:
            # Dice only (unless negative)
            if oh_ability_mod < 0:
                oh_damage = f"{oh_damage_dice} - {abs(oh_ability_mod)}"
                oh_damage_bonus = oh_ability_mod
            else:
                oh_damage = oh_damage_dice
                oh_damage_bonus = 0

        # Offhand average (no GWF adjustment needed here - applied to individual weapons)
        oh_avg_damage = self._calculate_average_damage(oh_damage_dice, oh_damage_bonus)

        # Check if the one-handed-melee condition bonus was applied to either
        # weapon (Dueling fighting style is the canonical source). Used only
        # for the user-facing footnote.
        has_one_handed_melee_bonus = (
            weapon1.get("_one_handed_melee_bonus", 0) > 0
            or weapon2.get("_one_handed_melee_bonus", 0) > 0
        )
        
        # Create combination name
        if weapon1["name"] == weapon2["name"]:
            combo_name = f"Two {weapon1['name']}s"
        else:
            combo_name = f"{weapon1['name']} & {weapon2['name']}"

        return {
            "type": "combination",
            "name": combo_name,
            "mainhand": {
                "name": weapon1["name"],
                "attack_bonus": mh_attack_bonus,
                "attack_bonus_display": f"+{mh_attack_bonus}"
                if mh_attack_bonus >= 0
                else str(mh_attack_bonus),
                "damage": mh_damage,
                "damage_type": weapon1["damage_type"],
                "avg_damage": mh_avg_damage,
                "icon": weapon1["icon"],
            },
            "offhand": {
                "name": weapon2["name"],
                "attack_bonus": oh_attack_bonus,
                "attack_bonus_display": f"+{oh_attack_bonus}"
                if oh_attack_bonus >= 0
                else str(oh_attack_bonus),
                "damage": oh_damage,
                "damage_type": weapon2["damage_type"],
                "avg_damage": oh_avg_damage,
                "icon": weapon2["icon"],
            },
            "notes": ["Dueling bonus does not apply when dual-wielding"]
            if has_one_handed_melee_bonus
            else [],
        }

    def _has_weapon_proficiency(
        self, weapon_props: Dict[str, Any], weapon_proficiencies: List[str]
    ) -> bool:
        weapon_name = weapon_props.get("name", "")
        weapon_properties = weapon_props.get("properties", [])
        weapon_category = weapon_props.get("category", "")
        prof_required = weapon_props.get("proficiency_required", "")
        if not prof_required:
            if "simple" in weapon_category.lower():
                prof_required = "Simple weapons"
            elif "martial" in weapon_category.lower():
                prof_required = "Martial weapons"

        # Check specific weapon proficiency first
        if weapon_name in weapon_proficiencies:
            return True

        # Check category proficiency
        if prof_required in weapon_proficiencies:
            return True

        # Check conditional proficiencies (e.g., "Martial weapons that have the Light property", "Martial weapons with Finesse or Light property")
        for prof in weapon_proficiencies:
            prof_lower = prof.lower()
            separator = None
            if " with " in prof_lower:
                separator = " with "
            elif " that have " in prof_lower:
                separator = " that have "
            elif " that has " in prof_lower:
                separator = " that has "
            
            if separator:
                parts = prof_lower.split(separator)
                if len(parts) == 2:
                    weapon_type = parts[0].strip()  # e.g., "martial weapons"
                    property_requirement = parts[1].replace("the ", "").strip()
                    
                    # Check if weapon matches the base type (Simple/Martial)
                    weapon_cat_lower = weapon_category.lower()
                    type_matches = False
                    if "simple" in weapon_type and "simple" in weapon_cat_lower:
                        type_matches = True
                    elif "martial" in weapon_type and "martial" in weapon_cat_lower:
                        type_matches = True
                    
                    if type_matches:
                        # Check if weapon has any of the required properties
                        if " or " in property_requirement:
                            required_props = [p.strip().replace(" property", "") 
                                            for p in property_requirement.split(" or ")]
                            for req_prop in required_props:
                                req_prop_capitalized = req_prop.capitalize()
                                if req_prop_capitalized in weapon_properties:
                                    return True
                                if any(req_prop_capitalized.lower() in prop.lower() 
                                      for prop in weapon_properties):
                                    return True
                        else:
                            # Single property requirement
                            req_prop = property_requirement.replace(" property", "").strip().capitalize()
                            if req_prop in weapon_properties:
                                return True
                            if any(req_prop.lower() in prop.lower() for prop in weapon_properties):
                                return True

        return False

    def _calculate_average_damage(
        self, dice_expr: str, bonus: int, is_crit: bool = False, has_gwf: bool = False
    ) -> float:
        """Calculate average damage from a dice expression.

        Args:
            dice_expr: Dice expression (e.g., "1d6", "2d8")
            bonus: Flat bonus damage
            is_crit: Whether this is a critical hit (doubles dice)
            has_gwf: Whether Great Weapon Fighting applies (reroll 1s and 2s)
        """
        try:
            if "d" not in dice_expr:
                return float(bonus)

            parts = dice_expr.lower().split("d")
            num_dice = int(parts[0]) if parts[0] else 1
            die_size = int(parts[1])

            # For crits, double the number of dice
            if is_crit:
                num_dice *= 2

            # Average of a die
            if has_gwf:
                # Great Weapon Fighting: reroll 1s and 2s
                # Expected value = (2/N)*avg_reroll + sum(3 to N)/N
                # Where avg_reroll is the normal die average
                avg_all = (1 + die_size) / 2.0
                sum_3_to_n = sum(range(3, die_size + 1))
                avg_per_die = (2 * avg_all + sum_3_to_n) / die_size
            else:
                avg_per_die = (1 + die_size) / 2.0

            total_avg = (num_dice * avg_per_die) + bonus

            return round(total_avg, 1)
        except (ValueError, IndexError):
            return float(bonus)

    def _get_weapon_icon(self, weapon_name: str) -> str:
        """Get the appropriate weapon icon path for a weapon name."""
        if not weapon_name:
            return "/static/images/weapons/sword.svg"

        weapon_lower = weapon_name.lower()

        # Weapon icon mappings
        icon_mappings = {
            "club": "club.svg",
            "dagger": "dagger.svg",
            "dart": "dart.svg",
            "greatclub": "club.svg",
            "handaxe": "axe.svg",
            "javelin": "spear.svg",
            "light_hammer": "hammer.svg",
            "mace": "mace.svg",
            "quarterstaff": "staff.svg",
            "sickle": "sickle.svg",
            "spear": "spear.svg",
            "crossbow_light": "crossbow.svg",
            "shortbow": "bow.svg",
            "battleaxe": "axe.svg",
            "flail": "flail.svg",
            "glaive": "polearm.svg",
            "greataxe": "axe.svg",
            "greatsword": "sword.svg",
            "halberd": "polearm.svg",
            "lance": "lance.svg",
            "longsword": "sword.svg",
            "maul": "hammer.svg",
            "morningstar": "mace.svg",
            "pike": "spear.svg",
            "rapier": "rapier.svg",
            "scimitar": "scimitar.svg",
            "shortsword": "sword.svg",
            "trident": "trident.svg",
            "war_pick": "pick.svg",
            "warhammer": "hammer.svg",
            "whip": "whip.svg",
            "crossbow_hand": "crossbow.svg",
            "crossbow_heavy": "crossbow.svg",
            "longbow": "bow.svg",
            "unarmed_strike": "strike.svg",
        }

        # Try exact match first
        normalized_name = weapon_lower.replace(" ", "_").replace("-", "_")
        if normalized_name in icon_mappings:
            return f"/static/images/weapons/{icon_mappings[normalized_name]}"

        # Try partial matches
        for key, icon in icon_mappings.items():
            if key in normalized_name or normalized_name in key:
                return f"/static/images/weapons/{icon}"

        # Default icon
        return "/static/images/weapons/sword.svg"

    def calculate_combat_stats(self) -> Dict[str, Any]:
        """Calculate combat statistics."""
        ability_scores = self.calculate_processed_ability_scores()
        equipment = self.character_data.get("equipment") or {
            "weapons": [],
            "armor": [],
            "items": [],
            "gold": 0,
        }
        level = self.character_data.get("level", 1)

        # Basic combat stats
        dex_modifier = ability_scores["dexterity"]["modifier"]
        wis_modifier = ability_scores["wisdom"]["modifier"]
        constitution_score = self.ability_scores.final_scores.get("Constitution", 10)

        # Calculate HP with bonuses
        class_name = self.character_data.get("class", "")
        class_data = self.character_data.get("class_data", {})
        hp_bonuses = self._extract_hp_bonuses()
        class_rows = self.character_data.get("class_breakdown")
        if isinstance(class_rows, list) and len(class_rows) > 1:
            hp_breakdown = self._get_multiclass_hp_breakdown(
                class_rows,
                constitution_score,
                hp_bonuses,
            )
        else:
            hp_breakdown = self.hp_calculator.get_hp_breakdown(
                class_name, constitution_score, hp_bonuses, level
            )
        max_hp = hp_breakdown["total_hp"]

        # Calculate AC using the full options system (handles armor, shield, effects)
        ac_options = self.calculate_ac_options()
        armor_ac = ac_options[0]["ac"] if ac_options else (10 + dex_modifier)

        # Speed (default 30, can be modified by species/features)
        speed = self.character_data.get("speed", 30)

        # Hit dice
        hit_die = class_data.get("hit_die", 8) if class_data else 8
        if isinstance(class_rows, list) and len(class_rows) > 1:
            hit_dice_parts = []
            for row in class_rows:
                row_class = row.get("class_name", "")
                row_level = row.get("level", 1)
                row_class_data = self._load_class_data(row_class) or {}
                row_hit_die = row_class_data.get("hit_die", self.hp_calculator.CLASS_HIT_DICE.get(row_class, 8))
                hit_dice_parts.append(f"{row_level}d{row_hit_die}")
            hit_dice_total = " + ".join(hit_dice_parts)
        else:
            hit_dice_total = f"{level}d{hit_die}"

        # Proficiency bonus
        proficiency_bonus = self.calculate_proficiency_bonus(level)
        initiative_bonus = self._calculate_initiative_bonus(
            dex_modifier,
            proficiency_bonus,
        )

        perception_bonus = (
            self.calculate_skills().get("perception", {}).get("modifier", wis_modifier)
        )

        best_option = ac_options[0] if ac_options else {}
        return {
            "armor_class": armor_ac,
            "uses_shield": bool(best_option.get("shield", False)),
            "initiative": initiative_bonus,  # For backward compatibility
            "initiative_bonus": initiative_bonus,
            "speed": speed,
            "hit_point_maximum": max_hp,  # For backward compatibility
            "hit_points": {"current": max_hp, "maximum": max_hp, "temporary": 0},
            "hp_breakdown": hp_breakdown,
            "hit_dice": {"total": hit_dice_total, "spent": 0},
            "passive_perception": 10 + perception_bonus,
        }

    @staticmethod
    def _modifier_tone(modifier: int) -> str:
        if modifier > 0:
            return "positive"
        if modifier < 0:
            return "negative"
        return "neutral"

    @staticmethod
    def _format_signed(value: int) -> str:
        return f"+{value}" if value >= 0 else str(value)

    def get_ability_generation_state(self) -> Dict[str, Any]:
        """Return display/validation state for the frontend ability step."""
        choices = self.character_data.get("choices_made", {})
        method = choices.get("ability_scores_method", "standard_array")
        raw_scores = choices.get("ability_scores")
        scores = raw_scores if isinstance(raw_scores, dict) else {}

        ability_rows: Dict[str, Dict[str, Any]] = {}
        for ability in ABILITIES:
            score = scores.get(ability, self.ability_scores.base_scores.get(ability, 8))
            try:
                score_int = int(score)
            except (TypeError, ValueError):
                score_int = 8
            modifier = self.calculate_ability_modifier(score_int)
            ability_rows[ability] = {
                "score": score_int,
                "modifier": modifier,
                "modifier_display": self._format_signed(modifier),
                "modifier_tone": self._modifier_tone(modifier),
            }

        standard_array = [15, 14, 13, 12, 10, 8]
        selected = []
        for ability in ABILITIES:
            try:
                selected.append(int(scores.get(ability)))
            except (TypeError, ValueError):
                pass
        standard_complete = len(selected) == len(ABILITIES)
        standard_valid = standard_complete and sorted(selected) == sorted(standard_array)
        standard_available: Dict[str, List[int]] = {}
        for ability in ABILITIES:
            current = scores.get(ability)
            used_by_others = set()
            for other in ABILITIES:
                if other == ability:
                    continue
                try:
                    used_by_others.add(int(scores.get(other)))
                except (TypeError, ValueError):
                    continue
            standard_available[ability] = [
                value
                for value in standard_array
                if value == current or value not in used_by_others
            ]

        spent = 0
        for ability in ABILITIES:
            try:
                spent += POINT_BUY_COSTS.get(int(scores.get(ability)), 0)
            except (TypeError, ValueError):
                pass
        is_valid, point_buy_message = (
            validate_point_buy(scores) if isinstance(scores, dict) else (False, "Missing scores")
        )
        point_controls: Dict[str, Dict[str, Any]] = {}
        for ability in ABILITIES:
            score = ability_rows[ability]["score"]
            current_cost = POINT_BUY_COSTS.get(score, 0)
            next_score = score + 1
            prev_score = score - 1
            next_cost = POINT_BUY_COSTS.get(next_score)
            can_increment = (
                next_cost is not None
                and score < POINT_BUY_MAX
                and spent + next_cost - current_cost <= POINT_BUY_TOTAL
            )
            can_decrement = prev_score in POINT_BUY_COSTS and score > POINT_BUY_MIN
            point_controls[ability] = {
                "current_cost": current_cost,
                "can_increment": can_increment,
                "can_decrement": can_decrement,
                "increment_score": next_score if can_increment else None,
                "decrement_score": prev_score if can_decrement else None,
            }

        asi = self.get_background_asi_options()
        asi_total = int(asi.get("total_points", 0) or 0)
        stored_bonuses = choices.get("background_bonuses")
        stored_bonuses = stored_bonuses if isinstance(stored_bonuses, dict) else {}
        asi_spent = 0
        for value in stored_bonuses.values():
            try:
                asi_spent += max(0, int(value))
            except (TypeError, ValueError):
                pass
        asi_options = asi.get("ability_options") or ABILITIES
        asi_values_by_ability: Dict[str, List[int]] = {}
        for ability in asi_options:
            try:
                current = int(stored_bonuses.get(ability, 0) or 0)
            except (TypeError, ValueError):
                current = 0
            asi_values_by_ability[ability] = [
                value
                for value in range(0, 3)
                if asi_spent - current + value <= asi_total
            ]

        return {
            "method": method,
            "abilities": ability_rows,
            "standard_array": {
                "values": standard_array,
                "assigned_count": len(selected),
                "complete": standard_complete,
                "valid": standard_valid,
                "available_values_by_ability": standard_available,
            },
            "point_buy": {
                "total": POINT_BUY_TOTAL,
                "min": POINT_BUY_MIN,
                "max": POINT_BUY_MAX,
                "spent": spent,
                "remaining": POINT_BUY_TOTAL - spent,
                "valid": is_valid,
                "message": point_buy_message,
                "controls": point_controls,
            },
            "manual": {"min": 3, "max": 18},
            "background_asi": {
                "spent": asi_spent,
                "remaining": asi_total - asi_spent,
                "values_by_ability": asi_values_by_ability,
            },
        }

    def roll_ability_scores(self) -> List[Dict[str, Any]]:
        """Roll six 4d6-drop-lowest ability score candidates for the UI."""
        rolls = []
        for _ in range(6):
            dice = sorted((random.randint(1, 6) for _ in range(4)), reverse=True)
            score = sum(dice[:3])
            modifier = self.calculate_ability_modifier(score)
            rolls.append({
                "value": score,
                "dice": dice,
                "modifier": modifier,
                "modifier_display": self._format_signed(modifier),
                "modifier_tone": self._modifier_tone(modifier),
            })
        return rolls

    @staticmethod
    def _parse_primary_abilities(primary: Any) -> Dict[str, Any]:
        if not isinstance(primary, str) or not primary.strip():
            return {"kind": "and", "abilities": []}
        trimmed = primary.strip()
        or_re = r"\s+or\s+|\s*/\s*"
        and_re = r"\s*&\s*|\s+and\s+"
        if re.search(or_re, trimmed, re.IGNORECASE):
            return {
                "kind": "or",
                "abilities": [p.strip() for p in re.split(or_re, trimmed, flags=re.IGNORECASE) if p.strip()],
            }
        if re.search(and_re, trimmed, re.IGNORECASE):
            return {
                "kind": "and",
                "abilities": [p.strip() for p in re.split(and_re, trimmed, flags=re.IGNORECASE) if p.strip()],
            }
        return {"kind": "and", "abilities": [trimmed]}

    def _current_prerequisite_scores(self) -> Dict[str, int] | None:
        choices = self.character_data.get("choices_made", {})
        if not isinstance(choices.get("ability_scores"), dict):
            return None
        processed = self.calculate_processed_ability_scores()
        scores: Dict[str, int] = {}
        for ability in ABILITIES:
            row = processed.get(ability.lower()) or {}
            scores[ability] = int(row.get("score", 0) or 0)
        return scores

    def evaluate_multiclass_prerequisites(
        self,
        candidate_class: Dict[str, Any],
        all_classes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate 2024 multiclass entry prerequisites for a candidate class."""
        scores = self._current_prerequisite_scores()
        if scores is None:
            return {"ok": True, "missing": [], "messages": [], "abilities_unknown": True}

        candidate_id = candidate_class.get("id") or candidate_class.get("name")
        by_id = {
            (entry.get("id") or entry.get("name")): entry
            for entry in all_classes
            if isinstance(entry, dict)
        }
        involved: List[Dict[str, Any]] = []
        for row in self._normalize_multiclass_rows(self.character_data.get("choices_made", {}).get("classes")):
            class_name = row.get("class_name")
            if not class_name or class_name == candidate_id:
                continue
            existing = by_id.get(class_name) or self._load_class_data(class_name) or {}
            if existing:
                involved.append(existing)
        involved.append(candidate_class)

        missing: Dict[str, int] = {}
        for cls in involved:
            parsed = self._parse_primary_abilities(cls.get("primary_ability"))
            abilities = parsed["abilities"]
            if not abilities:
                continue
            checks = [scores.get(ability, 0) >= 13 for ability in abilities]
            ok = any(checks) if parsed["kind"] == "or" else all(checks)
            if not ok:
                for ability in abilities:
                    if scores.get(ability, 0) < 13:
                        missing[ability] = scores.get(ability, 0)

        messages = [
            f"Requires {ability} 13+ (have {score})"
            for ability, score in missing.items()
        ]
        return {
            "ok": not missing,
            "missing": list(missing.keys()),
            "messages": messages,
            "abilities_unknown": False,
        }

    def evaluate_feat_prerequisite(
        self,
        prerequisite: Any,
        *,
        level: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Evaluate display warnings for a feat prerequisite string."""
        if not isinstance(prerequisite, str) or not prerequisite.strip():
            return {"met": True, "messages": [], "abilities_unknown": False}

        scores = self._current_prerequisite_scores()
        abilities_unknown = scores is None
        current_level = int(level or self.character_data.get("level", 1) or 1)
        messages: List[str] = []

        for part in [p.strip() for p in re.split(r"[,;]", prerequisite) if p.strip()]:
            level_match = re.search(r"(?:(\d+)(?:st|nd|rd|th)?\s+level|level\s+(\d+)\+?)", part, re.IGNORECASE)
            if level_match:
                required_level = int(level_match.group(1) or level_match.group(2))
                if current_level < required_level:
                    messages.append(
                        f"Requires level {required_level}. Current level: {current_level}."
                    )
                continue

            score_match = re.search(r"(\d+)\+", part)
            if not score_match or abilities_unknown:
                continue

            required_score = int(score_match.group(1))
            present = [
                ability
                for ability in ABILITIES
                if re.search(rf"\b{re.escape(ability)}\b", part, re.IGNORECASE)
            ]
            if not present:
                continue
            if re.search(r"\bor\b", part, re.IGNORECASE):
                if not any(scores.get(ability, 0) >= required_score for ability in present):
                    current = ", ".join(f"{ability} {scores.get(ability, 0)}" for ability in present)
                    messages.append(
                        f"Requires {' or '.join(present)} {required_score}+. Current: {current}."
                    )
                continue
            for ability in present:
                current = scores.get(ability, 0)
                if current < required_score:
                    messages.append(
                        f"Requires {ability} {required_score}+. Current {ability}: {current}."
                    )

        return {
            "met": not messages,
            "messages": messages,
            "abilities_unknown": abilities_unknown,
        }

    def _extract_hp_bonuses(self) -> List[Dict[str, Any]]:
        """Extract HP bonuses from effects and features.

        Phase 6: reads from the structured ``hp_bonuses`` field populated by
        ``_apply_effect``. Never reads ``applied_effects`` directly.
        """
        hp_bonuses = []
        for entry in self.character_data.get("hp_bonuses", []):
            hp_bonuses.append({
                "source": entry.get("source", "Unknown"),
                "value": entry.get("value", 0),
                "scaling": entry.get("scaling"),
                "source_type": entry.get("source_type"),
                "source_class_name": entry.get("source_class_name"),
            })

        return hp_bonuses

    def _build_initiative_bonus_entry(
        self,
        effect: Dict[str, Any],
        source_name: str,
        source_type: Optional[str],
        source_class_name: Optional[str],
    ) -> Dict[str, Any]:
        """Create the canonical structured entry for a bonus_initiative effect."""
        return {
            "value": effect.get("value", 0),
            "source": source_name,
            "source_type": source_type,
            "source_class_name": source_class_name,
        }

    def _calculate_initiative_bonus(
        self,
        dex_modifier: int,
        proficiency_bonus: int,
    ) -> int:
        """Calculate initiative from Dexterity plus structured initiative bonuses."""
        initiative_bonus = dex_modifier
        for entry in self.character_data.get("initiative_bonuses", []):
            value = entry.get("value", 0)
            if value == "proficiency":
                initiative_bonus += proficiency_bonus
            else:
                initiative_bonus += int(value)

        return initiative_bonus

    def _enrich_all_feature_choices(self, character_data: Dict[str, Any]) -> None:
        """Enrich all features with the choices made, option descriptions, and stats.

        Handles all feature choices across classes, subclasses, species, lineages,
        and supplements (e.g. Battle Master maneuvers, Arcane Archer shots,
        Hunter's Prey, Defensive Tactics, Divine Order, Primal Order, Metamagic, etc.).
        """
        choices_made = character_data.get("choices_made", {})
        features_dict = character_data.get("features", {})
        level = character_data.get("level", 1)
        pb = self.calculate_proficiency_bonus(level)

        def load_external(file_name: str, list_name: str) -> Dict[str, Any]:
            if not file_name or not list_name:
                return {}
            path = self._external_data_path(file_name)
            if path and path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        return d.get(list_name, {})
                except Exception:
                    pass
            return {}

        subclass_data = (
            character_data.get("subclass_data")
            or self.character_data.get("subclass_data")
            or {}
        )
        class_data = (
            character_data.get("class_data")
            or self.character_data.get("class_data")
            or {}
        )
        species_data = (
            character_data.get("species_data")
            or self.character_data.get("species_data")
            or {}
        )
        lineage_data = (
            character_data.get("lineage_data")
            or self.character_data.get("lineage_data")
            or {}
        )
        background_data = (
            character_data.get("background_data")
            or self.character_data.get("background_data")
            or {}
        )

        # Build lookup: feature_name -> (feature_def, source_data)
        feature_defs: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {}
        for sdata in [subclass_data, class_data, species_data, lineage_data, background_data]:
            if not sdata or not isinstance(sdata, dict):
                continue
            f_by_lvl = sdata.get("features_by_level", {})
            if isinstance(f_by_lvl, dict):
                for feats in f_by_lvl.values():
                    if isinstance(feats, dict):
                        for fname, fdef in feats.items():
                            if isinstance(fdef, dict):
                                feature_defs[fname] = (fdef, sdata)
            traits = sdata.get("traits", {})
            if isinstance(traits, dict):
                for tname, tdef in traits.items():
                    if isinstance(tdef, dict):
                        feature_defs[tname] = (tdef, sdata)

        for category, feature_list in features_dict.items():
            if not isinstance(feature_list, list):
                continue
            for feat in feature_list:
                if not isinstance(feat, dict):
                    continue
                raw_name = feat.get("name", "")
                base_name = raw_name.split(":")[0].strip()

                fdef_tuple = feature_defs.get(base_name) or feature_defs.get(raw_name)
                if not fdef_tuple:
                    continue
                fdef, sdata = fdef_tuple

                choices_config = fdef.get("choices")
                feature_options = fdef.get("options") or {}

                if not choices_config and not feature_options:
                    continue

                choice_items = []
                if isinstance(choices_config, dict):
                    choice_items.append(choices_config)
                elif isinstance(choices_config, list):
                    for c in choices_config:
                        if isinstance(c, dict):
                            choice_items.append(c)

                collected_chosen_options = []
                selected_names = []

                for c_cfg in choice_items:
                    c_name = c_cfg.get("name", base_name.lower().replace(" ", "_"))
                    candidate_keys = [
                        c_name,
                        f"subclass_{base_name}_{c_name}",
                        f"subclass_{base_name}",
                        f"class_{base_name}_{c_name}",
                        f"class_{base_name}",
                        base_name,
                        f"subclass_{c_name}",
                        f"class_{c_name}",
                    ]
                    val = None
                    for ck in candidate_keys:
                        if ck in choices_made:
                            val = choices_made[ck]
                            break
                    if val is None:
                        if c_name == "maneuvers":
                            val = character_data.get("maneuvers_known")
                        elif c_name == "arcane_shots":
                            val = character_data.get("arcane_shots_known")

                    if not val:
                        continue

                    val_list = val if isinstance(val, list) else [val]

                    source_cfg = c_cfg.get("source", {})
                    stype = source_cfg.get("type")
                    catalog = {}
                    if stype == "external":
                        catalog = load_external(source_cfg.get("file"), source_cfg.get("list"))
                    elif stype == "internal":
                        catalog = sdata.get(source_cfg.get("list"), {})
                    elif feature_options:
                        catalog = feature_options

                    for v in val_list:
                        if not isinstance(v, str) or not v:
                            continue
                        selected_names.append(v)
                        opt_desc = ""
                        if isinstance(catalog, dict) and v in catalog:
                            item_data = catalog[v]
                            if isinstance(item_data, dict):
                                opt_desc = item_data.get("description", "")
                            elif isinstance(item_data, str):
                                opt_desc = item_data
                        elif isinstance(feature_options, dict) and v in feature_options:
                            opt_desc = feature_options[v]

                        collected_chosen_options.append({
                            "name": v,
                            "description": opt_desc,
                            "choice_key": c_name,
                        })

                if not choice_items and feature_options:
                    c_name = base_name.lower().replace(" ", "_")
                    val = (
                        choices_made.get(c_name)
                        or choices_made.get(f"subclass_{base_name}")
                        or choices_made.get(f"class_{base_name}")
                        or choices_made.get(base_name)
                    )
                    if val:
                        val_list = val if isinstance(val, list) else [val]
                        for v in val_list:
                            if isinstance(v, str) and v:
                                selected_names.append(v)
                                collected_chosen_options.append({
                                    "name": v,
                                    "description": feature_options.get(v, ""),
                                    "choice_key": c_name,
                                })

                if not collected_chosen_options:
                    continue

                feat["chosen_options"] = collected_chosen_options

                # Update feature display name with all selected choices
                if selected_names:
                    feat["name"] = f"{base_name}: {', '.join(selected_names)}"

                base_desc = feat.get("description", "")
                extra_lines = []

                if base_name == "Combat Superiority":
                    str_mod = self.ability_scores.get_modifier("Strength")
                    dex_mod = self.ability_scores.get_modifier("Dexterity")
                    dc = 8 + max(str_mod, dex_mod) + pb
                    sup_dice = character_data.setdefault("superiority_dice", {})
                    count = sup_dice.get("count", 4)
                    die = sup_dice.get("die", "d8")
                    sup_dice["save_dc"] = dc
                    character_data["maneuvers"] = collected_chosen_options
                    if f"**Maneuver Save DC**: {dc}" not in base_desc:
                        extra_lines.append(f"\n\n**Superiority Dice**: {count} ({die}) | **Maneuver Save DC**: {dc}")
                    unadded = [opt for opt in collected_chosen_options if f"**{opt['name']}**" not in base_desc]
                    if unadded:
                        extra_lines.append("\n**Selected Maneuvers**:")
                        for opt in unadded:
                            desc_str = f": {opt['description']}" if opt['description'] else ""
                            extra_lines.append(f"• **{opt['name']}**{desc_str}")

                elif base_name == "Arcane Shot":
                    int_mod = self.ability_scores.get_modifier("Intelligence")
                    dc = 8 + int_mod + pb
                    uses = max(1, int_mod)
                    die = character_data.get("arcane_shot_die") or "d6"
                    character_data["arcane_shot_die"] = die
                    character_data["arcane_shot_dc"] = dc
                    character_data["arcane_shot_uses"] = uses
                    character_data["arcane_shots"] = collected_chosen_options
                    if f"**Save DC**: {dc}" not in base_desc:
                        extra_lines.append(f"\n\n**Arcane Shot Die**: {die} | **Save DC**: {dc} | **Uses**: {uses} per Short or Long Rest")
                    unadded = [opt for opt in collected_chosen_options if f"**{opt['name']}**" not in base_desc]
                    if unadded:
                        extra_lines.append("\n**Selected Arcane Shots**:")
                        for opt in unadded:
                            desc_str = f": {opt['description']}" if opt['description'] else ""
                            extra_lines.append(f"• **{opt['name']}**{desc_str}")

                else:
                    unadded = []
                    for opt in collected_chosen_options:
                        opt_name = opt["name"]
                        opt_desc_check = (opt.get("description") or "").strip()
                        if f"**{opt_name}**" in base_desc:
                            continue
                        if opt_desc_check and opt_desc_check in base_desc:
                            continue
                        if not opt_desc_check and opt_name in base_desc:
                            continue
                        unadded.append(opt)

                    if unadded:
                        if any(opt.get("description") for opt in unadded):
                            extra_lines.append("\n\n**Selected Options**:")
                            for opt in unadded:
                                desc_str = f": {opt['description']}" if opt['description'] else ""
                                extra_lines.append(f"• **{opt['name']}**{desc_str}")
                        else:
                            extra_lines.append(f"\n\n**Selected**: {', '.join([o['name'] for o in unadded])}")

                add_text = "\n".join(extra_lines)
                if add_text and add_text.strip() not in base_desc:
                    feat["description"] = (base_desc + add_text).strip()

        # Enrich Eldritch Invocations class feature
        inv_stats = character_data.get("eldritch_invocation_stats")
        if not inv_stats and (character_data.get("class") == "Warlock" or any(c.get("class_name") == "Warlock" for c in character_data.get("classes", []) if isinstance(c, dict))):
            inv_stats = self.calculate_eldritch_invocation_stats()
        inv_list = (inv_stats or {}).get("invocations", [])
        if inv_list:
            for category, feature_list in features_dict.items():
                if not isinstance(feature_list, list):
                    continue
                for feat in feature_list:
                    if not isinstance(feat, dict):
                        continue
                    raw_name = feat.get("name", "")
                    base_name = raw_name.split(":")[0].strip()
                    if base_name == "Eldritch Invocations":
                        feat["chosen_options"] = [
                            {
                                "name": inv.get("name", ""),
                                "description": inv.get("description", ""),
                                "choice_key": "eldritch_invocations",
                            }
                            for inv in inv_list
                        ]
                        names_summary = ", ".join(inv.get("name", "") for inv in inv_list if inv.get("name"))
                        feat["name"] = f"Eldritch Invocations: {names_summary}"
                        base_desc = feat.get("description", "")
                        if "**Selected Invocations**:" not in base_desc:
                            inv_lines = ["\n\n**Selected Invocations**:"]
                            for inv in inv_list:
                                n = inv.get("name", "")
                                d = inv.get("description", "")
                                desc_str = f": {d}" if d else ""
                                inv_lines.append(f"• **{n}**{desc_str}")
                            feat["description"] = (base_desc + "\n".join(inv_lines)).strip()

    # ==================== Export Methods ====================

    def to_character(self) -> Dict[str, Any]:
        """
        Export character as complete calculated data dictionary.
        This is the main method that returns character_data with all calculations.

        Returns:
            Complete character data with all calculated values
        """
        # Start with base character data
        character_data = deepcopy(self.character_data)

        # Phase 6: the structured bonus fields are *internal* calculation
        # inputs. They are derived purely from the effects already captured
        # in ``applied_effects`` (which is exported). Hiding them keeps the
        # exported sheet stable and avoids leaking calculation scaffolding
        # into API consumers.
        for _internal_key in (
            "damage_bonuses",
            "attack_bonuses",
            "ac_bonuses",
            "hp_bonuses",
            "initiative_bonuses",
            "alternative_ac_options",
            "fighting_style_flags",
            "attack_ability_overrides",
        ):
            character_data.pop(_internal_key, None)

        if not character_data.get("arcane_shots_known") and character_data.get("arcane_shot_die") is None:
            character_data.pop("arcane_shots_known", None)
            character_data.pop("arcane_shot_die", None)

        # Late-resolve choice_substitutions placeholders in features.
        # Species traits may have been applied before ancestry choices were stored.
        for category_features in character_data["features"].values():
            for feature in category_features:
                subs = feature.get("choice_substitutions")
                if subs and "{" in feature.get("description", ""):
                    for var_name, choice_name in subs.items():
                        choice_value = self._resolve_choice_value(choice_name)
                        if choice_value:
                            resolved = self._extract_parenthetical(choice_value)
                            feature["description"] = feature["description"].replace(
                                f"{{{var_name}}}", resolved
                            )

        # Add calculated ability scores
        character_data["ability_scores"] = self.ability_scores.final_scores
        character_data["abilities"] = self.calculate_processed_ability_scores()

        # Add calculated skills
        character_data["skills"] = self.calculate_skills()

        # Add calculated combat stats
        character_data["combat"] = self.calculate_combat_stats()
        if "climb_speed" in self.character_data:
            character_data["climb_speed"] = self.character_data["climb_speed"]
            character_data["combat"]["climb_speed"] = self.character_data["climb_speed"]
        if "swim_speed" in self.character_data:
            character_data["swim_speed"] = self.character_data["swim_speed"]
            character_data["combat"]["swim_speed"] = self.character_data["swim_speed"]

        # Add calculated weapon attacks and combinations
        weapon_data = self.calculate_weapon_attacks()
        character_data["attacks"] = weapon_data.get("attacks", [])
        character_data["attack_combinations"] = weapon_data.get("combinations", [])
        combinations = character_data["attack_combinations"]
        if combinations:
            character_data["best_attack_combination"] = combinations[0]

        # Add calculated AC options
        character_data["ac_options"] = self.calculate_ac_options()

        # Process spell data for template display
        spells = character_data.get("spells", {})
        spell_slots = spells.get("slots", {})
        spell_metadata = character_data.get("spell_metadata", {})

        ABILITY_NAMES = {"Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"}
        for ab in ABILITY_NAMES:
            spells.get("always_prepared", {}).pop(ab, None)
            spell_metadata.pop(ab, None)
            if isinstance(spells.get("prepared"), dict):
                spells["prepared"].get("cantrips", {}).pop(ab, None)
                spells["prepared"].get("spells", {}).pop(ab, None)
            spells.get("known", {}).pop(ab, None)
            spells.get("background_spells", {}).pop(ab, None)

        # Organize spells by level for display
        spells_by_level = {}

        # Process always_prepared spells (dict of spell_name -> metadata)
        for spell_name, spell_info in spells.get("always_prepared", {}).items():
            if not spell_name or spell_name in ABILITY_NAMES:
                continue
            spell_data = self._load_spell_definition(spell_name)
            if spell_data and spell_data.get("name") not in ABILITY_NAMES:
                # Merge with stored metadata
                spell_data.update(
                    {
                        "source": spell_info.get("source", "Unknown"),
                        "always_prepared": True,
                        "once_per_day": spell_info.get("once_per_day", False),
                        "once_per_long_rest": spell_info.get(
                            "once_per_long_rest", False
                        ),
                    }
                )
                if spell_info.get("spellcasting_ability"):
                    spell_data["spellcasting_ability"] = spell_info["spellcasting_ability"]
                level = spell_info.get("level", spell_data.get("level", 0))
                if level not in spells_by_level:
                    spells_by_level[level] = []
                spells_by_level[level].append(spell_data)

        # Process prepared spells (dict with cantrips and spells subdicts)
        prepared = spells.get("prepared", {})
        if isinstance(prepared, dict):
            # Process prepared cantrips
            for spell_name, spell_info in prepared.get("cantrips", {}).items():
                if not spell_name or spell_name in ABILITY_NAMES:
                    continue
                spell_data = self._load_spell_definition(spell_name)
                if spell_data and spell_data.get("name") not in ABILITY_NAMES:
                    meta = spell_metadata.get(spell_name, {})
                    spell_data.update(
                        {
                            "source": meta.get("source") or spell_info.get("source", "Selected"),
                            "always_prepared": meta.get("always_prepared", False),
                        }
                    )
                    if 0 not in spells_by_level:
                        spells_by_level[0] = []
                    spells_by_level[0].append(spell_data)

            # Process prepared spells
            for spell_name, spell_info in prepared.get("spells", {}).items():
                if not spell_name or spell_name in ABILITY_NAMES:
                    continue
                spell_data = self._load_spell_definition(spell_name)
                if spell_data and spell_data.get("name") not in ABILITY_NAMES:
                    meta = spell_metadata.get(spell_name, {})
                    spell_data.update(
                        {
                            "source": meta.get("source") or spell_info.get("source", "Selected"),
                            "always_prepared": meta.get("always_prepared", False),
                        }
                    )
                    level = spell_data.get("level", 1)
                    if level not in spells_by_level:
                        spells_by_level[level] = []
                    spells_by_level[level].append(spell_data)

        # Process known spells (dict of spell_name -> metadata)
        for spell_name, spell_info in spells.get("known", {}).items():
            if not spell_name or spell_name in ABILITY_NAMES:
                continue
            spell_data = self._load_spell_definition(spell_name)
            if spell_data and spell_data.get("name") not in ABILITY_NAMES:
                spell_data.update(spell_info)
                level = spell_info.get("level", spell_data.get("level", 1))
                if level not in spells_by_level:
                    spells_by_level[level] = []
                spells_by_level[level].append(spell_data)

        # Process background spells (dict of spell_name -> metadata)
        for spell_name, spell_info in spells.get("background_spells", {}).items():
            if not spell_name or spell_name in ABILITY_NAMES:
                continue
            spell_data = self._load_spell_definition(spell_name)
            if spell_data and spell_data.get("name") not in ABILITY_NAMES:
                spell_data.update(
                    {
                        "source": spell_info.get("source", "Background"),
                        "once_per_day": True,
                    }
                )
                level = spell_info.get("level", spell_data.get("level", 0))
                if level not in spells_by_level:
                    spells_by_level[level] = []
                spells_by_level[level].append(spell_data)


        character_data["spells_by_level"] = spells_by_level

        # Phase 7 (D0-1) / P2-4: apply per-spell range overrides (e.g. Eldritch
        # Spear changes Eldritch Blast's range to 300 feet). Reads from
        # spell_metadata[spell]["range_override"] (consolidated in P2-4).
        spell_meta = character_data.get("spell_metadata") or {}
        for spell_list in spells_by_level.values():
            for spell in spell_list:
                name = spell.get("name")
                meta = spell_meta.get(name) or {}
                range_override = meta.get("range_override")
                if range_override:
                    spell["range"] = range_override["range"]
                    spell["range_override_source"] = range_override["source"]

        # Phase 7 (D0-1) / P2-4: annotate per-spell damage bonuses (e.g. Agonizing
        # Blast adds Charisma to Eldritch Blast damage). Reads from
        # spell_metadata[spell]["damage_bonus"] (consolidated in P2-4).
        for spell_list in spells_by_level.values():
            for spell in spell_list:
                name = spell.get("name")
                meta = spell_meta.get(name) or {}
                damage_bonus = meta.get("damage_bonus")
                if damage_bonus:
                    spell["damage_ability_bonus"] = damage_bonus

        # Annotate per-spell ability, attack bonus, and save DC
        processed_abilities = self.calculate_processed_ability_scores()
        prof_bonus = self.calculate_proficiency_bonus(character_data.get("level", 1))
        class_data = character_data.get("class_data") or {}
        subclass_data = character_data.get("subclass_data") or {}
        class_spell_ability = (class_data.get("spellcasting_ability") if isinstance(class_data, dict) else None) or (subclass_data.get("spellcasting_ability") if isinstance(subclass_data, dict) else None)
        lineage_spell_ability = self.character_data.get("spellcasting_ability")
        feat_abilities = self.character_data.get("feat_spellcasting_abilities", {})

        for spell_list in spells_by_level.values():
            for spell in spell_list:
                s_name = spell.get("name")
                meta = spell_meta.get(s_name) or {}
                sp_ability = spell.get("spellcasting_ability") or meta.get("spellcasting_ability")
                source_str = str(spell.get("source", ""))
                if not sp_ability:
                    if source_str in feat_abilities:
                        sp_ability = feat_abilities[source_str]
                    elif source_str in (self.character_data.get("lineage"), self.character_data.get("species"), "Species", "Lineage"):
                        sp_ability = lineage_spell_ability
                    elif source_str in (self.character_data.get("class"), self.character_data.get("subclass"), "Class", "Subclass"):
                        sp_ability = class_spell_ability
                    elif class_spell_ability:
                        sp_ability = class_spell_ability

                if sp_ability:
                    spell["spellcasting_ability"] = sp_ability
                    ab_mod = processed_abilities.get(sp_ability.lower(), {}).get("modifier", 0)
                    spell["spell_save_dc"] = 8 + prof_bonus + ab_mod
                    spell["spell_attack_bonus"] = prof_bonus + ab_mod

        # For compatibility with tests: add 'cantrips' and 'level_1' keys to spells
        # 'cantrips' = all level 0 spells, 'level_1' = all level 1 spells
        cantrips_list = []
        level1_list = []
        for spell in spells_by_level.get(0, []):
            entry = spell.copy()
            entry["name"] = entry.get("name") or entry.get("spell") or entry.get("id")
            cantrips_list.append(entry)
        for spell in spells_by_level.get(1, []):
            entry = spell.copy()
            entry["name"] = entry.get("name") or entry.get("spell") or entry.get("id")
            level1_list.append(entry)
        character_data.setdefault("spells", {})["cantrips"] = cantrips_list
        character_data["spells"]["level_1"] = level1_list

        multiclass_spellcasting = self._calculate_multiclass_spell_slot_progression()

        # If spell_slots not in session data, compute from class/subclass data.
        if not spell_slots:
            if multiclass_spellcasting.get("is_multiclass"):
                spell_slots = multiclass_spellcasting.get("spell_slots", {})
            else:
                class_data = character_data.get("class_data") or {}
                subclass_data = character_data.get("subclass_data")
                level = self._get_primary_class_level()
                slots_source = class_data.get("spell_slots_by_level", {})
                if not slots_source and subclass_data:
                    slots_source = subclass_data.get("spell_slots_by_level", {})
                level_slots = slots_source.get(str(level), [])
                spell_slots = self._slots_payload_to_dict(level_slots)

        character_data["spell_slots"] = spell_slots
        if multiclass_spellcasting.get("pact_magic_slots"):
            character_data["pact_magic_slots"] = multiclass_spellcasting["pact_magic_slots"]
        if multiclass_spellcasting.get("notes"):
            character_data["spell_slot_notes"] = multiclass_spellcasting["notes"]

        # Add proficiency bonus (total character level for multiclass).
        character_data["proficiency_bonus"] = self.calculate_proficiency_bonus(
            character_data.get("level", 1)
        )

        # Expose darkvision range explicitly (0 = none; e.g. 60 = 60 ft).
        # The value is already tracked in character_data via grant_darkvision
        # effects; this line ensures a guaranteed int is always present.
        character_data["darkvision"] = int(character_data.get("darkvision", 0))

        # Add spellcasting stats
        character_data["spellcasting_stats"] = self.calculate_spellcasting_stats()

        # Add weapon mastery stats
        character_data["weapon_mastery_stats"] = self.calculate_weapon_mastery_stats()

        # Add Eldritch Invocation stats (Warlock only)
        character_data["eldritch_invocation_stats"] = self.calculate_eldritch_invocation_stats()

        # Add Replicate Magic Item stats (Artificer only)
        artificer_replications = self.calculate_artificer_replications_stats()
        if artificer_replications.get("has_replications"):
            character_data["artificer_replications"] = artificer_replications

        # Add Barbarian stats (Barbarian only)
        barbarian_stats = self.calculate_barbarian_stats()
        if barbarian_stats.get("has_rage"):
            character_data["barbarian_stats"] = barbarian_stats

        # Add Bard stats (Bard only)
        bard_stats = self.calculate_bard_stats()
        if bard_stats.get("has_bardic_inspiration"):
            character_data["bard_stats"] = bard_stats

        # Add Cleric stats (Cleric only)
        cleric_stats = self.calculate_cleric_stats()
        if cleric_stats.get("cleric_level", 0) > 0:
            character_data["cleric_stats"] = cleric_stats

        # Add Druid stats (Druid only)
        druid_stats = self.calculate_druid_stats()
        if druid_stats.get("druid_level", 0) > 0:
            character_data["druid_stats"] = druid_stats

        # Add Fighter stats (Fighter only)
        fighter_stats = self.calculate_fighter_stats()
        if fighter_stats.get("fighter_level", 0) > 0:
            character_data["fighter_stats"] = fighter_stats

        # Add Monk stats (Monk only)
        monk_stats = self.calculate_monk_stats()
        if monk_stats.get("monk_level", 0) > 0:
            character_data["monk_stats"] = monk_stats

        # Add applied effects for export
        if hasattr(self, "applied_effects") and self.applied_effects:
            effects_for_export = []
            for applied_effect in self.applied_effects:
                effect = applied_effect["effect"].copy()
                effect["source"] = applied_effect.get("source", "Unknown")
                effect["source_type"] = applied_effect.get("source_type", "Unknown")
                if applied_effect.get("source_class_name"):
                    effect["source_class_name"] = applied_effect["source_class_name"]
                effects_for_export.append(effect)
            character_data["effects"] = effects_for_export
        else:
            character_data["effects"] = []

        # Flatten proficiencies for easier template access
        proficiencies = character_data.get("proficiencies", {})
        character_data["languages"] = proficiencies.get("languages", [])
        character_data["skill_proficiencies"] = proficiencies.get("skills", [])
        character_data["weapon_proficiencies"] = proficiencies.get("weapons", [])
        character_data["armor_proficiencies"] = proficiencies.get("armor", [])
        character_data["tool_proficiencies"] = proficiencies.get("tools", [])

        # Include choices_made for web app compatibility
        character_data["choices_made"] = character_data.get("choices_made", {})

        # Include spell selections in choices_made for export/import
        spells = character_data.get("spells", {})
        prepared = spells.get("prepared", {})
        background_spells = spells.get("background_spells", {})

        spell_selections = {
            "cantrips": list(prepared.get("cantrips", {}).keys()),
            "spells": list(prepared.get("spells", {}).keys()),
            "background_cantrips": [
                name
                for name, data in background_spells.items()
                if data.get("level") == 0
            ],
            "background_spells": [
                name
                for name, data in background_spells.items()
                if data.get("level", 1) > 0
            ],
        }
        spellbook = spells.get("spellbook", {})
        if isinstance(spellbook, dict) and spellbook:
            spell_selections["spellbook"] = list(spellbook.keys())

        # Only include if there are any spell selections
        if any(spell_selections.values()):
            character_data["choices_made"]["spell_selections"] = spell_selections

        # Include weapon mastery selections in choices_made for export/import
        weapon_masteries = character_data.get("weapon_masteries", {})
        selected_masteries = weapon_masteries.get("selected", [])

        if selected_masteries:
            character_data["choices_made"]["weapon_mastery_selections"] = (
                selected_masteries
            )

        # Include Eldritch Invocation selections in choices_made for export/import
        eldritch_invocations = self._normalize_eldritch_invocation_selections(
            character_data.get("eldritch_invocations", {})
        ) or {"selected": [], "cantrip_choices": {}, "choices": {}}
        selected_invocations = eldritch_invocations["selected"]
        if selected_invocations:
            character_data["choices_made"]["eldritch_invocation_selections"] = {
                "selected": selected_invocations,
                "cantrip_choices": eldritch_invocations["cantrip_choices"],
                "choices": eldritch_invocations["choices"],
            }

        # Include Replicate Magic Item selections in choices_made for export/import
        replications = character_data.get("artificer_replications")
        if replications and replications.get("has_replications"):
            if replications.get("known_plans"):
                character_data["choices_made"]["artificer_replicate_plans"] = list(replications["known_plans"])
            if replications.get("active_items"):
                character_data["choices_made"]["artificer_active_replications"] = list(replications["active_items"])

        # Enrich all feature choices with option descriptions, calculated stats, and selections
        self._enrich_all_feature_choices(character_data)

        return character_data

    def to_json(self) -> Dict[str, Any]:
        """
        Legacy method - now calls to_character() for consistency.

        Returns:
            Complete character data as dictionary
        """
        return self.to_character()

    def from_json(self, data: dict):
        """
        Import character from JSON dictionary.

        Args:
            data: Character data dictionary
        """
        self.character_data = deepcopy(data)

        # Ensure weapon_masteries structure exists (for backwards compatibility)
        if "weapon_masteries" not in self.character_data:
            self.character_data["weapon_masteries"] = {
                "selected": [],
                "available": [],
                "max_count": 0,
            }

        # Ensure choices_made exists (for backwards compatibility)
        if "choices_made" not in self.character_data:
            self.character_data["choices_made"] = {}

        # Reconstruct ability scores
        # First check for ability_scores (raw scores exported by to_character)
        if "ability_scores" in data:
            self.ability_scores.set_base_scores(data["ability_scores"])

        # Also check for detailed abilities structure
        abilities = data.get("abilities", {})
        if abilities:
            if "base" in abilities:
                self.ability_scores.set_base_scores(abilities["base"])
            if "species_bonuses" in abilities:
                self.ability_scores.apply_species_bonuses(abilities["species_bonuses"])
            if "background_bonuses" in abilities:
                self.ability_scores.apply_background_bonuses(
                    abilities["background_bonuses"]
                )
            if "additional_modifiers" in abilities:
                self.ability_scores.apply_additional_modifiers(
                    abilities["additional_modifiers"]
                )

        # Restore applied_effects from exported effects array
        # This is critical for preserving effects across session save/restore cycles
        self.applied_effects = []
        if "effects" in data and isinstance(data["effects"], list):
            for effect in data["effects"]:
                if isinstance(effect, dict):
                    # Reconstruct the applied_effect structure
                    applied_effect = {
                        "type": effect.get("type"),  # Preserve top-level type
                        "effect": {
                            k: v
                            for k, v in effect.items()
                            if k not in ["source", "source_type", "source_class_name"]
                        },
                        "source": effect.get("source", "Unknown"),
                        "source_type": effect.get("source_type", "Unknown"),
                    }
                    if effect.get("source_class_name"):
                        applied_effect["source_class_name"] = effect["source_class_name"]
                    self.applied_effects.append(applied_effect)
        # Rebuild Phase 6 structured bonus fields from the restored audit log.
        self._rebuild_structured_bonuses()
        self._ensure_base_language()

    @classmethod
    def quick_create(
        cls,
        species: str,
        char_class: str,
        background: str,
        abilities: Dict[str, int],
        lineage: Optional[str] = None,
        subclass: Optional[str] = None,
        level: int = 1,
        spellcasting_ability: Optional[str] = None,
    ) -> "CharacterBuilder":
        """
        Factory method for quick character creation (useful for testing).

        Args:
            species: Species name
            char_class: Class name
            background: Background name
            abilities: Ability scores
            lineage: Optional lineage/variant name
            subclass: Optional subclass name
            level: Character level
            spellcasting_ability: Optional spellcasting ability for lineages

        Returns:
            Fully configured CharacterBuilder
        """
        builder = cls()
        builder.set_species(species)

        if lineage:
            builder.set_lineage(lineage, spellcasting_ability)

        builder.set_class(char_class, level)

        if subclass:
            builder.set_subclass(subclass)

        builder.set_background(background)
        builder.set_abilities(abilities)

        return builder

    # ==================== Validation & Query Methods ====================

    def is_complete(self) -> bool:
        """Check if character creation is complete."""
        return self.character_data["step"] == "complete"

    def get_current_step(self) -> str:
        """Get the current creation step."""
        return self.character_data["step"]

    def set_step(self, step: str) -> None:
        """
        Set the current creation step.

        Args:
            step: The step name ('class', 'species', 'lineage', etc.)
        """
        self.character_data["step"] = step

    def get_cantrips(self) -> List[str]:
        """Get list of known cantrips."""
        return self.character_data["spells"]["cantrips"]

    def get_spells(self) -> List[str]:
        """Get list of known spells."""
        return self.character_data["spells"]["known"]

    def get_proficiencies(self, prof_type: str) -> List[str]:
        """
        Get proficiencies of a specific type.

        Args:
            prof_type: Type of proficiency ('armor', 'weapons', 'skills', etc.)

        Returns:
            List of proficiencies
        """
        return self.character_data["proficiencies"].get(prof_type, [])

    def get_all_spells(self) -> Dict[int, List[Dict[str, Any]]]:
        """
        Gather all spells known by the character from various sources.

        Returns a dictionary mapping spell level (0 for cantrips, 1-9 for leveled spells)
        to a list of spell dictionaries containing name, school, components, description,
        source, and other metadata.

        Sources include:
        - Effects (grant_cantrip, grant_spell)
        - Prepared spells (domain/species spells)
        - Known spells
        - Class cantrips from choices
        - Bonus cantrips from grant_cantrip_choice effects
        - Subclass spells from effects

        Returns:
            Dictionary mapping spell level to list of spell dicts
        """
        spells_by_level = {}
        character = self.to_json()
        choices_made = character.get("choices_made", {})
        class_name = character.get("class", "")
        subclass_name = character.get("subclass")
        character_level = character.get("level", 1)

        # Helper to load spell definition
        def load_spell_definition(spell_name: str) -> Dict[str, Any]:
            """Load spell details from definitions folder."""
            spell_file = (
                self.data_dir
                / "spells"
                / "definitions"
                / f"{spell_name.lower().replace(' ', '_')}.json"
            )
            if spell_file.exists():
                spell_info = self._load_json_file(spell_file)
                return spell_info or {}
            return {}

        # 1) Add spells granted directly via character effects
        effects = character.get("effects", [])
        if isinstance(effects, list):
            for effect in effects:
                if not isinstance(effect, dict):
                    continue

                # Check min_level requirement
                min_level = effect.get("min_level")
                if isinstance(min_level, int) and character_level < min_level:
                    continue

                effect_type = effect.get("type")

                if effect_type == "grant_cantrip":
                    cantrip_name = effect.get("spell")
                    if not cantrip_name:
                        continue

                    # Avoid duplicates
                    if 0 in spells_by_level and any(
                        s.get("name") == cantrip_name for s in spells_by_level[0]
                    ):
                        continue

                    cantrip_info = load_spell_definition(cantrip_name)

                    if 0 not in spells_by_level:
                        spells_by_level[0] = []

                    spells_by_level[0].append(
                        {
                            "name": cantrip_name,
                            "school": cantrip_info.get("school", ""),
                            "casting_time": cantrip_info.get("casting_time", ""),
                            "range": cantrip_info.get("range", ""),
                            "components": cantrip_info.get("components", ""),
                            "duration": cantrip_info.get("duration", ""),
                            "description": cantrip_info.get("description", ""),
                            "source": effect.get("source", "Effects"),
                        }
                    )

                elif effect_type == "grant_spell":
                    spell_name = effect.get("spell")
                    spell_level = effect.get("level")
                    if not spell_name or not isinstance(spell_level, int):
                        continue

                    # Avoid duplicates
                    if spell_level in spells_by_level and any(
                        s.get("name") == spell_name
                        for s in spells_by_level[spell_level]
                    ):
                        continue

                    spell_info = load_spell_definition(spell_name)

                    if spell_level not in spells_by_level:
                        spells_by_level[spell_level] = []

                    spells_by_level[spell_level].append(
                        {
                            "name": spell_name,
                            "school": spell_info.get("school", ""),
                            "casting_time": spell_info.get("casting_time", ""),
                            "range": spell_info.get("range", ""),
                            "components": spell_info.get("components", ""),
                            "duration": spell_info.get("duration", ""),
                            "description": spell_info.get("description", ""),
                            "source": effect.get("source", "Effects"),
                        }
                    )

        # 2) Add spells from character['spells']['prepared'] (domain/species spells - always prepared)
        prepared_spells = character.get("spells", {}).get("prepared", [])
        spell_metadata = character.get("spell_metadata", {})

        if isinstance(prepared_spells, list):
            for spell_name in prepared_spells:
                if not spell_name or not isinstance(spell_name, str):
                    continue

                spell_info = load_spell_definition(spell_name)
                spell_level = spell_info.get("level", 1)

                if spell_level not in spells_by_level:
                    spells_by_level[spell_level] = []

                if not any(
                    s.get("name") == spell_name for s in spells_by_level[spell_level]
                ):
                    # Get metadata for this spell
                    metadata = spell_metadata.get(spell_name, {})
                    once_per_day = metadata.get("once_per_day", False)

                    # Determine the source from metadata
                    spell_source = metadata.get("source", "always_prepared")
                    if spell_source == "lineage":
                        lineage = character.get("lineage", "")
                        display_source = (
                            f"{lineage} Spells" if lineage else "Lineage Spells"
                        )
                    elif spell_source == "subclass":
                        display_source = (
                            f"{subclass_name} Spells"
                            if subclass_name
                            else "Subclass Spells"
                        )
                    else:
                        display_source = "Always Prepared"

                    spells_by_level[spell_level].append(
                        {
                            "name": spell_name,
                            "school": spell_info.get("school", ""),
                            "casting_time": spell_info.get("casting_time", ""),
                            "range": spell_info.get("range", ""),
                            "components": spell_info.get("components", ""),
                            "duration": spell_info.get("duration", ""),
                            "description": spell_info.get("description", ""),
                            "source": display_source,
                            "always_prepared": True,
                            "once_per_day": once_per_day,
                        }
                    )

        # 3) Add spells from character['spells']['known']
        known_spells = character.get("spells", {}).get("known", [])
        if isinstance(known_spells, list):
            for spell_name in known_spells:
                if not spell_name or not isinstance(spell_name, str):
                    continue

                spell_info = load_spell_definition(spell_name)
                spell_level = spell_info.get("level", 1)

                if spell_level not in spells_by_level:
                    spells_by_level[spell_level] = []

                if not any(
                    s.get("name") == spell_name for s in spells_by_level[spell_level]
                ):
                    spells_by_level[spell_level].append(
                        {
                            "name": spell_name,
                            "school": spell_info.get("school", ""),
                            "casting_time": spell_info.get("casting_time", ""),
                            "range": spell_info.get("range", ""),
                            "components": spell_info.get("components", ""),
                            "duration": spell_info.get("duration", ""),
                            "description": spell_info.get("description", ""),
                            "source": "Known Spells",
                        }
                    )

        # 4) Get class cantrips from choices
        cantrips = choices_made.get("cantrips", [])
        if not cantrips:
            # Try common feature names
            for key in ["Spellcasting", "spellcasting", "Cantrips"]:
                if key in choices_made:
                    potential_cantrips = choices_made[key]
                    if isinstance(potential_cantrips, list):
                        cantrips = potential_cantrips
                        break

        if cantrips and class_name:
            if 0 not in spells_by_level:
                spells_by_level[0] = []

            # Load class cantrip list
            spell_data = self._get_class_spell_list(class_name)
            if spell_data:
                available_cantrips = spell_data.get("cantrips", [])

                for cantrip_name in cantrips:
                    if cantrip_name in available_cantrips:
                        existing_names = [s["name"] for s in spells_by_level[0]]
                        if cantrip_name not in existing_names:
                            cantrip_info = load_spell_definition(cantrip_name)

                            spells_by_level[0].append(
                                {
                                    "name": cantrip_name,
                                    "school": cantrip_info.get("school", ""),
                                    "casting_time": cantrip_info.get(
                                        "casting_time", ""
                                    ),
                                    "range": cantrip_info.get("range", ""),
                                    "components": cantrip_info.get(
                                        "components", ""
                                    ),
                                    "duration": cantrip_info.get("duration", ""),
                                    "description": cantrip_info.get(
                                        "description", ""
                                    ),
                                    "source": f"{class_name} Class",
                                }
                            )

        # 5) Add bonus cantrips from grant_cantrip_choice effects
        if class_name:
            class_data = self._load_class_data(class_name)
            if class_data:
                # Scan for options with grant_cantrip_choice effects
                for data_key, data_value in class_data.items():
                    if isinstance(data_value, dict):
                        for option_name, option_data in data_value.items():
                            if (
                                isinstance(option_data, dict)
                                and "effects" in option_data
                            ):
                                # Check if this option was selected
                                for choice_key, choice_value in choices_made.items():
                                    if choice_value == option_name:
                                        # Check for grant_cantrip_choice effects
                                        for effect in option_data.get("effects", []):
                                            if (
                                                effect.get("type")
                                                == "grant_cantrip_choice"
                                            ):
                                                bonus_cantrip_key = (
                                                    f"{option_name}_bonus_cantrip"
                                                )
                                                bonus_cantrips = choices_made.get(
                                                    bonus_cantrip_key
                                                )

                                                if bonus_cantrips:
                                                    spell_list = effect.get(
                                                        "spell_list", class_name
                                                    )
                                                    spell_data = self._get_class_spell_list(spell_list)
                                                    if spell_data:
                                                        available_cantrips = (
                                                            spell_data.get(
                                                                "cantrips", []
                                                            )
                                                        )

                                                        if 0 not in spells_by_level:
                                                            spells_by_level[0] = []

                                                        cantrip_list = (
                                                            bonus_cantrips
                                                            if isinstance(
                                                                bonus_cantrips, list
                                                            )
                                                            else [bonus_cantrips]
                                                        )

                                                        for (
                                                            cantrip_name
                                                        ) in cantrip_list:
                                                            if (
                                                                cantrip_name
                                                                in available_cantrips
                                                            ):
                                                                existing_names = [
                                                                    s["name"]
                                                                    for s in spells_by_level[
                                                                        0
                                                                    ]
                                                                ]
                                                                if (
                                                                    cantrip_name
                                                                    not in existing_names
                                                                ):
                                                                    cantrip_info = load_spell_definition(
                                                                        cantrip_name
                                                                    )

                                                                    spells_by_level[
                                                                        0
                                                                    ].append(
                                                                        {
                                                                            "name": cantrip_name,
                                                                            "school": cantrip_info.get(
                                                                                "school",
                                                                                "",
                                                                            ),
                                                                            "casting_time": cantrip_info.get(
                                                                                "casting_time",
                                                                                "",
                                                                            ),
                                                                            "range": cantrip_info.get(
                                                                                "range",
                                                                                "",
                                                                            ),
                                                                            "components": cantrip_info.get(
                                                                                "components",
                                                                                "",
                                                                            ),
                                                                            "duration": cantrip_info.get(
                                                                                "duration",
                                                                                "",
                                                                            ),
                                                                            "description": cantrip_info.get(
                                                                                "description",
                                                                                "",
                                                                            ),
                                                                            "source": f"{option_name} ({data_key})",
                                                                        }
                                                                    )

        # 6) Add cantrips from subclass features with grant_cantrip effects
        if subclass_name and class_name:
            subclass_data = self._load_subclass_data(class_name, subclass_name)
            if subclass_data:
                features_by_level = subclass_data.get("features_by_level", {})

                # Load class cantrip list once for efficiency
                spell_data = self._get_class_spell_list(class_name)
                available_cantrips = spell_data.get("cantrips", []) if spell_data else []

                # Check each level up to character level for effects
                for level in range(1, character_level + 1):
                    level_str = str(level)
                    if level_str in features_by_level:
                        level_features = features_by_level[level_str]
                        for feature_name, feature_data in level_features.items():
                            if (
                                isinstance(feature_data, dict)
                                and "effects" in feature_data
                            ):
                                for effect in feature_data.get("effects", []):
                                    if effect.get("type") == "grant_cantrip":
                                        cantrip_name = effect.get("spell")
                                        if (
                                            cantrip_name
                                            and cantrip_name in available_cantrips
                                        ):
                                            if 0 not in spells_by_level:
                                                spells_by_level[0] = []

                                            existing_names = [
                                                s["name"] for s in spells_by_level[0]
                                            ]
                                            if cantrip_name not in existing_names:
                                                cantrip_info = load_spell_definition(
                                                    cantrip_name
                                                )

                                                spells_by_level[0].append(
                                                    {
                                                        "name": cantrip_name,
                                                        "school": cantrip_info.get(
                                                            "school", ""
                                                        ),
                                                        "casting_time": cantrip_info.get(
                                                            "casting_time", ""
                                                        ),
                                                        "range": cantrip_info.get(
                                                            "range", ""
                                                        ),
                                                        "components": cantrip_info.get(
                                                            "components", ""
                                                        ),
                                                        "duration": cantrip_info.get(
                                                            "duration", ""
                                                        ),
                                                        "description": cantrip_info.get(
                                                            "description", ""
                                                        ),
                                                        "source": f"{subclass_name} (Level {level})",
                                                    }
                                                )

        return spells_by_level

    def get_language_options(self) -> Dict[str, Any]:
        """
        Get language choices for the 2024 baseline flow.

        Returns:
            dict with keys:
                - base_languages: standard languages already known (excl. user-picked standard)
                - rare_base_languages: rare languages already known via class/species/feature grants
                - available_languages: languages available for the 2-language standard selection
                - selection_count: required number of selected languages
                - selected_languages: current user-selected standard languages
                - all_rare_languages: full rare language list minus already-known rare languages
                - selected_rare_languages: current user-selected optional rare languages
        """
        self._ensure_base_language()
        language_sources = self.character_data["proficiency_sources"]["languages"]
        known_languages = self.character_data["proficiencies"]["languages"]
        selected_languages = self.character_data["choices_made"].get("languages", [])
        if not isinstance(selected_languages, list):
            selected_languages = []
        selected_rare_languages = self.character_data["choices_made"].get("rare_languages", [])
        if not isinstance(selected_rare_languages, list):
            selected_rare_languages = []

        rare_set = set(self.RARE_LANGUAGE_OPTIONS)

        base_languages = {self.BASE_LANGUAGE}
        rare_base_languages = set()
        for lang in known_languages:
            if language_sources.get(lang) not in ("user_choice", "rare_user_choice"):
                if lang in rare_set:
                    rare_base_languages.add(lang)
                else:
                    base_languages.add(lang)

        standard_available = [
            lang for lang in self.STANDARD_LANGUAGE_OPTIONS if lang not in base_languages
        ]
        rare_available = [
            lang for lang in self.RARE_LANGUAGE_OPTIONS if lang not in rare_base_languages
        ]

        # All selectable languages (standard first, then rare)
        available_languages = standard_available + rare_available

        # Combined pool of valid selectable languages
        valid_pool = set(available_languages)
        combined_selected = []
        for l in selected_languages + selected_rare_languages:
            if l in valid_pool and l not in combined_selected:
                combined_selected.append(l)

        # Exclude feature-granted rare languages from the selectable list
        # (user-selected rare languages remain in the list so the UI can toggle them)
        all_rare_languages = sorted(rare_set - rare_base_languages)

        return {
            "base_languages": sorted(base_languages),
            "rare_base_languages": sorted(rare_base_languages),
            "available_languages": available_languages,
            "standard_available_languages": standard_available,
            "rare_available_languages": rare_available,
            "selection_count": self.REQUIRED_LANGUAGE_SELECTION_COUNT,
            "selected_languages": combined_selected[:self.REQUIRED_LANGUAGE_SELECTION_COUNT],
            "all_rare_languages": all_rare_languages,
            "selected_rare_languages": [
                lang for lang in combined_selected if lang in rare_set
            ],
        }

    def roll_languages(self) -> List[str]:
        """Randomly choose the required number of standard languages."""
        options = self.get_language_options()
        available_languages = options["available_languages"]
        selection_count = options["selection_count"]

        if len(available_languages) <= selection_count:
            return list(available_languages)
        return random.sample(available_languages, selection_count)

    def get_background_asi_options(self) -> Dict[str, Any]:
        """
        Get background ability score increase options and suggested allocation.

        Returns:
            dict with keys:
                - total_points: Total ASI points to allocate (typically 3)
                - suggested: Suggested allocation from background data
                - ability_options: List of abilities available for allocation
        """
        background_name = self.character_data.get("background")
        if not background_name:
            return {
                "total_points": 3,
                "suggested": {},
                "ability_options": [
                    "Strength",
                    "Dexterity",
                    "Constitution",
                    "Intelligence",
                    "Wisdom",
                    "Charisma",
                ],
            }

        background_data = self._load_background_data(background_name)
        if not background_data:
            return {
                "total_points": 3,
                "suggested": {},
                "ability_options": [
                    "Strength",
                    "Dexterity",
                    "Constitution",
                    "Intelligence",
                    "Wisdom",
                    "Charisma",
                ],
            }

        # D&D 2024 standard
        total_points = 3
        suggested = {}
        ability_options = [
            "Strength",
            "Dexterity",
            "Constitution",
            "Intelligence",
            "Wisdom",
            "Charisma",
        ]

        if "ability_score_increase" in background_data:
            asi_data = background_data["ability_score_increase"]
            if "suggested" in asi_data:
                suggested = asi_data["suggested"]
            if "options" in asi_data:
                # Keep background-specific abilities in standard D&D order
                bg_options = asi_data["options"]
                ability_options = [
                    ability for ability in ability_options if ability in bg_options
                ]

        return {
            "total_points": total_points,
            "suggested": suggested,
            "ability_options": ability_options,
        }

    def get_species_trait_choices(self) -> Dict[str, Dict[str, Any]]:
        """
        Get trait choices for the character's species (e.g., Keen Senses for Elf).

        Returns:
            dict mapping trait_name -> {description, options, count}
        """
        species_name = self.character_data.get("species")
        if not species_name:
            return {}

        species_data = self._load_species_data(species_name)
        if not species_data or "traits" not in species_data:
            return {}

        trait_choices = {}

        def _collect_choice_traits(traits: Dict[str, Any]) -> None:
            for trait_name, trait_data in traits.items():
                if isinstance(trait_data, dict) and trait_data.get("type") == "choice":
                    choices_data = trait_data.get("choices", {})
                    source_data = choices_data.get("source", {})
                    options = []

                    # If this is Versatile or an origin feat choice, resolve from DataLoader with active supplements
                    if trait_name == "Versatile" or source_data.get("list") == "origin_feats":
                        from modules.data_loader import DataLoader
                        active_sources = (
                            self.character_data.get("choices_made", {}).get("active_sources")
                            or self.character_data.get("active_sources")
                        )
                        dl = DataLoader(data_dir=str(self.data_dir))
                        all_origin_feats = dl.get_feats(feat_type="origin", active_sources=active_sources)
                        if all_origin_feats:
                            options = list(all_origin_feats.keys())

                    if not options:
                        try:
                            from utils.choice_resolver import resolve_choice_options
                            options = resolve_choice_options(choices_data, self.character_data)
                        except Exception:
                            options = []

                    if not options:
                        options = source_data.get("options", [])

                    option_descriptions = {}
                    if trait_name == "Versatile" or source_data.get("list") == "origin_feats":
                        from modules.data_loader import DataLoader
                        active_sources = (
                            self.character_data.get("choices_made", {}).get("active_sources")
                            or self.character_data.get("active_sources")
                        )
                        dl = DataLoader(data_dir=str(self.data_dir))
                        all_origin_feats = dl.get_feats(feat_type="origin", active_sources=active_sources)
                        for fname, fdef in all_origin_feats.items():
                            fdesc = fdef.get("description", "")
                            benefits = fdef.get("benefits", [])
                            if benefits:
                                fdesc += " " + " ".join(benefits)
                            option_descriptions[fname] = fdesc

                    trait_choices[trait_name] = {
                        "description": trait_data.get("description", ""),
                        "options": options,
                        "option_descriptions": option_descriptions,
                        "count": choices_data.get("count", 1),
                    }

        _collect_choice_traits(species_data.get("traits", {}))

        lineage_name = self.character_data.get("lineage")
        if lineage_name:
            lineage_data = self._load_lineage_data(species_name, lineage_name)
            if isinstance(lineage_data, dict):
                _collect_choice_traits(lineage_data.get("traits", {}))

        return trait_choices

    def get_class_features_and_choices(self) -> Dict[str, Any]:
        """
        Get all class and subclass features with their choices for character's level.

        This method processes:
        - Skill proficiency selections
        - Class features by level (informational and choice-based)
        - Subclass features by level (informational and choice-based)
        - Nested choices from effects (e.g., bonus cantrips from grant_cantrip_choice)

        Returns a dictionary with:
        - 'features_by_level': Dict mapping level (int) to list of feature dicts
        - 'choices': List of choice dicts for form processing
        - 'skill_choice': Dict with skill selection info (or None)

        Returns:
            Dictionary with features_by_level, choices, and skill_choice
        """
        character = self.to_json()
        class_name = character.get("class")
        subclass_name = character.get("subclass")
        character_level = character.get("level", 1)
        choices_made = character.get("choices_made", {})

        if not class_name:
            return {"features_by_level": {}, "choices": [], "skill_choice": None}

        # Load class and subclass data
        class_data = self._load_class_data(class_name)
        if not class_data:
            return {"features_by_level": {}, "choices": [], "skill_choice": None}

        subclass_data = None
        if subclass_name:
            subclass_data = self._load_subclass_data(class_name, subclass_name)

        all_features_by_level = {}
        choices = []
        skill_choice = None

        # All D&D skills - constant list
        ALL_SKILLS = [
            "Acrobatics",
            "Animal Handling",
            "Arcana",
            "Athletics",
            "Deception",
            "History",
            "Insight",
            "Intimidation",
            "Investigation",
            "Medicine",
            "Nature",
            "Perception",
            "Performance",
            "Persuasion",
            "Religion",
            "Sleight of Hand",
            "Stealth",
            "Survival",
        ]

        # 1) Add skill selection (level 1)
        if "skill_options" in class_data and "skill_proficiencies_count" in class_data:
            skill_options = class_data["skill_options"]

            # Expand "Any" to all available skills
            if skill_options == ["Any"] or (
                len(skill_options) == 1 and skill_options[0] == "Any"
            ):
                skill_options = ALL_SKILLS

            if 1 not in all_features_by_level:
                all_features_by_level[1] = []

            all_features_by_level[1].append(
                {
                    "name": "Skill Proficiencies",
                    "type": "choice",
                    "description": f"Choose {class_data['skill_proficiencies_count']} skill proficiencies from the available options.",
                    "level": 1,
                    "source": "Class",
                }
            )

            skill_choice = {
                "choice_key": "skill_choices",
                "choices_made_key": "skill_choices",
                "title": "Skill Proficiencies",
                "type": "skills",
                "description": f"Choose {class_data['skill_proficiencies_count']} skill proficiencies from the available options.",
                "options": skill_options,
                "count": class_data["skill_proficiencies_count"],
                "required": True,
                "level": 1,
            }
            choices.append(skill_choice)

        # 1b) Add tool proficiency selection (level 1)
        if "tool_options" in class_data and "tool_proficiencies_count" in class_data:
            tool_options = class_data["tool_options"]
            tool_count = class_data["tool_proficiencies_count"]

            if 1 not in all_features_by_level:
                all_features_by_level[1] = []

            all_features_by_level[1].append(
                {
                    "name": "Tool Proficiency",
                    "type": "choice",
                    "description": f"Choose {tool_count} tool {'proficiency' if tool_count == 1 else 'proficiencies'} from the available options.",
                    "level": 1,
                    "source": "Class",
                }
            )

            tool_choice = {
                "choice_key": "tool_choices",
                "choices_made_key": "tool_choices",
                "title": "Tool Proficiency",
                "type": "tools",
                "description": f"Choose {tool_count} tool {'proficiency' if tool_count == 1 else 'proficiencies'} from the available options.",
                "options": tool_options,
                "count": tool_count,
                "required": True,
                "level": 1,
            }
            choices.append(tool_choice)

        # Get class and subclass features
        class_features_by_level = class_data.get("features_by_level", {})
        subclass_features_by_level = {}
        if subclass_data:
            subclass_features_by_level = subclass_data.get("features_by_level", {})

        # 2) Process all levels up to character level
        for level in range(1, character_level + 1):
            level_str = str(level)

            if level not in all_features_by_level:
                all_features_by_level[level] = []

            # Process class features for this level
            self._process_level_features(
                level,
                level_str,
                class_features_by_level.get(level_str, {}),
                all_features_by_level,
                choices,
                character,
                class_data,
                None,
                source_name="Class",
            )

            # Process subclass features for this level
            if subclass_name and level_str in subclass_features_by_level:
                self._process_level_features(
                    level,
                    level_str,
                    subclass_features_by_level[level_str],
                    all_features_by_level,
                    choices,
                    character,
                    class_data,
                    subclass_data,
                    source_name=subclass_name,
                )

        # 3) Add nested choices from effects (e.g., bonus cantrips from grant_cantrip_choice)
        self._add_nested_choices_from_effects(
            choices, choices_made, class_data, character, class_name
        )

        # 4) Inject sub-choices for any already-selected class-level feats
        self._add_class_level_feat_sub_choices(choices, choices_made, character)

        return {
            "features_by_level": all_features_by_level,
            "choices": choices,
            "skill_choice": skill_choice,
        }

    def _process_level_features(
        self,
        level: int,
        level_str: str,
        level_features: Dict[str, Any],
        all_features_by_level: Dict[int, List[Dict]],
        choices: List[Dict],
        character: Dict,
        class_data: Dict,
        subclass_data: Optional[Dict],
        source_name: str,
    ):
        """
        Process features for a specific level (class or subclass).

        Adds features to all_features_by_level and choices lists.
        """
        for feature_name, feature_data in level_features.items():
            if isinstance(feature_data, dict) and "choices" in feature_data:
                # Choice-based feature
                all_features_by_level[level].append(
                    {
                        "name": feature_name,
                        "type": "choice",
                        "description": feature_data.get("description", ""),
                        "level": level,
                        "source": source_name,
                    }
                )

                # Add to choices for form processing
                choices_data = feature_data["choices"]
                if isinstance(choices_data, list):
                    # Multiple choices
                    for idx, choice_item in enumerate(choices_data):
                        raw_name = choice_item.get("name", f"choice_{idx}")
                        choice_name_suffix = (
                            choice_item.get("display_name")
                            or choice_item.get("label")
                            or raw_name.replace("_", " ").title()
                        )
                        feature_key = f"{feature_name}_{raw_name}"

                        # For subclass features, prefix with 'subclass_'
                        if subclass_data:
                            feature_key = f"subclass_{feature_key}"

                        choice = {
                            "title": f"{feature_name} - {choice_name_suffix} ({source_name}, Level {level})",
                            "type": "feature",
                            "description": feature_data.get("description", ""),
                            "options": resolve_choice_options(
                                choice_item, character, class_data, subclass_data
                            ),
                            "count": choice_item.get("count", 1),
                            "required": not choice_item.get("optional", False),
                            "level": level,
                            "feature_name": feature_key,
                            "choice_key": raw_name,
                            # Phase 5 / P1-3: canonical key the frontend MUST write into
                            # choices_made. Apply_choice dispatches on this exact key.
                            "choices_made_key": feature_key,
                            "option_descriptions": get_option_descriptions(
                                feature_data, choice_item, class_data, subclass_data
                            ),
                        }
                        _cat = self._get_choice_category(choice_item)
                        if _cat:
                            choice["choice_category"] = _cat

                        # Skip subclass-related features in class-only context
                        if (
                            source_name == "Class"
                            and "subclass" not in feature_name.lower()
                        ):
                            choices.append(choice)
                        elif source_name != "Class":
                            choices.append(choice)
                else:
                    # Single choice
                    feature_key = feature_name
                    if subclass_data:
                        feature_key = f"subclass_{feature_name}"

                    choice = {
                        "title": f"{feature_name} ({source_name}, Level {level})",
                        "type": "feature",
                        "description": feature_data.get("description", ""),
                        "options": resolve_choice_options(
                            choices_data, character, class_data, subclass_data
                        ),
                        "count": choices_data.get("count", 1),
                        "required": not choices_data.get("optional", False),
                        "level": level,
                        "feature_name": feature_key,
                        "choice_key": choices_data.get("name", feature_key),
                        # Phase 5 / P1-3: canonical key the frontend MUST write into
                        # choices_made. Apply_choice dispatches on this exact key.
                        "choices_made_key": choices_data.get("name", feature_key),
                        "option_descriptions": get_option_descriptions(
                            feature_data, choices_data, class_data, subclass_data
                        ),
                    }
                    _cat = self._get_choice_category(choices_data)
                    if _cat:
                        choice["choice_category"] = _cat

                    # Skip subclass-related features in class-only context
                    if (
                        source_name == "Class"
                        and "subclass" not in feature_name.lower()
                    ):
                        choices.append(choice)
                    elif source_name != "Class":
                        choices.append(choice)
            else:
                # Feature without choices (simple informational)
                description = (
                    feature_data
                    if isinstance(feature_data, str)
                    else feature_data.get("description", "")
                )
                all_features_by_level[level].append(
                    {
                        "name": feature_name,
                        "type": "info",
                        "description": description,
                        "level": level,
                        "source": source_name,
                    }
                )

    def _add_nested_choices_from_effects(
        self,
        choices: List[Dict],
        choices_made: Dict[str, Any],
        class_data: Dict,
        character: Dict,
        class_name: str,
    ):
        """
        Add nested choices triggered by grant_cantrip_choice effects.

        Scans class_data for ALL options with grant_cantrip_choice effects and adds
        the corresponding bonus cantrip choices to the choices list (hidden by default,
        shown by JavaScript when parent option is selected).
        """
        def _normalize_choice_identifier(value: Any) -> Optional[str]:
            if not isinstance(value, str):
                return None
            return value.strip().lower().replace(" ", "_")

        # First, find the parent choice key from existing choices
        parent_choice_key = None
        for choice in choices:
            feature_name = choice.get("feature_name")
            # Check if any options in class_data match this choice and have grant_cantrip_choice effects
            for data_key, data_value in class_data.items():
                if isinstance(data_value, dict):
                    for option_name, option_data in data_value.items():
                        if isinstance(option_data, dict) and "effects" in option_data:
                            for effect in option_data.get("effects", []):
                                if effect.get("type") == "grant_cantrip_choice":
                                    # Found a parent choice that triggers nested choices
                                    # Use the choice's feature_name or a normalized key
                                    if not parent_choice_key:
                                        # Try to derive the choice key from the feature name or data_key
                                        parent_choice_key = (
                                            feature_name.lower().replace(" ", "_")
                                            if feature_name
                                            else data_key.rstrip("s")
                                        )

        # Scan all keys in class_data for option lists that might have effects
        for data_key, data_value in class_data.items():
            if isinstance(data_value, dict):
                # This could be a choice list (e.g., divine_orders, fighting_styles, etc.)
                for option_name, option_data in data_value.items():
                    if isinstance(option_data, dict) and "effects" in option_data:
                        # Check for grant_cantrip_choice effects (add ALL, not just selected ones)
                        for effect in option_data.get("effects", []):
                            if effect.get("type") == "grant_cantrip_choice":
                                cantrip_count = effect.get("count", 1)
                                spell_list = effect.get("spell_list", class_name)

                                # Load cantrip options
                                class_lower = spell_list.lower()
                                spell_file_path = (
                                    f"spells/class_lists/{class_lower}.json"
                                )
                                cantrip_options = resolve_choice_options(
                                    {
                                        "source": {
                                            "type": "external",
                                            "file": spell_file_path,
                                            "list": "cantrips",
                                        }
                                    },
                                    character,
                                    class_data,
                                    None,
                                )

                                # Create unique feature name based on the option that grants it
                                bonus_feature_name = f"{option_name}_bonus_cantrip"

                                # Derive parent choice key.
                                # Prefer an explicit "depends_on" field on the effect (e.g., "fighting_style").
                                # Fall back to stripping the "_options" suffix when present
                                # (e.g., "fighting_style_options" → "fighting_style"), or
                                # stripping a trailing "s" for simple plural keys
                                # (e.g., "divine_orders" → "divine_order").
                                if effect.get("depends_on"):
                                    choice_key = effect["depends_on"]
                                elif data_key.endswith("_options"):
                                    choice_key = data_key[: -len("_options")]
                                else:
                                    choice_key = data_key.rstrip("s")

                                # Only add if not already in choices
                                if not any(
                                    c.get("feature_name") == bonus_feature_name
                                    for c in choices
                                ):
                                    choice = {
                                        "title": f"{option_name} - Bonus Cantrip (Level 1)",
                                        "type": "feature",
                                        "description": f"Choose {cantrip_count} additional cantrip from the {spell_list} spell list.",
                                        "options": cantrip_options,
                                        "count": cantrip_count,
                                        "required": True,
                                        "level": 1,
                                        "feature_name": bonus_feature_name,
                                        # Phase 5 / P1-3: canonical key. Nested cantrip
                                        # picks are stored under this exact key in choices_made.
                                        "choices_made_key": bonus_feature_name,
                                        "depends_on": choice_key,
                                        "depends_on_value": option_name,
                                        "is_nested": True,
                                        "option_descriptions": get_option_descriptions(
                                            {
                                                "choices": {
                                                    "source": {
                                                        "type": "external",
                                                        "file": spell_file_path,
                                                        "list": "cantrips",
                                                    }
                                                }
                                            },
                                            {
                                                "source": {
                                                    "type": "external",
                                                    "file": spell_file_path,
                                                    "list": "cantrips",
                                                }
                                            },
                                            class_data,
                                            None,
                                        ),
                                    }
                                    insertion_index = len(choices)
                                    normalized_choice_key = _normalize_choice_identifier(
                                        choice_key
                                    )
                                    for idx, existing_choice in enumerate(choices):
                                        existing_identifiers = {
                                            identifier
                                            for identifier in [
                                                _normalize_choice_identifier(
                                                    existing_choice.get("choice_key")
                                                ),
                                                _normalize_choice_identifier(
                                                    existing_choice.get("feature_name")
                                                ),
                                            ]
                                            if identifier is not None
                                        }
                                        if (
                                            normalized_choice_key is not None
                                            and normalized_choice_key
                                            in existing_identifiers
                                        ):
                                            insertion_index = idx + 1
                                            while insertion_index < len(choices) and (
                                                _normalize_choice_identifier(
                                                    choices[insertion_index].get(
                                                        "depends_on"
                                                    )
                                                )
                                                == normalized_choice_key
                                            ):
                                                insertion_index += 1
                                            break

                                    choices.insert(insertion_index, choice)

    def _add_class_level_feat_sub_choices(
        self,
        choices: List[Dict],
        choices_made: Dict[str, Any],
        character: Dict,
    ):
        """
        After a class-level feat slot (e.g. class_feat_4) is selected, inject
        the feat's own sub-choices (e.g. which ability to boost for ASI) into
        the choices list so the UI can present them.

        Scans choices_made for keys matching ``^class_feat_\\d+$``, loads the
        chosen feat's data, and appends a choice entry for each sub-choice item
        defined in the feat.  Avoids adding duplicates.
        """
        for parent_key, feat_name in choices_made.items():
            if not _CLASS_FEAT_SLOT_RE.match(parent_key):
                continue
            if not isinstance(feat_name, str) or not feat_name:
                continue

            feat_data = self._load_feat_data(feat_name)
            if not feat_data:
                continue

            sub_choice_items = feat_data.get("choices", [])
            if not isinstance(sub_choice_items, list):
                continue

            # Extract slot level from parent_key (e.g. "class_feat_4" -> 4)
            slot_level = self._class_feat_slot_level(parent_key)

            for sub_item in sub_choice_items:
                if not isinstance(sub_item, dict):
                    continue
                sub_item_name = sub_item.get("name", "")
                if not sub_item_name:
                    continue

                sub_key = f"{parent_key}_{sub_item_name}"

                # Skip if already in choices list
                if any(c.get("choice_key") == sub_key for c in choices):
                    continue

                sub_choice = {
                    "title": f"{feat_name} \u2014 {_humanize(sub_item_name)} (Level {slot_level})",
                    "type": "feature",
                    "description": sub_item.get("description") or feat_data.get("description", ""),
                    "options": resolve_choice_options(sub_item, character),
                    "count": sub_item.get("count", 1),
                    "required": not sub_item.get("optional", False),
                    "level": slot_level,
                    "feature_name": sub_key,
                    "choice_key": sub_key,
                    # Phase 5 / P1-3: canonical key for class-level feat sub-choices
                    # (e.g. class_feat_4_ability for an ASI inside a feat slot).
                    "choices_made_key": sub_key,
                    "depends_on": (
                        f"{parent_key}_{sub_item['depends_on']}"
                        if sub_item.get("depends_on")
                        else parent_key
                    ),
                    "depends_on_value": sub_item.get("depends_on_value"),
                    "option_descriptions": {},
                }
                choices.append(sub_choice)

    # ==================== Feat Choices ====================

    _ALL_SKILLS = [
        "Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception",
        "History", "Insight", "Intimidation", "Investigation", "Medicine",
        "Nature", "Perception", "Performance", "Persuasion", "Religion",
        "Sleight of Hand", "Stealth", "Survival",
    ]

    # ==================== Background Skill Replacement ====================

    def get_background_skill_replacement_info(self) -> Dict[str, Any]:
        """
        Return information about background skill replacement choices needed.

        When a background grants a skill proficiency the character already has
        (e.g. from their class), D&D 2024 rules require offering a replacement
        from the class's available skill options.

        Returns:
            Dict with keys:
            - 'needed': int — number of replacement skills to choose
            - 'options': list[str] — skills available to pick as replacements
            - 'already_chosen': list[str] — replacements already committed
        """
        needed = self.character_data["choices_made"].get(
            "background_skill_replacements_needed", 0
        )
        already_chosen_raw = self.character_data["choices_made"].get(
            "background_skill_replacements", []
        )
        if isinstance(already_chosen_raw, str):
            already_chosen = [already_chosen_raw] if already_chosen_raw else []
        elif isinstance(already_chosen_raw, list):
            already_chosen = already_chosen_raw
        else:
            already_chosen = []
        if not needed:
            return {"needed": 0, "options": [], "already_chosen": already_chosen}

        current_profs = set(self.character_data["proficiencies"]["skills"])

        # Prefer the class's own skill_options list; fall back to all skills
        class_data = self.character_data.get("class_data") or {}
        skill_options = class_data.get("skill_options", [])
        if not skill_options or skill_options == ["Any"]:
            skill_options = list(self._ALL_SKILLS)

        options = [s for s in skill_options if s not in current_profs]

        # If the class list is exhausted, allow any unproficient skill
        if not options:
            options = [s for s in self._ALL_SKILLS if s not in current_profs]

        return {"needed": needed, "options": options, "already_chosen": already_chosen}

    def apply_background_skill_replacement(self, skills: List[str]) -> bool:
        """
        Apply replacement skill proficiencies chosen to offset background overlaps.

        Args:
            skills: Skill names selected by the player as replacements.

        Returns:
            True on success.
        """
        background_data = self.character_data.get("background_data") or {}
        background_name = background_data.get(
            "name", self.character_data.get("background", "Unknown")
        )
        needed = self.character_data["choices_made"].get(
            "background_skill_replacements_needed", 0
        )

        # Remove previously committed replacements so re-submission is idempotent
        prev_replacements = self.character_data["choices_made"].get(
            "background_skill_replacements", []
        )
        self._remove_skills_sourced_from(prev_replacements, background_name)

        # Apply new replacements (capped at the number needed)
        skill_sources = self.character_data["proficiency_sources"]["skills"]
        valid_skills = [s for s in skills if s in self._ALL_SKILLS][:needed]
        for skill in valid_skills:
            if skill not in self.character_data["proficiencies"]["skills"]:
                self.character_data["proficiencies"]["skills"].append(skill)
                skill_sources[skill] = background_name

        self.character_data["choices_made"][
            "background_skill_replacements"
        ] = valid_skills
        return True

    # ==================== Species Skill Replacement ====================

    def get_species_skill_replacement_info(self) -> Dict[str, Any]:
        """
        Return information about species/lineage skill replacement choices needed.

        When a species or lineage grants a skill proficiency the character
        already has (e.g. from their class or background), D&D 2024 rules
        require offering a replacement from any skill the character doesn't
        already have.

        Returns:
            Dict with keys:
            - 'needed': int — number of replacement skills to choose
            - 'options': list[str] — skills available to pick as replacements
            - 'already_chosen': list[str] — replacements already committed
        """
        needed = self.character_data["choices_made"].get(
            "species_skill_replacements_needed", 0
        )
        already_chosen_raw = self.character_data["choices_made"].get(
            "species_skill_replacements", []
        )
        if isinstance(already_chosen_raw, str):
            already_chosen = [already_chosen_raw] if already_chosen_raw else []
        elif isinstance(already_chosen_raw, list):
            already_chosen = already_chosen_raw
        else:
            already_chosen = []
        if not needed:
            return {"needed": 0, "options": [], "already_chosen": already_chosen}

        current_profs = set(self.character_data["proficiencies"]["skills"])
        options = [s for s in self._ALL_SKILLS if s not in current_profs]

        return {"needed": needed, "options": options, "already_chosen": already_chosen}

    def apply_species_skill_replacement(self, skills: List[str]) -> bool:
        """
        Apply replacement skill proficiencies chosen to offset species/lineage overlaps.

        Args:
            skills: Skill names selected by the player as replacements.

        Returns:
            True on success.
        """
        species_name = self.character_data.get("species", "Unknown")
        needed = self.character_data["choices_made"].get(
            "species_skill_replacements_needed", 0
        )

        # Remove previously committed replacements so re-submission is idempotent
        prev_replacements = self.character_data["choices_made"].get(
            "species_skill_replacements", []
        )
        self._remove_skills_sourced_from(prev_replacements, species_name)

        # Apply new replacements (capped at the number needed)
        skill_sources = self.character_data["proficiency_sources"]["skills"]
        valid_skills = [s for s in skills if s in self._ALL_SKILLS][:needed]
        for skill in valid_skills:
            if skill not in self.character_data["proficiencies"]["skills"]:
                self.character_data["proficiencies"]["skills"].append(skill)
                skill_sources[skill] = species_name

        self.character_data["choices_made"][
            "species_skill_replacements"
        ] = valid_skills
        return True


    def get_feat_choices(self) -> Dict[str, Any]:
        """
        Get choices required by the background's origin feat.

        Inspects the feat granted by the current background, extracts any
        ``choices`` entries, and resolves the available options.

        Returns:
            Dict with keys:
            - 'feat_name': str | None — name of the feat, or None if absent
            - 'feat_description': str — feat description
            - 'feat_benefits': list[str] — bullet-point benefits
            - 'choices': list[dict] — choice dicts ready for template rendering,
              each containing 'title', 'type', 'description', 'options',
              'count', 'required', 'feature_name', 'choice_type', and
              'option_descriptions'.
        """
        background_data = self.character_data.get("background_data") or {}
        feat_name = self._background_feat_name(background_data)
        if not feat_name:
            return {"feat_name": None, "feat_description": "", "feat_benefits": [], "choices": []}

        feat_data = self._load_feat_data(feat_name)
        if not feat_data:
            return {"feat_name": feat_name, "feat_description": "", "feat_benefits": [], "choices": []}

        raw_choices = feat_data.get("choices", [])
        if not raw_choices:
            return {
                "feat_name": feat_name,
                "feat_description": feat_data.get("description", ""),
                "feat_benefits": feat_data.get("benefits", []),
                "choices": [],
            }

        character = self.to_json()
        choices_made = character.get("choices_made", {})
        choices: List[Dict[str, Any]] = []

        for choice_item in raw_choices:
            choice_name = choice_item.get("name", "choice")
            choices_made_key = f"feat_{feat_name}_{choice_name}"

            options = resolve_choice_options(choice_item, character)

            already_chosen = choices_made.get(choices_made_key)
            if isinstance(already_chosen, str):
                already_chosen = [already_chosen]

            choice = {
                "title": f"{feat_name} — {_humanize(choice_name)}",
                "type": "feature",
                "description": choice_item.get("description") or feat_data.get("description", ""),
                "options": options,
                "count": choice_item.get("count", 1),
                "required": True,
                "feature_name": choice_name,
                "choices_made_key": choices_made_key,
                "choice_type": choice_item.get("type", "select_multiple"),
                "option_descriptions": {},
                "already_chosen": already_chosen or [],
            }
            choice_category = self._get_choice_category(choice_item)
            if choice_category:
                choice["choice_category"] = choice_category
            choices.append(choice)

        return {
            "feat_name": feat_name,
            "feat_description": feat_data.get("description", ""),
            "feat_benefits": feat_data.get("benefits", []),
            "choices": choices,
        }

    def get_species_feat_choices(self) -> Dict[str, Any]:
        """
        Get choices required by the origin feat granted via a species trait
        (e.g. Human Versatile → Skilled).

        Works identically to :meth:`get_feat_choices` but reads the feat name
        from ``character_data['pending_species_feat']`` instead of the
        background data.

        Returns:
            Dict with keys:
            - 'feat_name': str | None
            - 'feat_description': str
            - 'feat_benefits': list[str]
            - 'choices': list[dict] — same shape as ``get_feat_choices``
        """
        feat_name = self.character_data.get("pending_species_feat")
        if not feat_name:
            return {"feat_name": None, "feat_description": "", "feat_benefits": [], "choices": []}

        feat_data = self._load_feat_data(feat_name)
        if not feat_data:
            return {"feat_name": feat_name, "feat_description": "", "feat_benefits": [], "choices": []}

        raw_choices = feat_data.get("choices", [])
        if not raw_choices:
            return {
                "feat_name": feat_name,
                "feat_description": feat_data.get("description", ""),
                "feat_benefits": feat_data.get("benefits", []),
                "choices": [],
            }

        character = self.to_json()
        choices_made = character.get("choices_made", {})
        choices: List[Dict[str, Any]] = []

        for choice_item in raw_choices:
            choice_name = choice_item.get("name", "choice")
            choices_made_key = f"feat_{feat_name}_{choice_name}"

            options = resolve_choice_options(choice_item, character)

            already_chosen = choices_made.get(choices_made_key)
            if isinstance(already_chosen, str):
                already_chosen = [already_chosen]

            choice = {
                "title": f"{feat_name} — {_humanize(choice_name)}",
                "type": "feature",
                "description": choice_item.get("description") or feat_data.get("description", ""),
                "options": options,
                "count": choice_item.get("count", 1),
                "required": True,
                "feature_name": choice_name,
                "choices_made_key": choices_made_key,
                "choice_type": choice_item.get("type", "select_multiple"),
                "option_descriptions": {},
                "already_chosen": already_chosen or [],
            }
            choice_category = self._get_choice_category(choice_item)
            if choice_category:
                choice["choice_category"] = choice_category
            choices.append(choice)

        return {
            "feat_name": feat_name,
            "feat_description": feat_data.get("description", ""),
            "feat_benefits": feat_data.get("benefits", []),
            "choices": choices,
        }

    @staticmethod
    def _get_choice_category(choice_item: Dict[str, Any]) -> Optional[str]:
        """Categorize feat choice options for frontend rendering."""
        source = choice_item.get("source", {})
        if not isinstance(source, dict):
            return None
        source_file = source.get("file", "")
        if isinstance(source_file, str) and source_file.startswith("spells/"):
            return "spells"
        if source_file == "languages.json":
            return "languages"
        return None

    def clear_pending_species_feat(self) -> None:
        """Clear the pending species feat flag after choices have been applied."""
        self.character_data.pop("pending_species_feat", None)

    def _clear_feat_choices(self, feat_name: str) -> None:
        """Clear previously applied feat choices so they can be re-applied cleanly.

        Removes skills, tools, cantrips, and spells that were granted by previous
        selections for the given feat, using the namespaced choices_made keys
        (``feat_{feat_name}_{choice_name}``) to identify what was previously chosen.
        """
        prefix = f"feat_{feat_name}_"
        choices_made = self.character_data["choices_made"]

        # Gather previous selections before removing them
        for key in [k for k in choices_made if k.startswith(prefix)]:
            choice_name = key[len(prefix):]
            old_values = choices_made[key]
            if isinstance(old_values, str):
                old_values = [old_values]
            if not isinstance(old_values, list):
                continue

            if choice_name in ("skills_or_tools", "skills", "skill"):
                skill_sources = self.character_data["proficiency_sources"]["skills"]
                tool_sources = self.character_data["proficiency_sources"]["tools"]
                for item in old_values:
                    if item in self._ALL_SKILLS:
                        if skill_sources.get(item) == feat_name:
                            self.character_data["proficiencies"]["skills"] = [
                                s for s in self.character_data["proficiencies"]["skills"] if s != item
                            ]
                            skill_sources.pop(item, None)
                    else:
                        if tool_sources.get(item) == feat_name:
                            self.character_data["proficiencies"]["tools"] = [
                                t for t in self.character_data["proficiencies"]["tools"] if t != item
                            ]
                            tool_sources.pop(item, None)

            elif choice_name in ("expertise", "skill_expertise"):
                expertise_sources = self.character_data.setdefault("proficiency_sources", {}).setdefault("expertise", {})
                for item in old_values:
                    if expertise_sources.get(item) == feat_name:
                        if "skill_expertise" in self.character_data:
                            self.character_data["skill_expertise"] = [
                                s for s in self.character_data["skill_expertise"] if s != item
                            ]
                        expertise_sources.pop(item, None)

            elif choice_name in ("language", "languages"):
                lang_sources = self.character_data["proficiency_sources"]["languages"]
                for item in old_values:
                    if lang_sources.get(item) == feat_name:
                        self.character_data["proficiencies"]["languages"] = [
                            l for l in self.character_data["proficiencies"]["languages"] if l != item
                        ]
                        lang_sources.pop(item, None)

            elif choice_name in ("tools", "tool", "artisan_tools", "musical_instruments"):
                tool_sources = self.character_data["proficiency_sources"]["tools"]
                for item in old_values:
                    if tool_sources.get(item) == feat_name:
                        self.character_data["proficiencies"]["tools"] = [
                            t for t in self.character_data["proficiencies"]["tools"] if t != item
                        ]
                        tool_sources.pop(item, None)

            elif choice_name == "cantrips":
                for cantrip in old_values:
                    self.character_data["spells"]["always_prepared"].pop(cantrip, None)
                    self.character_data["spells"]["prepared"]["cantrips"].pop(cantrip, None)  # legacy
                    self.character_data["spell_metadata"].pop(cantrip, None)

            elif choice_name == "spellcasting_ability":
                self.character_data.get("feat_spellcasting_abilities", {}).pop(feat_name, None)

            elif "spell" in choice_name and choice_name != "spellcasting_ability":
                for spell in old_values:
                    self.character_data["spells"]["always_prepared"].pop(spell, None)
                    self.character_data["spells"]["prepared"]["spells"].pop(spell, None)  # legacy
                    self.character_data["spell_metadata"].pop(spell, None)

            # Remove the old choices_made entry
            del choices_made[key]

        # Clear any applied effects from this feat's choices
        if hasattr(self, "applied_effects"):
            self._filter_applied_effects(
                lambda e: e.get("source_type") == "feat" and e.get("source") == feat_name
            )

    def apply_feat_choices(self, choices: Dict[str, Any], feat_name: Optional[str] = None) -> bool:
        """
        Apply the selections made on the feat-choices page.

        ``choices`` maps the raw choice name (as returned by ``get_feat_choices``
        in ``choice['feature_name']``) to the user-submitted value(s).

        Args:
            choices: Dict mapping choice name → selected value(s).
            feat_name: Name of the feat whose choices are being applied.
                       If omitted the feat granted by the current background is
                       used (backwards-compatible default).

        Handles:
        - ``skills_or_tools``: each item is added to ``proficiencies['skills']``
          if it is a D&D skill, otherwise to ``proficiencies['tools']``.
        - ``cantrips``: each item is added to ``spells['always_prepared']``
          (e.g. Magic Initiate).
        - any choice whose name contains ``spell``: each item is added to
          ``spells['always_prepared']`` (e.g. Magic Initiate 1st-level spell).

        Unrecognised choice names are still stored in ``choices_made`` so that
        future handlers can use them.

        Returns:
            True always (errors are silently ignored to keep the wizard flowing).
        """
        if feat_name is None:
            background_data = self.character_data.get("background_data") or {}
            feat_name = self._background_feat_name(background_data) or ""

        # Clear previous selections for this feat before applying new ones
        self._clear_feat_choices(feat_name)


        # Load feat_data for this feat_name
        feat_data = self._load_feat_data(feat_name) if feat_name else None

        for choice_name, choice_value in choices.items():
            self._apply_feat_choice_selection(
                feat_name,
                choice_name,
                choice_value,
                feat_data=feat_data,
                persist_choice_key=f"feat_{feat_name}_{choice_name}",
            )

        return True

    def validate(self) -> Dict[str, List[str]]:
        """
        Validate character data.

        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []

        # Check required fields
        if not self.character_data.get("species"):
            errors.append("Species is required")

        if not self.character_data.get("class"):
            errors.append("Class is required")

        if not self.character_data.get("background"):
            errors.append("Background is required")

        if not self.character_data.get("abilities"):
            errors.append("Ability scores are required")

        # Check ability score validity
        abilities = self.character_data.get("abilities", {}).get("base", {})
        for ability, score in abilities.items():
            if score < 1 or score > 20:
                errors.append(f"{ability} score {score} is out of valid range (1-20)")

        return {"errors": errors, "warnings": warnings}
