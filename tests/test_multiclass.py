"""Diagnostic tests for reported multiclass bugs (D&D 2024).

These tests encode the user-supplied expected values derived from the D&D 2024
rules and the Multiclass Spellcaster table. They exercise the
:class:`CharacterBuilder` directly via the ``classes`` payload (the same shape
the v1 REST API normalises into ``class_breakdown``).

They are intentionally written to be skeptical — some assertions are expected
to FAIL, and those failures are the diagnostic signal.

Three bug areas are covered:
    * HP: primary class L1 max die + average dice per other level (per class)
    * Proficiencies: secondary classes grant only multiclass-entry profs
    * Spell slots: Multiclass Spellcaster table with ceil(level/2) for half
      casters and floor(level/3) for third casters

Wiki source text (D&D 2024) for the proficiency checks:
    * Druid  ("As a Multiclass Druid"):
        "Gain the following traits from the Core Druid Traits table:
         Hit Point Die and training with Light armor and Shields."
    * Wizard ("As a Multiclass Character"):
        "Gain the Hit Point Die from the Core Wizard Traits table."
    * Cleric ("As a Multiclass Character"):
        "Gain the following traits from the Core Cleric Traits table:
         Hit Point Die and training with Light and Medium armor and Shields."
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from modules.character_builder import CharacterBuilder


# ---------------------------------------------------------------------------
# D&D 2024 Multiclass Spellcaster table (effective caster level → slot list)
# ---------------------------------------------------------------------------
MULTICLASS_SLOT_TABLE: Dict[int, List[int]] = {
    1:  [2, 0, 0, 0, 0, 0, 0, 0, 0],
    2:  [3, 0, 0, 0, 0, 0, 0, 0, 0],
    3:  [4, 2, 0, 0, 0, 0, 0, 0, 0],
    4:  [4, 3, 0, 0, 0, 0, 0, 0, 0],
    5:  [4, 3, 2, 0, 0, 0, 0, 0, 0],
    6:  [4, 3, 3, 0, 0, 0, 0, 0, 0],
    7:  [4, 3, 3, 1, 0, 0, 0, 0, 0],
    8:  [4, 3, 3, 2, 0, 0, 0, 0, 0],
    9:  [4, 3, 3, 3, 1, 0, 0, 0, 0],
    10: [4, 3, 3, 3, 2, 0, 0, 0, 0],
    11: [4, 3, 3, 3, 2, 1, 0, 0, 0],
    12: [4, 3, 3, 3, 2, 1, 0, 0, 0],
    13: [4, 3, 3, 3, 2, 1, 1, 0, 0],
    14: [4, 3, 3, 3, 2, 1, 1, 0, 0],
    15: [4, 3, 3, 3, 2, 1, 1, 1, 0],
    16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
    17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
    18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
    19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
    20: [4, 3, 3, 3, 3, 2, 2, 1, 1],
}

SLOT_KEYS = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build(
    classes: List[Dict[str, Any]],
    *,
    con: int = 14,
    species: str = "Human",
    background: str = "Acolyte",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a character from a multiclass `classes` payload.

    Uses fixed flat ability scores (all 10 except Con) so HP and slot
    computations are deterministic and not perturbed by ASIs.
    """
    choices: Dict[str, Any] = {
        "character_name": "Diag",
        "species": species,
        "background": background,
        "languages": ["Draconic"],
        "ability_scores": {
            "Strength": 10,
            "Dexterity": 10,
            "Constitution": con,
            "Intelligence": 10,
            "Wisdom": 10,
            "Charisma": 10,
        },
        # Background grants are 0 so Con stays exactly as supplied.
        "background_bonuses": {"Strength": 0, "Dexterity": 0, "Wisdom": 0},
        "classes": classes,
    }
    if extra:
        choices.update(extra)
    builder = CharacterBuilder()
    builder.apply_choices(choices)
    return builder.to_character()


def _slots_dict(eff_level: int) -> Dict[str, int]:
    table = MULTICLASS_SLOT_TABLE[eff_level]
    return {SLOT_KEYS[i]: table[i] for i in range(9) if table[i] > 0}


