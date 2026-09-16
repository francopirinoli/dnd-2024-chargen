"""Stateless character build endpoints.

These endpoints take a `choices_made` dict in the request body and return
the calculated character. They never touch the Flask session — the React
frontend is the source of truth for in-progress choices, the Python
`CharacterBuilder` is the source of truth for calculated stats.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from modules.ability_scores import ABILITIES
from modules.ability_scores import validate_point_buy
from modules.character_builder import CharacterBuilder, SelectionValidationError
from modules.data_loader import DataLoader
from modules import strict_mode
from modules.derived_stats import (
    build_damage_cantrip_rows,
    build_invocation_management_view,
    build_level_up_preview,
    build_mastery_management_view,
    build_spell_management_view,
)

character_bp = Blueprint("character", __name__, url_prefix="/character")
logger = logging.getLogger(__name__)

_DERIVED_VIEWS = {
    "damage_cantrips",
    "spell_management",
    "mastery_management",
    "invocation_management",
}
_CORE_TRAIT_PROFICIENCY_KEYS = {"skill_choices", "tool_choices"}


class ChoicesValidationError(ValueError):
    """Raised when API request choices are structurally invalid."""

    def __init__(self, message: str, field: str | None = None, code: str = "invalid_request"):
        super().__init__(message)
        self.message = message
        self.field = field
        self.code = code

    def to_response(self) -> Dict[str, Any]:
        error: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.field:
            error["field"] = self.field
        return {"error": error}


_MAX_COLLECTION_ITEMS = 100
_MAX_CLASSES = 12
_MAX_STRING_LENGTH = 512
_MAX_NESTING_DEPTH = 8
_ENDPOINT_FIELDS = {
    "build": {"choices_made"},
    "validate": {"choices_made"},
    "preview-step": {"choices_made", "step"},
    "random-languages": {"choices_made"},
    "derived": {"choices_made", "view"},
    "level-up-preview": {"choices_made"},
}
_OPTIONAL_ENDPOINT_FIELDS = {
    "level-up-preview": {"class_to_level", "subclass_to_level"},
}


def _internal_error_response(action: str, exc: Exception):
    correlation_id = uuid.uuid4().hex
    logger.exception(
        "Unhandled character API error while %s (correlation_id=%s, error_type=%s)",
        action,
        correlation_id,
        exc.__class__.__name__,
    )
    return jsonify({
        "error": "Internal server error",
        "correlation_id": correlation_id,
    }), 500


# ==================== Multiclass nested-choice filtering ====================
#
# Per D&D 2024 multiclassing rules, a secondary class entry grants core-trait
# proficiencies listed in that class's `multiclassing` block while still
# granting class features by level. The class preview pipeline can include many
# nested choices (features from multiple levels), so for secondary rows we only
# filter the core-trait proficiency pickers and preserve all other feature
# choices unchanged.
# Subclass selection is handled by `available_subclasses` / `needs_subclass`
# on the response and is always allowed for any class row.


def _classify_choice_for_multiclass(choice: Dict[str, Any]) -> str:
    """Classify a nested_choice as 'skill', 'tool', or 'other'.

    Inspects the structured `type` field first (set by CharacterBuilder for
    level-1 proficiency pickers), then falls back to keywords in
    `choice_key` / `feature_name` / `title`. Branching is intentionally
    generic — never on specific class or feature names.
    """
    ctype = (choice.get("type") or "").lower()
    if ctype == "skills":
        return "skill"
    if ctype == "tools":
        return "tool"
    if ctype:
        # Explicit type is set but is not skills/tools (e.g. "feature").
        # Do not fall through to keyword matching — the choice is not a
        # basic proficiency pick and must be dropped on secondary rows.
        return "other"
    key = " ".join(
        str(choice.get(k) or "")
        for k in ("choice_key", "feature_name", "title")
    ).lower()
    if "skill" in key:
        return "skill"
    if "tool" in key or "instrument" in key:
        return "tool"
    return "other"


def _parse_tool_wildcard(tool_training: List[Any]) -> Dict[str, Any] | None:
    """Return {count, label} for the first wildcard entry, or None.

    Wildcard form: "<Category> (<N> of your choice)" or any entry containing
    "of your choice" (case-insensitive). Concrete grants like "Thieves' Tools"
    are NOT wildcards and produce no picker.
    """
    for entry in tool_training or []:
        if not isinstance(entry, str) or "of your choice" not in entry.lower():
            continue
        count = 1
        m = re.search(r"\((\d+)\s+of your choice\)", entry, re.IGNORECASE)
        if m:
            count = int(m.group(1))
        label = re.sub(r"\s*\(.*?\)\s*$", "", entry).strip() or entry
        return {"count": count, "label": label}
    return None


def _is_core_trait_proficiency_picker(choice: Dict[str, Any]) -> bool:
    """True when a nested choice is the class core-trait skill/tool picker."""
    key = str(choice.get("choice_key") or "").strip().lower()
    choices_key = str(choice.get("choices_made_key") or "").strip().lower()
    return key in _CORE_TRAIT_PROFICIENCY_KEYS or choices_key in _CORE_TRAIT_PROFICIENCY_KEYS


def _filter_nested_choices_for_secondary_class(
    nested_choices: List[Dict[str, Any]],
    class_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Apply multiclass core-trait proficiency narrowing.

    Core-trait skill/tool pickers are narrowed to the multiclass entry
    (e.g. Rogue multiclass = 1 skill from a constrained list). Other nested
    choices (feature choices at any level) are preserved unchanged.
    """
    multiclass = class_data.get("multiclassing") or {}

    skill_block = multiclass.get("skill_proficiencies")
    allow_skill = isinstance(skill_block, dict)

    tool_wildcard = _parse_tool_wildcard(multiclass.get("tool_training") or [])
    allow_tool = tool_wildcard is not None
    filtered: List[Dict[str, Any]] = []
    for choice in nested_choices:
        kind = _classify_choice_for_multiclass(choice)

        if kind == "skill":
            if not _is_core_trait_proficiency_picker(choice):
                filtered.append(dict(choice))
                continue
            if allow_skill:
                narrowed = dict(choice)
                mc_options = skill_block.get("options")
                # "any" (Bard) → keep the existing full-skill list the builder
                # already expanded. A constrained list (Rogue, Ranger) → use the
                # multiclass list directly as the authoritative set; do NOT
                # intersect with the primary class's skill_options, which may be
                # narrower than the multiclass-entry list per RAW.
                if isinstance(mc_options, list) and mc_options:
                    narrowed["options"] = list(mc_options)
                mc_count = skill_block.get("count")
                if isinstance(mc_count, int) and mc_count > 0:
                    narrowed["count"] = mc_count
                    noun = "proficiency" if mc_count == 1 else "proficiencies"
                    narrowed["description"] = (
                        f"Choose {mc_count} skill {noun} (multiclass)."
                    )
                filtered.append(narrowed)
            continue

        if kind == "tool":
            if not _is_core_trait_proficiency_picker(choice):
                filtered.append(dict(choice))
                continue
            if allow_tool:
                narrowed = dict(choice)
                narrowed["count"] = tool_wildcard["count"]
                # The primary class's tool_options usually already enumerates the
                # category (e.g. Bard's instrument list). If empty, fall back to
                # the label as a single non-selectable entry.
                if not narrowed.get("options"):
                    narrowed["options"] = [tool_wildcard["label"]]
                    # TODO: enumerate the category from a shared data source once
                    # one exists for tool categories beyond Musical Instrument.
                    narrowed["_todo"] = (
                        "Multiclass tool picker has no options list; using label fallback."
                    )
                filtered.append(narrowed)
            continue

        # Preserve all non-core-trait nested choices.
        else:
            filtered.append(dict(choice))

    return filtered


