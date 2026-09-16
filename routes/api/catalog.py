"""Read-only catalog endpoints — game data exposed as JSON.

The frontend uses these to populate selection lists. All responses come
straight from the data files via `DataLoader`; no character state is
involved.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from flask import Blueprint, jsonify, abort, request

from modules.data_loader import DataLoader

catalog_bp = Blueprint("catalog", __name__, url_prefix="/catalog")

_data_loader: DataLoader | None = None
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _dl() -> DataLoader:
    global _data_loader
    if _data_loader is None:
        _data_loader = DataLoader(data_dir=str(_DATA_DIR))
    return _data_loader


def _get_active_sources() -> Optional[List[str]]:
    sources_param = request.args.get("sources")
    if sources_param:
        return [s.strip() for s in sources_param.split(",") if s.strip()]
    return None


def _summarize(name: str, data: Dict[str, Any], extra_fields: List[str]) -> Dict[str, Any]:
    summary = {"id": name, "name": data.get("name", name)}
    if "description" in data:
        summary["description"] = data["description"]
    if "source" in data:
        summary["source"] = data["source"]
    if "source_id" in data:
        summary["source_id"] = data["source_id"]
    if "source_title" in data:
        summary["source_title"] = data["source_title"]
    for field in extra_fields:
        if field in data:
            summary[field] = data[field]
    return summary


# ==================== Classes ====================


@catalog_bp.get("/classes")
def list_classes():
    sources = _get_active_sources()
    classes = _dl().get_classes(sources)
    return jsonify({
        "classes": [
            _summarize(name, data, ["hit_die", "primary_ability", "subclass_selection_level"])
            for name, data in sorted(classes.items())
        ]
    })


@catalog_bp.get("/classes/<class_name>")
def get_class(class_name: str):
    sources = _get_active_sources()
    classes = _dl().get_classes(sources)
    data = classes.get(class_name)
    if data is None:
        match = next((c for c in classes if c.lower() == class_name.lower()), None)
        if match:
            data = classes[match]
    if data is None:
        abort(404, description=f"Unknown class: {class_name}")
    return jsonify(data)


@catalog_bp.get("/classes/<class_name>/subclasses")
def list_subclasses(class_name: str):
    sources = _get_active_sources()
    classes = _dl().get_classes(sources)
    if class_name not in classes:
        # Check case-insensitive
        match = next((c for c in classes if c.lower() == class_name.lower()), None)
        if match:
            class_name = match
        else:
            abort(404, description=f"Unknown class: {class_name}")
    subclasses = _dl().get_subclasses_for_class(class_name, sources)
    return jsonify({
        "class": class_name,
        "subclasses": [
            _summarize(name, data, [])
            for name, data in sorted(subclasses.items())
        ],
    })


@catalog_bp.get("/classes/<class_name>/subclasses/<subclass_name>")
def get_subclass(class_name: str, subclass_name: str):
    sources = _get_active_sources()
    subclasses = _dl().get_subclasses_for_class(class_name, sources)
    data = subclasses.get(subclass_name)
    if data is None:
        match = next((s for s in subclasses if s.lower() == subclass_name.lower()), None)
        if match:
            data = subclasses[match]
    if data is None:
        data = _dl().supplement_manager.get_subclass(class_name, subclass_name, sources)
    if data is None:
        abort(404, description=f"Unknown subclass: {subclass_name}")
    return jsonify(data)


# ==================== Species ====================


@catalog_bp.get("/species")
def list_species():
    sources = _get_active_sources()
    species = _dl().get_species(sources)
    out = []
    for name, data in sorted(species.items()):
        summary = _summarize(name, data, ["creature_type", "size", "speed", "darkvision"])
        summary["has_lineages"] = bool(data.get("lineages"))
        summary["has_trait_choices"] = any(
            isinstance(t, dict) and t.get("type") == "choice"
            for t in data.get("traits", {}).values()
        )
        out.append(summary)
    return jsonify({"species": out})


@catalog_bp.get("/species/<species_name>")
def get_species(species_name: str):
    sources = _get_active_sources()
    data = _dl().supplement_manager.get_species_detail(species_name, sources)
    if data is None:
        all_species = _dl().get_species(sources)
        match = next((s for s in all_species if s.lower() == species_name.lower()), None)
        if match:
            data = all_species[match]
    if data is None:
        abort(404, description=f"Unknown species: {species_name}")
    return jsonify(data)


# ==================== Backgrounds ====================


def _extract_background_feat(data: Dict[str, Any]) -> str | None:
    """Return the feat name from a grant_origin_feat effect, or None."""
    for effect in data.get("effects", []):
        if effect.get("type") == "grant_origin_feat":
            return effect.get("feat")
    return None


def _is_default_background(data: Dict[str, Any]) -> bool:
    """Return True for backgrounds in the default D&D 2024 catalog."""
    return data.get("edition") == "2024" and data.get("status") == "active"


@catalog_bp.get("/backgrounds")
def list_backgrounds():
    sources = _get_active_sources()
    backgrounds = _dl().get_backgrounds(sources)
    include_legacy = request.args.get("include_legacy", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    items = []
    for name, data in sorted(backgrounds.items()):
        if not include_legacy and not _is_default_background(data) and data.get("source_id") == _dl().supplement_manager.CORE_ID:
            continue
        enriched = dict(data)
        if "feat" not in enriched:
            feat = _extract_background_feat(data)
            if feat is not None:
                enriched["feat"] = feat
        items.append(_summarize(name, enriched, ["skill_proficiencies", "ability_scores", "feat", "edition", "status"]))
    return jsonify({"backgrounds": items})


@catalog_bp.get("/backgrounds/<background_name>")
def get_background(background_name: str):
    data = _dl().supplement_manager.get_background(background_name)
    if data is None:
        abort(404, description=f"Unknown background: {background_name}")
    enriched = dict(data)
    skill_proficiencies: List[str] = []
    tool_proficiencies: List[str] = []
    for effect in data.get("effects", []):
        etype = effect.get("type")
        if etype == "grant_skill_proficiency":
            skill_proficiencies.extend(effect.get("skills", []))
        elif etype == "grant_tool_proficiency":
            tool_proficiencies.extend(effect.get("tools", []))
    if skill_proficiencies and "skill_proficiencies" not in enriched:
        enriched["skill_proficiencies"] = skill_proficiencies
    if tool_proficiencies and "tool_proficiencies" not in enriched:
        enriched["tool_proficiencies"] = tool_proficiencies
    if "feat" not in enriched:
        feat = _extract_background_feat(data)
        if feat is not None:
            enriched["feat"] = feat
    return jsonify(enriched)


# ==================== Feats ====================


@catalog_bp.get("/feats")
def list_feats():
    feat_type = request.args.get("type")  # "origin", "general", or None
    sources = _get_active_sources()
    feats = _dl().get_feats(feat_type=feat_type, active_sources=sources)
    items = []
    for name, data in sorted(feats.items()):
        category = data.get("category", "general")
        if feat_type:
            ft = feat_type.strip().lower().replace("_", " ")
            cat = category.strip().lower().replace("_", " ")
            if ft != cat and not (ft == "general" and cat in ("general", "epic boon")):
                continue
        items.append(_summarize(name, data, ["category", "prerequisites"]))
    return jsonify({"feats": items})


@catalog_bp.get("/feats/<feat_name>")
def get_feat(feat_name: str):
    data = _dl().get_feats().get(feat_name)
    if data is None:
        abort(404, description=f"Unknown feat: {feat_name}")
    return jsonify(data)


# ==================== Spells ====================


@catalog_bp.get("/spells/<class_name>")
def list_class_spells(class_name: str):
    """Return the spell list for a class, optionally filtered by level.

    Query: ?level=N (0 = cantrips). Omit to return all.
    """
    sources = _get_active_sources()
    data = _dl().get_class_spells(class_name, sources)
    if data is None or (not data.get("cantrips") and not data.get("spells_by_level")):
        abort(404, description=f"No spell list for class: {class_name}")
    level_param = request.args.get("level")
    if level_param is None:
        return jsonify(data)
    try:
        level = int(level_param)
    except ValueError:
        abort(400, description="level must be an integer")
    if level == 0:
        return jsonify({"class": data.get("class"), "level": 0, "spells": data.get("cantrips", [])})
    spells = data.get("spells_by_level", {}).get(str(level), [])
    return jsonify({"class": data.get("class"), "level": level, "spells": spells})


@catalog_bp.get("/spells/definitions/<spell_name>")
def get_spell_definition(spell_name: str):
    """Return the full spell definition for a single spell."""
    sources = _get_active_sources()
    data = _dl().get_spell_definition(spell_name, sources)
    if data is None:
        abort(404, description=f"Unknown spell: {spell_name}")
    return jsonify(data)


# ==================== Equipment ====================


@catalog_bp.get("/equipment")
def get_all_equipment():
    """Return a unified catalog of all basic items (weapons, armor, adventuring gear)."""
    items = []

    # 1. Weapons
    weapons_path = _DATA_DIR / "equipment" / "weapons.json"
    if weapons_path.exists():
        with open(weapons_path, "r", encoding="utf-8") as f:
            weapons_data = json.load(f)
            for name, w in sorted(weapons_data.items()):
                items.append({
                    "id": f"wep_{name.lower().replace(' ', '_')}",
                    "name": name,
                    "category": "Weapon",
                    "subcategory": w.get("category", "Weapon"),
                    "cost": w.get("cost", "—"),
                    "weight": w.get("weight", 0),
                    "damage": w.get("damage"),
                    "damage_type": w.get("damage_type"),
                    "properties": w.get("properties", []),
                    "mastery": w.get("mastery"),
                })

    # 2. Armor & Shields
    armor_path = _DATA_DIR / "equipment" / "armor.json"
    if armor_path.exists():
        with open(armor_path, "r", encoding="utf-8") as f:
            armor_data = json.load(f)
            for name, a in sorted(armor_data.items()):
                cat = "Shield" if a.get("category") == "Shield" or name == "Shield" else "Armor"
                items.append({
                    "id": f"arm_{name.lower().replace(' ', '_')}",
                    "name": name,
                    "category": cat,
                    "subcategory": a.get("category", cat),
                    "cost": a.get("cost", "—"),
                    "weight": a.get("weight", 0),
                    "ac_base": a.get("ac_base"),
                    "ac_formula": a.get("ac_formula"),
                    "ac_bonus": a.get("ac_bonus", 2 if cat == "Shield" else 0),
                    "stealth_disadvantage": a.get("stealth_disadvantage", False),
                    "strength_requirement": a.get("strength_requirement"),
                })

    # 3. Adventuring Gear & Tools
    gear_path = _DATA_DIR / "equipment" / "adventuring_gear.json"
    if gear_path.exists():
        with open(gear_path, "r", encoding="utf-8") as f:
            gear_data = json.load(f)
            for name, g in sorted(gear_data.items()):
                raw_cat = g.get("category", "Gear")
                cat = "Tool" if raw_cat == "Tool" else "Consumable" if raw_cat in ("Consumable", "Potion") else "Gear"
                items.append({
                    "id": f"gear_{name.lower().replace(' ', '_')}",
                    "name": name,
                    "category": cat,
                    "subcategory": raw_cat,
                    "cost": g.get("cost", "—"),
                    "weight": g.get("weight", 0),
                })

    return jsonify({"items": items})


@catalog_bp.get("/equipment/<kind>")
def get_equipment(kind: str):
    allowed = {"weapons", "armor", "adventuring_gear", "weapon_masteries"}
    if kind not in allowed:
        abort(404, description=f"Unknown equipment kind: {kind}. Valid: {sorted(allowed)}")
    path = _DATA_DIR / "equipment" / f"{kind}.json"
    if not path.exists():
        abort(404, description=f"Equipment file missing: {kind}.json")
    with open(path, "r") as f:
        return jsonify(json.load(f))


# ==================== Fighting Styles / Invocations / etc. ====================


@catalog_bp.get("/reference/<name>")
def get_reference(name: str):
    """Top-level reference JSON files (fighting_styles, eldritch_invocations, etc.)."""
    allowed = {
        "fighting_styles",
        "eldritch_invocations",
        "origin_feats",
        "general_feats",
        "trait_patterns",
    }
    if name not in allowed:
        abort(404, description=f"Unknown reference: {name}")

    sources = _get_active_sources()
    if name == "origin_feats":
        feats = _dl().get_feats(feat_type="origin", active_sources=sources)
        return jsonify({"origin_feats": feats})
    elif name == "general_feats":
        feats = _dl().get_feats(feat_type="general", active_sources=sources)
        return jsonify({"general_feats": feats})
    elif name == "eldritch_invocations":
        invocations = _dl().get_eldritch_invocations(active_sources=sources)
        return jsonify(invocations)

    path = _DATA_DIR / f"{name}.json"
    if not path.exists():
        abort(404, description=f"Reference file missing: {name}.json")
    with open(path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))