def _actual_slots(character: Dict[str, Any]) -> Dict[str, int]:
    return {k: v for k, v in (character.get("spell_slots") or {}).items() if v}


# ===========================================================================
# Bug 1 — Hit Points
# ===========================================================================
class TestMulticlassHP:
    """Primary class L1 = max die. All other levels = avg die OF THAT CLASS."""

    def test_fighter3_druid2_con14(self):
        """Fighter 3 / Druid 2, Con 14 → 12 + 16 + 14 = 42."""
        ch = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Druid", "level": 2},
            ],
            con=14,
        )
        actual = ch["combat"]["hit_points"]["maximum"]
        assert actual == 42, (
            f"Fighter 3 / Druid 2 Con 14: expected 42, got {actual}. "
            f"Breakdown source: 10+2 (F L1 max d10) + 2*(6+2) (F L2-3 avg d10) "
            f"+ 2*(5+2) (D L1-2 avg d8) = 42"
        )

    def test_cleric4_wizard2_con14(self):
        """Cleric 4 / Wizard 2, Con 14 → 10 + 21 + 12 = 43."""
        ch = _build(
            [
                {"class_name": "Cleric", "level": 4, "subclass": "Life Domain"},
                {"class_name": "Wizard", "level": 2},
            ],
            con=14,
        )
        actual = ch["combat"]["hit_points"]["maximum"]
        assert actual == 43, (
            f"Cleric 4 / Wizard 2 Con 14: expected 43, got {actual}. "
            f"8+2 (C L1 max d8) + 3*(5+2) (C L2-4 avg d8) "
            f"+ 2*(4+2) (W L1-2 avg d6) = 43"
        )

    def test_paladin5_sorcerer5_con14(self):
        """Paladin 5 / Sorcerer 5 (Draconic), Con 14 → 12 + 32 + 30 + 5 = 79.

        Breakdown:
            * Paladin L1 (primary, max d10): 10 + 2 = 12
            * Paladin L2-5 (avg d10): 4 * (6 + 2) = 32
            * Sorcerer L1-5 (avg d6): 5 * (4 + 2) = 30
            * Draconic Resilience (per-level, scoped to Sorcerer level): +5
        """
        ch = _build(
            [
                {"class_name": "Paladin", "level": 5, "subclass": "Oath of Devotion"},
                {"class_name": "Sorcerer", "level": 5, "subclass": "Draconic Sorcery"},
            ],
            con=14,
        )
        actual = ch["combat"]["hit_points"]["maximum"]
        # Pal level 1 max d10+Con + 4×(avg d10+Con) + 5×(avg d6+Con) + 5 (Draconic Resilience, scaled to Sorcerer level)
        assert actual == 79, (
            f"Paladin 5 / Sorcerer 5 (Draconic) Con 14: expected 79, got {actual}. "
            f"10+2 (P L1 max d10) + 4*(6+2) (P L2-5 avg d10) "
            f"+ 5*(4+2) (S L1-5 avg d6) + 5 (Draconic Resilience per Sorcerer level) = 79"
        )


