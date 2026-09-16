"""Wizard metadata endpoints.

Expose the structure of the character-creation wizard as data so the React
frontend doesn't need to hardcode step ordering or cascade rules. Adding
a new step here propagates to the UI without frontend changes.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

wizard_bp = Blueprint("wizard", __name__, url_prefix="/wizard")


# Logical user-facing wizard steps. Each step may contain conditional
# nested choices (handled by /api/v1/character/preview-step). The
# breadcrumb in the SPA renders one entry per step in this list.
_STEPS = [
    {
        "id": "class",
        "label": "Class",
        "description": "Class selection(s), per-class levels, subclass (when level qualifies), and class feature choices.",
        "required_keys": ["class"],
        "nested_choices": ["subclass", "fighting_style", "maneuvers", "spells", "cantrips"],
    },
    {
        "id": "background",
        "label": "Background",
        "description": "Background, origin feat, and skill overlap resolution.",
        "required_keys": ["background"],
        "nested_choices": ["background_skill_replacement", "origin_feat"],
    },
    {
        "id": "species",
        "label": "Species",
        "description": "Species, trait choices, lineage, species feat, and skill overlap.",
        "required_keys": ["species"],
        "nested_choices": [
            "lineage",
            "species_trait_choices",
            "species_feat_choices",
            "species_skill_replacement",
        ],
    },
    {
        "id": "languages",
        "label": "Languages",
        "description": "Choose exactly two additional languages or roll randomly.",
        "required_keys": [],
    },
    {
        "id": "abilities",
        "label": "Ability Scores",
        "description": "Assign ability scores and apply background ASI bonuses.",
        "required_keys": ["ability_scores"],
        "nested_choices": ["background_bonuses"],
    },
    {
        "id": "equipment",
        "label": "Equipment",
        "description": "Pick starting equipment from class and background.",
        "required_keys": [],
    },
    {
        "id": "complete",
        "label": "Summary",
        "description": "Review the finished character.",
        "required_keys": [],
    },
]


# Cascade rules: changing any key on the left side invalidates all keys on
# the right side. The React frontend uses this to clear downstream choices
# before submitting a rebuild — preventing stale subclass / spell picks
# when the class changes, etc.
_DEPENDENCIES = {
    "classes": [
        "subclass",
        "fighting_style",
        "maneuvers",
        "spells",
        "cantrips",
        "class_features",
        "skill_choices",
        "tool_choices",
        "background_skill_replacement",
        "equipment_selections",
    ],
    "level": ["subclass", "spells", "cantrips", "fighting_style", "maneuvers", "class_features"],
    "class": [
        "subclass",
        "fighting_style",
        "maneuvers",
        "spells",
        "cantrips",
        "class_features",
        "skill_choices",
        "tool_choices",
        "background_skill_replacement",
        "equipment_selections",
    ],
    "subclass": ["subclass_features", "spells", "cantrips"],
    "background": [
        "background_bonuses",
        "background_skill_replacement",
        "origin_feat",
        "feat_choices",
        "equipment_selections",
    ],
    "species": [
        "lineage",
        "species_trait_choices",
        "species_feat_choices",
        "species_skill_replacement",
        "languages",
    ],
    "lineage": ["lineage_features", "lineage_spells", "languages"],
}


@wizard_bp.get("/steps")
def get_steps():
    return jsonify({"steps": _STEPS})


@wizard_bp.get("/dependencies")
def get_dependencies():
    """Return the cascade map: changing key X invalidates dependent keys."""
    return jsonify({"dependencies": _DEPENDENCIES})
