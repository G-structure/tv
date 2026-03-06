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

## 1. Artifact structure

### 1.1 Directory layout

```
tv/
├── tv2en.md                    # URL pattern reference (existing)
├── tvenscrape.md               # This file
├── data/
│   ├── raw/                    # Raw scraped HTML/text (not uploaded to HF)
│   │   ├── jw_tvl/             # JW.org Tuvaluan pages
│   │   ├── jw_en/              # JW.org English pages
│   │   ├── wol_tvl/            # WOL Tuvaluan pages
│   │   └── wol_en/             # WOL English pages
│   ├── aligned/                # Intermediate aligned pairs (JSONL)
│   │   ├── bible_verses.jsonl  # Verse-level aligned Bible text
│   │   ├── articles.jsonl      # Article/paragraph-level aligned text
│   │   ├── daily_text.jsonl    # Date-keyed daily text pairs
│   │   └── publications.jsonl  # Publication chapter pairs
│   ├── hf_dataset/             # HuggingFace-ready Parquet files
│   │   ├── README.md           # HF dataset card
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
│   └── finetune/               # LLM fine-tuning formats
│       ├── openai_chat.jsonl   # OpenAI chat completion format
│       ├── instruction.jsonl   # Alpaca-style instruction format
│       └── monolingual_tvl.jsonl  # Tuvaluan-only for continued pretraining
├── scripts/
│   ├── scrape_sitemap.py       # Parse JW sitemap, enumerate URLs
│   ├── scrape_bible.py         # Scrape Bible chapters (verse-aligned)
│   ├── scrape_articles.py      # Scrape WOL articles by docId
│   ├── scrape_daily_text.py    # Scrape date-based daily text
│   ├── align.py                # Align scraped content into pairs
│   ├── build_hf_dataset.py     # Convert aligned JSONL → Parquet + dataset card
│   ├── build_finetune.py       # Convert aligned JSONL → fine-tuning formats
│   ├── quality.py              # Quality filtering and validation
│   └── stats.py                # Dataset statistics and reporting
└── logs/
    ├── scrape.log              # Scraping progress/errors
    └── alignment.log           # Alignment decisions/failures
```

### 1.2 Raw data storage

Each scraped page is saved as a JSON file keyed by its alignment anchor:

```json
{
  "url": "https://wol.jw.org/tvl/wol/d/r153/lp-vl/1102008070",
  "lang": "tvl",
  "doc_id": "1102008070",
  "content_type": "article",
  "title": "E ‵Tau o Faka‵malu te Fakaipoipoga",
  "html": "<article>...</article>",
  "text": "cleaned plain text...",
  "paragraphs": ["paragraph 1...", "paragraph 2..."],
  "scraped_at": "2026-03-06T00:00:00Z",
  "http_status": 200
}
```

For Bible content, the raw format includes verse-level segmentation:

```json
{
  "url": "https://www.jw.org/tvl/tusi/tusi-tapu/nwt/tusi/salamo/19/",
  "lang": "tvl",
  "book_num": 19,
  "book_name": "salamo",
  "chapter": 19,
  "content_type": "bible_chapter",
  "verses": {
    "1": "Ko lagi e fakailoa te manuia o te Atua...",
    "2": "Aso taki tasi e tuku atu te kupu...",
    "...": "..."
  },
  "scraped_at": "2026-03-06T00:00:00Z"
}
```

---

## 2. Output formats (HuggingFace + fine-tuning)

### 2.1 HuggingFace parallel corpus (primary artifact)

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

### 2.2 OpenAI chat completion format (for fine-tuning)

```jsonl
{"messages": [{"role": "system", "content": "You are a translator between Tuvaluan and English. Translate the following text accurately."}, {"role": "user", "content": "Translate from Tuvaluan to English:\n\nKo lagi e fakailoa te manuia o te Atua"}, {"role": "assistant", "content": "The heavens declare the glory of God"}]}
{"messages": [{"role": "system", "content": "You are a translator between Tuvaluan and English. Translate the following text accurately."}, {"role": "user", "content": "Translate from English to Tuvaluan:\n\nThe heavens declare the glory of God"}, {"role": "assistant", "content": "Ko lagi e fakailoa te manuia o te Atua"}]}
```

Both directions (tvl→en and en→tvl) are generated from each pair. System prompt is kept consistent.

### 2.3 Alpaca-style instruction format

