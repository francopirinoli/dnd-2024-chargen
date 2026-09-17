"""
Supplement Manager Module

Manages discovering, validating, loading, and merging modular 1st and 3rd party
game supplements for D&D 2024.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema
from jsonschema import Draft7Validator, RefResolver


def _normalize_name(name: str) -> str:
    """Normalize string for case-insensitive matching."""
    return name.strip().lower()


def _slugify(name: str) -> str:
    """Convert display name to canonical filename slug."""
    s = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[-\s]+", "_", s).strip("_")


class SupplementManager:
    """
    Manages modular rule supplements (Core 2024, Kobold Press, MCDM, Homebrew, etc.).
    """

    CORE_ID = "core-phb-2024"
    BUILTIN_SUPPLEMENT_IDS = {
        "core-phb-2024",
        "arcana-unleashed",
        "astarions-book-of-hungers",
        "eberron-forge-of-the-artificer",
        "forgotten-realms-heroes-of-faerun",
        "lorwyn-first-light",
        "ravenloft-the-horrors-within",
        "ua-2026-underdark-options",
        "ua-2026-villainous-options",
    }

    def __init__(self, data_dir: str = "data", supplements_dir: str = "supplements"):
        self.data_dir = Path(data_dir).resolve()
        self.supplements_dir = Path(supplements_dir).resolve()
        self.models_dir = self.data_dir.parent / "models"
        
        # Ensure supplements folder exists
        self.supplements_dir.mkdir(parents=True, exist_ok=True)

        # Loaded packages: supplement_id -> parsed package dict
        self.packages: Dict[str, Dict[str, Any]] = {}
        
        # Manifests: supplement_id -> manifest dict
        self.manifests: Dict[str, Dict[str, Any]] = {}

        # Load validator
        self._schema = self._load_schema()

        # Register core manifest
        self._register_core()

        # Load all installed supplements from disk
        self.reload_all()

    def _load_schema(self) -> Optional[Dict[str, Any]]:
        schema_path = self.models_dir / "supplement_schema.json"
        if schema_path.exists():
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load supplement_schema.json: {e}")
        return None

    def _register_core(self) -> None:
        """Register the built-in D&D 2024 ruleset as the baseline module."""
        manifest = {
            "id": self.CORE_ID,
            "title": "Player's Handbook (2024)",
            "publisher": "Wizards of the Coast",
            "version": "1.0.0",
            "compatibility": "2024",
            "description": "Official 2024 Player's Handbook core rules, classes, species, and backgrounds.",
            "is_core": True,
            "is_builtin": True,
            "is_user_uploaded": False,
            "enabled": True,
            "dependencies": [],
        }
        self.manifests[self.CORE_ID] = manifest

    def validate_package(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate a supplement package against the JSON Schema."""
        if not self._schema:
            return True, []

        base_uri = (self.models_dir / "supplement_schema.json").resolve().as_uri()
        resolver = RefResolver(base_uri=base_uri, referrer=self._schema)
        validator = Draft7Validator(self._schema, resolver=resolver)

        errors = []
        for err in validator.iter_errors(data):
            path = ".".join(str(p) for p in err.path)
            errors.append(f"[{path or 'root'}]: {err.message}")

        return len(errors) == 0, errors

    def reload_all(self) -> None:
        """Reload all supplement packages from the supplements directory."""
        self.packages.clear()
        
        # Scan JSON files in supplements/
        for json_file in sorted(self.supplements_dir.glob("*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    pkg = json.load(f)
                manifest = pkg.get("manifest", {})
                pkg_id = manifest.get("id")
                if pkg_id:
                    is_builtin = pkg_id in self.BUILTIN_SUPPLEMENT_IDS
                    manifest["is_core"] = False
                    manifest["is_builtin"] = is_builtin
                    manifest["is_user_uploaded"] = not is_builtin
                    manifest["enabled"] = True
                    manifest["file_path"] = str(json_file)
                    self.manifests[pkg_id] = manifest
                    self.packages[pkg_id] = pkg
            except Exception as e:
                print(f"Error loading supplement {json_file}: {e}")

        # Scan subdirectories with manifest.json
        for sub_dir in sorted(self.supplements_dir.iterdir()):
            if sub_dir.is_dir() and (sub_dir / "manifest.json").exists():
                try:
                    with open(sub_dir / "manifest.json", "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    pkg_id = manifest.get("id")
                    if pkg_id:
                        is_builtin = pkg_id in self.BUILTIN_SUPPLEMENT_IDS
                        manifest["is_core"] = False
                        manifest["is_builtin"] = is_builtin
                        manifest["is_user_uploaded"] = not is_builtin
                        manifest["enabled"] = True
                        manifest["dir_path"] = str(sub_dir)
                        self.manifests[pkg_id] = manifest
                        self.packages[pkg_id] = self._load_directory_supplement(sub_dir, manifest)
                except Exception as e:
                    print(f"Error loading supplement directory {sub_dir}: {e}")

    def _load_directory_supplement(self, dir_path: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Load an unpacked supplement folder."""
        pkg: Dict[str, Any] = {"manifest": manifest}

        # Subclasses
        subclasses_dir = dir_path / "subclasses"
        if subclasses_dir.exists():
            subclasses = []
            for sc_file in subclasses_dir.rglob("*.json"):
                try:
                    with open(sc_file, "r", encoding="utf-8") as f:
                        sc_data = json.load(f)
                        subclasses.append(sc_data)
                except Exception:
                    pass
            if subclasses:
                pkg["subclasses"] = subclasses

        # Species
        species_dir = dir_path / "species"
        if species_dir.exists():
            species = []
            for sp_file in species_dir.glob("*.json"):
                try:
                    with open(sp_file, "r", encoding="utf-8") as f:
                        species.append(json.load(f))
                except Exception:
                    pass
            if species:
                pkg["species"] = species

        # Spells
        spells_dir = dir_path / "spells"
        if spells_dir.exists():
            spells = []
            for sp_file in spells_dir.rglob("*.json"):
                try:
                    with open(sp_file, "r", encoding="utf-8") as f:
                        spells.append(json.load(f))
                except Exception:
                    pass
            if spells:
                pkg["spells"] = spells

        # Backgrounds
        bg_dir = dir_path / "backgrounds"
        if bg_dir.exists():
            bgs = []
            for bg_file in bg_dir.glob("*.json"):
                try:
                    with open(bg_file, "r", encoding="utf-8") as f:
                        bgs.append(json.load(f))
                except Exception:
                    pass
            if bgs:
                pkg["backgrounds"] = bgs

        return pkg

    def install_supplement(self, pkg: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Install a new supplement package."""
        valid, errors = self.validate_package(pkg)
        if not valid:
            return False, "Validation failed: " + "; ".join(errors[:5]), {}

        manifest = pkg.get("manifest", {})
        pkg_id = manifest.get("id")
        if not pkg_id:
            return False, "Package is missing manifest.id", {}

        if pkg_id == self.CORE_ID or pkg_id in self.BUILTIN_SUPPLEMENT_IDS:
            return False, f"Cannot overwrite built-in supplement ID: {pkg_id}", {}

        # Save to supplements/<pkg_id>.json
        target_path = self.supplements_dir / f"{pkg_id}.json"
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(pkg, f, indent=2, ensure_ascii=False)
            
            manifest["is_core"] = False
            manifest["is_builtin"] = False
            manifest["is_user_uploaded"] = True
            manifest["enabled"] = True
            manifest["file_path"] = str(target_path)
            self.manifests[pkg_id] = manifest
            self.packages[pkg_id] = pkg
            return True, f"Successfully installed '{manifest.get('title', pkg_id)}'", manifest
        except Exception as e:
            return False, f"Failed to save supplement: {e}", {}

    def uninstall_supplement(self, supplement_id: str) -> Tuple[bool, str]:
        """Uninstall/delete an installed supplement."""
        if supplement_id == self.CORE_ID or supplement_id in self.BUILTIN_SUPPLEMENT_IDS:
            return False, "Cannot uninstall built-in rulebooks or supplements included with the system."

        manifest = self.manifests.get(supplement_id)
        if not manifest:
            return False, f"Supplement not found: {supplement_id}"

        if manifest.get("is_builtin"):
            return False, "Cannot uninstall built-in rulebooks or supplements included with the system."

        file_path = manifest.get("file_path")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                return False, f"Could not delete file: {e}"

        self.manifests.pop(supplement_id, None)
        self.packages.pop(supplement_id, None)
        return True, f"Uninstalled {supplement_id}"

    def list_supplements(self) -> List[Dict[str, Any]]:
        """Return a list of all registered supplements with summary counts."""
        result = []
        for pkg_id, manifest in self.manifests.items():
            entry = dict(manifest)
            if pkg_id == self.CORE_ID:
                # Count files in core data directory
                entry["counts"] = {
                    "classes": len(list((self.data_dir / "classes").glob("*.json"))),
                    "subclasses": len(list((self.data_dir / "subclasses").rglob("*.json"))),
                    "species": len(list((self.data_dir / "species").glob("*.json"))),
                    "backgrounds": len(list((self.data_dir / "backgrounds").glob("*.json"))),
                    "spells": len(list((self.data_dir / "spells" / "definitions").glob("*.json"))),
                    "feats": len(self.get_feats(active_sources=[self.CORE_ID])),
                }
            else:
                pkg = self.packages.get(pkg_id, {})
                pkg_feats = pkg.get("feats", {})
                feats_count = len(pkg_feats.get("origin_feats", {})) + len(pkg_feats.get("general_feats", {}))
                entry["counts"] = {
                    "classes": len(pkg.get("classes", [])),
                    "subclasses": len(pkg.get("subclasses", [])),
                    "species": len(pkg.get("species", [])),
                    "backgrounds": len(pkg.get("backgrounds", [])),
                    "spells": len(pkg.get("spells", [])),
                    "feats": feats_count,
                }
            result.append(entry)
        return result

    def _is_active(self, source_id: str, active_sources: Optional[List[str]]) -> bool:
        """Check if a source is currently active."""
        if active_sources is None:
            return True
        if "all" in active_sources:
            return True
        return source_id in active_sources

    # ==================== Entity Querying ====================

    def get_classes(self, active_sources: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Get all classes from active sources."""
        classes: Dict[str, Dict[str, Any]] = {}

        # Core
        if self._is_active(self.CORE_ID, active_sources):
            classes_dir = self.data_dir / "classes"
            if classes_dir.exists():
                for f in sorted(classes_dir.glob("*.json")):
                    try:
                        with open(f, "r", encoding="utf-8") as jf:
                            data = json.load(jf)
                            name = data.get("name")
                            if name:
                                data["source_id"] = self.CORE_ID
                                data["source_title"] = self.manifests[self.CORE_ID]["title"]
                                classes[name] = data
                    except Exception:
                        pass

        # Supplements
        for pkg_id, pkg in self.packages.items():
            if self._is_active(pkg_id, active_sources):
                title = self.manifests.get(pkg_id, {}).get("title", pkg_id)
                for item in pkg.get("classes", []):
                    name = item.get("name")
                    if name:
                        copy_item = dict(item)
                        copy_item["source_id"] = pkg_id
                        copy_item["source_title"] = title
                        classes[name] = copy_item

        return classes

    def get_subclasses_for_class(
        self, class_name: str, active_sources: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get all subclasses for a given class from active sources."""
        subclasses: Dict[str, Dict[str, Any]] = {}
        c_name_norm = _normalize_name(class_name)
        if not c_name_norm:
            return {}

        # Core
        if self._is_active(self.CORE_ID, active_sources):
            sc_dir = self.data_dir / "subclasses" / c_name_norm
            try:
                if sc_dir.is_dir():
                    for f in sorted(sc_dir.glob("*.json")):
                        try:
                            with open(f, "r", encoding="utf-8") as jf:
                                data = json.load(jf)
                                name = data.get("name")
                                if name:
                                    data["source_id"] = self.CORE_ID
                                    data["source_title"] = self.manifests[self.CORE_ID]["title"]
                                    subclasses[name] = data
                        except Exception:
                            pass
            except OSError:
                pass

        # Supplements
        for pkg_id, pkg in self.packages.items():
            if self._is_active(pkg_id, active_sources):
                title = self.manifests.get(pkg_id, {}).get("title", pkg_id)
                for sc in pkg.get("subclasses", []):
                    if _normalize_name(sc.get("class", "")) == c_name_norm:
                        name = sc.get("name")
                        if name:
                            copy_sc = dict(sc)
                            copy_sc["source_id"] = pkg_id
                            copy_sc["source_title"] = title
                            subclasses[name] = copy_sc

        return subclasses

    def get_subclass(
        self, class_name: str, subclass_name: str, active_sources: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Find a specific subclass by name and class."""
        sc_map = self.get_subclasses_for_class(class_name, active_sources)
        sc_name_norm = _normalize_name(subclass_name)
        for name, data in sc_map.items():
            if _normalize_name(name) == sc_name_norm:
                return data
        return None

    def get_species(self, active_sources: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Get all species from active sources."""
        species: Dict[str, Dict[str, Any]] = {}

        # Core
        if self._is_active(self.CORE_ID, active_sources):
            species_dir = self.data_dir / "species"
            if species_dir.exists():
                for f in sorted(species_dir.glob("*.json")):
                    try:
                        with open(f, "r", encoding="utf-8") as jf:
                            data = json.load(jf)
                            name = data.get("name")
                            if name:
                                data["source_id"] = self.CORE_ID
                                data["source_title"] = self.manifests[self.CORE_ID]["title"]
                                species[name] = data
                    except Exception:
                        pass

        # Supplements
        for pkg_id, pkg in self.packages.items():
            if self._is_active(pkg_id, active_sources):
                title = self.manifests.get(pkg_id, {}).get("title", pkg_id)
                for sp in pkg.get("species", []):
                    name = sp.get("name")
                    if name:
                        copy_sp = dict(sp)
                        copy_sp["source_id"] = pkg_id
                        copy_sp["source_title"] = title
                        species[name] = copy_sp

        # Attach / merge supplement species_variants into parent species lineages
        for pkg_id, pkg in self.packages.items():
            if self._is_active(pkg_id, active_sources):
                for var in pkg.get("species_variants", []):
                    parent_species = var.get("parent_species")
                    var_name = var.get("name")
                    if not parent_species or not var_name:
                        continue
                    parent_key = next(
                        (k for k in species if _normalize_name(k) == _normalize_name(parent_species)),
                        None
                    )
                    if parent_key:
                        sp_entry = dict(species[parent_key])
                        existing_lineages = sp_entry.get("lineages")
                        if existing_lineages is None:
                            sp_entry["lineages"] = [var_name]
                        elif isinstance(existing_lineages, list):
                            if var_name not in existing_lineages:
                                sp_entry["lineages"] = list(existing_lineages) + [var_name]
                        elif isinstance(existing_lineages, dict):
                            if var_name not in existing_lineages:
                                sp_entry["lineages"] = dict(existing_lineages)
                                sp_entry["lineages"][var_name] = var
                        species[parent_key] = sp_entry

        return species

    def get_species_detail(
        self, species_name: str, active_sources: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get detailed species info."""
        all_sp = self.get_species(active_sources)
        sp_norm = _normalize_name(species_name)
        for name, data in all_sp.items():
            if _normalize_name(name) == sp_norm:
                return data
        return None

    def get_species_variants(
        self, active_sources: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get all species variants / lineages."""
        variants: Dict[str, Dict[str, Any]] = {}

        # Core
        if self._is_active(self.CORE_ID, active_sources):
            var_dir = self.data_dir / "species_variants"
            if var_dir.exists():
                for f in sorted(var_dir.glob("*.json")):
                    try:
                        with open(f, "r", encoding="utf-8") as jf:
                            data = json.load(jf)
                            name = data.get("name")
                            if name:
                                data["source_id"] = self.CORE_ID
                                variants[name] = data
                    except Exception:
                        pass

        # Supplements
        for pkg_id, pkg in self.packages.items():
            if self._is_active(pkg_id, active_sources):
                for var in pkg.get("species_variants", []):
                    name = var.get("name")
                    if name:
                        copy_var = dict(var)
                        copy_var["source_id"] = pkg_id
                        variants[name] = copy_var

        return variants

    def get_lineage(
        self, lineage_name: str, active_sources: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Find a lineage/variant by name."""
        all_vars = self.get_species_variants(active_sources)
        l_norm = _normalize_name(lineage_name)
        for name, data in all_vars.items():
            if _normalize_name(name) == l_norm:
                return data
        return None

    def get_backgrounds(
        self, active_sources: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get all backgrounds from active sources."""
        backgrounds: Dict[str, Dict[str, Any]] = {}

        # Core
        if self._is_active(self.CORE_ID, active_sources):
            bg_dir = self.data_dir / "backgrounds"
            if bg_dir.exists():
                for f in sorted(bg_dir.glob("*.json")):
                    try:
                        with open(f, "r", encoding="utf-8") as jf:
                            data = json.load(jf)
                            name = data.get("name")
                            if name:
                                data["source_id"] = self.CORE_ID
                                data["source_title"] = self.manifests[self.CORE_ID]["title"]
                                backgrounds[name] = data
                    except Exception:
                        pass

        # Supplements
        for pkg_id, pkg in self.packages.items():
            if self._is_active(pkg_id, active_sources):
                title = self.manifests.get(pkg_id, {}).get("title", pkg_id)
                for bg in pkg.get("backgrounds", []):
                    name = bg.get("name")
                    if name:
                        copy_bg = dict(bg)
                        copy_bg["source_id"] = pkg_id
                        copy_bg["source_title"] = title
                        backgrounds[name] = copy_bg

        return backgrounds

    def get_background(
        self, background_name: str, active_sources: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get background detail."""
        all_bg = self.get_backgrounds(active_sources)
        bg_norm = _normalize_name(background_name)
        for name, data in all_bg.items():
            if _normalize_name(name) == bg_norm:
                return data
        return None

    def get_feats(
        self, feat_type: Optional[str] = None, active_sources: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get feats (origin / general) from active sources."""
        feats: Dict[str, Dict[str, Any]] = {}

        # Core
        if self._is_active(self.CORE_ID, active_sources):
            if feat_type in (None, "origin"):
                origin_file = self.data_dir / "origin_feats.json"
                if origin_file.exists():
                    try:
                        with open(origin_file, "r", encoding="utf-8") as f:
                            for k, v in json.load(f).get("origin_feats", {}).items():
                                item = dict(v)
                                item["category"] = "origin"
                                item["source_id"] = self.CORE_ID
                                feats[k] = item
                    except Exception:
                        pass
            if feat_type in (None, "general"):
                general_file = self.data_dir / "general_feats.json"
                if general_file.exists():
                    try:
                        with open(general_file, "r", encoding="utf-8") as f:
                            for k, v in json.load(f).get("general_feats", {}).items():
                                item = dict(v)
                                item["category"] = "general"
                                item["source_id"] = self.CORE_ID
                                feats[k] = item
                    except Exception:
                        pass

        # Supplements
        for pkg_id, pkg in self.packages.items():
            if self._is_active(pkg_id, active_sources):
                pkg_feats = pkg.get("feats", {})
                if feat_type in (None, "origin", "Origin"):
                    for k, v in pkg_feats.get("origin_feats", {}).items():
                        item = dict(v)
                        item["category"] = v.get("category", "Origin")
                        item["source_id"] = pkg_id
                        feats[k] = item
                if feat_type in (None, "general", "General"):
                    for k, v in pkg_feats.get("general_feats", {}).items():
                        item = dict(v)
                        item["category"] = v.get("category", "General")
                        item["source_id"] = pkg_id
                        feats[k] = item

        return feats

    def get_eldritch_invocations(
        self, active_sources: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get eldritch invocations from active sources."""
        invocations: Dict[str, Dict[str, Any]] = {}

        # Core
        if self._is_active(self.CORE_ID, active_sources):
            core_file = self.data_dir / "eldritch_invocations.json"
            if core_file.exists():
                try:
                    with open(core_file, "r", encoding="utf-8") as f:
                        for k, v in json.load(f).items():
                            item = dict(v)
                            item["source_id"] = self.CORE_ID
                            invocations[k] = item
                except Exception:
                    pass

        # Supplements
        for pkg_id, pkg in self.packages.items():
            if self._is_active(pkg_id, active_sources):
                pkg_invocations = pkg.get("eldritch_invocations", {})
                for k, v in pkg_invocations.items():
                    item = dict(v)
                    item["source_id"] = pkg_id
                    invocations[k] = item

        return invocations

    def get_spell_definition(
        self, spell_name: str, active_sources: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a single spell definition by name."""
        spell_norm = _normalize_name(spell_name)
        safe_slug = re.sub(r"[^a-z0-9_]", "_", spell_norm.replace(" ", "_"))

        # Core
        if self._is_active(self.CORE_ID, active_sources):
            core_path = self.data_dir / "spells" / "definitions" / f"{safe_slug}.json"
            if core_path.exists():
                try:
                    with open(core_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["source_id"] = self.CORE_ID
                        return data
                except Exception:
                    pass

        # Supplements
        for pkg_id, pkg in self.packages.items():
            if self._is_active(pkg_id, active_sources):
                for spell in pkg.get("spells", []):
                    if _normalize_name(spell.get("name", "")) == spell_norm:
                        copy_spell = dict(spell)
                        copy_spell["source_id"] = pkg_id
                        return copy_spell

        return None

    def get_class_spells(
        self, class_name: str, active_sources: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the merged spell list for a class from active sources."""
        c_lower = class_name.lower()
        result: Dict[str, Any] = {"class": class_name, "cantrips": [], "spells_by_level": {}}

        # Core
        if self._is_active(self.CORE_ID, active_sources):
            core_list = self.data_dir / "spells" / "class_lists" / f"{c_lower}.json"
            if core_list.exists():
                try:
                    with open(core_list, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "class" in data:
                            result["class"] = data["class"]
                        result["cantrips"].extend(data.get("cantrips", []))
                        for lvl, spells in data.get("spells_by_level", {}).items():
                            result["spells_by_level"].setdefault(lvl, []).extend(spells)
                except Exception:
                    pass

        # Supplements
        for pkg_id, pkg in self.packages.items():
            if self._is_active(pkg_id, active_sources):
                lists = pkg.get("spell_class_lists", {}).get(c_lower, {})
                result["cantrips"].extend(lists.get("cantrips", []))
                for lvl, spells in lists.get("spells_by_level", {}).items():
                    result["spells_by_level"].setdefault(lvl, []).extend(spells)

        # Deduplicate
        result["cantrips"] = sorted(list(set(result["cantrips"])))
        for lvl in result["spells_by_level"]:
            result["spells_by_level"][lvl] = sorted(list(set(result["spells_by_level"][lvl])))

        return result


# Global singleton instance
_supplement_manager: Optional[SupplementManager] = None


def get_supplement_manager(data_dir: str = "data", supplements_dir: str = "supplements") -> SupplementManager:
    global _supplement_manager
    if _supplement_manager is None:
        _supplement_manager = SupplementManager(data_dir=data_dir, supplements_dir=supplements_dir)
    return _supplement_manager
