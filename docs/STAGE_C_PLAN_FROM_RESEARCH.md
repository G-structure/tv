# Stage C Plan From Research

This is the canonical repo-facing Stage C execution memo.

It translates the earlier research-plan draft into the concrete Stage C order that now matches the shipped repo code, configs, and artifact layout.

Related docs:

- [STAGE_C_NATIVE_GROUNDING_SPEC.md](STAGE_C_NATIVE_GROUNDING_SPEC.md)
- [TRAINING_PIPELINE.md](TRAINING_PIPELINE.md)
- [UNSTRUCTURED_DATA_SOURCES.md](UNSTRUCTURED_DATA_SOURCES.md)
- [TVL_EN_TINKER_PLAN.md](TVL_EN_TINKER_PLAN.md)
- [PRIVATE_CHAT_DATA_PLAN.md](PRIVATE_CHAT_DATA_PLAN.md)
- [UNSTRUCTURED_DATA_PIPELINE.md](UNSTRUCTURED_DATA_PIPELINE.md)
- [UNSTRUCTURED_DATA_MINING_PLAYBOOK.md](UNSTRUCTURED_DATA_MINING_PLAYBOOK.md)
- [DATA_PIPELINE.md](DATA_PIPELINE.md)

Last updated: `2026-03-30`

## 1. Executive Summary

The paper set still supports the same core Stage C thesis:

1. native Tuvaluan documents should be the answer anchor
2. OCR recovery is worth doing when it unlocks real TVL articles
3. prompt-side variation is useful, but it should not replace grounded answers
4. hold-out eval should be by document
5. preference tuning should come after grounded SFT

The shipped repo implementation follows that order.

## 2. What The Repo Now Builds

The current Stage C builder lives at:

- `scripts/build_stage_c_pipeline.py`
- `tv/training/stage_c/pipeline.py`

It emits:

- `data/external/stage_c_seed/raw_source_manifest.jsonl`
- `data/external/stage_c_seed/extracted_text/page_text.jsonl`
- `data/external/stage_c_seed/ocr_recovered/native_news_articles.jsonl`
- `data/external/stage_c_seed/ocr_recovered/recovered_segments.jsonl`
- `data/external/stage_c_seed/native_doc_registry.jsonl`
- `data/external/stage_c_seed/grounded_sft.jsonl`
- `data/external/stage_c_seed/news_article_tasks.jsonl`
- `data/external/stage_c_seed/grounded_sft_mirrors.jsonl`
- `data/external/stage_c_seed/terms/entities.jsonl`
- `data/external/stage_c_seed/terms/glossary_candidates.jsonl`
- `data/external/stage_c_seed/terms/constrained_tasks.jsonl`
- `data/external/stage_c_seed/preferences.jsonl`
- `data/finetune/stage_c_sft/train.jsonl`
- `data/finetune/stage_c_sft/val.jsonl`
- `data/finetune/stage_c_sft/arms/*.jsonl`
- `data/finetune/stage_c_dpo/train.jsonl`
- `data/finetune/stage_c_dpo/val.jsonl`
- `data/finetune/stage_c_eval/manifest.jsonl`
- `data/finetune/stage_c_eval/held_out_native.jsonl`
- `eval/stage_c_native/manifest.jsonl`
- `eval/stage_c_native/human_check_subset.jsonl`

The Stage C eval entrypoint lives at:

- `scripts/eval_stage_c_native.py`
- `tv/training/stage_c/eval.py`

Optional offline OpenAI jobs live at:

- `scripts/stage_c_openai_jobs.py`
- `tv/training/stage_c/openai_jobs.py`

Those jobs default to dry-run request-manifest generation unless `--execute` is passed.

## 3. Research-Backed Decisions That Stayed Intact

### 3.1 Native corpora stay at the center

Stage C is still built around native or native-heavy TVL documents, especially:

- historic news scans
- civic and government PDFs
- health and education documents
- children’s books and oral/traditional material

Translated-English capability data is not the default Stage C backbone.

### 3.2 Filtering matters more than naive scale

The builder intentionally creates more grounded candidates than the default train render keeps.

That gives the repo room to:

- reject English-heavy bundles from the default SFT pool
- exclude duplicate and quarantine assets
- preserve a clean held-out split by document
- compare prompt-mixture arms instead of guessing

### 3.3 Preference tuning comes after grounded SFT

The repo now builds `preferences.jsonl` after the grounded SFT candidates exist.

The main failure targets remain:

- English leakage
- wrong-language drift
- translationese
- entity loss
- dropped numbers and dates
- unsupported hallucination

### 3.4 Eval is document-held-out and source-aware

The held-out eval set is document-based, not row-randomized.

It keeps explicit slices for:

- government and civic material
- cultural and narrative text
- OCR-noisy recovered news
- entity preservation
- mixed-prompt handling

## 4. Execution Order Chosen In Code

The shipped pipeline follows this order:

1. scan `unstruct_lang_data/` into a raw manifest
2. reuse existing Stage A seed rows and OCR artifacts where possible
3. extract or recover page text from PDFs and images
4. recover article-level native news bundles where feasible
5. register native documents with provenance and hold-out eligibility
6. generate grounded SFT, news tasks, mirrors, terminology tasks, and preferences
7. assemble Stage C SFT, DPO, and held-out eval renders
8. route Stage C training through dedicated configs on the existing Stage B trainer

This is the minimal safe integration path for the current repo.

## 5. Prompt-Mixture Ablations

The current four Stage C ablation arms are:

1. `native_only`
2. `native_plus_english`
3. `native_plus_stage_b_translated`
4. `native_plus_bilingual`

These are built automatically under `data/finetune/stage_c_sft/arms/` and can be trained by swapping config files rather than changing trainer code.

## 6. Current Default

The current default Stage C render is:

- `native_plus_english`

That choice is operational rather than final research dogma. The arm files exist so later runs can measure whether English mirrors, bilingual mirrors, or Stage-B-translated mirrors help or hurt.

## 7. What Is Still Deliberately Deferred

The repo now has Stage C build, eval, and offline job scaffolding, but these remain intentionally secondary:

- large translated-English-only Stage C expansion
- full RLHF infrastructure
- broad round-trip RL
- always-on ASR for all media assets
- live OpenAI batch execution as the default path

Those may matter later, but they are not required for a first grounded Stage C release.

## 8. Commands

```bash
uv run python scripts/build_stage_c_pipeline.py --config configs/stage_c_pipeline_default.json
uv run python scripts/eval_stage_c_native.py --config configs/stage_c_eval_native_oss120b.json --dry-run
uv run python scripts/train_stage_b_agent.py --config configs/stage_c_agent_oss120b_native_plus_english.json
uv run python scripts/train_stage_b_agent.py --config configs/stage_c_agent_oss120b_native_only.json
uv run python scripts/train_stage_b_agent.py --config configs/stage_c_agent_oss120b_native_plus_stage_b_translated.json
uv run python scripts/train_stage_b_agent.py --config configs/stage_c_agent_oss120b_native_plus_bilingual.json
```

## 9. Remaining Next Steps

The highest-value next steps after this Stage C implementation are:

1. run the full Stage C ablation trainings
2. score them on `data/finetune/stage_c_eval/manifest.jsonl`
3. expand OCR recovery beyond the current recovered native news set
4. add transcript extraction for the `Media-only` assets that have usable speech or captions
5. optionally run the offline OpenAI cleanup and preference manifests with `--execute`
