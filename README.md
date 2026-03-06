# Tuvaluan-English Parallel Corpus: Scraping & Dataset Plan

## 0. Project goal

Build a HuggingFace-ready Tuvaluan↔English parallel corpus from JW.org and WOL content, producing artifacts suitable for:

1. **Machine translation** fine-tuning (tvl→en, en→tvl)
2. **Multilingual LLM fine-tuning** (instruction/chat format)
3. **Continued pretraining** on Tuvaluan text (monolingual)
4. **Evaluation benchmarks** (held-out verse-aligned test sets)

Tuvaluan (ISO 639-3: `tvl`) is a Polynesian language with ~11,000 speakers. It is mutually intelligible with Tokelauan. Existing NLP resources are extremely limited — JW content represents one of the largest available sources of parallel text.

### Prior art

- **JW300**: A parallel corpus covering 300+ languages from JW.org, widely used for low-resource MT. Our work extends this specifically for Tuvaluan with richer metadata and multiple output formats.
- **Christodoulopoulos Bible Corpus**: 100-language verse-aligned Bible corpus (XML). Does not include Tuvaluan.
- **FLORES+**: Meta's MT evaluation benchmark (200+ languages). May include Tuvaluan evaluation sentences.
- **jwsoup**: Python package for scraping JW Bible content (pip installable).

---

## 1. Fetching: Docker curl-impersonate + BeautifulSoup

### Why curl-impersonate is required

Both `jw.org` and `wol.jw.org` perform **TLS fingerprint detection**. Standard Python HTTP clients fail:

| Client | jw.org | wol.jw.org | Failure mode |
|---|---|---|---|
| `requests` | Timeout | Timeout | Read timeout after 30s |
| `httpx` (HTTP/2) | StreamReset | Intermittent (works 1st request, blocks after) | `RemoteProtocolError: StreamReset error_code:2` |
| `curl` (system) | Exit 92 | Exit 56 | HTTP/2 stream error / recv failure |
| **Docker curl-impersonate** | **200** | **200** | **Works reliably** |

The sites reset HTTP/2 streams when the TLS handshake doesn't match a known browser fingerprint. `curl-impersonate` mimics real browser TLS/HTTP handshakes, which passes the check.

### Docker setup

We use the pre-built Firefox Docker image (runs under Rosetta on Apple Silicon):

```bash
# Image already pulled:
docker pull lwthiker/curl-impersonate:0.6-ff

# Test:
docker run --rm lwthiker/curl-impersonate:0.6-ff \
  curl_ff117 -s -o /dev/null -w "HTTP %{http_code}\n" \
  "https://www.jw.org/tvl/sitemap.xml"
# → HTTP 200
```

The platform warning (`linux/amd64 does not match linux/arm64/v8`) is expected on Apple Silicon and does not affect functionality.

### Python integration

All scripts use `scripts/fetch.py`, which shells out to Docker curl-impersonate and returns HTML to BeautifulSoup:

```python
# scripts/fetch.py — shared fetcher
import subprocess, time
from bs4 import BeautifulSoup

DOCKER_IMAGE = "lwthiker/curl-impersonate:0.6-ff"
DOCKER_WRAPPER = "curl_ff117"
DELAY = 2  # seconds between requests

def fetch(url, timeout=30, retries=3):
    """Fetch via Docker curl-impersonate. Returns HTML string or None."""
    result = subprocess.run(
        ["docker", "run", "--rm", DOCKER_IMAGE, DOCKER_WRAPPER,
         "-s", "-L", "--max-time", str(timeout), url],
        capture_output=True, text=True, timeout=timeout + 10,
    )
    return result.stdout if result.returncode == 0 else None

def fetch_soup(url, parser="html5lib"):
    html = fetch(url)
    return BeautifulSoup(html, parser) if html else None
```

Rate limiting (2s delay) and exponential-backoff retries are built in. Raw HTML is saved to `data/raw/` for offline reprocessing.

### Performance

