#!/usr/bin/env python3
"""
Script to fetch D&D 2024 species wiki data and store it locally.
This creates a cache of species wiki data in the wiki_data/ folder that can be used
to generate species data files without repeatedly hitting the wiki.
"""

import argparse
import json
import requests
import time
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

# Base URLs
WIKI_BASE = "http://dnd2024.wikidot.com"

# All species to update
SPECIES = [
    "human",
    "elf",
    "dwarf",
    "halfling",
    "dragonborn",
    "gnome",
    "tiefling",
    "orc",
    "aasimar",
    "goliath",
]

# Wiki data directory
WIKI_DATA_DIR = Path("wiki_data")


def fetch_wiki_page(url):
    """Fetch a page from the wiki."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"  ❌ Error fetching {url}: {e}")
        return None


def extract_page_content(soup):
    """Extract the main content from a wiki page."""
    if not soup:
        return None

    # Find the main content div
    content_div = soup.find("div", {"id": "page-content"})
    if not content_div:
        return None

    # Extract text content while preserving structure
    content = {
        "text": content_div.get_text(separator="\n", strip=True),
        "html": str(content_div),
    }

    return content


def save_wiki_data(filepath, data):
    """Save wiki data to a JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fetch_species_data(species_name, overwrite=False):
    """Fetch and save species data from wiki."""
    filepath = WIKI_DATA_DIR / "species" / f"{species_name}.json"

    # Skip if file exists and overwrite is False
    if not overwrite and filepath.exists():
        print(f"Skipping species: {species_name} (already exists)")
        return True

    print(f"Fetching species: {species_name}...")
    url = f"{WIKI_BASE}/species:{species_name}"
    soup = fetch_wiki_page(url)

    if not soup:
        print(f"  ❌ Failed to fetch {species_name}")
        return False

    content = extract_page_content(soup)
    if not content:
        print(f"  ❌ Failed to extract content for {species_name}")
        return False

    # Create data structure
    wiki_data = {
        "species_name": species_name,
        "url": url,
        "fetched_at": datetime.now().isoformat(),
        "content": content,
    }

    # Save to file
    save_wiki_data(filepath, wiki_data)
    print(f"  ✅ Saved to {filepath}")
    return True


def main():
    """Main fetch function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Fetch D&D 2024 species wiki data and cache it locally.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch only missing data (default)
  python update_species.py
  
  # Overwrite all existing data
  python update_species.py --overwrite
  
  # Fetch only elf species and its variants
  python update_species.py --species elf
  
  # Overwrite elf data
  python update_species.py --species elf --overwrite
        """,
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing cached files (default: skip existing files)",
    )
    parser.add_argument(
        "--species",
        dest="species_filter",
        type=str,
        choices=SPECIES,
        help="Fetch only a specific species and its variants",
    )

    args = parser.parse_args()

    # Determine which species to fetch
    species_to_fetch = [args.species_filter] if args.species_filter else SPECIES

    print("=" * 70)
    print("D&D 2024 Species Wiki Data Fetcher")
    print("=" * 70)
    print(f"\nFetching data from: {WIKI_BASE}")
    print(f"Saving to: {WIKI_DATA_DIR.absolute()}")
    print(f"Mode: {'OVERWRITE all files' if args.overwrite else 'SKIP existing files'}")
    if args.species_filter:
        print(f"Filter: {args.species_filter} only")
    print("\nThis will create a local cache of species and variant wiki pages.")
    print("-" * 70)

    # Create wiki_data directory
    WIKI_DATA_DIR.mkdir(exist_ok=True)

    # Fetch species
    print("\n🧙 FETCHING SPECIES")
    print("-" * 70)
    species_success = 0
    species_failed = 0

    for species_name in species_to_fetch:
        result = fetch_species_data(species_name, overwrite=args.overwrite)
        if result:
            # Check if it was actually fetched or skipped
            filepath = WIKI_DATA_DIR / "species" / f"{species_name}.json"
            if filepath.exists():
                # Read to check if it was just created
                species_success += 1
        else:
            species_failed += 1
        time.sleep(1)  # Be nice to the server

    # Summary
    print("\n" + "=" * 70)
    print("📊 FETCH SUMMARY")
    print("=" * 70)
    if args.species_filter:
        print(f"Species filter: {args.species_filter}")
    print(f"Species: {species_success} processed, {species_failed} failed")
    print(f"\nData saved in: {WIKI_DATA_DIR.absolute()}")
    print("\n✅ Species wiki data fetch complete!")
    print("\nNext steps:")
    print("  1. Review the fetched data in wiki_data/")
    print("  2. Create a separate script to transform wiki_data → data/")


if __name__ == "__main__":
    main()
    print("Consider updating files incrementally with fetch_webpage tool.")
    print("=" * 60)

if __name__ == "__main__":
    main()
