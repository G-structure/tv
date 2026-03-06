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
# Regex for library sub-pages
LIBRARY_RE = re.compile(r"/wol/library/r153/lp-vl/")

WOL_BASE = "https://wol.jw.org"


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


def harvest_docids_from_library(url: str, max_depth: int = 5,
                                _visited: set | None = None) -> list[str]:
    """Recursively crawl WOL library pages to harvest all docIds.

    Follows /wol/library/ sub-page links and /wol/publication/ links,
    collecting all /wol/d/ docId links found.
    """
    if _visited is None:
        _visited = set()

    if url in _visited or max_depth <= 0:
        return []
    _visited.add(url)

    html = fetch(url)
    if html is None:
        return []

    soup = BeautifulSoup(html, "html5lib")
    article = soup.find("article", id="article") or soup

    doc_ids = []
    sub_pages = []
    pub_pages = []

    for a_tag in article.find_all("a", href=True):
        href = a_tag["href"]

        # Direct docId link
        m = DOCID_RE.search(href)
        if m:
            doc_ids.append(m.group(1))
            continue

        # Library sub-page (same category)
        if LIBRARY_RE.search(href) and href not in _visited:
            full_url = WOL_BASE + href if href.startswith("/") else href
            if full_url not in _visited:
                sub_pages.append(full_url)
            continue

        # Publication TOC page
        m = SECTION_RE.search(href)
        if m:
            full_url = WOL_BASE + href if href.startswith("/") else href
            if full_url not in _visited:
                pub_pages.append(full_url)

    # Crawl library sub-pages recursively
    for sub_url in sub_pages:
        sub_ids = harvest_docids_from_library(sub_url, max_depth - 1, _visited)
        doc_ids.extend(sub_ids)

    # Crawl publication TOC pages (these have docId links directly)
    for pub_url in pub_pages:
        if pub_url in _visited:
            continue
        _visited.add(pub_url)
        pub_html = fetch(pub_url)
        if pub_html is None:
            continue
        pub_soup = BeautifulSoup(pub_html, "html5lib")
        pub_article = pub_soup.find("article", id="article")
        if pub_article is None:
            continue
        for a_tag in pub_article.find_all("a", href=True):
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

    return unique_ids


def harvest_all_library() -> list[str]:
    """Harvest docIds from all categories in the WOL library."""
    categories = [
        ("Watchtower", "faleleoleo-maluga"),
        ("Awake!", "ala-mai"),
        ("Books", "tusi"),
        ("Meeting", "tusi-mō-fakatasiga"),
        ("Ministry", "te-tou-galuega-talai"),
        ("Brochures", "polosiua-ki-te-tamā-tusi"),
    ]

    all_ids = []
    seen = set()
    visited_urls = set()

    for name, slug in categories:
        url = f"{WOL_BASE}/tvl/wol/library/r153/lp-vl/tusi-katoa/{slug}"
        print(f"\nCrawling {name} ({slug})...")
        ids = harvest_docids_from_library(url, max_depth=5, _visited=visited_urls)
        new_ids = [d for d in ids if d not in seen]
        for d in new_ids:
            seen.add(d)
        all_ids.extend(new_ids)
        print(f"  {name}: {len(new_ids)} new docIds ({len(ids)} total found)")

    print(f"\nTotal unique docIds across all categories: {len(all_ids)}")
    return all_ids


def is_metadata_paragraph(text: str) -> bool:
    """Detect boilerplate paragraphs (chapter headers, copyright, credits, TOC)."""
    t = text.strip()
    # Chapter/section headers: "CHAPTER 7", "MATAUPU E 7", "SECTION 3", etc.
    if re.match(r"^(CHAPTER|MATAUPU\s+E|SECTION|PART)\s+\d+$", t, re.IGNORECASE):
        return True
    # Copyright lines
    if re.match(r"^©\s*\d{4}", t):
        return True
    # Photo credits
    if t.lower().startswith("photo credit"):
        return True
    # Page/chapter index lines like "236Mataupu Fakaopoopo" or "PAGECHAPTER"
    if re.match(r"^\d+[A-Z]", t) and len(t) < 40:
        return True
    if t in ("PAGECHAPTER", "MATAUPUTE ITULAU"):
        return True
    return False


def extract_paragraphs(html: str) -> list[tuple[str, str]]:
    """Extract (data-pid, text) tuples from article paragraphs.

    Scoped to article#article to avoid footnote panel paragraphs.
    Removes footnotes (a.fn), cross-refs (a.b), and superscripts (sup).
    Filters out metadata paragraphs (chapter headers, copyright, credits).
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

        if text and not is_metadata_paragraph(text):
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

            # Skip very short pairs (headers, page numbers, etc.)
            if tvl_chars < 20 and en_chars < 20:
                continue

            # Skip extreme ratio pairs (likely pid misalignment)
            if en_chars > 0:
                ratio = tvl_chars / en_chars
                if ratio < 0.15 or ratio > 7.0:
                    continue

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
    parser.add_argument("--library", action="store_true",
                        help="Crawl entire WOL library (all categories)")
    parser.add_argument("--library-cat", type=str,
                        help="Crawl a single library category by slug")
    args = parser.parse_args()

    pub_code = None

    if args.pilot:
        doc_ids = PILOT_DOCIDS
        pub_code = "lv"
    elif args.library:
        doc_ids = harvest_all_library()
        if not doc_ids:
            print("No docIds found in library")
            sys.exit(1)
    elif args.library_cat:
        slug = args.library_cat
        url = f"{WOL_BASE}/tvl/wol/library/r153/lp-vl/tusi-katoa/{slug}"
        print(f"Crawling library category: {slug}")
        doc_ids = harvest_docids_from_library(url)
        if not doc_ids:
            print(f"No docIds found for category '{slug}'")
            sys.exit(1)
        print(f"Found {len(doc_ids)} docIds")
    elif args.pub:
        pub_code = args.pub
        doc_ids = harvest_docids_from_pub(pub_code)
        if not doc_ids:
            print(f"No docIds found for publication '{pub_code}'")
            sys.exit(1)
    elif args.docids:
        doc_ids = args.docids
    else:
        print("Specify --pilot, --pub <code>, --docids, --library, or --library-cat <slug>")
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
