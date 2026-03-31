# Unstructured Data Sources

This document is the working catalog of the raw assets stored under `unstruct_lang_data/`.

Its job is not to explain the whole pipeline. Its job is to answer three operational questions:

1. what source is this?
2. what is its current pipeline status?
3. what should we do with it next?

Related docs:

- [UNSTRUCTURED_DATA_PIPELINE.md](UNSTRUCTURED_DATA_PIPELINE.md)
- [UNSTRUCTURED_DATA_MINING_PLAYBOOK.md](UNSTRUCTURED_DATA_MINING_PLAYBOOK.md)
- [DATA_PIPELINE.md](DATA_PIPELINE.md)

Last checked: `2026-03-30`

## 1. Snapshot

`unstruct_lang_data/` currently contains **182 files**.

| Type | Count |
|---|---:|
| PDF | 74 |
| MP4 | 66 |
| JPG | 26 |
| CSV | 4 |
| TSV | 3 |
| ZIP | 2 |
| JSONL | 2 |
| WEBM | 1 |
| DOCX | 1 |
| TXT | 1 |
| JSON | 1 |

This folder is broader than the current text-training pipeline.

Some assets are already converted into `data/external/stage_a_seed/*.jsonl`, some only feed OCR term mining, and some are still raw-only.

The Stage C manifest builder ignores the Finder helper file `REAL ONES ONLY/.DS_Store`, so `data/external/stage_c_seed/raw_source_manifest.jsonl` currently contains `181` primary-source rows rather than `182`.

## 2. Status legend

Use these labels consistently throughout this file.

| Status | Meaning |
|---|---|
| `Ingested` | Converted into Stage A seed rows in `data/external/stage_a_seed/` |
| `Merged` | Included in the merged training render `data/finetune/stage_a_mt_v2/` |
| `Term-only` | Used only for OCR term extraction in `data/external/stage_b_seed/unstruct_ocr_terms.jsonl` |
| `Raw-only` | Present in `unstruct_lang_data/` but not wired into the current text pipeline |
| `Duplicate/reference` | Extra copy, archive, manifest, or metadata helper rather than a primary source |
| `Media-only` | Audio/video asset not currently transcribed into text training data |

## 3. Stage C operator summary

If the goal is to improve Stage C quickly, the most important distinction is not just status. It is **recommended next use**.

### 3.1 Highest-value sources to promote next

These are the strongest candidates for native-document grounding once cleaned:

- `Tuvalu_News_Sheets_66-99.pdf`
- `Tuvalu_News_Sheets_Part 2.pdf`
- `REAL ONES ONLY/Documents/Historic archives 70s-2000_s/Tuvalu - News Sheets Part One (1).pdf`
- `The_magical_garlands_of_Nukufetau.pdf`
- `Matua Fakamoe of Nanumaga(1).pdf`
- `Am I Small/*.jpg`
- `Medicare is Australia’s health care system - Tuvaluan.pdf`
- `Tuvalu STEPS report 2015.pdf`
- `finance_budget_2025_2026_tuvaluan.pdf`
- `Action-Plan-for-Pacific-Education-20202030.pdf`
- `Tuvalu R2R BioRAP Field Guide.pdf`
- media assets that already contain subtitles or can be transcribed

### 3.2 Support sources that should remain support sources

These are useful for lexical grounding, bilingual anchoring, or terminology control, but should not become the behavioral backbone of Stage C:

- dictionary
- Tatoeba
- `corpus_v2`
- language cards
- grammar and biodiversity references

### 3.3 Sources to quarantine or treat cautiously

These should not be pulled into default training without extra review:

- duplicate copies
- archive bundles
- metadata exports and listing PDFs
- `REAL ONES ONLY/Documents/Don_t use yet/`
- OCR-heavy scans that remain page dumps rather than article-level recovery

### 3.4 Current Stage C outputs from this tree

The current Stage C build now materializes this inventory into:

- `data/external/stage_c_seed/raw_source_manifest.jsonl` with `181` manifest rows
- `data/external/stage_c_seed/extracted_text/page_text.jsonl` with `31793` extracted rows
- `data/external/stage_c_seed/ocr_recovered/native_news_articles.jsonl` with `41` recovered article bundles
- `data/external/stage_c_seed/native_doc_registry.jsonl` with `124` registered documents
- `data/finetune/stage_c_sft/train.jsonl` and `val.jsonl` for the default `native_plus_english` arm