~4 seconds per chapter pair (2 fetches + parse) with Docker curl-impersonate, vs ~25 seconds with httpx when it intermittently worked. Full Bible scrape (1,189 chapters) estimated at ~80 minutes.

### Other endpoints tested

| Endpoint | Result |
|---|---|
| `b.jw-cdn.org/apis/pub-media/GETPUBMEDIALINKS` | Tuvaluan language codes `TVL`, `VL`, `TV` all return 400/404 — Tuvaluan is not in the CDN publication API |
| `www.jw.org/en/languages/` | StreamReset — blocked like other jw.org pages |
| Sitemap hreflang alternates | None present — 0/7,103 URLs have `<xhtml:link>` alternates |

---

## 2. Artifact structure

### 2.1 Directory layout

```
tv/
├── tv2en.md                       # URL pattern reference
├── README.md                      # This file
├── pyproject.toml                 # uv project config
├── curl-imp/                      # curl-impersonate setup
│   ├── curl-impersonate/          # cloned repo
│   ├── curl-impersonate-fetch-skill/  # Claude Code skill
│   ├── claude-code-curl-impersonate-guide.md
│   └── fetch-with-curl-impersonate.sh
├── data/
│   ├── raw/                       # Raw scraped HTML (not uploaded to HF)
│   │   ├── sitemap_tvl.xml        # Full sitemap (1.1MB, 7,103 URLs)
│   │   ├── sitemap_tvl.json       # Parsed + classified sitemap
│   │   ├── wol_tvl/               # WOL Tuvaluan pages (bible_{bookNo}_{ch}.html)
│   │   └── wol_en/                # WOL English pages
│   ├── aligned/                   # Verse/paragraph-aligned pairs (JSONL)
│   │   ├── bible_verses.jsonl     # Verse-level aligned Bible text
│   │   ├── articles.jsonl         # Article/paragraph-level aligned text
│   │   ├── daily_text.jsonl       # Date-keyed daily text pairs
│   │   └── publications.jsonl     # Publication chapter pairs
│   ├── hf_dataset/                # HuggingFace-ready Parquet files
│   │   ├── README.md              # HF dataset card
│   │   ├── bible/
│   │   │   ├── train.parquet
│   │   │   ├── validation.parquet
│   │   │   └── test.parquet
│   │   ├── articles/
│   │   │   └── train.parquet
│   │   ├── daily_text/
│   │   │   └── train.parquet
│   │   └── all/
│   │       ├── train.parquet
│   │       ├── validation.parquet
│   │       └── test.parquet
│   └── finetune/                  # LLM fine-tuning formats
│       ├── openai_chat.jsonl
│       ├── instruction.jsonl
│       └── monolingual_tvl.jsonl
├── scripts/
│   ├── fetch.py                   # Docker curl-impersonate fetcher (shared)
│   ├── scrape_sitemap.py          # Parse JW sitemap, classify URLs
│   ├── scrape_bible.py            # Scrape Bible chapters (verse-aligned)
│   ├── scrape_articles.py         # Scrape WOL articles by docId
│   ├── scrape_daily_text.py       # Scrape date-based daily text
│   ├── align.py                   # Align scraped content into pairs
│   ├── build_hf_dataset.py        # Convert aligned JSONL → Parquet
│   ├── build_finetune.py          # Convert aligned JSONL → fine-tuning formats
│   ├── quality.py                 # Quality filtering and validation
│   └── stats.py                   # Dataset statistics and reporting
└── logs/
    ├── scrape.log
    └── alignment.log
```

### 2.2 Raw data storage

Bible chapters are saved as raw HTML files keyed by book number and chapter:
`data/raw/wol_tvl/bible_{bookNo}_{chapter}.html`

The parsed sitemap is saved as JSON with URL classification:
`data/raw/sitemap_tvl.json`

---

## 3. Sitemap analysis (Experiment 1 — completed)

