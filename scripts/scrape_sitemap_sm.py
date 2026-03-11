"""Parse JW.org Samoan sitemap and classify all URLs."""

import re
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path

# Add scripts dir to path for fetch module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch

SITEMAP_URL = "https://www.jw.org/sm/sitemap.xml"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUTPUT_FILE = OUTPUT_DIR / "sitemap_sm.json"
SITEMAP_CACHE = OUTPUT_DIR / "sitemap_sm.xml"

# URL classifiers from sm2en.md — order matters (first match wins)
CLASSIFIERS = [
    # Bible chapters (NWT + BI12)
    ("bible_chapter", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/tusi-paia/(nwt|bi12)/tusi/[^/]+/\d+/")),
    ("bible_book_toc", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/tusi-paia/(nwt|bi12)/tusi/[^/]+/?$")),
    ("bible_supplement", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/tusi-paia/(nwt|bi12)/faatomuaga")),
    ("bible_index", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/tusi-paia/")),
    # Publications
    ("magazine", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/mekasini/")),
    ("book", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/tusi/")),
    ("brochure", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/polosiua/")),
    ("song", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/musika-pese/")),
    ("video", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/viti")),
    ("meeting_workbook", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/jw-polokalame-mo-le-sauniga/")),
    ("kingdom_ministry", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/faiva-o-le-malo/")),
    ("program", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/polokalame/")),
    ("series", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/faasologa/")),
    ("tract", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/s%C4%81vali/")),
    ("audio_stories", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/tala-faalogologo")),
    ("glossary", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/faasino-upu/")),
    ("guide", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/ta%CA%BBiala/")),
    ("publication_index", re.compile(r"jw\.org/sm/lomiga-ma-isi-mea/")),
    # Study / FAQ
    ("faq", re.compile(r"jw\.org/sm/a%CA%BBoa%CA%BBoga-a-le-tusi-paia/o-fesili/")),
    ("study_youth", re.compile(r"jw\.org/sm/a%CA%BBoa%CA%BBoga-a-le-tusi-paia/talavou/")),
    ("study_children", re.compile(r"jw\.org/sm/a%CA%BBoa%CA%BBoga-a-le-tusi-paia/tamaiti/")),
    ("study_science", re.compile(r"jw\.org/sm/a%CA%BBoa%CA%BBoga-a-le-tusi-paia/faasaienisi/")),
    ("study_family", re.compile(r"jw\.org/sm/a%CA%BBoa%CA%BBoga-a-le-tusi-paia/aiga/")),
    ("study_scripture", re.compile(r"jw\.org/sm/a%CA%BBoa%CA%BBoga-a-le-tusi-paia/mau-o-le-tusi-paia/")),
    ("study_hub", re.compile(r"jw\.org/sm/a%CA%BBoa%CA%BBoga-a-le-tusi-paia/")),
    # Other sections
    ("news", re.compile(r"jw\.org/sm/mea-tutupu/")),
    ("about_jw", re.compile(r"jw\.org/sm/molimau-a-ieova/")),
    ("help", re.compile(r"jw\.org/sm/fesoasoani/")),
    ("legal", re.compile(r"jw\.org/sm/mataupu-tau-tulafono/")),
    ("whats_new", re.compile(r"jw\.org/sm/mea-fou/")),
    ("search", re.compile(r"jw\.org/sm/su%CA%BBe/")),
    ("home", re.compile(r"jw\.org/sm/?$")),
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
