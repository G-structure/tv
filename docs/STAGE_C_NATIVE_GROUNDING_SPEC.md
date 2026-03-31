# Stage C Native-Document Grounding Spec

This document defines **what Stage C is**, **what it is not**, and **what artifacts must exist** before Stage C data is considered ready for training.

Stage C is not a single prompt recipe. It is a **native-document grounding pipeline** for improving the bilingual capability adapter with real, source-backed Tuvaluan data.

The central rule is simple:

- keep the **assistant side** in real or source-faithful Tuvaluan whenever possible
- spend synthetic effort mainly on **prompt expansion**, **task variation**, **metadata**, **ranking**, and **evaluation** around grounded Tuvaluan answers

Related docs:

- [STAGE_C_PLAN_FROM_RESEARCH.md](STAGE_C_PLAN_FROM_RESEARCH.md)
- [TRAINING_PIPELINE.md](TRAINING_PIPELINE.md)
- [TVL_EN_TINKER_PLAN.md](TVL_EN_TINKER_PLAN.md)
- [UNSTRUCTURED_DATA_SOURCES.md](UNSTRUCTURED_DATA_SOURCES.md)
- [PRIVATE_CHAT_DATA_PLAN.md](PRIVATE_CHAT_DATA_PLAN.md)

Last updated: `2026-03-30`

## 1. Scope

In the current repo vocabulary:

- **Stage A** = translation adapter
- **Stage B** = bilingual capability adapter
- **Stage C** = the next data layer for the bilingual capability stage, built around grounded native-TVL sources rather than generic translated instructions

This spec covers:

1. source selection
2. grounded task construction
3. artifact layout
4. JSONL contracts
5. quality gates
6. preference data targets
7. evaluation requirements
8. minimum conditions for a first shippable Stage C build

This spec does **not** cover:

- LoRA hyperparameters
- trainer implementation details
- OCR model selection in full detail
- general repo-wide data conventions that already belong in [TRAINING_PIPELINE.md](TRAINING_PIPELINE.md)

## 2. Design goals

Stage C should improve the following behaviors:

1. native Tuvaluan instruction following
2. faithful use of local source documents
3. better register control across news, civic, formal, and plain-language writing
4. stronger preservation of names, institutions, dates, numbers, and quotations
5. lower English leakage, lower translationese, and lower wrong-language drift

Stage C should **not** primarily optimize for:

- maximum synthetic volume
- translated-English-only chat data
- RL-heavy experimentation under short deadlines
- ungrounded “write anything in Tuvaluan” generation

## 3. Operating thesis

The source document is the center of gravity.

For each native TVL document, page range, transcript span, or cleaned segment, Stage C should derive multiple task variants while preserving a **real** or **source-supported** Tuvaluan answer.

Preferred answer hierarchy:

1. **direct source text**
2. **light source-faithful transformation**
3. **fact compilation from source spans**
4. **clearly marked synthetic fallback** only when grounding is impossible and the example is excluded from the default training pool

The practical consequence is that Stage C should look much more like:

- “wrap this native TVL article in several task forms”

than like:

- “translate a large English chat dataset and call it Stage C”

## 4. Source policy

### 4.1 Priority order

Use the most native, local, and behaviorally rich material first.

Highest-priority source families:

- recovered native TVL news scans and notices
- government and civic documents with substantial Tuvaluan text
- oral-history, narrative, and cultural writing
- community-facing health and education documents
- radio-style and news-style prose
- cleaned subtitles or transcripts from media assets

Likely repo-local candidates are cataloged in [UNSTRUCTURED_DATA_SOURCES.md](UNSTRUCTURED_DATA_SOURCES.md).

### 4.2 Source tiers

Use a simple three-tier model when building Stage C.

**Tier A — backbone**

Use heavily for grounded answer creation.

Examples:

- recovered native news scans
- native-heavy civic PDFs
- oral and traditional narrative material
- long-form community documents with natural Tuvaluan prose

**Tier B — support**

Use for supplemental task expansion, bilingual anchoring, and terminology support.

Examples:

- paired PDFs
- bilingual government/health/education PDFs
- community informational materials with mixed TVL/EN coverage

**Tier C — lexical/anchor only**

Use for term control, glossary tasks, lexical augmentation, and short anchored rewrites, but not as the behavioral backbone of Stage C.

Examples:

- dictionary resources
- phrase corpora
- short sentence-pair datasets
- word cards

### 4.3 Source exclusions by default

Do not include the following in the default Stage C training pool unless they are explicitly cleaned and promoted:

- duplicate/reference copies
- metadata helper files
- archive bundles
- unpaired staging files from “don’t use yet” folders
- low-confidence OCR pages without article recovery
- media files with no transcript path

## 5. Task model

One source document should expand into **many** grounded task families. Do not concentrate the distribution around one `topic -> full article` template.

### 5.1 Required task families

Every serious Stage C build should support these families where source type allows:

- `native_request_article`
- `english_request_tvl_answer`
- `mixed_request_tvl_answer`
- `fact_sheet_to_article`
- `headline_generation`
- `lead_generation`
- `summary_short`
- `summary_medium`
- `qa_grounded`
- `entity_extraction`
- `quote_preservation`
- `radio_rewrite`
- `formal_rewrite`
- `plain_language_rewrite`
- `translation_to_english`
- `explain_in_english`

### 5.2 Optional later task families

These are useful, but should not block the first Stage C release:

- `bulletin_board_notice`
- `speech_script`
- `reading_comprehension`
- `stance_or_theme_identification`
- `error_correction`

### 5.3 Prompt modes

Each grounded answer should normally be paired with multiple prompt styles.

Minimum set:

1. `native_tvl_user`
2. `english_user_tvl_answer`
3. `mixed_user_tvl_answer`
4. `fact_sheet_transform`

Recommended extensions:

- `radio_host_style`
- `formal_official_style`
- `simple_reader_style`
- `headline_editor_style`

The answer may stay identical across these prompt modes when the point is prompt-side robustness rather than answer-side variation.

## 6. Grounding policy

### 6.1 What must stay real

Prefer real Tuvaluan for:

- assistant answers
- names and place names
- institution names
- dates, numbers, amounts, and local references
- quotations
- idiomatic phrasing that already exists in the source

### 6.2 What may be synthesized freely

Synthetic generation is encouraged for:

- user prompts
- rubrics
- task framing
- style labels
- metadata
- contrastive rejected answers
- extracted facts and structured control fields

### 6.3 Support classes

Every Stage C example must declare its support class.

Allowed support classes:

- `direct_support`
- `light_transform`
- `fact_compilation`
- `weak_support`

Default training pools should contain only:

- `direct_support`
- `light_transform`
- `fact_compilation`

`weak_support` examples may be kept for analysis or ablation, but should not enter the default SFT render.

## 7. Artifact layout

To match the repo’s current data split patterns, Stage C should use a **seed layer** and a **training render layer**.

### 7.1 Seed-layer artifacts

Use `data/external/stage_c_seed/` for source-level and intermediate artifacts.

The shipped builder keeps the canonical Stage C seed JSONLs flat at the Stage C root, with only OCR, extracted-text, terms, and optional offline job manifests in subdirectories.

Current layout:

```text
data/
  external/
    stage_c_seed/
      raw_source_manifest.jsonl
      native_doc_registry.jsonl
      grounded_sft.jsonl
      news_article_tasks.jsonl
      grounded_sft_mirrors.jsonl
      preferences.jsonl
      build_manifest.json
      extracted_text/
        page_text.jsonl
      ocr_recovered/
        native_news_articles.jsonl
        recovered_segments.jsonl
      terms/
        entities.jsonl
        glossary_candidates.jsonl
        constrained_tasks.jsonl
      openai_jobs/
        ...
```

### 7.2 Training-render artifacts

Use `data/finetune/` for training-ready outputs.

Recommended layout:

```text
data/
  finetune/
    stage_c_sft/
      train.jsonl
      val.jsonl
    stage_c_dpo/
      train.jsonl
      val.jsonl
    stage_c_eval/
      manifest.jsonl
      held_out_native.jsonl
```

This separation fixes a common ambiguity in the earlier drafts: source recovery and dataset assembly should not live in the same namespace.

## 8. Required artifact contracts

### 8.1 Native document registry

Purpose:

- canonical list of Stage C candidate documents
- provenance, quality status, rights notes, source family, and split eligibility

Suggested path:

- `data/external/stage_c_seed/native_doc_registry.jsonl`

Schema:

```json
{
  "doc_id": "native_doc:news:funafuti:2026-0001",
  "source_path": "unstruct_lang_data/REAL ONES ONLY/Documents/...",
  "source_family": "government_pdf",
  "title": "Optional title if known",
  "language_profile": "tvl_primary",
  "domains": ["news", "civic"],
  "content_kind": "article",
  "text_quality": {
    "ocr_quality": "medium",
    "normalization_status": "normalized_v1",
    "orthography_reviewed": false
  },
  "grounding_level": "direct_text",
  "copyright_status": "internal_research_only",
  "ingest_status": "candidate",
  "segment_count": 14,
  "holdout_eligible": true,
  "notes": "Native TVL article with some OCR noise.",
  "metadata": {
    "page_start": 3,
    "page_end": 5,
    "source_hash": "sha256:...",
    "created_at": "2026-03-31T00:00:00Z"
  }
}
```