The Tuvaluan sitemap contains **7,103 URLs** (significantly more than the 1,310 initially estimated from earlier sitemap retrieval attempts that timed out and returned partial results).

### Category breakdown

| Category | Count | Notes |
|---|---|---|
| magazine | 2,489 | Largest non-Bible category |
| publication_index | 1,605 | TOC/index pages |
| bible_chapter | 1,189 | All 66 books confirmed |
| book | 499 | Book chapters/sections |
| bible_index | 290 | Bible navigation pages |
| brochure | 257 | Brochure sections |
| song | 227 | Song pages |
| video | 146 | Video pages (may have transcripts) |
| program | 95 | Convention/assembly programs |
| bible_book_toc | 66 | One per book |
| faq | 49 | Bible Q&A pages |
| news | 36 | News articles |
| bible_supplement | 34 | Appendix/supplemental material |
| about_jw | 32 | About pages |
| study_youth | 27 | Youth study content |
| misc_publication | 22 | Miscellaneous articles |
| help | 17 | Help/support pages |
| study_children | 8 | Children's content |
| study_hub | 4 | Study landing pages |
| study_science | 4 | Science topic pages |
| other | 5 | Home, search, what's new, all topics |

### Key finding: no hreflang alternates

The sitemap contains **zero** hreflang alternate links. This means we cannot use sitemap metadata for cross-language page pairing. We must rely entirely on:
- WOL docId swap (strongest)
- WOL bookNo/chapter numeric alignment (Bible)
- WOL date alignment (daily text / meetings)
- Issue code matching (magazines)
- URL pattern heuristics (everything else)

---

## 4. WOL Bible HTML structure (Experiment 2 — confirmed)

The WOL Bible page structure differs from what prior scrapers (jwsoup, crawl-for-parallel-corpora) documented for jw.org. The actual structure on WOL:

### Verse markup

```html
<article class="article bible html5 pub-nwt jwac showRuby ml-VL ms-ROMAN dir-ltr"
         data-lang="VL" dir="ltr" id="article" lang="tvl">
  <div class="scalableui">
    <header><h1>Kenese</h1></header>

    <p class="sb" data-pid="2" id="p2">
      <span class="v" id="v1-1-1-1">
        <span class="cl" data-vlid="vl0"><strong>1</strong> </span>
        I te kamataga ne faite ne te Atua a te lagi
        <a class="fn" data-fnid="1" href="...">*</a>
        mo te lalolagi.
        <a class="b" data-bid="1-1" href="...">+</a>
      </span>
    </p>

    <p class="sb" data-pid="3" id="p3">
      <span class="v" id="v1-1-2-1">
        <span class="vl">2 </span>
        A te lalolagi e seki foliga faka‵lei kae lavaki,...
      </span>
    </p>
  </div>
</article>
```

### Key selectors (WOL-specific, different from jw.org)

| Element | Selector | Purpose |
|---|---|---|
| Verse span | `span.v` | Contains one verse's text (NOT `span.verse`) |
| Verse ID | `id="v{bookNo}-{ch}-{verse}-{part}"` | Parseable verse reference |
| Verse number | `span.vl` or `span.cl > strong` | Leading number display |
| Footnote | `a.fn` | Remove before text extraction (NOT `a.footnoteLink`) |
| Cross-reference | `a.b` | Remove before text extraction (NOT `a.xrefLink`) |
| Paragraph | `p[data-pid]` | Numbered paragraph container |
| Article root | `article#article` | Main content container |
| Language tag | `article[data-lang="VL"]` | Confirms Tuvaluan content |

### Verse ID format

`v{bookNo}-{chapter}-{verse}-{part}` where:
- bookNo: 1–66 (Genesis–Revelation)
- chapter: chapter number
- verse: verse number
- part: usually 1; >1 for verses split across paragraphs (merge these)

### Extraction algorithm

