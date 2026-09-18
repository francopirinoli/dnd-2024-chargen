"""Pure derived-stat / view-model functions.

Phase 2 extraction: these were previously private helpers inside
`routes/character_summary.py`, mixing session state and file I/O with
pure calculation. They are now pure functions over a `CharacterBuilder`
or its `to_character()` output, exposed through the `/api/v1/character/derived`
endpoint.

NEVER import Flask or session state here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Constants (mirror routes/character_summary.py for backward compatibility)
# ---------------------------------------------------------------------------

ORDINAL_TO_INT: Dict[str, int] = {
    "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5,
    "6th": 6, "7th": 7, "8th": 8, "9th": 9,
}

_DAMAGE_DICE_RE = re.compile(r'(\d+d\d+)\s+(\w+)\s+damage', re.IGNORECASE)
_SPELL_ATTACK_RE = re.compile(r'make\s+a\s+(melee|ranged)\s+spell\s+attack', re.IGNORECASE)
_SAVING_THROW_RE = re.compile(r'succeed\s+on\s+an?\s+(\w+)\s+saving\s+throw', re.IGNORECASE)
_SAVE_FAIL_RE = re.compile(r'saving throw or ([^.;]+)', re.IGNORECASE)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SPELL_CLASS_LISTS = _DATA_DIR / "spells" / "class_lists"
_WEAPONS_FILE = _DATA_DIR / "equipment" / "weapons.json"
_WEAPON_MASTERIES_FILE = _DATA_DIR / "equipment" / "weapon_masteries.json"

_SAVANT_SCHOOL_BY_SUBCLASS: Dict[str, str] = {
    "abjurer": "Abjuration",
    "abjuration": "Abjuration",
    "diviner": "Divination",
    "divination": "Divination",
    "evoker": "Evocation",
    "evocation": "Evocation",
    "illusionist": "Illusion",
    "illusion": "Illusion",
    "conjurer": "Conjuration",
    "conjuration": "Conjuration",
    "enchanter": "Enchantment",
    "enchantment": "Enchantment",
    "necromancer": "Necromancy",
    "necromancy": "Necromancy",
    "transmuter": "Transmutation",
    "transmutation": "Transmutation",
}

_SAVANT_FEATURE_RE = re.compile(
    r'^(Abjuration|Conjuration|Divination|Enchantment|Evocation|Illusion|Necromancy|Transmutation)\s+Savant$',
    re.IGNORECASE,
)


def calculate_wizard_spellbook_stats(builder, wizard_level: int) -> Dict[str, Any]:
    """Calculate base spells, Savant bonus spells, and total spellbook allowance for a Wizard."""
    base_spells = 6 + max(0, wizard_level - 1) * 2

    # Subclass Savant detection
    subclass_name = ""
    classes = builder.character_data.get("classes", [])
    if isinstance(classes, list):
        for row in classes:
            if isinstance(row, dict) and str(row.get("class_name", "")).lower() == "wizard":
                subclass_name = str(row.get("subclass", "") or "")
                break
    if not subclass_name:
        subclass_name = str(builder.character_data.get("subclass", "") or "")

    subclass_lower = subclass_name.strip().lower()
    savant_school = _SAVANT_SCHOOL_BY_SUBCLASS.get(subclass_lower)

    if not savant_school:
        subclass_data = builder.character_data.get("subclass_data") or {}
        features_by_lvl = subclass_data.get("features_by_level", {})
        if isinstance(features_by_lvl, dict):
            for lvl_k, features in features_by_lvl.items():
                try:
                    lvl_int = int(lvl_k)
                except ValueError:
                    lvl_int = 0
                if lvl_int <= wizard_level and isinstance(features, dict):
                    for feat_name in features.keys():
                        m = _SAVANT_FEATURE_RE.match(feat_name.strip())
                        if m:
                            savant_school = m.group(1).capitalize()
                            break
                if savant_school:
                    break

    savant_spells = 0
    if savant_school and wizard_level >= 3:
        slot_unlock_levels = [3, 5, 7, 9, 11, 13, 15, 17]
        savant_spells = 2 + sum(1 for lvl in slot_unlock_levels[1:] if wizard_level >= lvl)

    return {
        "base_spells": base_spells,
        "savant_spells": savant_spells,
        "total_spells": base_spells + savant_spells,
        "savant_school": savant_school,
    }


# ---------------------------------------------------------------------------
# Cantrip damage scaling
# ---------------------------------------------------------------------------

def scale_cantrip_damage(base_dice: str, level: int) -> str:
    """Scale cantrip damage dice by character level (D&D 5e/2024 tiers: 5/11/17)."""
    match = re.match(r'(\d+)d(\d+)', base_dice)
    if not match:
        return base_dice
    base_count = int(match.group(1))
    die = match.group(2)

    if level >= 17:
        multiplier = 4
    elif level >= 11:
        multiplier = 3
    elif level >= 5:
        multiplier = 2
    else:
        multiplier = 1

    return f"{base_count * multiplier}d{die}"


def build_damage_cantrip_rows(character_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build damage-cantrip display rows from a `to_character()` output."""
    cantrips = character_data.get("spells_by_level", {}).get(0, []) or []
    spell_stats = character_data.get("spellcasting_stats", {}) or {}
    level = character_data.get("level", 1)
    rows: List[Dict[str, Any]] = []

    for cantrip in cantrips:
        desc = cantrip.get("description", "")
        dmg_match = _DAMAGE_DICE_RE.search(desc)
        if not dmg_match:
            continue

        base_dice = dmg_match.group(1)
        damage_type = dmg_match.group(2).capitalize()
        damage = scale_cantrip_damage(base_dice, level)

        atk_match = _SPELL_ATTACK_RE.search(desc)
        save_match = _SAVING_THROW_RE.search(desc)
        if atk_match:
            bonus = spell_stats.get("spell_attack_bonus", 0)
            atk_display = f"+{bonus}" if bonus >= 0 else str(bonus)
        elif save_match:
            dc = spell_stats.get("spell_save_dc", 0)
            ability = save_match.group(1)[:3].upper()  # "Wisdom" → "WIS"
            atk_display = f"{ability} {dc}"
        else:
            atk_display = ""

        range_text = cantrip.get("range", "").replace(" feet", "ft").replace(" foot", "ft")
        raw_components = cantrip.get("components", [])
        if isinstance(raw_components, str):
            comp_text = raw_components
        else:
            comp_text = ", ".join(c for c in raw_components if c) if raw_components else ""
        notes = f"{range_text} | {comp_text}" if (range_text and comp_text) else (range_text or comp_text)

        rows.append({
            "name": cantrip.get("name", ""),
            "atk_display": atk_display,
            "damage": damage,
            "damage_type": damage_type,
            "notes": notes,
        })

    return rows