### 8.2 OCR-recovered article pool

Purpose:

- promote OCR-heavy native scans into article-level Tuvaluan text that can feed grounded task generation

Suggested path:

- `data/external/stage_c_seed/ocr_recovered/native_news_articles.jsonl`

Schema:

```json
{
  "article_id": "ocr_news:1978-04-001",
  "source_scan": "unstruct_lang_data/Tuvalu_News_Sheets_66-99.pdf",
  "page_range": [12, 13],
  "layout_type": "bilingual_two_column",
  "language_profile": "tvl_primary",
  "tvl_text": "...",
  "en_text": "...",
  "segments": [
    {"segment_id": "seg_01", "text": "..."},
    {"segment_id": "seg_02", "text": "..."}
  ],
  "ocr_confidence": "medium",
  "recovery_method": "column_split_plus_manual_rules_v1",
  "qa_status": "spot_checked",
  "metadata": {
    "created_at": "2026-03-31T00:00:00Z"
  }
}
```

### 8.3 Grounded SFT examples

Purpose:

- source-anchored instruction-following examples for supervised tuning

Suggested path:

- `data/external/stage_c_seed/grounded_sft.jsonl`

The shipped Stage C rows keep source-family, domain, grounding-level, and register information under `provenance`.

Schema:

```json
{
  "id": "grounded_sft:news:funafuti:2026-0001:headline:native_tvl_user:00",
  "task_family": "headline_generation",
  "prompt_mode": "native_tvl_user",
  "prompt_lang": "tvl",
  "prompt_origin": "native",
  "assistant_lang": "tvl",
  "messages": [
    {
      "role": "system",
      "content": "You are a careful Tuvaluan writer. Stay faithful to the source."
    },
    {
      "role": "user",
      "content": "Tuku mai se ulutala puupuu mo tonu mo te tala tenei."
    },
    {
      "role": "assistant",
      "content": "..."
    }
  ],
  "answer_origin": "source_derived",
  "source_doc_id": "native_doc:news:funafuti:2026-0001",
  "source_segments": ["seg_04", "seg_05"],
  "support_type": "light_transform",
  "provenance": {
    "source_path": "unstruct_lang_data/Tuvalu_News_Sheets_66-99.pdf",
    "source_family": "historic_news_scan",
    "domains": ["news", "civic"],
    "grounding_level": "ocr_recovered_article",
    "register": "journalistic"
  }
}
```

### 8.4 Preference pairs

Purpose:

- language-fidelity and style-alignment tuning after grounded SFT exists

Suggested path:

- `data/external/stage_c_seed/preferences.jsonl`

Schema:

```json
{
  "id": "pref:news:funafuti:2026-0001:radio_rewrite:00",
  "task_family": "radio_rewrite",
  "prompt_mode": "english_user_tvl_answer",
  "messages": [
    {
      "role": "system",
      "content": "Write in natural Tuvaluan and stay faithful to the source."
    },
    {
      "role": "user",
      "content": "Rewrite this for radio in Tuvaluan."
    }
  ],
  "chosen": "Natural Tuvaluan answer...",
  "rejected": "Leaky or translationese answer...",
  "preference_reason_tags": [
    "english_leakage",
    "translationese",
    "entity_drop"
  ],
  "source_doc_id": "native_doc:news:funafuti:2026-0001",
  "source_segments": ["seg_04", "seg_05", "seg_06"],
  "metadata": {
    "pair_source": "model_judged_then_human_verified",
    "chosen_model": "gpt-5.4",
    "rejected_model": "gpt-5.4-mini"
  }
}
```

### 8.5 Held-out eval items

Purpose:

- document-level, contamination-resistant evaluation for native-TVL behaviors

Suggested path:

- `data/finetune/stage_c_eval/held_out_native.jsonl`
- `data/finetune/stage_c_eval/manifest.jsonl`
- `eval/stage_c_native/manifest.jsonl`

Schema:

```json
{
  "id": "eval:native_doc:news:funafuti:2026-0001:summary_medium:00",
  "split": "held_out",
  "task_family": "summary_medium",
  "prompt": "Fakatoetoefaka se tala tenei i te Tuvaluan.",
  "reference_answer": "Reference TVL answer...",
  "source_doc_id": "native_doc:news:funafuti:2026-0001",
  "source_segments": ["seg_02", "seg_03", "seg_04"],
  "scoring_axes": [
    "adequacy",
    "in_language_fidelity",
    "entity_preservation",
    "style_fit",
    "source_support"
  ],
  "metadata": {
    "human_verified": true
  }
}
```

## 9. Cleaning and filtering

Cleaning should happen **before** large-scale prompt expansion.

Mandatory preprocessing:

1. OCR repair
2. orthography normalization
3. duplicate removal
4. language-ID sanity checks
5. entity normalization
6. boilerplate stripping
7. domain balancing

Hard filters for grounded SFT:

- empty or near-empty answers
- unsupported answers
- obvious English leakage in TVL targets
- Samoan or other Polynesian drift where not supported by source
- broken entities, dates, or numbers
- duplicate prompt-answer pairs
- low-confidence OCR segments without review

Recommended quality fields:

- `language_purity_score`
- `entity_preservation_score`
- `source_support_score`
- `ocr_corruption_flag`
- `duplicate_cluster_id`

## 10. Preference-tuning targets

Preference data should be built only **after** the grounded SFT pool exists.

Primary rejection tags:

- `english_leakage`
- `translationese`
- `wrong_language`
- `entity_drop`
- `hallucinated_fact`
- `bad_register`
- `unnatural_headline`
- `quote_mangling`
- `overly_literal_translation`

Default ordering of work:

1. grounded SFT
2. preference data for fidelity and style
3. only then any RL-style work if still justified

## 11. Evaluation requirements

Stage C eval must be:

- native first
- held out by document, not by random row
- source-aware
- decomposed into explicit scoring axes
- partly human-checked

Required slices:

- news/article writing and rewriting
- government/civic notices
- cultural or narrative prose
- short factual notices
- OCR-noisy sources after cleanup
- mixed TVL/EN prompt handling

The scorer should not rely on a TVL-only model judge alone. Use rubric-based or pairwise scoring with human review on a subset.

## 12. Build sequence and acceptance gates

### 12.1 Stage C entry conditions

Before a source family can feed default Stage C training, it must have:

- stable provenance
- usable segmentation
- source-support tracking
- basic language sanity checks
- contamination-aware split assignment

### 12.2 Minimum build order

1. build or refresh the native document registry
2. recover OCR-heavy native scans into article-level text where possible
3. segment source documents with span tracking
4. generate grounded task families
5. filter and score candidates
6. build document-level held-out eval
7. assemble SFT render
8. build preference pairs for the winner only

### 12.3 First shippable Stage C package

If only one short build can ship, it should contain:

1. 50 to 200 native TVL source documents
2. cleaned segmentation and provenance
3. 6 to 12 grounded task variants per document
4. TVL-first assistant answers
5. one small preference set focused on leakage and entity preservation
6. one document-level held-out eval slice

That is the minimum useful Stage C release.

## 13. Non-goals

For the first serious Stage C pass, do **not** make these the center of effort:

- retranslating large English capability corpora as the main bet
- relying on a single article template family
- treating all synthetic TVL as equally reliable
- pushing RL as the primary optimization path
- trusting low-resource automatic judges without source-aware rubrics

## 14. Implementation checklist

A Stage C implementation is complete only when all of the following exist:

1. a native document registry
2. a recovered/segmented source pool with provenance
3. grounded task expansion for the required families
4. filtering for leakage, entity loss, duplicates, and weak support
5. a held-out native eval builder
6. a preference-pair builder for language fidelity
7. training-ready renders in `data/finetune/`

Once those exist, Stage C is a reproducible pipeline rather than an ad hoc prompting idea.

## 15. Shipped CLI surface

The current repo-facing Stage C commands are:

```bash
uv run python scripts/build_stage_c_pipeline.py --config configs/stage_c_pipeline_default.json
uv run python scripts/eval_stage_c_native.py --config configs/stage_c_eval_native_oss120b.json --dry-run
uv run python scripts/train_stage_b_agent.py --config configs/stage_c_agent_oss120b_native_plus_english.json
uv run python scripts/stage_c_openai_jobs.py --job-type prompt_synthesis --input-path data/external/stage_c_seed/grounded_sft_mirrors.jsonl
```

The Stage C trainer integration is intentionally minimal: it reuses the existing Stage B training entrypoint and swaps in Stage C JSONL renders through dedicated configs.