```jsonl
{"instruction": "Translate the following Tuvaluan text to English.", "input": "Ko lagi e fakailoa te manuia o te Atua", "output": "The heavens declare the glory of God", "metadata": {"content_type": "bible_verse", "book_num": 19, "chapter": 19, "verse": 1}}
```

### 2.4 Monolingual Tuvaluan (continued pretraining)

Dolma-compatible JSONL for language model pretraining on Tuvaluan:

```jsonl
{"id": "jw-tvl-bible-19-19", "text": "Ko lagi e fakailoa te manuia o te Atua; ko te ato e fakailoa te galuega a ona lima.", "source": "jw.org", "added": "2026-03-06", "metadata": {"lang": "tvl", "domain": "bible", "content_type": "bible_chapter", "url": "https://www.jw.org/tvl/tusi/tusi-tapu/nwt/tusi/salamo/19/"}}
```

For monolingual, text is at the chapter or article level (not verse level) to provide more context per document.

---

## 3. Scraping strategy

### 3.1 Scraping priority order

Content types are prioritized by alignment confidence and volume:

| Priority | Content type | Alignment method | Est. pairs | Confidence |
|---|---|---|---|---|
| 1 | Bible chapters | verse number (bookNo + chapter + verse) | ~25,000 verses | Very high |
| 2 | WOL articles by docId | docId swap | ~500–2,000 articles | Very high |
| 3 | Daily text | date alignment | ~365/year × N years | Very high |
| 4 | Publications by pubCode | pubCode + chapter | ~100–500 sections | High |
| 5 | Magazines by issue code | issue code + article position | ~100–300 articles | Medium-high |
| 6 | Brochures/books | title slug match | ~50–200 sections | Medium |
| 7 | FAQ/study | sitemap hreflang | ~50–100 pages | Medium |
| 8 | News | date + region match | ~10–50 articles | Medium |
| 9 | Songs | song number | ~150 songs | High (but lyrics, not prose) |
| 10 | Help pages | path match | ~20–50 pages | Medium |

### 3.2 Scraping approach by content type

#### Bible (Priority 1)

**Source**: JW.org Bible chapter pages
**Method**:
1. Enumerate all 66 books × chapters from the Bible book index at `jw.org/tvl/tusi/tusi-tapu/nwt/tusi-i-te-tusi-tapu/`
2. For each chapter, fetch both Tuvaluan and English pages
3. Parse verse-level content using CSS selector `span.verse`
4. Remove footnotes (`a.footnoteLink`), cross-references (`a.xrefLink`), and paragraph breaks (`span.parabreak`)
5. Align by verse number (universal across languages)

**Tuvaluan URL**: `jw.org/tvl/tusi/tusi-tapu/nwt/tusi/{book-slug}/{chapter}/`
**English URL**: `jw.org/en/library/bible/nwt/books/{book-slug}/{chapter}/`

**Book slug mapping**: Build a lookup table from Tuvaluan book slug → WOL book number → English book slug. The WOL `binav` page provides numeric book numbers.

**Alternative source**: WOL Bible pages use numeric bookNo directly:
- TVL: `wol.jw.org/tvl/wol/b/r153/lp-vl/nwt/{bookNo}/{chapter}`
- EN: `wol.jw.org/en/wol/b/r1/lp-e/nwt/{bookNo}/{chapter}`

This avoids the slug mapping problem entirely.

#### WOL articles (Priority 2)

**Source**: WOL document pages
**Method**:
1. Harvest docIds from WOL library browse pages and publication TOCs
2. For each docId, fetch both language versions via swap bundle
3. Parse article content (main body text, paragraphs)
4. Align at paragraph level by position within the document

**Tuvaluan URL**: `wol.jw.org/tvl/wol/d/r153/lp-vl/{docId}`
**English URL**: `wol.jw.org/en/wol/d/r1/lp-e/{docId}`

**DocId harvesting sources**:
- Publication TOC pages: `wol.jw.org/tvl/wol/publication/r153/lp-vl/{pubCode}`
- Library browse: `wol.jw.org/tvl/wol/library/r153/lp-vl/tusi-katoa`
- Links found in other scraped pages

#### Daily text (Priority 3)

**Source**: WOL daily text pages
**Method**:
1. Enumerate dates over a known range (e.g., 2020-01-01 to 2026-03-05)
2. Fetch both language versions
3. Align by date (universal key)

