"""Scrape tuvalu.aa-ken.jp Tuvaluan learning app — words + expressions.

The site is a Svelte SPA that loads JSON data from ./data/ endpoints.
Two data types:
  - expressions.json: 23 categories of Tuvaluan/English/Japanese phrase sets
  - {subcategory}.json: 42 word lists with Tuvaluan/English pairs

Uses Docker curl-impersonate for fetching (browser-like TLS fingerprint).

Usage:
    uv run python scripts/scrape_tuvalu_app.py
    uv run python scripts/scrape_tuvalu_app.py --words-only
    uv run python scripts/scrape_tuvalu_app.py --expressions-only
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

from tqdm import tqdm

# Add scripts dir to path for fetch module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw" / "tuvalu_app"
ALIGNED_DIR = DATA_DIR / "aligned"

BASE_URL = "https://tuvalu.aa-ken.jp/webapp/data"

# Categories and subcategories extracted from the app's bundle.js
WORD_CATEGORIES = [
    {"category": "Human", "subCategory": [
        "Family", "Relationships", "Body Parts", "Feelings",
        "Character & Appearance", "Health", "Occupation",
        "Sports & Amusements", "Life & Identity"]},
    {"category": "House", "subCategory": ["House", "Furniture & Necessities"]},
    {"category": "Food", "subCategory": ["Food"]},
    {"category": "Clothes", "subCategory": ["Clothes"]},
    {"category": "Number", "subCategory": ["Numbers"]},
    {"category": "Time & Dates", "subCategory": ["Times", "A Week & Months"]},
    {"category": "Colors", "subCategory": ["Colors"]},
    {"category": "Nature", "subCategory": ["Climates", "Land, Sea, Sky"]},
    {"category": "Education", "subCategory": ["Education"]},
    {"category": "Politics & Religion", "subCategory": ["Politics & Religion"]},
    {"category": "Countries & Places", "subCategory": [
        "Countries & Islands", "Town & Facilities"]},
    {"category": "Animals", "subCategory": ["Animals"]},
    {"category": "Plants", "subCategory": ["Plants"]},
    {"category": "Basic Verbs", "subCategory": [
        "A-E", "F", "faka-", "G-K", "L-N", "O-P", "S", "T", "U-V"]},
    {"category": "Adjectives & Adverbs", "subCategory": [
        "A-F", "G-L", "M", "N-S", "T-V"]},
    {"category": "Directions", "subCategory": ["Directions"]},
    {"category": "Useful Expressions", "subCategory": ["Useful Expressions"]},
    {"category": "Interrogatives", "subCategory": ["Interrogatives"]},
]


SOURCE_URL = "https://tuvalu.aa-ken.jp/webapp/"

# Fullwidth → ASCII replacements (source is Japanese-authored)
FULLWIDTH_MAP = str.maketrans({
    "\uff1f": "?", "\uff01": "!", "\uff0c": ",", "\uff0e": ".",
    "\uff08": "(", "\uff09": ")", "\uff1a": ":", "\uff1b": ";",
    "\uff10": "0", "\uff11": "1", "\uff12": "2", "\uff13": "3",
    "\uff14": "4", "\uff15": "5", "\uff16": "6", "\uff17": "7",
    "\uff18": "8", "\uff19": "9",
})


def normalize_fullwidth(text: str) -> str:
    """Replace fullwidth Japanese-style punctuation/digits with ASCII equivalents."""
    return text.translate(FULLWIDTH_MAP)


def split_slash_alternatives(tvl: str, en: str) -> list[tuple[str, str]]:
    """Split slash-separated alternatives into individual pairs.

    Only splits when both sides have the same number of slash-separated parts.
    Returns list of (tvl, en) tuples.
    """
    # Don't split if slash is part of a word (no spaces around it)
    # Only split on " / " (space-delimited) for expressions
    if " / " in tvl and " / " in en:
        tvl_parts = [p.strip() for p in tvl.split(" / ")]
        en_parts = [p.strip() for p in en.split(" / ")]
        if len(tvl_parts) == len(en_parts) and len(tvl_parts) > 1:
            return list(zip(tvl_parts, en_parts))

    # For single words with "/" (no spaces), split only if counts match
    if "/" in tvl and "/" in en and " " not in tvl and " " not in en:
        tvl_parts = [p.strip() for p in tvl.split("/")]
        en_parts = [p.strip() for p in en.split("/")]
        if len(tvl_parts) == len(en_parts) and len(tvl_parts) > 1:
            return list(zip(tvl_parts, en_parts))

    return [(tvl, en)]


def normalize_glottal_stop(text: str) -> str:
    """Normalize ASCII apostrophe to reversed prime (U+2035) for Tuvaluan glottal stop.

    The corpus (bible, articles) uses ‵ (U+2035), but this source uses ' (U+0027).
    """
    return text.replace("'", "\u2035")


def strip_filler_hyphens(text: str) -> str:
    """Strip placeholder hyphens from dictionary entries.

    Handles:
      - "to stop -" → "to stop"
      - "who -?" → "who?"
      - "Se a - ?" → "Se a?"
      - "what -? (singular)" → "what? (singular)"
      - "Tefea -?/Tehea?" → "Tefea?/Tehea?"  (mid-word slash compounds)
      - "kaia-?" → "kaia?"
    """
    # " -?" or " - ?" with optional trailing content → collapse to "?"
    text = re.sub(r"\s*-\s*\?", "?", text)
    # "-?" stuck to word (no space) → just "?"
    text = re.sub(r"-\?", "?", text)
    # Trailing " -" (no question mark) → strip
    text = re.sub(r"\s+-\s*$", "", text)
    return text.strip()


def strip_pedagogical_parens(text: str) -> str:
    """Remove pedagogical parenthetical commentary from EN text.

    Keeps short grammatical disambiguators like (plural), (weight), (of string).
    Strips longer explanatory notes like (next to you), (the thing is near...).
    """
    def should_strip(match):
        content = match.group(1).strip()
        # Keep short grammatical disambiguators
        keep = {"plural", "singular", "weight", "of string", "people",
                "future", "past", "formal", "informal"}
        if content.lower() in keep:
            return match.group(0)  # keep as-is
        # Strip if it contains pronouns/articles (sentence-like commentary)
        if re.search(r"\b(you|he|she|it|the|is|are|was|near|next|ok)\b", content, re.I):
            return ""
        return match.group(0)  # keep by default

    return re.sub(r"\s*\(([^)]+)\)", should_strip, text).strip()


# Known EN typos in source data
TYPO_FIXES = {
    "listner": "listener",
}


def fix_typos(text: str) -> str:
    """Fix known typos in the source data."""
    for wrong, right in TYPO_FIXES.items():
        text = text.replace(wrong, right)
    return text


def clean_text(text: str, is_tvl: bool = False) -> str:
    """Clean a single text field: normalize fullwidth chars, strip whitespace."""
    text = normalize_fullwidth(text)
    text = unicodedata.normalize("NFC", text)
    if is_tvl:
        text = normalize_glottal_stop(text)
    else:
        text = fix_typos(text)
        text = strip_pedagogical_parens(text)
    text = strip_filler_hyphens(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def subcategory_to_filename(name: str) -> str:
    """Convert subcategory name to JSON filename (matches app's Ve function)."""
    return name.replace("&", "and").lower().replace(" ", "_") + ".json"


def fetch_json(url: str) -> dict | list | None:
    """Fetch a URL and parse as JSON."""
    html = fetch(url)
    if html is None:
        return None
    try:
        return json.loads(html)
    except json.JSONDecodeError as e:
        print(f"  JSON decode error for {url}: {e}", file=sys.stderr)
        return None


def scrape_expressions() -> list[dict]:
    """Scrape expressions.json — trilingual phrase sets."""
    url = f"{BASE_URL}/expressions.json"
    print(f"Fetching expressions from {url}")

    # Cache raw JSON
    raw_path = RAW_DIR / "expressions.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    if raw_path.exists() and raw_path.stat().st_size > 0:
        data = json.loads(raw_path.read_text())
        print(f"  Loaded from cache: {len(data)} categories")
    else:
        data = fetch_json(url)
        if data is None:
            print("  FAILED to fetch expressions.json", file=sys.stderr)
            return []
        raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"  Fetched {len(data)} expression categories")

    records = []
    for cat in data:
        cat_name = cat.get("category_e", cat.get("name", ""))
        tvl_exprs = cat.get("expression_t", [])
        en_exprs = cat.get("expression_e", [])
        jp_exprs = cat.get("expression_j", [])

        for i, (tvl_raw, en_raw) in enumerate(zip(tvl_exprs, en_exprs)):
            tvl = clean_text(tvl_raw, is_tvl=True)
            en = clean_text(en_raw, is_tvl=False)
            if not tvl or not en:
                continue

            # Split slash-separated alternatives into individual pairs
            pairs = split_slash_alternatives(tvl, en)
            for j, (tvl_part, en_part) in enumerate(pairs):
                if not tvl_part or not en_part:
                    continue
                suffix = f"_{j}" if len(pairs) > 1 else ""
                record = {
                    "id": f"tuvalu_app_expr_{cat['name']}_{i}{suffix}",
                    "tvl": tvl_part,
                    "en": en_part,
                    "content_type": "expression",
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
                    "category": cat_name,
                    "subcategory": cat["name"],
                    "tvl_chars": len(tvl_part),
                    "en_chars": len(en_part),
                    "length_ratio": round(len(tvl_part) / len(en_part), 3)
                        if len(en_part) > 0 else 0,
                }
                records.append(record)

    return records


