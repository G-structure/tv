"""Scrape WOL Bible chapters and extract verse-aligned parallel text.

Usage:
    uv run python scripts/scrape_bible.py --pilot    # 3 chapters pilot
    uv run python scripts/scrape_bible.py --full      # all 66 books
"""

import re
import sys
import json
import time
import argparse
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from tqdm import tqdm

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
ALIGNED_DIR = DATA_DIR / "aligned"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# WOL URL templates — bookNo and chapter are numeric, universal across languages
WOL_BIBLE_URL = "https://wol.jw.org/{lang}/wol/b/{rcode}/{lpcode}/nwt/{book_no}/{chapter}"
TVL_BUNDLE = {"lang": "tvl", "rcode": "r153", "lpcode": "lp-vl"}
EN_BUNDLE = {"lang": "en", "rcode": "r1", "lpcode": "lp-e"}

# Bible books: (bookNo, english_name, chapter_count)
BIBLE_BOOKS = [
    (1, "Genesis", 50), (2, "Exodus", 40), (3, "Leviticus", 27),
    (4, "Numbers", 36), (5, "Deuteronomy", 34), (6, "Joshua", 24),
    (7, "Judges", 21), (8, "Ruth", 4), (9, "1 Samuel", 31),
    (10, "2 Samuel", 24), (11, "1 Kings", 22), (12, "2 Kings", 25),
    (13, "1 Chronicles", 29), (14, "2 Chronicles", 36), (15, "Ezra", 10),
    (16, "Nehemiah", 13), (17, "Esther", 10), (18, "Job", 42),
    (19, "Psalms", 150), (20, "Proverbs", 31), (21, "Ecclesiastes", 12),
    (22, "Song of Solomon", 8), (23, "Isaiah", 66), (24, "Jeremiah", 52),
    (25, "Lamentations", 5), (26, "Ezekiel", 48), (27, "Daniel", 12),
    (28, "Hosea", 14), (29, "Joel", 3), (30, "Amos", 9),
    (31, "Obadiah", 1), (32, "Jonah", 4), (33, "Micah", 7),
    (34, "Nahum", 3), (35, "Habakkuk", 3), (36, "Zephaniah", 3),
    (37, "Haggai", 2), (38, "Zechariah", 14), (39, "Malachi", 4),
    (40, "Matthew", 28), (41, "Mark", 16), (42, "Luke", 24),
    (43, "John", 21), (44, "Acts", 28), (45, "Romans", 16),
    (46, "1 Corinthians", 16), (47, "2 Corinthians", 13),
    (48, "Galatians", 6), (49, "Ephesians", 6), (50, "Philippians", 4),
    (51, "Colossians", 4), (52, "1 Thessalonians", 5),
    (53, "2 Thessalonians", 3), (54, "1 Timothy", 6), (55, "2 Timothy", 4),
    (56, "Titus", 3), (57, "Philemon", 1), (58, "Hebrews", 13),
    (59, "James", 5), (60, "1 Peter", 5), (61, "2 Peter", 3),
    (62, "1 John", 5), (63, "2 John", 1), (64, "3 John", 1),
    (65, "Jude", 1), (66, "Revelation", 22),
]

PILOT_CHAPTERS = [
    (1, 1),   # Genesis 1
    (19, 19), # Psalm 19
    (43, 3),  # John 3
]

DELAY = 3  # seconds between requests


def fetch_page(client: httpx.Client, url: str, max_retries: int = 3) -> str | None:
    """Fetch a page with retries and exponential backoff."""
    for attempt in range(max_retries):
        try:
            r = client.get(url)
            if r.status_code == 200:
                return r.text
            elif r.status_code == 404:
                return None
            else:
                print(f"  HTTP {r.status_code} for {url}", file=sys.stderr)
        except Exception as e:
            wait = DELAY * (2 ** attempt)
            print(f"  Retry {attempt+1}/{max_retries} after {wait}s: {e}", file=sys.stderr)
            time.sleep(wait)
    return None


