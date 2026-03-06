"""Scrape WOL articles by docId, paragraph-aligned.

Uses Docker curl-impersonate for fetching (browser-like TLS fingerprint).

Usage:
    uv run python scripts/scrape_articles.py --pilot              # 5 articles
    uv run python scripts/scrape_articles.py --pub lv             # all chapters from pub "lv"
    uv run python scripts/scrape_articles.py --docids 1102008070 1102015820  # specific docIds
"""

import re
import sys
import json
import argparse
from pathlib import Path

from bs4 import BeautifulSoup
from tqdm import tqdm

# Add scripts dir to path for fetch module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch, fetch_and_save, fetch_soup

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
ALIGNED_DIR = DATA_DIR / "aligned"

TVL_BUNDLE = {"lang": "tvl", "rcode": "r153", "lpcode": "lp-vl"}
EN_BUNDLE = {"lang": "en", "rcode": "r1", "lpcode": "lp-e"}

WOL_ARTICLE_URL = "https://wol.jw.org/{lang}/wol/d/{rcode}/{lpcode}/{docId}"
WOL_PUB_TOC_URL = "https://wol.jw.org/tvl/wol/publication/r153/lp-vl/{pubCode}"

PILOT_DOCIDS = [
    "1102008070",  # "Let Marriage Be Honorable" (lv book chapter)
    "1102015820",  # "Answers to 10 Questions Young People Ask"
    "1102008066",  # another lv chapter
    "1102008067",  # another lv chapter
    "1102008068",  # another lv chapter
]

# Regex for extracting docIds from WOL links
DOCID_RE = re.compile(r"/wol/d/r\d+/lp-\w+/(\d+)")
# Regex for section sub-pages within a publication
SECTION_RE = re.compile(r"/wol/publication/r153/lp-vl/([^/]+)/\d+")


def harvest_docids_from_pub(pub_code: str) -> list[str]:
    """Harvest docIds from a publication's TOC page, including section sub-pages."""
    toc_url = WOL_PUB_TOC_URL.format(pubCode=pub_code)
    print(f"Fetching TOC: {toc_url}")

    html = fetch(toc_url)
    if html is None:
        print(f"  Failed to fetch TOC for {pub_code}")
        return []

    soup = BeautifulSoup(html, "html5lib")
    article = soup.find("article", id="article")
    if article is None:
        print(f"  No article#article found in TOC for {pub_code}")
        return []

    doc_ids = []
    section_urls = []

    for a_tag in article.find_all("a", href=True):
        href = a_tag["href"]

        # Check for docId links
        m = DOCID_RE.search(href)
        if m:
            doc_ids.append(m.group(1))
            continue

        # Check for section sub-pages
        m = SECTION_RE.search(href)
        if m:
            # Build full URL for the section page
            section_url = f"https://wol.jw.org{href}"
            section_urls.append(section_url)

    # Fetch section sub-pages and harvest more docIds
    if section_urls:
        print(f"  Found {len(section_urls)} section sub-pages, harvesting docIds...")
        for section_url in tqdm(section_urls, desc="Sections"):
            section_html = fetch(section_url)
            if section_html is None:
                continue
            section_soup = BeautifulSoup(section_html, "html5lib")
            section_article = section_soup.find("article", id="article")
            if section_article is None:
                continue
            for a_tag in section_article.find_all("a", href=True):
                m = DOCID_RE.search(a_tag["href"])
                if m:
                    doc_ids.append(m.group(1))

    # Deduplicate while preserving order
    seen = set()
    unique_ids = []
    for did in doc_ids:
        if did not in seen:
            seen.add(did)
            unique_ids.append(did)

    print(f"  Harvested {len(unique_ids)} unique docIds from {pub_code}")
    return unique_ids