# ===========================================================================
# Bug 2 — Multiclass-entry proficiencies (secondary class)
# ===========================================================================
class TestMulticlassProficiencies:
    """Secondary-class dips grant only the multiclass-entry profs per wiki."""

    # --- Druid dip ---------------------------------------------------------
    # Wiki: "Hit Point Die and training with Light armor and Shields."

    def test_fighter3_druid1_armor_no_heavy(self):
        ch = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Druid", "level": 1},
            ]
        )
        armor = ch["proficiencies"]["armor"]
        # Fighter already grants Heavy; multiclass dip into Druid shouldn't
        # CHANGE that. But many builders incorrectly *re-apply* the primary
        # Druid armor list which includes only Light + Shields (no Heavy),
        # or grant nothing harmful. The real bug surfaces in the other
        # direction: armor lists for the *Druid dip* should not pretend
        # Druid grants Heavy. Fighter still has Heavy from its own primary.
        assert "Heavy armor" in armor or "Heavy" in armor, (
            f"Fighter primary should still grant Heavy armor; got {armor}"
        )

    def test_fighter3_druid1_no_druid_weapon_profs_added(self):
        """Druid multiclass entry grants NO weapon profs.

        Fighter primary already has Simple+Martial, so the only way to
        detect a bug is to compare against Fighter-only. Any weapon prof
        present in F3/D1 that is NOT present in F3-only is a false grant.
        """
        f_only = _build([{"class_name": "Fighter", "level": 3, "subclass": "Champion"}])
        f_druid = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Druid", "level": 1},
            ]
        )
        extra = set(f_druid["proficiencies"]["weapons"]) - set(
            f_only["proficiencies"]["weapons"]
        )
        assert extra == set(), (
            f"Druid multiclass entry must not grant weapon profs. "
            f"Extra weapons granted by Druid 1 dip: {extra}"
        )

    def test_fighter3_druid1_no_druid_save_profs_added(self):
        """Druid multiclass entry grants NO saving-throw profs.

        Fighter primary has Str+Con. Any extra save (e.g. Wis or Int)
        appearing after a Druid 1 dip is a false grant.
        """
        f_only = _build([{"class_name": "Fighter", "level": 3, "subclass": "Champion"}])
        f_druid = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Druid", "level": 1},
            ]
        )
        extra = set(f_druid["proficiencies"]["saving_throws"]) - set(
            f_only["proficiencies"]["saving_throws"]
        )
        assert extra == set(), (
            f"Druid multiclass entry must not grant save profs. "
            f"Extra saves granted by Druid 1 dip: {extra}"
        )

    def test_fighter3_druid1_armor_only_light_and_shields_added(self):
        """The ONLY armor profs Druid 1 multiclass adds are Light and Shields."""
        f_only = _build([{"class_name": "Fighter", "level": 3, "subclass": "Champion"}])
        f_druid = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Druid", "level": 1},
            ]
        )
        extra = set(f_druid["proficiencies"]["armor"]) - set(
            f_only["proficiencies"]["armor"]
        )
        # Fighter primary already has Light, Medium, Heavy, Shields, so
        # extra should normally be empty. The assertion enforces no other
        # categories sneak in (e.g. "Medium armor" via wrong handler).
        assert extra <= {"Light armor", "Shields"}, (
            f"Druid multiclass should add at most Light + Shields. Extra: {extra}"
        )

    # --- Wizard dip --------------------------------------------------------
    # Wiki: "Gain the Hit Point Die from the Core Wizard Traits table."

    def test_fighter3_wizard1_no_armor_added(self):
        f_only = _build([{"class_name": "Fighter", "level": 3, "subclass": "Champion"}])
        f_wiz = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Wizard", "level": 1},
            ]
        )
        extra = set(f_wiz["proficiencies"]["armor"]) - set(f_only["proficiencies"]["armor"])
        assert extra == set(), (
            f"Wizard multiclass entry grants no armor profs. Extra: {extra}"
        )

    def test_fighter3_wizard1_no_weapons_added(self):
        f_only = _build([{"class_name": "Fighter", "level": 3, "subclass": "Champion"}])
        f_wiz = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Wizard", "level": 1},
            ]
        )
        extra = set(f_wiz["proficiencies"]["weapons"]) - set(
            f_only["proficiencies"]["weapons"]
        )
        assert extra == set(), (
            f"Wizard multiclass entry grants no weapon profs. Extra: {extra}"
        )

    def test_fighter3_wizard1_no_int_or_wis_save(self):
        f_only = _build([{"class_name": "Fighter", "level": 3, "subclass": "Champion"}])
        f_wiz = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Wizard", "level": 1},
            ]
        )
        extra = set(f_wiz["proficiencies"]["saving_throws"]) - set(
            f_only["proficiencies"]["saving_throws"]
        )
        assert "Intelligence" not in extra, (
            f"Wizard multiclass must not grant INT save prof. Extra saves: {extra}"
        )
        assert "Wisdom" not in extra, (
            f"Wizard multiclass must not grant WIS save prof. Extra saves: {extra}"
        )

    # --- Cleric dip --------------------------------------------------------
    # Wiki: "Hit Point Die and training with Light and Medium armor and Shields."

    def test_fighter3_cleric1_armor_only_light_medium_shields_added(self):
        f_only = _build([{"class_name": "Fighter", "level": 3, "subclass": "Champion"}])
        f_cleric = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Cleric", "level": 1, "subclass": "Life Domain"},
            ]
        )
        extra = set(f_cleric["proficiencies"]["armor"]) - set(
            f_only["proficiencies"]["armor"]
        )
        allowed = {"Light armor", "Medium armor", "Shields"}
        assert extra <= allowed, (
            f"Cleric multiclass should add at most {allowed}. Extra: {extra}"
        )

    def test_fighter3_cleric1_no_weapons_added(self):
        """Cleric multiclass entry grants NO weapon profs."""
        f_only = _build([{"class_name": "Fighter", "level": 3, "subclass": "Champion"}])
        f_cleric = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Cleric", "level": 1, "subclass": "Life Domain"},
            ]
        )
        extra = set(f_cleric["proficiencies"]["weapons"]) - set(
            f_only["proficiencies"]["weapons"]
        )
        assert extra == set(), (
            f"Cleric multiclass entry grants no weapon profs. Extra: {extra}"
        )

    def test_fighter3_cleric1_no_save_profs_added(self):
        """Cleric multiclass entry grants NO save profs (WIS/CHA from primary only)."""
        f_only = _build([{"class_name": "Fighter", "level": 3, "subclass": "Champion"}])
        f_cleric = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Cleric", "level": 1, "subclass": "Life Domain"},
            ]
        )
        extra = set(f_cleric["proficiencies"]["saving_throws"]) - set(
            f_only["proficiencies"]["saving_throws"]
        )
        assert extra == set(), (
            f"Cleric multiclass entry grants no save profs. Extra saves: {extra}"
        )