```python
for v_span in soup.find_all("span", class_="v"):
    vid = v_span.get("id", "")
    m = re.match(r"v(\d+)-(\d+)-(\d+)-(\d+)", vid)
    verse_no = int(m.group(3))

    # Remove footnotes and cross-references
    for unwanted in v_span.find_all("a", class_=["fn", "b"]):
        unwanted.decompose()
    for sup in v_span.find_all("sup"):
        sup.decompose()

    text = v_span.get_text(strip=True)
    text = re.sub(r"^\d+\s*", "", text)  # strip leading verse number
```

---

## 5. Bible pilot results (Experiment 2 — completed)

Scraped 3 chapters (Genesis 1, Psalm 19, John 3) in both Tuvaluan and English via WOL.

### Results

| Chapter | TVL verses | EN verses | Aligned pairs |
|---|---|---|---|
| Genesis 1 | 31 | 31 | 31 |
| Psalm 19 | 15 | 15 | 15 |
| John 3 | 36 | 36 | 36 |
| **Total** | **82** | **82** | **82** |

**100% alignment** — every verse matched 1:1.

### Sample pairs

| ID | Tuvaluan | English | Ratio |
|---|---|---|---|
| `bible_1_1_1` | I te kamataga ne faite ne te Atua a te lagimo te lalolagi. | In the beginning God created the heavens and the earth. | 1.05 |
| `bible_19_19_0` | Ki te takitaki o te kau fai pese. Ko te pese a Tavita. | To the director. A melody of David. | 1.54 |
| `bible_43_3_16` | (John 3:16 — full verse) | (John 3:16 — full verse) | 1.19 |

### Length ratio statistics

- **Average**: 1.21 (Tuvaluan text is ~21% longer than English)
- **Range**: 0.83 – 1.64
- **All within quality threshold** (0.3 – 3.0)

This ratio is consistent with Polynesian languages, which tend to use more function words and particles than English.

### Average text length

- TVL: 144 chars/verse
- EN: 121 chars/verse

---

## 6. Output formats (HuggingFace + fine-tuning)

### 6.1 HuggingFace parallel corpus (primary artifact)

**Format**: Parquet
**Feature type**: Flat columns (not nested `Translation` feature — flat is more widely compatible and allows richer metadata)

#### Schema

| Column | Type | Description |
|---|---|---|
| `id` | `string` | Unique row identifier: `{content_type}_{alignment_key}` |
| `tvl` | `string` | Tuvaluan text |
| `en` | `string` | English text |
| `content_type` | `string` | One of: `bible_verse`, `article_paragraph`, `daily_text`, `publication_section` |
| `domain` | `string` | One of: `bible`, `magazine`, `book`, `brochure`, `daily_text`, `faq`, `news`, `song`, `meeting_workbook` |
| `alignment_method` | `string` | How the pair was aligned: `verse_number`, `doc_id`, `date`, `paragraph_position`, `pub_code` |
| `alignment_confidence` | `float32` | 0.0–1.0 confidence score |
| `doc_id` | `string` | WOL document ID (when available; strongest cross-language key) |
| `source_url_tvl` | `string` | Source URL for Tuvaluan text |
| `source_url_en` | `string` | Source URL for English text |
| `book_num` | `int32` | Bible book number 1–66 (null for non-Bible) |
| `chapter` | `int32` | Bible chapter (null for non-Bible) |
| `verse` | `int32` | Bible verse (null for non-Bible) |
| `date` | `string` | ISO date YYYY-MM-DD (for daily text; null otherwise) |
| `pub_code` | `string` | WOL publication code (e.g., `lv`, `bt`, `T-31`; null if n/a) |
| `tvl_chars` | `int32` | Character count of Tuvaluan text |
| `en_chars` | `int32` | Character count of English text |
| `length_ratio` | `float32` | `tvl_chars / en_chars` (for quality filtering) |

#### HuggingFace dataset card YAML (README.md frontmatter)

