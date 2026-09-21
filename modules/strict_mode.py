"""
Strict-mode toggle, known-effect/known-choice registries.

Audit Phase 5 (P2-6, D6-4): catch typos in JSON data and unknown keys in
``choices_made`` early, instead of letting them silently no-op.

Toggle
------
Default ON in dev and tests, OFF in production. Controlled by:

- ``DND_STRICT_EFFECTS=1``  → strict ON  (explicit)
- ``DND_STRICT_EFFECTS=0``  → strict OFF (explicit; takes precedence over FLASK_ENV)
- ``FLASK_ENV=production``  → strict OFF (default for prod)
- otherwise                 → strict ON

In strict mode, violations raise ``ValueError``. In lenient mode, they emit a
``warnings.warn`` so production logs still surface them without breaking
mid-build.

The closed effect-type enum mirrors ``models/_shared/effect.json`` and is the
source of truth for ``_apply_effect``'s strict check. The two are kept in sync
by ``tests/core/test_strict_mode.py``.
"""

from __future__ import annotations

import os
import re
import warnings
from typing import Any, Dict, Iterable, Set


# ---------------------------------------------------------------------------
# Toggle
# ---------------------------------------------------------------------------

def is_strict() -> bool:
    """Return True if strict effect/choice validation is enabled."""
    explicit = os.environ.get("DND_STRICT_EFFECTS")
    if explicit is not None:
        return explicit.strip().lower() not in ("0", "false", "no", "")
    if os.environ.get("FLASK_ENV", "").lower() == "production":
        return False
    return True


def _violate(msg: str) -> None:
    """Raise in strict mode, warn in lenient mode."""
    if is_strict():
        raise ValueError(msg)
    warnings.warn(msg, stacklevel=3)


# ---------------------------------------------------------------------------
# Closed effect.type enum (mirrors models/_shared/effect.json)
# ---------------------------------------------------------------------------

KNOWN_EFFECT_TYPES: frozenset = frozenset({
    "ability_bonus",
    "attack_ability_override",
    "alternative_ac",
    "bonus_ac",
    "bonus_attack",
    "bonus_damage",
    "bonus_hp",
    "bonus_initiative",
    "bonus_spell_damage_ability_mod",
    "bonus_spell_range",
    "grant_arcane_shot",
    "grant_arcane_shot_dice",
    "grant_armor_proficiency",
    "grant_cantrip",
    "grant_cantrip_choice",
    "grant_condition_immunity",
    "grant_damage_resistance",
    "grant_darkvision",
    "grant_language",
    "grant_magical_darkness_sight",
    "grant_maneuver",
    "grant_origin_feat",
    "grant_save_advantage",
    "grant_save_proficiency",
    "grant_skill_expertise",
    "grant_skill_proficiency",
    "grant_skill_proficiency_or_expertise",
    "grant_spell",
    "grant_spell_at_will",
    "grant_superiority_dice",
    "grant_tool_proficiency",
    "grant_weapon_proficiency",
    "grant_spell_slots",
    "grant_weapon_mastery",
    "great_weapon_fighting",
    "increase_speed",
    "monk_dexterous_attacks",
    "set_martial_arts_die",
    "two_weapon_fighting_modifier",
    "unarmed_fighting",
})


def check_effect_type(effect_type: Any, source_label: str) -> None:
    """Validate an ``effect['type']`` against the closed enum.

    Called at the top of ``CharacterBuilder._apply_effect``. Some of the 28
    types (e.g. ``bonus_ac``, ``bonus_damage``) intentionally have no branch
    in ``_apply_effect`` — they are consumed downstream by calculation methods
    that read ``applied_effects``. That asymmetry is what Phase 6 collapses;
    Phase 5 just makes sure no typo'd type slips through.
    """
    if not isinstance(effect_type, str) or not effect_type:
        _violate(
            f"effect missing or non-string 'type' field "
            f"(source={source_label!r})"
        )
        return
    if effect_type not in KNOWN_EFFECT_TYPES:
        _violate(
            f"unknown effect type {effect_type!r} "
            f"(source={source_label!r}); not in closed enum. "
            f"Add it to models/_shared/effect.json and modules/strict_mode.py "
            f"in lockstep — see .github/instructions/effects-system.instructions.md."
        )