Default Stage C SFT still excludes media-only assets, duplicate/reference files, quarantine PDFs, and English-dominant source bundles that fail the TVL-heavy gating used by the current builder.

## 4. Canonical root-level sources

These are the root-level files that originally seeded the unstructured work.

| Source | Description | Current status | Recommended next use |
|---|---|---|---|
| `DICTIONARY_Tuv_Palagi.pdf` | Tuvaluan-English dictionary PDF | `Ingested`, `Merged` | Keep as lexical and glossary support |
| `Tatoeba-v2023-04-12-en&tvl.tsv` | Tatoeba sentence and phrase pairs | `Ingested`, `Merged` | Keep as support only |
| `tuvalu_en_bilingual_corpus_full_listing.pdf` | Corpus listing reference PDF | `Duplicate/reference` | Reference only |
| `The_magical_garlands_of_Nukufetau.pdf` | Scanned children's book at repo root | `Term-only` | Promote to OCR recovery and grounded tasks |
| `Tuvalu_News_Sheets_66-99.pdf` | Historic news archive scan | `Term-only` | Promote to article-level OCR recovery |
| `Tuvalu_News_Sheets_Part 2.pdf` | Historic news archive scan | `Term-only` | Promote to article-level OCR recovery |
| `REAL ONES ONLY-20260310T045923Z-3-001.zip` | Archive bundle | `Duplicate/reference` | Do not train directly |

## 5. Word-pair and lexical sources

These are the best short-pair sources in the tree.

### 5.1 Dictionary

- Primary file: `DICTIONARY_Tuv_Palagi.pdf`
- Duplicate copy: `REAL ONES ONLY/Linguistic Academic Guides/DICTIONARY Tuv_Palagi (2).PDF.pdf`

Current outputs:

- `data/external/stage_a_seed/unstruct_dictionary_tvl_en.jsonl`
- `data/external/stage_a_seed/unstruct_dictionary_en_tvl.jsonl`
- `data/external/stage_b_seed/unstruct_dictionary_terms.jsonl`

Coverage:

- Stage A seed rows: `9304` TVL->EN and `10780` EN->TVL
- Merged Stage A v2 domain contribution: `46734` directional examples

Recommended use:

- glossary control
- entity normalization
- short lexical tasks
- constrained translation anchors

### 5.2 Tatoeba

- Primary file: `Tatoeba-v2023-04-12-en&tvl.tsv`
- Duplicate copy: `REAL ONES ONLY/word pairings and data sets/Tatoeba-v2023-04-12-en_26tvl (1).tsv`
- Status: `Ingested`, `Merged`

Current output:

- `data/external/stage_a_seed/unstruct_tatoeba.jsonl` with `14` rows

Recommended use:

- support only
- useful as a tiny anchor, not as a major behavioral source

### 5.3 Corpus v2 package

Folder:

- `REAL ONES ONLY/word pairings and data sets/tuvalu_en_bilingual_corpus_v2/`

Important files:

- `pairs/corpus_pairs_dedup.jsonl`
- `pairs/training_pairs.tsv`
- `pairs/corpus_pairs_with_audio.csv`
- `pairs/corpus_pairs_without_audio.csv`
- `metadata/corpus_full.jsonl`
- `metadata/corpus_full.csv`
- `tuvalu_en_bilingual_corpus_full_listing.pdf`

Status:

- pair data is `Ingested`, `Merged` via `unstruct_corpus_v2.jsonl`
- listing PDFs, CSVs, README, and metadata files are mostly `Duplicate/reference`

Current output:

- `data/external/stage_a_seed/unstruct_corpus_v2.jsonl` with `3658` rows

Recommended use:

- support data
- bilingual anchoring
- lexical control
- not the core of Stage C style learning

## 6. Government, health, education, and civic PDFs

These sit under `REAL ONES ONLY/Documents/` and are among the most useful sources for grounded instruction data.

### 6.1 Eng-TVL together

Folder:

- `REAL ONES ONLY/Documents/Eng-TVL together/`