@lru_cache(maxsize=None)
def _load_feat_definitions() -> Dict[str, Dict[str, Any]]:
    """Load feat definitions needed for server-side prerequisite warnings."""
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    feats: Dict[str, Dict[str, Any]] = {}
    for filename, wrapper_key in (
        ("general_feats.json", "general_feats"),
        ("origin_feats.json", "origin_feats"),
    ):
        path = data_dir / filename
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        entries = payload.get(wrapper_key, {})
        if isinstance(entries, dict):
            feats.update({
                name: data
                for name, data in entries.items()
                if isinstance(data, dict)
            })
    return feats


def _class_feat_prerequisite_warnings(
    builder: CharacterBuilder,
    choices: Dict[str, Any],
) -> List[Dict[str, Any]]:
    feats = _load_feat_definitions()
    total_level = 1
    class_rows = choices.get("classes")
    if isinstance(class_rows, list) and class_rows:
        total_level = sum(
            int(row.get("level", 0) or 0)
            for row in class_rows
            if isinstance(row, dict)
        )
    elif isinstance(choices.get("level"), int):
        total_level = int(choices["level"])

    warnings: List[Dict[str, Any]] = []
    for key, selected_feat in choices.items():
        if not re.match(r"^class_feat_\d+$", str(key)):
            continue
        if not isinstance(selected_feat, str) or not selected_feat:
            continue
        feat = feats.get(selected_feat)
        prerequisite = feat.get("prerequisite") if isinstance(feat, dict) else None
        evaluation = builder.evaluate_feat_prerequisite(
            prerequisite,
            level=total_level,
        )
        if not evaluation["met"] and evaluation["messages"]:
            warnings.append({
                "choice_key": key,
                "feat_name": selected_feat,
                "messages": evaluation["messages"],
            })
    return warnings


def _resolve_class_row_context(
    request_choices: Dict[str, Any],
    previewed_class: str | None,
) -> Dict[str, Any]:
    """Determine which row of choices_made.classes is being previewed.

    Resolution rules:
      - No `classes` array (legacy single-class) → row_index 0, primary.
      - Otherwise: find the first row whose class_name matches the previewed
        class. If multiple rows share the class name (rare; e.g. someone
        previewing a duplicate), the first match wins. The request currently
        has no row-index hint — Phase 2 will likely add one; until then,
        first-match is the documented resolution.
    """
    classes = request_choices.get("classes")
    if not isinstance(classes, list) or not classes:
        return {"row_index": 0, "is_primary": True, "total_class_rows": 1}

    total = len(classes)
    row_index = 0
    if previewed_class:
        target = previewed_class.strip().lower()
        for idx, row in enumerate(classes):
            if not isinstance(row, dict):
                continue
            name = row.get("class_name")
            if isinstance(name, str) and name.strip().lower() == target:
                row_index = idx
                break
    return {
        "row_index": row_index,
        "is_primary": row_index == 0,
        "total_class_rows": total,
    }


def _validation_response(exc: ChoicesValidationError):
    error: Dict[str, Any] = {
        "code": exc.code,
        "message": "Invalid character request",
    }
    if exc.field:
        error["field"] = exc.field
    return jsonify({"error": error}), 400


def _require_request(endpoint: str) -> Dict[str, Any]:
    if not request.is_json:
        raise ChoicesValidationError("Body must be a JSON object")
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ChoicesValidationError("Body must be a JSON object")
    allowed = _ENDPOINT_FIELDS[endpoint]
    optional = _OPTIONAL_ENDPOINT_FIELDS.get(endpoint, set())
    unknown = set(body) - (allowed | optional)
    if unknown:
        raise ChoicesValidationError(
            f"Unknown request fields: {', '.join(sorted(unknown))}",
            code="unknown_field",
        )
    missing = allowed - set(body)
    if missing:
        field = sorted(missing)[0]
        raise ChoicesValidationError(
            f"Missing required request fields: {', '.join(sorted(missing))}",
            field,
            code="missing_field",
        )
    if not isinstance(body["choices_made"], dict):
        raise ChoicesValidationError("'choices_made' must be a JSON object", "choices_made")
    return body