# ---------------------------------------------------------------------------
# Known top-level keys in choices_made
# ---------------------------------------------------------------------------
#
# Two sources of truth:
#   (1) Static well-known keys explicitly handled by CharacterBuilder.apply_choice.
#   (2) Dynamic per-feat / per-feature keys (regex predicate below).
#
# Any choice key that matches neither (1) nor (2) AND is not a feature/choice
# name found in currently-loaded class/subclass/species/lineage data is
# treated as unknown.

# (1) Static keys handled explicitly in apply_choice's if/elif chain.
KNOWN_CHOICE_KEYS: frozenset = frozenset({
    # Supplements / active sources
    "active_sources",
    "sources",
    "supplement_sources",
    "active_supplements",
    # Identity
    "character_name",
    "name",
    "alignment",
    # Species / lineage
    "species",
    "lineage",
    "lineage_spellcasting_ability",
    "species_trait_choices",
    "species_skill_replacements",
    "species_feat_choices",
    # Class / level / multiclass
    "class",
    "subclass",
    "level",
    "classes",
    # Background
    "background",
    "background_skill_replacements",
    "background_skill_replacement",      # Singular alias normalised by apply_choices
    "background_ability_score_assignment",
    "background_bonuses",
    "background_bonuses_method",
    # Abilities
    "ability_scores",
    "abilities",
    "ability_scores_method",
    "additional_ability_modifiers",
    "ability_modifiers",
    # Languages
    "languages",
    "rare_languages",
    # Proficiencies
    "skill_choices",
    "skills",
    "tool_choices",
    "tools",
    # Spellcasting
    "spellcasting",
    "spell_selections",
    # Class-data-driven
    "weapon mastery",
    "weapon_mastery_selections",
    "eldritch_invocation_selections",
    "pact_weapon",
    "maneuvers",
    "arcane_shots",
    # Barbarian
    "primal_knowledge_skill",
    "aspect_of_the_wilds",
    "subclass_aspect_of_the_wilds",
    # Bard / Supplements
    "primal_lore_skill",
    # Cleric
    "divine_order",
    "blessed_strikes",
    "knowledge_artisan_tool",
    "knowledge_skills",
    # Artificer Replicate Magic Item
    "artificer_replicate_plans",
    "artificer_plans",
    "artificer_active_replications",
    "artificer_active_items",
    "artificer_replications",
    # Equipment
    "equipment_selections",
    "inventory",
    # Backend-internal counters written into choices_made by the builder
    # itself (not authored by frontend payloads). Surface here so strict
    # mode does not flag them on round-trip rebuild.
    "background_skill_replacements_needed",
    "species_skill_replacements_needed",
    # Multiclass entry-skill picks (separate from primary-class skill_choices).
    "multiclass_skill_choices",
    # Documented in data/example_complete_character.json as the split
    # between skills granted by the class vs. the background. The backend
    # does NOT read these keys (skill_choices / background_skill_replacements
    # are the canonical handlers). Listed here so the sample file does not
    # trip strict mode. Phase 5 finding — flagged for follow-up: either drop
    # them from the sample or wire them into apply_choice.
    "class_skills",
    "background_skills",
    # Legacy species trait flat keys that the resolver still accepts
    # (apply_choices.normalize lifts these into species_trait_choices).
    # These do not have dedicated handlers; treat them as known so legacy
    # fixtures don't trip strict mode.
    "elven lineage",
    "gnomish lineage",
})


# (2) Dynamic-key regex predicates. Each key these match is considered well-formed.
_DYNAMIC_KEY_PATTERNS = tuple(re.compile(p) for p in (
    # Class-level feat slot, e.g. "class_feat_4"
    r"^class_feat_\d+$",
    # Class-level feat sub-choice, e.g. "class_feat_4_ability"
    r"^class_feat_\d+_.+$",
    # Namespaced feat choice, e.g. "feat_Skilled_skills_or_tools"
    r"^feat_.+$",
    # Subclass-prefixed feature choice, e.g. "subclass_Spellcasting_cantrips"
    r"^subclass_.+$",
    # Species-trait-prefixed flat key (legacy), e.g. "species_trait_Elven Lineage"
    r"^species_trait_.+$",
    # Nested bonus-cantrip choice emitted by _add_nested_choices_from_effects,
    # e.g. "Thaumaturge_bonus_cantrip", "Druidic Warrior_bonus_cantrip".
    r"^.+_bonus_cantrip$",
    # Class expertise choices, e.g. "bard_expertise_skills_2", "rogue_expertise_skills_1"
    r"^.+_expertise_skills_\d+$",
))


