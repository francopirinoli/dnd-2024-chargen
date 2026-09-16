#!/usr/bin/env python3
"""Validate D&D 2024 data files against their schemas.

A category manifest below maps every JSON file under data/ to the schema in
models/ that describes it. The script:

  1. Validates each data file against its schema, printing each failure
     with the file path and the verbatim jsonschema error.
  2. Errors out at startup if any JSON file under data/ is not covered by
     the manifest (and is not explicitly excluded as a non-entity file).
     This keeps future contributors from adding a new category without a
     schema.

Run from the repo root:  python validate_data.py
"""

import fnmatch
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import jsonschema  # noqa: F401  (kept for explicit dependency error)
    from jsonschema import Draft7Validator, RefResolver
except ImportError:
    print("❌ jsonschema not installed. Install with: pip install jsonschema")
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parent


# Each entry: human-readable category name, glob (relative to repo root),
# and schema file (relative to repo root). Globs use fnmatch semantics
# where '*' does not cross '/' (so 'data/subclasses/*/*.json' is two
# components after data/subclasses/).
CATEGORIES = [
    {"name": "classes",              "glob": "data/classes/*.json",                  "schema": "models/class_schema.json"},
    {"name": "subclasses",           "glob": "data/subclasses/*/*.json",             "schema": "models/subclass_schema.json"},
    {"name": "species",              "glob": "data/species/*.json",                  "schema": "models/species_schema.json"},
    {"name": "species_variants",     "glob": "data/species_variants/*.json",         "schema": "models/species_variant_schema.json"},
    {"name": "backgrounds",          "glob": "data/backgrounds/*.json",              "schema": "models/background_schema.json"},
    {"name": "origin_feats",         "glob": "data/origin_feats.json",               "schema": "models/feat_schema.json"},
    {"name": "general_feats",        "glob": "data/general_feats.json",              "schema": "models/feat_schema.json"},
    {"name": "spell_definitions",    "glob": "data/spells/definitions/*.json",       "schema": "models/spell_schema.json"},
    {"name": "spell_class_lists",    "glob": "data/spells/class_lists/*.json",       "schema": "models/spell_class_list_schema.json"},
    {"name": "weapons",              "glob": "data/equipment/weapons.json",          "schema": "models/weapon_schema.json"},
    {"name": "armor",                "glob": "data/equipment/armor.json",            "schema": "models/armor_schema.json"},
    {"name": "weapon_masteries",     "glob": "data/equipment/weapon_masteries.json", "schema": "models/weapon_mastery_schema.json"},
    {"name": "adventuring_gear",     "glob": "data/equipment/adventuring_gear.json", "schema": "models/adventuring_gear_schema.json"},
    {"name": "fighting_styles",      "glob": "data/fighting_styles.json",            "schema": "models/fighting_style_schema.json"},
    {"name": "maneuvers",            "glob": "data/maneuvers.json",                  "schema": "models/maneuver_schema.json"},
    {"name": "arcane_shots",         "glob": "data/arcane_shots.json",               "schema": "models/arcane_shot_schema.json"},
    {"name": "eldritch_invocations", "glob": "data/eldritch_invocations.json",       "schema": "models/eldritch_invocation_schema.json"},
    {"name": "languages",            "glob": "data/languages.json",                  "schema": "models/languages_schema.json"},
    {"name": "trait_patterns",       "glob": "data/trait_patterns.json",             "schema": "models/trait_patterns_schema.json"},
]


# Files under data/ that are intentionally NOT entity data and therefore
# don't get a schema. Keep this list short and justified.
EXCLUDED_FILES = {
    # JSON-schema document describing the v1 character sheet model
    # (lives in data/ for historical reasons, not entity content).
    "data/character_sheet_model.json",
    # Reference fixture: example of CharacterBuilder.to_character() output.
    "data/example_complete_character.json",
    # Machine-readable completeness tracker, not entity content.
    "data/completeness/backlog.json",
}


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _matches(rel_path: str, glob: str) -> bool:
    return fnmatch.fnmatchcase(rel_path, glob)


def _collect_all_data_files():
    data_root = REPO_ROOT / "data"
    return [p.relative_to(REPO_ROOT).as_posix() for p in sorted(data_root.rglob("*.json"))]


def _validate_one(data_file: Path, schema_path: Path):
    try:
        data = load_json(data_file)
        schema = load_json(schema_path)
    except Exception as e:
        return False, f"failed to load: {e}"

    # Resolve $ref relative to the schema file so refs like
    # "_shared/effect.json" find models/_shared/effect.json.
    base_uri = schema_path.resolve().as_uri()
    resolver = RefResolver(base_uri=base_uri, referrer=schema)
    validator = Draft7Validator(schema, resolver=resolver)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if not errors:
        return True, None
    msgs = []
    for e in errors:
        loc = "/".join(str(p) for p in e.absolute_path) or "<root>"
        msgs.append(f"at {loc}: {e.message}")
    return False, "\n     ".join(msgs)


def _check_coverage(all_files):
    """Return data files not covered by any category entry and not excluded."""
    uncovered = []
    for rel in all_files:
        if rel in EXCLUDED_FILES:
            continue
        if not any(_matches(rel, c["glob"]) for c in CATEGORIES):
            uncovered.append(rel)
    return uncovered


def main() -> int:
    print("D&D 2024 Data Validator")
    print("Validating data files against schemas in models/")
    print()

    missing_schemas = [c for c in CATEGORIES if not (REPO_ROOT / c["schema"]).exists()]
    if missing_schemas:
        print("❌ Schema files missing for these categories:")
        for c in missing_schemas:
            print(f"   - {c['name']}: {c['schema']}")
        return 2

    all_files = _collect_all_data_files()

    uncovered = _check_coverage(all_files)
    if uncovered:
        print("❌ Uncovered data files (no matching schema in CATEGORIES manifest):")
        for u in uncovered:
            print(f"   - {u}")
        print()
        print("Every JSON file under data/ must either:")
        print("  (a) match a glob in validate_data.CATEGORIES with a schema, or")
        print("  (b) be listed in validate_data.EXCLUDED_FILES with a justification.")
        return 2

    all_valid = True
    summary = []
    for cat in CATEGORIES:
        files = [REPO_ROOT / rel for rel in all_files if _matches(rel, cat["glob"])]
        if not files:
            print(f"⚠️  {cat['name']}: no files matched glob {cat['glob']}")
            summary.append((cat["name"], 0, 0))
            continue
        schema_path = REPO_ROOT / cat["schema"]
        print("=" * 70)
        print(f"VALIDATING {cat['name'].upper()}  ({len(files)} file(s), schema: {cat['schema']})")
        print("=" * 70)
        failed = 0
        for f in files:
            ok, err = _validate_one(f, schema_path)
            rel = f.relative_to(REPO_ROOT).as_posix()
            if ok:
                print(f"✅ {rel}")
            else:
                print(f"❌ {rel}")
                print(f"     {err}")
                failed += 1
                all_valid = False
        summary.append((cat["name"], len(files), failed))
        print()

    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    total = 0
    total_failed = 0
    for name, count, failed in summary:
        total += count
        total_failed += failed
        mark = "✅" if failed == 0 else "❌"
        print(f"  {mark} {name:30s} {count - failed}/{count} valid")
    print(f"\n  Total: {total - total_failed}/{total} files valid")

    if all_valid:
        print("\n✅ All data files are valid!")
        return 0
    print("\n❌ Some data files failed validation")
    print("\nTo fix validation errors:")
    print("  1. Review the schema in models/ for the failing category")
    print("  2. Update the data file to match the schema (do NOT loosen the schema unless authorized)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