```yaml
---
language:
  - tvl
  - en
license: cc-by-4.0
task_categories:
  - translation
task_ids:
  - translation-other-tvl-en
pretty_name: "Tuvaluan-English Parallel Corpus (JW)"
size_categories:
  - 10K<n<100K
tags:
  - parallel-corpus
  - low-resource
  - polynesian
  - bible
  - machine-translation
configs:
  - config_name: bible
    data_files:
      - split: train
        path: "bible/train.parquet"
      - split: validation
        path: "bible/validation.parquet"
      - split: test
        path: "bible/test.parquet"
  - config_name: articles
    data_files:
      - split: train
        path: "articles/train.parquet"
  - config_name: daily_text
    data_files:
      - split: train
        path: "daily_text/train.parquet"
  - config_name: all
    default: true
    data_files:
      - split: train
        path: "all/train.parquet"
      - split: validation
        path: "all/validation.parquet"
      - split: test
        path: "all/test.parquet"
---
```

#### Split strategy

For a low-resource language with limited data, splits must be chosen carefully:

- **Bible config**: 80/10/10 split by book (not random verse sampling, to avoid data leakage across adjacent verses)
  - Test: held-out books (e.g., Ruth, Philemon, Jude — short books for manageable eval)
  - Validation: another set of held-out books
  - Train: remaining books
- **All config**: same book-based split for Bible portion; articles/daily_text/publications go to train only (too small to split further)
- **Articles, daily_text configs**: train only (no split — not enough data)

### 6.2 OpenAI chat completion format (for fine-tuning)

```jsonl
{"messages": [{"role": "system", "content": "You are a translator between Tuvaluan and English. Translate the following text accurately."}, {"role": "user", "content": "Translate from Tuvaluan to English:\n\nKo lagi e fakailoa te manuia o te Atua"}, {"role": "assistant", "content": "The heavens declare the glory of God"}]}
{"messages": [{"role": "system", "content": "You are a translator between Tuvaluan and English. Translate the following text accurately."}, {"role": "user", "content": "Translate from English to Tuvaluan:\n\nThe heavens declare the glory of God"}, {"role": "assistant", "content": "Ko lagi e fakailoa te manuia o te Atua"}]}
```

Both directions (tvl→en and en→tvl) are generated from each pair. System prompt is kept consistent.

### 6.3 Alpaca-style instruction format

```jsonl
{"instruction": "Translate the following Tuvaluan text to English.", "input": "Ko lagi e fakailoa te manuia o te Atua", "output": "The heavens declare the glory of God", "metadata": {"content_type": "bible_verse", "book_num": 19, "chapter": 19, "verse": 1}}
```

### 6.4 Monolingual Tuvaluan (continued pretraining)

Dolma-compatible JSONL for language model pretraining on Tuvaluan:

```jsonl
{"id": "jw-tvl-bible-19-19", "text": "Ko lagi e fakailoa te manuia o te Atua; ko te ato e fakailoa te galuega a ona lima.", "source": "jw.org", "added": "2026-03-06", "metadata": {"lang": "tvl", "domain": "bible", "content_type": "bible_chapter", "url": "https://www.jw.org/tvl/tusi/tusi-tapu/nwt/tusi/salamo/19/"}}
```

For monolingual, text is at the chapter or article level (not verse level) to provide more context per document.

---

## 7. Scraping strategy

### 7.1 Scraping priority order

Content types are prioritized by alignment confidence and volume. Estimated pairs updated based on sitemap analysis (7,103 URLs):

| Priority | Content type | Alignment method | Est. pairs | Confidence |
|---|---|---|---|---|
| 1 | Bible chapters (1,189 ch) | verse number (bookNo + chapter + verse) | ~25,000 verses | Very high |
| 2 | WOL articles by docId | docId swap | ~500–2,000 articles | Very high |
| 3 | Daily text | date alignment | ~365/year × N years | Very high |
| 4 | Magazines (2,489 pages) | issue code + article position | ~1,000–2,000 articles | Medium-high |
| 5 | Books (499 pages) | pubCode + chapter / docId | ~200–500 sections | High |
| 6 | Brochures (257 pages) | title slug / docId | ~100–300 sections | Medium |
| 7 | FAQ/study (92 pages) | docId / slug match | ~50–100 pages | Medium |
| 8 | Songs (227 pages) | song number | ~200 songs | High (lyrics) |
| 9 | News (36 pages) | date + region match | ~30 articles | Medium |
| 10 | Help (17 pages) | path match | ~15 pages | Medium |