def is_dynamic_choice_key(key: str) -> bool:
    """True if *key* matches one of the dynamic-key patterns."""
    if not isinstance(key, str):
        return False
    return any(p.match(key) for p in _DYNAMIC_KEY_PATTERNS)


def _normalize(key: str) -> str:
    return key.strip().lower().replace(" ", "_")


# ---------------------------------------------------------------------------
# Global cache of every feature/choice name authored in data/
# ---------------------------------------------------------------------------
#
# The catch-all branch in CharacterBuilder.apply_choice dispatches by matching
# the incoming choice_key against any feature_name found in class/subclass/
# species/lineage data — regardless of whether that data is currently loaded
# in the active builder. To keep strict-mode validation aligned with that
# behaviour (and to avoid false positives on sparse fixtures like
# data/example_complete_character.json), we scan all of data/ once and cache
# every feature_name + nested-choice name + species-trait name.

_AUTHORED_KEYS_CACHE: Set[str] | None = None


def _authored_choice_keys() -> Set[str]:
    """Lazily collect every feature/choice/trait name authored in data/.

    Includes both the raw name and its ``snake_case`` form so that
    ``"Fighting Style"`` matches both ``"Fighting Style"`` and
    ``"fighting_style"`` in incoming payloads.
    """
    global _AUTHORED_KEYS_CACHE
    if _AUTHORED_KEYS_CACHE is not None:
        return _AUTHORED_KEYS_CACHE

    import json
    from pathlib import Path

    keys: Set[str] = set()

    def _add(name: Any) -> None:
        if isinstance(name, str) and name:
            keys.add(name)
            keys.add(_normalize(name))

    def _walk_features_by_level(fbl: Any) -> None:
        if not isinstance(fbl, dict):
            return
        for level_features in fbl.values():
            if not isinstance(level_features, dict):
                continue
            for feature_name, fd in level_features.items():
                _add(feature_name)
                if isinstance(fd, dict):
                    nested = fd.get("choices")
                    if isinstance(nested, list):
                        for ci in nested:
                            if isinstance(ci, dict):
                                _add(ci.get("name"))
                    elif isinstance(nested, dict):
                        _add(nested.get("name"))

    def _walk_doc(doc: Any) -> None:
        if not isinstance(doc, dict):
            return
        _walk_features_by_level(doc.get("features_by_level"))
        traits = doc.get("traits") or {}
        if isinstance(traits, dict):
            for trait_name, tdata in traits.items():
                _add(trait_name)
                if isinstance(tdata, dict):
                    nested = tdata.get("choices")
                    if isinstance(nested, list):
                        for ci in nested:
                            if isinstance(ci, dict):
                                _add(ci.get("name"))
        # Lineages live under species docs and have their own traits.
        lineages = doc.get("lineages") or {}
        if isinstance(lineages, dict):
            for ldata in lineages.values():
                _walk_doc(ldata)

    # data/ resolved relative to this file: modules/strict_mode.py
    repo_root = Path(__file__).resolve().parent.parent
    data_root = repo_root / "data"
    if not data_root.exists():
        _AUTHORED_KEYS_CACHE = keys
        return keys

    for subdir in ("classes", "species", "species_variants", "backgrounds"):
        d = data_root / subdir
        if not d.exists():
            continue
        for f in d.glob("*.json"):
            try:
                _walk_doc(json.loads(f.read_text()))
            except (json.JSONDecodeError, OSError):
                pass
    subclass_dir = data_root / "subclasses"
    if subclass_dir.exists():
        for class_dir in subclass_dir.iterdir():
            if not class_dir.is_dir():
                continue
            for f in class_dir.glob("*.json"):
                try:
                    _walk_doc(json.loads(f.read_text()))
                except (json.JSONDecodeError, OSError):
                    pass

    supplements_dir = repo_root / "supplements"
    if supplements_dir.exists():
        for f in supplements_dir.glob("*.json"):
            try:
                supp_data = json.loads(f.read_text(encoding="utf-8"))
                for list_key in ("classes", "subclasses", "species", "backgrounds"):
                    for item in supp_data.get(list_key, []):
                        if isinstance(item, dict):
                            _walk_doc(item)
            except (json.JSONDecodeError, OSError):
                pass

    _AUTHORED_KEYS_CACHE = keys
    return keys


