# tv2en — Tuvaluan-English LLM, Corpus, and Football Product Loop

A complete pipeline for building a Tuvaluan↔English parallel corpus, training specialized Tuvaluan models, and shipping a live bilingual football product that turns real usage into future language data.

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
| **Interaction export** | Normalized JSONL for feedback / corrections / polls | `scripts/export_football_interactions.py` |

---

## Repository Structure

```text
scripts/                      # Thin CLI entrypoints and orchestration
tv/
  common/                     # Shared config/IO/metrics/CLI helpers
  corpus/                     # Corpus cleaning, splits, rendering
  training/                   # Canonical training/eval/synthetic modules
site/                         # SolidStart football site
configs/                      # Training/eval JSON configs
tests/                        # Repo-local unit/smoke tests
data/                         # Corpus, splits, finetune data, football DB
docs/                         # Pipeline, training, scraping, and product docs
vendor/                       # Submodules and third-party code
.github/workflows/            # Deploy + football pipeline automation
```

---

## Dataset

### All Data Sources

Every source of TVL↔EN parallel data, sorted by token contribution to training. Two pipelines feed the final dataset: the **main pipeline** (JW.org + online dictionary → clean → splits → render) and the **unstructured seed** (PDFs, OCR, scraped corpora → ingest → merge).

| # | Source | Origin | Raw Pairs | Train Examples | ~Tokens | % |
|---|--------|--------|----------:|---------------:|--------:|---:|
| 1 | **JW.org Articles** — 7,255 docIds, 22 pub codes | WOL paragraph alignment | 275,430 | 247,236 | 57.5M | 77.2% |
| 2 | **Bible** — 66 books, 1,189 chapters | Verse-level by `span.v` ID | 30,838 | 60,862 | 8.5M | 11.5% |
| 3 | **Daily Text** — 2017–2025, 3,287 dates | Date-level 3-day page | 3,432 | 5,828 | 3.7M | 5.0% |
| 4 | **Dictionary PDF** — Tuvaluan-Palagi physical dictionary | `build_unstructured_seed.py` OCR extraction | 20,084 | 39,368 | 2.9M | 3.9% |
| 5 | **Corpus v2** — tuvalu.aa-ken.jp bilingual corpus | Word/expression JSON pairs | 3,658 | 7,316 | 536K | 0.7% |
| 6 | **Grammar** — Besnier's Tuvaluan descriptive grammar | Interlinear gloss extraction | 2,333 | 4,658 | 412K | 0.6% |
| 7 | **Online Dictionary** — tuvalu.aa-ken.jp (words + app) | Scraped 157 categories + 42 JSON endpoints | 4,421 | 7,366 | 407K | 0.5% |
| 8 | **Paired PDFs** — 16 government docs (health, budget, climate) | EN/TVL paragraph alignment | 573 | 1,138 | 191K | 0.3% |
| 9 | **Fishes** — Thaman 2015, Appendix III columnar table | TVL name ↔ EN common name | 998 | 1,996 | 146K | 0.2% |
| 10 | **Flora** — Thaman 2016, annotated systematic listing | TVL name ↔ EN common name | 436 | 850 | 61K | 0.1% |
| 11 | **Toku Atufenua Pele** — bilingual children's essays | Language detection + paragraph pairing | 80 | 160 | 23K | <0.1% |
| 12 | **Bilingual Gov Docs** — Family Tax, Child Care (AU) | TUVALUAN/ENGLISH header segmentation | 24 | 48 | 20K | <0.1% |
| 13 | **Te Papa Activity Book** — vocabulary lists | Manual extraction | 83 | 128 | 9K | <0.1% |
| 14 | **Nanumea Tales** — 2 oral tradition transcripts | Numbered paragraph alignment | 43 | 28 | 8K | <0.1% |
| 15 | **Language Cards** — MPP bilingual phrase cards | Two-column layout extraction | 45 | 88 | 7K | <0.1% |
| 16 | **Pai & Vau** — bilingual children's book | Alternating EN/TVL paragraph detection | 12 | 24 | 4K | <0.1% |
| 17 | **Tatoeba** — community sentence pairs | Direct download | 14 | 26 | 2K | <0.1% |
| 18 | **Mormon Prayer** — sacrament prayer JPG pair | Tesseract OCR | 1 | 2 | 1K | <0.1% |
| | **TOTAL** | | **342,505** | **377,122** | **~74.6M** | **100%** |