def extract_verses(html: str) -> dict[int, str]:
    """Extract verse number → text mapping from a WOL Bible chapter page.

    HTML structure:
      <span class="v" id="v{bookNo}-{ch}-{verse}-1">
        <span class="vl">N </span>
        verse text...
        <a class="fn">*</a>       ← footnote (remove)
        <a class="b">+</a>        ← cross-ref (remove)
      </span>
    """
    soup = BeautifulSoup(html, "html5lib")
    verses = {}

    for v_span in soup.find_all("span", class_="v"):
        vid = v_span.get("id", "")
        # Parse verse number from id: v{book}-{ch}-{verse}-{part}
        m = re.match(r"v(\d+)-(\d+)-(\d+)-(\d+)", vid)
        if not m:
            continue
        verse_no = int(m.group(3))

        # Remove footnotes and cross-references before extracting text
        for unwanted in v_span.find_all("a", class_=["fn", "b"]):
            unwanted.decompose()
        # Remove superscripts that are just markers
        for sup in v_span.find_all("sup"):
            sup.decompose()

        text = v_span.get_text(strip=True)
        # Remove the leading verse number (e.g., "1 " or "23 ")
        text = re.sub(r"^\d+\s*", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        if text:
            # Merge multi-part verses (same verse number, different part)
            if verse_no in verses:
                verses[verse_no] += " " + text
            else:
                verses[verse_no] = text

    return verses


def scrape_chapter(client: httpx.Client, book_no: int, chapter: int,
                   book_name: str) -> dict | None:
    """Scrape a single chapter in both languages and return aligned verses."""
    tvl_url = WOL_BIBLE_URL.format(book_no=book_no, chapter=chapter, **TVL_BUNDLE)
    en_url = WOL_BIBLE_URL.format(book_no=book_no, chapter=chapter, **EN_BUNDLE)

    # Fetch Tuvaluan
    time.sleep(DELAY)
    tvl_html = fetch_page(client, tvl_url)
    if tvl_html is None:
        print(f"  SKIP {book_name} {chapter} — TVL not found")
        return None

    # Save raw HTML
    raw_tvl = RAW_DIR / "wol_tvl" / f"bible_{book_no}_{chapter}.html"
    raw_tvl.parent.mkdir(parents=True, exist_ok=True)
    raw_tvl.write_text(tvl_html)

    # Fetch English
    time.sleep(DELAY)
    en_html = fetch_page(client, en_url)
    if en_html is None:
        print(f"  SKIP {book_name} {chapter} — EN not found")
        return None

    raw_en = RAW_DIR / "wol_en" / f"bible_{book_no}_{chapter}.html"
    raw_en.parent.mkdir(parents=True, exist_ok=True)
    raw_en.write_text(en_html)

    # Extract verses
    tvl_verses = extract_verses(tvl_html)
    en_verses = extract_verses(en_html)

    # Align by verse number
    aligned = []
    all_verse_nos = sorted(set(tvl_verses.keys()) | set(en_verses.keys()))
    for vno in all_verse_nos:
        tvl_text = tvl_verses.get(vno, "")
        en_text = en_verses.get(vno, "")
        if tvl_text and en_text:
            tvl_chars = len(tvl_text)
            en_chars = len(en_text)
            aligned.append({
                "id": f"bible_{book_no}_{chapter}_{vno}",
                "tvl": tvl_text,
                "en": en_text,
                "content_type": "bible_verse",
                "domain": "bible",
                "alignment_method": "verse_number",
                "alignment_confidence": 1.0,
                "doc_id": None,
                "source_url_tvl": tvl_url,
                "source_url_en": en_url,
                "book_num": book_no,
                "book_name": book_name,
                "chapter": chapter,
                "verse": vno,
                "date": None,
                "pub_code": "nwt",
                "tvl_chars": tvl_chars,
                "en_chars": en_chars,
                "length_ratio": round(tvl_chars / en_chars, 3) if en_chars > 0 else 0,
            })

    return {
        "book_no": book_no,
        "book_name": book_name,
        "chapter": chapter,
        "tvl_verses": len(tvl_verses),
        "en_verses": len(en_verses),
        "aligned_pairs": len(aligned),
        "pairs": aligned,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true", help="Pilot: 3 chapters only")
    parser.add_argument("--full", action="store_true", help="Full: all 66 books")
    parser.add_argument("--book", type=int, help="Scrape a single book by number (1-66)")
    args = parser.parse_args()

    if args.pilot:
        chapters_to_scrape = [(bno, ch, next(n for b, n, _ in BIBLE_BOOKS if b == bno))
                              for bno, ch in PILOT_CHAPTERS]
    elif args.book:
        book_info = next((b for b in BIBLE_BOOKS if b[0] == args.book), None)
        if not book_info:
            print(f"Book number {args.book} not found")
            sys.exit(1)
        bno, bname, num_ch = book_info
        chapters_to_scrape = [(bno, ch, bname) for ch in range(1, num_ch + 1)]
    elif args.full:
        chapters_to_scrape = [(bno, ch, bname)
                              for bno, bname, num_ch in BIBLE_BOOKS
                              for ch in range(1, num_ch + 1)]
    else:
        print("Specify --pilot, --full, or --book N")
        sys.exit(1)

    ALIGNED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = ALIGNED_DIR / "bible_verses.jsonl"

    # Load existing data to support resume
    existing_ids = set()
    if output_file.exists():
        with open(output_file) as f:
            for line in f:
                row = json.loads(line)
                existing_ids.add(row["id"])
        print(f"Found {len(existing_ids)} existing aligned pairs, will skip duplicates")

    client = httpx.Client(http2=True, headers=HEADERS, timeout=30, follow_redirects=True)

    total_pairs = 0
    skipped = 0

    with open(output_file, "a") as out:
        for book_no, chapter, book_name in tqdm(chapters_to_scrape, desc="Scraping"):
            # Check if already done
            test_id = f"bible_{book_no}_{chapter}_1"
            if test_id in existing_ids:
                skipped += 1
                continue

            result = scrape_chapter(client, book_no, chapter, book_name)
            if result is None:
                continue

            for pair in result["pairs"]:
                if pair["id"] not in existing_ids:
                    out.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    total_pairs += 1
                    existing_ids.add(pair["id"])

            tqdm.write(f"  {book_name} {chapter}: "
                       f"{result['tvl_verses']} TVL / {result['en_verses']} EN → "
                       f"{result['aligned_pairs']} pairs")

    client.close()

    print(f"\nDone! {total_pairs} new pairs written ({skipped} chapters skipped)")
    print(f"Total pairs in {output_file}: {len(existing_ids)}")


if __name__ == "__main__":
    main()