### 7.2 Bible scraping (Priority 1)

**Source**: WOL Bible pages (numeric bookNo URLs avoid slug mapping)
**Script**: `scripts/scrape_bible.py`

```bash
uv run python scripts/scrape_bible.py --pilot    # 3 chapters
uv run python scripts/scrape_bible.py --book 1    # Genesis only
uv run python scripts/scrape_bible.py --full      # all 66 books
```

**URL pattern**:
- TVL: `wol.jw.org/tvl/wol/b/r153/lp-vl/nwt/{bookNo}/{chapter}`
- EN: `wol.jw.org/en/wol/b/r1/lp-e/nwt/{bookNo}/{chapter}`

**Resumable**: tracks completed chapter IDs in the output JSONL; skips already-scraped chapters on restart.

### 7.3 WOL articles (Priority 2)

**Source**: WOL document pages by docId
**Script**: `scripts/scrape_articles.py` (planned)

**DocId harvesting sources**:
- Publication TOC pages: `wol.jw.org/tvl/wol/publication/r153/lp-vl/{pubCode}`
- Library browse: `wol.jw.org/tvl/wol/library/r153/lp-vl/tusi-katoa`
- Links found in other scraped pages

### 7.4 Daily text (Priority 3)

**Source**: WOL daily text pages
**Script**: `scripts/scrape_daily_text.py` (planned)

**URL pattern**:
- TVL: `wol.jw.org/tvl/wol/h/r153/lp-vl/{yyyy}/{m}/{d}`
- EN: `wol.jw.org/en/wol/h/r1/lp-e/{yyyy}/{m}/{d}`

### 7.5 Rate limiting and politeness

- **Delay**: 2 seconds between requests (built into `fetch.py`)
- **Respect robots.txt**: Avoid disallowed paths (`/choose-language`, query params like `contentLanguageFilter`)
- **Cache**: Raw HTML saved locally — never re-fetch a page already on disk
- **Resume**: Progress tracked by checking existing output IDs

---

## 8. Alignment strategy

### 8.1 Alignment levels

| Level | Use case | Method |
|---|---|---|
| Verse | Bible text | Book number + chapter + verse number |
| Paragraph | Articles, publications | Position within document (paragraph index) |
| Document | Short articles, FAQ | Whole document as one unit |
| Date | Daily text, meetings | Calendar date |

### 8.2 Paragraph alignment for articles

For articles aligned by docId, paragraph-level alignment uses position matching:

1. Extract ordered paragraphs from both language versions
2. If paragraph counts match: align 1:1
3. If counts differ: use length-ratio heuristics and fall back to document-level alignment
4. Flag mismatched documents for manual review

### 8.3 Quality filtering

After alignment, apply quality filters:

| Filter | Threshold | Rationale |
|---|---|---|
| Empty text | Drop if either side is empty | Broken scrape or missing translation |
| Length ratio | Drop if `tvl_chars/en_chars` outside 0.3–3.0 | Misalignment signal |
| Duplicate detection | Drop exact duplicates by text hash | Deduplicate repeated content |
| Language detection | Flag if detected language ≠ expected | Catch scraping errors |
| Min length | Drop if either side < 10 characters | Too short to be useful |
| Max length | Truncate at 4096 characters per side | Practical limit for most models |

### 8.4 Alignment confidence scoring

Each pair gets a confidence score based on:

- `1.0` — Verse-aligned Bible text, date-aligned daily text
- `0.9` — DocId-matched article with matching paragraph count
- `0.8` — DocId-matched article with paragraph count mismatch (position-aligned)
- `0.7` — PubCode-matched publication section
- `0.6` — Issue code + article position match
- `0.5` — Title/slug match
- `0.4` — Sitemap/hreflang match only

---

## 9. Quality considerations

### 9.1 Domain bias

JW content is predominantly religious text. This creates a well-known domain bias:

- **Register**: Formal, instructional, ecclesiastical
- **Vocabulary**: Religious terminology overrepresented; everyday/colloquial Tuvaluan underrepresented
- **Sentence structure**: Translation-influenced (translated from English originals; may not reflect natural Tuvaluan syntax)

**Mitigations documented in metadata**:
- The `domain` column allows downstream users to filter by content type
- The `content_type` column distinguishes Bible from magazine from FAQ etc.
- Users should be warned in the dataset card that this is religious-domain data

### 9.2 Translation directionality

Most JW content is originally written in English and translated into Tuvaluan. This means:
- The Tuvaluan text may exhibit "translationese" (English-influenced syntax)
- For training tvl→en models, this is fine (translationese source → natural target)
- For training en→tvl models, the "natural" Tuvaluan target may itself be unnatural

### 9.3 Deduplication

Religious texts contain significant repetition (cross-references, repeated phrases, liturgical formulas). Deduplication strategy:
- **Exact dedup**: Hash-based on concatenated `tvl+en` text
- **Near dedup**: MinHash/LSH for detecting paraphrased duplicates
- **Cross-split dedup**: Ensure test/validation pairs don't appear in training (critical for Bible verse dedup — adjacent verses may share content)

---

## 10. Experiments log

### Experiment 1: Sitemap enumeration — DONE

**Goal**: Parse `jw.org/tvl/sitemap.xml` and enumerate all Tuvaluan URLs.

**Method**: Fetched sitemap via Docker curl-impersonate (1.1MB XML), parsed all `<loc>` entries, classified by URL pattern using regex classifiers from `tv2en.md` section 10.

**Result**: **7,103 URLs** classified into 25 categories. No hreflang alternates present. See section 3 above for full breakdown.

**Output**: `data/raw/sitemap_tvl.xml`, `data/raw/sitemap_tvl.json`

---

### Experiment 2: Bible verse extraction (pilot) — DONE

**Goal**: Scrape 3 Bible chapters (Genesis 1, Psalm 19, John 3) in both Tuvaluan and English. Verify verse-level alignment works.

**Method**: Fetched WOL Bible pages via Docker curl-impersonate, parsed with BeautifulSoup (html5lib), extracted verses via `span.v` elements, aligned by verse number.

**Result**: **82/82 verses aligned** (100%). TVL/EN length ratio avg 1.21 (range 0.83–1.64). See section 5 above for details.

**Output**: `data/aligned/bible_verses.jsonl` (82 pairs)

---

### Experiment 3: WOL article extraction (pilot) — PENDING

**Goal**: Scrape 5 WOL articles by docId in both languages. Verify paragraph alignment works.

---

### Experiment 4: Daily text extraction (pilot) — PENDING

**Goal**: Scrape 7 consecutive daily texts in both languages. Verify date alignment works.

---

### Experiment 5: Full Bible scrape — PENDING

**Goal**: Scrape entire NWT Bible (all 66 books, 1,189 chapters) in both languages.

**Depends on**: Experiment 2 (verified)

**Estimated time**: ~80 minutes (4s/chapter × 1,189 chapters × 2 languages)

---

### Experiment 6: Full docId harvest + article scrape — PENDING

**Goal**: Harvest all accessible docIds from WOL library browse pages, then scrape all articles in both languages.

**Depends on**: Experiment 3

---

### Experiment 7: Dataset assembly — PENDING

**Goal**: Combine all aligned data into HuggingFace Parquet files with proper splits, metadata, and dataset card.

**Depends on**: Experiments 5 + 6

---

## 11. Tools and dependencies

### Python (managed with uv)