def collect_data_driven_choice_keys(character_data: Dict[str, Any]) -> Set[str]:
    """Enumerate valid catch-all choice keys for the active builder.

    Union of: (a) feature/choice names from data sources currently loaded on
    ``character_data`` (class_data, subclass_data, etc.); (b) the global
    authored-keys cache scanned from all of ``data/`` once.

    The ``apply_choice`` else-branch dispatches to ``_apply_choice_effects``
    which scans loaded data for a feature whose name matches the incoming
    key — e.g. ``"Divine Order"`` for Cleric, ``"Draconic Ancestry"`` for
    Dragonborn. Sparse fixtures (e.g. example_complete_character.json) carry
    those keys without loading the owning class/species, so the global cache
    is the safety net.
    """
    keys: Set[str] = set(_authored_choice_keys())

    def _add(name: Any) -> None:
        if isinstance(name, str) and name:
            keys.add(name)
            keys.add(_normalize(name))

    def _walk_features_by_level(fbl: Any) -> None:
        if not isinstance(fbl, dict):
            return
        for level_features in fbl.values():
            if not isinstance(level_features, dict):
                continue
            for feature_name, fd in level_features.items():
                _add(feature_name)
                if isinstance(fd, dict):
                    nested = fd.get("choices")
                    if isinstance(nested, list):
                        for ci in nested:
                            if isinstance(ci, dict):
                                _add(ci.get("name"))
                    elif isinstance(nested, dict):
                        _add(nested.get("name"))

    for src_key in (
        "class_data",
        "subclass_data",
        "species_data",
        "lineage_data",
        "background_data",
    ):
        data = character_data.get(src_key) or {}
        if not isinstance(data, dict):
            continue
        _walk_features_by_level(data.get("features_by_level"))
        traits = data.get("traits") or {}
        if isinstance(traits, dict):
            for trait_name, tdata in traits.items():
                _add(trait_name)
                if isinstance(tdata, dict):
                    nested = tdata.get("choices")
                    if isinstance(nested, list):
                        for ci in nested:
                            if isinstance(ci, dict):
                                _add(ci.get("name"))

    return keys


def check_choices_made_keys(
    choices: Dict[str, Any],
    character_data: Dict[str, Any],
) -> None:
    """Validate the top-level keys of a ``choices_made`` payload.

    Called once at the end of ``CharacterBuilder.apply_choices`` after all
    passes have run and class/subclass/species data is loaded. Anything that
    doesn't match the static allowlist, the dynamic regex, OR a feature name
    in currently-loaded data is flagged.
    """
    if not isinstance(choices, dict):
        return
    data_keys = collect_data_driven_choice_keys(character_data)
    unknown = []
    for key in choices:
        if not isinstance(key, str):
            unknown.append(repr(key))
            continue
        if key in KNOWN_CHOICE_KEYS:
            continue
        if is_dynamic_choice_key(key):
            continue
        if key in data_keys or _normalize(key) in data_keys:
            continue
        unknown.append(key)
    if unknown:
        _violate(
            "unknown top-level keys in choices_made: "
            + ", ".join(repr(k) for k in unknown)
            + ". Add the handler in CharacterBuilder.apply_choice, add the key "
            "to modules/strict_mode.KNOWN_CHOICE_KEYS, or extend the dynamic "
            "regex set if this is a per-feat/per-feature key."
        )


# ---------------------------------------------------------------------------
# Choice-value fallback resolution
# ---------------------------------------------------------------------------

def warn_choice_fallback(choice_name: str, matched_key: str) -> None:
    """Report a non-canonical fallback hit in ``_resolve_choice_value``.

    The canonical storage for species trait picks is the nested
    ``choices_made['species_trait_choices']`` object. Any hit on the legacy
    flat / prefixed key variants means the input payload predates Phase 4 and
    relies on the normalizer. Strict mode raises; lenient mode warns.
    """
    _violate(
        f"choice {choice_name!r} resolved only via non-canonical fallback key "
        f"{matched_key!r}; canonical location is "
        f"choices_made['species_trait_choices'][{choice_name!r}]. "
        "Frontend should write the nested form (Phase 4); see "
        ".github/instructions/choice-reference.instructions.md."
    )