def _validate_json_value(value: Any, field: str, depth: int = 0) -> None:
    if depth > _MAX_NESTING_DEPTH:
        raise ChoicesValidationError("Value is nested too deeply", field, "out_of_bounds")
    if isinstance(value, str):
        if len(value) > _MAX_STRING_LENGTH:
            raise ChoicesValidationError("String is too long", field, "out_of_bounds")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, list):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise ChoicesValidationError("Collection has too many items", field, "out_of_bounds")
        for index, item in enumerate(value):
            _validate_json_value(item, f"{field}[{index}]", depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise ChoicesValidationError("Collection has too many items", field, "out_of_bounds")
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > _MAX_STRING_LENGTH:
                raise ChoicesValidationError("Object keys must be bounded non-empty strings", field)
            _validate_json_value(item, f"{field}.{key}", depth + 1)
        return
    raise ChoicesValidationError("Value must be JSON-compatible", field)


def _canonical_identifier(value: Any, options: Dict[str, Any], field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChoicesValidationError("Must be a non-empty string", field)
    normalized = value.strip().casefold()
    canonical = next((name for name in options if name.casefold() == normalized), None)
    if canonical is None:
        raise ChoicesValidationError("Unknown identifier", field, "unknown_identifier")
    return canonical


def _canonical_subclass_identifier(
    value: Any,
    class_name: str,
    loader: DataLoader,
    field: str,
    active_sources: Optional[List[str]] = None,
) -> str:
    subclasses = loader.get_subclasses_for_class(class_name, active_sources)
    try:
        return _canonical_identifier(value, subclasses, field)
    except ChoicesValidationError:
        if not isinstance(value, str) or not value.strip():
            raise
        requested = value.strip().casefold()
        matches = [
            name for name in subclasses
            if name.casefold().startswith(f"{requested} ")
            or name.casefold().endswith(f" {requested}")
            or (
                len(requested.split()) > 1
                and name.casefold().split()[0] == requested.split()[0]
            )
        ]
        if len(matches) == 1:
            return matches[0]
        raise


def _coerce_level(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ChoicesValidationError("Must be an integer", field_name)
    level = value
    if not 1 <= level <= 20:
        raise ChoicesValidationError("Must be between 1 and 20", field_name, "out_of_bounds")
    return level


def _normalize_class_entries(classes: Any, field_name: str = "choices_made.classes") -> List[Dict[str, Any]]:
    """Validate and normalize classes payload entries."""
    if not isinstance(classes, list):
        raise ChoicesValidationError(f"'{field_name}' must be an array")
    if len(classes) == 0:
        raise ChoicesValidationError(f"'{field_name}' must contain at least one class entry")
    if len(classes) > _MAX_CLASSES:
        raise ChoicesValidationError("Too many class entries", field_name, "out_of_bounds")

    normalized_entries: List[Dict[str, Any]] = []
    for idx, class_entry in enumerate(classes):
        entry_path = f"{field_name}[{idx}]"
        if not isinstance(class_entry, dict):
            raise ChoicesValidationError(f"'{entry_path}' must be an object")
        unknown = set(class_entry) - {"class_name", "level", "subclass"}
        if unknown:
            raise ChoicesValidationError(
                f"Unknown class entry fields: {', '.join(sorted(unknown))}",
                entry_path,
                "unknown_field",
            )

        class_name = class_entry.get("class_name")
        if not isinstance(class_name, str) or not class_name.strip():
            raise ChoicesValidationError(f"'{entry_path}.class_name' must be a non-empty string")

        level = _coerce_level(class_entry.get("level"), f"{entry_path}.level")
        normalized_entry: Dict[str, Any] = {
            "class_name": class_name.strip(),
            "level": level,
        }

        subclass = class_entry.get("subclass")
        if subclass is not None:
            if not isinstance(subclass, str):
                raise ChoicesValidationError(f"'{entry_path}.subclass' must be a string when provided")
            if subclass.strip():
                normalized_entry["subclass"] = subclass.strip()

        normalized_entries.append(normalized_entry)

    if sum(entry["level"] for entry in normalized_entries) > 20:
        raise ChoicesValidationError(
            "Total class levels must be between 1 and 20",
            field_name,
            "out_of_bounds",
        )
    return normalized_entries


def _normalize_choices_for_builder(
    choices_made: Dict[str, Any],
    *,
    preserve_explicit_class_context: bool = False,
) -> Dict[str, Any]:
    """Normalize legacy/new class payload shapes into canonical class structures."""
    if not isinstance(choices_made, dict):
        raise ChoicesValidationError("'choices_made' must be a JSON object")

    normalized = dict(choices_made)
    _validate_json_value(normalized, "choices_made")

    # Normalise singular API key → plural internal key expected by CharacterBuilder.
    if "background_skill_replacement" in normalized and "background_skill_replacements" not in normalized:
        replacement_value = normalized.pop("background_skill_replacement")
        if isinstance(replacement_value, str):
            replacement_value = [replacement_value] if replacement_value else []
        normalized["background_skill_replacements"] = replacement_value

    # Normalise singular API key → plural internal key expected by CharacterBuilder.
    if "species_skill_replacement" in normalized and "species_skill_replacements" not in normalized:
        replacement_value = normalized.pop("species_skill_replacement")
        if isinstance(replacement_value, str):
            replacement_value = [replacement_value] if replacement_value else []
        normalized["species_skill_replacements"] = replacement_value

    if "active_supplements" in normalized and "active_sources" not in normalized:
        normalized["active_sources"] = normalized.get("active_supplements")

    classes = normalized.get("classes")
    if classes is None:
        # Legacy compatibility: class/level(/subclass) remains supported.
        class_name = normalized.get("class")
        if isinstance(class_name, str) and class_name.strip():
            level = _coerce_level(normalized.get("level", 1), "choices_made.level")
            class_entry: Dict[str, Any] = {
                "class_name": class_name.strip(),
                "level": level,
            }
            subclass = normalized.get("subclass")
            if isinstance(subclass, str) and subclass.strip():
                class_entry["subclass"] = subclass.strip()
            normalized["classes"] = [class_entry]
            normalized["class"] = class_entry["class_name"]
            normalized["level"] = level
        return normalized

    class_entries = _normalize_class_entries(classes)
    normalized["classes"] = class_entries

    explicit_class = normalized.get("class")
    if (
        preserve_explicit_class_context
        and isinstance(explicit_class, str)
        and explicit_class.strip()
    ):
        target_name = explicit_class.strip()
        matching_entry = next(
            (entry for entry in class_entries if entry.get("class_name") == target_name),
            None,
        )
        if matching_entry is not None:
            explicit_level = matching_entry["level"]
            explicit_subclass = matching_entry.get("subclass") or normalized.get("subclass")
        else:
            explicit_level = _coerce_level(
                normalized.get("level", 1), "choices_made.level"
            )
            explicit_subclass = normalized.get("subclass")

        normalized["class"] = target_name
        normalized["level"] = explicit_level
        class_entry: Dict[str, Any] = {
            "class_name": target_name,
            "level": explicit_level,
        }
        if isinstance(explicit_subclass, str) and explicit_subclass.strip():
            normalized["subclass"] = explicit_subclass.strip()
            class_entry["subclass"] = normalized["subclass"]
        else:
            normalized.pop("subclass", None)
        normalized["classes"] = [class_entry]
        return normalized

    primary = class_entries[0]
    normalized["class"] = primary["class_name"]
    normalized["level"] = sum(entry["level"] for entry in class_entries)
    if primary.get("subclass"):
        normalized["subclass"] = primary["subclass"]
    else:
        normalized.pop("subclass", None)

    return normalized


def _validate_and_canonicalize_choices(
    choices_made: Dict[str, Any],
    *,
    preserve_explicit_class_context: bool = False,
) -> Dict[str, Any]:
    """Reject malformed choices and normalize data-backed identifiers."""
    allowed_keys = strict_mode.KNOWN_CHOICE_KEYS | strict_mode.collect_data_driven_choice_keys({})
    unknown_keys = [
        key for key in choices_made
        if key not in allowed_keys and not strict_mode.is_dynamic_choice_key(key)
    ]
    if unknown_keys:
        raise ChoicesValidationError(
            f"Unknown choices: {', '.join(sorted(unknown_keys))}",
            "choices_made",
            "unknown_field",
        )
    normalized = _normalize_choices_for_builder(
        choices_made,
        preserve_explicit_class_context=preserve_explicit_class_context,
    )
    loader = DataLoader()
    active_sources = normalized.get("active_sources") or normalized.get("sources")
    available_classes = loader.get_classes(active_sources)
    available_species = loader.get_species(active_sources)
    available_backgrounds = loader.get_backgrounds(active_sources)

    if "classes" in normalized:
        seen_classes = set()
        for index, entry in enumerate(normalized["classes"]):
            path = f"choices_made.classes[{index}]"
            entry["class_name"] = _canonical_identifier(
                entry["class_name"], available_classes, f"{path}.class_name"
            )
            class_key = entry["class_name"].casefold()
            if class_key in seen_classes:
                raise ChoicesValidationError("Duplicate class entry", path, "invalid_request")
            seen_classes.add(class_key)
            if "subclass" in entry:
                entry["subclass"] = _canonical_subclass_identifier(
                    entry["subclass"], entry["class_name"], loader, f"{path}.subclass", active_sources
                )
        primary = normalized["classes"][0]
        normalized["class"] = primary["class_name"]
        normalized["level"] = (
            normalized["level"] if "class" in choices_made else sum(
                entry["level"] for entry in normalized["classes"]
            )
        )
        if primary.get("subclass"):
            normalized["subclass"] = primary["subclass"]
    elif "class" in normalized:
        normalized["class"] = _canonical_identifier(
            normalized["class"], available_classes, "choices_made.class"
        )
        normalized["level"] = _coerce_level(
            normalized.get("level", 1), "choices_made.level"
        )
        if "subclass" in normalized and normalized["subclass"] not in (None, ""):
            normalized["subclass"] = _canonical_subclass_identifier(
                normalized["subclass"], normalized["class"], loader, "choices_made.subclass", active_sources
            )

    for key, catalog in (("species", available_species), ("background", available_backgrounds)):
        if key in normalized and normalized[key] not in (None, ""):
            normalized[key] = _canonical_identifier(normalized[key], catalog, f"choices_made.{key}")

    if "lineage" in normalized and normalized["lineage"] not in (None, ""):
        species_name = normalized.get("species")
        if not species_name:
            raise ChoicesValidationError("Requires a selected species", "choices_made.lineage")
        sp_data = available_species.get(species_name) or {}
        lineages = sp_data.get("lineages") or {}
        lineage_options = (
            {name: None for name in lineages}
            if isinstance(lineages, list)
            else lineages
            if isinstance(lineages, dict)
            else {}
        )
        normalized["lineage"] = _canonical_identifier(
            normalized["lineage"], lineage_options, "choices_made.lineage"
        )

    scores = normalized.get("ability_scores", normalized.get("abilities"))
    if scores is not None:
        field = "choices_made.ability_scores" if "ability_scores" in normalized else "choices_made.abilities"
        if not isinstance(scores, dict) or not set(scores).issubset(ABILITIES):
            raise ChoicesValidationError(
                "Must be an ability-to-integer map with valid ability names", field
            )
        if any(isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 20
               for score in scores.values()):
            raise ChoicesValidationError("Scores must be integers between 1 and 20", field)

    for key in (
        "background_ability_score_assignment",
        "background_bonuses",
        "additional_ability_modifiers",
        "ability_modifiers",
    ):
        if key not in normalized:
            continue
        bonuses = normalized[key]
        if (
            not isinstance(bonuses, dict)
            or not set(bonuses).issubset(ABILITIES)
            or any(
                isinstance(value, bool) or not isinstance(value, int) or not -20 <= value <= 20
                for value in bonuses.values()
            )
        ):
            raise ChoicesValidationError(
                "Must be an ability-to-integer map with values between -20 and 20",
                f"choices_made.{key}",
            )

    for key in ("languages", "skill_choices", "tools", "tool_choices", "rare_languages"):
        if key in normalized:
            value = normalized[key]
            if (not isinstance(value, list) or any(not isinstance(item, str) for item in value)
                    or len(value) != len(set(value))):
                raise ChoicesValidationError(
                    "Must be an array of unique strings", f"choices_made.{key}"
                )

    if "inventory" in normalized:
        if not isinstance(normalized["inventory"], dict):
            raise ChoicesValidationError(
                "Must be an inventory object", "choices_made.inventory"
            )

    return normalized

def _build(
    choices_made: Dict[str, Any],
    *,
    preserve_explicit_class_context: bool = False,
) -> CharacterBuilder:
    normalized_choices = _validate_and_canonicalize_choices(
        choices_made,
        preserve_explicit_class_context=preserve_explicit_class_context,
    )
    builder = CharacterBuilder()
    if not builder.apply_choices(normalized_choices, fail_on_error=True):
        raise ChoicesValidationError(
            "A character choice could not be applied",
            code="choice_error",
        )
    return builder


def _enrich_lineages(raw, variant_manager) -> List[Dict[str, Any]]:
    """Normalize lineage data into a uniform list for the SPA.

    Species JSON files store `lineages` either as a list of names
    (`["Drow", "High Elf", ...]`) or as a dict map. Variant detail
    (description, traits) lives in `data/species_variants/`. This
    helper returns a single list of `{id, name, description, traits}`
    so the frontend can render rich lineage cards consistently.
    """
    names: List[str]
    extra: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw, list):
        names = [str(n) for n in raw]
    elif isinstance(raw, dict):
        names = list(raw.keys())
        for n, v in raw.items():
            if isinstance(v, dict):
                extra[n] = v
    else:
        return []

    out: List[Dict[str, Any]] = []
    for name in names:
        variant = variant_manager.get_variant_data(name) or {}
        merged = {
            "id": name,
            "name": variant.get("name", name),
            "description": variant.get("description", ""),
            "traits": variant.get("traits", {}),
        }
        # Per-species inline overrides take precedence over variant file.
        if name in extra:
            merged.update({k: v for k, v in extra[name].items() if v})
        out.append(merged)
    return out


def _subclass_level_feature_names(
    subclass_data: Dict[str, Any],
    level: int = 3,
    limit: int = 3,
) -> List[str]:
    """Return up to `limit` feature names from subclass level data."""
    features_by_level = subclass_data.get("features_by_level")
    if not isinstance(features_by_level, dict):
        return []
    level_data = features_by_level.get(str(level), {})
    if not isinstance(level_data, dict):
        return []
    return [str(name) for name in list(level_data.keys())[:limit]]


# ==================== Build ====================


@character_bp.post("/build")
def build_character():
    """Build a complete character from `choices_made`.

    Request: `{ "choices_made": { ... } }`
    Response: `{ "character": <to_character() output> }`
    """
    try:
        body = _require_request("build")
        builder = _build(body["choices_made"], preserve_explicit_class_context=True)
        return jsonify({"character": builder.to_character()})
    except SelectionValidationError as exc:
        return jsonify(exc.to_error_payload()), 400
    except ChoicesValidationError as exc:
        return _validation_response(exc)
    except ValueError as exc:
        return _validation_response(ChoicesValidationError(str(exc), code="choice_error"))
    except Exception as exc:
        return _internal_error_response("building character", exc)


# ==================== Validate ====================


# Required choice keys for each logical wizard step. Used by /validate to
# report per-step completion. Optional/conditional keys (subclass, lineage,
# trait choices) are evaluated dynamically against the current build.
_STEP_REQUIRED_KEYS: Dict[str, List[str]] = {
    "class": ["class"],
    "background": ["background"],
    "species": ["species"],
    "languages": [],
    "abilities": ["ability_scores"],
    "equipment": [],  # equipment_selections optional
    "complete": [],
}


def _step_status(builder: CharacterBuilder, step: str) -> Dict[str, Any]:
    character = builder.to_character()
    choices = character.get("choices_made", {}) or {}
    missing: List[str] = []

    def _is_empty_choice_value(value: Any) -> bool:
        return value in (None, "", [], {})

    for key in _STEP_REQUIRED_KEYS.get(step, []):
        if key == "class":
            has_legacy_class = bool(choices.get("class"))
            classes = choices.get("classes")
            has_classes = isinstance(classes, list) and len(classes) > 0
            if not has_legacy_class and not has_classes:
                missing.append("class")
            continue

        if key not in choices or choices[key] in (None, "", [], {}):
            missing.append(key)

    # Conditional / dynamic checks per step
    if step == "class":
        from modules.data_loader import DataLoader
        from pathlib import Path

        dl = DataLoader(data_dir=str(Path(__file__).resolve().parent.parent.parent / "data"))

        class_rows = choices.get("classes")
        if isinstance(class_rows, list) and class_rows:
            for idx, row in enumerate(class_rows):
                if not isinstance(row, dict):
                    continue
                class_name = row.get("class_name")
                if not class_name:
                    continue
                try:
                    class_level = int(row.get("level", 1))
                except (TypeError, ValueError):
                    class_level = 1
                cdata = dl.classes.get(class_name, {})
                sub_level = cdata.get("subclass_selection_level", 3)
                if class_level >= sub_level and not row.get("subclass"):
                    missing.append(f"classes[{idx}].subclass")
        else:
            class_name = choices.get("class")
            level = choices.get("level", 1)
            if class_name:
                cdata = dl.classes.get(class_name, {})
                sub_level = cdata.get("subclass_selection_level", 3)
                if level >= sub_level and not choices.get("subclass"):
                    missing.append("subclass")
        # Class feature choices
        try:
            choice_data = builder.get_class_features_and_choices()
            for choice in choice_data.get("choices", []) or []:
                # Mirror the key resolution the frontend uses:
                # choice.choices_made_key ?? choice.choice_key ?? choice.feature_name ?? choice.name
                canonical_key = (
                    choice.get("choices_made_key")
                    or choice.get("choice_key")
                    or choice.get("feature_name")
                    or choice.get("name")
                )
                if not canonical_key:
                    continue
                # Skip conditional choices whose parent condition isn't met yet.
                # Try multiple key variants (snake_case, Title Case) to match how
                # the frontend stores parent choices, mirroring parentKeyVariants().
                depends_on = choice.get("depends_on")
                if depends_on:
                    snake = depends_on.lower().replace(" ", "_").replace("-", "_")
                    title = " ".join(w.capitalize() for w in snake.split("_"))
                    parent_val = next(
                        (choices[k] for k in (depends_on, snake, title) if k in choices),
                        None,
                    )
                    depends_on_value = choice.get("depends_on_value")
                    if depends_on_value is not None:
                        matches = (
                            depends_on_value in parent_val
                            if isinstance(parent_val, list)
                            else parent_val == depends_on_value
                        )
                    else:
                        matches = bool(parent_val)
                    if not matches:
                        continue

                possible_keys = [
                    choice.get("choices_made_key"),
                    choice.get("choice_key"),
                    choice.get("feature_name"),
                    choice.get("name"),
                    f"{choice.get('feature_name')}_{choice.get('choice_key')}",
                    f"{choice.get('feature_name')}_{choice.get('name')}",
                ]
                checked_keys = [k for k in dict.fromkeys(possible_keys) if k]

                key = next((k for k in checked_keys if k in choices), canonical_key)
                val = choices.get(key)
                required_count = choice.get("count", 1)
                if val is None:
                    missing.append(canonical_key)
                elif isinstance(val, list) and len(val) < required_count:
                    missing.append(canonical_key)
        except Exception:
            pass

    elif step == "species":
        species = choices.get("species")
        if species:
            try:
                trait_choices = builder.get_species_trait_choices()
                nested_trait_choices = choices.get("species_trait_choices")
                if not isinstance(nested_trait_choices, dict):
                    nested_trait_choices = {}
                for trait_name in trait_choices.keys():
                    nested_value = nested_trait_choices.get(trait_name)
                    if _is_empty_choice_value(nested_value):
                        missing.append(trait_name)
            except Exception:
                pass
            # lineage required if species has lineages
            from modules.data_loader import DataLoader
            from pathlib import Path
            dl = DataLoader(data_dir=str(Path(__file__).resolve().parent.parent.parent / "data"))
            sdata = dl.species.get(species, {})
            if sdata.get("lineages") and not choices.get("lineage"):
                missing.append("lineage")
            # Skill replacement
            try:
                info = builder.get_species_skill_replacement_info()
                if info.get("needed") and not info.get("already_chosen"):
                    missing.append("species_skill_replacement")
            except Exception:
                pass

    elif step == "background":
        if choices.get("background"):
            try:
                info = builder.get_background_skill_replacement_info()
                if len(info.get("already_chosen", [])) < info.get("needed", 0):
                    missing.append("background_skill_replacement")
            except Exception:
                pass

    elif step == "abilities":
        method = choices.get("ability_scores_method")
        scores = choices.get("ability_scores")
        abilities = [
            "Strength",
            "Dexterity",
            "Constitution",
            "Intelligence",
            "Wisdom",
            "Charisma",
        ]

        if method == "standard_array":
            standard_array = [15, 14, 13, 12, 10, 8]
            valid_standard_array = False
            if isinstance(scores, dict) and all(a in scores for a in abilities):
                try:
                    selected = [int(scores.get(a, 0)) for a in abilities]
                    valid_standard_array = sorted(selected) == sorted(standard_array)
                except (TypeError, ValueError):
                    valid_standard_array = False
            if not valid_standard_array:
                missing.append("ability_scores")
        elif method == "point_buy":
            if not isinstance(scores, dict):
                missing.append("ability_scores")
            else:
                is_valid, _ = validate_point_buy(scores)
                if not is_valid:
                    missing.append("ability_scores")

        # Background ASI bonuses required if applicable
        try:
            asi = builder.get_background_asi_options()
            if asi.get("total_points", 0) > 0 and not choices.get("background_bonuses"):
                missing.append("background_bonuses")
        except Exception:
            pass
    elif step == "languages":
        try:
            language_options = builder.get_language_options()
            required_count = language_options.get("selection_count", 2)
            available_languages = set(language_options.get("available_languages", []))
            selected = choices.get("languages", [])
            if not isinstance(selected, list):
                selected = []

            normalized = []
            for lang in selected:
                if (
                    isinstance(lang, str)
                    and lang in available_languages
                    and lang not in normalized
                ):
                    normalized.append(lang)
            if len(normalized) != required_count:
                missing.append("languages")
        except Exception:
            missing.append("languages")

    return {"step": step, "complete": len(missing) == 0, "missing": missing}


@character_bp.post("/validate")
def validate_character():
    """Return per-step completion status for a `choices_made` payload."""
    try:
        body = _require_request("validate")
        builder = _build(body["choices_made"])
        steps = list(_STEP_REQUIRED_KEYS.keys())
        statuses = [_step_status(builder, s) for s in steps]
        return jsonify({
            "complete": all(s["complete"] for s in statuses),
            "steps": statuses,
        })
    except ChoicesValidationError as exc:
        logger.info("Character validation rejected: %s (field=%s)", exc.message, exc.field)
        return _validation_response(exc)
    except ValueError as exc:
        logger.info("Character validation choice error: %s", exc)
        return _validation_response(ChoicesValidationError(str(exc), code="choice_error"))
    except Exception as exc:
        return _internal_error_response("validating character", exc)


# ==================== Preview step ====================


@character_bp.post("/preview-step")
def preview_step():
    """Return the dynamic, data-driven options for a given wizard step.

    The React frontend posts the current `choices_made` plus the step it
    is rendering; this endpoint returns the structured nested-choice
    schema that should drive the UI for that step. This is what makes the
    wizard data-driven — adding a new species/class/feature in JSON
    automatically surfaces here without any frontend code change.

    Request: `{ "choices_made": {...}, "step": "class" }`
    Response: `{ "step": "class", "nested_choices": [...], "features": ... }`
    """
    try:
        body = _require_request("preview-step")
        step = body["step"]
        if not isinstance(step, str) or step not in _STEP_REQUIRED_KEYS:
            raise ChoicesValidationError("Unknown wizard step", "step", "unknown_identifier")
        # preserve_explicit_class_context ensures that when the frontend sends
        # `class: "druid"` for the active multiclass row, the builder uses only
        # that class — not the first entry in the `classes` array (which would
        # surface the wrong class's features, e.g. Cleric's Divine Order for Druid).
        builder = _build(body["choices_made"], preserve_explicit_class_context=True)
    except ChoicesValidationError as exc:
        return _validation_response(exc)
    except ValueError as exc:
        return _validation_response(ChoicesValidationError(str(exc), code="choice_error"))
    except Exception as exc:
        return _internal_error_response("preparing step preview", exc)

    try:
        result: Dict[str, Any] = {"step": step, "choices_made": body["choices_made"]}
        # Only call to_character() for steps that actually use its result.
        # The "languages" step only needs builder.get_language_options() and must
        # not fail when choices_made is empty (no class/species set yet).
        _STEPS_NEEDING_CHARACTER = {"class", "species", "background", "abilities", "equipment"}
        character = builder.to_character() if step in _STEPS_NEEDING_CHARACTER else {}

        if step == "class":
            request_choices = body.get("choices_made") or {}
            explicit_class = request_choices.get("class")
            class_name = (
                explicit_class.strip()
                if isinstance(explicit_class, str) and explicit_class.strip()
                else character.get("class")
            )
            level = (
                _coerce_level(request_choices.get("level", 1), "choices_made.level")
                if isinstance(explicit_class, str) and explicit_class.strip()
                else character.get("level", 1)
            )
            class_rows = (character.get("choices_made") or {}).get("classes")
            if (
                not isinstance(explicit_class, str)
                or not explicit_class.strip()
            ) and isinstance(class_rows, list) and class_rows and isinstance(class_rows[0], dict):
                class_name = class_rows[0].get("class_name", class_name)
                level = class_rows[0].get("level", level)
            if class_name:
                from modules.data_loader import DataLoader
                from pathlib import Path
                dl = DataLoader(data_dir=str(Path(__file__).resolve().parent.parent.parent / "data"))
                active_sources = request_choices.get("active_sources") or request_choices.get("sources")
                all_classes = dl.get_classes(active_sources)
                # DataLoader keys classes by their canonical-cased name (e.g.
                # "Bard"), but request payloads carry lowercase ("bard"). Do a
                # case-insensitive resolution so the multiclassing block and
                # subclass lookups work regardless of incoming case.
                canonical_class = next(
                    (k for k in all_classes if k.lower() == class_name.lower()),
                    class_name,
                )
                cdata = all_classes.get(canonical_class, {})
                class_summaries = [
                    {"id": key, **value}
                    for key, value in sorted(all_classes.items())
                    if isinstance(value, dict)
                ]
                sub_level = cdata.get("subclass_selection_level", 3)
                result["needs_subclass"] = level >= sub_level
                if result["needs_subclass"]:
                    result["available_subclasses"] = [
                        {
                            "id": n,
                            "name": d.get("name", n),
                            "description": d.get("description", ""),
                            "level_3_feature_names": _subclass_level_feature_names(d),
                            "source": d.get("source") or d.get("source_id", "core-phb-2024"),
                            "source_id": d.get("source_id", "core-phb-2024"),
                            "source_title": d.get("source_title", "Player's Handbook 2024"),
                        }
                        for n, d in sorted(dl.get_subclasses_for_class(canonical_class, active_sources).items())
                    ]
                feature_data = builder.get_class_features_and_choices()
                result["features_by_level"] = feature_data.get("features_by_level", {})
                result["nested_choices"] = feature_data.get("choices", [])

                # Resolve which class row this preview corresponds to and, if it
                # is a secondary multiclass row, filter nested_choices down to
                # only the proficiency picks RAW grants on multiclass entry.
                row_context = _resolve_class_row_context(request_choices, class_name)
                if not row_context["is_primary"]:
                    result["nested_choices"] = _filter_nested_choices_for_secondary_class(
                        result["nested_choices"], cdata
                    )
                result["row_context"] = row_context
                result["multiclass_prerequisites"] = {
                    "classes": {
                        (entry.get("id") or entry.get("name")): builder.evaluate_multiclass_prerequisites(
                            entry,
                            class_summaries,
                        )
                        for entry in class_summaries
                    }
                }
                result["class_feat_prerequisite_warnings"] = (
                    _class_feat_prerequisite_warnings(builder, request_choices)
                )
                # Surface currently-known languages so the frontend can disable
                # them in language choice pickers (e.g. Thieves' Cant).
                result["granted_languages"] = character.get("languages", [])
            else:
                # No class resolved — still surface a legacy single-class context.
                result["row_context"] = {
                    "row_index": 0,
                    "is_primary": True,
                    "total_class_rows": 1,
                }

        elif step == "species":
            species = character.get("species")
            if species:
                from modules.data_loader import DataLoader
                from modules.variant_manager import VariantManager
                from pathlib import Path
                dl = DataLoader(data_dir=str(Path(__file__).resolve().parent.parent.parent / "data"))
                request_choices = body.get("choices_made") or {}
                active_sources = request_choices.get("active_sources") or request_choices.get("sources")
                all_species = dl.get_species(active_sources)
                sdata = all_species.get(species, {})
                if not sdata:
                    match = next((s for s in all_species if s.lower() == species.lower()), None)
                    if match:
                        sdata = all_species[match]
                result["traits"] = sdata.get("traits", {})
                result["lineages"] = _enrich_lineages(sdata.get("lineages", {}), VariantManager(active_sources=active_sources))
                result["trait_choices"] = builder.get_species_trait_choices()
                result["species_feat_choices"] = builder.get_species_feat_choices()
                result["skill_replacement"] = builder.get_species_skill_replacement_info()
                # Surface the background's granted feat so the UI can grey it
                # out in the species feat picker (e.g. Human "Versatile").
                try:
                    bg_feat_info = builder.get_feat_choices()
                    if bg_feat_info.get("feat_name"):
                        result["background_feat"] = bg_feat_info["feat_name"]
                except Exception:
                    pass
                # Include currently-granted proficiencies so feat skill pickers
                # can grey out already-covered options.
                result["granted_proficiencies"] = {
                    "skills": character.get("proficiencies", {}).get("skills", []),
                    "tools": character.get("proficiencies", {}).get("tools", []),
                }

        elif step == "background":
            background = character.get("background")
            if background:
                result["skill_replacement"] = builder.get_background_skill_replacement_info()
                result["origin_feat_choices"] = builder.get_feat_choices()
            # Include currently-granted skill and tool proficiencies so the UI
            # can grey out already-covered options in feat skill pickers (e.g.
            # the Skilled origin feat).
            result["granted_proficiencies"] = {
                "skills": character.get("proficiencies", {}).get("skills", []),
                "tools": character.get("proficiencies", {}).get("tools", []),
            }

        elif step == "languages":
            result["language_options"] = builder.get_language_options()

        elif step == "abilities":
            result["background_asi"] = builder.get_background_asi_options()
            result["ability_generation"] = builder.get_ability_generation_state()
            class_name = character.get("class", "")
            if class_name:
                from modules.data_loader import DataLoader
                from pathlib import Path
                dl = DataLoader(data_dir=str(Path(__file__).resolve().parent.parent.parent / "data"))
                cdata = dl.classes.get(class_name, {})
                recommended = cdata.get("standard_array_assignment")
                if isinstance(recommended, dict):
                    result["recommended_array"] = recommended

        elif step == "equipment":
            class_name = character.get("class", "")
            background_name = character.get("background", "")
            from modules.data_loader import DataLoader
            from pathlib import Path
            dl = DataLoader(data_dir=str(Path(__file__).resolve().parent.parent.parent / "data"))
            result["class_equipment"] = dl.classes.get(class_name, {}).get("starting_equipment", {})
            result["background_equipment"] = dl.backgrounds.get(background_name, {}).get("starting_equipment", {})

        return jsonify(result)
    except ValueError as exc:
        return _validation_response(ChoicesValidationError(str(exc), code="choice_error"))
    except Exception as exc:
        return _internal_error_response("rendering step preview", exc)


@character_bp.post("/random-languages")
def random_languages():
    """Return a random valid language selection for the language step."""
    try:
        body = _require_request("random-languages")
        builder = _build(body["choices_made"])
        return jsonify({"languages": builder.roll_languages()})
    except ChoicesValidationError as exc:
        return _validation_response(exc)
    except ValueError as exc:
        return _validation_response(ChoicesValidationError(str(exc), code="choice_error"))
    except Exception as exc:
        return _internal_error_response("generating random languages", exc)


@character_bp.post("/roll-abilities")
def roll_abilities():
    """Return server-rolled 4d6-drop-lowest ability score candidates."""
    try:
        builder = CharacterBuilder()
        return jsonify({"rolls": builder.roll_ability_scores()})
    except Exception as exc:
        return _internal_error_response("rolling ability scores", exc)


# ==================== Derived views ====================


@character_bp.post("/derived")
def derived_view():
    """Return a derived view-model from `choices_made` for the React SPA.

    Request: `{ "choices_made": {...}, "view": "damage_cantrips" | "spell_management" |
                "mastery_management" | "invocation_management" }`
    Response: `{ "view": "<name>", "applicable": true|false, "data": {...}|null }`

    Returns 400 on missing/invalid body or unknown view. If a view is valid but
    not applicable to the current character (e.g. invocations on a non-Warlock),
    returns 200 with `applicable: false` and a human-readable `reason`.
    """
    try:
        body = _require_request("derived")
        view = body["view"]
        if not isinstance(view, str) or view not in _DERIVED_VIEWS:
            return jsonify({
                "error": {
                    "code": "unknown_identifier",
                    "field": "view",
                    "message": "Unknown derived view",
                },
                "allowed": sorted(_DERIVED_VIEWS),
            }), 400
        builder = _build(body["choices_made"], preserve_explicit_class_context=True)
    except ChoicesValidationError as exc:
        return _validation_response(exc)
    except ValueError as exc:
        return _validation_response(ChoicesValidationError(str(exc), code="choice_error"))
    except Exception as exc:
        return _internal_error_response("building derived view", exc)

    try:
        if view == "damage_cantrips":
            data = build_damage_cantrip_rows(builder.to_character())
        elif view == "spell_management":
            data = build_spell_management_view(builder)
        elif view == "mastery_management":
            data = build_mastery_management_view(builder)
        else:  # invocation_management
            data = build_invocation_management_view(builder)
        return jsonify({
            "view": view,
            "applicable": True,
            "choices_made": body["choices_made"],
            "data": data,
        })
    except ValueError as exc:
        return jsonify({
            "view": view,
            "applicable": False,
            "choices_made": body["choices_made"],
            "reason": str(exc),
            "data": None,
        })
    except Exception as exc:
        return _internal_error_response("rendering derived view", exc)


# ==================== Level Up Preview ====================


@character_bp.post("/level-up-preview")
def level_up_preview():
    """Return an actionable preview of leveling up the character.

    Request: `{ "choices_made": {...}, "class_to_level": optional str }`
    Response: `{ "preview": {...} }`
    """
    try:
        body = _require_request("level-up-preview")
        class_to_level = body.get("class_to_level")
        subclass_to_level = body.get("subclass_to_level")
        data = build_level_up_preview(
            body["choices_made"],
            class_to_level=class_to_level,
            subclass_to_level=subclass_to_level,
        )
        return jsonify({"preview": data})
    except ChoicesValidationError as exc:
        return _validation_response(exc)
    except ValueError as exc:
        return _validation_response(ChoicesValidationError(str(exc), code="choice_error"))
    except Exception as exc:
        return _internal_error_response("generating level up preview", exc)

