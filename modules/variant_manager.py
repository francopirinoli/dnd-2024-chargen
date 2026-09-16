"""
Species Variant Manager for D&D 2024 Character Creator

Handles the complex variant system where species like Elves, Tieflings, and Dragonborn
have multiple sub-variants that provide different features and abilities at various levels.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class VariantManager:
    """Manages species variants and their level-based features"""

    def __init__(self, active_sources: Optional[List[str]] = None):
        self.active_sources = active_sources
        self.data_dir = Path(__file__).parent.parent / "data"
        self.variant_data = self._load_variant_data()
        self.species_variants = self._organize_variants_by_species()

    def _load_variant_data(self) -> Dict[str, Dict[str, Any]]:
        """Load all variant data from JSON files"""
        variant_dir = self.data_dir / "species_variants"
        variants = {}

        if variant_dir.exists():
            for json_file in variant_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        variant_data = json.load(f)
                        name = variant_data.get("name")
                        if name:
                            variants[name] = variant_data
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Could not load {json_file}: {e}")

        try:
            from .supplement_manager import get_supplement_manager
            sm = get_supplement_manager(data_dir=str(self.data_dir))
            supp_variants = sm.get_species_variants(self.active_sources)
            for name, vdata in supp_variants.items():
                if name not in variants:
                    variants[name] = vdata
        except Exception:
            pass

        return variants

    def _organize_variants_by_species(self) -> Dict[str, List[str]]:
        """Organize variants by their parent species"""
        by_species = {}

        for variant_name, variant_data in self.variant_data.items():
            parent_species = variant_data.get("parent_species")
            if parent_species:
                if parent_species not in by_species:
                    by_species[parent_species] = []
                by_species[parent_species].append(variant_name)

        return by_species

    def get_available_variants(self, species_name: str) -> List[str]:
        """Get list of available variants for a species"""
        return self.species_variants.get(species_name, [])

    def has_variants(self, species_name: str) -> bool:
        """Check if a species has variants available"""
        return species_name in self.species_variants

    def get_variant_data(self, variant_name: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific variant"""
        return self.variant_data.get(variant_name)

    def get_variant_features_at_level(self, variant_name: str, level: int) -> List[str]:
        """Get features gained by a variant at a specific level"""
        variant_data = self.get_variant_data(variant_name)
        if not variant_data:
            return []

        level_features = variant_data.get("level_features", {})
        features = []

        # Get features for this exact level
        if str(level) in level_features:
            features.extend(level_features[str(level)])

        return features

    def get_all_variant_features_up_to_level(
        self, variant_name: str, level: int
    ) -> Dict[int, List[str]]:
        """Get all features gained by a variant from level 1 to the specified level"""
        variant_data = self.get_variant_data(variant_name)
        if not variant_data:
            return {}

        level_features = variant_data.get("level_features", {})
        all_features = {}

        for feature_level in range(1, level + 1):
            if str(feature_level) in level_features:
                all_features[feature_level] = level_features[str(feature_level)]

        return all_features

    def get_variant_spells_at_level(self, variant_name: str, level: int) -> List[str]:
        """Get spells available to a variant at a specific level"""
        variant_data = self.get_variant_data(variant_name)
        if not variant_data:
            return []

        spells_by_level = variant_data.get("spells_by_level", {})
        available_spells = []

        # Add cantrips (always available)
        if "cantrip" in spells_by_level:
            available_spells.extend(spells_by_level["cantrip"])

        # Add level-based spells
        for spell_level in range(1, 10):  # D&D spell levels 1-9
            if str(spell_level) in spells_by_level and level >= spell_level:
                available_spells.extend(spells_by_level[str(spell_level)])

        return available_spells

    def apply_variant_to_character(self, character, variant_name: str) -> bool:
        """Apply variant features to a character"""
        variant_data = self.get_variant_data(variant_name)
        if not variant_data:
            return False

        # Add variant name to character
        character.species_variant = variant_name

        # Apply immediate traits
        traits = variant_data.get("traits", {})
        for trait_name, trait_description in traits.items():
            character.feature_manager.add_feature(
                trait_name, trait_description, "Species Variant"
            )

        # Apply weapon proficiencies
        weapon_profs = variant_data.get("weapon_proficiencies", [])
        if weapon_profs:
            character.weapon_proficiencies.extend(weapon_profs)

        # Apply armor proficiencies
        armor_profs = variant_data.get("armor_proficiencies", [])
        if armor_profs:
            character.armor_proficiencies.extend(armor_profs)

        # Apply tool proficiencies
        tool_profs = variant_data.get("tool_proficiencies", [])
        if tool_profs:
            character.tool_proficiencies.extend(tool_profs)

        # Apply speed bonus
        speed_bonus = variant_data.get("speed_bonus", 0)
        if speed_bonus:
            character.speed += speed_bonus

        # Apply HP bonus per level (like Dwarven Toughness)
        hp_bonus_per_level = variant_data.get("hp_bonus_per_level", 0)
        if hp_bonus_per_level:
            character.hp_calculator.add_bonus_per_level(
                "Species Variant", hp_bonus_per_level
            )

        # Apply darkvision range changes
        darkvision_range = variant_data.get("darkvision_range")
        if darkvision_range:
            character.darkvision_range = darkvision_range

        # Apply spells known
        spellcasting_ability = variant_data.get("spellcasting_ability")
        if spellcasting_ability:
            character.spellcasting_ability = spellcasting_ability

        cantrips_known = variant_data.get("cantrips_known", 0)
        if cantrips_known:
            character.cantrips_known += cantrips_known

        return True

    def display_variants_for_species(self, species_name: str) -> None:
        """Display available variants for a species with their features"""
        variants = self.get_available_variants(species_name)
        if not variants:
            print(f"No variants available for {species_name}")
            return

        print(f"\\nAvailable {species_name} Variants:")
        print("=" * 50)

        for i, variant_name in enumerate(variants, 1):
            variant_data = self.get_variant_data(variant_name)
            if variant_data:
                print(f"{i}. {variant_name}")

                # Show immediate traits
                traits = variant_data.get("traits", {})
                for trait_name, trait_desc in traits.items():
                    # Truncate long descriptions
                    desc = (
                        trait_desc[:80] + "..." if len(trait_desc) > 80 else trait_desc
                    )
                    print(f"   • {trait_name}: {desc}")

                # Show level-based features
                level_features = variant_data.get("level_features", {})
                if level_features:
                    print("   Level Features:")
                    for level, features in sorted(
                        level_features.items(), key=lambda x: int(x[0])
                    ):
                        print(f"     Level {level}: {', '.join(features)}")

                # Show spell progression
                spells_by_level = variant_data.get("spells_by_level", {})
                if spells_by_level:
                    print("   Spell Progression:")
                    for level, spells in sorted(spells_by_level.items()):
                        level_name = (
                            "Cantrips" if level == "cantrip" else f"Level {level}"
                        )
                        print(f"     {level_name}: {', '.join(spells)}")

                print()

    def get_variant_summary(self, variant_name: str) -> str:
        """Get a brief summary of a variant's key features"""
        variant_data = self.get_variant_data(variant_name)
        if not variant_data:
            return f"Unknown variant: {variant_name}"

        summary_parts = []

        # Count immediate traits
        traits_count = len(variant_data.get("traits", {}))
        if traits_count:
            summary_parts.append(f"{traits_count} traits")

        # Check for spell abilities
        if variant_data.get("spells_by_level"):
            summary_parts.append("spell abilities")

        # Check for proficiencies
        prof_types = []
        if variant_data.get("weapon_proficiencies"):
            prof_types.append("weapon")
        if variant_data.get("armor_proficiencies"):
            prof_types.append("armor")
        if variant_data.get("tool_proficiencies"):
            prof_types.append("tool")

        if prof_types:
            summary_parts.append(f"{'/'.join(prof_types)} proficiency")

        # Check for special bonuses
        if variant_data.get("speed_bonus"):
            summary_parts.append("speed bonus")
        if variant_data.get("hp_bonus_per_level"):
            summary_parts.append("HP bonus")
        if variant_data.get("darkvision_range"):
            summary_parts.append("enhanced darkvision")

        # Check for level-based features
        level_features = variant_data.get("level_features", {})
        if level_features:
            levels = sorted([int(level) for level in level_features.keys()])
            summary_parts.append(f"features at levels {', '.join(map(str, levels))}")

        if not summary_parts:
            return f"{variant_name} - Basic variant"

        return f"{variant_name} - {', '.join(summary_parts)}"