def scrape_words() -> list[dict]:
    """Scrape all word category JSON files."""
    records = []
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Build flat list of (category, subcategory, filename)
    subcats = []
    for cat in WORD_CATEGORIES:
        for sub in cat["subCategory"]:
            fname = subcategory_to_filename(sub)
            subcats.append((cat["category"], sub, fname))

    print(f"Fetching {len(subcats)} word subcategories")

    for category, subcategory, fname in tqdm(subcats, desc="Scraping words"):
        raw_path = RAW_DIR / fname

        if raw_path.exists() and raw_path.stat().st_size > 0:
            data = json.loads(raw_path.read_text())
        else:
            url = f"{BASE_URL}/{fname}"
            data = fetch_json(url)
            if data is None:
                tqdm.write(f"  FAILED: {fname}")
                continue
            raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

        words = data.get("words", [])
        for word in words:
            tvl = clean_text(word.get("tuvalu", ""), is_tvl=True)
            en = clean_text(word.get("english", ""), is_tvl=False)
            if not tvl or not en:
                continue

            # Split slash-separated alternatives
            pairs = split_slash_alternatives(tvl, en)
            for j, (tvl_part, en_part) in enumerate(pairs):
                if not tvl_part or not en_part:
                    continue
                suffix = f"_{j}" if len(pairs) > 1 else ""
                # Useful Expressions are full phrases, not single words
                ctype = "expression" if subcategory == "Useful Expressions" else "word"
                record = {
                    "id": f"tuvalu_app_word_{fname[:-5]}_{word.get('id', 0)}{suffix}",
                    "tvl": tvl_part,
                    "en": en_part,
                    "content_type": ctype,
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
                    "category": category,
                    "subcategory": subcategory,
                    "tvl_chars": len(tvl_part),
                    "en_chars": len(en_part),
                    "length_ratio": round(len(tvl_part) / len(en_part), 3)
                        if len(en_part) > 0 else 0,
                }
                records.append(record)

    return records


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Scrape tuvalu.aa-ken.jp learning app (words + expressions)")
    parser.add_argument("--words-only", action="store_true",
                        help="Only scrape word categories")
    parser.add_argument("--expressions-only", action="store_true",
                        help="Only scrape expressions")
    args = parser.parse_args()

    ALIGNED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = ALIGNED_DIR / "tuvalu_app.jsonl"

    all_records = []

    if not args.words_only:
        expr_records = scrape_expressions()
        all_records.extend(expr_records)
        print(f"Expressions: {len(expr_records)} pairs")

    if not args.expressions_only:
        word_records = scrape_words()
        all_records.extend(word_records)
        print(f"Words: {len(word_records)} pairs")

    # Deduplicate by (tvl.lower(), en.lower()) content
    seen = set()
    deduped = []
    dupes = 0
    for record in all_records:
        key = (record["tvl"].lower(), record["en"].lower())
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        deduped.append(record)

    if dupes:
        print(f"Deduplicated: {dupes} duplicate (tvl, en) pairs removed")

    # Write output
    with open(output_file, "w") as f:
        for record in deduped:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nDone! {len(deduped)} total pairs written to {output_file}")


if __name__ == "__main__":
    main()
