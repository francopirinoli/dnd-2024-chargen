"""
Data Loader Module

Handles loading all game data from JSON files in the data/ directory.
This module provides a clean interface for accessing D&D 2024 game data.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List


def _validate_features_by_level(
    fbl: Any, source_label: str
) -> None:
    """Validate the ``features_by_level`` shape once at load time.

    Canonical shape (audit, .github/instructions/data-schemas.instructions.md):

        {
          "<level_str>": {
            "<feature_name>": "<description>" | { ...feature_object... }
          }
        }

    Anything else (arrays, non-dict level entries, non-string level keys)
    is a real data defect — raise immediately with a path-qualified message
    instead of letting runtime warnings drown the signal.

    Phase 5 (audit P2-6) replaces the defensive runtime checks scattered
    through ``character_builder.py`` with this single load-time gate.
    """
    if fbl is None:
        return
    if not isinstance(fbl, dict):
        raise ValueError(
            f"{source_label}: features_by_level must be an object, got "
            f"{type(fbl).__name__}"
        )
    for level_key, level_features in fbl.items():
        if not isinstance(level_key, str):
            raise ValueError(
                f"{source_label}: features_by_level level keys must be strings, "
                f"got {type(level_key).__name__}: {level_key!r}"
            )
        if not isinstance(level_features, dict):
            raise ValueError(
                f"{source_label}: features_by_level[{level_key!r}] must be an "
                f"object mapping feature_name -> description, got "
                f"{type(level_features).__name__}. "
                f"NEVER use arrays here — see "
                f".github/instructions/data-schemas.instructions.md."
            )


class DataLoader:
    """
    Loads and provides access to D&D 2024 game data from JSON files.

    Attributes:
        data_dir: Path to the data directory
        classes: Dictionary of class data keyed by class name
        backgrounds: Dictionary of background data keyed by background name
        species: Dictionary of species data keyed by species name
        species_variants: Dictionary of species variant data
        feats: Dictionary of feat data keyed by feat name (loaded from origin_feats.json and general_feats.json)
        subclasses: Dictionary of subclass data organized by class name
    """

    def __init__(self, data_dir: str = "data"):
        """
        Initialize the data loader.

        Args:
            data_dir: Path to the directory containing game data JSON files
        """
        self.data_dir = Path(data_dir)
        self.classes = self._load_data("classes")
        self.backgrounds = self._load_data("backgrounds")
        self.species = self._load_data("species")
        self.species_variants = self._load_data("species_variants")
        self.feats = self._load_feats()
        self.subclasses = self._load_subclasses()
        from .supplement_manager import get_supplement_manager
        self.supplement_manager = get_supplement_manager(data_dir=str(self.data_dir))

    def _load_data(self, data_type: str) -> Dict[str, Dict[str, Any]]:
        """
        Load JSON data files from a directory.

        Args:
            data_type: Name of the subdirectory to load from (e.g., 'classes', 'species')

        Returns:
            Dictionary of loaded data keyed by the 'name' field in each JSON file
        """
        data_dir = self.data_dir / data_type
        data = {}

        if data_dir.exists():
            for json_file in data_dir.glob("*.json"):
                try:
                    with open(json_file, "r") as f:
                        file_data = json.load(f)
                        name = file_data.get("name")
                        if name:
                            _validate_features_by_level(
                                file_data.get("features_by_level"),
                                f"{json_file}",
                            )
                            data[name] = file_data
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Could not load {json_file}: {e}")

        return data

    def _load_feats(self) -> Dict[str, Dict[str, Any]]:
        """
        Load feat data from grouped feat files (origin_feats.json, general_feats.json).

        Returns:
            Dictionary of all feats keyed by feat name
        """
        feats = {}
        
        # Load origin feats
        origin_feats_file = self.data_dir / "origin_feats.json"
        if origin_feats_file.exists():
            try:
                with open(origin_feats_file, "r") as f:
                    origin_data = json.load(f)
                    if "origin_feats" in origin_data:
                        feats.update(origin_data["origin_feats"])
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load {origin_feats_file}: {e}")
        
        # Load general feats
        general_feats_file = self.data_dir / "general_feats.json"
        if general_feats_file.exists():
            try:
                with open(general_feats_file, "r") as f:
                    general_data = json.load(f)
                    if "general_feats" in general_data:
                        feats.update(general_data["general_feats"])
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load {general_feats_file}: {e}")
        
        return feats

    def _load_subclasses(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Load subclass data organized by class name.

        Returns:
            Dictionary with structure: {class_name: {subclass_name: subclass_data}}
        """
        subclass_dir = self.data_dir / "subclasses"
        subclasses = {}

        if subclass_dir.exists():
            # Each subdirectory represents a class
            for class_dir in subclass_dir.iterdir():
                if class_dir.is_dir():
                    class_name = class_dir.name.title()
                    subclasses[class_name] = {}

                    # Load all subclass files in this class directory
                    for json_file in class_dir.glob("*.json"):
                        try:
                            with open(json_file, "r") as f:
                                subclass_data = json.load(f)
                                subclass_name = subclass_data.get("name")
                                if subclass_name:
                                    _validate_features_by_level(
                                        subclass_data.get("features_by_level"),
                                        f"{json_file}",
                                    )
                                    subclasses[class_name][subclass_name] = (
                                        subclass_data
                                    )
                        except (json.JSONDecodeError, IOError) as e:
                            print(f"Warning: Could not load {json_file}: {e}")

        return subclasses

    def get_subclasses_for_class(
        self, class_name: str, active_sources: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get available subclasses for a class from active sources."""
        return self.supplement_manager.get_subclasses_for_class(class_name, active_sources)

    def get_classes(self, active_sources: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Get available classes from active sources."""
        return self.supplement_manager.get_classes(active_sources)

    def get_species(self, active_sources: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Get available species from active sources."""
        return self.supplement_manager.get_species(active_sources)

    def get_backgrounds(self, active_sources: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Get available backgrounds from active sources."""
        return self.supplement_manager.get_backgrounds(active_sources)

    def get_feats(
        self, feat_type: Optional[str] = None, active_sources: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get available feats from active sources."""
        return self.supplement_manager.get_feats(feat_type, active_sources)

    def get_spell_definition(
        self, spell_name: str, active_sources: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get spell definition from active sources."""
        return self.supplement_manager.get_spell_definition(spell_name, active_sources)

    def get_class_spells(
        self, class_name: str, active_sources: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get class spell list from active sources."""
        return self.supplement_manager.get_class_spells(class_name, active_sources)

    def get_eldritch_invocations(
        self, active_sources: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get eldritch invocations from active sources."""
        return self.supplement_manager.get_eldritch_invocations(active_sources)