# ---------------------------------------------------------------------------
# Spell management view-model
# ---------------------------------------------------------------------------

def _load_class_spell_list(class_name: str, builder=None) -> Dict[str, Any]:
    if not class_name:
        return {}
    if builder is not None and hasattr(builder, "_get_class_spell_list"):
        return builder._get_class_spell_list(class_name)
    if builder is not None and hasattr(builder, "data_loader") and builder.data_loader:
        active_sources = None
        if hasattr(builder, "character_data") and isinstance(builder.character_data, dict):
            active_sources = (
                builder.character_data.get("active_sources")
                or builder.character_data.get("choices_made", {}).get("active_sources")
            )
        res = builder.data_loader.get_class_spells(class_name, active_sources)
        if res:
            return res
    f = _SPELL_CLASS_LISTS / f"{class_name.lower()}.json"
    if not f.exists():
        return {}
    try:
        with open(f, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, IOError):
        return {}


def build_spell_management_view(builder) -> Dict[str, Any]:
    """Return the spell-management modal view as a plain dict.

    Raises `ValueError` if the character is not a spellcaster.
    """
    stats = builder.calculate_spellcasting_stats()
    if not stats or not stats.get("has_spellcasting"):
        raise ValueError("Character is not a spellcaster")

    # Always-prepared
    always_prepared: List[Dict[str, Any]] = []
    spells_block = builder.character_data.get("spells", {}) or {}
    for spell_name, spell_data in (spells_block.get("always_prepared", {}) or {}).items():
        spell_definition = builder._load_spell_definition(spell_name)
        always_prepared.append({
            **spell_definition,
            "name": spell_name,
            "level": spell_data.get("level", spell_definition.get("level", 0)),
            "source": spell_data.get("source", "Unknown"),
            "counts_against_limit": spell_data.get("counts_against_limit", True),
        })

    available_cantrips = [
        builder._load_spell_definition(name)
        for name in stats.get("available_cantrips", []) or []
    ]
    available_spells: Dict[str, List[Dict[str, Any]]] = {}
    for level, spell_names in (stats.get("available_spells", {}) or {}).items():
        available_spells[str(level)] = [
            builder._load_spell_definition(name) for name in spell_names
        ]

    # Filter available spells by levels the character actually has slots for.
    # Read directly from class/subclass data to avoid a full to_character() build.
    _char_level = builder._get_primary_class_level()
    _class_data = builder.character_data.get("class_data") or {}
    _subclass_data = builder.character_data.get("subclass_data") or {}
    _multiclass = builder._calculate_multiclass_spell_slot_progression()
    if _multiclass.get("is_multiclass") and _multiclass.get("spell_slots"):
        _char_slots = _multiclass["spell_slots"]
    else:
        _slots_src = _class_data if _class_data.get("spell_slots_by_level") else _subclass_data
        _level_slots = (_slots_src.get("spell_slots_by_level") or {}).get(str(_char_level), [])
        _char_slots = builder._slots_payload_to_dict(_level_slots)
    available_slot_levels = {
        ORDINAL_TO_INT[name]
        for name in _char_slots
        if name in ORDINAL_TO_INT and _char_slots[name] > 0
    }
    if available_slot_levels:
        available_spells = {
            level: spells
            for level, spells in available_spells.items()
            if int(level) in available_slot_levels
        }

    prepared = spells_block.get("prepared", {})
    if isinstance(prepared, list):
        prepared = {"cantrips": {}, "spells": {}}

    current_prepared_spells = (
        list(prepared.get("spells", {}).keys())
        if isinstance(prepared.get("spells", {}), dict)
        else []
    )

    current_selections = {
        "cantrips": (
            list(prepared.get("cantrips", {}).keys())
            if isinstance(prepared.get("cantrips", {}), dict)
            else []
        ),
        "spells": current_prepared_spells,
        "background_cantrips": [],
        "background_spells": [],
    }

    # Determine primary class and wizard spellbook status
    primary_class_row = builder._get_primary_class_row()
    primary_class_name = (
        primary_class_row.get("class_name", "")
        if primary_class_row
        else builder.character_data.get("class", "")
    ).lower()

    classes_list = builder.character_data.get("classes", [])
    wizard_row = None
    if isinstance(classes_list, list):
        for row in classes_list:
            if isinstance(row, dict) and str(row.get("class_name", "")).lower() == "wizard":
                wizard_row = row
                break
    if not wizard_row and primary_class_name == "wizard":
        wizard_row = primary_class_row or {"class_name": "Wizard", "level": _char_level}

    has_spellbook = wizard_row is not None
    spellbook_limits = None
    spellbook_definitions: List[Dict[str, Any]] = []

    if has_spellbook:
        w_level = int(wizard_row.get("level", _char_level)) if wizard_row else _char_level
        spellbook_limits = calculate_wizard_spellbook_stats(builder, w_level)

        spellbook_raw = spells_block.get("spellbook", {})
        if not spellbook_raw:
            spellbook_raw = (
                (builder.character_data.get("choices_made") or {})
                .get("spell_selections", {})
                .get("spellbook", {})
            )
        if isinstance(spellbook_raw, dict):
            spellbook_names = list(spellbook_raw.keys())
        elif isinstance(spellbook_raw, list):
            spellbook_names = [s for s in spellbook_raw if isinstance(s, str)]
        else:
            spellbook_names = []

        # Backward compatibility: if spellbook is empty but prepared spells exist, populate spellbook
        if not spellbook_names and current_prepared_spells:
            spellbook_names = list(current_prepared_spells)

        current_selections["spellbook"] = spellbook_names
        spellbook_definitions = [
            builder._load_spell_definition(name)
            for name in spellbook_names
        ]

    background_requirements = None
    bg_req = stats.get("background_spell_requirements")
    if bg_req:
        background_requirements = {}
        bg_spells_data = spells_block.get("background_spells", {})

        if bg_req.get("cantrips_needed", 0) > 0:
            bg_class = bg_req.get("cantrip_class", "")
            class_list = _load_class_spell_list(bg_class, builder=builder)
            bg_cantrips = [
                builder._load_spell_definition(name)
                for name in class_list.get("cantrips", []) or []
            ]
            background_requirements["cantrips"] = {
                "count": bg_req["cantrips_needed"],
                "class_name": bg_class,
                "available": bg_cantrips,
            }
            if isinstance(bg_spells_data, dict):
                current_selections["background_cantrips"] = [
                    name for name, data in bg_spells_data.items()
                    if isinstance(data, dict) and data.get("level") == 0
                ]

        if bg_req.get("spells_needed", 0) > 0:
            bg_class = bg_req.get("spell_class", "")
            class_list = _load_class_spell_list(bg_class, builder=builder)
            bg_spell_names = (class_list.get("spells_by_level", {}) or {}).get("1", [])
            bg_spells = [builder._load_spell_definition(name) for name in bg_spell_names]
            background_requirements["spells"] = {
                "count": bg_req["spells_needed"],
                "class_name": bg_class,
                "available": bg_spells,
            }
            if isinstance(bg_spells_data, dict):
                current_selections["background_spells"] = [
                    name for name, data in bg_spells_data.items()
                    if isinstance(data, dict) and data.get("level", 0) > 0
                ]

    limits = {
        "cantrips": stats.get("max_cantrips_to_prepare", 0),
        "spells": stats.get("max_spells_to_prepare", 0),
    }

    # Determine prepare_rule from the primary class name.
    _LONG_REST_CASTERS = {"cleric", "druid", "paladin", "wizard"}
    _LEVEL_UP_CASTERS = {"bard", "ranger", "sorcerer"}
    _SHORT_REST_CASTERS = {"warlock"}

    if limits["cantrips"] == 0 and limits["spells"] == 0 and not always_prepared:
        prepare_rule = "fixed"
    elif primary_class_name in _LONG_REST_CASTERS:
        prepare_rule = "long_rest"
    elif primary_class_name in _LEVEL_UP_CASTERS:
        prepare_rule = "level_up"
    elif primary_class_name in _SHORT_REST_CASTERS:
        prepare_rule = "short_rest"
    else:
        prepare_rule = "long_rest"

    return {
        "always_prepared": always_prepared,
        "available_cantrips": available_cantrips,
        "available_spells": available_spells,
        "has_spellbook": has_spellbook,
        "spellbook": spellbook_definitions,
        "spellbook_limits": spellbook_limits,
        "available_spellbook_spells": available_spells if has_spellbook else None,
        "spell_slots": _char_slots,
        "pact_magic_slots": stats.get("pact_magic_slots", []),
        "current_selections": current_selections,
        "limits": limits,
        "background_requirements": background_requirements,
        "prepare_rule": prepare_rule,
    }


