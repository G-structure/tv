"""Scrape the full Tuvaluan-English dictionary from tuvalu.aa-ken.jp.

The main site is a Laravel app serving ~3,200 unique word entries across
158 categories, paginated at 10 per page. Categories are keyed by Japanese
names in the URL query parameter.

Uses Docker curl-impersonate for fetching (browser-like TLS fingerprint).

Usage:
    uv run python scripts/scrape_tuvalu_dictionary.py
    uv run python scripts/scrape_tuvalu_dictionary.py --dry-run
    uv run python scripts/scrape_tuvalu_dictionary.py --category "動詞一覧"
"""

import json
import math
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote, urlencode

from bs4 import BeautifulSoup
from tqdm import tqdm

# Add scripts dir to path for fetch module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw" / "tuvalu_dictionary"
ALIGNED_DIR = DATA_DIR / "aligned"

BASE_URL = "https://tuvalu.aa-ken.jp/en/search/"
SOURCE_URL = "https://tuvalu.aa-ken.jp/en/search/"
ENTRIES_PER_PAGE = 10

# Fullwidth → ASCII (source sometimes has fullwidth chars)
FULLWIDTH_MAP = str.maketrans({
    "\uff1f": "?", "\uff01": "!", "\uff0c": ",", "\uff0e": ".",
    "\uff08": "(", "\uff09": ")", "\uff1a": ":", "\uff1b": ";",
})


def clean_text(text: str) -> str:
    """Normalize text: NFC, fullwidth, whitespace."""
    text = text.translate(FULLWIDTH_MAP)
    text = unicodedata.normalize("NFC", text)
    # Normalize glottal stop: ASCII ' (U+0027) → reversed prime (U+2035)
    text = text.replace("'", "\u2035")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_categories(html: str) -> list[dict]:
    """Extract all categories from the sidebar of a search page.

    The sidebar uses hierarchical Japanese keys in href (e.g. 人間:家族・親族)
    while data-jpn only has the leaf name. We extract the full key from href.

    Returns list of {jpn_key, en_name} dicts.
    """
    from urllib.parse import unquote

    soup = BeautifulSoup(html, "html5lib")
    categories = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "category=" not in href:
            continue

        # Extract full category key from URL
        cat_param = href.split("category=")[1].split("&")[0].split("#")[0]
        jpn_key = unquote(cat_param)

        if not jpn_key or jpn_key in seen:
            continue
        seen.add(jpn_key)

        en_name = a.get_text(strip=True)
        # Skip non-category links (like language switcher "JP"/"EN")
        if en_name in ("JP", "EN", ""):
            continue

        categories.append({
            "jpn_key": jpn_key,
            "en_name": en_name,
        })

    return categories


def extract_entry_count(html: str) -> int:
    """Extract the total entry count from a search results page."""
    soup = BeautifulSoup(html, "html5lib")
    entry_num = soup.find("div", class_="entry-num")
    if not entry_num:
        return 0
    text = entry_num.get_text(strip=True)
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else 0