# ===========================================================================
# Bug 3 — Multiclass spell slots
# ===========================================================================
class TestMulticlassSpellSlots:
    def test_cleric3_wizard2_eff5(self):
        """Cleric 3 + Wizard 2 = full 3 + full 2 = eff 5 → 4/3/2."""
        ch = _build(
            [
                {"class_name": "Cleric", "level": 3, "subclass": "Life Domain"},
                {"class_name": "Wizard", "level": 2},
            ]
        )
        expected = _slots_dict(5)
        actual = _actual_slots(ch)
        assert actual == expected, (
            f"Cleric 3 / Wizard 2 (eff 5): expected {expected}, got {actual}"
        )

    def test_paladin4_wizard2_round_up_eff4(self):
        """Paladin 4 (ceil(4/2)=2) + Wizard 2 = eff 4 → 4/3."""
        ch = _build(
            [
                {"class_name": "Paladin", "level": 4, "subclass": "Oath of Devotion"},
                {"class_name": "Wizard", "level": 2},
            ]
        )
        expected = _slots_dict(4)
        actual = _actual_slots(ch)
        assert actual == expected, (
            f"Paladin 4 / Wizard 2 (eff ceil(4/2)+2=4): expected {expected}, got {actual}"
        )

    def test_paladin5_wizard2_round_up_eff5(self):
        """Paladin 5 (ceil(5/2)=3) + Wizard 2 = eff 5 → 4/3/2.

        This is the round-UP regression. If the builder uses floor(level/2),
        Paladin 5 would contribute 2 → eff 4 → 4/3, missing a 3rd-level slot.
        """
        ch = _build(
            [
                {"class_name": "Paladin", "level": 5, "subclass": "Oath of Devotion"},
                {"class_name": "Wizard", "level": 2},
            ]
        )
        expected = _slots_dict(5)
        actual = _actual_slots(ch)
        assert actual == expected, (
            f"Paladin 5 / Wizard 2 (eff ceil(5/2)+2=5): expected {expected}, got {actual}"
        )

    def test_fighter6_ek_wizard1_third_caster(self):
        """EK Fighter 6 (floor(6/3)=2) + Wizard 1 = eff 3 → 4/2."""
        ch = _build(
            [
                {"class_name": "Fighter", "level": 6, "subclass": "Eldritch Knight"},
                {"class_name": "Wizard", "level": 1},
            ]
        )
        expected = _slots_dict(3)
        actual = _actual_slots(ch)
        assert actual == expected, (
            f"EK Fighter 6 / Wizard 1 (eff floor(6/3)+1=3): "
            f"expected {expected}, got {actual}"
        )

    def test_warlock2_sorcerer3_pact_tracked_separately(self):
        """Warlock 2 / Sorcerer 3: standard eff 3 → 4/2; pact 2 slots of L1."""
        ch = _build(
            [
                {"class_name": "Sorcerer", "level": 3, "subclass": "Draconic Sorcery"},
                {"class_name": "Warlock", "level": 2, "subclass": "Fiend Patron"},
            ]
        )
        expected_standard = _slots_dict(3)  # {'1st': 4, '2nd': 2}
        actual_standard = _actual_slots(ch)
        assert actual_standard == expected_standard, (
            f"Sorcerer 3 / Warlock 2 standard slots (eff 3): "
            f"expected {expected_standard}, got {actual_standard}"
        )

        pact = ch.get("pact_magic_slots") or []
        assert pact, f"Expected pact_magic_slots list, got {pact!r}"
        # Find Warlock entry
        warlock_pact = next(
            (p for p in pact if p.get("class_name") == "Warlock"), None
        )
        assert warlock_pact is not None, (
            f"Expected Warlock pact entry; got {pact!r}"
        )
        assert warlock_pact.get("slots") == 2, (
            f"Warlock 2 pact slots: expected 2, got {warlock_pact.get('slots')!r}"
        )
        assert warlock_pact.get("slot_level") == 1, (
            f"Warlock 2 pact slot_level: expected 1, "
            f"got {warlock_pact.get('slot_level')!r}"
        )

    def test_warlock5_single_class_uses_pact_not_multiclass_table(self):
        """Warlock 5 alone must NOT use multiclass full-caster slots.

        Multiclass row 5 would give {1st:4, 2nd:3, 3rd:2}; warlock alone
        has Pact Magic = 2 slots of level 3 only. Assertion: the standard
        spell_slots dict must NOT equal the multiclass row.
        """
        ch = _build(
            [{"class_name": "Warlock", "level": 5, "subclass": "Fiend Patron"}]
        )
        bad = _slots_dict(5)  # {'1st': 4, '2nd': 3, '3rd': 2}
        actual = _actual_slots(ch)
        assert actual != bad, (
            f"Warlock 5 alone should not get multiclass full-caster slots, "
            f"but got exactly {actual} == multiclass row 5 ({bad})"
        )