**Tuvaluan URL**: `wol.jw.org/tvl/wol/h/r153/lp-vl/{yyyy}/{m}/{d}`
**English URL**: `wol.jw.org/en/wol/h/r1/lp-e/{yyyy}/{m}/{d}`

### 3.3 HTML parsing details

Based on existing JW.org scrapers (jwsoup, crawl-for-parallel-corpora):

**Bible pages**:
- Content container: `<span class="verse">` contains verse text
- Verse numbers: `<sup>` or `<span class="verseNum">` within verse spans
- Remove before extracting text:
  - `a.footnoteLink` — footnote references
  - `a.xrefLink` — cross-references
  - `span.parabreak` — paragraph break markers

**WOL article pages**:
- Content is in the main article body (semantic HTML5 `<article>` or similar container)
- Paragraphs are standard `<p>` elements
- Numbered paragraphs may have `data-pid` attributes

**Parser**: BeautifulSoup4 with `html5lib` backend (handles malformed HTML gracefully)

### 3.4 Rate limiting and politeness

- **Delay**: 1–2 seconds between requests
- **Respect robots.txt**: Avoid disallowed paths (`/choose-language`, query params like `contentLanguageFilter`)
- **User-Agent**: Identify as a research crawler
- **Batch by language**: Scrape all Tuvaluan pages first, then all English pages (reduces interleaving load)
- **Cache**: Store raw HTML locally to avoid re-fetching
- **Resume**: Track progress in a state file; support resumption after interruption

---

## 4. Alignment strategy

### 4.1 Alignment levels

| Level | Use case | Method |
|---|---|---|
| Verse | Bible text | Book number + chapter + verse number |
| Paragraph | Articles, publications | Position within document (paragraph index) |
| Document | Short articles, FAQ | Whole document as one unit |
| Date | Daily text, meetings | Calendar date |

### 4.2 Paragraph alignment for articles

For articles aligned by docId, paragraph-level alignment uses position matching:

1. Extract ordered paragraphs from both language versions
2. If paragraph counts match: align 1:1
3. If counts differ: use length-ratio heuristics and fall back to document-level alignment
4. Flag mismatched documents for manual review

### 4.3 Quality filtering

After alignment, apply quality filters:

| Filter | Threshold | Rationale |
|---|---|---|
| Empty text | Drop if either side is empty | Broken scrape or missing translation |
| Length ratio | Drop if `tvl_chars/en_chars` outside 0.3–3.0 | Misalignment signal |
| Duplicate detection | Drop exact duplicates by text hash | Deduplicate repeated content |
| Language detection | Flag if detected language ≠ expected | Catch scraping errors |
| Min length | Drop if either side < 10 characters | Too short to be useful |
| Max length | Truncate at 4096 characters per side | Practical limit for most models |

### 4.4 Alignment confidence scoring

Each pair gets a confidence score based on:

- `1.0` — Verse-aligned Bible text, date-aligned daily text
- `0.9` — DocId-matched article with matching paragraph count
- `0.8` — DocId-matched article with paragraph count mismatch (position-aligned)
- `0.7` — PubCode-matched publication section
- `0.6` — Issue code + article position match
- `0.5` — Title/slug match
- `0.4` — Sitemap/hreflang match only

---

## 5. Quality considerations

### 5.1 Domain bias

JW content is predominantly religious text. This creates a well-known domain bias:

- **Register**: Formal, instructional, ecclesiastical
- **Vocabulary**: Religious terminology overrepresented; everyday/colloquial Tuvaluan underrepresented
- **Sentence structure**: Translation-influenced (translated from English originals; may not reflect natural Tuvaluan syntax)

**Mitigations documented in metadata**:
- The `domain` column allows downstream users to filter by content type
- The `content_type` column distinguishes Bible from magazine from FAQ etc.
- Users should be warned in the dataset card that this is religious-domain data

### 5.2 Translation directionality

Most JW content is originally written in English and translated into Tuvaluan. This means:
- The Tuvaluan text may exhibit "translationese" (English-influenced syntax)
- For training tvl→en models, this is fine (translationese source → natural target)
- For training en→tvl models, the "natural" Tuvaluan target may itself be unnatural

### 5.3 Deduplication

Religious texts contain significant repetition (cross-references, repeated phrases, liturgical formulas). Deduplication strategy:
- **Exact dedup**: Hash-based on concatenated `tvl+en` text
- **Near dedup**: MinHash/LSH for detecting paraphrased duplicates
- **Cross-split dedup**: Ensure test/validation pairs don't appear in training (critical for Bible verse dedup — adjacent verses may share content)