def extract_entries(html: str, category_en: str, category_jpn: str) -> list[dict]:
    """Extract dictionary entries from a search results page."""
    soup = BeautifulSoup(html, "html5lib")
    entries = []

    for entry_div in soup.find_all("div", class_="dictionary-entry"):
        rows = entry_div.find_all("div", class_="row", recursive=False)
        if not rows:
            continue

        main_row = rows[0]
        cols = main_row.find_all("div", recursive=False)
        if len(cols) < 2:
            continue

        # Column 1: Tuvaluan word + audio
        tvl_col = cols[0]

        # Remove audio link before extracting text
        audio_id = None
        audio_link = tvl_col.find("a", class_="sounds")
        if audio_link:
            audio_id = audio_link.get("data-file", "")
            audio_link.decompose()

        # Strip homograph superscript numbers (e.g. "gata<sup>2</sup>" → "gata")
        for sup in tvl_col.find_all("sup"):
            sup.decompose()
        tvl_word = tvl_col.get_text(strip=True)

        # Strip "volume_up" text artifact from audio icon rendering
        tvl_word = re.sub(r"volume_up", "", tvl_word).strip()

        if not tvl_word:
            continue

        # Column 2: English definitions
        def_col = cols[1] if len(cols) > 1 else None
        en_parts = []
        if def_col:
            # Remove Japanese definition divs to get only English
            def_col_copy = def_col.__copy__() if hasattr(def_col, '__copy__') else def_col
            for eng_div in def_col.find_all("div", class_="eng"):
                eng_div.decompose()
            # Get English text (POS markers + definitions)
            en_text = def_col.get_text(" ", strip=True)
            en_text = re.sub(r"\s+", " ", en_text).strip()
            if en_text:
                en_parts.append(en_text)

        en_def = " ".join(en_parts).strip()
        if not en_def:
            continue

        # Check for photos
        has_photo = False
        photos = []
        if len(rows) > 1:
            pic_row = rows[1]
            if "pictures" in (pic_row.get("class") or []):
                has_photo = True
                for img in pic_row.find_all("img"):
                    src = img.get("src", "")
                    if src:
                        photos.append(src)

        tvl_clean = clean_text(tvl_word)
        en_clean = clean_text(en_def)

        entry = {
            "tvl": tvl_clean,
            "en": en_clean,
            "category": category_en,
            "category_jpn": category_jpn,
            "audio_id": audio_id if audio_id else None,
            "has_photo": has_photo,
        }
        entries.append(entry)

    return entries


