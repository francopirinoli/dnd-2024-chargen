#!/usr/bin/env python3
"""
Script to fetch D&D 2024 wiki data and store it locally.
This creates a cache of wiki data in the wiki_data/ folder that can be used
to generate data files without repeatedly hitting the wiki.
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

# All classes to update
CLASSES = [
    "barbarian",
    "bard",
    "cleric",
    "druid",
    "fighter",
    "monk",
    "paladin",
    "ranger",
    "rogue",
    "sorcerer",
    "warlock",
    "wizard",
]

# Subclasses organized by class (based on existing files)
SUBCLASSES = {
    "barbarian": [
        "path-of-the-berserker",
        "path-of-the-wild-heart",
        "path-of-the-world-tree",
        "path-of-the-zealot",
    ],
    "bard": [
        "college-of-dance",
        "college-of-glamour",
        "college-of-lore",
        "college-of-valor",
    ],
    "cleric": ["life-domain", "light-domain", "trickery-domain", "war-domain"],
    "druid": [
        "circle-of-the-land",
        "circle-of-the-moon",
        "circle-of-the-sea",
        "circle-of-the-stars",
    ],
    "fighter": ["battle-master", "champion", "eldritch-knight", "psi-warrior"],
    "monk": [
        "warrior-of-mercy",
        "warrior-of-shadow",
        "warrior-of-the-elements",
        "warrior-of-the-open-hand",
    ],
    "paladin": [
        "oath-of-devotion",
        "oath-of-glory",
        "oath-of-the-ancients",
        "oath-of-vengeance",
    ],
    "ranger": ["beast-master", "fey-wanderer", "gloom-stalker", "hunter"],
    "rogue": ["arcane-trickster", "assassin", "soulknife", "thief"],
    "sorcerer": [
        "aberrant-sorcery",
        "clockwork-sorcery",
        "draconic-sorcery",
        "wild-magic-sorcery",
    ],
    "warlock": [
        "archfey-patron",
        "celestial-patron",
        "fiend-patron",
        "great-old-one-patron",
    ],
    "wizard": ["abjurer", "diviner", "evoker", "illusionist"],
}

# Class-specific extra pages to fetch (e.g. invocation/maneuver lists).
# Keys are class slugs; values are wiki page slugs (the path after the base URL).
CLASS_EXTRA_PAGES = {
    "warlock": ["warlock:eldritch-invocation"],
}

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


def fetch_class_data(class_name, overwrite=False):
    """Fetch and save class data from wiki."""
    filepath = WIKI_DATA_DIR / "classes" / f"{class_name}.json"

    # Skip if file exists and overwrite is False
    if not overwrite and filepath.exists():
        print(f"Skipping class: {class_name} (already exists)")
        return True

    print(f"Fetching class: {class_name}...")
    url = f"{WIKI_BASE}/{class_name}:main"
    soup = fetch_wiki_page(url)

    if not soup:
        print(f"  ❌ Failed to fetch {class_name}")
        return False

    content = extract_page_content(soup)
    if not content:
        print(f"  ❌ Failed to extract content for {class_name}")
        return False

    # Create data structure
    wiki_data = {
        "class_name": class_name,
        "url": url,
        "fetched_at": datetime.now().isoformat(),
        "content": content,
    }

    # Save to file
    save_wiki_data(filepath, wiki_data)
    print(f"  ✅ Saved to {filepath}")
    return True


def fetch_subclass_data(class_name, subclass_name, overwrite=False):
    """Fetch and save subclass data from wiki."""
    filepath = WIKI_DATA_DIR / "subclasses" / class_name / f"{subclass_name}.json"

    # Skip if file exists and overwrite is False
    if not overwrite and filepath.exists():
        print(f"Skipping subclass: {class_name}/{subclass_name} (already exists)")
        return True

    print(f"Fetching subclass: {class_name}/{subclass_name}...")
    url = f"{WIKI_BASE}/{class_name}:{subclass_name}"
    soup = fetch_wiki_page(url)

    if not soup:
        print(f"  ❌ Failed to fetch {class_name}:{subclass_name}")
        return False

    content = extract_page_content(soup)
    if not content:
        print(f"  ❌ Failed to extract content for {class_name}:{subclass_name}")
        return False

    # Create data structure
    wiki_data = {
        "class_name": class_name,
        "subclass_name": subclass_name,
        "url": url,
        "fetched_at": datetime.now().isoformat(),
        "content": content,
    }

    # Save to file
    save_wiki_data(filepath, wiki_data)
    print(f"  ✅ Saved to {filepath}")
    return True


def fetch_extra_page_data(class_name, page_slug, overwrite=False):
    """Fetch and save an extra class-related page (e.g. warlock invocations)."""
    # page_slug is the wiki path, e.g. "warlock:eldritch-invocation".
    # Strip the "<class>:" prefix to derive the on-disk filename.
    if ":" in page_slug:
        _, file_slug = page_slug.split(":", 1)
    else:
        file_slug = page_slug

    filepath = WIKI_DATA_DIR / "classes" / class_name / f"{file_slug}.json"

    if not overwrite and filepath.exists():
        print(f"Skipping extra page: {page_slug} (already exists)")
        return True

    print(f"  📜 Fetching extra page: {page_slug}")
    url = f"{WIKI_BASE}/{page_slug}"
    soup = fetch_wiki_page(url)

    if not soup:
        print(f"  ❌ Failed to fetch {page_slug}")
        return False

    content = extract_page_content(soup)
    if not content:
        print(f"  ❌ Failed to extract content for {page_slug}")
        return False

    wiki_data = {
        "class_name": class_name,
        "page_slug": page_slug,
        "url": url,
        "fetched_at": datetime.now().isoformat(),
        "content": content,
    }

    filepath.parent.mkdir(parents=True, exist_ok=True)
    save_wiki_data(filepath, wiki_data)
    print(f"  ✅ Saved to {filepath}")
    return True


def main():
    """Main fetch function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Fetch D&D 2024 wiki data and cache it locally.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch only missing data (default)
  python update_classes.py
  
  # Overwrite all existing data
  python update_classes.py --overwrite
  
  # Fetch only wizard class and its subclasses
  python update_classes.py --class wizard
  
  # Overwrite wizard data
  python update_classes.py --class wizard --overwrite
        """,
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing cached files (default: skip existing files)",
    )
    parser.add_argument(
        "--class",
        dest="class_filter",
        type=str,
        choices=CLASSES,
        help="Fetch only a specific class and its subclasses",
    )

    args = parser.parse_args()

    # Determine which classes to fetch
    classes_to_fetch = [args.class_filter] if args.class_filter else CLASSES

    print("=" * 70)
    print("D&D 2024 Wiki Data Fetcher")
    print("=" * 70)
    print(f"\nFetching data from: {WIKI_BASE}")
    print(f"Saving to: {WIKI_DATA_DIR.absolute()}")
    print(f"Mode: {'OVERWRITE all files' if args.overwrite else 'SKIP existing files'}")
    if args.class_filter:
        print(f"Filter: {args.class_filter} only")
    print("\nThis will create a local cache of class and subclass wiki pages.")
    print("-" * 70)

    # Create wiki_data directory
    WIKI_DATA_DIR.mkdir(exist_ok=True)

    # Fetch classes
    print("\n📚 FETCHING CLASSES")
    print("-" * 70)
    class_success = 0
    class_failed = 0

    for class_name in classes_to_fetch:
        result = fetch_class_data(class_name, overwrite=args.overwrite)
        if result:
            # Check if it was actually fetched or skipped
            filepath = WIKI_DATA_DIR / "classes" / f"{class_name}.json"
            if filepath.exists():
                # Read to check if it was just created
                class_success += 1
        else:
            class_failed += 1
        time.sleep(1)  # Be nice to the server

    # Fetch subclasses
    print("\n🎭 FETCHING SUBCLASSES")
    print("-" * 70)
    subclass_success = 0
    subclass_failed = 0

    for class_name in classes_to_fetch:
        if class_name in SUBCLASSES:
            for subclass in SUBCLASSES[class_name]:
                result = fetch_subclass_data(
                    class_name, subclass, overwrite=args.overwrite
                )
                if result:
                    subclass_success += 1
                else:
                    subclass_failed += 1
                time.sleep(1)  # Be nice to the server

    # Fetch class-specific extra pages (e.g. warlock invocations)
    print("\n📜 FETCHING EXTRA PAGES")
    print("-" * 70)
    extra_success = 0
    extra_failed = 0

    for class_name in classes_to_fetch:
        for page_slug in CLASS_EXTRA_PAGES.get(class_name, []):
            result = fetch_extra_page_data(
                class_name, page_slug, overwrite=args.overwrite
            )
            if result:
                extra_success += 1
            else:
                extra_failed += 1
            time.sleep(1)  # Be nice to the server

    # Summary
    print("\n" + "=" * 70)
    print("📊 FETCH SUMMARY")
    print("=" * 70)
    if args.class_filter:
        print(f"Class filter: {args.class_filter}")
    print(f"Classes: {class_success} processed, {class_failed} failed")
    print(f"Subclasses: {subclass_success} processed, {subclass_failed} failed")
    print(f"Extra pages: {extra_success} processed, {extra_failed} failed")
    print(f"Total: {class_success + subclass_success + extra_success} pages")
    print(f"\nData saved in: {WIKI_DATA_DIR.absolute()}")
    print("\n✅ Wiki data fetch complete!")
    print("\nNext steps:")
    print("  1. Review the fetched data in wiki_data/")
    print("  2. Create a separate script to transform wiki_data → data/")


if __name__ == "__main__":
    main()
    print("Consider updating files incrementally with fetch_webpage tool.")
    print("=" * 60)

if __name__ == "__main__":
    main()
