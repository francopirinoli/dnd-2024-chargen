#!/usr/bin/env python3
"""
Supplement Validator CLI Tool

Validates a D&D 2024 supplement JSON package against models/supplement_schema.json
and constituent entity schemas.

Usage:
    python tools/validate_supplement.py path/to/supplement.json
"""

import json
import sys
from pathlib import Path

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from modules.supplement_manager import get_supplement_manager


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/validate_supplement.py <path_to_supplement.json>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error: Failed to parse JSON in {file_path}: {e}")
        sys.exit(1)

    mgr = get_supplement_manager()
    valid, errors = mgr.validate_package(data)

    manifest = data.get("manifest", {})
    title = manifest.get("title", "Untitled Supplement")
    pkg_id = manifest.get("id", "no-id")

    print("=" * 60)
    print(f"VALIDATING SUPPLEMENT: {title} ({pkg_id})")
    print(f"Source file: {file_path}")
    print("=" * 60)

    if valid:
        print("STATUS: VALID PACKAGE")
        print("\nIncluded Content:")
        print(f"  - Classes:           {len(data.get('classes', []))}")
        print(f"  - Subclasses:        {len(data.get('subclasses', []))}")
        print(f"  - Species:           {len(data.get('species', []))}")
        print(f"  - Species Variants:  {len(data.get('species_variants', []))}")
        print(f"  - Backgrounds:       {len(data.get('backgrounds', []))}")
        print(f"  - Spells:            {len(data.get('spells', []))}")
        feats = data.get("feats", {})
        print(f"  - Origin Feats:      {len(feats.get('origin_feats', {}))}")
        print(f"  - General Feats:     {len(feats.get('general_feats', {}))}")
        invocations = data.get("eldritch_invocations", {})
        if invocations:
            print(f"  - Invocations:       {len(invocations)}")
        print("=" * 60)
        sys.exit(0)
    else:
        print("STATUS: INVALID PACKAGE")
        print(f"\nFound {len(errors)} error(s):")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
