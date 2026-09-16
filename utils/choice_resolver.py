"""
Choice resolution utilities for the Choice Reference System.
Handles resolving choice options from various source types.
"""

import json
import os
from functools import lru_cache
from pathlib import Path


def _spellbook_entries(spellbook: object) -> list[tuple[str, dict]]:
    """Normalize persisted spellbook names/entries for computed choices."""
    if isinstance(spellbook, dict):
        return [
            (name, data if isinstance(data, dict) else {})
            for name, data in spellbook.items()
            if isinstance(name, str)
        ]
    if isinstance(spellbook, list):
        entries = []
        for item in spellbook:
            if isinstance(item, str):
                entries.append((item, {}))
            elif isinstance(item, dict) and isinstance(item.get("name"), str):
                entries.append((item["name"], item))
        return entries
    return []


@lru_cache(maxsize=1)
def _spell_definitions_by_name() -> dict[str, dict]:
    """Index trusted spell definitions once for computed spellbook choices."""
    definitions_dir = Path(__file__).parent.parent / "data" / "spells" / "definitions"
    definitions = {}
    for definition_path in definitions_dir.glob("*.json"):
        try:
            with definition_path.open("r", encoding="utf-8") as f:
                definition = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(definition, dict) and isinstance(definition.get("name"), str):
            # Retain the first glob-order match, as the former per-name scan did.
            definitions.setdefault(definition["name"], definition)
    return definitions


def _spell_definition(name: str) -> dict:
    """Return a canonical definition used to filter a spellbook choice."""
    if not isinstance(name, str):
        return {}
    return _spell_definitions_by_name().get(name, {})


def _matches_filter(entry: dict, filters: object) -> bool:
    """Return whether an entry satisfies every declarative source filter."""
    if not isinstance(filters, dict):
        return True
    for key, expected in filters.items():
        actual = entry.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def is_unresolved_placeholder(skill_value: object) -> bool:
    return (
        isinstance(skill_value, str)
        and skill_value.startswith("__")
        and skill_value.endswith("__")
    )


def resolve_data_file_path(file_path: str) -> Path | None:
    """Resolve *file_path* against ``data/`` and reject anything outside it.

    ``file_path`` is a relative path taken from a choice ``source`` block. Some
    of those blocks are built from player selections (``external_dynamic``
    patterns, class-derived spell lists), so the resolved path is verified to
    stay inside the data directory before it is opened.
    """
    if not isinstance(file_path, str) or not file_path:
        return None
    data_dir = os.path.realpath(str(Path(__file__).parent.parent / "data"))
    candidate = os.path.realpath(os.path.join(data_dir, file_path))
    if not candidate.startswith(data_dir + os.sep):
        return None
    return Path(candidate)


