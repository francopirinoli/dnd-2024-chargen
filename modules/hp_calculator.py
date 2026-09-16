#!/usr/bin/env python3
"""
HP Calculator Module
Handles HP calculations including class hit dice, Constitution bonuses, and feature scaling.
"""

from typing import Dict, List, Any


class HPCalculator:
    """Manages hit point calculations for D&D characters"""

    # Class hit dice mapping
    CLASS_HIT_DICE = {
        "Barbarian": 12,
        "Fighter": 10,
        "Paladin": 10,
        "Ranger": 10,
        "Bard": 8,
        "Cleric": 8,
        "Druid": 8,
        "Monk": 8,
        "Rogue": 8,
        "Warlock": 8,
        "Artificer": 8,
        "Sorcerer": 6,
        "Wizard": 6,
    }

    def __init__(self):
        # Track per-level bonuses (like Dwarven Toughness)
        self.per_level_bonuses: List[Dict[str, Any]] = []

    def get_base_hp(self, class_name: str) -> int:
        """Get base HP for a class (max hit die at level 1)"""
        return self.CLASS_HIT_DICE.get(class_name, 6)

    def calculate_constitution_bonus(self, constitution_score: int, level: int) -> int:
        """Calculate HP bonus from Constitution modifier"""
        con_modifier = (constitution_score - 10) // 2
        return con_modifier * level

    def calculate_feature_bonuses(
        self, feature_bonuses: List[Dict[str, Any]], level: int
    ) -> int:
        """Calculate HP bonuses from features like Dwarven Toughness"""
        total_bonus = 0

        for hp_bonus in feature_bonuses:
            scaling = hp_bonus.get("scaling")
            value = hp_bonus.get("value", 0)

            if scaling == "per_level":
                total_bonus += value * level
            else:
                total_bonus += value

        return total_bonus

    def calculate_total_hp(
        self,
        class_name: str,
        constitution_score: int,
        feature_bonuses: List[Dict[str, Any]],
        level: int = 1,
    ) -> int:
        """Calculate total HP from all sources.

        Uses D&D 2024 standard calculation:
        - Level 1: Max hit die + Con modifier + feature bonuses
        - Level 2+: Average hit die per level + Con modifier per level + feature bonuses per level
        """
        hit_die = self.CLASS_HIT_DICE.get(class_name, 6)
        con_modifier = (constitution_score - 10) // 2

        # Level 1: Max hit die
        base_hp = hit_die

        # Additional levels: Average of hit die (rounded up)
        if level > 1:
            avg_hit_die = (hit_die // 2) + 1  # Average roll rounded up
            additional_hp = avg_hit_die * (level - 1)
            base_hp += additional_hp

        # Constitution bonus (per level)
        constitution_bonus = con_modifier * level

        # Feature bonuses
        feature_bonus = self.calculate_feature_bonuses(feature_bonuses, level)

        return base_hp + constitution_bonus + feature_bonus

    def get_hp_breakdown(
        self,
        class_name: str,
        constitution_score: int,
        feature_bonuses: List[Dict[str, Any]],
        level: int = 1,
    ) -> Dict[str, Any]:
        """Get detailed breakdown of HP calculation"""
        hit_die = self.CLASS_HIT_DICE.get(class_name, 6)
        con_modifier = (constitution_score - 10) // 2

        # Calculate base HP with level scaling
        base_hp = hit_die  # Level 1: max hit die
        if level > 1:
            avg_hit_die = (hit_die // 2) + 1
            additional_hp = avg_hit_die * (level - 1)
            base_hp += additional_hp

        constitution_bonus = con_modifier * level
        feature_bonus = self.calculate_feature_bonuses(feature_bonuses, level)
        total_hp = base_hp + constitution_bonus + feature_bonus

        # Break down feature bonuses
        feature_breakdown = []
        for hp_bonus in feature_bonuses:
            source = hp_bonus.get("source", "Unknown")
            value = hp_bonus.get("value", 0)
            scaling = hp_bonus.get("scaling")

            if scaling == "per_level":
                total_bonus = value * level
                feature_breakdown.append(
                    f"{source}: +{value} per level (+{total_bonus} total)"
                )
            else:
                feature_breakdown.append(f"{source}: +{value}")

        # Create detailed breakdown
        breakdown_text = f"Level 1: {hit_die} (max d{hit_die})"
        if level > 1:
            avg_hit_die = (hit_die // 2) + 1
            additional_hp = avg_hit_die * (level - 1)
            breakdown_text += f" + Levels 2-{level}: {additional_hp} (avg d{hit_die})"

        return {
            "base_hp": base_hp,
            "base_hp_breakdown": breakdown_text,
            "class_name": class_name,
            "hit_die": hit_die,
            "level": level,
            "constitution_score": constitution_score,
            "constitution_modifier": con_modifier,
            "constitution_bonus": constitution_bonus,
            "feature_bonus": feature_bonus,
            "feature_breakdown": feature_breakdown,
            "total_hp": total_hp,
        }

    def print_hp_breakdown(self, breakdown: Dict[str, Any]):
        """Print a detailed HP breakdown"""
        print(
            f"\nHP Breakdown for Level {breakdown['level']} {breakdown['class_name']}:"
        )
        print(
            f"  Base HP (d{self.CLASS_HIT_DICE.get(breakdown['class_name'], 6)}): {breakdown['base_hp']}"
        )
        print(
            f"  Constitution {breakdown['constitution_score']} ({breakdown['constitution_modifier']:+d}): +{breakdown['constitution_bonus']}"
        )

        if breakdown["feature_breakdown"]:
            print("  Features:")
            for feature in breakdown["feature_breakdown"]:
                print(f"    {feature}")

        print(f"  Total HP: {breakdown['total_hp']}")

    def simulate_level_progression(
        self,
        class_name: str,
        constitution_score: int,
        feature_bonuses: List[Dict[str, Any]],
        levels: List[int] = None,
    ) -> Dict[int, Dict[str, Any]]:
        """Simulate HP at different levels"""
        if levels is None:
            levels = [1, 3, 5, 10, 15, 20]

        progression = {}
        for level in levels:
            breakdown = self.get_hp_breakdown(
                class_name, constitution_score, feature_bonuses, level
            )
            progression[level] = breakdown

        return progression

    def print_level_progression(self, progression: Dict[int, Dict[str, Any]]):
        """Print HP progression across levels"""
        print("\nHP Progression by Level:")
        print("Level | Base | Con Bonus | Feature Bonus | Total HP")
        print("------|------|-----------|---------------|----------")

        for level, breakdown in sorted(progression.items()):
            print(
                f"  {level:2d}  |  {breakdown['base_hp']:2d}  |    +{breakdown['constitution_bonus']:2d}    |      +{breakdown['feature_bonus']:2d}      |   {breakdown['total_hp']:3d}"
            )

    def add_bonus_per_level(self, source: str, value: int) -> None:
        """Add a per-level HP bonus (like Dwarven Toughness)"""
        bonus = {"source": source, "value": value, "scaling": "per_level"}
        self.per_level_bonuses.append(bonus)

    def get_total_hp_with_bonuses(
        self, class_name: str, constitution_score: int, level: int
    ) -> int:
        """Calculate total HP including tracked per-level bonuses"""
        base_hp = self.get_base_hp(class_name)
        constitution_bonus = self.calculate_constitution_bonus(
            constitution_score, level
        )

        # Calculate bonuses from tracked per-level bonuses
        bonus_hp = 0
        for bonus in self.per_level_bonuses:
            if bonus.get("scaling") == "per_level":
                bonus_hp += bonus.get("value", 0) * level
            else:
                bonus_hp += bonus.get("value", 0)

        return base_hp + constitution_bonus + bonus_hp