---

## 6. Scraping experiments log

### Experiment 1: Sitemap enumeration

**Goal**: Parse `jw.org/tvl/sitemap.xml` and enumerate all 1,310 Tuvaluan URLs.

**Method**: Fetch sitemap XML, extract all `<loc>` entries, classify by URL pattern (Bible, article, magazine, etc.) using regex classifiers from `tv2en.md` section 10.

**Status**: Pending

---

### Experiment 2: Bible verse extraction (pilot)

**Goal**: Scrape 3 Bible chapters (Genesis 1, Psalm 19, John 3) in both Tuvaluan and English. Verify verse-level alignment works.

**Method**:
1. Fetch WOL Bible pages: `wol.jw.org/{lang}/wol/b/{rCode}/{lpCode}/nwt/{bookNo}/{chapter}`
2. Parse verse content with BeautifulSoup
3. Align by verse number
4. Output to `data/aligned/bible_verses.jsonl`

**Status**: Pending

---

### Experiment 3: WOL article extraction (pilot)

**Goal**: Scrape 5 WOL articles by docId in both languages. Verify paragraph alignment works.

**Method**:
1. Pick 5 known docIds (e.g., `1102008070`, `1102015820`)
2. Fetch both language versions
3. Extract paragraphs
4. Align by position
5. Output to `data/aligned/articles.jsonl`

**Status**: Pending

---

### Experiment 4: Daily text extraction (pilot)

**Goal**: Scrape 7 consecutive daily texts in both languages. Verify date alignment works.

**Method**:
1. Enumerate 2025-01-01 to 2025-01-07
2. Fetch WOL daily text pages for both languages
3. Extract text content
4. Align by date
5. Output to `data/aligned/daily_text.jsonl`

**Status**: Pending

---

### Experiment 5: Full Bible scrape

**Goal**: Scrape entire NWT Bible (all 66 books, all chapters) in both languages.

**Depends on**: Experiment 2 results (verify parsing works)

**Status**: Pending

---

### Experiment 6: Full docId harvest + article scrape

**Goal**: Harvest all accessible docIds from WOL library browse pages, then scrape all articles in both languages.

**Depends on**: Experiment 3 results (verify article parsing works)

**Status**: Pending

---

### Experiment 7: Dataset assembly

**Goal**: Combine all aligned data into HuggingFace Parquet files with proper splits, metadata, and dataset card.

**Depends on**: Experiments 5 + 6 completion

**Status**: Pending

---

## 7. Tools and dependencies

```
python >= 3.10
requests          # HTTP fetching
beautifulsoup4    # HTML parsing
html5lib          # HTML5 parser backend
lxml              # Fast XML parsing (for sitemaps)
pandas            # Data manipulation
pyarrow           # Parquet file creation
datasets          # HuggingFace datasets library
lingua-py         # Language detection (quality filtering)
tqdm              # Progress bars
```

---

## 8. Estimated dataset size

| Content type | Est. pairs | Avg chars/pair | Est. total chars |
|---|---|---|---|
| Bible verses | ~25,000 | ~200 | ~5M |
| WOL articles | ~500–2,000 | ~500 | ~0.5M–1M |
| Daily text | ~1,000–2,000 | ~300 | ~0.3M–0.6M |
| Publications | ~100–500 | ~1,000 | ~0.1M–0.5M |
| Magazines | ~100–300 | ~500 | ~0.05M–0.15M |
| Other | ~100–300 | ~300 | ~0.03M–0.09M |
| **Total** | **~27,000–30,000** | — | **~6M–7.5M chars** |

This is a small but valuable dataset — comparable to other low-resource parallel corpora used for MT research.

---

## 9. HuggingFace upload plan

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

## 10. Open questions

- [ ] Does the JW.org Tuvaluan sitemap include hreflang alternates? (Would enable high-confidence JW.org page pairing without WOL)
- [ ] What is the exact `wtlocale` value for Tuvaluan `open` links? (`TVL` vs `VL`)
- [ ] How many WOL docIds actually have Tuvaluan translations? (Need to discover via scraping)
- [ ] Are there additional WOL Bible translation codes beyond `nwt` for Tuvaluan?
- [ ] What date range of daily text content exists in Tuvaluan?
- [ ] Should songs/lyrics be included or excluded? (Different text type; may confuse MT models)
- [ ] Should we include a Tokelauan subset as a related-language augmentation?
