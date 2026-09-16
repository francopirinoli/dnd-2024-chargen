#!/usr/bin/env python3
"""
Ability Scores Module
Handles ability score calculations, bonuses, and final score computation for D&D characters.
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# D&D 2024 Point Buy cost table: score → points spent
POINT_BUY_COSTS: Dict[int, int] = {
    8: 0,
    9: 1,
    10: 2,
    11: 3,
    12: 4,
    13: 5,
    14: 7,
    15: 9,
}

POINT_BUY_TOTAL = 27
POINT_BUY_MIN = 8
POINT_BUY_MAX = 15

ABILITIES = [
    "Strength",
    "Dexterity",
    "Constitution",
    "Intelligence",
    "Wisdom",
    "Charisma",
]


def validate_point_buy(scores: Dict[str, int]) -> Tuple[bool, str]:
    """Validate that a set of ability scores is legal under the Point Buy system.

    Returns (is_valid, error_message).  error_message is empty when valid.
    """
    for ability in ABILITIES:
        if ability not in scores:
            return False, f"Missing score for {ability}"
        score = scores[ability]
        if score not in POINT_BUY_COSTS:
            return (
                False,
                f"{ability} score {score} is outside the allowed range "
                f"({POINT_BUY_MIN}–{POINT_BUY_MAX})",
            )

    total_spent = sum(POINT_BUY_COSTS[scores[a]] for a in ABILITIES)
    if total_spent > POINT_BUY_TOTAL:
        return False, f"Point buy total {total_spent} exceeds the limit of {POINT_BUY_TOTAL}"

    return True, ""


@dataclass
class AbilityScores:
    """Manages all aspects of a character's ability scores"""

    # Core ability names
    ABILITIES = [
        "Strength",
        "Dexterity",
        "Constitution",
        "Intelligence",
        "Wisdom",
        "Charisma",
    ]

    def __init__(self):
        self.base_scores: Dict[str, int] = {ability: 10 for ability in self.ABILITIES}
        self.species_bonuses: Dict[str, int] = {
            ability: 0 for ability in self.ABILITIES
        }
        self.background_bonuses: Dict[str, int] = {
            ability: 0 for ability in self.ABILITIES
        }
        self.additional_modifiers: Dict[str, int] = {
            ability: 0 for ability in self.ABILITIES
        }
        self.final_scores: Dict[str, int] = {ability: 10 for ability in self.ABILITIES}

        # Legacy compatibility
        self.legacy_scores: Dict[str, int] = {ability: 0 for ability in self.ABILITIES}

    def set_base_scores(self, scores: Dict[str, int]):
        """Set the base ability scores"""
        for ability in self.ABILITIES:
            if ability in scores:
                self.base_scores[ability] = scores[ability]
        self._compute_final_scores()

    def apply_species_bonuses(self, bonuses: Dict[str, int]):
        """Apply species ability score bonuses"""
        for ability in self.ABILITIES:
            if ability in bonuses:
                self.species_bonuses[ability] = bonuses[ability]
        self._compute_final_scores()

    def apply_background_bonuses(self, bonuses: Dict[str, int]):
        """Apply background ability score bonuses"""
        for ability in self.ABILITIES:
            if ability in bonuses:
                self.background_bonuses[ability] = bonuses[ability]
        self._compute_final_scores()

    def apply_additional_modifiers(self, modifiers: Dict[str, int]):
        """Apply additional user ability score modifiers"""
        for ability in self.ABILITIES:
            if ability in modifiers:
                self.additional_modifiers[ability] = modifiers[ability]
        self._compute_final_scores()

    def _compute_final_scores(self):
        """Compute final ability scores from all sources"""
        for ability in self.ABILITIES:
            self.final_scores[ability] = (
                self.base_scores[ability]
                + self.species_bonuses[ability]
                + self.background_bonuses[ability]
                + self.additional_modifiers[ability]
            )

        # Update legacy field for compatibility
        self.legacy_scores = self.background_bonuses.copy()

    def get_modifier(self, ability: str) -> int:
        """Get the ability modifier for a given ability"""
        return (self.final_scores.get(ability, 10) - 10) // 2

    def get_all_modifiers(self) -> Dict[str, int]:
        """Get all ability modifiers"""
        return {ability: self.get_modifier(ability) for ability in self.ABILITIES}

    def assign_standard_array(self, class_recommendations: List[str]) -> Dict[str, int]:
        """Assign ability scores using standard array and class recommendations"""
        # D&D 2024 Standard Array
        standard_array = [15, 14, 13, 12, 10, 8]

        # Create assignment mapping
        assignment = {}
        used_scores = []

        # Assign recommended abilities first (highest scores)
        for i, rec_ability in enumerate(class_recommendations[: len(standard_array)]):
            if rec_ability in self.ABILITIES and standard_array:
                score = max(standard_array)
                assignment[rec_ability] = score
                standard_array.remove(score)
                used_scores.append(rec_ability)

        # Assign remaining abilities
        remaining_abilities = [a for a in self.ABILITIES if a not in used_scores]
        for ability in remaining_abilities:
            if standard_array:
                assignment[ability] = standard_array.pop(0)
            else:
                assignment[ability] = 10

        self.set_base_scores(assignment)
        return assignment

    def get_class_recommendations(self, class_name: str) -> List[str]:
        """Get recommended ability score priority for a class"""
        recommendations = {
            "Barbarian": [
                "Strength",
                "Constitution",
                "Dexterity",
                "Wisdom",
                "Charisma",
                "Intelligence",
            ],
            "Bard": [
                "Charisma",
                "Dexterity",
                "Constitution",
                "Wisdom",
                "Intelligence",
                "Strength",
            ],
            "Cleric": [
                "Wisdom",
                "Constitution",
                "Strength",
                "Charisma",
                "Dexterity",
                "Intelligence",
            ],
            "Druid": [
                "Wisdom",
                "Constitution",
                "Dexterity",
                "Intelligence",
                "Strength",
                "Charisma",
            ],
            "Fighter": [
                "Strength",
                "Constitution",
                "Dexterity",
                "Wisdom",
                "Charisma",
                "Intelligence",
            ],
            "Monk": [
                "Dexterity",
                "Wisdom",
                "Constitution",
                "Strength",
                "Intelligence",
                "Charisma",
            ],
            "Paladin": [
                "Strength",
                "Charisma",
                "Constitution",
                "Wisdom",
                "Dexterity",
                "Intelligence",
            ],
            "Ranger": [
                "Dexterity",
                "Wisdom",
                "Constitution",
                "Strength",
                "Intelligence",
                "Charisma",
            ],
            "Rogue": [
                "Dexterity",
                "Constitution",
                "Intelligence",
                "Wisdom",
                "Charisma",
                "Strength",
            ],
            "Sorcerer": [
                "Charisma",
                "Constitution",
                "Dexterity",
                "Wisdom",
                "Intelligence",
                "Strength",
            ],
            "Warlock": [
                "Charisma",
                "Constitution",
                "Dexterity",
                "Wisdom",
                "Intelligence",
                "Strength",
            ],
            "Wizard": [
                "Intelligence",
                "Constitution",
                "Dexterity",
                "Wisdom",
                "Charisma",
                "Strength",
            ],
        }

        return recommendations.get(class_name, self.ABILITIES.copy())

    def print_ability_breakdown(self, character_name: str = "Character"):
        """Print a detailed breakdown of ability scores"""
        print(f"\nFinal Ability Scores for {character_name}:")
        print(
            f"{'Ability':<12} {'Base':<4} {'Species':<7} {'Background':<10} {'Final':<5} {'Modifier':<8}"
        )
        print("-" * 55)

        for ability in self.ABILITIES:
            base = self.base_scores[ability]
            species = self.species_bonuses[ability]
            background = self.background_bonuses[ability]
            final = self.final_scores[ability]
            modifier = self.get_modifier(ability)
            mod_str = f"+{modifier}" if modifier >= 0 else str(modifier)

            print(
                f"{ability:<12} {base:<4} +{species:<6} +{background:<9} {final:<5} {mod_str:<8}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "base_ability_scores": self.base_scores.copy(),
            "species_ability_bonuses": self.species_bonuses.copy(),
            "background_ability_bonuses": self.background_bonuses.copy(),
            "additional_ability_modifiers": self.additional_modifiers.copy(),
            "final_ability_scores": self.final_scores.copy(),
            "ability_scores": self.legacy_scores.copy(),  # For compatibility
        }

    def from_dict(self, data: Dict[str, Any]):
        """Load from dictionary"""
        if "base_ability_scores" in data:
            self.base_scores.update(data["base_ability_scores"])
        if "species_ability_bonuses" in data:
            self.species_bonuses.update(data["species_ability_bonuses"])
        if "background_ability_bonuses" in data:
            self.background_bonuses.update(data["background_ability_bonuses"])
        if "additional_ability_modifiers" in data:
            self.additional_modifiers.update(data["additional_ability_modifiers"])
        if "final_ability_scores" in data:
            self.final_scores.update(data["final_ability_scores"])
        if "ability_scores" in data:
            self.legacy_scores.update(data["ability_scores"])