| Source | Notes | Status | Recommended next use |
|---|---|---|---|
| `BILINGUAL Family Tax Benefit - Tuvaluan.pdf` | Bilingual government service document | `Ingested`, `Merged` | Keep in paired/bilingual support pool |
| `Child Care Subsidy - Tuvaluan.pdf` | Bilingual government service document | `Ingested`, `Merged` | Keep in paired/bilingual support pool |
| `mpp_te_gana_tuvalu_language_cards_bilingual.pdf` | Language-card style vocabulary source | `Ingested`, `Merged` | Lexical and support tasks only |
| `tepapa_tuvalu_activity_book_bilingual.pdf` | Te Papa educational activity book | `Ingested`, `Merged` | Support tasks and child-oriented rewrites |
| `Medicare is Australia’s health care system - Tuvaluan.pdf` | Health/system guide | `Raw-only` | Promote to grounded civic/health tasks |
| `Tuvalu STEPS report 2015.pdf` | Public health and survey report | `Raw-only` | Promote to report-summary and fact tasks |

### 6.2 En-TVL separate

Folder:

- `REAL ONES ONLY/Documents/En-TVL seperate/`

Sources already ingested:

- `BCG Vaccine/` pair
- `Citizen budget 2025/` pair
- `Climate children/` pair
- `Covid alert Levels/` pair
- `covid level 4/` pair
- `Diabetes/` pair
- `Health reform/` pair
- `Measles/` pair
- `Menincoccal (inconsistent format/` pair
- `Mormon Prayer/` JPG pair via OCR
- `Pac education 2030/` pair
- `Resilient emergency sheet/` pair
- `Strategic Action Plan /` pair
- `TCCP 2012/` pair
- `Traveller Factsheet/` pair
- `biogass /` pair

These currently feed:

- `data/external/stage_a_seed/unstruct_paired_pdfs.jsonl`
- `data/external/stage_a_seed/unstruct_bilingual_pdfs.jsonl`
- `data/external/stage_a_seed/unstruct_language_cards.jsonl`
- `data/external/stage_a_seed/unstruct_mormon_prayer.jsonl`

Known raw-only items in this family:

| Source | Status | Recommended next use |
|---|---|---|
| `Finance budget/finance_budget_2025_2026_en.pdf` | `Raw-only` | Pair with the TVL side for structured financial tasks |
| `Finance budget/finance_budget_2025_2026_tuvaluan.pdf` | `Raw-only` | Promote to native financial and budget tasks |
| `Pacific Education action Plan/Action-Plan-for-Pacific-Education-20202030.pdf` | `Raw-only` | Promote to education-policy summaries and QA |

### 6.3 “Don’t use yet” holding area

Folder:

- `REAL ONES ONLY/Documents/Don_t use yet/`

Files:

- `he2212_bcg_info_parents_tuvaluan.pdf`
- `he2233_bcg_aftercare_tuvaluan.pdf`
- `he2783_free_bowel_screening_tuvaluan.pdf`
- `he5031_measles_watch_for_symptoms_tuvaluan.pdf`
- `he5032_measles_protect_yourself_tuvaluan.pdf`
- `he5033_measles_could_you_have_it_tuvaluan.pdf`
- `he7521_bowel_test_kit_instructions_tuvaluan.pdf`

Status: `Raw-only`

Recommended next use:

- quarantine until pairing, deduplication, and source-role cleanup are done
- useful later as civic/health material once cleaned

## 7. Children’s books and oral material

Folder:

- `REAL ONES ONLY/Childrens books/`

| Source | Notes | Status | Recommended next use |
|---|---|---|---|
| `The gifts of Pai and Vau-spreads.pdf` | Bilingual children's book | `Ingested`, `Merged` | Keep in narrative support and style tasks |
| `Tuvalu Toku Atufenua Pele.pdf` | Bilingual essays/book | `Ingested`, `Merged` | Keep in narrative and expository support |
| `Matua Fakamoe of Nanumaga(1).pdf` | Additional children's book | `Raw-only` | Promote to OCR recovery and grounded narrative tasks |
| `The magical garlands of Nukufetau(2).pdf` | Duplicate or alternate copy of root scan | `Raw-only` | Compare against root version; keep best scan only |
| `Am I Small/*.jpg` | 24 screenshot images of a children's book | `Raw-only` | OCR/image extraction for page-aligned narrative tasks |