```toml
# pyproject.toml
[project]
dependencies = [
    "beautifulsoup4",
    "html5lib",
    "httpx[http2]",  # kept as fallback; primary fetching via Docker
    "lxml",
    "requests",      # kept as fallback
    "tqdm",
]
```

```bash
uv add pandas pyarrow datasets lingua-py  # add when needed for dataset assembly
```

### System dependencies

- **Docker Desktop** — required for curl-impersonate
- **Docker image**: `lwthiker/curl-impersonate:0.6-ff` (Firefox 117 fingerprint, linux/amd64 via Rosetta on Apple Silicon)
- **Python 3.14** via Homebrew

---

## 12. Estimated dataset size

Updated estimates based on sitemap analysis (7,103 URLs vs original 1,310 estimate):

| Content type | Sitemap URLs | Est. pairs | Avg chars/pair | Est. total chars |
|---|---|---|---|---|
| Bible verses | 1,189 chapters | ~25,000 | ~265 (confirmed) | ~6.6M |
| Magazines | 2,489 pages | ~1,000–2,000 | ~500 | ~0.5M–1M |
| Books | 499 pages | ~200–500 | ~1,000 | ~0.2M–0.5M |
| Brochures | 257 pages | ~100–300 | ~500 | ~0.05M–0.15M |
| Songs | 227 pages | ~200 | ~200 | ~0.04M |
| WOL articles (docId) | N/A (harvest needed) | ~500–2,000 | ~500 | ~0.25M–1M |
| Daily text | N/A (date range) | ~1,000–2,000 | ~300 | ~0.3M–0.6M |
| Other (FAQ, news, etc.) | ~344 pages | ~100–300 | ~300 | ~0.03M–0.09M |
| **Total** | **7,103+** | **~28,000–32,000** | — | **~8M–10M chars** |

---

## 13. HuggingFace upload plan

1. Create dataset repo: `{username}/tuvaluan-english-parallel-jw`
2. Upload Parquet files organized by config
3. Include comprehensive dataset card with:
   - Language description and typological notes
   - Data collection methodology
   - Alignment strategy documentation
   - Known limitations (domain bias, translationese)
   - Suggested usage and citation
   - License information
4. Use `datasets` library `push_to_hub()` for upload
5. Verify dataset loads correctly: `datasets.load_dataset("{username}/tuvaluan-english-parallel-jw")`

---

## 14. Answered questions

- [x] **Does the JW.org Tuvaluan sitemap include hreflang alternates?** No — 0/7,103 URLs have alternates. Must use WOL-based alignment.
- [x] **What is the WOL Bible verse HTML structure?** `span.v` with `id="v{bookNo}-{ch}-{verse}-{part}"`, footnotes as `a.fn`, cross-refs as `a.b`. Different from jw.org's `span.verse` / `a.footnoteLink` / `a.xrefLink`.
- [x] **Does the CDN publication API support Tuvaluan?** No — language codes TVL, VL, TV all return 400/404.
- [x] **Can standard Python HTTP clients access JW.org/WOL?** No — TLS fingerprint detection blocks requests, httpx, and system curl. Docker curl-impersonate required.
- [x] **How many Tuvaluan pages exist?** 7,103 (not 1,310 as initially estimated from partial sitemap).
- [x] **What is the TVL/EN length ratio for Bible text?** Average 1.21 (TVL ~21% longer), range 0.83–1.64.

## 15. Open questions

- [ ] How many WOL docIds actually have Tuvaluan translations? (Need to discover via scraping)
- [ ] Are there additional WOL Bible translation codes beyond `nwt` for Tuvaluan?
- [ ] What date range of daily text content exists in Tuvaluan?
- [ ] Should songs/lyrics be included or excluded? (Different text type; may confuse MT models)
- [ ] Should we include a Tokelauan subset as a related-language augmentation?
- [ ] What is the exact `wtlocale` value for Tuvaluan `open` links? (`TVL` vs `VL`)
