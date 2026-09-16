"""Shared helper functions for route modules.

This module provides common functionality used across all route blueprints,
including session management and logging utilities.
"""

import logging
from typing import Optional, Dict, Any
from flask import session, url_for as flask_url_for, redirect
from modules.character_builder import CharacterBuilder
from modules.data_loader import DataLoader

# Valid edit sections and the builder step each one sets
EDIT_SECTIONS = {
    "class": "class",
    "background": "background",
    "species": "species",
    "languages": "languages",
    "abilities": "ability_scores",
    "equipment": "equipment",
}

logger = logging.getLogger(__name__)


def get_builder_from_session() -> Optional[CharacterBuilder]:
    """
    Get CharacterBuilder from session.

    Returns:
        CharacterBuilder if found in session, None otherwise
    """
    if "builder_state" not in session:
        return None

    builder = CharacterBuilder()
    builder.from_json(session["builder_state"])
    return builder


def save_builder_to_session(builder: CharacterBuilder):
    """
    Save CharacterBuilder state to session.

    Args:
        builder: The CharacterBuilder instance to save
    """
    session["builder_state"] = builder.to_json()
    session.modified = True


# ==================== Edit Mode Helpers ====================


def is_editing() -> bool:
    """Check if the user is currently editing from the summary page."""
    return "editing_section" in session


def get_editing_section() -> Optional[str]:
    """Get the section currently being edited, or None."""
    return session.get("editing_section")


def clear_editing():
    """Clear the editing flag from the session."""
    session.pop("editing_section", None)
    session.modified = True


def set_editing(section: str):
    """Set the editing section flag in the session."""
    session["editing_section"] = section
    session.modified = True


def redirect_after_edit_or(default_endpoint: str, **kwargs):
    """If editing, clear flag and redirect to summary. Otherwise redirect to default."""
    if is_editing():
        clear_editing()
        builder = get_builder_from_session()
        if builder:
            builder.set_step("complete")
            save_builder_to_session(builder)
        return redirect(flask_url_for("character_summary.character_summary"))
    return redirect(flask_url_for(default_endpoint, **kwargs))


def log_route_processing(
    route_name: str,
    choices_made: Dict[str, Any],
    builder_before: Optional[CharacterBuilder],
    builder_after: Optional[CharacterBuilder],
):
    """
    Log route processing with choices made and builder changes.

    Args:
        route_name: Name of the route being processed
        choices_made: Dictionary of choices made in this route
        builder_before: Builder state before processing (unused but kept for compatibility)
        builder_after: Builder state after processing (unused but kept for compatibility)
    """
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Route: {route_name}")
    logger.info(f"{'=' * 80}")

    # Log choices made in this route
    if choices_made:
        logger.info("Choices made:")
        for key, value in choices_made.items():
            if isinstance(value, list):
                logger.info(f"  {key}: [{', '.join(str(v) for v in value)}]")
            else:
                logger.info(f"  {key}: {value}")
    else:
        logger.info("No choices made in this route")

    logger.info(f"{'=' * 80}\n")


# ==================== Navigation Context ====================

_data_loader = None


def _get_data_loader() -> DataLoader:
    """Lazy-load DataLoader singleton."""
    global _data_loader
    if _data_loader is None:
        _data_loader = DataLoader()
    return _data_loader


def _species_has_trait_choices(species_name: str) -> bool:
    """Check if a species has trait choices."""
    dl = _get_data_loader()
    species_data = dl.species.get(species_name, {})
    if "traits" in species_data:
        for trait_data in species_data["traits"].values():
            if isinstance(trait_data, dict) and trait_data.get("type") == "choice":
                return True
    return False


def _species_has_lineages(species_name: str) -> bool:
    """Check if a species has lineage variants."""
    dl = _get_data_loader()
    species_data = dl.species.get(species_name, {})
    return bool(species_data.get("lineages"))


