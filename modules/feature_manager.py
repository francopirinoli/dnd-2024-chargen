#!/usr/bin/env python3
"""
Feature Manager Module
Handles feature tracking, parsing, and application for D&D characters.
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class FeatureManager:
    """Manages character features and their effects"""

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = data_dir
        self.trait_patterns = self._load_trait_patterns()

        # Feature registry for tracking active features
        self.feature_registry: Dict[str, Dict[str, Any]] = {}

        # Feature bonus categories
        self.bonus_categories = {
            "hit_points": [],
            "armor_class": [],
            "speed": [],
            "saving_throws": [],
            "skills": [],
            "damage_resistance": [],
            "damage_immunity": [],
            "condition_immunity": [],
        }

    def _load_trait_patterns(self) -> Dict[str, Any]:
        """Load trait parsing patterns from JSON"""
        patterns_file = self.data_dir / "trait_patterns.json"
        if patterns_file.exists():
            with open(patterns_file, "r") as f:
                return json.load(f)
        return {"patterns": [], "fallback_patterns": []}

    def parse_trait_features(
        self, trait_name: str, trait_data: Any, source: str
    ) -> List[Dict[str, Any]]:
        """Parse trait data to extract structured features using JSON patterns"""
        features = []

        if isinstance(trait_data, str):
            features.extend(self._parse_string_trait(trait_name, trait_data, source))
        elif isinstance(trait_data, dict):
            features.extend(self._parse_dict_trait(trait_name, trait_data, source))

        return features

    def _parse_string_trait(
        self, trait_name: str, description: str, source: str
    ) -> List[Dict[str, Any]]:
        """Parse string-based trait descriptions"""
        features = []
        description_lower = description.lower()
        trait_name_lower = trait_name.lower()

        # Check each pattern
        for pattern_data in self.trait_patterns["patterns"]:
            if self._matches_pattern(trait_name_lower, description_lower, pattern_data):
                feature = self._create_feature_from_pattern(
                    trait_name, description, source, pattern_data
                )
                features.append(feature)
                # Stop at first match to avoid duplicates
                break

        # If no pattern matched, use fallback
        if not features:
            for fallback_pattern in self.trait_patterns["fallback_patterns"]:
                feature = self._create_feature_from_pattern(
                    trait_name, description, source, fallback_pattern
                )
                features.append(feature)
                break

        return features

    def _parse_dict_trait(
        self, trait_name: str, trait_data: dict, source: str
    ) -> List[Dict[str, Any]]:
        """Parse dictionary-based trait data"""
        if trait_data.get("effect_type"):
            # Already structured feature
            feature = {"name": trait_name, "source": source, **trait_data}
            return [feature]
        else:
            # Generic feature for unstructured dictionary
            return [
                {
                    "name": trait_name,
                    "source": source,
                    "effect_type": "special",
                    "description": str(trait_data),
                }
            ]

    def _matches_pattern(
        self, trait_name: str, description: str, pattern_data: dict
    ) -> bool:
        """Check if a trait matches a specific pattern"""
        pattern_type = pattern_data["pattern_type"]
        pattern = pattern_data["pattern"]

        if pattern_type == "exact_name":
            return pattern in trait_name

        elif pattern_type == "text_contains":
            if isinstance(pattern, str):
                return pattern in description
            elif isinstance(pattern, list):
                requires_all = pattern_data.get("requires_all", False)
                matches = [p in description for p in pattern]
                return all(matches) if requires_all else any(matches)

        return False

    def _create_feature_from_pattern(
        self, trait_name: str, description: str, source: str, pattern_data: dict
    ) -> Dict[str, Any]:
        """Create a feature dictionary from a matched pattern"""
        feature_template = pattern_data["feature"]

        feature = {
            "name": trait_name,
            "source": source,
            "effect_type": feature_template["effect_type"],
            "value": feature_template["value"],
            "scaling": feature_template.get("scaling"),
            "description": feature_template.get("description_override") or description,
        }

        # Remove None values
        feature = {k: v for k, v in feature.items() if v is not None}

        return feature

    def apply_feature(
        self, feature: Dict[str, Any], feature_bonuses: Dict[str, List[Dict[str, Any]]]
    ):
        """Apply a feature to the character's bonus tracking"""
        effect_type = feature.get("effect_type")
        if effect_type and effect_type in feature_bonuses:
            feature_bonuses[effect_type].append(
                {
                    "source": f"{feature.get('source', 'Unknown')}: {feature.get('name', 'Unknown')}",
                    "value": feature.get("value", 0),
                    "condition": feature.get("condition", "always"),
                    "scaling": feature.get("scaling", None),
                }
            )

    def get_feature_summary(
        self, active_features: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Get a summary of all active features organized by source"""
        summary = {
            "Species Features": [],
            "Class Features": [],
            "Background Features": [],
            "Feat Features": [],
        }

        for feature in active_features:
            source = feature.get("source", "Unknown")
            if "Species" in source:
                source_type = "Species Features"
            elif "Class" in source:
                source_type = "Class Features"
            elif "Background" in source:
                source_type = "Background Features"
            else:
                source_type = "Feat Features"

            # Create description based on effect type
            effect_type = feature.get("effect_type", "special")
            if effect_type == "hit_points":
                scaling = feature.get("scaling")
                if scaling == "per_level":
                    description = f"+{feature.get('value', 0)} HP per level"
                else:
                    description = f"+{feature.get('value', 0)} HP"
            elif effect_type == "damage_resistance":
                description = f"Resistance to {feature.get('value', 'unknown')}"
            elif effect_type == "vision":
                description = f"{feature.get('value', 'Special vision')}"
            elif effect_type == "saving_throws":
                value = feature.get("value", "unknown")
                description = f"Advantage on {value} saves"
            elif effect_type == "condition_immunity":
                description = feature.get("description", "Condition resistance")
            else:
                description = feature.get("description", "Special ability")

            feature_text = f"{feature.get('name', 'Unknown Feature')}: {description}"
            summary[source_type].append(feature_text)

        return summary

    def create_empty_feature_bonuses(self) -> Dict[str, List[Dict[str, Any]]]:
        """Create an empty feature bonuses dictionary"""
        return {category: [] for category in self.bonus_categories.keys()}

    def add_feature(self, feature_name: str, description: str, source: str) -> None:
        """Add a feature to the registry"""
        self.feature_registry[feature_name] = {
            "name": feature_name,
            "description": description,
            "source": source,
        }

    def get_features_by_source(self, source: str) -> Dict[str, Dict[str, Any]]:
        """Get all features from a specific source"""
        return {
            name: data
            for name, data in self.feature_registry.items()
            if data.get("source") == source
        }

    def remove_feature(self, feature_name: str) -> bool:
        """Remove a feature from the registry"""
        if feature_name in self.feature_registry:
            del self.feature_registry[feature_name]
            return True
        return False