# ---------------------------------------------------------------------------
# Mastery management view-model
# ---------------------------------------------------------------------------

def build_mastery_management_view(builder) -> Dict[str, Any]:
    """Return the weapon-mastery modal view as a plain dict.

    Raises `ValueError` if the character does not have weapon mastery.
    """
    stats = builder.calculate_weapon_mastery_stats()
    if not stats or not stats.get("has_mastery"):
        raise ValueError("Character does not have weapon mastery")

    weapon_masteries: Dict[str, str] = {}
    if _WEAPONS_FILE.exists():
        try:
            with open(_WEAPONS_FILE, "r") as f:
                weapons_data = json.load(f)
            for weapon_name in stats.get("available_weapons", []) or []:
                if weapon_name in weapons_data:
                    weapon_masteries[weapon_name] = weapons_data[weapon_name].get(
                        "mastery", "Unknown"
                    )
        except (json.JSONDecodeError, IOError):
            pass

    # Build mastery_properties: property_name -> { name, description, weapons: [weapon_name, ...] }
    mastery_properties: Dict[str, Any] = {}
    if _WEAPON_MASTERIES_FILE.exists():
        try:
            with open(_WEAPON_MASTERIES_FILE, "r") as f:
                masteries_data = json.load(f)
            for weapon_name, prop_name in weapon_masteries.items():
                if prop_name in masteries_data:
                    if prop_name not in mastery_properties:
                        mastery_properties[prop_name] = {
                            "name": prop_name,
                            "description": masteries_data[prop_name].get("description", ""),
                            "weapons": [],
                        }
                    mastery_properties[prop_name]["weapons"].append(weapon_name)
        except (json.JSONDecodeError, IOError):
            pass

    return {
        "available_weapons": stats.get("available_weapons", []),
        "max_masteries": stats.get("max_masteries", 0),
        "current_masteries": stats.get("current_masteries", []),
        "weapon_masteries": weapon_masteries,
        "mastery_properties": mastery_properties,
    }