# ===========================================================================
# Positive-direction proficiency grants (a dip DOES add what it should)
# ===========================================================================
class TestMulticlassProficienciesGranted:
    """Complement the delta-vs-Fighter tests: a dip into X must grant the
    proficiencies X's multiclass entry promises, and must NOT silently drop
    them. These caught the bug where a class's multiclass block was loaded
    but never applied additively to a primary class that lacked them.
    """

    def test_wizard3_druid1_grants_light_armor_and_shields(self):
        """Wizard 3 / Druid 1 must add Light armor + Shields.

        Control: Wizard alone has neither.
        """
        wiz_only = _build([{"class_name": "Wizard", "level": 3}])
        assert "Light armor" not in wiz_only["proficiencies"]["armor"], (
            f"Control failed: Wizard alone should not have Light armor. "
            f"Got {wiz_only['proficiencies']['armor']}"
        )
        assert "Shields" not in wiz_only["proficiencies"]["armor"], (
            f"Control failed: Wizard alone should not have Shields. "
            f"Got {wiz_only['proficiencies']['armor']}"
        )

        ch = _build(
            [
                {"class_name": "Wizard", "level": 3},
                {"class_name": "Druid", "level": 1},
            ]
        )
        armor = ch["proficiencies"]["armor"]
        assert "Light armor" in armor, (
            f"Druid 1 dip must grant Light armor. Got {armor}"
        )
        assert "Shields" in armor, (
            f"Druid 1 dip must grant Shields. Got {armor}"
        )

    def test_wizard3_cleric1_grants_light_medium_shields(self):
        """Wizard 3 / Cleric 1 must add Light, Medium armor + Shields."""
        ch = _build(
            [
                {"class_name": "Wizard", "level": 3},
                {"class_name": "Cleric", "level": 1, "subclass": "Life Domain"},
            ]
        )
        armor = ch["proficiencies"]["armor"]
        for required in ("Light armor", "Medium armor", "Shields"):
            assert required in armor, (
                f"Cleric 1 dip must grant {required}. Got {armor}"
            )

    def test_wizard3_fighter1_grants_martial_weapons(self):
        """Wizard 3 / Fighter 1 must add Martial weapons proficiency."""
        ch = _build(
            [
                {"class_name": "Wizard", "level": 3},
                {"class_name": "Fighter", "level": 1, "subclass": "Champion"},
            ]
        )
        weapons = ch["proficiencies"]["weapons"]
        assert "Martial weapons" in weapons, (
            f"Fighter 1 dip must grant Martial weapons. Got {weapons}"
        )

    def test_sorcerer3_wizard1_grants_nothing_extra(self):
        """Wizard multiclass entry grants Hit Point Die only.

        Sorcerer 3 / Wizard 1's armor list must equal Sorcerer 3 alone.
        """
        sorc_only = _build(
            [{"class_name": "Sorcerer", "level": 3, "subclass": "Draconic Sorcery"}]
        )
        ch = _build(
            [
                {"class_name": "Sorcerer", "level": 3, "subclass": "Draconic Sorcery"},
                {"class_name": "Wizard", "level": 1},
            ]
        )
        assert set(ch["proficiencies"]["armor"]) == set(
            sorc_only["proficiencies"]["armor"]
        ), (
            f"Wizard multiclass entry must grant no armor. "
            f"Sorcerer-only: {sorc_only['proficiencies']['armor']}, "
            f"Sor3/Wiz1: {ch['proficiencies']['armor']}"
        )

    def test_fighter3_rogue1_queues_skill_choice(self):
        """Rogue 1 dip with no choice provided must queue a pending choice."""
        ch = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Rogue", "level": 1, "subclass": "Thief"},
            ]
        )
        pending = ch.get("pending_multiclass_skill_choices") or []
        rogue_entry = next(
            (p for p in pending if p.get("class_name") == "Rogue"), None
        )
        assert rogue_entry is not None, (
            f"Expected a pending multiclass skill choice for Rogue; got {pending!r}"
        )
        assert rogue_entry.get("count") == 1, (
            f"Rogue multiclass skill count should be 1, got {rogue_entry.get('count')!r}"
        )
        options = rogue_entry.get("options")
        assert isinstance(options, list), (
            f"Rogue pending skill options should be a list, got {type(options).__name__}"
        )
        assert "Stealth" in options, (
            f"Rogue skill options should include Stealth. Got {options}"
        )

    def test_fighter3_rogue1_applies_chosen_skill(self):
        """Providing a multiclass skill pick must apply and clear the queue."""
        ch = _build(
            [
                {"class_name": "Fighter", "level": 3, "subclass": "Champion"},
                {"class_name": "Rogue", "level": 1, "subclass": "Thief"},
            ],
            extra={
                "multiclass_skill_choices": {"Rogue": ["Stealth"]},
            },
        )
        skills = ch["proficiencies"]["skills"]
        assert "Stealth" in skills, (
            f"Chosen multiclass skill 'Stealth' must be applied. Got {skills}"
        )
        pending = ch.get("pending_multiclass_skill_choices") or []
        rogue_entry = next(
            (p for p in pending if p.get("class_name") == "Rogue"), None
        )
        assert rogue_entry is None, (
            f"Rogue pending skill choice should be cleared once chosen; "
            f"still present: {rogue_entry!r}"
        )


