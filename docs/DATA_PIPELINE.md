# Data Pipeline: Collection, Processing, and Training

Complete reference for the tv2en Tuvaluan-English parallel corpus — from raw scraping through cleaned datasets, decontaminated splits, and rendered training data.

---

## Table of Contents

1. [Data Sources](#1-data-sources)
2. [Raw Data Summary](#2-raw-data-summary)
3. [Cleaning Pipeline](#3-cleaning-pipeline)
4. [Cleaned Data Summary](#4-cleaned-data-summary)
5. [Decontaminated Splits](#5-decontaminated-splits)
6. [Unstructured Seed Data](#6-unstructured-seed-data)
7. [Rendered Training Data](#7-rendered-training-data)
8. [Step-by-Step: Running the Full Pipeline](#8-step-by-step-running-the-full-pipeline)
9. [Football Translation Pipeline](#9-football-translation-pipeline)

---

## 1. Data Sources

All parallel text is scraped from JW.org / Watchtower Online Library (WOL), which publishes religious content in ~1,000 languages including Tuvaluan. Every scraper uses Docker `curl-impersonate` (via `scripts/fetch.py`) because jw.org blocks standard HTTP clients via TLS fingerprint detection.

### 1.1 Bible (`scrape_bible.py`)

| Property | Value |
|---|---|
| Source | WOL Bible — all 66 books, 1,189 chapters |
| Alignment | Verse-level (`span.v` elements matched by verse ID) |
| Granularity | One pair per verse |
| Key fields | `book_num`, `book_name`, `chapter`, `verse` |
| Content type | `bible_verse` |

The highest-quality source — verse IDs provide exact structural alignment between TVL and EN.

### 1.2 Articles (`scrape_articles.py`)

| Property | Value |
|---|---|
| Source | WOL publications — Watchtower, Awake!, books, brochures, study guides |
| Alignment | Paragraph-level (matched by `data-pid` attribute) |
| Granularity | One pair per paragraph |
| Key fields | `doc_id`, `pub_code` |
| Content type | `article_paragraph` |
| Coverage | 7,255 unique docIds across 22 publication codes + 6 library categories |

The largest source by volume. Paragraphs are aligned via `data-pid` attributes that JW.org uses internally to link translated content.

### 1.3 Daily Text (`scrape_daily_text.py`)

| Property | Value |
|---|---|
| Source | WOL daily text devotionals |
| Alignment | Date-level (theme scripture + commentary per day) |
| Granularity | One pair per day |
| Key fields | `date` |
| Content type | `daily_text` |
| Coverage | 2017-01-01 through 2025-12-31 (3,287 dates, 0 gaps) |

Uses a 3-day page optimization — each fetched page contains 3 consecutive days, reducing HTTP requests by ~3x.

**Known issue:** May 2025 daily texts have truncated TVL (only theme, missing commentary).

### 1.4 Tuvalu App Expressions (`tuvalu_app.jsonl`)

| Property | Value |
|---|---|
| Source | Tuvalu language app — common expressions and phrases |
| Alignment | Expression-level |
| Granularity | One pair per expression |
| Content type | `expression` |

Short conversational phrases (greetings, common expressions). Small but linguistically diverse.

---

## 2. Raw Data Summary

All raw data lives in `data/aligned/` and is **immutable** — never modified after scraping.

### By source

| Source | File | Pairs | TVL chars | EN chars | ~Tokens | Size |
|---|---|---|---|---|---|---|
| Bible | `bible_verses.jsonl` | 30,838 | 4,837,553 | 4,110,723 | ~2.2M | 23 MB |
| Articles | `articles.jsonl` | 275,430 | 77,128,491 | 62,237,298 | ~34.8M | 262 MB |
| Daily text | `daily_text.jsonl` | 3,432 | 3,862,585 | 3,141,431 | ~1.8M | 8.4 MB |
| Tuvalu app | `tuvalu_app.jsonl` | 1,009 | 9,595 | 11,723 | ~5K | 392 KB |
| **Total** | | **310,709** | **85,838,224** | **69,501,175** | **~38.8M** | **294 MB** |

Token estimates use chars/4 approximation.

### Record schema (shared across all sources)

```json
{
  "id": "bible_1_1_1",
  "tvl": "I te kaamata ne faatu ai e te Atua na lagi maa te lalolagi.",
  "en": "In the beginning God created the heavens and the earth.",
  "content_type": "bible_verse",
  "domain": "bible",
  "alignment_method": "structural",
  "alignment_confidence": 1.0,
  "doc_id": "bible_1_1",
  "source_url_tvl": "https://wol.jw.org/tvl/...",
  "source_url_en": "https://wol.jw.org/en/...",
  "book_num": 1,
  "chapter": 1,
  "verse": 1,
  "tvl_chars": 60,
  "en_chars": 55,
  "length_ratio": 1.09
}
```

---

## 3. Cleaning Pipeline

**Script:** `scripts/clean_pipeline.py`
**Input:** `data/aligned/*.jsonl` (immutable) → **Output:** `data/cleaned/`

### 3.1 Cleaning stages (applied in order)

| Stage | What it does |
|---|---|
| **1. Text normalization** | NFC unicode normalization, strip invisible characters (zero-width spaces, BOM, soft hyphens), replace residual HTML entities (`&amp;`, `&nbsp;`), collapse whitespace |
| **2. Dedup by record ID** | Reject if the same `id` was already seen |
| **3. Dedup by content hash** | SHA-256 of `tvl.lower() + "|||" + en.lower()` — rejects semantically identical pairs regardless of ID |
| **4. Quality filters** | Applied in priority order (first match wins): |
| | `empty_text` — either side empty after normalization |
| | `metadata` — matches boilerplate regex (picture captions, chart markers, photo credits, copyright, page numbers, footnotes) |
| | `identical_pair` — TVL == EN (untranslated content) |
| | `too_short` — both sides below `min_chars` |
| | `too_long` — either side above `max_chars` |
| | `bad_ratio` — TVL/EN char ratio outside bounds (Bible uses tighter bounds than articles) |
| | `truncated_daily` — May 2025 daily texts with truncated TVL |
| **5. Rebuild record** | Strip internal fields, add computed `tvl_chars`, `en_chars`, `length_ratio` |

### 3.2 Cleaning profiles

| Setting | Balanced (default) | Strict | Lenient |
|---|---|---|---|
| `min_chars` | 10 | 20 | 5 |
| `max_chars` | 8,192 | 4,096 | 16,384 |
| `ratio_min` | 0.2 | 0.3 | 0.15 |
| `ratio_max` | 5.0 | 3.5 | 7.0 |
| `bible_ratio_min` | 0.4 | 0.5 | 0.3 |
| `bible_ratio_max` | 2.5 | 2.0 | 3.0 |

### 3.3 Rejection breakdown (balanced profile)

| Rejection reason | Count | % of rejected |
|---|---|---|
| `duplicate_id` | 118,553 | 90.3% |
| `duplicate_content` | 11,075 | 8.4% |
| `metadata` | 1,049 | 0.8% |
| `identical_pair` | 406 | 0.3% |
| `bad_ratio` | 246 | 0.2% |
| **Total rejected** | **131,329** | |

---

## 4. Cleaned Data Summary

**Output:** `data/cleaned/cleaned.jsonl` — 178,371 pairs (57.6% acceptance rate)

### By source

| Source | Pairs | TVL chars | EN chars | ~Tokens |
|---|---|---|---|---|
| Articles | 144,287 | 44,536,183 | 35,922,498 | ~20.1M |
| Bible | 30,827 | 4,833,946 | 4,109,540 | ~2.2M |
| Daily text | 3,257 | 3,688,487 | 2,972,467 | ~1.7M |
| **Total** | **178,371** | **53,058,616** | **43,004,505** | **~24.0M** |

### Character length statistics

| Metric | TVL chars | EN chars | Length ratio (TVL/EN) |
|---|---|---|---|
| Min | 6 | 4 | 0.20 |
| Mean | 297.5 | 241.1 | 1.243 |
| Median | 146 | 120 | 1.233 |
| Max | 8,078 | 2,447 | 5.00 |

Tuvaluan text averages ~24% longer than English (agglutinative morphology, more function words).

### Output files

| File | Description |
|---|---|
| `cleaned.jsonl` | Accepted pairs (178,371) |
| `rejected.jsonl` | Rejected pairs with rejection reason (131,329) |
| `cleaning_report.json` | Full statistics and config |
| `rejection_samples.jsonl` | Sampled rejections for manual review |

---

## 5. Decontaminated Splits

**Script:** `scripts/build_splits.py`
**Input:** `data/cleaned/cleaned.jsonl` → **Output:** `data/splits/`

### 5.1 Five-phase pipeline

#### Phase 1: Doc-level split assignment

All pairs from the same document land in the same split — no leakage via partial documents.

| Content type | Split strategy |
|---|---|
| **Bible** | Split by **whole book**. Test: Ruth, Philemon, Jude. Validation: Obadiah, Haggai, Titus, 2 John, 3 John. All other books → train. |
| **Articles** | Grouped by `doc_id`. SHA-256 hash of group key mod 10000 → deterministic bucket: test (5%), validation (5%), train (90%). |
| **Daily text** | Grouped by `date`. Same hash-bucket approach as articles. |

#### Phase 2: Build held-out n-gram index

Extracts **10-gram sets** (word-level, lowercased) from all test+validation Bible verses (both TVL and EN sides). Also builds exact text hash sets and short-verse containment lists.

#### Phase 3: Cross-source decontamination

Scans all non-Bible training rows against the held-out Bible index:

| Check | What it catches |
|---|---|
| **Exact match** | SHA-256 text hash collision — identical text across sources |
| **N-gram overlap** | Any shared 10-gram between training example and held-out Bible verse |
| **High containment** | For short verses (< 10 words), checks if verse token sequence appears contiguously in training text, or > 60% containment |

Contaminated rows are **quarantined** (moved to `quarantined.jsonl`), not deleted.

#### Phase 4: Validation

Six zero-leakage checks:
1. No `doc_id` overlap between splits
2. No Bible book overlap between splits
3. No date overlap between splits
4. No exact text overlap post-quarantine
5. No n-gram overlap post-quarantine
6. Minimum split sizes (test ≥ 300, val ≥ 100) with per-domain representation

#### Phase 5: Write outputs

### 5.2 Split sizes

| Split | Total | Bible | Articles | Daily text | TVL chars | EN chars |
|---|---|---|---|---|---|---|
| Train | 161,916 | 30,560 | 128,441 | 2,915 | 47,996,378 | 38,903,557 |
| Validation | 7,435 | 132 | 7,144 | 159 | 2,428,603 | 1,962,402 |
| Test | 7,467 | 134 | 7,177 | 156 | 2,409,505 | 1,940,333 |
| Quarantined | 1,553 | — | — | — | — | — |
| **Total** | **178,371** | **30,826** | **142,762** | **3,230** | | |

### 5.3 Quarantine details

- **1,553 pairs** quarantined total
- 1,450 flagged as `exact_match` (identical text found across Bible and non-Bible sources)
- 230 flagged as `ngram_overlap` (shared 10-grams with held-out Bible verses)
- Some pairs flagged for both reasons

### 5.4 Output files

| File | Lines | Description |
|---|---|---|
| `train.jsonl` | 161,916 | Training set |
| `validation.jsonl` | 7,435 | Validation set |
| `test.jsonl` | 7,467 | Held-out test set |
| `quarantined.jsonl` | 1,553 | Decontaminated pairs (removed from train) |
| `contamination_details.jsonl` | 1,553 | Quarantine reasons and matched n-grams |
| `split_report.json` | — | Full config, counts, validation results |

---

## 6. Unstructured Seed Data

**Script:** `scripts/build_unstructured_seed.py`
**Output:** `data/external/stage_a_seed/` (translation pairs), `data/external/stage_b_seed/` (term candidates)

Additional high-confidence TVL-EN pairs mined from non-JW.org sources to augment training data.

### 6.1 Sources

| Source | Type | Pairs kept | Notes |
|---|---|---|---|
| **Tuvaluan-English Dictionary** (PDF) | Dictionary entries parsed via `pdftotext` | 20,084 | TVL→EN section (9,304 pairs) + EN→TVL section (10,780 pairs). Confidence: 0.80–0.85. |
| **Tatoeba** (community translations) | Aligned sentence pairs | 14 | Tiny but high-confidence (1.0). Only 15 TVL-EN pairs exist in Tatoeba. |
| **OCR scanned PDFs** | Term extraction only | → Stage B | Tuvalu News Sheets, Nukufetau folklore. Feeds terminology, not translation pairs. |

### 6.2 Output files

| File | Lines | Description |
|---|---|---|
| `unstruct_dictionary_en_tvl.jsonl` | 10,780 | EN→TVL dictionary entries |
| `unstruct_dictionary_tvl_en.jsonl` | 9,304 | TVL→EN dictionary entries |
| `unstruct_tatoeba.jsonl` | 14 | Tatoeba sentence pairs |
| `rejected.jsonl` | 3 | Rejected entries with reasons |

---

## 7. Rendered Training Data

**Script:** `scripts/render_training_data.py`
**Input:** `data/splits/` + `data/external/` → **Output:** `data/finetune/stage_a_mt_v2/`

### 7.1 Rendering process

Each cleaned pair is rendered into **both translation directions** (TVL→EN and EN→TVL), doubling the example count. Each example becomes a 3-message chat:

```json
{
  "id": "bible_1_1_1::tvl_to_en",
  "messages": [
    {
      "role": "system",
      "content": "You are a careful translator between Tuvaluan and English. Translate faithfully. Preserve names, numbers, punctuation, line breaks, and structure when possible. Output only the translation."
    },
    {
      "role": "user",
      "content": "Translate from Tuvaluan to English:\n\n{source text}"
    },
    {
      "role": "assistant",
      "content": "{target text}"
    }
  ],
  "metadata": { "source": "bible", "direction": "tvl_to_en", ... }
}
```

**Template variation:** 3 prompt templates per direction, selected deterministically via stable hash of `row_id::direction`. Templates vary phrasing ("Translate from X to Y", "Translate the following X text into Y", "Convert this X text to Y") to prevent overfitting on a single prompt format.

### 7.2 Bible downsampling

Default `--bible-max-train-share` = 0.70 (70%). Prevents Bible data from dominating the training set. Bible examples are sorted by stable hash and truncated to the cap.

### 7.3 Final training data sizes

| File | Examples | Per direction | Chars | ~Tokens |
|---|---|---|---|---|
| `train_full.jsonl` | 360,106 | 180,053 each | 271,792,003 | ~68.0M |
| `train_balanced.jsonl` | 360,106 | 180,053 each | 271,792,003 | ~68.0M |
| `validation.jsonl` | 14,870 | 7,435 each | 12,740,472 | ~3.2M |
| `test.jsonl` | 14,934 | 7,467 each | 12,675,801 | ~3.2M |

### 7.4 Training set composition (by domain)

| Domain | Examples | % of train |
|---|---|---|
| Articles (book) | 256,882 | 71.3% |
| Bible | 61,120 | 17.0% |
| Dictionary (unstructured seed) | 36,246 | 10.1% |
| Daily text | 5,830 | 1.6% |
| Tatoeba | 28 | <0.01% |
| **Total** | **360,106** | |

### 7.5 Mean target length

| Split | Mean target chars |
|---|---|
| Train | 244.2 |
| Validation | 295.3 |
| Test | 291.3 |

---

## 8. Step-by-Step: Running the Full Pipeline

### Prerequisites

- Docker running (for `curl-impersonate`)
- `uv` installed
- `TINKER_API_KEY` in `.env` (for training/eval only)

### Stage 1: Scrape raw data

```bash
# 1a. Map the sitemap (optional — for exploration)
uv run scripts/scrape_sitemap.py

# 1b. Scrape Bible (all 66 books)
uv run scripts/scrape_bible.py --full

# 1c. Scrape articles (recursive library crawl)
uv run scripts/scrape_articles.py --library

# 1d. Scrape daily texts (2017–2025)
uv run scripts/scrape_daily_text.py --range 2017-01-01 2025-12-31

# 1e. Verify raw data stats
uv run scripts/stats.py
```

**Output:** `data/aligned/{bible_verses,articles,daily_text}.jsonl`
**Time:** Several hours (rate-limited HTTP fetching). All scrapers support resume — safe to interrupt and restart.

### Stage 2: Clean

```bash
uv run scripts/clean_pipeline.py
# Or preview first:
uv run scripts/clean_pipeline.py --dry-run
```

**Output:** `data/cleaned/cleaned.jsonl` (178,371 pairs)

### Stage 3: Build decontaminated splits

```bash
# 3a. Build splits
uv run scripts/build_splits.py

# 3b. Validate (CI-safe — exits 0 on pass, 1 on fail)
uv run scripts/validate_splits.py
```

**Output:** `data/splits/{train,validation,test,quarantined}.jsonl`

### Stage 4: Mine unstructured seed data (optional)

```bash
# Full pipeline: OCR + seed mining
uv run scripts/run_unstructured_datamining.py --run-name full-v1

# Or step by step:
uv run scripts/ocr_scanned_pdfs.py --inputs data/raw/pdfs/*.pdf --output-dir data/ocr/
uv run scripts/build_unstructured_seed.py --asset-dir data/external/assets/
```

**Output:** `data/external/stage_a_seed/*.jsonl` (20,098 pairs)

### Stage 5: Render training data

```bash
# Without unstructured seed:
uv run scripts/render_training_data.py

# With unstructured seed (recommended):
uv run scripts/render_training_data.py --include-unstructured
```

**Output:** `data/finetune/stage_a_mt_v2/{train_balanced,validation,test}.jsonl`

### Stage 6: Train

```bash
# One-time setup
bash scripts/bootstrap_tinker.sh

# Train Stage A translation adapter
uv run scripts/train_stage_a_translation.py \
  --config configs/stage_a_translation_qwen30b_base.json
```

### Stage 7: Evaluate

```bash
uv run scripts/eval_stage_a_translation.py \
  --config configs/stage_a_translation_qwen30b_base.json \
  --parallel 64
```

### Data flow diagram

```
jw.org (WOL)                    External sources
    │                                │
    ▼                                ▼
┌──────────────────┐     ┌──────────────────────┐
│  data/aligned/   │     │  data/external/       │
│  bible_verses    │     │  stage_a_seed/        │
│  articles        │     │  (dictionary+tatoeba) │
│  daily_text      │     └──────────┬────────────┘
│  tuvalu_app      │               │
└────────┬─────────┘               │
         │                         │
    clean_pipeline.py              │
         │                         │
         ▼                         │
┌──────────────────┐               │
│  data/cleaned/   │               │
│  cleaned.jsonl   │               │
└────────┬─────────┘               │
         │                         │
    build_splits.py                │
         │                         │
         ▼                         │
┌──────────────────┐               │
│  data/splits/    │               │
│  train/val/test  │               │
│  quarantined     │               │
└────────┬─────────┘               │
         │                         │
    render_training_data.py ◄──────┘
         │
         ▼
┌──────────────────────────┐
│  data/finetune/          │
│  stage_a_mt_v2/          │
│  train_balanced.jsonl    │  ← 360,106 chat examples (~68M tokens)
│  validation.jsonl        │  ← 14,870 chat examples (~3.2M tokens)
│  test.jsonl              │  ← 14,934 chat examples (~3.2M tokens)
└──────────┬───────────────┘
           │
      Tinker API
           │
           ▼
    Qwen3-30B-A3B LoRA
```

---

## 9. Football Translation Pipeline

A separate pipeline that scrapes English football news, translates to Tuvaluan via the trained model, and deploys to [talafutipolo.pages.dev](https://talafutipolo.pages.dev).

```bash
# Initialize database (one-time)
uv run scripts/init_football_db.py

# Scrape + translate
uv run scripts/pipeline_football.py

# Deploy to Cloudflare D1
uv run scripts/sync_to_d1.py
```

Sources: FIFA.com, Goal.com, Sky Sports. Articles are cleaned (`clean_article_bodies.py`), translated paragraph-by-paragraph via Tinker API with collapse detection (`detect_collapse.py`), and all translation attempts are recorded for future RL training.

See `docs/FOOTBALL_SETUP.md` for full deployment details.