# ---------------------------------------------------------------------------
# Eldritch Invocation management view-model
# ---------------------------------------------------------------------------

def build_invocation_management_view(builder) -> Dict[str, Any]:
    """Return the Eldritch Invocation modal view as a plain dict.

    Raises `ValueError` if the character does not have invocations.
    """
    stats = builder.calculate_eldritch_invocation_stats()
    if not stats or not stats.get("has_invocations"):
        raise ValueError("Character does not have Eldritch Invocations")

    view = {
        "available_invocations": stats.get("available_invocations", []),
        "max_invocations": stats.get("max_invocations", 0),
        "current_invocations": stats.get("current_invocations", []),
        "invocations": stats.get("invocations", []),
        "current_choices": stats.get("current_choices", {}),
        "cantrip_choices": stats.get("cantrip_choices", {}),
        "dependency_map": stats.get("dependency_map", {}),
    }
    if stats.get("cantrip_choice_descriptors"):
        view["cantrip_choice_descriptors"] = stats["cantrip_choice_descriptors"]
    if stats.get("invocation_choice_descriptors"):
        view["invocation_choice_descriptors"] = stats["invocation_choice_descriptors"]
    return view


def build_replicate_magic_item_view(builder) -> Dict[str, Any]:
    """Return the Replicate Magic Item modal view as a plain dict.

    Raises `ValueError` if the character does not have Replicate Magic Item.
    """
    stats = builder.calculate_artificer_replications_stats()
    if not stats or not stats.get("has_replications"):
        raise ValueError("Character does not have Replicate Magic Item")
    return stats