Oral and traditional narrative material:

- `REAL ONES ONLY/Documents/nanumea/Tefolaha tale 1 - Tepou, pp 292-307 from Heirs of Tefolaha.pdf`
- `REAL ONES ONLY/Documents/nanumea/Tefolaha tale 2 - Sosemea & Takitua, pp 308-316 from Heirs of Tefolaha.pdf`

Status: `Ingested`, `Merged`

These feed `unstruct_nanumea_tales.jsonl`.

Recommended use:

- culturally grounded rewrites
- summarization
- narrative style transfer
- held-out cultural eval slices

## 8. Linguistic and academic references

Folder:

- `REAL ONES ONLY/Linguistic Academic Guides/`

| Source | Notes | Status | Recommended next use |
|---|---|---|---|
| `epdf.pub_tuvaluan-a-polynesian-language-of-the-central-pacific-descriptive-grammars.pdf` | Besnier grammar source | `Ingested`, `Merged` | Support only; useful for analysis and lexical checks |
| `DICTIONARY Tuv_Palagi (2).PDF.pdf` | Duplicate dictionary copy | `Duplicate/reference` | Reference only |

Outputs:

- `data/external/stage_a_seed/unstruct_grammar.jsonl` with `2333` rows

## 9. Nature and biodiversity sources

Folder:

- `REAL ONES ONLY/Nature/`

| Source | Notes | Status | Recommended next use |
|---|---|---|---|
| `Fauna/Thaman_2015_Fishes_Tuvalu_Tokelau.PDF.pdf` | Fish names and biodiversity table | `Ingested`, `Merged` | Terminology and domain-tagged tasks |
| `Thaman 2016.pdf` | Flora listing | `Ingested`, `Merged` | Terminology and factual support |
| `Flora/Copy of Thaman 2016.pdf` | Duplicate flora copy | `Duplicate/reference` | Reference only |
| `Tuvalu R2R BioRAP Field Guide.pdf` | Broader biodiversity reference | `Raw-only` | Promote to grounded field-guide and biodiversity tasks |
| `tv-nr-05-en.pdf` | Nature-related PDF, English-side reference | `Raw-only` | Support pairing or glossary work, not native backbone |

Outputs:

- `data/external/stage_a_seed/unstruct_fishes.jsonl` with `998` rows
- `data/external/stage_a_seed/unstruct_flora.jsonl` with `436` rows

## 10. Historic archives and OCR-heavy scans

These are the most important long-form native-document sources still underused by the pipeline.

| Source | Notes | Status | Recommended next use |
|---|---|---|---|
| `Tuvalu_News_Sheets_66-99.pdf` | Root-level archive scan | `Term-only` | Re-run or upgrade OCR and recover article boundaries |
| `Tuvalu_News_Sheets_Part 2.pdf` | Root-level archive scan | `Term-only` | Re-run or upgrade OCR and recover article boundaries |
| `REAL ONES ONLY/Documents/Historic archives 70s-2000_s/Tuvalu News Sheets 66-99 (1).pdf` | Archive copy | `Raw-only` | Compare scan quality; keep the best copy |
| `REAL ONES ONLY/Documents/Historic archives 70s-2000_s/Tuvalu News Sheets Part 2 (1).pdf` | Archive copy | `Raw-only` | Compare scan quality; keep the best copy |
| `REAL ONES ONLY/Documents/Historic archives 70s-2000_s/Tuvalu - News Sheets Part One (1).pdf` | Part one archive copy | `Raw-only` | High-priority OCR recovery |
| `The_magical_garlands_of_Nukufetau.pdf` | Root-level scan | `Term-only` | Promote to page- or segment-level text recovery |

Current pipeline use:

- OCR artifacts exist in `data/external/ocr_scans/`
- these scans do **not** currently produce translation pairs
- they still contribute conservative OCR term candidates in `data/external/stage_b_seed/unstruct_ocr_terms.jsonl`
- Stage C now also recovers article-level outputs in `data/external/stage_c_seed/ocr_recovered/native_news_articles.jsonl`

Recommended next action:

- stop treating these as term-only sources
- promote them to article-level or page-level recovered text with provenance

## 11. Audio and video collections

Folders:

- `REAL ONES ONLY/Audio/`
- `REAL ONES ONLY/Audio/Tuvalu songs/`
- `REAL ONES ONLY/Audio/voice/`

Examples:

- `WIKITONGUES_ Paulo speaking Tuvaluan.mp4`
- `Tuvalu language strong but still under threat.mp4`
- `Tuvalu Language Week 2025.mp4`
- `Ocean-Buoy-Awareness-Tuvaluan...mp4`
- `Coastal_Inundation_Awareness_-_Tuvaluan.webm...`
- 20+ song files under `Audio/Tuvalu songs/`

Status: `Media-only`

Current limitation:

- there is no checked-in speech-to-text or subtitle extraction path feeding these files into training datasets

Recommended next use:

1. detect embedded subtitles or sidecars first
2. extract transcript text where available
3. add optional ASR/transcription later behind flags
4. use song files cautiously; spoken media should generally come first

## 12. Miscellaneous, duplicates, and support files

These exist in the tree but are not primary corpus sources.

| Source family | Notes | Status | Recommended next use |
|---|---|---|---|
| `REAL ONES ONLY/misc copies/*` | Duplicate copies of other PDFs | `Duplicate/reference` | Reference only |
| `REAL ONES ONLY/tuvalu.zip` | Archive bundle | `Duplicate/reference` | Do not train directly |
| `REAL ONES ONLY/Tuvalu - Instructions for building an eval.docx` | Planning doc, not corpus text | `Duplicate/reference` | Planning reference only |
| `tuvalu_en_bilingual_corpus_v2/README.txt` | Metadata helper | `Duplicate/reference` | Reference only |
| `tuvalu_en_bilingual_corpus_v2/metadata/*.csv|jsonl` | Corpus metadata | `Duplicate/reference` | Reference only |
| `tuvalu_en_bilingual_corpus_v2/pairs/*csv` | Derived or export helper tables | `Duplicate/reference` | Reference only |

## 13. Coverage summary

### 13.1 Sources already converted into Stage A seed files

- dictionary
- Tatoeba
- `corpus_v2` pairs
- paired government and health PDFs
- bilingual PDFs
- language cards
- Te Papa activity book
- Mormon prayer image pair
- Besnier grammar examples
- fishes and flora
- `Pai and Vau`
- `Toku Atufenua`
- Nanumea tales

### 13.2 Sources present in `unstruct_lang_data/` but still not converted into training rows

- `The_magical_garlands_of_Nukufetau.pdf`
- `Tuvalu_News_Sheets_66-99.pdf`
- `Tuvalu_News_Sheets_Part 2.pdf`
- `Matua Fakamoe of Nanumaga(1).pdf`
- `Am I Small/*.jpg`
- `Tuvalu STEPS report 2015.pdf`
- `Medicare is Australia’s health care system - Tuvaluan.pdf`
- `finance_budget_2025_2026_en.pdf`
- `finance_budget_2025_2026_tuvaluan.pdf`
- `Action-Plan-for-Pacific-Education-20202030.pdf`
- `Tuvalu R2R BioRAP Field Guide.pdf`
- `tv-nr-05-en.pdf`
- all audio and video assets

## 14. Important training note

The presence of a source in `unstruct_lang_data/` does **not** mean it was used in training.

Current repo state:

- raw unstructured extractions live in `data/external/stage_a_seed/`
- the standalone unstructured Stage A build lives in `data/finetune/stage_a_mt/unstructured_seed/`
- the merged render that includes unstructured data is `data/finetune/stage_a_mt_v2/`

If training used `data/finetune/stage_a_mt/train_balanced.jsonl`, that run did **not** use the unstructured corpus.

If training used `data/finetune/stage_a_mt_v2/train_balanced.jsonl`, then the merged unstructured sources listed here were included.

## 15. Immediate next actions

If the goal is Stage C improvement rather than catalog completeness, the next actions should be:

1. expand the historic-news recovery beyond the current `41` recovered article bundles
2. promote more raw-only civic, finance, health, and education PDFs from `candidate_only` to default grounded SFT eligibility
3. recover more children’s-book text from scans and images
4. build a subtitle/transcript path for the `Media-only` collection
5. keep duplicate, metadata, and quarantine files out of default training builds

That is the shortest path from raw asset inventory to usable Stage C data.