def extract_paragraphs(html: str) -> list[tuple[str, str]]:
    """Extract (data-pid, text) tuples from article paragraphs.

    Scoped to article#article to avoid footnote panel paragraphs.
    Removes footnotes (a.fn), cross-refs (a.b), and superscripts (sup).
    """
    soup = BeautifulSoup(html, "html5lib")
    article = soup.find("article", id="article")
    if article is None:
        return []

    paragraphs = []
    for p_tag in article.find_all("p", attrs={"data-pid": True}):
        pid = p_tag["data-pid"]

        # Remove footnotes, cross-refs, and superscripts
        for unwanted in p_tag.find_all("a", class_=["fn", "b"]):
            unwanted.decompose()
        for sup in p_tag.find_all("sup"):
            sup.decompose()

        text = p_tag.get_text(strip=True)
        text = re.sub(r"\s+", " ", text).strip()

        if text:
            paragraphs.append((pid, text))

    return paragraphs


def align_paragraphs(tvl_paras: list[tuple[str, str]],
                     en_paras: list[tuple[str, str]],
                     doc_id: str,
                     pub_code: str | None) -> list[dict]:
    """Align TVL and EN paragraphs and return list of aligned pair dicts."""
    tvl_url = WOL_ARTICLE_URL.format(docId=doc_id, **TVL_BUNDLE)
    en_url = WOL_ARTICLE_URL.format(docId=doc_id, **EN_BUNDLE)

    tvl_pids = [pid for pid, _ in tvl_paras]
    en_pids = [pid for pid, _ in en_paras]

    tvl_dict = {pid: text for pid, text in tvl_paras}
    en_dict = {pid: text for pid, text in en_paras}

    pairs = []

    # Check alignment quality
    common_pids = [pid for pid in tvl_pids if pid in en_dict]
    tvl_count = len(tvl_paras)
    en_count = len(en_paras)

    if tvl_count == 0 or en_count == 0:
        return []

    mismatch_ratio = abs(tvl_count - en_count) / max(tvl_count, en_count)

    if mismatch_ratio > 0.2 and len(common_pids) < min(tvl_count, en_count) * 0.8:
        # Fall back to document-level alignment
        tvl_text = " ".join(text for _, text in tvl_paras)
        en_text = " ".join(text for _, text in en_paras)
        tvl_chars = len(tvl_text)
        en_chars = len(en_text)
        pairs.append({
            "id": f"article_{doc_id}_doc",
            "tvl": tvl_text,
            "en": en_text,
            "content_type": "article_paragraph",
            "domain": "book",
            "alignment_method": "document_level",
            "alignment_confidence": 0.6,
            "doc_id": doc_id,
            "source_url_tvl": tvl_url,
            "source_url_en": en_url,
            "book_num": None,
            "chapter": None,
            "verse": None,
            "date": None,
            "pub_code": pub_code,
            "tvl_chars": tvl_chars,
            "en_chars": en_chars,
            "length_ratio": round(tvl_chars / en_chars, 3) if en_chars > 0 else 0,
        })
    else:
        # Align by matching data-pid values
        if tvl_count == en_count and tvl_pids == en_pids:
            confidence = 0.9
        else:
            confidence = 0.8

        for pid in common_pids:
            tvl_text = tvl_dict[pid]
            en_text = en_dict[pid]
            tvl_chars = len(tvl_text)
            en_chars = len(en_text)
            pairs.append({
                "id": f"article_{doc_id}_p{pid}",
                "tvl": tvl_text,
                "en": en_text,
                "content_type": "article_paragraph",
                "domain": "book",
                "alignment_method": "paragraph_position",
                "alignment_confidence": confidence,
                "doc_id": doc_id,
                "source_url_tvl": tvl_url,
                "source_url_en": en_url,
                "book_num": None,
                "chapter": None,
                "verse": None,
                "date": None,
                "pub_code": pub_code,
                "tvl_chars": tvl_chars,
                "en_chars": en_chars,
                "length_ratio": round(tvl_chars / en_chars, 3) if en_chars > 0 else 0,
            })

    return pairs