# ---------------------------------------------------------------------------
# Level Up Preview view-model
# ---------------------------------------------------------------------------

def _is_choice_dependency_satisfied(choice: Dict[str, Any], choices_made: Dict[str, Any]) -> bool:
    dep_key = choice.get("depends_on")
    if not dep_key:
        return True
    expected = choice.get("depends_on_value")
    actual = choices_made.get(dep_key)
    if actual is None:
        norm_dep = dep_key.strip().lower().replace(" ", "_")
        for k, v in choices_made.items():
            if k.strip().lower().replace(" ", "_") == norm_dep:
                actual = v
                break
    if actual is None:
        return False
    if expected is None:
        return bool(actual)
    if isinstance(actual, list):
        return expected in actual or str(expected).lower() in [str(x).lower() for x in actual]
    return str(actual).lower() == str(expected).lower()


def build_level_up_preview(
    choices_made: Dict[str, Any],
    class_to_level: Any = None,
    subclass_to_level: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute an actionable preview of leveling up a character.

    Calculates HP gains, proficiency bonus scaling, features unlocked at the
    new level, subclass/feat/feature choices required, spell slot advancements,
    and Wizard spellbook expansions.
    """
    from copy import deepcopy
    from modules.character_builder import CharacterBuilder
    from modules.data_loader import DataLoader

    # 1. Inspect current character state
    builder_current = CharacterBuilder()
    builder_current.apply_choices(choices_made, fail_on_error=False)
    char_current = builder_current.to_character()

    # Resolve class allocations
    raw_classes = choices_made.get("classes")
    class_rows: List[Dict[str, Any]] = []
    if isinstance(raw_classes, list) and raw_classes:
        for r in raw_classes:
            if isinstance(r, dict) and r.get("class_name"):
                class_rows.append({
                    "class_name": str(r["class_name"]),
                    "level": int(r.get("level", 1) or 1),
                    "subclass": r.get("subclass"),
                })
    if not class_rows:
        primary_cls = choices_made.get("class") or char_current.get("class") or "Fighter"
        primary_lvl = int(choices_made.get("level") or char_current.get("level") or 1)
        subclass_name = choices_made.get("subclass") or char_current.get("subclass")
        class_rows = [{
            "class_name": str(primary_cls),
            "level": primary_lvl,
            "subclass": subclass_name,
        }]

    current_total_level = sum(r["level"] for r in class_rows)
    if current_total_level >= 20:
        return {
            "can_level_up": False,
            "reason": "Character has already reached the maximum level (20).",
            "current_total_level": current_total_level,
        }

    # Identify target class to advance
    target_row = None
    if class_to_level and isinstance(class_to_level, str):
        for r in class_rows:
            if r["class_name"].lower() == class_to_level.lower():
                target_row = r
                break
    if target_row is None:
        target_row = class_rows[0]

    target_class_name = target_row["class_name"]
    current_class_level = target_row["level"]
    next_class_level = current_class_level + 1
    next_total_level = current_total_level + 1

    # Load class data to determine subclass rules
    class_data = builder_current._load_class_data(target_class_name) or {}
    subclass_selection_level = int(class_data.get("subclass_selection_level", 3) or 3)

    # Subclass resolution:
    # original_subclass is what the character already possessed prior to this level up
    original_subclass = (
        target_row.get("subclass")
        if current_class_level >= subclass_selection_level
        else None
    )
    if not original_subclass and current_class_level >= subclass_selection_level:
        original_subclass = choices_made.get("subclass")

    # Character needs subclass if reaching milestone without an established subclass
    needs_subclass = (next_class_level >= subclass_selection_level) and not bool(original_subclass)

    # active_subclass is the subclass used for computing previews, unlocked features, and choices
    active_subclass = (
        original_subclass
        if not needs_subclass
        else (subclass_to_level or choices_made.get("subclass") or target_row.get("subclass"))
    )

    # 2. Build next level choices
    choices_next = deepcopy(choices_made)
    next_class_rows = deepcopy(class_rows)
    for r in next_class_rows:
        if r["class_name"].lower() == target_class_name.lower():
            r["level"] = next_class_level
            if active_subclass:
                r["subclass"] = active_subclass
            break
    choices_next["classes"] = next_class_rows
    choices_next["level"] = next_total_level
    if next_class_rows[0]["class_name"].lower() == target_class_name.lower():
        choices_next["class"] = target_class_name
        if active_subclass:
            choices_next["subclass"] = active_subclass

    builder_next = CharacterBuilder()
    builder_next.apply_choices(choices_next, fail_on_error=False)
    char_next = builder_next.to_character()

    # 3. HP Increase breakdown
    hit_die = int(class_data.get("hit_die", 8) or 8)
    avg_roll = (hit_die // 2) + 1
    con_score = int(char_current.get("abilities", {}).get("constitution", {}).get("score", 10) or 10)
    con_mod = (con_score - 10) // 2

    current_max_hp = int(char_current.get("combat", {}).get("hit_points", {}).get("maximum", 0) or 0)
    next_max_hp = int(char_next.get("combat", {}).get("hit_points", {}).get("maximum", 0) or 0)
    total_hp_increase = max(1, next_max_hp - current_max_hp)
    feature_hp_bonus = total_hp_increase - (avg_roll + con_mod)

    # 4. Proficiency Bonus
    pb_current = int(char_current.get("proficiency_bonus", 2) or 2)
    pb_next = int(char_next.get("proficiency_bonus", 2) or 2)

    # 5. Features at next level (scoped to the specific class being advanced)
    choices_target_class = deepcopy(choices_next)
    choices_target_class["class"] = target_class_name
    choices_target_class["level"] = next_class_level
    choices_target_class["subclass"] = active_subclass
    choices_target_class["classes"] = [{
        "class_name": target_class_name,
        "level": next_class_level,
        "subclass": active_subclass,
    }]
    builder_target = CharacterBuilder()
    builder_target.apply_choices(choices_target_class, fail_on_error=False)

    feat_data_next = builder_target.get_class_features_and_choices()
    features_by_level = feat_data_next.get("features_by_level", {})
    features_at_lvl = features_by_level.get(next_class_level, [])
    features_gained = []
    for f in features_at_lvl:
        if isinstance(f, dict):
            features_gained.append({
                "name": f.get("name", "Unknown"),
                "description": f.get("description", ""),
                "type": f.get("type", "info"),
                "source": f.get("source", "Class"),
                "level": next_class_level,
            })

    # 6. Subclass requirements
    available_subclasses = []
    if needs_subclass:
        dl = DataLoader(data_dir=str(_DATA_DIR))
        raw_subs = dl.get_subclasses_for_class(target_class_name, choices_made.get("active_sources"))
        for sub_id, sub_data in sorted(raw_subs.items()):
            if isinstance(sub_data, dict):
                # Extract level 3 feature names/descriptions
                l3_features = []
                f_by_l = sub_data.get("features_by_level", {}).get("3", {})
                if isinstance(f_by_l, dict):
                    for fn, fd in f_by_l.items():
                        desc = fd.get("description", "") if isinstance(fd, dict) else str(fd)
                        l3_features.append({"name": fn, "description": desc})
                available_subclasses.append({
                    "id": sub_id,
                    "name": sub_data.get("name", sub_id),
                    "description": sub_data.get("description", ""),
                    "level_3_features": l3_features,
                    "source": sub_data.get("source", "Player's Handbook 2024"),
                })

    # 7. Feat requirements
    all_choices = feat_data_next.get("choices", [])
    feat_choice_key = f"class_feat_{next_class_level}"
    needs_feat = any(
        (c.get("choice_key") == feat_choice_key or c.get("choices_made_key") == feat_choice_key)
        for c in all_choices
    )
    feat_sub_choices = [
        c for c in all_choices
        if (c.get("choice_key") or c.get("choices_made_key") or "").startswith(f"{feat_choice_key}_")
    ]

    # 8. Other Choices at this level (including subclass choices and satisfied dependent choices)
    choices_needed = []
    for c in all_choices:
        ck = c.get("choice_key") or c.get("choices_made_key")
        # Skip the feat slot itself (handled separately via Feat picker)
        if ck and ck.startswith("class_feat_"):
            continue
        if ck in ("skill_choices", "tool_choices"):
            continue

        c_level = c.get("level")
        is_at_this_level = (c_level == next_class_level)

        dep_key = c.get("depends_on")
        if dep_key:
            if not _is_choice_dependency_satisfied(c, choices_made):
                continue
            parent_at_this_level = any(
                (pc.get("choice_key") == dep_key or pc.get("choices_made_key") == dep_key)
                and pc.get("level") == next_class_level
                for pc in all_choices
            )
            if not (is_at_this_level or parent_at_this_level):
                continue
        else:
            if not is_at_this_level:
                continue

        choices_needed.append(c)

    # 9. Spellcasting changes
    current_stats = char_current.get("spellcasting_stats", {}) or {}
    next_stats = char_next.get("spellcasting_stats", {}) or {}
    has_spellcasting = bool(next_stats.get("has_spellcasting"))

    current_slots = char_current.get("spell_slots") or {}
    next_slots = char_next.get("spell_slots") or {}
    current_pact = char_current.get("pact_magic_slots") or {}
    next_pact = char_next.get("pact_magic_slots") or {}

    unlocked_slots = []
    if next_slots and isinstance(next_slots, dict):
        for slot_lvl, count in next_slots.items():
            if int(count or 0) > 0 and int((current_slots or {}).get(slot_lvl, 0) or 0) == 0:
                lvl_num = ORDINAL_TO_INT.get(str(slot_lvl))
                if lvl_num is None:
                    m = re.search(r'\d+', str(slot_lvl))
                    lvl_num = int(m.group(0)) if m else 0
                if lvl_num > 0:
                    unlocked_slots.append(lvl_num)

    is_wizard = target_class_name.lower() == "wizard"
    wizard_spellbook_data = None
    if is_wizard:
        sb_curr = calculate_wizard_spellbook_stats(builder_current, current_class_level)
        sb_next = calculate_wizard_spellbook_stats(builder_next, next_class_level)
        wizard_spellbook_data = {
            "current_limit": sb_curr.get("total_spells", 0),
            "next_limit": sb_next.get("total_spells", 0),
            "spells_added": 2,
            "savant_school": sb_next.get("savant_school"),
            "savant_bonus": sb_next.get("savant_spells", 0) - sb_curr.get("savant_spells", 0),
        }

    # 10. Weapon Mastery changes
    m_curr = builder_current.calculate_weapon_mastery_stats()
    m_next = builder_next.calculate_weapon_mastery_stats()
    mastery_changes = {
        "has_mastery": bool(m_next.get("has_mastery")),
        "current_max": int(m_curr.get("max_masteries", 0) or 0),
        "next_max": int(m_next.get("max_masteries", 0) or 0),
        "increased": int(m_next.get("max_masteries", 0) or 0) > int(m_curr.get("max_masteries", 0) or 0),
    }

    # 11. Eldritch Invocation changes
    inv_curr = builder_current.calculate_eldritch_invocation_stats()
    inv_next = builder_next.calculate_eldritch_invocation_stats()
    is_warlock = target_class_name.lower() == "warlock"
    invocation_changes = {
        "has_invocations": bool(inv_next.get("has_invocations")),
        "is_warlock": is_warlock,
        "current_max": int(inv_curr.get("max_invocations", 0) or 0),
        "next_max": int(inv_next.get("max_invocations", 0) or 0),
        "invocations_gained": max(
            0,
            int(inv_next.get("max_invocations", 0) or 0)
            - int(inv_curr.get("max_invocations", 0) or 0),
        ),
        "allows_swap": is_warlock and next_class_level > current_class_level,
        "current_invocations": inv_curr.get("current_invocations", []),
        "available_invocations": inv_next.get("available_invocations", []),
        "cantrip_choice_descriptors": inv_next.get("cantrip_choice_descriptors", []),
        "invocation_choice_descriptors": inv_next.get("invocation_choice_descriptors", []),
        "dependency_map": inv_next.get("dependency_map", {}),
    }

    rep_curr = builder_current.calculate_artificer_replications_stats()
    rep_next = builder_next.calculate_artificer_replications_stats()
    is_artificer = target_class_name.lower() == "artificer"
    replication_changes = {
        "has_replications": bool(rep_next.get("has_replications")),
        "is_artificer": is_artificer,
        "current_max_plans": int(rep_curr.get("max_plans", 0) or 0),
        "next_max_plans": int(rep_next.get("max_plans", 0) or 0),
        "plans_gained": max(0, int(rep_next.get("max_plans", 0) or 0) - int(rep_curr.get("max_plans", 0) or 0)),
        "current_max_active": int(rep_curr.get("max_active", 0) or 0),
        "next_max_active": int(rep_next.get("max_active", 0) or 0),
        "active_gained": max(0, int(rep_next.get("max_active", 0) or 0) - int(rep_curr.get("max_active", 0) or 0)),
        "known_plans": rep_curr.get("known_plans", []),
        "available_plans": rep_next.get("available_plans", []),
    }

    return {
        "can_level_up": True,
        "class_name": target_class_name,
        "current_class_level": current_class_level,
        "next_class_level": next_class_level,
        "current_total_level": current_total_level,
        "next_total_level": next_total_level,
        "all_classes": class_rows,
        "hp_increase": {
            "hit_die": hit_die,
            "average_roll": avg_roll,
            "con_modifier": con_mod,
            "feature_bonus": feature_hp_bonus,
            "total_increase": total_hp_increase,
            "current_max_hp": current_max_hp,
            "next_max_hp": next_max_hp,
        },
        "proficiency_bonus": {
            "current": pb_current,
            "next": pb_next,
            "increased": pb_next > pb_current,
        },
        "hit_dice": {
            "current": char_current.get("combat", {}).get("hit_dice", {}).get("total", f"{current_total_level}d{hit_die}"),
            "next": char_next.get("combat", {}).get("hit_dice", {}).get("total", f"{next_total_level}d{hit_die}"),
            "gained": f"1d{hit_die}",
        },
        "features_gained": features_gained,
        "subclass": {
            "needs_subclass": needs_subclass,
            "current_subclass": original_subclass,
            "selected_subclass": active_subclass,
            "selection_level": subclass_selection_level,
            "available_subclasses": available_subclasses,
        },
        "feat": {
            "needs_feat": needs_feat,
            "choice_key": feat_choice_key if needs_feat else None,
            "slot_level": next_class_level if needs_feat else None,
            "sub_choices": feat_sub_choices if needs_feat else [],
        },
        "choices_needed": choices_needed,
        "spellcasting_changes": {
            "has_spellcasting": has_spellcasting,
            "current_slots": current_slots,
            "next_slots": next_slots,
            "current_pact_slots": current_pact,
            "next_pact_slots": next_pact,
            "unlocked_slot_levels": sorted(unlocked_slots),
            "current_prepared_limit": int(current_stats.get("max_prepared_spells", 0) or 0),
            "next_prepared_limit": int(next_stats.get("max_prepared_spells", 0) or 0),
            "is_wizard": is_wizard,
            "wizard_spellbook": wizard_spellbook_data,
        },
        "mastery_changes": mastery_changes,
        "invocation_changes": invocation_changes,
        "replication_changes": replication_changes,
    }