def resolve_choice_options(
    choices_data: dict,
    character: dict,
    class_data: dict | None = None,
    subclass_data: dict | None = None,
) -> list:
    """Resolve choice options from various source types in the Choice Reference System."""
    source = choices_data.get("source", {})
    source_type = source.get("type")

    if source_type == "internal":
        # Reference list within same JSON file (e.g., fighting_styles in Fighter, maneuvers in Battle Master)
        list_name = source.get("list", "")
        # Try subclass_data first (for subclass features), then class_data (for class features)
        data_source = (
            subclass_data
            if subclass_data and list_name in subclass_data
            else class_data
        )
        if data_source and list_name in data_source:
            choice_list = data_source[list_name]
            if isinstance(choice_list, dict):
                return list(choice_list.keys())
            elif isinstance(choice_list, list):
                return choice_list
        return []
    elif source_type == "external":
        # Reference specific external file
        file_path = source.get("file", "")
        list_name = source.get("list", "")
        active_sources = None
        if isinstance(character, dict):
            active_sources = (
                character.get("choices_made", {}).get("active_sources")
                or character.get("active_sources")
            )
        if not active_sources:
            active_sources = ["core-phb-2024"]

        if list_name in ("general_feats", "origin_feats"):
            try:
                from modules.data_loader import DataLoader
                dl = DataLoader()
                feat_type = "general" if list_name == "general_feats" else "origin"
                feats = dl.get_feats(feat_type=feat_type, active_sources=active_sources)
                if feats:
                    return list(feats.keys())
            except Exception:
                pass
        return load_external_choice_list(file_path, list_name, active_sources=active_sources)
    elif source_type == "external_dynamic":
        # Dynamic file based on previous choice
        file_pattern = source.get("file_pattern", "")
        depends_on = source.get("depends_on", "")
        list_name = source.get("list", "")

        # Get the dependency value from character's choices
        choices_made = character.get("choices_made", {})
        dependency_value = choices_made.get(depends_on)

        if dependency_value:
            active_sources = None
            if isinstance(character, dict):
                active_sources = (
                    character.get("choices_made", {}).get("active_sources")
                    or character.get("active_sources")
                )
            if not active_sources:
                active_sources = ["core-phb-2024"]
            file_path = file_pattern.format(**{depends_on: dependency_value})
            return load_external_choice_list(file_path, list_name, active_sources=active_sources)
        return []
    elif source_type == "fixed_list":
        # Direct option list
        return source.get("options", [])
    elif source_type == "fixed_list_intersect_proficiencies":
        # Filter fixed options to skills the character is currently proficient in
        fixed_options = source.get("options", [])
        proficient = set(character.get("proficiencies", {}).get("skills", []))
        return [option for option in fixed_options if option in proficient]
    elif source_type == "proficient_skills":
        # Skills the character is currently proficient in
        return [
            skill
            for skill in character.get("proficiencies", {}).get("skills", [])
            if not is_unresolved_placeholder(skill)
        ]
    elif source_type == "computed":
        from_value = source.get("from", "")
        if from_value == "skill_proficiencies":
            skills = [
                skill
                for skill in character.get("proficiencies", {}).get("skills", [])
                if not is_unresolved_placeholder(skill)
            ]
            if not skills and class_data:
                # Fall back to the class's available skill options when
                # proficiencies haven't been resolved yet (e.g. during
                # preview-step before skill choices are submitted).
                # Filter out "Any" sentinel values used by some classes to
                # indicate "any skill" — callers expect concrete skill names.
                skill_options = class_data.get("skill_options", [])
                if isinstance(skill_options, list):
                    return [s for s in skill_options if s.lower() != "any"]
            return skills
        if from_value == "spellbook":
            filters = source.get("filter", {})
            options = []
            for name, stored_entry in _spellbook_entries(
                character.get("spells", {}).get("spellbook", {})
            ):
                spell = _spell_definition(name)
                if not spell:
                    spell = stored_entry
                if spell and _matches_filter(spell, filters):
                    options.append(name)
            return options
    elif source_type == "reference":
        target = source.get("target", "")
        if target == "skills":
            return [
                "Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception",
                "History", "Insight", "Intimidation", "Investigation", "Medicine",
                "Nature", "Perception", "Performance", "Persuasion", "Religion",
                "Sleight of Hand", "Stealth", "Survival"
            ]
        elif target == "languages":
            lang_path = resolve_data_file_path("languages.json")
            if lang_path and lang_path.exists():
                try:
                    with open(lang_path, "r", encoding="utf-8") as f:
                        ldata = json.load(f)
                        return ldata.get("standard", []) + ldata.get("rare", [])
                except Exception:
                    pass
            return [
                "Common Sign Language", "Draconic", "Dwarvish", "Elvish", "Giant",
                "Gnomish", "Goblin", "Halfling", "Orc", "Abyssal", "Celestial",
                "Deep Speech", "Druidic", "Giant Owl", "Gnoll", "Primordial",
                "Sylvan", "Thieves' Cant", "Undercommon"
            ]

    return []