def scrape_article(doc_id: str, pub_code: str | None = None) -> list[dict] | None:
    """Scrape a single article by docId in both languages, return aligned pairs."""
    tvl_url = WOL_ARTICLE_URL.format(docId=doc_id, **TVL_BUNDLE)
    en_url = WOL_ARTICLE_URL.format(docId=doc_id, **EN_BUNDLE)

    raw_tvl_path = str(RAW_DIR / "wol_tvl" / f"article_{doc_id}.html")
    raw_en_path = str(RAW_DIR / "wol_en" / f"article_{doc_id}.html")

    # Fetch Tuvaluan
    tvl_html = fetch_and_save(tvl_url, raw_tvl_path)
    if tvl_html is None:
        print(f"  SKIP {doc_id} -- TVL not found")
        return None

    # Fetch English
    en_html = fetch_and_save(en_url, raw_en_path)
    if en_html is None:
        print(f"  SKIP {doc_id} -- EN not found")
        return None

    # Extract paragraphs
    tvl_paras = extract_paragraphs(tvl_html)
    en_paras = extract_paragraphs(en_html)

    if not tvl_paras or not en_paras:
        print(f"  SKIP {doc_id} -- no paragraphs extracted "
              f"(TVL: {len(tvl_paras)}, EN: {len(en_paras)})")
        return None

    # Align
    pairs = align_paragraphs(tvl_paras, en_paras, doc_id, pub_code)
    return pairs


def main():
    parser = argparse.ArgumentParser(
        description="Scrape WOL articles by docId, paragraph-aligned.")
    parser.add_argument("--pilot", action="store_true",
                        help="Pilot: 5 known articles")
    parser.add_argument("--pub", type=str,
                        help="Harvest docIds from publication TOC (e.g., 'lv')")
    parser.add_argument("--docids", nargs="+",
                        help="Specific docIds to scrape")
    args = parser.parse_args()

    pub_code = None

    if args.pilot:
        doc_ids = PILOT_DOCIDS
        pub_code = "lv"
    elif args.pub:
        pub_code = args.pub
        doc_ids = harvest_docids_from_pub(pub_code)
        if not doc_ids:
            print(f"No docIds found for publication '{pub_code}'")
            sys.exit(1)
    elif args.docids:
        doc_ids = args.docids
    else:
        print("Specify --pilot, --pub <code>, or --docids <id1> <id2> ...")
        sys.exit(1)

    ALIGNED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = ALIGNED_DIR / "articles.jsonl"

    # Load existing data to support resume
    existing_ids = set()
    existing_docids = set()
    if output_file.exists():
        with open(output_file) as f:
            for line in f:
                row = json.loads(line)
                existing_ids.add(row["id"])
                if row.get("doc_id"):
                    existing_docids.add(row["doc_id"])
        print(f"Found {len(existing_ids)} existing aligned pairs "
              f"({len(existing_docids)} articles), will skip duplicates")

    total_new_pairs = 0
    total_pairs_cumulative = len(existing_ids)
    skipped = 0
    failed = 0

    with open(output_file, "a") as out:
        for doc_id in tqdm(doc_ids, desc="Scraping articles"):
            if doc_id in existing_docids:
                skipped += 1
                continue

            pairs = scrape_article(doc_id, pub_code)
            if pairs is None:
                failed += 1
                continue

            article_new = 0
            for pair in pairs:
                if pair["id"] not in existing_ids:
                    out.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    total_new_pairs += 1
                    article_new += 1
                    existing_ids.add(pair["id"])
                    total_pairs_cumulative += 1

            existing_docids.add(doc_id)

            tqdm.write(f"  {doc_id}: {article_new} pairs "
                       f"[cumulative: {total_pairs_cumulative} total, "
                       f"{total_new_pairs} new]")

    print(f"\nDone! {total_new_pairs} new pairs written "
          f"({skipped} articles skipped, {failed} failed)")
    print(f"Total pairs in {output_file}: {total_pairs_cumulative}")


if __name__ == "__main__":
    main()