def get_nav_context(builder: CharacterBuilder, current_step: str) -> Dict[str, Any]:
    """Compute navigation labels and URLs for the wizard step.

    Returns a dict with keys:
        back_url, back_label, next_label
    that templates can pass directly to the wizard_nav macro.
    """
    character = builder.to_json()
    species_name = character.get("species", "")
    level = character.get("level", 1)
    dl = _get_data_loader()
    class_name = character.get("class", "")
    class_data = dl.classes.get(class_name, {})
    subclass_level = class_data.get("subclass_selection_level", 3)
    has_subclass = level >= subclass_level and class_name in dl.classes

    ctx: Dict[str, Any] = {}

    if current_step == "create":
        ctx["back_url"] = flask_url_for("index.index")
        ctx["back_label"] = "Back to Home"
        ctx["next_label"] = "Continue to Class Selection"

    elif current_step == "class":
        ctx["back_url"] = flask_url_for("character_creation.create_character")
        ctx["back_label"] = "Back to Character Details"
        ctx["next_label"] = "Continue to Class Features"

    elif current_step == "class_choices":
        ctx["back_url"] = flask_url_for("character_creation.choose_class")
        ctx["back_label"] = "Back to Class Selection"
        ctx["next_label"] = "Continue to Background"

    elif current_step == "background":
        ctx["back_url"] = flask_url_for("character_creation.class_choices")
        ctx["back_label"] = "Back to Class Features"
        ctx["next_label"] = "Continue to Species Selection"

    elif current_step == "background_skill_replacement":
        ctx["back_url"] = flask_url_for("background.choose_background")
        ctx["back_label"] = "Back to Background"
        ctx["next_label"] = "Confirm & Continue"

    elif current_step == "feat_choices":
        ctx["back_url"] = flask_url_for("background.choose_background")
        ctx["back_label"] = "Back to Background"
        ctx["next_label"] = "Continue to Species Selection"

    elif current_step == "species":
        ctx["back_url"] = flask_url_for("background.choose_background")
        ctx["back_label"] = "Back to Background"
        if species_name and _species_has_trait_choices(species_name):
            ctx["next_label"] = "Continue to Species Traits"
        elif species_name and _species_has_lineages(species_name):
            ctx["next_label"] = "Continue to Lineage"
        else:
            ctx["next_label"] = "Continue to Languages"

    elif current_step == "species_traits":
        ctx["back_url"] = flask_url_for("species.choose_species")
        ctx["back_label"] = "Back to Species"
        if species_name and _species_has_lineages(species_name):
            ctx["next_label"] = "Continue to Lineage"
        else:
            ctx["next_label"] = "Continue to Languages"

    elif current_step == "species_feat_choices":
        ctx["back_url"] = flask_url_for("species.choose_species_traits")
        ctx["back_label"] = "Back to Species Traits"
        if species_name and _species_has_lineages(species_name):
            ctx["next_label"] = "Continue to Lineage"
        else:
            ctx["next_label"] = "Continue to Languages"

    elif current_step == "lineage":
        ctx["back_url"] = flask_url_for("species.choose_species")
        ctx["back_label"] = "Back to Species"
        ctx["next_label"] = "Continue to Languages"

    elif current_step == "species_skill_replacement":
        # Back depends on whether the species has lineages
        if species_name and _species_has_lineages(species_name):
            ctx["back_url"] = flask_url_for("species.choose_lineage")
            ctx["back_label"] = "Back to Lineage"
        elif species_name and _species_has_trait_choices(species_name):
            ctx["back_url"] = flask_url_for("species.choose_species_traits")
            ctx["back_label"] = "Back to Species Traits"
        else:
            ctx["back_url"] = flask_url_for("species.choose_species")
            ctx["back_label"] = "Back to Species"
        ctx["next_label"] = "Confirm & Continue"

    elif current_step == "languages":
        # Back: to lineage if species has lineages, else to species
        if species_name and _species_has_lineages(species_name):
            ctx["back_url"] = flask_url_for("species.choose_lineage")
            ctx["back_label"] = "Back to Lineage"
        elif species_name and _species_has_trait_choices(species_name):
            ctx["back_url"] = flask_url_for("species.choose_species_traits")
            ctx["back_label"] = "Back to Species Traits"
        else:
            ctx["back_url"] = flask_url_for("species.choose_species")
            ctx["back_label"] = "Back to Species"
        ctx["next_label"] = "Continue to Ability Scores"

    elif current_step == "ability_scores":
        ctx["back_url"] = flask_url_for("languages.choose_languages")
        ctx["back_label"] = "Back to Languages"
        ctx["next_label"] = "Continue to Equipment"

    elif current_step == "equipment":
        ctx["back_url"] = flask_url_for("ability_scores.assign_ability_scores")
        ctx["back_label"] = "Back to Ability Scores"
        ctx["next_label"] = "Complete Character"

    else:
        ctx["back_url"] = None
        ctx["back_label"] = "Back"
        ctx["next_label"] = "Continue"

    # Edit mode: override labels and add editing flag
    editing = is_editing()
    ctx["editing"] = editing
    if editing:
        # Map each section to its terminal steps (where the section ends)
        editing_section = get_editing_section()
        terminal_steps = {
            "class": ["class_choices"],
            "background": ["feat_choices", "background_skill_replacement"],
            "species": ["species", "species_traits", "species_feat_choices",
                        "lineage", "species_skill_replacement"],
            "languages": ["languages"],
            "abilities": ["ability_scores"],
            "equipment": ["equipment"],
        }
        section_terminals = terminal_steps.get(editing_section, [])
        if current_step in section_terminals:
            ctx["next_label"] = "Save & Return to Summary"

    return ctx