def build_search_url(category_jpn: str, page: int = 1) -> str:
    """Build a search URL for a given Japanese category key and page number."""
    params = {"category": category_jpn}
    if page > 1:
        params["page"] = str(page)
    return f"{BASE_URL}?{urlencode(params)}"


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Scrape the full Tuvaluan-English dictionary from tuvalu.aa-ken.jp")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only discover categories and counts, don't scrape entries")
    parser.add_argument("--category", type=str,
                        help="Only scrape a specific category (Japanese key)")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ALIGNED_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Fetch a search page to extract all categories from sidebar
    print("Discovering categories...")
    cat_cache = RAW_DIR / "categories.json"

    if cat_cache.exists():
        categories = json.loads(cat_cache.read_text())
        print(f"  Loaded {len(categories)} categories from cache")
    else:
        # Fetch the Colors category (small, loads fast) to get sidebar
        html = fetch(build_search_url("色"))
        if html is None:
            # Try a different known category
            html = fetch(build_search_url("動詞一覧"))
        if html is None:
            print("ERROR: Cannot fetch any search page", file=sys.stderr)
            sys.exit(1)

        categories = extract_categories(html)
        cat_cache.write_text(json.dumps(categories, ensure_ascii=False, indent=2))
        print(f"  Discovered {len(categories)} categories")

    if args.category:
        categories = [c for c in categories if c["jpn_key"] == args.category]
        if not categories:
            print(f"Category '{args.category}' not found", file=sys.stderr)
            sys.exit(1)

    # Step 2: Get entry counts for each category
    print("\nGetting entry counts...")
    cat_counts_cache = RAW_DIR / "category_counts.json"

    if cat_counts_cache.exists() and not args.category:
        cat_counts = json.loads(cat_counts_cache.read_text())
        print(f"  Loaded counts from cache")
    else:
        cat_counts = {}

    cats_to_count = [c for c in categories if c["jpn_key"] not in cat_counts]
    if cats_to_count:
        for cat in tqdm(cats_to_count, desc="Counting"):
            url = build_search_url(cat["jpn_key"])
            html = fetch(url)
            if html is None:
                tqdm.write(f"  SKIP {cat['en_name']}: fetch failed")
                cat_counts[cat["jpn_key"]] = 0
                continue
            count = extract_entry_count(html)
            cat_counts[cat["jpn_key"]] = count

            # Cache the first page HTML for scraping later
            page_cache = RAW_DIR / "pages" / f"{quote(cat['jpn_key'], safe='')}_p1.html"
            page_cache.parent.mkdir(parents=True, exist_ok=True)
            if not page_cache.exists():
                page_cache.write_text(html)

        cat_counts_cache.write_text(json.dumps(cat_counts, ensure_ascii=False, indent=2))

    total_entries = sum(cat_counts.get(c["jpn_key"], 0) for c in categories)
    total_pages = sum(math.ceil(cat_counts.get(c["jpn_key"], 0) / ENTRIES_PER_PAGE)
                      for c in categories)
    print(f"  Total: {total_entries} entries across {len(categories)} categories "
          f"({total_pages} pages to fetch)")

    if args.dry_run:
        print("\n[DRY RUN] Category summary:")
        for cat in sorted(categories, key=lambda c: -cat_counts.get(c["jpn_key"], 0)):
            count = cat_counts.get(cat["jpn_key"], 0)
            pages = math.ceil(count / ENTRIES_PER_PAGE)
            print(f"  {cat['en_name']:50s} {count:>5d} entries ({pages:>3d} pages)")
        return

    # Step 3: Scrape all pages
    print("\nScraping entries...")
    all_entries = []

    for cat in tqdm(categories, desc="Categories"):
        count = cat_counts.get(cat["jpn_key"], 0)
        if count == 0:
            continue

        num_pages = math.ceil(count / ENTRIES_PER_PAGE)

        for page in range(1, num_pages + 1):
            page_cache = RAW_DIR / "pages" / f"{quote(cat['jpn_key'], safe='')}_p{page}.html"
            page_cache.parent.mkdir(parents=True, exist_ok=True)

            if page_cache.exists() and page_cache.stat().st_size > 0:
                html = page_cache.read_text()
            else:
                url = build_search_url(cat["jpn_key"], page)
                html = fetch(url)
                if html is None:
                    tqdm.write(f"  FAIL: {cat['en_name']} page {page}")
                    continue
                page_cache.write_text(html)

            entries = extract_entries(html, cat["en_name"], cat["jpn_key"])
            all_entries.extend(entries)

    print(f"\nRaw entries scraped: {len(all_entries)}")

    # Step 4: Deduplicate by (tvl, en) content
    seen = set()
    deduped = []
    # Track all categories per word for metadata
    word_categories = {}  # (tvl, en) -> list of categories

    for entry in all_entries:
        key = (entry["tvl"].lower(), entry["en"].lower())
        if key not in word_categories:
            word_categories[key] = []
        if entry["category"] not in word_categories[key]:
            word_categories[key].append(entry["category"])

        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)

    print(f"After deduplication: {len(deduped)} unique entries "
          f"({len(all_entries) - len(deduped)} duplicates removed)")

    # Step 5: Build output records
    output_file = ALIGNED_DIR / "tuvalu_dictionary.jsonl"
    records = []

    for i, entry in enumerate(deduped):
        key = (entry["tvl"].lower(), entry["en"].lower())
        all_cats = word_categories.get(key, [entry["category"]])

        record = {
            "id": f"tuvalu_dict_{i}",
            "tvl": entry["tvl"],
            "en": entry["en"],
            "content_type": "word",
            "domain": "dictionary",
            "alignment_method": "index",
            "alignment_confidence": 1.0,
            "doc_id": None,
            "source_url_tvl": SOURCE_URL,
            "source_url_en": SOURCE_URL,
            "book_num": None,
            "chapter": None,
            "verse": None,
            "date": None,
            "pub_code": None,
            "category": entry["category"],
            "categories": all_cats,
            "subcategory": entry.get("category_jpn"),
            "audio_id": entry.get("audio_id"),
            "tvl_chars": len(entry["tvl"]),
            "en_chars": len(entry["en"]),
            "length_ratio": round(len(entry["tvl"]) / len(entry["en"]), 3)
                if len(entry["en"]) > 0 else 0,
        }
        records.append(record)

    with open(output_file, "w") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nDone! {len(records)} unique entries written to {output_file}")

    # Summary stats
    audio_count = sum(1 for r in records if r.get("audio_id"))
    cats = set()
    for r in records:
        for c in r.get("categories", []):
            cats.add(c)
    print(f"  With audio: {audio_count}")
    print(f"  Categories represented: {len(cats)}")


if __name__ == "__main__":
    main()
