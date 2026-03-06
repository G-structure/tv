"""Experiment 1: Parse JW.org Tuvaluan sitemap and classify all URLs."""

import re
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path

# Add scripts dir to path for fetch module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch

SITEMAP_URL = "https://www.jw.org/tvl/sitemap.xml"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUTPUT_FILE = OUTPUT_DIR / "sitemap_tvl.json"
SITEMAP_CACHE = OUTPUT_DIR / "sitemap_tvl.xml"

# URL classifiers from tv2en.md section 10
CLASSIFIERS = [
    ("bible_chapter", re.compile(r"jw\.org/tvl/tusi/tusi-tapu/nwt/tusi/[^/]+/\d+/")),
    ("bible_book_toc", re.compile(r"jw\.org/tvl/tusi/tusi-tapu/nwt/tusi/[^/]+/?$")),
    ("bible_supplement", re.compile(r"jw\.org/tvl/tusi/tusi-tapu/nwt/mataupu-fakaopoopo")),
    ("bible_index", re.compile(r"jw\.org/tvl/tusi/tusi-tapu/")),
    ("magazine", re.compile(r"jw\.org/tvl/tusi/mekesini/")),
    ("book", re.compile(r"jw\.org/tvl/tusi/tusi/")),
    ("brochure", re.compile(r"jw\.org/tvl/tusi/polosiua/")),
    ("song", re.compile(r"jw\.org/tvl/tusi/pese-fakatagitagi")),
    ("video", re.compile(r"jw\.org/tvl/tusi/vitio")),
    ("meeting_workbook", re.compile(r"jw\.org/tvl/tusi/tusi-m\u014d-fakatasiga")),
    ("program", re.compile(r"jw\.org/tvl/tusi/polokalame/")),
    ("misc_publication", re.compile(r"jw\.org/tvl/tusi/kesekese/")),
    ("publication_index", re.compile(r"jw\.org/tvl/tusi/")),
    ("faq", re.compile(r"jw\.org/tvl/akoakoga-i-te-tusi-tapu/fesili/")),
    ("study_youth", re.compile(r"jw\.org/tvl/akoakoga-i-te-tusi-tapu/talavou/")),
    ("study_children", re.compile(r"jw\.org/tvl/akoakoga-i-te-tusi-tapu/tamaliki/")),
    ("study_science", re.compile(r"jw\.org/tvl/akoakoga-i-te-tusi-tapu/saienisi/")),
    ("study_family", re.compile(r"jw\.org/tvl/akoakoga-i-te-tusi-tapu/tauavaga-matua/")),
    ("study_hub", re.compile(r"jw\.org/tvl/akoakoga-i-te-tusi-tapu/")),
    ("news", re.compile(r"jw\.org/tvl/tala/")),
    ("about_jw", re.compile(r"jw\.org/tvl/molimau-a-ieova/")),
    ("help", re.compile(r"jw\.org/tvl/online-help/")),
    ("whats_new", re.compile(r"jw\.org/tvl/mea-fou/")),
    ("all_topics", re.compile(r"jw\.org/tvl/mataupu-fatoa-fakapa/")),
    ("search", re.compile(r"jw\.org/tvl/sala/")),
    ("home", re.compile(r"jw\.org/tvl/?$")),
]


def classify_url(url: str) -> str:
    for label, pattern in CLASSIFIERS:
        if pattern.search(url):
            return label
    return "other"


def parse_sitemap(xml_text: str) -> list[dict]:
    # Strip namespace for easier parsing
    xml_text = re.sub(r'\s+xmlns[^"]*"[^"]*"', "", xml_text, count=10)
    root = ET.fromstring(xml_text)

    entries = []
    for url_elem in root.findall(".//url"):
        loc = url_elem.findtext("loc", "")
        lastmod = url_elem.findtext("lastmod", "")
        # Check for hreflang alternates
        alternates = {}
        for link in url_elem.findall("link"):
            hreflang = link.get("hreflang", "")
            href = link.get("href", "")
            if hreflang and href:
                alternates[hreflang] = href

        if loc:
            entries.append({
                "url": loc,
                "lastmod": lastmod,
                "category": classify_url(loc),
                "alternates": alternates if alternates else None,
            })
    return entries


def main():
    # Use cached XML if available
    if SITEMAP_CACHE.exists() and SITEMAP_CACHE.stat().st_size > 0:
        print(f"Reading cached sitemap from {SITEMAP_CACHE}")
        xml_text = SITEMAP_CACHE.read_text()
    else:
        print(f"Fetching {SITEMAP_URL}...")
        xml_text = fetch(SITEMAP_URL)
        if xml_text is None:
            print("ERROR: Failed to fetch sitemap. Check Docker curl-impersonate.")
            sys.exit(1)
        # Save raw XML to disk for caching
        SITEMAP_CACHE.parent.mkdir(parents=True, exist_ok=True)
        SITEMAP_CACHE.write_text(xml_text)
        print(f"Saved raw XML to {SITEMAP_CACHE}")

    print(f"Got {len(xml_text)} bytes")

    entries = parse_sitemap(xml_text)
    print(f"Parsed {len(entries)} URLs")

    # Classify and count
    categories = {}
    for e in entries:
        cat = e["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print("\n--- Category breakdown ---")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Check for hreflang alternates
    has_alternates = sum(1 for e in entries if e["alternates"])
    print(f"\nURLs with hreflang alternates: {has_alternates}/{len(entries)}")

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump({
            "total": len(entries),
            "categories": categories,
            "has_alternates": has_alternates,
            "entries": entries,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