# ===========================================================================
# Per-class bonus_hp scoping regression (Phase 6 fix)
# ===========================================================================
class TestPerClassBonusHpScoping:
    """A subclass's per-level bonus_hp (e.g. Draconic Resilience) must scale
    on that subclass's class level, NOT on total character level.
    """

    def test_draconic_resilience_scales_on_sorcerer_level_only(self):
        """Pal 5 / Sor 5 and Fighter 5 / Sor 5 (Draconic), Con 14 → 79.

        If the bonus scaled on total character level (10), HP would be 84;
        if it scaled on primary class level (5) instead of the source class,
        the answer would still be 79 in both cases by coincidence, so we
        assert both arrangements to lock in the rule.
        """
        pal_sor = _build(
            [
                {"class_name": "Paladin", "level": 5, "subclass": "Oath of Devotion"},
                {"class_name": "Sorcerer", "level": 5, "subclass": "Draconic Sorcery"},
            ],
            con=14,
        )
        assert pal_sor["combat"]["hit_points"]["maximum"] == 79, (
            f"Pal 5 / Sor 5 (Draconic) Con 14: expected 79, "
            f"got {pal_sor['combat']['hit_points']['maximum']}"
        )

        fig_sor = _build(
            [
                {"class_name": "Fighter", "level": 5, "subclass": "Champion"},
                {"class_name": "Sorcerer", "level": 5, "subclass": "Draconic Sorcery"},
            ],
            con=14,
        )
        # Fighter primary: L1 max d10 (10+2=12) + 4*(6+2)=32 + 5*(4+2)=30 + 5 DR = 79
        assert fig_sor["combat"]["hit_points"]["maximum"] == 79, (
            f"Fighter 5 / Sor 5 (Draconic) Con 14: expected 79, "
            f"got {fig_sor['combat']['hit_points']['maximum']}"
        )

    def test_single_class_draconic_sorcerer_still_gets_full_bonus(self):
        """Sorcerer 5 (Draconic) alone, Con 14 → 37.

        Breakdown: L1 max d6+Con = 8; L2-5 avg d6+Con = 4*(4+2)=24;
        Draconic Resilience per-level scaled to Sorcerer 5 = +5. Total 37.
        """
        ch = _build(
            [{"class_name": "Sorcerer", "level": 5, "subclass": "Draconic Sorcery"}],
            con=14,
        )
        actual = ch["combat"]["hit_points"]["maximum"]
        assert actual == 37, (
            f"Sorcerer 5 (Draconic) Con 14 alone: expected 37, got {actual}. "
            f"6+2 (S L1 max d6) + 4*(4+2) (S L2-5 avg d6) + 5 (DR) = 37"
        )