Sources 1–3 and 7 go through the main pipeline (scrape → clean → decontaminated splits → render). Sources 4–6 and 8–18 go through the unstructured seed pipeline (extract → quality cleanup → relaxed-threshold chat format → merge into training).

Vocabulary entries (dictionary words, species names, short phrases) use dedicated **vocabulary templates** ("What does X mean in English?", "How do you say X in Tuvaluan?") with a dictionary-specific system prompt. Sentence/paragraph entries use standard translation templates.

### Pipeline

```
data/aligned/*.jsonl ──→ clean_pipeline.py ──→ build_splits.py ──→ render_training_data.py ──→ train_balanced.jsonl
                                                                            ↑
data/external/stage_a_seed/*.jsonl ──→ build_stage_a_mt_data.py ────────────┘ (--include-unstructured)
        ↑
ingest_new_unstruct.py (12 sources)
build_unstructured_seed.py (dictionary PDF, Tatoeba)
```

### Cleaning

`scripts/clean_pipeline.py` reads immutable raw data from `data/aligned/` and applies: NFC normalization → macron correction (430 dictionary→corpus mappings) → glottal stop normalization → ID deduplication → content hash deduplication → metadata/boilerplate filtering → pub ref stripping → identical-pair removal → length ratio filtering. Dictionary entries use relaxed thresholds (`min_chars: 1`, `ratio_min: 0.005`).

| Metric | Value |
|---|---|
| Raw input | 314,121 pairs |
| Accepted (balanced profile) | 176,157 pairs (56.1%) |
| Rejected | 137,964 (90% duplicate IDs from overlapping crawls) |

### Decontaminated Splits

`scripts/build_splits.py` creates leak-proof splits via a 5-phase pipeline: doc-level assignment → n-gram indexing → cross-source decontamination → validation → output.

| Split | Pairs | Content |
|---|---|---|
| Train | 160,646 | 123,618 articles + 30,431 Bible + 3,541 words + 2,914 daily text + 142 expressions |
| Validation | 7,272 | 6,766 articles + 206 words + 159 daily text + 132 Bible + 9 expressions |
| Test | 7,407 | 6,884 articles + 229 words + 156 daily text + 134 Bible + 4 expressions |
| Quarantined | 832 | |

**Held-out Bible books:** Test: Ruth, Philemon, Jude. Validation: Obadiah, Haggai, Titus, 2 John, 3 John.

### Rendered Training Data

`scripts/render_training_data.py` converts splits into bidirectional chat JSONL (TVL→EN + EN→TVL) with template variation, Bible downsampling, and optional unstructured seed merging.

| File | Examples | ~Tokens |
|---|---|---|
| `train_balanced.jsonl` | 377,122 | ~74.6M |
| `validation.jsonl` | 14,544 | ~3.1M |
| `test.jsonl` | 14,814 | ~3.2M |

Composition: 65.6% articles, 16.1% Bible, 10.4% dictionary, 1.5% daily text, 4.6% vocabulary-template entries, 1.8% other external sources.

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
| **Article** (`/articles/:id`) | Bilingual paragraph display with language toggle (TV / TV+EN / EN) plus a coaching form for explicit feedback, mode preference, and correction notes |
| **Category** (`/category/:slug`) | Filtered article list |
| **Search** (`/search`) | Full-text article search |
| **Fatele** (`/fatele`) | Community dashboard — monthly signals, coaching submissions, correction counts, and island participation |
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

### Export football interactions

```bash
uv run python scripts/export_football_interactions.py
uv run python scripts/export_football_interactions.py --output-dir data/football/exports/demo_run
```

This writes normalized JSONL artifacts plus a manifest under
`data/football/exports/interactions/` by default. If Cloudflare D1 env vars are
set, the exporter uses the same env-based backend selection as the football
scripts; otherwise it reads the local SQLite DB at `data/football/football.db`.

### Demo the gamified loop locally

1. Run the football pipeline and sync it to D1:

```bash
uv run python scripts/pipeline_football.py --scrape-limit 10 --translate-limit 10
uv run python scripts/sync_to_d1.py
```

2. Start the site:

```bash
cd site && npm install && npm run dev
```

3. In the app:
- open any translated article
- fill out the `Coach the Translator` card
- visit `/fatele` to see the contribution reflected in the community dashboard

4. Export the collected interactions:

```bash
uv run python scripts/export_football_interactions.py
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
