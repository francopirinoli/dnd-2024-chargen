#!/usr/bin/env python3
"""
Script to fetch D&D 2024 spell lists from the wiki and generate
spell list JSON files for the character creator.

Usage:
    python update_spells.py --class sorcerer          # Fetch one class
    python update_spells.py --all                      # Fetch all spellcasting classes
    python update_spells.py --class wizard --overwrite  # Overwrite existing files

Generates:
    data/spells/class_lists/{class}.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests

WIKI_BASE = "http://dnd2024.wikidot.com"

# Classes that have spell lists on the wiki
SPELLCASTING_CLASSES = [
    "bard",
    "cleric",
    "druid",
    "paladin",
    "ranger",
    "sorcerer",
    "warlock",
    "wizard",
]

SPELLS_DIR = Path("data/spells")
CLASS_LISTS_DIR = SPELLS_DIR / "class_lists"

LEVEL_NAMES = ["cantrip", "1", "2", "3", "4", "5", "6", "7", "8", "9"]


def fetch_spell_list_html(class_name):
    """Fetch the raw HTML for a class's spell list page."""
    url = f"{WIKI_BASE}/{class_name}:spell-list"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"  ❌ Error fetching {url}: {e}")
        return None


def parse_spell_tabs(html):
    """
    Parse the wikidot tabview HTML to extract spells by level.

    The wiki uses JavaScript tabs (yui-content divs) with all content
    present in the raw HTML inside <div id="wiki-tab-0-{n}"> sections.
    Spell links follow the pattern: <a href="/spell:{slug}">Spell Name</a>

    Tab labels are read dynamically from the navigation, since not all
    classes have cantrips (e.g. Paladin, Ranger start at 1st Level).
    """
    result = {}

    # Extract tab labels from the yui-nav list
    nav_match = re.search(r'<ul class="yui-nav">(.*?)</ul>', html, re.DOTALL)
    if not nav_match:
        print("  ❌ Could not find tab navigation in HTML")
        return None

    tab_labels = re.findall(r'<em>([^<]+)</em>', nav_match.group(1))
    if not tab_labels:
        print("  ❌ Could not parse tab labels")
        return None

    # Map label text to our level keys
    label_to_level = {"Cantrip": "cantrip"}
    for i in range(1, 10):
        suffixes = {1: "st", 2: "nd", 3: "rd"}
        suffix = suffixes.get(i, "th")
        label_to_level[f"{i}{suffix} Level"] = str(i)

    # Split on the yui-content container
    parts = html.split('<div class="yui-content">')
    if len(parts) < 2:
        print("  ❌ Could not find tabview content in HTML")
        return None

    main_content = parts[1]

    # Split by individual tab divs
    tab_divs = main_content.split('<div id="wiki-tab-')

    for i, tab in enumerate(tab_divs[1:]):  # skip first empty segment
        if i >= len(tab_labels):
            break

        label = tab_labels[i]
        level = label_to_level.get(label)
        if level is None:
            continue  # skip unknown tabs

        spells = re.findall(r'<a href="/spell:[^"]*">([^<]+)</a>', tab)
        result[level] = sorted(spells)

    return result


def write_cantrips_file(class_name, cantrips, overwrite=False):
    """Write the {class}_cantrips.json file."""
    filepath = SPELLS_DIR / f"{class_name}_cantrips.json"
    if filepath.exists() and not overwrite:
        print(f"  Skipping {filepath.name} (exists, use --overwrite)")
        return False

    data = {"cantrips": cantrips}
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"  ✅ Wrote {filepath.name} ({len(cantrips)} cantrips)")
    return True


def write_spells_file(class_name, spells_by_level, overwrite=False):
    """Write the {class}_spells.json file."""
    filepath = SPELLS_DIR / f"{class_name}_spells.json"
    if filepath.exists() and not overwrite:
        print(f"  Skipping {filepath.name} (exists, use --overwrite)")
        return False

    data = {}
    level_labels = {
        "1": "1st_level", "2": "2nd_level", "3": "3rd_level",
        "4": "4th_level", "5": "5th_level", "6": "6th_level",
        "7": "7th_level", "8": "8th_level", "9": "9th_level",
    }
    for level_key, label in level_labels.items():
        if level_key in spells_by_level and spells_by_level[level_key]:
            data[label] = spells_by_level[level_key]

    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    total = sum(len(v) for v in data.values())
    print(f"  ✅ Wrote {filepath.name} ({total} spells across {len(data)} levels)")
    return True


def write_class_list_file(class_name, cantrips, spells_by_level, overwrite=False):
    """Write the class_lists/{class}.json file."""
    CLASS_LISTS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = CLASS_LISTS_DIR / f"{class_name}.json"
    if filepath.exists() and not overwrite:
        print(f"  Skipping {filepath.name} (exists, use --overwrite)")
        return False

    data = {
        "class": class_name.capitalize(),
        "cantrips": cantrips,
        "spells_by_level": {},
    }
    for level_key in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
        if level_key in spells_by_level and spells_by_level[level_key]:
            data["spells_by_level"][level_key] = spells_by_level[level_key]

    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"  ✅ Wrote {filepath.name}")
    return True


def update_class_spells(class_name, overwrite=False):
    """Fetch and write all spell list files for a class."""
    print(f"\nFetching spell list for {class_name}...")

    html = fetch_spell_list_html(class_name)
    if not html:
        return False

    spells = parse_spell_tabs(html)
    if not spells:
        return False

    cantrips = spells.get("cantrip", [])
    leveled = {k: v for k, v in spells.items() if k != "cantrip"}

    print(f"  Found {len(cantrips)} cantrips, "
          f"{sum(len(v) for v in leveled.values())} leveled spells")

    if cantrips:
        write_class_list_file(class_name, cantrips, leveled, overwrite)
    else:
        write_class_list_file(class_name, [], leveled, overwrite)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Fetch D&D 2024 spell lists from the wiki"
    )
    parser.add_argument(
        "--class", dest="class_name",
        help="Class name to fetch (e.g. sorcerer)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Fetch spell lists for all spellcasting classes",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite existing files",
    )

    args = parser.parse_args()

    if not args.class_name and not args.all:
        parser.print_help()
        sys.exit(1)

    classes = SPELLCASTING_CLASSES if args.all else [args.class_name.lower()]

    for cls in classes:
        if cls not in SPELLCASTING_CLASSES:
            print(f"⚠️  {cls} is not a known spellcasting class, trying anyway...")
        update_class_spells(cls, overwrite=args.overwrite)

    print("\nDone!")


if __name__ == "__main__":
    main()
