# tv2en — Tuvaluan-English Parallel Corpus & Translation System

A complete pipeline for building a Tuvaluan↔English parallel corpus, training a neural translation model, and serving translated content — from raw web scraping through LoRA fine-tuning to a live bilingual football news site.

Tuvaluan (ISO 639-3: `tvl`) is a Polynesian language with ~11,000 speakers. Existing NLP resources are extremely limited. This project creates the largest known Tuvaluan-English parallel dataset and uses it to train a translation model that powers [talafutipolo.pages.dev](https://talafutipolo.pages.dev) — a Tuvaluan-language football news reader.

---

## Project Components

| Component | Description | Status |
|---|---|---|
| **Parallel corpus** | 310K raw pairs → 178K cleaned from JW.org/WOL | Complete |
| **Data pipeline** | Cleaning, decontamination, leak-proof splits | Complete |
| **Translation model** | Qwen3-30B-A3B LoRA via Tinker API (Stage A) | Trained — chrF++ 64.5, BLEU 46.7 |
| **Football site** | SolidStart + Cloudflare Pages/D1, 3 news sources | Live at [talafutipolo.pages.dev](https://talafutipolo.pages.dev) |
| **CI pipeline** | Auto-scrape football news every 6h, translate, deploy | Running |

---

## Repository Structure

```
tv/
├── scripts/                  # All pipeline scripts (see scripts/README.md)
├── training/                 # Python training modules
│   ├── common/               #   Shared infra (config, metrics, manifests, Tinker runtime)
│   ├── stage_a_mt/           #   Stage A: translation LoRA (build, train, eval, export)
│   ├── stage_b_agent/        #   Stage B: bilingual capability adapter
│   └── synthetic/            #   Synthetic data generation (selective translation)
├── site/                     # SolidStart football news site
│   └── src/routes/           #   Pages: home, article, category, search, fatele, feed
├── configs/                  # Training/eval JSON configs
├── tests/                    # Unit tests (splits, quality, schemas, selective translate)
├── data/
│   ├── aligned/              # Raw scraped pairs (IMMUTABLE)
│   ├── cleaned/              # After dedup + quality filtering
│   ├── splits/               # Decontaminated train/val/test
│   ├── finetune/             # Rendered chat JSONL for Tinker
│   ├── external/             # Unstructured seed (dictionary, Tatoeba)
│   └── football/             # Football article DB
├── docs/                     # Detailed documentation
├── vendor/                   # Git submodules (tinker-cookbook)
└── .github/workflows/        # CI: site deploy + football pipeline
```

---

## Dataset

### Sources

All parallel text is scraped from JW.org / Watchtower Online Library using Docker `curl-impersonate` (required — jw.org blocks standard HTTP clients via TLS fingerprint detection).

| Source | Alignment | Pairs | ~Tokens | Quality |
|---|---|---|---|---|
| **Bible** (66 books, 1,189 chapters) | Verse-level by `span.v` ID | 30,838 | 2.2M | Highest — structural 1:1 |
| **Articles** (7,255 docIds, 22 pub codes) | Paragraph-level by `data-pid` | 275,430 | 34.8M | High — attribute matching |
| **Daily text** (2017–2025, 3,287 dates) | Date-level | 3,432 | 1.8M | High — date alignment |
| **Tuvalu app** (expressions) | Expression-level | 1,009 | 5K | High — curated |
| **Total raw** | | **310,709** | **~38.8M** | |

Plus unstructured seed data mined from a Tuvaluan-English dictionary (20,098 entries) and Tatoeba (14 sentence pairs).

### Cleaning

`scripts/clean_pipeline.py` reads immutable raw data and applies: NFC normalization → ID deduplication → content hash deduplication → metadata/boilerplate filtering → identical-pair removal → length ratio filtering.

| Metric | Value |
|---|---|
| Raw input | 310,709 pairs |
| Accepted (balanced profile) | 178,371 pairs (57.6%) |
| Rejected | 131,329 (90% duplicate IDs from overlapping crawls) |
| Cleaned tokens | ~24M |

### Decontaminated Splits

`scripts/build_splits.py` creates leak-proof splits via a 5-phase pipeline:

1. **Doc-level assignment** — Bible split by whole book; articles/daily text by hashed `doc_id`/`date` buckets
2. **N-gram indexing** — 10-gram sets from held-out Bible verses
3. **Cross-source decontamination** — quarantine training rows that share exact text or 10-grams with test/val
4. **Validation** — zero-overlap checks across all dimensions
5. **Output** — clean train/val/test JSONL

| Split | Pairs | TVL chars | EN chars |
|---|---|---|---|
| Train | 161,916 | 48.0M | 38.9M |
| Validation | 7,435 | 2.4M | 2.0M |
| Test | 7,467 | 2.4M | 1.9M |
| Quarantined | 1,553 | — | — |

**Held-out Bible books:** Test: Ruth, Philemon, Jude. Validation: Obadiah, Haggai, Titus, 2 John, 3 John.

### Rendered Training Data

`scripts/render_training_data.py` converts splits into bidirectional chat JSONL (TVL→EN + EN→TVL) with template variation, Bible downsampling, and optional unstructured seed merging.

| File | Examples | ~Tokens |
|---|---|---|
| `train_balanced.jsonl` | 360,106 | ~68M |
| `validation.jsonl` | 14,870 | ~3.2M |
| `test.jsonl` | 14,934 | ~3.2M |

Training composition: 71% articles, 17% Bible, 10% dictionary seed, 2% daily text.

For the full data pipeline reference, see [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md).

---

## Translation Model

### Architecture

- **Base model:** Qwen/Qwen3-30B-A3B-Base (MoE — 30B total, 3B active)
- **Method:** LoRA fine-tuning (r=32) via [Tinker](https://thinkingemachines.ai) API
- **Training:** 3 epochs on 75,619 examples (~19M target tokens), batch size 64, lr 2e-4, max length 2048

### Training Curriculum

| Stage | Purpose | Status |
|---|---|---|
| **A: Translation adapter** | TVL↔EN translation LoRA on parallel corpus | Complete |
| **B: Capability adapter** | Bilingual tool use / reasoning on synthetic data | Planned |

Stage B uses selective translation — preserving code, JSON, tool schemas, and structured content while translating natural language.

### Stage A Results

| Metric | All | EN→TVL | TVL→EN |
|---|---|---|---|
| chrF++ | 64.5 | 68.2 | 59.9 |
| BLEU | 46.7 | 49.9 | 42.1 |
| Exact match | 2.8% | — | — |

Best checkpoint at step 2000 (val loss 0.5552). Overfitting visible by epoch 3.

---

## Football Site — Talafutipolo

A bilingual Tuvaluan football news reader at [talafutipolo.pages.dev](https://talafutipolo.pages.dev).

### Stack

- **Frontend:** SolidStart (SSR) with Cloudflare Pages
- **Database:** Cloudflare D1 (SQLite)
- **Sources:** Goal.com, FIFA.com, Sky Sports
- **Translation:** Tinker API with paragraph-level chunking and collapse detection

### Features

| Page | Description |
|---|---|
| **Home** (`/`) | Paginated article list with category filter and hero card |
| **Article** (`/articles/:id`) | Bilingual paragraph display with language toggle (TV / TV+EN / EN) |
| **Category** (`/category/:slug`) | Filtered article list |
| **Search** (`/search`) | Full-text article search |
| **Fatele** (`/fatele`) | Community dashboard — feedback counts by Tuvaluan island |
| **RSS** (`/feed.xml`) | RSS feed (20 latest articles) |

### CI Pipeline

The football pipeline runs automatically via GitHub Actions (`.github/workflows/football-pipeline.yml`):

- **Schedule:** Every 6 hours
- **Scrape:** Goal.com, FIFA.com, Sky Sports → writes directly to D1
- **Translate:** 2 articles per run via Tinker API (backlog clears gradually)
- **Collapse detection:** Multi-signal n-gram repetition analysis with 3-attempt retry

Site deploys automatically on push to `main` (`.github/workflows/deploy.yml`).

---

## Quick Start

### Prerequisites

- Python 3.14+ with [uv](https://docs.astral.sh/uv/)
- Docker (for `curl-impersonate`)
- Node 22+ (for the site)

### Install

```bash
git clone https://github.com/G-structure/tv.git && cd tv
uv sync
```

### Run the full data pipeline

```bash
# 1. Scrape (requires Docker running)
uv run scripts/scrape_bible.py --full
uv run scripts/scrape_articles.py --library
uv run scripts/scrape_daily_text.py --range 2017-01-01 2025-12-31

# 2. Clean
uv run scripts/clean_pipeline.py

# 3. Split with decontamination
uv run scripts/build_splits.py
uv run scripts/validate_splits.py

# 4. Render training data
uv run scripts/render_training_data.py --include-unstructured

# 5. Train (requires TINKER_API_KEY)
bash scripts/bootstrap_tinker.sh
uv run scripts/train_stage_a_translation.py --config configs/stage_a_translation_qwen30b_base.json

# 6. Evaluate
uv run scripts/eval_stage_a_translation.py --config configs/stage_a_translation_qwen30b_base.json --parallel 64
```

### Run the football pipeline

```bash
uv run scripts/pipeline_football.py                # scrape + translate
uv run scripts/sync_to_d1.py                       # push to Cloudflare D1
```

### Run the site locally

```bash
cd site && npm install && npm run dev
```

### Run tests

```bash
uv run pytest tests/
```

---

## Documentation

| Doc | Contents |
|---|---|
| [scripts/README.md](scripts/README.md) | All 39 scripts — descriptions, usage, CLI flags |
| [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md) | Full data pipeline: sources, cleaning, splits, token counts |
| [docs/TRAINING_PIPELINE.md](docs/TRAINING_PIPELINE.md) | Training commands and config reference |
| [docs/SCRAPING_PLAYBOOK.md](docs/SCRAPING_PLAYBOOK.md) | Step-by-step scraping reproduction guide |
| [docs/UNSTRUCTURED_DATA_PIPELINE.md](docs/UNSTRUCTURED_DATA_PIPELINE.md) | OCR and external data mining |
| [docs/SELECTIVE_TRANSLATION_SPEC.md](docs/SELECTIVE_TRANSLATION_SPEC.md) | Rules for preserving code/JSON in translation |
| [docs/FOOTBALL_SETUP.md](docs/FOOTBALL_SETUP.md) | Football site deployment and D1 setup |

---

## Technical Notes

### Why curl-impersonate?

JW.org performs TLS fingerprint detection — `requests`, `httpx`, and system `curl` all fail. Docker `curl-impersonate` mimics Firefox's TLS handshake to pass the check.

| Client | Result |
|---|---|
| `requests` | Timeout |
| `httpx` (HTTP/2) | `StreamReset error_code:2` |
| `curl` (system) | Exit 92 / Exit 56 |
| **Docker curl-impersonate** | **200 OK** |

### WOL locale codes

- Tuvaluan `wtlocale`: `VL` (not `TVL` — that resolves to English)
- WOL swap bundle: TVL = `tvl/r153/lp-vl`, EN = `en/r1/lp-e`

### Tuvaluan text characteristics

- TVL text averages ~24% longer than English (agglutinative morphology)
- Mean TVL/EN character ratio: 1.24
- Most content is translated from English originals (translationese is present)
- Domain bias: predominantly religious text; football site adds sports domain

---

## Prior Art

- **JW300** — 300+ language parallel corpus from JW.org. Our work extends this for Tuvaluan with richer metadata, decontaminated splits, and a trained model.
- **Christodoulopoulos Bible Corpus** — 100-language verse-aligned Bible (XML). Does not include Tuvaluan.
- **FLORES+** — Meta's 200+ language MT benchmark.

---

## License

Dataset and code in this repository. The parallel text is derived from publicly available JW.org content.