def get_option_descriptions(
    feature_data: dict,
    choices_data: dict,
    class_data: dict | None = None,
    subclass_data: dict | None = None,
) -> dict:
    """Get option descriptions from various sources."""
    # First check if feature_data has option_descriptions field
    if "option_descriptions" in feature_data:
        return feature_data["option_descriptions"]

    # For external sources, load the file and extract descriptions
    source = choices_data.get("source", {})
    if source.get("type") == "external":
        file_path = source.get("file", "")
        list_name = source.get("list", "")
        if list_name in ("general_feats", "origin_feats"):
            try:
                from modules.data_loader import DataLoader
                dl = DataLoader()
                feat_type = "general" if list_name == "general_feats" else "origin"
                feats = dl.get_feats(feat_type=feat_type)
                if feats:
                    return {
                        k: v.get("description", "")
                        for k, v in feats.items()
                        if isinstance(v, dict) and "description" in v
                    }
            except Exception:
                pass
        if file_path and list_name:
            try:
                full_path = resolve_data_file_path(file_path)
                if full_path is not None and full_path.exists():
                    with open(full_path, "r") as f:
                        data = json.load(f)
                        # Support dot-notation for nested keys
                        choice_list = data
                        for key in list_name.split("."):
                            if isinstance(choice_list, dict):
                                choice_list = choice_list.get(key, {})
                            else:
                                choice_list = {}
                                break
                        if isinstance(choice_list, dict):
                            # Extract descriptions from structured objects
                            descriptions = {}
                            for key, value in choice_list.items():
                                if isinstance(value, dict) and "description" in value:
                                    descriptions[key] = value["description"]
                                elif isinstance(value, str):
                                    descriptions[key] = value
                                else:
                                    descriptions[key] = str(value)
                            return descriptions
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load descriptions from {file_path}: {e}")

    # For internal sources, look for the list in the data
    if source.get("type") == "internal":
        list_name = source.get("list", "")
        # Try subclass_data first, then class_data
        data_source = (
            subclass_data
            if subclass_data and list_name in subclass_data
            else class_data
        )
        if data_source and list_name in data_source:
            choice_list = data_source[list_name]
            if isinstance(choice_list, dict):
                # Extract descriptions from structured objects (e.g., divine_orders with effects)
                descriptions = {}
                for key, value in choice_list.items():
                    if isinstance(value, dict) and "description" in value:
                        descriptions[key] = value["description"]
                    elif isinstance(value, str):
                        descriptions[key] = value
                    else:
                        descriptions[key] = str(value)
                return descriptions

    return {}


def load_external_choice_list(
    file_path: str, list_name: str, active_sources: list | None = None
) -> list:
    """Load choice options from external JSON file.

    ``list_name`` may use dot-notation to traverse nested keys,
    e.g. ``"spells_by_level.1"`` resolves ``data["spells_by_level"]["1"]``.
    """
    normalized_path = file_path.replace("\\", "/")
    if normalized_path.startswith("spells/class_lists/"):
        try:
            from modules.data_loader import DataLoader
            dl = DataLoader()
            class_name = Path(normalized_path).stem.lower()
            data = dl.get_class_spells(class_name, active_sources)
            if data:
                choice_list = data
                for key in list_name.split("."):
                    if isinstance(choice_list, dict):
                        choice_list = choice_list.get(key, {})
                    else:
                        return []
                if isinstance(choice_list, dict):
                    return list(choice_list.keys())
                elif isinstance(choice_list, list):
                    return choice_list
        except Exception as e:
            print(f"Warning: Could not load class spells via DataLoader: {e}")

    try:
        full_path = resolve_data_file_path(file_path)
        if full_path is not None and full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Support dot-notation for nested keys
                choice_list = data
                for key in list_name.split("."):
                    if isinstance(choice_list, dict):
                        choice_list = choice_list.get(key, {})
                    else:
                        return []
                if isinstance(choice_list, dict):
                    return list(choice_list.keys())
                elif isinstance(choice_list, list):
                    return choice_list
        return []
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load choice list from {file_path}: {e}")
        return []