# ===========================================================================
# Single-class spell slot regression (non-multiclass path)
# ===========================================================================
class TestSingleClassSpellSlots:
    """Single-class characters must read slots from their own class table,
    not from the multiclass spellcaster table.
    """

    def test_single_class_wizard_uses_wizard_table_not_multiclass_table(self):
        """Wizard 5 alone → exactly Wizard's own spell_slots_by_level['5']."""
        ch = _build([{"class_name": "Wizard", "level": 5}])
        # Wizard 5: [4, 3, 2, 0, ...] → {'1st': 4, '2nd': 3, '3rd': 2}
        expected = {"1st": 4, "2nd": 3, "3rd": 2}
        actual = _actual_slots(ch)
        assert actual == expected, (
            f"Wizard 5 alone: expected {expected} from Wizard's own table, "
            f"got {actual}"
        )

    def test_single_class_paladin5_spell_slots(self):
        """Paladin 5 alone, Con 14 → Paladin's own table at level 5.

        Paladin 5 (half caster): [4, 2, 0, ...] → {'1st': 4, '2nd': 2}.
        The multiclass table eff-5 would give {'1st': 4, '2nd': 3, '3rd': 2};
        getting that would mean Paladin alone was routed through the
        multiclass path, which is the regression this test guards.
        """
        ch = _build(
            [{"class_name": "Paladin", "level": 5, "subclass": "Oath of Devotion"}],
            con=14,
        )
        expected = {"1st": 4, "2nd": 2}
        actual = _actual_slots(ch)
        assert actual == expected, (
            f"Paladin 5 alone: expected {expected} from Paladin's own table, "
            f"got {actual}"
        )
